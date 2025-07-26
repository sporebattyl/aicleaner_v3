"""
AICleaner v3 MQTT Service
Manages MQTT connection, publishing, and Home Assistant MQTT Discovery.
"""

import asyncio
import logging
import json
import secrets
from typing import Dict, Any, Optional, Callable, List
from paho.mqtt import client as mqtt_client
from paho.mqtt.enums import MQTTErrorCode

logger = logging.getLogger(__name__)

class MQTTService:
    """
    Manages MQTT connection, publishing, and Home Assistant MQTT Discovery.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.broker_host = config.get('broker', {}).get('host', 'localhost')
        self.broker_port = config.get('broker', {}).get('port', 1883)
        self.username = config.get('broker', {}).get('username')
        self.password = config.get('broker', {}).get('password')
        self.client_id = config.get('broker', {}).get('client_id', f"aicleaner_v3_{secrets.token_hex(4)}")
        self.auto_discovery_enabled = config.get('auto_discovery', {}).get('enabled', True)
        self.discovery_prefix = config.get('auto_discovery', {}).get('topic_prefix', 'homeassistant')
        self.node_id = config.get('auto_discovery', {}).get('node_id', 'aicleaner_v3')

        self._client: Optional[mqtt_client.Client] = None
        self._is_connected = False
        self._message_queue = asyncio.Queue()
        self._publisher_task: Optional[asyncio.Task] = None
        self._discovered_devices: Dict[str, Any] = {}

        logger.info(f"MQTTService initialized for broker: {self.broker_host}:{self.broker_port}")

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info("Connected to MQTT Broker!")
            self._is_connected = True
            # Stop any existing publisher task and start a new one
            self._stop_and_start_publisher_task()
        else:
            logger.error(f"Failed to connect to MQTT, return code {rc}: {MQTTErrorCode(rc).getName()}")
            self._is_connected = False

    def _stop_and_start_publisher_task(self):
        """Safely stops existing task and starts a new publisher task (non-async)."""
        # Cancel existing task if running
        if self._publisher_task and not self._publisher_task.done():
            logger.debug("Cancelling existing MQTT publisher task...")
            self._publisher_task.cancel()
        
        # Start new publisher task
        self._publisher_task = asyncio.create_task(self._message_publisher())
        logger.debug("Started new MQTT publisher task")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        logger.warning(f"Disconnected from MQTT Broker with code: {rc}")
        self._is_connected = False
        if self._publisher_task and not self._publisher_task.done():
            self._publisher_task.cancel()

    def _on_message(self, client, userdata, msg):
        logger.debug(f"Received `{msg.payload.decode()}` from `{msg.topic}`")
        # Implement message handling if needed (e.g., for command topics)

    async def connect(self):
        """Connects to the MQTT broker."""
        if self._client and self._is_connected:
            logger.info("Already connected to MQTT broker.")
            return

        try:
            self._client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2, self.client_id)
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message

            if self.username and self.password:
                self._client.username_pw_set(self.username, self.password)

            # Use loop_start() for non-blocking network loop
            self._client.connect(self.broker_host, self.broker_port, 60)
            self._client.loop_start()

            # Wait for connection to establish
            for _ in range(10):  # Try for up to 10 seconds
                if self._is_connected:
                    logger.info("MQTT connection established.")
                    return
                await asyncio.sleep(1)
            logger.warning("MQTT connection timed out.")

        except ConnectionRefusedError as e:
            logger.error(f"MQTT broker connection refused: Broker actively refused connection. Is it running? {e}")
            self._is_connected = False
        except TimeoutError as e:
            logger.error(f"MQTT connection timeout: Could not connect within timeout period. {e}")
            self._is_connected = False  
        except OSError as e:
            logger.error(f"MQTT network error: Could not reach broker. Check network connectivity. {e}")
            self._is_connected = False
        except ValueError as e:
            logger.error(f"MQTT configuration error: Invalid broker settings. {e}")
            self._is_connected = False
        except Exception as e:
            logger.error(f"Unexpected MQTT connection error: {e}", exc_info=True)
            self._is_connected = False

    async def _stop_publisher_task(self):
        """Safely stops the publisher task if it's running."""
        if self._publisher_task and not self._publisher_task.done():
            logger.debug("Stopping existing MQTT publisher task...")
            self._publisher_task.cancel()
            try:
                await self._publisher_task
            except asyncio.CancelledError:
                logger.debug("MQTT publisher task cancelled successfully")
            except Exception as e:
                logger.error(f"Error stopping MQTT publisher task: {e}")
            finally:
                self._publisher_task = None

    async def disconnect(self):
        """Disconnects from the MQTT broker."""
        if self._client:
            await self._stop_publisher_task()
            self._client.loop_stop()
            self._client.disconnect()
            self._is_connected = False
            logger.info("Disconnected from MQTT Broker.")

    def is_connected(self) -> bool:
        """Returns true if connected to MQTT broker."""
        return self._is_connected

    async def publish(self, topic: str, payload: Any, qos: int = 0, retain: bool = False):
        """
        Publishes a message to an MQTT topic.
        Messages are queued and published by a background task.
        """
        if not self._is_connected:
            logger.warning(f"Not connected to MQTT, cannot publish to {topic}. Message queued.")
        await self._message_queue.put((topic, payload, qos, retain))

    async def _message_publisher(self):
        """Background task to publish messages from the queue."""
        while True:
            try:
                topic, payload, qos, retain = await self._message_queue.get()
                if self._is_connected and self._client:
                    result, mid = self._client.publish(topic, payload, qos, retain)
                    if result == mqtt_client.MQTT_ERR_SUCCESS:
                        logger.debug(f"Published message to {topic} (mid={mid})")
                    else:
                        logger.error(f"Failed to publish message to {topic}: {MQTTErrorCode(result).getName()}")
                else:
                    logger.warning(f"MQTT not connected, re-queueing message for {topic}")
                    await self._message_queue.put((topic, payload, qos, retain))  # Re-queue if not connected
                self._message_queue.task_done()
            except asyncio.CancelledError:
                logger.info("MQTT publisher task cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in MQTT publisher task: {e}")
                await asyncio.sleep(5)  # Prevent tight loop on error

    async def publish_ha_discovery_sensor(self,
                                          component: str,
                                          object_id: str,
                                          name: str,
                                          state_topic: str,
                                          unit_of_measurement: Optional[str] = None,
                                          device_class: Optional[str] = None,
                                          value_template: Optional[str] = None,
                                          icon: Optional[str] = None,
                                          entity_category: Optional[str] = None,
                                          unique_id: Optional[str] = None,
                                          device_info: Optional[Dict[str, Any]] = None):
        """
        Publishes Home Assistant MQTT Discovery message for a sensor.
        https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
        """
        if not self.auto_discovery_enabled:
            logger.debug("MQTT Discovery is disabled. Skipping discovery message.")
            return

        if not unique_id:
            unique_id = f"{self.node_id}_{object_id}"

        config_topic = f"{self.discovery_prefix}/{component}/{self.node_id}/{object_id}/config"

        payload = {
            "name": name,
            "state_topic": state_topic,
            "unique_id": unique_id,
            "qos": 0,
            "retain": False,
        }
        if unit_of_measurement:
            payload["unit_of_measurement"] = unit_of_measurement
        if device_class:
            payload["device_class"] = device_class
        if value_template:
            payload["value_template"] = value_template
        if icon:
            payload["icon"] = icon
        if entity_category:
            payload["entity_category"] = entity_category

        # Device information for grouping entities in HA
        if not device_info:
            device_info = {
                "identifiers": [self.node_id],
                "name": "AICleaner v3",
                "manufacturer": "AICleaner",
                "model": "Core Service",
                "sw_version": "1.0.0",
            }
        payload["device"] = device_info

        try:
            await self.publish(config_topic, json.dumps(payload), retain=True)
            logger.info(f"Published HA MQTT Discovery for sensor: {name} on topic: {config_topic}")
            self._discovered_devices[unique_id] = payload  # Store for internal tracking
        except Exception as e:
            logger.error(f"Failed to publish HA MQTT Discovery for {name}: {e}")

    def get_discovered_devices(self) -> List[Dict[str, Any]]:
        """Returns a list of currently discovered devices/sensors."""
        return list(self._discovered_devices.values())