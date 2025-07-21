"""
Resource Monitor - Real-time system resource monitoring
Implements 5-10 second polling with smart alerting
"""

import asyncio
import logging
import psutil
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ResourceAlert:
    timestamp: datetime
    level: AlertLevel
    metric: str
    value: float
    threshold: float
    message: str


class ResourceMonitor:
    """
    Real-time resource monitoring with smart alerting
    Polls critical metrics every 5-10 seconds with threshold-based alerting
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Monitoring configuration
        self.poll_interval = config.get("poll_interval", 8.0)  # 8 seconds default
        self.alert_consecutive_threshold = config.get("alert_consecutive_threshold", 3)
        
        # Resource thresholds
        self.thresholds = {
            "cpu_warning": config.get("cpu_warning_threshold", 80.0),
            "cpu_critical": config.get("cpu_critical_threshold", 95.0),
            "memory_warning": config.get("memory_warning_threshold", 80.0),
            "memory_critical": config.get("memory_critical_threshold", 95.0),
            "disk_warning": config.get("disk_warning_threshold", 85.0),
            "disk_critical": config.get("disk_critical_threshold", 95.0),
            "response_time_warning": config.get("response_time_warning", 15.0),
            "response_time_critical": config.get("response_time_critical", 30.0)
        }
        
        # Monitoring state
        self._monitoring = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._current_metrics: Dict[str, Any] = {}
        self._metric_history: List[Dict[str, Any]] = []
        self._consecutive_alerts: Dict[str, int] = {}
        self._alert_callbacks: List[Callable[[ResourceAlert], None]] = []
        
        # Performance tracking
        self._response_times: List[float] = []
        self._max_history_size = config.get("max_history_size", 720)  # 1 hour at 5s intervals

    async def start(self) -> None:
        """Start resource monitoring"""
        if self._monitoring:
            self.logger.warning("Resource monitoring already started")
            return
        
        self.logger.info(f"Starting resource monitoring (poll interval: {self.poll_interval}s)")
        self._monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def stop(self) -> None:
        """Stop resource monitoring"""
        if not self._monitoring:
            return
        
        self.logger.info("Stopping resource monitoring")
        self._monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

    def add_alert_callback(self, callback: Callable[[ResourceAlert], None]) -> None:
        """Add callback for resource alerts"""
        self._alert_callbacks.append(callback)

    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get the most recent resource metrics"""
        if not self._current_metrics:
            # Get metrics once if monitoring hasn't started
            await self._collect_metrics()
        
        return self._current_metrics.copy()

    async def get_metrics_history(self, duration_minutes: int = 60) -> List[Dict[str, Any]]:
        """Get metrics history for the specified duration"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        
        return [
            metric for metric in self._metric_history
            if metric.get("timestamp", datetime.min) > cutoff_time
        ]

    async def record_response_time(self, response_time: float) -> None:
        """Record a response time for performance tracking"""
        self._response_times.append(response_time)
        
        # Keep only recent response times
        max_response_times = 100
        if len(self._response_times) > max_response_times:
            self._response_times = self._response_times[-max_response_times:]
        
        # Check response time thresholds
        await self._check_response_time_alerts(response_time)

    async def get_system_info(self) -> Dict[str, Any]:
        """Get static system information"""
        try:
            return {
                "cpu_count": psutil.cpu_count(),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "memory_total": psutil.virtual_memory().total,
                "disk_total": psutil.disk_usage('/').total,
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                "platform": psutil.disk_usage('/').total  # Simplified
            }
        except Exception as e:
            self.logger.error(f"Failed to get system info: {e}")
            return {}

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        self.logger.debug("Resource monitoring loop started")
        
        while self._monitoring:
            try:
                # Collect current metrics
                await self._collect_metrics()
                
                # Check for alerts
                await self._check_alerts()
                
                # Maintain history size
                self._maintain_history()
                
                # Wait for next poll interval
                await asyncio.sleep(self.poll_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.poll_interval)
        
        self.logger.debug("Resource monitoring loop stopped")

    async def _collect_metrics(self) -> None:
        """Collect current system metrics"""
        try:
            timestamp = datetime.now()
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Network metrics
            network = psutil.net_io_counters()
            
            # Process-specific metrics (current process)
            try:
                current_process = psutil.Process()
                process_memory = current_process.memory_info()
                process_cpu = current_process.cpu_percent()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                process_memory = None
                process_cpu = 0.0
            
            # Response time metrics
            avg_response_time = (
                sum(self._response_times) / len(self._response_times)
                if self._response_times else 0.0
            )
            
            # Compile metrics
            metrics = {
                "timestamp": timestamp,
                "cpu": {
                    "usage_percent": cpu_percent,
                    "usage_per_core": cpu_per_core,
                    "load_average": getattr(psutil, 'getloadavg', lambda: [0, 0, 0])()
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "usage_percent": memory.percent,
                    "swap_total": swap.total,
                    "swap_used": swap.used,
                    "swap_percent": swap.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "usage_percent": disk.used / disk.total * 100,
                    "read_bytes": disk_io.read_bytes if disk_io else 0,
                    "write_bytes": disk_io.write_bytes if disk_io else 0
                },
                "network": {
                    "bytes_sent": network.bytes_sent if network else 0,
                    "bytes_recv": network.bytes_recv if network else 0,
                    "packets_sent": network.packets_sent if network else 0,
                    "packets_recv": network.packets_recv if network else 0
                },
                "process": {
                    "memory_rss": process_memory.rss if process_memory else 0,
                    "memory_vms": process_memory.vms if process_memory else 0,
                    "cpu_percent": process_cpu
                },
                "performance": {
                    "avg_response_time": avg_response_time,
                    "response_time_samples": len(self._response_times)
                }
            }
            
            # Update current metrics
            self._current_metrics = metrics
            
            # Add to history
            self._metric_history.append(metrics.copy())
            
        except Exception as e:
            self.logger.error(f"Failed to collect metrics: {e}")

    async def _check_alerts(self) -> None:
        """Check current metrics against thresholds and generate alerts"""
        if not self._current_metrics:
            return
        
        # CPU alerts
        cpu_usage = self._current_metrics["cpu"]["usage_percent"]
        await self._check_metric_alert("cpu", cpu_usage, "cpu_warning", "cpu_critical")
        
        # Memory alerts
        memory_usage = self._current_metrics["memory"]["usage_percent"]
        await self._check_metric_alert("memory", memory_usage, "memory_warning", "memory_critical")
        
        # Disk alerts
        disk_usage = self._current_metrics["disk"]["usage_percent"]
        await self._check_metric_alert("disk", disk_usage, "disk_warning", "disk_critical")

    async def _check_metric_alert(self, metric_name: str, value: float, 
                                 warning_key: str, critical_key: str) -> None:
        """Check a specific metric against warning and critical thresholds"""
        warning_threshold = self.thresholds[warning_key]
        critical_threshold = self.thresholds[critical_key]
        
        alert_key = f"{metric_name}_alert"
        
        # Check critical threshold
        if value >= critical_threshold:
            self._consecutive_alerts[alert_key] = self._consecutive_alerts.get(alert_key, 0) + 1
            
            if self._consecutive_alerts[alert_key] >= self.alert_consecutive_threshold:
                await self._trigger_alert(
                    AlertLevel.CRITICAL,
                    metric_name,
                    value,
                    critical_threshold,
                    f"{metric_name.upper()} usage critically high: {value:.1f}%"
                )
        
        # Check warning threshold
        elif value >= warning_threshold:
            self._consecutive_alerts[alert_key] = self._consecutive_alerts.get(alert_key, 0) + 1
            
            if self._consecutive_alerts[alert_key] >= self.alert_consecutive_threshold:
                await self._trigger_alert(
                    AlertLevel.WARNING,
                    metric_name,
                    value,
                    warning_threshold,
                    f"{metric_name.upper()} usage high: {value:.1f}%"
                )
        
        # Reset consecutive alerts if metric is below thresholds
        else:
            self._consecutive_alerts[alert_key] = 0

    async def _check_response_time_alerts(self, response_time: float) -> None:
        """Check response time against thresholds"""
        warning_threshold = self.thresholds["response_time_warning"]
        critical_threshold = self.thresholds["response_time_critical"]
        
        if response_time >= critical_threshold:
            await self._trigger_alert(
                AlertLevel.CRITICAL,
                "response_time",
                response_time,
                critical_threshold,
                f"Response time critically slow: {response_time:.1f}s"
            )
        elif response_time >= warning_threshold:
            await self._trigger_alert(
                AlertLevel.WARNING,
                "response_time",
                response_time,
                warning_threshold,
                f"Response time slow: {response_time:.1f}s"
            )

    async def _trigger_alert(self, level: AlertLevel, metric: str, value: float, 
                           threshold: float, message: str) -> None:
        """Trigger an alert and notify callbacks"""
        alert = ResourceAlert(
            timestamp=datetime.now(),
            level=level,
            metric=metric,
            value=value,
            threshold=threshold,
            message=message
        )
        
        self.logger.warning(f"Resource alert: {alert.message}")
        
        # Notify callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")

    def _maintain_history(self) -> None:
        """Maintain metrics history size"""
        if len(self._metric_history) > self._max_history_size:
            # Remove oldest entries
            excess = len(self._metric_history) - self._max_history_size
            self._metric_history = self._metric_history[excess:]