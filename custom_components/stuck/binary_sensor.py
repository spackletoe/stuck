"""Binary sensor platform for the Stuck integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN, STATUS_OVERDUE
from .coordinator import StuckCoordinator
from .models import TrackedObject


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Stuck binary sensors for a config entry."""
    coordinator: StuckCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    entities = [
        StuckOverdueBinarySensor(coordinator, entry.entry_id, obj)
        for obj in coordinator.list_tracked_objects_for_ui()
    ]
    async_add_entities(entities)


class StuckOverdueBinarySensor(CoordinatorEntity[StuckCoordinator], BinarySensorEntity):
    """Binary sensor indicating whether a tracked object is overdue."""

    def __init__(
        self,
        coordinator: StuckCoordinator,
        config_entry_id: str,
        obj: TrackedObject,
    ) -> None:
        """Initialize the overdue binary sensor."""
        super().__init__(coordinator)
        self._config_entry_id = config_entry_id
        self._object_id = obj.id
        self._attr_name = f"{obj.name} Overdue"
        self._attr_unique_id = f"{config_entry_id}_{obj.id}_overdue"
        self._attr_has_entity_name = True

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return self.coordinator.get_object(self._object_id) is not None

    @property
    def is_on(self) -> bool:
        """Return true if the tracked object is overdue."""
        obj = self.coordinator.get_object(self._object_id)
        if obj is None:
            return False
        return self.coordinator.get_object_status(obj) == STATUS_OVERDUE
