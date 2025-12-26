
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN, ATTR_PERIODS, ATTR_COUNTDOWN_HM, ATTR_NEXT_CHANGE_TYPE

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        EnergyUAMinutesSensor(coordinator, entry.entry_id),
        EnergyUACountdownSensor(coordinator, entry.entry_id),
    ]
    async_add_entities(entities)

class EnergyUAMinutesSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "EnergyUA Minutes Until Next Change"
    _attr_native_unit_of_measurement = "min"
    _attr_unique_id = "energyua_minutes_until_next_change"

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": "EnergyUA Schedule",
            "manufacturer": "Energy-UA",
        }

    @property
    def native_value(self):
        return self.coordinator.data.get("minutes_until")

    @property
    def extra_state_attributes(self):
        periods = self.coordinator.data.get("periods", [])
        # Convert to human-readable
        periods_txt = [p.get("text") for p in periods]
        return {
            ATTR_COUNTDOWN_HM: self.coordinator.data.get("countdown_hm"),
            ATTR_NEXT_CHANGE_TYPE: self.coordinator.data.get("next_type"),
            ATTR_PERIODS: periods_txt,
        }

class EnergyUACountdownSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "EnergyUA Countdown"
    _attr_unique_id = "energyua_countdown_hm"

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": "EnergyUA Schedule",
            "manufacturer": "Energy-UA",
        }

    @property
    def native_value(self):
        return self.coordinator.data.get("countdown_hm")
