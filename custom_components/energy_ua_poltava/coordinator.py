
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
    DEFAULT_PRETRIGGER_MINUTES,
    DEFAULT_SCAN_MINUTES,
    CONF_GROUP,
    CONF_SCAN_INTERVAL,
    CONF_PRETRIGGER_MINUTES,
    USER_AGENT,
)
from .schedule import Period, ScheduleParseError, compute, parse_schedule

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 20
# Після невдалого запиту (Cloudflare, мережа) пробуємо знову раніше за scan_minutes,
# але не частіше ніж раз на пів години, щоб не довбати сайт.
RETRY_INTERVAL = timedelta(minutes=30)


class EnergyUAPeriodsCoordinator(DataUpdateCoordinator):
    """Графік тягнемо раз на scan_minutes, таймер перераховуємо щохвилини локально."""

    def __init__(self, hass: HomeAssistant, entry):
        self.entry = entry

        self.group: str = entry.data.get(CONF_GROUP)
        self.scan_min = int(
            entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL))
            or DEFAULT_SCAN_MINUTES
        )
        self.pretrigger_min = int(
            entry.options.get(CONF_PRETRIGGER_MINUTES, entry.data.get(CONF_PRETRIGGER_MINUTES))
            or DEFAULT_PRETRIGGER_MINUTES
        )

        self.url = f"{DEFAULT_BASE_URL}{self.group}"
        self._scan_interval = timedelta(minutes=self.scan_min)

        self._periods: List[Period] = []
        self._last_success: Optional[datetime] = None
        self._unsub_tick = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=self._scan_interval,
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
            # Лишаємо попередній графік: час у ньому абсолютний, таймер далі рахує
            _LOGGER.warning(
                "EnergyUA: графік не оновився (%s), лишаю отриманий %s", err, self._last_success
            )
            self.update_interval = min(RETRY_INTERVAL, self._scan_interval)
        else:
            self._periods = periods
            self._last_success = dt_util.now()
            self.update_interval = self._scan_interval
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
