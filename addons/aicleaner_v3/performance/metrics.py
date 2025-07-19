"""
Performance Metrics Collection
Phase 5A: Performance Optimization

Provides metrics collection and tracking for performance analysis.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """Individual metric value"""
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels
        }


class Metric:
    """Base metric class"""
    
    def __init__(self, name: str, description: str, metric_type: MetricType):
        self.name = name
        self.description = description
        self.type = metric_type
        self._values: deque = deque(maxlen=1000)  # Keep last 1000 values
        
    def add_value(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Add a value to the metric"""
        metric_value = MetricValue(value=value, labels=labels or {})
        self._values.append(metric_value)
        
    def get_latest_value(self) -> Optional[MetricValue]:
        """Get the most recent value"""
        return self._values[-1] if self._values else None
        
    def get_values(self, limit: Optional[int] = None) -> List[MetricValue]:
        """Get recent values"""
        if limit:
            return list(self._values)[-limit:]
        return list(self._values)
        
    def get_statistics(self) -> Dict[str, float]:
        """Get statistical summary of values"""
        if not self._values:
            return {}
            
        values = [v.value for v in self._values]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1]
        }


class Counter(Metric):
    """Counter metric - monotonically increasing"""
    
    def __init__(self, name: str, description: str):
        super().__init__(name, description, MetricType.COUNTER)
        self._total = 0.0
        
    def increment(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment the counter"""
        self._total += amount
        self.add_value(self._total, labels)
        
    def get_total(self) -> float:
        """Get total count"""
        return self._total
        
    def reset(self):
        """Reset counter to zero"""
        self._total = 0.0
        self.add_value(0.0)


class Gauge(Metric):
    """Gauge metric - can go up or down"""
    
    def __init__(self, name: str, description: str):
        super().__init__(name, description, MetricType.GAUGE)
        
    def set(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Set gauge value"""
        self.add_value(value, labels)
        
    def increment(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment gauge value"""
        current = self.get_latest_value()
        current_value = current.value if current else 0.0
        self.set(current_value + amount, labels)
        
    def decrement(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Decrement gauge value"""
        self.increment(-amount, labels)


class Histogram(Metric):
    """Histogram metric - tracks distribution of values"""
    
    def __init__(self, name: str, description: str, buckets: Optional[List[float]] = None):
        super().__init__(name, description, MetricType.HISTOGRAM)
        self.buckets = buckets or [0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self._bucket_counts = defaultdict(int)
        self._sum = 0.0
        self._count = 0
        
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a value"""
        self.add_value(value, labels)
        self._sum += value
        self._count += 1
        
        # Update bucket counts
        for bucket in self.buckets:
            if value <= bucket:
                self._bucket_counts[bucket] += 1
                
    def get_quantile(self, quantile: float) -> float:
        """Get quantile value (approximate)"""
        if not self._values:
            return 0.0
            
        values = sorted([v.value for v in self._values])
        index = int(len(values) * quantile)
        return values[min(index, len(values) - 1)]
        
    def get_histogram_stats(self) -> Dict[str, Any]:
        """Get histogram statistics"""
        stats = self.get_statistics()
        stats.update({
            "sum": self._sum,
            "count": self._count,
            "buckets": dict(self._bucket_counts),
            "p50": self.get_quantile(0.5),
            "p95": self.get_quantile(0.95),
            "p99": self.get_quantile(0.99)
        })
        return stats


class Timer(Histogram):
    """Timer metric - specialized histogram for timing operations"""
    
    def __init__(self, name: str, description: str):
        # Default buckets in seconds: 1ms to 10s
        buckets = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        super().__init__(name, description, buckets)
        
    def time_context(self, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing operations"""
        return TimerContext(self, labels)
        
    def time_async_context(self, labels: Optional[Dict[str, str]] = None):
        """Async context manager for timing operations"""
        return AsyncTimerContext(self, labels)


class TimerContext:
    """Context manager for timing operations"""
    
    def __init__(self, timer: Timer, labels: Optional[Dict[str, str]] = None):
        self.timer = timer
        self.labels = labels
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.perf_counter() - self.start_time
            self.timer.observe(duration, self.labels)


class AsyncTimerContext:
    """Async context manager for timing operations"""
    
    def __init__(self, timer: Timer, labels: Optional[Dict[str, str]] = None):
        self.timer = timer
        self.labels = labels
        self.start_time = None
        
    async def __aenter__(self):
        self.start_time = time.perf_counter()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.perf_counter() - self.start_time
            self.timer.observe(duration, self.labels)


class PerformanceMetrics:
    """Central metrics registry"""
    
    def __init__(self):
        self._metrics: Dict[str, Metric] = {}
        self._enabled = True
        
    def enable(self):
        """Enable metrics collection"""
        self._enabled = True
        logger.info("Performance metrics enabled")
        
    def disable(self):
        """Disable metrics collection"""
        self._enabled = False
        logger.info("Performance metrics disabled")
        
    def counter(self, name: str, description: str) -> Counter:
        """Get or create a counter metric"""
        if name not in self._metrics:
            self._metrics[name] = Counter(name, description)
        return self._metrics[name]
        
    def gauge(self, name: str, description: str) -> Gauge:
        """Get or create a gauge metric"""
        if name not in self._metrics:
            self._metrics[name] = Gauge(name, description)
        return self._metrics[name]
        
    def histogram(self, name: str, description: str, buckets: Optional[List[float]] = None) -> Histogram:
        """Get or create a histogram metric"""
        if name not in self._metrics:
            self._metrics[name] = Histogram(name, description, buckets)
        return self._metrics[name]
        
    def timer(self, name: str, description: str) -> Timer:
        """Get or create a timer metric"""
        if name not in self._metrics:
            self._metrics[name] = Timer(name, description)
        return self._metrics[name]
        
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric by name"""
        return self._metrics.get(name)
        
    def get_all_metrics(self) -> Dict[str, Metric]:
        """Get all metrics"""
        return self._metrics.copy()
        
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        summary = {}
        for name, metric in self._metrics.items():
            summary[name] = {
                "type": metric.type.value,
                "description": metric.description,
                "statistics": metric.get_statistics()
            }
            
            # Add type-specific information
            if isinstance(metric, Histogram):
                summary[name]["histogram_stats"] = metric.get_histogram_stats()
            elif isinstance(metric, Counter):
                summary[name]["total"] = metric.get_total()
                
        return summary
        
    def clear_all(self):
        """Clear all metrics"""
        self._metrics.clear()
        logger.info("All performance metrics cleared")


class PerformanceTracker:
    """High-level performance tracking for common operations"""
    
    def __init__(self, metrics: PerformanceMetrics):
        self.metrics = metrics
        self._setup_default_metrics()
        
    def _setup_default_metrics(self):
        """Setup default performance metrics"""
        # Request metrics
        self.request_counter = self.metrics.counter(
            "http_requests_total", 
            "Total HTTP requests"
        )
        self.request_duration = self.metrics.timer(
            "http_request_duration_seconds",
            "HTTP request duration"
        )
        
        # Database/Storage metrics
        self.db_operations = self.metrics.timer(
            "db_operation_duration_seconds",
            "Database operation duration"
        )
        
        # AI Provider metrics
        self.ai_requests = self.metrics.counter(
            "ai_requests_total",
            "Total AI provider requests"
        )
        self.ai_request_duration = self.metrics.timer(
            "ai_request_duration_seconds",
            "AI request duration"
        )
        self.ai_cache_hits = self.metrics.counter(
            "ai_cache_hits_total",
            "AI cache hits"
        )
        
        # MQTT metrics
        self.mqtt_messages_published = self.metrics.counter(
            "mqtt_messages_published_total",
            "MQTT messages published"
        )
        self.mqtt_messages_received = self.metrics.counter(
            "mqtt_messages_received_total", 
            "MQTT messages received"
        )
        
        # Zone/Device metrics
        self.zone_operations = self.metrics.timer(
            "zone_operation_duration_seconds",
            "Zone operation duration"
        )
        self.device_operations = self.metrics.timer(
            "device_operation_duration_seconds",
            "Device operation duration"
        )
        
        # System metrics
        self.memory_usage = self.metrics.gauge(
            "memory_usage_mb",
            "Memory usage in MB"
        )
        self.cpu_usage = self.metrics.gauge(
            "cpu_usage_percent",
            "CPU usage percentage"
        )
        
    def track_request(self, method: str, endpoint: str):
        """Track HTTP request"""
        labels = {"method": method, "endpoint": endpoint}
        self.request_counter.increment(labels=labels)
        return self.request_duration.time_context(labels)
        
    def track_db_operation(self, operation: str, table: str = None):
        """Track database operation"""
        labels = {"operation": operation}
        if table:
            labels["table"] = table
        return self.db_operations.time_context(labels)
        
    def track_ai_request(self, provider: str, model: str = None):
        """Track AI provider request"""
        labels = {"provider": provider}
        if model:
            labels["model"] = model
        self.ai_requests.increment(labels=labels)
        return self.ai_request_duration.time_async_context(labels)
        
    def track_ai_cache_hit(self, provider: str):
        """Track AI cache hit"""
        self.ai_cache_hits.increment(labels={"provider": provider})
        
    def track_mqtt_publish(self, topic: str = None):
        """Track MQTT message publish"""
        labels = {"topic": topic} if topic else {}
        self.mqtt_messages_published.increment(labels=labels)
        
    def track_mqtt_receive(self, topic: str = None):
        """Track MQTT message receive"""
        labels = {"topic": topic} if topic else {}
        self.mqtt_messages_received.increment(labels=labels)
        
    def track_zone_operation(self, zone_id: str, operation: str):
        """Track zone operation"""
        labels = {"zone_id": zone_id, "operation": operation}
        return self.zone_operations.time_async_context(labels)
        
    def track_device_operation(self, device_id: str, operation: str):
        """Track device operation"""
        labels = {"device_id": device_id, "operation": operation}
        return self.device_operations.time_async_context(labels)
        
    def update_system_metrics(self, memory_mb: float, cpu_percent: float):
        """Update system resource metrics"""
        self.memory_usage.set(memory_mb)
        self.cpu_usage.set(cpu_percent)


# Global metrics instance
_global_metrics = PerformanceMetrics()
_global_tracker = PerformanceTracker(_global_metrics)


def get_metrics() -> PerformanceMetrics:
    """Get global metrics instance"""
    return _global_metrics


def get_tracker() -> PerformanceTracker:
    """Get global performance tracker"""
    return _global_tracker