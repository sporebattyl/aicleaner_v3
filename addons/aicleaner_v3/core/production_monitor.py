"""
Production Readiness Monitor for AICleaner
Provides comprehensive error handling, logging, performance monitoring, and debugging capabilities
"""
import os
import json
import logging
import time
import traceback
import psutil
import threading
import asyncio
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import functools

try:
    from core.resource_monitor import ResourceMonitor, ResourceMetrics
    from core.alert_manager import AlertManager, ResourceAlert, AlertLevel, ResourceType
    ADVANCED_MONITORING_AVAILABLE = True
except ImportError:
    ADVANCED_MONITORING_AVAILABLE = False


class LogLevel(Enum):
    """Enhanced logging levels"""
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class PerformanceMetric(Enum):
    """Performance metrics to track"""
    RESPONSE_TIME = "response_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    AVAILABILITY = "availability"
    DISK_USAGE = "disk_usage"
    NETWORK_LATENCY = "network_latency"
    MODEL_INFERENCE_TIME = "model_inference_time"
    CACHE_HIT_RATE = "cache_hit_rate"


class TrendDirection(Enum):
    """Trend direction for performance metrics"""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    VOLATILE = "volatile"


@dataclass
class PerformanceTrend:
    """Performance trend analysis"""
    metric: PerformanceMetric
    direction: TrendDirection
    change_rate: float  # Percentage change per hour
    confidence: float   # 0.0 to 1.0
    prediction: Optional[float] = None  # Predicted value in next hour
    recommendation: Optional[str] = None


@dataclass
class ErrorContext:
    """Context information for errors"""
    timestamp: str
    error_type: str
    error_message: str
    stack_trace: str
    component: str
    operation: str
    user_context: Optional[Dict] = None
    system_state: Optional[Dict] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False


@dataclass
class PerformanceSample:
    """Performance measurement sample"""
    timestamp: str
    metric: PerformanceMetric
    value: float
    component: str
    operation: str
    context: Optional[Dict] = None


@dataclass
class HealthCheck:
    """System health check result"""
    component: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    timestamp: str
    metrics: Dict[str, Any]
    recommendations: List[str]


class ProductionMonitor:
    """
    Production readiness monitor for AICleaner
    
    Features:
    - Enhanced error handling with context capture
    - Comprehensive logging with structured output
    - Performance benchmarking and monitoring
    - System health checks
    - Automatic recovery mechanisms
    - Debug information collection
    - Production metrics dashboard
    """
    
    def __init__(self, data_path: str = "/data/production"):
        """
        Initialize production monitor
        
        Args:
            data_path: Path to store production monitoring data
        """
        self.data_path = data_path
        self.logger = self._setup_enhanced_logging()
        
        # Ensure data directory exists
        os.makedirs(data_path, exist_ok=True)
        
        # Error tracking
        self.error_history = deque(maxlen=1000)  # Keep last 1000 errors
        self.error_counts = defaultdict(int)
        self.recovery_strategies = {}
        
        # Performance tracking
        self.performance_history = deque(maxlen=10000)  # Keep last 10k samples
        self.performance_baselines = {}
        self.performance_alerts = []
        
        # Health monitoring
        self.health_checks = {}
        self.system_metrics = {}

        # Advanced monitoring components
        self.resource_monitor = None
        self.alert_manager = None

        # Trend analysis
        self.trend_analysis_enabled = True
        self.trend_history = defaultdict(list)  # metric -> list of values
        self.performance_trends = {}

        # Predictive monitoring
        self.prediction_models = {}
        self.anomaly_detection_enabled = True
        self.baseline_metrics = {}

        # Advanced performance tracking
        self.component_performance = defaultdict(lambda: defaultdict(list))
        self.operation_timings = defaultdict(list)
        self.resource_utilization_history = deque(maxlen=1000)
        
        # Initialize advanced monitoring if available
        if ADVANCED_MONITORING_AVAILABLE:
            self._initialize_advanced_monitoring()

        # Monitoring thread
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()

        self.logger.info("Production Monitor initialized")
    
    def _setup_enhanced_logging(self) -> logging.Logger:
        """Setup enhanced logging with structured output"""
        logger = logging.getLogger(f"{__name__}.production")
        
        # Create formatter for structured logging
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s'
        )
        
        # File handler for production logs
        log_file = os.path.join(self.data_path, "production.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # Error file handler
        error_log_file = os.path.join(self.data_path, "errors.log")
        error_handler = logging.FileHandler(error_log_file)
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        
        logger.addHandler(file_handler)
        logger.addHandler(error_handler)
        logger.setLevel(logging.DEBUG)
        
        return logger
    
    def capture_error(self, error: Exception, component: str, operation: str, 
                     user_context: Optional[Dict] = None) -> ErrorContext:
        """
        Capture comprehensive error information
        
        Args:
            error: The exception that occurred
            component: Component where error occurred
            operation: Operation being performed
            user_context: User-specific context
            
        Returns:
            ErrorContext with full error information
        """
        error_context = ErrorContext(
            timestamp=datetime.now(timezone.utc).isoformat(),
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            component=component,
            operation=operation,
            user_context=user_context,
            system_state=self._capture_system_state()
        )
        
        # Store error
        self.error_history.append(error_context)
        self.error_counts[f"{component}.{operation}"] += 1
        
        # Log with full context
        self.logger.error(
            f"Error in {component}.{operation}: {error_context.error_message}",
            extra={
                'component': component,
                'operation': operation,
                'error_type': error_context.error_type,
                'user_context': user_context,
                'system_state': error_context.system_state
            }
        )
        
        # Attempt recovery if strategy exists
        recovery_strategy = self.recovery_strategies.get(f"{component}.{operation}")
        if recovery_strategy:
            try:
                error_context.recovery_attempted = True
                recovery_strategy(error_context)
                error_context.recovery_successful = True
                self.logger.info(f"Recovery successful for {component}.{operation}")
            except Exception as recovery_error:
                self.logger.error(f"Recovery failed for {component}.{operation}: {recovery_error}")
        
        return error_context
    
    def _capture_system_state(self) -> Dict[str, Any]:
        """Capture current system state for debugging"""
        try:
            return {
                'memory_usage': psutil.virtual_memory()._asdict(),
                'cpu_usage': psutil.cpu_percent(interval=0.1),
                'disk_usage': psutil.disk_usage('/')._asdict(),
                'process_count': len(psutil.pids()),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {'error': f"Failed to capture system state: {e}"}
    
    def register_recovery_strategy(self, component: str, operation: str, 
                                 strategy: Callable[[ErrorContext], None]):
        """Register automatic recovery strategy for specific errors"""
        key = f"{component}.{operation}"
        self.recovery_strategies[key] = strategy
        self.logger.info(f"Registered recovery strategy for {key}")
    
    def performance_monitor(self, component: str, operation: str):
        """Decorator for performance monitoring"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Record successful execution metrics
                    end_time = time.time()
                    end_memory = psutil.Process().memory_info().rss
                    
                    self.record_performance(
                        PerformanceMetric.RESPONSE_TIME,
                        end_time - start_time,
                        component,
                        operation
                    )
                    
                    self.record_performance(
                        PerformanceMetric.MEMORY_USAGE,
                        end_memory - start_memory,
                        component,
                        operation
                    )
                    
                    return result
                    
                except Exception as e:
                    # Record error and re-raise
                    self.capture_error(e, component, operation)
                    raise
                    
            return wrapper
        return decorator
    
    def record_performance(self, metric: PerformanceMetric, value: float, 
                          component: str, operation: str, context: Optional[Dict] = None):
        """Record a performance measurement"""
        sample = PerformanceSample(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric=metric,
            value=value,
            component=component,
            operation=operation,
            context=context
        )
        
        self.performance_history.append(sample)
        
        # Check against baselines and alert if needed
        self._check_performance_baseline(sample)

        # Advanced monitoring: trend analysis and anomaly detection
        if ADVANCED_MONITORING_AVAILABLE:
            self._update_trend_analysis(sample)
            self._detect_anomalies(sample)

    def _initialize_advanced_monitoring(self):
        """Initialize advanced monitoring components."""
        try:
            # Initialize resource monitor
            self.resource_monitor = ResourceMonitor({"performance_optimization": {}})

            # Initialize alert manager
            self.alert_manager = AlertManager({"performance_optimization": {}})

            # Start advanced monitoring
            asyncio.create_task(self._start_advanced_monitoring())

            self.logger.info("Advanced monitoring components initialized")

        except Exception as e:
            self.logger.error(f"Error initializing advanced monitoring: {e}")

    async def _start_advanced_monitoring(self):
        """Start advanced monitoring components."""
        try:
            if self.resource_monitor:
                await self.resource_monitor.start_monitoring(interval=30)

            if self.alert_manager:
                await self.alert_manager.start()

        except Exception as e:
            self.logger.error(f"Error starting advanced monitoring: {e}")

    def get_performance_trends(self) -> Dict[str, PerformanceTrend]:
        """Get current performance trends analysis."""
        return self.performance_trends.copy()

    def get_predictive_insights(self) -> Dict[str, Any]:
        """Get predictive insights based on historical data."""
        insights = {
            "trends": self.get_performance_trends(),
            "predictions": {},
            "recommendations": [],
            "risk_assessment": "low"
        }

        try:
            # Analyze trends for predictions
            for metric, trend in self.performance_trends.items():
                if trend.prediction is not None:
                    insights["predictions"][metric] = {
                        "predicted_value": trend.prediction,
                        "confidence": trend.confidence,
                        "direction": trend.direction.value
                    }

                # Generate recommendations based on trends
                if trend.direction == TrendDirection.DEGRADING and trend.confidence > 0.7:
                    insights["recommendations"].append(
                        f"Performance degradation detected in {metric}. "
                        f"Consider optimization or resource scaling."
                    )
                    if insights["risk_assessment"] == "low":
                        insights["risk_assessment"] = "medium"

                if trend.direction == TrendDirection.VOLATILE and trend.confidence > 0.8:
                    insights["recommendations"].append(
                        f"High volatility in {metric}. "
                        f"Investigate potential instability causes."
                    )
                    insights["risk_assessment"] = "high"

            return insights

        except Exception as e:
            self.logger.error(f"Error generating predictive insights: {e}")
            return insights

    def _update_trend_analysis(self, sample: PerformanceSample):
        """Update trend analysis with new performance sample."""
        try:
            metric_key = f"{sample.component}.{sample.operation}.{sample.metric.value}"

            # Add to trend history
            self.trend_history[metric_key].append({
                "timestamp": time.time(),
                "value": sample.value
            })

            # Keep only recent history (last 24 hours)
            cutoff_time = time.time() - 86400  # 24 hours
            self.trend_history[metric_key] = [
                entry for entry in self.trend_history[metric_key]
                if entry["timestamp"] > cutoff_time
            ]

            # Analyze trend if we have enough data points
            if len(self.trend_history[metric_key]) >= 10:
                trend = self._analyze_trend(metric_key, self.trend_history[metric_key])
                self.performance_trends[metric_key] = trend

        except Exception as e:
            self.logger.error(f"Error updating trend analysis: {e}")

    def _analyze_trend(self, metric_key: str, history: List[Dict]) -> PerformanceTrend:
        """Analyze trend for a specific metric."""
        try:
            if len(history) < 2:
                return PerformanceTrend(
                    metric=PerformanceMetric.RESPONSE_TIME,  # Default
                    direction=TrendDirection.STABLE,
                    change_rate=0.0,
                    confidence=0.0
                )

            # Extract values and timestamps
            values = [entry["value"] for entry in history]
            timestamps = [entry["timestamp"] for entry in history]

            # Calculate linear regression for trend
            n = len(values)
            sum_x = sum(timestamps)
            sum_y = sum(values)
            sum_xy = sum(t * v for t, v in zip(timestamps, values))
            sum_x2 = sum(t * t for t in timestamps)

            # Slope calculation
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

            # Convert slope to percentage change per hour
            time_range = timestamps[-1] - timestamps[0]
            if time_range > 0:
                change_rate = (slope * 3600 / statistics.mean(values)) * 100  # % per hour
            else:
                change_rate = 0.0

            # Determine trend direction
            if abs(change_rate) < 1.0:  # Less than 1% change per hour
                direction = TrendDirection.STABLE
            elif change_rate > 0:
                direction = TrendDirection.DEGRADING if "time" in metric_key.lower() else TrendDirection.IMPROVING
            else:
                direction = TrendDirection.IMPROVING if "time" in metric_key.lower() else TrendDirection.DEGRADING

            # Calculate confidence based on R-squared
            mean_y = statistics.mean(values)
            ss_tot = sum((y - mean_y) ** 2 for y in values)
            ss_res = sum((y - (slope * x + (sum_y - slope * sum_x) / n)) ** 2
                        for x, y in zip(timestamps, values))

            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            confidence = max(0.0, min(1.0, r_squared))

            # Check for volatility
            if statistics.stdev(values) > statistics.mean(values) * 0.3:  # High coefficient of variation
                direction = TrendDirection.VOLATILE

            # Simple prediction (linear extrapolation)
            current_time = time.time()
            prediction = slope * current_time + (sum_y - slope * sum_x) / n

            return PerformanceTrend(
                metric=PerformanceMetric.RESPONSE_TIME,  # This should be parsed from metric_key
                direction=direction,
                change_rate=change_rate,
                confidence=confidence,
                prediction=prediction,
                recommendation=self._generate_trend_recommendation(direction, change_rate, confidence)
            )

        except Exception as e:
            self.logger.error(f"Error analyzing trend for {metric_key}: {e}")
            return PerformanceTrend(
                metric=PerformanceMetric.RESPONSE_TIME,
                direction=TrendDirection.STABLE,
                change_rate=0.0,
                confidence=0.0
            )

    def _generate_trend_recommendation(self, direction: TrendDirection, change_rate: float, confidence: float) -> str:
        """Generate recommendation based on trend analysis."""
        if confidence < 0.5:
            return "Insufficient data for reliable recommendation"

        if direction == TrendDirection.DEGRADING:
            if abs(change_rate) > 10:
                return "Critical: Rapid performance degradation detected. Immediate investigation required."
            elif abs(change_rate) > 5:
                return "Warning: Performance degradation trend. Consider optimization."
            else:
                return "Monitor: Slight performance degradation trend detected."

        elif direction == TrendDirection.VOLATILE:
            return "Alert: High performance volatility. Investigate system stability."

        elif direction == TrendDirection.IMPROVING:
            return "Good: Performance improvement trend detected."

        else:
            return "Stable: Performance within normal parameters."

    def _detect_anomalies(self, sample: PerformanceSample):
        """Detect performance anomalies using statistical methods."""
        try:
            if not self.anomaly_detection_enabled:
                return

            metric_key = f"{sample.component}.{sample.operation}.{sample.metric.value}"

            # Get recent history for baseline
            if metric_key in self.trend_history and len(self.trend_history[metric_key]) >= 20:
                recent_values = [entry["value"] for entry in self.trend_history[metric_key][-20:]]

                mean_val = statistics.mean(recent_values)
                std_val = statistics.stdev(recent_values) if len(recent_values) > 1 else 0

                # Z-score anomaly detection
                if std_val > 0:
                    z_score = abs(sample.value - mean_val) / std_val

                    # Alert if value is more than 3 standard deviations from mean
                    if z_score > 3:
                        self._handle_anomaly_detection(sample, z_score, mean_val, std_val)

        except Exception as e:
            self.logger.error(f"Error in anomaly detection: {e}")

    def _handle_anomaly_detection(self, sample: PerformanceSample, z_score: float, mean_val: float, std_val: float):
        """Handle detected performance anomaly."""
        try:
            anomaly_message = (
                f"Performance anomaly detected in {sample.component}.{sample.operation}: "
                f"{sample.metric.value} = {sample.value:.2f} "
                f"(Z-score: {z_score:.2f}, Mean: {mean_val:.2f}, StdDev: {std_val:.2f})"
            )

            self.logger.warning(anomaly_message)

            # Create alert if alert manager is available
            if self.alert_manager and ADVANCED_MONITORING_AVAILABLE:
                alert = ResourceAlert(
                    alert_id=f"anomaly_{int(time.time())}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    resource_type=ResourceType.PROCESS,
                    alert_level=AlertLevel.WARNING if z_score < 4 else AlertLevel.CRITICAL,
                    message=anomaly_message,
                    current_value=sample.value,
                    threshold_value=mean_val + 3 * std_val,
                    metadata={"z_score": z_score, "component": sample.component, "operation": sample.operation}
                )

                asyncio.create_task(self.alert_manager.process_resource_alert(alert))

        except Exception as e:
            self.logger.error(f"Error handling anomaly detection: {e}")

    def _check_performance_baseline(self, sample: PerformanceSample):
        """Check performance against established baselines"""
        key = f"{sample.component}.{sample.operation}.{sample.metric.value}"
        
        if key in self.performance_baselines:
            baseline = self.performance_baselines[key]
            threshold = baseline * 2.0  # Alert if 2x slower than baseline
            
            if sample.value > threshold:
                alert = {
                    'timestamp': sample.timestamp,
                    'component': sample.component,
                    'operation': sample.operation,
                    'metric': sample.metric.value,
                    'value': sample.value,
                    'baseline': baseline,
                    'threshold': threshold,
                    'severity': 'warning' if sample.value < threshold * 1.5 else 'critical'
                }
                
                self.performance_alerts.append(alert)
                self.logger.warning(f"Performance alert: {key} = {sample.value:.3f} (baseline: {baseline:.3f})")
    
    def establish_performance_baseline(self, component: str, operation: str, 
                                     metric: PerformanceMetric, samples: int = 100):
        """Establish performance baseline from recent samples"""
        key = f"{component}.{operation}.{metric.value}"
        
        # Get recent samples for this metric
        recent_samples = [
            s.value for s in self.performance_history
            if (s.component == component and s.operation == operation and 
                s.metric == metric)
        ][-samples:]
        
        if len(recent_samples) >= 10:  # Need at least 10 samples
            import statistics
            baseline = statistics.median(recent_samples)
            self.performance_baselines[key] = baseline
            self.logger.info(f"Established baseline for {key}: {baseline:.3f}")
            return baseline
        
        return None

    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                self._collect_system_metrics()

                # Run health checks
                self._run_health_checks()

                # Clean up old data
                self._cleanup_old_data()

                # Sleep for monitoring interval
                time.sleep(60)  # Monitor every minute

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)

    def _collect_system_metrics(self):
        """Collect system-wide metrics"""
        try:
            self.system_metrics = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'memory': psutil.virtual_memory()._asdict(),
                'cpu': {
                    'percent': psutil.cpu_percent(interval=1),
                    'count': psutil.cpu_count(),
                    'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else None
                },
                'disk': psutil.disk_usage('/')._asdict(),
                'network': psutil.net_io_counters()._asdict(),
                'processes': len(psutil.pids()),
                'uptime': time.time() - psutil.boot_time()
            }
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")

    def _run_health_checks(self):
        """Run all registered health checks"""
        for check_name, check_func in self.health_checks.items():
            try:
                result = check_func()
                if isinstance(result, HealthCheck):
                    self.logger.debug(f"Health check {check_name}: {result.status}")
                    if result.status != "healthy":
                        self.logger.warning(f"Health check {check_name} failed: {result.message}")
            except Exception as e:
                self.logger.error(f"Health check {check_name} failed with exception: {e}")

    def register_health_check(self, name: str, check_func: Callable[[], HealthCheck]):
        """Register a health check function"""
        self.health_checks[name] = check_func
        self.logger.info(f"Registered health check: {name}")

    def _cleanup_old_data(self):
        """Clean up old monitoring data"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)
        cutoff_str = cutoff_time.isoformat()

        # Clean up old performance alerts
        self.performance_alerts = [
            alert for alert in self.performance_alerts
            if alert['timestamp'] > cutoff_str
        ]

    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the last N hours"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_str = cutoff_time.isoformat()

        recent_errors = [
            error for error in self.error_history
            if error.timestamp > cutoff_str
        ]

        # Group errors by component and type
        error_groups = defaultdict(list)
        for error in recent_errors:
            key = f"{error.component}.{error.error_type}"
            error_groups[key].append(error)

        # Calculate error rates
        error_rates = {}
        for key, errors in error_groups.items():
            error_rates[key] = {
                'count': len(errors),
                'rate_per_hour': len(errors) / hours,
                'recovery_rate': sum(1 for e in errors if e.recovery_successful) / len(errors) if errors else 0
            }

        return {
            'total_errors': len(recent_errors),
            'unique_error_types': len(error_groups),
            'error_rates': error_rates,
            'most_common_errors': sorted(error_rates.items(), key=lambda x: x[1]['count'], reverse=True)[:5],
            'recovery_success_rate': sum(1 for e in recent_errors if e.recovery_successful) / len(recent_errors) if recent_errors else 0,
            'time_period_hours': hours
        }

    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the last N hours"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_str = cutoff_time.isoformat()

        recent_samples = [
            sample for sample in self.performance_history
            if sample.timestamp > cutoff_str
        ]

        # Group by metric type
        metric_groups = defaultdict(list)
        for sample in recent_samples:
            key = f"{sample.component}.{sample.operation}.{sample.metric.value}"
            metric_groups[key].append(sample.value)

        # Calculate statistics
        import statistics
        metric_stats = {}
        for key, values in metric_groups.items():
            if values:
                metric_stats[key] = {
                    'count': len(values),
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'min': min(values),
                    'max': max(values),
                    'stdev': statistics.stdev(values) if len(values) > 1 else 0
                }

        return {
            'total_samples': len(recent_samples),
            'metric_statistics': metric_stats,
            'performance_alerts': [
                alert for alert in self.performance_alerts
                if alert['timestamp'] > cutoff_str
            ],
            'baselines_established': len(self.performance_baselines),
            'time_period_hours': hours
        }

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        # Run immediate health checks
        health_results = {}
        for check_name, check_func in self.health_checks.items():
            try:
                result = check_func()
                health_results[check_name] = asdict(result) if isinstance(result, HealthCheck) else result
            except Exception as e:
                health_results[check_name] = {
                    'status': 'unhealthy',
                    'message': f"Health check failed: {e}",
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }

        # Determine overall health
        statuses = [result.get('status', 'unknown') for result in health_results.values()]
        if 'unhealthy' in statuses:
            overall_status = 'unhealthy'
        elif 'degraded' in statuses:
            overall_status = 'degraded'
        elif 'healthy' in statuses:
            overall_status = 'healthy'
        else:
            overall_status = 'unknown'

        return {
            'overall_status': overall_status,
            'health_checks': health_results,
            'system_metrics': self.system_metrics,
            'error_summary': self.get_error_summary(1),  # Last hour
            'performance_summary': self.get_performance_summary(1),  # Last hour
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def export_diagnostics(self) -> Dict[str, Any]:
        """Export comprehensive diagnostic information"""
        return {
            'system_info': {
                'platform': os.name,
                'python_version': os.sys.version,
                'process_id': os.getpid(),
                'working_directory': os.getcwd(),
                'data_path': self.data_path
            },
            'monitoring_status': {
                'monitoring_active': self.monitoring_active,
                'error_history_size': len(self.error_history),
                'performance_history_size': len(self.performance_history),
                'health_checks_registered': len(self.health_checks),
                'recovery_strategies_registered': len(self.recovery_strategies)
            },
            'recent_errors': [asdict(error) for error in list(self.error_history)[-10:]],
            'recent_performance': [asdict(sample) for sample in list(self.performance_history)[-50:]],
            'system_health': self.get_system_health(),
            'export_timestamp': datetime.now(timezone.utc).isoformat()
        }

    def shutdown(self):
        """Shutdown the production monitor"""
        self.monitoring_active = False
        if self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        self.logger.info("Production Monitor shutdown complete")
