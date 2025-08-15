"""
Configuration Loader for AICleaner V3
Handles loading, validation, and management of configuration
"""

import json
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
import logging
from datetime import datetime

from .schema import (
    AICleanerConfig, GeminiConfig, OllamaConfig,
    ConfigValidationError, validate_config_dict, create_default_config
)

class ConfigurationManager:
    """Manages configuration loading, validation, and updates"""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        self.config_path = Path(config_path) if config_path else None
        self.config: Optional[AICleanerConfig] = None
        self.logger = logging.getLogger(__name__)
        
        # Config sources (in order of preference)
        self._config_sources = [
            'AICleaner V3 config file',
            'Home Assistant addon options',
            'Environment variables',
            'Default configuration'
        ]
    
    def load_configuration(self, config_path: Optional[Union[str, Path]] = None) -> AICleanerConfig:
        """
        Load configuration from various sources
        
        Args:
            config_path: Optional path to configuration file
            
        Returns:
            Validated AICleanerConfig instance
            
        Raises:
            ConfigValidationError: If configuration loading/validation fails
        """
        if config_path:
            self.config_path = Path(config_path)
        
        self.logger.info("Loading AICleaner V3 configuration...")
        
        # Try to load from file first
        if self.config_path and self.config_path.exists():
            try:
                config_dict = self._load_from_file(self.config_path)
                self.logger.info(f"Configuration loaded from file: {self.config_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load config from file {self.config_path}: {e}")
                config_dict = {}
        else:
            config_dict = {}
        
        # Merge with Home Assistant addon options if available
        ha_config = self._load_from_ha_options()
        if ha_config:
            config_dict = self._merge_config_dicts(ha_config, config_dict)
            self.logger.info("Merged Home Assistant addon options")
        
        # Merge with environment variables
        env_config = self._load_from_environment()
        if env_config:
            config_dict = self._merge_config_dicts(env_config, config_dict)
            self.logger.info("Merged environment variables")
        
        # If still no config, use defaults
        if not config_dict:
            self.logger.info("No configuration found, using defaults")
            config_dict = create_default_config().to_dict()
        
        # Validate and create configuration object
        try:
            self.config = validate_config_dict(config_dict)
            self._log_configuration_summary()
            return self.config
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise ConfigValidationError(f"Invalid configuration: {e}")
    
    def _load_from_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from JSON or YAML file"""
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                elif file_path.suffix.lower() == '.json':
                    return json.load(f) or {}
                else:
                    # Try to detect format by content
                    content = f.read()
                    f.seek(0)
                    
                    if content.strip().startswith('{'):
                        return json.load(f) or {}
                    else:
                        return yaml.safe_load(f) or {}
                        
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ConfigValidationError(f"Invalid configuration file format: {e}")
        except Exception as e:
            raise ConfigValidationError(f"Failed to load configuration file: {e}")
    
    def _load_from_ha_options(self) -> Optional[Dict[str, Any]]:
        """Load configuration from Home Assistant addon options"""
        options_file = Path('/data/options.json')
        
        if not options_file.exists():
            return None
        
        try:
            with open(options_file, 'r') as f:
                ha_options = json.load(f)
            
            # Convert HA addon options to our config format
            config_dict = self._convert_ha_options_to_config(ha_options)
            return config_dict
            
        except Exception as e:
            self.logger.warning(f"Failed to load HA addon options: {e}")
            return None
    
    def _convert_ha_options_to_config(self, ha_options: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Home Assistant addon options to our config format"""
        config = {}
        
        # System settings
        config['system'] = {
            'log_level': ha_options.get('log_level', 'info'),
            'debug_mode': ha_options.get('debug_mode', False),
            'auto_dashboard': ha_options.get('auto_dashboard', True)
        }
        
        # Privacy settings
        privacy_level = ha_options.get('privacy_level', 2)
        config['privacy'] = {
            'default_level': privacy_level
        }
        
        # Home Assistant integration
        config['homeassistant'] = {
            'device_id': ha_options.get('device_id', 'aicleaner_v3'),
            'discovery_prefix': ha_options.get('mqtt_discovery_prefix', 'homeassistant'),
            'default_camera': ha_options.get('default_camera'),
            'default_todo_list': ha_options.get('default_todo_list'),
            'mqtt_use_external': ha_options.get('mqtt_external_broker', False),
            'mqtt_host': ha_options.get('mqtt_host'),
            'mqtt_port': ha_options.get('mqtt_port', 1883),
            'mqtt_username': ha_options.get('mqtt_username'),
            'mqtt_password': ha_options.get('mqtt_password')
        }
        
        # Provider configurations
        providers = {}
        
        # Gemini provider
        primary_api_key = ha_options.get('primary_api_key')
        if primary_api_key and primary_api_key.strip():
            providers['gemini'] = {
                'api_key': primary_api_key,
                'model': ha_options.get('gemini_model', 'gemini-pro-vision')
            }
        
        # Backup Gemini providers
        backup_keys = ha_options.get('backup_api_keys', [])
        for i, api_key in enumerate(backup_keys):
            if api_key and api_key.strip():
                providers[f'gemini_backup_{i+1}'] = {
                    'api_key': api_key,
                    'model': ha_options.get('gemini_model', 'gemini-pro-vision')
                }
        
        # Ollama provider
        ollama_enabled = ha_options.get('enable_ollama', True)
        if ollama_enabled:
            providers['ollama'] = {
                'host': ha_options.get('ollama_host', 'localhost'),
                'port': ha_options.get('ollama_port', 11434),
                'vision_model': ha_options.get('ollama_vision_model', 'llava:13b'),
                'text_model': ha_options.get('ollama_text_model', 'mistral:7b')
            }
        
        config['providers'] = providers
        
        # Provider selection
        if providers:
            config['primary_provider'] = list(providers.keys())[0]
            config['fallback_providers'] = list(providers.keys())[1:3]  # Up to 2 fallbacks
        
        return config
    
    def _load_from_environment(self) -> Optional[Dict[str, Any]]:
        """Load configuration from environment variables"""
        config = {}
        
        # System environment variables
        if os.getenv('AICLEANER_LOG_LEVEL'):
            config.setdefault('system', {})['log_level'] = os.getenv('AICLEANER_LOG_LEVEL')
        
        if os.getenv('AICLEANER_DEBUG_MODE'):
            config.setdefault('system', {})['debug_mode'] = os.getenv('AICLEANER_DEBUG_MODE').lower() in ['true', '1', 'yes']
        
        # Privacy level
        if os.getenv('AICLEANER_PRIVACY_LEVEL'):
            try:
                privacy_level = int(os.getenv('AICLEANER_PRIVACY_LEVEL'))
                config.setdefault('privacy', {})['default_level'] = privacy_level
            except ValueError:
                pass
        
        # Provider API keys
        providers = {}
        
        gemini_key = os.getenv('GEMINI_API_KEY') or os.getenv('AICLEANER_GEMINI_KEY')
        if gemini_key:
            providers['gemini'] = {'api_key': gemini_key}
        
        # Ollama configuration
        ollama_host = os.getenv('OLLAMA_HOST') or os.getenv('AICLEANER_OLLAMA_HOST')
        ollama_port = os.getenv('OLLAMA_PORT') or os.getenv('AICLEANER_OLLAMA_PORT')
        
        if ollama_host or ollama_port:
            providers['ollama'] = {}
            if ollama_host:
                providers['ollama']['host'] = ollama_host
            if ollama_port:
                try:
                    providers['ollama']['port'] = int(ollama_port)
                except ValueError:
                    pass
        
        if providers:
            config['providers'] = providers
        
        return config if config else None
    
    def _merge_config_dicts(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two configuration dictionaries, with override taking precedence"""
        merged = base.copy()
        
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_config_dicts(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def _log_configuration_summary(self) -> None:
        """Log configuration summary"""
        if not self.config:
            return
        
        self.logger.info("Configuration Summary:")
        self.logger.info(f"  Privacy Level: {self.config.privacy.default_level.value} ({self.config.get_privacy_description()})")
        self.logger.info(f"  Primary Provider: {self.config.primary_provider}")
        self.logger.info(f"  Fallback Providers: {', '.join(self.config.fallback_providers)}")
        self.logger.info(f"  Configured Providers: {', '.join(self.config.providers.keys())}")
        self.logger.info(f"  Debug Mode: {self.config.system.debug_mode}")
        self.logger.info(f"  Auto Dashboard: {self.config.system.auto_dashboard}")
        
        # Log provider-specific info (without sensitive data)
        for name, provider in self.config.providers.items():
            if isinstance(provider, GeminiConfig):
                self.logger.info(f"  {name}: Gemini {provider.model}")
            elif isinstance(provider, OllamaConfig):
                self.logger.info(f"  {name}: Ollama at {provider.host}:{provider.port}")
    
    def save_configuration(self, file_path: Optional[Union[str, Path]] = None, include_sensitive: bool = False) -> None:
        """
        Save current configuration to file
        
        Args:
            file_path: Path to save configuration (uses default if None)
            include_sensitive: Whether to include sensitive data (API keys, passwords)
        """
        if not self.config:
            raise ValueError("No configuration loaded to save")
        
        save_path = Path(file_path) if file_path else self.config_path
        if not save_path:
            raise ValueError("No file path specified for saving configuration")
        
        # Create directory if it doesn't exist
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get config dict (masked or full)
        if include_sensitive:
            config_dict = self.config.to_dict()
        else:
            config_dict = self.config.to_yaml_safe_dict()
        
        # Add metadata
        config_dict['_metadata'] = {
            'generated_by': 'AICleaner V3 Configuration Manager',
            'generated_at': datetime.now().isoformat(),
            'version': '3.0.0',
            'sensitive_data_masked': not include_sensitive
        }
        
        # Save as YAML (more readable)
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False, indent=2)
            
            self.logger.info(f"Configuration saved to: {save_path}")
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            raise
    
    def validate_runtime_requirements(self) -> List[str]:
        """
        Validate runtime requirements and return list of issues
        
        Returns:
            List of validation issues (empty list if all good)
        """
        issues = []
        
        if not self.config:
            issues.append("No configuration loaded")
            return issues
        
        # Check provider configurations
        for name, provider in self.config.providers.items():
            if isinstance(provider, GeminiConfig):
                if not provider.api_key or provider.api_key == "your-gemini-api-key-here":
                    issues.append(f"Gemini provider '{name}' has invalid API key")
            
            elif isinstance(provider, OllamaConfig):
                # We can't check Ollama connectivity here, but we can validate config
                if not provider.host:
                    issues.append(f"Ollama provider '{name}' has invalid host")
        
        # Check primary provider exists
        if self.config.primary_provider not in self.config.providers:
            issues.append(f"Primary provider '{self.config.primary_provider}' not configured")
        
        # Check Home Assistant configuration
        if self.config.homeassistant.mqtt_use_external and not self.config.homeassistant.mqtt_host:
            issues.append("External MQTT enabled but no host configured")
        
        return issues
    
    def get_provider_configs_by_type(self, provider_type: type) -> Dict[str, Any]:
        """Get all provider configs of a specific type"""
        if not self.config:
            return {}
        
        return {
            name: config for name, config in self.config.providers.items()
            if isinstance(config, provider_type)
        }
    
    def update_provider_config(self, provider_name: str, updates: Dict[str, Any]) -> None:
        """Update a provider's configuration"""
        if not self.config:
            raise ValueError("No configuration loaded")
        
        if provider_name not in self.config.providers:
            raise ValueError(f"Provider '{provider_name}' not found")
        
        provider = self.config.providers[provider_name]
        
        # Update provider config
        for key, value in updates.items():
            if hasattr(provider, key):
                setattr(provider, key, value)
        
        self.logger.info(f"Updated provider '{provider_name}' configuration")
    
    @property
    def is_configured(self) -> bool:
        """Check if configuration is loaded and valid"""
        return self.config is not None
    
    def reload_configuration(self) -> AICleanerConfig:
        """Reload configuration from sources"""
        return self.load_configuration(self.config_path)

# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None

def get_config_manager() -> ConfigurationManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager

def load_config(config_path: Optional[Union[str, Path]] = None) -> AICleanerConfig:
    """Load configuration using global manager"""
    manager = get_config_manager()
    return manager.load_configuration(config_path)

def get_current_config() -> Optional[AICleanerConfig]:
    """Get currently loaded configuration"""
    manager = get_config_manager()
    return manager.config