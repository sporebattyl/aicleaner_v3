"""
Phase 3B: Home Assistant Integration
Seamless integration with Home Assistant for zone management and device control.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from .models import Zone, Device, Rule, DeviceType
from .logger import setup_logger
from .utils import sanitize_name, retry


class HomeAssistantIntegration:
    """
    Home Assistant integration for zone management.
    
    Provides seamless integration with Home Assistant including device
    registration, state synchronization, and service exposure.
    """
    
    def __init__(self, hass, config: Dict[str, Any]):
        """
        Initialize Home Assistant integration.
        
        Args:
            hass: Home Assistant instance
            config: Configuration dictionary
        """
        self.hass = hass
        self.config = config
        self.logger = setup_logger(__name__)
        
        # Integration configuration
        self.domain = 'aicleaner_zones'
        self.entity_prefix = 'aicleaner_zone'
        
        # State tracking
        self.registered_zones: Dict[str, str] = {}  # zone_id -> entity_id
        self.registered_devices: Dict[str, str] = {}  # device_id -> entity_id
        self.zone_entities: Dict[str, Any] = {}  # entity_id -> entity object
        
        # Service definitions
        self.services = {
            'create_zone': self._service_create_zone,
            'update_zone': self._service_update_zone,
            'delete_zone': self._service_delete_zone,
            'execute_zone_automation': self._service_execute_automation,
            'optimize_zone': self._service_optimize_zone,
            'get_zone_status': self._service_get_zone_status
        }
        
        self.logger.info("Home Assistant Integration initialized")
    
    async def initialize(self) -> None:
        """Initialize Home Assistant integration components."""
        try:
            # Register domain
            await self._register_domain()
            
            # Register services
            await self._register_services()
            
            # Set up event listeners
            await self._setup_event_listeners()
            
            self.logger.info("Home Assistant integration initialized successfully")
        
        except Exception as e:
            self.logger.error(f"Failed to initialize Home Assistant integration: {e}")
            raise
    
    async def _register_domain(self) -> None:
        """Register the aicleaner_zones domain with Home Assistant."""
        try:
            # Register domain if not already registered
            if self.domain not in self.hass.data:
                self.hass.data[self.domain] = {
                    'zones': {},
                    'devices': {},
                    'integration': self
                }
            
            self.logger.info(f"Registered domain: {self.domain}")
        
        except Exception as e:
            self.logger.error(f"Failed to register domain: {e}")
            raise
    
    async def _register_services(self) -> None:
        """Register zone management services with Home Assistant."""
        try:
            for service_name, service_handler in self.services.items():
                self.hass.services.async_register(
                    self.domain,
                    service_name,
                    service_handler,
                    schema=self._get_service_schema(service_name)
                )
            
            self.logger.info(f"Registered {len(self.services)} services")
        
        except Exception as e:
            self.logger.error(f"Failed to register services: {e}")
            raise
    
    def _get_service_schema(self, service_name: str) -> Dict[str, Any]:
        """Get service schema for validation."""
        schemas = {
            'create_zone': {
                'zone_config': {'required': True, 'type': 'dict'}
            },
            'update_zone': {
                'zone_id': {'required': True, 'type': 'string'},
                'zone_config': {'required': True, 'type': 'dict'}
            },
            'delete_zone': {
                'zone_id': {'required': True, 'type': 'string'}
            },
            'execute_zone_automation': {
                'zone_id': {'required': True, 'type': 'string'}
            },
            'optimize_zone': {
                'zone_id': {'required': True, 'type': 'string'}
            },
            'get_zone_status': {
                'zone_id': {'required': True, 'type': 'string'}
            }
        }
        
        return schemas.get(service_name, {})
    
    async def _setup_event_listeners(self) -> None:
        """Set up Home Assistant event listeners."""
        try:
            # Listen for state changes
            self.hass.bus.async_listen('state_changed', self._handle_state_change)
            
            # Listen for device registry events
            self.hass.bus.async_listen('device_registry_updated', self._handle_device_registry_update)
            
            self.logger.info("Event listeners configured")
        
        except Exception as e:
            self.logger.error(f"Failed to setup event listeners: {e}")
    
    @retry(tries=3, delay=1.0)
    async def register_zone(self, zone: Zone) -> None:
        """
        Register a zone with Home Assistant.
        
        Args:
            zone: Zone to register
        """
        try:
            entity_id = f"{self.entity_prefix}.{zone.id}"
            
            # Create zone entity
            zone_entity = await self._create_zone_entity(zone, entity_id)
            
            if zone_entity:
                # Store entity mapping
                self.registered_zones[zone.id] = entity_id
                self.zone_entities[entity_id] = zone_entity
                
                # Update Home Assistant data
                self.hass.data[self.domain]['zones'][zone.id] = zone.dict()
                
                # Register zone devices
                for device in zone.devices:
                    await self._register_zone_device(zone, device)
                
                self.logger.info(f"Registered zone '{zone.name}' with entity ID: {entity_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to register zone '{zone.name}': {e}")
            raise
    
    async def _create_zone_entity(self, zone: Zone, entity_id: str) -> Optional[Any]:
        """Create Home Assistant entity for zone."""
        try:
            # Create zone state attributes
            attributes = {
                'zone_id': zone.id,
                'zone_name': zone.name,
                'description': zone.description,
                'location': zone.location,
                'room_type': zone.room_type,
                'area_size_sqm': zone.area_size_sqm,
                'device_count': len(zone.devices),
                'rule_count': len(zone.rules),
                'is_active': zone.is_active,
                'auto_optimization': zone.auto_optimization,
                'health_score': zone.get_zone_health_score(),
                'energy_consumption': zone.calculate_energy_consumption(),
                'date_created': zone.date_created.isoformat(),
                'last_modified': zone.last_modified.isoformat(),
                'performance_metrics': zone.performance_metrics.dict()
            }
            
            # Determine zone state
            if not zone.is_active:
                state = 'inactive'
            elif zone.get_zone_health_score() < 0.7:
                state = 'warning'
            elif any(not d.is_available() for d in zone.devices):
                state = 'partial'
            else:
                state = 'active'
            
            # Create entity state
            self.hass.states.async_set(
                entity_id,
                state,
                attributes,
                force_update=True
            )
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to create zone entity: {e}")
            return None
    
    async def _register_zone_device(self, zone: Zone, device: Device) -> None:
        """Register a zone device with Home Assistant."""
        try:
            device_entity_id = f"{self.domain}.{zone.id}_{device.id}".replace('.', '_')
            
            # Create device attributes
            attributes = {
                'zone_id': zone.id,
                'zone_name': zone.name,
                'device_id': device.id,
                'device_name': device.name,
                'device_type': device.type,
                'manufacturer': device.manufacturer,
                'model': device.model,
                'ip_address': device.ip_address,
                'mac_address': device.mac_address,
                'polling_frequency': device.polling_frequency,
                'zone_role': device.zone_role,
                'is_active': device.is_active,
                'power_consumption': device.power_consumption,
                'response_time_ms': device.response_time_ms,
                'reliability_score': device.reliability_score,
                'error_count': device.error_count,
                'last_seen': device.last_seen.isoformat() if device.last_seen else None,
                'capabilities': device.capabilities,
                'current_state': device.current_state
            }
            
            # Determine device state
            if not device.is_active:
                state = 'inactive'
            elif not device.is_available():
                state = 'unavailable'
            elif device.reliability_score < 0.8:
                state = 'warning'
            else:
                state = 'available'
            
            # Create device entity
            self.hass.states.async_set(
                device_entity_id,
                state,
                attributes,
                force_update=True
            )
            
            # Store device mapping
            self.registered_devices[device.id] = device_entity_id
            
            self.logger.debug(f"Registered device '{device.name}' with entity ID: {device_entity_id}")
        
        except Exception as e:
            self.logger.error(f"Failed to register device '{device.name}': {e}")
    
    @retry(tries=3, delay=1.0)
    async def update_zone(self, zone: Zone) -> None:
        """
        Update zone in Home Assistant.
        
        Args:
            zone: Updated zone
        """
        try:
            if zone.id not in self.registered_zones:
                self.logger.warning(f"Zone '{zone.name}' not registered, registering now")
                await self.register_zone(zone)
                return
            
            entity_id = self.registered_zones[zone.id]
            
            # Update zone entity
            await self._create_zone_entity(zone, entity_id)
            
            # Update Home Assistant data
            self.hass.data[self.domain]['zones'][zone.id] = zone.dict()
            
            # Update zone devices
            for device in zone.devices:
                await self._register_zone_device(zone, device)
            
            self.logger.info(f"Updated zone '{zone.name}' in Home Assistant")
        
        except Exception as e:
            self.logger.error(f"Failed to update zone '{zone.name}': {e}")
            raise
    
    @retry(tries=3, delay=1.0)
    async def remove_zone(self, zone: Zone) -> None:
        """
        Remove zone from Home Assistant.
        
        Args:
            zone: Zone to remove
        """
        try:
            if zone.id not in self.registered_zones:
                self.logger.warning(f"Zone '{zone.name}' not registered")
                return
            
            entity_id = self.registered_zones[zone.id]
            
            # Remove zone entity
            self.hass.states.async_remove(entity_id)
            
            # Remove zone devices
            for device in zone.devices:
                if device.id in self.registered_devices:
                    device_entity_id = self.registered_devices[device.id]
                    self.hass.states.async_remove(device_entity_id)
                    del self.registered_devices[device.id]
            
            # Clean up mappings
            del self.registered_zones[zone.id]
            if entity_id in self.zone_entities:
                del self.zone_entities[entity_id]
            
            # Update Home Assistant data
            if zone.id in self.hass.data[self.domain]['zones']:
                del self.hass.data[self.domain]['zones'][zone.id]
            
            self.logger.info(f"Removed zone '{zone.name}' from Home Assistant")
        
        except Exception as e:
            self.logger.error(f"Failed to remove zone '{zone.name}': {e}")
            raise
    
    async def _handle_state_change(self, event) -> None:
        """Handle Home Assistant state change events."""
        try:
            event_data = event.data
            entity_id = event_data.get('entity_id')
            new_state = event_data.get('new_state')
            
            # Check if it's a zone-related entity
            if not entity_id or not entity_id.startswith(self.domain):
                return
            
            # Update zone data if needed
            if entity_id in self.zone_entities:
                await self._sync_zone_state(entity_id, new_state)
        
        except Exception as e:
            self.logger.error(f"Error handling state change: {e}")
    
    async def _handle_device_registry_update(self, event) -> None:
        """Handle device registry update events."""
        try:
            # Sync with device discovery if needed
            self.logger.debug("Device registry updated")
        
        except Exception as e:
            self.logger.error(f"Error handling device registry update: {e}")
    
    async def _sync_zone_state(self, entity_id: str, new_state) -> None:
        """Synchronize zone state changes."""
        try:
            if not new_state:
                return
            
            # Find zone ID from entity ID
            zone_id = None
            for zid, eid in self.registered_zones.items():
                if eid == entity_id:
                    zone_id = zid
                    break
            
            if not zone_id:
                return
            
            # Update zone data in Home Assistant
            if zone_id in self.hass.data[self.domain]['zones']:
                zone_data = self.hass.data[self.domain]['zones'][zone_id]
                # Sync any state changes back to zone data
                self.logger.debug(f"Synced state for zone: {zone_id}")
        
        except Exception as e:
            self.logger.error(f"Error syncing zone state: {e}")
    
    # Service handlers
    async def _service_create_zone(self, call) -> None:
        """Handle create_zone service call."""
        try:
            zone_config = call.data.get('zone_config')
            
            # Get zone manager from Home Assistant data
            zone_manager = self.hass.data.get('zone_manager')
            if not zone_manager:
                self.logger.error("Zone manager not available")
                return
            
            # Create zone
            zone = await zone_manager.create_zone(zone_config)
            
            self.logger.info(f"Created zone via service: {zone.name}")
        
        except Exception as e:
            self.logger.error(f"Error in create_zone service: {e}")
    
    async def _service_update_zone(self, call) -> None:
        """Handle update_zone service call."""
        try:
            zone_id = call.data.get('zone_id')
            zone_config = call.data.get('zone_config')
            
            # Get zone manager
            zone_manager = self.hass.data.get('zone_manager')
            if not zone_manager:
                self.logger.error("Zone manager not available")
                return
            
            # Update zone
            zone = await zone_manager.update_zone(zone_id, zone_config)
            
            self.logger.info(f"Updated zone via service: {zone.name}")
        
        except Exception as e:
            self.logger.error(f"Error in update_zone service: {e}")
    
    async def _service_delete_zone(self, call) -> None:
        """Handle delete_zone service call."""
        try:
            zone_id = call.data.get('zone_id')
            
            # Get zone manager
            zone_manager = self.hass.data.get('zone_manager')
            if not zone_manager:
                self.logger.error("Zone manager not available")
                return
            
            # Delete zone
            success = await zone_manager.delete_zone(zone_id)
            
            if success:
                self.logger.info(f"Deleted zone via service: {zone_id}")
            else:
                self.logger.error(f"Failed to delete zone: {zone_id}")
        
        except Exception as e:
            self.logger.error(f"Error in delete_zone service: {e}")
    
    async def _service_execute_automation(self, call) -> None:
        """Handle execute_zone_automation service call."""
        try:
            zone_id = call.data.get('zone_id')
            
            # Get zone manager
            zone_manager = self.hass.data.get('zone_manager')
            if not zone_manager:
                self.logger.error("Zone manager not available")
                return
            
            # Execute automation
            result = await zone_manager.execute_zone_automation(zone_id)
            
            self.logger.info(f"Executed automation for zone {zone_id}: {result}")
        
        except Exception as e:
            self.logger.error(f"Error in execute_automation service: {e}")
    
    async def _service_optimize_zone(self, call) -> None:
        """Handle optimize_zone service call."""
        try:
            zone_id = call.data.get('zone_id')
            
            # Get zone manager
            zone_manager = self.hass.data.get('zone_manager')
            if not zone_manager:
                self.logger.error("Zone manager not available")
                return
            
            # Optimize zone
            result = await zone_manager.optimize_zone(zone_id)
            
            self.logger.info(f"Optimized zone {zone_id}: {result}")
        
        except Exception as e:
            self.logger.error(f"Error in optimize_zone service: {e}")
    
    async def _service_get_zone_status(self, call) -> None:
        """Handle get_zone_status service call."""
        try:
            zone_id = call.data.get('zone_id')
            
            # Get zone manager
            zone_manager = self.hass.data.get('zone_manager')
            if not zone_manager:
                self.logger.error("Zone manager not available")
                return
            
            # Get zone status
            zone = await zone_manager.get_zone(zone_id)
            if zone:
                status = {
                    'zone_id': zone.id,
                    'name': zone.name,
                    'is_active': zone.is_active,
                    'health_score': zone.get_zone_health_score(),
                    'energy_consumption': zone.calculate_energy_consumption(),
                    'device_count': len(zone.devices),
                    'rule_count': len(zone.rules)
                }
                
                self.logger.info(f"Zone status for {zone_id}: {status}")
            else:
                self.logger.error(f"Zone not found: {zone_id}")
        
        except Exception as e:
            self.logger.error(f"Error in get_zone_status service: {e}")
    
    def get_zone_entity_id(self, zone_id: str) -> Optional[str]:
        """Get Home Assistant entity ID for a zone."""
        return self.registered_zones.get(zone_id)
    
    def get_device_entity_id(self, device_id: str) -> Optional[str]:
        """Get Home Assistant entity ID for a device."""
        return self.registered_devices.get(device_id)
    
    def get_registered_zones(self) -> Dict[str, str]:
        """Get all registered zones."""
        return self.registered_zones.copy()
    
    async def trigger_zone_event(self, zone_id: str, event_type: str, event_data: Dict[str, Any]) -> None:
        """Trigger a zone-related event in Home Assistant."""
        try:
            self.hass.bus.async_fire(
                f"{self.domain}_{event_type}",
                {
                    'zone_id': zone_id,
                    **event_data
                }
            )
        
        except Exception as e:
            self.logger.error(f"Error triggering zone event: {e}")


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    from .models import Zone, Device, DeviceType
    
    async def test_ha_integration():
        """Test Home Assistant integration functionality."""
        
        # Mock Home Assistant object
        class MockHass:
            def __init__(self):
                self.data = {}
                self.states = MockStates()
                self.services = MockServices()
                self.bus = MockBus()
        
        class MockStates:
            def async_set(self, entity_id, state, attributes, force_update=False):
                print(f"Entity {entity_id}: {state}")
            
            def async_remove(self, entity_id):
                print(f"Removed entity: {entity_id}")
        
        class MockServices:
            def async_register(self, domain, service, handler, schema=None):
                print(f"Registered service: {domain}.{service}")
        
        class MockBus:
            def async_listen(self, event_type, handler):
                print(f"Listening for: {event_type}")
            
            def async_fire(self, event_type, data):
                print(f"Fired event: {event_type}")
        
        hass = MockHass()
        config = {}
        
        integration = HomeAssistantIntegration(hass, config)
        await integration.initialize()
        
        # Test zone registration
        zone = Zone(
            id='test_living_room',
            name='Test Living Room',
            devices=[
                Device(
                    id='light1',
                    name='Living Room Light',
                    type=DeviceType.LIGHT
                )
            ]
        )
        
        await integration.register_zone(zone)
        
        # Test zone update
        zone.description = "Updated description"
        await integration.update_zone(zone)
        
        # Test zone removal
        await integration.remove_zone(zone)
        
        print("Home Assistant integration test completed!")
    
    # Run test
    asyncio.run(test_ha_integration())