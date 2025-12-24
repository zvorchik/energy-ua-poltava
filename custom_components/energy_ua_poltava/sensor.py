
from __future__ import annotations

import logging
import re
from datetime import datetime, time as dtime, timedelta
from typing import Any, Dict, Optional, List, Tuple

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None

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

# Regex: intervals like "З 12:30 до 16:00, тривалість ..."
OFF_INTERVAL_RE = re.compile(r"З\s*(\d{1,2}:\d{2})\s*до\s*(\d{1,2}:\d{2})", re.IGNORECASE)
HMS_RE = re.compile(r"(?:(\d+)\s*(?:год|г|год\.|г\.|h))?\s*(?:(\d+)\s*(?:хв|хв\.|m))?\s*(?:(\d+)\s*(?:сек|с|сек\.|s))?", re.IGNORECASE)

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
        self._tz = None
        try:
            if ZoneInfo and hass.config.time_zone:
                self._tz = ZoneInfo(hass.config.time_zone)
        except Exception:
            self._tz = None

    def _now(self) -> datetime:
        if self._tz:
            return datetime.now(self._tz)
        return datetime.now()

    def _combine(self, t: dtime) -> datetime:
        n = self._now()
        return datetime(n.year, n.month, n.day, t.hour, t.minute, tzinfo=self._tz)

    @staticmethod
    def _parse_time_str(ts: str) -> dtime:
        h, m = ts.split(":")
        return dtime(int(h), int(m))

    @staticmethod
    def _hms_to_seconds(m: re.Match) -> int:
        h = int(m.group(1) or 0)
        mn = int(m.group(2) or 0)
        s = int(m.group(3) or 0)
        return h * 3600 + mn * 60 + s

    def _parse_off_intervals(self, page_text: str) -> List[Tuple[datetime, datetime]]:
        intervals: List[Tuple[datetime, datetime]] = []
        for m in OFF_INTERVAL_RE.finditer(page_text):
            start_t = self._parse_time_str(m.group(1))
            end_t = self._parse_time_str(m.group(2))
            start_dt = self._combine(start_t)
            end_dt = self._combine(end_t)
            # Cross-midnight safety
            if end_dt <= start_dt:
                end_dt = end_dt + timedelta(days=1)
            intervals.append((start_dt, end_dt))
        return sorted(intervals, key=lambda x: x[0])

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            async with self._session.get(self._url, timeout=20, headers={'User-Agent': USER_AGENT}) as resp:
                html = await resp.text()
        except Exception as err:
            raise UpdateFailed(f"Energy UA fetch error: {err}") from err

        data: Dict[str, Any] = {SENSOR_KEY_TEXT: None, SENSOR_KEY_TIME: None, SENSOR_KEY_STATUS: None}
        soup = BeautifulSoup(html, 'html.parser')

        # --- TEXT ---
        text_div = soup.find('div', class_='ch_timer_text')
        text_value: Optional[str] = None
        if text_div:
            text_value = text_div.get_text(separator=' ', strip=True)
            data[SENSOR_KEY_TEXT] = text_value

        # Detection text for status & fallbacks
        detection_text = text_value or soup.get_text(separator='
', strip=True)

        # --- STATUS ---
        status: Optional[str] = None
        if any(p in detection_text for p in STATUS_ON_PHRASES):
            status = 'ON'
        elif any(p in detection_text for p in STATUS_OFF_PHRASES):
            status = 'OFF'
        elif 'Електроенергія присутня' in detection_text:
            status = 'ON'
        elif 'Електроенергія відсутня' in detection_text:
            status = 'OFF'
        data[SENSOR_KEY_STATUS] = status

        # --- TIME FROM DOM (hours/minutes/seconds) ---
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

        # --- FALLBACKS ---
        # 1) Parse H/M/S in text
        if (seconds is None) or (seconds == 0):
            m = HMS_RE.search(detection_text)
            if m and (m.group(1) or m.group(2) or m.group(3)):
                seconds = self._hms_to_seconds(m)

        # 2) Compute from OFF intervals list "З HH:MM до HH:MM"
        if (seconds is None) or (seconds == 0):
            intervals = self._parse_off_intervals(detection_text)
            now = self._now()
            if intervals:
                # Are we currently OFF?
                current_off = next(((st, en) for st, en in intervals if st <= now < en), None)
                if current_off:
                    # Time until ON (end of current OFF interval)
                    seconds = max(0, int((current_off[1] - now).total_seconds()))
                    data[SENSOR_KEY_STATUS] = data[SENSOR_KEY_STATUS] or 'OFF'
                else:
                    # Next OFF interval → time until OFF
                    next_off = next(((st, en) for st, en in intervals if st > now), None)
                    if next_off:
                        seconds = max(0, int((next_off[0] - now).total_seconds()))
                        data[SENSOR_KEY_STATUS] = data[SENSOR_KEY_STATUS] or 'ON'

        data[SENSOR_KEY_TIME] = seconds

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
