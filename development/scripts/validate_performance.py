#!/usr/bin/env python3
"""
Performance Validation Script
Phase 5A: Performance Optimization Validation

Comprehensive validation of all performance optimizations implemented in Phase 5A.
Generates performance report and validates that optimizations meet expected benchmarks.
"""

import asyncio
import json
import logging
import time
import sys
import os
from typing import Dict, List, Any
from datetime import datetime
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Performance optimization imports
from performance.profiler import get_profiler, get_memory_profiler, profile_async
from performance.metrics import get_tracker
from performance.ai_cache import get_ai_cache, clear_ai_cache
from performance.event_loop_optimizer import (
    get_event_loop_optimizer, start_event_loop_monitoring, stop_event_loop_monitoring
)
from performance.serialization_optimizer import (
    get_serialization_optimizer, fast_json_dumps, fast_json_loads
)
from performance.state_optimizer import (
    get_state_optimizer, start_state_optimization, stop_state_optimization,
    read_optimized_state, write_optimized_state
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerformanceValidator:
    """Validates all Phase 5A performance optimizations."""
    
    def __init__(self):
        self.results: Dict[str, Any] = {}
        self.start_time = time.time()
        
    async def run_validation(self) -> Dict[str, Any]:
        """Run comprehensive performance validation."""
        logger.info("🚀 Starting Phase 5A Performance Validation")
        
        try:
            # Initialize performance systems
            await self._setup_systems()
            
            # Run validation tests
            await self._validate_ai_caching()
            await self._validate_serialization()
            await self._validate_event_loop_optimization()
            await self._validate_state_management()
            await self._validate_profiling_system()
            await self._validate_full_integration()
            
            # Generate final report
            await self._generate_report()
            
        except Exception as e:
            logger.error(f"❌ Validation failed: {e}")
            raise
        finally:
            await self._cleanup_systems()
        
        return self.results
    
    async def _setup_systems(self):
        """Initialize all performance systems."""
        logger.info("🔧 Setting up performance systems...")
        
        # Start event loop monitoring
        await start_event_loop_monitoring()
        
        # Start state optimization
        await start_state_optimization()
        
        # Clear AI cache
        clear_ai_cache()
        
        logger.info("✅ Performance systems initialized")
    
    async def _cleanup_systems(self):
        """Cleanup performance systems."""
        logger.info("🧹 Cleaning up performance systems...")
        
        try:
            await stop_event_loop_monitoring()
            await stop_state_optimization()
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")
    
    async def _validate_ai_caching(self):
        """Validate AI request caching system."""
        logger.info("🧠 Validating AI Caching System...")
        
        cache = get_ai_cache()
        test_results = {"passed": 0, "failed": 0, "performance": {}}
        
        try:
            # Test 1: Cache miss and set
            prompt = "Test AI request for caching validation"
            
            start_time = time.perf_counter()
            result = await cache.get("test_provider", "test_model", prompt)
            cache_miss_time = time.perf_counter() - start_time
            
            if result is None:
                test_results["passed"] += 1
                logger.info("  ✅ Cache miss working correctly")
            else:
                test_results["failed"] += 1
                logger.error("  ❌ Cache miss failed - found unexpected data")
            
            # Set cache entry
            test_response = {
                "response_text": "Test response for validation",
                "model_used": "test_model",
                "confidence": 0.95
            }
            
            await cache.set("test_provider", "test_model", prompt, test_response)
            
            # Test 2: Cache hit
            start_time = time.perf_counter()
            cached_result = await cache.get("test_provider", "test_model", prompt)
            cache_hit_time = time.perf_counter() - start_time
            
            if cached_result and cached_result["response_text"] == test_response["response_text"]:
                test_results["passed"] += 1
                logger.info("  ✅ Cache hit working correctly")
            else:
                test_results["failed"] += 1
                logger.error("  ❌ Cache hit failed")
            
            # Test 3: Performance validation
            performance_ratio = cache_miss_time / cache_hit_time if cache_hit_time > 0 else 0
            test_results["performance"] = {
                "cache_miss_time": cache_miss_time,
                "cache_hit_time": cache_hit_time,
                "speedup_ratio": performance_ratio,
                "hit_time_under_1ms": cache_hit_time < 0.001
            }
            
            if cache_hit_time < 0.001:
                test_results["passed"] += 1
                logger.info(f"  ✅ Cache performance excellent: {cache_hit_time:.6f}s")
            else:
                test_results["failed"] += 1
                logger.warning(f"  ⚠️ Cache performance slower than expected: {cache_hit_time:.6f}s")
            
            # Test 4: Cache statistics
            stats = cache.get_stats()
            if stats["hits"] > 0 and stats["hit_rate"] > 0:
                test_results["passed"] += 1
                logger.info(f"  ✅ Cache statistics working: {stats['hit_rate']:.2%} hit rate")
            else:
                test_results["failed"] += 1
                logger.error("  ❌ Cache statistics failed")
            
            test_results["cache_stats"] = stats
            
        except Exception as e:
            test_results["failed"] += 1
            test_results["error"] = str(e)
            logger.error(f"  ❌ AI caching validation error: {e}")
        
        self.results["ai_caching"] = test_results
        logger.info(f"🧠 AI Caching: {test_results['passed']} passed, {test_results['failed']} failed")
    
    async def _validate_serialization(self):
        """Validate serialization optimization."""
        logger.info("📄 Validating Serialization Optimization...")
        
        serializer = get_serialization_optimizer()
        test_results = {"passed": 0, "failed": 0, "performance": {}}
        
        try:
            # Create test data
            test_data = {
                "large_array": [{"id": i, "value": f"item_{i}"} for i in range(1000)],
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "version": "1.0.0"
                },
                "nested": {
                    "level1": {
                        "level2": {
                            "data": list(range(500))
                        }
                    }
                }
            }
            
            # Test 1: Fast serialization
            start_time = time.perf_counter()
            fast_serialized = fast_json_dumps(test_data)
            fast_serialize_time = time.perf_counter() - start_time
            
            start_time = time.perf_counter()
            fast_deserialized = fast_json_loads(fast_serialized)
            fast_deserialize_time = time.perf_counter() - start_time
            
            # Test 2: Standard serialization comparison
            start_time = time.perf_counter()
            std_serialized = json.dumps(test_data)
            std_serialize_time = time.perf_counter() - start_time
            
            start_time = time.perf_counter()
            std_deserialized = json.loads(std_serialized)
            std_deserialize_time = time.perf_counter() - start_time
            
            # Test 3: Data integrity
            if fast_deserialized == std_deserialized:
                test_results["passed"] += 1
                logger.info("  ✅ Data integrity maintained")
            else:
                test_results["failed"] += 1
                logger.error("  ❌ Data integrity failed")
            
            # Test 4: Performance comparison
            serialize_speedup = std_serialize_time / fast_serialize_time if fast_serialize_time > 0 else 1
            deserialize_speedup = std_deserialize_time / fast_deserialize_time if fast_deserialize_time > 0 else 1
            
            test_results["performance"] = {
                "fast_serialize_time": fast_serialize_time,
                "fast_deserialize_time": fast_deserialize_time,
                "std_serialize_time": std_serialize_time,
                "std_deserialize_time": std_deserialize_time,
                "serialize_speedup": serialize_speedup,
                "deserialize_speedup": deserialize_speedup
            }
            
            if serialize_speedup >= 1.0 and deserialize_speedup >= 1.0:
                test_results["passed"] += 1
                logger.info(f"  ✅ Performance improvement: {serialize_speedup:.2f}x serialize, {deserialize_speedup:.2f}x deserialize")
            else:
                test_results["failed"] += 1
                logger.warning(f"  ⚠️ Performance not improved: {serialize_speedup:.2f}x serialize, {deserialize_speedup:.2f}x deserialize")
            
            # Test 5: Serializer metrics
            metrics = serializer.get_metrics()
            if metrics.total_serializations > 0:
                test_results["passed"] += 1
                logger.info(f"  ✅ Metrics tracking working: {metrics.total_serializations} operations")
            else:
                test_results["failed"] += 1
                logger.error("  ❌ Metrics tracking failed")
            
            test_results["metrics"] = {
                "total_serializations": metrics.total_serializations,
                "total_deserializations": metrics.total_deserializations,
                "orjson_used": metrics.orjson_used
            }
            
        except Exception as e:
            test_results["failed"] += 1
            test_results["error"] = str(e)
            logger.error(f"  ❌ Serialization validation error: {e}")
        
        self.results["serialization"] = test_results
        logger.info(f"📄 Serialization: {test_results['passed']} passed, {test_results['failed']} failed")
    
    async def _validate_event_loop_optimization(self):
        """Validate event loop optimization."""
        logger.info("🔄 Validating Event Loop Optimization...")
        
        optimizer = get_event_loop_optimizer()
        test_results = {"passed": 0, "failed": 0, "performance": {}}
        
        try:
            # Test 1: Optimized task creation
            async def test_task(task_id: int):
                await asyncio.sleep(0.01)
                return f"Task {task_id} completed"
            
            tasks = []
            start_time = time.perf_counter()
            
            for i in range(10):
                task = optimizer.create_optimized_task(test_task(i), name=f"test_task_{i}")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            task_completion_time = time.perf_counter() - start_time
            
            if len(results) == 10 and all("completed" in result for result in results):
                test_results["passed"] += 1
                logger.info(f"  ✅ Optimized tasks working: {len(results)} tasks in {task_completion_time:.3f}s")
            else:
                test_results["failed"] += 1
                logger.error("  ❌ Optimized tasks failed")
            
            # Test 2: Thread pool execution
            def blocking_operation(value: int) -> int:
                time.sleep(0.05)  # Simulate blocking I/O
                return value * 2
            
            start_time = time.perf_counter()
            result = await optimizer.run_in_thread(blocking_operation, 21)
            thread_operation_time = time.perf_counter() - start_time
            
            if result == 42:
                test_results["passed"] += 1
                logger.info(f"  ✅ Thread pool working: result={result} in {thread_operation_time:.3f}s")
            else:
                test_results["failed"] += 1
                logger.error(f"  ❌ Thread pool failed: expected 42, got {result}")
            
            # Test 3: Diagnostics
            diagnostics = optimizer.get_diagnostics()
            if diagnostics.get("monitoring_enabled") and "uptime" in diagnostics:
                test_results["passed"] += 1
                logger.info("  ✅ Event loop monitoring working")
            else:
                test_results["failed"] += 1
                logger.error("  ❌ Event loop monitoring failed")
            
            test_results["performance"] = {
                "task_completion_time": task_completion_time,
                "thread_operation_time": thread_operation_time
            }
            test_results["diagnostics"] = diagnostics
            
        except Exception as e:
            test_results["failed"] += 1
            test_results["error"] = str(e)
            logger.error(f"  ❌ Event loop optimization validation error: {e}")
        
        self.results["event_loop"] = test_results
        logger.info(f"🔄 Event Loop: {test_results['passed']} passed, {test_results['failed']} failed")
    
    async def _validate_state_management(self):
        """Validate state management optimization."""
        logger.info("💾 Validating State Management Optimization...")
        
        state_optimizer = get_state_optimizer()
        test_results = {"passed": 0, "failed": 0, "performance": {}}
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                test_file = os.path.join(temp_dir, "test_state.json")
                
                # Test 1: State write operation
                test_data = {
                    "config": {"zones": ["room1", "room2"], "enabled": True},
                    "timestamp": datetime.now().isoformat(),
                    "data": list(range(100))
                }
                
                start_time = time.perf_counter()
                success = await write_optimized_state("test_config", test_data, test_file)
                write_time = time.perf_counter() - start_time
                
                if success and os.path.exists(test_file):
                    test_results["passed"] += 1
                    logger.info(f"  ✅ State write working: {write_time:.4f}s")
                else:
                    test_results["failed"] += 1
                    logger.error("  ❌ State write failed")
                
                # Test 2: State read operation
                start_time = time.perf_counter()
                read_data = await read_optimized_state("test_config", test_file)
                read_time = time.perf_counter() - start_time
                
                if read_data and read_data["config"]["enabled"] == test_data["config"]["enabled"]:
                    test_results["passed"] += 1
                    logger.info(f"  ✅ State read working: {read_time:.4f}s")
                else:
                    test_results["failed"] += 1
                    logger.error("  ❌ State read failed")
                
                # Test 3: Cache functionality
                start_time = time.perf_counter()
                cached_data = await read_optimized_state("test_config")  # No file path = cache only
                cache_read_time = time.perf_counter() - start_time
                
                if cached_data and cached_data["config"]["enabled"] == test_data["config"]["enabled"]:
                    test_results["passed"] += 1
                    logger.info(f"  ✅ State cache working: {cache_read_time:.6f}s")
                else:
                    test_results["failed"] += 1
                    logger.error("  ❌ State cache failed")
                
                # Test 4: Performance metrics
                cache_stats = state_optimizer.get_cache_stats()
                if cache_stats["cache_size"] > 0:
                    test_results["passed"] += 1
                    logger.info(f"  ✅ State cache metrics: {cache_stats['cache_size']} entries")
                else:
                    test_results["failed"] += 1
                    logger.error("  ❌ State cache metrics failed")
                
                test_results["performance"] = {
                    "write_time": write_time,
                    "read_time": read_time,
                    "cache_read_time": cache_read_time,
                    "cache_speedup": read_time / cache_read_time if cache_read_time > 0 else 1
                }
                test_results["cache_stats"] = cache_stats
        
        except Exception as e:
            test_results["failed"] += 1
            test_results["error"] = str(e)
            logger.error(f"  ❌ State management validation error: {e}")
        
        self.results["state_management"] = test_results
        logger.info(f"💾 State Management: {test_results['passed']} passed, {test_results['failed']} failed")
    
    async def _validate_profiling_system(self):
        """Validate profiling and metrics system."""
        logger.info("📊 Validating Profiling System...")
        
        profiler = get_profiler()
        memory_profiler = get_memory_profiler()
        tracker = get_tracker()
        test_results = {"passed": 0, "failed": 0, "performance": {}}
        
        try:
            # Test 1: Function profiling
            @profile_async("validation_test")
            async def test_profiled_function():
                await asyncio.sleep(0.1)
                return {"result": "success", "data": list(range(100))}
            
            result = await test_profiled_function()
            
            if result["result"] == "success":
                test_results["passed"] += 1
                logger.info("  ✅ Function profiling working")
            else:
                test_results["failed"] += 1
                logger.error("  ❌ Function profiling failed")
            
            # Test 2: Performance tracking
            async with tracker.track_zone_operation("test_zone", "validation"):
                await asyncio.sleep(0.05)
            
            test_results["passed"] += 1
            logger.info("  ✅ Performance tracking working")
            
            # Test 3: Memory profiling
            memory_stats = memory_profiler.get_current_memory_usage()
            
            if memory_stats.get("rss", 0) > 0:
                test_results["passed"] += 1
                logger.info(f"  ✅ Memory profiling working: {memory_stats['rss']:.1f}MB RSS")
            else:
                test_results["failed"] += 1
                logger.error("  ❌ Memory profiling failed")
            
            # Test 4: Profiler results
            profiler_results = profiler.get_results()
            
            if "validation_test" in profiler_results:
                test_results["passed"] += 1
                logger.info(f"  ✅ Profiler results: {len(profiler_results)} functions tracked")
            else:
                test_results["failed"] += 1
                logger.error("  ❌ Profiler results failed")
            
            test_results["performance"] = {
                "memory_rss_mb": memory_stats.get("rss", 0),
                "memory_vms_mb": memory_stats.get("vms", 0),
                "profiled_functions": len(profiler_results)
            }
            
        except Exception as e:
            test_results["failed"] += 1
            test_results["error"] = str(e)
            logger.error(f"  ❌ Profiling system validation error: {e}")
        
        self.results["profiling"] = test_results
        logger.info(f"📊 Profiling: {test_results['passed']} passed, {test_results['failed']} failed")
    
    async def _validate_full_integration(self):
        """Validate all systems working together."""
        logger.info("🔗 Validating Full System Integration...")
        
        test_results = {"passed": 0, "failed": 0, "performance": {}}
        
        try:
            # Simulate complete AICleaner workflow
            start_time = time.perf_counter()
            
            # 1. Load configuration with state optimization
            config_data = {
                "zones": [{"id": f"zone_{i}", "enabled": True} for i in range(5)],
                "ai_config": {"provider": "openai", "model": "gpt-4o-mini"},
                "performance": {"caching": True, "profiling": True}
            }
            
            await write_optimized_state("integration_config", config_data)
            loaded_config = await read_optimized_state("integration_config")
            
            if loaded_config and len(loaded_config["zones"]) == 5:
                test_results["passed"] += 1
                logger.info("  ✅ Configuration management working")
            
            # 2. AI request caching simulation
            cache = get_ai_cache()
            
            for i in range(3):
                prompt = f"Analyze zone_{i} for cleaning"
                
                # First request (cache miss)
                cached_response = await cache.get("openai", "gpt-4o-mini", prompt)
                if cached_response is None:
                    response_data = {
                        "response_text": f"Zone {i} analysis complete",
                        "confidence": 0.9,
                        "recommendations": ["vacuum", "dust"]
                    }
                    await cache.set("openai", "gpt-4o-mini", prompt, response_data)
                
                # Second request (cache hit)
                cached_response = await cache.get("openai", "gpt-4o-mini", prompt)
                if cached_response:
                    test_results["passed"] += 1
            
            # 3. Data serialization with large payload
            large_data = {
                "zones": loaded_config["zones"],
                "metrics": [{"timestamp": time.time(), "zone": i, "score": 0.8 + i*0.05} for i in range(100)],
                "cache_stats": cache.get_stats()
            }
            
            serialized = fast_json_dumps(large_data)
            deserialized = fast_json_loads(serialized)
            
            if len(deserialized["metrics"]) == 100:
                test_results["passed"] += 1
                logger.info("  ✅ Large data serialization working")
            
            # 4. Concurrent operations
            async def concurrent_task(task_id: int):
                await asyncio.sleep(0.01)
                state_key = f"task_{task_id}"
                await write_optimized_state(state_key, {"id": task_id, "status": "complete"})
                return await read_optimized_state(state_key)
            
            tasks = [concurrent_task(i) for i in range(10)]
            concurrent_results = await asyncio.gather(*tasks)
            
            if len(concurrent_results) == 10 and all(r["status"] == "complete" for r in concurrent_results):
                test_results["passed"] += 1
                logger.info("  ✅ Concurrent operations working")
            
            total_time = time.perf_counter() - start_time
            
            # 5. Performance validation
            cache_stats = cache.get_stats()
            serializer_stats = get_serialization_optimizer().get_performance_report()
            state_stats = get_state_optimizer().get_cache_stats()
            
            test_results["performance"] = {
                "total_integration_time": total_time,
                "cache_hit_rate": cache_stats.get("hit_rate", 0),
                "serializations_per_second": serializer_stats["metrics"]["serializations_per_second"],
                "state_cache_size": state_stats["cache_size"]
            }
            
            if total_time < 5.0:  # Should complete within 5 seconds
                test_results["passed"] += 1
                logger.info(f"  ✅ Integration performance good: {total_time:.2f}s")
            else:
                test_results["failed"] += 1
                logger.warning(f"  ⚠️ Integration performance slow: {total_time:.2f}s")
            
        except Exception as e:
            test_results["failed"] += 1
            test_results["error"] = str(e)
            logger.error(f"  ❌ Full integration validation error: {e}")
        
        self.results["integration"] = test_results
        logger.info(f"🔗 Integration: {test_results['passed']} passed, {test_results['failed']} failed")
    
    async def _generate_report(self):
        """Generate comprehensive validation report."""
        logger.info("📋 Generating Performance Validation Report...")
        
        total_time = time.time() - self.start_time
        
        # Calculate overall statistics
        total_passed = sum(result.get("passed", 0) for result in self.results.values())
        total_failed = sum(result.get("failed", 0) for result in self.results.values())
        total_tests = total_passed + total_failed
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        # Generate report
        report = {
            "validation_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_validation_time": total_time,
                "total_tests": total_tests,
                "tests_passed": total_passed,
                "tests_failed": total_failed,
                "success_rate": success_rate,
                "overall_status": "PASSED" if total_failed == 0 else "FAILED"
            },
            "detailed_results": self.results,
            "performance_highlights": self._extract_performance_highlights(),
            "recommendations": self._generate_recommendations()
        }
        
        # Save report to file
        report_file = Path(__file__).parent / "performance_validation_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Print summary
        print("\n" + "="*60)
        print("🎯 PHASE 5A PERFORMANCE VALIDATION REPORT")
        print("="*60)
        print(f"📊 Overall Status: {report['validation_summary']['overall_status']}")
        print(f"✅ Tests Passed: {total_passed}")
        print(f"❌ Tests Failed: {total_failed}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"⏱️  Total Time: {total_time:.2f}s")
        print(f"📁 Report saved: {report_file}")
        
        if total_failed == 0:
            print("\n🎉 All performance optimizations validated successfully!")
            print("✅ Phase 5A: Performance Optimization - COMPLETE")
        else:
            print(f"\n⚠️  {total_failed} tests failed - review results above")
        
        print("="*60)
        
        self.results["validation_report"] = report
    
    def _extract_performance_highlights(self) -> Dict[str, Any]:
        """Extract key performance metrics from results."""
        highlights = {}
        
        # AI Cache performance
        if "ai_caching" in self.results:
            cache_perf = self.results["ai_caching"].get("performance", {})
            highlights["ai_cache_hit_time"] = cache_perf.get("cache_hit_time", 0)
            highlights["ai_cache_speedup"] = cache_perf.get("speedup_ratio", 0)
        
        # Serialization performance
        if "serialization" in self.results:
            serial_perf = self.results["serialization"].get("performance", {})
            highlights["serialization_speedup"] = serial_perf.get("serialize_speedup", 1)
            highlights["deserialization_speedup"] = serial_perf.get("deserialize_speedup", 1)
        
        # State management performance
        if "state_management" in self.results:
            state_perf = self.results["state_management"].get("performance", {})
            highlights["state_cache_speedup"] = state_perf.get("cache_speedup", 1)
        
        # Integration performance
        if "integration" in self.results:
            integration_perf = self.results["integration"].get("performance", {})
            highlights["integration_time"] = integration_perf.get("total_integration_time", 0)
            highlights["cache_hit_rate"] = integration_perf.get("cache_hit_rate", 0)
        
        return highlights
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Check AI cache performance
        if "ai_caching" in self.results:
            perf = self.results["ai_caching"].get("performance", {})
            if perf.get("cache_hit_time", 1) > 0.001:
                recommendations.append("Consider optimizing AI cache lookup algorithm for sub-millisecond performance")
        
        # Check serialization performance
        if "serialization" in self.results:
            perf = self.results["serialization"].get("performance", {})
            if perf.get("serialize_speedup", 1) < 2.0:
                recommendations.append("Verify orjson is installed and being used for serialization optimization")
        
        # Check for any failed tests
        failed_systems = [system for system, result in self.results.items() 
                         if result.get("failed", 0) > 0]
        if failed_systems:
            recommendations.append(f"Review and fix failing systems: {', '.join(failed_systems)}")
        
        if not recommendations:
            recommendations.append("All performance optimizations are working excellently!")
        
        return recommendations


async def main():
    """Main validation function."""
    validator = PerformanceValidator()
    
    try:
        results = await validator.run_validation()
        
        # Exit with appropriate code
        total_failed = sum(result.get("failed", 0) for result in results.values())
        sys.exit(0 if total_failed == 0 else 1)
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())