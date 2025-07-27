"""
MQTT Client for AICleaner Home Assistant Addon
Provides MQTT connectivity with discovery, birth/last will messages, and error handling
"""

import json
import logging
import time
import threading
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum

try:
    import paho.mqtt.client as mqtt
except ImportError:
    logging.error("paho-mqtt not installed. Please install with: pip install paho-mqtt")
    mqtt = None


class MQTTConnectionState(Enum):
    """MQTT connection state enumeration"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class MQTTErrorRecovery:
    """MQTT error recovery and retry management"""

    def __init__(self, max_retries: int = 5, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.retry_count = 0
        self.last_error_time = 0

    def should_retry(self) -> bool:
        """Check if we should attempt retry"""
        return self.retry_count < self.max_retries

    def get_delay(self) -> float:
        """Get exponential backoff delay"""
        delay = min(self.base_delay * (2 ** self.retry_count), self.max_delay)
        return delay

    def record_attempt(self):
        """Record a retry attempt"""
        self.retry_count += 1
        self.last_error_time = time.time()

    def reset(self):
        """Reset retry counter on success"""
        self.retry_count = 0
        self.last_error_time = 0


class MQTTClient:
    """
    MQTT Client for Home Assistant integration with discovery support
    Follows Home Assistant MQTT best practices and patterns
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize MQTT client with configuration
        
        Args:
            config: Dictionary containing MQTT configuration options
        """
        if mqtt is None:
            raise ImportError("paho-mqtt library is required but not installed")
            
        self.config = config
        self.client = None
        self.connected = False
        self.discovery_prefix = config.get('mqtt_discovery_prefix', 'homeassistant')
        self.availability_topic = config.get('mqtt_availability_topic', 'aicleaner/availability')
        self.client_id = config.get('mqtt_client_id', 'aicleaner')
        self.qos = config.get('mqtt_qos', 0)
        self.retain = config.get('mqtt_retain', False)
        
        # Enhanced error handling and recovery
        self.connection_state = MQTTConnectionState.DISCONNECTED
        self.error_recovery = MQTTErrorRecovery(
            max_retries=config.get('mqtt_max_retries', 5),
            base_delay=config.get('mqtt_retry_delay', 1.0),
            max_delay=config.get('mqtt_max_retry_delay', 60.0)
        )
        self.last_successful_publish = 0
        self.publish_failure_count = 0
        self.connection_attempts = 0
        self.total_messages_sent = 0
        self.total_messages_received = 0

        # Callback handlers
        self.message_handlers: Dict[str, Callable] = {}
        self.connection_callbacks: list = []
        self.disconnection_callbacks: list = []

        # Thread safety
        self._lock = threading.Lock()

        # Enhanced logging with context
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info(f"MQTT Client initialized with broker: {config.get('mqtt_broker_host', 'localhost')}:{config.get('mqtt_broker_port', 1883)}")
        
    def initialize(self) -> bool:
        """
        Initialize MQTT client and setup callbacks
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Create MQTT client instance
            self.client = mqtt.Client(
                client_id=self.client_id,
                clean_session=True,
                protocol=mqtt.MQTTv311
            )
            
            # Set up callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_log = self._on_log
            
            # Configure authentication if provided
            username = self.config.get('mqtt_username')
            password = self.config.get('mqtt_password')
            if username:
                self.client.username_pw_set(username, password)
                
            # Configure TLS if enabled
            if self.config.get('mqtt_use_tls', False):
                ca_cert_path = self.config.get('mqtt_ca_cert_path')
                if ca_cert_path:
                    self.client.tls_set(ca_cert_path)
                else:
                    self.client.tls_set()
                    
            # Set keepalive and other options
            keepalive = self.config.get('mqtt_keepalive', 60)
            self.client.keepalive = keepalive
            
            # Set last will and testament (availability)
            self.client.will_set(
                self.availability_topic,
                payload="offline",
                qos=self.qos,
                retain=True
            )
            
            self.logger.info("MQTT client initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MQTT client: {e}")
            return False
            
    def connect(self) -> bool:
        """
        Connect to MQTT broker
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if not self.client:
            self.logger.error("MQTT client not initialized")
            return False

        if self.connected:
            self.logger.info("Already connected to MQTT broker")
            return True

        # Update connection state and tracking
        self.connection_state = MQTTConnectionState.CONNECTING
        self.connection_attempts += 1

        try:
            host = self.config.get('mqtt_broker_host', 'localhost')
            port = self.config.get('mqtt_broker_port', 1883)

            self.logger.info(f"Connecting to MQTT broker at {host}:{port} (attempt {self.connection_attempts})")

            # Connect to broker
            result = self.client.connect(host, port, keepalive=self.client.keepalive)
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                # Start the network loop
                self.client.loop_start()
                
                # Wait for connection with timeout
                timeout = 10  # seconds
                start_time = time.time()
                while not self.connected and (time.time() - start_time) < timeout:
                    time.sleep(0.1)
                    
                if self.connected:
                    self.connection_state = MQTTConnectionState.CONNECTED
                    self.error_recovery.reset()  # Reset retry counter on success
                    self.logger.info(f"Successfully connected to MQTT broker (total attempts: {self.connection_attempts})")
                    return True
                else:
                    self.connection_state = MQTTConnectionState.ERROR
                    timeout = self.config.get('mqtt_connect_timeout', 10)
                    self.logger.error(f"Connection timeout after {timeout} seconds")
                    return False
            else:
                self.connection_state = MQTTConnectionState.ERROR
                error_msg = mqtt.error_string(result) if hasattr(mqtt, 'error_string') else f"Error code: {result}"
                self.logger.error(f"Failed to connect to MQTT broker: {error_msg}")
                return False

        except Exception as e:
            self.connection_state = MQTTConnectionState.ERROR
            self.logger.error(f"Exception during MQTT connection: {e}", exc_info=True)
            return False
            
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client and self.connected:
            try:
                # Publish offline status
                self.publish(self.availability_topic, "offline", retain=True)
                
                # Disconnect and stop loop
                self.client.disconnect()
                self.client.loop_stop()
                
                self.logger.info("Disconnected from MQTT broker")
                
            except Exception as e:
                self.logger.error(f"Error during MQTT disconnection: {e}")
                
    def publish(self, topic: str, payload: Any, qos: Optional[int] = None, retain: Optional[bool] = None) -> bool:
        """
        Publish message to MQTT topic
        
        Args:
            topic: MQTT topic to publish to
            payload: Message payload (will be JSON encoded if dict/list)
            qos: Quality of Service level (uses default if None)
            retain: Retain flag (uses default if None)
            
        Returns:
            bool: True if publish successful, False otherwise
        """
        if not self.client or not self.connected:
            self.logger.warning(f"Cannot publish to {topic}: not connected (state: {self.connection_state.value})")
            return False
            
        try:
            # Use default values if not specified
            if qos is None:
                qos = self.qos
            if retain is None:
                retain = self.retain
                
            # Convert payload to string if needed
            if isinstance(payload, (dict, list)):
                payload = json.dumps(payload)
            elif payload is not None:
                payload = str(payload)
            else:
                payload = ""
                
            # Publish message
            result = self.client.publish(topic, payload, qos=qos, retain=retain)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.total_messages_sent += 1
                self.last_successful_publish = time.time()
                self.publish_failure_count = 0  # Reset failure count on success
                self.logger.debug(f"Published to {topic}: {payload[:100]}{'...' if len(str(payload)) > 100 else ''}")
                return True
            else:
                self.publish_failure_count += 1
                error_msg = mqtt.error_string(result.rc) if hasattr(mqtt, 'error_string') else f"Error code: {result.rc}"
                self.logger.error(f"Failed to publish to {topic}: {error_msg} (failure count: {self.publish_failure_count})")

                # Log additional context for debugging
                if self.publish_failure_count > 3:
                    self.logger.warning(f"High publish failure count ({self.publish_failure_count}). Connection state: {self.connection_state.value}")

                return False

        except Exception as e:
            self.publish_failure_count += 1
            self.logger.error(f"Exception during publish to {topic}: {e}", exc_info=True)
            return False
            
    def subscribe(self, topic: str, callback: Callable[[str, str], None], qos: Optional[int] = None) -> bool:
        """
        Subscribe to MQTT topic with callback
        
        Args:
            topic: MQTT topic to subscribe to
            callback: Function to call when message received (topic, payload)
            qos: Quality of Service level (uses default if None)
            
        Returns:
            bool: True if subscription successful, False otherwise
        """
        if not self.client or not self.connected:
            self.logger.warning(f"Cannot subscribe to {topic}: not connected")
            return False
            
        try:
            if qos is None:
                qos = self.qos
                
            # Store callback for this topic
            with self._lock:
                self.message_handlers[topic] = callback
                
            # Subscribe to topic
            result, _ = self.client.subscribe(topic, qos=qos)
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Subscribed to topic: {topic}")
                return True
            else:
                self.logger.error(f"Failed to subscribe to {topic}: {mqtt.error_string(result)}")
                return False
                
        except Exception as e:
            self.logger.error(f"Exception during subscribe to {topic}: {e}")
            return False
            
    def unsubscribe(self, topic: str) -> bool:
        """
        Unsubscribe from MQTT topic
        
        Args:
            topic: MQTT topic to unsubscribe from
            
        Returns:
            bool: True if unsubscription successful, False otherwise
        """
        if not self.client:
            return False
            
        try:
            # Remove callback handler
            with self._lock:
                self.message_handlers.pop(topic, None)
                
            # Unsubscribe from topic
            result, _ = self.client.unsubscribe(topic)
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Unsubscribed from topic: {topic}")
                return True
            else:
                self.logger.error(f"Failed to unsubscribe from {topic}: {mqtt.error_string(result)}")
                return False
                
        except Exception as e:
            self.logger.error(f"Exception during unsubscribe from {topic}: {e}")
            return False

    def add_connection_callback(self, callback: Callable[[], None]):
        """Add callback to be called when connected"""
        self.connection_callbacks.append(callback)

    def add_disconnection_callback(self, callback: Callable[[], None]):
        """Add callback to be called when disconnected"""
        self.disconnection_callbacks.append(callback)

    def publish_birth_message(self):
        """Publish birth message to indicate addon is online"""
        self.publish(self.availability_topic, "online", retain=True)

    def publish_discovery_config(self, component: str, node_id: str, object_id: str, config: Dict[str, Any]) -> bool:
        """
        Publish Home Assistant MQTT discovery configuration

        Args:
            component: HA component type (sensor, button, select, etc.)
            node_id: Unique node identifier
            object_id: Unique object identifier
            config: Discovery configuration payload

        Returns:
            bool: True if published successfully, False otherwise
        """
        topic = f"{self.discovery_prefix}/{component}/{node_id}/{object_id}/config"
        return self.publish(topic, config, retain=True)

    def remove_discovery_config(self, component: str, node_id: str, object_id: str) -> bool:
        """
        Remove Home Assistant MQTT discovery configuration

        Args:
            component: HA component type
            node_id: Unique node identifier
            object_id: Unique object identifier

        Returns:
            bool: True if removed successfully, False otherwise
        """
        topic = f"{self.discovery_prefix}/{component}/{node_id}/{object_id}/config"
        return self.publish(topic, "", retain=True)  # Empty payload removes entity

    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when client connects to broker"""
        if rc == 0:
            self.connected = True
            self.logger.info("Connected to MQTT broker")

            # Publish birth message
            self.publish_birth_message()

            # Call connection callbacks
            for callback in self.connection_callbacks:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(f"Error in connection callback: {e}")
        else:
            self.logger.error(f"Failed to connect to MQTT broker: {mqtt.connack_string(rc)}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback for when client disconnects from broker with enhanced recovery"""
        self.connected = False
        self.connection_state = MQTTConnectionState.DISCONNECTED

        if rc != 0:
            # Unexpected disconnection
            error_msg = mqtt.error_string(rc) if hasattr(mqtt, 'error_string') else f"Error code: {rc}"
            self.logger.warning(f"Unexpected MQTT disconnection: {error_msg}")

            # Check if we should attempt reconnection
            if self.error_recovery.should_retry():
                self.connection_state = MQTTConnectionState.RECONNECTING
                reconnect_delay = self.error_recovery.get_delay()
                self.error_recovery.record_attempt()

                self.logger.info(f"Attempting reconnection in {reconnect_delay:.1f} seconds (attempt {self.error_recovery.retry_count}/{self.error_recovery.max_retries})")

                def reconnect():
                    time.sleep(reconnect_delay)
                    if not self.connected and self.error_recovery.should_retry():
                        success = self.connect()
                        if not success:
                            self.logger.error(f"Reconnection attempt {self.error_recovery.retry_count} failed")

                threading.Thread(target=reconnect, daemon=True).start()
            else:
                self.connection_state = MQTTConnectionState.ERROR
                self.logger.error(f"Maximum reconnection attempts ({self.error_recovery.max_retries}) exceeded. Manual intervention required.")
        else:
            # Clean disconnection
            self.logger.info("Cleanly disconnected from MQTT broker")

        # Call disconnection callbacks
        for callback in self.disconnection_callbacks:
            try:
                callback()
            except Exception as e:
                self.logger.error(f"Error in disconnection callback: {e}", exc_info=True)

    def _on_message(self, client, userdata, msg):
        """Callback for when message is received with enhanced tracking"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')

            # Track received messages
            self.total_messages_received += 1

            self.logger.debug(f"Received message on {topic}: {payload[:100]}{'...' if len(payload) > 100 else ''}")

            # Find matching handler
            with self._lock:
                handler = self.message_handlers.get(topic)

            if handler:
                try:
                    handler(topic, payload)
                except Exception as e:
                    self.logger.error(f"Error in message handler for {topic}: {e}", exc_info=True)
            else:
                self.logger.debug(f"No handler registered for topic: {topic}")

        except Exception as e:
            self.logger.error(f"Error processing received message: {e}", exc_info=True)

    def _on_log(self, client, userdata, level, buf):
        """Callback for MQTT client logging"""
        # Map MQTT log levels to Python logging levels
        if level == mqtt.MQTT_LOG_DEBUG:
            self.logger.debug(f"MQTT: {buf}")
        elif level == mqtt.MQTT_LOG_INFO:
            self.logger.info(f"MQTT: {buf}")
        elif level == mqtt.MQTT_LOG_NOTICE:
            self.logger.info(f"MQTT: {buf}")
        elif level == mqtt.MQTT_LOG_WARNING:
            self.logger.warning(f"MQTT: {buf}")
        elif level == mqtt.MQTT_LOG_ERR:
            self.logger.error(f"MQTT: {buf}")

    @property
    def is_connected(self) -> bool:
        """Check if client is connected to broker"""
        return self.connected

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive connection statistics and health information

        Returns:
            Dict containing connection statistics
        """
        current_time = time.time()
        return {
            'connection_state': self.connection_state.value,
            'connected': self.connected,
            'connection_attempts': self.connection_attempts,
            'retry_count': self.error_recovery.retry_count,
            'max_retries': self.error_recovery.max_retries,
            'total_messages_sent': self.total_messages_sent,
            'total_messages_received': self.total_messages_received,
            'publish_failure_count': self.publish_failure_count,
            'last_successful_publish': self.last_successful_publish,
            'time_since_last_publish': current_time - self.last_successful_publish if self.last_successful_publish > 0 else None,
            'last_error_time': self.error_recovery.last_error_time,
            'time_since_last_error': current_time - self.error_recovery.last_error_time if self.error_recovery.last_error_time > 0 else None,
            'broker_host': self.config.get('mqtt_broker_host', 'localhost'),
            'broker_port': self.config.get('mqtt_broker_port', 1883),
            'client_id': self.client_id,
            'qos': self.qos,
            'keepalive': self.config.get('mqtt_keepalive', 60)
        }

    def log_connection_health(self):
        """Log current connection health and statistics"""
        stats = self.get_connection_stats()

        health_status = "HEALTHY" if self.connected and self.publish_failure_count < 3 else "DEGRADED" if self.connected else "UNHEALTHY"

        self.logger.info(f"MQTT Health Check - Status: {health_status}")
        self.logger.info(f"  Connection: {stats['connection_state']} | Attempts: {stats['connection_attempts']}")
        self.logger.info(f"  Messages: Sent={stats['total_messages_sent']}, Received={stats['total_messages_received']}")
        self.logger.info(f"  Failures: Publish={stats['publish_failure_count']}, Retries={stats['retry_count']}/{stats['max_retries']}")

        if stats['time_since_last_publish'] is not None:
            self.logger.info(f"  Last publish: {stats['time_since_last_publish']:.1f}s ago")

        if stats['time_since_last_error'] is not None and stats['time_since_last_error'] < 300:  # 5 minutes
            self.logger.warning(f"  Recent error: {stats['time_since_last_error']:.1f}s ago")

    def get_discovery_topic(self, component: str, node_id: str, object_id: str) -> str:
        """Get discovery topic for given component and identifiers"""
        return f"{self.discovery_prefix}/{component}/{node_id}/{object_id}/config"

    def get_state_topic(self, component: str, node_id: str, object_id: str) -> str:
        """Get state topic for given component and identifiers"""
        return f"{self.discovery_prefix}/{component}/{node_id}/{object_id}/state"

    def get_command_topic(self, component: str, node_id: str, object_id: str) -> str:
        """Get command topic for given component and identifiers"""
        return f"{self.discovery_prefix}/{component}/{node_id}/{object_id}/command"
