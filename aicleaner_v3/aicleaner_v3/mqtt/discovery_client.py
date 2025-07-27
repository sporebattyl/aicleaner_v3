"""
MQTT Discovery Client
Core MQTT client for Home Assistant Discovery protocol
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import ssl
import paho.mqtt.client as mqtt
from paho.mqtt.client import MQTTMessage

logger = logging.getLogger(__name__)

class MQTTDiscoveryClient:
    """
    MQTT Discovery Client for Home Assistant integration
    """
    
    def __init__(
        self,
        broker_host: str,
        broker_port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = False,
        discovery_prefix: str = "homeassistant"
    ):
        """Initialize MQTT Discovery Client"""
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.discovery_prefix = discovery_prefix
        
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.will_topic: Optional[str] = None
        self.subscribed_topics: List[str] = []
        self.message_handlers: Dict[str, Callable] = {}
        
        # Device information
        self.device_info = {
            "identifiers": ["aicleaner_v3"],
            "name": "AICleaner v3",
            "model": "AI Cleaning Assistant",
            "manufacturer": "AICleaner",
            "sw_version": "3.0.0"
        }
    
    def set_will(self, topic: str, payload: str = "offline", qos: int = 1, retain: bool = True):
        """Set the will (last will and testament) for the client.

        Args:
            topic: The topic to publish the will to.
            payload: The payload to send.
            qos: The quality of service level to use.
            retain: Whether the will should be retained.
        """
        self.will_topic = topic
        logger.info(f"Will set on topic: {topic} with payload: {payload}")
    
    async def async_connect(self) -> bool:
        """Connect to MQTT broker"""
        try:
            self.client = mqtt.Client(client_id="aicleaner_v3_discovery")
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_publish = self._on_publish
            
            # Configure authentication
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            # Configure TLS
            if self.use_tls:
                self.client.tls_set(ca_certs=None, certfile=None, keyfile=None, 
                                  cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS,
                                  ciphers=None)
            
            # Set Last Will and Testament (LWT)
            if self.will_topic:
                self.client.will_set(self.will_topic, payload="offline", qos=1, retain=True)

            # Connect to broker
            result = self.client.connect(self.broker_host, self.broker_port, 60)
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.client.loop_start()
                
                # Wait for connection
                for _ in range(50):  # 5 second timeout
                    if self.connected:
                        break
                    await asyncio.sleep(0.1)
                
                if self.connected:
                    logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
                    return True
                else:
                    logger.error("MQTT connection timeout")
                    return False
            else:
                logger.error(f"Failed to connect to MQTT broker: {result}")
                return False
                
        except Exception as e:
            logger.error(f"MQTT connection error: {e}")
            return False
    
    async def async_disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client and self.connected:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("Disconnected from MQTT broker")
    
    async def async_publish_discovery(
        self,
        component_type: str,
        object_id: str,
        config: Dict[str, Any],
        retain: bool = True
    ) -> bool:
        """
        Publish Home Assistant MQTT Discovery configuration
        """
        if not self.connected:
            logger.error("MQTT client not connected")
            return False
        
        try:
            # Build discovery topic
            topic = f"{self.discovery_prefix}/{component_type}/aicleaner_v3/{object_id}/config"

            # Add device info to config
            config["device"] = self.device_info

            # Add unique_id if not present
            if "unique_id" not in config:
                config["unique_id"] = f"aicleaner_v3_{object_id}"

            # Validate topic (import topic manager for validation)
            from .topic_manager import MQTTTopicManager
            if not MQTTTopicManager.validate_topic_structure(topic):
                logger.error(f"Invalid topic structure: {topic}")
                return False

            # Publish configuration
            payload = json.dumps(config)
            result = self.client.publish(topic, payload, qos=1, retain=retain)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published discovery config for {component_type}.{object_id}")
                return True
            else:
                logger.error(f"Failed to publish discovery config to {topic}: {result.rc}")
                return False

        except ValueError as ve:
            logger.error(f"JSON serialization error for {component_type}.{object_id}: {ve}")
            return False
        except Exception as e:
            logger.error(f"Error publishing discovery config for {component_type}.{object_id}: {e}")
            return False
    
    async def async_publish_state(
        self,
        state_topic: str,
        state: Any,
        retain: bool = False
    ) -> bool:
        """Publish entity state"""
        if not self.connected:
            logger.error("MQTT client not connected")
            return False
        
        try:
            payload = str(state) if not isinstance(state, dict) else json.dumps(state)
            result = self.client.publish(state_topic, payload, qos=1, retain=retain)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published state to {state_topic}: {payload}")
                return True
            else:
                logger.error(f"Failed to publish state: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing state: {e}")
            return False
    
    async def async_subscribe(self, topic: str, handler: Optional[Callable] = None) -> bool:
        """Subscribe to MQTT topic"""
        if not self.connected:
            logger.error("MQTT client not connected")
            return False
        
        try:
            result, _ = self.client.subscribe(topic, qos=1)
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.subscribed_topics.append(topic)
                if handler:
                    self.message_handlers[topic] = handler
                logger.info(f"Subscribed to topic: {topic}")
                return True
            else:
                logger.error(f"Failed to subscribe to {topic}: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error subscribing to topic: {e}")
            return False
    
    async def async_unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from MQTT topic"""
        if not self.connected:
            return True
        
        try:
            result, _ = self.client.unsubscribe(topic)
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                if topic in self.subscribed_topics:
                    self.subscribed_topics.remove(topic)
                if topic in self.message_handlers:
                    del self.message_handlers[topic]
                logger.info(f"Unsubscribed from topic: {topic}")
                return True
            else:
                logger.error(f"Failed to unsubscribe from {topic}: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error unsubscribing from topic: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection"""
        if rc == 0:
            self.connected = True
            logger.info("MQTT client connected successfully")
        else:
            self.connected = False
            logger.error(f"MQTT connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection"""
        self.connected = False
        if rc == 0:
            logger.info("MQTT client disconnected gracefully")
        else:
            logger.warning(f"MQTT client disconnected unexpectedly: {rc}")
    
    def _on_message(self, client, userdata, msg: MQTTMessage):
        """Handle incoming MQTT message"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logger.debug(f"Received message on {topic}: {payload}")
            
            # Call specific handler if registered
            if topic in self.message_handlers:
                handler = self.message_handlers[topic]
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(topic, payload))
                    else:
                        handler(topic, payload)
                except Exception as e:
                    logger.error(f"Error in message handler for {topic}: {e}")
            
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def _on_publish(self, client, userdata, mid):
        """Handle message publish confirmation"""
        logger.debug(f"Message {mid} published successfully")
    
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.connected
    
    def get_subscribed_topics(self) -> List[str]:
        """Get list of subscribed topics"""
        return self.subscribed_topics.copy()
