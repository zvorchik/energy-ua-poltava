
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    DEFAULT_BASE_URL,
    DEFAULT_AUTO_UPDATE,
    DEFAULT_PRETRIGGER_MINUTES,
    DEFAULT_SCAN_MINUTES,
    MIN_SCAN_MINUTES,
    CONF_AUTO_UPDATE,
    CONF_GROUP,
    CONF_SCAN_INTERVAL,
    CONF_PRETRIGGER_MINUTES,
    USER_AGENT,
)
from .schedule import Period, ScheduleParseError, compute, parse_schedule

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 20


class EnergyUAPeriodsCoordinator(DataUpdateCoordinator):
    """Графік тягнемо при старті, далі раз на scan_minutes (якщо auto_update)
    або кнопкою; таймер перераховуємо щохвилини локально."""

    def __init__(self, hass: HomeAssistant, entry):
        self.entry = entry
        conf = {**entry.data, **entry.options}

        self.group: str = conf.get(CONF_GROUP)
        self.scan_min = max(
            MIN_SCAN_MINUTES, int(conf.get(CONF_SCAN_INTERVAL) or DEFAULT_SCAN_MINUTES)
        )
        self.pretrigger_min = int(conf.get(CONF_PRETRIGGER_MINUTES) or DEFAULT_PRETRIGGER_MINUTES)
        self.auto_update = bool(conf.get(CONF_AUTO_UPDATE, DEFAULT_AUTO_UPDATE))

        self.url = f"{DEFAULT_BASE_URL}{self.group}"

        self._periods: List[Period] = []
        self._last_success: Optional[datetime] = None
        self._unsub_tick = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # None — сайт питаємо лише при старті й кнопкою "Fetch schedule"
            update_interval=timedelta(minutes=self.scan_min) if self.auto_update else None,
        )

    @callback
    def start_tick(self) -> None:
        # Рівно о :00 кожної хвилини, щоб pretrigger спрацьовував точно за N хвилин
        self._unsub_tick = async_track_time_change(self.hass, self._handle_tick, second=0)

    @callback
    def stop_tick(self) -> None:
        if self._unsub_tick is not None:
            self._unsub_tick()
            self._unsub_tick = None

    @callback
    def _handle_tick(self, _now) -> None:
        if self._last_success is None:
            return
        # Не async_set_updated_data: він щоразу відкладає планове оновлення
        # на update_interval, і при хвилинному тіку сайт не опитувався б ніколи.
        self.data = self._build_data(dt_util.now())
        self.async_update_listeners()

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            html = await self._async_fetch()
            periods = parse_schedule(html, dt_util.now())
        except (aiohttp.ClientError, asyncio.TimeoutError, ScheduleParseError) as err:
            if self._last_success is None:
                raise UpdateFailed(f"EnergyUA: не вдалося отримати графік: {err}") from err
            # Лишаємо попередній графік: час у ньому абсолютний, таймер далі рахує.
            # Наступна спроба — за звичайним інтервалом або кнопкою.
            _LOGGER.warning(
                "EnergyUA: графік не оновився (%s), лишаю отриманий %s", err, self._last_success
            )
        else:
            self._periods = periods
            self._last_success = dt_util.now()
        return self._build_data(dt_util.now())

    async def _async_fetch(self) -> str:
        session = async_get_clientsession(self.hass)
        async with session.get(
            self.url,
            headers={"User-Agent": USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
        ) as resp:
            resp.raise_for_status()
            return await resp.text()

    def _build_data(self, now: datetime) -> Dict[str, Any]:
        data = compute(self._periods, now, self.pretrigger_min)
        data["last_success"] = self._last_success
        data["source_url"] = self.url
        return data
