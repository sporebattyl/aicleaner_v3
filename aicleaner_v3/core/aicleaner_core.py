"""
AICleaner Core System Coordinator
Phase 4A: Enhanced Home Assistant Integration
Phase 4B: MQTT Discovery Integration
Phase 5A: Performance Optimization

Central coordinator that orchestrates all AICleaner core functionality
without direct dependencies on Home Assistant.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ha_integration.ha_adapter import HomeAssistantAdapter
from mqtt.adapter import MQTTAdapter, DeviceInfo

# Performance monitoring - Phase 5A
from performance.profiler import profile_async, get_profiler, get_memory_profiler
from performance.metrics import get_tracker
from performance.event_loop_optimizer import start_event_loop_monitoring, stop_event_loop_monitoring
from performance.state_optimizer import start_state_optimization, stop_state_optimization

logger = logging.getLogger(__name__)


class AICleanerCore:
    """
    The central coordinator for AICleaner systems.
    
    This class orchestrates all core functionality and provides a clean
    interface for service handlers and external integrations.
    """
    
    def __init__(self, config_data: Dict[str, Any], ha_adapter: HomeAssistantAdapter, 
                 ai_provider_manager=None, mqtt_adapter: Optional[MQTTAdapter] = None):
        """
        Initialize the AICleaner core system.
        
        Args:
            config_data: Configuration dictionary
            ha_adapter: Home Assistant adapter for HA interactions
            ai_provider_manager: AI provider manager instance
            mqtt_adapter: MQTT adapter for discovery and state management
        """
        self.config = config_data
        self.ha_adapter = ha_adapter
        self.ai_provider_manager = ai_provider_manager
        self.mqtt_adapter = mqtt_adapter
        
        # System state
        self._running = False
        self._cleaning_active = False
        self._current_cleaning_zones: List[str] = []
        self._system_status = "idle"
        
        # For now, we'll create lightweight managers that don't depend on hass
        # In the future, these would be the real zone and device managers
        self._zones_data: Dict[str, Dict[str, Any]] = {}
        self._devices_data: Dict[str, Dict[str, Any]] = {}
        
        logger.info("AICleaner Core initialized")
    
    @profile_async("core.start")
    async def start(self) -> bool:
        """
        Start the AICleaner core system.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self._running:
                logger.warning("AICleaner core is already running")
                return True
            
            # Start event loop monitoring - Phase 5A
            await start_event_loop_monitoring()
            
            # Start state optimization - Phase 5A
            await start_state_optimization()
            
            # Initialize default zones from config
            await self._initialize_zones()
            
            # Initialize device discovery
            await self._initialize_devices()
            
            # Start MQTT adapter if available
            if self.mqtt_adapter:
                mqtt_success = await self.mqtt_adapter.start()
                if mqtt_success:
                    logger.info("MQTT adapter started successfully")
                    # Publish device discovery messages
                    await self._publish_mqtt_discovery()
                else:
                    logger.warning("Failed to start MQTT adapter")
            
            # Set system state
            self._running = True
            self._system_status = "ready"
            
            # Update HA entities if adapter is available
            if self.ha_adapter.is_available():
                await self._update_ha_status()
            
            logger.info("AICleaner Core started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start AICleaner Core: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        Stop the AICleaner core system.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Stop any active cleaning operations
            if self._cleaning_active:
                await self.stop_cleaning()
            
            # Stop MQTT adapter if available
            if self.mqtt_adapter:
                await self.mqtt_adapter.stop()
                logger.info("MQTT adapter stopped")
            
            # Stop event loop monitoring - Phase 5A
            await stop_event_loop_monitoring()
            
            # Stop state optimization - Phase 5A
            await stop_state_optimization()
            
            self._running = False
            self._system_status = "stopped"
            
            # Update HA entities if adapter is available
            if self.ha_adapter.is_available():
                await self._update_ha_status()
            
            logger.info("AICleaner Core stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping AICleaner Core: {e}")
            return False
    
    @profile_async("core.clean_zone_by_id")
    async def clean_zone_by_id(self, zone_id: str, cleaning_mode: str = "normal", 
                              duration: Optional[int] = None) -> Dict[str, Any]:
        """
        Orchestrates the cleaning of a specific zone.
        
        Args:
            zone_id: Zone identifier to clean
            cleaning_mode: Cleaning mode (normal, deep, quick)
            duration: Optional duration in minutes
            
        Returns:
            Operation result dictionary
        """
        try:
            logger.info(f"Core system received request to clean zone: {zone_id}")
            
            if not self._running:
                return {
                    "status": "error",
                    "message": "AICleaner core is not running",
                    "zone_id": zone_id
                }
            
            # Validate zone exists
            if zone_id not in self._zones_data:
                return {
                    "status": "error",
                    "message": f"Zone {zone_id} not found",
                    "zone_id": zone_id
                }
            
            zone_info = self._zones_data[zone_id]
            
            # Check if zone is enabled
            if not zone_info.get("enabled", True):
                return {
                    "status": "error",
                    "message": f"Zone {zone_id} is disabled",
                    "zone_id": zone_id
                }
            
            # Start cleaning operation with performance tracking
            tracker = get_tracker()
            async with tracker.track_zone_operation(zone_id, "start_cleaning"):
                await self._start_zone_cleaning(zone_id, cleaning_mode, duration)
            
            # Update system state
            if zone_id not in self._current_cleaning_zones:
                self._current_cleaning_zones.append(zone_id)
            self._cleaning_active = True
            self._system_status = "cleaning"
            
            # Update HA entities
            if self.ha_adapter.is_available():
                await self._update_ha_status()
                await self._update_zone_status(zone_id, "cleaning")
            
            # Update MQTT states
            await self.update_mqtt_states()
            
            result = {
                "status": "success",
                "message": f"Cleaning started in zone {zone_id}",
                "zone_id": zone_id,
                "mode": cleaning_mode,
                "estimated_duration": duration or zone_info.get("default_duration", 30),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Zone cleaning started: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error cleaning zone {zone_id}: {e}")
            return {
                "status": "error",
                "message": f"Failed to start cleaning: {str(e)}",
                "zone_id": zone_id
            }
    
    async def clean_all_zones(self, cleaning_mode: str = "normal") -> Dict[str, Any]:
        """
        Start cleaning in all enabled zones.
        
        Args:
            cleaning_mode: Cleaning mode to use
            
        Returns:
            Operation result dictionary
        """
        try:
            logger.info("Starting cleaning in all zones")
            
            if not self._running:
                return {
                    "status": "error",
                    "message": "AICleaner core is not running"
                }
            
            enabled_zones = [
                zone_id for zone_id, zone_info in self._zones_data.items()
                if zone_info.get("enabled", True)
            ]
            
            if not enabled_zones:
                return {
                    "status": "error",
                    "message": "No enabled zones found"
                }
            
            results = []
            for zone_id in enabled_zones:
                try:
                    result = await self.clean_zone_by_id(zone_id, cleaning_mode)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to start cleaning in zone {zone_id}: {e}")
                    results.append({
                        "status": "error",
                        "zone_id": zone_id,
                        "message": str(e)
                    })
            
            return {
                "status": "success",
                "message": f"Cleaning started in {len(enabled_zones)} zones",
                "mode": cleaning_mode,
                "zone_results": results,
                "zones_cleaning": enabled_zones
            }
            
        except Exception as e:
            logger.error(f"Error starting cleaning in all zones: {e}")
            return {
                "status": "error",
                "message": f"Failed to start cleaning: {str(e)}"
            }
    
    async def stop_cleaning(self, zone_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Stop cleaning operations.
        
        Args:
            zone_id: Optional specific zone to stop, None for all zones
            
        Returns:
            Operation result dictionary
        """
        try:
            if zone_id:
                logger.info(f"Stopping cleaning in zone: {zone_id}")
                
                if zone_id in self._current_cleaning_zones:
                    self._current_cleaning_zones.remove(zone_id)
                    await self._stop_zone_cleaning(zone_id)
                    
                    # Update HA entities
                    if self.ha_adapter.is_available():
                        await self._update_zone_status(zone_id, "idle")
                    
                    return {
                        "status": "success",
                        "message": f"Cleaning stopped in zone {zone_id}",
                        "zone_id": zone_id
                    }
                else:
                    return {
                        "status": "warning",
                        "message": f"Zone {zone_id} was not being cleaned",
                        "zone_id": zone_id
                    }
            else:
                logger.info("Stopping cleaning in all zones")
                
                stopped_zones = self._current_cleaning_zones.copy()
                for zone_id in stopped_zones:
                    await self._stop_zone_cleaning(zone_id)
                    if self.ha_adapter.is_available():
                        await self._update_zone_status(zone_id, "idle")
                
                self._current_cleaning_zones.clear()
                self._cleaning_active = False
                self._system_status = "ready"
                
                # Update HA entities
                if self.ha_adapter.is_available():
                    await self._update_ha_status()
                
                # Update MQTT states
                await self.update_mqtt_states()
                
                return {
                    "status": "success",
                    "message": "Cleaning stopped in all zones",
                    "stopped_zones": stopped_zones
                }
                
        except Exception as e:
            logger.error(f"Error stopping cleaning: {e}")
            return {
                "status": "error",
                "message": f"Failed to stop cleaning: {str(e)}"
            }
    
    def list_zones(self) -> List[Dict[str, Any]]:
        """
        List all configured zones.
        
        Returns:
            List of zone information dictionaries
        """
        zones = []
        for zone_id, zone_info in self._zones_data.items():
            zones.append({
                "id": zone_id,
                "name": zone_info.get("name", zone_id),
                "enabled": zone_info.get("enabled", True),
                "status": "cleaning" if zone_id in self._current_cleaning_zones else "idle",
                "devices": zone_info.get("devices", []),
                "default_duration": zone_info.get("default_duration", 30)
            })
        
        return zones
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get overall system status.
        
        Returns:
            System status dictionary
        """
        return {
            "running": self._running,
            "status": self._system_status,
            "cleaning_active": self._cleaning_active,
            "zones_cleaning": self._current_cleaning_zones.copy(),
            "total_zones": len(self._zones_data),
            "enabled_zones": len([z for z in self._zones_data.values() if z.get("enabled", True)]),
            "ha_adapter_available": self.ha_adapter.is_available(),
            "ai_provider_available": self.ai_provider_manager is not None,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _initialize_zones(self) -> None:
        """Initialize zones from configuration"""
        try:
            zones_config = self.config.get("zones", [])
            
            # Add default zone if no zones configured
            if not zones_config:
                zones_config = [{
                    "name": "Living Room",
                    "enabled": True,
                    "devices": []
                }]
            
            for i, zone_config in enumerate(zones_config):
                zone_id = f"zone_{i+1}"
                self._zones_data[zone_id] = {
                    "name": zone_config.get("name", f"Zone {i+1}"),
                    "enabled": zone_config.get("enabled", True),
                    "devices": zone_config.get("devices", []),
                    "default_duration": zone_config.get("duration", 30)
                }
            
            logger.info(f"Initialized {len(self._zones_data)} zones")
            
        except Exception as e:
            logger.error(f"Error initializing zones: {e}")
    
    async def _initialize_devices(self) -> None:
        """Initialize device discovery and management"""
        try:
            # For now, create mock device data
            # In the future, this would integrate with real device discovery
            self._devices_data = {
                "vacuum_001": {
                    "name": "Robot Vacuum",
                    "type": "vacuum",
                    "status": "docked"
                },
                "mop_001": {
                    "name": "Robot Mop",
                    "type": "mop", 
                    "status": "idle"
                }
            }
            
            logger.info(f"Initialized {len(self._devices_data)} devices")
            
        except Exception as e:
            logger.error(f"Error initializing devices: {e}")
    
    async def _start_zone_cleaning(self, zone_id: str, mode: str, duration: Optional[int]) -> None:
        """Start cleaning in a specific zone"""
        try:
            # This would interface with real cleaning devices/systems
            # For now, we'll simulate the operation
            
            logger.info(f"Starting {mode} cleaning in zone {zone_id} for {duration} minutes")
            
            # Call any available devices for this zone
            zone_info = self._zones_data[zone_id]
            for device_id in zone_info.get("devices", []):
                if device_id in self._devices_data:
                    await self._activate_device(device_id, mode)
            
            # If AI provider is available, get intelligent cleaning recommendations
            if self.ai_provider_manager:
                try:
                    # This would use AI to optimize cleaning parameters
                    logger.debug(f"AI-enhanced cleaning started for zone {zone_id}")
                except Exception as e:
                    logger.warning(f"AI enhancement failed for zone {zone_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error starting zone cleaning: {e}")
    
    async def _stop_zone_cleaning(self, zone_id: str) -> None:
        """Stop cleaning in a specific zone"""
        try:
            logger.info(f"Stopping cleaning in zone {zone_id}")
            
            # Stop any devices for this zone
            zone_info = self._zones_data[zone_id]
            for device_id in zone_info.get("devices", []):
                if device_id in self._devices_data:
                    await self._deactivate_device(device_id)
            
        except Exception as e:
            logger.error(f"Error stopping zone cleaning: {e}")
    
    async def _activate_device(self, device_id: str, mode: str) -> None:
        """Activate a cleaning device"""
        try:
            device_info = self._devices_data[device_id]
            device_type = device_info.get("type", "unknown")
            
            # Update device status
            device_info["status"] = "active"
            device_info["mode"] = mode
            
            # Use HA adapter to control real devices if available
            if self.ha_adapter.is_available():
                entity_id = f"{device_type}.{device_id}"
                await self.ha_adapter.call_service(device_type, "start", {
                    "entity_id": entity_id,
                    "mode": mode
                })
            
            logger.info(f"Activated device {device_id} in {mode} mode")
            
        except Exception as e:
            logger.error(f"Error activating device {device_id}: {e}")
    
    async def _deactivate_device(self, device_id: str) -> None:
        """Deactivate a cleaning device"""
        try:
            device_info = self._devices_data[device_id]
            device_type = device_info.get("type", "unknown")
            
            # Update device status
            device_info["status"] = "idle"
            device_info.pop("mode", None)
            
            # Use HA adapter to control real devices if available
            if self.ha_adapter.is_available():
                entity_id = f"{device_type}.{device_id}"
                await self.ha_adapter.call_service(device_type, "stop", {
                    "entity_id": entity_id
                })
            
            logger.info(f"Deactivated device {device_id}")
            
        except Exception as e:
            logger.error(f"Error deactivating device {device_id}: {e}")
    
    async def _update_ha_status(self) -> None:
        """Update Home Assistant entities with current status"""
        try:
            if not self.ha_adapter.is_available():
                return
            
            # Update main system status entity
            await self.ha_adapter.set_state(
                "sensor.aicleaner_status",
                self._system_status,
                {
                    "cleaning_active": self._cleaning_active,
                    "zones_cleaning": len(self._current_cleaning_zones),
                    "total_zones": len(self._zones_data)
                }
            )
            
        except Exception as e:
            logger.error(f"Error updating HA status: {e}")
    
    async def _update_zone_status(self, zone_id: str, status: str) -> None:
        """Update zone status in Home Assistant"""
        try:
            if not self.ha_adapter.is_available():
                return
            
            zone_info = self._zones_data.get(zone_id, {})
            await self.ha_adapter.set_state(
                f"sensor.aicleaner_{zone_id}_status",
                status,
                {
                    "zone_name": zone_info.get("name", zone_id),
                    "enabled": zone_info.get("enabled", True),
                    "devices": len(zone_info.get("devices", []))
                }
            )
            
        except Exception as e:
            logger.error(f"Error updating zone status: {e}")
    
    # MQTT Discovery Methods - Phase 4B
    
    async def _publish_mqtt_discovery(self) -> None:
        """Publish MQTT discovery messages for all zones and devices"""
        try:
            if not self.mqtt_adapter:
                return
            
            logger.info("Publishing MQTT discovery messages")
            
            # Publish zone sensor entities
            for zone_id, zone_info in self._zones_data.items():
                await self._publish_zone_discovery(zone_id, zone_info)
            
            # Publish device entities  
            for device_id, device_info in self._devices_data.items():
                await self._publish_device_discovery(device_id, device_info)
            
            # Publish system status entity
            await self._publish_system_discovery()
            
            logger.info("MQTT discovery messages published successfully")
            
        except Exception as e:
            logger.error(f"Error publishing MQTT discovery: {e}")
    
    async def _publish_zone_discovery(self, zone_id: str, zone_info: Dict[str, Any]) -> None:
        """Publish MQTT discovery for a zone"""
        try:
            # Zone status sensor
            zone_status_device = DeviceInfo(
                entity_id=f"{zone_id}_status",
                name=f"{zone_info['name']} Status",
                device_class="enum",
                icon="mdi:room-service-outline",
                entity_category="diagnostic"
            )
            
            await self.mqtt_adapter.publish_discovery_message(zone_status_device, "sensor")
            
            # Zone cleaning switch (if enabled)
            if zone_info.get("enabled", True):
                zone_switch_device = DeviceInfo(
                    entity_id=f"{zone_id}_cleaning",
                    name=f"{zone_info['name']} Cleaning",
                    device_class=None,
                    icon="mdi:robot-vacuum"
                )
                
                await self.mqtt_adapter.publish_discovery_message(zone_switch_device, "switch")
                
                # Subscribe to cleaning commands
                await self.mqtt_adapter.subscribe_to_commands(
                    f"{zone_id}_cleaning",
                    lambda topic, payload: asyncio.create_task(
                        self._handle_zone_command(zone_id, topic, payload)
                    )
                )
            
            # Publish initial state
            await self._publish_zone_state(zone_id)
            
        except Exception as e:
            logger.error(f"Error publishing zone discovery for {zone_id}: {e}")
    
    async def _publish_device_discovery(self, device_id: str, device_info: Dict[str, Any]) -> None:
        """Publish MQTT discovery for a device"""
        try:
            device_type = device_info.get("type", "unknown")
            device_name = device_info.get("name", device_id)
            
            # Device status sensor
            device_sensor = DeviceInfo(
                entity_id=f"{device_id}_status", 
                name=f"{device_name} Status",
                device_class="enum",
                icon=f"mdi:robot-{device_type}" if device_type in ["vacuum", "mop"] else "mdi:robot",
                entity_category="diagnostic"
            )
            
            await self.mqtt_adapter.publish_discovery_message(device_sensor, "sensor")
            
            # Device control switch
            device_switch = DeviceInfo(
                entity_id=f"{device_id}_control",
                name=f"{device_name} Control", 
                device_class=None,
                icon=f"mdi:robot-{device_type}" if device_type in ["vacuum", "mop"] else "mdi:robot"
            )
            
            await self.mqtt_adapter.publish_discovery_message(device_switch, "switch")
            
            # Subscribe to device commands
            await self.mqtt_adapter.subscribe_to_commands(
                f"{device_id}_control",
                lambda topic, payload: asyncio.create_task(
                    self._handle_device_command(device_id, topic, payload)
                )
            )
            
            # Publish initial state
            await self._publish_device_state(device_id)
            
        except Exception as e:
            logger.error(f"Error publishing device discovery for {device_id}: {e}")
    
    async def _publish_system_discovery(self) -> None:
        """Publish MQTT discovery for system status"""
        try:
            # System status sensor
            system_sensor = DeviceInfo(
                entity_id="system_status",
                name="AICleaner System Status",
                device_class="enum",
                icon="mdi:home-automation",
                entity_category="diagnostic"
            )
            
            await self.mqtt_adapter.publish_discovery_message(system_sensor, "sensor")
            
            # System control switch
            system_switch = DeviceInfo(
                entity_id="system_control",
                name="AICleaner System Control",
                device_class=None,
                icon="mdi:power"
            )
            
            await self.mqtt_adapter.publish_discovery_message(system_switch, "switch")
            
            # Subscribe to system commands
            await self.mqtt_adapter.subscribe_to_commands(
                "system_control",
                lambda topic, payload: asyncio.create_task(
                    self._handle_system_command(topic, payload)
                )
            )
            
            # Publish initial state
            await self._publish_system_state()
            
        except Exception as e:
            logger.error(f"Error publishing system discovery: {e}")
    
    async def _publish_zone_state(self, zone_id: str) -> None:
        """Publish current zone state to MQTT"""
        try:
            if not self.mqtt_adapter:
                return
            
            zone_info = self._zones_data.get(zone_id, {})
            is_cleaning = zone_id in self._current_cleaning_zones
            
            # Zone status
            await self.mqtt_adapter.publish_state(
                f"{zone_id}_status",
                "cleaning" if is_cleaning else "idle",
                {
                    "zone_name": zone_info.get("name", zone_id),
                    "enabled": zone_info.get("enabled", True),
                    "device_count": len(zone_info.get("devices", []))
                }
            )
            
            # Zone cleaning switch
            if zone_info.get("enabled", True):
                await self.mqtt_adapter.publish_state(
                    f"{zone_id}_cleaning",
                    "ON" if is_cleaning else "OFF"
                )
            
        except Exception as e:
            logger.error(f"Error publishing zone state for {zone_id}: {e}")
    
    async def _publish_device_state(self, device_id: str) -> None:
        """Publish current device state to MQTT"""
        try:
            if not self.mqtt_adapter:
                return
            
            device_info = self._devices_data.get(device_id, {})
            status = device_info.get("status", "idle")
            
            # Device status
            await self.mqtt_adapter.publish_state(
                f"{device_id}_status",
                status,
                {
                    "device_name": device_info.get("name", device_id),
                    "device_type": device_info.get("type", "unknown"),
                    "mode": device_info.get("mode")
                }
            )
            
            # Device control switch
            await self.mqtt_adapter.publish_state(
                f"{device_id}_control",
                "ON" if status == "active" else "OFF"
            )
            
        except Exception as e:
            logger.error(f"Error publishing device state for {device_id}: {e}")
    
    async def _publish_system_state(self) -> None:
        """Publish current system state to MQTT"""
        try:
            if not self.mqtt_adapter:
                return
            
            # System status
            await self.mqtt_adapter.publish_state(
                "system_status",
                self._system_status,
                {
                    "running": self._running,
                    "cleaning_active": self._cleaning_active,
                    "zones_cleaning": len(self._current_cleaning_zones),
                    "total_zones": len(self._zones_data),
                    "ha_available": self.ha_adapter.is_available(),
                    "mqtt_available": self.mqtt_adapter.is_connected() if self.mqtt_adapter else False
                }
            )
            
            # System control switch
            await self.mqtt_adapter.publish_state(
                "system_control",
                "ON" if self._running else "OFF"
            )
            
        except Exception as e:
            logger.error(f"Error publishing system state: {e}")
    
    # MQTT Command Handlers
    
    async def _handle_zone_command(self, zone_id: str, topic: str, payload: Any) -> None:
        """Handle MQTT command for zone control"""
        try:
            logger.info(f"Received zone command for {zone_id}: {payload}")
            
            if isinstance(payload, str):
                command = payload.upper()
            elif isinstance(payload, dict):
                command = payload.get("state", "").upper()
            else:
                command = str(payload).upper()
            
            if command == "ON":
                # Start cleaning in zone
                result = await self.clean_zone_by_id(zone_id, "normal")
                logger.info(f"Zone cleaning started via MQTT: {result}")
            elif command == "OFF":
                # Stop cleaning in zone
                result = await self.stop_cleaning(zone_id)
                logger.info(f"Zone cleaning stopped via MQTT: {result}")
            
            # Update state
            await self._publish_zone_state(zone_id)
            
        except Exception as e:
            logger.error(f"Error handling zone command: {e}")
    
    async def _handle_device_command(self, device_id: str, topic: str, payload: Any) -> None:
        """Handle MQTT command for device control"""
        try:
            logger.info(f"Received device command for {device_id}: {payload}")
            
            if isinstance(payload, str):
                command = payload.upper()
            elif isinstance(payload, dict):
                command = payload.get("state", "").upper()
            else:
                command = str(payload).upper()
            
            if command == "ON":
                # Activate device
                await self._activate_device(device_id, "normal")
            elif command == "OFF":
                # Deactivate device
                await self._deactivate_device(device_id)
            
            # Update state
            await self._publish_device_state(device_id)
            
        except Exception as e:
            logger.error(f"Error handling device command: {e}")
    
    async def _handle_system_command(self, topic: str, payload: Any) -> None:
        """Handle MQTT command for system control"""
        try:
            logger.info(f"Received system command: {payload}")
            
            if isinstance(payload, str):
                command = payload.upper()
            elif isinstance(payload, dict):
                command = payload.get("state", "").upper()
            else:
                command = str(payload).upper()
            
            if command == "ON":
                # Start system if not running
                if not self._running:
                    await self.start()
            elif command == "OFF":
                # Stop system
                await self.stop()
            
            # Update state
            await self._publish_system_state()
            
        except Exception as e:
            logger.error(f"Error handling system command: {e}")
    
    async def update_mqtt_states(self) -> None:
        """Update all MQTT entity states (called after operations)"""
        try:
            if not self.mqtt_adapter or not self.mqtt_adapter.is_connected():
                return
            
            # Update system state
            await self._publish_system_state()
            
            # Update all zone states
            for zone_id in self._zones_data.keys():
                await self._publish_zone_state(zone_id)
            
            # Update all device states
            for device_id in self._devices_data.keys():
                await self._publish_device_state(device_id)
            
        except Exception as e:
            logger.error(f"Error updating MQTT states: {e}")