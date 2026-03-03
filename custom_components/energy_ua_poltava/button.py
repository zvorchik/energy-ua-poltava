from homeassistant.components.button import ButtonEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([EnergyUAReloadButton(hass, entry)])


class EnergyUAReloadButton(ButtonEntity):
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self._attr_name = "Reload EnergyUA Poltava"
        self._attr_unique_id = f"{entry.entry_id}_reload"
        self._attr_icon = "mdi:reload"

    async def async_press(self):
        await self.hass.services.async_call(
            "homeassistant",
            "reload_config_entry",
            {"entry_id": self.entry.entry_id},
            blocking=True,
        )
