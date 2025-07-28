"""
AICleaner v3 Configurable Monitoring System
Smart escalation monitoring implementing "Intelligent Simplicity"

Features:
- Basic Level (Default): Simple status sensors, essential health indicators
- Detailed Level (Auto-Escalation): Performance metrics, resource tracking
- Expert Level (Optional): Real-time dashboards, advanced debugging
- Smart escalation during issues
- Configurable alerting and notifications
"""

import asyncio
import logging
import json
import psutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import aiohttp


class MonitoringLevel(Enum):
    """Monitoring complexity levels"""
    BASIC = "basic"
    DETAILED = "detailed"
    EXPERT = "expert"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics collected"""
    PERFORMANCE = "performance"
    RESOURCE = "resource"
    HEALTH = "health"
    SECURITY = "security"
    USAGE = "usage"


@dataclass
class MonitoringAlert:
    """Monitoring alert"""
    alert_id: str
    severity: AlertSeverity
    metric_type: MetricType
    title: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False
    escalated: bool = False


@dataclass
class MetricData:
    """Individual metric data point"""
    metric_name: str
    metric_type: MetricType
    value: Any
    unit: str
    timestamp: datetime
    tags: Dict[str, str]


@dataclass
class MonitoringStatus:
    """Overall monitoring system status"""
    current_level: MonitoringLevel
    active_alerts: int
    critical_alerts: int
    system_health_score: float
    uptime_seconds: float
    last_escalation: Optional[datetime]
    auto_escalation_enabled: bool


class ConfigurableMonitor:
    """
    Configurable monitoring system with smart escalation
    
    Monitoring Levels:
    - Basic: Simple HA sensors, essential health checks
    - Detailed: Performance metrics, resource usage, auto-escalation
    - Expert: Real-time dashboards, advanced debugging, manual activation
    
    Smart Escalation:
    - Automatically escalates from Basic to Detailed during issues
    - Provides performance insights when needed
    - Returns to Basic level when issues resolve
    """
    
    def __init__(self, config_path: Path, config: Dict[str, Any] = None):
        self.config_path = Path("/data")  # Data directory for persistent storage
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Monitoring state
        self.current_level = MonitoringLevel.BASIC
        self.start_time = datetime.now()
        self.active_alerts: List[MonitoringAlert] = []
        self.metrics_history: List[MetricData] = []
        
        # Configuration
        self.auto_escalation_enabled = self.config.get("auto_escalation_enabled", True)
        self.escalation_threshold = self.config.get("escalation_threshold", 3)  # Number of warnings to trigger escalation
        self.metrics_retention_hours = self.config.get("metrics_retention_hours", 24)
        self.collection_interval_seconds = self.config.get("collection_interval_seconds", 60)
        
        # Thresholds
        self.thresholds = {
            "cpu_percent": {"warning": 70, "critical": 90},
            "memory_percent": {"warning": 80, "critical": 95},
            "disk_percent": {"warning": 85, "critical": 95},
            "response_time_ms": {"warning": 5000, "critical": 10000},
            "error_rate_percent": {"warning": 5, "critical": 15}
        }
        
        # Callbacks for external integrations
        self.alert_callbacks: List[Callable] = []
        self.metric_callbacks: List[Callable] = []
        
        # Monitoring tasks
        self._monitoring_tasks: List[asyncio.Task] = []
        self._is_running = False
    
    async def initialize(self) -> None:
        """Initialize the monitoring system"""
        try:
            self.logger.info("Initializing configurable monitoring system")
            
            # Load configuration
            await self._load_monitoring_config()
            
            # Start monitoring tasks based on current level
            await self._start_monitoring_tasks()
            
            self._is_running = True
            self.logger.info(f"Monitoring system started at {self.current_level.value} level")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring system: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the monitoring system"""
        self.logger.info("Shutting down monitoring system")
        
        self._is_running = False
        
        # Cancel monitoring tasks
        for task in self._monitoring_tasks:
            if not task.done():
                task.cancel()
        
        await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        self._monitoring_tasks.clear()
    
    # Level Management
    
    async def set_monitoring_level(self, level: MonitoringLevel, 
                                  manual_override: bool = False) -> bool:
        """
        Set monitoring level
        
        Args:
            level: Target monitoring level
            manual_override: If True, disables auto-escalation until next restart
        
        Returns:
            bool: Success status
        """
        try:
            if level == self.current_level:
                return True
            
            self.logger.info(f"Changing monitoring level from {self.current_level.value} to {level.value}")
            
            # Stop current monitoring tasks
            await self._stop_monitoring_tasks()
            
            # Update level
            old_level = self.current_level
            self.current_level = level
            
            # Disable auto-escalation if manual override
            if manual_override:
                self.auto_escalation_enabled = False
                self.logger.info("Auto-escalation disabled due to manual override")
            
            # Start new monitoring tasks
            await self._start_monitoring_tasks()
            
            # Log level change
            await self._create_alert(
                AlertSeverity.INFO,
                MetricType.HEALTH,
                "Monitoring Level Changed",
                f"Monitoring level changed from {old_level.value} to {level.value}",
                {"old_level": old_level.value, "new_level": level.value, "manual": manual_override}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set monitoring level: {e}")
            return False
    
    async def auto_escalate(self, trigger_reason: str) -> bool:
        """
        Automatically escalate monitoring level due to issues
        
        Args:
            trigger_reason: Reason for escalation
        
        Returns:
            bool: True if escalated
        """
        if not self.auto_escalation_enabled:
            return False
        
        # Only escalate from Basic to Detailed automatically
        if self.current_level != MonitoringLevel.BASIC:
            return False
        
        try:
            self.logger.warning(f"Auto-escalating monitoring due to: {trigger_reason}")
            
            success = await self.set_monitoring_level(MonitoringLevel.DETAILED)
            
            if success:
                await self._create_alert(
                    AlertSeverity.WARNING,
                    MetricType.HEALTH,
                    "Monitoring Auto-Escalated",
                    f"Monitoring automatically escalated to detailed level: {trigger_reason}",
                    {"trigger": trigger_reason, "previous_level": "basic"}
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Auto-escalation failed: {e}")
            return False
    
    async def auto_de_escalate(self) -> bool:
        """
        Automatically de-escalate monitoring when issues resolve
        
        Returns:
            bool: True if de-escalated
        """
        if not self.auto_escalation_enabled or self.current_level != MonitoringLevel.DETAILED:
            return False
        
        # Check if we should de-escalate (no critical alerts for 30 minutes)
        critical_alerts = [alert for alert in self.active_alerts 
                          if alert.severity == AlertSeverity.CRITICAL and not alert.resolved]
        
        if critical_alerts:
            return False
        
        # Check for recent warnings
        recent_warnings = [
            alert for alert in self.active_alerts
            if alert.severity in [AlertSeverity.WARNING, AlertSeverity.ERROR] 
            and not alert.resolved
            and alert.timestamp > datetime.now() - timedelta(minutes=30)
        ]
        
        if len(recent_warnings) > 2:
            return False
        
        try:
            self.logger.info("Auto de-escalating monitoring - issues have been resolved")
            
            success = await self.set_monitoring_level(MonitoringLevel.BASIC)
            
            if success:
                await self._create_alert(
                    AlertSeverity.INFO,
                    MetricType.HEALTH,
                    "Monitoring Auto De-escalated",
                    "Monitoring returned to basic level - issues resolved",
                    {"previous_level": "detailed"}
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Auto de-escalation failed: {e}")
            return False
    
    # Metrics Collection
    
    async def collect_basic_metrics(self) -> List[MetricData]:
        """Collect basic health metrics"""
        metrics = []
        timestamp = datetime.now()
        
        try:
            # System uptime
            uptime = (datetime.now() - self.start_time).total_seconds()
            metrics.append(MetricData(
                metric_name="system_uptime",
                metric_type=MetricType.HEALTH,
                value=uptime,
                unit="seconds",
                timestamp=timestamp,
                tags={"level": "basic"}
            ))
            
            # Basic CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.append(MetricData(
                metric_name="cpu_usage",
                metric_type=MetricType.RESOURCE,
                value=cpu_percent,
                unit="percent",
                timestamp=timestamp,
                tags={"level": "basic"}
            ))
            
            # Basic memory usage
            memory = psutil.virtual_memory()
            metrics.append(MetricData(
                metric_name="memory_usage",
                metric_type=MetricType.RESOURCE,
                value=memory.percent,
                unit="percent",
                timestamp=timestamp,
                tags={"level": "basic"}
            ))
            
            # Service health (simplified check)
            service_healthy = await self._check_service_health()
            metrics.append(MetricData(
                metric_name="service_health",
                metric_type=MetricType.HEALTH,
                value=1 if service_healthy else 0,
                unit="boolean",
                timestamp=timestamp,
                tags={"level": "basic"}
            ))
            
        except Exception as e:
            self.logger.error(f"Failed to collect basic metrics: {e}")
        
        return metrics
    
    async def collect_detailed_metrics(self) -> List[MetricData]:
        """Collect detailed performance metrics"""
        metrics = await self.collect_basic_metrics()  # Include basic metrics
        timestamp = datetime.now()
        
        try:
            # Detailed CPU metrics
            cpu_times = psutil.cpu_times_percent(interval=1)
            metrics.extend([
                MetricData("cpu_user", MetricType.PERFORMANCE, cpu_times.user, "percent", timestamp, {"level": "detailed"}),
                MetricData("cpu_system", MetricType.PERFORMANCE, cpu_times.system, "percent", timestamp, {"level": "detailed"}),
                MetricData("cpu_iowait", MetricType.PERFORMANCE, getattr(cpu_times, 'iowait', 0), "percent", timestamp, {"level": "detailed"})
            ])
            
            # Memory details
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            metrics.extend([
                MetricData("memory_available", MetricType.RESOURCE, memory.available, "bytes", timestamp, {"level": "detailed"}),
                MetricData("memory_used", MetricType.RESOURCE, memory.used, "bytes", timestamp, {"level": "detailed"}),
                MetricData("swap_usage", MetricType.RESOURCE, swap.percent, "percent", timestamp, {"level": "detailed"})
            ])
            
            # Disk I/O
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            metrics.extend([
                MetricData("disk_usage", MetricType.RESOURCE, (disk_usage.used / disk_usage.total) * 100, "percent", timestamp, {"level": "detailed"}),
                MetricData("disk_read_bytes", MetricType.PERFORMANCE, disk_io.read_bytes if disk_io else 0, "bytes", timestamp, {"level": "detailed"}),
                MetricData("disk_write_bytes", MetricType.PERFORMANCE, disk_io.write_bytes if disk_io else 0, "bytes", timestamp, {"level": "detailed"})
            ])
            
            # Network I/O
            network_io = psutil.net_io_counters()
            metrics.extend([
                MetricData("network_bytes_sent", MetricType.PERFORMANCE, network_io.bytes_sent if network_io else 0, "bytes", timestamp, {"level": "detailed"}),
                MetricData("network_bytes_recv", MetricType.PERFORMANCE, network_io.bytes_recv if network_io else 0, "bytes", timestamp, {"level": "detailed"})
            ])
            
            # Process information
            process_count = len(psutil.pids())
            metrics.append(MetricData(
                metric_name="process_count",
                metric_type=MetricType.RESOURCE,
                value=process_count,
                unit="count",
                timestamp=timestamp,
                tags={"level": "detailed"}
            ))
            
            # API response time (if service is available)
            response_time = await self._measure_api_response_time()
            if response_time is not None:
                metrics.append(MetricData(
                    metric_name="api_response_time",
                    metric_type=MetricType.PERFORMANCE,
                    value=response_time,
                    unit="milliseconds",
                    timestamp=timestamp,
                    tags={"level": "detailed"}
                ))
            
        except Exception as e:
            self.logger.error(f"Failed to collect detailed metrics: {e}")
        
        return metrics
    
    async def collect_expert_metrics(self) -> List[MetricData]:
        """Collect expert-level debugging metrics"""
        metrics = await self.collect_detailed_metrics()  # Include detailed metrics
        timestamp = datetime.now()
        
        try:
            # Thread and connection counts
            metrics.extend([
                MetricData("active_threads", MetricType.RESOURCE, 0, "count", timestamp, {"level": "expert"}),  # Would implement actual counting
                MetricData("open_connections", MetricType.RESOURCE, 0, "count", timestamp, {"level": "expert"})  # Would implement actual counting
            ])
            
            # Garbage collection metrics (Python-specific)
            import gc
            metrics.append(MetricData(
                metric_name="gc_objects",
                metric_type=MetricType.RESOURCE,
                value=len(gc.get_objects()),
                unit="count",
                timestamp=timestamp,
                tags={"level": "expert"}
            ))
            
            # Custom application metrics would go here
            # (AI provider response times, model loading times, etc.)
            
        except Exception as e:
            self.logger.error(f"Failed to collect expert metrics: {e}")
        
        return metrics
    
    # Alert Management
    
    async def _create_alert(self, severity: AlertSeverity, metric_type: MetricType,
                           title: str, message: str, details: Dict[str, Any]) -> str:
        """Create a new monitoring alert"""
        import secrets
        
        alert_id = secrets.token_hex(8)
        alert = MonitoringAlert(
            alert_id=alert_id,
            severity=severity,
            metric_type=metric_type,
            title=title,
            message=message,
            details=details,
            timestamp=datetime.now()
        )
        
        self.active_alerts.append(alert)
        
        # Trigger callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")
        
        # Log alert
        log_level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL
        }[severity]
        
        self.logger.log(log_level, f"ALERT [{severity.value.upper()}] {title}: {message}")
        
        # Check for auto-escalation
        if severity in [AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
            await self._check_auto_escalation()
        
        return alert_id
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                self.logger.info(f"Alert acknowledged: {alert.title}")
                return True
        return False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                self.logger.info(f"Alert resolved: {alert.title}")
                return True
        return False
    
    async def get_active_alerts(self) -> List[MonitoringAlert]:
        """Get all active (unresolved) alerts"""
        return [alert for alert in self.active_alerts if not alert.resolved]
    
    # Status and Reporting
    
    async def get_monitoring_status(self) -> MonitoringStatus:
        """Get current monitoring system status"""
        active_alerts = await self.get_active_alerts()
        critical_alerts = [alert for alert in active_alerts if alert.severity == AlertSeverity.CRITICAL]
        
        # Calculate system health score (0-100)
        health_score = await self._calculate_health_score()
        
        # Find last escalation
        last_escalation = None
        for alert in reversed(self.active_alerts):
            if "escalat" in alert.message.lower():
                last_escalation = alert.timestamp
                break
        
        return MonitoringStatus(
            current_level=self.current_level,
            active_alerts=len(active_alerts),
            critical_alerts=len(critical_alerts),
            system_health_score=health_score,
            uptime_seconds=(datetime.now() - self.start_time).total_seconds(),
            last_escalation=last_escalation,
            auto_escalation_enabled=self.auto_escalation_enabled
        )
    
    async def get_metrics_for_ha(self) -> Dict[str, Any]:
        """Get metrics formatted for Home Assistant sensors"""
        try:
            status = await self.get_monitoring_status()
            latest_metrics = self.metrics_history[-20:] if self.metrics_history else []
            
            # Basic sensors (always available)
            ha_sensors = {
                "aicleaner_monitoring_level": self.current_level.value,
                "aicleaner_system_health": status.system_health_score,
                "aicleaner_active_alerts": status.active_alerts,
                "aicleaner_uptime": status.uptime_seconds,
                "aicleaner_service_status": "online" if await self._check_service_health() else "offline"
            }
            
            # Add detailed metrics if monitoring level permits
            if self.current_level in [MonitoringLevel.DETAILED, MonitoringLevel.EXPERT]:
                for metric in latest_metrics:
                    if metric.metric_name in ["cpu_usage", "memory_usage", "api_response_time"]:
                        sensor_name = f"aicleaner_{metric.metric_name}"
                        ha_sensors[sensor_name] = metric.value
            
            return ha_sensors
            
        except Exception as e:
            self.logger.error(f"Failed to get HA metrics: {e}")
            return {"aicleaner_service_status": "error"}
    
    # Helper Methods
    
    async def _start_monitoring_tasks(self) -> None:
        """Start monitoring tasks based on current level"""
        if self.current_level == MonitoringLevel.BASIC:
            task = asyncio.create_task(self._basic_monitoring_loop())
            self._monitoring_tasks.append(task)
        
        elif self.current_level == MonitoringLevel.DETAILED:
            task1 = asyncio.create_task(self._basic_monitoring_loop())
            task2 = asyncio.create_task(self._detailed_monitoring_loop())
            self._monitoring_tasks.extend([task1, task2])
        
        elif self.current_level == MonitoringLevel.EXPERT:
            task1 = asyncio.create_task(self._basic_monitoring_loop())
            task2 = asyncio.create_task(self._detailed_monitoring_loop())
            task3 = asyncio.create_task(self._expert_monitoring_loop())
            self._monitoring_tasks.extend([task1, task2, task3])
        
        # Always run alert management
        alert_task = asyncio.create_task(self._alert_management_loop())
        self._monitoring_tasks.append(alert_task)
    
    async def _stop_monitoring_tasks(self) -> None:
        """Stop all monitoring tasks"""
        for task in self._monitoring_tasks:
            if not task.done():
                task.cancel()
        
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        
        self._monitoring_tasks.clear()
    
    async def _basic_monitoring_loop(self) -> None:
        """Basic monitoring loop"""
        while self._is_running:
            try:
                metrics = await self.collect_basic_metrics()
                await self._process_metrics(metrics)
                
                await asyncio.sleep(self.collection_interval_seconds * 2)  # Slower collection for basic
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Basic monitoring loop error: {e}")
                await asyncio.sleep(60)
    
    async def _detailed_monitoring_loop(self) -> None:
        """Detailed monitoring loop"""
        while self._is_running:
            try:
                metrics = await self.collect_detailed_metrics()
                await self._process_metrics(metrics)
                
                await asyncio.sleep(self.collection_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Detailed monitoring loop error: {e}")
                await asyncio.sleep(30)
    
    async def _expert_monitoring_loop(self) -> None:
        """Expert monitoring loop"""
        while self._is_running:
            try:
                metrics = await self.collect_expert_metrics()
                await self._process_metrics(metrics)
                
                await asyncio.sleep(self.collection_interval_seconds // 2)  # Faster collection for expert
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Expert monitoring loop error: {e}")
                await asyncio.sleep(15)
    
    async def _alert_management_loop(self) -> None:
        """Alert management and cleanup loop"""
        while self._is_running:
            try:
                # Check for auto de-escalation
                await self.auto_de_escalate()
                
                # Cleanup old alerts (keep last 100)
                if len(self.active_alerts) > 100:
                    self.active_alerts = self.active_alerts[-100:]
                
                # Cleanup old metrics
                cutoff_time = datetime.now() - timedelta(hours=self.metrics_retention_hours)
                self.metrics_history = [
                    metric for metric in self.metrics_history 
                    if metric.timestamp > cutoff_time
                ]
                
                await asyncio.sleep(300)  # Run every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Alert management loop error: {e}")
                await asyncio.sleep(60)
    
    async def _process_metrics(self, metrics: List[MetricData]) -> None:
        """Process collected metrics and check thresholds"""
        for metric in metrics:
            # Store metric
            self.metrics_history.append(metric)
            
            # Check thresholds
            await self._check_metric_thresholds(metric)
            
            # Trigger callbacks
            for callback in self.metric_callbacks:
                try:
                    await callback(metric)
                except Exception as e:
                    self.logger.error(f"Metric callback failed: {e}")
    
    async def _check_metric_thresholds(self, metric: MetricData) -> None:
        """Check if metric exceeds thresholds and create alerts if needed"""
        if metric.metric_name not in self.thresholds:
            return
        
        thresholds = self.thresholds[metric.metric_name]
        value = float(metric.value)
        
        if value >= thresholds.get("critical", 100):
            await self._create_alert(
                AlertSeverity.CRITICAL,
                metric.metric_type,
                f"Critical {metric.metric_name}",
                f"{metric.metric_name} is critically high: {value}{metric.unit}",
                {"metric": metric.metric_name, "value": value, "threshold": thresholds["critical"]}
            )
        elif value >= thresholds.get("warning", 80):
            await self._create_alert(
                AlertSeverity.WARNING,
                metric.metric_type,
                f"Warning {metric.metric_name}",
                f"{metric.metric_name} is elevated: {value}{metric.unit}",
                {"metric": metric.metric_name, "value": value, "threshold": thresholds["warning"]}
            )
    
    async def _check_auto_escalation(self) -> None:
        """Check if conditions warrant auto-escalation"""
        if not self.auto_escalation_enabled or self.current_level != MonitoringLevel.BASIC:
            return
        
        # Count recent warnings/errors
        recent_time = datetime.now() - timedelta(minutes=10)
        recent_alerts = [
            alert for alert in self.active_alerts
            if alert.timestamp > recent_time and alert.severity in [AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL]
            and not alert.resolved
        ]
        
        if len(recent_alerts) >= self.escalation_threshold:
            await self.auto_escalate(f"{len(recent_alerts)} alerts in 10 minutes")
    
    async def _calculate_health_score(self) -> float:
        """Calculate overall system health score (0-100)"""
        try:
            score = 100.0
            
            # Penalize for active alerts
            active_alerts = await self.get_active_alerts()
            
            for alert in active_alerts:
                if alert.severity == AlertSeverity.CRITICAL:
                    score -= 20
                elif alert.severity == AlertSeverity.ERROR:
                    score -= 10
                elif alert.severity == AlertSeverity.WARNING:
                    score -= 5
            
            # Check recent metrics
            if self.metrics_history:
                recent_metrics = [m for m in self.metrics_history if m.timestamp > datetime.now() - timedelta(minutes=5)]
                
                for metric in recent_metrics:
                    if metric.metric_name == "cpu_usage" and float(metric.value) > 90:
                        score -= 10
                    elif metric.metric_name == "memory_usage" and float(metric.value) > 95:
                        score -= 15
            
            return max(0.0, min(100.0, score))
            
        except Exception as e:
            self.logger.error(f"Failed to calculate health score: {e}")
            return 50.0  # Neutral score on error
    
    async def _check_service_health(self) -> bool:
        """Check if the main service is healthy"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8099/health", timeout=5) as response:
                    return response.status == 200
        except:
            return False
    
    async def _measure_api_response_time(self) -> Optional[float]:
        """Measure API response time in milliseconds"""
        try:
            import time
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8099/health", timeout=10) as response:
                    if response.status == 200:
                        end_time = time.time()
                        return (end_time - start_time) * 1000  # Convert to milliseconds
            
            return None
            
        except Exception:
            return None
    
    async def _load_monitoring_config(self) -> None:
        """Load monitoring configuration from file"""
        config_file = Path("/config/monitoring_config.yaml")  # Monitoring config in /config
        
        if config_file.exists():
            try:
                import yaml
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f) or {}
                
                # Update configuration
                self.auto_escalation_enabled = config.get("auto_escalation_enabled", self.auto_escalation_enabled)
                self.escalation_threshold = config.get("escalation_threshold", self.escalation_threshold)
                self.collection_interval_seconds = config.get("collection_interval_seconds", self.collection_interval_seconds)
                
                # Update thresholds
                if "thresholds" in config:
                    self.thresholds.update(config["thresholds"])
                
                self.logger.info("Monitoring configuration loaded")
                
            except Exception as e:
                self.logger.error(f"Failed to load monitoring config: {e}")
    
    # External Integration
    
    def add_alert_callback(self, callback: Callable[[MonitoringAlert], None]) -> None:
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)
    
    def add_metric_callback(self, callback: Callable[[MetricData], None]) -> None:
        """Add callback for metric processing"""
        self.metric_callbacks.append(callback)