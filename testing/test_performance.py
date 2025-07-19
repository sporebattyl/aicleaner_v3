"""
Performance Testing Module for AICleaner v3
Tests system performance under various conditions
"""

import time
import asyncio
import gc
import psutil
from pathlib import Path
from typing import Dict, Any, List
import sys
import os

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from addons.aicleaner_v3.core.simple_logging import get_simple_logger
from addons.aicleaner_v3.core.diagnostics import get_diagnostic_tool

logger = get_simple_logger("test_performance")


class PerformanceTester:
    """Performance testing utility"""
    
    def __init__(self):
        self.diagnostic_tool = get_diagnostic_tool()
        self.baseline_metrics = None
        self.test_results = {}
    
    def capture_baseline(self) -> Dict[str, Any]:
        """Capture baseline system metrics"""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            baseline = {
                "memory_used_mb": memory.used / (1024 * 1024),
                "memory_percent": memory.percent,
                "cpu_percent": cpu_percent,
                "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
                "processes": len(psutil.pids())
            }
            
            self.baseline_metrics = baseline
            logger.info("Baseline metrics captured")
            return baseline
        except Exception as e:
            logger.error(f"Error capturing baseline: {e}")
            return {}
    
    def benchmark_logging_performance(self) -> Dict[str, Any]:
        """Benchmark logging system performance"""
        logger.info("Starting logging performance benchmark...")
        
        # Test different log levels and message sizes
        test_cases = [
            ("info", "Short message", 1000),
            ("debug", "Medium length message with some metadata and context", 500),
            ("error", "Long error message with detailed context and stack trace information that might be generated during error conditions", 200),
        ]
        
        results = {}
        
        for level, message, iterations in test_cases:
            test_logger = get_simple_logger(f"perf_test_{level}")
            
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            
            for i in range(iterations):
                if level == "info":
                    test_logger.info(f"{message} #{i}")
                elif level == "debug":
                    test_logger.debug(f"{message} #{i}")
                elif level == "error":
                    test_logger.error(f"{message} #{i}")
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss
            
            duration = end_time - start_time
            memory_delta = (end_memory - start_memory) / (1024 * 1024)  # MB
            
            results[f"logging_{level}"] = {
                "duration_seconds": duration,
                "messages_per_second": iterations / duration,
                "memory_delta_mb": memory_delta,
                "status": "PASS" if duration < 5.0 else "WARN"
            }
            
            logger.info(f"Logging {level}: {iterations} messages in {duration:.2f}s ({iterations/duration:.1f} msg/s)")
        
        return results
    
    def benchmark_diagnostic_tools(self) -> Dict[str, Any]:
        """Benchmark diagnostic tool performance"""
        logger.info("Starting diagnostic tools benchmark...")
        
        results = {}
        
        # Test system info gathering
        start_time = time.time()
        system_info = self.diagnostic_tool.get_system_info()
        system_info_time = time.time() - start_time
        
        results["system_info_gathering"] = {
            "duration_seconds": system_info_time,
            "status": "PASS" if system_info_time < 2.0 else "WARN",
            "memory_total_gb": system_info.memory_total / (1024**3)
        }
        
        # Test health check
        start_time = time.time()
        health_check = self.diagnostic_tool.perform_health_check()
        health_check_time = time.time() - start_time
        
        results["health_check"] = {
            "duration_seconds": health_check_time,
            "status": "PASS" if health_check_time < 5.0 else "WARN",
            "overall_health": health_check.overall_status,
            "issues_found": len(health_check.issues)
        }
        
        # Test log analysis
        start_time = time.time()
        recent_logs = self.diagnostic_tool.get_recent_logs(100)
        log_analysis_time = time.time() - start_time
        
        results["log_analysis"] = {
            "duration_seconds": log_analysis_time,
            "status": "PASS" if log_analysis_time < 3.0 else "WARN",
            "logs_analyzed": len(recent_logs)
        }
        
        return results
    
    def benchmark_memory_usage(self) -> Dict[str, Any]:
        """Benchmark memory usage patterns"""
        logger.info("Starting memory usage benchmark...")
        
        results = {}
        
        # Test memory usage over time
        initial_memory = psutil.Process().memory_info().rss / (1024 * 1024)
        
        # Simulate sustained operation
        test_logger = get_simple_logger("memory_test")
        for i in range(1000):
            test_logger.info(f"Memory test iteration {i}")
            if i % 100 == 0:
                gc.collect()  # Force garbage collection
        
        # Capture memory after operations
        final_memory = psutil.Process().memory_info().rss / (1024 * 1024)
        memory_growth = final_memory - initial_memory
        
        results["memory_usage"] = {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_growth_mb": memory_growth,
            "status": "PASS" if memory_growth < 50 else "WARN"  # Allow up to 50MB growth
        }
        
        # Test memory cleanup
        gc.collect()
        cleanup_memory = psutil.Process().memory_info().rss / (1024 * 1024)
        memory_recovered = final_memory - cleanup_memory
        
        results["memory_cleanup"] = {
            "memory_recovered_mb": memory_recovered,
            "cleanup_memory_mb": cleanup_memory,
            "status": "PASS" if memory_recovered > 0 else "WARN"
        }
        
        return results
    
    def benchmark_concurrent_operations(self) -> Dict[str, Any]:
        """Benchmark concurrent operation performance"""
        logger.info("Starting concurrent operations benchmark...")
        
        results = {}
        
        async def concurrent_logging_task(task_id: int, message_count: int):
            """Simulate concurrent logging operations"""
            test_logger = get_simple_logger(f"concurrent_task_{task_id}")
            for i in range(message_count):
                test_logger.info(f"Task {task_id} message {i}")
                await asyncio.sleep(0.001)  # Small delay to simulate real work
        
        # Test concurrent logging
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        async def run_concurrent_test():
            tasks = []
            for i in range(5):  # 5 concurrent tasks
                task = concurrent_logging_task(i, 100)
                tasks.append(task)
            await asyncio.gather(*tasks)
        
        try:
            asyncio.run(run_concurrent_test())
            concurrent_time = time.time() - start_time
            end_memory = psutil.Process().memory_info().rss
            memory_delta = (end_memory - start_memory) / (1024 * 1024)
            
            results["concurrent_logging"] = {
                "duration_seconds": concurrent_time,
                "memory_delta_mb": memory_delta,
                "status": "PASS" if concurrent_time < 10.0 else "WARN"
            }
        except Exception as e:
            results["concurrent_logging"] = {
                "duration_seconds": 0,
                "memory_delta_mb": 0,
                "status": "FAIL",
                "error": str(e)
            }
        
        return results
    
    def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all performance benchmarks"""
        logger.info("Starting comprehensive performance benchmarks...")
        
        # Capture baseline
        baseline = self.capture_baseline()
        
        # Run individual benchmarks
        all_results = {
            "baseline": baseline,
            "timestamp": time.time(),
            "system_info": {
                "python_version": sys.version,
                "platform": sys.platform,
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / (1024**3)
            }
        }
        
        # Run each benchmark
        try:
            all_results.update(self.benchmark_logging_performance())
            all_results.update(self.benchmark_diagnostic_tools())
            all_results.update(self.benchmark_memory_usage())
            all_results.update(self.benchmark_concurrent_operations())
        except Exception as e:
            logger.error(f"Error during benchmarking: {e}")
            all_results["benchmark_error"] = str(e)
        
        logger.info("Performance benchmarks completed")
        return all_results


def run_performance_benchmarks() -> Dict[str, Any]:
    """Main function to run performance benchmarks"""
    tester = PerformanceTester()
    return tester.run_all_benchmarks()


if __name__ == "__main__":
    # Run benchmarks if script is executed directly
    results = run_performance_benchmarks()
    
    # Print summary
    print("\n=== Performance Benchmark Summary ===")
    for key, value in results.items():
        if isinstance(value, dict) and "status" in value:
            status = value["status"]
            print(f"{key}: {status}")
    print("======================================")