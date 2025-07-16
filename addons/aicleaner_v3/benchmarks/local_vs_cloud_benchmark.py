"""
Local vs Cloud Benchmark for AICleaner Phase 3C.2
Comprehensive comparison between local and cloud AI implementations.
"""

import asyncio
import time
import logging
import json
import os
import statistics
from datetime import datetime, timezone
from typing import Dict, List, Any, Callable, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from core.performance_benchmarks import PerformanceBenchmarks, BenchmarkResult, BenchmarkType
    from integrations.ollama_client import OllamaClient, OptimizationOptions
    from ai.ai_coordinator import AICoordinator
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False


class ComparisonMetric(Enum):
    """Metrics for comparing local vs cloud performance."""
    RESPONSE_TIME = "response_time"
    ACCURACY = "accuracy"
    COST = "cost"
    RELIABILITY = "reliability"
    THROUGHPUT = "throughput"
    RESOURCE_USAGE = "resource_usage"


@dataclass
class ComparisonTestCase:
    """Test case for local vs cloud comparison."""
    test_id: str
    name: str
    description: str
    input_data: Any
    expected_output_type: str
    complexity_level: str  # simple, medium, complex
    test_category: str  # image_analysis, task_generation, etc.


@dataclass
class ComparisonResult:
    """Result of a local vs cloud comparison."""
    test_case_id: str
    local_metrics: Dict[str, float]
    cloud_metrics: Dict[str, float]
    comparison_ratios: Dict[str, float]  # local/cloud ratios
    winner: str  # "local", "cloud", or "tie"
    confidence_score: float
    recommendations: List[str]


@dataclass
class BenchmarkReport:
    """Comprehensive benchmark report."""
    report_id: str
    timestamp: str
    test_configuration: Dict[str, Any]
    individual_results: List[ComparisonResult]
    aggregate_metrics: Dict[str, Dict[str, float]]
    overall_recommendation: str
    cost_analysis: Dict[str, float]
    performance_summary: Dict[str, Any]


class LocalVsCloudBenchmark:
    """
    Comprehensive benchmark suite for comparing local and cloud AI implementations.
    
    Features:
    - Side-by-side performance comparison
    - Multiple test scenarios and complexity levels
    - Cost analysis and ROI calculations
    - Accuracy and reliability testing
    - Resource utilization analysis
    - Automated recommendation generation
    """
    
    def __init__(self, config: Dict[str, Any], data_path: str = "/data/benchmarks"):
        """
        Initialize Local vs Cloud Benchmark.
        
        Args:
            config: Configuration dictionary
            data_path: Path to store benchmark results
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.data_path = data_path
        
        # Ensure data directory exists
        os.makedirs(data_path, exist_ok=True)
        
        # Test cases
        self.test_cases: List[ComparisonTestCase] = []
        
        # Results storage
        self.comparison_results: List[ComparisonResult] = []
        self.benchmark_reports: List[BenchmarkReport] = []
        
        # AI components
        self.local_ai = None
        self.cloud_ai = None
        
        # Performance tracking
        self.performance_benchmarks = None
        
        # Initialize components if available
        if DEPENDENCIES_AVAILABLE:
            self._initialize_components()
        
        # Create default test cases
        self._create_default_test_cases()
        
        self.logger.info("Local vs Cloud Benchmark initialized")

    def _initialize_components(self):
        """Initialize AI components for testing."""
        try:
            # Initialize local AI (Ollama)
            self.local_ai = OllamaClient(self.config)
            
            # Initialize cloud AI coordinator
            self.cloud_ai = AICoordinator(self.config)
            
            # Initialize performance benchmarks
            self.performance_benchmarks = PerformanceBenchmarks(self.data_path)
            
        except Exception as e:
            self.logger.error(f"Error initializing AI components: {e}")

    def _create_default_test_cases(self):
        """Create default test cases for comparison."""
        # Image analysis test cases
        self.add_test_case(ComparisonTestCase(
            test_id="img_simple_room",
            name="Simple Room Analysis",
            description="Analyze a simple, well-lit room image",
            input_data="test_images/simple_room.jpg",
            expected_output_type="room_analysis",
            complexity_level="simple",
            test_category="image_analysis"
        ))
        
        self.add_test_case(ComparisonTestCase(
            test_id="img_complex_cluttered",
            name="Complex Cluttered Space",
            description="Analyze a complex, cluttered space with multiple objects",
            input_data="test_images/cluttered_room.jpg",
            expected_output_type="room_analysis",
            complexity_level="complex",
            test_category="image_analysis"
        ))
        
        # Task generation test cases
        self.add_test_case(ComparisonTestCase(
            test_id="task_simple_clean",
            name="Simple Cleaning Tasks",
            description="Generate tasks for basic room cleaning",
            input_data="Room has some clothes on the floor and unmade bed",
            expected_output_type="task_list",
            complexity_level="simple",
            test_category="task_generation"
        ))
        
        self.add_test_case(ComparisonTestCase(
            test_id="task_complex_organization",
            name="Complex Organization Tasks",
            description="Generate tasks for complex room organization",
            input_data="Cluttered office with papers, books, electronics scattered everywhere",
            expected_output_type="task_list",
            complexity_level="complex",
            test_category="task_generation"
        ))

    def add_test_case(self, test_case: ComparisonTestCase):
        """Add a test case to the benchmark suite."""
        self.test_cases.append(test_case)
        self.logger.info(f"Added test case: {test_case.name}")

    async def run_comprehensive_benchmark(self, iterations: int = 3) -> BenchmarkReport:
        """
        Run comprehensive benchmark comparing local and cloud implementations.
        
        Args:
            iterations: Number of iterations per test case
            
        Returns:
            BenchmarkReport with detailed analysis
        """
        self.logger.info("Starting comprehensive local vs cloud benchmark")
        
        report_id = f"benchmark_report_{int(time.time())}"
        start_time = datetime.now(timezone.utc)
        
        # Run all test cases
        individual_results = []
        
        for test_case in self.test_cases:
            self.logger.info(f"Running test case: {test_case.name}")
            
            try:
                result = await self._run_comparison_test(test_case, iterations)
                individual_results.append(result)
                
            except Exception as e:
                self.logger.error(f"Error running test case {test_case.test_id}: {e}")
        
        # Calculate aggregate metrics
        aggregate_metrics = self._calculate_aggregate_metrics(individual_results)
        
        # Generate overall recommendation
        overall_recommendation = self._generate_overall_recommendation(aggregate_metrics)
        
        # Perform cost analysis
        cost_analysis = self._perform_cost_analysis(individual_results)
        
        # Create performance summary
        performance_summary = self._create_performance_summary(individual_results)
        
        # Create benchmark report
        report = BenchmarkReport(
            report_id=report_id,
            timestamp=start_time.isoformat(),
            test_configuration={
                "iterations_per_test": iterations,
                "total_test_cases": len(self.test_cases),
                "test_categories": list(set(tc.test_category for tc in self.test_cases))
            },
            individual_results=individual_results,
            aggregate_metrics=aggregate_metrics,
            overall_recommendation=overall_recommendation,
            cost_analysis=cost_analysis,
            performance_summary=performance_summary
        )
        
        # Store report
        self.benchmark_reports.append(report)
        self._save_benchmark_report(report)
        
        self.logger.info("Comprehensive benchmark completed")
        return report

    async def _run_comparison_test(self, test_case: ComparisonTestCase, iterations: int) -> ComparisonResult:
        """Run a single comparison test between local and cloud."""
        local_times = []
        cloud_times = []
        local_errors = 0
        cloud_errors = 0
        local_results = []
        cloud_results = []
        
        for i in range(iterations):
            # Test local implementation
            try:
                local_start = time.time()
                local_result = await self._execute_local_test(test_case)
                local_time = time.time() - local_start
                
                local_times.append(local_time)
                local_results.append(local_result)
                
            except Exception as e:
                local_errors += 1
                self.logger.debug(f"Local test error: {e}")
            
            # Test cloud implementation
            try:
                cloud_start = time.time()
                cloud_result = await self._execute_cloud_test(test_case)
                cloud_time = time.time() - cloud_start
                
                cloud_times.append(cloud_time)
                cloud_results.append(cloud_result)
                
            except Exception as e:
                cloud_errors += 1
                self.logger.debug(f"Cloud test error: {e}")
            
            # Small delay between iterations
            await asyncio.sleep(0.1)
        
        # Calculate metrics
        local_metrics = self._calculate_test_metrics(local_times, local_errors, local_results, iterations)
        cloud_metrics = self._calculate_test_metrics(cloud_times, cloud_errors, cloud_results, iterations)
        
        # Calculate comparison ratios
        comparison_ratios = self._calculate_comparison_ratios(local_metrics, cloud_metrics)
        
        # Determine winner
        winner, confidence_score = self._determine_winner(local_metrics, cloud_metrics, test_case)
        
        # Generate recommendations
        recommendations = self._generate_test_recommendations(local_metrics, cloud_metrics, test_case)
        
        return ComparisonResult(
            test_case_id=test_case.test_id,
            local_metrics=local_metrics,
            cloud_metrics=cloud_metrics,
            comparison_ratios=comparison_ratios,
            winner=winner,
            confidence_score=confidence_score,
            recommendations=recommendations
        )

    async def _execute_local_test(self, test_case: ComparisonTestCase) -> Any:
        """Execute test using local AI implementation."""
        if not self.local_ai:
            raise Exception("Local AI not available")
        
        if test_case.test_category == "image_analysis":
            # Use optimized settings for local inference
            optimization_options = OptimizationOptions(
                quantization_level="dynamic",
                use_gpu=True,
                context_length=2048
            )
            
            result = await self.local_ai.analyze_image_local(
                image_path=test_case.input_data,
                optimization_options=optimization_options
            )
            return result
            
        elif test_case.test_category == "task_generation":
            optimization_options = OptimizationOptions(
                quantization_level="dynamic",
                use_gpu=True,
                context_length=1024,
                num_predict=256
            )
            
            result = await self.local_ai.generate_tasks_local(
                analysis=test_case.input_data,
                context={},
                optimization_options=optimization_options
            )
            return result
        
        else:
            raise Exception(f"Unsupported test category: {test_case.test_category}")

    async def _execute_cloud_test(self, test_case: ComparisonTestCase) -> Any:
        """Execute test using cloud AI implementation."""
        if not self.cloud_ai:
            raise Exception("Cloud AI not available")
        
        if test_case.test_category == "image_analysis":
            result = await self.cloud_ai.analyze_image(test_case.input_data)
            return result
            
        elif test_case.test_category == "task_generation":
            result = await self.cloud_ai.generate_tasks(test_case.input_data, {})
            return result
        
        else:
            raise Exception(f"Unsupported test category: {test_case.test_category}")

    def _calculate_test_metrics(self, times: List[float], errors: int, 
                               results: List[Any], iterations: int) -> Dict[str, float]:
        """Calculate metrics for a single test."""
        total_requests = len(times) + errors
        success_rate = len(times) / iterations if iterations > 0 else 0
        
        metrics = {
            "avg_response_time": statistics.mean(times) if times else float('inf'),
            "min_response_time": min(times) if times else 0,
            "max_response_time": max(times) if times else 0,
            "success_rate": success_rate,
            "error_rate": errors / iterations if iterations > 0 else 1,
            "throughput": len(times) / sum(times) if times and sum(times) > 0 else 0
        }
        
        # Add response time percentiles if we have data
        if times:
            sorted_times = sorted(times)
            metrics["p95_response_time"] = sorted_times[int(0.95 * len(sorted_times))]
            metrics["p99_response_time"] = sorted_times[int(0.99 * len(sorted_times))]
        
        return metrics

    def _calculate_comparison_ratios(self, local_metrics: Dict[str, float], 
                                   cloud_metrics: Dict[str, float]) -> Dict[str, float]:
        """Calculate ratios between local and cloud metrics."""
        ratios = {}
        
        for metric in local_metrics:
            if metric in cloud_metrics:
                cloud_val = cloud_metrics[metric]
                local_val = local_metrics[metric]
                
                if cloud_val != 0:
                    ratios[f"{metric}_ratio"] = local_val / cloud_val
                else:
                    ratios[f"{metric}_ratio"] = float('inf') if local_val > 0 else 1.0
        
        return ratios

    def _determine_winner(self, local_metrics: Dict[str, float], cloud_metrics: Dict[str, float], 
                         test_case: ComparisonTestCase) -> Tuple[str, float]:
        """Determine winner based on weighted scoring."""
        # Scoring weights based on test complexity
        if test_case.complexity_level == "simple":
            weights = {"response_time": 0.4, "success_rate": 0.3, "throughput": 0.3}
        elif test_case.complexity_level == "complex":
            weights = {"response_time": 0.3, "success_rate": 0.4, "throughput": 0.3}
        else:  # medium
            weights = {"response_time": 0.35, "success_rate": 0.35, "throughput": 0.3}
        
        local_score = 0
        cloud_score = 0
        
        # Response time (lower is better)
        if cloud_metrics["avg_response_time"] > 0:
            time_ratio = local_metrics["avg_response_time"] / cloud_metrics["avg_response_time"]
            if time_ratio < 1:
                local_score += weights["response_time"] * (1 - time_ratio)
            else:
                cloud_score += weights["response_time"] * (1 - 1/time_ratio)
        
        # Success rate (higher is better)
        local_score += weights["success_rate"] * local_metrics["success_rate"]
        cloud_score += weights["success_rate"] * cloud_metrics["success_rate"]
        
        # Throughput (higher is better)
        if local_metrics["throughput"] + cloud_metrics["throughput"] > 0:
            total_throughput = local_metrics["throughput"] + cloud_metrics["throughput"]
            local_score += weights["throughput"] * (local_metrics["throughput"] / total_throughput)
            cloud_score += weights["throughput"] * (cloud_metrics["throughput"] / total_throughput)
        
        # Determine winner
        if abs(local_score - cloud_score) < 0.1:
            winner = "tie"
            confidence = 1 - abs(local_score - cloud_score)
        elif local_score > cloud_score:
            winner = "local"
            confidence = min(1.0, (local_score - cloud_score) / max(local_score, cloud_score))
        else:
            winner = "cloud"
            confidence = min(1.0, (cloud_score - local_score) / max(local_score, cloud_score))
        
        return winner, confidence

    def _generate_test_recommendations(self, local_metrics: Dict[str, float], 
                                     cloud_metrics: Dict[str, float], 
                                     test_case: ComparisonTestCase) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Response time analysis
        if local_metrics["avg_response_time"] < cloud_metrics["avg_response_time"] * 0.5:
            recommendations.append("Local implementation shows significantly faster response times")
        elif cloud_metrics["avg_response_time"] < local_metrics["avg_response_time"] * 0.5:
            recommendations.append("Cloud implementation shows significantly faster response times")
        
        # Reliability analysis
        if local_metrics["success_rate"] > 0.95 and cloud_metrics["success_rate"] < 0.9:
            recommendations.append("Local implementation shows better reliability")
        elif cloud_metrics["success_rate"] > 0.95 and local_metrics["success_rate"] < 0.9:
            recommendations.append("Cloud implementation shows better reliability")
        
        # Complexity-specific recommendations
        if test_case.complexity_level == "complex":
            if cloud_metrics["success_rate"] > local_metrics["success_rate"]:
                recommendations.append("Cloud may be better for complex tasks requiring advanced AI capabilities")
        
        if test_case.complexity_level == "simple":
            if local_metrics["avg_response_time"] < cloud_metrics["avg_response_time"]:
                recommendations.append("Local implementation preferred for simple, frequent tasks")
        
        return recommendations

    def _calculate_aggregate_metrics(self, results: List[ComparisonResult]) -> Dict[str, Dict[str, float]]:
        """Calculate aggregate metrics across all test results."""
        if not results:
            return {}
        
        local_times = []
        cloud_times = []
        local_success_rates = []
        cloud_success_rates = []
        
        for result in results:
            local_times.append(result.local_metrics["avg_response_time"])
            cloud_times.append(result.cloud_metrics["avg_response_time"])
            local_success_rates.append(result.local_metrics["success_rate"])
            cloud_success_rates.append(result.cloud_metrics["success_rate"])
        
        return {
            "local": {
                "avg_response_time": statistics.mean(local_times),
                "avg_success_rate": statistics.mean(local_success_rates),
                "response_time_stdev": statistics.stdev(local_times) if len(local_times) > 1 else 0
            },
            "cloud": {
                "avg_response_time": statistics.mean(cloud_times),
                "avg_success_rate": statistics.mean(cloud_success_rates),
                "response_time_stdev": statistics.stdev(cloud_times) if len(cloud_times) > 1 else 0
            }
        }

    def _generate_overall_recommendation(self, aggregate_metrics: Dict[str, Dict[str, float]]) -> str:
        """Generate overall recommendation based on aggregate results."""
        if not aggregate_metrics:
            return "Insufficient data for recommendation"
        
        local = aggregate_metrics.get("local", {})
        cloud = aggregate_metrics.get("cloud", {})
        
        local_time = local.get("avg_response_time", float('inf'))
        cloud_time = cloud.get("avg_response_time", float('inf'))
        local_success = local.get("avg_success_rate", 0)
        cloud_success = cloud.get("avg_success_rate", 0)
        
        # Decision logic
        if local_time < cloud_time * 0.7 and local_success > 0.9:
            return "Recommend local implementation for better performance and reliability"
        elif cloud_success > local_success * 1.1 and cloud_time < local_time * 1.5:
            return "Recommend cloud implementation for better accuracy and reasonable performance"
        elif abs(local_time - cloud_time) / max(local_time, cloud_time) < 0.2:
            return "Performance is similar - consider hybrid approach based on use case"
        else:
            return "Mixed results - detailed analysis required for specific use cases"

    def _perform_cost_analysis(self, results: List[ComparisonResult]) -> Dict[str, float]:
        """Perform cost analysis for local vs cloud implementations."""
        # Simplified cost model - in reality this would be more complex
        local_cost_per_request = 0.001  # Estimated local cost
        cloud_cost_per_request = 0.01   # Estimated cloud cost
        
        total_requests = len(results)
        
        return {
            "local_total_cost": total_requests * local_cost_per_request,
            "cloud_total_cost": total_requests * cloud_cost_per_request,
            "cost_savings_local": (total_requests * cloud_cost_per_request) - (total_requests * local_cost_per_request),
            "cost_ratio": cloud_cost_per_request / local_cost_per_request
        }

    def _create_performance_summary(self, results: List[ComparisonResult]) -> Dict[str, Any]:
        """Create performance summary from results."""
        local_wins = sum(1 for r in results if r.winner == "local")
        cloud_wins = sum(1 for r in results if r.winner == "cloud")
        ties = sum(1 for r in results if r.winner == "tie")
        
        return {
            "total_tests": len(results),
            "local_wins": local_wins,
            "cloud_wins": cloud_wins,
            "ties": ties,
            "local_win_rate": local_wins / len(results) if results else 0,
            "cloud_win_rate": cloud_wins / len(results) if results else 0,
            "avg_confidence": statistics.mean([r.confidence_score for r in results]) if results else 0
        }

    def _save_benchmark_report(self, report: BenchmarkReport):
        """Save benchmark report to disk."""
        try:
            report_file = os.path.join(self.data_path, f"benchmark_report_{report.report_id}.json")
            
            with open(report_file, 'w') as f:
                json.dump(asdict(report), f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Error saving benchmark report: {e}")

    def get_latest_report(self) -> Optional[BenchmarkReport]:
        """Get the latest benchmark report."""
        return self.benchmark_reports[-1] if self.benchmark_reports else None
