
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_KEY_STATUS, CONF_PRETRIGGER_MINUTES

# Binary sensors are declared in sensor.py (_Base subclasses). This file kept for future ext.
