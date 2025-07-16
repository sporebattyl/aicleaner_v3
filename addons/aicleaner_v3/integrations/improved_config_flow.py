"""
Improved Config Flow Implementation
Proper ConfigFlow inheritance and HA integration patterns
"""

import voluptuous as vol
from homeassistant import config_entries, core
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.components import hassio
import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "aicleaner_v3"

class AiCleanerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle AICleaner v3 configuration flow with proper HA integration."""
    
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize config flow."""
        self.discovery_info = {}

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            try:
                # Validate configuration
                await self._validate_config(user_input)
                
                # Check for existing entries
                await self.async_set_unique_id(f"aicleaner_{user_input[CONF_HOST]}")
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title="AICleaner v3",
                    data=user_input
                )
                
            except ValueError as e:
                errors["base"] = "invalid_config"
                _LOGGER.error(f"Config validation failed: {e}")
            except Exception as e:
                errors["base"] = "unknown"
                _LOGGER.error(f"Unexpected error: {e}")

        # Configuration schema
        data_schema = vol.Schema({
            vol.Required(CONF_HOST, default="localhost"): str,
            vol.Required(CONF_PORT, default=8123): int,
            vol.Optional("ai_provider", default="openai"): vol.In([
                "openai", "anthropic", "google", "ollama"
            ]),
            vol.Optional("enable_performance_monitoring", default=True): bool,
            vol.Optional("cleanup_schedule", default="daily"): vol.In([
                "hourly", "daily", "weekly"
            ])
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"name": "AICleaner v3"}
        )

    async def async_step_hassio(self, discovery_info):
        """Handle hassio discovery."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        self.discovery_info = discovery_info
        return await self.async_step_hassio_confirm()

    async def async_step_hassio_confirm(self, user_input=None):
        """Confirm hassio discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title="AICleaner v3 (Hassio)",
                data=self.discovery_info
            )

        return self.async_show_form(
            step_id="hassio_confirm",
            description_placeholders={"addon_name": "AICleaner v3"}
        )

    async def _validate_config(self, config):
        """Validate the user configuration."""
        host = config[CONF_HOST]
        port = config[CONF_PORT]
        
        # Basic validation
        if not host:
            raise ValueError("Host cannot be empty")
        
        if not isinstance(port, int) or port <= 0:
            raise ValueError("Port must be a positive integer")
        
        # Test connection if possible
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://{host}:{port}/api/",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status >= 400:
                        raise ValueError("Cannot connect to Home Assistant")
                        
        except Exception as e:
            _LOGGER.warning(f"Connection test failed: {e}")
            # Don't fail config on connection test failure

    @staticmethod
    @core.callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return AiCleanerOptionsFlow(config_entry)


class AiCleanerOptionsFlow(config_entries.OptionsFlow):
    """Handle AICleaner v3 options flow."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_config = self.config_entry.data
        options_schema = vol.Schema({
            vol.Optional(
                "ai_provider", 
                default=current_config.get("ai_provider", "openai")
            ): vol.In(["openai", "anthropic", "google", "ollama"]),
            vol.Optional(
                "enable_performance_monitoring",
                default=current_config.get("enable_performance_monitoring", True)
            ): bool,
            vol.Optional(
                "cleanup_schedule",
                default=current_config.get("cleanup_schedule", "daily")
            ): vol.In(["hourly", "daily", "weekly"])
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema
        )
