#!/usr/bin/env python3
"""
Benchmark Runner Script for AICleaner Phase 3C.2
Orchestrates and executes all performance benchmarks.
"""

import asyncio
import argparse
import logging
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from benchmarks.load_test_suite import LoadTestSuite, LoadTestConfig
    from benchmarks.local_vs_cloud_benchmark import LocalVsCloudBenchmark
    from core.performance_benchmarks import PerformanceBenchmarks
    from core.resource_monitor import ResourceMonitor
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False


class BenchmarkRunner:
    """
    Orchestrates and executes all performance benchmarks for AICleaner.
    
    Features:
    - Configurable benchmark execution
    - Comprehensive reporting
    - Resource monitoring during tests
    - Automated result analysis
    - Export capabilities
    """
    
    def __init__(self, config_path: str = "config.yaml", data_path: str = "/data/benchmarks"):
        """
        Initialize Benchmark Runner.
        
        Args:
            config_path: Path to configuration file
            data_path: Path to store benchmark results
        """
        self.logger = self._setup_logging()
        self.config = self._load_config(config_path)
        self.data_path = data_path
        
        # Ensure data directory exists
        os.makedirs(data_path, exist_ok=True)
        
        # Initialize benchmark components
        self.load_test_suite = None
        self.local_vs_cloud_benchmark = None
        self.performance_benchmarks = None
        self.resource_monitor = None
        
        if DEPENDENCIES_AVAILABLE:
            self._initialize_components()
        
        self.logger.info("Benchmark Runner initialized")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('benchmark_runner.log')
            ]
        )
        return logging.getLogger(__name__)

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                import yaml
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f)
            else:
                with open(config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Could not load config from {config_path}: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "local_llm": {
                "enabled": True,
                "ollama_host": "localhost:11434"
            },
            "cloud_ai": {
                "enabled": True,
                "providers": ["openai", "anthropic"]
            },
            "performance_optimization": {
                "monitoring": {
                    "enabled": True
                },
                "benchmarking": {
                    "enabled": True
                }
            }
        }

    def _initialize_components(self):
        """Initialize benchmark components."""
        try:
            self.load_test_suite = LoadTestSuite(self.config, self.data_path)
            self.local_vs_cloud_benchmark = LocalVsCloudBenchmark(self.config, self.data_path)
            self.performance_benchmarks = PerformanceBenchmarks(self.data_path)
            self.resource_monitor = ResourceMonitor(self.config, self.data_path)
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")

    async def run_all_benchmarks(self, quick_mode: bool = False) -> Dict[str, Any]:
        """
        Run all available benchmarks.
        
        Args:
            quick_mode: If True, run abbreviated versions of benchmarks
            
        Returns:
            Dictionary with all benchmark results
        """
        self.logger.info("Starting comprehensive benchmark suite")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "quick_mode": quick_mode,
            "benchmarks": {}
        }
        
        # Start resource monitoring
        if self.resource_monitor:
            await self.resource_monitor.start_monitoring(interval=10)
        
        try:
            # Run load tests
            if self.load_test_suite:
                self.logger.info("Running load tests...")
                load_results = await self._run_load_tests(quick_mode)
                results["benchmarks"]["load_tests"] = load_results
            
            # Run local vs cloud comparison
            if self.local_vs_cloud_benchmark:
                self.logger.info("Running local vs cloud comparison...")
                comparison_results = await self._run_comparison_benchmarks(quick_mode)
                results["benchmarks"]["local_vs_cloud"] = comparison_results
            
            # Run performance benchmarks
            if self.performance_benchmarks:
                self.logger.info("Running performance benchmarks...")
                perf_results = await self._run_performance_benchmarks(quick_mode)
                results["benchmarks"]["performance"] = perf_results
            
        except Exception as e:
            self.logger.error(f"Error during benchmark execution: {e}")
            results["error"] = str(e)
        
        finally:
            # Stop resource monitoring
            if self.resource_monitor:
                await self.resource_monitor.stop_monitoring()
                
                # Get resource summary
                resource_summary = await self.resource_monitor.get_performance_summary()
                results["resource_utilization"] = resource_summary
        
        # Save comprehensive results
        self._save_comprehensive_results(results)
        
        self.logger.info("Comprehensive benchmark suite completed")
        return results

    async def _run_load_tests(self, quick_mode: bool) -> Dict[str, Any]:
        """Run load test scenarios."""
        results = {}
        
        scenarios = ["image_analysis_load", "task_generation_load"]
        if not quick_mode:
            scenarios.extend(["state_management_load", "mixed_workload"])
        
        for scenario_id in scenarios:
            try:
                # Configure test parameters
                config = LoadTestConfig(
                    max_concurrent_users=5 if quick_mode else 10,
                    test_duration_seconds=30 if quick_mode else 120,
                    ramp_up_duration_seconds=10 if quick_mode else 30
                )
                
                result = await self.load_test_suite.run_load_test(scenario_id, config)
                results[scenario_id] = {
                    "status": "completed",
                    "requests_per_second": result.requests_per_second,
                    "error_rate_percent": result.error_rate_percent,
                    "average_response_time": result.average_response_time,
                    "p95_response_time": result.p95_response_time
                }
                
            except Exception as e:
                self.logger.error(f"Error in load test {scenario_id}: {e}")
                results[scenario_id] = {"status": "failed", "error": str(e)}
        
        return results

    async def _run_comparison_benchmarks(self, quick_mode: bool) -> Dict[str, Any]:
        """Run local vs cloud comparison benchmarks."""
        try:
            iterations = 2 if quick_mode else 5
            report = await self.local_vs_cloud_benchmark.run_comprehensive_benchmark(iterations)
            
            return {
                "status": "completed",
                "report_id": report.report_id,
                "overall_recommendation": report.overall_recommendation,
                "performance_summary": report.performance_summary,
                "cost_analysis": report.cost_analysis,
                "test_count": len(report.individual_results)
            }
            
        except Exception as e:
            self.logger.error(f"Error in comparison benchmarks: {e}")
            return {"status": "failed", "error": str(e)}

    async def _run_performance_benchmarks(self, quick_mode: bool) -> Dict[str, Any]:
        """Run core performance benchmarks."""
        results = {}
        
        try:
            # Simple latency test
            async def test_function():
                await asyncio.sleep(0.01)
                return "test"
            
            latency_result = await self.performance_benchmarks.benchmark_latency(
                component="test_component",
                operation="test_operation", 
                test_func=test_function,
                iterations=5 if quick_mode else 20
            )
            
            results["latency_test"] = {
                "status": "completed",
                "avg_time": latency_result.metrics.get("avg_time", 0),
                "min_time": latency_result.metrics.get("min_time", 0),
                "max_time": latency_result.metrics.get("max_time", 0)
            }
            
            # Throughput test
            throughput_result = await self.performance_benchmarks.benchmark_throughput(
                component="test_component",
                operation="test_operation",
                test_func=test_function,
                duration_seconds=10 if quick_mode else 30
            )
            
            results["throughput_test"] = {
                "status": "completed",
                "requests_per_second": throughput_result.metrics.get("requests_per_second", 0),
                "total_requests": throughput_result.metrics.get("total_requests", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error in performance benchmarks: {e}")
            results["error"] = str(e)
        
        return results

    def _save_comprehensive_results(self, results: Dict[str, Any]):
        """Save comprehensive benchmark results."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comprehensive_benchmark_results_{timestamp}.json"
            filepath = os.path.join(self.data_path, filename)
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            self.logger.info(f"Comprehensive results saved to {filepath}")
            
        except Exception as e:
            self.logger.error(f"Error saving comprehensive results: {e}")

    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a human-readable report from benchmark results."""
        report_lines = [
            "=" * 60,
            "AICleaner Performance Benchmark Report",
            "=" * 60,
            f"Timestamp: {results.get('timestamp', 'Unknown')}",
            f"Quick Mode: {results.get('quick_mode', False)}",
            ""
        ]
        
        # Load test results
        if "load_tests" in results.get("benchmarks", {}):
            report_lines.extend([
                "Load Test Results:",
                "-" * 20
            ])
            
            for scenario, result in results["benchmarks"]["load_tests"].items():
                if result.get("status") == "completed":
                    report_lines.extend([
                        f"  {scenario}:",
                        f"    RPS: {result.get('requests_per_second', 0):.2f}",
                        f"    Error Rate: {result.get('error_rate_percent', 0):.2f}%",
                        f"    Avg Response Time: {result.get('average_response_time', 0):.3f}s",
                        ""
                    ])
        
        # Comparison results
        if "local_vs_cloud" in results.get("benchmarks", {}):
            comparison = results["benchmarks"]["local_vs_cloud"]
            if comparison.get("status") == "completed":
                report_lines.extend([
                    "Local vs Cloud Comparison:",
                    "-" * 30,
                    f"  Recommendation: {comparison.get('overall_recommendation', 'N/A')}",
                    f"  Tests Completed: {comparison.get('test_count', 0)}",
                    ""
                ])
        
        # Resource utilization
        if "resource_utilization" in results:
            resource = results["resource_utilization"]
            report_lines.extend([
                "Resource Utilization:",
                "-" * 22,
                f"  CPU: {resource.get('cpu', {}).get('average_percent', 0):.1f}% avg",
                f"  Memory: {resource.get('memory', {}).get('average_percent', 0):.1f}% avg",
                ""
            ])
        
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)


async def main():
    """Main entry point for benchmark runner."""
    parser = argparse.ArgumentParser(description="AICleaner Performance Benchmark Runner")
    parser.add_argument("--config", default="config.yaml", help="Configuration file path")
    parser.add_argument("--data-path", default="/data/benchmarks", help="Data storage path")
    parser.add_argument("--quick", action="store_true", help="Run in quick mode")
    parser.add_argument("--output", help="Output file for results")
    
    args = parser.parse_args()
    
    # Initialize runner
    runner = BenchmarkRunner(args.config, args.data_path)
    
    if not DEPENDENCIES_AVAILABLE:
        print("Error: Required dependencies not available. Please install all components.")
        return 1
    
    try:
        # Run benchmarks
        results = await runner.run_all_benchmarks(quick_mode=args.quick)
        
        # Generate and display report
        report = runner.generate_report(results)
        print(report)
        
        # Save to output file if specified
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"\nReport saved to {args.output}")
        
        return 0
        
    except Exception as e:
        print(f"Error running benchmarks: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
