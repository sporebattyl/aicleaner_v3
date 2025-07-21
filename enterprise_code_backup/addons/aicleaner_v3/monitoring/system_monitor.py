"""
System Monitoring for AICleaner v3
Provides real-time monitoring and alerting capabilities
"""

import time
import psutil
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import deque, defaultdict
import json

from utils.unified_logger import get_logger, log_performance, log_security_event

logger = get_logger("aicleaner.monitoring")

@dataclass
class MetricThreshold:
    """Threshold configuration for metrics."""
    warning: float
    critical: float
    name: str
    description: str = ""

@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    process_count: int = 0
    load_average_1m: float = 0.0

@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    metric_name: str
    threshold: float
    condition: str  # 'greater_than', 'less_than', 'equals'
    duration_seconds: int = 60  # How long condition must persist
    cooldown_seconds: int = 300  # Minimum time between alerts
    enabled: bool = True
    last_triggered: Optional[datetime] = None

class SystemMonitor:
    """Real-time system monitoring for Home Assistant addon."""
    
    def __init__(self, 
                 collection_interval: int = 30,
                 retention_hours: int = 24,
                 enable_alerts: bool = True):
        """
        Initialize system monitor.
        
        Args:
            collection_interval: How often to collect metrics (seconds)
            retention_hours: How long to keep metrics in memory
            enable_alerts: Whether to enable alerting
        """
        self.collection_interval = collection_interval
        self.retention_hours = retention_hours
        self.enable_alerts = enable_alerts
        
        # Metrics storage (in-memory for simplicity)
        max_samples = int((retention_hours * 3600) / collection_interval)
        self.metrics_history: deque = deque(maxlen=max_samples)
        
        # Alert tracking
        self.alert_rules: List[AlertRule] = []
        self.alert_callbacks: List[Callable] = []
        
        # Performance tracking
        self.performance_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Component health tracking
        self.component_health: Dict[str, Dict] = {}
        
        # Default thresholds for Home Assistant addon
        self.thresholds = {
            "cpu_percent": MetricThreshold(70.0, 90.0, "CPU Usage", "CPU utilization percentage"),
            "memory_percent": MetricThreshold(80.0, 95.0, "Memory Usage", "Memory utilization percentage"),
            "disk_usage_percent": MetricThreshold(85.0, 95.0, "Disk Usage", "Disk space utilization percentage"),
            "load_average_1m": MetricThreshold(2.0, 4.0, "Load Average", "System load average (1 minute)")
        }
        
        # Setup default alert rules
        self._setup_default_alerts()
        
        # Monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
    
    def _setup_default_alerts(self):
        """Setup default alert rules for Home Assistant addon."""
        self.alert_rules = [
            AlertRule(
                name="High CPU Usage",
                metric_name="cpu_percent",
                threshold=85.0,
                condition="greater_than",
                duration_seconds=120,
                cooldown_seconds=300
            ),
            AlertRule(
                name="High Memory Usage", 
                metric_name="memory_percent",
                threshold=90.0,
                condition="greater_than",
                duration_seconds=60,
                cooldown_seconds=300
            ),
            AlertRule(
                name="Low Disk Space",
                metric_name="disk_usage_percent",
                threshold=90.0,
                condition="greater_than",
                duration_seconds=300,
                cooldown_seconds=600
            ),
            AlertRule(
                name="High Load Average",
                metric_name="load_average_1m",
                threshold=3.0,
                condition="greater_than",
                duration_seconds=180,
                cooldown_seconds=300
            )
        ]
    
    def collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            
            # Network metrics (if available)
            network_bytes_sent = 0
            network_bytes_recv = 0
            try:
                net_io = psutil.net_io_counters()
                network_bytes_sent = net_io.bytes_sent
                network_bytes_recv = net_io.bytes_recv
            except:
                pass  # Network metrics not available
            
            # Process count
            process_count = len(psutil.pids())
            
            # Load average (Linux/Unix only)
            load_average_1m = 0.0
            try:
                load_average_1m = psutil.getloadavg()[0]
            except (AttributeError, OSError):
                # Not available on all systems
                pass
            
            return SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb,
                network_bytes_sent=network_bytes_sent,
                network_bytes_recv=network_bytes_recv,
                process_count=process_count,
                load_average_1m=load_average_1m
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            # Return empty metrics on error
            return SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0
            )
    
    def check_alerts(self, metrics: SystemMetrics):
        """Check metrics against alert rules."""
        if not self.enable_alerts:
            return
        
        current_time = datetime.utcnow()
        
        for rule in self.alert_rules:
            if not rule.enabled:
                continue
            
            # Check cooldown
            if (rule.last_triggered and 
                (current_time - rule.last_triggered).total_seconds() < rule.cooldown_seconds):
                continue
            
            # Get metric value
            metric_value = getattr(metrics, rule.metric_name, None)
            if metric_value is None:
                continue
            
            # Check condition
            condition_met = False
            if rule.condition == "greater_than" and metric_value > rule.threshold:
                condition_met = True
            elif rule.condition == "less_than" and metric_value < rule.threshold:
                condition_met = True
            elif rule.condition == "equals" and metric_value == rule.threshold:
                condition_met = True
            
            if condition_met:
                # For simplicity, trigger alert immediately instead of tracking duration
                # In a more complex system, you'd track how long the condition persists
                self._trigger_alert(rule, metric_value, metrics)
                rule.last_triggered = current_time
    
    def _trigger_alert(self, rule: AlertRule, value: float, metrics: SystemMetrics):
        """Trigger an alert."""
        alert_data = {
            "alert_name": rule.name,
            "metric_name": rule.metric_name,
            "threshold": rule.threshold,
            "current_value": value,
            "condition": rule.condition,
            "timestamp": metrics.timestamp.isoformat(),
            "severity": "critical" if value > rule.threshold * 1.1 else "warning"
        }
        
        # Log security event for critical alerts
        if alert_data["severity"] == "critical":
            log_security_event(
                event_type="system_alert",
                severity="high",
                details=alert_data
            )
        else:
            logger.warning(f"System Alert: {rule.name} - {rule.metric_name}={value:.1f} (threshold={rule.threshold})")
        
        # Call registered alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def add_alert_callback(self, callback: Callable[[Dict], None]):
        """Add a callback function for alert notifications."""
        self.alert_callbacks.append(callback)
    
    def record_performance(self, operation: str, duration: float, **kwargs):
        """Record performance metrics for an operation."""
        self.performance_metrics[operation].append({
            "timestamp": datetime.utcnow(),
            "duration": duration,
            "metadata": kwargs
        })
        
        # Log performance if it's notably slow
        avg_duration = self.get_average_performance(operation)
        if avg_duration and duration > avg_duration * 2:
            log_performance(operation, duration, slow_operation=True, **kwargs)
    
    def get_average_performance(self, operation: str) -> Optional[float]:
        """Get average performance for an operation."""
        metrics = self.performance_metrics.get(operation)
        if not metrics:
            return None
        
        durations = [m["duration"] for m in metrics]
        return sum(durations) / len(durations)
    
    def update_component_health(self, component: str, status: str, details: Optional[Dict] = None):
        """Update health status for a component."""
        self.component_health[component] = {
            "status": status,  # healthy, warning, error
            "last_updated": datetime.utcnow(),
            "details": details or {}
        }
        
        if status in ["warning", "error"]:
            severity = "medium" if status == "warning" else "high"
            log_security_event(
                event_type="component_health",
                severity=severity,
                details={
                    "component": component,
                    "status": status,
                    "details": details
                }
            )
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Get the most recent metrics."""
        if self.metrics_history:
            return self.metrics_history[-1]
        return None
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get summary statistics for the specified time period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {}
        
        # Calculate averages
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        avg_disk = sum(m.disk_usage_percent for m in recent_metrics) / len(recent_metrics)
        
        # Get max values
        max_cpu = max(m.cpu_percent for m in recent_metrics)
        max_memory = max(m.memory_percent for m in recent_metrics)
        max_disk = max(m.disk_usage_percent for m in recent_metrics)
        
        return {
            "period_hours": hours,
            "sample_count": len(recent_metrics),
            "averages": {
                "cpu_percent": round(avg_cpu, 1),
                "memory_percent": round(avg_memory, 1),
                "disk_usage_percent": round(avg_disk, 1)
            },
            "maximums": {
                "cpu_percent": round(max_cpu, 1),
                "memory_percent": round(max_memory, 1),
                "disk_usage_percent": round(max_disk, 1)
            },
            "component_health": dict(self.component_health),
            "recent_alerts": len([r for r in self.alert_rules if r.last_triggered and 
                                (datetime.utcnow() - r.last_triggered).total_seconds() < 3600])
        }
    
    async def start_monitoring(self):
        """Start the monitoring loop."""
        if self._running:
            return
        
        self._running = True
        logger.info("Starting system monitoring")
        
        while self._running:
            try:
                # Collect metrics
                metrics = self.collect_metrics()
                self.metrics_history.append(metrics)
                
                # Check alerts
                self.check_alerts(metrics)
                
                # Log metrics periodically (every 5 minutes)
                if len(self.metrics_history) % 10 == 0:  # Assuming 30s interval
                    logger.info(f"System metrics: CPU={metrics.cpu_percent:.1f}%, "
                              f"Memory={metrics.memory_percent:.1f}%, "
                              f"Disk={metrics.disk_usage_percent:.1f}%")
                
                # Wait for next collection
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.collection_interval)
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
        logger.info("Stopped system monitoring")
    
    def get_health_check(self) -> Dict[str, Any]:
        """Get health check information for API endpoints."""
        current_metrics = self.get_current_metrics()
        
        # Determine overall health status
        health_status = "healthy"
        issues = []
        
        if current_metrics:
            for metric_name, threshold in self.thresholds.items():
                value = getattr(current_metrics, metric_name, 0)
                if value > threshold.critical:
                    health_status = "critical"
                    issues.append(f"{threshold.name}: {value:.1f}% (critical)")
                elif value > threshold.warning and health_status == "healthy":
                    health_status = "warning"
                    issues.append(f"{threshold.name}: {value:.1f}% (warning)")
        
        # Check component health
        unhealthy_components = [name for name, health in self.component_health.items() 
                              if health["status"] != "healthy"]
        
        if unhealthy_components:
            if health_status == "healthy":
                health_status = "warning"
            issues.extend([f"Component {comp} is {self.component_health[comp]['status']}" 
                          for comp in unhealthy_components])
        
        return {
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": time.time() - psutil.boot_time() if hasattr(psutil, 'boot_time') else None,
            "issues": issues,
            "metrics": {
                "cpu_percent": current_metrics.cpu_percent if current_metrics else 0,
                "memory_percent": current_metrics.memory_percent if current_metrics else 0,
                "disk_usage_percent": current_metrics.disk_usage_percent if current_metrics else 0
            } if current_metrics else {},
            "components": dict(self.component_health)
        }

# Global monitor instance
_global_monitor: Optional[SystemMonitor] = None

def get_system_monitor() -> SystemMonitor:
    """Get the global system monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = SystemMonitor()
    return _global_monitor

def configure_monitoring(collection_interval: int = 30,
                        retention_hours: int = 24,
                        enable_alerts: bool = True) -> SystemMonitor:
    """Configure global system monitoring."""
    global _global_monitor
    _global_monitor = SystemMonitor(
        collection_interval=collection_interval,
        retention_hours=retention_hours,
        enable_alerts=enable_alerts
    )
    return _global_monitor

# Home Assistant addon specific configuration
def configure_ha_addon_monitoring() -> SystemMonitor:
    """Configure monitoring for Home Assistant addon environment."""
    monitor = configure_monitoring(
        collection_interval=60,  # Longer interval for addon
        retention_hours=12,      # Less retention in addon
        enable_alerts=True
    )
    
    # Add HA-specific alert callback
    def ha_alert_callback(alert_data):
        """Handle alerts in HA addon context."""
        logger.error(f"HA Addon Alert: {alert_data['alert_name']} - "
                    f"{alert_data['metric_name']}={alert_data['current_value']:.1f}")
    
    monitor.add_alert_callback(ha_alert_callback)
    return monitor