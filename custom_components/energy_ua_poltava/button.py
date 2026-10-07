from homeassistant.components.button import ButtonEntity

from .const import DOMAIN
from .entity import device_info


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        EnergyUAReloadButton(hass, entry),
        EnergyUAFetchButton(coordinator, entry),
    ])


class EnergyUAReloadButton(ButtonEntity):
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self._attr_name = "Reload EnergyUA Poltava"
        self._attr_unique_id = f"{entry.entry_id}_reload"
        self._attr_icon = "mdi:reload"
        self._attr_device_info = device_info(entry.entry_id)

    async def async_press(self):
        await self.hass.services.async_call(
            "homeassistant",
            "reload_config_entry",
            {"entry_id": self.entry.entry_id},
            blocking=True,
        )


class EnergyUAFetchButton(ButtonEntity):
    """Один запит до сайту зараз. Повторні натискання протягом ~10 с зливаються в один."""

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._attr_name = "EnergyUA Fetch Schedule"
        self._attr_unique_id = f"{entry.entry_id}_fetch"
        self._attr_icon = "mdi:cloud-download"
        self._attr_device_info = device_info(entry.entry_id)

    async def async_press(self):
        await self.coordinator.async_request_refresh()
