"""
Enhanced Logging Manager for AICleaner v3
Phase 1C: Logging System Enhancement

This module provides the main logging manager that coordinates all log handlers,
implements log analysis, alerting, and provides a unified interface for logging
throughout the application.

Key Features:
- Centralized log management
- Real-time log streaming
- Log analysis and pattern detection
- Alerting and notification system
- Performance monitoring integration
- Configuration-driven logging setup
"""

import asyncio
import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Set, Tuple
import weakref
import psutil
import queue
from concurrent.futures import ThreadPoolExecutor

from .enhanced_logging import (
    LogLevel, LogCategory, LogOrigin, LogContext, LogEntry, LogFilter,
    LogHandler, FileLogHandler, ConsoleLogHandler, HomeAssistantLogHandler,
    SecurityLogHandler, PerformanceLogHandler
)


@dataclass
class LoggingConfig:
    """Logging system configuration"""
    log_directory: str = "logs"
    max_log_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    compression: bool = True
    console_logging: bool = True
    file_logging: bool = True
    ha_logging: bool = True
    security_logging: bool = True
    performance_logging: bool = True
    log_level: LogLevel = LogLevel.INFO
    buffer_size: int = 1000
    flush_interval: float = 5.0
    enable_analysis: bool = True
    enable_alerting: bool = True
    analysis_window: int = 300  # 5 minutes
    alert_thresholds: Dict[str, Any] = field(default_factory=lambda: {
        "error_rate": 0.1,  # 10% error rate
        "critical_count": 5,  # 5 critical errors
        "memory_usage": 500 * 1024 * 1024,  # 500MB
        "disk_usage": 0.9  # 90% disk usage
    })


@dataclass
class LogAlert:
    """Log alert information"""
    alert_id: str
    alert_type: str
    severity: LogLevel
    message: str
    timestamp: datetime
    context: LogContext
    metrics: Dict[str, Any]
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class LogAnalysis:
    """Log analysis results"""
    time_window: timedelta
    total_entries: int
    entries_by_level: Dict[LogLevel, int]
    entries_by_category: Dict[LogCategory, int]
    entries_by_component: Dict[str, int]
    error_patterns: List[Dict[str, Any]]
    performance_summary: Dict[str, Any]
    security_events: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]
    trends: Dict[str, Any]


class LogStream:
    """Real-time log streaming"""
    
    def __init__(self, name: str, log_filter: LogFilter = None):
        self.name = name
        self.filter = log_filter or LogFilter()
        self.subscribers: Set[Callable[[LogEntry], None]] = set()
        self.buffer = deque(maxlen=100)
        self.lock = threading.Lock()
    
    def subscribe(self, callback: Callable[[LogEntry], None]):
        """Subscribe to log stream"""
        with self.lock:
            self.subscribers.add(callback)
    
    def unsubscribe(self, callback: Callable[[LogEntry], None]):
        """Unsubscribe from log stream"""
        with self.lock:
            self.subscribers.discard(callback)
    
    def should_stream(self, entry: LogEntry) -> bool:
        """Check if entry should be streamed"""
        # Use same filtering logic as handlers
        if entry.level.value < self.filter.min_level.value:
            return False
        if self.filter.categories and entry.context.category not in self.filter.categories:
            return False
        if self.filter.components and entry.context.component not in self.filter.components:
            return False
        return True
    
    async def stream_entry(self, entry: LogEntry):
        """Stream log entry to subscribers"""
        if not self.should_stream(entry):
            return
        
        with self.lock:
            self.buffer.append(entry)
            subscribers = self.subscribers.copy()
        
        # Notify subscribers
        for callback in subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(entry)
                else:
                    callback(entry)
            except Exception:
                # Remove failed callback
                with self.lock:
                    self.subscribers.discard(callback)


class LogAnalyzer:
    """Log analysis and pattern detection"""
    
    def __init__(self, analysis_window: int = 300):
        self.analysis_window = timedelta(seconds=analysis_window)
        self.entry_buffer = deque()
        self.error_patterns = defaultdict(int)
        self.performance_trends = defaultdict(list)
        self.security_events = []
        self.anomaly_detectors = []
        self.lock = threading.Lock()
    
    def add_entry(self, entry: LogEntry):
        """Add log entry for analysis"""
        with self.lock:
            # Add to buffer
            self.entry_buffer.append(entry)
            
            # Clean old entries
            cutoff_time = datetime.now() - self.analysis_window
            while (self.entry_buffer and 
                   self.entry_buffer[0].timestamp < cutoff_time):
                self.entry_buffer.popleft()
            
            # Update patterns
            self._update_patterns(entry)
            
            # Track performance trends
            self._update_performance_trends(entry)
            
            # Track security events
            self._track_security_events(entry)
    
    def _update_patterns(self, entry: LogEntry):
        """Update error patterns"""
        if entry.level.value >= LogLevel.ERROR.value:
            # Create pattern key
            pattern_key = f"{entry.context.component}:{entry.context.operation}"
            self.error_patterns[pattern_key] += 1
    
    def _update_performance_trends(self, entry: LogEntry):
        """Update performance trends"""
        if entry.performance_metrics:
            component = entry.context.component or "unknown"
            metrics = entry.performance_metrics
            
            for metric_name, value in metrics.items():
                if isinstance(value, (int, float)):
                    trend_key = f"{component}:{metric_name}"
                    self.performance_trends[trend_key].append({
                        "timestamp": entry.timestamp,
                        "value": value
                    })
                    
                    # Keep only recent data
                    cutoff_time = datetime.now() - self.analysis_window
                    self.performance_trends[trend_key] = [
                        point for point in self.performance_trends[trend_key]
                        if point["timestamp"] > cutoff_time
                    ]
    
    def _track_security_events(self, entry: LogEntry):
        """Track security events"""
        if entry.context.category == LogCategory.SECURITY:
            security_event = {
                "timestamp": entry.timestamp,
                "message": entry.message,
                "component": entry.context.component,
                "security_context": entry.security_context,
                "correlation_id": entry.context.correlation_id
            }
            self.security_events.append(security_event)
            
            # Keep only recent events
            cutoff_time = datetime.now() - self.analysis_window
            self.security_events = [
                event for event in self.security_events
                if event["timestamp"] > cutoff_time
            ]
    
    def analyze(self) -> LogAnalysis:
        """Perform comprehensive log analysis"""
        with self.lock:
            entries = list(self.entry_buffer)
        
        if not entries:
            return LogAnalysis(
                time_window=self.analysis_window,
                total_entries=0,
                entries_by_level={},
                entries_by_category={},
                entries_by_component={},
                error_patterns=[],
                performance_summary={},
                security_events=[],
                anomalies=[],
                trends={}
            )
        
        # Count entries by level
        entries_by_level = defaultdict(int)
        for entry in entries:
            entries_by_level[entry.level] += 1
        
        # Count entries by category
        entries_by_category = defaultdict(int)
        for entry in entries:
            entries_by_category[entry.context.category] += 1
        
        # Count entries by component
        entries_by_component = defaultdict(int)
        for entry in entries:
            if entry.context.component:
                entries_by_component[entry.context.component] += 1
        
        # Extract error patterns
        error_patterns = [
            {"pattern": pattern, "count": count}
            for pattern, count in sorted(
                self.error_patterns.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
        ]
        
        # Analyze performance trends
        performance_summary = self._analyze_performance_trends()
        
        # Detect anomalies
        anomalies = self._detect_anomalies()
        
        # Calculate trends
        trends = self._calculate_trends(entries)
        
        return LogAnalysis(
            time_window=self.analysis_window,
            total_entries=len(entries),
            entries_by_level=dict(entries_by_level),
            entries_by_category=dict(entries_by_category),
            entries_by_component=dict(entries_by_component),
            error_patterns=error_patterns,
            performance_summary=performance_summary,
            security_events=list(self.security_events),
            anomalies=anomalies,
            trends=trends
        )
    
    def _analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends"""
        summary = {}
        
        for trend_key, data_points in self.performance_trends.items():
            if len(data_points) < 2:
                continue
            
            values = [point["value"] for point in data_points]
            
            summary[trend_key] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1],
                "trend": "increasing" if values[-1] > values[0] else "decreasing"
            }
        
        return summary
    
    def _detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalies in log patterns"""
        anomalies = []
        
        # Check for error rate spikes
        recent_entries = [
            entry for entry in self.entry_buffer
            if entry.timestamp > datetime.now() - timedelta(minutes=5)
        ]
        
        if recent_entries:
            error_count = sum(
                1 for entry in recent_entries
                if entry.level.value >= LogLevel.ERROR.value
            )
            error_rate = error_count / len(recent_entries)
            
            if error_rate > 0.2:  # 20% error rate
                anomalies.append({
                    "type": "high_error_rate",
                    "description": f"Error rate of {error_rate:.2%} detected",
                    "severity": LogLevel.WARNING,
                    "timestamp": datetime.now()
                })
        
        # Check for performance degradation
        for trend_key, data_points in self.performance_trends.items():
            if "response_time" in trend_key and len(data_points) >= 5:
                recent_values = [point["value"] for point in data_points[-5:]]
                avg_recent = sum(recent_values) / len(recent_values)
                
                if len(data_points) >= 10:
                    older_values = [point["value"] for point in data_points[-10:-5]]
                    avg_older = sum(older_values) / len(older_values)
                    
                    if avg_recent > avg_older * 1.5:  # 50% increase
                        anomalies.append({
                            "type": "performance_degradation",
                            "description": f"Response time increased by {((avg_recent/avg_older)-1)*100:.1f}% for {trend_key}",
                            "severity": LogLevel.WARNING,
                            "timestamp": datetime.now()
                        })
        
        return anomalies
    
    def _calculate_trends(self, entries: List[LogEntry]) -> Dict[str, Any]:
        """Calculate logging trends"""
        if len(entries) < 2:
            return {}
        
        # Calculate time-based trends
        time_buckets = defaultdict(int)
        bucket_size = timedelta(minutes=1)
        
        for entry in entries:
            bucket_time = entry.timestamp.replace(second=0, microsecond=0)
            time_buckets[bucket_time] += 1
        
        # Calculate rate trends
        bucket_times = sorted(time_buckets.keys())
        if len(bucket_times) >= 2:
            recent_rate = time_buckets[bucket_times[-1]]
            avg_rate = sum(time_buckets.values()) / len(time_buckets)
            
            return {
                "log_rate_trend": "increasing" if recent_rate > avg_rate else "decreasing",
                "current_rate": recent_rate,
                "average_rate": avg_rate,
                "rate_change": (recent_rate - avg_rate) / max(avg_rate, 1)
            }
        
        return {}


class LoggingManager:
    """Enhanced logging manager"""
    
    def __init__(self, config: LoggingConfig = None):
        self.config = config or LoggingConfig()
        self.handlers: Dict[str, LogHandler] = {}
        self.streams: Dict[str, LogStream] = {}
        self.analyzer = LogAnalyzer(self.config.analysis_window)
        self.alerts: List[LogAlert] = []
        self.alert_callbacks: Set[Callable[[LogAlert], None]] = set()
        
        # Threading and async management
        self.log_queue = queue.Queue(maxsize=self.config.buffer_size)
        self.worker_thread = None
        self.shutdown_event = threading.Event()
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="LogWorker")
        
        # Statistics
        self.stats = {
            "total_logs": 0,
            "logs_by_level": defaultdict(int),
            "logs_by_component": defaultdict(int),
            "errors": 0,
            "last_flush": datetime.now()
        }
        
        # Initialize logging system
        self._setup_logging()
        self._start_worker()
    
    def _setup_logging(self):
        """Setup logging handlers"""
        log_dir = Path(self.config.log_directory)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Console handler
        if self.config.console_logging:
            console_filter = LogFilter(min_level=self.config.log_level)
            self.handlers["console"] = ConsoleLogHandler(
                "console", colored=True, log_filter=console_filter
            )
        
        # File handler
        if self.config.file_logging:
            file_filter = LogFilter(min_level=LogLevel.DEBUG)
            self.handlers["file"] = FileLogHandler(
                "file",
                str(log_dir / "aicleaner.log"),
                max_size=self.config.max_log_size,
                backup_count=self.config.backup_count,
                compression=self.config.compression,
                log_filter=file_filter
            )
        
        # Home Assistant handler
        if self.config.ha_logging:
            ha_filter = LogFilter(min_level=self.config.log_level)
            self.handlers["home_assistant"] = HomeAssistantLogHandler(
                "home_assistant", log_filter=ha_filter
            )
        
        # Security handler
        if self.config.security_logging:
            security_filter = LogFilter(
                categories={LogCategory.SECURITY, LogCategory.AUDIT}
            )
            self.handlers["security"] = SecurityLogHandler(
                "security",
                str(log_dir / "security.log"),
                log_filter=security_filter
            )
        
        # Performance handler
        if self.config.performance_logging:
            perf_filter = LogFilter(categories={LogCategory.PERFORMANCE})
            self.handlers["performance"] = PerformanceLogHandler(
                "performance",
                str(log_dir / "performance.log"),
                log_filter=perf_filter
            )
    
    def _start_worker(self):
        """Start background worker thread"""
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            name="LoggingWorker",
            daemon=True
        )
        self.worker_thread.start()
    
    def _worker_loop(self):
        """Main worker loop for processing log entries"""
        while not self.shutdown_event.is_set():
            try:
                # Get log entry with timeout
                try:
                    entry = self.log_queue.get(timeout=self.config.flush_interval)
                except queue.Empty:
                    continue
                
                # Process entry
                asyncio.run(self._process_log_entry(entry))
                self.log_queue.task_done()
                
            except Exception as e:
                print(f"Error in logging worker: {e}")
    
    async def _process_log_entry(self, entry: LogEntry):
        """Process a single log entry"""
        try:
            # Update statistics
            self.stats["total_logs"] += 1
            self.stats["logs_by_level"][entry.level] += 1
            if entry.context.component:
                self.stats["logs_by_component"][entry.context.component] += 1
            
            # Add to analyzer
            if self.config.enable_analysis:
                self.analyzer.add_entry(entry)
            
            # Process through handlers
            tasks = []
            for handler in self.handlers.values():
                tasks.append(handler.handle_log(entry))
            
            # Process through streams
            for stream in self.streams.values():
                tasks.append(stream.stream_entry(entry))
            
            # Wait for all handlers to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for alerts
            if self.config.enable_alerting:
                await self._check_alerts(entry)
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Error processing log entry: {e}")
    
    async def _check_alerts(self, entry: LogEntry):
        """Check if log entry should trigger alerts"""
        alerts_to_fire = []
        
        # Critical error alert
        if entry.level == LogLevel.CRITICAL:
            alert = LogAlert(
                alert_id=f"critical_{entry.context.correlation_id}",
                alert_type="critical_error",
                severity=LogLevel.CRITICAL,
                message=f"Critical error in {entry.context.component}: {entry.message}",
                timestamp=entry.timestamp,
                context=entry.context,
                metrics={"error_level": "critical"}
            )
            alerts_to_fire.append(alert)
        
        # Security event alert
        if entry.context.category == LogCategory.SECURITY:
            alert = LogAlert(
                alert_id=f"security_{entry.context.correlation_id}",
                alert_type="security_event",
                severity=LogLevel.ERROR,
                message=f"Security event: {entry.message}",
                timestamp=entry.timestamp,
                context=entry.context,
                metrics=entry.security_context or {}
            )
            alerts_to_fire.append(alert)
        
        # Performance degradation alert
        if (entry.performance_metrics and 
            "response_time" in entry.performance_metrics):
            response_time = entry.performance_metrics["response_time"]
            if response_time > 5000:  # 5 seconds
                alert = LogAlert(
                    alert_id=f"perf_{entry.context.correlation_id}",
                    alert_type="performance_degradation",
                    severity=LogLevel.WARNING,
                    message=f"Slow response time: {response_time}ms in {entry.context.component}",
                    timestamp=entry.timestamp,
                    context=entry.context,
                    metrics={"response_time": response_time}
                )
                alerts_to_fire.append(alert)
        
        # Fire alerts
        for alert in alerts_to_fire:
            await self._fire_alert(alert)
    
    async def _fire_alert(self, alert: LogAlert):
        """Fire an alert"""
        self.alerts.append(alert)
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception:
                # Remove failed callback
                self.alert_callbacks.discard(callback)
    
    def log(self, level: LogLevel, message: str, context: LogContext = None,
            exception: Exception = None, performance_metrics: Dict[str, Any] = None,
            security_context: Dict[str, Any] = None):
        """Log a message"""
        try:
            # Create log context if not provided
            if context is None:
                context = LogContext()
            
            # Create log entry
            import inspect
            frame = inspect.currentframe().f_back
            
            entry = LogEntry(
                timestamp=datetime.now(),
                level=level,
                message=message,
                context=context,
                logger_name="aicleaner.enhanced",
                module=frame.f_globals.get("__name__", "unknown"),
                function=frame.f_code.co_name,
                line_number=frame.f_lineno,
                thread_id=threading.get_ident(),
                thread_name=threading.current_thread().name,
                process_id=os.getpid(),
                exception_info=str(exception) if exception else None,
                stack_trace=traceback.format_exc() if exception else None,
                performance_metrics=performance_metrics,
                security_context=security_context
            )
            
            # Add to queue
            try:
                self.log_queue.put_nowait(entry)
            except queue.Full:
                # Drop oldest entry and add new one
                try:
                    self.log_queue.get_nowait()
                    self.log_queue.put_nowait(entry)
                except queue.Empty:
                    pass
                
        except Exception as e:
            # Fallback logging
            print(f"Error in enhanced logging: {e}")
    
    def get_logger(self, component: str) -> 'ComponentLogger':
        """Get a component-specific logger"""
        return ComponentLogger(self, component)
    
    def create_stream(self, name: str, log_filter: LogFilter = None) -> LogStream:
        """Create a log stream"""
        stream = LogStream(name, log_filter)
        self.streams[name] = stream
        return stream
    
    def remove_stream(self, name: str):
        """Remove a log stream"""
        self.streams.pop(name, None)
    
    def add_alert_callback(self, callback: Callable[[LogAlert], None]):
        """Add alert callback"""
        self.alert_callbacks.add(callback)
    
    def remove_alert_callback(self, callback: Callable[[LogAlert], None]):
        """Remove alert callback"""
        self.alert_callbacks.discard(callback)
    
    def get_analysis(self) -> LogAnalysis:
        """Get current log analysis"""
        return self.analyzer.analyze()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        stats = self.stats.copy()
        
        # Add handler stats
        handler_stats = {}
        for name, handler in self.handlers.items():
            handler_stats[name] = handler.stats.copy()
        stats["handlers"] = handler_stats
        
        # Add queue stats
        stats["queue_size"] = self.log_queue.qsize()
        stats["queue_max_size"] = self.config.buffer_size
        
        return stats
    
    def shutdown(self):
        """Shutdown logging manager"""
        self.shutdown_event.set()
        
        # Drain queue
        while not self.log_queue.empty():
            try:
                self.log_queue.get_nowait()
            except queue.Empty:
                break
        
        # Wait for worker to finish
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5.0)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)


class ComponentLogger:
    """Component-specific logger wrapper"""
    
    def __init__(self, manager: LoggingManager, component: str):
        self.manager = manager
        self.component = component
    
    def _create_context(self, operation: str = None, **kwargs) -> LogContext:
        """Create log context for this component"""
        context = LogContext(component=self.component, operation=operation)
        
        # Add any additional context
        for key, value in kwargs.items():
            if hasattr(context, key):
                setattr(context, key, value)
            else:
                context.metadata[key] = value
        
        return context
    
    def trace(self, message: str, operation: str = None, **kwargs):
        """Log trace message"""
        context = self._create_context(operation, **kwargs)
        self.manager.log(LogLevel.TRACE, message, context)
    
    def debug(self, message: str, operation: str = None, **kwargs):
        """Log debug message"""
        context = self._create_context(operation, **kwargs)
        self.manager.log(LogLevel.DEBUG, message, context)
    
    def info(self, message: str, operation: str = None, **kwargs):
        """Log info message"""
        context = self._create_context(operation, **kwargs)
        self.manager.log(LogLevel.INFO, message, context)
    
    def warning(self, message: str, operation: str = None, **kwargs):
        """Log warning message"""
        context = self._create_context(operation, **kwargs)
        self.manager.log(LogLevel.WARNING, message, context)
    
    def error(self, message: str, operation: str = None, exception: Exception = None, **kwargs):
        """Log error message"""
        context = self._create_context(operation, **kwargs)
        self.manager.log(LogLevel.ERROR, message, context, exception=exception)
    
    def critical(self, message: str, operation: str = None, exception: Exception = None, **kwargs):
        """Log critical message"""
        context = self._create_context(operation, **kwargs)
        self.manager.log(LogLevel.CRITICAL, message, context, exception=exception)
    
    def security(self, message: str, operation: str = None, security_context: Dict[str, Any] = None, **kwargs):
        """Log security message"""
        context = self._create_context(operation, **kwargs)
        context.category = LogCategory.SECURITY
        self.manager.log(LogLevel.SECURITY, message, context, security_context=security_context)
    
    def audit(self, message: str, operation: str = None, **kwargs):
        """Log audit message"""
        context = self._create_context(operation, **kwargs)
        context.category = LogCategory.AUDIT
        self.manager.log(LogLevel.AUDIT, message, context)
    
    def performance(self, message: str, metrics: Dict[str, Any], operation: str = None, **kwargs):
        """Log performance message"""
        context = self._create_context(operation, **kwargs)
        context.category = LogCategory.PERFORMANCE
        self.manager.log(LogLevel.INFO, message, context, performance_metrics=metrics)


# Global logging manager instance
_logging_manager: Optional[LoggingManager] = None


def get_logging_manager() -> LoggingManager:
    """Get global logging manager instance"""
    global _logging_manager
    if _logging_manager is None:
        _logging_manager = LoggingManager()
    return _logging_manager


def get_logger(component: str) -> ComponentLogger:
    """Get component logger"""
    return get_logging_manager().get_logger(component)


# Convenience functions
def log_info(message: str, component: str = "system", **kwargs):
    """Log info message"""
    get_logger(component).info(message, **kwargs)


def log_error(message: str, component: str = "system", exception: Exception = None, **kwargs):
    """Log error message"""
    get_logger(component).error(message, exception=exception, **kwargs)


def log_security(message: str, component: str = "security", security_context: Dict[str, Any] = None, **kwargs):
    """Log security event"""
    get_logger(component).security(message, security_context=security_context, **kwargs)


def log_performance(message: str, metrics: Dict[str, Any], component: str = "performance", **kwargs):
    """Log performance metrics"""
    get_logger(component).performance(message, metrics, **kwargs)