"""Home Assistant notifications asking what an unidentified device is."""
from __future__ import annotations

import logging
import time
from datetime import datetime

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant

from . import queries
from .const import DOMAIN, PANEL_URL_PATH
from .vendors import PRIVATE

_LOGGER = logging.getLogger(__name__)

SETTLE_SECONDS = 300  # give a new address time to announce its name or be merged


def _nid(mac: str) -> str:
    return f"{DOMAIN}_{mac.replace('-', '').lower()}"


class DeviceNotifier:
    """Raises one notification per unidentified device and clears it once identified."""

    def __init__(self, hass: HomeAssistant, collector, loader) -> None:
        self.hass = hass
        self.collector = collector
        self.loader = loader
        # Kept in memory only: Home Assistant forgets its notifications on restart,
        # so after one every still-unidentified device is asked about again.
        self._notified: set[str] = set()

    def _scan(self) -> tuple[list[dict], set[str]]:
        """DB thread: devices to ask about now, and every device still unidentified."""
        store = self.collector.store
        settings = self.loader.get()
        idx = queries.ClientIndex(store.clients(), settings)
        now = time.time()
        pending = {m for m, c in idx.by_mac.items() if c["needs_id"]}
        fresh = [
            {**idx.by_mac[m], "tz": settings.tz}
            for m in pending - self._notified
            if (idx.by_mac[m].get("first_seen") or 0) <= now - SETTLE_SECONDS
        ]
        return fresh, pending

    async def async_check(self) -> None:
        if not self.collector.store:
            return
        try:
            fresh, pending = await self.collector.run_db(self._scan)
        except Exception:  # noqa: BLE001 - never let a notification break polling
            _LOGGER.exception("Device notification check failed")
            return
        done = self._notified - pending
        for c in fresh:
            mac = c["mac"]
            seen = datetime.fromtimestamp(c.get("first_seen") or time.time(), c["tz"]).strftime("%a %d %b, %H:%M")
            facts = [f"Made by {c['vendor']}" if c.get("vendor") and c["vendor"] != PRIVATE else "uses a private Wi-Fi address" if c.get("vendor") else None,
                     f"calls itself {c['mdns_name']}" if c.get("mdns_name") else None,
                     f"connected through {c['via']}" if c.get("via") else None,
                     f"IP {c['ip']}" if c.get("ip") else None, f"address {mac}"]
            persistent_notification.async_create(
                self.hass,
                f"**{c['label']}** was first seen {seen}.\n\n"
                + " · ".join(f for f in facts if f)
                + f"\n\n[Name it and choose whose it is](/{PANEL_URL_PATH}?device={mac})",
                title="What device is this?",
                notification_id=_nid(mac),
            )
            self._notified.add(mac)
        for mac in done:
            persistent_notification.async_dismiss(self.hass, _nid(mac))
            self._notified.discard(mac)
