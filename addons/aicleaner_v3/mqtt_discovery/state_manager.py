import logging
from typing import Dict, Any

from .client import MQTTClient

logger = logging.getLogger(__name__)

class StateManager:
    """Manages device state subscriptions and updates."""

    def __init__(self, entity_manager: Any, mqtt_client: MQTTClient):
        """
        Initializes the StateManager.

        Args:
            entity_manager: The Phase 4A EntityManager instance.
            mqtt_client: The MQTTClient instance.
        """
        self.entity_manager = entity_manager
        self.mqtt_client = mqtt_client
        self._state_topic_map: Dict[str, str] = {}

    async def add_entity_subscription(self, entity_id: str, state_topic: str):
        """Subscribes to the state topic for a given entity."""
        if state_topic not in self._state_topic_map:
            logger.info(f"Adding subscription for entity '{entity_id}' on topic '{state_topic}'")
            await self.mqtt_client.subscribe(state_topic)
            self._state_topic_map[state_topic] = entity_id
        else:
            logger.warning(f"Topic '{state_topic}' is already being watched.")

    async def update_entity_state(self, topic: str, payload: str):
        """Updates the state of an entity based on an MQTT message."""
        entity_id = self._state_topic_map.get(topic)
        if entity_id:
            logger.debug(f"Updating state for entity '{entity_id}' with payload: {payload}")
            # Interface with existing Phase 4A EntityManager
            if hasattr(self.entity_manager, 'async_update_state'):
                await self.entity_manager.async_update_state(entity_id, payload)
            else:
                # Fallback for different EntityManager interface
                await self.entity_manager.update_entity_state(entity_id, payload)
        else:
            logger.warning(f"Received state update on unmapped topic: {topic}")