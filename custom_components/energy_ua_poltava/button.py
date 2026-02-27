from homeassistant.components.button import ButtonEntity

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([EnergyUARestartButton(hass, entry)])

class EnergyUARestartButton(ButtonEntity):
    def __init__(self, hass, entry):
        self._hass = hass
        self._entry = entry

    @property
    def name(self):
        return "Energy UA Перезапуск"

    async def async_press(self):
        await self._hass.config_entries.async_reload(self._entry.entry_id)