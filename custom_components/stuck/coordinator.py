"""Coordinator for the Stuck integration."""

from __future__ import annotations

import logging
from calendar import monthrange
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_DEFAULT_DUE_SOON_THRESHOLD_DAYS,
    CONF_SHOW_INACTIVE_OBJECTS,
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
from .models import IntegrationSettings, OnboardingState, PendingTag, TrackedObject, utc_now_iso
from .storage import StuckStorage

_LOGGER = logging.getLogger(__name__)


class StuckCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate in-memory state for the Stuck integration."""

    def __init__(
        self,
        hass: HomeAssistant,
        storage: StuckStorage,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, logger=_LOGGER, name=DOMAIN)
        self.storage = storage
        self._config_entry = config_entry
        self._config_entry_id = config_entry.entry_id if config_entry else ""
        self.objects: dict[str, TrackedObject] = {}
        self.pending_tags: dict[str, PendingTag] = {}
        self.settings = IntegrationSettings(
            default_due_soon_threshold_days=DEFAULT_DUE_SOON_THRESHOLD_DAYS,
            show_inactive_objects=DEFAULT_SHOW_INACTIVE_OBJECTS,
        )
        self.onboarding = OnboardingState()

    @property
    def config_entry_id(self) -> str:
        """Config entry id for this coordinator instance."""
        return self._config_entry_id

    def _apply_config_entry_settings(self) -> None:
        """Overlay config entry data/options onto integration settings."""
        if self._config_entry is None:
            return
        merged = {**self._config_entry.data, **self._config_entry.options}
        threshold = merged.get(CONF_DEFAULT_DUE_SOON_THRESHOLD_DAYS)
        show_inactive = merged.get(CONF_SHOW_INACTIVE_OBJECTS)
        updates: dict[str, Any] = {}
        if threshold is not None:
            updates["default_due_soon_threshold_days"] = int(threshold)
        if show_inactive is not None:
            updates["show_inactive_objects"] = bool(show_inactive)
        if updates:
            self.settings = replace(self.settings, **updates)

    def list_tracked_objects_for_ui(self) -> list[TrackedObject]:
        """Tracked objects exposed as entities and in dashboard inventory."""
        objects = sorted(self.objects.values(), key=lambda item: item.name.lower())
        if self.settings.show_inactive_objects:
            return list(objects)
        return [obj for obj in objects if obj.active]

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
        self._apply_config_entry_settings()
        self.onboarding = OnboardingState.from_dict(raw.get("onboarding", {}))

        return self._snapshot()

    async def async_save(self) -> None:
        """Persist current state to storage and refresh listeners."""
        self._apply_config_entry_settings()
        await self.storage.async_save(self.objects, self.pending_tags, self.settings, self.onboarding)
        self.async_set_updated_data(self._snapshot())

    def get_object(self, object_id: str) -> TrackedObject | None:
        """Return a tracked object by its object ID."""
        return self.objects.get(object_id)

    async def async_set_onboarding_mode(
        self,
        mode: str,
        *,
        return_path: str | None = None,
    ) -> None:
        """Set the current onboarding mode."""
        self.onboarding = replace(
            self.onboarding,
            mode=mode,
            return_path=return_path if return_path is not None else self.onboarding.return_path,
            updated_at=utc_now_iso(),
        )
        await self.async_save()

    async def async_clear_onboarding_mode(self) -> None:
        """Return onboarding mode to idle."""
        self.onboarding = replace(
            self.onboarding,
            mode='idle',
            updated_at=utc_now_iso(),
        )
        await self.async_save()

    async def async_select_existing_tag(
        self,
        *,
        tag_id: str | None = None,
        tag_entity_id: str | None = None,
        source: str = 'existing',
    ) -> None:
        """Select an existing tag for the onboarding flow."""
        resolved_tag_id = self._normalize_tag_identifier(tag_id or tag_entity_id)
        selected_entity_id = tag_entity_id

        if selected_entity_id is None and resolved_tag_id:
            selected_entity_id = self._find_tag_entity_id_by_normalized_tag_id(resolved_tag_id)

        self.onboarding = replace(
            self.onboarding,
            selected_tag_id=resolved_tag_id or None,
            selected_tag_entity_id=selected_entity_id,
            selected_tag_source=source,
            updated_at=utc_now_iso(),
        )
        await self.async_save()

    async def async_clear_selected_existing_tag(self) -> None:
        """Clear the selected existing tag from onboarding state."""
        self.onboarding = replace(
            self.onboarding,
            selected_tag_id=None,
            selected_tag_entity_id=None,
            selected_tag_source=None,
            updated_at=utc_now_iso(),
        )
        await self.async_save()

    async def async_resume_latest_pending_tag_for_onboarding(self) -> PendingTag:
        """Promote the latest pending tag into onboarding selection state."""
        pending = self.get_latest_pending_tag()
        if pending is None:
            raise ValueError('No pending tags to resume')

        await self.async_select_existing_tag(
            tag_id=pending.tag_id,
            tag_entity_id=pending.tag_entity_id,
            source='pending',
        )
        await self.async_set_onboarding_mode('object_details')
        return pending

    async def async_finish_onboarding(
        self,
        *,
        name: str,
        interval_value: int,
        interval_unit: str,
        notes: str | None = None,
        icon: str | None = None,
        category: str | None = None,
        due_soon_threshold_days: int | None = None,
        active: bool = True,
        last_reset_at: str | None = None,
    ) -> TrackedObject:
        """Create a tracked object from the currently selected onboarding tag."""
        if not self.onboarding.selected_tag_id:
            raise ValueError('No onboarding tag is currently selected')

        obj = await self.async_create_object(
            name=name,
            tag_id=self.onboarding.selected_tag_id,
            interval_value=interval_value,
            interval_unit=interval_unit,
            notes=notes,
            icon=icon,
            category=category,
            due_soon_threshold_days=due_soon_threshold_days,
            active=active,
            last_reset_at=last_reset_at,
        )
        await self.async_clear_onboarding_mode()
        await self.async_clear_selected_existing_tag()
        return obj

    def get_object_by_tag(self, tag_id: str) -> TrackedObject | None:
        """Return a tracked object by its tag identifier or related tag entity ID."""
        normalized = self._normalize_tag_identifier(tag_id)
        for obj in self.objects.values():
            if self._normalize_tag_identifier(obj.tag_id) == normalized:
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
        self,
        tag_id: str,
        *,
        source_device: str | None = None,
        tag_entity_id: str | None = None,
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
                tag_entity_id=tag_entity_id,
            )
        else:
            pending = replace(
                existing,
                last_seen_at=now,
                scan_count=existing.scan_count + 1,
                source_device=source_device or existing.source_device,
                tag_entity_id=tag_entity_id or existing.tag_entity_id,
            )

        self.pending_tags[tag_id] = pending
        await self.async_save()
        return pending

    async def async_dismiss_pending_tag(self, tag_id: str) -> None:
        """Dismiss a pending tag if it exists."""
        if tag_id in self.pending_tags:
            self.pending_tags.pop(tag_id)
            await self.async_save()

    async def async_claim_pending_tag(
        self,
        *,
        tag_id: str,
        name: str,
        interval_value: int,
        interval_unit: str,
        notes: str | None = None,
        icon: str | None = None,
        category: str | None = None,
        due_soon_threshold_days: int | None = None,
        active: bool = True,
        last_reset_at: str | None = None,
    ) -> TrackedObject:
        """Turn a pending tag into a tracked object."""
        if tag_id not in self.pending_tags:
            raise ValueError(f"Pending tag not found: {tag_id}")

        return await self.async_create_object(
            name=name,
            tag_id=tag_id,
            interval_value=interval_value,
            interval_unit=interval_unit,
            notes=notes,
            icon=icon,
            category=category,
            due_soon_threshold_days=due_soon_threshold_days,
            active=active,
            last_reset_at=last_reset_at,
        )

    async def async_claim_latest_pending_tag(
        self,
        *,
        name: str,
        interval_value: int,
        interval_unit: str,
        notes: str | None = None,
        icon: str | None = None,
        category: str | None = None,
        due_soon_threshold_days: int | None = None,
        active: bool = True,
        last_reset_at: str | None = None,
    ) -> TrackedObject:
        """Turn the most recently seen pending tag into a tracked object."""
        pending = self.get_latest_pending_tag()
        if pending is None:
            raise ValueError("No pending tags to claim")

        return await self.async_claim_pending_tag(
            tag_id=pending.tag_id,
            name=name,
            interval_value=interval_value,
            interval_unit=interval_unit,
            notes=notes,
            icon=icon,
            category=category,
            due_soon_threshold_days=due_soon_threshold_days,
            active=active,
            last_reset_at=last_reset_at,
        )

    def get_latest_pending_tag(self) -> PendingTag | None:
        """Return the most recently seen pending tag."""
        pending_tags = self.get_pending_tags()
        if not pending_tags:
            return None
        return pending_tags[0]

    def get_pending_tags(self) -> list[PendingTag]:
        """Return pending tags sorted by most recently seen first."""
        return sorted(
            self.pending_tags.values(),
            key=lambda pending: self._parse_utc_iso(pending.last_seen_at),
            reverse=True,
        )

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

    def get_object_url(self, obj: TrackedObject) -> str:
        """Return a dashboard URL for a tracked object."""
        slug = obj.id.lower()
        return f"/stuck-dashboard?stuck_object={slug}"

    def get_tag_inventory(self) -> dict[str, list[dict[str, Any]]]:
        """Return Home Assistant tag inventory split into available and assigned buckets."""
        entity_registry = async_get_entity_registry(self.hass)
        tags: list[dict[str, Any]] = []
        seen_object_ids: set[str] = set()

        for entry in entity_registry.entities.values():
            if entry.entity_id.split('.', 1)[0] != 'tag':
                continue

            assigned_object = self.get_object_by_tag(entry.entity_id)
            if assigned_object is not None:
                seen_object_ids.add(assigned_object.id)
            state = self.hass.states.get(entry.entity_id)
            tags.append(
                {
                    'entity_id': entry.entity_id,
                    'name': entry.name or entry.original_name or entry.entity_id,
                    'tag_id': self._normalize_tag_identifier(entry.entity_id),
                    'last_scanned': None if state is None else state.state,
                    'assigned_to_stuck': assigned_object is not None,
                    'object_id': None if assigned_object is None else assigned_object.id,
                    'object_name': None if assigned_object is None else assigned_object.name,
                    'object_status': None if assigned_object is None else self.get_object_status(assigned_object),
                    'object_url': None if assigned_object is None else self.get_object_url(assigned_object),
                }
            )

        for obj in sorted(self.objects.values(), key=lambda item: item.name.lower()):
            if obj.id in seen_object_ids:
                continue
            tags.append(
                {
                    'entity_id': None,
                    'name': obj.name,
                    'tag_id': obj.tag_id,
                    'last_scanned': None,
                    'assigned_to_stuck': True,
                    'object_id': obj.id,
                    'object_name': obj.name,
                    'object_status': self.get_object_status(obj),
                    'object_url': self.get_object_url(obj),
                }
            )

        tags.sort(key=lambda item: (item['name'] or '').lower())
        return {
            'available_tags': [item for item in tags if not item['assigned_to_stuck']],
            'assigned_tags': [item for item in tags if item['assigned_to_stuck']],
        }

    def get_onboarding_state(self) -> dict[str, Any]:
        """Return dashboard-friendly onboarding state."""
        selected_tag = self.get_selected_existing_tag_details()
        return {
            'mode': self.onboarding.mode,
            'selected_tag_id': self.onboarding.selected_tag_id,
            'selected_tag_entity_id': self.onboarding.selected_tag_entity_id,
            'selected_tag_source': self.onboarding.selected_tag_source,
            'selected_tag_name': None if selected_tag is None else selected_tag.get('name'),
            'return_path': self.onboarding.return_path,
            'updated_at': self.onboarding.updated_at,
            'has_pending_tags': bool(self.pending_tags),
            'pending_count': len(self.pending_tags),
            'can_resume_pending': bool(self.pending_tags),
            'has_selected_tag': bool(self.onboarding.selected_tag_id or self.onboarding.selected_tag_entity_id),
        }

    def get_selected_existing_tag_details(self) -> dict[str, Any] | None:
        """Return the currently selected existing-tag details, if any."""
        selected_tag_id = self.onboarding.selected_tag_id
        selected_entity_id = self.onboarding.selected_tag_entity_id
        if not selected_tag_id and not selected_entity_id:
            return None

        normalized = self._normalize_tag_identifier(selected_tag_id or selected_entity_id)
        inventory = self.get_tag_inventory()
        for tag in inventory['available_tags']:
            if self._normalize_tag_identifier(tag.get('tag_id') or tag.get('entity_id')) == normalized:
                return tag
        return {
            'name': selected_entity_id or selected_tag_id,
            'entity_id': selected_entity_id,
            'tag_id': selected_tag_id,
        }

    def _tracked_object_row(self, obj: TrackedObject) -> dict[str, Any]:
        """Build a dashboard-friendly dict for one tracked object."""
        next_due_at = self.get_next_due_at(obj)
        status = self.get_object_status(obj)
        remaining = self.get_remaining_duration(obj)
        elapsed = self.get_elapsed_duration(obj)
        overdue = self.get_overdue_duration(obj)
        return {
            'object_id': obj.id,
            'name': obj.name,
            'tag_id': obj.tag_id,
            'interval_value': obj.interval_value,
            'interval_unit': obj.interval_unit,
            'notes': obj.notes,
            'icon': obj.icon,
            'category': obj.category,
            'active': obj.active,
            'created_at': obj.created_at,
            'created_at_label': self._format_datetime_label(obj.created_at),
            'last_reset_at': obj.last_reset_at,
            'last_reset_label': self._format_relative_label(
                self._parse_utc_iso(obj.last_reset_at), prefix='Last reset'
            ),
            'status': status,
            'status_label': self._format_status_label(status),
            'next_due_at': next_due_at.isoformat(),
            'next_due_label': self._format_relative_label(next_due_at, prefix='Due'),
            'time_remaining': str(remaining),
            'time_remaining_label': self._format_duration_label(remaining, future=True),
            'time_elapsed': str(elapsed),
            'time_elapsed_label': self._format_duration_label(elapsed, past=True),
            'overdue_duration': str(overdue),
            'overdue_duration_label': self._format_duration_label(overdue, past=True),
            'status_entity_id': self._tracked_object_entity_id('sensor', obj, 'status'),
            'next_due_entity_id': self._tracked_object_entity_id('sensor', obj, 'next_due'),
            'time_remaining_entity_id': self._tracked_object_entity_id(
                'sensor', obj, 'time_remaining'
            ),
            'time_elapsed_entity_id': self._tracked_object_entity_id(
                'sensor', obj, 'time_elapsed'
            ),
            'overdue_entity_id': self._tracked_object_entity_id('binary_sensor', obj, 'overdue'),
            'reset_entity_id': self._tracked_object_entity_id('button', obj, 'reset'),
            'object_url': self.get_object_url(obj),
        }

    def get_tracked_object_inventory(self) -> list[dict[str, Any]]:
        """Return tracked objects as a dashboard-friendly inventory list."""
        return [
            self._tracked_object_row(obj) for obj in self.list_tracked_objects_for_ui()
        ]

    def build_known_tag_scan_payload(
        self, obj: TrackedObject, *, source_device: str | None = None
    ) -> dict[str, Any]:
        """Return bus event payload for a known tag scan (includes live dashboard fields)."""
        row = self._tracked_object_row(obj)
        return {
            'kind': 'known',
            'config_entry_id': self._config_entry_id,
            'source_device': source_device,
            **row,
        }

    def _tracked_object_entity_id(self, domain: str, obj: TrackedObject, suffix: str) -> str:
        """Resolve entity id from the registry when possible, else a name-based guess."""
        if self._config_entry_id:
            unique_id = f"{self._config_entry_id}_{obj.id}_{suffix}"
            er = async_get_entity_registry(self.hass)
            resolved = er.async_get_entity_id(domain, DOMAIN, unique_id)
            if resolved is not None:
                return resolved
        return f"{domain}.{_slugify(obj.name)}_{suffix}"

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
            "onboarding": self.onboarding,
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

    def _find_tag_entity_id_by_normalized_tag_id(self, tag_id: str) -> str | None:
        """Find a tag.* entity ID by normalized tag ID."""
        entity_registry = async_get_entity_registry(self.hass)
        for entry in entity_registry.entities.values():
            if entry.entity_id.split('.', 1)[0] != 'tag':
                continue
            if self._normalize_tag_identifier(entry.entity_id) == tag_id:
                return entry.entity_id
        return None

    @staticmethod
    def _normalize_tag_identifier(tag_id: str | None) -> str:
        """Normalize tag identifiers so raw tag IDs and tag.* entity IDs can match."""
        if not tag_id:
            return ''
        if tag_id.startswith('tag.'):
            return tag_id.split('.', 1)[1]
        return tag_id

    @staticmethod
    def _format_status_label(status: str) -> str:
        """Return a friendlier human label for object status."""
        return status.replace('_', ' ').title()

    @staticmethod
    def _format_datetime_label(value: str) -> str:
        """Return a compact ISO-derived display label."""
        dt = datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(UTC)
        return dt.strftime('%Y-%m-%d %H:%M UTC')

    @staticmethod
    def _format_relative_label(value: datetime, *, prefix: str) -> str:
        """Return a human-readable relative datetime label."""
        now = datetime.now(UTC)
        delta = value - now
        if abs(delta.total_seconds()) < 60:
            return f'{prefix} now'
        if delta.total_seconds() > 0:
            return f'{prefix} in {StuckCoordinator._humanize_duration(delta)}'
        return f'{prefix} {StuckCoordinator._humanize_duration(-delta)} ago'

    @staticmethod
    def _format_duration_label(
        value: timedelta,
        *,
        future: bool = False,
        past: bool = False,
    ) -> str:
        """Return a human-readable duration label."""
        if value.total_seconds() < 0:
            value = -value
        human = StuckCoordinator._humanize_duration(value)
        if future:
            return f'in {human}'
        if past:
            return f'{human} ago'
        return human

    @staticmethod
    def _humanize_duration(value: timedelta) -> str:
        """Return a short human-friendly duration."""
        total_seconds = int(value.total_seconds())
        if total_seconds <= 0:
            return '0 minutes'

        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, _ = divmod(remainder, 60)

        parts: list[str] = []
        if days:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours and len(parts) < 2:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes and len(parts) < 2:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

        return ', '.join(parts[:2]) or '0 minutes'


def _slugify(value: str) -> str:
    """Create a Home Assistant style slug from an object name."""
    return value.strip().lower().replace(' ', '_').replace('-', '_')
