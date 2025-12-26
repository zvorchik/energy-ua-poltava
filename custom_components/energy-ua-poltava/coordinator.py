
from __future__ import annotations

import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_URL,
    CONF_UPDATE_MINUTES,
    CONF_PRETRIGGER_MINUTES,
    ATTR_PERIODS,
    ATTR_COUNTDOWN_HM,
    ATTR_NEXT_CHANGE_TYPE,
)

TIME_RE = re.compile(r"(\d{2}:\d{2}).*?(\d{2}:\d{2})")

class EnergyUACoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry):
        self.hass = hass
        self.entry = entry
        url = entry.data.get(CONF_URL)
        update_minutes = entry.options.get(CONF_UPDATE_MINUTES, entry.data.get(CONF_UPDATE_MINUTES))
        self.pretrigger = entry.options.get(CONF_PRETRIGGER_MINUTES, entry.data.get(CONF_PRETRIGGER_MINUTES))
        self.url = url
        self.update_interval = timedelta(minutes=update_minutes)
        super().__init__(
            hass,
            logger=hass.logger,
            name=DOMAIN,
            update_interval=self.update_interval,
        )

    async def _async_update_data(self):
        session = async_get_clientsession(self.hass)
        periods = []
        try:
            async with session.get(self.url, timeout=20) as resp:
                html = await resp.text()
        except Exception as e:
            # Keep previous data if request fails
            html = ""

        if html:
            soup = BeautifulSoup(html, "html.parser")
            cont = soup.select_one("div.periods_items")
            if cont:
                spans = cont.find_all("span")
                for sp in spans:
                    text = sp.get_text(" ", strip=True)
                    m = TIME_RE.search(text)
                    if not m:
                        continue
                    start_s, end_s = m.group(1), m.group(2)
                    # Build aware datetimes in local timezone today
                    tz = dt_util.get_time_zone(str(self.hass.config.time_zone)) if self.hass.config.time_zone else dt_util.DEFAULT_TIME_ZONE
                    today = dt_util.now(tz).date()
                    sdt = dt_util.as_local(dt_util.parse_datetime(f"{today} {start_s}:00"))
                    edt = dt_util.as_local(dt_util.parse_datetime(f"{today} {end_s}:00"))
                    if edt < sdt:
                        # Cross midnight → end is next day
                        edt = edt + timedelta(days=1)
                    periods.append({"start": sdt, "end": edt, "text": text})

        # Compute states
        nowdt = dt_util.now()
        in_outage = False
        next_change = None
        # Is now inside any period?
        for p in periods:
            s, e = p["start"], p["end"]
            if s <= nowdt <= e:
                in_outage = True
                next_change = e
                break
        if not in_outage:
            # Next start
            for p in periods:
                s = p["start"]
                if s > nowdt and (next_change is None or s < next_change):
                    next_change = s
        minutes_until = -1
        countdown_hm = "unknown"
        next_type = None
        if next_change is not None:
            minutes_until = int((next_change - nowdt).total_seconds() // 60)
            h = minutes_until // 60
            m = minutes_until % 60
            countdown_hm = f"{h:02d}:{m:02d}"
            next_type = "on" if in_outage else "off"

        pretrigger_on = minutes_until >= 0 and (minutes_until == int(self.pretrigger or 10))

        return {
            "periods": periods,
            "in_outage": in_outage,
            "next_change": next_change,
            "minutes_until": minutes_until,
            "countdown_hm": countdown_hm,
            "next_type": next_type,
            "pretrigger": pretrigger_on,
        }
