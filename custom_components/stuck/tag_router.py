"""Tag scan routing for the Stuck integration."""

from __future__ import annotations

import logging
from typing import Any

from .coordinator import StuckCoordinator
from .models import PendingTag, TrackedObject

_LOGGER = logging.getLogger(__name__)


class StuckTagRouter:
    """Resolve tag scans into known-object or pending-tag paths."""

    def __init__(self, coordinator: StuckCoordinator) -> None:
        """Initialize the tag router."""
        self.coordinator = coordinator

    async def async_handle_tag_scan(
        self,
        tag_id: str,
        *,
        source_device: str | None = None,
        tag_entity_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle a tag scan and return a routing result."""
        obj = self.coordinator.get_object_by_tag(tag_id)
        if obj is not None:
            _LOGGER.debug("Resolved known tag %s to object %s", tag_id, obj.id)
            return self._known_result(self.coordinator, obj, source_device=source_device)

        pending = await self.coordinator.async_upsert_pending_tag(
            tag_id,
            source_device=source_device,
            tag_entity_id=tag_entity_id,
        )
        _LOGGER.debug("Tracked unknown tag %s as pending", tag_id)
        return self._pending_result(pending)

    @staticmethod
    def _known_result(
        coordinator: StuckCoordinator,
        obj: TrackedObject,
        *,
        source_device: str | None = None,
    ) -> dict[str, Any]:
        """Return result payload for a known tag."""
        return {
            "kind": "known",
            "object_id": obj.id,
            "tag_id": obj.tag_id,
            "name": obj.name,
            "status": coordinator.get_object_status(obj),
            "object_url": coordinator.get_object_url(obj),
            "source_device": source_device,
        }

    @staticmethod
    def _pending_result(pending: PendingTag) -> dict[str, Any]:
        """Return result payload for an unknown tag."""
        return {
            "kind": "pending",
            "tag_id": pending.tag_id,
            "first_seen_at": pending.first_seen_at,
            "last_seen_at": pending.last_seen_at,
            "scan_count": pending.scan_count,
            "source_device": pending.source_device,
            "tag_entity_id": pending.tag_entity_id,
        }
