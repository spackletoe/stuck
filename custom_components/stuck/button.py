"""Button platform for the Stuck integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import StuckCoordinator
from .models import TrackedObject


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Stuck button entities for a config entry."""
    coordinator: StuckCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    entities = [
        StuckResetButton(coordinator, entry.entry_id, obj)
        for obj in coordinator.objects.values()
    ]
    async_add_entities(entities)


class StuckResetButton(CoordinatorEntity[StuckCoordinator], ButtonEntity):
    """Button entity to reset a tracked object timer."""

    def __init__(
        self,
        coordinator: StuckCoordinator,
        config_entry_id: str,
        obj: TrackedObject,
    ) -> None:
        """Initialize the reset button."""
        super().__init__(coordinator)
        self._config_entry_id = config_entry_id
        self._object_id = obj.id
        self._attr_name = f"{obj.name} Reset"
        self._attr_unique_id = f"{config_entry_id}_{obj.id}_reset"
        self._attr_has_entity_name = True

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return self.coordinator.get_object(self._object_id) is not None

    async def async_press(self) -> None:
        """Reset the tracked object timer."""
        await self.coordinator.async_reset_object(self._object_id)
