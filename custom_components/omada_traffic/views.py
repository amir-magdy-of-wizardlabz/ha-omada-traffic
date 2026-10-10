"""HTTP API used by the Traffic panel. All endpoints require HA auth."""
from __future__ import annotations

import logging
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from . import queries
from .const import DOMAIN, HOME_BUCKET

_LOGGER = logging.getLogger(__name__)


def _runtime(request: web.Request) -> dict[str, Any]:
    return request.app["hass"].data[DOMAIN]


async def _call(request: web.Request, fn):
    """Run a query function on the DB thread with fresh settings and client index.

    fn(store, samples, idx, settings, start_hour) runs off the event loop, so the
    settings files may be re-read there without blocking HA.
    """
    rt = _runtime(request)
    collector = rt["collector"]
    loader = rt["settings"]
    raw_start = request.query.get("day_start")

    def work():
        settings = loader.get()
        start_hour = int(raw_start) if raw_start in ("0", "6") else settings.day_start_hour
        clients = collector.store.clients()
        idx = queries.ClientIndex(clients, settings)
        return fn(collector.store, collector.samples, idx, settings, start_hour)

    return await collector.run_db(work)


class MetaView(HomeAssistantView):
    url = f"/api/{DOMAIN}/meta"
    name = f"api:{DOMAIN}:meta"

    async def get(self, request: web.Request) -> web.Response:
        rt = _runtime(request)
        collector = rt["collector"]
        info = {
            "last_poll": collector.last_poll_ts,
            "last_error": collector.last_error,
            "poll_seconds": collector.poll_seconds,
        }
        data = await _call(request, lambda store, samples, idx, settings, sh: queries.meta(idx, settings, info))
        return self.json(data)


class SummaryView(HomeAssistantView):
    url = f"/api/{DOMAIN}/summary"
    name = f"api:{DOMAIN}:summary"

    async def get(self, request: web.Request) -> web.Response:
        collector = _runtime(request)["collector"]
        data = await _call(
            request,
            lambda store, samples, idx, s, sh: queries.summary(store, samples, idx, s, sh, collector.last_poll_ts),
        )
        return self.json(data)


class BandwidthView(HomeAssistantView):
    url = f"/api/{DOMAIN}/bandwidth"
    name = f"api:{DOMAIN}:bandwidth"

    async def get(self, request: web.Request) -> web.Response:
        window = request.query.get("window", "1h")
        flt = request.query.get("filter") or None
        end = request.query.get("end")
        end_ts = int(float(end)) if end else None
        data = await _call(
            request,
            lambda store, samples, idx, s, sh: queries.bandwidth(store, samples, idx, window, flt, end_ts),
        )
        return self.json(data)


class UsageView(HomeAssistantView):
    url = f"/api/{DOMAIN}/usage"
    name = f"api:{DOMAIN}:usage"

    async def get(self, request: web.Request) -> web.Response:
        window = request.query.get("window", "24h")
        flt = request.query.get("filter") or None
        data = await _call(
            request,
            lambda store, samples, idx, s, sh: queries.usage(store, idx, s, window, flt, sh),
        )
        return self.json(data)


class TableView(HomeAssistantView):
    url = f"/api/{DOMAIN}/table"
    name = f"api:{DOMAIN}:table"

    async def get(self, request: web.Request) -> web.Response:
        by = request.query.get("by", "device")
        window = request.query.get("window", "24h")
        data = await _call(
            request,
            lambda store, samples, idx, s, sh: queries.table(store, samples, idx, s, by, window, sh),
        )
        return self.json(data)


class AssignView(HomeAssistantView):
    """POST {mac, owner?, name?, type?}: update a device's owner/name/type. Admins only."""

    url = f"/api/{DOMAIN}/assign"
    name = f"api:{DOMAIN}:assign"

    async def post(self, request: web.Request) -> web.Response:
        if not request["hass_user"].is_admin:
            return self.json_message("admin only", 403)
        body = await request.json()
        mac = str(body.get("mac") or "").strip()
        if not mac:
            return self.json_message("mac required", 400)
        rt = _runtime(request)
        loader = rt["settings"]
        owner = body.get("owner")
        if owner is not None and owner not in loader.get().people and owner not in ("", HOME_BUCKET):
            return self.json_message("unknown person", 400)
        entry = loader.assign(mac, owner, body.get("name"), body.get("type"))
        return self.json({"mac": mac.upper().replace(":", "-"), "entry": entry})


class PersonView(HomeAssistantView):
    """POST {name}: add a person. Admins only."""

    url = f"/api/{DOMAIN}/person"
    name = f"api:{DOMAIN}:person"

    async def post(self, request: web.Request) -> web.Response:
        if not request["hass_user"].is_admin:
            return self.json_message("admin only", 403)
        body = await request.json()
        name = str(body.get("name") or "").strip()
        if not name or len(name) > 40:
            return self.json_message("name required", 400)
        rt = _runtime(request)
        people = rt["settings"].add_person(name)
        return self.json({"people": people})


VIEWS = (MetaView, SummaryView, BandwidthView, UsageView, TableView, AssignView, PersonView)
