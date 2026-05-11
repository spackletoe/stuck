"""The Stuck integration."""

from __future__ import annotations

import logging

from homeassistant.components.persistent_notification import async_create as create_notification
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.typing import ConfigType

from .const import (
    DATA_COORDINATOR,
    DATA_STORAGE,
    DATA_TAG_ROUTER,
    DOMAIN,
    EVENT_STUCK_TAG_SCANNED,
    EVENT_TAG_SCANNED,
    PLATFORMS,
)
from .coordinator import StuckCoordinator
from .services import async_register_services, async_unregister_services
from .storage import StuckStorage
from .tag_router import StuckTagRouter

_LOGGER = logging.getLogger(__name__)

type StuckConfigEntry = ConfigEntry


async def _async_config_entry_changed(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when config entry options or data change."""
    if entry.state is not ConfigEntryState.LOADED:
        return
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Stuck integration from YAML."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: StuckConfigEntry) -> bool:
    """Set up Stuck from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    storage = StuckStorage(hass)
    coordinator = StuckCoordinator(hass, storage, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.async_on_unload(entry.add_update_listener(_async_config_entry_changed))
    tag_router = StuckTagRouter(coordinator)

    @callback
    async def async_handle_tag_scanned(event: Event) -> None:
        """Handle Home Assistant tag scanned events."""
        data = event.data or {}
        tag_id = data.get("tag_id") or data.get("tag")
        if not tag_id:
            return

        source_device = data.get("device_id") or data.get("source_device")
        tag_entity_id = data.get("entity_id") or data.get("tag_entity_id")
        result = await tag_router.async_handle_tag_scan(
            tag_id,
            source_device=source_device,
            tag_entity_id=tag_entity_id,
        )
        hass.bus.async_fire(EVENT_STUCK_TAG_SCANNED, result)

        if result.get("kind") == "pending":
            create_notification(
                hass,
                (
                    "A new NFC tag was detected by Stuck.\n\n"
                    f"Tag ID: `{tag_id}`\n\n"
                    "Use the `stuck.claim_pending_tag` service or the Stuck dashboard "
                    "to turn it into a tracked object."
                ),
                title="Stuck: New tag detected",
                notification_id=f"stuck_pending_{tag_id}",
            )
        elif result.get("kind") == "known":
            create_notification(
                hass,
                (
                    f"Scanned **{result.get('name', 'Stuck object')}**.\n\n"
                    f"Status: `{result.get('status', 'unknown')}`\n"
                    f"Open: {result.get('object_url', '/stuck-dashboard')}"
                ),
                title="Stuck: Known tag scanned",
                notification_id=f"stuck_known_{tag_id}",
            )

        _LOGGER.debug("Stuck tag event routed: %s", result)

    remove_listener = hass.bus.async_listen(EVENT_TAG_SCANNED, async_handle_tag_scanned)

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_STORAGE: storage,
        DATA_COORDINATOR: coordinator,
        DATA_TAG_ROUTER: tag_router,
        "remove_listener": remove_listener,
    }

    await async_register_services(hass)

    if PLATFORMS:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: StuckConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = True

    if PLATFORMS:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if entry_data and "remove_listener" in entry_data:
            entry_data["remove_listener"]()
        if not hass.data[DOMAIN]:
            await async_unregister_services(hass)

    return unload_ok
