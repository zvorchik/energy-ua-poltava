from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

class EnergyUAReloadButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        self._attr_name = "Reload EnergyUA Poltava"
        self._attr_icon = "mdi:reload"

    async def async_press(self) -> None:
        # викликаємо перезавантаження інтеграційного запису
        await self.hass.services.async_call(
            "homeassistant",
            "reload_config_entry",
            {"entry_id": self.entry.entry_id},
        )
