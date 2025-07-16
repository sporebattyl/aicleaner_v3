"""
Configuration Performance Monitor and Benchmarking System
Phase 1A: Configuration Schema Consolidation

This module provides comprehensive performance monitoring and benchmarking
for configuration operations to ensure they meet the specified requirements.

Performance Requirements:
- Config loading: <200ms
- Migration: <5s
- Validation: <50ms per config
- 10 concurrent accesses: <500ms
- 3 simultaneous migrations: <150MB memory
- Migration memory usage: <100MB

Key Features:
- Real-time performance monitoring
- Benchmarking against target metrics
- Memory usage tracking
- Concurrent operation monitoring
- Performance alerting and reporting
"""

import logging
import time
import psutil
import threading
import statistics
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path
import concurrent.futures
from contextlib import contextmanager

class PerformanceMetric(Enum):
    """Performance metric types"""
    CONFIG_LOAD_TIME = "config_load_time"
    MIGRATION_TIME = "migration_time"
    VALIDATION_TIME = "validation_time"
    MEMORY_USAGE = "memory_usage"
    CONCURRENT_ACCESS = "concurrent_access"
    THROUGHPUT = "throughput"

class PerformanceThreshold(Enum):
    """Performance threshold levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class PerformanceMeasurement:
    """Individual performance measurement"""
    metric: PerformanceMetric
    value: float
    timestamp: datetime
    operation: str
    context: Dict[str, Any] = field(default_factory=dict)
    threshold_level: PerformanceThreshold = PerformanceThreshold.GOOD

@dataclass
class PerformanceBenchmark:
    """Performance benchmark results"""
    metric: PerformanceMetric
    measurements: List[PerformanceMeasurement] = field(default_factory=list)
    min_value: float = float('inf')
    max_value: float = float('-inf')
    avg_value: float = 0.0
    p95_value: float = 0.0
    p99_value: float = 0.0
    passed: bool = True
    target_value: float = 0.0
    threshold_level: PerformanceThreshold = PerformanceThreshold.GOOD

class ConfigPerformanceMonitor:
    """
    Configuration performance monitor and benchmarking system
    
    Provides comprehensive performance monitoring for configuration operations
    with real-time metrics, benchmarking, and alerting capabilities.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Performance targets (in milliseconds unless specified)
        self.performance_targets = {
            PerformanceMetric.CONFIG_LOAD_TIME: 200,
            PerformanceMetric.MIGRATION_TIME: 5000,
            PerformanceMetric.VALIDATION_TIME: 50,
            PerformanceMetric.CONCURRENT_ACCESS: 500,
            PerformanceMetric.MEMORY_USAGE: 150,  # MB
            PerformanceMetric.THROUGHPUT: 20  # operations per second
        }
        
        # Threshold levels (multipliers of target)
        self.threshold_multipliers = {
            PerformanceThreshold.EXCELLENT: 0.5,
            PerformanceThreshold.GOOD: 1.0,
            PerformanceThreshold.WARNING: 1.5,
            PerformanceThreshold.CRITICAL: 2.0
        }
        
        # Measurement storage
        self.measurements: Dict[PerformanceMetric, List[PerformanceMeasurement]] = {
            metric: [] for metric in PerformanceMetric
        }
        
        # Performance alerts
        self.alerts: List[Dict[str, Any]] = []
        
        # Benchmarking results
        self.benchmarks: Dict[str, PerformanceBenchmark] = {}
        
        # Process monitoring
        self.process = psutil.Process()
        self.baseline_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        # Thread safety
        self.lock = threading.Lock()
        
    @contextmanager
    def measure_operation(self, metric: PerformanceMetric, operation: str, context: Dict[str, Any] = None):
        """
        Context manager for measuring operation performance
        
        Args:
            metric: Performance metric to measure
            operation: Operation name
            context: Additional context information
        """
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024
        
        try:
            yield
        finally:
            # Calculate performance metrics
            elapsed_time = (time.time() - start_time) * 1000  # Convert to ms
            current_memory = self.process.memory_info().rss / 1024 / 1024
            memory_delta = current_memory - start_memory
            
            # Determine primary metric value
            if metric == PerformanceMetric.MEMORY_USAGE:
                value = memory_delta
            else:
                value = elapsed_time
            
            # Create measurement
            measurement = PerformanceMeasurement(
                metric=metric,
                value=value,
                timestamp=datetime.now(),
                operation=operation,
                context=context or {},
                threshold_level=self._determine_threshold_level(metric, value)
            )
            
            # Store measurement
            with self.lock:
                self.measurements[metric].append(measurement)
                
                # Keep only last 1000 measurements per metric
                if len(self.measurements[metric]) > 1000:
                    self.measurements[metric] = self.measurements[metric][-1000:]
            
            # Check for alerts
            self._check_performance_alert(measurement)
            
            # Log performance
            self._log_performance_measurement(measurement)
    
    def _determine_threshold_level(self, metric: PerformanceMetric, value: float) -> PerformanceThreshold:
        """Determine threshold level for a measurement"""
        target = self.performance_targets.get(metric, 1000)
        
        if value <= target * self.threshold_multipliers[PerformanceThreshold.EXCELLENT]:
            return PerformanceThreshold.EXCELLENT
        elif value <= target * self.threshold_multipliers[PerformanceThreshold.GOOD]:
            return PerformanceThreshold.GOOD
        elif value <= target * self.threshold_multipliers[PerformanceThreshold.WARNING]:
            return PerformanceThreshold.WARNING
        else:
            return PerformanceThreshold.CRITICAL
    
    def _check_performance_alert(self, measurement: PerformanceMeasurement):
        """Check if measurement triggers performance alert"""
        if measurement.threshold_level in [PerformanceThreshold.WARNING, PerformanceThreshold.CRITICAL]:
            alert = {
                "timestamp": measurement.timestamp.isoformat(),
                "metric": measurement.metric.value,
                "operation": measurement.operation,
                "value": measurement.value,
                "threshold_level": measurement.threshold_level.value,
                "target": self.performance_targets.get(measurement.metric, 0),
                "context": measurement.context
            }
            
            with self.lock:
                self.alerts.append(alert)
                
                # Keep only last 100 alerts
                if len(self.alerts) > 100:
                    self.alerts = self.alerts[-100:]
            
            # Log alert
            self.logger.warning(
                f"Performance alert: {measurement.metric.value} "
                f"({measurement.operation}) took {measurement.value:.2f}ms "
                f"(threshold: {measurement.threshold_level.value})"
            )
    
    def _log_performance_measurement(self, measurement: PerformanceMeasurement):
        """Log performance measurement"""
        target = self.performance_targets.get(measurement.metric, 0)
        
        if measurement.threshold_level == PerformanceThreshold.CRITICAL:
            self.logger.error(
                f"Critical performance: {measurement.metric.value} "
                f"({measurement.operation}) took {measurement.value:.2f}ms "
                f"(target: {target}ms)"
            )
        elif measurement.threshold_level == PerformanceThreshold.WARNING:
            self.logger.warning(
                f"Slow performance: {measurement.metric.value} "
                f"({measurement.operation}) took {measurement.value:.2f}ms "
                f"(target: {target}ms)"
            )
        else:
            self.logger.debug(
                f"Performance: {measurement.metric.value} "
                f"({measurement.operation}) took {measurement.value:.2f}ms"
            )
    
    def benchmark_config_loading(self, config_loader_func, num_iterations: int = 100) -> PerformanceBenchmark:
        """
        Benchmark configuration loading performance
        
        Args:
            config_loader_func: Function to load configuration
            num_iterations: Number of benchmark iterations
            
        Returns:
            Performance benchmark results
        """
        measurements = []
        
        for i in range(num_iterations):
            with self.measure_operation(
                PerformanceMetric.CONFIG_LOAD_TIME, 
                "config_load_benchmark",
                {"iteration": i}
            ):
                config_loader_func()
            
            # Get the latest measurement
            measurements.append(self.measurements[PerformanceMetric.CONFIG_LOAD_TIME][-1])
        
        return self._create_benchmark_result(PerformanceMetric.CONFIG_LOAD_TIME, measurements)
    
    def benchmark_validation_performance(self, validator_func, config_data: Dict[str, Any], num_iterations: int = 100) -> PerformanceBenchmark:
        """
        Benchmark validation performance
        
        Args:
            validator_func: Validation function
            config_data: Configuration data to validate
            num_iterations: Number of benchmark iterations
            
        Returns:
            Performance benchmark results
        """
        measurements = []
        
        for i in range(num_iterations):
            with self.measure_operation(
                PerformanceMetric.VALIDATION_TIME,
                "validation_benchmark",
                {"iteration": i}
            ):
                validator_func(config_data)
            
            measurements.append(self.measurements[PerformanceMetric.VALIDATION_TIME][-1])
        
        return self._create_benchmark_result(PerformanceMetric.VALIDATION_TIME, measurements)
    
    def benchmark_migration_performance(self, migration_func, num_iterations: int = 10) -> PerformanceBenchmark:
        """
        Benchmark migration performance
        
        Args:
            migration_func: Migration function
            num_iterations: Number of benchmark iterations
            
        Returns:
            Performance benchmark results
        """
        measurements = []
        
        for i in range(num_iterations):
            with self.measure_operation(
                PerformanceMetric.MIGRATION_TIME,
                "migration_benchmark",
                {"iteration": i}
            ):
                migration_func()
            
            measurements.append(self.measurements[PerformanceMetric.MIGRATION_TIME][-1])
        
        return self._create_benchmark_result(PerformanceMetric.MIGRATION_TIME, measurements)
    
    def benchmark_concurrent_access(self, operation_func, num_threads: int = 10, operations_per_thread: int = 10) -> PerformanceBenchmark:
        """
        Benchmark concurrent access performance
        
        Args:
            operation_func: Operation function to execute concurrently
            num_threads: Number of concurrent threads
            operations_per_thread: Operations per thread
            
        Returns:
            Performance benchmark results
        """
        measurements = []
        
        def thread_worker(thread_id: int):
            thread_measurements = []
            for op_id in range(operations_per_thread):
                with self.measure_operation(
                    PerformanceMetric.CONCURRENT_ACCESS,
                    "concurrent_access_benchmark",
                    {"thread_id": thread_id, "operation_id": op_id}
                ):
                    operation_func()
                
                thread_measurements.append(self.measurements[PerformanceMetric.CONCURRENT_ACCESS][-1])
            
            return thread_measurements
        
        # Execute concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(thread_worker, i) for i in range(num_threads)]
            
            for future in concurrent.futures.as_completed(futures):
                measurements.extend(future.result())
        
        return self._create_benchmark_result(PerformanceMetric.CONCURRENT_ACCESS, measurements)
    
    def benchmark_memory_usage(self, operation_func, num_iterations: int = 50) -> PerformanceBenchmark:
        """
        Benchmark memory usage during operations
        
        Args:
            operation_func: Operation function to monitor
            num_iterations: Number of benchmark iterations
            
        Returns:
            Performance benchmark results
        """
        measurements = []
        
        for i in range(num_iterations):
            with self.measure_operation(
                PerformanceMetric.MEMORY_USAGE,
                "memory_usage_benchmark",
                {"iteration": i}
            ):
                operation_func()
            
            measurements.append(self.measurements[PerformanceMetric.MEMORY_USAGE][-1])
        
        return self._create_benchmark_result(PerformanceMetric.MEMORY_USAGE, measurements)
    
    def _create_benchmark_result(self, metric: PerformanceMetric, measurements: List[PerformanceMeasurement]) -> PerformanceBenchmark:
        """Create benchmark result from measurements"""
        values = [m.value for m in measurements]
        
        benchmark = PerformanceBenchmark(
            metric=metric,
            measurements=measurements,
            min_value=min(values),
            max_value=max(values),
            avg_value=statistics.mean(values),
            p95_value=statistics.quantiles(values, n=20)[18] if len(values) > 1 else values[0],
            p99_value=statistics.quantiles(values, n=100)[98] if len(values) > 1 else values[0],
            target_value=self.performance_targets.get(metric, 0)
        )
        
        # Determine if benchmark passed
        target = self.performance_targets.get(metric, float('inf'))
        benchmark.passed = benchmark.avg_value <= target
        
        # Determine overall threshold level
        if benchmark.p95_value <= target * self.threshold_multipliers[PerformanceThreshold.GOOD]:
            benchmark.threshold_level = PerformanceThreshold.GOOD
        elif benchmark.p95_value <= target * self.threshold_multipliers[PerformanceThreshold.WARNING]:
            benchmark.threshold_level = PerformanceThreshold.WARNING
        else:
            benchmark.threshold_level = PerformanceThreshold.CRITICAL
        
        # Store benchmark
        benchmark_key = f"{metric.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.benchmarks[benchmark_key] = benchmark
        
        return benchmark
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "baseline_memory_mb": self.baseline_memory,
            "current_memory_mb": self.process.memory_info().rss / 1024 / 1024,
            "targets": {metric.value: target for metric, target in self.performance_targets.items()},
            "metrics": {},
            "alerts": len(self.alerts),
            "recent_alerts": self.alerts[-10:] if self.alerts else []
        }
        
        # Calculate metrics summary
        for metric in PerformanceMetric:
            measurements = self.measurements[metric][-100:]  # Last 100 measurements
            
            if measurements:
                values = [m.value for m in measurements]
                summary["metrics"][metric.value] = {
                    "count": len(measurements),
                    "min": min(values),
                    "max": max(values),
                    "avg": statistics.mean(values),
                    "p95": statistics.quantiles(values, n=20)[18] if len(values) > 1 else values[0],
                    "target": self.performance_targets.get(metric, 0),
                    "within_target": all(v <= self.performance_targets.get(metric, float('inf')) for v in values)
                }
        
        return summary
    
    def get_benchmark_report(self) -> Dict[str, Any]:
        """Get benchmark report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "benchmarks": {},
            "summary": {
                "total_benchmarks": len(self.benchmarks),
                "passed_benchmarks": sum(1 for b in self.benchmarks.values() if b.passed),
                "failed_benchmarks": sum(1 for b in self.benchmarks.values() if not b.passed)
            }
        }
        
        # Add benchmark details
        for key, benchmark in self.benchmarks.items():
            report["benchmarks"][key] = {
                "metric": benchmark.metric.value,
                "measurements_count": len(benchmark.measurements),
                "min_value": benchmark.min_value,
                "max_value": benchmark.max_value,
                "avg_value": benchmark.avg_value,
                "p95_value": benchmark.p95_value,
                "p99_value": benchmark.p99_value,
                "target_value": benchmark.target_value,
                "passed": benchmark.passed,
                "threshold_level": benchmark.threshold_level.value
            }
        
        return report
    
    def export_performance_data(self, file_path: str):
        """Export performance data to file"""
        data = {
            "summary": self.get_performance_summary(),
            "benchmarks": self.get_benchmark_report(),
            "raw_measurements": {
                metric.value: [
                    {
                        "value": m.value,
                        "timestamp": m.timestamp.isoformat(),
                        "operation": m.operation,
                        "context": m.context,
                        "threshold_level": m.threshold_level.value
                    }
                    for m in measurements[-100:]  # Last 100 measurements
                ]
                for metric, measurements in self.measurements.items()
                if measurements
            }
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"Performance data exported to {file_path}")
    
    def clear_measurements(self):
        """Clear all measurements and reset monitoring"""
        with self.lock:
            self.measurements = {metric: [] for metric in PerformanceMetric}
            self.alerts = []
            self.benchmarks = {}
        
        self.logger.info("Performance measurements cleared")

# Global performance monitor instance
performance_monitor = ConfigPerformanceMonitor()

# Context manager for easy performance monitoring
def monitor_performance(metric: PerformanceMetric, operation: str, context: Dict[str, Any] = None):
    """
    Convenient context manager for performance monitoring
    
    Args:
        metric: Performance metric to measure
        operation: Operation name
        context: Additional context information
    """
    return performance_monitor.measure_operation(metric, operation, context)

# Example usage following AAA pattern
def example_performance_monitoring():
    """Example of performance monitoring usage"""
    
    # Arrange - Set up test operation
    def test_operation():
        time.sleep(0.1)  # Simulate work
        return {"result": "success"}
    
    # Act - Monitor performance
    with monitor_performance(PerformanceMetric.CONFIG_LOAD_TIME, "example_operation"):
        result = test_operation()
    
    # Assert - Check performance was recorded
    summary = performance_monitor.get_performance_summary()
    assert "config_load_time" in summary["metrics"]
    assert summary["metrics"]["config_load_time"]["count"] > 0
    
    print("Performance monitoring example completed successfully")