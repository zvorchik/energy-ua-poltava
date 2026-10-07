from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import EnergyUAPeriodsCoordinator

PLATFORMS = ["sensor", "binary_sensor", "button"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Координатор створюється тут, а не в sensor.py: інакше binary_sensor міг
    # піднятися раніше і не знайти його в hass.data.
    coordinator = EnergyUAPeriodsCoordinator(hass, entry)
    # Не async_config_entry_first_refresh: якщо сайт недоступний (Cloudflare),
    # HA повторював би налаштування кожну хвилину-дві. Так сутності будуть
    # unavailable, а наступна спроба — за RETRY_INTERVAL.
    await coordinator.async_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    coordinator.start_tick()
    entry.async_on_unload(coordinator.stop_tick)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    if hasattr(hass.config_entries, "async_forward_entry_setups"):
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    else:
        for platform in PLATFORMS:
            await hass.config_entries.async_forward_entry_setup(entry, platform)

    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


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
