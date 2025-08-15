import os
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from .schema import AICleanerConfig

logger = logging.getLogger(__name__)


class ConfigurationLoader:
    """Configuration loader supporting multiple sources and formats."""
    
    def __init__(self):
        self.config: Optional[AICleanerConfig] = None
        
    async def load_config(self, config_path: Optional[str] = None) -> AICleanerConfig:
        """Load configuration from multiple sources with priority order."""
        
        # Priority order: CLI args > Environment > Config file > Defaults
        config_dict = {}
        
        # 1. Start with default configuration
        try:
            config_dict = self._load_defaults()
            logger.info("Loaded default configuration")
        except Exception as e:
            logger.error(f"Failed to load defaults: {e}")
            raise
            
        # 2. Load from config file if specified or found
        file_config = await self._load_from_file(config_path)
        if file_config:
            config_dict = self._deep_merge(config_dict, file_config)
            logger.info(f"Merged configuration from file: {config_path or 'auto-detected'}")
            
        # 3. Override with environment variables
        env_config = self._load_from_environment()
        if env_config:
            config_dict = self._deep_merge(config_dict, env_config)
            logger.info("Merged configuration from environment variables")
            
        # 4. Validate and create final configuration
        try:
            self.config = AICleanerConfig(**config_dict)
            logger.info("Configuration validation successful")
            return self.config
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise ValueError(f"Invalid configuration: {e}")
            
    def _load_defaults(self) -> Dict[str, Any]:
        """Load default configuration values."""
        return {
            "provider_priority": ["gemini"],
            "processing": {
                "privacy_level": "fast",
                "batch_size": 10,
                "max_image_size_mb": 10.0,
                "supported_formats": ["jpg", "jpeg", "png", "gif", "bmp", "webp"]
            },
            "health": {
                "check_interval": 60,
                "max_failures": 3,
                "timeout": 10
            },
            "logging": {
                "level": "INFO"
            },
            "home_assistant": {
                "enabled": True,
                "mqtt_host": "localhost",
                "mqtt_port": 1883,
                "device_name": "AI Cleaner"
            }
        }
        
    async def _load_from_file(self, config_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load configuration from YAML or JSON file."""
        
        # Determine config file path
        if config_path:
            file_path = Path(config_path)
        else:
            # Auto-detect config file
            possible_paths = [
                Path("config.yaml"),
                Path("config.yml"), 
                Path("config.json"),
                Path("aicleaner.yaml"),
                Path("aicleaner.yml"),
                Path("aicleaner.json"),
                Path("/data/options.json"),  # Home Assistant addon config
            ]
            
            file_path = None
            for path in possible_paths:
                if path.exists():
                    file_path = path
                    break
                    
        if not file_path or not file_path.exists():
            logger.info("No configuration file found, using defaults")
            return None
            
        try:
            content = file_path.read_text()
            
            if file_path.suffix.lower() in ['.yaml', '.yml']:
                return yaml.safe_load(content)
            elif file_path.suffix.lower() == '.json':
                return json.loads(content)
            else:
                logger.warning(f"Unsupported config file format: {file_path.suffix}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load config from {file_path}: {e}")
            raise ValueError(f"Cannot load configuration file {file_path}: {e}")
            
    def _load_from_environment(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}
        
        # Map environment variables to config structure
        env_mappings = {
            'AICLEANER_GEMINI_API_KEY': ['gemini', 'api_key'],
            'AICLEANER_GEMINI_MODEL': ['gemini', 'model'],
            'AICLEANER_OLLAMA_URL': ['ollama', 'base_url'],
            'AICLEANER_OLLAMA_MODEL': ['ollama', 'model'],
            'AICLEANER_PRIVACY_LEVEL': ['processing', 'privacy_level'],
            'AICLEANER_BATCH_SIZE': ['processing', 'batch_size'],
            'AICLEANER_LOG_LEVEL': ['logging', 'level'],
            'AICLEANER_MQTT_HOST': ['home_assistant', 'mqtt_host'],
            'AICLEANER_MQTT_PORT': ['home_assistant', 'mqtt_port'],
            'AICLEANER_MQTT_USERNAME': ['home_assistant', 'mqtt_username'],
            'AICLEANER_MQTT_PASSWORD': ['home_assistant', 'mqtt_password'],
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if config_path[-1] in ['batch_size', 'mqtt_port', 'max_failures', 'check_interval', 'timeout']:
                    try:
                        value = int(value)
                    except ValueError:
                        logger.warning(f"Invalid integer value for {env_var}: {value}")
                        continue
                elif config_path[-1] in ['max_image_size_mb']:
                    try:
                        value = float(value)
                    except ValueError:
                        logger.warning(f"Invalid float value for {env_var}: {value}")
                        continue
                elif config_path[-1] == 'enabled':
                    value = value.lower() in ['true', '1', 'yes', 'on']
                    
                # Set nested configuration value
                self._set_nested_value(env_config, config_path, value)
                
        return env_config
        
    def _set_nested_value(self, config: Dict[str, Any], path: list, value: Any) -> None:
        """Set a nested configuration value using a path list."""
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
        
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result
        
    def get_config(self) -> AICleanerConfig:
        """Get the loaded configuration."""
        if self.config is None:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")
        return self.config
        
    def validate_provider_config(self, provider_type: str) -> bool:
        """Validate that a specific provider is properly configured."""
        if self.config is None:
            return False
            
        if provider_type == "gemini":
            return (self.config.gemini is not None and 
                   self.config.gemini.api_key is not None and
                   len(self.config.gemini.api_key.strip()) > 0)
        elif provider_type == "ollama":
            return (self.config.ollama is not None and
                   self.config.ollama.base_url is not None)
        
        return False