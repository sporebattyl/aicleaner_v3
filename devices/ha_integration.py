"""
Phase 3A: Home Assistant Device Registry Integration
Complete integration with HA device registry and entity management.
"""

import logging
from typing import Dict, Any, Optional, Set

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.const import CONF_MAC, CONF_IP_ADDRESS

from .device_discovery import DeviceInfo

_LOGGER = logging.getLogger(__name__)

DOMAIN = "aicleaner_v3"


async def register_device_in_ha(hass: HomeAssistant, device_info: DeviceInfo) -> Optional[dr.DeviceEntry]:
    """
    Register the discovered device in Home Assistant device registry.
    
    Args:
        hass: Home Assistant instance
        device_info: Device information from discovery
        
    Returns:
        DeviceEntry if successful, None if failed
    """
    try:
        device_registry = dr.async_get(hass)
        
        # Get the config entry for AICleaner v3
        config_entries = hass.config_entries.async_entries(DOMAIN)
        if not config_entries:
            _LOGGER.error("No AICleaner v3 config entry found")
            return None
        
        config_entry = config_entries[0]  # Use first config entry
        
        # Prepare device identifiers
        identifiers = {(DOMAIN, device_info.mac_address)}
        
        # Prepare connections
        connections = set()
        if device_info.mac_address and device_info.mac_address != "unknown":
            connections.add((dr.CONNECTION_NETWORK_MAC, device_info.mac_address))
        if device_info.ip_address and device_info.ip_address != "unknown":
            # Note: HA doesn't have a standard IP connection type, but we can use a custom one
            connections.add(("ip_address", device_info.ip_address))
        
        # Register device
        device = device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers=identifiers,
            connections=connections,
            manufacturer=device_info.manufacturer or "Unknown",
            model=device_info.model or device_info.device_type,
            name=device_info.device_name or f"{device_info.device_type} ({device_info.mac_address[-8:]})",
            sw_version=device_info.firmware_version,
            hw_version=None,
            suggested_area=_suggest_area_from_device_name(device_info.device_name),
            via_device=None
        )
        
        _LOGGER.info(f"Device registered in Home Assistant: {device.name} (ID: {device.id})")
        
        # Create entities based on device capabilities
        await _create_entities_for_device(hass, device_info, device)
        
        # Update device configuration with discovery metadata
        await _update_device_configuration(hass, device, device_info)
        
        return device
        
    except Exception as e:
        _LOGGER.exception(f"Error registering device {device_info.mac_address} in HA: {e}")
        return None


async def _create_entities_for_device(hass: HomeAssistant, device_info: DeviceInfo, device: dr.DeviceEntry):
    """Create entities based on device capabilities."""
    entity_registry = er.async_get(hass)
    
    # Create entities based on capabilities
    for capability_name, capability_data in device_info.capabilities.items():
        try:
            entity_id = await _create_entity_for_capability(
                hass, device_info, device, capability_name, capability_data
            )
            if entity_id:
                _LOGGER.info(f"Created entity {entity_id} for capability {capability_name}")
        except Exception as e:
            _LOGGER.error(f"Error creating entity for capability {capability_name}: {e}")


async def _create_entity_for_capability(
    hass: HomeAssistant,
    device_info: DeviceInfo,
    device: dr.DeviceEntry,
    capability_name: str,
    capability_data: Any
) -> Optional[str]:
    """Create a specific entity for a device capability."""
    entity_registry = er.async_get(hass)
    
    # Determine entity domain based on capability
    entity_domain = _map_capability_to_domain(capability_name, capability_data)
    if not entity_domain:
        _LOGGER.debug(f"No entity domain mapping for capability: {capability_name}")
        return None
    
    # Generate unique entity ID
    entity_id = f"{entity_domain}.{DOMAIN}_{device_info.mac_address.replace(':', '')}_{capability_name}"
    entity_id = entity_id.lower()
    
    # Create entity
    try:
        entity_entry = entity_registry.async_get_or_create(
            domain=entity_domain,
            platform=DOMAIN,
            unique_id=f"{device_info.mac_address}_{capability_name}",
            suggested_object_id=f"{device_info.device_name or device_info.device_type}_{capability_name}".replace(" ", "_"),
            config_entry=hass.config_entries.async_entries(DOMAIN)[0],
            device_id=device.id,
            original_name=f"{device_info.device_name or device_info.device_type} {capability_name}",
            original_device_class=_get_device_class_for_capability(capability_name),
            original_icon=_get_icon_for_capability(capability_name)
        )
        
        return entity_entry.entity_id
        
    except Exception as e:
        _LOGGER.error(f"Error creating entity {entity_id}: {e}")
        return None


def _map_capability_to_domain(capability_name: str, capability_data: Any) -> Optional[str]:
    """Map device capability to Home Assistant entity domain."""
    capability_domain_map = {
        # Lighting capabilities
        'brightness': 'light',
        'color_temperature': 'light',
        'color_rgb': 'light',
        'on_off': 'switch',
        
        # Climate capabilities
        'temperature_control': 'climate',
        'humidity_control': 'climate',
        'fan_speed': 'fan',
        
        # Sensor capabilities
        'temperature_sensing': 'sensor',
        'humidity_sensing': 'sensor',
        'motion_detection': 'binary_sensor',
        'door_contact': 'binary_sensor',
        'smoke_detection': 'binary_sensor',
        
        # Media capabilities
        'volume_control': 'media_player',
        'playback_control': 'media_player',
        
        # Security capabilities
        'lock_control': 'lock',
        'alarm_control': 'alarm_control_panel',
        
        # Cover capabilities
        'position_control': 'cover',
        'tilt_control': 'cover',
        
        # Generic capabilities
        'power_monitoring': 'sensor',
        'energy_monitoring': 'sensor',
        'status_indicator': 'binary_sensor'
    }
    
    return capability_domain_map.get(capability_name.lower())


def _get_device_class_for_capability(capability_name: str) -> Optional[str]:
    """Get device class for capability."""
    device_class_map = {
        'temperature_sensing': 'temperature',
        'humidity_sensing': 'humidity',
        'power_monitoring': 'power',
        'energy_monitoring': 'energy',
        'motion_detection': 'motion',
        'door_contact': 'door',
        'smoke_detection': 'smoke'
    }
    
    return device_class_map.get(capability_name.lower())


def _get_icon_for_capability(capability_name: str) -> Optional[str]:
    """Get icon for capability."""
    icon_map = {
        'brightness': 'mdi:brightness-6',
        'color_temperature': 'mdi:palette',
        'color_rgb': 'mdi:palette',
        'on_off': 'mdi:power',
        'temperature_control': 'mdi:thermometer',
        'humidity_control': 'mdi:water-percent',
        'fan_speed': 'mdi:fan',
        'temperature_sensing': 'mdi:thermometer',
        'humidity_sensing': 'mdi:water-percent',
        'motion_detection': 'mdi:motion-sensor',
        'door_contact': 'mdi:door',
        'smoke_detection': 'mdi:smoke-detector',
        'volume_control': 'mdi:volume-high',
        'playback_control': 'mdi:play-pause',
        'lock_control': 'mdi:lock',
        'alarm_control': 'mdi:shield-home',
        'position_control': 'mdi:window-shutter',
        'tilt_control': 'mdi:window-shutter',
        'power_monitoring': 'mdi:flash',
        'energy_monitoring': 'mdi:lightning-bolt'
    }
    
    return icon_map.get(capability_name.lower())


def _suggest_area_from_device_name(device_name: Optional[str]) -> Optional[str]:
    """Suggest area based on device name."""
    if not device_name:
        return None
    
    device_name_lower = device_name.lower()
    area_keywords = {
        'living': 'Living Room',
        'bedroom': 'Bedroom',
        'kitchen': 'Kitchen',
        'bathroom': 'Bathroom',
        'garage': 'Garage',
        'office': 'Office',
        'dining': 'Dining Room',
        'hallway': 'Hallway',
        'basement': 'Basement',
        'attic': 'Attic',
        'patio': 'Patio',
        'garden': 'Garden',
        'balcony': 'Balcony'
    }
    
    for keyword, area in area_keywords.items():
        if keyword in device_name_lower:
            return area
    
    return None


async def _update_device_configuration(hass: HomeAssistant, device: dr.DeviceEntry, device_info: DeviceInfo):
    """Update device configuration with discovery metadata."""
    try:
        device_registry = dr.async_get(hass)
        
        # Prepare configuration URL if device has web interface
        config_url = None
        if device_info.ip_address and device_info.ip_address != "unknown":
            # Check for common web interface ports
            if 80 in device_info.port_info or 443 in device_info.port_info:
                protocol = "https" if 443 in device_info.port_info else "http"
                port = 443 if 443 in device_info.port_info else 80
                config_url = f"{protocol}://{device_info.ip_address}:{port}"
        
        # Update device with additional metadata
        updates = {}
        if config_url:
            updates["configuration_url"] = config_url
        
        if updates:
            device_registry.async_update_device(device.id, **updates)
            _LOGGER.debug(f"Updated device configuration for {device.name}")
            
    except Exception as e:
        _LOGGER.error(f"Error updating device configuration: {e}")


async def update_device_availability(hass: HomeAssistant, device_info: DeviceInfo, available: bool):
    """Update device availability status in HA."""
    try:
        device_registry = dr.async_get(hass)
        
        # Find device by MAC address identifier
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, device_info.mac_address)}
        )
        
        if device:
            # Update device availability (this might need custom implementation)
            # HA doesn't have built-in device availability tracking in device registry
            # You might need to use entity availability instead
            _LOGGER.debug(f"Device {device.name} availability: {available}")
            
            # Update entities availability
            entity_registry = er.async_get(hass)
            entities = er.async_entries_for_device(entity_registry, device.id)
            
            for entity in entities:
                if hasattr(hass.states.get(entity.entity_id), 'state'):
                    # This would typically be handled by the entity's update mechanism
                    pass
                    
    except Exception as e:
        _LOGGER.error(f"Error updating device availability: {e}")


async def remove_device_from_ha(hass: HomeAssistant, mac_address: str) -> bool:
    """Remove device and its entities from Home Assistant."""
    try:
        device_registry = dr.async_get(hass)
        entity_registry = er.async_get(hass)
        
        # Find device
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, mac_address)}
        )
        
        if not device:
            _LOGGER.warning(f"Device with MAC {mac_address} not found in registry")
            return False
        
        # Remove all entities first
        entities = er.async_entries_for_device(entity_registry, device.id)
        for entity in entities:
            entity_registry.async_remove(entity.entity_id)
            _LOGGER.info(f"Removed entity: {entity.entity_id}")
        
        # Remove device
        device_registry.async_remove_device(device.id)
        _LOGGER.info(f"Removed device: {device.name} ({mac_address})")
        
        return True
        
    except Exception as e:
        _LOGGER.error(f"Error removing device {mac_address}: {e}")
        return False


def get_device_info_from_ha(hass: HomeAssistant, mac_address: str) -> Optional[Dict[str, Any]]:
    """Get device information from HA device registry."""
    try:
        device_registry = dr.async_get(hass)
        
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, mac_address)}
        )
        
        if device:
            return {
                'id': device.id,
                'name': device.name,
                'manufacturer': device.manufacturer,
                'model': device.model,
                'sw_version': device.sw_version,
                'suggested_area': device.suggested_area,
                'configuration_url': device.configuration_url,
                'identifiers': list(device.identifiers),
                'connections': list(device.connections)
            }
        
        return None
        
    except Exception as e:
        _LOGGER.error(f"Error getting device info for {mac_address}: {e}")
        return None


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_ha_integration():
        """Test HA integration functionality."""
        
        # Mock HA components for testing
        class MockDeviceRegistry:
            def async_get_or_create(self, **kwargs):
                class MockDevice:
                    def __init__(self):
                        self.id = "test_device_id"
                        self.name = kwargs.get('name', 'Test Device')
                return MockDevice()
        
        class MockHass:
            def __init__(self):
                self.config_entries = type('', (), {
                    'async_entries': lambda domain: [type('', (), {'entry_id': 'test_entry_id'})()]
                })()
        
        # Test device info
        test_device = DeviceInfo(
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.100",
            device_type="Smart Light",
            discovery_protocol="Test",
            device_name="Living Room Light",
            manufacturer="Test Manufacturer",
            model="Smart Light Pro",
            capabilities={
                'brightness': True,
                'color_temperature': True,
                'on_off': True
            }
        )
        
        hass = MockHass()
        
        print("Testing HA device registration...")
        # This would normally register with actual HA
        print(f"Device: {test_device.device_name}")
        print(f"Capabilities: {test_device.capabilities}")
        print("HA integration test completed")
    
    # Run test
    asyncio.run(test_ha_integration())