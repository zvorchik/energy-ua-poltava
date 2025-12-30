
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_GROUP,
    CONF_SCAN_INTERVAL,
    CONF_PRETRIGGER_MINUTES,
    DEFAULT_GROUP,
    DEFAULT_SCAN_MINUTES,
    DEFAULT_PRETRIGGER_MINUTES,
)

class EnergyUAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_GROUP])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="EnergyUA Schedule", data=user_input)
        schema = vol.Schema({
            vol.Required(CONF_GROUP, default=DEFAULT_GROUP): str,
            vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_MINUTES): vol.All(int, vol.Range(min=1, max=1440)),
            vol.Required(CONF_PRETRIGGER_MINUTES, default=DEFAULT_PRETRIGGER_MINUTES): vol.All(int, vol.Range(min=1, max=180)),
        })
        return self.async_show_form(step_id="user", data_schema=schema)

class EnergyUAOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_options(user_input)

    async def async_step_options(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        options = self.config_entry.options
        schema = vol.Schema({
            vol.Required(CONF_SCAN_INTERVAL, default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_MINUTES)): vol.All(int, vol.Range(min=1, max=1440)),
            vol.Required(CONF_PRETRIGGER_MINUTES, default=options.get(CONF_PRETRIGGER_MINUTES, DEFAULT_PRETRIGGER_MINUTES)): vol.All(int, vol.Range(min=1, max=180)),
        })
        return self.async_show_form(step_id="options", data_schema=schema)

@callback
def async_get_options_flow(config_entry):
    return EnergyUAOptionsFlowHandler(config_entry)
