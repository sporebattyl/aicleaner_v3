"""
MQTT Entity Templates for AICleaner Home Assistant Addon
Provides discovery payload templates for sensors, buttons, and select entities
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime


class MQTTEntityTemplates:
    """
    Templates for Home Assistant MQTT discovery payloads
    Follows HA MQTT discovery specification and best practices
    """
    
    def __init__(self, discovery_prefix: str = "homeassistant", node_id: str = "aicleaner"):
        """
        Initialize entity templates
        
        Args:
            discovery_prefix: MQTT discovery prefix (default: homeassistant)
            node_id: Unique node identifier for this addon
        """
        self.discovery_prefix = discovery_prefix
        self.node_id = node_id
        
    def get_device_config(self, zone_name: str = None) -> Dict[str, Any]:
        """
        Get unified device configuration for all entities

        Args:
            zone_name: Optional zone name for zone-specific device grouping

        Returns:
            Dict containing device configuration
        """
        if zone_name:
            # Zone-specific device configuration for logical grouping
            zone_id = self.sanitize_zone_name(zone_name)
            return {
                "identifiers": [f"aicleaner_zone_{zone_id}"],
                "name": f"AICleaner {zone_name}",
                "model": "Zone Controller",
                "manufacturer": "AICleaner Project",
                "sw_version": "2.0.1",
                "configuration_url": "http://192.168.88.17:8099",
                "via_device": f"aicleaner_{self.node_id}",  # Link to main device
                "suggested_area": zone_name.lower()
            }
        else:
            # Main system device configuration - FIXED: Removed invalid 'origin' field
            return {
                "identifiers": [f"aicleaner_{self.node_id}"],
                "name": "AICleaner",
                "model": "AICleaner v2.0+",
                "manufacturer": "AICleaner Project",
                "sw_version": "2.0.1",
                "configuration_url": "http://192.168.88.17:8099",
                "hw_version": "MQTT",
                "connections": [["mac", "02:00:00:00:00:00"]]  # Virtual MAC for identification
            }

    def get_main_device_config(self) -> Dict[str, Any]:
        """
        Get main system device configuration

        Returns:
            Dict containing main device configuration
        """
        return self.get_device_config()

    def get_zone_device_config(self, zone_name: str) -> Dict[str, Any]:
        """
        Get zone-specific device configuration

        Args:
            zone_name: Zone name for device grouping

        Returns:
            Dict containing zone device configuration
        """
        return self.get_device_config(zone_name)

    def get_all_device_configs(self, zones: List[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get all device configurations for system and zones

        Args:
            zones: List of zone names to create device configs for

        Returns:
            Dict mapping device identifiers to device configurations
        """
        devices = {
            'main': self.get_main_device_config()
        }

        if zones:
            for zone_name in zones:
                zone_id = self.sanitize_zone_name(zone_name)
                devices[f'zone_{zone_id}'] = self.get_zone_device_config(zone_name)

        return devices

    def publish_device_configurations(self, mqtt_client, zones: List[str] = None) -> bool:
        """
        Publish device configurations to MQTT for device registry

        Args:
            mqtt_client: MQTT client instance
            zones: List of zone names

        Returns:
            bool: True if all configurations published successfully
        """
        try:
            device_configs = self.get_all_device_configs(zones)

            for device_id, config in device_configs.items():
                # Publish device configuration to special device topic
                device_topic = f"{self.discovery_prefix}/device/{self.node_id}/{device_id}/config"
                mqtt_client.publish(device_topic, json.dumps(config), retain=True)

            return True

        except Exception as e:
            import logging
            logging.error(f"Error publishing device configurations: {e}")
            return False

    def create_system_status_sensor(self) -> Dict[str, Any]:
        """
        Create system status sensor discovery payload with comprehensive attributes
        FIXED: Removed invalid 'entity_category' field

        Returns:
            Dict containing discovery configuration
        """
        return {
            "name": "AICleaner System Status",
            "unique_id": f"{self.node_id}_system_status",
            "object_id": "system_status",
            "state_topic": f"{self.discovery_prefix}/sensor/{self.node_id}/system_status/state",
            "json_attributes_topic": f"{self.discovery_prefix}/sensor/{self.node_id}/system_status/attributes",
            "availability_topic": f"{self.node_id}/availability",
            "device_class": None,
            "state_class": None,
            "icon": "mdi:robot-vacuum",
            "device": self.get_device_config(),
            # Additional configuration for rich attributes
            "force_update": True,
            "expire_after": 300,  # 5 minutes
            # JSON attributes will include:
            # - status, total_zones, total_active_tasks, total_completed_tasks
            # - global_completion_rate, average_efficiency_score
            # - uptime_seconds, uptime_hours, uptime_formatted
            # - health_status, health_components
            # - cpu_usage, memory_usage_mb, disk_usage_percent, active_threads
            # - mqtt_enabled, mqtt_connected, discovery_prefix
            # - version, addon_name, last_analysis, last_updated
        }
        
    def create_zone_task_sensor(self, zone_name: str, zone_id: str) -> Dict[str, Any]:
        """
        Create zone task sensor discovery payload
        FIXED: Removed invalid 'entity_category' field
        
        Args:
            zone_name: Human-readable zone name
            zone_id: Sanitized zone identifier
            
        Returns:
            Dict containing discovery configuration
        """
        return {
            "name": f"{zone_name} Tasks",
            "unique_id": f"{self.node_id}_zone_{zone_id}_tasks",
            "object_id": f"zone_{zone_id}_tasks",
            "state_topic": f"{self.discovery_prefix}/sensor/{self.node_id}/zone_{zone_id}_tasks/state",
            "json_attributes_topic": f"{self.discovery_prefix}/sensor/{self.node_id}/zone_{zone_id}_tasks/attributes",
            "availability_topic": f"{self.node_id}/availability",
            "device_class": None,
            "unit_of_measurement": "tasks",
            "state_class": "measurement",
            "icon": "mdi:format-list-checks",
            "device": self.get_device_config(zone_name)
        }
        
    def create_zone_cleanliness_sensor(self, zone_name: str, zone_id: str) -> Dict[str, Any]:
        """
        Create zone cleanliness sensor discovery payload
        FIXED: Removed invalid 'entity_category' field
        
        Args:
            zone_name: Human-readable zone name
            zone_id: Sanitized zone identifier
            
        Returns:
            Dict containing discovery configuration
        """
        return {
            "name": f"{zone_name} Cleanliness",
            "unique_id": f"{self.node_id}_zone_{zone_id}_cleanliness",
            "object_id": f"zone_{zone_id}_cleanliness",
            "state_topic": f"{self.discovery_prefix}/sensor/{self.node_id}/zone_{zone_id}_cleanliness/state",
            "json_attributes_topic": f"{self.discovery_prefix}/sensor/{self.node_id}/zone_{zone_id}_cleanliness/attributes",
            "availability_topic": f"{self.node_id}/availability",
            "device_class": None,
            "unit_of_measurement": "%",
            "state_class": "measurement",
            "icon": "mdi:sparkles",
            "device": self.get_device_config(zone_name)
        }
        
    def create_zone_analyze_button(self, zone_name: str, zone_id: str) -> Dict[str, Any]:
        """
        Create zone analyze button discovery payload
        FIXED: Removed invalid 'entity_category' field
        
        Args:
            zone_name: Human-readable zone name
            zone_id: Sanitized zone identifier
            
        Returns:
            Dict containing discovery configuration
        """
        return {
            "name": f"Analyze {zone_name}",
            "unique_id": f"{self.node_id}_zone_{zone_id}_analyze",
            "object_id": f"zone_{zone_id}_analyze",
            "command_topic": f"{self.discovery_prefix}/button/{self.node_id}/zone_{zone_id}_analyze/command",
            "availability_topic": f"{self.node_id}/availability",
            "payload_press": "ANALYZE",
            "device_class": None,
            "icon": "mdi:camera-iris",
            "device": self.get_device_config(zone_name)
        }
        
    def create_zone_camera_button(self, zone_name: str, zone_id: str) -> Dict[str, Any]:
        """
        Create zone camera button discovery payload
        FIXED: Removed invalid 'entity_category' field
        
        Args:
            zone_name: Human-readable zone name
            zone_id: Sanitized zone identifier
            
        Returns:
            Dict containing discovery configuration
        """
        return {
            "name": f"Take {zone_name} Snapshot",
            "unique_id": f"{self.node_id}_zone_{zone_id}_camera",
            "object_id": f"zone_{zone_id}_camera",
            "command_topic": f"{self.discovery_prefix}/button/{self.node_id}/zone_{zone_id}_camera/command",
            "availability_topic": f"{self.node_id}/availability",
            "payload_press": "SNAPSHOT",
            "device_class": None,
            "icon": "mdi:camera",
            "device": self.get_device_config(zone_name)
        }
        
    def create_ai_model_select(self) -> Dict[str, Any]:
        """
        Create AI model selection entity discovery payload
        FIXED: Removed invalid 'entity_category' field
        
        Returns:
            Dict containing discovery configuration
        """
        return {
            "name": "AI Model",
            "unique_id": f"{self.node_id}_ai_model",
            "object_id": "ai_model",
            "command_topic": f"{self.discovery_prefix}/select/{self.node_id}/ai_model/command",
            "state_topic": f"{self.discovery_prefix}/select/{self.node_id}/ai_model/state",
            "availability_topic": f"{self.node_id}/availability",
            "options": ["flash", "pro"],
            "icon": "mdi:brain",
            "device": self.get_device_config()
        }
        
    def get_state_payload(self, state: Any, attributes: Optional[Dict[str, Any]] = None) -> str:
        """
        Create state payload for sensor updates
        
        Args:
            state: The state value
            attributes: Optional attributes dictionary
            
        Returns:
            JSON string for state topic
        """
        return str(state)
        
    def get_attributes_payload(self, attributes: Dict[str, Any]) -> str:
        """
        Create attributes payload for sensor updates
        
        Args:
            attributes: Attributes dictionary
            
        Returns:
            JSON string for attributes topic
        """
        # Add timestamp to attributes
        attributes_with_timestamp = attributes.copy()
        attributes_with_timestamp['last_updated'] = datetime.now().isoformat()
        
        return json.dumps(attributes_with_timestamp)
        
    def get_discovery_topic(self, component: str, object_id: str) -> str:
        """
        Get discovery topic for given component and object ID
        
        Args:
            component: HA component type (sensor, button, select)
            object_id: Unique object identifier
            
        Returns:
            Discovery topic string
        """
        return f"{self.discovery_prefix}/{component}/{self.node_id}/{object_id}/config"
        
    def get_state_topic(self, component: str, object_id: str) -> str:
        """
        Get state topic for given component and object ID
        
        Args:
            component: HA component type
            object_id: Unique object identifier
            
        Returns:
            State topic string
        """
        return f"{self.discovery_prefix}/{component}/{self.node_id}/{object_id}/state"
        
    def get_attributes_topic(self, component: str, object_id: str) -> str:
        """
        Get attributes topic for given component and object ID
        
        Args:
            component: HA component type
            object_id: Unique object identifier
            
        Returns:
            Attributes topic string
        """
        return f"{self.discovery_prefix}/{component}/{self.node_id}/{object_id}/attributes"
        
    def get_command_topic(self, component: str, object_id: str) -> str:
        """
        Get command topic for given component and object ID
        
        Args:
            component: HA component type
            object_id: Unique object identifier
            
        Returns:
            Command topic string
        """
        return f"{self.discovery_prefix}/{component}/{self.node_id}/{object_id}/command"

    def create_all_zone_entities(self, zone_name: str, zone_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Create all entity configurations for a zone

        Args:
            zone_name: Human-readable zone name
            zone_id: Sanitized zone identifier

        Returns:
            Dict containing all entity configurations for the zone
        """
        return {
            'task_sensor': self.create_zone_task_sensor(zone_name, zone_id),
            'cleanliness_sensor': self.create_zone_cleanliness_sensor(zone_name, zone_id),
            'analyze_button': self.create_zone_analyze_button(zone_name, zone_id),
            'camera_button': self.create_zone_camera_button(zone_name, zone_id)
        }

    def create_all_system_entities(self) -> Dict[str, Dict[str, Any]]:
        """
        Create all system-level entity configurations

        Returns:
            Dict containing all system entity configurations
        """
        return {
            'system_status': self.create_system_status_sensor(),
            'ai_model_select': self.create_ai_model_select()
        }

    def remove_entity_config(self) -> str:
        """
        Get empty payload for removing entity discovery configuration

        Returns:
            Empty string to remove entity
        """
        return ""

    def validate_zone_id(self, zone_id: str) -> bool:
        """
        Validate zone ID for MQTT topic compatibility

        Args:
            zone_id: Zone identifier to validate

        Returns:
            True if valid, False otherwise
        """
        # Zone ID should only contain alphanumeric characters and underscores
        import re
        return bool(re.match(r'^[a-zA-Z0-9_]+$', zone_id))

    def sanitize_zone_name(self, zone_name: str) -> str:
        """
        Sanitize zone name for use as zone_id

        Args:
            zone_name: Original zone name

        Returns:
            Sanitized zone identifier
        """
        import re
        # Convert to lowercase and replace non-alphanumeric with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9]', '_', zone_name.lower())
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        return sanitized or 'unknown_zone'

    def get_attributes_payload(self, attributes: Dict[str, Any]) -> str:
        """
        Generate JSON payload for attributes

        Args:
            attributes: Dictionary of attributes

        Returns:
            JSON string payload
        """
        try:
            return json.dumps(attributes, default=str)
        except Exception:
            return "{}"