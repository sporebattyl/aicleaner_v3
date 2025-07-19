"""Manages Home Assistant services for the AICleaner v3 addon."""
import logging
from typing import Callable

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

class AICleanerServiceManager:
    """Handles registration and execution of services."""

    def __init__(self, hass: HomeAssistant, domain: str):
        self.hass = hass
        self.domain = domain

    async def async_register_service(self, name: str, schema: vol.Schema, handler: Callable, supports_response: SupportsResponse = SupportsResponse.NONE):
        """Register a service with Home Assistant."""
        
        async def service_handler_wrapper(call: ServiceCall) -> None:
            try:
                _LOGGER.info(f"Executing service '{name}' with data: {call.data}")
                response = await handler(call)
                if supports_response == SupportsResponse.ONLY:
                    return response
            except vol.Invalid as err:
                _LOGGER.error(f"Invalid data for service '{name}': {err}")
                raise HomeAssistantError(f"Invalid data for service '{name}': {err}") from err
            except Exception as e:
                _LOGGER.exception(f"Error executing service '{name}': {e}")
                raise HomeAssistantError(f"Error executing service '{name}': {e}") from e

        self.hass.services.async_register(
            self.domain, name, service_handler_wrapper, schema=schema, supports_response=supports_response
        )
        _LOGGER.info(f"Service '{self.domain}.{name}' registered.")

    async def async_remove_service(self, name: str):
        """Remove a registered service."""
        self.hass.services.async_remove(self.domain, name)
        _LOGGER.info(f"Service '{self.domain}.{name}' removed.")