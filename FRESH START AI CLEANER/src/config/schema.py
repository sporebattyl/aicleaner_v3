"""
Configuration Schema for AICleaner V3
Pydantic models for comprehensive configuration validation
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import re
from pathlib import Path

from ..core.privacy_engine import PrivacyLevel

class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class ProviderType(str, Enum):
    GEMINI = "gemini"
    OLLAMA = "ollama"

class GeminiConfig(BaseModel):
    """Gemini provider configuration"""
    name: str = Field(default="gemini", description="Provider name")
    api_key: str = Field(..., min_length=10, description="Gemini API key")
    model: str = Field(default="gemini-pro-vision", description="Model to use")
    base_url: Optional[str] = Field(default=None, description="Custom API base URL")
    max_retries: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")
    timeout: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")
    
    # Generation parameters
    temperature: float = Field(default=0.1, ge=0.0, le=1.0, description="Generation temperature")
    max_tokens: int = Field(default=2048, ge=100, le=8192, description="Maximum output tokens")
    top_p: float = Field(default=0.8, ge=0.0, le=1.0, description="Top-p sampling")
    top_k: int = Field(default=40, ge=1, le=100, description="Top-k sampling")
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if not v or v.strip() == '':
            raise ValueError('API key cannot be empty')
        # Basic format validation for Gemini API keys
        if not re.match(r'^[\w\-]{20,}$', v):
            raise ValueError('Invalid API key format')
        return v
    
    @validator('model')
    def validate_model(cls, v):
        valid_models = [
            'gemini-pro', 'gemini-pro-vision', 
            'gemini-1.5-pro', 'gemini-1.5-flash'
        ]
        if v not in valid_models:
            raise ValueError(f'Model must be one of: {", ".join(valid_models)}')
        return v

class OllamaConfig(BaseModel):
    """Ollama provider configuration"""
    name: str = Field(default="ollama", description="Provider name")
    host: str = Field(default="localhost", description="Ollama server host")
    port: int = Field(default=11434, ge=1, le=65535, description="Ollama server port")
    vision_model: str = Field(default="llava:13b", description="Vision model name")
    text_model: str = Field(default="mistral:7b", description="Text model name")
    timeout: int = Field(default=120, ge=30, le=600, description="Request timeout in seconds")
    max_retries: int = Field(default=2, ge=1, le=5, description="Maximum retry attempts")
    
    # Resource limits
    max_cpu_percent: float = Field(default=80.0, ge=10.0, le=100.0, description="Max CPU usage %")
    max_memory_gb: float = Field(default=8.0, ge=1.0, le=64.0, description="Max memory usage GB")
    
    # Generation parameters
    temperature: float = Field(default=0.1, ge=0.0, le=1.0, description="Generation temperature")
    max_tokens: int = Field(default=1024, ge=100, le=4096, description="Maximum output tokens")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top-p sampling")
    
    @validator('host')
    def validate_host(cls, v):
        if not v or v.strip() == '':
            raise ValueError('Host cannot be empty')
        # Basic hostname/IP validation
        if not re.match(r'^[a-zA-Z0-9\.\-_]+$', v):
            raise ValueError('Invalid host format')
        return v
    
    @validator('vision_model', 'text_model')
    def validate_model_name(cls, v):
        if not v or v.strip() == '':
            raise ValueError('Model name cannot be empty')
        # Basic model name validation (name:tag format)
        if not re.match(r'^[a-zA-Z0-9\.\-_]+(?::[a-zA-Z0-9\.\-_]+)?$', v):
            raise ValueError('Invalid model name format (should be name:tag)')
        return v
    
    @property
    def base_url(self) -> str:
        """Get the base URL for Ollama API"""
        return f"http://{self.host}:{self.port}"

class PrivacyConfig(BaseModel):
    """Privacy engine configuration"""
    default_level: PrivacyLevel = Field(default=PrivacyLevel.LEVEL_2_SANITIZED, description="Default privacy level")
    allow_level_override: bool = Field(default=True, description="Allow per-request privacy level override")
    
    # Sanitization settings
    face_blur_strength: int = Field(default=99, ge=3, le=199, description="Face blur kernel size (odd numbers)")
    text_blur_strength: int = Field(default=15, ge=3, le=51, description="Text blur kernel size (odd numbers)")
    min_face_size: int = Field(default=30, ge=10, le=200, description="Minimum face detection size")
    
    @validator('face_blur_strength', 'text_blur_strength')
    def validate_blur_strength(cls, v):
        if v % 2 == 0:
            raise ValueError('Blur strength must be odd number')
        return v
    
    @validator('default_level')
    def validate_privacy_level(cls, v):
        if not isinstance(v, PrivacyLevel):
            if isinstance(v, int):
                v = PrivacyLevel(v)
            else:
                raise ValueError(f'Invalid privacy level: {v}')
        return v

class AnnotationConfig(BaseModel):
    """Annotation engine configuration"""
    enable_annotations: bool = Field(default=True, description="Enable visual annotations")
    max_text_length: int = Field(default=50, ge=10, le=200, description="Max annotation text length")
    min_box_size: int = Field(default=20, ge=5, le=100, description="Minimum bounding box size")
    font_size: int = Field(default=14, ge=8, le=32, description="Annotation font size")
    
    # Colors (RGB tuples)
    box_color: List[int] = Field(default=[255, 0, 0], description="Bounding box color (RGB)")
    text_color: List[int] = Field(default=[255, 255, 255], description="Text color (RGB)")
    background_color: List[int] = Field(default=[255, 0, 0], description="Text background color (RGB)")
    
    # Behavior
    number_tasks: bool = Field(default=True, description="Number tasks in annotations")
    show_confidence: bool = Field(default=True, description="Show confidence scores")
    alpha: float = Field(default=0.8, ge=0.1, le=1.0, description="Annotation transparency")
    
    @validator('box_color', 'text_color', 'background_color')
    def validate_color(cls, v):
        if not isinstance(v, list) or len(v) != 3:
            raise ValueError('Color must be RGB list with 3 values')
        if not all(0 <= c <= 255 for c in v):
            raise ValueError('RGB values must be between 0-255')
        return v

class HomeAssistantConfig(BaseModel):
    """Home Assistant integration configuration"""
    device_id: str = Field(default="aicleaner_v3", description="Device ID for MQTT discovery")
    discovery_prefix: str = Field(default="homeassistant", description="MQTT discovery prefix")
    
    # Entity configuration
    default_camera: Optional[str] = Field(default=None, description="Default camera entity")
    default_todo_list: Optional[str] = Field(default=None, description="Default todo list entity")
    
    # MQTT settings
    mqtt_host: Optional[str] = Field(default=None, description="External MQTT broker host")
    mqtt_port: int = Field(default=1883, ge=1, le=65535, description="MQTT broker port")
    mqtt_username: Optional[str] = Field(default=None, description="MQTT username")
    mqtt_password: Optional[str] = Field(default=None, description="MQTT password")
    mqtt_use_external: bool = Field(default=False, description="Use external MQTT broker")
    
    @validator('device_id')
    def validate_device_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Device ID cannot be empty')
        # Must be valid for MQTT topics
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Device ID must contain only letters, numbers, and underscores')
        return v
    
    @validator('default_camera', 'default_todo_list')
    def validate_entity_id(cls, v):
        if v is not None and v.strip():
            # Basic HA entity ID validation: domain.entity_name
            if not re.match(r'^[a-z][a-z0-9_]*\.[a-z0-9_]+$', v.strip()):
                raise ValueError('Invalid Home Assistant entity ID format')
        return v
    
    @root_validator
    def validate_mqtt_config(cls, values):
        use_external = values.get('mqtt_use_external', False)
        mqtt_host = values.get('mqtt_host')
        
        if use_external and not mqtt_host:
            raise ValueError('MQTT host is required when using external broker')
        
        return values

class SystemConfig(BaseModel):
    """System-wide configuration"""
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    debug_mode: bool = Field(default=False, description="Enable debug features")
    auto_dashboard: bool = Field(default=True, description="Auto-configure HA dashboard")
    
    # Performance settings
    max_concurrent_requests: int = Field(default=3, ge=1, le=10, description="Max concurrent analysis requests")
    request_timeout: int = Field(default=300, ge=30, le=3600, description="Max request processing time")
    
    # Health monitoring
    health_check_interval: int = Field(default=60, ge=10, le=3600, description="Health check interval (seconds)")
    performance_history_size: int = Field(default=100, ge=10, le=1000, description="Performance history entries to keep")
    
    # File paths
    data_directory: Optional[str] = Field(default=None, description="Data storage directory")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    
    @validator('data_directory', 'log_file')
    def validate_path(cls, v):
        if v is not None and v.strip():
            path = Path(v.strip())
            if v == 'data_directory' and not path.is_absolute():
                raise ValueError('Data directory must be absolute path')
        return v

class AICleanerConfig(BaseModel):
    """Main AICleaner configuration"""
    system: SystemConfig = Field(default_factory=SystemConfig, description="System configuration")
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig, description="Privacy settings")
    annotation: AnnotationConfig = Field(default_factory=AnnotationConfig, description="Annotation settings")
    homeassistant: HomeAssistantConfig = Field(default_factory=HomeAssistantConfig, description="Home Assistant integration")
    
    # Provider configurations
    providers: Dict[str, Union[GeminiConfig, OllamaConfig]] = Field(default_factory=dict, description="LLM provider configurations")
    
    # Provider selection
    primary_provider: str = Field(default="gemini", description="Primary provider name")
    fallback_providers: List[str] = Field(default_factory=list, description="Fallback provider names")
    
    @validator('providers')
    def validate_providers(cls, v):
        if not v:
            raise ValueError('At least one provider must be configured')
        
        for name, config in v.items():
            if not isinstance(config, (GeminiConfig, OllamaConfig)):
                raise ValueError(f'Invalid provider config type for {name}')
        
        return v
    
    @validator('primary_provider')
    def validate_primary_provider(cls, v, values):
        providers = values.get('providers', {})
        if v not in providers:
            raise ValueError(f'Primary provider "{v}" not found in providers')
        return v
    
    @validator('fallback_providers')
    def validate_fallback_providers(cls, v, values):
        providers = values.get('providers', {})
        primary = values.get('primary_provider')
        
        for provider in v:
            if provider not in providers:
                raise ValueError(f'Fallback provider "{provider}" not found in providers')
            if provider == primary:
                raise ValueError(f'Fallback provider "{provider}" cannot be same as primary')
        
        return v
    
    @root_validator
    def validate_complete_config(cls, values):
        """Validate complete configuration consistency"""
        
        # Ensure at least one provider supports vision
        providers = values.get('providers', {})
        has_vision_provider = False
        
        for provider_config in providers.values():
            if isinstance(provider_config, (GeminiConfig, OllamaConfig)):
                has_vision_provider = True
                break
        
        if not has_vision_provider:
            raise ValueError('At least one vision-capable provider must be configured')
        
        return values
    
    def get_provider_config(self, provider_name: str) -> Optional[Union[GeminiConfig, OllamaConfig]]:
        """Get configuration for a specific provider"""
        return self.providers.get(provider_name)
    
    def get_privacy_description(self) -> str:
        """Get human-readable privacy level description"""
        level = self.privacy.default_level
        descriptions = {
            PrivacyLevel.LEVEL_1_RAW: "Raw images sent to cloud (fastest, no privacy)",
            PrivacyLevel.LEVEL_2_SANITIZED: "Faces/sensitive data blurred before cloud processing (recommended)",
            PrivacyLevel.LEVEL_3_METADATA: "Only metadata sent to cloud (faster, limited accuracy)",
            PrivacyLevel.LEVEL_4_LOCAL: "Everything processed locally (slowest, maximum privacy)"
        }
        return descriptions.get(level, "Unknown privacy level")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return self.dict()
    
    def to_yaml_safe_dict(self) -> Dict[str, Any]:
        """Convert to dictionary safe for YAML export (masks sensitive data)"""
        config_dict = self.dict()
        
        # Mask sensitive information
        for provider_name, provider_config in config_dict.get('providers', {}).items():
            if 'api_key' in provider_config:
                api_key = provider_config['api_key']
                provider_config['api_key'] = f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"
            
            if 'mqtt_password' in provider_config:
                provider_config['mqtt_password'] = "***MASKED***"
        
        return config_dict

class ConfigValidationError(Exception):
    """Configuration validation error"""
    pass

def validate_config_dict(config_dict: Dict[str, Any]) -> AICleanerConfig:
    """
    Validate configuration dictionary and return AICleanerConfig instance
    
    Args:
        config_dict: Configuration dictionary
        
    Returns:
        Validated AICleanerConfig instance
        
    Raises:
        ConfigValidationError: If configuration is invalid
    """
    try:
        return AICleanerConfig(**config_dict)
    except Exception as e:
        raise ConfigValidationError(f"Configuration validation failed: {e}")

def create_default_config() -> AICleanerConfig:
    """Create a default configuration with placeholders"""
    
    gemini_config = GeminiConfig(
        api_key="your-gemini-api-key-here",
        model="gemini-pro-vision"
    )
    
    ollama_config = OllamaConfig(
        host="localhost",
        port=11434,
        vision_model="llava:13b",
        text_model="mistral:7b"
    )
    
    return AICleanerConfig(
        providers={
            "gemini": gemini_config,
            "ollama": ollama_config
        },
        primary_provider="gemini",
        fallback_providers=["ollama"]
    )