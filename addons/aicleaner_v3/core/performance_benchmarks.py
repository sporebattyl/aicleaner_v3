"""
Performance Benchmarking System for AICleaner
Provides comprehensive performance testing and benchmarking capabilities
"""
import time
import asyncio
import statistics
import json
import os
import threading
import psutil
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import logging

try:
    from core.resource_monitor import ResourceMonitor, ResourceMetrics
    from core.local_model_manager import LocalModelManager
    from integrations.ollama_client import OllamaClient, OptimizationOptions
    ADVANCED_BENCHMARKING_AVAILABLE = True
except ImportError:
    ADVANCED_BENCHMARKING_AVAILABLE = False


class BenchmarkType(Enum):
    """Types of benchmarks"""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    MEMORY = "memory"
    CPU = "cpu"
    ACCURACY = "accuracy"
    RELIABILITY = "reliability"
    LOAD_TEST = "load_test"
    STRESS_TEST = "stress_test"
    ENDURANCE = "endurance"
    COMPARATIVE = "comparative"
    REGRESSION = "regression"


class BenchmarkStatus(Enum):
    """Benchmark execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BenchmarkResult:
    """Result of a benchmark test"""
    benchmark_id: str
    benchmark_type: BenchmarkType
    component: str
    operation: str
    status: BenchmarkStatus
    start_time: str
    end_time: Optional[str]
    duration_seconds: Optional[float]
    metrics: Dict[str, Any]
    metadata: Dict[str, Any]
    error_message: Optional[str] = None
    baseline_comparison: Optional[Dict[str, float]] = None
    regression_detected: bool = False
    performance_score: Optional[float] = None


@dataclass
class BenchmarkSuite:
    """Collection of related benchmarks"""
    suite_id: str
    name: str
    description: str
    benchmarks: List[str]  # List of benchmark IDs
    schedule: Optional[str] = None  # Cron-like schedule
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None


@dataclass
class PerformanceBaseline:
    """Performance baseline for comparison"""
    baseline_id: str
    component: str
    operation: str
    benchmark_type: BenchmarkType
    baseline_metrics: Dict[str, float]
    created_at: str
    sample_count: int
    confidence_interval: Dict[str, Tuple[float, float]]


@dataclass
class PerformanceTarget:
    """Performance target for benchmarking"""
    metric_name: str
    target_value: float
    tolerance: float  # Acceptable deviation percentage
    unit: str
    description: str


class PerformanceBenchmarks:
    """
    Performance benchmarking system for AICleaner
    
    Features:
    - Automated performance testing
    - Baseline establishment and comparison
    - Regression detection
    - Performance target validation
    - Comprehensive reporting
    """
    
    def __init__(self, data_path: str = "/data/benchmarks"):
        """
        Initialize performance benchmarking system
        
        Args:
            data_path: Path to store benchmark data
        """
        self.data_path = data_path
        self.logger = logging.getLogger(__name__)
        
        # Ensure data directory exists
        os.makedirs(data_path, exist_ok=True)
        
        # Benchmark storage
        self.benchmark_results = []
        self.performance_targets = {}
        self.baselines = {}
        self.benchmark_suites = {}
        self.performance_baselines = {}

        # Advanced benchmarking
        self.automated_benchmarks_enabled = True
        self.regression_detection_enabled = True
        self.comparative_analysis_enabled = True
        self.benchmark_scheduler = None

        # Performance tracking
        self.performance_history = defaultdict(list)
        self.regression_alerts = deque(maxlen=100)

        # Load existing data
        self._load_benchmark_data()

        # Initialize advanced features if available
        if ADVANCED_BENCHMARKING_AVAILABLE:
            self._initialize_advanced_benchmarking()

        self.logger.info("Performance Benchmarks system initialized")
    
    def _load_benchmark_data(self):
        """Load existing benchmark data"""
        results_file = os.path.join(self.data_path, "benchmark_results.json")
        if os.path.exists(results_file):
            try:
                with open(results_file, 'r') as f:
                    data = json.load(f)
                    self.benchmark_results = [
                        BenchmarkResult(**result) for result in data
                    ]
                self.logger.info(f"Loaded {len(self.benchmark_results)} benchmark results")
            except Exception as e:
                self.logger.error(f"Failed to load benchmark results: {e}")
        
        baselines_file = os.path.join(self.data_path, "baselines.json")
        if os.path.exists(baselines_file):
            try:
                with open(baselines_file, 'r') as f:
                    self.baselines = json.load(f)
                self.logger.info(f"Loaded {len(self.baselines)} performance baselines")
            except Exception as e:
                self.logger.error(f"Failed to load baselines: {e}")
    
    def _save_benchmark_data(self):
        """Save benchmark data"""
        results_file = os.path.join(self.data_path, "benchmark_results.json")
        try:
            with open(results_file, 'w') as f:
                json.dump([asdict(result) for result in self.benchmark_results], f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save benchmark results: {e}")
        
        baselines_file = os.path.join(self.data_path, "baselines.json")
        try:
            with open(baselines_file, 'w') as f:
                json.dump(self.baselines, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save baselines: {e}")
    
    def register_performance_target(self, component: str, operation: str, target: PerformanceTarget):
        """Register a performance target for a component operation"""
        key = f"{component}.{operation}"
        if key not in self.performance_targets:
            self.performance_targets[key] = []
        self.performance_targets[key].append(target)
        self.logger.info(f"Registered performance target for {key}: {target.metric_name} = {target.target_value} {target.unit}")
    
    async def benchmark_latency(self, component: str, operation: str, 
                               test_func: Callable, iterations: int = 100,
                               warmup_iterations: int = 10) -> BenchmarkResult:
        """
        Benchmark latency of an operation
        
        Args:
            component: Component being tested
            operation: Operation being tested
            test_func: Function to benchmark
            iterations: Number of test iterations
            warmup_iterations: Number of warmup iterations
            
        Returns:
            BenchmarkResult with latency metrics
        """
        benchmark_id = f"latency_{component}_{operation}_{int(time.time())}"
        start_time = datetime.now(timezone.utc)
        
        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            benchmark_type=BenchmarkType.LATENCY,
            component=component,
            operation=operation,
            status=BenchmarkStatus.RUNNING,
            start_time=start_time.isoformat(),
            end_time=None,
            duration_seconds=None,
            metrics={},
            metadata={
                'iterations': iterations,
                'warmup_iterations': warmup_iterations
            }
        )
        
        try:
            # Warmup
            for _ in range(warmup_iterations):
                if asyncio.iscoroutinefunction(test_func):
                    await test_func()
                else:
                    test_func()
            
            # Actual benchmarking
            latencies = []
            for _ in range(iterations):
                start = time.perf_counter()
                if asyncio.iscoroutinefunction(test_func):
                    await test_func()
                else:
                    test_func()
                end = time.perf_counter()
                latencies.append((end - start) * 1000)  # Convert to milliseconds
            
            # Calculate metrics
            result.metrics = {
                'mean_latency_ms': statistics.mean(latencies),
                'median_latency_ms': statistics.median(latencies),
                'min_latency_ms': min(latencies),
                'max_latency_ms': max(latencies),
                'p95_latency_ms': self._percentile(latencies, 95),
                'p99_latency_ms': self._percentile(latencies, 99),
                'std_dev_ms': statistics.stdev(latencies) if len(latencies) > 1 else 0,
                'total_iterations': iterations,
                'successful_iterations': len(latencies)
            }
            
            result.status = BenchmarkStatus.COMPLETED
            
        except Exception as e:
            result.status = BenchmarkStatus.FAILED
            result.error_message = str(e)
            self.logger.error(f"Latency benchmark failed for {component}.{operation}: {e}")
        
        finally:
            end_time = datetime.now(timezone.utc)
            result.end_time = end_time.isoformat()
            result.duration_seconds = (end_time - start_time).total_seconds()
            
            self.benchmark_results.append(result)
            self._save_benchmark_data()
        
        return result
    
    async def benchmark_throughput(self, component: str, operation: str,
                                  test_func: Callable, duration_seconds: int = 60,
                                  concurrent_workers: int = 1) -> BenchmarkResult:
        """
        Benchmark throughput of an operation
        
        Args:
            component: Component being tested
            operation: Operation being tested
            test_func: Function to benchmark
            duration_seconds: How long to run the test
            concurrent_workers: Number of concurrent workers
            
        Returns:
            BenchmarkResult with throughput metrics
        """
        benchmark_id = f"throughput_{component}_{operation}_{int(time.time())}"
        start_time = datetime.now(timezone.utc)
        
        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            benchmark_type=BenchmarkType.THROUGHPUT,
            component=component,
            operation=operation,
            status=BenchmarkStatus.RUNNING,
            start_time=start_time.isoformat(),
            end_time=None,
            duration_seconds=None,
            metrics={},
            metadata={
                'duration_seconds': duration_seconds,
                'concurrent_workers': concurrent_workers
            }
        )
        
        try:
            completed_operations = 0
            errors = 0
            
            async def worker():
                nonlocal completed_operations, errors
                end_time = time.time() + duration_seconds
                
                while time.time() < end_time:
                    try:
                        if asyncio.iscoroutinefunction(test_func):
                            await test_func()
                        else:
                            test_func()
                        completed_operations += 1
                    except Exception:
                        errors += 1
            
            # Run concurrent workers
            tasks = [worker() for _ in range(concurrent_workers)]
            await asyncio.gather(*tasks)
            
            # Calculate metrics
            actual_duration = duration_seconds
            result.metrics = {
                'total_operations': completed_operations,
                'operations_per_second': completed_operations / actual_duration,
                'operations_per_minute': (completed_operations / actual_duration) * 60,
                'error_count': errors,
                'error_rate': errors / (completed_operations + errors) if (completed_operations + errors) > 0 else 0,
                'success_rate': completed_operations / (completed_operations + errors) if (completed_operations + errors) > 0 else 0,
                'concurrent_workers': concurrent_workers,
                'actual_duration_seconds': actual_duration
            }
            
            result.status = BenchmarkStatus.COMPLETED
            
        except Exception as e:
            result.status = BenchmarkStatus.FAILED
            result.error_message = str(e)
            self.logger.error(f"Throughput benchmark failed for {component}.{operation}: {e}")
        
        finally:
            end_time = datetime.now(timezone.utc)
            result.end_time = end_time.isoformat()
            result.duration_seconds = (end_time - start_time).total_seconds()
            
            self.benchmark_results.append(result)
            self._save_benchmark_data()
        
        return result

    async def benchmark_comparative_analysis(self, component: str, operation: str,
                                           local_func: Callable, cloud_func: Callable,
                                           test_cases: List[Any], iterations: int = 5) -> BenchmarkResult:
        """
        Compare performance between local and cloud implementations.

        Args:
            component: Component being tested
            operation: Operation being tested
            local_func: Local implementation function
            cloud_func: Cloud implementation function
            test_cases: List of test cases to run
            iterations: Number of iterations per test case

        Returns:
            BenchmarkResult with comparative analysis
        """
        benchmark_id = f"comparative_{component}_{operation}_{int(time.time())}"
        start_time = datetime.now(timezone.utc)

        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            benchmark_type=BenchmarkType.COMPARATIVE,
            component=component,
            operation=operation,
            status=BenchmarkStatus.RUNNING,
            start_time=start_time.isoformat(),
            end_time=None,
            duration_seconds=None,
            metrics={}
        )

        try:
            local_times = []
            cloud_times = []
            local_errors = 0
            cloud_errors = 0

            for test_case in test_cases:
                for _ in range(iterations):
                    # Test local implementation
                    try:
                        local_start = time.time()
                        await local_func(test_case) if asyncio.iscoroutinefunction(local_func) else local_func(test_case)
                        local_times.append(time.time() - local_start)
                    except Exception as e:
                        local_errors += 1
                        self.logger.debug(f"Local function error: {e}")

                    # Test cloud implementation
                    try:
                        cloud_start = time.time()
                        await cloud_func(test_case) if asyncio.iscoroutinefunction(cloud_func) else cloud_func(test_case)
                        cloud_times.append(time.time() - cloud_start)
                    except Exception as e:
                        cloud_errors += 1
                        self.logger.debug(f"Cloud function error: {e}")

            # Calculate metrics
            local_avg = statistics.mean(local_times) if local_times else float('inf')
            cloud_avg = statistics.mean(cloud_times) if cloud_times else float('inf')

            result.metrics = {
                'local_avg_time': local_avg,
                'cloud_avg_time': cloud_avg,
                'local_min_time': min(local_times) if local_times else 0,
                'cloud_min_time': min(cloud_times) if cloud_times else 0,
                'local_max_time': max(local_times) if local_times else 0,
                'cloud_max_time': max(cloud_times) if cloud_times else 0,
                'local_error_rate': local_errors / (len(test_cases) * iterations),
                'cloud_error_rate': cloud_errors / (len(test_cases) * iterations),
                'performance_ratio': local_avg / cloud_avg if cloud_avg > 0 else float('inf'),
                'local_success_rate': 1 - (local_errors / (len(test_cases) * iterations)),
                'cloud_success_rate': 1 - (cloud_errors / (len(test_cases) * iterations))
            }

            result.status = BenchmarkStatus.COMPLETED
            result.metadata = {
                'test_cases_count': len(test_cases),
                'iterations_per_case': iterations,
                'total_tests': len(test_cases) * iterations
            }

        except Exception as e:
            result.status = BenchmarkStatus.FAILED
            result.metadata = {'error': str(e)}
            self.logger.error(f"Comparative benchmark failed: {e}")

        finally:
            end_time = datetime.now(timezone.utc)
            result.end_time = end_time.isoformat()
            result.duration_seconds = (end_time - start_time).total_seconds()

            self.benchmark_results.append(result)
            self._save_benchmark_data()

        return result

    async def benchmark_load_test(self, component: str, operation: str,
                                 test_func: Callable, concurrent_users: int = 10,
                                 duration_seconds: int = 60, ramp_up_seconds: int = 10) -> BenchmarkResult:
        """
        Perform load testing with gradually increasing concurrent users.

        Args:
            component: Component being tested
            operation: Operation being tested
            test_func: Function to test under load
            concurrent_users: Maximum number of concurrent users
            duration_seconds: Duration of the load test
            ramp_up_seconds: Time to ramp up to max users

        Returns:
            BenchmarkResult with load test metrics
        """
        benchmark_id = f"load_test_{component}_{operation}_{int(time.time())}"
        start_time = datetime.now(timezone.utc)

        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            benchmark_type=BenchmarkType.LOAD_TEST,
            component=component,
            operation=operation,
            status=BenchmarkStatus.RUNNING,
            start_time=start_time.isoformat(),
            end_time=None,
            duration_seconds=None,
            metrics={}
        )

        try:
            response_times = []
            error_count = 0
            success_count = 0

            # Semaphore to control concurrency
            semaphore = asyncio.Semaphore(concurrent_users)

            async def worker():
                nonlocal error_count, success_count
                async with semaphore:
                    try:
                        worker_start = time.time()
                        if asyncio.iscoroutinefunction(test_func):
                            await test_func()
                        else:
                            test_func()
                        response_times.append(time.time() - worker_start)
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        self.logger.debug(f"Load test worker error: {e}")

            # Start load test
            tasks = []
            test_start = time.time()

            while time.time() - test_start < duration_seconds:
                # Gradually ramp up users
                current_time = time.time() - test_start
                if current_time < ramp_up_seconds:
                    current_users = int((current_time / ramp_up_seconds) * concurrent_users)
                else:
                    current_users = concurrent_users

                # Start new tasks up to current user limit
                while len([t for t in tasks if not t.done()]) < current_users:
                    task = asyncio.create_task(worker())
                    tasks.append(task)

                await asyncio.sleep(0.1)  # Small delay to prevent tight loop

            # Wait for remaining tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)

            # Calculate metrics
            total_requests = success_count + error_count
            avg_response_time = statistics.mean(response_times) if response_times else 0

            result.metrics = {
                'total_requests': total_requests,
                'successful_requests': success_count,
                'failed_requests': error_count,
                'error_rate': error_count / total_requests if total_requests > 0 else 0,
                'avg_response_time': avg_response_time,
                'min_response_time': min(response_times) if response_times else 0,
                'max_response_time': max(response_times) if response_times else 0,
                'requests_per_second': total_requests / duration_seconds,
                'concurrent_users': concurrent_users
            }

            result.status = BenchmarkStatus.COMPLETED

        except Exception as e:
            result.status = BenchmarkStatus.FAILED
            result.metadata = {'error': str(e)}
            self.logger.error(f"Load test benchmark failed: {e}")

        finally:
            end_time = datetime.now(timezone.utc)
            result.end_time = end_time.isoformat()
            result.duration_seconds = (end_time - start_time).total_seconds()

            self.benchmark_results.append(result)
            self._save_benchmark_data()

        return result

    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data"""
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def establish_baseline(self, component: str, operation: str, 
                          benchmark_type: BenchmarkType) -> Optional[Dict[str, float]]:
        """
        Establish performance baseline from recent benchmark results
        
        Args:
            component: Component name
            operation: Operation name
            benchmark_type: Type of benchmark
            
        Returns:
            Baseline metrics or None if insufficient data
        """
        # Get recent successful benchmarks
        recent_results = [
            result for result in self.benchmark_results[-50:]  # Last 50 results
            if (result.component == component and 
                result.operation == operation and
                result.benchmark_type == benchmark_type and
                result.status == BenchmarkStatus.COMPLETED)
        ]
        
        if len(recent_results) < 5:  # Need at least 5 results
            return None
        
        # Calculate baseline from median values
        baseline = {}
        
        if benchmark_type == BenchmarkType.LATENCY:
            latencies = [result.metrics.get('median_latency_ms', 0) for result in recent_results]
            baseline = {
                'median_latency_ms': statistics.median(latencies),
                'p95_latency_ms': statistics.median([result.metrics.get('p95_latency_ms', 0) for result in recent_results])
            }
        elif benchmark_type == BenchmarkType.THROUGHPUT:
            throughputs = [result.metrics.get('operations_per_second', 0) for result in recent_results]
            baseline = {
                'operations_per_second': statistics.median(throughputs),
                'success_rate': statistics.median([result.metrics.get('success_rate', 0) for result in recent_results])
            }
        
        # Store baseline
        key = f"{component}.{operation}.{benchmark_type.value}"
        self.baselines[key] = {
            'metrics': baseline,
            'established_at': datetime.now(timezone.utc).isoformat(),
            'sample_count': len(recent_results)
        }
        
        self._save_benchmark_data()
        self.logger.info(f"Established baseline for {key}: {baseline}")
        
        return baseline

    def compare_to_baseline(self, result: BenchmarkResult) -> Dict[str, Any]:
        """
        Compare benchmark result to established baseline

        Args:
            result: Benchmark result to compare

        Returns:
            Comparison analysis
        """
        key = f"{result.component}.{result.operation}.{result.benchmark_type.value}"

        if key not in self.baselines:
            return {
                'baseline_available': False,
                'message': 'No baseline established for this benchmark'
            }

        baseline = self.baselines[key]['metrics']
        comparison = {
            'baseline_available': True,
            'baseline_date': self.baselines[key]['established_at'],
            'metrics_comparison': {},
            'overall_assessment': 'unknown',
            'recommendations': []
        }

        # Compare metrics
        for metric_name, baseline_value in baseline.items():
            if metric_name in result.metrics:
                current_value = result.metrics[metric_name]

                if baseline_value > 0:
                    change_percent = ((current_value - baseline_value) / baseline_value) * 100
                else:
                    change_percent = 0

                comparison['metrics_comparison'][metric_name] = {
                    'baseline': baseline_value,
                    'current': current_value,
                    'change_percent': change_percent,
                    'improved': self._is_improvement(metric_name, change_percent)
                }

        # Overall assessment
        improvements = sum(1 for m in comparison['metrics_comparison'].values() if m['improved'])
        regressions = sum(1 for m in comparison['metrics_comparison'].values() if not m['improved'] and abs(m['change_percent']) > 5)

        if regressions > 0:
            comparison['overall_assessment'] = 'regression'
            comparison['recommendations'].append('Performance regression detected - investigate recent changes')
        elif improvements > 0:
            comparison['overall_assessment'] = 'improvement'
            comparison['recommendations'].append('Performance improvement detected - consider updating baseline')
        else:
            comparison['overall_assessment'] = 'stable'
            comparison['recommendations'].append('Performance is stable within expected range')

        return comparison

    def _is_improvement(self, metric_name: str, change_percent: float) -> bool:
        """Determine if a metric change is an improvement"""
        # Lower is better for latency metrics
        if 'latency' in metric_name.lower():
            return change_percent < 0

        # Higher is better for throughput and success rate
        if any(term in metric_name.lower() for term in ['throughput', 'operations', 'success']):
            return change_percent > 0

        # Default: lower change is better (more stable)
        return abs(change_percent) < 5

    def validate_performance_targets(self, result: BenchmarkResult) -> Dict[str, Any]:
        """
        Validate benchmark result against performance targets

        Args:
            result: Benchmark result to validate

        Returns:
            Validation results
        """
        key = f"{result.component}.{result.operation}"

        if key not in self.performance_targets:
            return {
                'targets_defined': False,
                'message': 'No performance targets defined for this operation'
            }

        targets = self.performance_targets[key]
        validation = {
            'targets_defined': True,
            'target_results': [],
            'overall_pass': True,
            'passed_targets': 0,
            'failed_targets': 0
        }

        for target in targets:
            if target.metric_name in result.metrics:
                current_value = result.metrics[target.metric_name]
                target_value = target.target_value
                tolerance = target.tolerance / 100  # Convert percentage to decimal

                # Calculate acceptable range
                min_acceptable = target_value * (1 - tolerance)
                max_acceptable = target_value * (1 + tolerance)

                # Check if within tolerance
                passed = min_acceptable <= current_value <= max_acceptable

                target_result = {
                    'metric_name': target.metric_name,
                    'target_value': target_value,
                    'current_value': current_value,
                    'tolerance_percent': target.tolerance,
                    'acceptable_range': [min_acceptable, max_acceptable],
                    'passed': passed,
                    'deviation_percent': ((current_value - target_value) / target_value) * 100 if target_value > 0 else 0,
                    'unit': target.unit,
                    'description': target.description
                }

                validation['target_results'].append(target_result)

                if passed:
                    validation['passed_targets'] += 1
                else:
                    validation['failed_targets'] += 1
                    validation['overall_pass'] = False

        return validation

    def generate_performance_report(self, component: Optional[str] = None,
                                  days: int = 7) -> Dict[str, Any]:
        """
        Generate comprehensive performance report

        Args:
            component: Specific component to report on (None for all)
            days: Number of days to include in report

        Returns:
            Performance report
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_str = cutoff_time.isoformat()

        # Filter results
        filtered_results = [
            result for result in self.benchmark_results
            if result.start_time > cutoff_str and
            (component is None or result.component == component)
        ]

        # Group by component and operation
        grouped_results = {}
        for result in filtered_results:
            key = f"{result.component}.{result.operation}"
            if key not in grouped_results:
                grouped_results[key] = []
            grouped_results[key].append(result)

        # Generate report sections
        report = {
            'report_period': {
                'start_date': cutoff_str,
                'end_date': datetime.now(timezone.utc).isoformat(),
                'days': days
            },
            'summary': {
                'total_benchmarks': len(filtered_results),
                'components_tested': len(set(r.component for r in filtered_results)),
                'operations_tested': len(grouped_results),
                'success_rate': sum(1 for r in filtered_results if r.status == BenchmarkStatus.COMPLETED) / len(filtered_results) if filtered_results else 0
            },
            'component_analysis': {},
            'performance_trends': {},
            'baseline_comparisons': {},
            'target_validations': {},
            'recommendations': []
        }

        # Analyze each component/operation
        for key, results in grouped_results.items():
            successful_results = [r for r in results if r.status == BenchmarkStatus.COMPLETED]

            if successful_results:
                # Latest result analysis
                latest_result = max(successful_results, key=lambda r: r.start_time)

                # Baseline comparison
                baseline_comparison = self.compare_to_baseline(latest_result)
                report['baseline_comparisons'][key] = baseline_comparison

                # Target validation
                target_validation = self.validate_performance_targets(latest_result)
                report['target_validations'][key] = target_validation

                # Component analysis
                report['component_analysis'][key] = {
                    'total_benchmarks': len(results),
                    'successful_benchmarks': len(successful_results),
                    'latest_result': asdict(latest_result),
                    'success_rate': len(successful_results) / len(results)
                }

        # Generate recommendations
        for key, comparison in report['baseline_comparisons'].items():
            if comparison.get('baseline_available') and comparison.get('overall_assessment') == 'regression':
                report['recommendations'].append(f"Investigate performance regression in {key}")

        for key, validation in report['target_validations'].items():
            if validation.get('targets_defined') and not validation.get('overall_pass'):
                report['recommendations'].append(f"Performance targets not met for {key}")

        return report
