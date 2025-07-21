"""
MQTT Client Manager for AICleaner v3
Phase 4B: MQTT Discovery Implementation

Handles MQTT connection, publishing, and message processing for Home Assistant integration.
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime

import paho.mqtt.client as mqtt
from paho.mqtt.client import MQTTMessage

from utils.unified_logger import get_logger

logger = get_logger(__name__)


@dataclass
class MQTTConfig:
    """MQTT configuration parameters"""
    enabled: bool = True
    host: str = "core-mosquitto"
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    base_topic: str = "aicleaner"
    keepalive: int = 60
    qos: int = 1
    retain: bool = True
    client_id: Optional[str] = None


class MQTTClientManager:
    """
    MQTT Client Manager for Home Assistant Discovery and Communication
    
    Handles:
    - Connection management with automatic reconnection
    - Publishing discovery configurations
    - State updates and command handling
    - Birth and Last Will & Testament (LWT) messages
    """
    
    def __init__(self, config: MQTTConfig, device_id: str):
        self.config = config
        self.device_id = device_id
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.message_callbacks: Dict[str, Callable] = {}
        
        # Generate unique client ID if not provided
        if not self.config.client_id:
            self.config.client_id = f"aicleaner_{device_id}_{uuid.uuid4().hex[:8]}"
        
        # MQTT topics
        self.base_topic = f"{self.config.base_topic}/{self.device_id}"
        self.lwt_topic = f"{self.base_topic}/status"
        self.discovery_prefix = "homeassistant"
        
        logger.info(f"MQTT Client Manager initialized for device {device_id}")

    async def connect(self) -> bool:
        """Connect to MQTT broker with automatic reconnection"""
        try:
            if self.client:
                await self.disconnect()
            
            # Create MQTT client
            self.client = mqtt.Client(
                client_id=self.config.client_id,
                clean_session=True,
                protocol=mqtt.MQTTv311
            )
            
            # Set up authentication if provided
            if self.config.username and self.config.password:
                self.client.username_pw_set(self.config.username, self.config.password)
            
            # Configure Last Will and Testament
            self.client.will_set(
                topic=self.lwt_topic,
                payload="offline",
                qos=self.config.qos,
                retain=self.config.retain
            )
            
            # Set up callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_log = self._on_log
            
            # Enable automatic reconnection
            self.client.reconnect_delay_set(min_delay=1, max_delay=120)
            
            # Connect to broker
            logger.info(f"Connecting to MQTT broker at {self.config.host}:{self.config.port}")
            self.client.connect(
                host=self.config.host,
                port=self.config.port,
                keepalive=self.config.keepalive
            )
            
            # Start network loop in background thread
            self.client.loop_start()
            
            # Wait for connection with timeout
            for _ in range(50):  # 5 second timeout
                if self.connected:
                    break
                await asyncio.sleep(0.1)
            
            if not self.connected:
                logger.error("Failed to connect to MQTT broker within timeout")
                return False
            
            logger.info("Successfully connected to MQTT broker")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from MQTT broker and cleanup"""
        try:
            if self.client and self.connected:
                # Publish offline status
                await self.publish_state(self.lwt_topic, "offline", retain=True)
                
                # Stop network loop and disconnect
                self.client.loop_stop()
                self.client.disconnect()
                
            self.connected = False
            self.client = None
            logger.info("Disconnected from MQTT broker")
            
        except Exception as e:
            logger.error(f"Error disconnecting from MQTT broker: {e}")

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Dict, rc: int) -> None:
        """Callback for successful MQTT connection"""
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to MQTT broker with result code {rc}")
            
            # Publish birth message
            client.publish(
                topic=self.lwt_topic,
                payload="online",
                qos=self.config.qos,
                retain=self.config.retain
            )
            
            # Subscribe to command topics
            self._subscribe_to_command_topics()
            
        else:
            self.connected = False
            logger.error(f"Failed to connect to MQTT broker with result code {rc}")

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        """Callback for MQTT disconnection"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection with result code {rc}")
        else:
            logger.info("Clean MQTT disconnection")

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: MQTTMessage) -> None:
        """Callback for received MQTT messages"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logger.debug(f"Received MQTT message: {topic} = {payload}")
            
            # Route message to appropriate handler
            for topic_pattern, callback in self.message_callbacks.items():
                if topic.startswith(topic_pattern):
                    asyncio.create_task(callback(topic, payload))
                    break
            
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _on_log(self, client: mqtt.Client, userdata: Any, level: int, buf: str) -> None:
        """Callback for MQTT client logging"""
        # Only log errors and warnings to avoid spam
        if level <= mqtt.MQTT_LOG_WARNING:
            logger.debug(f"MQTT Client Log: {buf}")

    def _subscribe_to_command_topics(self) -> None:
        """Subscribe to all command topics for this device"""
        try:
            command_topic = f"{self.base_topic}/+/command"
            self.client.subscribe(command_topic, qos=self.config.qos)
            logger.info(f"Subscribed to command topics: {command_topic}")
            
        except Exception as e:
            logger.error(f"Error subscribing to command topics: {e}")

    def register_message_callback(self, topic_prefix: str, callback: Callable) -> None:
        """Register callback for messages matching topic prefix"""
        self.message_callbacks[topic_prefix] = callback
        logger.debug(f"Registered message callback for topic prefix: {topic_prefix}")

    async def publish_discovery_config(self, component: str, object_id: str, config: Dict[str, Any]) -> bool:
        """Publish Home Assistant discovery configuration"""
        try:
            topic = f"{self.discovery_prefix}/{component}/{self.device_id}/{object_id}/config"
            payload = json.dumps(config)
            
            return await self.publish_state(topic, payload, retain=True)
            
        except Exception as e:
            logger.error(f"Error publishing discovery config: {e}")
            return False

    async def publish_state(self, topic: str, payload: str, retain: bool = None) -> bool:
        """Publish state message to MQTT topic"""
        try:
            if not self.client or not self.connected:
                logger.warning("Cannot publish: MQTT client not connected")
                return False
            
            if retain is None:
                retain = self.config.retain
            
            result = self.client.publish(
                topic=topic,
                payload=payload,
                qos=self.config.qos,
                retain=retain
            )
            
            # Wait for message to be published
            result.wait_for_publish(timeout=5.0)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published to {topic}: {payload}")
                return True
            else:
                logger.error(f"Failed to publish to {topic}: Error code {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing to {topic}: {e}")
            return False

    async def publish_entity_state(self, entity_id: str, state: str, attributes: Optional[Dict] = None) -> bool:
        """Publish entity state and attributes"""
        try:
            # Publish state
            state_topic = f"{self.base_topic}/{entity_id}/state"
            success = await self.publish_state(state_topic, state)
            
            # Publish attributes if provided
            if attributes:
                attr_topic = f"{self.base_topic}/attributes"
                attr_payload = json.dumps({
                    entity_id: attributes,
                    "last_updated": datetime.now().isoformat()
                })
                await self.publish_state(attr_topic, attr_payload)
            
            return success
            
        except Exception as e:
            logger.error(f"Error publishing entity state for {entity_id}: {e}")
            return False

    async def remove_discovery_config(self, component: str, object_id: str) -> bool:
        """Remove Home Assistant discovery configuration by publishing empty payload"""
        try:
            topic = f"{self.discovery_prefix}/{component}/{self.device_id}/{object_id}/config"
            return await self.publish_state(topic, "", retain=True)
            
        except Exception as e:
            logger.error(f"Error removing discovery config: {e}")
            return False

    def get_device_topic(self, entity_id: str) -> str:
        """Get the base topic for a specific entity"""
        return f"{self.base_topic}/{entity_id}"

    def get_discovery_topic(self, component: str, object_id: str) -> str:
        """Get the discovery topic for a specific entity"""
        return f"{self.discovery_prefix}/{component}/{self.device_id}/{object_id}/config"

    def get_status(self) -> Dict[str, Any]:
        """Get current MQTT client status"""
        return {
            "connected": self.connected,
            "client_id": self.config.client_id,
            "device_id": self.device_id,
            "broker": f"{self.config.host}:{self.config.port}",
            "base_topic": self.base_topic,
            "callbacks_registered": len(self.message_callbacks)
        }