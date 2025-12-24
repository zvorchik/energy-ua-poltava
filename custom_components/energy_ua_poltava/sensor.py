from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Any, Dict, Optional

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from bs4 import BeautifulSoup

from .const import (
    DOMAIN,
    DEFAULT_BASE_URL,
    DEFAULT_GROUP,
    DEFAULT_SCAN_SECONDS,
    SENSOR_KEY_TEXT,
    SENSOR_KEY_TIME,
    CONF_GROUP,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_GROUP, default=DEFAULT_GROUP): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=timedelta(seconds=DEFAULT_SCAN_SECONDS)): cv.time_period,
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Energy UA Poltava sensors via YAML (HA 2022.5.5)."""
    group = config.get(CONF_GROUP, DEFAULT_GROUP)
    scan_interval = config.get(CONF_SCAN_INTERVAL, timedelta(seconds=DEFAULT_SCAN_SECONDS))
    url = f"{DEFAULT_BASE_URL}{group}"

    session = async_get_clientsession(hass)

    coordinator = EnergyUATimerCoordinator(hass, session, url, scan_interval)
    await coordinator.async_refresh()

    entities = [
        EnergyUATextSensor(coordinator, url),
        EnergyUATimeSensor(coordinator, url),
]
    async_add_entities(entities)

class EnergyUATimerCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Coordinator that fetches and parses energy-ua.info page."""

    def __init__(self, hass, session, url: str, scan_interval: timedelta):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=scan_interval)
        self._session = session
        self._url = url

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            async with self._session.get(self._url, timeout=20) as resp:
                html = await resp.text()
        except Exception as err:
            raise UpdateFailed(f"Energy UA fetch error: {err}") from err

        data: Dict[str, Any] = {SENSOR_KEY_TEXT: None, SENSOR_KEY_TIME: None}

        soup = BeautifulSoup(html, 'html.parser')

        text_el = soup.find(id=SENSOR_KEY_TEXT)
        if text_el:
            data[SENSOR_KEY_TEXT] = text_el.get_text(strip=True)

        time_el = soup.find(id=SENSOR_KEY_TIME)
        raw_time = time_el.get_text(strip=True) if time_el else None
        seconds: Optional[int] = None

        if raw_time and raw_time.isdigit():
            seconds = int(raw_time)
        else:
            pattern = re.compile(r"(?:(\d+)\s*(?:год|г))?.*?(?:(\d+)\s*(?:хв))?.*?(?:(\d+)\s*(?:сек|с))?", flags=re.IGNORECASE | re.DOTALL)
            m = pattern.search(raw_time or '')
            if m:
                h = int(m.group(1) or 0)
                mn = int(m.group(2) or 0)
                s = int(m.group(3) or 0)
                seconds = h * 3600 + mn * 60 + s

        data[SENSOR_KEY_TIME] = seconds

        return data

class BaseEnergyUASensor(CoordinatorEntity[EnergyUATimerCoordinator], SensorEntity):
    def __init__(self, coordinator: EnergyUATimerCoordinator, url: str, name_suffix: str, icon: str):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{name_suffix}"
        self._attr_name = f"Energy UA {name_suffix}"
        self._attr_icon = icon
        self._url = url
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, 'energy-ua')},
            name='Energy UA',
            configuration_url=url,
            manufacturer='Energy UA (community)',
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data is not None

class EnergyUATextSensor(BaseEnergyUASensor):
    def __init__(self, coordinator: EnergyUATimerCoordinator, url: str):
        super().__init__(coordinator, url, 'ch_timer_text', 'mdi:format-text')

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get(SENSOR_KEY_TEXT)

class EnergyUATimeSensor(BaseEnergyUASensor):
    _attr_native_unit_of_measurement = 's'

    def __init__(self, coordinator: EnergyUATimerCoordinator, url: str):
        super().__init__(coordinator, url, 'ch_timer_time', 'mdi:timer-outline')

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get(SENSOR_KEY_TIME)
