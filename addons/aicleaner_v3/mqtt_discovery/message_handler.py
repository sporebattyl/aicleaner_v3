import asyncio
import json
import logging
from asyncio import Queue

from .config import MQTTConfig
from .entity_registrar import EntityRegistrar
from .state_manager import StateManager

logger = logging.getLogger(__name__)

class MessageHandler:
    """Processes incoming MQTT messages from the queue."""

    def __init__(self, config: MQTTConfig, queue: Queue, registrar: EntityRegistrar, state_manager: StateManager):
        self.config = config
        self.queue = queue
        self.registrar = registrar
        self.state_manager = state_manager
        self._task: asyncio.Task | None = None

    def start(self):
        """Starts the message processing loop."""
        self._task = asyncio.create_task(self._process_queue())
        logger.info("MQTT message handler started.")

    def stop(self):
        """Stops the message processing loop."""
        if self._task:
            self._task.cancel()
        logger.info("MQTT message handler stopped.")

    async def _process_queue(self):
        """Continuously processes messages from the queue."""
        discovery_prefix = f"{self.config.DISCOVERY_PREFIX}/"
        while True:
            try:
                topic, payload = await self.queue.get()
                try:
                    if topic.startswith(discovery_prefix):
                        await self._handle_discovery_message(topic, payload)
                    else:
                        await self.state_manager.update_entity_state(topic, payload)
                except Exception as e:
                    logger.error(f"Error processing message from topic '{topic}': {e}")
                finally:
                    self.queue.task_done()
            except asyncio.CancelledError:
                logger.info("Message handler processing cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in message handler: {e}")

    async def _handle_discovery_message(self, topic: str, payload: str):
        """Handles a Home Assistant MQTT discovery message."""
        logger.debug(f"Handling discovery message on topic: {topic}")
        try:
            # Handle empty payload as entity removal
            if not payload.strip():
                logger.info(f"Received empty payload for topic {topic}, treating as entity removal")
                return
                
            config_payload = json.loads(payload)
            topic_parts = topic.split('/')
            # Format: <discovery_prefix>/<component>/<node_id>/<object_id>/config
            if len(topic_parts) >= 4 and topic_parts[-1] == 'config':
                component = topic_parts[1]
                object_id = topic_parts[-2]
                await self.registrar.register_entity(component, object_id, config_payload)
            else:
                logger.warning(f"Discovery topic format not recognized: {topic}")
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in discovery payload on topic: {topic}")
        except Exception as e:
            logger.error(f"Failed to handle discovery message on topic {topic}: {e}")

    async def get_queue_stats(self) -> dict:
        """Returns statistics about the message queue."""
        return {
            "queue_size": self.queue.qsize(),
            "queue_empty": self.queue.empty(),
            "queue_full": self.queue.full()
        }