"""Polls the Omada controller and turns running totals into per-minute deltas."""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import RETAIN_FIVEMIN, RETAIN_MINUTES, SAMPLES_IN_MEMORY, SIGNAL_UPDATED
from .mdns import reverse_lookup
from .omada_api import OmadaClient, OmadaError
from .store import Store

_LOGGER = logging.getLogger(__name__)

MAX_PLAUSIBLE_BPS = 2_000_000_000 / 8  # 2 Gbit/s: anything above is a counter glitch
NAME_RETRY = 120  # ask an unnamed private-address device for its name this often (s)
NAME_REFRESH = 1800  # and a named one this often


class Collector:
    """Owns the poll loop, the delta logic, the in-memory samples and the DB."""

    def __init__(self, hass: HomeAssistant, api: OmadaClient, db_path: str, poll_seconds: int) -> None:
        self.hass = hass
        self.api = api
        self.poll_seconds = poll_seconds
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="omada_traffic")
        self._db_path = db_path
        self.store: Store | None = None
        self._task: asyncio.Task | None = None
        self._state: dict[str, dict] = {}
        # mac -> deque of (ts, down_bps, up_bps); "house" is the sum of all clients
        self.samples: dict[str, deque] = {}
        self.last_poll_ts: int | None = None
        self.last_error: str | None = None
        self.last_clients: list[dict[str, Any]] = []
        self._poll_count = 0
        self._wan_state: dict[int, dict] = {}
        self.wan_rates: dict[int, tuple[float, float]] = {}  # port -> (down_bps, up_bps)
        # A device whose private address rotated: new MAC -> the MAC its history lives under.
        self._alias: dict[str, str] = {}
        self._names: dict[str, str] = {}
        self._name_due: dict[str, float] = {}

    async def run_db(self, fn, *args):
        """Run a Store call on the DB thread."""
        return await self.hass.loop.run_in_executor(self._executor, fn, *args)

    async def async_start(self) -> None:
        self.store = await self.run_db(Store, self._db_path)
        self._state = await self.run_db(self.store.load_client_state)
        self._wan_state = await self.run_db(self.store.load_wan_state)
        self._alias = await self.run_db(self.store.load_aliases)
        self._names = await self.run_db(self.store.mdns_names)
        self._task = self.hass.loop.create_task(self._loop())

    async def async_stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.api.close()
        if self.store:
            await self.run_db(self.store.close)
        self._executor.shutdown(wait=False)

    async def _loop(self) -> None:
        while True:
            started = time.monotonic()
            try:
                await self.poll_once()
                self.last_error = None
                await self.poll_wan()
                await self.poll_names()
            except OmadaError as err:
                self.last_error = str(err)
                _LOGGER.warning("Omada poll failed: %s", err)
            except Exception:  # noqa: BLE001 - keep the loop alive
                self.last_error = "unexpected error, see log"
                _LOGGER.exception("Unexpected error in Omada poll")
            elapsed = time.monotonic() - started
            await asyncio.sleep(max(5.0, self.poll_seconds - elapsed))

    # ------------------------------------------------------------------ core
    async def poll_once(self) -> None:
        clients = await self.api.get_active_clients()
        now = int(time.time())
        rows, minute_adds, seen = [], {}, set()
        house_down = house_up = 0.0

        for c in clients:
            mac = c.get("mac")
            if not mac:
                continue
            seen.add(mac)
            td = int(c.get("trafficDown") or 0)
            tu = int(c.get("trafficUp") or 0)
            uptime = int(c.get("uptime") or 0)
            prev = self._state.get(mac)
            dd = du = 0
            dt = 0
            if prev and prev.get("ts"):
                dt = now - int(prev["ts"])
                pd, pu, pup = int(prev["down"] or 0), int(prev["up"] or 0), int(prev["uptime"] or 0)
                reset = td < pd or tu < pu
                if reset:
                    # Counters went backwards: they restarted since the last poll
                    # (roam/reconnect/reboot), so everything counted so far
                    # happened in this interval.
                    dd, du = td, tu
                    if uptime and uptime < dt:
                        dt = max(uptime, 1)
                    _LOGGER.info(
                        "Counter reset for %s: down %s->%s up %s->%s uptime %s->%s",
                        mac, pd, td, pu, tu, pup, uptime,
                    )
                else:
                    # Uptime may drop on a reconnect while the totals carry on;
                    # trust the totals, which is the safe reading.
                    dd, du = td - pd, tu - pu
                    if uptime + 5 < pup:
                        _LOGGER.info(
                            "Uptime reset without counter reset for %s: uptime %s->%s, down %s->%s",
                            mac, pup, uptime, pd, td,
                        )
                if dt > 0 and (dd / dt > MAX_PLAUSIBLE_BPS or du / dt > MAX_PLAUSIBLE_BPS):
                    _LOGGER.warning("Implausible delta for %s (%s B / %s s), dropping", mac, dd, dt)
                    dd = du = 0
                if dt > 0 and (dd or du):
                    self._spread(minute_adds, self._alias.get(mac, mac), now - dt, now, dd, du)
            self._state[mac] = {"down": td, "up": tu, "uptime": uptime, "ts": now, "online": True}

            # Rate for the live charts: delta-based when we have an interval,
            # otherwise Omada's own instantaneous figure.
            if dt > 0:
                down_bps, up_bps = dd / dt, du / dt
            else:
                down_bps, up_bps = float(c.get("activity") or 0), float(c.get("uploadActivity") or 0)
            house_down += down_bps
            house_up += up_bps
            self._push_sample(self._alias.get(mac, mac), now, down_bps, up_bps)

            via = c.get("apName") or c.get("switchName") or c.get("gatewayName") or ""
            if c.get("port") is not None and not c.get("wireless"):
                via = f"{via} port {c.get('port')}".strip()
            rows.append((
                mac, c.get("name"), c.get("hostName"), c.get("ip"), c.get("vendor"),
                c.get("deviceCategory"), c.get("deviceType"), via,
                1 if c.get("wireless") else 0, c.get("ssid"),
                now, now, td, tu, uptime, now, down_bps, up_bps,
            ))

        offline = [m for m, s in self._state.items() if m not in seen and s.get("online")]
        for m in offline:
            self._state[m]["online"] = False
            if m not in self._alias:
                self._push_sample(m, now, 0.0, 0.0)
        self._push_sample("house", now, house_down, house_up)

        if self.store:
            await self.run_db(self.store.write_poll, now, rows, minute_adds, offline)
            self._poll_count += 1
            if self._poll_count % 120 == 1:  # roughly hourly at 30 s polls
                await self.run_db(self.store.prune, RETAIN_MINUTES, RETAIN_FIVEMIN)

        self.last_poll_ts = now
        self.last_clients = clients
        async_dispatcher_send(self.hass, SIGNAL_UPDATED)

    async def poll_names(self) -> None:
        """Ask private-address devices for their own name, and follow rotations.

        A rotating private address makes a device look brand new to Omada. Its
        announced name stays the same, so addresses sharing a name are merged.
        """
        now = time.monotonic()
        due = {}
        for c in self.last_clients:
            mac, ip = c.get("mac"), c.get("ip")
            if mac and ip and mac[1] in "26AE" and self._name_due.get(mac, 0) <= now:
                due[ip] = mac
        if due:
            found = await reverse_lookup(list(due))
            names = {}
            for ip, mac in due.items():
                name = found.get(ip)
                if name and self._names.get(mac) != name:
                    names[mac] = name
                    _LOGGER.info("Device %s calls itself %s", mac, name)
                self._name_due[mac] = now + (NAME_REFRESH if name or mac in self._names else NAME_RETRY)
            if names and self.store:
                self._names.update(names)
                await self.run_db(self.store.set_mdns_names, names, int(time.time()))
        if self.store and self._names:
            for mac, canonical, name in await self.run_db(self.store.merge_same_name, int(time.time())):
                _LOGGER.info("Address %s is %s again (%s): history merged", mac, canonical, name)
                for m, c in list(self._alias.items()):
                    if c == mac:
                        self._alias[m] = canonical
                self._alias[mac] = canonical
                self.samples.pop(mac, None)

    async def poll_wan(self) -> None:
        """Read the gateway's WAN port counters: the true internet usage per line."""
        ports = await self.api.get_wan_ports()
        now = int(time.time())
        states, adds = [], []
        for p in ports:
            port = int(p.get("port"))
            name = p.get("portDesc") or p.get("name") or f"WAN {port}"
            rx, tx = int(p.get("rx") or 0), int(p.get("tx") or 0)
            prev = self._wan_state.get(port)
            if prev and prev.get("ts"):
                dt = max(now - int(prev["ts"]), 1)
                if rx < int(prev["rx"] or 0) or tx < int(prev["tx"] or 0):
                    # Gateway rebooted: counters restarted from zero.
                    dd, du = rx, tx
                    _LOGGER.info("WAN %s counters reset (gateway restart?)", name)
                else:
                    dd, du = rx - int(prev["rx"] or 0), tx - int(prev["tx"] or 0)
                if dd / dt > MAX_PLAUSIBLE_BPS or du / dt > MAX_PLAUSIBLE_BPS:
                    _LOGGER.warning("Implausible WAN delta on %s (%s B / %s s), dropping", name, dd, dt)
                    dd = du = 0
                if dd or du:
                    adds.append((now - now % 3600, port, dd, du))
                self.wan_rates[port] = (dd / dt, du / dt)
            self._wan_state[port] = {"name": name, "rx": rx, "tx": tx, "ts": now}
            states.append((port, name, rx, tx, now))
        if self.store and states:
            await self.run_db(self.store.write_wan, now, states, adds)

    @staticmethod
    def _spread(adds: dict, mac: str, start: int, end: int, dd: int, du: int) -> None:
        """Split a delta proportionally across the minute buckets it spans."""
        total = max(end - start, 1)
        first = start - start % 60
        t = first
        acc_d = acc_u = 0
        while t < end:
            seg_start, seg_end = max(t, start), min(t + 60, end)
            frac = (seg_end - seg_start) / total
            d = int(round(dd * frac))
            u = int(round(du * frac))
            acc_d += d
            acc_u += u
            if t + 60 >= end:  # last bucket absorbs rounding remainder
                d += dd - acc_d
                u += du - acc_u
            if d or u:
                k = (t, mac)
                cur = adds.get(k, (0, 0))
                adds[k] = (cur[0] + d, cur[1] + u)
            t += 60

    def _push_sample(self, key: str, ts: int, down: float, up: float) -> None:
        dq = self.samples.get(key)
        if dq is None:
            dq = self.samples[key] = deque()
        dq.append((ts, down, up))
        cutoff = ts - SAMPLES_IN_MEMORY
        while dq and dq[0][0] < cutoff:
            dq.popleft()
