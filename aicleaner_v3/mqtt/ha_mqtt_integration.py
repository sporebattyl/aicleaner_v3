"""
Home Assistant MQTT Integration
Coordinates MQTT Discovery with Home Assistant integration
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class HAMQTTIntegration:
    """
    Coordinates MQTT Discovery with Home Assistant integration
    """
    
    def __init__(self, hass, mqtt_client, topic_manager, device_publisher):
        """Initialize HA MQTT Integration"""
        self.hass = hass
        self.mqtt_client = mqtt_client
        self.topic_manager = topic_manager
        self.device_publisher = device_publisher
        self.integration_active = False
        
    async def async_setup(self) -> bool:
        """Set up HA MQTT integration"""
        try:
            # Set will topic on MQTT client
            availability_topic = self.topic_manager.create_availability_topic()
            self.mqtt_client.set_will(availability_topic, "offline", retain=True)
            
            # Connect to MQTT broker
            if not await self.mqtt_client.async_connect():
                logger.error("Failed to connect to MQTT broker")
                return False
            
            # Publish device via MQTT Discovery
            if not await self.device_publisher.async_publish_device():
                logger.error("Failed to publish device via MQTT Discovery")
                return False
            
            # Set up periodic state updates
            await self._setup_periodic_updates()
            
            # Register HA event listeners
            await self._register_ha_event_listeners()
            
            self.integration_active = True
            logger.info("HA MQTT Integration setup completed")
            
            # Fire integration ready event
            self.hass.bus.async_fire("aicleaner_v3_mqtt_ready", {
                "mqtt_connected": self.mqtt_client.is_connected(),
                "device_published": self.device_publisher.is_device_online()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"HA MQTT Integration setup failed: {e}")
            return False
    
    async def async_shutdown(self):
        """Shutdown HA MQTT integration"""
        try:
            self.integration_active = False
            
            # Unpublish device
            await self.device_publisher.async_unpublish_device()
            
            # Disconnect from MQTT
            await self.mqtt_client.async_disconnect()
            
            logger.info("HA MQTT Integration shutdown completed")
            
        except Exception as e:
            logger.error(f"HA MQTT Integration shutdown error: {e}")
    
    async def _setup_periodic_updates(self):
        """Set up periodic state updates"""
        try:
            # Update system metrics every 30 seconds
            async def update_system_metrics():
                while self.integration_active:
                    try:
                        await self._update_system_metrics()
                        await asyncio.sleep(30)
                    except Exception as e:
                        logger.error(f"Error updating system metrics: {e}")
                        await asyncio.sleep(30)
            
            # Start background task
            asyncio.create_task(update_system_metrics())
            
            # Update availability every 60 seconds
            async def update_availability():
                while self.integration_active:
                    try:
                        availability_topic = self.topic_manager.create_availability_topic()
                        await self.mqtt_client.async_publish_state(
                            availability_topic,
                            "online",
                            retain=True
                        )
                        await asyncio.sleep(60)
                    except Exception as e:
                        logger.error(f"Error updating availability: {e}")
                        await asyncio.sleep(60)
            
            # Start availability task
            asyncio.create_task(update_availability())
            
            logger.info("Set up periodic MQTT updates")
            
        except Exception as e:
            logger.error(f"Error setting up periodic updates: {e}")
    
    async def _update_system_metrics(self):
        """Update system metrics via MQTT"""
        try:
            # Get current metrics (this would integrate with actual monitoring)
            metrics = await self._collect_system_metrics()
            
            # Update CPU usage
            await self.device_publisher._update_entity_state(
                "sensor", "cpu_usage", metrics.get("cpu_usage", 0)
            )
            
            # Update memory usage
            await self.device_publisher._update_entity_state(
                "sensor", "memory_usage", metrics.get("memory_usage", 0)
            )
            
            # Update performance score
            await self.device_publisher._update_entity_state(
                "sensor", "performance_score", metrics.get("performance_score", 100)
            )
            
            # Update system health
            system_healthy = metrics.get("cpu_usage", 0) < 80 and metrics.get("memory_usage", 0) < 90
            await self.device_publisher._update_entity_state(
                "binary_sensor", "system_health", "OFF" if system_healthy else "ON"
            )
            
        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")
    
    async def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        try:
            # This would integrate with the actual performance monitor
            import psutil
            
            metrics = {
                "cpu_usage": psutil.cpu_percent(interval=1),
                "memory_usage": psutil.virtual_memory().percent,
                "timestamp": datetime.now().isoformat()
            }
            
            # Calculate performance score
            cpu_score = max(0, 100 - metrics["cpu_usage"])
            memory_score = max(0, 100 - metrics["memory_usage"])
            metrics["performance_score"] = int((cpu_score + memory_score) / 2)
            
            return metrics
            
        except ImportError:
            # Fallback if psutil not available
            return {
                "cpu_usage": 15.0,
                "memory_usage": 45.0,
                "performance_score": 85,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {}
    
    async def _register_ha_event_listeners(self):
        """Register Home Assistant event listeners"""
        try:
            # Listen for cleanup events
            self.hass.bus.async_listen("aicleaner_v3_cleanup_started", self._handle_cleanup_started)
            self.hass.bus.async_listen("aicleaner_v3_cleanup_completed", self._handle_cleanup_completed)
            self.hass.bus.async_listen("aicleaner_v3_cleanup_failed", self._handle_cleanup_failed)
            
            # Listen for optimization events
            self.hass.bus.async_listen("aicleaner_v3_optimization_started", self._handle_optimization_started)
            self.hass.bus.async_listen("aicleaner_v3_optimization_completed", self._handle_optimization_completed)
            
            logger.info("Registered HA event listeners for MQTT integration")
            
        except Exception as e:
            logger.error(f"Error registering HA event listeners: {e}")
    
    async def _handle_cleanup_started(self, event):
        """Handle cleanup started event"""
        try:
            # Update cleanup active binary sensor
            await self.device_publisher._update_entity_state(
                "binary_sensor", "cleanup_active", "ON"
            )
            
            # Reset cleanup progress
            await self.device_publisher._update_entity_state(
                "sensor", "cleanup_progress", 0
            )
            
            logger.info("Updated MQTT entities for cleanup started")
            
        except Exception as e:
            logger.error(f"Error handling cleanup started event: {e}")
    
    async def _handle_cleanup_completed(self, event):
        """Handle cleanup completed event"""
        try:
            # Update cleanup active binary sensor
            await self.device_publisher._update_entity_state(
                "binary_sensor", "cleanup_active", "OFF"
            )
            
            # Set cleanup progress to 100%
            await self.device_publisher._update_entity_state(
                "sensor", "cleanup_progress", 100
            )
            
            # Update last cleanup timestamp
            await self.device_publisher._update_entity_state(
                "sensor", "last_cleanup", datetime.now().isoformat()
            )
            
            logger.info("Updated MQTT entities for cleanup completed")
            
        except Exception as e:
            logger.error(f"Error handling cleanup completed event: {e}")
    
    async def _handle_cleanup_failed(self, event):
        """Handle cleanup failed event"""
        try:
            # Update cleanup active binary sensor
            await self.device_publisher._update_entity_state(
                "binary_sensor", "cleanup_active", "OFF"
            )
            
            # Keep current progress (partial completion)
            
            logger.info("Updated MQTT entities for cleanup failed")
            
        except Exception as e:
            logger.error(f"Error handling cleanup failed event: {e}")
    
    async def _handle_optimization_started(self, event):
        """Handle optimization started event"""
        try:
            # Could update specific optimization entities if needed
            logger.info("Handling optimization started event")
            
        except Exception as e:
            logger.error(f"Error handling optimization started event: {e}")
    
    async def _handle_optimization_completed(self, event):
        """Handle optimization completed event"""
        try:
            # Update performance score after optimization
            await asyncio.sleep(5)  # Wait for metrics to update
            await self._update_system_metrics()
            
            logger.info("Updated MQTT entities after optimization")
            
        except Exception as e:
            logger.error(f"Error handling optimization completed event: {e}")
    
    async def async_update_cleanup_progress(self, progress: int):
        """Update cleanup progress via MQTT"""
        try:
            await self.device_publisher._update_entity_state(
                "sensor", "cleanup_progress", min(100, max(0, progress))
            )
        except Exception as e:
            logger.error(f"Error updating cleanup progress: {e}")
    
    async def async_publish_custom_entity(
        self,
        component_type: str,
        object_id: str,
        name: str,
        initial_state: Any = None,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Publish custom entity via MQTT Discovery"""
        try:
            # Create base config based on component type
            if component_type == "sensor":
                config = self.topic_manager.create_sensor_config(object_id, name)
            elif component_type == "switch":
                config = self.topic_manager.create_switch_config(object_id, name)
            elif component_type == "binary_sensor":
                config = self.topic_manager.create_binary_sensor_config(object_id, name)
            else:
                logger.error(f"Unsupported component type: {component_type}")
                return False
            
            # Apply config overrides
            if config_overrides:
                config.update(config_overrides)
            
            # Publish entity config
            success = await self.device_publisher._publish_entity_config(
                component_type, object_id, config
            )
            
            if success and initial_state is not None:
                await self.device_publisher._update_entity_state(
                    component_type, object_id, initial_state
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error publishing custom entity {component_type}.{object_id}: {e}")
            return False
    
    def is_integration_active(self) -> bool:
        """Check if MQTT integration is active"""
        return self.integration_active
    
    def get_mqtt_status(self) -> Dict[str, Any]:
        """Get MQTT integration status"""
        return {
            "integration_active": self.integration_active,
            "mqtt_connected": self.mqtt_client.is_connected() if self.mqtt_client else False,
            "device_online": self.device_publisher.is_device_online() if self.device_publisher else False,
            "published_entities": len(self.device_publisher.get_published_entities()) if self.device_publisher else 0
        }
