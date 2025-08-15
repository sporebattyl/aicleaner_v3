"""
Configuration management for AI Cleaner Home Assistant addon.
Provides Pydantic-based configuration with validation and defaults.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from dataclasses import dataclass
from pydantic import BaseModel, Field, validator, SecretStr
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ZoneConfig:
    """Configuration for a cleaning zone."""
    id: str
    name: str
    camera_entity: Optional[str] = None
    priority: int = Field(default=3, ge=1, le=5)  # 1-5 scale
    schedule: Optional[str] = None  # Cron-like schedule
    enabled: bool = True


class PrivacyLevel(str):
    """Privacy level enumeration."""
    MINIMAL = "minimal"
    STANDARD = "standard" 
    DETAILED = "detailed"


class AIProvider(str):
    """AI provider enumeration."""
    GEMINI = "gemini"
    OLLAMA = "ollama"


class AiCleanerConfig(BaseModel):
    """Main configuration class for AI Cleaner addon."""
    
    # System configuration
    log_level: str = Field(default="info", description="Logging level")
    ai_provider: AIProvider = Field(default=AIProvider.GEMINI, description="AI provider to use")
    
    # AI Provider configuration
    gemini_api_key: Optional[SecretStr] = Field(default=None, description="Google Gemini API key")
    ollama_host: str = Field(default="http://host.docker.internal:11434", description="Ollama host URL")
    ollama_model: str = Field(default="llava", description="Ollama vision model name")
    
    # Home Assistant integration
    ha_token: Optional[SecretStr] = Field(default=None, description="Home Assistant long-lived access token")
    ha_url: str = Field(default="http://supervisor/core", description="Home Assistant API URL")
    mqtt_host: str = Field(default="core-mosquitto", description="MQTT broker hostname")
    mqtt_port: int = Field(default=1883, description="MQTT broker port")
    mqtt_username: Optional[str] = Field(default=None, description="MQTT username")
    mqtt_password: Optional[SecretStr] = Field(default=None, description="MQTT password")
    
    # Entity configuration
    camera_entity: Optional[str] = Field(default=None, description="Default camera entity ID")
    todo_entity: Optional[str] = Field(default="todo.cleaning_tasks", description="Todo list entity ID")
    
    # Zone configuration
    enable_zones: bool = Field(default=False, description="Enable zone-based cleaning")
    zones: List[ZoneConfig] = Field(default_factory=list, description="Zone configurations")
    
    # Privacy settings
    privacy_level: PrivacyLevel = Field(default=PrivacyLevel.STANDARD, description="Privacy level")
    save_images: bool = Field(default=False, description="Save analyzed images")
    image_retention_days: int = Field(default=7, ge=1, le=365, description="Days to retain saved images")
    
    # PDCA settings
    analysis_interval: int = Field(default=300, ge=60, le=86400, description="Analysis interval in seconds")
    auto_create_tasks: bool = Field(default=True, description="Automatically create cleaning tasks")
    task_priority_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence for task creation")
    
    # Scheduling
    enable_scheduling: bool = Field(default=True, description="Enable scheduled analysis")
    quiet_hours_start: Optional[str] = Field(default=None, description="Quiet hours start time (HH:MM)")
    quiet_hours_end: Optional[str] = Field(default=None, description="Quiet hours end time (HH:MM)")
    
    # Performance settings
    max_concurrent_analysis: int = Field(default=2, ge=1, le=10, description="Maximum concurrent image analyses")
    analysis_timeout: int = Field(default=120, ge=30, le=600, description="Analysis timeout in seconds")
    
    # Notification settings
    enable_notifications: bool = Field(default=True, description="Enable Home Assistant notifications")
    notification_threshold: int = Field(default=5, ge=1, le=20, description="Minimum tasks for notification")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['debug', 'info', 'warning', 'error', 'critical']
        if v.lower() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.lower()
    
    @validator('quiet_hours_start', 'quiet_hours_end')
    def validate_time_format(cls, v):
        """Validate time format (HH:MM)."""
        if v is None:
            return v
        try:
            datetime.strptime(v, '%H:%M')
        except ValueError:
            raise ValueError("Time must be in HH:MM format")
        return v
    
    @validator('zones')
    def validate_zones(cls, v):
        """Validate zone configurations."""
        if not v:
            return v
        
        # Check for duplicate zone IDs
        zone_ids = [zone.id for zone in v]
        if len(zone_ids) != len(set(zone_ids)):
            raise ValueError("Duplicate zone IDs found")
        
        # Validate zone names are not empty
        for zone in v:
            if not zone.name.strip():
                raise ValueError(f"Zone {zone.id} must have a non-empty name")
        
        return v
    
    @validator('privacy_level')
    def validate_privacy_level(cls, v):
        """Validate privacy level."""
        valid_levels = [PrivacyLevel.MINIMAL, PrivacyLevel.STANDARD, PrivacyLevel.DETAILED]
        if v not in valid_levels:
            raise ValueError(f"Invalid privacy level. Must be one of: {valid_levels}")
        return v
    
    def get_ai_provider_config(self) -> Dict[str, Any]:
        """Get configuration for the selected AI provider."""
        if self.ai_provider == AIProvider.GEMINI:
            return {
                'api_key': self.gemini_api_key.get_secret_value() if self.gemini_api_key else None,
                'model': 'gemini-1.5-pro-vision-latest'
            }
        elif self.ai_provider == AIProvider.OLLAMA:
            return {
                'host': self.ollama_host,
                'model': self.ollama_model
            }
        else:
            raise ValueError(f"Unknown AI provider: {self.ai_provider}")
    
    def get_mqtt_config(self) -> Dict[str, Any]:
        """Get MQTT configuration."""
        config = {
            'host': self.mqtt_host,
            'port': self.mqtt_port,
            'username': self.mqtt_username,
        }
        if self.mqtt_password:
            config['password'] = self.mqtt_password.get_secret_value()
        return config
    
    def is_in_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours."""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        now = datetime.now().time()
        start = datetime.strptime(self.quiet_hours_start, '%H:%M').time()
        end = datetime.strptime(self.quiet_hours_end, '%H:%M').time()
        
        if start <= end:
            return start <= now <= end
        else:  # Crosses midnight
            return now >= start or now <= end
    
    def get_zone_by_id(self, zone_id: str) -> Optional[ZoneConfig]:
        """Get zone configuration by ID."""
        for zone in self.zones:
            if zone.id == zone_id:
                return zone
        return None
    
    def get_enabled_zones(self) -> List[ZoneConfig]:
        """Get list of enabled zones."""
        return [zone for zone in self.zones if zone.enabled]


class ConfigManager:
    """Configuration manager for loading and validating addon configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager."""
        self.config_path = config_path or "/data/options.json"
        self._config: Optional[AiCleanerConfig] = None
        self.logger = logging.getLogger(__name__)
    
    def load_config(self) -> AiCleanerConfig:
        """Load and validate configuration from options.json."""
        try:
            # Load addon options
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    options = json.load(f)
                self.logger.info(f"Loaded configuration from {self.config_path}")
            else:
                self.logger.warning(f"Configuration file not found at {self.config_path}, using defaults")
                options = {}
            
            # Merge with environment variables
            env_config = self._load_from_environment()
            options.update(env_config)
            
            # Create and validate configuration
            self._config = AiCleanerConfig(**options)
            
            # Validate provider availability
            self._validate_provider_config()
            
            self.logger.info("Configuration loaded and validated successfully")
            return self._config
        
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise ConfigurationError(f"Configuration error: {e}")
    
    def _load_from_environment(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}
        
        # Map environment variables to config fields
        env_mappings = {
            'AI_CLEANER_LOG_LEVEL': 'log_level',
            'AI_CLEANER_AI_PROVIDER': 'ai_provider',
            'AI_CLEANER_GEMINI_API_KEY': 'gemini_api_key',
            'AI_CLEANER_OLLAMA_HOST': 'ollama_host',
            'AI_CLEANER_HA_TOKEN': 'ha_token',
            'AI_CLEANER_HA_URL': 'ha_url',
            'AI_CLEANER_MQTT_HOST': 'mqtt_host',
            'AI_CLEANER_MQTT_USERNAME': 'mqtt_username',
            'AI_CLEANER_MQTT_PASSWORD': 'mqtt_password',
            'AI_CLEANER_CAMERA_ENTITY': 'camera_entity',
            'AI_CLEANER_TODO_ENTITY': 'todo_entity',
            'AI_CLEANER_PRIVACY_LEVEL': 'privacy_level',
        }
        
        for env_var, config_key in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if config_key in ['save_images', 'enable_zones', 'auto_create_tasks', 'enable_scheduling', 'enable_notifications']:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif config_key in ['analysis_interval', 'max_concurrent_analysis', 'analysis_timeout', 'notification_threshold']:
                    value = int(value)
                elif config_key in ['task_priority_threshold']:
                    value = float(value)
                
                env_config[config_key] = value
        
        if env_config:
            self.logger.info(f"Loaded {len(env_config)} configuration values from environment")
        
        return env_config
    
    def _validate_provider_config(self):
        """Validate AI provider configuration."""
        if not self._config:
            return
        
        if self._config.ai_provider == AIProvider.GEMINI:
            if not self._config.gemini_api_key:
                raise ConfigurationError("Gemini API key is required when using Gemini provider")
        elif self._config.ai_provider == AIProvider.OLLAMA:
            if not self._config.ollama_host:
                raise ConfigurationError("Ollama host is required when using Ollama provider")
    
    def get_config(self) -> AiCleanerConfig:
        """Get current configuration."""
        if not self._config:
            return self.load_config()
        return self._config
    
    def reload_config(self) -> AiCleanerConfig:
        """Reload configuration from file."""
        self._config = None
        return self.load_config()
    
    def save_config(self, config: AiCleanerConfig):
        """Save configuration to file (for testing purposes)."""
        config_dict = config.dict()
        
        # Convert SecretStr objects to strings for JSON serialization
        for key, value in config_dict.items():
            if hasattr(value, 'get_secret_value'):
                config_dict[key] = value.get_secret_value()
        
        with open(self.config_path, 'w') as f:
            json.dump(config_dict, f, indent=2, default=str)
        
        self.logger.info(f"Configuration saved to {self.config_path}")


class ConfigurationError(Exception):
    """Configuration-related exception."""
    pass


# Global configuration instance
_config_manager = ConfigManager()
config = _config_manager.get_config()


def get_config() -> AiCleanerConfig:
    """Get global configuration instance."""
    return _config_manager.get_config()


def reload_config() -> AiCleanerConfig:
    """Reload global configuration."""
    return _config_manager.reload_config()