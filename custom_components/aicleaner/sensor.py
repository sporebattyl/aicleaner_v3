"""AICleaner Sensor Platform"""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import AiCleanerCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AICleaner sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    sensors = [
        AiCleanerStatusSensor(coordinator),
        AiCleanerConnectionSensor(coordinator),
        AiCleanerUptimeSensor(coordinator),
        AiCleanerProvidersSensor(coordinator),
        AiCleanerLastAnalysisSensor(coordinator),
        AiCleanerLastGenerationSensor(coordinator),
    ]
    
    async_add_entities(sensors, True)


class AiCleanerStatusSensor(CoordinatorEntity, SensorEntity):
    """AICleaner Status Sensor."""
    
    def __init__(self, coordinator: AiCleanerCoordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "AICleaner Status"
        self._attr_unique_id = f"{DOMAIN}_status"
        self._attr_icon = "mdi:robot"
    
    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self.coordinator.data.get("status", "unknown")
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        return {
            "version": self.coordinator.data.get("version"),
            "last_update": self.coordinator.data.get("last_update"),
        }


class AiCleanerConnectionSensor(CoordinatorEntity, SensorEntity):
    """AICleaner Connection Status Sensor."""
    
    def __init__(self, coordinator: AiCleanerCoordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "AICleaner Connection"
        self._attr_unique_id = f"{DOMAIN}_connection"
    
    @property
    def native_value(self) -> str:
        """Return the connection status."""
        status = self.coordinator.data.get("status", "unknown")
        return {
            "ok": "Connected",
            "auth_error": "Authentication Failed", 
            "connection_error": "Connection Failed",
            "timeout": "Connection Timeout",
            "service_unavailable": "Service Down",
            "rate_limited": "Rate Limited"
        }.get(status, "Unknown")
    
    @property
    def icon(self) -> str:
        """Return the icon for the sensor."""
        status = self.coordinator.data.get("status", "unknown")
        return {
            "ok": "mdi:check-network",
            "auth_error": "mdi:key-alert",
            "connection_error": "mdi:close-network",
            "timeout": "mdi:timer-alert", 
            "service_unavailable": "mdi:server-off",
            "rate_limited": "mdi:speedometer-slow"
        }.get(status, "mdi:help-network")
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        status = self.coordinator.data.get("status", "unknown")
        return {
            "last_successful_update": self.coordinator.last_update_success,
            "update_interval_seconds": self.coordinator.update_interval.total_seconds(),
            "raw_status": status
        }


class AiCleanerUptimeSensor(CoordinatorEntity, SensorEntity):
    """AICleaner Uptime Sensor."""
    
    def __init__(self, coordinator: AiCleanerCoordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "AICleaner Uptime"
        self._attr_unique_id = f"{DOMAIN}_uptime"
        self._attr_icon = "mdi:clock"
        self._attr_native_unit_of_measurement = "s"
        self._attr_device_class = "duration"
    
    @property
    def native_value(self) -> float:
        """Return the uptime in seconds."""
        return self.coordinator.data.get("uptime_seconds", 0)


class AiCleanerProvidersSensor(CoordinatorEntity, SensorEntity):
    """AICleaner Providers Status Sensor."""
    
    def __init__(self, coordinator: AiCleanerCoordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "AICleaner Providers"
        self._attr_unique_id = f"{DOMAIN}_providers"
        self._attr_icon = "mdi:cloud"
    
    @property
    def native_value(self) -> int:
        """Return the number of available providers."""
        providers = self.coordinator.data.get("providers", {})
        return len([p for p in providers.values() if p.get("available", False)])
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return provider details as attributes."""
        providers = self.coordinator.data.get("providers", {})
        attributes = {}
        
        for name, provider in providers.items():
            attributes[f"{name}_available"] = provider.get("available", False)
            attributes[f"{name}_models"] = len(provider.get("models", []))
        
        return attributes


class AiCleanerLastAnalysisSensor(SensorEntity):
    """Sensor for last camera analysis result."""
    
    def __init__(self, coordinator: AiCleanerCoordinator):
        """Initialize the sensor."""
        self._attr_name = "AICleaner Last Analysis"
        self._attr_unique_id = f"{DOMAIN}_last_analysis"
        self._attr_icon = "mdi:camera-iris"
        self._state = "No analysis yet"
        self._attributes = {}
    
    @property
    def native_value(self) -> str:
        """Return the analysis result."""
        return self._state
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return analysis details as attributes."""
        return self._attributes
    
    async def async_added_to_hass(self):
        """When entity is added to hass."""
        # Listen for analysis completion events
        self.hass.bus.async_listen(
            "aicleaner_analysis_complete",
            self._handle_analysis_complete
        )
    
    async def _handle_analysis_complete(self, event):
        """Handle analysis completion event."""
        result = event.data.get("result", {})
        camera = event.data.get("camera", "unknown")
        
        self._state = result.get("text", "No result")[:255]  # Limit state length
        self._attributes = {
            "camera": camera,
            "provider": result.get("provider", "unknown"),
            "response_time_ms": result.get("response_time_ms", 0),
            "usage": result.get("usage", {}),
            "timestamp": dt_util.utcnow().isoformat()
        }
        self.async_write_ha_state()


class AiCleanerLastGenerationSensor(SensorEntity):
    """Sensor for last text generation result."""
    
    def __init__(self, coordinator: AiCleanerCoordinator):
        """Initialize the sensor."""
        self._attr_name = "AICleaner Last Generation"
        self._attr_unique_id = f"{DOMAIN}_last_generation"
        self._attr_icon = "mdi:text-box"
        self._state = "No generation yet"
        self._attributes = {}
    
    @property
    def native_value(self) -> str:
        """Return the generation result."""
        return self._state
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return generation details as attributes."""
        return self._attributes
    
    async def async_added_to_hass(self):
        """When entity is added to hass."""
        # Listen for generation completion events
        self.hass.bus.async_listen(
            "aicleaner_generation_complete",
            self._handle_generation_complete
        )
    
    async def _handle_generation_complete(self, event):
        """Handle generation completion event."""
        result = event.data.get("result", {})
        
        self._state = result.get("text", "No result")[:255]  # Limit state length
        self._attributes = {
            "provider": result.get("provider", "unknown"),
            "response_time_ms": result.get("response_time_ms", 0),
            "usage": result.get("usage", {}),
            "cost": result.get("cost", {}),
            "timestamp": dt_util.utcnow().isoformat()
        }
        self.async_write_ha_state()
