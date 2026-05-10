"""Service registration for the Stuck integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_INTERVAL_UNIT,
    ATTR_INTERVAL_VALUE,
    ATTR_MODE,
    ATTR_OBJECT_ID,
    ATTR_RETURN_PATH,
    ATTR_SELECTED_TAG_ENTITY_ID,
    ATTR_SELECTED_TAG_ID,
    ATTR_SELECTED_TAG_SOURCE,
    ATTR_TAG_ENTITY_ID,
    ATTR_TAG_ID,
    DATA_COORDINATOR,
    DOMAIN,
    SERVICE_ASSOCIATE_EXISTING_TAG,
    SERVICE_ASSOCIATE_EXISTING_TAG_FROM_HELPERS,
    SERVICE_ASSOCIATE_SELECTED_EXISTING_TAG_FROM_HELPERS,
    SERVICE_CLAIM_LATEST_PENDING_TAG,
    SERVICE_CLAIM_LATEST_PENDING_TAG_FROM_HELPERS,
    SERVICE_CLAIM_PENDING_TAG,
    SERVICE_CLEAR_ONBOARDING_MODE,
    SERVICE_CLEAR_SELECTED_EXISTING_TAG,
    SERVICE_CREATE_OBJECT,
    SERVICE_DELETE_OBJECT,
    SERVICE_DISMISS_PENDING_TAG,
    SERVICE_FINISH_ONBOARDING,
    SERVICE_RESET_OBJECT,
    SERVICE_RESUME_LATEST_PENDING_TAG,
    SERVICE_SELECT_EXISTING_TAG,
    SERVICE_SET_ONBOARDING_MODE,
    SERVICE_UPDATE_OBJECT,
    VALID_INTERVAL_UNITS,
)

_LOGGER = logging.getLogger(__name__)


async def _async_reload_entry(hass: HomeAssistant, config_entry_id: str) -> None:
    """Reload a config entry after structure-changing operations."""
    entry = hass.config_entries.async_get_entry(config_entry_id)
    if entry is None:
        return
    if entry.state not in {ConfigEntryState.LOADED, ConfigEntryState.SETUP_RETRY}:
        return
    await asyncio.sleep(0)
    await hass.config_entries.async_reload(config_entry_id)

SERVICE_CREATE_OBJECT_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required("name"): cv.string,
        vol.Required(ATTR_TAG_ID): cv.string,
        vol.Required(ATTR_INTERVAL_VALUE): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required(ATTR_INTERVAL_UNIT): vol.In(VALID_INTERVAL_UNITS),
        vol.Optional("notes"): vol.Any(None, cv.string),
        vol.Optional("icon"): vol.Any(None, cv.string),
        vol.Optional("category"): vol.Any(None, cv.string),
        vol.Optional("due_soon_threshold_days"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1))),
        vol.Optional("active", default=True): cv.boolean,
        vol.Optional("last_reset_at"): vol.Any(None, cv.string),
    }
)

SERVICE_UPDATE_OBJECT_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required(ATTR_OBJECT_ID): cv.string,
        vol.Optional("name"): cv.string,
        vol.Optional(ATTR_TAG_ID): cv.string,
        vol.Optional(ATTR_INTERVAL_VALUE): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional(ATTR_INTERVAL_UNIT): vol.In(VALID_INTERVAL_UNITS),
        vol.Optional("notes"): vol.Any(None, cv.string),
        vol.Optional("icon"): vol.Any(None, cv.string),
        vol.Optional("category"): vol.Any(None, cv.string),
        vol.Optional("due_soon_threshold_days"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1))),
        vol.Optional("active"): cv.boolean,
        vol.Optional("last_reset_at"): vol.Any(None, cv.string),
    }
)

SERVICE_DELETE_OBJECT_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required(ATTR_OBJECT_ID): cv.string,
    }
)

SERVICE_RESET_OBJECT_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Exclusive(ATTR_OBJECT_ID, "target"): cv.string,
        vol.Exclusive(ATTR_TAG_ID, "target"): cv.string,
        vol.Optional("reset_at"): vol.Any(None, cv.string),
    }
)

SERVICE_DISMISS_PENDING_TAG_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required(ATTR_TAG_ID): cv.string,
    }
)

SERVICE_CLAIM_PENDING_TAG_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required(ATTR_TAG_ID): cv.string,
        vol.Required("name"): cv.string,
        vol.Required(ATTR_INTERVAL_VALUE): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required(ATTR_INTERVAL_UNIT): vol.In(VALID_INTERVAL_UNITS),
        vol.Optional("notes"): vol.Any(None, cv.string),
        vol.Optional("icon"): vol.Any(None, cv.string),
        vol.Optional("category"): vol.Any(None, cv.string),
        vol.Optional("due_soon_threshold_days"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1))),
        vol.Optional("active", default=True): cv.boolean,
        vol.Optional("last_reset_at"): vol.Any(None, cv.string),
    }
)

SERVICE_CLAIM_LATEST_PENDING_TAG_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required("name"): cv.string,
        vol.Required(ATTR_INTERVAL_VALUE): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required(ATTR_INTERVAL_UNIT): vol.In(VALID_INTERVAL_UNITS),
        vol.Optional("notes"): vol.Any(None, cv.string),
        vol.Optional("icon"): vol.Any(None, cv.string),
        vol.Optional("category"): vol.Any(None, cv.string),
        vol.Optional("due_soon_threshold_days"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1))),
        vol.Optional("active", default=True): cv.boolean,
        vol.Optional("last_reset_at"): vol.Any(None, cv.string),
    }
)

SERVICE_CLAIM_LATEST_PENDING_TAG_FROM_HELPERS_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Optional("notes"): vol.Any(None, cv.string),
        vol.Optional("icon"): vol.Any(None, cv.string),
        vol.Optional("category"): vol.Any(None, cv.string),
        vol.Optional("due_soon_threshold_days"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1))),
        vol.Optional("active", default=True): cv.boolean,
        vol.Optional("last_reset_at"): vol.Any(None, cv.string),
        vol.Optional("clear_name_helper", default=True): cv.boolean,
    }
)

SERVICE_ASSOCIATE_EXISTING_TAG_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Exclusive(ATTR_TAG_ID, "tag_target"): cv.string,
        vol.Exclusive(ATTR_TAG_ENTITY_ID, "tag_target"): cv.string,
        vol.Required("name"): cv.string,
        vol.Required(ATTR_INTERVAL_VALUE): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required(ATTR_INTERVAL_UNIT): vol.In(VALID_INTERVAL_UNITS),
        vol.Optional("notes"): vol.Any(None, cv.string),
        vol.Optional("icon"): vol.Any(None, cv.string),
        vol.Optional("category"): vol.Any(None, cv.string),
        vol.Optional("due_soon_threshold_days"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1))),
        vol.Optional("active", default=True): cv.boolean,
        vol.Optional("last_reset_at"): vol.Any(None, cv.string),
    }
)

SERVICE_ASSOCIATE_EXISTING_TAG_FROM_HELPERS_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Exclusive(ATTR_TAG_ID, "tag_target"): cv.string,
        vol.Exclusive(ATTR_TAG_ENTITY_ID, "tag_target"): cv.string,
        vol.Optional("notes"): vol.Any(None, cv.string),
        vol.Optional("icon"): vol.Any(None, cv.string),
        vol.Optional("category"): vol.Any(None, cv.string),
        vol.Optional("due_soon_threshold_days"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1))),
        vol.Optional("active", default=True): cv.boolean,
        vol.Optional("last_reset_at"): vol.Any(None, cv.string),
        vol.Optional("clear_name_helper", default=True): cv.boolean,
    }
)

SERVICE_ASSOCIATE_SELECTED_EXISTING_TAG_FROM_HELPERS_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Optional("notes"): vol.Any(None, cv.string),
        vol.Optional("icon"): vol.Any(None, cv.string),
        vol.Optional("category"): vol.Any(None, cv.string),
        vol.Optional("due_soon_threshold_days"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1))),
        vol.Optional("active", default=True): cv.boolean,
        vol.Optional("last_reset_at"): vol.Any(None, cv.string),
        vol.Optional("clear_name_helper", default=True): cv.boolean,
    }
)

SERVICE_SET_ONBOARDING_MODE_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required(ATTR_MODE): cv.string,
        vol.Optional(ATTR_RETURN_PATH): vol.Any(None, cv.string),
    }
)

SERVICE_CLEAR_ONBOARDING_MODE_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
    }
)

SERVICE_SELECT_EXISTING_TAG_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Exclusive(ATTR_SELECTED_TAG_ID, "selected_tag"): cv.string,
        vol.Exclusive(ATTR_SELECTED_TAG_ENTITY_ID, "selected_tag"): cv.string,
        vol.Optional(ATTR_SELECTED_TAG_SOURCE, default="existing"): cv.string,
    }
)

SERVICE_CLEAR_SELECTED_EXISTING_TAG_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
    }
)

SERVICE_FINISH_ONBOARDING_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required("name"): cv.string,
        vol.Required(ATTR_INTERVAL_VALUE): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required(ATTR_INTERVAL_UNIT): vol.In(VALID_INTERVAL_UNITS),
        vol.Optional("notes"): vol.Any(None, cv.string),
        vol.Optional("icon"): vol.Any(None, cv.string),
        vol.Optional("category"): vol.Any(None, cv.string),
        vol.Optional("due_soon_threshold_days"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1))),
        vol.Optional("active", default=True): cv.boolean,
        vol.Optional("last_reset_at"): vol.Any(None, cv.string),
    }
)

SERVICE_RESUME_LATEST_PENDING_TAG_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
    }
)


async def async_register_services(hass: HomeAssistant) -> None:
    """Register Stuck services."""
    if hass.services.has_service(DOMAIN, SERVICE_CREATE_OBJECT):
        return

    async def _get_coordinator(config_entry_id: str):
        entry_data = hass.data[DOMAIN].get(config_entry_id)
        if entry_data is None:
            raise ValueError(f"Unknown config_entry_id: {config_entry_id}")
        return entry_data[DATA_COORDINATOR]

    async def handle_create_object(call: ServiceCall) -> None:
        """Handle object creation."""
        config_entry_id = call.data["config_entry_id"]
        coordinator = await _get_coordinator(config_entry_id)
        await coordinator.async_create_object(
            name=call.data["name"],
            tag_id=call.data[ATTR_TAG_ID],
            interval_value=call.data[ATTR_INTERVAL_VALUE],
            interval_unit=call.data[ATTR_INTERVAL_UNIT],
            notes=call.data.get("notes"),
            icon=call.data.get("icon"),
            category=call.data.get("category"),
            due_soon_threshold_days=call.data.get("due_soon_threshold_days"),
            active=call.data.get("active", True),
            last_reset_at=call.data.get("last_reset_at"),
        )
        await _async_reload_entry(hass, config_entry_id)

    async def handle_update_object(call: ServiceCall) -> None:
        """Handle object updates."""
        coordinator = await _get_coordinator(call.data["config_entry_id"])
        changes: dict[str, Any] = {
            key: value
            for key, value in call.data.items()
            if key not in {"config_entry_id", ATTR_OBJECT_ID}
        }
        await coordinator.async_update_object(call.data[ATTR_OBJECT_ID], **changes)

    async def handle_delete_object(call: ServiceCall) -> None:
        """Handle object deletion."""
        config_entry_id = call.data["config_entry_id"]
        coordinator = await _get_coordinator(config_entry_id)
        await coordinator.async_delete_object(call.data[ATTR_OBJECT_ID])
        await _async_reload_entry(hass, config_entry_id)

    async def handle_reset_object(call: ServiceCall) -> None:
        """Handle timer reset."""
        coordinator = await _get_coordinator(call.data["config_entry_id"])

        object_id = call.data.get(ATTR_OBJECT_ID)
        if object_id is None:
            tag_id = call.data.get(ATTR_TAG_ID)
            if tag_id is None:
                raise ValueError("Either object_id or tag_id is required")
            obj = coordinator.get_object_by_tag(tag_id)
            if obj is None:
                raise ValueError(f"Unknown tag_id: {tag_id}")
            object_id = obj.id

        await coordinator.async_reset_object(
            object_id, reset_at=call.data.get("reset_at")
        )

    async def handle_dismiss_pending_tag(call: ServiceCall) -> None:
        """Handle pending tag dismissal."""
        coordinator = await _get_coordinator(call.data["config_entry_id"])
        await coordinator.async_dismiss_pending_tag(call.data[ATTR_TAG_ID])

    async def handle_claim_pending_tag(call: ServiceCall) -> None:
        """Turn a pending tag into a tracked object."""
        config_entry_id = call.data["config_entry_id"]
        coordinator = await _get_coordinator(config_entry_id)
        await coordinator.async_claim_pending_tag(
            tag_id=call.data[ATTR_TAG_ID],
            name=call.data["name"],
            interval_value=call.data[ATTR_INTERVAL_VALUE],
            interval_unit=call.data[ATTR_INTERVAL_UNIT],
            notes=call.data.get("notes"),
            icon=call.data.get("icon"),
            category=call.data.get("category"),
            due_soon_threshold_days=call.data.get("due_soon_threshold_days"),
            active=call.data.get("active", True),
            last_reset_at=call.data.get("last_reset_at"),
        )
        await _async_reload_entry(hass, config_entry_id)

    async def handle_claim_latest_pending_tag(call: ServiceCall) -> None:
        """Turn the latest pending tag into a tracked object."""
        config_entry_id = call.data["config_entry_id"]
        coordinator = await _get_coordinator(config_entry_id)
        await coordinator.async_claim_latest_pending_tag(
            name=call.data["name"],
            interval_value=call.data[ATTR_INTERVAL_VALUE],
            interval_unit=call.data[ATTR_INTERVAL_UNIT],
            notes=call.data.get("notes"),
            icon=call.data.get("icon"),
            category=call.data.get("category"),
            due_soon_threshold_days=call.data.get("due_soon_threshold_days"),
            active=call.data.get("active", True),
            last_reset_at=call.data.get("last_reset_at"),
        )
        await _async_reload_entry(hass, config_entry_id)

    def _resolve_tag_id_from_inputs(
        coordinator,
        *,
        tag_id: str | None = None,
        tag_entity_id: str | None = None,
    ) -> str:
        if tag_id:
            return tag_id
        if not tag_entity_id:
            raise ValueError("Either tag_id or tag_entity_id is required")

        state = hass.states.get(tag_entity_id)
        if state is None:
            raise ValueError(f"Unknown tag entity: {tag_entity_id}")

        candidate = state.attributes.get("tag_id") or state.object_id
        if not candidate:
            raise ValueError(f"Unable to resolve tag_id from {tag_entity_id}")

        pending = coordinator.pending_tags.get(candidate)
        if pending is not None:
            pending.tag_entity_id = tag_entity_id
        return candidate

    def _read_onboarding_helpers() -> tuple[str, int, str]:
        name = hass.states.get("input_text.stuck_new_object_name")
        interval_value = hass.states.get("input_number.stuck_new_interval_value")
        interval_unit = hass.states.get("input_select.stuck_new_interval_unit")

        if name is None or not name.state.strip():
            raise ValueError("input_text.stuck_new_object_name is empty")
        if interval_value is None:
            raise ValueError("input_number.stuck_new_interval_value not found")
        if interval_unit is None:
            raise ValueError("input_select.stuck_new_interval_unit not found")

        return name.state.strip(), int(float(interval_value.state)), interval_unit.state

    def _read_selected_existing_tag(coordinator) -> str:
        selected = coordinator.onboarding.selected_tag_id
        selected_entity = coordinator.onboarding.selected_tag_entity_id
        if selected:
            return selected
        if selected_entity:
            return _resolve_tag_id_from_inputs(coordinator, tag_entity_id=selected_entity)
        raise ValueError("No existing HA tag is currently selected in onboarding state")

    async def _clear_name_helper() -> None:
        await hass.services.async_call(
            "input_text",
            "set_value",
            {
                "entity_id": "input_text.stuck_new_object_name",
                "value": "",
            },
            blocking=True,
        )

    async def handle_claim_latest_pending_tag_from_helpers(call: ServiceCall) -> None:
        """Claim the latest pending tag using dashboard helper values."""
        config_entry_id = call.data["config_entry_id"]
        coordinator = await _get_coordinator(config_entry_id)
        name, interval_value, interval_unit = _read_onboarding_helpers()

        await coordinator.async_claim_latest_pending_tag(
            name=name,
            interval_value=interval_value,
            interval_unit=interval_unit,
            notes=call.data.get("notes"),
            icon=call.data.get("icon"),
            category=call.data.get("category"),
            due_soon_threshold_days=call.data.get("due_soon_threshold_days"),
            active=call.data.get("active", True),
            last_reset_at=call.data.get("last_reset_at"),
        )

        if call.data.get("clear_name_helper", True):
            await _clear_name_helper()

        await coordinator.async_clear_onboarding_mode()
        await coordinator.async_clear_selected_existing_tag()
        await _async_reload_entry(hass, config_entry_id)

    async def handle_associate_existing_tag(call: ServiceCall) -> None:
        """Associate an existing Home Assistant tag with a new Stuck object."""
        config_entry_id = call.data["config_entry_id"]
        coordinator = await _get_coordinator(config_entry_id)
        resolved_tag_id = _resolve_tag_id_from_inputs(
            coordinator,
            tag_id=call.data.get(ATTR_TAG_ID),
            tag_entity_id=call.data.get(ATTR_TAG_ENTITY_ID),
        )

        await coordinator.async_create_object(
            name=call.data["name"],
            tag_id=resolved_tag_id,
            interval_value=call.data[ATTR_INTERVAL_VALUE],
            interval_unit=call.data[ATTR_INTERVAL_UNIT],
            notes=call.data.get("notes"),
            icon=call.data.get("icon"),
            category=call.data.get("category"),
            due_soon_threshold_days=call.data.get("due_soon_threshold_days"),
            active=call.data.get("active", True),
            last_reset_at=call.data.get("last_reset_at"),
        )
        await _async_reload_entry(hass, config_entry_id)

    async def handle_associate_existing_tag_from_helpers(call: ServiceCall) -> None:
        """Associate an existing Home Assistant tag with helper-provided object data."""
        config_entry_id = call.data["config_entry_id"]
        coordinator = await _get_coordinator(config_entry_id)
        name, interval_value, interval_unit = _read_onboarding_helpers()
        resolved_tag_id = _resolve_tag_id_from_inputs(
            coordinator,
            tag_id=call.data.get(ATTR_TAG_ID),
            tag_entity_id=call.data.get(ATTR_TAG_ENTITY_ID),
        )

        await coordinator.async_create_object(
            name=name,
            tag_id=resolved_tag_id,
            interval_value=interval_value,
            interval_unit=interval_unit,
            notes=call.data.get("notes"),
            icon=call.data.get("icon"),
            category=call.data.get("category"),
            due_soon_threshold_days=call.data.get("due_soon_threshold_days"),
            active=call.data.get("active", True),
            last_reset_at=call.data.get("last_reset_at"),
        )

        if call.data.get("clear_name_helper", True):
            await _clear_name_helper()

        await _async_reload_entry(hass, config_entry_id)

    async def handle_associate_selected_existing_tag_from_helpers(call: ServiceCall) -> None:
        """Associate the selected onboarding tag using onboarding helpers."""
        config_entry_id = call.data["config_entry_id"]
        coordinator = await _get_coordinator(config_entry_id)
        name, interval_value, interval_unit = _read_onboarding_helpers()
        resolved_tag_id = _read_selected_existing_tag(coordinator)

        await coordinator.async_create_object(
            name=name,
            tag_id=resolved_tag_id,
            interval_value=interval_value,
            interval_unit=interval_unit,
            notes=call.data.get("notes"),
            icon=call.data.get("icon"),
            category=call.data.get("category"),
            due_soon_threshold_days=call.data.get("due_soon_threshold_days"),
            active=call.data.get("active", True),
            last_reset_at=call.data.get("last_reset_at"),
        )

        if call.data.get("clear_name_helper", True):
            await _clear_name_helper()

        await coordinator.async_clear_onboarding_mode()
        await coordinator.async_clear_selected_existing_tag()
        await _async_reload_entry(hass, config_entry_id)

    async def handle_set_onboarding_mode(call: ServiceCall) -> None:
        """Set the integration-owned onboarding mode."""
        coordinator = await _get_coordinator(call.data["config_entry_id"])
        await coordinator.async_set_onboarding_mode(
            call.data[ATTR_MODE],
            return_path=call.data.get(ATTR_RETURN_PATH),
        )

    async def handle_clear_onboarding_mode(call: ServiceCall) -> None:
        """Clear the integration-owned onboarding mode."""
        coordinator = await _get_coordinator(call.data["config_entry_id"])
        await coordinator.async_clear_onboarding_mode()

    async def handle_select_existing_tag(call: ServiceCall) -> None:
        """Select an existing HA tag for the onboarding flow."""
        coordinator = await _get_coordinator(call.data["config_entry_id"])
        await coordinator.async_select_existing_tag(
            tag_id=call.data.get(ATTR_SELECTED_TAG_ID),
            tag_entity_id=call.data.get(ATTR_SELECTED_TAG_ENTITY_ID),
            source=call.data.get(ATTR_SELECTED_TAG_SOURCE, 'existing'),
        )

    async def handle_clear_selected_existing_tag(call: ServiceCall) -> None:
        """Clear the selected tag from onboarding state."""
        coordinator = await _get_coordinator(call.data["config_entry_id"])
        await coordinator.async_clear_selected_existing_tag()

    async def handle_finish_onboarding(call: ServiceCall) -> None:
        """Create a tracked object from the currently selected onboarding tag."""
        config_entry_id = call.data["config_entry_id"]
        coordinator = await _get_coordinator(config_entry_id)
        await coordinator.async_finish_onboarding(
            name=call.data["name"],
            interval_value=call.data[ATTR_INTERVAL_VALUE],
            interval_unit=call.data[ATTR_INTERVAL_UNIT],
            notes=call.data.get("notes"),
            icon=call.data.get("icon"),
            category=call.data.get("category"),
            due_soon_threshold_days=call.data.get("due_soon_threshold_days"),
            active=call.data.get("active", True),
            last_reset_at=call.data.get("last_reset_at"),
        )
        await _async_reload_entry(hass, config_entry_id)

    async def handle_resume_latest_pending_tag(call: ServiceCall) -> None:
        """Promote the latest pending tag into onboarding selection state."""
        coordinator = await _get_coordinator(call.data["config_entry_id"])
        await coordinator.async_resume_latest_pending_tag_for_onboarding()

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_OBJECT,
        handle_create_object,
        schema=SERVICE_CREATE_OBJECT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_OBJECT,
        handle_update_object,
        schema=SERVICE_UPDATE_OBJECT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_OBJECT,
        handle_delete_object,
        schema=SERVICE_DELETE_OBJECT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_OBJECT,
        handle_reset_object,
        schema=SERVICE_RESET_OBJECT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DISMISS_PENDING_TAG,
        handle_dismiss_pending_tag,
        schema=SERVICE_DISMISS_PENDING_TAG_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLAIM_PENDING_TAG,
        handle_claim_pending_tag,
        schema=SERVICE_CLAIM_PENDING_TAG_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLAIM_LATEST_PENDING_TAG,
        handle_claim_latest_pending_tag,
        schema=SERVICE_CLAIM_LATEST_PENDING_TAG_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLAIM_LATEST_PENDING_TAG_FROM_HELPERS,
        handle_claim_latest_pending_tag_from_helpers,
        schema=SERVICE_CLAIM_LATEST_PENDING_TAG_FROM_HELPERS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ASSOCIATE_EXISTING_TAG,
        handle_associate_existing_tag,
        schema=SERVICE_ASSOCIATE_EXISTING_TAG_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ASSOCIATE_EXISTING_TAG_FROM_HELPERS,
        handle_associate_existing_tag_from_helpers,
        schema=SERVICE_ASSOCIATE_EXISTING_TAG_FROM_HELPERS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ASSOCIATE_SELECTED_EXISTING_TAG_FROM_HELPERS,
        handle_associate_selected_existing_tag_from_helpers,
        schema=SERVICE_ASSOCIATE_SELECTED_EXISTING_TAG_FROM_HELPERS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ONBOARDING_MODE,
        handle_set_onboarding_mode,
        schema=SERVICE_SET_ONBOARDING_MODE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_ONBOARDING_MODE,
        handle_clear_onboarding_mode,
        schema=SERVICE_CLEAR_ONBOARDING_MODE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SELECT_EXISTING_TAG,
        handle_select_existing_tag,
        schema=SERVICE_SELECT_EXISTING_TAG_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_SELECTED_EXISTING_TAG,
        handle_clear_selected_existing_tag,
        schema=SERVICE_CLEAR_SELECTED_EXISTING_TAG_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_FINISH_ONBOARDING,
        handle_finish_onboarding,
        schema=SERVICE_FINISH_ONBOARDING_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESUME_LATEST_PENDING_TAG,
        handle_resume_latest_pending_tag,
        schema=SERVICE_RESUME_LATEST_PENDING_TAG_SCHEMA,
    )

    _LOGGER.debug("Registered Stuck services")


async def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister Stuck services."""
    for service in (
        SERVICE_CREATE_OBJECT,
        SERVICE_UPDATE_OBJECT,
        SERVICE_DELETE_OBJECT,
        SERVICE_RESET_OBJECT,
        SERVICE_DISMISS_PENDING_TAG,
        SERVICE_CLAIM_PENDING_TAG,
        SERVICE_CLAIM_LATEST_PENDING_TAG,
        SERVICE_CLAIM_LATEST_PENDING_TAG_FROM_HELPERS,
        SERVICE_ASSOCIATE_EXISTING_TAG,
        SERVICE_ASSOCIATE_EXISTING_TAG_FROM_HELPERS,
        SERVICE_ASSOCIATE_SELECTED_EXISTING_TAG_FROM_HELPERS,
        SERVICE_SET_ONBOARDING_MODE,
        SERVICE_CLEAR_ONBOARDING_MODE,
        SERVICE_SELECT_EXISTING_TAG,
        SERVICE_CLEAR_SELECTED_EXISTING_TAG,
        SERVICE_FINISH_ONBOARDING,
        SERVICE_RESUME_LATEST_PENDING_TAG,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
