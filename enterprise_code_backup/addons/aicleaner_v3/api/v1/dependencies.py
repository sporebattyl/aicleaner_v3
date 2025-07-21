"""
Dependency injection for AICleaner v3 Developer API v1
"""

import logging
from typing import Optional, List, Dict, Any, Tuple

from utils.manager_registry import get_registry, ManagerRegistry
from utils.simple_health_monitor import SimpleHealthMonitor
from integrations.security_validator import SecurityValidator
from utils.security_presets import SecurityPresetManager
from utils.configuration_manager import ConfigurationManager
from utils.tiered_config_manager import TieredConfigurationManager

logger = logging.getLogger(__name__)


# Original Manager Registry Service (for broader, direct access if needed)

class ManagerRegistryService:
    """Service layer for ManagerRegistry operations with dependency injection"""
    
    def __init__(self, registry: ManagerRegistry):
        self._registry = registry
    
    def get_manager_status(self) -> Dict[str, Any]:
        """Get status of all managers"""
        return self._registry.get_manager_status()
    
    def get_manager(self, name: str) -> Optional[Any]:
        """Get a specific manager by name"""
        return self._registry.get_manager(name)
    
    def get_all_managers(self) -> Dict[str, Any]:
        """Get all registered managers"""
        return self._registry.get_all_managers()
    
    def unregister_manager(self, name: str) -> bool:
        """Unregister a manager"""
        return self._registry.unregister_manager(name)
    
    async def reload_all_managers(self) -> Tuple[List[str], List[str]]:
        """Reload all registered managers and return (successful, failed)"""
        reloaded_managers = []
        failed_managers = []
        
        for name, manager in self._registry.get_all_managers().items():
            try:
                if hasattr(manager, 'reload'):
                    if hasattr(manager.reload, '__await__'):
                        await manager.reload()
                    else:
                        manager.reload()
                    reloaded_managers.append(name)
                elif hasattr(manager, 'restart'):
                    if hasattr(manager.restart, '__await__'):
                        await manager.restart()
                    else:
                        manager.restart()
                    reloaded_managers.append(name)
                else:
                    # Fallback: shutdown and re-create on next access
                    if hasattr(manager, 'shutdown'):
                        if hasattr(manager.shutdown, '__await__'):
                            await manager.shutdown()
                        else:
                            manager.shutdown()
                    self._registry.unregister_manager(name)
                    reloaded_managers.append(name)
                    
                logger.info(f"Successfully reloaded manager: {name}")
                    
            except Exception as e:
                logger.error(f"Failed to reload manager {name}: {e}")
                failed_managers.append(name)
                
        return reloaded_managers, failed_managers
    
    async def shutdown_all_managers(self) -> Tuple[List[str], List[str]]:
        """Shutdown all registered managers and return (successful, failed)"""
        shutdown_managers = []
        failed_managers = []
        
        for name, manager in self._registry.get_all_managers().items():
            try:
                if hasattr(manager, 'shutdown'):
                    if hasattr(manager.shutdown, '__await__'):
                        await manager.shutdown()
                    else:
                        manager.shutdown()
                    shutdown_managers.append(name)
                    logger.info(f"Successfully shut down manager: {name}")
                else:
                    logger.warning(f"Manager {name} does not have a 'shutdown' method")
                    
                # Unregister the manager after shutdown
                self._registry.unregister_manager(name)
                    
            except Exception as e:
                logger.error(f"Failed to shutdown manager {name}: {e}")
                failed_managers.append(name)
                
        return shutdown_managers, failed_managers


def get_manager_service() -> ManagerRegistryService:
    """FastAPI dependency provider for ManagerRegistryService"""
    return ManagerRegistryService(get_registry())

# --- Feature-Oriented Services ---

class HealthService:
    """Service for system health monitoring."""
    def __init__(self, registry: ManagerRegistry):
        # Fail-fast: ensures health_monitor is registered on startup
        self.health_monitor: SimpleHealthMonitor = registry.get_manager("health_monitor")

    def get_health_status(self) -> Dict[str, Any]:
        """Retrieves the current system health status."""
        return self.health_monitor.get_status()

class SecurityService:
    """Service for security-related operations."""
    def __init__(self, registry: ManagerRegistry):
        # Fail-fast: ensures security managers are registered on startup
        self.security_validator: SecurityValidator = registry.get_manager("security_validator")
        self.preset_manager: SecurityPresetManager = registry.get_manager("security_preset_manager")

    def validate_request(self, request_data: Dict[str, Any]) -> bool:
        """Validates incoming request data using the SecurityValidator."""
        return self.security_validator.validate(request_data)

    def get_security_presets(self) -> List[str]:
        """Gets available security presets."""
        return self.preset_manager.get_presets()

class ConfigurationService:
    """Service for configuration management."""
    def __init__(self, registry: ManagerRegistry):
        # Fail-fast: ensures config managers are registered on startup
        self.config_manager: ConfigurationManager = registry.get_manager("config_manager")
        self.tiered_manager: TieredConfigurationManager = registry.get_manager("tiered_config_manager")

    def get_config_value(self, key: str) -> Optional[Any]:
        """Gets a configuration value."""
        return self.config_manager.get(key)

    def get_tiered_config_for_user(self, user_id: str) -> Dict[str, Any]:
        """Gets the final, tiered configuration for a specific user."""
        return self.tiered_manager.get_final_config(user_id)


# --- FastAPI Dependency Providers for Feature-Oriented Services ---

def get_health_service() -> HealthService:
    """FastAPI dependency provider for HealthService."""
    return HealthService(get_registry())

def get_security_service() -> SecurityService:
    """FastAPI dependency provider for SecurityService."""
    return SecurityService(get_registry())

def get_configuration_service() -> ConfigurationService:
    """FastAPI dependency provider for ConfigurationService."""
    return ConfigurationService(get_registry())