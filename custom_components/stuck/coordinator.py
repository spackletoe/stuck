"""Coordinator for the Stuck integration."""

from __future__ import annotations

import logging
from calendar import monthrange
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DEFAULT_DUE_SOON_THRESHOLD_DAYS,
    DEFAULT_SHOW_INACTIVE_OBJECTS,
    DOMAIN,
    STATUS_DUE_NOW,
    STATUS_DUE_SOON,
    STATUS_HEALTHY,
    STATUS_OVERDUE,
    UNIT_DAY,
    UNIT_MONTH,
    UNIT_WEEK,
    VALID_INTERVAL_UNITS,
)
from .models import IntegrationSettings, PendingTag, TrackedObject, utc_now_iso
from .storage import StuckStorage

_LOGGER = logging.getLogger(__name__)


class StuckCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate in-memory state for the Stuck integration."""

    def __init__(self, hass: HomeAssistant, storage: StuckStorage) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, logger=_LOGGER, name=DOMAIN)
        self.storage = storage
        self.objects: dict[str, TrackedObject] = {}
        self.pending_tags: dict[str, PendingTag] = {}
        self.settings = IntegrationSettings(
            default_due_soon_threshold_days=DEFAULT_DUE_SOON_THRESHOLD_DAYS,
            show_inactive_objects=DEFAULT_SHOW_INACTIVE_OBJECTS,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Load integration data from storage."""
        raw = await self.storage.async_load()
        self.objects = {
            object_id: TrackedObject.from_dict(data)
            for object_id, data in raw["objects"].items()
        }
        self.pending_tags = {
            tag_id: PendingTag.from_dict(data)
            for tag_id, data in raw["pending_tags"].items()
        }
        self.settings = IntegrationSettings.from_dict(raw["settings"])

        return self._snapshot()

    async def async_save(self) -> None:
        """Persist current state to storage and refresh listeners."""
        await self.storage.async_save(self.objects, self.pending_tags, self.settings)
        self.async_set_updated_data(self._snapshot())

    def get_object(self, object_id: str) -> TrackedObject | None:
        """Return a tracked object by its object ID."""
        return self.objects.get(object_id)

    def get_object_by_tag(self, tag_id: str) -> TrackedObject | None:
        """Return a tracked object by its tag ID."""
        for obj in self.objects.values():
            if obj.tag_id == tag_id:
                return obj
        return None

    async def async_create_object(
        self,
        *,
        name: str,
        tag_id: str,
        interval_value: int,
        interval_unit: str,
        notes: str | None = None,
        icon: str | None = None,
        category: str | None = None,
        due_soon_threshold_days: int | None = None,
        active: bool = True,
        last_reset_at: str | None = None,
    ) -> TrackedObject:
        """Create a new tracked object."""
        self._validate_interval(interval_value, interval_unit)
        self._ensure_tag_is_unique(tag_id)

        now = utc_now_iso()
        object_id = uuid4().hex
        obj = TrackedObject(
            id=object_id,
            name=name,
            tag_id=tag_id,
            interval_value=interval_value,
            interval_unit=interval_unit,
            created_at=now,
            last_reset_at=last_reset_at or now,
            notes=notes,
            icon=icon,
            category=category,
            due_soon_threshold_days=due_soon_threshold_days,
            active=active,
        )

        self.objects[object_id] = obj
        self.pending_tags.pop(tag_id, None)
        await self.async_save()
        return obj

    async def async_update_object(self, object_id: str, **changes: Any) -> TrackedObject:
        """Update an existing tracked object."""
        obj = self._require_object(object_id)

        if "interval_value" in changes or "interval_unit" in changes:
            self._validate_interval(
                changes.get("interval_value", obj.interval_value),
                changes.get("interval_unit", obj.interval_unit),
            )

        if "tag_id" in changes and changes["tag_id"] != obj.tag_id:
            self._ensure_tag_is_unique(changes["tag_id"], exclude_object_id=object_id)
            self.pending_tags.pop(changes["tag_id"], None)

        updated = replace(obj, **changes)
        self.objects[object_id] = updated
        await self.async_save()
        return updated

    async def async_delete_object(self, object_id: str) -> None:
        """Delete a tracked object."""
        self._require_object(object_id)
        self.objects.pop(object_id)
        await self.async_save()

    async def async_reset_object(
        self, object_id: str, *, reset_at: str | None = None
    ) -> TrackedObject:
        """Reset the timer for a tracked object."""
        obj = self._require_object(object_id)
        updated = replace(obj, last_reset_at=reset_at or utc_now_iso())
        self.objects[object_id] = updated
        await self.async_save()
        return updated

    async def async_upsert_pending_tag(
        self, tag_id: str, *, source_device: str | None = None
    ) -> PendingTag:
        """Create or update a pending tag entry."""
        existing = self.pending_tags.get(tag_id)
        now = utc_now_iso()

        if existing is None:
            pending = PendingTag(
                tag_id=tag_id,
                first_seen_at=now,
                last_seen_at=now,
                scan_count=1,
                source_device=source_device,
            )
        else:
            pending = replace(
                existing,
                last_seen_at=now,
                scan_count=existing.scan_count + 1,
                source_device=source_device or existing.source_device,
            )

        self.pending_tags[tag_id] = pending
        await self.async_save()
        return pending

    async def async_dismiss_pending_tag(self, tag_id: str) -> None:
        """Dismiss a pending tag if it exists."""
        if tag_id in self.pending_tags:
            self.pending_tags.pop(tag_id)
            await self.async_save()

    def get_object_status(self, obj: TrackedObject) -> str:
        """Return the derived status for a tracked object."""
        if not obj.active:
            return STATUS_HEALTHY

        now = datetime.now(UTC)
        next_due = self.get_next_due_at(obj)
        if now > next_due:
            return STATUS_OVERDUE
        if now == next_due:
            return STATUS_DUE_NOW

        remaining = next_due - now
        threshold_days = (
            obj.due_soon_threshold_days
            if obj.due_soon_threshold_days is not None
            else self.settings.default_due_soon_threshold_days
        )
        if remaining <= timedelta(days=threshold_days):
            return STATUS_DUE_SOON

        return STATUS_HEALTHY

    def get_next_due_at(self, obj: TrackedObject) -> datetime:
        """Return the next due datetime for a tracked object."""
        last_reset = self._parse_utc_iso(obj.last_reset_at)

        if obj.interval_unit == UNIT_DAY:
            return last_reset + timedelta(days=obj.interval_value)
        if obj.interval_unit == UNIT_WEEK:
            return last_reset + timedelta(weeks=obj.interval_value)
        if obj.interval_unit == UNIT_MONTH:
            return self._add_months(last_reset, obj.interval_value)

        raise ValueError(f"Unsupported interval unit: {obj.interval_unit}")

    def get_elapsed_duration(self, obj: TrackedObject) -> timedelta:
        """Return time elapsed since the last reset."""
        return datetime.now(UTC) - self._parse_utc_iso(obj.last_reset_at)

    def get_remaining_duration(self, obj: TrackedObject) -> timedelta:
        """Return time remaining until next due."""
        return self.get_next_due_at(obj) - datetime.now(UTC)

    def get_overdue_duration(self, obj: TrackedObject) -> timedelta:
        """Return time overdue, or zero when not overdue."""
        overdue = datetime.now(UTC) - self.get_next_due_at(obj)
        if overdue.total_seconds() < 0:
            return timedelta(0)
        return overdue

    def _snapshot(self) -> dict[str, Any]:
        """Return the current state snapshot."""
        return {
            "objects": self.objects,
            "pending_tags": self.pending_tags,
            "settings": self.settings,
        }

    def _require_object(self, object_id: str) -> TrackedObject:
        """Return a tracked object or raise if it does not exist."""
        obj = self.objects.get(object_id)
        if obj is None:
            raise ValueError(f"Unknown object_id: {object_id}")
        return obj

    def _ensure_tag_is_unique(
        self, tag_id: str, *, exclude_object_id: str | None = None
    ) -> None:
        """Ensure a tag is not already assigned to another tracked object."""
        for object_id, obj in self.objects.items():
            if object_id == exclude_object_id:
                continue
            if obj.tag_id == tag_id:
                raise ValueError(f"Tag already assigned: {tag_id}")

    def _validate_interval(self, interval_value: int, interval_unit: str) -> None:
        """Validate interval fields."""
        if interval_value < 1:
            raise ValueError("interval_value must be greater than zero")
        if interval_unit not in VALID_INTERVAL_UNITS:
            raise ValueError(f"Invalid interval_unit: {interval_unit}")

    @staticmethod
    def _parse_utc_iso(value: str) -> datetime:
        """Parse a stored UTC ISO-8601 timestamp."""
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)

    @staticmethod
    def _add_months(value: datetime, months: int) -> datetime:
        """Add calendar months to a datetime."""
        month_index = (value.month - 1) + months
        year = value.year + month_index // 12
        month = month_index % 12 + 1
        day = min(value.day, monthrange(year, month)[1])
        return value.replace(year=year, month=month, day=day)
