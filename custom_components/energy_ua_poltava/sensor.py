
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
    SENSOR_KEY_STATUS,
    CONF_GROUP,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

STATUS_ON_PHRASES = [
    "Наступне відключення заплановане через",
]
STATUS_OFF_PHRASES = [
    "До увімкнення залишилось",
    "До увімкнення залишилось почекати",
]

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
        EnergyUAStatusSensor(coordinator, url),
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

        data: Dict[str, Any] = {SENSOR_KEY_TEXT: None, SENSOR_KEY_TIME: None, SENSOR_KEY_STATUS: None}
        soup = BeautifulSoup(html, 'html.parser')

        # --- TEXT & STATUS ---
        text_div = soup.find('div', class_='ch_timer_text')
        text_value: Optional[str] = None
        if text_div:
            text_value = text_div.get_text(separator=' ', strip=True)
            data[SENSOR_KEY_TEXT] = text_value

        # Determine status based on phrases
        status: Optional[str] = None
        detection_text = text_value or soup.get_text(separator=' ', strip=True)
        if any(p in detection_text for p in STATUS_ON_PHRASES):
            status = 'ON'
        elif any(p in detection_text for p in STATUS_OFF_PHRASES):
            status = 'OFF'
        # Secondary hints
        elif 'Електроенергія присутня' in detection_text:
            status = 'ON'
        elif 'Електроенергія відсутня' in detection_text:
            status = 'OFF'
        data[SENSOR_KEY_STATUS] = status

        # --- TIME (from ids: hours, minutes, seconds inside .ch_timer_time) ---
        seconds: Optional[int] = None
        time_div = soup.find('div', class_='ch_timer_time')
        if time_div:
            try:
                h_el = time_div.find(id='hours')
                m_el = time_div.find(id='minutes')
                s_el = time_div.find(id='seconds')
                h = int((h_el.get_text(strip=True) if h_el else '0') or 0)
                m = int((m_el.get_text(strip=True) if m_el else '0') or 0)
                s = int((s_el.get_text(strip=True) if s_el else '0') or 0)
                seconds = h * 3600 + m * 60 + s
            except Exception as parse_err:
                _LOGGER.debug("Energy UA: time parse error: %s", parse_err)
                seconds = None

        # Fallback: parse any H:M:S pattern in page text if needed
        if seconds is None:
            page_text = detection_text
            pattern = re.compile(r"(?:(\d+)\s*(?:год|г))?\s*(?:(\d+)\s*хв)?\s*(?:(\d+)\s*(?:сек|с))?", re.IGNORECASE)
            m = pattern.search(page_text)
            if m and (m.group(1) or m.group(2) or m.group(3)):
                h = int(m.group(1) or 0)
                mn = int(m.group(2) or 0)
                s = int(m.group(3) or 0)
                seconds = h * 3600 + mn * 60 + s

        data[SENSOR_KEY_TIME] = seconds

        # Debug aid if not found
        if data[SENSOR_KEY_TEXT] is None and data[SENSOR_KEY_TIME] is None:
            _LOGGER.debug("Energy UA: expected content not found. HTML head: %s", html[:1000])

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

class EnergyUAStatusSensor(BaseEnergyUASensor):
    def __init__(self, coordinator: EnergyUATimerCoordinator, url: str):
        super().__init__(coordinator, url, 'ch_status', 'mdi:power')
    @property
    def native_value(self):
        return (self.coordinator.data or {}).get(SENSOR_KEY_STATUS)

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
            'status': d.get(SENSOR_KEY_STATUS),
            'group': self._group,
            'source': self._url,
        }
