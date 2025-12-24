
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_SCAN_INTERVAL
from .const import DOMAIN, CONF_GROUP, DEFAULT_GROUP, DEFAULT_SCAN_SECONDS

class EnergyUaPoltavaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title=f"Group {user_input[CONF_GROUP]}", data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_GROUP, default=DEFAULT_GROUP): str,
            vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_SECONDS): int,
        })
        return self.async_show_form(step_id='user', data_schema=schema, errors=errors)

    @callback
    def async_get_options_flow(self, config_entry):
        return EnergyUaPoltavaOptionsFlowHandler(config_entry)

class EnergyUaPoltavaOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_options(user_input)

    async def async_step_options(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title='', data=user_input)

        current = self.config_entry.data
        schema = vol.Schema({
            vol.Required(CONF_GROUP, default=current.get(CONF_GROUP, DEFAULT_GROUP)): str,
            vol.Optional(CONF_SCAN_INTERVAL, default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_SECONDS)): int,
        })
        return self.async_show_form(step_id='options', data_schema=schema)
