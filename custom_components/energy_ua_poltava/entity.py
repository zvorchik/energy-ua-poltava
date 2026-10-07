
from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EnergyUAPeriodsCoordinator


def device_info(entry_id: str) -> dict:
    return {
        "identifiers": {(DOMAIN, entry_id)},
        "name": "EnergyUA Schedule",
    }


class EnergyUAEntity(CoordinatorEntity[EnergyUAPeriodsCoordinator]):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_device_info = device_info(entry_id)
