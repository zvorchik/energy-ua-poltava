
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from .const import DOMAIN

PLATFORMS = [Platform.SENSOR]

async def async_setup(hass: HomeAssistant, config):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}
    # Compatibility shim: new API (2024+) vs old (2022.5)
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except AttributeError:
        hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
