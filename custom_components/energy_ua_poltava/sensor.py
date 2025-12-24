
from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import CONF_SCAN_INTERVAL

from bs4 import BeautifulSoup

from .const import (
    DOMAIN,
    DEFAULT_BASE_URL,
    DEFAULT_SCAN_SECONDS,
    SENSOR_KEY_TEXT,
    SENSOR_KEY_TIME,
    CONF_GROUP,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    group = entry.data.get(CONF_GROUP)
    scan_seconds = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_SECONDS)
    url = f"{DEFAULT_BASE_URL}{group}"
    session = async_get_clientsession(hass)
    coordinator = EnergyUATimerCoordinator(hass, session, url, timedelta(seconds=scan_seconds))
    await coordinator.async_refresh()
    async_add_entities([
        EnergyUATextSensor(coordinator, url),
        EnergyUATimeSensor(coordinator, url),
        EnergyUACombinedSensor(coordinator, url, group),
    ])

class EnergyUATimerCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, session, url: str, scan_interval: timedelta):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=scan_interval)
        self._session = session
        self._url = url

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            async with self._session.get(self._url, timeout=20, headers={'User-Agent': USER_AGENT}) as resp:
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

        # Фолбек: інколи текст містить час без окремого елемента
        if seconds is None and data[SENSOR_KEY_TEXT]:
            m = re.search(r"(\d+)\s*год.*?(\d+)\s*хв.*?(\d+)\s*сек", data[SENSOR_KEY_TEXT], flags=re.IGNORECASE)
            if m:
                seconds = int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3))

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

class EnergyUACombinedSensor(BaseEnergyUASensor):
    _attr_native_unit_of_measurement = 's'
    def __init__(self, coordinator: EnergyUATimerCoordinator, url: str, group: str):
        super().__init__(coordinator, url, 'ch_timer', 'mdi:timer')
        self._group = group
    @property
    def native_value(self):
        return (self.coordinator.data or {}).get(SENSOR_KEY_TIME)
    @property
    def extra_state_attributes(self):
        d = self.coordinator.data or {}
        return {
            'text': d.get(SENSOR_KEY_TEXT),
            'group': self._group,
            'source': self._url,
        }
