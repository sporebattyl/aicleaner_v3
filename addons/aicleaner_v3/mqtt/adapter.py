"""
MQTT Adapter Implementation
Phase 4B: MQTT Discovery System

MQTTAdapter provides clean interface for MQTT communication following the
established adapter pattern. Supports both real MQTT and mock mode for testing.
"""

import json
import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from dataclasses import dataclass

# Performance optimization - Phase 5A
from performance.serialization_optimizer import fast_json_dumps, fast_json_loads

import paho.mqtt.client as mqtt

from .config import MQTTConfig


logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Device information for MQTT discovery"""
    entity_id: str
    name: str
    device_class: Optional[str] = None
    state_class: Optional[str] = None
    unit_of_measurement: Optional[str] = None
    icon: Optional[str] = None
    entity_category: Optional[str] = None


@dataclass
class DiscoveryMessage:
    """MQTT Discovery message structure"""
    component: str  # sensor, binary_sensor, switch, etc.
    object_id: str
    config: Dict[str, Any]
    topic: str


class MQTTAdapter:
    """
    MQTT Adapter for Home Assistant Discovery
    
    Provides clean interface for MQTT communication with support for:
    - Device discovery and registration
    - State publishing and command handling
    - Connection management with automatic reconnection
    - Mock mode for testing without real MQTT broker
    """
    
    def __init__(self, config: MQTTConfig, mock_mode: bool = False):
        """Initialize MQTT adapter"""
        self.config = config
        self.mock_mode = mock_mode
        
        # Connection state
        self._connected = False
        self._running = False
        self._client: Optional[mqtt.Client] = None
        
        # Discovery and state tracking
        self._discovered_entities: Dict[str, DiscoveryMessage] = {}
        self._entity_states: Dict[str, Any] = {}
        self._command_callbacks: Dict[str, Callable] = {}
        
        # Mock mode storage
        self._mock_published_messages: List[Dict[str, Any]] = []
        self._mock_subscriptions: List[str] = []
        
        # Metrics
        self._connection_attempts = 0
        self._last_connection_time: Optional[datetime] = None
        self._messages_published = 0
        self._messages_received = 0
        
        if not mock_mode:
            self._setup_mqtt_client()
    
    def _setup_mqtt_client(self):
        """Setup MQTT client with callbacks"""
        client_id = self.config.get_client_id()
        self._client = mqtt.Client(client_id=client_id, clean_session=self.config.clean_session)
        
        # Set authentication if provided
        if self.config.username and self.config.password:
            self._client.username_pw_set(self.config.username, self.config.password)
        
        # Setup TLS if enabled
        if self.config.use_tls:
            self._client.tls_set(
                ca_certs=self.config.ca_cert_path,
                certfile=self.config.cert_path,
                keyfile=self.config.key_path
            )
        
        # Setup callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.on_publish = self._on_publish
        self._client.on_subscribe = self._on_subscribe
        
        # Setup last will if configured
        if self.config.will_topic and self.config.will_payload:
            self._client.will_set(
                self.config.will_topic,
                self.config.will_payload,
                qos=self.config.qos_state,
                retain=True
            )
    
    async def start(self) -> bool:
        """Start MQTT adapter"""
        if self.mock_mode:
            logger.info("Starting MQTT adapter in mock mode")
            self._connected = True
            self._running = True
            return True
        
        try:
            logger.info(f"Connecting to MQTT broker at {self.config.broker_host}:{self.config.broker_port}")
            
            self._running = True
            self._connection_attempts += 1
            
            # Connect to broker
            result = self._client.connect(
                self.config.broker_host,
                self.config.broker_port,
                self.config.keepalive
            )
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                # Start network loop
                self._client.loop_start()
                
                # Wait for connection
                await self._wait_for_connection()
                
                # Publish availability
                await self._publish_availability("online")
                
                logger.info("MQTT adapter started successfully")
                return True
            else:
                logger.error(f"Failed to connect to MQTT broker: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting MQTT adapter: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop MQTT adapter"""
        if self.mock_mode:
            logger.info("Stopping MQTT adapter (mock mode)")
            self._connected = False
            self._running = False
            return True
        
        try:
            self._running = False
            
            if self._client and self._connected:
                # Publish offline availability
                await self._publish_availability("offline")
                
                # Disconnect from broker
                self._client.disconnect()
                self._client.loop_stop()
                
                logger.info("MQTT adapter stopped successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Error stopping MQTT adapter: {e}")
            return False
    
    async def publish_discovery_message(self, device_info: DeviceInfo, component: str = "sensor") -> bool:
        """
        Publish MQTT discovery message for a device
        
        Args:
            device_info: Device information
            component: HA component type (sensor, binary_sensor, switch, etc.)
        
        Returns:
            Success status
        """
        try:
            # Generate discovery configuration
            config = self._build_discovery_config(device_info, component)
            topic = self.config.get_discovery_topic(component, device_info.entity_id)
            
            # Create discovery message
            discovery_msg = DiscoveryMessage(
                component=component,
                object_id=device_info.entity_id,
                config=config,
                topic=topic
            )
            
            # Store for re-publishing on reconnection
            self._discovered_entities[device_info.entity_id] = discovery_msg
            
            # Publish discovery message
            success = await self._publish_message(
                topic,
                fast_json_dumps(config),
                qos=self.config.qos_discovery,
                retain=self.config.retain_discovery
            )
            
            if success:
                logger.info(f"Published discovery for {device_info.entity_id} ({component})")
            else:
                logger.error(f"Failed to publish discovery for {device_info.entity_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error publishing discovery message: {e}")
            return False
    
    async def publish_state(self, entity_id: str, state: Any, attributes: Optional[Dict[str, Any]] = None) -> bool:
        """
        Publish state update for an entity
        
        Args:
            entity_id: Entity identifier
            state: State value
            attributes: Optional attributes dictionary
        
        Returns:
            Success status
        """
        try:
            # Build state payload
            payload = {
                "state": state,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if attributes:
                payload["attributes"] = attributes
            
            # Store current state
            self._entity_states[entity_id] = payload
            
            # Publish state
            topic = self.config.get_state_topic(entity_id)
            success = await self._publish_message(
                topic,
                fast_json_dumps(payload),
                qos=self.config.qos_state,
                retain=self.config.retain_state
            )
            
            if success:
                logger.debug(f"Published state for {entity_id}: {state}")
            else:
                logger.error(f"Failed to publish state for {entity_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error publishing state: {e}")
            return False
    
    async def subscribe_to_commands(self, entity_id: str, callback: Callable[[str, Any], None]) -> bool:
        """
        Subscribe to command topic for an entity
        
        Args:
            entity_id: Entity identifier
            callback: Function to call when command received
        
        Returns:
            Success status
        """
        try:
            topic = self.config.get_command_topic(entity_id)
            self._command_callbacks[topic] = callback
            
            if self.mock_mode:
                self._mock_subscriptions.append(topic)
                logger.info(f"Mock subscription to {topic}")
                return True
            
            if self._client and self._connected:
                result, _ = self._client.subscribe(topic, qos=self.config.qos_command)
                if result == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"Subscribed to command topic: {topic}")
                    return True
                else:
                    logger.error(f"Failed to subscribe to {topic}: {result}")
                    return False
            else:
                logger.warning(f"Cannot subscribe to {topic}: not connected")
                return False
                
        except Exception as e:
            logger.error(f"Error subscribing to commands: {e}")
            return False
    
    async def unsubscribe_from_commands(self, entity_id: str) -> bool:
        """Unsubscribe from command topic for an entity"""
        try:
            topic = self.config.get_command_topic(entity_id)
            
            if topic in self._command_callbacks:
                del self._command_callbacks[topic]
            
            if self.mock_mode:
                if topic in self._mock_subscriptions:
                    self._mock_subscriptions.remove(topic)
                return True
            
            if self._client and self._connected:
                result, _ = self._client.unsubscribe(topic)
                return result == mqtt.MQTT_ERR_SUCCESS
            
            return False
            
        except Exception as e:
            logger.error(f"Error unsubscribing from commands: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if adapter is connected"""
        return self._connected
    
    def is_running(self) -> bool:
        """Check if adapter is running"""
        return self._running
    
    def get_status(self) -> Dict[str, Any]:
        """Get adapter status information"""
        return {
            "connected": self._connected,
            "running": self._running,
            "mock_mode": self.mock_mode,
            "connection_attempts": self._connection_attempts,
            "last_connection": self._last_connection_time.isoformat() if self._last_connection_time else None,
            "discovered_entities": len(self._discovered_entities),
            "active_subscriptions": len(self._command_callbacks),
            "messages_published": self._messages_published,
            "messages_received": self._messages_received,
            "broker_host": self.config.broker_host,
            "broker_port": self.config.broker_port
        }
    
    def get_mock_published_messages(self) -> List[Dict[str, Any]]:
        """Get published messages in mock mode"""
        return self._mock_published_messages.copy()
    
    def get_mock_subscriptions(self) -> List[str]:
        """Get subscriptions in mock mode"""
        return self._mock_subscriptions.copy()
    
    def clear_mock_data(self):
        """Clear mock mode data"""
        self._mock_published_messages.clear()
        self._mock_subscriptions.clear()
    
    # Private methods
    
    def _build_discovery_config(self, device_info: DeviceInfo, component: str) -> Dict[str, Any]:
        """Build Home Assistant discovery configuration"""
        config = {
            "unique_id": f"{self.config.device_id}_{device_info.entity_id}",
            "name": device_info.name,
            "state_topic": self.config.get_state_topic(device_info.entity_id),
            "availability_topic": self.config.get_availability_topic(),
            "device": {
                "identifiers": [self.config.device_id],
                "name": self.config.device_name,
                "manufacturer": "AICleaner",
                "model": "AICleaner v3",
                "sw_version": "3.0.0"
            }
        }
        
        # Add optional attributes
        if device_info.device_class:
            config["device_class"] = device_info.device_class
        if device_info.state_class:
            config["state_class"] = device_info.state_class
        if device_info.unit_of_measurement:
            config["unit_of_measurement"] = device_info.unit_of_measurement
        if device_info.icon:
            config["icon"] = device_info.icon
        if device_info.entity_category:
            config["entity_category"] = device_info.entity_category
        
        # Add command topic for writable entities
        if component in ["switch", "button", "select"]:
            config["command_topic"] = self.config.get_command_topic(device_info.entity_id)
        
        # Component-specific configuration
        if component == "sensor":
            config["value_template"] = "{{ value_json.state }}"
        elif component == "binary_sensor":
            config["value_template"] = "{{ value_json.state }}"
            config["payload_on"] = "ON"
            config["payload_off"] = "OFF"
        elif component == "switch":
            config["value_template"] = "{{ value_json.state }}"
            config["payload_on"] = "ON"
            config["payload_off"] = "OFF"
            config["state_on"] = "ON"
            config["state_off"] = "OFF"
        
        return config
    
    async def _publish_message(self, topic: str, payload: str, qos: int = 1, retain: bool = False) -> bool:
        """Publish MQTT message"""
        if self.mock_mode:
            self._mock_published_messages.append({
                "topic": topic,
                "payload": payload,
                "qos": qos,
                "retain": retain,
                "timestamp": datetime.utcnow().isoformat()
            })
            self._messages_published += 1
            return True
        
        if not self._client or not self._connected:
            logger.warning(f"Cannot publish to {topic}: not connected")
            return False
        
        try:
            info = self._client.publish(topic, payload, qos=qos, retain=retain)
            
            # Wait for message to be published for QoS > 0
            if qos > 0:
                info.wait_for_publish(timeout=5.0)
            
            self._messages_published += 1
            return True
            
        except Exception as e:
            logger.error(f"Error publishing message to {topic}: {e}")
            return False
    
    async def _publish_availability(self, status: str):
        """Publish device availability status"""
        topic = self.config.get_availability_topic()
        await self._publish_message(topic, status, qos=1, retain=True)
    
    async def _wait_for_connection(self, timeout: float = 10.0):
        """Wait for MQTT connection"""
        start_time = time.time()
        while not self._connected and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.1)
        
        if not self._connected:
            raise TimeoutError("MQTT connection timeout")
    
    async def _republish_discovery_messages(self):
        """Republish all discovery messages on reconnection"""
        logger.info("Republishing discovery messages after reconnection")
        
        for entity_id, discovery_msg in self._discovered_entities.items():
            await self._publish_message(
                discovery_msg.topic,
                fast_json_dumps(discovery_msg.config),
                qos=self.config.qos_discovery,
                retain=self.config.retain_discovery
            )
            
            # Also republish current state if available
            if entity_id in self._entity_states:
                state_topic = self.config.get_state_topic(entity_id)
                await self._publish_message(
                    state_topic,
                    fast_json_dumps(self._entity_states[entity_id]),
                    qos=self.config.qos_state,
                    retain=self.config.retain_state
                )
    
    async def _resubscribe_to_commands(self):
        """Resubscribe to all command topics on reconnection"""
        for topic in self._command_callbacks.keys():
            if self._client:
                self._client.subscribe(topic, qos=self.config.qos_command)
    
    # MQTT Callbacks
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self._connected = True
            self._last_connection_time = datetime.utcnow()
            logger.info("Connected to MQTT broker")
            
            # Schedule async tasks
            asyncio.create_task(self._publish_availability("online"))
            asyncio.create_task(self._republish_discovery_messages())
            asyncio.create_task(self._resubscribe_to_commands())
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self._connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection: {rc}")
        else:
            logger.info("Disconnected from MQTT broker")
    
    def _on_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            self._messages_received += 1
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logger.debug(f"Received MQTT message on {topic}: {payload}")
            
            # Handle command messages
            if topic in self._command_callbacks:
                callback = self._command_callbacks[topic]
                try:
                    # Parse JSON payload if possible
                    try:
                        parsed_payload = fast_json_loads(payload)
                    except json.JSONDecodeError:
                        parsed_payload = payload
                    
                    # Call the registered callback
                    callback(topic, parsed_payload)
                    
                except Exception as e:
                    logger.error(f"Error in command callback for {topic}: {e}")
            
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def _on_publish(self, client, userdata, mid):
        """MQTT publish callback"""
        logger.debug(f"Message published: {mid}")
    
    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """MQTT subscribe callback"""
        logger.debug(f"Subscribed: {mid}, QoS: {granted_qos}")