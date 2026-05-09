"""Storage layer for the Stuck integration."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DEFAULT_DUE_SOON_THRESHOLD_DAYS,
    DEFAULT_SHOW_INACTIVE_OBJECTS,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .models import IntegrationSettings, OnboardingState, PendingTag, TrackedObject


class StuckStorage:
    """Persist and load Stuck integration data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize storage."""
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def async_load(self) -> dict[str, Any]:
        """Load stored data or return defaults."""
        data = await self._store.async_load()
        if data is None:
            return self._default_data()

        return {
            "objects": data.get("objects", {}),
            "pending_tags": data.get("pending_tags", {}),
            "settings": {
                "default_due_soon_threshold_days": data.get("settings", {}).get(
                    "default_due_soon_threshold_days",
                    DEFAULT_DUE_SOON_THRESHOLD_DAYS,
                ),
                "show_inactive_objects": data.get("settings", {}).get(
                    "show_inactive_objects",
                    DEFAULT_SHOW_INACTIVE_OBJECTS,
                ),
            },
            "onboarding": data.get("onboarding", {}),
        }

    async def async_save(
        self,
        objects: dict[str, TrackedObject],
        pending_tags: dict[str, PendingTag],
        settings: IntegrationSettings,
        onboarding: OnboardingState,
    ) -> None:
        """Save the current integration state."""
        payload = {
            "objects": {object_id: obj.to_dict() for object_id, obj in objects.items()},
            "pending_tags": {
                tag_id: pending.to_dict() for tag_id, pending in pending_tags.items()
            },
            "settings": settings.to_dict(),
            "onboarding": onboarding.to_dict(),
        }
        await self._store.async_save(payload)

    @staticmethod
    def _default_data() -> dict[str, Any]:
        """Return default storage contents."""
        return {
            "objects": {},
            "pending_tags": {},
            "settings": {
                "default_due_soon_threshold_days": DEFAULT_DUE_SOON_THRESHOLD_DAYS,
                "show_inactive_objects": DEFAULT_SHOW_INACTIVE_OBJECTS,
            },
            "onboarding": {},
        }
