"""Tag scan routing for the Stuck integration."""

from __future__ import annotations

import logging
from typing import Any

from .coordinator import StuckCoordinator
from .models import PendingTag

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
            return self.coordinator.build_known_tag_scan_payload(
                obj, source_device=source_device
            )

        pending = await self.coordinator.async_upsert_pending_tag(
            tag_id,
            source_device=source_device,
            tag_entity_id=tag_entity_id,
        )
        _LOGGER.debug("Tracked unknown tag %s as pending", tag_id)
        return self._pending_result(pending)

    def _pending_result(self, pending: PendingTag) -> dict[str, Any]:
        """Return result payload for an unknown tag."""
        return {
            "kind": "pending",
            "config_entry_id": self.coordinator.config_entry_id,
            "tag_id": pending.tag_id,
            "first_seen_at": pending.first_seen_at,
            "last_seen_at": pending.last_seen_at,
            "scan_count": pending.scan_count,
            "source_device": pending.source_device,
            "tag_entity_id": pending.tag_entity_id,
        }
