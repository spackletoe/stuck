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
    ATTR_OBJECT_ID,
    ATTR_TAG_ID,
    DATA_COORDINATOR,
    DOMAIN,
    SERVICE_CREATE_OBJECT,
    SERVICE_DELETE_OBJECT,
    SERVICE_DISMISS_PENDING_TAG,
    SERVICE_RESET_OBJECT,
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

    _LOGGER.debug("Registered Stuck services")


async def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister Stuck services."""
    for service in (
        SERVICE_CREATE_OBJECT,
        SERVICE_UPDATE_OBJECT,
        SERVICE_DELETE_OBJECT,
        SERVICE_RESET_OBJECT,
        SERVICE_DISMISS_PENDING_TAG,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
