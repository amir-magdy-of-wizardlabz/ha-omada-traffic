"""A few whole-house sensors so the data is usable elsewhere in Home Assistant."""
from __future__ import annotations

import time

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfDataRate, UnitOfInformation
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import queries
from .const import DOMAIN, SIGNAL_UPDATED


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    rt = hass.data[DOMAIN]
    async_add_entities(
        [
            RateSensor(rt, "download", 0),
            RateSensor(rt, "upload", 1),
            TodaySensor(rt),
            PlanUsedSensor(rt),
        ]
    )


class _Base(SensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, rt) -> None:
        self._rt = rt
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, rt["entry_id"])}, name="Omada Traffic", entry_type=DeviceEntryType.SERVICE
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_UPDATED, self._updated))

    @callback
    def _updated(self) -> None:
        self.async_schedule_update_ha_state(True)


class RateSensor(_Base):
    _attr_device_class = SensorDeviceClass.DATA_RATE
    _attr_native_unit_of_measurement = UnitOfDataRate.MEGABITS_PER_SECOND
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(self, rt, direction: str, index: int) -> None:
        super().__init__(rt)
        self._index = index
        self._attr_name = f"{direction.capitalize()} rate"
        self._attr_unique_id = f"{DOMAIN}_house_{direction}_rate"
        self._attr_icon = "mdi:download-network" if index == 0 else "mdi:upload-network"

    async def async_update(self) -> None:
        dq = self._rt["collector"].samples.get("house")
        self._attr_native_value = round(dq[-1][1 + self._index] * 8 / 1e6, 3) if dq else 0


class TodaySensor(_Base):
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_native_unit_of_measurement = UnitOfInformation.GIGABYTES
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 2
    _attr_name = "Used today"
    _attr_unique_id = f"{DOMAIN}_house_today"
    _attr_icon = "mdi:calendar-today"

    async def async_update(self) -> None:
        self._attr_native_value = await _summary_value(self._rt, lambda s: (s["today"]["down"] + s["today"]["up"]) / 1e9)
        self._attr_last_reset = None


class PlanUsedSensor(_Base):
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_native_unit_of_measurement = UnitOfInformation.GIGABYTES
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 1
    _attr_name = "Used this plan period"
    _attr_unique_id = f"{DOMAIN}_house_plan_used"
    _attr_icon = "mdi:gauge"

    async def async_update(self) -> None:
        self._attr_native_value = await _summary_value(self._rt, lambda s: s["plan"]["used"] / 1e9)


async def _summary_value(rt, pick):
    collector = rt["collector"]
    loader = rt["settings"]
    if not collector.store:
        return None

    def work():
        settings = loader.get()
        idx = queries.ClientIndex(collector.store.clients(), settings)
        return pick(queries.summary(collector.store, collector.samples, idx, settings, settings.day_start_hour, collector.last_poll_ts))

    return round(await collector.run_db(work), 3)
