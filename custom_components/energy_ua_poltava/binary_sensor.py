
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DOMAIN, ATTR_NEXT_CHANGE_TYPE
from .entity import EnergyUAEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        EnergyUAPowerState(coordinator, entry.entry_id),
        EnergyUAPretrigger(coordinator, entry.entry_id),
    ])


class EnergyUAPowerState(EnergyUAEntity, BinarySensorEntity):
    _attr_name = "EnergyUA Power State Now"
    _attr_device_class = "power"
    _attr_unique_id = "energyua_power_state_now"

    @property
    def is_on(self):
        return not self.coordinator.data.get("in_outage")


class EnergyUAPretrigger(EnergyUAEntity, BinarySensorEntity):
    """on за pretrigger_minutes до будь-якої зміни: і до відключення, і до появи світла.
    Напрямок — в атрибуті next_change_type (on — світло з'явиться, off — зникне)."""

    _attr_name = "EnergyUA Pretrigger"
    _attr_unique_id = "energyua_pretrigger"

    @property
    def is_on(self):
        return bool(self.coordinator.data.get("pretrigger"))

    @property
    def extra_state_attributes(self):
        return {
            ATTR_NEXT_CHANGE_TYPE: self.coordinator.data.get("next_change_type"),
            "minutes_until": self.coordinator.data.get("minutes_until"),
        }
