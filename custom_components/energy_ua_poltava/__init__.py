
from __future__ import annotations
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN
from .coordinator import EnergyUACoordinator

PLATFORMS = ["sensor", "binary_sensor"]

async def async_setup_entry(hass, entry):
    coordinator = EnergyUACoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Совместимость: новый API (2024+) или старый (2022.5.x)
    if hasattr(hass.config_entries, "async_forward_entry_setups"):
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    else:
        for platform in PLATFORMS:
            await hass.config_entries.async_forward_entry_setup(entry, platform)
    return True

async def async_unload_entry(hass, entry):
    # Выгрузка платформ (с учётом старых версий)
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
