from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class MQTTEntity:
    """Represents a single Home Assistant entity discovered via MQTT."""
    unique_id: str
    component: str  # e.g., 'sensor', 'binary_sensor', 'light'
    config_payload: Dict[str, Any]
    state_topic: Optional[str] = None
    command_topic: Optional[str] = None
    availability_topic: Optional[str] = None

@dataclass
class MQTTDevice:
    """Represents a device with multiple entities discovered via MQTT."""
    identifiers: List[str]
    name: str
    model: str
    manufacturer: str
    entities: Dict[str, MQTTEntity] = field(default_factory=dict)