"""
Manager Registry for AICleaner v3 FastAPI Server
Thread-safe singleton pattern for manager instances across concurrent requests
"""

import threading
import logging
import time
from typing import Dict, Any, Optional, Type, TypeVar
from pathlib import Path

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ManagerRegistry:
    """
    Thread-safe singleton registry for managing all server manager instances.
    
    Ensures consistent state across FastAPI requests and provides centralized
    lifecycle management for all manager objects.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(ManagerRegistry, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._managers: Dict[str, Any] = {}
        self._manager_lock = threading.Lock()
        self._addon_root: Optional[Path] = None
        
        logger.info("ManagerRegistry initialized")
    
    def set_addon_root(self, addon_root: str):
        """Set the addon root path for manager initialization"""
        self._addon_root = Path(addon_root)
        logger.debug(f"Addon root set to: {self._addon_root}")
    
    def register_manager(self, name: str, manager_instance: Any) -> None:
        """
        Register a manager instance with thread-safe access.
        
        Args:
            name: Unique name for the manager
            manager_instance: The manager instance to register
        """
        with self._manager_lock:
            if name in self._managers:
                logger.warning(f"Manager '{name}' already registered, replacing")
            
            # Set creation time for tracking if not already set
            if not hasattr(manager_instance, '_creation_time'):
                manager_instance._creation_time = time.time()
            
            self._managers[name] = manager_instance
            logger.debug(f"Registered manager: {name}")
    
    def get_manager(self, name: str) -> Optional[Any]:
        """
        Get a registered manager instance with thread-safe access.
        
        Args:
            name: Name of the manager to retrieve
            
        Returns:
            Manager instance or None if not found
        """
        with self._manager_lock:
            manager = self._managers.get(name)
            if manager is None:
                logger.warning(f"Manager '{name}' not found in registry")
            return manager
    
    def get_or_create_manager(self, name: str, manager_class: Type[T], *args, **kwargs) -> T:
        """
        Get existing manager or create new one if it doesn't exist.
        
        Args:
            name: Unique name for the manager
            manager_class: Class to instantiate if manager doesn't exist
            *args, **kwargs: Arguments for manager constructor
            
        Returns:
            Manager instance
        """
        with self._manager_lock:
            if name in self._managers:
                return self._managers[name]
            
            # Create new manager instance
            try:
                logger.debug(f"Creating new manager: {name}")
                manager_instance = manager_class(*args, **kwargs)
                
                # Set creation time for tracking
                if not hasattr(manager_instance, '_creation_time'):
                    manager_instance._creation_time = time.time()
                
                self._managers[name] = manager_instance
                logger.info(f"Created and registered manager: {name}")
                return manager_instance
                
            except Exception as e:
                logger.error(f"Failed to create manager '{name}': {e}")
                raise
    
    def unregister_manager(self, name: str) -> bool:
        """
        Unregister a manager instance.
        
        Args:
            name: Name of the manager to unregister
            
        Returns:
            True if manager was found and removed, False otherwise
        """
        with self._manager_lock:
            if name in self._managers:
                del self._managers[name]
                logger.debug(f"Unregistered manager: {name}")
                return True
            return False
    
    def get_all_managers(self) -> Dict[str, Any]:
        """Get all registered managers (copy for thread safety)"""
        with self._manager_lock:
            return self._managers.copy()
    
    def clear_all_managers(self) -> None:
        """Clear all registered managers (useful for testing)"""
        with self._manager_lock:
            self._managers.clear()
            logger.debug("Cleared all managers from registry")
    
    def shutdown_all_managers(self) -> None:
        """Shutdown all managers gracefully"""
        with self._manager_lock:
            for name, manager in self._managers.items():
                try:
                    if hasattr(manager, 'shutdown'):
                        logger.debug(f"Shutting down manager: {name}")
                        manager.shutdown()
                    elif hasattr(manager, 'cleanup'):
                        logger.debug(f"Cleaning up manager: {name}")
                        manager.cleanup()
                    elif hasattr(manager, 'close'):
                        logger.debug(f"Closing manager: {name}")
                        manager.close()
                except Exception as e:
                    logger.error(f"Error shutting down manager '{name}': {e}")
            
            self._managers.clear()
            logger.info("All managers shut down and cleared")
    
    def get_manager_status(self) -> Dict[str, Any]:
        """Get comprehensive status information about all registered managers"""
        with self._manager_lock:
            status = {
                "total_managers": len(self._managers),
                "manager_names": list(self._managers.keys()),
                "addon_root": str(self._addon_root) if self._addon_root else None,
                "registry_initialized": self._initialized,
                "timestamp": time.time(),
                "memory_usage": len(self._managers) * 64  # Rough estimate in bytes
            }
            
            # Add individual manager status with enhanced details
            manager_details = {}
            for name, manager in self._managers.items():
                manager_info = {
                    "type": type(manager).__name__,
                    "module": type(manager).__module__,
                    "memory_address": hex(id(manager)),
                    "creation_time": getattr(manager, '_creation_time', 'unknown')
                }
                
                # Try to get manager-specific status with performance metrics
                if hasattr(manager, 'get_status'):
                    try:
                        start_time = time.time()
                        manager_info["status"] = manager.get_status()
                        manager_info["status_call_duration_ms"] = round((time.time() - start_time) * 1000, 2)
                    except Exception as e:
                        manager_info["status_error"] = str(e)
                
                # Check for configuration capabilities
                if hasattr(manager, 'get_config'):
                    manager_info["configurable"] = True
                
                # Check for health monitoring capabilities  
                if hasattr(manager, 'get_health'):
                    manager_info["health_monitoring"] = True
                
                manager_details[name] = manager_info
            
            status["managers"] = manager_details
            return status


# Convenience functions for easy access
def get_registry() -> ManagerRegistry:
    """Get the singleton ManagerRegistry instance"""
    return ManagerRegistry()


def get_manager(name: str) -> Optional[Any]:
    """Get a manager from the registry"""
    return get_registry().get_manager(name)


def register_manager(name: str, manager_instance: Any) -> None:
    """Register a manager in the registry"""
    get_registry().register_manager(name, manager_instance)


def get_or_create_manager(name: str, manager_class: Type[T], *args, **kwargs) -> T:
    """Get or create a manager in the registry"""
    return get_registry().get_or_create_manager(name, manager_class, *args, **kwargs)


# Standard manager names for consistency
from enum import Enum

class ManagerNames(Enum):
    """Standard manager names used throughout the application"""
    TIERED_CONFIG = "tiered_config"
    HEALTH_MONITOR = "health_monitor"
    SECURITY_PRESETS = "security_presets"
    CONFIGURATION = "configuration"
    SECURITY_VALIDATOR = "security_validator"
    AI_PROVIDER = "ai_provider"
    MQTT_ADAPTER = "mqtt_adapter"
    ZONE_MANAGER = "zone_manager"
    DEVICE_MANAGER = "device_manager"


# Context manager for testing
class ManagerRegistryContext:
    """Context manager for testing with clean manager registry"""
    
    def __init__(self):
        self.registry = get_registry()
        self._original_managers = None
    
    def __enter__(self):
        self._original_managers = self.registry.get_all_managers()
        self.registry.clear_all_managers()
        return self.registry
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.registry.clear_all_managers()
        # Restore original managers
        for name, manager in self._original_managers.items():
            self.registry.register_manager(name, manager)