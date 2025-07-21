"""
Phase 2C: AI Performance Monitoring System
Real-time AI performance monitoring, alerting, and analytics.
"""

import asyncio
import time
import json
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime, timedelta
import logging
import statistics
from collections import deque, defaultdict
import psutil
import os


class MetricType(Enum):
    """Types of performance metrics."""
    RESPONSE_TIME = "response_time"
    SUCCESS_RATE = "success_rate"
    ERROR_RATE = "error_rate"
    COST_PER_REQUEST = "cost_per_request"
    QUALITY_SCORE = "quality_score"
    THROUGHPUT = "throughput"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    TOKEN_USAGE = "token_usage"
    CACHE_HIT_RATE = "cache_hit_rate"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """Individual performance metric data point."""
    metric_type: MetricType
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    provider: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'metric_type': self.metric_type.value,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'provider': self.provider,
            'context': self.context
        }


@dataclass
class PerformanceAlert:
    """Performance alert data."""
    alert_id: str
    severity: AlertSeverity
    metric_type: MetricType
    message: str
    current_value: float
    threshold_value: float
    provider: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'alert_id': self.alert_id,
            'severity': self.severity.value,
            'metric_type': self.metric_type.value,
            'message': self.message,
            'current_value': self.current_value,
            'threshold_value': self.threshold_value,
            'provider': self.provider,
            'timestamp': self.timestamp.isoformat(),
            'resolved': self.resolved
        }


@dataclass
class MonitoringConfig:
    """Configuration for performance monitoring."""
    # Sampling settings
    collection_interval_seconds: int = 10
    metric_retention_hours: int = 24
    aggregation_window_minutes: int = 5
    
    # Alert thresholds
    response_time_threshold_ms: float = 3000.0
    error_rate_threshold: float = 0.05  # 5%
    success_rate_threshold: float = 0.95  # 95%
    memory_usage_threshold_mb: float = 500.0
    cpu_usage_threshold: float = 0.8  # 80%
    cost_per_request_threshold: float = 0.10  # $0.10
    quality_score_threshold: float = 0.7
    
    # Performance targets
    target_response_time_ms: float = 1500.0
    target_success_rate: float = 0.98
    target_cost_per_request: float = 0.05
    target_quality_score: float = 0.85
    
    # Monitoring settings
    enable_real_time_alerts: bool = True
    enable_trend_analysis: bool = True
    enable_performance_dashboard: bool = True
    alert_cooldown_minutes: int = 15


class MetricsCollector:
    """Collects performance metrics from various sources."""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.metrics_storage = defaultdict(lambda: deque(maxlen=1000))
        self.current_requests = {}  # Track ongoing requests
        self.logger = logging.getLogger(__name__)
        
        # Process monitoring
        self.process = psutil.Process()
        
        # Start collection thread
        self.collection_thread = threading.Thread(target=self._collect_system_metrics, daemon=True)
        self.collection_thread.start()
    
    def record_request_start(self, request_id: str, provider: str, context: Dict[str, Any] = None):
        """Record the start of an AI request."""
        self.current_requests[request_id] = {
            'start_time': time.time(),
            'provider': provider,
            'context': context or {}
        }
    
    def record_request_end(
        self,
        request_id: str,
        success: bool,
        response_data: Dict[str, Any] = None,
        error: str = None
    ):
        """Record the completion of an AI request."""
        if request_id not in self.current_requests:
            self.logger.warning(f"Request {request_id} not found in tracking")
            return
        
        request_info = self.current_requests.pop(request_id)
        end_time = time.time()
        response_time = (end_time - request_info['start_time']) * 1000  # Convert to ms
        
        provider = request_info['provider']
        context = request_info['context']
        
        # Record response time
        self.add_metric(PerformanceMetric(
            metric_type=MetricType.RESPONSE_TIME,
            value=response_time,
            provider=provider,
            context={'request_id': request_id, **context}
        ))
        
        # Record success/error
        if success:
            self.add_metric(PerformanceMetric(
                metric_type=MetricType.SUCCESS_RATE,
                value=1.0,
                provider=provider,
                context={'request_id': request_id}
            ))
            
            # Record additional metrics from response
            if response_data:
                if 'quality_score' in response_data:
                    self.add_metric(PerformanceMetric(
                        metric_type=MetricType.QUALITY_SCORE,
                        value=response_data['quality_score'],
                        provider=provider,
                        context={'request_id': request_id}
                    ))
                
                if 'cost' in response_data:
                    self.add_metric(PerformanceMetric(
                        metric_type=MetricType.COST_PER_REQUEST,
                        value=response_data['cost'],
                        provider=provider,
                        context={'request_id': request_id}
                    ))
                
                if 'token_count' in response_data:
                    self.add_metric(PerformanceMetric(
                        metric_type=MetricType.TOKEN_USAGE,
                        value=response_data['token_count'],
                        provider=provider,
                        context={'request_id': request_id}
                    ))
        else:
            self.add_metric(PerformanceMetric(
                metric_type=MetricType.ERROR_RATE,
                value=1.0,
                provider=provider,
                context={'request_id': request_id, 'error': error}
            ))
    
    def record_cache_event(self, hit: bool, provider: str = None):
        """Record cache hit or miss."""
        self.add_metric(PerformanceMetric(
            metric_type=MetricType.CACHE_HIT_RATE,
            value=1.0 if hit else 0.0,
            provider=provider
        ))
    
    def add_metric(self, metric: PerformanceMetric):
        """Add a performance metric to storage."""
        key = f"{metric.metric_type.value}_{metric.provider or 'global'}"
        self.metrics_storage[key].append(metric)
        
        # Log metric for debugging
        self.logger.debug(f"Metric recorded: {metric.metric_type.value}={metric.value} for {metric.provider}")
    
    def get_metrics(
        self,
        metric_type: MetricType,
        provider: str = None,
        time_window_minutes: int = 60
    ) -> List[PerformanceMetric]:
        """Get metrics for a specific type and time window."""
        key = f"{metric_type.value}_{provider or 'global'}"
        metrics = list(self.metrics_storage[key])
        
        # Filter by time window
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        return [m for m in metrics if m.timestamp >= cutoff_time]
    
    def _collect_system_metrics(self):
        """Collect system performance metrics continuously."""
        while True:
            try:
                # Memory usage
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)
                
                self.add_metric(PerformanceMetric(
                    metric_type=MetricType.MEMORY_USAGE,
                    value=memory_mb
                ))
                
                # CPU usage
                cpu_percent = self.process.cpu_percent()
                self.add_metric(PerformanceMetric(
                    metric_type=MetricType.CPU_USAGE,
                    value=cpu_percent / 100.0  # Convert to 0-1 range
                ))
                
                # Sleep until next collection
                time.sleep(self.config.collection_interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Error collecting system metrics: {str(e)}")
                time.sleep(self.config.collection_interval_seconds)


class TrendAnalyzer:
    """Analyzes performance trends and patterns."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.logger = logging.getLogger(__name__)
    
    def analyze_trends(
        self,
        metric_type: MetricType,
        provider: str = None,
        analysis_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Analyze trends for a specific metric."""
        metrics = self.metrics_collector.get_metrics(
            metric_type, provider, analysis_window_hours * 60
        )
        
        if not metrics:
            return {'trend': 'no_data', 'confidence': 0.0}
        
        # Extract values and timestamps
        values = [m.value for m in metrics]
        timestamps = [m.timestamp.timestamp() for m in metrics]
        
        # Calculate trend
        trend_result = self._calculate_trend(values, timestamps)
        
        # Calculate statistics
        stats = {
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
            'min': min(values),
            'max': max(values),
            'count': len(values)
        }
        
        # Detect anomalies
        anomalies = self._detect_anomalies(values)
        
        return {
            'trend': trend_result['direction'],
            'trend_strength': trend_result['strength'],
            'confidence': trend_result['confidence'],
            'statistics': stats,
            'anomalies': anomalies,
            'analysis_window_hours': analysis_window_hours,
            'provider': provider
        }
    
    def _calculate_trend(self, values: List[float], timestamps: List[float]) -> Dict[str, Any]:
        """Calculate trend direction and strength."""
        if len(values) < 3:
            return {'direction': 'insufficient_data', 'strength': 0.0, 'confidence': 0.0}
        
        # Simple linear regression
        n = len(values)
        sum_x = sum(timestamps)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(timestamps, values))
        sum_x2 = sum(x * x for x in timestamps)
        
        # Calculate slope
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Determine trend direction
        if abs(slope) < 0.001:  # Very small slope
            direction = 'stable'
            strength = 0.0
        elif slope > 0:
            direction = 'increasing'
            strength = min(1.0, abs(slope) * 1000)  # Normalize
        else:
            direction = 'decreasing'
            strength = min(1.0, abs(slope) * 1000)  # Normalize
        
        # Calculate confidence based on R-squared
        mean_y = sum_y / n
        ss_tot = sum((y - mean_y) ** 2 for y in values)
        ss_res = sum((y - (slope * x + (sum_y - slope * sum_x) / n)) ** 2 
                    for x, y in zip(timestamps, values))
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        confidence = max(0.0, min(1.0, r_squared))
        
        return {
            'direction': direction,
            'strength': strength,
            'confidence': confidence,
            'slope': slope
        }
    
    def _detect_anomalies(self, values: List[float]) -> List[Dict[str, Any]]:
        """Detect anomalies in metric values."""
        if len(values) < 5:
            return []
        
        mean = statistics.mean(values)
        std_dev = statistics.stdev(values)
        threshold = 2.0  # 2 standard deviations
        
        anomalies = []
        for i, value in enumerate(values):
            z_score = abs(value - mean) / std_dev if std_dev > 0 else 0
            if z_score > threshold:
                anomalies.append({
                    'index': i,
                    'value': value,
                    'z_score': z_score,
                    'deviation': abs(value - mean)
                })
        
        return anomalies


class AlertManager:
    """Manages performance alerts and notifications."""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.alert_cooldowns = {}
        self.logger = logging.getLogger(__name__)
        
        # Alert callbacks
        self.alert_callbacks = []
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Add callback function for alert notifications."""
        self.alert_callbacks.append(callback)
    
    def check_thresholds(
        self,
        metric_type: MetricType,
        current_value: float,
        provider: str = None
    ):
        """Check if metric value exceeds thresholds and trigger alerts."""
        if not self.config.enable_real_time_alerts:
            return
        
        alert_key = f"{metric_type.value}_{provider or 'global'}"
        
        # Check cooldown
        if self._is_in_cooldown(alert_key):
            return
        
        # Check thresholds based on metric type
        alert = None
        
        if metric_type == MetricType.RESPONSE_TIME:
            if current_value > self.config.response_time_threshold_ms:
                alert = self._create_alert(
                    alert_key,
                    AlertSeverity.WARNING if current_value < self.config.response_time_threshold_ms * 1.5 else AlertSeverity.ERROR,
                    metric_type,
                    f"Response time {current_value:.1f}ms exceeds threshold {self.config.response_time_threshold_ms:.1f}ms",
                    current_value,
                    self.config.response_time_threshold_ms,
                    provider
                )
        
        elif metric_type == MetricType.ERROR_RATE:
            if current_value > self.config.error_rate_threshold:
                alert = self._create_alert(
                    alert_key,
                    AlertSeverity.ERROR,
                    metric_type,
                    f"Error rate {current_value:.2%} exceeds threshold {self.config.error_rate_threshold:.2%}",
                    current_value,
                    self.config.error_rate_threshold,
                    provider
                )
        
        elif metric_type == MetricType.SUCCESS_RATE:
            if current_value < self.config.success_rate_threshold:
                alert = self._create_alert(
                    alert_key,
                    AlertSeverity.ERROR,
                    metric_type,
                    f"Success rate {current_value:.2%} below threshold {self.config.success_rate_threshold:.2%}",
                    current_value,
                    self.config.success_rate_threshold,
                    provider
                )
        
        elif metric_type == MetricType.MEMORY_USAGE:
            if current_value > self.config.memory_usage_threshold_mb:
                alert = self._create_alert(
                    alert_key,
                    AlertSeverity.WARNING,
                    metric_type,
                    f"Memory usage {current_value:.1f}MB exceeds threshold {self.config.memory_usage_threshold_mb:.1f}MB",
                    current_value,
                    self.config.memory_usage_threshold_mb,
                    provider
                )
        
        elif metric_type == MetricType.CPU_USAGE:
            if current_value > self.config.cpu_usage_threshold:
                alert = self._create_alert(
                    alert_key,
                    AlertSeverity.WARNING,
                    metric_type,
                    f"CPU usage {current_value:.1%} exceeds threshold {self.config.cpu_usage_threshold:.1%}",
                    current_value,
                    self.config.cpu_usage_threshold,
                    provider
                )
        
        elif metric_type == MetricType.COST_PER_REQUEST:
            if current_value > self.config.cost_per_request_threshold:
                alert = self._create_alert(
                    alert_key,
                    AlertSeverity.WARNING,
                    metric_type,
                    f"Cost per request ${current_value:.3f} exceeds threshold ${self.config.cost_per_request_threshold:.3f}",
                    current_value,
                    self.config.cost_per_request_threshold,
                    provider
                )
        
        elif metric_type == MetricType.QUALITY_SCORE:
            if current_value < self.config.quality_score_threshold:
                alert = self._create_alert(
                    alert_key,
                    AlertSeverity.WARNING,
                    metric_type,
                    f"Quality score {current_value:.2f} below threshold {self.config.quality_score_threshold:.2f}",
                    current_value,
                    self.config.quality_score_threshold,
                    provider
                )
        
        if alert:
            self._trigger_alert(alert)
    
    def _create_alert(
        self,
        alert_key: str,
        severity: AlertSeverity,
        metric_type: MetricType,
        message: str,
        current_value: float,
        threshold_value: float,
        provider: str = None
    ) -> PerformanceAlert:
        """Create a new alert."""
        return PerformanceAlert(
            alert_id=alert_key,
            severity=severity,
            metric_type=metric_type,
            message=message,
            current_value=current_value,
            threshold_value=threshold_value,
            provider=provider
        )
    
    def _trigger_alert(self, alert: PerformanceAlert):
        """Trigger an alert and notify callbacks."""
        # Add to active alerts
        self.active_alerts[alert.alert_id] = alert
        
        # Add to history
        self.alert_history.append(alert)
        
        # Set cooldown
        self.alert_cooldowns[alert.alert_id] = datetime.now()
        
        # Log alert
        self.logger.warning(f"ALERT [{alert.severity.value.upper()}]: {alert.message}")
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {str(e)}")
    
    def resolve_alert(self, alert_id: str):
        """Resolve an active alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            del self.active_alerts[alert_id]
            self.logger.info(f"Alert resolved: {alert.message}")
    
    def _is_in_cooldown(self, alert_key: str) -> bool:
        """Check if alert is in cooldown period."""
        if alert_key not in self.alert_cooldowns:
            return False
        
        cooldown_end = self.alert_cooldowns[alert_key] + timedelta(minutes=self.config.alert_cooldown_minutes)
        return datetime.now() < cooldown_end
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[PerformanceAlert]:
        """Get alert history for specified time window."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp >= cutoff_time]


class PerformanceDashboard:
    """Performance dashboard for real-time monitoring."""
    
    def __init__(
        self,
        metrics_collector: MetricsCollector,
        trend_analyzer: TrendAnalyzer,
        alert_manager: AlertManager
    ):
        self.metrics_collector = metrics_collector
        self.trend_analyzer = trend_analyzer
        self.alert_manager = alert_manager
        self.logger = logging.getLogger(__name__)
    
    def get_dashboard_data(self, time_window_hours: int = 1) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        providers = ['openai', 'anthropic', 'google', 'ollama', None]  # Include global
        
        dashboard_data = {
            'overview': self._get_overview_metrics(time_window_hours),
            'providers': {},
            'trends': {},
            'alerts': {
                'active': [alert.to_dict() for alert in self.alert_manager.get_active_alerts()],
                'recent': [alert.to_dict() for alert in self.alert_manager.get_alert_history(24)]
            },
            'system_health': self._get_system_health(),
            'timestamp': datetime.now().isoformat()
        }
        
        # Provider-specific data
        for provider in providers:
            if provider:  # Skip None for provider-specific section
                dashboard_data['providers'][provider] = self._get_provider_metrics(provider, time_window_hours)
        
        # Trend analysis
        for metric_type in MetricType:
            dashboard_data['trends'][metric_type.value] = self.trend_analyzer.analyze_trends(
                metric_type, None, time_window_hours
            )
        
        return dashboard_data
    
    def _get_overview_metrics(self, time_window_hours: int) -> Dict[str, Any]:
        """Get overview metrics for all providers combined."""
        metrics = {}
        
        for metric_type in MetricType:
            metric_data = self.metrics_collector.get_metrics(metric_type, None, time_window_hours * 60)
            
            if metric_data:
                values = [m.value for m in metric_data]
                metrics[metric_type.value] = {
                    'current': values[-1] if values else 0,
                    'average': statistics.mean(values),
                    'min': min(values),
                    'max': max(values),
                    'count': len(values)
                }
            else:
                metrics[metric_type.value] = {
                    'current': 0,
                    'average': 0,
                    'min': 0,
                    'max': 0,
                    'count': 0
                }
        
        return metrics
    
    def _get_provider_metrics(self, provider: str, time_window_hours: int) -> Dict[str, Any]:
        """Get metrics for a specific provider."""
        provider_data = {
            'name': provider,
            'metrics': {},
            'health_score': 0.0
        }
        
        total_score = 0
        metric_count = 0
        
        for metric_type in MetricType:
            metric_data = self.metrics_collector.get_metrics(metric_type, provider, time_window_hours * 60)
            
            if metric_data:
                values = [m.value for m in metric_data]
                avg_value = statistics.mean(values)
                
                provider_data['metrics'][metric_type.value] = {
                    'current': values[-1],
                    'average': avg_value,
                    'min': min(values),
                    'max': max(values),
                    'count': len(values)
                }
                
                # Calculate health contribution
                health_contribution = self._calculate_health_contribution(metric_type, avg_value)
                total_score += health_contribution
                metric_count += 1
        
        # Calculate overall health score
        if metric_count > 0:
            provider_data['health_score'] = total_score / metric_count
        
        return provider_data
    
    def _calculate_health_contribution(self, metric_type: MetricType, value: float) -> float:
        """Calculate health score contribution for a metric."""
        config = self.metrics_collector.config
        
        if metric_type == MetricType.RESPONSE_TIME:
            # Lower is better
            return max(0, 1 - (value / config.target_response_time_ms))
        elif metric_type == MetricType.SUCCESS_RATE:
            # Higher is better
            return value
        elif metric_type == MetricType.ERROR_RATE:
            # Lower is better
            return max(0, 1 - (value / 0.1))  # 10% error rate = 0 health
        elif metric_type == MetricType.QUALITY_SCORE:
            # Higher is better
            return value
        elif metric_type == MetricType.COST_PER_REQUEST:
            # Lower is better
            return max(0, 1 - (value / config.target_cost_per_request))
        else:
            # Default neutral contribution
            return 0.5
    
    def _get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        # Get recent system metrics
        memory_metrics = self.metrics_collector.get_metrics(MetricType.MEMORY_USAGE, None, 5)
        cpu_metrics = self.metrics_collector.get_metrics(MetricType.CPU_USAGE, None, 5)
        
        memory_usage = memory_metrics[-1].value if memory_metrics else 0
        cpu_usage = cpu_metrics[-1].value if cpu_metrics else 0
        
        # Calculate health score
        memory_health = max(0, 1 - (memory_usage / self.metrics_collector.config.memory_usage_threshold_mb))
        cpu_health = max(0, 1 - (cpu_usage / self.metrics_collector.config.cpu_usage_threshold))
        
        overall_health = (memory_health + cpu_health) / 2
        
        # Determine status
        if overall_health >= 0.8:
            status = "healthy"
        elif overall_health >= 0.6:
            status = "warning"
        else:
            status = "unhealthy"
        
        return {
            'status': status,
            'health_score': overall_health,
            'memory_usage_mb': memory_usage,
            'cpu_usage_percent': cpu_usage * 100,
            'memory_health': memory_health,
            'cpu_health': cpu_health
        }


class AIPerformanceMonitor:
    """
    Main AI Performance Monitoring System.
    Provides comprehensive monitoring, alerting, and analytics for AI operations.
    """
    
    def __init__(self, config: MonitoringConfig = None):
        self.config = config or MonitoringConfig()
        
        # Initialize components
        self.metrics_collector = MetricsCollector(self.config)
        self.trend_analyzer = TrendAnalyzer(self.metrics_collector)
        self.alert_manager = AlertManager(self.config)
        self.dashboard = PerformanceDashboard(
            self.metrics_collector,
            self.trend_analyzer,
            self.alert_manager
        )
        
        self.logger = logging.getLogger(__name__)
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        self.logger.info("AI Performance Monitor initialized and started")
    
    def track_request(self, request_id: str, provider: str, context: Dict[str, Any] = None):
        """Start tracking an AI request."""
        self.metrics_collector.record_request_start(request_id, provider, context)
    
    def complete_request(
        self,
        request_id: str,
        success: bool,
        response_data: Dict[str, Any] = None,
        error: str = None
    ):
        """Complete tracking an AI request."""
        self.metrics_collector.record_request_end(request_id, success, response_data, error)
    
    def record_cache_hit(self, provider: str = None):
        """Record a cache hit."""
        self.metrics_collector.record_cache_event(True, provider)
    
    def record_cache_miss(self, provider: str = None):
        """Record a cache miss."""
        self.metrics_collector.record_cache_event(False, provider)
    
    def add_alert_handler(self, callback: Callable[[PerformanceAlert], None]):
        """Add custom alert handler."""
        self.alert_manager.add_alert_callback(callback)
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        return self.dashboard.get_dashboard_data(hours)
    
    def get_provider_comparison(self, hours: int = 24) -> Dict[str, Any]:
        """Get comparative analysis of AI providers."""
        providers = ['openai', 'anthropic', 'google', 'ollama']
        comparison = {}
        
        for provider in providers:
            provider_metrics = {}
            
            # Get key metrics for comparison
            for metric_type in [MetricType.RESPONSE_TIME, MetricType.SUCCESS_RATE, 
                              MetricType.QUALITY_SCORE, MetricType.COST_PER_REQUEST]:
                metrics = self.metrics_collector.get_metrics(metric_type, provider, hours * 60)
                if metrics:
                    values = [m.value for m in metrics]
                    provider_metrics[metric_type.value] = {
                        'average': statistics.mean(values),
                        'count': len(values)
                    }
                else:
                    provider_metrics[metric_type.value] = {'average': 0, 'count': 0}
            
            comparison[provider] = provider_metrics
        
        return comparison
    
    def _monitoring_loop(self):
        """Main monitoring loop for real-time analysis."""
        while True:
            try:
                # Check metrics against thresholds
                self._check_all_thresholds()
                
                # Auto-resolve alerts if conditions improve
                self._check_alert_resolution()
                
                # Sleep until next check
                time.sleep(self.config.aggregation_window_minutes * 60)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying
    
    def _check_all_thresholds(self):
        """Check all metrics against thresholds."""
        providers = ['openai', 'anthropic', 'google', 'ollama', None]
        
        for provider in providers:
            for metric_type in MetricType:
                # Get recent metrics (last 5 minutes)
                metrics = self.metrics_collector.get_metrics(metric_type, provider, 5)
                
                if metrics:
                    # Calculate average for threshold checking
                    values = [m.value for m in metrics]
                    avg_value = statistics.mean(values)
                    
                    # Check threshold
                    self.alert_manager.check_thresholds(metric_type, avg_value, provider)
    
    def _check_alert_resolution(self):
        """Check if active alerts should be resolved."""
        active_alerts = self.alert_manager.get_active_alerts()
        
        for alert in active_alerts:
            # Get recent metrics
            metrics = self.metrics_collector.get_metrics(alert.metric_type, alert.provider, 5)
            
            if metrics:
                values = [m.value for m in metrics]
                current_avg = statistics.mean(values)
                
                # Check if condition has improved
                if self._should_resolve_alert(alert, current_avg):
                    self.alert_manager.resolve_alert(alert.alert_id)
    
    def _should_resolve_alert(self, alert: PerformanceAlert, current_value: float) -> bool:
        """Determine if an alert should be resolved based on current value."""
        # Add hysteresis to prevent alert flapping
        threshold_buffer = 0.1  # 10% buffer
        
        if alert.metric_type in [MetricType.RESPONSE_TIME, MetricType.ERROR_RATE, 
                               MetricType.MEMORY_USAGE, MetricType.CPU_USAGE, 
                               MetricType.COST_PER_REQUEST]:
            # For "lower is better" metrics
            improved_threshold = alert.threshold_value * (1 - threshold_buffer)
            return current_value < improved_threshold
        else:
            # For "higher is better" metrics
            improved_threshold = alert.threshold_value * (1 + threshold_buffer)
            return current_value > improved_threshold


# Example usage and testing
if __name__ == "__main__":
    async def test_performance_monitoring():
        """Test AI performance monitoring system."""
        
        # Initialize monitor
        config = MonitoringConfig(
            collection_interval_seconds=1,
            response_time_threshold_ms=2000.0,
            enable_real_time_alerts=True
        )
        
        monitor = AIPerformanceMonitor(config)
        
        # Add alert handler
        def alert_handler(alert: PerformanceAlert):
            print(f"ALERT: {alert.message}")
        
        monitor.add_alert_handler(alert_handler)
        
        # Simulate AI requests
        import uuid
        
        for i in range(10):
            request_id = str(uuid.uuid4())
            provider = 'openai' if i % 2 == 0 else 'anthropic'
            
            # Start tracking
            monitor.track_request(request_id, provider, {'test_request': i})
            
            # Simulate processing time
            await asyncio.sleep(0.1)
            
            # Complete tracking
            monitor.complete_request(
                request_id,
                success=True,
                response_data={
                    'quality_score': 0.8 + (i * 0.02),
                    'cost': 0.01 + (i * 0.001),
                    'token_count': 100 + (i * 10)
                }
            )
            
            # Record cache events
            if i % 3 == 0:
                monitor.record_cache_hit(provider)
            else:
                monitor.record_cache_miss(provider)
        
        # Wait for metrics collection
        await asyncio.sleep(2)
        
        # Get performance summary
        summary = monitor.get_performance_summary(1)
        print("Performance Summary:")
        print(json.dumps(summary, indent=2, default=str))
        
        # Get provider comparison
        comparison = monitor.get_provider_comparison(1)
        print("\nProvider Comparison:")
        print(json.dumps(comparison, indent=2, default=str))
    
    # Run test
    asyncio.run(test_performance_monitoring())