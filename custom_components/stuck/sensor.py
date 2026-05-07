"""Sensor platform for the Stuck integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
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
    """Set up Stuck sensor entities for a config entry."""
    coordinator: StuckCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    entities: list[SensorEntity] = [
        StuckTrackedObjectStatusSensor(coordinator, entry.entry_id, obj)
        for obj in coordinator.objects.values()
    ]
    entities.extend(
        [
            StuckTrackedObjectNextDueSensor(coordinator, entry.entry_id, obj)
            for obj in coordinator.objects.values()
        ]
    )
    entities.extend(
        [
            StuckTrackedObjectTimeRemainingSensor(coordinator, entry.entry_id, obj)
            for obj in coordinator.objects.values()
        ]
    )
    entities.extend(
        [
            StuckTrackedObjectTimeElapsedSensor(coordinator, entry.entry_id, obj)
            for obj in coordinator.objects.values()
        ]
    )
    entities.extend(
        [
            StuckObjectCountSensor(coordinator, entry.entry_id),
            StuckOverdueCountSensor(coordinator, entry.entry_id),
            StuckDueSoonCountSensor(coordinator, entry.entry_id),
            StuckPendingTagCountSensor(coordinator, entry.entry_id),
        ]
    )

    async_add_entities(entities)


class StuckBaseEntity(CoordinatorEntity[StuckCoordinator]):
    """Base class for Stuck entities."""

    def __init__(self, coordinator: StuckCoordinator, config_entry_id: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._config_entry_id = config_entry_id


class StuckTrackedObjectEntity(StuckBaseEntity):
    """Base class for entities tied to a tracked object."""

    def __init__(
        self,
        coordinator: StuckCoordinator,
        config_entry_id: str,
        obj: TrackedObject,
    ) -> None:
        """Initialize the tracked object entity."""
        super().__init__(coordinator, config_entry_id)
        self._object_id = obj.id
        self._attr_has_entity_name = True

    @property
    def tracked_object(self) -> TrackedObject | None:
        """Return the latest tracked object from the coordinator."""
        return self.coordinator.get_object(self._object_id)

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return self.tracked_object is not None


class StuckTrackedObjectStatusSensor(StuckTrackedObjectEntity, SensorEntity):
    """Status sensor for a tracked object."""

    def __init__(self, coordinator: StuckCoordinator, config_entry_id: str, obj: TrackedObject) -> None:
        super().__init__(coordinator, config_entry_id, obj)
        self._attr_name = f"{obj.name} Status"
        self._attr_unique_id = f"{config_entry_id}_{obj.id}_status"

    @property
    def native_value(self) -> str | None:
        obj = self.tracked_object
        if obj is None:
            return None
        return self.coordinator.get_object_status(obj)


class StuckTrackedObjectNextDueSensor(StuckTrackedObjectEntity, SensorEntity):
    """Next due sensor for a tracked object."""

    _attr_device_class = "timestamp"

    def __init__(self, coordinator: StuckCoordinator, config_entry_id: str, obj: TrackedObject) -> None:
        super().__init__(coordinator, config_entry_id, obj)
        self._attr_name = f"{obj.name} Next Due"
        self._attr_unique_id = f"{config_entry_id}_{obj.id}_next_due"

    @property
    def native_value(self):
        obj = self.tracked_object
        if obj is None:
            return None
        return self.coordinator.get_next_due_at(obj)


class StuckTrackedObjectTimeRemainingSensor(StuckTrackedObjectEntity, SensorEntity):
    """Remaining-time sensor for a tracked object."""

    def __init__(self, coordinator: StuckCoordinator, config_entry_id: str, obj: TrackedObject) -> None:
        super().__init__(coordinator, config_entry_id, obj)
        self._attr_name = f"{obj.name} Time Remaining"
        self._attr_unique_id = f"{config_entry_id}_{obj.id}_time_remaining"

    @property
    def native_value(self) -> str | None:
        obj = self.tracked_object
        if obj is None:
            return None
        remaining = self.coordinator.get_remaining_duration(obj)
        return _format_timedelta(remaining)


class StuckTrackedObjectTimeElapsedSensor(StuckTrackedObjectEntity, SensorEntity):
    """Elapsed-time sensor for a tracked object."""

    def __init__(self, coordinator: StuckCoordinator, config_entry_id: str, obj: TrackedObject) -> None:
        super().__init__(coordinator, config_entry_id, obj)
        self._attr_name = f"{obj.name} Time Elapsed"
        self._attr_unique_id = f"{config_entry_id}_{obj.id}_time_elapsed"

    @property
    def native_value(self) -> str | None:
        obj = self.tracked_object
        if obj is None:
            return None
        elapsed = self.coordinator.get_elapsed_duration(obj)
        return _format_timedelta(elapsed)


class StuckObjectCountSensor(StuckBaseEntity, SensorEntity):
    """Count sensor for tracked objects."""

    _attr_name = "Stuck Object Count"

    def __init__(self, coordinator: StuckCoordinator, config_entry_id: str) -> None:
        super().__init__(coordinator, config_entry_id)
        self._attr_unique_id = f"{config_entry_id}_object_count"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.objects)


class StuckOverdueCountSensor(StuckBaseEntity, SensorEntity):
    """Count sensor for overdue objects."""

    _attr_name = "Stuck Overdue Count"

    def __init__(self, coordinator: StuckCoordinator, config_entry_id: str) -> None:
        super().__init__(coordinator, config_entry_id)
        self._attr_unique_id = f"{config_entry_id}_overdue_count"

    @property
    def native_value(self) -> int:
        return sum(
            1
            for obj in self.coordinator.objects.values()
            if self.coordinator.get_object_status(obj) == "overdue"
        )


class StuckDueSoonCountSensor(StuckBaseEntity, SensorEntity):
    """Count sensor for due-soon objects."""

    _attr_name = "Stuck Due Soon Count"

    def __init__(self, coordinator: StuckCoordinator, config_entry_id: str) -> None:
        super().__init__(coordinator, config_entry_id)
        self._attr_unique_id = f"{config_entry_id}_due_soon_count"

    @property
    def native_value(self) -> int:
        return sum(
            1
            for obj in self.coordinator.objects.values()
            if self.coordinator.get_object_status(obj) == "due_soon"
        )


class StuckPendingTagCountSensor(StuckBaseEntity, SensorEntity):
    """Count sensor for pending tags."""

    _attr_name = "Stuck Pending Tag Count"

    def __init__(self, coordinator: StuckCoordinator, config_entry_id: str) -> None:
        super().__init__(coordinator, config_entry_id)
        self._attr_unique_id = f"{config_entry_id}_pending_tag_count"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.pending_tags)


def _format_timedelta(value: timedelta) -> str:
    """Format a timedelta as a compact string."""
    total_seconds = int(value.total_seconds())
    sign = "-" if total_seconds < 0 else ""
    total_seconds = abs(total_seconds)

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _seconds = divmod(remainder, 60)

    return f"{sign}{days}d {hours}h {minutes}m"
