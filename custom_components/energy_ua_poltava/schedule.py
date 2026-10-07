"""Розбір сторінки energy-ua.info/cherga/<група> і розрахунок таймера.

Модуль не залежить від Home Assistant, щоб логіку можна було перевірити окремо.
"""
from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

# Статуси з JS сайту: red — світла немає, yellow — можливе відключення.
# Решта статусів на графіку малюються як "світло є".
OUTAGE_STATUSES = ("red", "yellow")

# Сусідні періоди з проміжком до хвилини (23:59 → 00:00) зливаються в один,
# щоб таймер не показував "світло через 1 хв" посеред суцільного відключення.
MERGE_GAP = timedelta(minutes=1)

NO_OUTAGES_TEXT = "Відключень немає"

TODAY_JS_RE = re.compile(r"\bconst\s+periods\s*=\s*")
TOMORROW_JS_RE = re.compile(r"\btomorrowPeriods\s*=\s*(?:Object\.values\(\s*)?")
PERIOD_TEXT_RE = re.compile(r"З\s*(\d{1,2}:\d{2})\s*до\s*(\d{1,2}:\d{2})", re.IGNORECASE)
TOMORROW_TITLE_RE = re.compile(r"Відключення\s+завтра", re.IGNORECASE)


class ScheduleParseError(Exception):
    """Сторінка не схожа на графік: заглушка Cloudflare, зміна верстки тощо."""


@dataclass(frozen=True)
class Period:
    start: datetime
    end: datetime
    status: str = "red"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "status": self.status,
        }


def parse_schedule(html: str, now: datetime) -> List[Period]:
    """Періоди на сьогодні й завтра. `now` — локальний aware datetime."""
    periods = _parse_js(html)
    if periods is None:
        periods = _parse_html(html, now)
    if periods is None:
        raise ScheduleParseError("на сторінці немає графіка")
    # Всередині все в UTC: Python віднімає й порівнює aware-дати з однаковим
    # tzinfo за настінним часом, і в ніч переведення годинника таймер брехав би на годину.
    return merge_periods(
        Period(p.start.astimezone(timezone.utc), p.end.astimezone(timezone.utc), p.status)
        for p in periods
    )


def merge_periods(periods) -> List[Period]:
    merged: List[Period] = []
    for p in sorted(periods, key=lambda x: x.start):
        if merged and p.start <= merged[-1].end + MERGE_GAP:
            last = merged[-1]
            status = "red" if "red" in (last.status, p.status) else last.status
            merged[-1] = Period(last.start, max(last.end, p.end), status)
        else:
            merged.append(p)
    return merged


def compute(periods: List[Period], now: datetime, pretrigger_minutes: int) -> Dict[str, Any]:
    """`periods` — з parse_schedule (UTC); у відповіді час у поясі `now`."""
    local_tz = now.tzinfo
    now = now.astimezone(timezone.utc)
    current = next((p for p in periods if p.start <= now < p.end), None)
    if current is not None:
        in_outage = True
        next_change: Optional[datetime] = current.end
        next_change_type: Optional[str] = "on"
    else:
        in_outage = False
        upcoming = [p for p in periods if p.start > now]
        nearest = min(upcoming, key=lambda p: p.start) if upcoming else None
        next_change = nearest.start if nearest else None
        next_change_type = "off" if nearest else None

    minutes_until: Optional[int] = None
    countdown_hm = NO_OUTAGES_TEXT
    if next_change is not None:
        # ceil: тік приходить на кілька мс пізніше :00, і floor дав би 9 замість 10
        minutes_until = max(0, math.ceil((next_change - now).total_seconds() / 60))
        countdown_hm = f"{minutes_until // 60:02d}:{minutes_until % 60:02d}"

    return {
        "periods": [
            Period(p.start.astimezone(local_tz), p.end.astimezone(local_tz), p.status)
            for p in periods
            if p.end > now
        ],
        "in_outage": in_outage,
        "next_change": next_change.astimezone(local_tz) if next_change is not None else None,
        "next_change_type": next_change_type,
        "minutes_until": minutes_until,
        "countdown_hm": countdown_hm,
        "pretrigger": minutes_until is not None and minutes_until <= pretrigger_minutes,
    }


def _parse_js(html: str) -> Optional[List[Period]]:
    """Дані з inline-скрипта: `const periods = [...]` і `tomorrowPeriods = Object.values(...)`.

    Час там в unix-секундах, тож дата й перехід через північ уже враховані.
    """
    today = _js_value(html, TODAY_JS_RE)
    if today is None:
        return None
    tomorrow = _js_value(html, TOMORROW_JS_RE)
    if tomorrow is None:
        _LOGGER.debug("EnergyUA: tomorrowPeriods не знайдено, беру лише сьогодні")
    out: List[Period] = []
    for item in _as_list(today) + _as_list(tomorrow):
        period = _period_from_js(item)
        if period is not None:
            out.append(period)
    return out


def _js_value(html: str, pattern: re.Pattern) -> Any:
    m = pattern.search(html)
    if not m:
        return None
    try:
        value, _ = json.JSONDecoder().raw_decode(html, m.end())
    except ValueError:
        _LOGGER.debug("EnergyUA: не вдалося розібрати JSON після %s", pattern.pattern)
        return None
    return value


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values())
    return []


def _period_from_js(item: Any) -> Optional[Period]:
    if not isinstance(item, dict):
        return None
    status = str(item.get("status") or "red")
    if status not in OUTAGE_STATUSES:
        return None
    try:
        start = datetime.fromtimestamp(float(item["time_from"]), timezone.utc)
        end = datetime.fromtimestamp(float(item["time_to"]), timezone.utc)
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        return None
    if end <= start:
        end += timedelta(days=1)
    return Period(start, end, status)


def _parse_html(html: str, now: datetime) -> Optional[List[Period]]:
    """Запасний варіант: список "З HH:MM до HH:MM" у блоках сьогодні/завтра."""
    soup = BeautifulSoup(html, "html.parser")
    titles = soup.select("h4.ch_day_title")
    containers = soup.select("div.periods_items")
    if not titles and not containers:
        return None

    out: List[Period] = []
    if containers:
        for cont in containers:
            day = now.date() + timedelta(days=_day_offset(cont))
            for span in cont.find_all("span"):
                b_tags = span.find_all("b")
                if len(b_tags) >= 2:
                    period = _period_from_hm(
                        b_tags[0].get_text(strip=True), b_tags[1].get_text(strip=True), day, now
                    )
                    if period is not None:
                        out.append(period)
        return out

    text = soup.get_text(" ", strip=True)
    parts = TOMORROW_TITLE_RE.split(text, maxsplit=1)
    for offset, part in enumerate(parts):
        day = now.date() + timedelta(days=offset)
        for m in PERIOD_TEXT_RE.finditer(part):
            period = _period_from_hm(m.group(1), m.group(2), day, now)
            if period is not None:
                out.append(period)
    return out


def _day_offset(container) -> int:
    title = container.find_previous("h4", class_="ch_day_title")
    if title is not None and "завтра" in title.get_text().lower():
        return 1
    return 0


def _period_from_hm(start_s: str, end_s: str, day: date, now: datetime) -> Optional[Period]:
    start = _at(day, start_s, now)
    end = _at(day, end_s, now)
    if start is None or end is None:
        return None
    if end <= start:
        end += timedelta(days=1)
    return Period(start, end, "red")


def _at(day: date, hm: str, now: datetime) -> Optional[datetime]:
    try:
        hours, minutes = (int(x) for x in hm.split(":"))
    except ValueError:
        return None
    if hours == 24 and minutes == 0:
        day, hours = day + timedelta(days=1), 0
    if not (0 <= hours < 24 and 0 <= minutes < 60):
        return None
    return datetime.combine(day, time(hours, minutes), tzinfo=now.tzinfo)
