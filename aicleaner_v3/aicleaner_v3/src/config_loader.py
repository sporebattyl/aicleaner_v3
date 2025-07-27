"""
Configuration loader for AICleaner v3 Core Service
Implements 2-tier configuration system: defaults + user overrides
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from copy import deepcopy

from .service_registry import Reloadable, ServiceRegistry, ReloadContext

logger = logging.getLogger(__name__)


class ConfigurationLoader(Reloadable):
    """
    Loads and merges configuration from default and user files.
    Supports environment variable substitution.
    """
    
    def __init__(self, config_dir: str = "/app/src", service_registry: Optional[ServiceRegistry] = None):
        self.config_dir = Path(config_dir)
        self.default_config_file = self.config_dir / "app_config.default.yaml"
        self.user_config_file = self.config_dir / "app_config.user.yaml"
        self._cached_config: Optional[Dict[str, Any]] = None
        self._config_version: int = 0
        self._last_loaded_config: Optional[Dict[str, Any]] = None
        self._service_registry: Optional[ServiceRegistry] = service_registry
        
    def load_configuration(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load and merge configuration from default and user files.
        
        Args:
            force_reload: If True, ignore cached configuration
            
        Returns:
            Merged configuration dictionary
        """
        if self._cached_config is not None and not force_reload:
            return self._cached_config
            
        try:
            # Load default configuration
            default_config = self._load_yaml_file(self.default_config_file)
            if not default_config:
                raise ValueError("Default configuration file is empty or invalid")
                
            # Start with defaults
            merged_config = deepcopy(default_config)
            
            # Overlay user configuration if it exists
            if self.user_config_file.exists():
                user_config = self._load_yaml_file(self.user_config_file)
                if user_config:
                    merged_config = self._deep_merge(merged_config, user_config)
                    logger.info("User configuration loaded and merged")
            else:
                logger.info("No user configuration file found, using defaults only")
            
            # Substitute environment variables
            merged_config = self._substitute_env_vars(merged_config)
            
            # Cache the result
            self._cached_config = merged_config
            self._last_loaded_config = deepcopy(merged_config) # Store for rollback/comparison
            self._config_version += 1 # Increment version on successful load
            
            logger.info("Configuration loaded successfully")
            return merged_config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML file and return dictionary"""
        try:
            with open(file_path, 'r') as f:
                content = yaml.safe_load(f)
                return content or {}
        except FileNotFoundError:
            logger.warning(f"Configuration file not found: {file_path}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            raise
    
    def _deep_merge(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.
        Dictionary values are merged, list values are replaced.
        """
        result = deepcopy(base)
        
        for key, value in overlay.items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    # Deep merge dictionaries
                    result[key] = self._deep_merge(result[key], value)
                else:
                    # Replace value (including lists)
                    result[key] = deepcopy(value)
            else:
                # Add new key
                result[key] = deepcopy(value)
        
        return result
    
    def _substitute_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively substitute environment variables in configuration.
        Variables should be in the format ${VAR_NAME}
        """
        if isinstance(config, dict):
            return {
                key: self._substitute_env_vars(value)
                for key, value in config.items()
            }
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str):
            return self._substitute_env_var_string(config)
        else:
            return config
    
    def _substitute_env_var_string(self, value: str) -> str:
        """
        Substitute environment variables in a string.
        Supports ${VAR_NAME} syntax.
        """
        if not isinstance(value, str) or "${" not in value:
            return value
            
        # Simple environment variable substitution
        import re
        
        def replace_env_var(match):
            var_name = match.group(1)
            env_value = os.getenv(var_name)
            if env_value is None:
                logger.warning(f"Environment variable {var_name} not found, keeping placeholder")
                return match.group(0)  # Return original ${VAR_NAME}
            return env_value
        
        # Pattern to match ${VAR_NAME}
        pattern = r'\$\{([^}]+)\}'
        result = re.sub(pattern, replace_env_var, value)
        
        return result
    
    def get_ai_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for a specific AI provider"""
        config = self.load_configuration()
        providers = config.get('ai_providers', {})
        
        if provider not in providers:
            raise ValueError(f"AI provider '{provider}' not configured")
            
        return providers[provider]
    
    def get_active_provider(self) -> str:
        """Get the currently active AI provider"""
        config = self.load_configuration()
        return config.get('general', {}).get('active_provider', 'ollama')
    
    def get_mqtt_config(self) -> Dict[str, Any]:
        """Get MQTT configuration"""
        config = self.load_configuration()
        return config.get('mqtt', {})
    
    def get_service_config(self) -> Dict[str, Any]:
        """Get service configuration"""
        config = self.load_configuration()
        return config.get('service', {})
    
    def validate_configuration(self) -> tuple[bool, list[str]]:
        """
        Validate the current configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            config = self.load_configuration()
            
            # Validate general settings
            general = config.get('general', {})
            active_provider = general.get('active_provider')
            if not active_provider:
                errors.append("No active AI provider specified")
            
            # Validate AI providers
            ai_providers = config.get('ai_providers', {})
            if not ai_providers:
                errors.append("No AI providers configured")
            elif active_provider and active_provider not in ai_providers:
                errors.append(f"Active provider '{active_provider}' not found in ai_providers")
            
            # Validate MQTT settings
            mqtt = config.get('mqtt', {})
            broker = mqtt.get('broker', {})
            if not broker.get('host'):
                errors.append("MQTT broker host not specified")
            
            port = broker.get('port')
            if port and (not isinstance(port, int) or port < 1 or port > 65535):
                errors.append("MQTT broker port must be between 1 and 65535")
            
            # Validate service settings
            service = config.get('service', {})
            api = service.get('api', {})
            
            api_port = api.get('port')
            if api_port and (not isinstance(api_port, int) or api_port < 1 or api_port > 65535):
                errors.append("API service port must be between 1 and 65535")
            
        except Exception as e:
            errors.append(f"Configuration validation failed: {e}")
        
        return len(errors) == 0, errors
    
    def get_config_version(self) -> int:
        """Returns the current configuration version."""
        return self._config_version

    def set_service_registry(self, registry: ServiceRegistry):
        """
        Sets the ServiceRegistry instance for coordinating reloads.
        """
        self._service_registry = registry
        logger.info("ServiceRegistry set for ConfigurationLoader.")

    async def reload_configuration(self, new_config_data: Optional[Dict[str, Any]] = None) -> ReloadContext:
        """
        Initiates a hot-reload of the configuration and dependent services.
        If new_config_data is provided, it's used directly; otherwise, it attempts
        to load from files.
        
        Args:
            new_config_data: Optional dictionary with new configuration. If None,
                             configuration is loaded from files.
        
        Returns:
            ReloadContext: The context object detailing the reload operation.
        """
        if self._service_registry is None:
            error_msg = "ServiceRegistry not set. Cannot initiate reload."
            logger.error(error_msg)
            return ReloadContext(self._config_version, "failed", [error_msg])

        # Load potential new configuration from files if not provided
        temp_config_loader = ConfigurationLoader(self.config_dir) # Use a temporary loader
        try:
            if new_config_data is None:
                # This will load from files and apply env vars, but not cache globally
                new_config_to_validate = temp_config_loader.load_configuration(force_reload=True)
            else:
                # If new_config_data is provided, we still need to apply env vars
                # and deep merge with defaults if necessary for full validation context.
                # For simplicity, assuming new_config_data is already a complete config
                # or will be merged by the service registry's process.
                # A more robust solution would involve merging new_config_data with defaults here.
                default_config = temp_config_loader._load_yaml_file(temp_config_loader.default_config_file)
                merged_new_config = temp_config_loader._deep_merge(default_config, new_config_data)
                new_config_to_validate = temp_config_loader._substitute_env_vars(merged_new_config)

        except Exception as e:
            error_msg = f"Failed to prepare new configuration for reload: {e}"
            logger.error(error_msg)
            return ReloadContext(self._config_version + 1, "failed", [error_msg])

        # Initiate the two-phase commit via the ServiceRegistry
        # The ServiceRegistry will call validate_config and reload_config on registered services
        # including this ConfigurationLoader instance if it's registered.
        return await self._service_registry.initiate_reload(new_config_to_validate, self._config_version + 1)

    async def validate_config(self, new_config: Dict) -> Tuple[bool, Optional[str]]:
        """
        Implements Reloadable.validate_config for ConfigurationLoader.
        Performs a fast validation (e.g., schema check, basic sanity).
        """
        logger.info("ConfigurationLoader: Performing fast validation of new config.")
        is_valid, errors = self.validate_configuration() # Re-use existing validation logic
        if not is_valid:
            return False, "; ".join(errors)

        # Add optimistic locking check here if config version is part of the new_config
        # For now, assuming the version check is handled by the caller (e.g., API endpoint)
        # or implicitly by the ServiceRegistry's single-reload-at-a-time lock.

        return True, None

    async def reload_config(self, new_config: Dict):
        """
        Implements Reloadable.reload_config for ConfigurationLoader.
        Applies the new configuration.
        """
        logger.info("ConfigurationLoader: Applying new configuration.")
        # This is where the actual config update happens for the loader itself.
        # We need to ensure the _cached_config and version are updated.
        self._cached_config = deepcopy(new_config)
        self._last_loaded_config = deepcopy(new_config)
        self._config_version += 1
        logger.info(f"ConfigurationLoader: Configuration updated to version {self._config_version}.")


# Global configuration loader instance
config_loader = ConfigurationLoader()


def get_config() -> Dict[str, Any]:
    """Get the current configuration (convenience function)"""
    return config_loader.load_configuration()


def get_ai_provider_config(provider: str) -> Dict[str, Any]:
    """Get configuration for a specific AI provider (convenience function)"""
    return config_loader.get_ai_provider_config(provider)


def get_active_provider() -> str:
    """Get the currently active AI provider (convenience function)"""
    return config_loader.get_active_provider()