
from __future__ import annotations

import re
import logging
from datetime import datetime, time as dtime, timedelta
from typing import Any, Dict, Optional, List, Tuple

from bs4 import BeautifulSoup
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    DEFAULT_BASE_URL,
    CONF_GROUP,
    CONF_SCAN_INTERVAL,
    CONF_PRETRIGGER_MINUTES,
    SENSOR_KEY_TEXT,
    SENSOR_KEY_TIME,
    SENSOR_KEY_STATUS,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

STATUS_ON_PHRASES = ["Наступне відключення заплановане через", "Електроенергія присутня"]
STATUS_OFF_PHRASES = ["До увімкнення залишилось", "До увімкнення залишилось почекати", "Електроенергія відсутня"]

OFF_INTERVAL_RE = re.compile(r"З\s*(\d{1,2}:\d{2})\s*до\s*(\d{1,2}:\d{2})", re.IGNORECASE)
HMS_RE = re.compile(r"(\d+)\s*(?:год\.?|h)?\s*(\d+)?\s*(?:хв\.?|m)?\s*(\d+)?\s*(?:сек\.?|s)?", re.IGNORECASE)

class EnergyUATimerCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry):
        self.hass = hass
        self.entry = entry
        self.session = async_get_clientsession(hass)
        self.group = entry.data.get(CONF_GROUP)
        scan_seconds = entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL))
        self.pretrigger = entry.options.get(CONF_PRETRIGGER_MINUTES, entry.data.get(CONF_PRETRIGGER_MINUTES))
        self.url = f"{DEFAULT_BASE_URL}{self.group}"
        self.last_html = None
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_seconds or 60),
        )

    def _now(self) -> datetime:
        return dt_util.now()

    def _combine_today(self, ts: str) -> Tuple[datetime, datetime]:
        h, m = ts.split(":")
        st = self._now().replace(hour=int(h), minute=int(m), second=0, microsecond=0)
        return st, st

    @staticmethod
    def _hms_to_seconds(m: re.Match) -> int:
        h = int(m.group(1) or 0)
        mn = int(m.group(2) or 0)
        s = int(m.group(3) or 0)
        return h * 3600 + mn * 60 + s

    def _parse_off_intervals(self, page_text: str) -> List[Tuple[datetime, datetime]]:
        intervals: List[Tuple[datetime, datetime]] = []
        now = self._now()
        for m in OFF_INTERVAL_RE.finditer(page_text):
            start_ts, end_ts = m.group(1), m.group(2)
            sh, sm = [int(x) for x in start_ts.split(":")]
            eh, em = [int(x) for x in end_ts.split(":")]
            sdt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
            edt = now.replace(hour=eh, minute=em, second=0, microsecond=0)
            if edt <= sdt:
                edt = edt + timedelta(days=1)
            intervals.append((sdt, edt))
        return sorted(intervals, key=lambda x: x[0])

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            async with self.session.get(self.url, timeout=20, headers={"User-Agent": USER_AGENT}) as resp:
                html = await resp.text()
        except Exception as err:
            raise UpdateFailed(f"Energy UA fetch error: {err}")
        self.last_html = html

        data: Dict[str, Any] = {SENSOR_KEY_TEXT: None, SENSOR_KEY_TIME: None, SENSOR_KEY_STATUS: None}
        soup = BeautifulSoup(html, "html.parser")

        # --- TEXT ---
        text_div = soup.find("div", class_="ch_timer_text")
        text_val = text_div.get_text(" ", strip=True) if text_div else None
        data[SENSOR_KEY_TEXT] = text_val
        detection_text = text_val or soup.get_text(" ", strip=True)

        # --- STATUS ---
        status = None
        if any(p in detection_text for p in STATUS_OFF_PHRASES):
            status = "OFF"
        elif any(p in detection_text for p in STATUS_ON_PHRASES):
            status = "ON"
        data[SENSOR_KEY_STATUS] = status

        # --- TIMER (H/M/S DOM) ---
        seconds = None
        t_div = soup.find("div", class_="ch_timer_time")
        if t_div:
            try:
                h_el = t_div.find(id="hours")
                m_el = t_div.find(id="minutes")
                s_el = t_div.find(id="seconds")
                h = int(h_el.get_text(strip=True)) if h_el else 0
                m = int(m_el.get_text(strip=True)) if m_el else 0
                s = int(s_el.get_text(strip=True)) if s_el else 0
                seconds = h * 3600 + m * 60 + s
            except Exception:
                seconds = None

        # --- FALLBACK 1: regex H/M/S ---
        if not seconds:
            m = HMS_RE.search(detection_text)
            if m and (m.group(1) or m.group(2) or m.group(3)):
                seconds = self._hms_to_seconds(m)

        # --- FALLBACK 2: intervals 'З HH:MM до HH:MM' ---
        if not seconds:
            intervals = self._parse_off_intervals(detection_text)
            now = self._now()
            if intervals:
                current = next(((st, en) for st, en in intervals if st <= now < en), None)
                if current:
                    seconds = max(0, int((current[1] - now).total_seconds()))
                    data[SENSOR_KEY_STATUS] = data[SENSOR_KEY_STATUS] or "OFF"
                else:
                    next_off = next(((st, en) for st, en in intervals if st > now), None)
                    if next_off:
                        seconds = max(0, int((next_off[0] - now).total_seconds()))
                        data[SENSOR_KEY_STATUS] = data[SENSOR_KEY_STATUS] or "ON"

        data[SENSOR_KEY_TIME] = seconds
        return data
