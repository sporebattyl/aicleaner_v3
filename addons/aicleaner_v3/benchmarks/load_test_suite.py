"""
Load Test Suite for AICleaner Phase 3C.2
Comprehensive load testing for all major components and operations.
"""

import asyncio
import time
import logging
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import threading

try:
    from core.performance_benchmarks import PerformanceBenchmarks, BenchmarkResult, BenchmarkType
    from core.resource_monitor import ResourceMonitor
    from core.local_model_manager import LocalModelManager
    from integrations.ollama_client import OllamaClient, OptimizationOptions
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False


@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    max_concurrent_users: int = 20
    test_duration_seconds: int = 300  # 5 minutes
    ramp_up_duration_seconds: int = 60  # 1 minute
    ramp_down_duration_seconds: int = 30  # 30 seconds
    think_time_seconds: float = 1.0  # Time between user actions
    target_rps: Optional[float] = None  # Target requests per second
    failure_threshold_percent: float = 5.0  # Max acceptable failure rate


@dataclass
class LoadTestScenario:
    """Definition of a load test scenario."""
    scenario_id: str
    name: str
    description: str
    test_function: Callable
    weight: float = 1.0  # Relative weight for mixed scenarios
    setup_function: Optional[Callable] = None
    teardown_function: Optional[Callable] = None


@dataclass
class LoadTestResult:
    """Results from a load test execution."""
    scenario_id: str
    start_time: str
    end_time: str
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate_percent: float
    resource_utilization: Dict[str, float]
    errors: List[Dict[str, Any]]


class LoadTestSuite:
    """
    Comprehensive load testing suite for AICleaner components.
    
    Features:
    - Configurable concurrent user simulation
    - Gradual ramp-up and ramp-down
    - Real-time resource monitoring
    - Multiple test scenarios
    - Detailed performance metrics
    - Error tracking and analysis
    """
    
    def __init__(self, config: Dict[str, Any], data_path: str = "/data/benchmarks"):
        """
        Initialize Load Test Suite.
        
        Args:
            config: Configuration dictionary
            data_path: Path to store benchmark results
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.data_path = data_path
        
        # Ensure data directory exists
        os.makedirs(data_path, exist_ok=True)
        
        # Load test configuration
        self.load_test_config = LoadTestConfig()
        
        # Test scenarios
        self.scenarios: Dict[str, LoadTestScenario] = {}
        
        # Results storage
        self.test_results: List[LoadTestResult] = []
        
        # Monitoring components
        self.resource_monitor = None
        self.performance_benchmarks = None
        
        # Test state
        self.test_running = False
        self.current_users = 0
        self.response_times = []
        self.errors = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Initialize components if available
        if DEPENDENCIES_AVAILABLE:
            self._initialize_components()
        
        # Register default scenarios
        self._register_default_scenarios()
        
        self.logger.info("Load Test Suite initialized")

    def _initialize_components(self):
        """Initialize monitoring and benchmarking components."""
        try:
            self.resource_monitor = ResourceMonitor(self.config)
            self.performance_benchmarks = PerformanceBenchmarks(self.data_path)
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")

    def register_scenario(self, scenario: LoadTestScenario):
        """Register a load test scenario."""
        self.scenarios[scenario.scenario_id] = scenario
        self.logger.info(f"Registered load test scenario: {scenario.name}")

    def _register_default_scenarios(self):
        """Register default load test scenarios."""
        # Image analysis scenario
        self.register_scenario(LoadTestScenario(
            scenario_id="image_analysis_load",
            name="Image Analysis Load Test",
            description="Load test for image analysis functionality",
            test_function=self._image_analysis_test_function
        ))
        
        # Task generation scenario
        self.register_scenario(LoadTestScenario(
            scenario_id="task_generation_load",
            name="Task Generation Load Test", 
            description="Load test for task generation functionality",
            test_function=self._task_generation_test_function
        ))
        
        # State management scenario
        self.register_scenario(LoadTestScenario(
            scenario_id="state_management_load",
            name="State Management Load Test",
            description="Load test for state management operations",
            test_function=self._state_management_test_function
        ))
        
        # Mixed workload scenario
        self.register_scenario(LoadTestScenario(
            scenario_id="mixed_workload",
            name="Mixed Workload Test",
            description="Mixed workload simulating real usage patterns",
            test_function=self._mixed_workload_test_function
        ))

    async def run_load_test(self, scenario_id: str, config: Optional[LoadTestConfig] = None) -> LoadTestResult:
        """
        Run a load test for a specific scenario.
        
        Args:
            scenario_id: ID of the scenario to test
            config: Optional custom configuration
            
        Returns:
            LoadTestResult with detailed metrics
        """
        if scenario_id not in self.scenarios:
            raise ValueError(f"Scenario {scenario_id} not found")
        
        scenario = self.scenarios[scenario_id]
        test_config = config or self.load_test_config
        
        self.logger.info(f"Starting load test: {scenario.name}")
        
        # Initialize test state
        self.test_running = True
        self.current_users = 0
        self.response_times = []
        self.errors = []
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Start resource monitoring
            if self.resource_monitor:
                await self.resource_monitor.start_monitoring(interval=5)
            
            # Run scenario setup if provided
            if scenario.setup_function:
                await scenario.setup_function()
            
            # Execute load test
            await self._execute_load_test(scenario, test_config)
            
            # Run scenario teardown if provided
            if scenario.teardown_function:
                await scenario.teardown_function()
            
        except Exception as e:
            self.logger.error(f"Error during load test: {e}")
            self.errors.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "type": "test_execution_error"
            })
        
        finally:
            self.test_running = False
            
            # Stop resource monitoring
            if self.resource_monitor:
                await self.resource_monitor.stop_monitoring()
        
        end_time = datetime.now(timezone.utc)
        
        # Calculate results
        result = self._calculate_test_results(scenario_id, start_time, end_time, test_config)
        
        # Store results
        self.test_results.append(result)
        self._save_test_results()
        
        self.logger.info(f"Load test completed: {scenario.name}")
        return result

    async def _execute_load_test(self, scenario: LoadTestScenario, config: LoadTestConfig):
        """Execute the actual load test with user simulation."""
        total_duration = config.test_duration_seconds
        ramp_up_duration = config.ramp_up_duration_seconds
        ramp_down_start = total_duration - config.ramp_down_duration_seconds
        
        # Create semaphore for controlling concurrency
        semaphore = asyncio.Semaphore(config.max_concurrent_users)
        
        # Track active tasks
        active_tasks = set()
        
        start_time = time.time()
        
        while time.time() - start_time < total_duration and self.test_running:
            current_time = time.time() - start_time
            
            # Calculate target user count based on ramp-up/ramp-down
            if current_time < ramp_up_duration:
                # Ramp-up phase
                target_users = int((current_time / ramp_up_duration) * config.max_concurrent_users)
            elif current_time > ramp_down_start:
                # Ramp-down phase
                remaining_time = total_duration - current_time
                ramp_down_duration = config.ramp_down_duration_seconds
                target_users = int((remaining_time / ramp_down_duration) * config.max_concurrent_users)
            else:
                # Steady state
                target_users = config.max_concurrent_users
            
            # Clean up completed tasks
            completed_tasks = {task for task in active_tasks if task.done()}
            active_tasks -= completed_tasks
            
            # Start new tasks if needed
            current_active = len(active_tasks)
            if current_active < target_users:
                for _ in range(target_users - current_active):
                    task = asyncio.create_task(self._simulate_user(scenario, semaphore, config))
                    active_tasks.add(task)
            
            # Update current user count
            with self._lock:
                self.current_users = len(active_tasks)
            
            await asyncio.sleep(0.1)  # Small delay to prevent tight loop
        
        # Wait for remaining tasks to complete
        if active_tasks:
            await asyncio.gather(*active_tasks, return_exceptions=True)

    async def _simulate_user(self, scenario: LoadTestScenario, semaphore: asyncio.Semaphore, config: LoadTestConfig):
        """Simulate a single user performing the test scenario."""
        async with semaphore:
            try:
                request_start = time.time()
                
                # Execute the test function
                if asyncio.iscoroutinefunction(scenario.test_function):
                    await scenario.test_function()
                else:
                    scenario.test_function()
                
                response_time = time.time() - request_start
                
                with self._lock:
                    self.response_times.append(response_time)
                
                # Think time between requests
                if config.think_time_seconds > 0:
                    await asyncio.sleep(config.think_time_seconds)
                
            except Exception as e:
                with self._lock:
                    self.errors.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "error": str(e),
                        "scenario": scenario.scenario_id,
                        "type": "user_simulation_error"
                    })

    def _calculate_test_results(self, scenario_id: str, start_time: datetime, 
                               end_time: datetime, config: LoadTestConfig) -> LoadTestResult:
        """Calculate comprehensive test results."""
        duration = (end_time - start_time).total_seconds()
        
        with self._lock:
            response_times = self.response_times.copy()
            errors = self.errors.copy()
        
        total_requests = len(response_times) + len(errors)
        successful_requests = len(response_times)
        failed_requests = len(errors)
        
        # Calculate response time statistics
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            # Calculate percentiles
            sorted_times = sorted(response_times)
            p95_index = int(0.95 * len(sorted_times))
            p99_index = int(0.99 * len(sorted_times))
            p95_response_time = sorted_times[p95_index] if p95_index < len(sorted_times) else max_response_time
            p99_response_time = sorted_times[p99_index] if p99_index < len(sorted_times) else max_response_time
        else:
            avg_response_time = 0
            min_response_time = 0
            max_response_time = 0
            p95_response_time = 0
            p99_response_time = 0
        
        # Calculate rates
        requests_per_second = total_requests / duration if duration > 0 else 0
        error_rate_percent = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Get resource utilization
        resource_utilization = {}
        if self.resource_monitor:
            try:
                # Get average resource usage during test
                recent_metrics = self.resource_monitor.metrics_history
                if recent_metrics:
                    cpu_values = [m.cpu_percent for m in recent_metrics]
                    memory_values = [m.memory_percent for m in recent_metrics]
                    
                    resource_utilization = {
                        "avg_cpu_percent": sum(cpu_values) / len(cpu_values),
                        "avg_memory_percent": sum(memory_values) / len(memory_values),
                        "peak_cpu_percent": max(cpu_values),
                        "peak_memory_percent": max(memory_values)
                    }
            except Exception as e:
                self.logger.debug(f"Error calculating resource utilization: {e}")
        
        return LoadTestResult(
            scenario_id=scenario_id,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            average_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            error_rate_percent=error_rate_percent,
            resource_utilization=resource_utilization,
            errors=errors
        )

    def _save_test_results(self):
        """Save test results to disk."""
        try:
            results_file = os.path.join(self.data_path, "load_test_results.json")
            
            # Convert results to serializable format
            serializable_results = [asdict(result) for result in self.test_results]
            
            with open(results_file, 'w') as f:
                json.dump(serializable_results, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Error saving test results: {e}")

    # Default test functions for scenarios
    async def _image_analysis_test_function(self):
        """Test function for image analysis load testing."""
        # Simulate image analysis workload
        await asyncio.sleep(0.1)  # Simulate processing time
        
        # In a real implementation, this would call the actual image analysis
        # For now, just simulate the operation
        return {"analysis": "simulated_result", "confidence": 0.95}

    async def _task_generation_test_function(self):
        """Test function for task generation load testing."""
        # Simulate task generation workload
        await asyncio.sleep(0.05)  # Simulate processing time
        
        return {"tasks": ["simulated_task_1", "simulated_task_2"]}

    async def _state_management_test_function(self):
        """Test function for state management load testing."""
        # Simulate state operations
        await asyncio.sleep(0.02)  # Simulate processing time
        
        return {"state": "updated", "timestamp": time.time()}

    async def _mixed_workload_test_function(self):
        """Test function for mixed workload simulation."""
        # Randomly choose between different operations
        import random
        
        operation = random.choice([
            self._image_analysis_test_function,
            self._task_generation_test_function,
            self._state_management_test_function
        ])
        
        return await operation()

    def get_test_summary(self) -> Dict[str, Any]:
        """Get summary of all test results."""
        if not self.test_results:
            return {"message": "No test results available"}
        
        summary = {
            "total_tests": len(self.test_results),
            "scenarios_tested": list(set(r.scenario_id for r in self.test_results)),
            "overall_stats": {
                "avg_requests_per_second": sum(r.requests_per_second for r in self.test_results) / len(self.test_results),
                "avg_error_rate": sum(r.error_rate_percent for r in self.test_results) / len(self.test_results),
                "avg_response_time": sum(r.average_response_time for r in self.test_results) / len(self.test_results)
            },
            "latest_test": asdict(self.test_results[-1]) if self.test_results else None
        }
        
        return summary
