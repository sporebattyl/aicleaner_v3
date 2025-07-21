"""
Unified Resource Management System
Phase 5B: Resource Management

Central resource manager that coordinates memory, CPU, disk, network, and health
monitoring systems with intelligent resource limits and controls.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json

# Import all resource managers
from .memory_manager import get_memory_manager, MemoryManager, MemoryStats
from .cpu_manager import get_cpu_manager, CPUManager, CPUStats
from .disk_manager import get_disk_manager, DiskManager, DiskStats
from .network_manager import get_network_manager, NetworkManager, NetworkStats
from .health_monitor import get_health_monitor, SystemHealthMonitor, SystemHealthMetrics, HealthStatus
from .supervisor_integration import get_supervisor_client, SupervisorAPIClient

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Resource types managed by the system"""
    MEMORY = "memory"
    CPU = "cpu"
    DISK = "disk"
    NETWORK = "network"
    OVERALL = "overall"


@dataclass
class ResourceLimits:
    """Resource limits configuration"""
    # Memory limits (MB)
    memory_limit_mb: Optional[int] = None
    memory_warning_mb: Optional[int] = None
    memory_critical_mb: Optional[int] = None
    
    # CPU limits (percentage)
    cpu_limit_percent: float = 70.0
    cpu_warning_percent: float = 60.0
    cpu_critical_percent: float = 80.0
    
    # Disk limits (percentage)
    disk_limit_percent: float = 85.0
    disk_warning_percent: float = 75.0
    disk_critical_percent: float = 90.0
    
    # Network limits
    max_connections: int = 100
    bandwidth_limit_mbps: Optional[float] = None
    request_rate_limit: int = 60  # requests per minute
    
    # Response time limits (milliseconds)
    response_time_warning_ms: float = 1000.0
    response_time_critical_ms: float = 5000.0
    
    # Error rate limits (percentage)
    error_rate_warning: float = 5.0
    error_rate_critical: float = 15.0


@dataclass
class ResourceStatus:
    """Current resource status across all systems"""
    timestamp: datetime
    memory: Optional[MemoryStats] = None
    cpu: Optional[CPUStats] = None
    disk: Optional[DiskStats] = None
    network: Optional[NetworkStats] = None
    health: Optional[SystemHealthMetrics] = None
    supervisor_info: Optional[Dict[str, Any]] = None
    
    # Calculated status
    overall_status: HealthStatus = HealthStatus.UNKNOWN
    resource_pressure: Dict[ResourceType, bool] = None
    active_limits: List[str] = None
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.resource_pressure is None:
            self.resource_pressure = {}
        if self.active_limits is None:
            self.active_limits = []
        if self.recommendations is None:
            self.recommendations = []


class UnifiedResourceManager:
    """
    Unified resource management system that coordinates all resource managers.
    
    Features:
    - Centralized resource monitoring and control
    - Intelligent resource limit enforcement
    - Cross-resource optimization strategies
    - Automated resource scaling and throttling
    - Integration with Home Assistant Supervisor
    - Resource usage forecasting
    - Emergency resource protection
    """
    
    def __init__(self,
                 limits: Optional[ResourceLimits] = None,
                 monitoring_interval: float = 30.0,
                 auto_enforcement: bool = True,
                 emergency_mode: bool = True):
        """
        Initialize unified resource manager.
        
        Args:
            limits: Resource limits configuration
            monitoring_interval: Monitoring interval in seconds
            auto_enforcement: Enable automatic limit enforcement
            emergency_mode: Enable emergency resource protection
        """
        self.limits = limits or ResourceLimits()
        self.monitoring_interval = monitoring_interval
        self.auto_enforcement = auto_enforcement
        self.emergency_mode = emergency_mode
        
        # Resource managers (lazy initialization)
        self._memory_manager: Optional[MemoryManager] = None
        self._cpu_manager: Optional[CPUManager] = None
        self._disk_manager: Optional[DiskManager] = None
        self._network_manager: Optional[NetworkManager] = None
        self._health_monitor: Optional[SystemHealthMonitor] = None
        self._supervisor_client: Optional[SupervisorAPIClient] = None
        
        # Monitoring
        self._monitoring_enabled = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._enforcement_task: Optional[asyncio.Task] = None
        
        # Status tracking
        self._current_status: Optional[ResourceStatus] = None
        self._status_history: List[ResourceStatus] = []
        self._max_history_size = 200
        
        # Enforcement tracking
        self._active_restrictions: Dict[ResourceType, List[str]] = {}
        self._enforcement_actions: List[Dict[str, Any]] = []
        
        # Callbacks
        self._limit_callbacks: List[Callable] = []
        self._enforcement_callbacks: List[Callable] = []
        self._emergency_callbacks: List[Callable] = []
        
        # Performance tracking
        self._resource_usage_forecast: Dict[ResourceType, List[float]] = {}
        
        logger.info("Unified resource manager initialized")
    
    async def start_monitoring(self) -> None:
        """Start unified resource monitoring."""
        if self._monitoring_enabled:
            logger.warning("Resource monitoring already enabled")
            return
        
        try:
            # Initialize all resource managers
            await self._initialize_managers()
            
            # Start monitoring task
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            # Start enforcement task if enabled
            if self.auto_enforcement:
                self._enforcement_task = asyncio.create_task(self._enforcement_loop())
            
            self._monitoring_enabled = True
            
            logger.info("Unified resource monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start resource monitoring: {e}")
            raise
    
    async def stop_monitoring(self) -> None:
        """Stop unified resource monitoring."""
        if not self._monitoring_enabled:
            return
        
        try:
            # Stop monitoring task
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
                self._monitoring_task = None
            
            # Stop enforcement task
            if self._enforcement_task:
                self._enforcement_task.cancel()
                try:
                    await self._enforcement_task
                except asyncio.CancelledError:
                    pass
                self._enforcement_task = None
            
            self._monitoring_enabled = False
            
            logger.info("Unified resource monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping resource monitoring: {e}")
    
    async def get_current_status(self) -> ResourceStatus:
        """Get current unified resource status."""
        status = ResourceStatus(timestamp=datetime.now())
        
        try:
            # Gather all resource information
            if self._memory_manager:
                status.memory = self._memory_manager.get_current_stats()
            
            if self._cpu_manager:
                status.cpu = self._cpu_manager.get_current_stats()
            
            if self._disk_manager:
                status.disk = self._disk_manager.get_current_stats()
            
            if self._network_manager and self._network_manager._current_stats:
                status.network = self._network_manager._current_stats
            
            if self._health_monitor:
                status.health = self._health_monitor.get_current_health()
            
            if self._supervisor_client:
                try:
                    status.supervisor_info = await self._supervisor_client.get_system_resources()
                except Exception as e:
                    logger.debug(f"Could not get supervisor info: {e}")
            
            # Calculate overall status and pressure
            status.overall_status = self._calculate_overall_status(status)
            status.resource_pressure = self._calculate_resource_pressure(status)
            status.active_limits = self._get_active_limits(status)
            status.recommendations = self._generate_recommendations(status)
            
            self._current_status = status
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting current status: {e}")
            return ResourceStatus(
                timestamp=datetime.now(),
                overall_status=HealthStatus.UNKNOWN,
                active_limits=[f"Status check error: {str(e)}"],
                recommendations=["Review resource monitoring configuration"]
            )
    
    async def enforce_limits(self, force: bool = False) -> List[str]:
        """Enforce resource limits and return actions taken."""
        if not self.auto_enforcement and not force:
            return ["Automatic enforcement disabled"]
        
        actions_taken = []
        current_status = await self.get_current_status()
        
        try:
            # Memory limit enforcement
            if current_status.resource_pressure.get(ResourceType.MEMORY, False):
                if self._memory_manager:
                    if await self._memory_manager.handle_memory_pressure():
                        actions_taken.append("Memory pressure mitigation applied")
            
            # CPU limit enforcement
            if current_status.resource_pressure.get(ResourceType.CPU, False):
                if self._cpu_manager:
                    if await self._cpu_manager.handle_cpu_pressure():
                        actions_taken.append("CPU pressure mitigation applied")
            
            # Disk limit enforcement
            if current_status.resource_pressure.get(ResourceType.DISK, False):
                if self._disk_manager:
                    if await self._disk_manager.handle_disk_pressure():
                        actions_taken.append("Disk pressure mitigation applied")
            
            # Emergency actions if critical
            if current_status.overall_status == HealthStatus.CRITICAL and self.emergency_mode:
                emergency_actions = await self._emergency_resource_protection()
                actions_taken.extend(emergency_actions)
            
            # Record enforcement actions
            if actions_taken:
                self._enforcement_actions.append({
                    "timestamp": datetime.now().isoformat(),
                    "actions": actions_taken,
                    "trigger": "automatic" if self.auto_enforcement else "manual",
                    "status": asdict(current_status)
                })
                
                # Keep only recent enforcement history
                if len(self._enforcement_actions) > 50:
                    self._enforcement_actions = self._enforcement_actions[-50:]
                
                # Trigger enforcement callbacks
                for callback in self._enforcement_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(actions_taken)
                        else:
                            callback(actions_taken)
                    except Exception as e:
                        logger.error(f"Error in enforcement callback: {e}")
            
            logger.info(f"Resource enforcement: {', '.join(actions_taken) if actions_taken else 'No actions needed'}")
            return actions_taken
            
        except Exception as e:
            error_msg = f"Error enforcing limits: {e}"
            logger.error(error_msg)
            return [error_msg]
    
    async def predict_resource_usage(self, hours_ahead: int = 4) -> Dict[ResourceType, float]:
        """Predict future resource usage based on trends."""
        predictions = {}
        
        try:
            # Analyze historical data for trends
            if len(self._status_history) < 10:
                return {"error": "Insufficient historical data for prediction"}
            
            # Simple linear trend analysis
            recent_data = self._status_history[-20:]  # Last 20 measurements
            
            # Memory prediction
            if all(s.memory for s in recent_data):
                memory_values = [s.memory.percent for s in recent_data]
                trend = self._calculate_trend(memory_values)
                current = memory_values[-1]
                predicted = min(100.0, max(0.0, current + (trend * hours_ahead)))
                predictions[ResourceType.MEMORY] = predicted
            
            # CPU prediction
            if all(s.cpu for s in recent_data):
                cpu_values = [s.cpu.process_cpu_percent for s in recent_data]
                trend = self._calculate_trend(cpu_values)
                current = cpu_values[-1]
                predicted = min(100.0, max(0.0, current + (trend * hours_ahead)))
                predictions[ResourceType.CPU] = predicted
            
            # Disk prediction
            if all(s.disk for s in recent_data):
                disk_values = [s.disk.used_percent for s in recent_data]
                trend = self._calculate_trend(disk_values)
                current = disk_values[-1]
                predicted = min(100.0, max(0.0, current + (trend * hours_ahead)))
                predictions[ResourceType.DISK] = predicted
            
        except Exception as e:
            logger.error(f"Error predicting resource usage: {e}")
            predictions["error"] = str(e)
        
        return predictions
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate linear trend from values."""
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x_values = list(range(n))
        
        # Simple linear regression
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        return slope
    
    async def _initialize_managers(self) -> None:
        """Initialize all resource managers."""
        try:
            # Initialize memory manager
            self._memory_manager = get_memory_manager(
                memory_limit_mb=self.limits.memory_limit_mb,
                warning_threshold=self.limits.memory_warning_mb / self.limits.memory_limit_mb if self.limits.memory_limit_mb and self.limits.memory_warning_mb else 0.8,
                critical_threshold=self.limits.memory_critical_mb / self.limits.memory_limit_mb if self.limits.memory_limit_mb and self.limits.memory_critical_mb else 0.95
            )
            if not self._memory_manager._monitoring_enabled:
                await self._memory_manager.start_monitoring()
            
            # Initialize CPU manager
            self._cpu_manager = get_cpu_manager(
                cpu_limit_percent=self.limits.cpu_limit_percent,
                warning_threshold=self.limits.cpu_warning_percent,
                critical_threshold=self.limits.cpu_critical_percent
            )
            if not self._cpu_manager._monitoring_enabled:
                await self._cpu_manager.start_monitoring()
            
            # Initialize disk manager
            self._disk_manager = get_disk_manager(
                disk_limit_percent=self.limits.disk_limit_percent,
                warning_threshold=self.limits.disk_warning_percent,
                critical_threshold=self.limits.disk_critical_percent
            )
            if not self._disk_manager._monitoring_enabled:
                await self._disk_manager.start_monitoring()
            
            # Initialize network manager
            self._network_manager = get_network_manager(
                max_connections=self.limits.max_connections
            )
            if not self._network_manager._monitoring_enabled:
                await self._network_manager.start_monitoring()
            
            # Initialize health monitor
            from .health_monitor import HealthThresholds
            health_thresholds = HealthThresholds(
                memory_warning=self.limits.memory_warning_mb / self.limits.memory_limit_mb if self.limits.memory_limit_mb and self.limits.memory_warning_mb else 80.0,
                memory_critical=self.limits.memory_critical_mb / self.limits.memory_limit_mb if self.limits.memory_limit_mb and self.limits.memory_critical_mb else 95.0,
                cpu_warning=self.limits.cpu_warning_percent,
                cpu_critical=self.limits.cpu_critical_percent,
                disk_warning=self.limits.disk_warning_percent,
                disk_critical=self.limits.disk_critical_percent,
                response_time_warning=self.limits.response_time_warning_ms,
                response_time_critical=self.limits.response_time_critical_ms,
                error_rate_warning=self.limits.error_rate_warning,
                error_rate_critical=self.limits.error_rate_critical
            )
            
            self._health_monitor = get_health_monitor(
                monitoring_interval=self.monitoring_interval,
                auto_remediation=False,  # We handle remediation here
                thresholds=health_thresholds
            )
            if not self._health_monitor._monitoring_enabled:
                await self._health_monitor.start_monitoring()
            
            # Initialize supervisor client
            self._supervisor_client = get_supervisor_client()
            
            logger.info("All resource managers initialized")
            
        except Exception as e:
            logger.error(f"Error initializing resource managers: {e}")
            raise
    
    def _calculate_overall_status(self, status: ResourceStatus) -> HealthStatus:
        """Calculate overall system status."""
        statuses = []
        
        if status.health:
            statuses.append(status.health.overall_status)
        
        # Add individual resource status assessments
        if status.memory:
            if status.memory.percent >= 95:
                statuses.append(HealthStatus.CRITICAL)
            elif status.memory.percent >= 80:
                statuses.append(HealthStatus.WARNING)
            else:
                statuses.append(HealthStatus.HEALTHY)
        
        if status.cpu:
            if status.cpu.process_cpu_percent >= self.limits.cpu_critical_percent:
                statuses.append(HealthStatus.CRITICAL)
            elif status.cpu.process_cpu_percent >= self.limits.cpu_warning_percent:
                statuses.append(HealthStatus.WARNING)
            else:
                statuses.append(HealthStatus.HEALTHY)
        
        if status.disk:
            if status.disk.used_percent >= self.limits.disk_critical_percent:
                statuses.append(HealthStatus.CRITICAL)
            elif status.disk.used_percent >= self.limits.disk_warning_percent:
                statuses.append(HealthStatus.WARNING)
            else:
                statuses.append(HealthStatus.HEALTHY)
        
        # Determine worst status
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        elif HealthStatus.HEALTHY in statuses:
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    def _calculate_resource_pressure(self, status: ResourceStatus) -> Dict[ResourceType, bool]:
        """Calculate resource pressure for each resource type."""
        pressure = {}
        
        # Memory pressure
        if status.memory:
            pressure[ResourceType.MEMORY] = status.memory.percent >= 85.0
        
        # CPU pressure
        if status.cpu:
            pressure[ResourceType.CPU] = status.cpu.process_cpu_percent >= self.limits.cpu_warning_percent
        
        # Disk pressure
        if status.disk:
            pressure[ResourceType.DISK] = status.disk.used_percent >= self.limits.disk_warning_percent
        
        # Network pressure (simplified)
        if status.network:
            pressure[ResourceType.NETWORK] = status.network.connection_count >= self.limits.max_connections * 0.8
        
        # Overall pressure
        pressure[ResourceType.OVERALL] = any(pressure.values())
        
        return pressure
    
    def _get_active_limits(self, status: ResourceStatus) -> List[str]:
        """Get list of currently active limits."""
        active_limits = []
        
        if status.memory and status.memory.percent >= 90:
            active_limits.append("Memory usage exceeding 90%")
        
        if status.cpu and status.cpu.process_cpu_percent >= self.limits.cpu_warning_percent:
            active_limits.append(f"CPU usage exceeding {self.limits.cpu_warning_percent}%")
        
        if status.disk and status.disk.used_percent >= self.limits.disk_warning_percent:
            active_limits.append(f"Disk usage exceeding {self.limits.disk_warning_percent}%")
        
        return active_limits
    
    def _generate_recommendations(self, status: ResourceStatus) -> List[str]:
        """Generate resource optimization recommendations."""
        recommendations = []
        
        # Memory recommendations
        if status.memory and status.memory.percent >= 80:
            recommendations.append("Consider clearing memory caches and reducing memory-intensive operations")
        
        # CPU recommendations
        if status.cpu and status.cpu.process_cpu_percent >= self.limits.cpu_warning_percent:
            recommendations.append("Consider reducing CPU-intensive operations or adding processing delays")
        
        # Disk recommendations
        if status.disk and status.disk.used_percent >= self.limits.disk_warning_percent:
            recommendations.append("Consider cleaning temporary files and logs to free disk space")
        
        # General recommendations based on trends
        predictions = await self.predict_resource_usage(2) if asyncio.iscoroutinefunction(self.predict_resource_usage) else {}
        
        for resource_type, predicted_usage in predictions.items():
            if isinstance(predicted_usage, float) and predicted_usage > 90:
                recommendations.append(f"Predicted high {resource_type.value} usage - consider proactive optimization")
        
        return recommendations
    
    async def _emergency_resource_protection(self) -> List[str]:
        """Emergency resource protection actions."""
        actions = []
        
        try:
            # Force aggressive memory cleanup
            if self._memory_manager:
                if await self._memory_manager.handle_memory_pressure():
                    actions.append("Emergency memory cleanup")
            
            # Force CPU throttling
            if self._cpu_manager:
                if await self._cpu_manager.handle_cpu_pressure():
                    actions.append("Emergency CPU throttling")
            
            # Force disk cleanup
            if self._disk_manager:
                if await self._disk_manager.handle_disk_pressure():
                    actions.append("Emergency disk cleanup")
            
            # Trigger emergency callbacks
            for callback in self._emergency_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(actions)
                    else:
                        callback(actions)
                except Exception as e:
                    logger.error(f"Error in emergency callback: {e}")
            
            if actions:
                logger.warning(f"Emergency resource protection activated: {', '.join(actions)}")
        
        except Exception as e:
            error_msg = f"Error in emergency protection: {e}"
            logger.error(error_msg)
            actions.append(error_msg)
        
        return actions
    
    def register_limit_callback(self, callback: Callable) -> None:
        """Register callback for limit violations."""
        self._limit_callbacks.append(callback)
    
    def register_enforcement_callback(self, callback: Callable) -> None:
        """Register callback for enforcement actions."""
        self._enforcement_callbacks.append(callback)
    
    def register_emergency_callback(self, callback: Callable) -> None:
        """Register callback for emergency situations."""
        self._emergency_callbacks.append(callback)
    
    async def _monitoring_loop(self) -> None:
        """Main unified monitoring loop."""
        while self._monitoring_enabled:
            try:
                # Get current status
                current_status = await self.get_current_status()
                
                # Store in history
                self._status_history.append(current_status)
                if len(self._status_history) > self._max_history_size:
                    self._status_history = self._status_history[-self._max_history_size:]
                
                # Check for limit violations
                if current_status.active_limits:
                    for callback in self._limit_callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(current_status)
                            else:
                                callback(current_status)
                        except Exception as e:
                            logger.error(f"Error in limit callback: {e}")
                
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in unified monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _enforcement_loop(self) -> None:
        """Enforcement loop for automatic limit enforcement."""
        while self._monitoring_enabled:
            try:
                # Run enforcement check
                await self.enforce_limits()
                
                # Wait before next enforcement check
                await asyncio.sleep(self.monitoring_interval * 2)  # Less frequent than monitoring
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in enforcement loop: {e}")
                await asyncio.sleep(60)
    
    def get_resource_report(self) -> Dict[str, Any]:
        """Get comprehensive resource management report."""
        current_status = self._current_status
        
        if not current_status:
            return {"error": "No resource data available"}
        
        return {
            "current_status": asdict(current_status),
            "limits": asdict(self.limits),
            "monitoring_config": {
                "monitoring_enabled": self._monitoring_enabled,
                "monitoring_interval": self.monitoring_interval,
                "auto_enforcement": self.auto_enforcement,
                "emergency_mode": self.emergency_mode
            },
            "enforcement_history": self._enforcement_actions[-10:],  # Last 10 actions
            "predictions": await self.predict_resource_usage() if asyncio.iscoroutinefunction(self.predict_resource_usage) else {},
            "active_restrictions": self._active_restrictions,
            "system_health": {
                "overall_status": current_status.overall_status.value,
                "resource_pressure": {rt.value: pressure for rt, pressure in current_status.resource_pressure.items()},
                "recommendations": current_status.recommendations
            }
        }


# Global unified resource manager instance
_unified_manager: Optional[UnifiedResourceManager] = None


def get_unified_resource_manager(
    limits: Optional[ResourceLimits] = None,
    monitoring_interval: float = 30.0,
    auto_enforcement: bool = True
) -> UnifiedResourceManager:
    """
    Get global unified resource manager instance.
    
    Args:
        limits: Resource limits configuration
        monitoring_interval: Monitoring interval in seconds
        auto_enforcement: Enable automatic limit enforcement
        
    Returns:
        UnifiedResourceManager instance
    """
    global _unified_manager
    
    if _unified_manager is None:
        _unified_manager = UnifiedResourceManager(
            limits=limits,
            monitoring_interval=monitoring_interval,
            auto_enforcement=auto_enforcement
        )
    
    return _unified_manager


async def start_unified_resource_monitoring() -> None:
    """Start unified resource monitoring."""
    manager = get_unified_resource_manager()
    await manager.start_monitoring()


async def stop_unified_resource_monitoring() -> None:
    """Stop unified resource monitoring."""
    global _unified_manager
    if _unified_manager:
        await _unified_manager.stop_monitoring()


async def get_resource_status() -> ResourceStatus:
    """Get current unified resource status."""
    manager = get_unified_resource_manager()
    return await manager.get_current_status()


async def enforce_resource_limits(force: bool = False) -> List[str]:
    """Enforce resource limits manually."""
    manager = get_unified_resource_manager()
    return await manager.enforce_limits(force)


async def predict_resource_usage(hours_ahead: int = 4) -> Dict[ResourceType, float]:
    """Predict future resource usage."""
    manager = get_unified_resource_manager()
    return await manager.predict_resource_usage(hours_ahead)