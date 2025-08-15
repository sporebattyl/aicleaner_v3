from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional
from enum import Enum
from ..providers.base_provider import PrivacyLevel


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO" 
    WARNING = "WARNING"
    ERROR = "ERROR"


class ProviderType(str, Enum):
    GEMINI = "gemini"
    OLLAMA = "ollama"


class GeminiConfig(BaseModel):
    api_key: str = Field(..., description="Gemini API key")
    model: str = Field(default="gemini-1.5-flash", description="Gemini model to use")
    max_retries: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")
    timeout: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")


class OllamaConfig(BaseModel):
    base_url: str = Field(default="http://localhost:11434", description="Ollama server URL")
    model: str = Field(default="llava", description="Ollama model to use")
    max_retries: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")
    timeout: int = Field(default=60, ge=5, le=600, description="Request timeout in seconds")


class ProcessingConfig(BaseModel):
    privacy_level: PrivacyLevel = Field(default=PrivacyLevel.FAST, description="Privacy level for processing")
    batch_size: int = Field(default=10, ge=1, le=100, description="Number of images to process in parallel")
    max_image_size_mb: float = Field(default=10.0, gt=0, le=50, description="Maximum image size in MB")
    supported_formats: List[str] = Field(
        default=["jpg", "jpeg", "png", "gif", "bmp", "webp"],
        description="Supported image formats"
    )
    output_directory: Optional[str] = Field(default=None, description="Directory to move deleted images (for backup)")


class HealthConfig(BaseModel):
    check_interval: int = Field(default=60, ge=10, le=3600, description="Health check interval in seconds")
    max_failures: int = Field(default=3, ge=1, le=10, description="Max consecutive failures before marking unhealthy")
    timeout: int = Field(default=10, ge=1, le=60, description="Health check timeout in seconds")


class LoggingConfig(BaseModel):
    level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    file_path: Optional[str] = Field(default=None, description="Log file path (stdout if None)")
    max_file_size_mb: int = Field(default=10, ge=1, le=100, description="Maximum log file size in MB")
    backup_count: int = Field(default=3, ge=0, le=10, description="Number of backup log files to keep")


class HAConfig(BaseModel):
    enabled: bool = Field(default=True, description="Enable Home Assistant integration")
    mqtt_host: str = Field(default="localhost", description="MQTT broker host")
    mqtt_port: int = Field(default=1883, ge=1, le=65535, description="MQTT broker port")
    mqtt_username: Optional[str] = Field(default=None, description="MQTT username")
    mqtt_password: Optional[str] = Field(default=None, description="MQTT password")
    device_name: str = Field(default="AI Cleaner", description="Device name in Home Assistant")
    discovery_topic: str = Field(default="homeassistant", description="Home Assistant discovery topic")


class AICleanerConfig(BaseModel):
    # Provider configurations
    gemini: Optional[GeminiConfig] = None
    ollama: Optional[OllamaConfig] = None
    
    # Active provider priority list
    provider_priority: List[ProviderType] = Field(
        default=[ProviderType.GEMINI], 
        description="Provider priority order for failover"
    )
    
    # Processing configuration
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    
    # Health monitoring
    health: HealthConfig = Field(default_factory=HealthConfig)
    
    # Logging configuration
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # Home Assistant integration
    home_assistant: HAConfig = Field(default_factory=HAConfig)
    
    # Custom analysis prompts
    analysis_prompt: str = Field(
        default="""
Analyze this image for photo collection cleanup. Consider:
1. Image quality (blurry, dark, overexposed)
2. Duplicate/similar content
3. Unwanted objects (screenshots, memes, accidental photos)
4. Personal value (people, pets, important events)
5. Artistic/aesthetic value

Delete low-quality, accidental, or duplicate images.
Keep meaningful photos with people, pets, or significant content.
        """.strip(),
        description="Custom prompt for image analysis"
    )
    
    @validator('provider_priority')
    def validate_provider_priority(cls, v):
        if not v:
            raise ValueError("At least one provider must be specified in priority list")
        return v
        
    @validator('gemini', always=True)
    def validate_gemini_config(cls, v, values):
        provider_priority = values.get('provider_priority', [])
        if ProviderType.GEMINI in provider_priority and not v:
            raise ValueError("Gemini configuration required when gemini is in provider_priority")
        return v
        
    @validator('ollama', always=True)
    def validate_ollama_config(cls, v, values):
        provider_priority = values.get('provider_priority', [])
        if ProviderType.OLLAMA in provider_priority and not v:
            raise ValueError("Ollama configuration required when ollama is in provider_priority")
        return v