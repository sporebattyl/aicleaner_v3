"""
MQTT Device Publisher
Publishes AICleaner v3 devices and entities via MQTT Discovery
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MQTTDevicePublisher:
    """
    Publishes AICleaner v3 devices and entities via MQTT Discovery
    """
    
    def __init__(self, mqtt_client, topic_manager):
        """Initialize Device Publisher"""
        self.mqtt_client = mqtt_client
        self.topic_manager = topic_manager
        self.published_entities: Dict[str, Dict[str, Any]] = {}
        self.device_online = False
        
    async def async_publish_device(self) -> bool:
        """Publish main AICleaner v3 device"""
        try:
            # Publish availability first
            availability_topic = self.topic_manager.create_availability_topic()
            await self.mqtt_client.async_publish_state(
                availability_topic, 
                "online", 
                retain=True
            )
            self.device_online = True
            
            # Publish all entity configurations
            await self._publish_system_entities()
            await self._publish_control_entities()
            await self._publish_monitoring_entities()
            
            logger.info("Successfully published AICleaner v3 device via MQTT Discovery")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish device: {e}")
            return False
    
    async def _publish_system_entities(self):
        """Publish system status entities"""
        
        # System Status Sensor
        system_config = self.topic_manager.create_sensor_config(
            object_id="system_status",
            name="System Status",
            device_class="enum",
            icon="mdi:cog"
        )
        await self._publish_entity_config("sensor", "system_status", system_config)
        await self._update_entity_state("sensor", "system_status", "ready")
        
        # Cleanup Progress Sensor
        progress_config = self.topic_manager.create_sensor_config(
            object_id="cleanup_progress",
            name="Cleanup Progress",
            unit_of_measurement="%",
            state_class="measurement",
            icon="mdi:progress-clock"
        )
        await self._publish_entity_config("sensor", "cleanup_progress", progress_config)
        await self._update_entity_state("sensor", "cleanup_progress", 0)
        
        # Performance Score Sensor
        performance_config = self.topic_manager.create_sensor_config(
            object_id="performance_score",
            name="Performance Score",
            unit_of_measurement="points",
            state_class="measurement",
            icon="mdi:speedometer"
        )
        await self._publish_entity_config("sensor", "performance_score", performance_config)
        await self._update_entity_state("sensor", "performance_score", 100)
        
        # Last Cleanup Sensor
        last_cleanup_config = self.topic_manager.create_sensor_config(
            object_id="last_cleanup",
            name="Last Cleanup",
            device_class="timestamp",
            icon="mdi:broom"
        )
        await self._publish_entity_config("sensor", "last_cleanup", last_cleanup_config)
        await self._update_entity_state("sensor", "last_cleanup", datetime.now().isoformat())
    
    async def _publish_control_entities(self):
        """Publish control entities"""
        
        # Auto Cleanup Switch
        auto_cleanup_config = self.topic_manager.create_switch_config(
            object_id="auto_cleanup",
            name="Auto Cleanup",
            icon="mdi:robot-vacuum"
        )
        await self._publish_entity_config("switch", "auto_cleanup", auto_cleanup_config)
        await self._update_entity_state("switch", "auto_cleanup", "OFF")
        
        # AI Optimization Switch
        ai_optimization_config = self.topic_manager.create_switch_config(
            object_id="ai_optimization",
            name="AI Optimization",
            icon="mdi:brain"
        )
        await self._publish_entity_config("switch", "ai_optimization", ai_optimization_config)
        await self._update_entity_state("switch", "ai_optimization", "ON")
        
        # Maintenance Mode Switch
        maintenance_config = self.topic_manager.create_switch_config(
            object_id="maintenance_mode",
            name="Maintenance Mode",
            icon="mdi:wrench"
        )
        await self._publish_entity_config("switch", "maintenance_mode", maintenance_config)
        await self._update_entity_state("switch", "maintenance_mode", "OFF")
    
    async def _publish_monitoring_entities(self):
        """Publish monitoring entities"""
        
        # System Health Binary Sensor
        health_config = self.topic_manager.create_binary_sensor_config(
            object_id="system_health",
            name="System Health",
            device_class="problem",
            icon="mdi:heart-pulse"
        )
        await self._publish_entity_config("binary_sensor", "system_health", health_config)
        await self._update_entity_state("binary_sensor", "system_health", "OFF")  # No problems
        
        # Cleanup Active Binary Sensor
        cleanup_active_config = self.topic_manager.create_binary_sensor_config(
            object_id="cleanup_active",
            name="Cleanup Active",
            device_class="running",
            icon="mdi:play-circle"
        )
        await self._publish_entity_config("binary_sensor", "cleanup_active", cleanup_active_config)
        await self._update_entity_state("binary_sensor", "cleanup_active", "OFF")
        
        # CPU Usage Sensor
        cpu_config = self.topic_manager.create_sensor_config(
            object_id="cpu_usage",
            name="CPU Usage",
            unit_of_measurement="%",
            state_class="measurement",
            icon="mdi:chip"
        )
        await self._publish_entity_config("sensor", "cpu_usage", cpu_config)
        await self._update_entity_state("sensor", "cpu_usage", 15.5)
        
        # Memory Usage Sensor
        memory_config = self.topic_manager.create_sensor_config(
            object_id="memory_usage",
            name="Memory Usage",
            unit_of_measurement="%",
            state_class="measurement",
            icon="mdi:memory"
        )
        await self._publish_entity_config("sensor", "memory_usage", memory_config)
        await self._update_entity_state("sensor", "memory_usage", 45.2)
    
    async def _publish_entity_config(
        self,
        component_type: str,
        object_id: str,
        config: Dict[str, Any]
    ) -> bool:
        """Publish entity configuration via MQTT Discovery"""
        try:
            success = await self.mqtt_client.async_publish_discovery(
                component_type,
                object_id,
                config,
                retain=True
            )
            
            if success:
                # Store entity info
                entity_key = f"{component_type}.{object_id}"
                self.published_entities[entity_key] = {
                    "component_type": component_type,
                    "object_id": object_id,
                    "config": config,
                    "published_at": datetime.now().isoformat(),
                    "state": None
                }
                
                # Subscribe to command topic if applicable
                if "command_topic" in config:
                    await self.mqtt_client.async_subscribe(
                        config["command_topic"],
                        self._handle_command_message
                    )
                
                logger.info(f"Published entity config: {entity_key}")
                return True
            else:
                logger.error(f"Failed to publish entity config: {entity_key}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing entity config {component_type}.{object_id}: {e}")
            return False
    
    async def _update_entity_state(
        self,
        component_type: str,
        object_id: str,
        state: Any,
        attributes: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update entity state"""
        try:
            entity_key = f"{component_type}.{object_id}"
            topics = self.topic_manager.get_entity_topics(component_type, object_id)
            
            if not topics:
                logger.error(f"No topics found for entity: {entity_key}")
                return False
            
            # Publish state
            success = await self.mqtt_client.async_publish_state(
                topics["state_topic"],
                state,
                retain=False
            )
            
            if success:
                # Update stored state
                if entity_key in self.published_entities:
                    self.published_entities[entity_key]["state"] = state
                    self.published_entities[entity_key]["last_updated"] = datetime.now().isoformat()

                # Publish attributes if provided
                if attributes and topics.get("attributes_topic"):
                    try:
                        attributes_payload = json.dumps(attributes)
                        await self.mqtt_client.async_publish_state(
                            topics["attributes_topic"],
                            attributes_payload,
                            retain=False  # Consider retain=True if attributes are relatively static
                        )
                        logger.debug(f"Published attributes to {topics['attributes_topic']}: {attributes_payload}")
                    except Exception as e:
                        logger.error(f"Error publishing attributes to {topics['attributes_topic']}: {e}")

                logger.debug(f"Updated state for {entity_key}: {state}")
                return True
            else:
                logger.error(f"Failed to update state for {entity_key}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating entity state {component_type}.{object_id}: {e}")
            return False
    
    async def _handle_command_message(self, topic: str, payload: str):
        """Handle incoming command messages"""
        try:
            logger.info(f"Received command on {topic}: {payload}")
            
            # Parse topic to get entity info
            # Topic format: homeassistant/switch/aicleaner_v3/object_id/cmd
            topic_parts = topic.split('/')
            if len(topic_parts) >= 4:
                component_type = topic_parts[1]
                object_id = topic_parts[3]
                
                # Handle switch commands
                if component_type == "switch":
                    await self._handle_switch_command(object_id, payload)
                
                # Handle other component commands...
                
        except Exception as e:
            logger.error(f"Error handling command message: {e}")
    
    async def _handle_switch_command(self, object_id: str, command: str):
        """Handle switch command with optimistic updates"""
        try:
            entity_key = f"switch.{object_id}"

            if command.upper() in ["ON", "OFF"]:
                new_state = command.upper()

                # Optimistically update switch state
                await self._update_entity_state("switch", object_id, new_state)
                logger.info(f"Optimistically updated {entity_key} to {new_state}")

                # Execute switch logic based on object_id
                try:
                    if object_id == "auto_cleanup":
                        await self._execute_auto_cleanup_toggle(new_state == "ON")
                    elif object_id == "ai_optimization":
                        await self._execute_ai_optimization_toggle(new_state == "ON")
                    elif object_id == "maintenance_mode":
                        await self._execute_maintenance_mode_toggle(new_state == "ON")

                    logger.info(f"Executed switch command for {object_id}: {command}")

                except Exception as e:
                    logger.error(f"Error executing switch logic for {object_id}: {e}")
                    # Revert state on failure
                    await self._update_entity_state("switch", object_id, "OFF" if new_state == "ON" else "ON")
                    logger.info(f"Reverted {entity_key} state due to execution failure.")

            else:
                logger.warning(f"Invalid switch command: {command}")

        except Exception as e:
            logger.error(f"Error handling switch command for {object_id}: {e}")
    
    async def _execute_auto_cleanup_toggle(self, enabled: bool):
        """Execute auto cleanup toggle logic"""
        if enabled:
            logger.info("Auto cleanup enabled")
            # Start auto cleanup logic
        else:
            logger.info("Auto cleanup disabled")
            # Stop auto cleanup logic
    
    async def _execute_ai_optimization_toggle(self, enabled: bool):
        """Execute AI optimization toggle logic"""
        if enabled:
            logger.info("AI optimization enabled")
            # Start AI optimization
        else:
            logger.info("AI optimization disabled")
            # Stop AI optimization
    
    async def _execute_maintenance_mode_toggle(self, enabled: bool):
        """Execute maintenance mode toggle logic"""
        if enabled:
            logger.info("Maintenance mode enabled")
            # Enter maintenance mode
        else:
            logger.info("Maintenance mode disabled")
            # Exit maintenance mode
    
    async def async_unpublish_device(self) -> bool:
        """Unpublish device and all entities"""
        try:
            # Publish empty configs to remove entities
            for entity_key, entity_data in self.published_entities.items():
                component_type = entity_data["component_type"]
                object_id = entity_data["object_id"]
                
                # Publish empty config to remove entity
                await self.mqtt_client.async_publish_discovery(
                    component_type,
                    object_id,
                    {},  # Empty config removes entity
                    retain=True
                )
            
            # Set device offline
            availability_topic = self.topic_manager.create_availability_topic()
            await self.mqtt_client.async_publish_state(
                availability_topic,
                "offline",
                retain=True
            )
            
            self.device_online = False
            self.published_entities.clear()
            
            logger.info("Successfully unpublished AICleaner v3 device")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unpublish device: {e}")
            return False
    
    def get_published_entities(self) -> Dict[str, Dict[str, Any]]:
        """Get all published entities"""
        return self.published_entities.copy()
    
    def is_device_online(self) -> bool:
        """Check if device is published as online"""
        return self.device_online
