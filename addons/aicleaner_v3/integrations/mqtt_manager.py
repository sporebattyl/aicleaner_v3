"""
MQTT manager for AI Cleaner addon.
Handles MQTT communication and discovery.
"""
import os
import logging
import asyncio
import json
import socket
from typing import Dict, Any, List, Optional, Callable

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

class MQTTManager:
    """
    MQTT manager.
    
    Features:
    - MQTT connection management
    - Auto-discovery
    - Sensor updates
    - Command handling
    """
    
    def __init__(self, config):
        """
        Initialize the MQTT manager.
        
        Args:
            config: Configuration
        """
        self.config = config
        self.logger = logging.getLogger("mqtt_manager")
        
        # MQTT settings
        self.enabled = config.get("enable_mqtt", True)
        self.broker_host = config.get("mqtt_broker_host", "core-mosquitto")
        self.broker_port = config.get("mqtt_broker_port", 1883)
        self.username = config.get("mqtt_username", "")
        self.password = config.get("mqtt_password", "")
        
        # Discovery prefix
        self.discovery_prefix = config.get("mqtt_discovery_prefix", "homeassistant")
        
        # Node ID (hostname)
        self.node_id = socket.gethostname()
        
        # MQTT client
        self.client = None
        
        # Connected flag
        self.connected = False
        
        # Command callback
        self.command_callback = None
        
    async def initialize(self):
        """Initialize the MQTT manager."""
        if not self.enabled:
            self.logger.info("MQTT disabled in configuration")
            return
            
        if not MQTT_AVAILABLE:
            self.logger.error("Paho MQTT package not available")
            return
            
        self.logger.info("Initializing MQTT manager")
        
        try:
            # Create MQTT client
            self.client = mqtt.Client(client_id=f"aicleaner_{self.node_id}")
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            # Set credentials if provided
            if self.username:
                self.client.username_pw_set(self.username, self.password)
                
            # Connect to broker
            self.client.connect_async(self.broker_host, self.broker_port)
            
            # Start loop in background thread
            self.client.loop_start()
            
            # Wait for connection
            for _ in range(10):
                if self.connected:
                    break
                await asyncio.sleep(1)
                
            if not self.connected:
                self.logger.error("Failed to connect to MQTT broker")
                return
                
            # Publish discovery information
            await self.publish_discovery()
            
            self.logger.info("MQTT manager initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing MQTT manager: {e}")
            
    async def shutdown(self):
        """Shutdown the MQTT manager."""
        self.logger.info("Shutting down MQTT manager")
        
        if self.client:
            # Stop loop
            self.client.loop_stop()
            
            # Disconnect
            self.client.disconnect()
            
    def _on_connect(self, client, userdata, flags, rc):
        """
        MQTT connect callback.
        
        Args:
            client: MQTT client
            userdata: User data
            flags: Flags
            rc: Result code
        """
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            self.connected = True
            
            # Subscribe to command topics
            topic = f"{self.discovery_prefix}/aicleaner/{self.node_id}/+/command"
            client.subscribe(topic)
            
        else:
            self.logger.error(f"Failed to connect to MQTT broker: {rc}")
            
    def _on_disconnect(self, client, userdata, rc):
        """
        MQTT disconnect callback.
        
        Args:
            client: MQTT client
            userdata: User data
            rc: Result code
        """
        self.logger.info("Disconnected from MQTT broker")
        self.connected = False
        
    def _on_message(self, client, userdata, msg):
        """
        MQTT message callback.
        
        Args:
            client: MQTT client
            userdata: User data
            msg: Message
        """
        try:
            # Parse topic
            topic_parts = msg.topic.split("/")
            
            if len(topic_parts) >= 5 and topic_parts[-1] == "command":
                # Extract command type
                command_type = topic_parts[-2]
                
                # Parse payload
                payload = json.loads(msg.payload.decode("utf-8"))
                
                self.logger.info(f"Received command: {command_type} - {payload}")
                
                # Call command callback if set
                if self.command_callback:
                    asyncio.create_task(self.command_callback(command_type, payload))
                    
        except Exception as e:
            self.logger.error(f"Error processing MQTT message: {e}")
            
    async def publish_discovery(self):
        """Publish MQTT discovery information."""
        if not self.connected:
            return
            
        try:
            # Publish sensor discovery
            await self.publish_sensor_discovery("api_calls_today", "API Calls Today", "calls")
            await self.publish_sensor_discovery("cost_estimate_today", "Cost Estimate Today", "USD")
            await self.publish_sensor_discovery("analysis_duration", "Analysis Duration", "s")
            await self.publish_sensor_discovery("analyses_completed", "Analyses Completed", "analyses")
            await self.publish_sensor_discovery("tasks_generated", "Tasks Generated", "tasks")
            
            # Publish button discovery
            for zone in self.config.get("zones", []):
                zone_name = zone.get("name")
                if zone_name:
                    await self.publish_button_discovery(f"analyze_{zone_name}", f"Analyze {zone_name}")
                    
            self.logger.info("Published MQTT discovery information")
            
        except Exception as e:
            self.logger.error(f"Error publishing MQTT discovery: {e}")
            
    async def publish_sensor_discovery(self, name: str, friendly_name: str, unit: str):
        """
        Publish sensor discovery.
        
        Args:
            name: Sensor name
            friendly_name: Friendly name
            unit: Unit of measurement
        """
        if not self.connected:
            return
            
        try:
            # Create discovery payload
            payload = {
                "name": friendly_name,
                "unique_id": f"aicleaner_{self.node_id}_{name}",
                "state_topic": f"{self.discovery_prefix}/sensor/aicleaner/{self.node_id}/{name}/state",
                "json_attributes_topic": f"{self.discovery_prefix}/sensor/aicleaner/{self.node_id}/{name}/attributes",
                "unit_of_measurement": unit,
                "device": {
                    "identifiers": [f"aicleaner_{self.node_id}"],
                    "name": self.config.get("display_name", "AI Cleaner"),
                    "model": "AI Cleaner v3",
                    "manufacturer": "Home Assistant Community"
                }
            }
            
            # Publish discovery
            topic = f"{self.discovery_prefix}/sensor/aicleaner/{self.node_id}/{name}/config"
            self.client.publish(topic, json.dumps(payload), retain=True)
            
        except Exception as e:
            self.logger.error(f"Error publishing sensor discovery: {e}")
            
    async def publish_button_discovery(self, name: str, friendly_name: str):
        """
        Publish button discovery.
        
        Args:
            name: Button name
            friendly_name: Friendly name
        """
        if not self.connected:
            return
            
        try:
            # Create discovery payload
            payload = {
                "name": friendly_name,
                "unique_id": f"aicleaner_{self.node_id}_{name}",
                "command_topic": f"{self.discovery_prefix}/button/aicleaner/{self.node_id}/{name}/command",
                "device": {
                    "identifiers": [f"aicleaner_{self.node_id}"],
                    "name": self.config.get("display_name", "AI Cleaner"),
                    "model": "AI Cleaner v3",
                    "manufacturer": "Home Assistant Community"
                }
            }
            
            # Publish discovery
            topic = f"{self.discovery_prefix}/button/aicleaner/{self.node_id}/{name}/config"
            self.client.publish(topic, json.dumps(payload), retain=True)
            
        except Exception as e:
            self.logger.error(f"Error publishing button discovery: {e}")
            
    async def update_sensor(self, name: str, state: Any, attributes: Dict[str, Any] = None):
        """
        Update sensor.
        
        Args:
            name: Sensor name
            state: State
            attributes: Attributes
        """
        if not self.connected:
            return
            
        try:
            # Publish state
            state_topic = f"{self.discovery_prefix}/sensor/aicleaner/{self.node_id}/{name}/state"
            self.client.publish(state_topic, str(state))
            
            # Publish attributes
            if attributes:
                attr_topic = f"{self.discovery_prefix}/sensor/aicleaner/{self.node_id}/{name}/attributes"
                self.client.publish(attr_topic, json.dumps(attributes))
                
        except Exception as e:
            self.logger.error(f"Error updating sensor: {e}")
            
    def set_command_callback(self, callback):
        """
        Set command callback.
        
        Args:
            callback: Callback function
        """
        self.command_callback = callback


