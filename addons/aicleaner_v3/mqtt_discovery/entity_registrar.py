import logging
from typing import Dict, Any

from .models import MQTTDevice, MQTTEntity
from .state_manager import StateManager

logger = logging.getLogger(__name__)

class EntityRegistrar:
    """Handles the registration of discovered devices and entities."""

    def __init__(self, entity_manager: Any, state_manager: StateManager):
        """
        Initializes the EntityRegistrar.

        Args:
            entity_manager: The Phase 4A EntityManager instance.
            state_manager: The StateManager instance.
        """
        self.entity_manager = entity_manager
        self.state_manager = state_manager
        self._registered_devices: Dict[str, MQTTDevice] = {}

    async def register_entity(self, component: str, object_id: str, config_payload: Dict[str, Any]):
        """Registers a new entity discovered via MQTT."""
        unique_id = config_payload.get('unique_id')
        if not unique_id:
            logger.error(f"Missing 'unique_id' in config for {component}/{object_id}. Skipping.")
            return

        # Check if entity already exists
        if hasattr(self.entity_manager, 'async_entity_exists'):
            entity_exists = await self.entity_manager.async_entity_exists(unique_id)
        else:
            # Fallback method name
            entity_exists = await self.entity_manager.entity_exists(unique_id)
            
        if entity_exists:
            logger.info(f"Entity '{unique_id}' is already registered. Skipping.")
            return

        logger.info(f"Registering new entity: {unique_id}")

        # Create entity and device objects from payload
        device_info = config_payload.get('device', {})
        device_identifiers = device_info.get('identifiers', [unique_id])

        entity = MQTTEntity(
            unique_id=unique_id,
            component=component,
            config_payload=config_payload,
            state_topic=config_payload.get('state_topic'),
            command_topic=config_payload.get('command_topic'),
            availability_topic=config_payload.get('availability_topic')
        )

        # Register entity with Phase 4A EntityManager
        if hasattr(self.entity_manager, 'async_add_entity'):
            await self.entity_manager.async_add_entity(entity.config_payload)
        else:
            # Fallback method name
            await self.entity_manager.add_entity(entity.config_payload)

        # Subscribe to state topic if available
        if entity.state_topic:
            await self.state_manager.add_entity_subscription(unique_id, entity.state_topic)

        # Store registered device info
        if device_identifiers:
            device_key = str(device_identifiers[0])
            if device_key not in self._registered_devices:
                self._registered_devices[device_key] = MQTTDevice(
                    identifiers=device_identifiers,
                    name=device_info.get('name', f'Device {device_key}'),
                    model=device_info.get('model', 'Unknown'),
                    manufacturer=device_info.get('manufacturer', 'Unknown'),
                    entities={}
                )
            self._registered_devices[device_key].entities[unique_id] = entity

    async def get_registered_devices(self) -> Dict[str, MQTTDevice]:
        """Returns all registered devices."""
        return self._registered_devices

    async def get_device_entity_count(self, device_id: str) -> int:
        """Returns the number of entities for a specific device."""
        device = self._registered_devices.get(device_id)
        return len(device.entities) if device else 0