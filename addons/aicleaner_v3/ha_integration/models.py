"""
Pydantic Models for Home Assistant Integration
Phase 4A: Enhanced Home Assistant Integration

Defines data structures for HA entity schemas and communication protocols.
"""

from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class HAEntityType(str, Enum):
    """Home Assistant entity types supported by AICleaner"""
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    SWITCH = "switch"
    BUTTON = "button"
    SELECT = "select"

class HADeviceClass(str, Enum):
    """Home Assistant device classes for entities"""
    # Sensor device classes
    TIMESTAMP = "timestamp"
    DURATION = "duration"
    PROBLEM = "problem"
    RUNNING = "running"
    
    # Binary sensor device classes
    CONNECTIVITY = "connectivity"
    BATTERY = "battery"
    POWER = "power"

class HADeviceInfo(BaseModel):
    """Home Assistant device information for device registry"""
    identifiers: List[str] = Field(..., description="List of unique identifiers for the device")
    name: str = Field(..., description="Human-readable device name")
    manufacturer: str = Field(default="AICleaner", description="Device manufacturer")
    model: str = Field(default="v3", description="Device model")
    sw_version: Optional[str] = Field(None, description="Software version")
    hw_version: Optional[str] = Field(None, description="Hardware version")
    configuration_url: Optional[str] = Field(None, description="URL for device configuration")
    suggested_area: Optional[str] = Field(None, description="Suggested area for the device")
    via_device: Optional[str] = Field(None, description="Parent device identifier")

class HAEntityConfigBase(BaseModel):
    """Base configuration for all HA entities"""
    name: str = Field(..., description="Human-readable entity name")
    unique_id: str = Field(..., description="Unique identifier for the entity")
    icon: Optional[str] = Field(None, description="MDI icon for the entity")
    entity_category: Optional[str] = Field(None, description="Entity category (config, diagnostic)")
    enabled_by_default: bool = Field(True, description="Whether entity is enabled by default")
    device: HADeviceInfo = Field(..., description="Device information")

class HASensorConfig(HAEntityConfigBase):
    """Configuration for HA sensor entities"""
    unit_of_measurement: Optional[str] = Field(None, description="Unit of measurement")
    device_class: Optional[str] = Field(None, description="HA device class")
    state_class: Optional[str] = Field(None, description="State class (measurement, total)")
    suggested_display_precision: Optional[int] = Field(None, description="Decimal precision")
    expire_after: Optional[int] = Field(None, description="Seconds after which state expires")

class HABinarySensorConfig(HAEntityConfigBase):
    """Configuration for HA binary sensor entities"""
    device_class: Optional[str] = Field(None, description="HA device class")
    payload_on: str = Field("ON", description="Payload representing 'on' state")
    payload_off: str = Field("OFF", description="Payload representing 'off' state")
    expire_after: Optional[int] = Field(None, description="Seconds after which state expires")

class HASwitchConfig(HAEntityConfigBase):
    """Configuration for HA switch entities"""
    payload_on: str = Field("ON", description="Payload to turn switch on")
    payload_off: str = Field("OFF", description="Payload to turn switch off")
    state_on: str = Field("ON", description="State representing 'on'")
    state_off: str = Field("OFF", description="State representing 'off'")
    optimistic: bool = Field(False, description="Whether to assume state changes")

class HAButtonConfig(HAEntityConfigBase):
    """Configuration for HA button entities"""
    payload_press: str = Field("PRESS", description="Payload when button is pressed")

class HASelectConfig(HAEntityConfigBase):
    """Configuration for HA select entities"""
    options: List[str] = Field(..., description="List of available options")

class HAServiceField(BaseModel):
    """HA service field definition"""
    name: str = Field(..., description="Field display name")
    description: Optional[str] = Field(None, description="Field description")
    selector: Dict[str, Any] = Field(..., description="HA selector configuration")
    required: bool = Field(False, description="Whether field is required")
    default: Optional[Any] = Field(None, description="Default value")

class HAServiceConfig(BaseModel):
    """Configuration for HA service registration"""
    service: str = Field(..., description="Service name (without domain)")
    name: str = Field(..., description="Human-readable service name")
    description: str = Field(..., description="Service description")
    fields: Dict[str, HAServiceField] = Field(default_factory=dict, description="Service fields")
    target: Optional[Dict[str, Any]] = Field(None, description="Service target configuration")

class HAEntityState(BaseModel):
    """HA entity state update"""
    entity_id: str = Field(..., description="Full entity ID (domain.object_id)")
    state: Union[str, int, float, bool] = Field(..., description="Entity state value")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Entity attributes")
    last_changed: Optional[datetime] = Field(None, description="Last changed timestamp")
    last_updated: Optional[datetime] = Field(None, description="Last updated timestamp")

# WebSocket Message Models

class HAAuthMessage(BaseModel):
    """HA WebSocket authentication message"""
    type: str = Field("auth", description="Message type")
    access_token: str = Field(..., description="Authentication token")

class HASubscribeMessage(BaseModel):
    """HA WebSocket event subscription message"""
    id: int = Field(..., description="Message ID")
    type: str = Field("subscribe_events", description="Message type")
    event_type: Optional[str] = Field(None, description="Event type to subscribe to")

class HACallServiceMessage(BaseModel):
    """HA WebSocket service call message"""
    id: int = Field(..., description="Message ID")
    type: str = Field("call_service", description="Message type")
    domain: str = Field(..., description="Service domain")
    service: str = Field(..., description="Service name")
    service_data: Dict[str, Any] = Field(default_factory=dict, description="Service data")
    target: Optional[Dict[str, Any]] = Field(None, description="Service target")

class HAGetStatesMessage(BaseModel):
    """HA WebSocket get states message"""
    id: int = Field(..., description="Message ID")
    type: str = Field("get_states", description="Message type")

class HAWebSocketResponse(BaseModel):
    """HA WebSocket response message"""
    id: Optional[int] = Field(None, description="Message ID")
    type: str = Field(..., description="Response type")
    success: Optional[bool] = Field(None, description="Whether request was successful")
    result: Optional[Any] = Field(None, description="Response result")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details")
    event: Optional[Dict[str, Any]] = Field(None, description="Event data")

# Configuration Models

class HAIntegrationConfig(BaseModel):
    """Configuration for HA integration"""
    enabled: bool = Field(True, description="Whether HA integration is enabled")
    websocket_url: str = Field(
        "ws://supervisor/core/websocket", 
        description="HA WebSocket API URL"
    )
    rest_api_url: str = Field(
        "http://supervisor/core/api", 
        description="HA REST API URL"
    )
    token_path: str = Field(
        "/var/run/secrets/supervisor_token",
        description="Path to supervisor authentication token"
    )
    entity_prefix: str = Field(
        "aicleaner_",
        description="Prefix for all created HA entities"
    )
    device_name: str = Field(
        "AICleaner Main Unit",
        description="Name for the device in HA Device Registry"
    )
    update_interval: int = Field(
        30,
        description="Update interval for entity states (seconds)"
    )
    reconnect_interval: int = Field(
        5,
        description="WebSocket reconnection interval (seconds)"
    )
    max_reconnect_attempts: int = Field(
        10,
        description="Maximum WebSocket reconnection attempts"
    )
    exposed_entities: Optional[List[Dict[str, str]]] = Field(
        None,
        description="List of entities to expose (if not all)"
    )

# Entity Factory Models

class EntityDefinition(BaseModel):
    """Definition for creating HA entities"""
    entity_type: HAEntityType = Field(..., description="Type of HA entity")
    object_id: str = Field(..., description="Entity object ID (without domain prefix)")
    name: str = Field(..., description="Human-readable name")
    config: Union[
        HASensorConfig, 
        HABinarySensorConfig, 
        HASwitchConfig, 
        HAButtonConfig,
        HASelectConfig
    ] = Field(..., description="Entity-specific configuration")
    initial_state: Optional[Any] = Field(None, description="Initial entity state")
    update_callback: Optional[str] = Field(None, description="Callback function name for updates")

class ServiceDefinition(BaseModel):
    """Definition for creating HA services"""
    service_name: str = Field(..., description="Service name")
    config: HAServiceConfig = Field(..., description="Service configuration")
    handler_callback: str = Field(..., description="Handler function name")

# Integration Status Models

class HAConnectionStatus(BaseModel):
    """HA connection status information"""
    connected: bool = Field(False, description="Whether connected to HA")
    websocket_connected: bool = Field(False, description="WebSocket connection status")
    authenticated: bool = Field(False, description="Authentication status")
    last_connection: Optional[datetime] = Field(None, description="Last connection time")
    last_error: Optional[str] = Field(None, description="Last connection error")
    reconnect_attempts: int = Field(0, description="Number of reconnection attempts")

class HAIntegrationStatus(BaseModel):
    """Overall HA integration status"""
    enabled: bool = Field(False, description="Whether integration is enabled")
    connection: HAConnectionStatus = Field(default_factory=HAConnectionStatus)
    registered_entities: int = Field(0, description="Number of registered entities")
    registered_services: int = Field(0, description="Number of registered services")
    last_entity_update: Optional[datetime] = Field(None, description="Last entity update time")
    error_count: int = Field(0, description="Number of integration errors")
    uptime: Optional[int] = Field(None, description="Integration uptime in seconds")