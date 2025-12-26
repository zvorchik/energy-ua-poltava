
from __future__ import annotations

import os
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .coordinator import EnergyUACoordinator

PLATFORMS = ["sensor", "binary_sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = EnergyUACoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Register service to dump last HTML
    async def _dump_html_service(call):
        out_dir = hass.config.path("www")
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "energyua_dump.html")
        content = coordinator.last_html or "(no html captured)"
        # Write in executor to avoid blocking
        def _write():
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        await hass.async_add_executor_job(_write)

    hass.services.async_register(DOMAIN, "dump_html", _dump_html_service)

    # Forward platforms (compat for old/new HA)
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
