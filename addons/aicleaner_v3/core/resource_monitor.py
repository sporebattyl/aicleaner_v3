"""
Resource Monitor for AICleaner Phase 3C.2
Provides dedicated resource tracking with real-time metrics, trend analysis, and alerts.
"""

import asyncio
import logging
import time
import psutil
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque, defaultdict
import threading

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class ResourceType(Enum):
    """Types of system resources to monitor."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"
    PROCESS = "process"


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class ResourceMetrics:
    """Comprehensive resource metrics."""
    timestamp: str
    cpu_percent: float
    cpu_cores: int
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    memory_total_mb: float
    disk_usage_percent: float
    disk_used_gb: float
    disk_free_gb: float
    disk_io_read_mb_per_sec: float
    disk_io_write_mb_per_sec: float
    network_sent_mb_per_sec: float
    network_recv_mb_per_sec: float
    gpu_available: bool = False
    gpu_memory_used_mb: float = 0.0
    gpu_memory_total_mb: float = 0.0
    gpu_utilization_percent: float = 0.0
    process_count: int = 0
    load_average: List[float] = None


@dataclass
class ResourceAlert:
    """Resource alert information."""
    alert_id: str
    timestamp: str
    resource_type: ResourceType
    alert_level: AlertLevel
    message: str
    current_value: float
    threshold_value: float
    metadata: Dict[str, Any] = None


class ResourceMonitor:
    """
    Advanced resource monitoring system for AICleaner.
    
    Features:
    - Real-time resource tracking
    - Historical trend analysis
    - Configurable alerts and thresholds
    - GPU monitoring support
    - Process-specific monitoring
    - Performance baseline establishment
    """
    
    def __init__(self, config: Dict[str, Any], data_path: str = "/data/resource_monitor"):
        """
        Initialize Resource Monitor.
        
        Args:
            config: Configuration dictionary
            data_path: Path to store monitoring data
        """
        self.logger = logging.getLogger(__name__)
        self.config = config.get("performance_optimization", {})
        self.data_path = data_path
        
        # Ensure data directory exists
        os.makedirs(data_path, exist_ok=True)
        
        # Monitoring configuration
        self.monitoring_config = self.config.get("monitoring", {})
        self.alert_thresholds = self.monitoring_config.get("alert_thresholds", {
            "memory_usage_percent": 90,
            "cpu_usage_percent": 95,
            "disk_usage_percent": 95,
            "response_time_seconds": 60,
            "error_rate_percent": 5
        })
        
        # Data storage
        self.metrics_history = deque(maxlen=10000)  # Keep last 10k samples
        self.alerts_history = deque(maxlen=1000)    # Keep last 1k alerts
        self.performance_baselines = {}
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_interval = 10  # seconds
        self.alert_callbacks: List[Callable] = []
        
        # Background tasks
        self._monitoring_task = None
        self._cleanup_task = None
        
        # GPU detection
        self._gpu_available = self._detect_gpu()
        
        # Previous metrics for rate calculations
        self._previous_disk_io = None
        self._previous_network_io = None
        self._previous_timestamp = None
        
        # Thread safety
        self._lock = threading.RLock()
        
        self.logger.info("Resource Monitor initialized")

    def _detect_gpu(self) -> bool:
        """Detect if GPU monitoring is available."""
        try:
            if TORCH_AVAILABLE:
                return torch.cuda.is_available()
            return False
        except Exception:
            return False

    async def start_monitoring(self, interval: int = 10):
        """
        Start resource monitoring.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self.monitoring_active:
            self.logger.warning("Resource monitoring already active")
            return
        
        self.monitoring_interval = interval
        self.monitoring_active = True
        
        # Start background tasks
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self.logger.info(f"Resource monitoring started with {interval}s interval")

    async def stop_monitoring(self):
        """Stop resource monitoring."""
        self.monitoring_active = False
        
        # Cancel background tasks
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Save current data
        await self._save_monitoring_data()
        
        self.logger.info("Resource monitoring stopped")

    def add_alert_callback(self, callback: Callable[[ResourceAlert], None]):
        """Add a callback function for alerts."""
        self.alert_callbacks.append(callback)

    async def get_current_metrics(self) -> ResourceMetrics:
        """Get current system resource metrics."""
        try:
            current_time = time.time()
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_cores = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)
            memory_total_mb = memory.total / (1024 * 1024)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_used_gb = disk.used / (1024 * 1024 * 1024)
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            
            # Disk I/O metrics
            disk_io = psutil.disk_io_counters()
            disk_io_read_rate = 0.0
            disk_io_write_rate = 0.0
            
            if self._previous_disk_io and self._previous_timestamp:
                time_delta = current_time - self._previous_timestamp
                if time_delta > 0:
                    read_delta = disk_io.read_bytes - self._previous_disk_io.read_bytes
                    write_delta = disk_io.write_bytes - self._previous_disk_io.write_bytes
                    disk_io_read_rate = (read_delta / time_delta) / (1024 * 1024)  # MB/s
                    disk_io_write_rate = (write_delta / time_delta) / (1024 * 1024)  # MB/s
            
            self._previous_disk_io = disk_io
            
            # Network metrics
            network_io = psutil.net_io_counters()
            network_sent_rate = 0.0
            network_recv_rate = 0.0
            
            if self._previous_network_io and self._previous_timestamp:
                time_delta = current_time - self._previous_timestamp
                if time_delta > 0:
                    sent_delta = network_io.bytes_sent - self._previous_network_io.bytes_sent
                    recv_delta = network_io.bytes_recv - self._previous_network_io.bytes_recv
                    network_sent_rate = (sent_delta / time_delta) / (1024 * 1024)  # MB/s
                    network_recv_rate = (recv_delta / time_delta) / (1024 * 1024)  # MB/s
            
            self._previous_network_io = network_io
            self._previous_timestamp = current_time
            
            # GPU metrics
            gpu_memory_used = 0.0
            gpu_memory_total = 0.0
            gpu_utilization = 0.0
            
            if self._gpu_available and TORCH_AVAILABLE:
                try:
                    gpu_memory_used = torch.cuda.memory_allocated() / (1024 * 1024)  # MB
                    gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)  # MB
                    gpu_utilization = (gpu_memory_used / gpu_memory_total) * 100 if gpu_memory_total > 0 else 0
                except Exception as gpu_e:
                    self.logger.debug(f"Error getting GPU metrics: {gpu_e}")
            
            # Process metrics
            process_count = len(psutil.pids())
            
            # Load average (Unix-like systems)
            load_average = None
            try:
                load_average = list(os.getloadavg())
            except (OSError, AttributeError):
                # Windows doesn't have getloadavg
                pass
            
            return ResourceMetrics(
                timestamp=timestamp,
                cpu_percent=cpu_percent,
                cpu_cores=cpu_cores,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                memory_total_mb=memory_total_mb,
                disk_usage_percent=disk_usage_percent,
                disk_used_gb=disk_used_gb,
                disk_free_gb=disk_free_gb,
                disk_io_read_mb_per_sec=disk_io_read_rate,
                disk_io_write_mb_per_sec=disk_io_write_rate,
                network_sent_mb_per_sec=network_sent_rate,
                network_recv_mb_per_sec=network_recv_rate,
                gpu_available=self._gpu_available,
                gpu_memory_used_mb=gpu_memory_used,
                gpu_memory_total_mb=gpu_memory_total,
                gpu_utilization_percent=gpu_utilization,
                process_count=process_count,
                load_average=load_average
            )
            
        except Exception as e:
            self.logger.error(f"Error getting resource metrics: {e}")
            # Return minimal metrics on error
            return ResourceMetrics(
                timestamp=datetime.now(timezone.utc).isoformat(),
                cpu_percent=0.0,
                cpu_cores=1,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                memory_total_mb=0.0,
                disk_usage_percent=0.0,
                disk_used_gb=0.0,
                disk_free_gb=0.0,
                disk_io_read_mb_per_sec=0.0,
                disk_io_write_mb_per_sec=0.0,
                network_sent_mb_per_sec=0.0,
                network_recv_mb_per_sec=0.0
            )

    async def get_metrics_history(self, hours: int = 24) -> List[ResourceMetrics]:
        """Get historical metrics for the specified time period."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_timestamp = cutoff_time.isoformat()

        with self._lock:
            return [
                metrics for metrics in self.metrics_history
                if metrics.timestamp >= cutoff_timestamp
            ]

    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary and statistics."""
        if not self.metrics_history:
            return {"error": "No metrics available"}

        recent_metrics = list(self.metrics_history)[-100:]  # Last 100 samples

        # Calculate averages
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        avg_disk = sum(m.disk_usage_percent for m in recent_metrics) / len(recent_metrics)

        # Calculate peaks
        peak_cpu = max(m.cpu_percent for m in recent_metrics)
        peak_memory = max(m.memory_percent for m in recent_metrics)
        peak_disk = max(m.disk_usage_percent for m in recent_metrics)

        # GPU stats if available
        gpu_stats = {}
        if self._gpu_available:
            gpu_metrics = [m for m in recent_metrics if m.gpu_available]
            if gpu_metrics:
                gpu_stats = {
                    "average_utilization": sum(m.gpu_utilization_percent for m in gpu_metrics) / len(gpu_metrics),
                    "peak_utilization": max(m.gpu_utilization_percent for m in gpu_metrics),
                    "average_memory_used_mb": sum(m.gpu_memory_used_mb for m in gpu_metrics) / len(gpu_metrics),
                    "total_memory_mb": gpu_metrics[0].gpu_memory_total_mb
                }

        return {
            "summary_period_samples": len(recent_metrics),
            "cpu": {
                "average_percent": round(avg_cpu, 2),
                "peak_percent": round(peak_cpu, 2),
                "cores": recent_metrics[0].cpu_cores if recent_metrics else 0
            },
            "memory": {
                "average_percent": round(avg_memory, 2),
                "peak_percent": round(peak_memory, 2),
                "total_mb": recent_metrics[0].memory_total_mb if recent_metrics else 0
            },
            "disk": {
                "average_percent": round(avg_disk, 2),
                "peak_percent": round(peak_disk, 2)
            },
            "gpu": gpu_stats,
            "alerts_count": len(self.alerts_history),
            "monitoring_active": self.monitoring_active
        }

    def _check_thresholds(self, metrics: ResourceMetrics):
        """Check metrics against configured thresholds and generate alerts."""
        alerts = []

        # CPU threshold check
        cpu_threshold = self.alert_thresholds.get("cpu_usage_percent", 95)
        if metrics.cpu_percent > cpu_threshold:
            alert = ResourceAlert(
                alert_id=f"cpu_{int(time.time())}",
                timestamp=metrics.timestamp,
                resource_type=ResourceType.CPU,
                alert_level=AlertLevel.WARNING if metrics.cpu_percent < 98 else AlertLevel.CRITICAL,
                message=f"High CPU usage: {metrics.cpu_percent:.1f}%",
                current_value=metrics.cpu_percent,
                threshold_value=cpu_threshold
            )
            alerts.append(alert)

        # Memory threshold check
        memory_threshold = self.alert_thresholds.get("memory_usage_percent", 90)
        if metrics.memory_percent > memory_threshold:
            alert = ResourceAlert(
                alert_id=f"memory_{int(time.time())}",
                timestamp=metrics.timestamp,
                resource_type=ResourceType.MEMORY,
                alert_level=AlertLevel.WARNING if metrics.memory_percent < 95 else AlertLevel.CRITICAL,
                message=f"High memory usage: {metrics.memory_percent:.1f}%",
                current_value=metrics.memory_percent,
                threshold_value=memory_threshold
            )
            alerts.append(alert)

        # Disk threshold check
        disk_threshold = self.alert_thresholds.get("disk_usage_percent", 95)
        if metrics.disk_usage_percent > disk_threshold:
            alert = ResourceAlert(
                alert_id=f"disk_{int(time.time())}",
                timestamp=metrics.timestamp,
                resource_type=ResourceType.DISK,
                alert_level=AlertLevel.WARNING if metrics.disk_usage_percent < 98 else AlertLevel.CRITICAL,
                message=f"High disk usage: {metrics.disk_usage_percent:.1f}%",
                current_value=metrics.disk_usage_percent,
                threshold_value=disk_threshold
            )
            alerts.append(alert)

        # GPU threshold check
        if self._gpu_available and metrics.gpu_utilization_percent > 90:
            alert = ResourceAlert(
                alert_id=f"gpu_{int(time.time())}",
                timestamp=metrics.timestamp,
                resource_type=ResourceType.GPU,
                alert_level=AlertLevel.WARNING,
                message=f"High GPU utilization: {metrics.gpu_utilization_percent:.1f}%",
                current_value=metrics.gpu_utilization_percent,
                threshold_value=90.0
            )
            alerts.append(alert)

        # Process alerts
        for alert in alerts:
            self._process_alert(alert)

    def _process_alert(self, alert: ResourceAlert):
        """Process and handle an alert."""
        with self._lock:
            self.alerts_history.append(alert)

        # Log the alert
        log_level = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.CRITICAL: logging.ERROR,
            AlertLevel.EMERGENCY: logging.CRITICAL
        }.get(alert.alert_level, logging.WARNING)

        self.logger.log(log_level, f"Resource Alert: {alert.message}")

        # Call registered callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")

    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while self.monitoring_active:
            try:
                # Get current metrics
                metrics = await self.get_current_metrics()

                # Store metrics
                with self._lock:
                    self.metrics_history.append(metrics)

                # Check thresholds
                self._check_thresholds(metrics)

                # Wait for next interval
                await asyncio.sleep(self.monitoring_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.monitoring_interval)

    async def _cleanup_loop(self):
        """Background cleanup loop."""
        while self.monitoring_active:
            try:
                # Save monitoring data periodically
                await self._save_monitoring_data()

                # Clean up old data
                await self._cleanup_old_data()

                # Wait for next cleanup cycle (every hour)
                await asyncio.sleep(3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)

    async def _save_monitoring_data(self):
        """Save monitoring data to disk."""
        try:
            data = {
                "metrics_history": [asdict(m) for m in list(self.metrics_history)],
                "alerts_history": [asdict(a) for a in list(self.alerts_history)],
                "performance_baselines": self.performance_baselines,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

            filepath = os.path.join(self.data_path, "resource_monitor_data.json")
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error saving monitoring data: {e}")

    async def _cleanup_old_data(self):
        """Clean up old monitoring data."""
        try:
            retention_hours = self.monitoring_config.get("metrics_retention_hours", 168)  # 7 days
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
            cutoff_timestamp = cutoff_time.isoformat()

            with self._lock:
                # Clean up old metrics
                self.metrics_history = deque(
                    [m for m in self.metrics_history if m.timestamp >= cutoff_timestamp],
                    maxlen=self.metrics_history.maxlen
                )

                # Clean up old alerts
                self.alerts_history = deque(
                    [a for a in self.alerts_history if a.timestamp >= cutoff_timestamp],
                    maxlen=self.alerts_history.maxlen
                )

        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
