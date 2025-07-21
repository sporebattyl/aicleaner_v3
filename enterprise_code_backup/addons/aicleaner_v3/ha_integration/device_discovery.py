"""
Home Assistant Device Discovery Service
Phase 4A: Enhanced HA Integration

Discovers and integrates with Home Assistant devices to provide
intelligent automation capabilities for AICleaner v3.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum

from homeassistant.core import HomeAssistant, Event
from homeassistant.const import EVENT_STATE_CHANGED, STATE_ON, STATE_OFF
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.device_registry import async_get as async_get_device_registry

from utils.unified_logger import get_logger

logger = get_logger(__name__)

class DeviceType(Enum):
    """Supported device types for automation"""
    LIGHT = "light"
    SWITCH = "switch"
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    CAMERA = "camera"
    CLIMATE = "climate"
    COVER = "cover"
    FAN = "fan"
    LOCK = "lock"
    VACUUM = "vacuum"
    MEDIA_PLAYER = "media_player"
    WATER_HEATER = "water_heater"
    ALARM_CONTROL_PANEL = "alarm_control_panel"

@dataclass
class DiscoveredDevice:
    """Represents a discovered Home Assistant device"""
    entity_id: str
    name: str
    device_type: DeviceType
    domain: str
    state: str
    attributes: Dict[str, Any]
    device_id: Optional[str] = None
    area_id: Optional[str] = None
    area_name: Optional[str] = None
    capabilities: List[str] = None
    last_seen: Optional[datetime] = None
    automation_eligible: bool = True
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.last_seen is None:
            self.last_seen = datetime.now()

class HADeviceDiscovery:
    """
    Home Assistant Device Discovery Service
    
    Discovers and monitors Home Assistant devices for automation integration
    """
    
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.discovered_devices: Dict[str, DiscoveredDevice] = {}
        self.monitored_entities: Set[str] = set()
        self.device_registry = None
        self.entity_registry = None
        self._listeners: List[callable] = []
        
    async def async_initialize(self):
        """Initialize the device discovery service"""
        try:
            # Get registries
            self.device_registry = async_get_device_registry(self.hass)
            self.entity_registry = async_get_entity_registry(self.hass)
            
            # Discover existing devices
            await self._discover_existing_devices()
            
            # Set up event listeners
            self._setup_event_listeners()
            
            logger.info(f"Device discovery initialized with {len(self.discovered_devices)} devices")
            
        except Exception as e:
            logger.error(f"Failed to initialize device discovery: {e}")
            raise
    
    async def cleanup(self):
        """Clean up resources"""
        for listener in self._listeners:
            listener()
        self._listeners.clear()
    
    async def _discover_existing_devices(self):
        """Discover existing Home Assistant devices"""
        try:
            # Get all entities from the registry
            entity_entries = list(self.entity_registry.entities.values())
            
            for entry in entity_entries:
                try:
                    # Get entity state
                    state = self.hass.states.get(entry.entity_id)
                    if not state:
                        continue
                    
                    # Determine device type
                    device_type = self._get_device_type(entry.entity_id)
                    if not device_type:
                        continue
                    
                    # Get device info
                    device_entry = None
                    area_name = None
                    
                    if entry.device_id:
                        device_entry = self.device_registry.async_get(entry.device_id)
                        if device_entry and device_entry.area_id:
                            area_info = self.hass.helpers.area_registry.async_get(device_entry.area_id)
                            if area_info:
                                area_name = area_info.name
                    
                    # Create discovered device
                    device = DiscoveredDevice(
                        entity_id=entry.entity_id,
                        name=entry.name or state.name,
                        device_type=device_type,
                        domain=entry.domain,
                        state=state.state,
                        attributes=dict(state.attributes),
                        device_id=entry.device_id,
                        area_id=device_entry.area_id if device_entry else None,
                        area_name=area_name,
                        capabilities=self._extract_capabilities(state),
                        automation_eligible=self._is_automation_eligible(entry.entity_id, state)
                    )
                    
                    self.discovered_devices[entry.entity_id] = device
                    
                except Exception as e:
                    logger.warning(f"Error processing entity {entry.entity_id}: {e}")
                    continue
            
            logger.info(f"Discovered {len(self.discovered_devices)} devices")
            
        except Exception as e:
            logger.error(f"Error discovering existing devices: {e}")
            raise
    
    def _setup_event_listeners(self):
        """Set up event listeners for device changes"""
        try:
            # Listen for state changes
            self._listeners.append(
                async_track_state_change_event(
                    self.hass,
                    list(self.discovered_devices.keys()),
                    self._handle_state_change
                )
            )
            
            # Listen for entity registry changes
            self._listeners.append(
                self.hass.bus.async_listen(
                    "entity_registry_updated",
                    self._handle_entity_registry_change
                )
            )
            
            # Listen for device registry changes
            self._listeners.append(
                self.hass.bus.async_listen(
                    "device_registry_updated",
                    self._handle_device_registry_change
                )
            )
            
            logger.info("Device discovery event listeners set up")
            
        except Exception as e:
            logger.error(f"Error setting up event listeners: {e}")
            raise
    
    async def _handle_state_change(self, event: Event):
        """Handle entity state changes"""
        try:
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            
            if entity_id in self.discovered_devices and new_state:
                device = self.discovered_devices[entity_id]
                device.state = new_state.state
                device.attributes = dict(new_state.attributes)
                device.last_seen = datetime.now()
                
                logger.debug(f"Updated device state: {entity_id} = {new_state.state}")
                
                # Notify listeners about device update
                await self._notify_device_update(device)
                
        except Exception as e:
            logger.error(f"Error handling state change: {e}")
    
    async def _handle_entity_registry_change(self, event: Event):
        """Handle entity registry changes"""
        try:
            action = event.data.get("action")
            entity_id = event.data.get("entity_id")
            
            if action == "create" and entity_id:
                # New entity added
                await self._add_new_entity(entity_id)
            elif action == "remove" and entity_id:
                # Entity removed
                if entity_id in self.discovered_devices:
                    del self.discovered_devices[entity_id]
                    logger.info(f"Removed device: {entity_id}")
            elif action == "update" and entity_id:
                # Entity updated
                if entity_id in self.discovered_devices:
                    await self._update_existing_entity(entity_id)
                    
        except Exception as e:
            logger.error(f"Error handling entity registry change: {e}")
    
    async def _handle_device_registry_change(self, event: Event):
        """Handle device registry changes"""
        try:
            action = event.data.get("action")
            device_id = event.data.get("device_id")
            
            if action in ("create", "update") and device_id:
                # Update devices associated with this device_id
                for device in self.discovered_devices.values():
                    if device.device_id == device_id:
                        await self._update_device_info(device)
                        
        except Exception as e:
            logger.error(f"Error handling device registry change: {e}")
    
    async def _add_new_entity(self, entity_id: str):
        """Add a newly discovered entity"""
        try:
            entry = self.entity_registry.async_get(entity_id)
            if not entry:
                return
            
            state = self.hass.states.get(entity_id)
            if not state:
                return
            
            device_type = self._get_device_type(entity_id)
            if not device_type:
                return
            
            # Get device info
            device_entry = None
            area_name = None
            
            if entry.device_id:
                device_entry = self.device_registry.async_get(entry.device_id)
                if device_entry and device_entry.area_id:
                    area_info = self.hass.helpers.area_registry.async_get(device_entry.area_id)
                    if area_info:
                        area_name = area_info.name
            
            # Create discovered device
            device = DiscoveredDevice(
                entity_id=entity_id,
                name=entry.name or state.name,
                device_type=device_type,
                domain=entry.domain,
                state=state.state,
                attributes=dict(state.attributes),
                device_id=entry.device_id,
                area_id=device_entry.area_id if device_entry else None,
                area_name=area_name,
                capabilities=self._extract_capabilities(state),
                automation_eligible=self._is_automation_eligible(entity_id, state)
            )
            
            self.discovered_devices[entity_id] = device
            logger.info(f"Added new device: {entity_id}")
            
            # Notify listeners about new device
            await self._notify_device_added(device)
            
        except Exception as e:
            logger.error(f"Error adding new entity {entity_id}: {e}")
    
    async def _update_existing_entity(self, entity_id: str):
        """Update an existing entity"""
        try:
            if entity_id not in self.discovered_devices:
                return
            
            device = self.discovered_devices[entity_id]
            entry = self.entity_registry.async_get(entity_id)
            state = self.hass.states.get(entity_id)
            
            if entry and state:
                device.name = entry.name or state.name
                device.state = state.state
                device.attributes = dict(state.attributes)
                device.capabilities = self._extract_capabilities(state)
                device.automation_eligible = self._is_automation_eligible(entity_id, state)
                device.last_seen = datetime.now()
                
                await self._update_device_info(device)
                
                logger.debug(f"Updated existing device: {entity_id}")
                
        except Exception as e:
            logger.error(f"Error updating existing entity {entity_id}: {e}")
    
    async def _update_device_info(self, device: DiscoveredDevice):
        """Update device information from registries"""
        try:
            if device.device_id:
                device_entry = self.device_registry.async_get(device.device_id)
                if device_entry and device_entry.area_id:
                    area_info = self.hass.helpers.area_registry.async_get(device_entry.area_id)
                    if area_info:
                        device.area_id = device_entry.area_id
                        device.area_name = area_info.name
                        
        except Exception as e:
            logger.error(f"Error updating device info for {device.entity_id}: {e}")
    
    def _get_device_type(self, entity_id: str) -> Optional[DeviceType]:
        """Determine device type from entity ID"""
        try:
            domain = entity_id.split(".")[0]
            
            # Map domains to device types
            domain_mapping = {
                "light": DeviceType.LIGHT,
                "switch": DeviceType.SWITCH,
                "sensor": DeviceType.SENSOR,
                "binary_sensor": DeviceType.BINARY_SENSOR,
                "camera": DeviceType.CAMERA,
                "climate": DeviceType.CLIMATE,
                "cover": DeviceType.COVER,
                "fan": DeviceType.FAN,
                "lock": DeviceType.LOCK,
                "vacuum": DeviceType.VACUUM,
                "media_player": DeviceType.MEDIA_PLAYER,
                "water_heater": DeviceType.WATER_HEATER,
                "alarm_control_panel": DeviceType.ALARM_CONTROL_PANEL
            }
            
            return domain_mapping.get(domain)
            
        except Exception as e:
            logger.error(f"Error determining device type for {entity_id}: {e}")
            return None
    
    def _extract_capabilities(self, state) -> List[str]:
        """Extract device capabilities from state"""
        capabilities = []
        
        try:
            # Check for common capabilities
            if hasattr(state, 'attributes'):
                attrs = state.attributes
                
                # Brightness support
                if 'brightness' in attrs:
                    capabilities.append('brightness')
                
                # Color support
                if 'rgb_color' in attrs or 'color_temp' in attrs:
                    capabilities.append('color')
                
                # Temperature support
                if 'temperature' in attrs:
                    capabilities.append('temperature')
                
                # Position support
                if 'position' in attrs:
                    capabilities.append('position')
                
                # Volume support
                if 'volume_level' in attrs:
                    capabilities.append('volume')
                
                # Motion detection
                if 'motion_detection' in attrs:
                    capabilities.append('motion_detection')
                
                # Battery level
                if 'battery_level' in attrs:
                    capabilities.append('battery')
                
        except Exception as e:
            logger.error(f"Error extracting capabilities: {e}")
        
        return capabilities
    
    def _is_automation_eligible(self, entity_id: str, state) -> bool:
        """Determine if device is eligible for automation"""
        try:
            # Skip certain entities
            skip_patterns = [
                "sun.",
                "weather.",
                "person.",
                "zone.",
                "automation.",
                "script.",
                "input_",
                "timer.",
                "counter.",
                "persistent_notification."
            ]
            
            for pattern in skip_patterns:
                if entity_id.startswith(pattern):
                    return False
            
            # Check for disabled entities
            if hasattr(state, 'attributes'):
                if state.attributes.get('disabled', False):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking automation eligibility for {entity_id}: {e}")
            return False
    
    async def _notify_device_added(self, device: DiscoveredDevice):
        """Notify listeners about new device"""
        try:
            logger.info(f"New device discovered: {device.entity_id} ({device.name})")
            # Implement notification logic for new devices
            
        except Exception as e:
            logger.error(f"Error notifying device added: {e}")
    
    async def _notify_device_update(self, device: DiscoveredDevice):
        """Notify listeners about device update"""
        try:
            logger.debug(f"Device updated: {device.entity_id}")
            # Implement notification logic for device updates
            
        except Exception as e:
            logger.error(f"Error notifying device update: {e}")
    
    # Public API methods
    
    def get_devices_by_type(self, device_type: DeviceType) -> List[DiscoveredDevice]:
        """Get devices filtered by type"""
        return [device for device in self.discovered_devices.values() 
                if device.device_type == device_type]
    
    def get_devices_by_area(self, area_name: str) -> List[DiscoveredDevice]:
        """Get devices filtered by area"""
        return [device for device in self.discovered_devices.values()
                if device.area_name == area_name]
    
    def get_automation_eligible_devices(self) -> List[DiscoveredDevice]:
        """Get devices eligible for automation"""
        return [device for device in self.discovered_devices.values()
                if device.automation_eligible]
    
    def get_device_by_entity_id(self, entity_id: str) -> Optional[DiscoveredDevice]:
        """Get device by entity ID"""
        return self.discovered_devices.get(entity_id)
    
    def get_device_count(self) -> int:
        """Get total number of discovered devices"""
        return len(self.discovered_devices)
    
    def get_device_statistics(self) -> Dict[str, Any]:
        """Get device discovery statistics"""
        stats = {
            "total_devices": len(self.discovered_devices),
            "automation_eligible": len(self.get_automation_eligible_devices()),
            "by_type": {},
            "by_area": {},
            "with_capabilities": 0
        }
        
        # Count by type
        for device_type in DeviceType:
            count = len(self.get_devices_by_type(device_type))
            if count > 0:
                stats["by_type"][device_type.value] = count
        
        # Count by area
        areas = set()
        for device in self.discovered_devices.values():
            if device.area_name:
                areas.add(device.area_name)
        
        for area in areas:
            stats["by_area"][area] = len(self.get_devices_by_area(area))
        
        # Count devices with capabilities
        stats["with_capabilities"] = len([
            device for device in self.discovered_devices.values()
            if device.capabilities
        ])
        
        return stats
    
    def get_devices_summary(self) -> List[Dict[str, Any]]:
        """Get a summary of all discovered devices"""
        return [
            {
                "entity_id": device.entity_id,
                "name": device.name,
                "type": device.device_type.value,
                "domain": device.domain,
                "state": device.state,
                "area": device.area_name,
                "capabilities": device.capabilities,
                "automation_eligible": device.automation_eligible,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None
            }
            for device in self.discovered_devices.values()
        ]