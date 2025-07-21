import asyncio
import logging
from asyncio import Queue
from typing import Optional, Any

try:
    import aio_mqtt
except ImportError:
    # Fallback for development/testing without aio_mqtt
    aio_mqtt = None

from .config import MQTTConfig

logger = logging.getLogger(__name__)

class MQTTClient:
    """Asynchronous MQTT client for discovery and state updates."""

    def __init__(self, config: MQTTConfig, message_queue: Queue):
        self.config = config
        self.message_queue = message_queue
        self.client: Optional[aio_mqtt.Client] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Connects to the MQTT broker and starts listening for messages."""
        if aio_mqtt is None:
            logger.error("aio_mqtt library not available. Install with: pip install aio-mqtt")
            raise ImportError("aio_mqtt library not available")
            
        logger.info("Starting MQTT client...")
        self.client = aio_mqtt.Client()
        try:
            # Prepare connection parameters
            connect_params = {
                'host': self.config.BROKER_ADDRESS,
                'port': self.config.BROKER_PORT,
                'username': self.config.USERNAME,
                'password': self.config.PASSWORD,
            }
            
            # Add TLS/SSL support if enabled
            if hasattr(self.config, 'USE_TLS') and self.config.USE_TLS:
                ssl_context = None
                if hasattr(self.config, 'TLS_CA_CERT') and self.config.TLS_CA_CERT:
                    import ssl
                    ssl_context = ssl.create_default_context()
                    ssl_context.load_verify_locations(self.config.TLS_CA_CERT)
                    
                    # Client certificate authentication if provided
                    if (hasattr(self.config, 'TLS_CERT_FILE') and self.config.TLS_CERT_FILE and
                        hasattr(self.config, 'TLS_KEY_FILE') and self.config.TLS_KEY_FILE):
                        ssl_context.load_cert_chain(self.config.TLS_CERT_FILE, self.config.TLS_KEY_FILE)
                    
                    # Handle insecure TLS (skip certificate verification)
                    if hasattr(self.config, 'TLS_INSECURE') and self.config.TLS_INSECURE:
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        logger.warning("TLS certificate verification disabled - not recommended for production")
                
                connect_params['ssl'] = ssl_context
                logger.info("TLS/SSL encryption enabled for MQTT connection")
            
            # Connect to broker with proper parameters
            await self.client.connect(**connect_params)
            self._task = asyncio.create_task(self._message_listener())
            logger.info("MQTT client connected and listener started.")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise

    async def stop(self):
        """Stops the MQTT client and disconnects gracefully."""
        if self._task:
            self._task.cancel()
        if self.client:
            await self.client.disconnect()
        logger.info("MQTT client stopped.")

    async def subscribe(self, topic: str, qos: int = 0):
        """Subscribes to an MQTT topic."""
        if self.client:
            await self.client.subscribe(topic, qos=qos)
            logger.info(f"Subscribed to topic: {topic}")

    async def _message_listener(self):
        """Listens for messages and puts them into the queue."""
        async with self.client.messages() as messages:
            async for message in messages:
                try:
                    decoded_payload = message.payload.decode()
                    await self.message_queue.put((message.topic, decoded_payload))
                except Exception as e:
                    logger.warning(f"Failed to process message from topic {message.topic}: {e}")