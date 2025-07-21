import asyncio
import logging
from asyncio import Queue
from typing import Any

from .client import MQTTClient
from .config import MQTTConfig
from .entity_registrar import EntityRegistrar
from .message_handler import MessageHandler
from .state_manager import StateManager

logger = logging.getLogger(__name__)

class MQTTDiscoveryManager:
    """Orchestrates the entire MQTT discovery process."""

    def __init__(self, entity_manager: Any, performance_monitor: Any = None, config_manager=None):
        """
        Initializes the MQTTDiscoveryManager.

        Args:
            entity_manager: The Phase 4A EntityManager instance.
            performance_monitor: The Phase 4A PerformanceMonitor instance.
            config_manager: Unified configuration manager instance.
        """
        self.config = MQTTConfig(config_manager=config_manager)
        self.config.log_config()
        
        self.message_queue = Queue()
        self.client = MQTTClient(self.config, self.message_queue)
        self.state_manager = StateManager(entity_manager, self.client)
        self.entity_registrar = EntityRegistrar(entity_manager, self.state_manager)
        self.message_handler = MessageHandler(self.config, self.message_queue, self.entity_registrar, self.state_manager)
        self.performance_monitor = performance_monitor
        
        # Track startup state
        self._is_running = False
        self._startup_time = None

    async def start(self):
        """Starts all MQTT discovery components."""
        if self._is_running:
            logger.warning("MQTT Discovery Manager is already running")
            return
            
        logger.info("Starting MQTT Discovery Manager...")
        start_time = asyncio.get_event_loop().time()
        
        try:
            await self.client.start()
            discovery_topic = f"{self.config.DISCOVERY_PREFIX}/#"
            await self.client.subscribe(discovery_topic, qos=self.config.QOS)
            self.message_handler.start()
            
            # Integrate with performance monitor if available
            if self.performance_monitor:
                # Register MQTT metrics
                if hasattr(self.performance_monitor, 'fire_performance_event'):
                    startup_duration = asyncio.get_event_loop().time() - start_time
                    self.performance_monitor.fire_performance_event('mqtt_startup', startup_duration)
            
            self._is_running = True
            self._startup_time = asyncio.get_event_loop().time()
            logger.info("MQTT Discovery Manager started successfully.")
            
        except Exception as e:
            logger.error(f"Failed to start MQTT Discovery Manager: {e}")
            await self.stop()  # Clean up on failure
            raise

    async def stop(self):
        """Stops all MQTT discovery components gracefully."""
        if not self._is_running:
            logger.warning("MQTT Discovery Manager is not running")
            return
            
        logger.info("Stopping MQTT Discovery Manager...")
        
        try:
            self.message_handler.stop()
            await self.client.stop()
            
            # Integrate with performance monitor if available
            if self.performance_monitor and self._startup_time:
                runtime_duration = asyncio.get_event_loop().time() - self._startup_time
                if hasattr(self.performance_monitor, 'fire_performance_event'):
                    self.performance_monitor.fire_performance_event('mqtt_runtime', runtime_duration)
                    
            self._is_running = False
            logger.info("MQTT Discovery Manager stopped.")
            
        except Exception as e:
            logger.error(f"Error during MQTT Discovery Manager shutdown: {e}")
            raise

    async def get_status(self) -> dict:
        """Returns the current status of the MQTT discovery system."""
        queue_stats = await self.message_handler.get_queue_stats()
        registered_devices = await self.entity_registrar.get_registered_devices()
        
        return {
            "running": self._is_running,
            "startup_time": self._startup_time,
            "broker_address": self.config.BROKER_ADDRESS,
            "broker_port": self.config.BROKER_PORT,
            "discovery_prefix": self.config.DISCOVERY_PREFIX,
            "queue_stats": queue_stats,
            "registered_devices_count": len(registered_devices),
            "total_entities": sum(len(device.entities) for device in registered_devices.values())
        }

    async def restart(self):
        """Restarts the MQTT discovery system."""
        logger.info("Restarting MQTT Discovery Manager...")
        await self.stop()
        await asyncio.sleep(1)  # Brief pause before restart
        await self.start()
        logger.info("MQTT Discovery Manager restarted successfully.")

    def is_running(self) -> bool:
        """Returns True if the MQTT discovery system is running."""
        return self._is_running