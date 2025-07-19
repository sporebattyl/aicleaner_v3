"""
Home Assistant Service Handler
Phase 4A: Enhanced Home Assistant Integration

Handles incoming service calls from Home Assistant and translates them
to AICleaner internal operations.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import inspect

from .models import HAServiceConfig, HAServiceField, ServiceDefinition
from .ha_client import HAClient
from .config_schema import HAIntegrationConfig

logger = logging.getLogger(__name__)

class ServiceHandler:
    """
    Handles Home Assistant service calls and translates them to AICleaner operations
    
    Registers AICleaner services with Home Assistant and processes incoming
    service calls through registered handler functions.
    """
    
    def __init__(self, ha_client: HAClient, config: HAIntegrationConfig, 
                 aicleaner_core=None):
        self.ha_client = ha_client
        self.config = config
        self.aicleaner_core = aicleaner_core
        self.registered_services: Dict[str, ServiceDefinition] = {}
        self.service_handlers: Dict[str, Callable] = {}
        self.service_call_history: List[Dict[str, Any]] = []
        self.max_history_size = 100
        
    async def initialize(self) -> bool:
        """
        Initialize service handler and register default services
        
        Returns:
            True if successful
        """
        try:
            logger.info("Initializing Home Assistant service handler...")
            
            # Register event handler for service calls
            await self.ha_client.subscribe_events(
                event_type="call_service",
                handler=self._handle_service_call_event
            )
            
            # Register default services
            if self.config.register_services:
                await self._register_default_services()
            
            logger.info("Service handler initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize service handler: {e}")
            return False
    
    async def _register_default_services(self):
        """Register default AICleaner services with Home Assistant"""
        default_services = [
            # Start cleaning service
            ServiceDefinition(
                service_name="start_cleaning",
                config=HAServiceConfig(
                    service="start_cleaning",
                    name="Start Cleaning",
                    description="Start AICleaner cleaning operation",
                    fields={
                        "zone_id": HAServiceField(
                            name="Zone ID",
                            description="ID of zone to clean (optional)",
                            selector={"text": {}},
                            required=False
                        ),
                        "cleaning_mode": HAServiceField(
                            name="Cleaning Mode",
                            description="Cleaning intensity mode",
                            selector={
                                "select": {
                                    "options": ["eco", "normal", "deep", "auto"]
                                }
                            },
                            default="normal",
                            required=False
                        ),
                        "duration": HAServiceField(
                            name="Duration",
                            description="Maximum cleaning duration in minutes",
                            selector={
                                "number": {
                                    "min": 5,
                                    "max": 480,
                                    "unit_of_measurement": "minutes"
                                }
                            },
                            required=False
                        )
                    }
                ),
                handler_callback="handle_start_cleaning"
            ),
            
            # Stop cleaning service
            ServiceDefinition(
                service_name="stop_cleaning",
                config=HAServiceConfig(
                    service="stop_cleaning",
                    name="Stop Cleaning", 
                    description="Stop current cleaning operation",
                    fields={}
                ),
                handler_callback="handle_stop_cleaning"
            ),
            
            # Pause/Resume cleaning service
            ServiceDefinition(
                service_name="pause_cleaning",
                config=HAServiceConfig(
                    service="pause_cleaning",
                    name="Pause Cleaning",
                    description="Pause or resume cleaning operation",
                    fields={
                        "action": HAServiceField(
                            name="Action",
                            description="Pause or resume action",
                            selector={
                                "select": {
                                    "options": ["pause", "resume"]
                                }
                            },
                            default="pause",
                            required=True
                        )
                    }
                ),
                handler_callback="handle_pause_cleaning"
            ),
            
            # Set cleaning mode service
            ServiceDefinition(
                service_name="set_cleaning_mode",
                config=HAServiceConfig(
                    service="set_cleaning_mode",
                    name="Set Cleaning Mode",
                    description="Change the cleaning mode",
                    fields={
                        "mode": HAServiceField(
                            name="Mode",
                            description="Cleaning mode to set",
                            selector={
                                "select": {
                                    "options": ["eco", "normal", "deep", "auto"]
                                }
                            },
                            required=True
                        )
                    }
                ),
                handler_callback="handle_set_cleaning_mode"
            ),
            
            # Update zone configuration service
            ServiceDefinition(
                service_name="update_zone",
                config=HAServiceConfig(
                    service="update_zone",
                    name="Update Zone",
                    description="Update zone configuration",
                    fields={
                        "zone_id": HAServiceField(
                            name="Zone ID",
                            description="ID of zone to update",
                            selector={"text": {}},
                            required=True
                        ),
                        "name": HAServiceField(
                            name="Name",
                            description="Zone name",
                            selector={"text": {}},
                            required=False
                        ),
                        "enabled": HAServiceField(
                            name="Enabled",
                            description="Whether zone is enabled",
                            selector={"boolean": {}},
                            required=False
                        ),
                        "priority": HAServiceField(
                            name="Priority",
                            description="Zone cleaning priority",
                            selector={
                                "number": {
                                    "min": 1,
                                    "max": 10
                                }
                            },
                            required=False
                        )
                    }
                ),
                handler_callback="handle_update_zone"
            ),
            
            # Emergency stop service
            ServiceDefinition(
                service_name="emergency_stop",
                config=HAServiceConfig(
                    service="emergency_stop",
                    name="Emergency Stop",
                    description="Immediately stop all AICleaner operations",
                    fields={}
                ),
                handler_callback="handle_emergency_stop"
            ),
            
            # Reload configuration service
            ServiceDefinition(
                service_name="reload_config",
                config=HAServiceConfig(
                    service="reload_config", 
                    name="Reload Configuration",
                    description="Reload AICleaner configuration",
                    fields={}
                ),
                handler_callback="handle_reload_config"
            ),
            
            # Get status service
            ServiceDefinition(
                service_name="get_status",
                config=HAServiceConfig(
                    service="get_status",
                    name="Get Status",
                    description="Get detailed AICleaner status",
                    fields={
                        "include_zones": HAServiceField(
                            name="Include Zones",
                            description="Include zone information in status",
                            selector={"boolean": {}},
                            default=False,
                            required=False
                        ),
                        "include_devices": HAServiceField(
                            name="Include Devices", 
                            description="Include device information in status",
                            selector={"boolean": {}},
                            default=False,
                            required=False
                        )
                    }
                ),
                handler_callback="handle_get_status"
            )
        ]
        
        # Register each service
        for service_def in default_services:
            await self.register_service(service_def)
    
    async def register_service(self, service_def: ServiceDefinition) -> bool:
        """
        Register a service with Home Assistant
        
        Args:
            service_def: Service definition
            
        Returns:
            True if successful
        """
        try:
            service_name = f"{self.config.service_domain}.{service_def.service_name}"
            
            # Prepare service configuration for HA
            service_config = self._prepare_service_config(service_def)
            
            # Register service with HA via REST API
            url = f"{self.ha_client.config.rest_api_url}/services/{self.config.service_domain}/{service_def.service_name}"
            
            async with self.ha_client.session.post(url, json=service_config) as response:
                if response.status in [200, 201]:
                    # Store service definition
                    self.registered_services[service_name] = service_def
                    
                    # Register handler function
                    handler_func = getattr(self, service_def.handler_callback, None)
                    if handler_func:
                        self.service_handlers[service_name] = handler_func
                    else:
                        logger.warning(f"Handler function not found: {service_def.handler_callback}")
                    
                    logger.info(f"Service registered: {service_name}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Service registration failed: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Service registration error: {e}")
            return False
    
    def _prepare_service_config(self, service_def: ServiceDefinition) -> Dict[str, Any]:
        """Prepare service configuration for Home Assistant"""
        config = {
            "description": service_def.config.description,
            "fields": {}
        }
        
        # Convert service fields to HA format
        for field_name, field_config in service_def.config.fields.items():
            config["fields"][field_name] = {
                "description": field_config.description or field_config.name,
                "selector": field_config.selector,
                "required": field_config.required
            }
            
            if field_config.default is not None:
                config["fields"][field_name]["default"] = field_config.default
        
        return config
    
    async def _handle_service_call_event(self, event_data: Dict[str, Any]):
        """Handle incoming service call events from Home Assistant"""
        try:
            event_info = event_data.get("data", {})
            domain = event_info.get("domain")
            service = event_info.get("service")
            service_data = event_info.get("service_data", {})
            
            # Check if this is for our domain
            if domain != self.config.service_domain:
                return
            
            service_name = f"{domain}.{service}"
            
            # Log service call
            self._log_service_call(service_name, service_data)
            
            # Find and execute handler
            if service_name in self.service_handlers:
                handler = self.service_handlers[service_name]
                
                try:
                    # Execute handler (handle both sync and async)
                    if inspect.iscoroutinefunction(handler):
                        result = await handler(service_data)
                    else:
                        result = handler(service_data)
                    
                    logger.info(f"Service call completed: {service_name}")
                    
                    # TODO: Send response back to HA if needed
                    
                except Exception as e:
                    logger.error(f"Service handler error for {service_name}: {e}")
                    # TODO: Send error response to HA
                    
            else:
                logger.warning(f"No handler found for service: {service_name}")
                
        except Exception as e:
            logger.error(f"Service call event handling error: {e}")
    
    def _log_service_call(self, service_name: str, service_data: Dict[str, Any]):
        """Log service call for history and debugging"""
        call_info = {
            "timestamp": datetime.now().isoformat(),
            "service": service_name,
            "data": service_data,
            "source": "home_assistant"
        }
        
        self.service_call_history.append(call_info)
        
        # Limit history size
        if len(self.service_call_history) > self.max_history_size:
            self.service_call_history = self.service_call_history[-self.max_history_size:]
        
        logger.debug(f"Service call logged: {service_name} with data: {service_data}")
    
    # Service Handler Functions
    
    async def handle_start_cleaning(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle start_cleaning service call"""
        zone_id = service_data.get("zone_id")
        cleaning_mode = service_data.get("cleaning_mode", "normal")
        duration = service_data.get("duration")
        
        logger.info(f"Starting cleaning: zone={zone_id}, mode={cleaning_mode}, duration={duration}")
        
        try:
            # Use AICleanerCore for orchestrated cleaning operations
            if self.aicleaner_core:
                if zone_id:
                    # Clean specific zone
                    result = await self.aicleaner_core.clean_zone_by_id(zone_id, cleaning_mode, duration)
                    logger.info(f"Zone cleaning initiated for {zone_id}: {result}")
                    return result
                else:
                    # Clean all zones
                    result = await self.aicleaner_core.clean_all_zones(cleaning_mode)
                    logger.info(f"All-zone cleaning initiated: {result}")
                    return result
            else:
                # Fallback for when core system is not available
                logger.warning("AICleaner core not available, returning mock response")
                return {
                    "status": "success",
                    "message": "Cleaning started (simulation mode)",
                    "zone_id": zone_id,
                    "mode": cleaning_mode,
                    "estimated_duration": duration,
                    "note": "AICleaner core not initialized"
                }
                
        except Exception as e:
            logger.error(f"Error starting cleaning: {e}")
            return {
                "status": "error",
                "message": f"Failed to start cleaning: {str(e)}",
                "zone_id": zone_id
            }
    
    async def handle_stop_cleaning(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stop_cleaning service call"""
        zone_id = service_data.get("zone_id")
        logger.info(f"Stopping cleaning operation for zone: {zone_id}")
        
        try:
            # Use AICleanerCore for orchestrated cleaning operations
            if self.aicleaner_core:
                result = await self.aicleaner_core.stop_cleaning(zone_id)
                logger.info(f"Cleaning stop initiated: {result}")
                return result
            else:
                logger.warning("AICleaner core not available, returning mock response")
                return {
                    "status": "success",
                    "message": "Cleaning stopped (simulation mode)",
                    "zone_id": zone_id,
                    "note": "AICleaner core not initialized"
                }
                
        except Exception as e:
            logger.error(f"Error stopping cleaning: {e}")
            return {
                "status": "error",
                "message": f"Failed to stop cleaning: {str(e)}"
            }
    
    async def handle_pause_cleaning(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pause_cleaning service call"""
        action = service_data.get("action", "pause")
        
        logger.info(f"Cleaning operation: {action}")
        
        # TODO: Interface with AICleaner core cleaning system
        # For now, return success response
        
        return {
            "status": "success",
            "message": f"Cleaning {action}d",
            "action": action
        }
    
    async def handle_set_cleaning_mode(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set_cleaning_mode service call"""
        mode = service_data.get("mode")
        
        if not mode:
            raise ValueError("Cleaning mode is required")
        
        logger.info(f"Setting cleaning mode to: {mode}")
        
        # TODO: Interface with AICleaner core configuration system
        # For now, return success response
        
        return {
            "status": "success",
            "message": "Cleaning mode updated",
            "mode": mode
        }
    
    async def handle_update_zone(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update_zone service call"""
        zone_id = service_data.get("zone_id")
        
        if not zone_id:
            raise ValueError("Zone ID is required")
        
        name = service_data.get("name")
        enabled = service_data.get("enabled")
        priority = service_data.get("priority")
        
        logger.info(f"Updating zone {zone_id}: name={name}, enabled={enabled}, priority={priority}")
        
        # TODO: Interface with AICleaner zone management system
        # For now, return success response
        
        return {
            "status": "success",
            "message": "Zone updated",
            "zone_id": zone_id,
            "updates": {k: v for k, v in service_data.items() if k != "zone_id" and v is not None}
        }
    
    async def handle_emergency_stop(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle emergency_stop service call"""
        logger.warning("Emergency stop activated!")
        
        # TODO: Interface with AICleaner emergency stop system
        # For now, return success response
        
        return {
            "status": "success",
            "message": "Emergency stop activated"
        }
    
    async def handle_reload_config(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle reload_config service call"""
        logger.info("Reloading AICleaner configuration")
        
        # TODO: Interface with AICleaner configuration system
        # For now, return success response
        
        return {
            "status": "success",
            "message": "Configuration reloaded"
        }
    
    async def handle_get_status(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_status service call"""
        include_zones = service_data.get("include_zones", False)
        include_devices = service_data.get("include_devices", False)
        
        logger.info(f"Getting status: zones={include_zones}, devices={include_devices}")
        
        # TODO: Interface with AICleaner status system
        # For now, return mock status
        
        status = {
            "status": "idle",
            "uptime": "2 hours",
            "last_cleaned": None,
            "cleaning_mode": "normal",
            "errors": [],
            "timestamp": datetime.now().isoformat()
        }
        
        if include_zones:
            status["zones"] = [
                {"id": "zone_1", "name": "Living Room", "enabled": True},
                {"id": "zone_2", "name": "Kitchen", "enabled": True}
            ]
        
        if include_devices:
            status["devices"] = [
                {"id": "device_1", "name": "Main Vacuum", "status": "connected"},
                {"id": "device_2", "name": "Sensor Hub", "status": "connected"}
            ]
        
        return status
    
    # Utility Methods
    
    async def call_external_service(self, domain: str, service: str, 
                                  service_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Call an external Home Assistant service
        
        Args:
            domain: Service domain
            service: Service name
            service_data: Service data
            
        Returns:
            Service call result
        """
        return await self.ha_client.call_service(domain, service, service_data)
    
    def get_service_call_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get service call history
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of service call records
        """
        history = self.service_call_history
        if limit:
            history = history[-limit:]
        return list(reversed(history))  # Most recent first
    
    def get_registered_services(self) -> List[str]:
        """Get list of registered service names"""
        return list(self.registered_services.keys())
    
    def get_service_count(self) -> int:
        """Get number of registered services"""
        return len(self.registered_services)
    
    async def unregister_service(self, service_name: str) -> bool:
        """
        Unregister a service from Home Assistant
        
        Args:
            service_name: Full service name (domain.service)
            
        Returns:
            True if successful
        """
        try:
            domain, service = service_name.split(".", 1)
            url = f"{self.ha_client.config.rest_api_url}/services/{domain}/{service}"
            
            async with self.ha_client.session.delete(url) as response:
                if response.status in [200, 204]:
                    # Remove from local tracking
                    self.registered_services.pop(service_name, None)
                    self.service_handlers.pop(service_name, None)
                    
                    logger.info(f"Service unregistered: {service_name}")
                    return True
                else:
                    error_text = await response.text()
                    logger.warning(f"Service unregistration failed: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Service unregistration error: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup service handler resources"""
        logger.info("Cleaning up service handler...")
        
        # Unregister all services
        for service_name in list(self.registered_services.keys()):
            await self.unregister_service(service_name)
        
        # Clear local state
        self.service_call_history.clear()
        
        logger.info("Service handler cleanup complete")