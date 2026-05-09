"""Data models for the Stuck integration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class TrackedObject:
    """Represents a physical object tracked by an NFC tag."""

    id: str
    name: str
    tag_id: str
    interval_value: int
    interval_unit: str
    created_at: str
    last_reset_at: str
    notes: str | None = None
    icon: str | None = None
    category: str | None = None
    due_soon_threshold_days: int | None = None
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize the tracked object to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrackedObject":
        """Create a tracked object from stored data."""
        return cls(**data)


@dataclass(slots=True)
class PendingTag:
    """Represents a tag seen by the system but not yet assigned."""

    tag_id: str
    first_seen_at: str
    last_seen_at: str
    scan_count: int = 1
    source_device: str | None = None
    tag_entity_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the pending tag to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PendingTag":
        """Create a pending tag from stored data."""
        return cls(**data)


@dataclass(slots=True)
class IntegrationSettings:
    """Represents global settings for the Stuck integration."""

    default_due_soon_threshold_days: int = 3
    show_inactive_objects: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize the settings to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IntegrationSettings":
        """Create settings from stored data."""
        return cls(**data)


@dataclass(slots=True)
class OnboardingState:
    """Represents UI flow state owned by the Stuck integration."""

    mode: str = "idle"
    selected_tag_id: str | None = None
    selected_tag_entity_id: str | None = None
    return_path: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize onboarding state to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OnboardingState":
        """Create onboarding state from stored data."""
        return cls(**data)


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
