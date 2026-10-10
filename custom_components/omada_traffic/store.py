"""SQLite storage for per-client traffic history.

All methods are synchronous and must run on the collector's single worker
thread (see Collector), which keeps SQLite happy and serialises writes.
"""
from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    mac TEXT PRIMARY KEY,
    name TEXT, host_name TEXT, ip TEXT, vendor TEXT,
    category TEXT, device_type TEXT, via TEXT, wireless INTEGER, ssid TEXT,
    first_seen INTEGER, last_seen INTEGER, online INTEGER DEFAULT 0,
    last_down INTEGER, last_up INTEGER, last_uptime INTEGER, last_ts INTEGER,
    now_down_bps REAL DEFAULT 0, now_up_bps REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS minutes (
    ts INTEGER NOT NULL, mac TEXT NOT NULL, down INTEGER NOT NULL, up INTEGER NOT NULL,
    PRIMARY KEY (ts, mac)
);
CREATE TABLE IF NOT EXISTS fivemin (
    ts INTEGER NOT NULL, mac TEXT NOT NULL, down INTEGER NOT NULL, up INTEGER NOT NULL,
    PRIMARY KEY (ts, mac)
);
CREATE TABLE IF NOT EXISTS hours (
    ts INTEGER NOT NULL, mac TEXT NOT NULL, down INTEGER NOT NULL, up INTEGER NOT NULL,
    PRIMARY KEY (ts, mac)
);
CREATE INDEX IF NOT EXISTS idx_minutes_ts ON minutes (ts);
CREATE INDEX IF NOT EXISTS idx_fivemin_ts ON fivemin (ts);
CREATE INDEX IF NOT EXISTS idx_hours_ts ON hours (ts);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS wan_hours (
    ts INTEGER NOT NULL, port INTEGER NOT NULL, down INTEGER NOT NULL, up INTEGER NOT NULL,
    PRIMARY KEY (ts, port)
);
CREATE TABLE IF NOT EXISTS aliases (
    mac TEXT PRIMARY KEY, canonical TEXT NOT NULL, name TEXT, created INTEGER
);
CREATE TABLE IF NOT EXISTS wan_state (
    port INTEGER PRIMARY KEY, name TEXT, last_rx INTEGER, last_tx INTEGER, last_ts INTEGER
);
"""

UPSERT = (
    "INSERT INTO {table} (ts, mac, down, up) VALUES (?, ?, ?, ?) "
    "ON CONFLICT(ts, mac) DO UPDATE SET down = down + excluded.down, up = up + excluded.up"
)


class Store:
    def __init__(self, path: str) -> None:
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(SCHEMA)
        have = {r[1] for r in self._conn.execute("PRAGMA table_info(clients)")}
        if "mdns_name" not in have:
            self._conn.execute("ALTER TABLE clients ADD COLUMN mdns_name TEXT")
            self._conn.execute("ALTER TABLE clients ADD COLUMN mdns_ts INTEGER")
        # Devices first seen after this moment count as new arrivals.
        self._conn.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('new_since', ?)", (str(int(time.time())),))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------ writes
    def write_poll(
        self,
        ts: int,
        client_rows: Iterable[tuple],
        minute_adds: dict[tuple[int, str], tuple[int, int]],
        offline_macs: Iterable[str],
    ) -> None:
        """Persist one poll: client metadata/state plus bucket increments."""
        cur = self._conn.cursor()
        cur.executemany(
            """INSERT INTO clients (mac, name, host_name, ip, vendor, category, device_type, via,
                   wireless, ssid, first_seen, last_seen, online, last_down, last_up, last_uptime,
                   last_ts, now_down_bps, now_up_bps)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(mac) DO UPDATE SET
                   name=excluded.name, host_name=excluded.host_name, ip=excluded.ip,
                   vendor=excluded.vendor, category=excluded.category, device_type=excluded.device_type,
                   via=excluded.via, wireless=excluded.wireless, ssid=excluded.ssid,
                   last_seen=excluded.last_seen, online=1, last_down=excluded.last_down,
                   last_up=excluded.last_up, last_uptime=excluded.last_uptime, last_ts=excluded.last_ts,
                   now_down_bps=excluded.now_down_bps, now_up_bps=excluded.now_up_bps""",
            client_rows,
        )
        offline = list(offline_macs)
        if offline:
            cur.executemany(
                "UPDATE clients SET online=0, now_down_bps=0, now_up_bps=0 WHERE mac=?",
                [(m,) for m in offline],
            )
        if minute_adds:
            mins = [(t, m, d, u) for (t, m), (d, u) in minute_adds.items()]
            cur.executemany(UPSERT.format(table="minutes"), mins)
            five: dict[tuple[int, str], list[int]] = {}
            hrs: dict[tuple[int, str], list[int]] = {}
            for (t, m), (d, u) in minute_adds.items():
                k5 = (t - t % 300, m)
                kh = (t - t % 3600, m)
                five.setdefault(k5, [0, 0])
                five[k5][0] += d
                five[k5][1] += u
                hrs.setdefault(kh, [0, 0])
                hrs[kh][0] += d
                hrs[kh][1] += u
            cur.executemany(UPSERT.format(table="fivemin"), [(t, m, v[0], v[1]) for (t, m), v in five.items()])
            cur.executemany(UPSERT.format(table="hours"), [(t, m, v[0], v[1]) for (t, m), v in hrs.items()])
        cur.execute("INSERT INTO meta (key, value) VALUES ('last_poll', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(ts),))
        self._conn.commit()

    def prune(self, retain_minutes: int, retain_fivemin: int) -> None:
        now = int(time.time())
        cur = self._conn.cursor()
        cur.execute("DELETE FROM minutes WHERE ts < ?", (now - retain_minutes,))
        cur.execute("DELETE FROM fivemin WHERE ts < ?", (now - retain_fivemin,))
        self._conn.commit()

    # ------------------------------------------------------------------ reads
    def load_client_state(self) -> dict[str, dict]:
        cur = self._conn.execute(
            "SELECT mac, last_down, last_up, last_uptime, last_ts, online FROM clients"
        )
        return {
            r[0]: {"down": r[1], "up": r[2], "uptime": r[3], "ts": r[4], "online": bool(r[5])}
            for r in cur.fetchall()
        }

    def clients(self) -> list[dict]:
        """One row per device: addresses merged by merge_same_name are folded together."""
        cur = self._conn.execute(
            """SELECT mac, name, host_name, ip, vendor, category, device_type, via, wireless, ssid,
                      first_seen, last_seen, online, now_down_bps, now_up_bps, mdns_name FROM clients"""
        )
        cols = [c[0] for c in cur.description]
        rows = {r[0]: dict(zip(cols, r)) for r in cur.fetchall()}
        new_since = int(self.meta("new_since") or 0)
        for r in rows.values():
            r["new"] = (r["first_seen"] or 0) >= new_since
        for mac, canonical in self.load_aliases().items():
            old, new = rows.get(canonical), rows.pop(mac, None)
            if not new:
                continue
            if not old:
                rows[canonical] = {**new, "mac": canonical}
                continue
            old["addresses"] = old.get("addresses", 1) + 1
            old["new"] = False  # a known device back under another address
            old["first_seen"] = min(old["first_seen"] or new["first_seen"], new["first_seen"] or old["first_seen"])
            if (new["last_seen"] or 0) >= (old["last_seen"] or 0):
                # The newest address describes where the device is now.
                for k in ("ip", "via", "wireless", "ssid", "last_seen", "online", "now_down_bps", "now_up_bps", "mdns_name"):
                    old[k] = new[k]
                for k in ("vendor", "category", "device_type"):
                    if new[k] and new[k] not in ("Unknown", "Others"):
                        old[k] = new[k]
        return list(rows.values())

    # ------------------------------------------------------------------ rotating addresses
    def load_aliases(self) -> dict[str, str]:
        return dict(self._conn.execute("SELECT mac, canonical FROM aliases").fetchall())

    def set_mdns_names(self, names: dict[str, str], ts: int) -> None:
        self._conn.executemany(
            "UPDATE clients SET mdns_name=?, mdns_ts=? WHERE mac=?", [(n, ts, m) for m, n in names.items()]
        )
        self._conn.commit()

    def mdns_names(self) -> dict[str, str]:
        return dict(self._conn.execute("SELECT mac, mdns_name FROM clients WHERE mdns_name IS NOT NULL").fetchall())

    def merge_same_name(self, ts: int) -> list[tuple[str, str, str]]:
        """Fold addresses that announce the same device name into one device.

        A device with a rotating private address comes back as a new MAC with
        the same name. Merge only when that is the plain reading: every address
        but the oldest is a private one, and at most one of them is connected
        (two live devices sharing a name are left alone).
        Returns (mac, canonical, name) for each address merged.
        """
        aliases = self.load_aliases()
        groups: dict[str, list[tuple]] = {}
        for mac, name, online, first_seen in self._conn.execute(
            "SELECT mac, mdns_name, online, first_seen FROM clients WHERE mdns_name IS NOT NULL"
        ):
            groups.setdefault(name, []).append((mac, online, first_seen or 0))
        merged = []
        for name, members in groups.items():
            roots: dict[str, dict] = {}
            for mac, online, first_seen in members:
                r = roots.setdefault(aliases.get(mac, mac), {"online": 0, "first": first_seen})
                r["online"] |= online or 0
                r["first"] = min(r["first"], first_seen)
            if len(roots) < 2 or sum(r["online"] for r in roots.values()) > 1:
                continue
            ordered = sorted(roots, key=lambda m: roots[m]["first"])
            canonical, rest = ordered[0], ordered[1:]
            if not all(m[1] in "26AE" for m in rest):
                continue
            cur = self._conn.cursor()
            for mac in rest:
                for table in ("minutes", "fivemin", "hours"):
                    cur.execute(
                        f"INSERT INTO {table} (ts, mac, down, up) SELECT ts, ?, down, up FROM {table} WHERE mac=? "
                        "ON CONFLICT(ts, mac) DO UPDATE SET down = down + excluded.down, up = up + excluded.up",
                        (canonical, mac),
                    )
                    cur.execute(f"DELETE FROM {table} WHERE mac=?", (mac,))
                cur.execute("UPDATE aliases SET canonical=? WHERE canonical=?", (canonical, mac))
                cur.execute(
                    "INSERT INTO aliases (mac, canonical, name, created) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(mac) DO UPDATE SET canonical=excluded.canonical",
                    (mac, canonical, name, ts),
                )
                merged.append((mac, canonical, name))
            self._conn.commit()
        return merged

    def buckets(self, table: str, start: int, end: int, macs: list[str] | None = None) -> list[tuple]:
        """Rows (ts, mac, down, up) with start <= ts < end."""
        sql = f"SELECT ts, mac, down, up FROM {table} WHERE ts >= ? AND ts < ?"
        args: list = [start, end]
        if macs is not None:
            if not macs:
                return []
            sql += " AND mac IN (%s)" % ",".join("?" * len(macs))
            args.extend(macs)
        return self._conn.execute(sql, args).fetchall()

    def sum_range(self, table: str, start: int, end: int) -> dict[str, tuple[int, int]]:
        """Per-mac totals in [start, end)."""
        cur = self._conn.execute(
            f"SELECT mac, SUM(down), SUM(up) FROM {table} WHERE ts >= ? AND ts < ? GROUP BY mac",
            (start, end),
        )
        return {r[0]: (r[1] or 0, r[2] or 0) for r in cur.fetchall()}

    def set_meta(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value)
        )
        self._conn.commit()

    def meta(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def earliest_hour(self) -> int | None:
        row = self._conn.execute("SELECT MIN(ts) FROM hours").fetchone()
        return row[0] if row and row[0] is not None else None

    # ------------------------------------------------------------------ WAN lines
    def load_wan_state(self) -> dict[int, dict]:
        cur = self._conn.execute("SELECT port, name, last_rx, last_tx, last_ts FROM wan_state")
        return {r[0]: {"name": r[1], "rx": r[2], "tx": r[3], "ts": r[4]} for r in cur.fetchall()}

    def write_wan(self, ts: int, states: list[tuple], adds: list[tuple]) -> None:
        """states: (port, name, rx, tx, ts); adds: (hour_ts, port, down, up)."""
        cur = self._conn.cursor()
        cur.executemany(
            """INSERT INTO wan_state (port, name, last_rx, last_tx, last_ts) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(port) DO UPDATE SET name=excluded.name, last_rx=excluded.last_rx,
                   last_tx=excluded.last_tx, last_ts=excluded.last_ts""",
            states,
        )
        cur.executemany(
            "INSERT INTO wan_hours (ts, port, down, up) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(ts, port) DO UPDATE SET down = down + excluded.down, up = up + excluded.up",
            adds,
        )
        self._conn.commit()

    def wan_names(self) -> dict[int, str]:
        return {r[0]: r[1] or "" for r in self._conn.execute("SELECT port, name FROM wan_state")}

    def wan_sum(self, port: int, start: int, end: int) -> tuple[int, int]:
        r = self._conn.execute(
            "SELECT SUM(down), SUM(up) FROM wan_hours WHERE port=? AND ts >= ? AND ts < ?", (port, start, end)
        ).fetchone()
        return (r[0] or 0, r[1] or 0)

    def wan_earliest(self, port: int) -> int | None:
        r = self._conn.execute("SELECT MIN(ts) FROM wan_hours WHERE port=?", (port,)).fetchone()
        return r[0] if r and r[0] is not None else None
