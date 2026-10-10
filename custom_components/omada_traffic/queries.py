"""Aggregations that turn stored buckets into what the Traffic page shows.

Everything here is synchronous and runs on the collector's DB thread.
"""
from __future__ import annotations

import time
from bisect import bisect_right
from datetime import datetime, timedelta

from .const import HOME_BUCKET, RETAIN_MINUTES, TYPE_ORDER
from .settings import Settings
from .store import Store
from .vendors import PRIVATE, vendor as lookup_vendor

BANDWIDTH_WINDOWS = {"1h": 3600, "6h": 6 * 3600, "24h": 24 * 3600, "7d": 7 * 86400}
USAGE_WINDOWS = {"6h": 6 * 3600, "24h": 24 * 3600, "7d": 7 * 86400, "14d": 14 * 86400, "30d": 30 * 86400}


def _apple_type(name: str | None) -> str | None:
    """Device type implied by an Apple default name such as Sams-MacBook-Pro."""
    n = (name or "").lower()
    for word, kind in (("iphone", "Phone"), ("ipad", "Tablet"), ("macbook", "Laptop"), ("imac", "PC"), ("mac-mini", "PC")):
        if word in n:
            return kind
    return None


class ClientIndex:
    """Resolves MACs to names, owners and types using the settings."""

    def __init__(self, clients: list[dict], settings: Settings) -> None:
        self.settings = settings
        self.by_mac: dict[str, dict] = {}
        for c in clients:
            mac = c["mac"]
            maker = lookup_vendor(mac, c.get("vendor"))
            said = c.get("mdns_name")  # what the device calls itself, e.g. Sams-iPhone
            hint = _apple_type(said)
            if hint and maker == PRIVATE:
                maker = "Apple"
            omada_name = c.get("name") if c.get("name") != mac else None
            label = (
                (settings.clients.get(mac) or {}).get("name")
                # A name typed into Omada differs from the hostname the device reported.
                or (omada_name if omada_name and c.get("host_name") and omada_name != c.get("host_name") else None)
                or (said.replace("-", " ") if said else None)
                or omada_name
                or c.get("host_name")
            )
            unnamed = not label
            if not label:
                # No name anywhere: say who made it and keep the MAC's tail to tell devices apart.
                label = f"{maker} ({mac[-5:]})" if maker == PRIVATE else f"{maker} device ({mac[-5:]})" if maker else mac
            kind = settings.type_of(mac, c.get("category"), c.get("device_type"))
            if kind == "Other" and hint and not (settings.clients.get(mac) or {}).get("type"):
                kind = hint
            self.by_mac[mac] = {
                **c,
                "vendor": maker,
                "label": label,
                "owner": settings.owner(mac),
                "type": kind,
                # Nobody has said what this is yet: it is nameless or newly arrived.
                "needs_id": mac not in settings.clients and (unnamed or bool(c.get("new"))),
            }

    def macs_for(self, flt: str | None) -> list[str] | None:
        """None means the whole house."""
        if not flt or flt == "house":
            return None
        kind, _, value = flt.partition(":")
        if kind == "device":
            return [value] if value in self.by_mac else []
        if kind == "person":
            return [m for m, c in self.by_mac.items() if c["owner"] == value]
        if kind == "type":
            return [m for m, c in self.by_mac.items() if c["type"] == value]
        return None

    def label_for(self, flt: str | None) -> str:
        if not flt or flt == "house":
            return "The whole house"
        kind, _, value = flt.partition(":")
        if kind == "device":
            return self.by_mac.get(value, {}).get("label", value)
        if kind == "person":
            return f"{value}'s devices" if value != HOME_BUCKET else "Home/Shared devices"
        if kind == "type":
            return f"Devices, type {value}"
        return flt

    def owner(self, mac: str) -> str:
        return self.by_mac.get(mac, {}).get("owner", HOME_BUCKET)

    def type(self, mac: str) -> str:
        return self.by_mac.get(mac, {}).get("type", "Other")

    def people_order(self) -> list[str]:
        return [*self.settings.people, HOME_BUCKET]


# ---------------------------------------------------------------------- helpers
def _rank(totals: dict[str, list[float]], order: list[str] | None = None) -> list[dict]:
    rows = [{"key": k, "down": v[0], "up": v[1]} for k, v in totals.items() if v[0] or v[1]]
    rows.sort(key=lambda r: -(r["down"] + r["up"]))
    if order:
        pos = {k: i for i, k in enumerate(order)}
        rows.sort(key=lambda r: (-(r["down"] + r["up"]), pos.get(r["key"], 999)))
    return rows


def _group_series(rows, macs, idx: ClientIndex, key_fn, n_buckets, bucket_of):
    """Sum rows into per-group arrays of [down, up] per bucket."""
    out: dict[str, list[list[float]]] = {}
    mac_set = None if macs is None else set(macs)
    for ts, mac, down, up in rows:
        if mac_set is not None and mac not in mac_set:
            continue
        b = bucket_of(ts)
        if b is None or b < 0 or b >= n_buckets:
            continue
        key = key_fn(mac)
        arr = out.get(key)
        if arr is None:
            arr = out[key] = [[0.0, 0.0] for _ in range(n_buckets)]
        arr[b][0] += down
        arr[b][1] += up
    return out


def _sum_series(groups: dict[str, list[list[float]]], n: int) -> list[list[float]]:
    total = [[0.0, 0.0] for _ in range(n)]
    for arr in groups.values():
        for i in range(n):
            total[i][0] += arr[i][0]
            total[i][1] += arr[i][1]
    return total


# ---------------------------------------------------------------------- bandwidth
def bandwidth(store: Store, samples: dict, idx: ClientIndex, window: str, flt: str | None, end: int | None) -> dict:
    now = int(time.time())
    span = BANDWIDTH_WINDOWS.get(window, 3600)
    live = end is None or end >= now - 60
    end = now if live else int(end)
    start = end - span
    macs = idx.macs_for(flt)

    # Pick the source: in-memory 30 s samples for live short windows, else the
    # minute table (kept 48 h), else the 5-minute table.
    house_dq = samples.get("house")
    covered = bool(house_dq) and house_dq[0][0] <= start + 120
    if window in ("1h", "6h") and live and covered:
        source, step = "samples", (30 if window == "1h" else 60)
    elif window in ("1h", "6h") and start >= now - RETAIN_MINUTES + 600:
        source, step = "minutes", 60
    elif window == "7d":
        source, step = "fivemin", 1800
    else:
        source, step = "fivemin", 300

    n = max(1, span // step)
    t_axis = [start + i * step for i in range(n)]

    def bucket_of(ts: int):
        b = (ts - start) // step
        return b if 0 <= b < n else None

    counts: dict[int, int] = {}
    if source == "samples":
        rows = []
        for mac, dq in samples.items():
            if mac == "house":
                continue
            for ts, d, u in dq:
                if start <= ts < end:
                    rows.append((ts, mac, d, u))
        for ts, _d, _u in house_dq:
            if start <= ts < end:
                b = (ts - start) // step
                counts[b] = counts.get(b, 0) + 1
        divisor = 1.0
    else:
        rows = store.buckets(source, start, end)
        divisor = float(step)

    by_person = _group_series(rows, macs, idx, idx.owner, n, bucket_of)
    by_type = _group_series(rows, macs, idx, idx.type, n, bucket_of)
    house_groups = _group_series(rows, None, idx, idx.owner, n, bucket_of)
    if counts:
        for g in (by_person, by_type, house_groups):
            for arr in g.values():
                for b, c in counts.items():
                    if c > 1 and b < n:
                        arr[b][0] /= c
                        arr[b][1] /= c
    selected = _sum_series(by_person, n)
    house = _sum_series(house_groups, n)

    def to_rate(arr):
        return [[round(a[0] / divisor, 1), round(a[1] / divisor, 1)] for a in arr]

    sel_rate = to_rate(selected)
    house_rate = to_rate(house)

    elapsed = [i for i in range(n) if t_axis[i] <= now]
    cnt = max(len(elapsed), 1)
    avg_d = sum(sel_rate[i][0] for i in elapsed) / cnt
    avg_u = sum(sel_rate[i][1] for i in elapsed) / cnt
    pk_d = max(elapsed, key=lambda i: sel_rate[i][0], default=None)
    pk_u = max(elapsed, key=lambda i: sel_rate[i][1], default=None)

    now_d = now_u = 0.0
    if live:
        if macs is None:
            if house_dq:
                now_d, now_u = house_dq[-1][1], house_dq[-1][2]
        else:
            for m in macs:
                dq = samples.get(m)
                if dq and dq[-1][0] >= now - 120:
                    now_d += dq[-1][1]
                    now_u += dq[-1][2]
    elif sel_rate:
        now_d, now_u = sel_rate[-1][0], sel_rate[-1][1]

    def avg_rank(groups, order=None):
        totals = {
            k: [sum(a[0] for a in v) / divisor / cnt, sum(a[1] for a in v) / divisor / cnt]
            for k, v in groups.items()
        }
        return _rank(totals, order)

    return {
        "window": window,
        "source": source,
        "step": step,
        "start": start,
        "end": end,
        "live": live,
        "label": idx.label_for(flt),
        "t": t_axis,
        "selected": sel_rate,
        "house": house_rate,
        "people": {k: to_rate(v) for k, v in by_person.items()},
        "types": {k: to_rate(v) for k, v in by_type.items()},
        "people_rank": avg_rank(by_person, idx.people_order()),
        "types_rank": avg_rank(by_type, TYPE_ORDER),
        "stats": {
            "now": [round(now_d, 1), round(now_u, 1)],
            "avg": [round(avg_d, 1), round(avg_u, 1)],
            "peak_down": [sel_rate[pk_d][0], t_axis[pk_d]] if pk_d is not None else [0, None],
            "peak_up": [sel_rate[pk_u][1], t_axis[pk_u]] if pk_u is not None else [0, None],
        },
    }


# ---------------------------------------------------------------------- usage
def _daily_buckets(settings: Settings, start_hour: int, start_ts: int, end_ts: int) -> list[int]:
    """Local day-start epochs covering [start_ts, end_ts)."""
    out = []
    t = settings.day_start(start_ts, start_hour)
    while t < end_ts:
        out.append(t)
        local = datetime.fromtimestamp(t, settings.tz) + timedelta(days=1)
        t = int(local.timestamp())
    return out


def usage(store: Store, idx: ClientIndex, settings: Settings, window: str, flt: str | None, start_hour: int) -> dict:
    now = int(time.time())
    macs = idx.macs_for(flt)
    if window == "plan":
        start, cycle_end = settings.cycle_bounds(now)
        end = now
        daily = True
    else:
        span = USAGE_WINDOWS.get(window, 86400)
        daily = span > 86400
        end = now
        start = end - span
        cycle_end = None

    if daily:
        edges = _daily_buckets(settings, start_hour, start, cycle_end or end)
        edges = [e for e in edges if e >= settings.day_start(start, start_hour)]
        n = len(edges)
        def bucket_of(ts):
            # find last edge <= ts
            lo, hi = 0, n - 1
            if ts < edges[0]:
                return None
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if edges[mid] <= ts:
                    lo = mid
                else:
                    hi = mid - 1
            return lo
        rows = store.buckets("hours", edges[0], cycle_end or end)
        t_axis = edges
        unit = "day"
    else:
        start = start - start % 3600
        n = (end - start + 3599) // 3600
        t_axis = [start + i * 3600 for i in range(n)]
        def bucket_of(ts):
            b = (ts - start) // 3600
            return b if 0 <= b < n else None
        rows = store.buckets("hours", start, end)
        unit = "hour"

    by_person = _group_series(rows, macs, idx, idx.owner, n, bucket_of)
    by_type = _group_series(rows, macs, idx, idx.type, n, bucket_of)
    house_groups = _group_series(rows, None, idx, idx.owner, n, bucket_of)
    selected = _sum_series(by_person, n)
    house = _sum_series(house_groups, n)

    complete = [i for i in range(n) if t_axis[i] <= now]
    tot_d = sum(selected[i][0] for i in complete)
    tot_u = sum(selected[i][1] for i in complete)
    cnt = max(len(complete), 1)
    bd = max(complete, key=lambda i: selected[i][0], default=None)
    bu = max(complete, key=lambda i: selected[i][1], default=None)

    def rank(groups, order=None):
        return _rank({k: [sum(a[0] for a in v), sum(a[1] for a in v)] for k, v in groups.items()}, order)

    return {
        "window": window,
        "unit": unit,
        "start": t_axis[0] if t_axis else start,
        "end": end,
        "cycle_end": cycle_end,
        "label": idx.label_for(flt),
        "t": t_axis,
        "selected": selected,
        "house": house,
        "people": by_person,
        "types": by_type,
        "people_rank": rank(by_person, idx.people_order()),
        "types_rank": rank(by_type, TYPE_ORDER),
        "stats": {
            "total": [tot_d, tot_u],
            "avg": [tot_d / cnt, tot_u / cnt],
            "busiest_down": [selected[bd][0], t_axis[bd]] if bd is not None else [0, None],
            "busiest_up": [selected[bu][1], t_axis[bu]] if bu is not None else [0, None],
        },
    }


# ---------------------------------------------------------------------- summary
def summary(store: Store, samples: dict, idx: ClientIndex, settings: Settings, start_hour: int, last_poll: int | None) -> dict:
    now = int(time.time())
    day_start = settings.day_start(now, start_hour)
    next_day = int((datetime.fromtimestamp(day_start, settings.tz) + timedelta(days=1)).timestamp())
    today = store.sum_range("hours", day_start, now)
    today_d = sum(v[0] for v in today.values())
    today_u = sum(v[1] for v in today.values())

    # Daily average over the previous 7 complete days (fall back to what exists).
    hist_start = int((datetime.fromtimestamp(day_start, settings.tz) - timedelta(days=7)).timestamp())
    earliest = store.earliest_hour()
    days_avail = 0.0
    avg_day = 0.0
    if earliest is not None and earliest < day_start:
        hist_start = max(hist_start, earliest - earliest % 3600)
        hist = store.sum_range("hours", hist_start, day_start)
        total = sum(v[0] + v[1] for v in hist.values())
        days_avail = (day_start - hist_start) / 86400
        if days_avail > 0:
            avg_day = total / days_avail
    elapsed = now - day_start
    remaining = max(next_day - now, 0)
    if avg_day > 0:
        projected_today = today_d + today_u + avg_day * remaining / 86400
    elif elapsed > 600:
        projected_today = (today_d + today_u) * 86400 / elapsed
    else:
        projected_today = today_d + today_u

    dq = samples.get("house")
    now_rates = [dq[-1][1], dq[-1][2]] if dq else [0, 0]

    wan_names = {name.strip().lower(): port for port, name in store.wan_names().items()}
    plans_out = []
    for plan in settings.plans:
        c_start, c_end = settings.cycle_bounds(now, plan)
        port = wan_names.get((plan.wan or "").strip().lower()) if plan.wan else None
        if port is not None:
            w_down, w_up = store.wan_sum(port, c_start, now)
            measured = w_down + w_up
            source = "wan"
            first = store.wan_earliest(port)
            rate = None
        else:
            cyc = store.sum_range("hours", c_start, now)
            measured = sum(v[0] + v[1] for v in cyc.values())
            source = "clients"
            first = store.earliest_hour()
        # Baseline: ISP-reported usage on a date inside this cycle, plus what we measured since.
        base_ts = None
        if plan.baseline_date:
            try:
                bd = datetime.fromisoformat(plan.baseline_date).replace(tzinfo=settings.tz)
                base_ts = int(bd.timestamp())
            except ValueError:
                base_ts = None
        used = measured
        if base_ts is not None and c_start <= base_ts <= now:
            if port is not None:
                d2, u2 = store.wan_sum(port, base_ts - base_ts % 3600, now)
                since = d2 + u2
            else:
                since = sum(v[0] + v[1] for v in store.sum_range("hours", base_ts - base_ts % 3600, now).values())
            used = plan.baseline_gb * 1e9 + since
        # Recording may have begun after the cycle started.
        observed_from = max(c_start, first) if first is not None else now
        partial = first is None or (first > c_start + 3600 and not (base_ts is not None and c_start <= base_ts <= now))
        obs_days = max((now - observed_from) / 86400, 0.02)
        per_day_line = measured / obs_days if first is not None and observed_from >= c_start and partial else (used / max((now - c_start) / 86400, 0.1))
        c_days = max(1, round((c_end - c_start) / 86400))
        left = max((c_end - now) / 86400, 0)
        projected = used + per_day_line * left
        quota_b = plan.quota_gb * 1e9
        plans_out.append({
            "name": plan.name, "quota": quota_b, "used": used, "start": c_start, "end": c_end,
            "day": min(c_days, int((now - c_start) // 86400) + 1), "days": c_days,
            "projected": projected, "spare": (quota_b - projected) if quota_b else None,
            "source": source, "partial": partial, "observed_from": observed_from,
        })

    return {
        "now": now,
        "last_poll": last_poll,
        "read_age": (now - last_poll) if last_poll else None,
        "rates": now_rates,
        "today": {
            "down": today_d, "up": today_u, "start": day_start, "end": next_day,
            "projected": projected_today, "avg_day": avg_day, "days_in_avg": round(days_avail, 1),
        },
        "plan": plans_out[0],
        "plans": plans_out,
        "day_start_hour": start_hour,
    }


# ---------------------------------------------------------------------- table
def table(store: Store, samples: dict, idx: ClientIndex, settings: Settings, by: str, window: str, start_hour: int) -> dict:
    now = int(time.time())
    day_start = settings.day_start(now, start_hour)
    today = store.sum_range("hours", day_start, now)

    if window == "plan":
        start, _ = settings.cycle_bounds(now)
    else:
        start = now - USAGE_WINDOWS.get(window, 86400)
    daily = window in ("7d", "14d", "30d", "plan")
    if daily:
        edges = _daily_buckets(settings, start_hour, start, now)
        n = len(edges)
        t_axis = edges
        def bucket_of(ts):
            b = bisect_right(edges, ts) - 1
            return b if b >= 0 else None
        rows = store.buckets("hours", edges[0], now)
    else:
        start = start - start % 3600
        n = (now - start + 3599) // 3600
        t_axis = [start + i * 3600 for i in range(n)]
        def bucket_of(ts):
            b = (ts - start) // 3600
            return b if 0 <= b < n else None
        rows = store.buckets("hours", start, now)

    per_mac: dict[str, list[list[float]]] = {}
    for ts, mac, d, u in rows:
        b = bucket_of(ts)
        if b is None:
            continue
        arr = per_mac.setdefault(mac, [[0.0, 0.0] for _ in range(n)])
        arr[b][0] += d
        arr[b][1] += u

    house_total = sum(sum(a[0] + a[1] for a in arr) for arr in per_mac.values()) or 1.0

    def device_row(mac: str) -> dict:
        c = idx.by_mac[mac]
        dq = samples.get(mac)
        live = dq[-1] if dq and dq[-1][0] >= now - 120 else None
        spark = per_mac.get(mac, [[0.0, 0.0] for _ in range(n)])
        wtot = sum(a[0] + a[1] for a in spark)
        return {
            "key": mac,
            "kind": "device",
            "label": c["label"],
            "sub": " · ".join(x for x in [c["type"], c.get("vendor") if c.get("vendor") != PRIVATE else None, "Wired" if not c.get("wireless") else c.get("via"), f"{c['owner']}'s" if c["owner"] != HOME_BUCKET else None] if x),
            "owner": c["owner"],
            "type": c["type"],
            "online": bool(c.get("online")),
            "last_seen": c.get("last_seen"),
            "now": [live[1] if live else 0, live[2] if live else 0],
            "today": list(today.get(mac, (0, 0))),
            "window": [sum(a[0] for a in spark), sum(a[1] for a in spark)],
            "spark": spark,
            "share": wtot / house_total,
        }

    devices = [device_row(m) for m in idx.by_mac]

    def group_rows(key: str, order: list[str]) -> list[dict]:
        groups: dict[str, list[dict]] = {}
        for d in devices:
            groups.setdefault(d[key], []).append(d)
        out = []
        for g, kids in groups.items():
            kids.sort(key=lambda r: -(r["window"][0] + r["window"][1]))
            spark = [[sum(k["spark"][i][0] for k in kids), sum(k["spark"][i][1] for k in kids)] for i in range(n)]
            out.append({
                "key": g, "kind": key, "label": g,
                "sub": f"{len(kids)} device{'s' if len(kids) != 1 else ''} · {sum(1 for k in kids if k['online'])} connected",
                "now": [sum(k["now"][0] for k in kids), sum(k["now"][1] for k in kids)],
                "today": [sum(k["today"][0] for k in kids), sum(k["today"][1] for k in kids)],
                "window": [sum(k["window"][0] for k in kids), sum(k["window"][1] for k in kids)],
                "spark": spark,
                "share": sum(k["share"] for k in kids),
                "children": kids,
            })
        pos = {k: i for i, k in enumerate(order)}
        out.sort(key=lambda r: (-(r["window"][0] + r["window"][1]), pos.get(r["key"], 999)))
        return out

    if by == "person":
        rows_out = group_rows("owner", idx.people_order())
    elif by == "type":
        rows_out = group_rows("type", TYPE_ORDER)
    else:
        devices.sort(key=lambda r: -(r["window"][0] + r["window"][1]))
        rows_out = devices
    return {"by": by, "window": window, "unit": "day" if daily else "hour", "t": t_axis, "rows": rows_out, "now": now}


def meta(idx: ClientIndex, settings: Settings, collector_info: dict) -> dict:
    return {
        "people": idx.people_order(),
        "types": [t for t in TYPE_ORDER if any(c["type"] == t for c in idx.by_mac.values())],
        "clients": [
            {"mac": m, "label": c["label"], "owner": c["owner"], "type": c["type"], "online": bool(c.get("online")),
             "last_seen": c.get("last_seen"), "first_seen": c.get("first_seen"), "needs_id": c["needs_id"],
             "calls_itself": c.get("mdns_name"), "ip": c.get("ip"), "vendor": c.get("vendor"), "via": c.get("via")}
            for m, c in sorted(idx.by_mac.items(), key=lambda kv: kv[1]["label"].lower())
        ],
        "settings": {
            "timezone": str(settings.tz), "day_start_hour": settings.day_start_hour,
            "plans": [{"name": p.name, "quota_gb": p.quota_gb, "renewal_day": p.renewal_day, "wan": p.wan} for p in settings.plans],
        },
        **collector_info,
    }
