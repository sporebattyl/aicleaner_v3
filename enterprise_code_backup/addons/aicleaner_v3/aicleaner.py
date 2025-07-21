"""
AI Cleaner addon for Home Assistant.
Analyzes camera images to identify cleaning tasks.
"""
import os
import json
import logging
import asyncio
import signal
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Import core components
from core.analyzer import ZoneAnalyzer
from core.analysis_queue import AnalysisPriority
from core.state_manager import AnalysisState
from core.scheduler import ZoneScheduler
from core.state_manager import StateManager
from core.performance_monitor import PerformanceMonitor

# Import integration components
from integrations.ha_client import HAClient
from integrations.mqtt_manager import MQTTManager
from integrations.gemini_client import GeminiClient
from ai.multi_model_ai import MultiModelAIOptimizer

# Import health monitoring components
from core.system_monitor import SystemMonitor
from core.health_entities import HealthEntityManager
from core.health_service_handler import HealthServiceHandler
from utils.service_registry import ServiceRegistry

class AICleaner:
    """
    AI Cleaner main application.
    
    Features:
    - Asynchronous processing
    - Component-based design
    - State persistence
    - Performance monitoring
    """
    
    def __init__(self):
        """Initialize the AI Cleaner application."""
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("aicleaner")
        
        # Configuration
        self.config = {}
        
        # Components
        self.ha_client = None

        self.state_manager = None
        self.performance_monitor = None
        self.mqtt_manager = None
        self.analyzer = None
        self.scheduler = None

        # Health monitoring components
        self.system_monitor = None
        self.health_entities = None
        self.health_service_handler = None
        self.service_registry = None
        
        # Running flag
        self.running = False
        
        # Shutdown event
        self.shutdown_event = asyncio.Event()
        
    async def start(self):
        """Start the AI Cleaner application."""
        self.logger.info("Starting AI Cleaner v3")
        self.running = True
        
        try:
            # Load configuration
            self._load_config()
            
            # Initialize components
            await self._initialize_components()
            
            # Register signal handlers
            self._register_signal_handlers()
            
            # Wait for shutdown
            await self.shutdown_event.wait()
            
        except Exception as e:
            self.logger.error(f"Error starting AI Cleaner: {e}")
            
        finally:
            # Shutdown components
            await self._shutdown()
            
        self.logger.info("AI Cleaner stopped")
        
    async def stop(self):
        """Stop the AI Cleaner application."""
        self.logger.info("Stopping AI Cleaner v3")
        self.running = False
        self.shutdown_event.set()
        
    def _load_config(self):
        """Load configuration."""
        try:
            # Get configuration from Home Assistant options
            options_path = "/data/options.json"
            if os.path.exists(options_path):
                with open(options_path, "r") as f:
                    self.config = json.load(f)
                    
                self.logger.info(f"Loaded configuration from {options_path}")
            else:
                self.logger.warning(f"Configuration file {options_path} not found, using defaults")
                self.config = {
                    "gemini_api_key": "",
                    "ha_api_url": "http://homeassistant.local:8123", # Default HA URL
                    "ha_access_token": "", # User must provide this
                    "display_name": "AI Cleaner",
                    "enable_mqtt": False,
                    "zones": []
                }
                
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            self.config = {
                "gemini_api_key": "",
                "ha_api_url": "http://homeassistant.local:8123", # Default HA URL
                "ha_access_token": "", # User must provide this
                "display_name": "AI Cleaner",
                "enable_mqtt": False,
                "zones": []
            }
            
    async def _initialize_components(self):
        """Initialize components."""
        try:
            # Initialize Home Assistant client
            ha_api_url = self.config.get("ha_api_url")
            ha_access_token = self.config.get("ha_access_token")
            if not ha_api_url or not ha_access_token:
                self.logger.error("Home Assistant API URL or access token not configured")
                raise ValueError("Home Assistant API URL or access token not configured")
            self.ha_client = HAClient(ha_api_url, ha_access_token)
            await self.ha_client.connect()
            
            # Initialize state manager
            self.state_manager = StateManager(self.config)
            await self.state_manager.initialize()
            
            # Link state manager to HA client
            self.ha_client.set_state_manager(self.state_manager)
            
            # Initialize performance monitor
            self.performance_monitor = PerformanceMonitor(self.ha_client, self.state_manager, self.config)
            await self.performance_monitor.initialize()
            
            # Initialize MultiModelAIOptimizer
            self.multi_model_ai_optimizer = MultiModelAIOptimizer(self.config.get("ai_model_config", {}))

            # Initialize MQTT manager if enabled
            if self.config.get("enable_mqtt", False):
                mqtt_config = {
                    "broker_host": self.config.get("mqtt_broker_host", "core-mosquitto"),
                    "broker_port": self.config.get("mqtt_broker_port", 1883),
                    "username": self.config.get("mqtt_username", ""),
                    "password": self.config.get("mqtt_password", ""),
                    "discovery_prefix": "homeassistant"
                }

                self.mqtt_manager = MQTTManager(mqtt_config)
                await self.mqtt_manager.connect()

                # Register MQTT command handlers
                self.mqtt_manager.register_command_handler(
                    "analyze_now",
                    self._handle_analyze_now_command
                )

                # Link performance monitor to MQTT manager
                self.performance_monitor.set_mqtt_manager(self.mqtt_manager)

            # Initialize zone analyzer
            self.analyzer = ZoneAnalyzer(
                self.ha_client,
                self.state_manager,
                self.config,
                self.multi_model_ai_optimizer
            )
            await self.analyzer.start()
            
            # Initialize zone scheduler
            self.scheduler = ZoneScheduler(self.analyzer, self.config)
            await self.scheduler.start()

            # Initialize health monitoring components
            await self._initialize_health_monitoring()

            self.logger.info("All components initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
            raise

    async def _initialize_health_monitoring(self):
        """Initialize health monitoring components."""
        try:
            self.logger.info("Initializing health monitoring components")

            # Initialize system monitor
            self.system_monitor = SystemMonitor(self.config, "/data/system_monitor")
            await self.system_monitor.start_monitoring()

            # Initialize health entities
            self.health_entities = HealthEntityManager(self.ha_client, self.config)
            await self.health_entities.initialize_entities()

            # Initialize health service handler
            self.health_service_handler = HealthServiceHandler(
                self.system_monitor,
                self.health_entities,
                self.ha_client,
                self.config
            )

            # Initialize service registry
            self.service_registry = ServiceRegistry(self.ha_client, "/app")

            # Register health service handlers
            self.service_registry.register_service_handler(
                'run_health_check',
                self.handle_service_run_health_check
            )
            self.service_registry.register_service_handler(
                'apply_performance_profile',
                self.handle_service_apply_performance_profile
            )

            # Register services with Home Assistant
            self.service_registry.register_services_with_ha()

            self.logger.info("Health monitoring components initialized successfully")

        except Exception as e:
            self.logger.error(f"Error initializing health monitoring: {e}")
            raise
            
    async def _shutdown(self):
        """Shutdown components."""
        self.logger.info("Shutting down components")
        
        # Shutdown scheduler
        if self.scheduler:
            try:
                await self.scheduler.stop()
            except Exception as e:
                self.logger.error(f"Error stopping scheduler: {e}")
                
        # Shutdown analyzer
        if self.analyzer:
            try:
                await self.analyzer.stop()
            except Exception as e:
                self.logger.error(f"Error stopping analyzer: {e}")
                
        # Shutdown MQTT manager
        if self.mqtt_manager:
            try:
                await self.mqtt_manager.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting MQTT manager: {e}")
                
        # Shutdown performance monitor
        if self.performance_monitor:
            try:
                await self.performance_monitor.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down performance monitor: {e}")
                
        # Shutdown state manager
        if self.state_manager:
            try:
                await self.state_manager.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down state manager: {e}")

        # Shutdown health monitoring components
        if self.system_monitor:
            try:
                await self.system_monitor.stop_monitoring()
            except Exception as e:
                self.logger.error(f"Error stopping system monitor: {e}")

        # Shutdown Home Assistant client
        if self.ha_client:
            try:
                await self.ha_client.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting Home Assistant client: {e}")
                
        self.logger.info("All components shut down")
        
    def _register_signal_handlers(self):
        """Register signal handlers."""
        loop = asyncio.get_running_loop()
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self._handle_signal()))
            
    async def _handle_signal(self):
        """Handle signal."""
        self.logger.info("Received shutdown signal")
        await self.stop()
        
    async def _handle_analyze_now_command(self, payload: str):
        """
        Handle analyze now command.
        
        Args:
            payload: Command payload
        """
        try:
            # Parse payload
            data = json.loads(payload) if payload else {}
            zone_name = data.get("zone")
            
            if zone_name:
                # Trigger analysis for specific zone
                await self.scheduler.trigger_analysis(zone_name)
                self.logger.info(f"Triggered analysis for zone {zone_name}")
            else:
                # Trigger analysis for all zones
                for zone in self.config.get("zones", []):
                    zone_name = zone.get("name")
                    if zone_name:
                        await self.scheduler.trigger_analysis(zone_name)
                    
                self.logger.info("Triggered analysis for all zones")
                
        except Exception as e:
            self.logger.error(f"Error handling analyze now command: {e}")

    async def handle_service_run_health_check(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the run_health_check service call.

        Args:
            service_data: Service call data from Home Assistant

        Returns:
            Dict with service call result
        """
        self.logger.info("Health check service called via Home Assistant")

        if not self.health_service_handler:
            error_msg = "Health service handler not initialized"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}

        try:
            result = await self.health_service_handler.handle_run_health_check(service_data)
            self.logger.info(f"Health check service completed: {result.get('success', False)}")
            return result
        except Exception as e:
            error_msg = f"Health check service failed: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def handle_service_apply_performance_profile(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the apply_performance_profile service call.

        Args:
            service_data: Service call data from Home Assistant

        Returns:
            Dict with service call result
        """
        self.logger.info("Apply performance profile service called via Home Assistant")

        if not self.health_service_handler:
            error_msg = "Health service handler not initialized"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}

        try:
            result = await self.health_service_handler.handle_apply_performance_profile(service_data)
            self.logger.info(f"Apply performance profile service completed: {result.get('success', False)}")
            return result
        except Exception as e:
            error_msg = f"Apply performance profile service failed: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}


async def main():
    """Main entry point."""
    app = AICleaner()
    await app.start()


if __name__ == "__main__":
    asyncio.run(main())