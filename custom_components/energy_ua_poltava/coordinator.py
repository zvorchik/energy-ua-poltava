
from __future__ import annotations

import re
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    DEFAULT_BASE_URL,
    CONF_GROUP,
    CONF_SCAN_INTERVAL,
    CONF_PRETRIGGER_MINUTES,
    ATTR_COUNTDOWN_HM,
    ATTR_NEXT_CHANGE_TYPE,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

# Регекс для "З HH:MM до HH:MM" — толерирует пробелы/переносы
PERIOD_RE = re.compile(r"З\s*(\d{1,2}:\d{2})\s*до\s*(\d{1,2}:\d{2})", re.IGNORECASE)


class EnergyUAPeriodsCoordinator(DataUpdateCoordinator):
    """Координатор:
    - по update_interval парсит сайт (scan_minutes в настройках);
    - каждые 60 секунд локально пересчитывает обратный отсчёт.
    """

    def __init__(self, hass: HomeAssistant, entry):
        self.hass = hass
        self.entry = entry

        self.group: str = entry.data.get(CONF_GROUP)
        self.scan_min: int = entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL))
        self.pretrigger_min: int = entry.options.get(CONF_PRETRIGGER_MINUTES, entry.data.get(CONF_PRETRIGGER_MINUTES))

        self.url = f"{DEFAULT_BASE_URL}{self.group}"

        # Кеш периодов (aware datetime)
        self._periods: List[Dict[str, Any]] = []
        self._unsub_tick = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=self.scan_min or 15),
        )

    async def async_config_entry_first_refresh(self) -> None:
        # Выполняем стандартную первую загрузку
        await super().async_config_entry_first_refresh()
        # Запускаем минутный тик локального таймера
        self._unsub_tick = async_track_time_interval(
            self.hass, self._recompute_and_notify, timedelta(minutes=1)
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Парсинг сайта и первичный расчёт состояния."""
        session = async_get_clientsession(self.hass)
        html = ""
        periods_raw: List[Dict[str, Any]] = []

        try:
            async with session.get(self.url, headers={"User-Agent": USER_AGENT}, timeout=20) as resp:
                html = await resp.text()
        except Exception as e:
            _LOGGER.warning("EnergyUA request failed: %s", e)

        if html:
            soup = BeautifulSoup(html, "html.parser")

            # 1) Попытка через контейнер
            cont = soup.select_one("div.periods_items")
            if cont:
                for sp in cont.find_all("span"):
                    b_tags = sp.find_all("b")
                    if len(b_tags) >= 2:
                        start_s = b_tags[0].get_text(strip=True)
                        end_s = b_tags[1].get_text(strip=True)
                        periods_raw.append({"start": start_s, "end": end_s, "text": sp.get_text(" ", strip=True)})

            # 2) Если не найдено — парсим весь текст регексом
            if not periods_raw:
                text = soup.get_text(" ", strip=True)
                for m in PERIOD_RE.finditer(text):
                    start_s, end_s = m.group(1), m.group(2)
                    periods_raw.append({"start": start_s, "end": end_s, "text": f"З {start_s} до {end_s}"})

        # Нормализация в aware datetime
        now = dt_util.now()
        norm_periods: List[Dict[str, Any]] = []
        for p in periods_raw:
            try:
                sh, sm = [int(x) for x in p["start"].split(":")]
                eh, em = [int(x) for x in p["end"].split(":")]
            except Exception:
                continue

            sdt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
            edt = now.replace(hour=eh, minute=em, second=0, microsecond=0)
            if edt <= sdt:
                edt = edt + timedelta(days=1)

            norm_periods.append({"start": sdt, "end": edt, "text": p.get("text")})

        self._periods = norm_periods

        # Возвращаем текущие вычисленные данные
        return self._compute(now)

    def _compute(self, now) -> Dict[str, Any]:
        """Локальный расчёт состояния/таймера от времени HA."""
        in_outage = False
        next_change: Optional[Any] = None

        for p in self._periods:
            s, e = p["start"], p["end"]
            if s <= now <= e:
                in_outage = True
                next_change = e
                break

        if not in_outage:
            for p in self._periods:
                s = p["start"]
                if s > now and (next_change is None or s < next_change):
                    next_change = s

        minutes_until = -1
        countdown_hm = "Неизвестно"
        next_change_type = None

        if next_change is not None:
            minutes_until = int((next_change - now).total_seconds() // 60)
            if minutes_until < 0:
                minutes_until = 0
            countdown_hm = f"{minutes_until//60:02d}:{minutes_until%60:02d}"
            next_change_type = "on" if in_outage else "off"

        # Претриггер: окно [0; pretrigger_min]
        pretrigger_on = minutes_until >= 0 and minutes_until <= int(self.pretrigger_min or 10)

        return {
            "periods": self._periods,
            "in_outage": in_outage,
            "minutes_until": minutes_until,
            "countdown_hm": countdown_hm,
            "next_change_type": next_change_type,
            "pretrigger": pretrigger_on,
            "source_url": self.url,
        }

    async def _recompute_and_notify(self, _now) -> None:
        """Минутный тик: пересчитать и уведомить подписчиков."""
        now = dt_util.now()
        data = self._compute(now)
        self.async_set_updated_data(data)
