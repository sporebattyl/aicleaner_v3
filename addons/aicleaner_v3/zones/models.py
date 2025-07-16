"""
Phase 3B: Zone Configuration Models
Complete data models for zones, devices, and automation rules.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class DeviceType(str, Enum):
    """Device type enumeration."""
    LIGHT = "light"
    SENSOR = "sensor"
    SWITCH = "switch"
    CLIMATE = "climate"
    MEDIA_PLAYER = "media_player"
    LOCK = "lock"
    COVER = "cover"
    FAN = "fan"
    CAMERA = "camera"
    UNKNOWN = "unknown"


class PollingFrequency(str, Enum):
    """Device polling frequency options."""
    LOW = "low"          # Every 30 seconds
    NORMAL = "normal"    # Every 10 seconds
    HIGH = "high"        # Every 5 seconds
    REALTIME = "realtime" # Every 1 second


class RulePriority(int, Enum):
    """Rule priority levels."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class Device(BaseModel):
    """Device model with complete metadata and capabilities."""
    id: str = Field(..., description="Unique identifier for the device")
    name: str = Field(..., description="User-friendly name of the device")
    type: DeviceType = Field(DeviceType.UNKNOWN, description="Type of device")
    manufacturer: Optional[str] = Field(None, description="Manufacturer of the device")
    model: Optional[str] = Field(None, description="Model number of the device")
    ip_address: Optional[str] = Field(None, description="IP address of the device")
    mac_address: Optional[str] = Field(None, description="MAC address of the device")
    polling_frequency: PollingFrequency = Field(PollingFrequency.NORMAL, description="Polling frequency")
    location: Optional[str] = Field(None, description="Physical location within the zone")
    is_active: bool = Field(True, description="Whether device is currently active")
    power_consumption: Optional[float] = Field(None, description="Current power consumption in watts")
    
    # Device capabilities and state
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Device capabilities")
    current_state: Dict[str, Any] = Field(default_factory=dict, description="Current device state")
    last_seen: Optional[datetime] = Field(None, description="Last time device was seen")
    
    # Performance metrics
    response_time_ms: Optional[float] = Field(None, description="Average response time in milliseconds")
    reliability_score: float = Field(1.0, description="Reliability score (0.0-1.0)")
    error_count: int = Field(0, description="Number of errors encountered")
    
    # Zone-specific settings
    zone_role: Optional[str] = Field(None, description="Role of device within the zone")
    automation_enabled: bool = Field(True, description="Whether device participates in automation")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        
    def __repr__(self):
        return f"Device(id='{self.id}', name='{self.name}', type='{self.type}')"
    
    def is_available(self) -> bool:
        """Check if device is currently available."""
        if not self.last_seen:
            return False
        
        # Consider device unavailable if not seen for more than 5 minutes
        time_diff = datetime.now() - self.last_seen
        return time_diff.total_seconds() < 300
    
    def update_state(self, new_state: Dict[str, Any]) -> None:
        """Update device state and mark as seen."""
        self.current_state.update(new_state)
        self.last_seen = datetime.now()


class Rule(BaseModel):
    """Automation rule model with complete configuration."""
    id: str = Field(..., description="Unique identifier for the rule")
    name: str = Field(..., description="User-friendly name of the rule")
    description: Optional[str] = Field(None, description="Detailed description of the rule")
    
    # Rule logic
    condition: str = Field(..., description="Condition that triggers the rule")
    action: str = Field(..., description="Action to perform when condition is met")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    
    # Rule configuration
    priority: RulePriority = Field(RulePriority.NORMAL, description="Rule priority")
    enabled: bool = Field(True, description="Whether rule is currently enabled")
    
    # Scheduling
    schedule: Optional[str] = Field(None, description="Cron-like schedule expression")
    time_constraints: Dict[str, Any] = Field(default_factory=dict, description="Time-based constraints")
    
    # Execution tracking
    last_executed: Optional[datetime] = Field(None, description="Last execution timestamp")
    execution_count: int = Field(0, description="Number of times rule has been executed")
    success_count: int = Field(0, description="Number of successful executions")
    error_message: Optional[str] = Field(None, description="Last error message if execution failed")
    
    # Performance metrics
    average_execution_time_ms: float = Field(0.0, description="Average execution time")
    success_rate: float = Field(1.0, description="Success rate (0.0-1.0)")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        
    def __repr__(self):
        return f"Rule(id='{self.id}', name='{self.name}', condition='{self.condition}', action='{self.action}')"
    
    def is_due_for_execution(self) -> bool:
        """Check if rule is due for execution based on schedule."""
        if not self.enabled:
            return False
            
        # Simple time-based check - in production would use proper cron parsing
        if self.schedule:
            # Placeholder for schedule evaluation
            return True
            
        return True
    
    def record_execution(self, success: bool, execution_time_ms: float, error: Optional[str] = None) -> None:
        """Record rule execution results."""
        self.execution_count += 1
        self.last_executed = datetime.now()
        
        if success:
            self.success_count += 1
            self.error_message = None
        else:
            self.error_message = error
            
        # Update success rate
        self.success_rate = self.success_count / self.execution_count
        
        # Update average execution time
        if self.execution_count == 1:
            self.average_execution_time_ms = execution_time_ms
        else:
            # Rolling average
            self.average_execution_time_ms = (
                (self.average_execution_time_ms * (self.execution_count - 1) + execution_time_ms) 
                / self.execution_count
            )


class ZonePerformanceMetrics(BaseModel):
    """Zone performance metrics model."""
    zone_id: str = Field(..., description="Zone identifier")
    
    # Device metrics
    total_devices: int = Field(0, description="Total number of devices in zone")
    active_devices: int = Field(0, description="Number of active devices")
    average_response_time_ms: float = Field(0.0, description="Average device response time")
    
    # Automation metrics
    total_rules: int = Field(0, description="Total number of automation rules")
    active_rules: int = Field(0, description="Number of active rules")
    rules_success_rate: float = Field(1.0, description="Overall rules success rate")
    
    # Energy metrics
    total_power_consumption: float = Field(0.0, description="Total power consumption in watts")
    energy_efficiency_score: float = Field(1.0, description="Energy efficiency score")
    
    # Zone optimization
    optimization_score: float = Field(0.0, description="Zone optimization score")
    last_optimization: Optional[datetime] = Field(None, description="Last optimization timestamp")
    
    # Usage analytics
    daily_activity_score: float = Field(0.0, description="Daily activity score")
    user_satisfaction_score: float = Field(1.0, description="User satisfaction score")
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True


class Zone(BaseModel):
    """Zone model with complete configuration and analytics."""
    id: str = Field(..., description="Unique identifier for the zone")
    name: str = Field(..., description="User-friendly name of the zone")
    description: Optional[str] = Field(None, description="Detailed description of the zone")
    
    # Zone composition
    devices: List[Device] = Field(default_factory=list, description="List of devices in the zone")
    rules: List[Rule] = Field(default_factory=list, description="List of automation rules")
    
    # Zone properties
    location: Optional[str] = Field(None, description="Physical location of the zone")
    area_size_sqm: Optional[float] = Field(None, description="Zone area in square meters")
    room_type: Optional[str] = Field(None, description="Type of room (bedroom, kitchen, etc.)")
    
    # Zone status
    is_active: bool = Field(True, description="Whether zone is currently active")
    auto_optimization: bool = Field(True, description="Whether auto-optimization is enabled")
    
    # Metadata
    date_created: datetime = Field(default_factory=datetime.now, description="Zone creation timestamp")
    last_modified: datetime = Field(default_factory=datetime.now, description="Last modification timestamp")
    owner: Optional[str] = Field(None, description="Owner of the zone")
    tags: List[str] = Field(default_factory=list, description="Zone tags for categorization")
    notes: Optional[str] = Field(None, description="Additional notes about the zone")
    
    # Performance and analytics
    performance_metrics: ZonePerformanceMetrics = Field(default_factory=lambda: ZonePerformanceMetrics(zone_id=""))
    
    # Configuration
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Zone-specific configuration")
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        
    def __post_init__(self):
        """Post-initialization setup."""
        if not self.performance_metrics.zone_id:
            self.performance_metrics.zone_id = self.id
            
    def __repr__(self):
        return f"Zone(id='{self.id}', name='{self.name}', devices={len(self.devices)}, rules={len(self.rules)})"
    
    def add_device(self, device: Device) -> None:
        """Add a device to the zone."""
        # Check if device already exists
        for existing_device in self.devices:
            if existing_device.id == device.id:
                # Update existing device
                existing_device.update(device.dict())
                return
                
        self.devices.append(device)
        self.last_modified = datetime.now()
        self._update_performance_metrics()
    
    def remove_device(self, device_id: str) -> bool:
        """Remove a device from the zone."""
        for i, device in enumerate(self.devices):
            if device.id == device_id:
                self.devices.pop(i)
                self.last_modified = datetime.now()
                self._update_performance_metrics()
                return True
        return False
    
    def add_rule(self, rule: Rule) -> None:
        """Add an automation rule to the zone."""
        # Check if rule already exists
        for existing_rule in self.rules:
            if existing_rule.id == rule.id:
                # Update existing rule
                existing_rule.update(rule.dict())
                return
                
        self.rules.append(rule)
        self.last_modified = datetime.now()
        self._update_performance_metrics()
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove an automation rule from the zone."""
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                self.rules.pop(i)
                self.last_modified = datetime.now()
                self._update_performance_metrics()
                return True
        return False
    
    def get_active_devices(self) -> List[Device]:
        """Get list of active devices in the zone."""
        return [device for device in self.devices if device.is_active and device.is_available()]
    
    def get_enabled_rules(self) -> List[Rule]:
        """Get list of enabled rules in the zone."""
        return [rule for rule in self.rules if rule.enabled]
    
    def calculate_energy_consumption(self) -> float:
        """Calculate total energy consumption of the zone."""
        total_consumption = 0.0
        for device in self.get_active_devices():
            if device.power_consumption:
                total_consumption += device.power_consumption
        return total_consumption
    
    def get_zone_health_score(self) -> float:
        """Calculate overall zone health score."""
        if not self.devices:
            return 1.0
            
        active_devices = len(self.get_active_devices())
        total_devices = len(self.devices)
        device_health = active_devices / total_devices if total_devices > 0 else 1.0
        
        enabled_rules = len(self.get_enabled_rules())
        total_rules = len(self.rules)
        rule_health = enabled_rules / total_rules if total_rules > 0 else 1.0
        
        # Average device reliability
        device_reliability = sum(d.reliability_score for d in self.devices) / len(self.devices)
        
        # Average rule success rate
        rule_success = sum(r.success_rate for r in self.rules) / len(self.rules) if self.rules else 1.0
        
        # Weighted health score
        health_score = (
            device_health * 0.3 +
            rule_health * 0.2 +
            device_reliability * 0.3 +
            rule_success * 0.2
        )
        
        return min(1.0, max(0.0, health_score))
    
    def _update_performance_metrics(self) -> None:
        """Update zone performance metrics."""
        self.performance_metrics.total_devices = len(self.devices)
        self.performance_metrics.active_devices = len(self.get_active_devices())
        self.performance_metrics.total_rules = len(self.rules)
        self.performance_metrics.active_rules = len(self.get_enabled_rules())
        
        # Update power consumption
        self.performance_metrics.total_power_consumption = self.calculate_energy_consumption()
        
        # Update average response time
        active_devices = self.get_active_devices()
        if active_devices:
            response_times = [d.response_time_ms for d in active_devices if d.response_time_ms]
            if response_times:
                self.performance_metrics.average_response_time_ms = sum(response_times) / len(response_times)
        
        # Update rules success rate
        if self.rules:
            self.performance_metrics.rules_success_rate = sum(r.success_rate for r in self.rules) / len(self.rules)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert zone to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'devices': [device.dict() for device in self.devices],
            'rules': [rule.dict() for rule in self.rules],
            'location': self.location,
            'area_size_sqm': self.area_size_sqm,
            'room_type': self.room_type,
            'is_active': self.is_active,
            'auto_optimization': self.auto_optimization,
            'date_created': self.date_created.isoformat(),
            'last_modified': self.last_modified.isoformat(),
            'owner': self.owner,
            'tags': self.tags,
            'notes': self.notes,
            'performance_metrics': self.performance_metrics.dict(),
            'configuration': self.configuration,
            'health_score': self.get_zone_health_score(),
            'energy_consumption': self.calculate_energy_consumption()
        }