"""
Configuration Schema for Home Assistant Integration
Phase 4A: Enhanced Home Assistant Integration

Defines Pydantic schemas for validating HA integration configuration.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
import os

class HAIntegrationConfig(BaseModel):
    """Home Assistant integration configuration schema"""
    
    enabled: bool = Field(
        default=True,
        description="Enable Home Assistant integration"
    )
    
    websocket_url: str = Field(
        default="ws://supervisor/core/websocket",
        description="Home Assistant WebSocket API URL"
    )
    
    rest_api_url: str = Field(
        default="http://supervisor/core/api",
        description="Home Assistant REST API URL"
    )
    
    token_path: str = Field(
        default="/var/run/secrets/supervisor_token",
        description="Path to Home Assistant supervisor authentication token"
    )
    
    entity_prefix: str = Field(
        default="aicleaner_",
        description="Prefix for all created Home Assistant entities",
        regex=r"^[a-z][a-z0-9_]*_$"
    )
    
    device_name: str = Field(
        default="AICleaner Main Unit",
        description="Name for the device in Home Assistant Device Registry",
        min_length=1,
        max_length=100
    )
    
    device_model: str = Field(
        default="v3",
        description="Device model identifier",
        min_length=1,
        max_length=50
    )
    
    device_manufacturer: str = Field(
        default="AICleaner",
        description="Device manufacturer name",
        min_length=1,
        max_length=50
    )
    
    suggested_area: Optional[str] = Field(
        default=None,
        description="Suggested area for device placement in HA",
        max_length=50
    )
    
    update_interval: int = Field(
        default=30,
        description="Entity state update interval in seconds",
        ge=5,
        le=3600
    )
    
    reconnect_interval: int = Field(
        default=5,
        description="WebSocket reconnection interval in seconds",
        ge=1,
        le=300
    )
    
    max_reconnect_attempts: int = Field(
        default=10,
        description="Maximum WebSocket reconnection attempts before giving up",
        ge=1,
        le=100
    )
    
    connection_timeout: int = Field(
        default=30,
        description="Connection timeout in seconds",
        ge=5,
        le=120
    )
    
    heartbeat_interval: int = Field(
        default=60,
        description="WebSocket heartbeat interval in seconds",
        ge=10,
        le=300
    )
    
    # Entity exposure control
    auto_register_entities: bool = Field(
        default=True,
        description="Automatically register all AICleaner entities in HA"
    )
    
    exposed_entities: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Specific entities to expose if auto_register_entities is False"
    )
    
    # Service configuration
    register_services: bool = Field(
        default=True,
        description="Register AICleaner services in Home Assistant"
    )
    
    service_domain: str = Field(
        default="aicleaner",
        description="Domain for AICleaner services in HA",
        regex=r"^[a-z][a-z0-9_]*$"
    )
    
    # Security settings
    verify_ssl: bool = Field(
        default=False,
        description="Verify SSL certificates for HA API calls"
    )
    
    require_auth: bool = Field(
        default=True,
        description="Require authentication for HA API access"
    )
    
    # Logging and monitoring
    log_level: str = Field(
        default="INFO",
        description="Log level for HA integration",
        regex=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"
    )
    
    enable_metrics: bool = Field(
        default=True,
        description="Enable collection of integration metrics"
    )
    
    metrics_retention_days: int = Field(
        default=7,
        description="Number of days to retain integration metrics",
        ge=1,
        le=365
    )
    
    # Advanced settings
    websocket_compression: bool = Field(
        default=True,
        description="Enable WebSocket compression"
    )
    
    max_pending_messages: int = Field(
        default=100,
        description="Maximum pending WebSocket messages",
        ge=10,
        le=1000
    )
    
    entity_state_cache_size: int = Field(
        default=500,
        description="Maximum number of entity states to cache",
        ge=50,
        le=5000
    )
    
    # Feature flags
    enable_device_registry: bool = Field(
        default=True,
        description="Register device in Home Assistant device registry"
    )
    
    enable_ingress: bool = Field(
        default=True,
        description="Enable Home Assistant ingress support for UI"
    )
    
    enable_websocket_events: bool = Field(
        default=True,
        description="Subscribe to Home Assistant WebSocket events"
    )
    
    enable_state_sync: bool = Field(
        default=True,
        description="Enable bidirectional state synchronization"
    )
    
    @validator('entity_prefix')
    def validate_entity_prefix(cls, v):
        """Validate entity prefix format"""
        if not v.endswith('_'):
            raise ValueError("Entity prefix must end with underscore")
        if not v.replace('_', '').isalnum():
            raise ValueError("Entity prefix must contain only alphanumeric characters and underscores")
        return v.lower()
    
    @validator('exposed_entities')
    def validate_exposed_entities(cls, v, values):
        """Validate exposed entities configuration"""
        if v is not None:
            for entity in v:
                if not isinstance(entity, dict):
                    raise ValueError("Each exposed entity must be a dictionary")
                if 'type' not in entity or 'id' not in entity:
                    raise ValueError("Each exposed entity must have 'type' and 'id' fields")
                if entity['type'] not in ['sensor', 'binary_sensor', 'switch', 'button', 'select']:
                    raise ValueError(f"Invalid entity type: {entity['type']}")
        return v
    
    @validator('token_path')
    def validate_token_path(cls, v):
        """Validate token path accessibility"""
        if not os.path.exists(os.path.dirname(v)):
            raise ValueError(f"Token directory does not exist: {os.path.dirname(v)}")
        return v
    
    class Config:
        """Pydantic configuration"""
        validate_assignment = True
        extra = "forbid"
        schema_extra = {
            "example": {
                "enabled": True,
                "websocket_url": "ws://supervisor/core/websocket",
                "rest_api_url": "http://supervisor/core/api",
                "token_path": "/var/run/secrets/supervisor_token",
                "entity_prefix": "aicleaner_",
                "device_name": "AICleaner Main Unit",
                "update_interval": 30,
                "reconnect_interval": 5,
                "max_reconnect_attempts": 10,
                "auto_register_entities": True,
                "register_services": True,
                "service_domain": "aicleaner",
                "log_level": "INFO",
                "enable_metrics": True
            }
        }

class HAEntityExposureConfig(BaseModel):
    """Configuration for specific entity exposure"""
    
    type: str = Field(
        ..., 
        description="Entity type",
        regex=r"^(sensor|binary_sensor|switch|button|select)$"
    )
    
    id: str = Field(
        ..., 
        description="Entity ID (without prefix)",
        regex=r"^[a-z][a-z0-9_]*$",
        min_length=1,
        max_length=50
    )
    
    name: Optional[str] = Field(
        None,
        description="Custom entity name (overrides default)",
        min_length=1,
        max_length=100
    )
    
    icon: Optional[str] = Field(
        None,
        description="Custom MDI icon",
        regex=r"^mdi:[a-z0-9-]+$"
    )
    
    enabled: bool = Field(
        default=True,
        description="Whether this entity should be enabled by default"
    )
    
    category: Optional[str] = Field(
        None,
        description="Entity category",
        regex=r"^(config|diagnostic)$"
    )

class HAServiceExposureConfig(BaseModel):
    """Configuration for specific service exposure"""
    
    service: str = Field(
        ...,
        description="Service name",
        regex=r"^[a-z][a-z0-9_]*$",
        min_length=1,
        max_length=50
    )
    
    name: Optional[str] = Field(
        None,
        description="Custom service name (overrides default)",
        min_length=1,
        max_length=100
    )
    
    description: Optional[str] = Field(
        None,
        description="Custom service description",
        min_length=1,
        max_length=200
    )
    
    enabled: bool = Field(
        default=True,
        description="Whether this service should be registered"
    )

# Integration with main config schema

def get_ha_integration_schema() -> Dict[str, Any]:
    """Get the JSON schema for HA integration configuration"""
    return HAIntegrationConfig.schema()

def validate_ha_config(config_data: Dict[str, Any]) -> HAIntegrationConfig:
    """Validate HA integration configuration data"""
    return HAIntegrationConfig(**config_data)