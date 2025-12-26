
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN, SENSOR_KEY_TEXT, SENSOR_KEY_TIME, SENSOR_KEY_STATUS, CONF_GROUP, DEFAULT_BASE_URL, CONF_PRETRIGGER_MINUTES
from .coordinator import EnergyUATimerCoordinator

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    # Build coordinator per entry
    coordinator = EnergyUATimerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Map to entities
    entities = [
        EnergyUAMinutesSensor(coordinator, entry),
        EnergyUACountdownSensor(coordinator, entry),
        EnergyUAPowerState(coordinator, entry),
        EnergyUAPretrigger(coordinator, entry),
        EnergyUAChTimeSensor(coordinator, entry),
        EnergyUAStatusSensor(coordinator, entry),
        EnergyUACombinedSensor(coordinator, entry),
    ]
    async_add_entities(entities)

class _Base(CoordinatorEntity[EnergyUATimerCoordinator], SensorEntity):
    def __init__(self, coordinator: EnergyUATimerCoordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        group = entry.data.get(CONF_GROUP)
        self._source = f"{DEFAULT_BASE_URL}{group}"
        self._pretrigger_min = entry.options.get(CONF_PRETRIGGER_MINUTES, entry.data.get(CONF_PRETRIGGER_MINUTES))

class EnergyUAMinutesSensor(_Base):
    _attr_name = "EnergyUA Minutes Until Next Change"
    _attr_native_unit_of_measurement = "min"
    _attr_unique_id = "energyua_minutes_until_next_change"
    @property
    def native_value(self):
        secs = self.coordinator.data.get(SENSOR_KEY_TIME)
        return -1 if secs is None else int(secs // 60)
    @property
    def extra_state_attributes(self):
        secs = self.coordinator.data.get(SENSOR_KEY_TIME)
        hm = "Невідомо" if secs is None else f"{int(secs)//60:02d}:{int(secs)%60:02d}"
        status = self.coordinator.data.get(SENSOR_KEY_STATUS)
        next_type = None
        if status == "OFF":
            next_type = "on"
        elif status == "ON":
            next_type = "off"
        return {
            "countdown_hm": hm,
            "next_change_type": next_type,
            "source_url": self._source,
        }

class EnergyUACountdownSensor(_Base):
    _attr_name = "EnergyUA Countdown"
    _attr_unique_id = "energyua_countdown_hm"
    @property
    def native_value(self):
        secs = self.coordinator.data.get(SENSOR_KEY_TIME)
        return "Невідомо" if secs is None else f"{int(secs)//60:02d}:{int(secs)%60:02d}"

class EnergyUAPowerState(_Base):
    _attr_name = "EnergyUA Power State Now"
    _attr_device_class = "power"
    _attr_unique_id = "energyua_power_state_now"
    @property
    def native_value(self):
        # not a numeric sensor, but keep for UI clarity
        return None
    @property
    def is_on(self):
        return self.coordinator.data.get(SENSOR_KEY_STATUS) == "ON"

class EnergyUAPretrigger(_Base):
    _attr_name = "EnergyUA Pretrigger"
    _attr_unique_id = "energyua_pretrigger"
    @property
    def is_on(self):
        secs = self.coordinator.data.get(SENSOR_KEY_TIME)
        return bool(secs is not None and int(secs) == int(self._pretrigger_min or 10) * 60)

class EnergyUAChTimeSensor(_Base):
    _attr_name = "Energy UA ch_timer_time"
    _attr_unique_id = "energyua_ch_timer_time"
    _attr_native_unit_of_measurement = "s"
    @property
    def native_value(self):
        return self.coordinator.data.get(SENSOR_KEY_TIME)

class EnergyUAStatusSensor(_Base):
    _attr_name = "Energy UA ch_status"
    _attr_unique_id = "energyua_ch_status"
    @property
    def native_value(self):
        return self.coordinator.data.get(SENSOR_KEY_STATUS)

class EnergyUACombinedSensor(_Base):
    _attr_name = "Energy UA ch_timer"
    _attr_unique_id = "energyua_ch_timer"
    _attr_native_unit_of_measurement = "s"
    @property
    def native_value(self):
        return self.coordinator.data.get(SENSOR_KEY_TIME)
    @property
    def extra_state_attributes(self):
        d = self.coordinator.data or {}
        return {
            "text": d.get(SENSOR_KEY_TEXT),
            "status": d.get(SENSOR_KEY_STATUS),
            "group": self._entry.data.get(CONF_GROUP),
            "source": self._source,
        }
