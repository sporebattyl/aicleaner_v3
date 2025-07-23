"""
MQTT Topic Manager
Manages MQTT topic structure and lifecycle for HA Discovery
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MQTTTopicManager:
    """
    Manages MQTT topic structure and lifecycle for Home Assistant Discovery
    """
    
    def __init__(self, discovery_prefix: str = "homeassistant", device_id: str = "aicleaner_v3"):
        """Initialize Topic Manager"""
        self.discovery_prefix = discovery_prefix
        self.device_id = device_id
        self.registered_topics: Dict[str, Dict[str, Any]] = {}
        
    def create_discovery_topic(self, component_type: str, object_id: str) -> str:
        """Create HA Discovery configuration topic"""
        return f"{self.discovery_prefix}/{component_type}/{self.device_id}/{object_id}/config"
    
    def create_state_topic(self, component_type: str, object_id: str) -> str:
        """Create state topic for entity"""
        return f"{self.discovery_prefix}/{component_type}/{self.device_id}/{object_id}/state"
    
    def create_command_topic(self, component_type: str, object_id: str) -> str:
        """Create command topic for entity"""
        return f"{self.discovery_prefix}/{component_type}/{self.device_id}/{object_id}/cmd"
    
    def create_availability_topic(self, object_id: str = "status") -> str:
        """Create availability topic"""
        return f"{self.discovery_prefix}/status/{self.device_id}/{object_id}"
    
    def create_attributes_topic(self, component_type: str, object_id: str) -> str:
        """Create attributes topic for entity"""
        return f"{self.discovery_prefix}/{component_type}/{self.device_id}/{object_id}/attributes"
    
    def register_entity_topics(
        self,
        component_type: str,
        object_id: str,
        config: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Register all topics for an entity and return topic mapping
        """
        topics = {
            "config_topic": self.create_discovery_topic(component_type, object_id),
            "state_topic": self.create_state_topic(component_type, object_id),
            "availability_topic": self.create_availability_topic()
        }
        
        # Add command topic for controllable entities
        if component_type in ["switch", "light", "fan", "climate"]:
            topics["command_topic"] = self.create_command_topic(component_type, object_id)
        
        # Add attributes topic if needed
        if config.get("json_attributes_topic"):
            topics["attributes_topic"] = self.create_attributes_topic(component_type, object_id)
        
        # Store registration
        entity_key = f"{component_type}.{object_id}"
        self.registered_topics[entity_key] = {
            "topics": topics,
            "config": config,
            "registered_at": datetime.now().isoformat(),
            "component_type": component_type,
            "object_id": object_id
        }
        
        logger.info(f"Registered topics for {entity_key}: {list(topics.keys())}")
        return topics
    
    def unregister_entity_topics(self, component_type: str, object_id: str) -> bool:
        """Unregister entity topics"""
        entity_key = f"{component_type}.{object_id}"
        
        if entity_key in self.registered_topics:
            del self.registered_topics[entity_key]
            logger.info(f"Unregistered topics for {entity_key}")
            return True
        else:
            logger.warning(f"Entity {entity_key} not found in registered topics")
            return False
    
    def get_entity_topics(self, component_type: str, object_id: str) -> Optional[Dict[str, str]]:
        """Get topics for a specific entity"""
        entity_key = f"{component_type}.{object_id}"
        
        if entity_key in self.registered_topics:
            return self.registered_topics[entity_key]["topics"]
        return None
    
    def get_all_registered_topics(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered topics"""
        return self.registered_topics.copy()
    
    def get_discovery_topics(self) -> List[str]:
        """Get all discovery configuration topics"""
        topics = []
        for entity_data in self.registered_topics.values():
            topics.append(entity_data["topics"]["config_topic"])
        return topics
    
    def get_state_topics(self) -> List[str]:
        """Get all state topics"""
        topics = []
        for entity_data in self.registered_topics.values():
            if "state_topic" in entity_data["topics"]:
                topics.append(entity_data["topics"]["state_topic"])
        return topics
    
    def get_command_topics(self) -> List[str]:
        """Get all command topics"""
        topics = []
        for entity_data in self.registered_topics.values():
            if "command_topic" in entity_data["topics"]:
                topics.append(entity_data["topics"]["command_topic"])
        return topics
    
    def create_sensor_config(
        self,
        object_id: str,
        name: str,
        unit_of_measurement: Optional[str] = None,
        device_class: Optional[str] = None,
        state_class: Optional[str] = None,
        icon: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create sensor configuration for HA Discovery"""
        topics = self.register_entity_topics("sensor", object_id, {})
        
        config = {
            "name": name,
            "state_topic": topics["state_topic"],
            "availability_topic": topics["availability_topic"],
            "payload_available": "online",
            "payload_not_available": "offline",
            "unique_id": f"{self.device_id}_{object_id}",
            "object_id": f"{self.device_id}_{object_id}"
        }
        
        if unit_of_measurement:
            config["unit_of_measurement"] = unit_of_measurement
        if device_class:
            config["device_class"] = device_class
        if state_class:
            config["state_class"] = state_class
        if icon:
            config["icon"] = icon
        
        return config
    
    def create_switch_config(
        self,
        object_id: str,
        name: str,
        icon: Optional[str] = None,
        device_class: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create switch configuration for HA Discovery"""
        topics = self.register_entity_topics("switch", object_id, {})
        
        config = {
            "name": name,
            "state_topic": topics["state_topic"],
            "command_topic": topics["command_topic"],
            "availability_topic": topics["availability_topic"],
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "payload_available": "online",
            "payload_not_available": "offline",
            "unique_id": f"{self.device_id}_{object_id}",
            "object_id": f"{self.device_id}_{object_id}"
        }
        
        if icon:
            config["icon"] = icon
        if device_class:
            config["device_class"] = device_class
        
        return config
    
    def create_binary_sensor_config(
        self,
        object_id: str,
        name: str,
        device_class: Optional[str] = None,
        icon: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create binary sensor configuration for HA Discovery"""
        topics = self.register_entity_topics("binary_sensor", object_id, {})
        
        config = {
            "name": name,
            "state_topic": topics["state_topic"],
            "availability_topic": topics["availability_topic"],
            "payload_on": "ON",
            "payload_off": "OFF",
            "payload_available": "online",
            "payload_not_available": "offline",
            "unique_id": f"{self.device_id}_{object_id}",
            "object_id": f"{self.device_id}_{object_id}"
        }
        
        if device_class:
            config["device_class"] = device_class
        if icon:
            config["icon"] = icon
        
        return config
    
    @staticmethod
    def validate_topic_structure(topic: str) -> bool:
        """Validate MQTT topic structure"""
        if not topic:
            return False
        
        # Check for valid characters
        invalid_chars = ['+', '#']
        if any(char in topic for char in invalid_chars):
            logger.warning(f"Topic contains invalid characters: {topic}")
            return False

        # Check topic length
        if len(topic) > 65535:
            logger.warning(f"Topic exceeds maximum length: {topic}")
            return False

        # Check for empty levels
        if '//' in topic:
            logger.warning(f"Topic contains empty levels: {topic}")
            return False

        return True
    
    def cleanup_all_topics(self) -> List[str]:
        """Get cleanup list for all registered topics"""
        cleanup_topics = []
        
        for entity_data in self.registered_topics.values():
            # Add config topic for removal (empty payload)
            cleanup_topics.append(entity_data["topics"]["config_topic"])
        
        logger.info(f"Prepared cleanup for {len(cleanup_topics)} topics")
        return cleanup_topics
