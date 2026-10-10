"""Omada Traffic: per-device internet usage dashboard fed by an Omada controller.

Set up from Settings > Devices & services > Add integration. The controller
address and login are kept in the config entry; people, plans and device
ownership are kept in Home Assistant's storage. Nothing private is in this code.
"""
from __future__ import annotations

import logging
import os

import voluptuous as vol
from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import ConfigType

from .collector import Collector
from .const import (
    CONF_OMADAC_ID,
    CONF_SITE_ID,
    CONF_SITE_NAME,
    DATA_DIRNAME,
    DB_FILENAME,
    DEFAULT_ENV_FILE,
    DEFAULT_POLL_SECONDS,
    DOMAIN,
    PANEL_URL_PATH,
    SIGNAL_UPDATED,
    STATIC_URL_PATH,
)
from .notify import DeviceNotifier
from .omada_api import OmadaClient
from .settings import SettingsLoader
from .views import VIEWS

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]
PANEL_VERSION = "0.5.0"
_HTTP_READY = f"{DOMAIN}_http_ready"

# Older installs were configured in configuration.yaml with a credentials file.
# That is still read once and turned into a config entry.
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional("env_file", default=DEFAULT_ENV_FILE): cv.string,
                vol.Optional("poll_seconds", default=DEFAULT_POLL_SECONDS): vol.All(int, vol.Range(min=10, max=600)),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def _read_env(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    conf = config.get(DOMAIN)
    if conf is None or hass.config_entries.async_entries(DOMAIN):
        return True
    try:
        env = await hass.async_add_executor_job(_read_env, conf["env_file"])
    except OSError as err:
        _LOGGER.error("Cannot read Omada credentials file %s: %s", conf["env_file"], err)
        return True
    missing = [k for k in ("OMADA_URL", "OMADA_OMADAC_ID", "OMADA_SITE_ID", "OMADA_USERNAME", "OMADA_PASSWORD") if not env.get(k)]
    if missing:
        _LOGGER.error("Omada credentials file is missing: %s", ", ".join(missing))
        return True
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={
                CONF_URL: env["OMADA_URL"],
                CONF_USERNAME: env["OMADA_USERNAME"],
                CONF_PASSWORD: env["OMADA_PASSWORD"],
                CONF_VERIFY_SSL: env.get("OMADA_VERIFY_SSL", "false").lower() == "true",
                CONF_OMADAC_ID: env["OMADA_OMADAC_ID"],
                CONF_SITE_ID: env["OMADA_SITE_ID"],
                CONF_SITE_NAME: env.get("OMADA_SITE_NAME") or "",
            },
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data_dir = hass.config.path(DATA_DIRNAME)
    await hass.async_add_executor_job(lambda: os.makedirs(data_dir, exist_ok=True))
    loader = SettingsLoader(hass)
    await loader.async_load(data_dir)

    api = OmadaClient(
        entry.data[CONF_URL],
        entry.data[CONF_OMADAC_ID],
        entry.data[CONF_SITE_ID],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, False),
    )
    collector = Collector(hass, api, os.path.join(data_dir, DB_FILENAME), DEFAULT_POLL_SECONDS)
    hass.data[DOMAIN] = {"collector": collector, "settings": loader, "entry_id": entry.entry_id}
    await collector.async_start()

    # HTTP API and static files can only be registered once per Home Assistant run.
    if not hass.data.get(_HTTP_READY):
        for view in VIEWS:
            hass.http.register_view(view())
        www = os.path.join(os.path.dirname(__file__), "www")
        await hass.http.async_register_static_paths([StaticPathConfig(STATIC_URL_PATH, www, False)])
        hass.data[_HTTP_READY] = True
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="omada-traffic-panel",
        frontend_url_path=PANEL_URL_PATH,
        module_url=f"{STATIC_URL_PATH}/panel.js?v={PANEL_VERSION}",
        sidebar_title="Traffic",
        sidebar_icon="mdi:chart-areaspline",
        require_admin=False,
        config={},
    )

    notifier = DeviceNotifier(hass, collector, loader)

    @callback
    def _on_poll() -> None:
        hass.async_create_task(notifier.async_check())

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_UPDATED, _on_poll))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("Omada Traffic started (poll every %ss, data in %s)", DEFAULT_POLL_SECONDS, data_dir)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    frontend.async_remove_panel(hass, PANEL_URL_PATH)
    rt = hass.data.pop(DOMAIN, None)
    if rt:
        await rt["collector"].async_stop()
    return True
