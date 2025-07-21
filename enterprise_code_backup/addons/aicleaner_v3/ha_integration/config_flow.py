"""Config flow for AICleaner v3."""
import logging
from typing import Any, Dict

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class AICleanerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AICleaner v3."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input: Dict[str, Any] = None):
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="AICleaner v3", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("api_key", default=""): str,
                vol.Optional("cleaning_interval", default=3600): int,
            })
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AICleanerOptionsFlowHandler(config_entry)


class AICleanerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Dict[str, Any] = None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("api_key", default=self.config_entry.options.get("api_key", "")): str,
                vol.Optional("cleaning_interval", default=self.config_entry.options.get("cleaning_interval", 3600)): int,
            }),
        )