"""Read-only client for the Omada controller's web API.

Only two calls are ever made: the login (authentication) and GET requests
that read data. Nothing here changes controller state.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class OmadaError(Exception):
    """Raised when the controller returns an error."""


class OmadaAuthError(OmadaError):
    """Raised when the controller rejects the username or password."""


async def discover(url: str, username: str, password: str, verify_ssl: bool) -> tuple[str, list[dict[str, str]]]:
    """Return the controller's id and its sites [{"id", "name"}]. Reads only."""
    url = url.rstrip("/")
    connector = aiohttp.TCPConnector(ssl=verify_ssl if verify_ssl else False)
    async with aiohttp.ClientSession(
        connector=connector, cookie_jar=aiohttp.CookieJar(unsafe=True), timeout=aiohttp.ClientTimeout(total=20)
    ) as session:
        try:
            async with session.get(f"{url}/api/info") as resp:
                info = await resp.json(content_type=None)
            cid = (info.get("result") or {}).get("omadacId")
            if not cid:
                raise OmadaError("not an Omada controller")
            async with session.post(f"{url}/{cid}/api/v2/login", json={"username": username, "password": password}) as resp:
                login = await resp.json(content_type=None)
            if login.get("errorCode") != 0:
                raise OmadaAuthError(str(login.get("msg")))
            headers = {"Csrf-Token": login["result"]["token"]}
            async with session.get(
                f"{url}/{cid}/api/v2/sites", params={"currentPage": 1, "currentPageSize": 100}, headers=headers
            ) as resp:
                sites = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise OmadaError(f"cannot reach the controller: {err}") from err
    data = (sites.get("result") or {}).get("data") or []
    return cid, [{"id": s["id"], "name": s.get("name") or s["id"]} for s in data if s.get("id")]


class OmadaClient:
    """Minimal async client for the private web API, read-only."""

    def __init__(
        self,
        url: str,
        omadac_id: str,
        site_id: str,
        username: str,
        password: str,
        verify_ssl: bool = False,
    ) -> None:
        self._base = url.rstrip("/")
        self._cid = omadac_id
        self._site = site_id
        self._user = username
        self._pass = password
        self._verify = verify_ssl
        self._session: aiohttp.ClientSession | None = None
        self._token: str | None = None
        self._login_lock = asyncio.Lock()
        self._last_login = 0.0

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=self._verify if self._verify else False)
            # The controller is addressed by IP; aiohttp drops cookies for IP
            # hosts unless the jar is marked unsafe.
            self._session = aiohttp.ClientSession(
                connector=connector,
                cookie_jar=aiohttp.CookieJar(unsafe=True),
                timeout=aiohttp.ClientTimeout(total=20),
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    async def login(self) -> None:
        """Authenticate and keep the CSRF token."""
        async with self._login_lock:
            # Avoid login storms when several callers hit an expired session.
            if time.monotonic() - self._last_login < 5 and self._token:
                return
            session = await self._ensure_session()
            session.cookie_jar.clear()
            async with session.post(
                f"{self._base}/{self._cid}/api/v2/login",
                json={"username": self._user, "password": self._pass},
            ) as resp:
                data = await resp.json(content_type=None)
            if data.get("errorCode") != 0:
                raise OmadaError(f"login failed: {data.get('msg')} ({data.get('errorCode')})")
            self._token = data["result"]["token"]
            self._last_login = time.monotonic()
            _LOGGER.debug("Logged in to Omada controller")

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET a site-relative API path, re-logging in once if needed."""
        for attempt in (1, 2):
            if not self._token:
                await self.login()
            session = await self._ensure_session()
            url = f"{self._base}/{self._cid}/api/v2/{path}"
            headers = {"Csrf-Token": self._token or ""}
            try:
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.content_type != "application/json":
                        raise OmadaError(f"non-JSON response ({resp.status}) for {path}")
                    data = await resp.json()
            except aiohttp.ClientError as err:
                raise OmadaError(f"request failed: {err}") from err
            code = data.get("errorCode", -1)
            if code == 0:
                return data.get("result")
            # Session expired or token invalid: log in again once.
            if attempt == 1 and code in (-1200, -1201, -1202, -1203, -1004, -1600, -1):
                _LOGGER.debug("Omada error %s on %s, re-login", code, path)
                self._token = None
                continue
            raise OmadaError(f"{path}: {data.get('msg')} ({code})")
        raise OmadaError("unreachable")

    async def get_active_clients(self) -> list[dict[str, Any]]:
        """Return every online client with live rates and running totals."""
        result = await self._get(
            f"sites/{self._site}/clients",
            {"currentPage": 1, "currentPageSize": 1000, "filters.active": "true"},
        )
        return list(result.get("data", [])) if isinstance(result, dict) else []

    async def get_devices(self) -> list[dict[str, Any]]:
        result = await self._get(f"sites/{self._site}/devices")
        return list(result) if isinstance(result, list) else list(result.get("data", []))

    async def get_wan_ports(self) -> list[dict[str, Any]]:
        """Return the gateway's WAN ports with their running byte counters."""
        if not getattr(self, "_gateway_mac", None):
            gw = next((d for d in await self.get_devices() if d.get("type") == "gateway"), None)
            if not gw:
                return []
            self._gateway_mac = gw["mac"]
        result = await self._get(f"sites/{self._site}/gateways/{self._gateway_mac}")
        ports = (result or {}).get("portStats") or []
        # mode 0 = WAN. Keep only ports that are acting as WAN.
        return [p for p in ports if p.get("mode") == 0]
