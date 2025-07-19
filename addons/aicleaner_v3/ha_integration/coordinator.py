"""
AICleaner v3 Phase 4A - Integration Coordinator
Central orchestration and lifecycle management for HA integration.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from contextlib import asynccontextmanager

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.typing import ConfigType

from .models import (
    IntegrationConfiguration,
    IntegrationState,
    IntegrationStatus,
    EventData,
    EventType,
    SecurityEvent,
    PerformanceMetrics
)
from .entity_manager import EntityManager
from .service_framework import ServiceFramework
from .platform_coordinator import PlatformCoordinator
from .config_flow_manager import ConfigFlowManager
from .event_system import EventSystem
from .security_framework import SecurityFramework
from .performance_monitor import PerformanceMonitor


@dataclass
class IntegrationContext:
    """Integration context for shared state."""
    hass: HomeAssistant
    config_entry: ConfigEntry
    config: IntegrationConfiguration
    state: IntegrationState
    logger: logging.Logger


class IntegrationCoordinator:
    """
    Central coordinator for AICleaner v3 HA integration.
    
    Manages the complete lifecycle of the integration including:
    - Component initialization and shutdown
    - Configuration management
    - Event coordination
    - Performance monitoring
    - Security enforcement
    - Error handling and recovery
    """
    
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Initialize the integration coordinator."""
        self.hass = hass
        self.config_entry = config_entry
        self.logger = logging.getLogger(f"aicleaner_v3.coordinator.{config_entry.entry_id}")
        
        # Integration state
        self.config = IntegrationConfiguration()
        self.state = IntegrationState(
            integration_id=config_entry.entry_id,
            status=IntegrationStatus.INITIALIZING
        )
        
        # Create integration context
        self.context = IntegrationContext(
            hass=hass,
            config_entry=config_entry,
            config=self.config,
            state=self.state,
            logger=self.logger
        )
        
        # Core components
        self.entity_manager = EntityManager(self.context)
        self.service_framework = ServiceFramework(self.context)
        self.platform_coordinator = PlatformCoordinator(self.context)
        self.config_flow_manager = ConfigFlowManager(self.context)
        self.event_system = EventSystem(self.context)
        self.security_framework = SecurityFramework(self.context)
        self.performance_monitor = PerformanceMonitor(self.context)
        
        # Component registry
        self.components: Dict[str, Any] = {
            "entity_manager": self.entity_manager,
            "service_framework": self.service_framework,
            "platform_coordinator": self.platform_coordinator,
            "config_flow_manager": self.config_flow_manager,
            "event_system": self.event_system,
            "security_framework": self.security_framework,
            "performance_monitor": self.performance_monitor
        }
        
        # Lifecycle management
        self.startup_tasks: List[Callable] = []
        self.shutdown_tasks: List[Callable] = []
        self.health_checks: List[Callable] = []
        
        # Error handling
        self.error_handlers: Dict[str, Callable] = {}
        self.retry_config = {
            "max_retries": 3,
            "base_delay": 1.0,
            "max_delay": 60.0,
            "backoff_factor": 2.0
        }
        
        self.logger.info("Integration coordinator initialized")
    
    async def async_setup(self) -> bool:
        """Set up the integration coordinator and all components."""
        try:
            self.logger.info("Setting up AICleaner v3 integration")
            
            # Update state
            self.state.update_state(status=IntegrationStatus.INITIALIZING)
            
            # Fire integration started event
            await self.event_system.fire_event(
                EventType.INTEGRATION_STARTED,
                {"integration_id": self.config_entry.entry_id}
            )
            
            # Load configuration
            await self._load_configuration()
            
            # Initialize security framework first
            await self.security_framework.async_setup()
            
            # Initialize performance monitoring
            await self.performance_monitor.async_setup()
            
            # Initialize event system
            await self.event_system.async_setup()
            
            # Initialize platform coordinator
            await self.platform_coordinator.async_setup()
            
            # Initialize entity manager
            await self.entity_manager.async_setup()
            
            # Initialize service framework
            await self.service_framework.async_setup()
            
            # Initialize config flow manager
            await self.config_flow_manager.async_setup()
            
            # Run startup tasks
            await self._run_startup_tasks()
            
            # Start health monitoring
            await self._start_health_monitoring()
            
            # Update state to active
            self.state.update_state(
                status=IntegrationStatus.ACTIVE,
                entity_count=len(self.entity_manager.entities),
                service_count=len(self.service_framework.services),
                platform_count=len(self.platform_coordinator.platforms)
            )
            
            self.logger.info("AICleaner v3 integration setup completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup integration: {e}")
            self.state.update_state(status=IntegrationStatus.ERROR)
            
            # Fire error event
            await self.event_system.fire_event(
                EventType.ERROR_OCCURRED,
                {"error": str(e), "component": "coordinator"}
            )
            
            raise ConfigEntryNotReady(f"Integration setup failed: {e}")
    
    async def async_unload(self) -> bool:
        """Unload the integration coordinator and all components."""
        try:
            self.logger.info("Unloading AICleaner v3 integration")
            
            # Update state
            self.state.update_state(status=IntegrationStatus.INACTIVE)
            
            # Stop health monitoring
            await self._stop_health_monitoring()
            
            # Run shutdown tasks
            await self._run_shutdown_tasks()
            
            # Shutdown components in reverse order
            await self.config_flow_manager.async_unload()
            await self.service_framework.async_unload()
            await self.entity_manager.async_unload()
            await self.platform_coordinator.async_unload()
            await self.event_system.async_unload()
            await self.performance_monitor.async_unload()
            await self.security_framework.async_unload()
            
            # Fire integration stopped event
            await self.event_system.fire_event(
                EventType.INTEGRATION_STOPPED,
                {"integration_id": self.config_entry.entry_id}
            )
            
            self.logger.info("AICleaner v3 integration unloaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unload integration: {e}")
            return False
    
    async def async_reload(self) -> bool:
        """Reload the integration configuration."""
        try:
            self.logger.info("Reloading AICleaner v3 integration")
            
            # Reload configuration
            await self._load_configuration()
            
            # Reload components
            for component_name, component in self.components.items():
                if hasattr(component, 'async_reload'):
                    await component.async_reload()
            
            # Update state
            self.state.update_state(last_update=datetime.now())
            
            self.logger.info("AICleaner v3 integration reloaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reload integration: {e}")
            return False
    
    async def _load_configuration(self) -> None:
        """Load integration configuration."""
        try:
            # Load configuration from config entry
            config_data = self.config_entry.data.copy()
            config_data.update(self.config_entry.options)
            
            # Validate and update configuration
            self.config = IntegrationConfiguration(**config_data)
            self.context.config = self.config
            
            self.logger.info("Configuration loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
    
    async def _run_startup_tasks(self) -> None:
        """Run startup tasks."""
        try:
            for task in self.startup_tasks:
                await task()
            self.logger.info("Startup tasks completed")
            
        except Exception as e:
            self.logger.error(f"Startup task failed: {e}")
            raise
    
    async def _run_shutdown_tasks(self) -> None:
        """Run shutdown tasks."""
        try:
            for task in self.shutdown_tasks:
                await task()
            self.logger.info("Shutdown tasks completed")
            
        except Exception as e:
            self.logger.error(f"Shutdown task failed: {e}")
    
    async def _start_health_monitoring(self) -> None:
        """Start health monitoring."""
        try:
            # Schedule periodic health checks
            async def health_check_loop():
                while self.state.status == IntegrationStatus.ACTIVE:
                    await self._run_health_checks()
                    await asyncio.sleep(30)  # Check every 30 seconds
            
            # Start health monitoring in background
            asyncio.create_task(health_check_loop())
            
            self.logger.info("Health monitoring started")
            
        except Exception as e:
            self.logger.error(f"Failed to start health monitoring: {e}")
    
    async def _stop_health_monitoring(self) -> None:
        """Stop health monitoring."""
        try:
            # Health monitoring will stop automatically when state changes
            self.logger.info("Health monitoring stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop health monitoring: {e}")
    
    async def _run_health_checks(self) -> None:
        """Run health checks on all components."""
        try:
            health_status = "healthy"
            performance_score = 100.0
            error_count = 0
            
            # Check component health
            for component_name, component in self.components.items():
                if hasattr(component, 'health_check'):
                    try:
                        health_result = await component.health_check()
                        if not health_result.get('healthy', True):
                            health_status = "degraded"
                            error_count += 1
                    except Exception as e:
                        self.logger.error(f"Health check failed for {component_name}: {e}")
                        health_status = "degraded"
                        error_count += 1
            
            # Update state
            self.state.update_state(
                health_status=health_status,
                performance_score=performance_score,
                error_count=error_count
            )
            
            # Log health status
            if health_status != "healthy":
                self.logger.warning(f"Integration health: {health_status}, errors: {error_count}")
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
    
    def register_startup_task(self, task: Callable) -> None:
        """Register a startup task."""
        self.startup_tasks.append(task)
    
    def register_shutdown_task(self, task: Callable) -> None:
        """Register a shutdown task."""
        self.shutdown_tasks.append(task)
    
    def register_health_check(self, check: Callable) -> None:
        """Register a health check."""
        self.health_checks.append(check)
    
    def register_error_handler(self, error_type: str, handler: Callable) -> None:
        """Register an error handler."""
        self.error_handlers[error_type] = handler
    
    async def handle_error(self, error: Exception, component: str) -> None:
        """Handle errors with appropriate recovery strategies."""
        try:
            error_type = type(error).__name__
            
            # Log error
            self.logger.error(f"Error in {component}: {error}")
            
            # Fire error event
            await self.event_system.fire_event(
                EventType.ERROR_OCCURRED,
                {
                    "error": str(error),
                    "error_type": error_type,
                    "component": component
                }
            )
            
            # Try registered error handler
            if error_type in self.error_handlers:
                await self.error_handlers[error_type](error, component)
            
            # Update error count
            self.state.update_state(error_count=self.state.error_count + 1)
            
        except Exception as e:
            self.logger.error(f"Error handling failed: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get integration status."""
        return {
            "integration_id": self.config_entry.entry_id,
            "status": self.state.status,
            "health_status": self.state.health_status,
            "performance_score": self.state.performance_score,
            "entity_count": self.state.entity_count,
            "service_count": self.state.service_count,
            "platform_count": self.state.platform_count,
            "error_count": self.state.error_count,
            "uptime": self.state.uptime,
            "last_update": self.state.last_update
        }
    
    async def get_metrics(self) -> List[PerformanceMetrics]:
        """Get performance metrics."""
        return await self.performance_monitor.get_metrics()
    
    async def get_events(self, limit: int = 100) -> List[EventData]:
        """Get recent events."""
        return await self.event_system.get_events(limit)
    
    async def get_security_events(self, limit: int = 50) -> List[SecurityEvent]:
        """Get recent security events."""
        return await self.security_framework.get_events(limit)
    
    @asynccontextmanager
    async def component_context(self, component_name: str):
        """Context manager for component operations."""
        try:
            component = self.components.get(component_name)
            if not component:
                raise ValueError(f"Component {component_name} not found")
            
            yield component
            
        except Exception as e:
            await self.handle_error(e, component_name)
            raise
    
    def get_component(self, component_name: str) -> Optional[Any]:
        """Get component by name."""
        return self.components.get(component_name)