"""
Core Component Performance Testing
Phase 5A: Performance Optimization

Tests performance of core Python components without external dependencies.
"""

import asyncio
import sys
import time
import json
from pathlib import Path

# Add addon path to Python path
addon_path = Path(__file__).parent.parent
sys.path.insert(0, str(addon_path))

from performance.simple_profiler import profiler

async def test_file_operations():
    """Test file I/O performance"""
    print("🔍 Testing file operations performance...")
    
    test_data = {
        "config": {
            "ai_providers": ["openai", "gemini", "anthropic"],
            "settings": {"debug": True, "max_requests": 100},
            "zones": [{"name": f"zone_{i}", "devices": list(range(10))} for i in range(20)]
        }
    }
    
    with profiler.profile_block("json_serialization"):
        # Test JSON serialization performance
        for i in range(100):
            json_str = json.dumps(test_data)
    
    with profiler.profile_block("json_deserialization"):
        # Test JSON deserialization performance
        for i in range(100):
            data = json.loads(json_str)
    
    test_file = Path("/tmp/test_config.json")
    
    with profiler.profile_block("file_write_operations"):
        # Test file writing
        for i in range(10):
            with open(test_file, 'w') as f:
                json.dump(test_data, f)
    
    with profiler.profile_block("file_read_operations"):
        # Test file reading
        for i in range(10):
            with open(test_file, 'r') as f:
                data = json.load(f)
    
    # Cleanup
    test_file.unlink(missing_ok=True)
    print("✅ File operations tested")

async def test_data_processing():
    """Test data processing performance"""
    print("🔍 Testing data processing performance...")
    
    # Generate test data
    large_dataset = []
    with profiler.profile_block("data_generation"):
        for i in range(1000):
            large_dataset.append({
                "id": i,
                "timestamp": time.time(),
                "values": [j * 0.1 for j in range(50)],
                "metadata": {"type": "sensor", "location": f"room_{i % 10}"}
            })
    
    with profiler.profile_block("data_filtering"):
        # Test filtering operations
        filtered_data = [item for item in large_dataset if item["id"] % 2 == 0]
    
    with profiler.profile_block("data_aggregation"):
        # Test aggregation operations
        total_values = 0
        for item in large_dataset:
            total_values += sum(item["values"])
        average = total_values / len(large_dataset)
    
    with profiler.profile_block("data_sorting"):
        # Test sorting operations
        sorted_data = sorted(large_dataset, key=lambda x: x["timestamp"])
    
    with profiler.profile_block("dict_comprehension"):
        # Test dictionary comprehension
        id_mapping = {item["id"]: item["timestamp"] for item in large_dataset}
    
    print(f"  Processed {len(large_dataset)} items")
    print(f"  Filtered to {len(filtered_data)} items")
    print(f"  Average value: {average:.2f}")
    print("✅ Data processing tested")

async def test_async_operations():
    """Test async operation performance"""
    print("🔍 Testing async operations performance...")
    
    async def mock_async_task(task_id: int, delay: float = 0.001):
        """Mock async task with small delay"""
        await asyncio.sleep(delay)
        return {"task_id": task_id, "result": task_id * 2, "timestamp": time.time()}
    
    with profiler.profile_block("async_sequential_execution"):
        # Test sequential async execution
        results = []
        for i in range(50):
            result = await mock_async_task(i)
            results.append(result)
    
    with profiler.profile_block("async_concurrent_execution"):
        # Test concurrent async execution
        tasks = [mock_async_task(i) for i in range(50)]
        concurrent_results = await asyncio.gather(*tasks)
    
    with profiler.profile_block("async_task_creation_overhead"):
        # Test task creation overhead
        tasks = []
        for i in range(100):
            task = asyncio.create_task(mock_async_task(i, 0))
            tasks.append(task)
        await asyncio.gather(*tasks)
    
    print(f"  Sequential results: {len(results)}")
    print(f"  Concurrent results: {len(concurrent_results)}")
    print("✅ Async operations tested")

async def test_string_operations():
    """Test string processing performance"""
    print("🔍 Testing string operations performance...")
    
    test_strings = [f"sensor_data_{i}_temperature_reading_value" for i in range(1000)]
    
    with profiler.profile_block("string_concatenation"):
        # Test string concatenation
        result = ""
        for s in test_strings[:100]:
            result += s + "_"
    
    with profiler.profile_block("string_join"):
        # Test string join (more efficient)
        result = "_".join(test_strings[:100])
    
    with profiler.profile_block("string_formatting"):
        # Test string formatting
        formatted = []
        for i, s in enumerate(test_strings[:100]):
            formatted.append(f"id_{i}_{s}_processed")
    
    with profiler.profile_block("string_regex_operations"):
        # Test regex-like operations using string methods
        import re
        pattern = re.compile(r"sensor_data_(\d+)_(.+)")
        matches = []
        for s in test_strings[:100]:
            match = pattern.match(s)
            if match:
                matches.append(match.groups())
    
    print(f"  Processed {len(test_strings)} strings")
    print(f"  Found {len(matches)} pattern matches")
    print("✅ String operations tested")

async def test_memory_patterns():
    """Test memory allocation patterns"""
    print("🔍 Testing memory allocation patterns...")
    
    with profiler.profile_block("list_creation_append"):
        # Test list creation with append
        large_list = []
        for i in range(10000):
            large_list.append({"id": i, "data": f"item_{i}"})
    
    with profiler.profile_block("list_creation_comprehension"):
        # Test list comprehension (more efficient)
        comp_list = [{"id": i, "data": f"item_{i}"} for i in range(10000)]
    
    with profiler.profile_block("dict_creation_update"):
        # Test dictionary creation with update
        large_dict = {}
        for i in range(5000):
            large_dict.update({f"key_{i}": {"value": i, "squared": i**2}})
    
    with profiler.profile_block("dict_creation_comprehension"):
        # Test dictionary comprehension
        comp_dict = {f"key_{i}": {"value": i, "squared": i**2} for i in range(5000)}
    
    # Cleanup
    with profiler.profile_block("memory_cleanup"):
        del large_list, comp_list, large_dict, comp_dict
    
    print("✅ Memory patterns tested")

async def run_core_performance_tests():
    """Run core performance tests"""
    print("🚀 Starting AICleaner v3 Core Performance Analysis")
    print("=" * 60)
    
    start_time = time.time()
    
    # System baseline
    baseline_metrics = profiler.get_system_metrics()
    print(f"📊 Baseline System Metrics:")
    print(f"  Process Memory: {baseline_metrics.get('process_memory_mb', 'N/A'):.1f} MB")
    print(f"  Disk Usage: {baseline_metrics.get('disk_percent', 'N/A'):.1f}%")
    print(f"  Python: {baseline_metrics.get('python_version', 'N/A')}")
    print(f"  Platform: {baseline_metrics.get('platform', 'N/A')}")
    print()
    
    # Run core tests
    await test_file_operations()
    await test_data_processing()
    await test_async_operations()
    await test_string_operations()
    await test_memory_patterns()
    
    # Generate report
    total_time = time.time() - start_time
    print(f"\n⏱️ Total testing time: {total_time:.2f}s")
    
    # Save metrics and generate report
    metrics_file = profiler.save_metrics("core_performance_metrics.json")
    print(f"📄 Metrics saved to: {metrics_file}")
    
    # Print summary
    profiler.print_summary()
    
    return metrics_file

if __name__ == "__main__":
    # Run core performance tests
    try:
        metrics_file = asyncio.run(run_core_performance_tests())
        print(f"\n✅ Core performance analysis complete!")
        print(f"📊 Results saved to: {metrics_file}")
        
        print("\n📋 Key Findings:")
        print("  1. Identify which operations are slowest")
        print("  2. Compare different implementation approaches")
        print("  3. Understand memory usage patterns")
        print("  4. Guide optimization priorities")
        
        print("\n🎯 Next Steps:")
        print("  1. Apply findings to actual AICleaner components")
        print("  2. Implement caching for expensive operations")
        print("  3. Optimize data structures and algorithms")
        print("  4. Add performance monitoring to production code")
        
    except KeyboardInterrupt:
        print("\n🛑 Performance testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Performance testing failed: {e}")
        import traceback
        traceback.print_exc()