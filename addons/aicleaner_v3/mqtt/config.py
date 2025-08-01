"""
MQTT Configuration Schema
Phase 4B: MQTT Discovery System

Configuration models for MQTT integration using Pydantic for validation.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class MQTTConfig(BaseModel):
    """MQTT configuration for Home Assistant discovery"""
    
    # Connection settings
    enabled: bool = Field(default=True, description="Enable MQTT integration")
    broker_host: str = Field(default="localhost", description="MQTT broker hostname")
    broker_port: int = Field(default=1883, description="MQTT broker port")
    
    # Authentication
    username: Optional[str] = Field(default=None, description="MQTT username")
    password: Optional[str] = Field(default=None, description="MQTT password")
    
    # TLS/SSL settings
    use_tls: bool = Field(default=False, description="Use TLS encryption")
    ca_cert_path: Optional[str] = Field(default=None, description="CA certificate path")
    cert_path: Optional[str] = Field(default=None, description="Client certificate path")
    key_path: Optional[str] = Field(default=None, description="Client key path")
    
    # MQTT Discovery settings
    discovery_prefix: str = Field(default="homeassistant", description="HA discovery prefix")
    device_id: str = Field(default="aicleaner_v3", description="Device identifier")
    device_name: str = Field(default="AICleaner v3", description="Device display name")
    
    # Connection management
    keepalive: int = Field(default=60, description="MQTT keepalive interval")
    reconnect_delay: int = Field(default=5, description="Reconnection delay in seconds")
    max_reconnect_attempts: int = Field(default=10, description="Maximum reconnection attempts")
    
    # Quality of Service
    qos_discovery: int = Field(default=1, description="QoS for discovery messages")
    qos_state: int = Field(default=1, description="QoS for state updates")
    qos_command: int = Field(default=1, description="QoS for command subscriptions")
    
    # Retained messages
    retain_discovery: bool = Field(default=True, description="Retain discovery messages")
    retain_state: bool = Field(default=False, description="Retain state messages")
    
    # Advanced settings
    client_id: Optional[str] = Field(default=None, description="Custom MQTT client ID")
    clean_session: bool = Field(default=True, description="Use clean session")
    will_topic: Optional[str] = Field(default=None, description="Last will topic")
    will_payload: Optional[str] = Field(default=None, description="Last will payload")
    
    @validator('broker_port')
    def validate_port(cls, v):
        """Validate broker port range"""
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v
    
    @validator('qos_discovery', 'qos_state', 'qos_command')
    def validate_qos(cls, v):
        """Validate QoS levels"""
        if v not in [0, 1, 2]:
            raise ValueError('QoS must be 0, 1, or 2')
        return v
    
    @validator('keepalive', 'reconnect_delay', 'max_reconnect_attempts')
    def validate_positive_ints(cls, v):
        """Validate positive integers"""
        if v <= 0:
            raise ValueError('Value must be positive')
        return v
    
    def get_broker_url(self) -> str:
        """Get complete broker URL"""
        protocol = "mqtts" if self.use_tls else "mqtt"
        if self.username and self.password:
            return f"{protocol}://{self.username}:{self.password}@{self.broker_host}:{self.broker_port}"
        return f"{protocol}://{self.broker_host}:{self.broker_port}"
    
    def get_client_id(self) -> str:
        """Get MQTT client ID"""
        if self.client_id:
            return self.client_id
        return f"{self.device_id}_client"
    
    def get_discovery_topic(self, component: str, object_id: str, config_type: str = "config") -> str:
        """Generate Home Assistant discovery topic"""
        return f"{self.discovery_prefix}/{component}/{self.device_id}/{object_id}/{config_type}"
    
    def get_state_topic(self, entity_id: str) -> str:
        """Generate state topic for entity"""
        return f"{self.device_id}/{entity_id}/state"
    
    def get_command_topic(self, entity_id: str) -> str:
        """Generate command topic for entity"""
        return f"{self.device_id}/{entity_id}/set"
    
    def get_availability_topic(self) -> str:
        """Get device availability topic"""
        return f"{self.device_id}/availability"
    
    def to_connection_dict(self) -> Dict[str, Any]:
        """Convert to paho-mqtt connection parameters"""
        config = {
            "host": self.broker_host,
            "port": self.broker_port,
            "keepalive": self.keepalive,
            "clean_session": self.clean_session
        }
        
        if self.username:
            config["username"] = self.username
        if self.password:
            config["password"] = self.password
            
        return config