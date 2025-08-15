"""
AI Cleaner - Main Application Entry Point

A production-ready application that coordinates all components for intelligent
image cleanup using AI providers with comprehensive health monitoring,
Home Assistant integration, and robust error handling.
"""

import asyncio
import logging
import signal
import sys
import time
import traceback
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, AsyncGenerator
from dataclasses import dataclass, field
import argparse
import os
from contextlib import asynccontextmanager

# Third-party imports
try:
    from aiohttp import web, ClientSession
    from aiohttp.web_request import Request
    from aiohttp.web_response import Response, json_response
except ImportError:
    print("Error: aiohttp not installed. Run: pip install aiohttp")
    sys.exit(1)

try:
    import paho.mqtt.client as mqtt
    from paho.mqtt.enums import CallbackAPIVersion
except ImportError:
    print("Warning: paho-mqtt not installed. MQTT integration will be disabled.")
    mqtt = None

from .config.loader import ConfigurationLoader
from .config.schema import AICleanerConfig
from .core.orchestrator import AICleanerOrchestrator
from .core.health import HealthMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('aicleaner.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class AppStats:
    """Application runtime statistics."""
    start_time: float = field(default_factory=time.time)
    total_sessions: int = 0
    total_images_processed: int = 0
    total_images_deleted: int = 0
    uptime: float = 0.0
    
    def update_uptime(self) -> None:
        self.uptime = time.time() - self.start_time


class DirectoryWatcher:
    """Watch directories for new images to process automatically."""
    
    def __init__(self, app: 'AICleanerApp'):
        self.app = app
        self.watched_directories: List[Path] = []
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
    def add_directory(self, directory: Path) -> bool:
        """Add a directory to watch for new images."""
        if directory.exists() and directory.is_dir():
            self.watched_directories.append(directory)
            logger.info(f"Added directory to watch: {directory}")
            return True
        logger.warning(f"Cannot watch non-existent directory: {directory}")
        return False
        
    async def start_watching(self) -> None:
        """Start monitoring watched directories."""
        if self._monitoring_task:
            return
            
        self._shutdown_event.clear()
        self._monitoring_task = asyncio.create_task(self._watch_loop())
        logger.info("Directory watching started")
        
    async def stop_watching(self) -> None:
        """Stop monitoring directories."""
        self._shutdown_event.set()
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        logger.info("Directory watching stopped")
        
    async def _watch_loop(self) -> None:
        """Main directory watching loop."""
        last_scan_times = {}
        
        while not self._shutdown_event.is_set():
            try:
                for directory in self.watched_directories:
                    last_scan = last_scan_times.get(str(directory), 0)
                    
                    # Find new images since last scan
                    new_images = []
                    for pattern in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.webp']:
                        for image_path in directory.glob(pattern):
                            if image_path.stat().st_mtime > last_scan:
                                new_images.append(image_path)
                                
                    if new_images:
                        logger.info(f"Found {len(new_images)} new images in {directory}")
                        await self.app.process_directory_async(directory, new_images)
                        
                    last_scan_times[str(directory)] = time.time()
                    
                # Wait before next scan
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                logger.info("Directory watcher cancelled")
                break
            except Exception as e:
                logger.error(f"Error in directory watcher: {e}")
                await asyncio.sleep(30)


class MQTTClient:
    """MQTT client for Home Assistant integration."""
    
    def __init__(self, config: AICleanerConfig, app: 'AICleanerApp'):
        self.config = config.home_assistant
        self.app = app
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        
    async def connect(self) -> bool:
        """Connect to MQTT broker."""
        if not mqtt or not self.config.enabled:
            logger.info("MQTT disabled or unavailable")
            return False
            
        try:
            # Create MQTT client
            self.client = mqtt.Client(
                callback_api_version=CallbackAPIVersion.VERSION2,
                client_id=f"aicleaner_{int(time.time())}"
            )
            
            # Set credentials if provided
            if self.config.mqtt_username and self.config.mqtt_password:
                self.client.username_pw_set(
                    self.config.mqtt_username, 
                    self.config.mqtt_password
                )
                
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            # Connect to broker
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.connect(
                    self.config.mqtt_host,
                    self.config.mqtt_port,
                    60
                )
            )
            
            # Start network loop
            self.client.loop_start()
            
            # Wait for connection confirmation
            for _ in range(10):  # Wait up to 10 seconds
                if self.connected:
                    break
                await asyncio.sleep(1)
                
            if self.connected:
                await self._setup_ha_discovery()
                logger.info("MQTT connection established and discovery configured")
                return True
            else:
                logger.error("MQTT connection timeout")
                return False
                
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            return False
            
    async def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("MQTT disconnected")
            
    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        """Handle MQTT connection."""
        if reason_code == 0:
            self.connected = True
            logger.info("MQTT connected successfully")
        else:
            logger.error(f"MQTT connection failed with code: {reason_code}")
            
    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        """Handle MQTT disconnection."""
        self.connected = False
        logger.warning(f"MQTT disconnected with code: {reason_code}")
        
    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            logger.debug(f"MQTT message received: {topic} -> {payload}")
            
            # Handle Home Assistant commands
            if topic.endswith('/command'):
                asyncio.create_task(self._handle_ha_command(payload))
                
        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")
            
    async def _handle_ha_command(self, command: str) -> None:
        """Handle commands from Home Assistant."""
        try:
            if command == "health_check":
                status = await self.app.get_system_status()
                await self.publish_status(status)
            elif command.startswith("process_directory:"):
                directory_path = command.split(":", 1)[1]
                await self.app.process_directory_async(Path(directory_path))
            else:
                logger.warning(f"Unknown MQTT command: {command}")
        except Exception as e:
            logger.error(f"Error handling MQTT command: {e}")
            
    async def _setup_ha_discovery(self) -> None:
        """Set up Home Assistant MQTT discovery."""
        if not self.client:
            return
            
        device_info = {
            "identifiers": ["aicleaner"],
            "name": self.config.device_name,
            "model": "AI Cleaner v1.0",
            "manufacturer": "AI Cleaner Project",
            "sw_version": "1.0.0"
        }
        
        # Health sensor configuration
        health_config = {
            "name": "AI Cleaner Health",
            "unique_id": "aicleaner_health",
            "state_topic": f"{self.config.discovery_topic}/sensor/aicleaner/health/state",
            "json_attributes_topic": f"{self.config.discovery_topic}/sensor/aicleaner/health/attributes",
            "device": device_info,
            "icon": "mdi:robot"
        }
        
        # Statistics sensor configuration  
        stats_config = {
            "name": "AI Cleaner Statistics",
            "unique_id": "aicleaner_stats",
            "state_topic": f"{self.config.discovery_topic}/sensor/aicleaner/stats/state",
            "json_attributes_topic": f"{self.config.discovery_topic}/sensor/aicleaner/stats/attributes",
            "device": device_info,
            "icon": "mdi:chart-line"
        }
        
        # Command topic for Home Assistant to send commands
        command_topic = f"{self.config.discovery_topic}/sensor/aicleaner/command"
        
        # Publish discovery configurations
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.client.publish(
                f"{self.config.discovery_topic}/sensor/aicleaner_health/config",
                json.dumps(health_config),
                retain=True
            )
        )
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.client.publish(
                f"{self.config.discovery_topic}/sensor/aicleaner_stats/config", 
                json.dumps(stats_config),
                retain=True
            )
        )
        
        # Subscribe to command topic
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.client.subscribe(f"{command_topic}")
        )
        
        logger.info("Home Assistant MQTT discovery configured")
        
    async def publish_status(self, status: Dict[str, Any]) -> None:
        """Publish system status to MQTT."""
        if not self.client or not self.connected:
            return
            
        try:
            # Publish health status
            health_state = status.get("status", "unknown")
            health_attrs = {
                "healthy_providers": status.get("healthy_providers", []),
                "provider_health": status.get("provider_health", {}),
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.publish(
                    f"{self.config.discovery_topic}/sensor/aicleaner/health/state",
                    health_state
                )
            )
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.publish(
                    f"{self.config.discovery_topic}/sensor/aicleaner/health/attributes",
                    json.dumps(health_attrs)
                )
            )
            
            # Publish statistics
            stats = status.get("processing_stats", {})
            stats_attrs = {
                **stats,
                "uptime_seconds": status.get("uptime", 0),
                "configuration": status.get("configuration", {})
            }
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.publish(
                    f"{self.config.discovery_topic}/sensor/aicleaner/stats/state",
                    stats.get("processed_images", 0)
                )
            )
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.publish(
                    f"{self.config.discovery_topic}/sensor/aicleaner/stats/attributes",
                    json.dumps(stats_attrs)
                )
            )
            
        except Exception as e:
            logger.error(f"Error publishing MQTT status: {e}")


class WebAPI:
    """Web API server for Home Assistant integration."""
    
    def __init__(self, app: 'AICleanerApp'):
        self.app = app
        self.web_app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        
        # Set up routes
        self._setup_routes()
        
    def _setup_routes(self) -> None:
        """Set up web API routes."""
        self.web_app.router.add_get('/health', self._handle_health)
        self.web_app.router.add_get('/status', self._handle_status) 
        self.web_app.router.add_get('/metrics', self._handle_metrics)
        self.web_app.router.add_post('/process', self._handle_process)
        self.web_app.router.add_post('/config', self._handle_config_update)
        self.web_app.router.add_get('/providers', self._handle_providers)
        self.web_app.router.add_post('/providers/{provider}/reset', self._handle_provider_reset)
        
        # Add middleware for CORS and error handling
        self.web_app.middlewares.append(self._cors_middleware)
        self.web_app.middlewares.append(self._error_middleware)
        
    async def start(self, host: str = '0.0.0.0', port: int = 8080) -> bool:
        """Start the web API server."""
        try:
            self.runner = web.AppRunner(self.web_app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, host, port)
            await self.site.start()
            
            logger.info(f"Web API server started on {host}:{port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start web API server: {e}")
            return False
            
    async def stop(self) -> None:
        """Stop the web API server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("Web API server stopped")
        
    @web.middleware
    async def _cors_middleware(self, request: Request, handler) -> Response:
        """CORS middleware for web API."""
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
        
    @web.middleware
    async def _error_middleware(self, request: Request, handler) -> Response:
        """Error handling middleware."""
        try:
            return await handler(request)
        except Exception as e:
            logger.error(f"API error: {e}")
            return json_response(
                {"error": str(e), "traceback": traceback.format_exc()},
                status=500
            )
            
    async def _handle_health(self, request: Request) -> Response:
        """Handle health check endpoint."""
        try:
            if self.app.orchestrator:
                health_status = await self.app.orchestrator.get_health_status_for_ha()
                return json_response(health_status)
            else:
                return json_response({"state": "not_initialized"}, status=503)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)
            
    async def _handle_status(self, request: Request) -> Response:
        """Handle system status endpoint."""
        try:
            status = await self.app.get_system_status()
            return json_response(status)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)
            
    async def _handle_metrics(self, request: Request) -> Response:
        """Handle metrics endpoint."""
        try:
            if self.app.orchestrator:
                metrics = self.app.orchestrator.export_health_history()
                return json_response(metrics)
            else:
                return json_response({"error": "Orchestrator not initialized"}, status=503)
        except Exception as e:
            return json_response({"error": str(e)}, status=500)
            
    async def _handle_process(self, request: Request) -> Response:
        """Handle image processing endpoint."""
        try:
            data = await request.json()
            directory = data.get('directory')
            
            if not directory:
                return json_response({"error": "Directory path required"}, status=400)
                
            directory_path = Path(directory)
            if not directory_path.exists():
                return json_response({"error": "Directory does not exist"}, status=400)
                
            # Start processing asynchronously
            asyncio.create_task(self.app.process_directory_async(directory_path))
            
            return json_response({"message": "Processing started", "directory": str(directory_path)})
            
        except Exception as e:
            return json_response({"error": str(e)}, status=500)
            
    async def _handle_config_update(self, request: Request) -> Response:
        """Handle configuration update endpoint."""
        try:
            new_config = await request.json()
            
            if self.app.orchestrator:
                success = await self.app.orchestrator.update_configuration(new_config)
                if success:
                    return json_response({"message": "Configuration updated successfully"})
                else:
                    return json_response({"error": "Configuration update failed"}, status=400)
            else:
                return json_response({"error": "Orchestrator not initialized"}, status=503)
                
        except Exception as e:
            return json_response({"error": str(e)}, status=500)
            
    async def _handle_providers(self, request: Request) -> Response:
        """Handle provider status endpoint."""
        try:
            if self.app.orchestrator:
                provider_metrics = {}
                for provider_name in ["gemini", "ollama"]:  # Known providers
                    metrics = self.app.orchestrator.get_provider_metrics(provider_name)
                    if metrics:
                        provider_metrics[provider_name] = metrics
                        
                return json_response(provider_metrics)
            else:
                return json_response({"error": "Orchestrator not initialized"}, status=503)
                
        except Exception as e:
            return json_response({"error": str(e)}, status=500)
            
    async def _handle_provider_reset(self, request: Request) -> Response:
        """Handle provider circuit breaker reset endpoint."""
        try:
            provider = request.match_info['provider']
            
            if self.app.orchestrator:
                success = self.app.orchestrator.reset_circuit_breaker(provider)
                if success:
                    return json_response({"message": f"Circuit breaker reset for {provider}"})
                else:
                    return json_response({"error": f"Failed to reset circuit breaker for {provider}"}, status=400)
            else:
                return json_response({"error": "Orchestrator not initialized"}, status=503)
                
        except Exception as e:
            return json_response({"error": str(e)}, status=500)


class AICleanerApp:
    """Main AI Cleaner application coordinating all components."""
    
    def __init__(self):
        self.config_loader = ConfigurationLoader()
        self.config: Optional[AICleanerConfig] = None
        self.orchestrator: Optional[AICleanerOrchestrator] = None
        self.stats = AppStats()
        
        # Integration components
        self.web_api = WebAPI(self)
        self.mqtt_client: Optional[MQTTClient] = None
        self.directory_watcher = DirectoryWatcher(self)
        
        # Application state
        self._shutdown_event = asyncio.Event()
        self._status_update_task: Optional[asyncio.Task] = None
        self._initialized = False
        
        # Set up signal handlers
        self._setup_signal_handlers()
        
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.shutdown())
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    async def initialize(self, config_path: Optional[str] = None) -> bool:
        """Initialize the application with all components."""
        try:
            logger.info("Initializing AI Cleaner application...")
            
            # Load configuration
            self.config = await self.config_loader.load_config(config_path)
            logger.info("Configuration loaded successfully")
            
            # Set up logging based on configuration
            await self._setup_logging()
            
            # Initialize orchestrator
            self.orchestrator = AICleanerOrchestrator(self.config_loader)
            success = await self.orchestrator.initialize(config_path)
            if not success:
                logger.error("Failed to initialize orchestrator")
                return False
            logger.info("Orchestrator initialized successfully")
            
            # Initialize MQTT client if enabled
            if self.config.home_assistant.enabled:
                self.mqtt_client = MQTTClient(self.config, self)
                mqtt_success = await self.mqtt_client.connect()
                if mqtt_success:
                    logger.info("MQTT client connected successfully")
                else:
                    logger.warning("MQTT client connection failed, continuing without MQTT")
            
            # Start web API server
            api_success = await self.web_api.start(port=8080)
            if not api_success:
                logger.error("Failed to start web API server")
                return False
                
            # Start status update task
            self._status_update_task = asyncio.create_task(self._status_update_loop())
            
            self._initialized = True
            logger.info("AI Cleaner application initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Application initialization failed: {e}")
            logger.error(traceback.format_exc())
            return False
            
    async def _setup_logging(self) -> None:
        """Set up logging based on configuration."""
        log_config = self.config.logging
        
        # Set log level
        logging.getLogger().setLevel(getattr(logging, log_config.level.value))
        
        # Add file handler if specified
        if log_config.file_path:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_config.file_path,
                maxBytes=log_config.max_file_size_mb * 1024 * 1024,
                backupCount=log_config.backup_count
            )
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            logging.getLogger().addHandler(file_handler)
            
    async def run(self) -> None:
        """Run the main application loop."""
        logger.info("Starting AI Cleaner main application loop...")
        
        try:
            # Wait for shutdown signal
            await self._shutdown_event.wait()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        finally:
            await self.shutdown()
            
    async def shutdown(self) -> None:
        """Graceful shutdown of the application."""
        logger.info("Shutting down AI Cleaner application...")
        
        try:
            # Signal shutdown
            self._shutdown_event.set()
            
            # Stop status update task
            if self._status_update_task:
                self._status_update_task.cancel()
                try:
                    await self._status_update_task
                except asyncio.CancelledError:
                    pass
                    
            # Stop directory watcher
            await self.directory_watcher.stop_watching()
            
            # Stop web API server
            await self.web_api.stop()
            
            # Disconnect MQTT client
            if self.mqtt_client:
                await self.mqtt_client.disconnect()
                
            # Shutdown orchestrator
            if self.orchestrator:
                await self.orchestrator.shutdown()
                
            logger.info("Application shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            
    async def _status_update_loop(self) -> None:
        """Periodic status updates for MQTT and logging."""
        while not self._shutdown_event.is_set():
            try:
                self.stats.update_uptime()
                
                # Get system status
                if self._initialized:
                    status = await self.get_system_status()
                    
                    # Publish to MQTT if connected
                    if self.mqtt_client and self.mqtt_client.connected:
                        await self.mqtt_client.publish_status(status)
                        
                    # Log periodic status
                    logger.info(f"System status: {status.get('status', 'unknown')}, "
                              f"Uptime: {self.stats.uptime:.1f}s, "
                              f"Processed: {self.stats.total_images_processed}")
                              
                # Wait for next update
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except asyncio.CancelledError:
                logger.info("Status update loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in status update loop: {e}")
                await asyncio.sleep(60)
                
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        if not self._initialized or not self.orchestrator:
            return {
                "status": "not_initialized",
                "uptime": self.stats.uptime,
                "error": "Application not fully initialized"
            }
            
        try:
            # Get orchestrator status
            orchestrator_status = await self.orchestrator.get_system_status()
            
            # Add application-level information
            status = {
                **orchestrator_status,
                "app_stats": {
                    "uptime": self.stats.uptime,
                    "total_sessions": self.stats.total_sessions,
                    "total_images_processed": self.stats.total_images_processed,
                    "total_images_deleted": self.stats.total_images_deleted,
                    "start_time": self.stats.start_time,
                },
                "integrations": {
                    "web_api": "active" if self.web_api.runner else "inactive",
                    "mqtt": "connected" if (self.mqtt_client and self.mqtt_client.connected) else "disconnected",
                    "directory_watcher": "active" if self.directory_watcher._monitoring_task else "inactive"
                },
                "watched_directories": [str(d) for d in self.directory_watcher.watched_directories]
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                "status": "error",
                "uptime": self.stats.uptime,
                "error": str(e)
            }
            
    async def process_directory_async(self, directory: Path, specific_images: Optional[List[Path]] = None) -> Dict[str, Any]:
        """Process a directory of images asynchronously with progress reporting."""
        if not self._initialized or not self.orchestrator:
            return {"error": "Application not initialized"}
            
        try:
            logger.info(f"Starting async processing of directory: {directory}")
            
            # Get list of images to process
            if specific_images:
                image_paths = specific_images
            else:
                image_paths = []
                for pattern in self.config.processing.supported_formats:
                    image_paths.extend(directory.glob(f"*.{pattern}"))
                    image_paths.extend(directory.glob(f"*.{pattern.upper()}"))
            
            if not image_paths:
                logger.info(f"No images found in directory: {directory}")
                return {"message": "No images found", "processed": 0}
                
            # Create progress callback
            async def progress_callback(image_path, result, stats):
                logger.debug(f"Progress: {stats.processed_images}/{stats.total_images} - "
                           f"{image_path.name}: {result.action}")
                           
                # Update app statistics
                self.stats.total_images_processed += 1
                if result.action == "delete":
                    self.stats.total_images_deleted += 1
                    
            # Process images
            processing_stats = await self.orchestrator.process_images(
                image_paths, 
                progress_callback=progress_callback
            )
            
            # Update session stats
            self.stats.total_sessions += 1
            
            logger.info(f"Completed processing directory: {directory}. "
                       f"Processed: {processing_stats.processed_images}, "
                       f"Deleted: {processing_stats.deleted_images}")
            
            return {
                "message": "Processing completed",
                "directory": str(directory),
                "total_images": processing_stats.total_images,
                "processed_images": processing_stats.processed_images,
                "kept_images": processing_stats.kept_images,
                "deleted_images": processing_stats.deleted_images,
                "failed_images": processing_stats.failed_images,
                "processing_time": processing_stats.total_processing_time,
                "completion_rate": processing_stats.completion_rate,
                "deletion_rate": processing_stats.deletion_rate
            }
            
        except Exception as e:
            logger.error(f"Error processing directory {directory}: {e}")
            return {"error": str(e), "directory": str(directory)}
            
    def add_watch_directory(self, directory: Path) -> bool:
        """Add a directory to watch for automatic processing."""
        return self.directory_watcher.add_directory(directory)
        
    async def start_directory_watching(self) -> None:
        """Start automatic directory watching."""
        await self.directory_watcher.start_watching()


def create_cli_parser() -> argparse.ArgumentParser:
    """Create command line interface parser."""
    parser = argparse.ArgumentParser(
        description="AI Cleaner - Intelligent image cleanup using AI providers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with default configuration
  python -m aicleaner.src.main
  
  # Start with custom configuration file
  python -m aicleaner.src.main --config /path/to/config.yaml
  
  # Process a directory once and exit
  python -m aicleaner.src.main --process-directory /path/to/images
  
  # Start with directory watching enabled
  python -m aicleaner.src.main --watch-directory /path/to/watch
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Configuration file path (YAML or JSON)'
    )
    
    parser.add_argument(
        '--process-directory', '-p',
        type=str,
        help='Process a directory once and exit'
    )
    
    parser.add_argument(
        '--watch-directory', '-w',
        type=str,
        action='append',
        help='Add directory to watch for automatic processing (can be used multiple times)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Web API server port (default: 8080)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--no-web-api',
        action='store_true',
        help='Disable web API server'
    )
    
    parser.add_argument(
        '--no-mqtt',
        action='store_true', 
        help='Disable MQTT integration'
    )
    
    return parser


async def main() -> int:
    """Main application entry point."""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    # Set log level from command line
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    app = AICleanerApp()
    
    try:
        # Initialize application
        success = await app.initialize(args.config)
        if not success:
            logger.error("Failed to initialize application")
            return 1
            
        # Handle one-time directory processing
        if args.process_directory:
            directory = Path(args.process_directory)
            if not directory.exists():
                logger.error(f"Directory does not exist: {directory}")
                return 1
                
            result = await app.process_directory_async(directory)
            if "error" in result:
                logger.error(f"Processing failed: {result['error']}")
                return 1
            else:
                logger.info(f"Processing completed: {result}")
                return 0
                
        # Add watch directories from command line
        if args.watch_directory:
            for watch_dir in args.watch_directory:
                directory = Path(watch_dir)
                if app.add_watch_directory(directory):
                    logger.info(f"Added watch directory: {directory}")
                else:
                    logger.warning(f"Failed to add watch directory: {directory}")
                    
            # Start directory watching
            await app.start_directory_watching()
            
        # Run main application loop
        await app.run()
        return 0
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Application failed: {e}")
        logger.error(traceback.format_exc())
        return 1
    finally:
        await app.shutdown()


if __name__ == '__main__':
    # Set up asyncio policy for Windows compatibility
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    # Run the application
    exit_code = asyncio.run(main())
    sys.exit(exit_code)