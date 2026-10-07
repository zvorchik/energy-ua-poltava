
from __future__ import annotations

DOMAIN = "energy_ua_poltava"
DEFAULT_BASE_URL = "https://energy-ua.info/cherga/"
DEFAULT_GROUP = "3-1"
DEFAULT_SCAN_MINUTES = 180
MIN_SCAN_MINUTES = 30
DEFAULT_PRETRIGGER_MINUTES = 10
DEFAULT_AUTO_UPDATE = True

CONF_GROUP = "group"
CONF_SCAN_INTERVAL = "scan_minutes"
CONF_PRETRIGGER_MINUTES = "pretrigger_minutes"
CONF_AUTO_UPDATE = "auto_update"

ATTR_COUNTDOWN_HM = "countdown_hm"
ATTR_NEXT_CHANGE_TYPE = "next_change_type"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
)
