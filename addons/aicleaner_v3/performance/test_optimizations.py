"""
Performance Optimization Testing Suite
Phase 5A: Performance Optimization

Tests the implemented optimizations to measure performance improvements.
"""

import asyncio
import time
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add addon path to Python path
addon_path = Path(__file__).parent.parent
sys.path.insert(0, str(addon_path))

from performance.simple_profiler import profiler
from performance.api_cache import api_cache, generate_cache_key
from performance.async_optimizer import ai_optimizer, optimize_ai_provider_calls
from performance.memory_optimizer import (
    process_entities_efficiently, 
    aggregate_sensor_data_efficiently,
    get_memory_stats,
    cleanup_memory
)
from performance.config_cache import get_cached_config, get_config_cache_stats

async def test_api_caching_performance():
    """Test API caching performance improvements"""
    print("🧪 Testing API Caching Performance...")
    
    # Simulate API responses
    test_responses = [
        {"data": f"response_{i}", "timestamp": time.time()}
        for i in range(100)
    ]
    
    # Test without caching (baseline)
    with profiler.profile_block("api_without_caching"):
        for i, response in enumerate(test_responses):
            # Simulate API processing time
            await asyncio.sleep(0.001)
            processed = {"id": i, **response}
    
    # Test with caching
    cache_key_base = "test_api_response"
    
    with profiler.profile_block("api_with_caching_first_time"):
        # First time - cache misses
        for i, response in enumerate(test_responses[:10]):
            cache_key = f"{cache_key_base}_{i}"
            
            # Check cache
            cached = await api_cache.get(cache_key)
            if cached is None:
                # Simulate API processing
                await asyncio.sleep(0.001)
                processed = {"id": i, **response}
                # Cache the result
                await api_cache.set(cache_key, processed, ttl=300)
            else:
                processed = cached
    
    with profiler.profile_block("api_with_caching_cache_hits"):
        # Second time - cache hits
        for i in range(10):
            cache_key = f"{cache_key_base}_{i}"
            cached = await api_cache.get(cache_key)
            # Should be instant from cache
    
    # Get cache stats
    cache_stats = api_cache.get_stats()
    print(f"  Cache hit rate: {cache_stats['hit_rate_percent']:.1f}%")
    print(f"  Cache entries: {cache_stats['cache_size']}")
    print("✅ API caching tested")

async def test_async_optimization_performance():
    """Test async concurrent optimization performance"""
    print("🧪 Testing Async Optimization Performance...")
    
    # Mock AI providers
    test_providers = [
        {"name": "openai", "model": "gpt-4"},
        {"name": "gemini", "model": "gemini-pro"},
        {"name": "anthropic", "model": "claude-3"},
        {"name": "local", "model": "llama-2"}
    ]
    
    test_prompt = "Analyze this sensor data and provide recommendations"
    
    # Test sequential calls (baseline)
    with profiler.profile_block("sequential_ai_calls"):
        sequential_results = []
        for provider in test_providers:
            # Simulate AI provider call
            start_time = time.time()
            await asyncio.sleep(0.1)  # Simulate processing time
            result = {
                "provider": provider["name"],
                "response": f"Response from {provider['name']}",
                "response_time": time.time() - start_time
            }
            sequential_results.append(result)
    
    # Test concurrent calls (optimized)
    with profiler.profile_block("concurrent_ai_calls"):
        concurrent_results = await optimize_ai_provider_calls(test_providers, test_prompt)
    
    print(f"  Sequential calls: {len(sequential_results)} providers")
    print(f"  Concurrent calls: {concurrent_results['successful_count']} successful")
    print(f"  Time saved: {profiler.metrics.get('sequential_ai_calls', {}).get('execution_time', 0) - profiler.metrics.get('concurrent_ai_calls', {}).get('execution_time', 0):.3f}s")
    print("✅ Async optimization tested")

async def test_memory_optimization_performance():
    """Test memory-efficient data processing"""
    print("🧪 Testing Memory Optimization Performance...")
    
    # Generate test entity data
    test_entities = []
    for i in range(5000):
        test_entities.append({
            "entity_id": f"sensor.test_{i}",
            "state": str(20 + (i % 40)),
            "last_changed": time.time(),
            "last_updated": time.time(),
            "attributes": {
                "friendly_name": f"Test Sensor {i}",
                "unit_of_measurement": "°C",
                "device_class": "temperature",
                "extra_data": f"extra_{i}" * 10  # Some extra data
            }
        })
    
    # Test traditional processing (baseline)
    initial_memory = get_memory_stats()
    
    with profiler.profile_block("traditional_entity_processing"):
        traditional_results = []
        for entity in test_entities:
            processed = {
                "entity_id": entity["entity_id"],
                "state": entity["state"],
                "last_changed": entity["last_changed"],
                "attributes": {
                    k: v for k, v in entity["attributes"].items()
                    if k in ["friendly_name", "unit_of_measurement", "device_class"]
                }
            }
            traditional_results.append(processed)
    
    mid_memory = get_memory_stats()
    
    # Test memory-efficient processing
    with profiler.profile_block("memory_efficient_processing"):
        efficient_results = process_entities_efficiently(test_entities)
    
    final_memory = get_memory_stats()
    
    # Test aggregation
    sensor_data = [{"value": 20 + (i % 40)} for i in range(1000)]
    
    with profiler.profile_block("sensor_aggregation"):
        aggregation_result = aggregate_sensor_data_efficiently(sensor_data)
    
    print(f"  Processed {len(test_entities)} entities")
    print(f"  Traditional memory usage: {mid_memory['memory_mb'] - initial_memory['memory_mb']:.1f} MB")
    print(f"  Efficient memory usage: {final_memory['memory_mb'] - mid_memory['memory_mb']:.1f} MB")
    print(f"  Aggregation result: avg={aggregation_result['average']:.1f}, count={aggregation_result['count']}")
    
    # Cleanup memory
    cleanup_stats = cleanup_memory()
    print(f"  Cleaned up {cleanup_stats['collected_objects']} objects")
    print("✅ Memory optimization tested")

async def test_config_caching_performance():
    """Test configuration caching performance"""
    print("🧪 Testing Configuration Caching Performance...")
    
    # Create test config file
    test_config_path = "/tmp/test_config.json"
    test_config = {
        "ai_providers": {
            "openai": {"enabled": True, "model": "gpt-4"},
            "gemini": {"enabled": True, "model": "gemini-pro"}
        },
        "settings": {"debug": False, "max_requests": 100},
        "zones": [{"name": f"zone_{i}", "devices": list(range(5))} for i in range(10)]
    }
    
    # Save test config
    with open(test_config_path, 'w') as f:
        json.dump(test_config, f)
    
    # Test file loading (baseline)
    with profiler.profile_block("config_file_loading"):
        for _ in range(20):
            with open(test_config_path, 'r') as f:
                loaded_config = json.load(f)
    
    # Test cached loading
    with profiler.profile_block("config_cached_loading"):
        for _ in range(20):
            cached_config = await get_cached_config(test_config_path)
    
    # Get cache stats
    config_cache_stats = await get_config_cache_stats()
    
    print(f"  Cache hit rate: {config_cache_stats['hit_rate_percent']:.1f}%")
    print(f"  Cached files: {config_cache_stats['cached_files']}")
    print("✅ Configuration caching tested")
    
    # Cleanup
    Path(test_config_path).unlink(missing_ok=True)

async def run_optimization_tests():
    """Run comprehensive optimization testing"""
    print("🚀 Starting AICleaner v3 Optimization Performance Tests")
    print("=" * 60)
    
    start_time = time.time()
    baseline_memory = get_memory_stats()
    
    print(f"📊 Baseline Metrics:")
    print(f"  Memory: {baseline_memory['memory_mb']:.1f} MB")
    print(f"  Objects: {baseline_memory['objects_count']}")
    print()
    
    # Run optimization tests
    await test_api_caching_performance()
    await test_async_optimization_performance()
    await test_memory_optimization_performance()
    await test_config_caching_performance()
    
    # Final metrics
    total_time = time.time() - start_time
    final_memory = get_memory_stats()
    
    print(f"\n⏱️ Total testing time: {total_time:.2f}s")
    print(f"📄 Memory usage: {final_memory['memory_mb']:.1f} MB")
    
    # Save and display metrics
    metrics_file = profiler.save_metrics("optimization_test_metrics.json")
    print(f"📊 Metrics saved to: {metrics_file}")
    
    profiler.print_summary()
    
    # Calculate performance improvements
    print(f"\n🎯 Performance Improvement Analysis:")
    
    # API caching improvement
    no_cache_time = profiler.metrics.get("api_without_caching", {}).get("execution_time", 0)
    cache_miss_time = profiler.metrics.get("api_with_caching_first_time", {}).get("execution_time", 0)
    cache_hit_time = profiler.metrics.get("api_with_caching_cache_hits", {}).get("execution_time", 0)
    
    if no_cache_time > 0 and cache_hit_time > 0:
        api_improvement = ((no_cache_time - cache_hit_time) / no_cache_time) * 100
        print(f"  API Caching: {api_improvement:.1f}% faster on cache hits")
    
    # Async improvement
    sequential_time = profiler.metrics.get("sequential_ai_calls", {}).get("execution_time", 0)
    concurrent_time = profiler.metrics.get("concurrent_ai_calls", {}).get("execution_time", 0)
    
    if sequential_time > 0 and concurrent_time > 0:
        async_improvement = ((sequential_time - concurrent_time) / sequential_time) * 100
        print(f"  Async Optimization: {async_improvement:.1f}% faster with concurrency")
    
    # Memory improvement
    traditional_memory = profiler.metrics.get("traditional_entity_processing", {}).get("memory_peak_bytes", 0)
    efficient_memory = profiler.metrics.get("memory_efficient_processing", {}).get("memory_peak_bytes", 0)
    
    if traditional_memory > 0 and efficient_memory > 0:
        memory_improvement = ((traditional_memory - efficient_memory) / traditional_memory) * 100
        print(f"  Memory Optimization: {memory_improvement:.1f}% less memory usage")
    
    # Config caching improvement
    file_time = profiler.metrics.get("config_file_loading", {}).get("execution_time", 0)
    cached_time = profiler.metrics.get("config_cached_loading", {}).get("execution_time", 0)
    
    if file_time > 0 and cached_time > 0:
        config_improvement = ((file_time - cached_time) / file_time) * 100
        print(f"  Config Caching: {config_improvement:.1f}% faster with caching")
    
    print(f"\n✅ Optimization testing complete!")
    print(f"🎯 Key Achievements:")
    print(f"  - API response caching with TTL")
    print(f"  - Concurrent AI provider calls")
    print(f"  - Memory-efficient data processing")
    print(f"  - Configuration caching layer")
    
    return metrics_file

if __name__ == "__main__":
    try:
        metrics_file = asyncio.run(run_optimization_tests())
        print(f"\n📊 Detailed metrics available in: {metrics_file}")
        
    except KeyboardInterrupt:
        print("\n🛑 Optimization testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Optimization testing failed: {e}")
        import traceback
        traceback.print_exc()