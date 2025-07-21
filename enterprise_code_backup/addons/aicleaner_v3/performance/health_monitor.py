"""
System Health Monitoring
Phase 5B: Resource Management

Comprehensive system health monitoring that integrates memory, CPU, disk, and 
network monitoring into a unified health assessment system.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json

# Import resource managers
from .memory_manager import get_memory_manager, MemoryStats
from .cpu_manager import get_cpu_manager, CPUStats
from .disk_manager import get_disk_manager, DiskStats

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """System health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class SystemHealthMetrics:
    """Comprehensive system health metrics"""
    timestamp: datetime
    overall_status: HealthStatus
    health_score: float  # 0-100, where 100 is perfect health
    
    # Resource status
    memory_status: HealthStatus
    cpu_status: HealthStatus
    disk_status: HealthStatus
    
    # Resource metrics
    memory_stats: Optional[MemoryStats] = None
    cpu_stats: Optional[CPUStats] = None
    disk_stats: Optional[DiskStats] = None
    
    # Performance indicators
    response_time_ms: float = 0.0
    uptime_seconds: float = 0.0
    error_rate: float = 0.0
    
    # System load
    load_average: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    
    # Alerts and recommendations
    active_alerts: List[str] = None
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.active_alerts is None:
            self.active_alerts = []
        if self.recommendations is None:
            self.recommendations = []


@dataclass
class HealthThresholds:
    """Health monitoring thresholds"""
    memory_warning: float = 80.0  # Memory usage %
    memory_critical: float = 95.0
    cpu_warning: float = 60.0     # CPU usage %
    cpu_critical: float = 80.0
    disk_warning: float = 75.0    # Disk usage %
    disk_critical: float = 90.0
    response_time_warning: float = 1000.0  # Response time ms
    response_time_critical: float = 5000.0
    error_rate_warning: float = 5.0       # Error rate %
    error_rate_critical: float = 15.0


class SystemHealthMonitor:
    """
    Comprehensive system health monitoring system.
    
    Features:
    - Unified health status across all resources
    - Health scoring algorithm
    - Predictive health analysis
    - Automated health reporting
    - Integration with all resource managers
    - Health-based recommendations
    - Alert management
    """
    
    def __init__(self,
                 monitoring_interval: float = 30.0,
                 health_history_size: int = 200,
                 auto_remediation: bool = True,
                 thresholds: Optional[HealthThresholds] = None):
        """
        Initialize system health monitor.
        
        Args:
            monitoring_interval: Health check interval in seconds
            health_history_size: Number of health records to keep
            auto_remediation: Enable automatic remediation actions
            thresholds: Custom health thresholds
        """
        self.monitoring_interval = monitoring_interval
        self.health_history_size = health_history_size
        self.auto_remediation = auto_remediation
        self.thresholds = thresholds or HealthThresholds()
        
        # Health monitoring
        self._monitoring_enabled = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._start_time = time.time()
        
        # Health data
        self._health_history: List[SystemHealthMetrics] = []
        self._current_health: Optional[SystemHealthMetrics] = None
        self._last_health_check = datetime.now()
        
        # Alert management
        self._active_alerts: Dict[str, datetime] = {}
        self._alert_cooldown = 300  # 5 minutes between same alerts
        
        # Performance tracking
        self._response_times: List[float] = []
        self._error_count = 0
        self._total_requests = 0
        
        # Callbacks
        self._health_callbacks: List[Callable] = []
        self._alert_callbacks: List[Callable] = []
        self._remediation_callbacks: List[Callable] = []
        
        # Resource managers (lazy initialization)
        self._memory_manager = None
        self._cpu_manager = None
        self._disk_manager = None
        
        logger.info("System health monitor initialized")
    
    async def start_monitoring(self) -> None:
        """Start system health monitoring."""
        if self._monitoring_enabled:
            logger.warning("Health monitoring already enabled")
            return
        
        try:
            # Initialize resource managers
            await self._initialize_resource_managers()
            
            # Start monitoring task
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self._monitoring_enabled = True
            
            logger.info("System health monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start health monitoring: {e}")
            raise
    
    async def stop_monitoring(self) -> None:
        """Stop system health monitoring."""
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
            
            self._monitoring_enabled = False
            
            logger.info("System health monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping health monitoring: {e}")
    
    async def check_system_health(self) -> SystemHealthMetrics:
        """Perform comprehensive system health check."""
        start_time = time.perf_counter()
        
        try:
            # Initialize metrics
            health_metrics = SystemHealthMetrics(
                timestamp=datetime.now(),
                overall_status=HealthStatus.UNKNOWN,
                health_score=0.0,
                memory_status=HealthStatus.UNKNOWN,
                cpu_status=HealthStatus.UNKNOWN,
                disk_status=HealthStatus.UNKNOWN,
                uptime_seconds=time.time() - self._start_time
            )
            
            # Get resource statistics
            if self._memory_manager:
                health_metrics.memory_stats = self._memory_manager.get_current_stats()
                health_metrics.memory_status = self._assess_memory_health(health_metrics.memory_stats)
            
            if self._cpu_manager:
                health_metrics.cpu_stats = self._cpu_manager.get_current_stats()
                health_metrics.cpu_status = self._assess_cpu_health(health_metrics.cpu_stats)
            
            if self._disk_manager:
                health_metrics.disk_stats = self._disk_manager.get_current_stats()
                health_metrics.disk_status = self._assess_disk_health(health_metrics.disk_stats)
            
            # Calculate response time
            response_time = (time.perf_counter() - start_time) * 1000
            health_metrics.response_time_ms = response_time
            
            # Calculate error rate
            if self._total_requests > 0:
                health_metrics.error_rate = (self._error_count / self._total_requests) * 100
            
            # Get system load
            try:
                import os
                if hasattr(os, 'getloadavg'):
                    health_metrics.load_average = os.getloadavg()
            except (AttributeError, OSError):
                pass
            
            # Calculate overall health
            health_metrics.overall_status, health_metrics.health_score = self._calculate_overall_health(health_metrics)
            
            # Generate alerts and recommendations
            health_metrics.active_alerts = self._generate_alerts(health_metrics)
            health_metrics.recommendations = self._generate_recommendations(health_metrics)
            
            # Store in history
            self._health_history.append(health_metrics)
            if len(self._health_history) > self.health_history_size:
                self._health_history = self._health_history[-self.health_history_size:]
            
            self._current_health = health_metrics
            self._last_health_check = datetime.now()
            
            return health_metrics
            
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return SystemHealthMetrics(
                timestamp=datetime.now(),
                overall_status=HealthStatus.UNKNOWN,
                health_score=0.0,
                memory_status=HealthStatus.UNKNOWN,
                cpu_status=HealthStatus.UNKNOWN,
                disk_status=HealthStatus.UNKNOWN,
                uptime_seconds=time.time() - self._start_time,
                active_alerts=[f"Health check error: {str(e)}"],
                recommendations=["Review system health monitoring configuration"]
            )
    
    def record_request_performance(self, response_time_ms: float, success: bool = True) -> None:
        """Record request performance metrics."""
        self._response_times.append(response_time_ms)
        self._total_requests += 1
        
        if not success:
            self._error_count += 1
        
        # Keep only recent response times
        if len(self._response_times) > 1000:
            self._response_times = self._response_times[-1000:]
    
    def get_health_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get health trends over specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self._health_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {"error": "Insufficient data for trend analysis"}
        
        # Calculate trends
        trends = {
            "time_period_hours": hours,
            "data_points": len(recent_metrics),
            "health_score": {
                "current": recent_metrics[-1].health_score if recent_metrics else 0,
                "average": sum(m.health_score for m in recent_metrics) / len(recent_metrics),
                "min": min(m.health_score for m in recent_metrics),
                "max": max(m.health_score for m in recent_metrics)
            },
            "status_distribution": {},
            "alert_frequency": {},
            "performance_trends": {}
        }
        
        # Status distribution
        status_counts = {}
        for metric in recent_metrics:
            status = metric.overall_status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        total_points = len(recent_metrics)
        trends["status_distribution"] = {
            status: (count / total_points) * 100
            for status, count in status_counts.items()
        }
        
        # Alert frequency
        all_alerts = []
        for metric in recent_metrics:
            all_alerts.extend(metric.active_alerts)
        
        alert_counts = {}
        for alert in all_alerts:
            alert_counts[alert] = alert_counts.get(alert, 0) + 1
        
        trends["alert_frequency"] = dict(sorted(alert_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        
        # Performance trends
        if recent_metrics:
            response_times = [m.response_time_ms for m in recent_metrics if m.response_time_ms > 0]
            error_rates = [m.error_rate for m in recent_metrics if m.error_rate >= 0]
            
            if response_times:
                trends["performance_trends"]["response_time"] = {
                    "average": sum(response_times) / len(response_times),
                    "min": min(response_times),
                    "max": max(response_times)
                }
            
            if error_rates:
                trends["performance_trends"]["error_rate"] = {
                    "average": sum(error_rates) / len(error_rates),
                    "min": min(error_rates),
                    "max": max(error_rates)
                }
        
        return trends
    
    async def _initialize_resource_managers(self) -> None:
        """Initialize resource managers for health monitoring."""
        try:
            # Initialize memory manager
            self._memory_manager = get_memory_manager()
            if not self._memory_manager._monitoring_enabled:
                await self._memory_manager.start_monitoring()
            
            # Initialize CPU manager
            self._cpu_manager = get_cpu_manager()
            if not self._cpu_manager._monitoring_enabled:
                await self._cpu_manager.start_monitoring()
            
            # Initialize disk manager
            self._disk_manager = get_disk_manager()
            if not self._disk_manager._monitoring_enabled:
                await self._disk_manager.start_monitoring()
            
            logger.info("Resource managers initialized for health monitoring")
            
        except Exception as e:
            logger.error(f"Error initializing resource managers: {e}")
    
    def _assess_memory_health(self, memory_stats: MemoryStats) -> HealthStatus:
        """Assess memory health status."""
        if not memory_stats:
            return HealthStatus.UNKNOWN
        
        usage_percent = memory_stats.percent
        
        if usage_percent >= self.thresholds.memory_critical:
            return HealthStatus.CRITICAL
        elif usage_percent >= self.thresholds.memory_warning:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def _assess_cpu_health(self, cpu_stats: CPUStats) -> HealthStatus:
        """Assess CPU health status."""
        if not cpu_stats:
            return HealthStatus.UNKNOWN
        
        usage_percent = cpu_stats.process_cpu_percent
        
        if usage_percent >= self.thresholds.cpu_critical:
            return HealthStatus.CRITICAL
        elif usage_percent >= self.thresholds.cpu_warning:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def _assess_disk_health(self, disk_stats: DiskStats) -> HealthStatus:
        """Assess disk health status."""
        if not disk_stats:
            return HealthStatus.UNKNOWN
        
        usage_percent = disk_stats.used_percent
        
        if usage_percent >= self.thresholds.disk_critical:
            return HealthStatus.CRITICAL
        elif usage_percent >= self.thresholds.disk_warning:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def _calculate_overall_health(self, metrics: SystemHealthMetrics) -> Tuple[HealthStatus, float]:
        """Calculate overall health status and score."""
        health_scores = []
        critical_count = 0
        warning_count = 0
        
        # Memory health scoring
        if metrics.memory_status != HealthStatus.UNKNOWN:
            if metrics.memory_status == HealthStatus.HEALTHY:
                health_scores.append(100)
            elif metrics.memory_status == HealthStatus.WARNING:
                health_scores.append(60)
                warning_count += 1
            else:  # CRITICAL
                health_scores.append(20)
                critical_count += 1
        
        # CPU health scoring
        if metrics.cpu_status != HealthStatus.UNKNOWN:
            if metrics.cpu_status == HealthStatus.HEALTHY:
                health_scores.append(100)
            elif metrics.cpu_status == HealthStatus.WARNING:
                health_scores.append(60)
                warning_count += 1
            else:  # CRITICAL
                health_scores.append(20)
                critical_count += 1
        
        # Disk health scoring
        if metrics.disk_status != HealthStatus.UNKNOWN:
            if metrics.disk_status == HealthStatus.HEALTHY:
                health_scores.append(100)
            elif metrics.disk_status == HealthStatus.WARNING:
                health_scores.append(60)
                warning_count += 1
            else:  # CRITICAL
                health_scores.append(20)
                critical_count += 1
        
        # Performance health scoring
        if metrics.response_time_ms > 0:
            if metrics.response_time_ms < self.thresholds.response_time_warning:
                health_scores.append(100)
            elif metrics.response_time_ms < self.thresholds.response_time_critical:
                health_scores.append(60)
                warning_count += 1
            else:
                health_scores.append(20)
                critical_count += 1
        
        # Error rate health scoring
        if metrics.error_rate >= 0:
            if metrics.error_rate < self.thresholds.error_rate_warning:
                health_scores.append(100)
            elif metrics.error_rate < self.thresholds.error_rate_critical:
                health_scores.append(60)
                warning_count += 1
            else:
                health_scores.append(20)
                critical_count += 1
        
        # Calculate overall score
        if health_scores:
            overall_score = sum(health_scores) / len(health_scores)
        else:
            overall_score = 0
        
        # Determine overall status
        if critical_count > 0:
            overall_status = HealthStatus.CRITICAL
        elif warning_count > 0:
            overall_status = HealthStatus.WARNING
        elif health_scores:
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN
        
        return overall_status, overall_score
    
    def _generate_alerts(self, metrics: SystemHealthMetrics) -> List[str]:
        """Generate active alerts based on health metrics."""
        alerts = []
        current_time = datetime.now()
        
        # Memory alerts
        if metrics.memory_status == HealthStatus.CRITICAL:
            alert = "Critical memory usage detected"
            if self._should_send_alert(alert, current_time):
                alerts.append(alert)
        elif metrics.memory_status == HealthStatus.WARNING:
            alert = "High memory usage warning"
            if self._should_send_alert(alert, current_time):
                alerts.append(alert)
        
        # CPU alerts
        if metrics.cpu_status == HealthStatus.CRITICAL:
            alert = "Critical CPU usage detected"
            if self._should_send_alert(alert, current_time):
                alerts.append(alert)
        elif metrics.cpu_status == HealthStatus.WARNING:
            alert = "High CPU usage warning"
            if self._should_send_alert(alert, current_time):
                alerts.append(alert)
        
        # Disk alerts
        if metrics.disk_status == HealthStatus.CRITICAL:
            alert = "Critical disk space usage detected"
            if self._should_send_alert(alert, current_time):
                alerts.append(alert)
        elif metrics.disk_status == HealthStatus.WARNING:
            alert = "Low disk space warning"
            if self._should_send_alert(alert, current_time):
                alerts.append(alert)
        
        # Performance alerts
        if metrics.response_time_ms > self.thresholds.response_time_critical:
            alert = "Critical response time detected"
            if self._should_send_alert(alert, current_time):
                alerts.append(alert)
        elif metrics.response_time_ms > self.thresholds.response_time_warning:
            alert = "Slow response time warning"
            if self._should_send_alert(alert, current_time):
                alerts.append(alert)
        
        # Error rate alerts
        if metrics.error_rate > self.thresholds.error_rate_critical:
            alert = "Critical error rate detected"
            if self._should_send_alert(alert, current_time):
                alerts.append(alert)
        elif metrics.error_rate > self.thresholds.error_rate_warning:
            alert = "High error rate warning"
            if self._should_send_alert(alert, current_time):
                alerts.append(alert)
        
        return alerts
    
    def _generate_recommendations(self, metrics: SystemHealthMetrics) -> List[str]:
        """Generate health improvement recommendations."""
        recommendations = []
        
        # Memory recommendations
        if metrics.memory_status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
            recommendations.append("Consider clearing caches or reducing memory-intensive operations")
            if metrics.memory_stats and len(metrics.memory_stats.largest_objects) > 0:
                recommendations.append("Review largest memory consumers for optimization opportunities")
        
        # CPU recommendations
        if metrics.cpu_status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
            recommendations.append("Consider reducing CPU-intensive operations or increasing processing capacity")
            if metrics.cpu_stats and metrics.cpu_stats.load_average[0] > metrics.cpu_stats.cpu_count:
                recommendations.append("System load is high - consider load balancing or task scheduling")
        
        # Disk recommendations
        if metrics.disk_status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
            recommendations.append("Free up disk space by cleaning temporary files and caches")
            if metrics.disk_stats and metrics.disk_stats.free_gb < 1.0:
                recommendations.append("Critical: Less than 1GB free space - immediate cleanup required")
        
        # Performance recommendations
        if metrics.response_time_ms > self.thresholds.response_time_warning:
            recommendations.append("Optimize application performance to reduce response times")
        
        if metrics.error_rate > self.thresholds.error_rate_warning:
            recommendations.append("Review error logs and implement error handling improvements")
        
        # General recommendations based on trends
        if len(self._health_history) > 10:
            recent_scores = [m.health_score for m in self._health_history[-10:]]
            if len(recent_scores) > 5:
                trend = (sum(recent_scores[-5:]) / 5) - (sum(recent_scores[:5]) / 5)
                if trend < -10:
                    recommendations.append("Health score is declining - review system performance")
        
        return recommendations
    
    def _should_send_alert(self, alert: str, current_time: datetime) -> bool:
        """Check if alert should be sent (considering cooldown)."""
        last_sent = self._active_alerts.get(alert)
        
        if last_sent is None:
            self._active_alerts[alert] = current_time
            return True
        
        time_since_last = (current_time - last_sent).total_seconds()
        if time_since_last >= self._alert_cooldown:
            self._active_alerts[alert] = current_time
            return True
        
        return False
    
    def register_health_callback(self, callback: Callable) -> None:
        """Register callback for health status changes."""
        self._health_callbacks.append(callback)
    
    def register_alert_callback(self, callback: Callable) -> None:
        """Register callback for new alerts."""
        self._alert_callbacks.append(callback)
    
    def register_remediation_callback(self, callback: Callable) -> None:
        """Register callback for remediation actions."""
        self._remediation_callbacks.append(callback)
    
    async def _monitoring_loop(self) -> None:
        """Main health monitoring loop."""
        while self._monitoring_enabled:
            try:
                # Perform health check
                health_metrics = await self.check_system_health()
                
                # Trigger health callbacks
                for callback in self._health_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(health_metrics)
                        else:
                            callback(health_metrics)
                    except Exception as e:
                        logger.error(f"Error in health callback: {e}")
                
                # Trigger alert callbacks for new alerts
                if health_metrics.active_alerts:
                    for callback in self._alert_callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(health_metrics.active_alerts)
                            else:
                                callback(health_metrics.active_alerts)
                        except Exception as e:
                            logger.error(f"Error in alert callback: {e}")
                
                # Auto-remediation
                if self.auto_remediation and health_metrics.overall_status == HealthStatus.CRITICAL:
                    await self._perform_auto_remediation(health_metrics)
                
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _perform_auto_remediation(self, metrics: SystemHealthMetrics) -> None:
        """Perform automatic remediation actions."""
        try:
            actions_taken = []
            
            # Memory remediation
            if metrics.memory_status == HealthStatus.CRITICAL and self._memory_manager:
                if await self._memory_manager.handle_memory_pressure():
                    actions_taken.append("Memory pressure remediation")
            
            # CPU remediation
            if metrics.cpu_status == HealthStatus.CRITICAL and self._cpu_manager:
                if await self._cpu_manager.handle_cpu_pressure():
                    actions_taken.append("CPU pressure remediation")
            
            # Disk remediation
            if metrics.disk_status == HealthStatus.CRITICAL and self._disk_manager:
                if await self._disk_manager.handle_disk_pressure():
                    actions_taken.append("Disk pressure remediation")
            
            if actions_taken:
                logger.info(f"Auto-remediation actions taken: {', '.join(actions_taken)}")
                
                # Trigger remediation callbacks
                for callback in self._remediation_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(actions_taken)
                        else:
                            callback(actions_taken)
                    except Exception as e:
                        logger.error(f"Error in remediation callback: {e}")
        
        except Exception as e:
            logger.error(f"Error in auto-remediation: {e}")
    
    def get_current_health(self) -> Optional[SystemHealthMetrics]:
        """Get current health status."""
        return self._current_health
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report."""
        current_health = self._current_health
        
        if not current_health:
            return {"error": "No health data available"}
        
        return {
            "current_health": asdict(current_health),
            "monitoring_config": {
                "monitoring_enabled": self._monitoring_enabled,
                "monitoring_interval": self.monitoring_interval,
                "auto_remediation": self.auto_remediation,
                "thresholds": asdict(self.thresholds)
            },
            "trends": self.get_health_trends(24),
            "statistics": {
                "uptime_hours": (time.time() - self._start_time) / 3600,
                "health_checks_performed": len(self._health_history),
                "total_requests": self._total_requests,
                "total_errors": self._error_count,
                "active_alerts": len(self._active_alerts)
            }
        }


# Global health monitor instance
_health_monitor: Optional[SystemHealthMonitor] = None


def get_health_monitor(
    monitoring_interval: float = 30.0,
    auto_remediation: bool = True,
    thresholds: Optional[HealthThresholds] = None
) -> SystemHealthMonitor:
    """
    Get global health monitor instance.
    
    Args:
        monitoring_interval: Health check interval in seconds
        auto_remediation: Enable automatic remediation
        thresholds: Custom health thresholds
        
    Returns:
        SystemHealthMonitor instance
    """
    global _health_monitor
    
    if _health_monitor is None:
        _health_monitor = SystemHealthMonitor(
            monitoring_interval=monitoring_interval,
            auto_remediation=auto_remediation,
            thresholds=thresholds
        )
    
    return _health_monitor


async def start_health_monitoring() -> None:
    """Start global health monitoring."""
    monitor = get_health_monitor()
    await monitor.start_monitoring()


async def stop_health_monitoring() -> None:
    """Stop global health monitoring."""
    global _health_monitor
    if _health_monitor:
        await _health_monitor.stop_monitoring()


async def check_system_health() -> SystemHealthMetrics:
    """Check current system health."""
    monitor = get_health_monitor()
    return await monitor.check_system_health()


def get_current_health_status() -> Optional[SystemHealthMetrics]:
    """Get current health status."""
    monitor = get_health_monitor()
    return monitor.get_current_health()


def record_request_performance(response_time_ms: float, success: bool = True) -> None:
    """Record request performance for health monitoring."""
    monitor = get_health_monitor()
    monitor.record_request_performance(response_time_ms, success)