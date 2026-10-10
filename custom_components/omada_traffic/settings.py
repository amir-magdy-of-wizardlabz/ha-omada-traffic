"""Household settings: people, internet plans, device ownership and types.

Everything here is private to the installation and lives in Home Assistant's
own storage (.storage/omada_traffic), never in the integration's files.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store as HAStore

from .const import DOMAIN, HOME_BUCKET, TYPE_BY_CATEGORY, TYPE_BY_DEVICE_TYPE

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1


@dataclass
class Plan:
    name: str = "Internet plan"
    quota_gb: float = 0
    renewal_day: int = 1
    wan: str | None = None
    baseline_date: str | None = None
    baseline_gb: float = 0


@dataclass
class Settings:
    tz: ZoneInfo
    day_start_hour: int = 0
    people: list[str] = field(default_factory=list)
    plan: Plan = field(default_factory=Plan)
    plans: list[Plan] = field(default_factory=list)
    clients: dict[str, dict] = field(default_factory=dict)

    def owner(self, mac: str) -> str:
        entry = self.clients.get(mac) or {}
        owner = entry.get("owner")
        return owner if owner in self.people else HOME_BUCKET

    def name(self, mac: str, omada_name: str | None, host_name: str | None) -> str:
        entry = self.clients.get(mac) or {}
        return entry.get("name") or omada_name or host_name or mac

    def type_of(self, mac: str, category: str | None, device_type: str | None) -> str:
        entry = self.clients.get(mac) or {}
        if entry.get("type"):
            return entry["type"]
        if device_type and device_type in TYPE_BY_DEVICE_TYPE:
            return TYPE_BY_DEVICE_TYPE[device_type]
        if category and category in TYPE_BY_CATEGORY:
            return TYPE_BY_CATEGORY[category]
        return "Other"

    # ---------------------------------------------------------------- time
    def day_start(self, ts: int, start_hour: int | None = None) -> int:
        """Epoch of the start of the local 'day' that contains ts."""
        h = self.day_start_hour if start_hour is None else start_hour
        local = datetime.fromtimestamp(ts, self.tz)
        start = local.replace(hour=h, minute=0, second=0, microsecond=0)
        if local < start:
            start -= timedelta(days=1)
        return int(start.timestamp())

    def cycle_bounds(self, ts: int, plan: Plan | None = None) -> tuple[int, int]:
        """(start, end) epochs of the plan cycle containing ts."""
        local = datetime.fromtimestamp(ts, self.tz)
        day = max(1, min(28, int((plan or self.plan).renewal_day or 1)))
        start = local.replace(day=day, hour=0, minute=0, second=0, microsecond=0)
        if local < start:
            start = (start.replace(day=1) - timedelta(days=1)).replace(day=day)
        nxt = (start.replace(day=28) + timedelta(days=4)).replace(day=day)
        return int(start.timestamp()), int(nxt.timestamp())


def _empty() -> dict:
    return {"day_start_hour": 0, "people": [], "plans": [], "clients": {}}


def _read_legacy(data_dir: str) -> dict | None:
    """Read the settings.yaml / clients.yaml used before settings moved into HA storage."""
    import yaml  # noqa: PLC0415 - only needed for this one-time import

    out = _empty()
    found = False
    try:
        with open(os.path.join(data_dir, "settings.yaml"), encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        found = True
        out["day_start_hour"] = int(raw.get("day_start_hour") or 0)
        out["people"] = [str(x) for x in (raw.get("people") or [])]
        for pr in raw.get("plans") or ([raw["plan"]] if raw.get("plan") else []):
            if isinstance(pr, dict):
                base = pr.get("baseline") or {}
                out["plans"].append({
                    "name": str(pr.get("name") or "Internet plan"),
                    "wan": str(pr["wan"]) if pr.get("wan") else None,
                    "quota_gb": float(pr.get("quota_gb") or 0),
                    "renewal_day": int(pr.get("renewal_day") or 1),
                    "baseline_date": str(base["date"]) if base.get("date") else None,
                    "baseline_gb": float(base.get("used_gb") or 0),
                })
    except (OSError, ValueError, yaml.YAMLError):
        pass
    try:
        with open(os.path.join(data_dir, "clients.yaml"), encoding="utf-8") as f:
            clients = yaml.safe_load(f) or {}
        found = True
        for mac, entry in clients.items():
            if isinstance(entry, dict):
                out["clients"][str(mac).upper().replace(":", "-")] = dict(entry)
    except (OSError, ValueError, yaml.YAMLError):
        pass
    return out if found else None


class SettingsLoader:
    """Holds the settings in memory and persists them through Home Assistant's storage.

    Writers run on the event loop. get() only returns a ready-made snapshot, so
    it is safe to call from the database thread.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store: HAStore = HAStore(hass, STORAGE_VERSION, DOMAIN)
        self._data: dict = _empty()
        self._cached: Settings = self._build()

    async def async_load(self, legacy_dir: str) -> None:
        data = await self._store.async_load()
        if data is None:
            data = await self.hass.async_add_executor_job(_read_legacy, legacy_dir)
            if data is not None:
                _LOGGER.info("Imported settings.yaml and clients.yaml from %s into Home Assistant storage", legacy_dir)
                await self._store.async_save(data)
        self._data = {**_empty(), **(data or {})}
        self._cached = self._build()

    def get(self) -> Settings:
        return self._cached

    def _build(self) -> Settings:
        try:
            tz = ZoneInfo(self.hass.config.time_zone)
        except Exception:  # noqa: BLE001
            tz = ZoneInfo("UTC")
        plans = [
            Plan(
                name=str(p.get("name") or "Internet plan"),
                quota_gb=float(p.get("quota_gb") or 0),
                renewal_day=int(p.get("renewal_day") or 1),
                wan=p.get("wan") or None,
                baseline_date=p.get("baseline_date") or None,
                baseline_gb=float(p.get("baseline_gb") or 0),
            )
            for p in self._data["plans"]
        ] or [Plan()]
        return Settings(
            tz=tz,
            day_start_hour=int(self._data["day_start_hour"] or 0),
            people=list(self._data["people"]),
            plan=plans[0],
            plans=plans,
            clients={m: dict(e) for m, e in self._data["clients"].items()},
        )

    @callback
    def _changed(self) -> None:
        self._cached = self._build()
        self._store.async_delay_save(lambda: self._data, 1)

    # ---------------------------------------------------------------- writers
    @callback
    def assign(self, mac: str, owner: str | None = None, name: str | None = None, type_: str | None = None) -> dict:
        """Update one device's entry (None leaves a field alone, "" clears it)."""
        mac = mac.upper().replace(":", "-")
        entry = dict(self._data["clients"].get(mac) or {})
        for key, val in (("owner", owner), ("name", name), ("type", type_)):
            if val is None:
                continue
            if val == "" or (key == "owner" and val == HOME_BUCKET):
                entry.pop(key, None)
            else:
                entry[key] = val
        # Any save from the page means someone has looked at this device.
        entry["known"] = True
        self._data["clients"][mac] = entry
        self._changed()
        return entry

    @callback
    def add_person(self, name: str) -> list[str]:
        name = name.strip()
        if name and name not in self._data["people"] and name != HOME_BUCKET:
            self._data["people"].append(name)
            self._changed()
        return list(self._data["people"])

    @callback
    def remove_person(self, name: str) -> None:
        if name in self._data["people"]:
            self._data["people"].remove(name)
            self._changed()

    @property
    def raw_plans(self) -> list[dict]:
        return [dict(p) for p in self._data["plans"]]

    @callback
    def set_plans(self, plans: list[dict]) -> None:
        self._data["plans"] = plans
        self._changed()

    @callback
    def set_day_start(self, hour: int) -> None:
        self._data["day_start_hour"] = int(hour)
        self._changed()
