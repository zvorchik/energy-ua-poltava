
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PLATFORMS = ["sensor", "binary_sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # створимо координатор у платформі, тут лише форвардинг
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {}
    if hasattr(hass.config_entries, "async_forward_entry_setups"):
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    else:
        for platform in PLATFORMS:
            await hass.config_entries.async_forward_entry_setup(entry, platform)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if hasattr(hass.config_entries, "async_unload_platforms"):
        unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    else:
        unloaded = True
        if hasattr(hass.config_entries, "async_forward_entry_unload"):
            for platform in PLATFORMS:
                ok = await hass.config_entries.async_forward_entry_unload(entry, platform)
                unloaded = unloaded and ok
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded
