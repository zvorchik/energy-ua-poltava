
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN, ATTR_COUNTDOWN_HM, ATTR_NEXT_CHANGE_TYPE
from .entity import EnergyUAEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        EnergyUAMinutesSensor(coordinator, entry.entry_id),
        EnergyUACountdownSensor(coordinator, entry.entry_id),
        EnergyUANextChangeSensor(coordinator, entry.entry_id),
    ])


def _iso(value):
    return value.isoformat() if value is not None else None


class EnergyUAMinutesSensor(EnergyUAEntity, SensorEntity):
    _attr_name = "EnergyUA Minutes Until Next Change"
    _attr_native_unit_of_measurement = "min"
    _attr_unique_id = "energyua_minutes_until_next_change"

    @property
    def native_value(self):
        # None (невідомо), коли відключень у графіку на сьогодні й завтра більше немає
        return self.coordinator.data.get("minutes_until")

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        return {
            ATTR_COUNTDOWN_HM: data.get("countdown_hm"),
            ATTR_NEXT_CHANGE_TYPE: data.get("next_change_type"),
            "next_change": _iso(data.get("next_change")),
            "periods": [p.as_dict() for p in data.get("periods", [])],
            "last_success": _iso(data.get("last_success")),
            "source_url": data.get("source_url"),
        }


class EnergyUACountdownSensor(EnergyUAEntity, SensorEntity):
    _attr_name = "EnergyUA Countdown"
    _attr_unique_id = "energyua_countdown_hm"

    @property
    def native_value(self):
        return self.coordinator.data.get("countdown_hm")


class EnergyUANextChangeSensor(EnergyUAEntity, SensorEntity):
    """Момент наступної зміни: фронтенд сам показує "через 2 год",
    а в автоматизаціях можна `trigger: time` з offset."""

    _attr_name = "EnergyUA Next Change"
    _attr_unique_id = "energyua_next_change"
    _attr_device_class = "timestamp"

    @property
    def native_value(self):
        return self.coordinator.data.get("next_change")

    @property
    def extra_state_attributes(self):
        return {ATTR_NEXT_CHANGE_TYPE: self.coordinator.data.get("next_change_type")}
