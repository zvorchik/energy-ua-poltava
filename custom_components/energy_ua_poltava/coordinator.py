
from __future__ import annotations

import logging, re
from datetime import timedelta
from bs4 import BeautifulSoup
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_URL, CONF_UPDATE_MINUTES, CONF_PRETRIGGER_MINUTES

_LOGGER = logging.getLogger(__name__)
TIME_RE = re.compile(r"З\s*(\d{2}:\d{2})\s*до\s*(\d{2}:\d{2})")

class EnergyUACoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry):
        self.hass = hass
        self.entry = entry
        self.url = entry.data.get(CONF_URL)
        update_minutes = entry.options.get(CONF_UPDATE_MINUTES, entry.data.get(CONF_UPDATE_MINUTES))
        self.pretrigger = entry.options.get(CONF_PRETRIGGER_MINUTES, entry.data.get(CONF_PRETRIGGER_MINUTES))
        self.last_html = None
        super().__init__(hass, logger=_LOGGER, name=DOMAIN, update_interval=timedelta(minutes=update_minutes))

    async def _async_update_data(self):
        session = async_get_clientsession(self.hass)
        periods = []
        html = ""
        try:
            async with session.get(self.url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20) as resp:
                html = await resp.text()
        except Exception as e:
            _LOGGER.warning("EnergyUA request failed: %s", e)
        self.last_html = html

        if html:
            soup = BeautifulSoup(html, "html.parser")

            # 1) Основний контейнер
            cont = soup.select_one("div.periods_items")
            spans = []
            if cont:
                spans = cont.find_all("span")

            # 2) Якщо немає контейнера — шукаємо span з двома <b> по всій сторінці
            if not spans:
                spans = [sp for sp in soup.find_all("span") if len(sp.find_all("b")) >= 2]

            # 3) Парсимо з <b> (надійний спосіб)
            for sp in spans:
                b_tags = sp.find_all("b")
                if len(b_tags) >= 2:
                    start_s = (b_tags[0].get_text(strip=True) or "").strip()
                    end_s   = (b_tags[1].get_text(strip=True) or "").strip()
                    now = dt_util.now()
                    try:
                        sh, sm = [int(x) for x in start_s.split(":")]
                        eh, em = [int(x) for x in end_s.split(":")]
                    except Exception:
                        continue
                    sdt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
                    edt = now.replace(hour=eh, minute=em, second=0, microsecond=0)
                    if edt < sdt:
                        edt = edt + timedelta(days=1)
                    periods.append({"start": sdt, "end": edt, "text": sp.get_text(" ", strip=True)})

            # 4) Якщо все ще порожньо — regex по всьому HTML
            if not periods:
                for m in TIME_RE.finditer(soup.get_text(" ", strip=True)):
                    start_s, end_s = m.group(1), m.group(2)
                    now = dt_util.now()
                    try:
                        sh, sm = [int(x) for x in start_s.split(":")]
                        eh, em = [int(x) for x in end_s.split(":")]
                    except Exception:
                        continue
                    sdt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
                    edt = now.replace(hour=eh, minute=em, second=0, microsecond=0)
                    if edt < sdt:
                        edt = edt + timedelta(days=1)
                    periods.append({"start": sdt, "end": edt, "text": f"З {start_s} до {end_s}"})

        # Обчислення
        nowdt = dt_util.now()
        in_outage = False
        next_change = None
        for p in periods:
            s, e = p["start"], p["end"]
            if s <= nowdt <= e:
                in_outage = True
                next_change = e
                break
        if not in_outage:
            for p in periods:
                s = p["start"]
                if s > nowdt and (next_change is None or s < next_change):
                    next_change = s
        minutes_until = -1
        countdown_hm = "Невідомо"
        next_type = None
        if next_change is not None:
            minutes_until = int((next_change - nowdt).total_seconds() // 60)
            countdown_hm = f"{minutes_until//60:02d}:{minutes_until%60:02d}"
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
