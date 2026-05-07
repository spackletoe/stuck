"""Config flow for the Stuck integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_DEFAULT_DUE_SOON_THRESHOLD_DAYS,
    CONF_SHOW_INACTIVE_OBJECTS,
    DEFAULT_DUE_SOON_THRESHOLD_DAYS,
    DEFAULT_SHOW_INACTIVE_OBJECTS,
    DOMAIN,
)


class StuckConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Stuck."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="Stuck", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEFAULT_DUE_SOON_THRESHOLD_DAYS,
                    default=DEFAULT_DUE_SOON_THRESHOLD_DAYS,
                ): vol.All(vol.Coerce(int), vol.Range(min=1)),
                vol.Required(
                    CONF_SHOW_INACTIVE_OBJECTS,
                    default=DEFAULT_SHOW_INACTIVE_OBJECTS,
                ): bool,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow for this handler."""
        return StuckOptionsFlow(config_entry)


class StuckOptionsFlow(config_entries.OptionsFlow):
    """Handle Stuck options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the Stuck options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {
            **self.config_entry.data,
            **self.config_entry.options,
        }

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEFAULT_DUE_SOON_THRESHOLD_DAYS,
                    default=current.get(
                        CONF_DEFAULT_DUE_SOON_THRESHOLD_DAYS,
                        DEFAULT_DUE_SOON_THRESHOLD_DAYS,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1)),
                vol.Required(
                    CONF_SHOW_INACTIVE_OBJECTS,
                    default=current.get(
                        CONF_SHOW_INACTIVE_OBJECTS,
                        DEFAULT_SHOW_INACTIVE_OBJECTS,
                    ),
                ): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
