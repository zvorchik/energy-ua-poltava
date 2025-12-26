
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        EnergyUAPowerState(coordinator, entry.entry_id),
        EnergyUAPretrigger(coordinator, entry.entry_id),
    ]
    async_add_entities(entities)

class EnergyUAPowerState(CoordinatorEntity, BinarySensorEntity):
    _attr_name = "EnergyUA Power State Now"
    _attr_device_class = "power"
    _attr_unique_id = "energyua_power_state_now"

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": "EnergyUA Schedule",
            "manufacturer": "Energy-UA",
        }

    @property
    def is_on(self):
        return not self.coordinator.data.get("in_outage")

class EnergyUAPretrigger(CoordinatorEntity, BinarySensorEntity):
    _attr_name = "EnergyUA Pretrigger"
    _attr_unique_id = "energyua_pretrigger"

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": "EnergyUA Schedule",
            "manufacturer": "Energy-UA",
        }

    @property
    def is_on(self):
        return bool(self.coordinator.data.get("pretrigger"))
