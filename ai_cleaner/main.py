"""
Main application entry point for AI Cleaner Home Assistant addon.
Orchestrates initialization, startup, and graceful shutdown of all components.
"""

import asyncio
import signal
import logging
import sys
import os
from datetime import datetime
from typing import Optional
import json

# Set up basic logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Import core modules
from core.config import get_config, reload_config, ConfigurationError
from core.analysis_manager import AnalysisManager


logger = logging.getLogger(__name__)


class AICleanerApp:
    """
    Main application class for AI Cleaner addon.
    
    Handles initialization, startup, shutdown, and signal handling.
    """
    
    def __init__(self):
        self.analysis_manager: Optional[AnalysisManager] = None
        self.config = None
        self.shutdown_event = asyncio.Event()
        self._shutdown_requested = False
    
    def setup_logging(self):
        """Setup logging based on configuration."""
        try:
            self.config = get_config()
            
            # Set log level from configuration
            log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Configure root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(log_level)
            
            # Remove existing handlers
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            # Add console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
            
            # Optionally add file handler for debugging
            if self.config.log_level.lower() == 'debug':
                try:
                    file_handler = logging.FileHandler('/data/ai_cleaner.log')
                    file_handler.setLevel(logging.DEBUG)
                    file_handler.setFormatter(formatter)
                    root_logger.addHandler(file_handler)
                except Exception as e:
                    logger.warning(f"Could not create log file: {e}")
            
            # Set specific logger levels
            logging.getLogger('aiohttp').setLevel(logging.WARNING)
            logging.getLogger('aiomqtt').setLevel(logging.INFO)
            
            logger.info(f"Logging configured - Level: {self.config.log_level.upper()}")
        
        except Exception as e:
            # Use basic logging if configuration fails
            logger.error(f"Failed to setup logging from config: {e}")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        if os.name != 'nt':  # Unix-like systems
            loop = asyncio.get_event_loop()
            
            for signum in [signal.SIGTERM, signal.SIGINT]:
                loop.add_signal_handler(
                    signum,
                    lambda s=signum: asyncio.create_task(self._signal_handler(s))
                )
            
            logger.info("Signal handlers configured")
        else:
            logger.info("Signal handlers not configured (Windows)")
    
    async def _signal_handler(self, signum: int):
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        logger.info(f"Received signal {signal_name}, initiating graceful shutdown...")
        
        self._shutdown_requested = True
        self.shutdown_event.set()
    
    async def initialize(self) -> bool:
        """Initialize the application and all components."""
        try:
            logger.info("=== AI Cleaner Home Assistant Addon Starting ===")
            logger.info(f"Startup time: {datetime.now().isoformat()}")
            
            # Load and validate configuration
            try:
                self.config = get_config()
                logger.info("Configuration loaded successfully")
                logger.info(f"AI Provider: {self.config.ai_provider}")
                logger.info(f"Privacy Level: {self.config.privacy_level}")
                logger.info(f"Zones Enabled: {self.config.enable_zones}")
                if self.config.enable_zones:
                    logger.info(f"Configured Zones: {len(self.config.zones)}")
            
            except ConfigurationError as e:
                logger.error(f"Configuration error: {e}")
                return False
            
            # Create and initialize analysis manager
            self.analysis_manager = AnalysisManager(self.config)
            
            if not await self.analysis_manager.initialize():
                logger.error("Failed to initialize Analysis Manager")
                return False
            
            logger.info("Application initialization completed successfully")
            return True
        
        except Exception as e:
            logger.error(f"Critical error during initialization: {e}")
            return False
    
    async def run(self):
        """Main application run loop."""
        try:
            # Initialize
            if not await self.initialize():
                logger.error("Initialization failed, exiting")
                return 1
            
            # Start analysis manager
            await self.analysis_manager.start()
            
            logger.info("AI Cleaner addon is now running...")
            logger.info("Components status:")
            
            # Log initial status
            if self.analysis_manager:
                status = self.analysis_manager.get_status()
                logger.info(f"  - Analysis Manager: {status['state']}")
                logger.info(f"  - AI Provider: {status['ai_provider']['name']} ({'available' if status['ai_provider']['available'] else 'unavailable'})")
                logger.info(f"  - Scheduler: {'running' if status['scheduler_status']['running'] else 'stopped'}")
                logger.info(f"  - Total Tasks: {status['scheduler_status']['total_tasks']}")
            
            # Main run loop - wait for shutdown signal
            await self.shutdown_event.wait()
            
            logger.info("Shutdown signal received, stopping...")
            return 0
        
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            return 0
        
        except Exception as e:
            logger.error(f"Critical error in main loop: {e}")
            return 1
        
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown of all components."""
        try:
            logger.info("Starting graceful shutdown...")
            
            if self.analysis_manager:
                await self.analysis_manager.shutdown()
            
            # Give a moment for final cleanup
            await asyncio.sleep(1)
            
            logger.info("=== AI Cleaner Addon Shutdown Complete ===")
        
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def health_check(self) -> dict:
        """Perform application health check."""
        health = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'uptime': None,
            'components': {},
            'errors': []
        }
        
        try:
            if self.analysis_manager:
                manager_status = self.analysis_manager.get_status()
                health['components']['analysis_manager'] = {
                    'status': manager_status['state'],
                    'initialized': manager_status['initialized'],
                    'running': manager_status['running']
                }
                
                # Check AI provider
                ai_status = manager_status['ai_provider']
                health['components']['ai_provider'] = {
                    'name': ai_status['name'],
                    'available': ai_status['available'],
                    'initialized': ai_status['initialized']
                }
                
                if not ai_status['available']:
                    health['status'] = 'degraded'
                    health['errors'].append('AI provider not available')
                
                # Check scheduler
                scheduler_status = manager_status['scheduler_status']
                health['components']['scheduler'] = {
                    'running': scheduler_status['running'] if scheduler_status else False,
                    'total_tasks': scheduler_status['total_tasks'] if scheduler_status else 0
                }
            
            else:
                health['status'] = 'unhealthy'
                health['errors'].append('Analysis manager not initialized')
        
        except Exception as e:
            health['status'] = 'unhealthy'
            health['errors'].append(f'Health check error: {e}')
        
        return health


# Web endpoint for health checks (if needed)
async def handle_health_check():
    """Simple health check endpoint for external monitoring."""
    try:
        app = getattr(handle_health_check, '_app_instance', None)
        if app:
            health = await app.health_check()
            return health
        else:
            return {'status': 'unhealthy', 'error': 'Application not initialized'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


async def main():
    """Main entry point."""
    app = AICleanerApp()
    
    # Store app instance for health checks
    handle_health_check._app_instance = app
    
    try:
        # Setup logging first
        app.setup_logging()
        
        # Setup signal handlers
        app.setup_signal_handlers()
        
        # Run the application
        exit_code = await app.run()
        
        return exit_code
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    try:
        # Handle different Python versions and event loop policies
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # Run the main application
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Fatal startup error: {e}")
        sys.exit(1)