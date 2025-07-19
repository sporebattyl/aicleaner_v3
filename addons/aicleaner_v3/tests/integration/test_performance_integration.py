"""
Integration Tests for Phase 5A Performance Optimizations
Validates all performance systems working together
"""

import asyncio
import json
import logging
import pytest
import time
from typing import Dict, Any, List
from datetime import datetime
import tempfile
import os

# Performance optimization imports
from performance.profiler import get_profiler, get_memory_profiler, profile_async
from performance.metrics import get_tracker
from performance.ai_cache import get_ai_cache, clear_ai_cache
from performance.event_loop_optimizer import get_event_loop_optimizer, start_event_loop_monitoring
from performance.serialization_optimizer import (
    get_serialization_optimizer, fast_json_dumps, fast_json_loads
)
from performance.state_optimizer import (
    get_state_optimizer, read_optimized_state, write_optimized_state
)

# Core systems
from ai.providers.openai_provider import OpenAIProvider
from ai.providers.base_provider import AIProviderConfiguration, AIRequest
from core.aicleaner_core import AICleanerCore
from ha_integration.ha_adapter import HomeAssistantAdapter

logger = logging.getLogger(__name__)


class TestPerformanceIntegration:
    """Integration tests for performance optimization systems."""
    
    @pytest.fixture
    async def setup_performance_systems(self):
        """Setup all performance systems for testing."""
        # Start event loop monitoring
        await start_event_loop_monitoring()
        
        # Clear any existing cache
        clear_ai_cache()
        
        yield
        
        # Cleanup
        from performance.event_loop_optimizer import stop_event_loop_monitoring
        await stop_event_loop_monitoring()
    
    @pytest.fixture
    def mock_ai_provider_config(self):
        """Create mock AI provider configuration."""
        return AIProviderConfiguration(
            name="test_openai",
            enabled=True,
            api_key="test_key",
            model_name="gpt-4o-mini",
            max_retries=1,
            timeout_seconds=30
        )
    
    @pytest.mark.asyncio
    async def test_ai_caching_integration(self, setup_performance_systems, mock_ai_provider_config):
        """Test AI request caching across multiple providers."""
        cache = get_ai_cache()
        
        # Test data
        test_prompt = "Analyze this room for cleaning recommendations"
        test_response = {
            "response_text": "This room appears clean and well-organized.",
            "model_used": "gpt-4o-mini",
            "confidence": 0.9,
            "metadata": {"usage": {"total_tokens": 150}}
        }
        
        # Test cache miss and set
        cached_response = await cache.get("openai", "gpt-4o-mini", test_prompt)
        assert cached_response is None  # Cache miss
        
        await cache.set("openai", "gpt-4o-mini", test_prompt, test_response)
        
        # Test cache hit
        cached_response = await cache.get("openai", "gpt-4o-mini", test_prompt)
        assert cached_response is not None
        assert cached_response["response_text"] == test_response["response_text"]
        assert cached_response["model_used"] == test_response["model_used"]
        
        # Test cache statistics
        stats = cache.get_stats()
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
        assert stats["hit_rate"] > 0
        
        logger.info(f"Cache test completed: {stats}")
    
    @pytest.mark.asyncio
    async def test_serialization_performance(self, setup_performance_systems):
        """Test serialization optimization performance."""
        serializer = get_serialization_optimizer()
        
        # Create test data
        large_data = {
            "zones": [
                {
                    "id": f"zone_{i}",
                    "name": f"Zone {i}",
                    "devices": [f"device_{j}" for j in range(10)],
                    "status": "active",
                    "metadata": {
                        "created": datetime.now().isoformat(),
                        "metrics": [random_value for random_value in range(100)]
                    }
                }
                for i in range(50)
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        # Test serialization performance
        start_time = time.perf_counter()
        serialized = serializer.serialize(large_data)
        serialize_time = time.perf_counter() - start_time
        
        # Test deserialization performance
        start_time = time.perf_counter()
        deserialized = serializer.deserialize(serialized)
        deserialize_time = time.perf_counter() - start_time
        
        # Verify data integrity
        assert deserialized["zones"][0]["name"] == "Zone 0"
        assert len(deserialized["zones"]) == 50
        
        # Check performance metrics
        metrics = serializer.get_metrics()
        assert metrics.total_serializations >= 1
        assert metrics.total_deserializations >= 1
        assert metrics.average_serialize_time > 0
        assert metrics.average_deserialize_time > 0
        
        # Test fast functions
        fast_serialized = fast_json_dumps(large_data)
        fast_deserialized = fast_json_loads(fast_serialized)
        assert fast_deserialized["zones"][0]["name"] == "Zone 0"
        
        logger.info(
            f"Serialization performance - Serialize: {serialize_time:.4f}s, "
            f"Deserialize: {deserialize_time:.4f}s"
        )
    
    @pytest.mark.asyncio
    async def test_state_optimization_integration(self, setup_performance_systems):
        """Test state management optimization."""
        state_optimizer = get_state_optimizer()
        await state_optimizer.start()
        
        try:
            # Test state read/write operations
            test_key = "test_zone_config"
            test_data = {
                "zones": ["living_room", "kitchen", "bedroom"],
                "config": {"auto_clean": True, "schedule": "daily"},
                "last_updated": datetime.now().isoformat()
            }
            
            with tempfile.TemporaryDirectory() as temp_dir:
                test_file = os.path.join(temp_dir, "test_state.json")
                
                # Test write operation
                success = await write_optimized_state(test_key, test_data, test_file)
                assert success
                assert os.path.exists(test_file)
                
                # Test read operation
                read_data = await read_optimized_state(test_key, test_file)
                assert read_data is not None
                assert read_data["zones"] == test_data["zones"]
                assert read_data["config"] == test_data["config"]
                
                # Test cache functionality
                cached_data = await read_optimized_state(test_key)  # No file path = cache only
                assert cached_data is not None
                assert cached_data["zones"] == test_data["zones"]
                
                # Test cache statistics
                cache_stats = state_optimizer.get_cache_stats()
                assert cache_stats["cache_size"] >= 1
                
                logger.info(f"State optimization test completed: {cache_stats}")
        
        finally:
            await state_optimizer.stop()
    
    @pytest.mark.asyncio
    async def test_event_loop_optimization(self, setup_performance_systems):
        """Test event loop optimization features."""
        optimizer = get_event_loop_optimizer()
        
        # Test optimized task creation
        @profile_async("test_task")
        async def test_async_task(duration: float = 0.1):
            await asyncio.sleep(duration)
            return f"Task completed in {duration}s"
        
        # Create multiple optimized tasks
        tasks = []
        for i in range(5):
            task = optimizer.create_optimized_task(
                test_async_task(0.1), 
                name=f"test_task_{i}"
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        assert len(results) == 5
        assert all("Task completed" in result for result in results)
        
        # Test thread pool functionality
        def blocking_operation(value: int) -> int:
            time.sleep(0.1)  # Simulate blocking I/O
            return value * 2
        
        # Run blocking operation in thread pool
        result = await optimizer.run_in_thread(blocking_operation, 42)
        assert result == 84
        
        # Get diagnostics
        diagnostics = optimizer.get_diagnostics()
        assert "uptime" in diagnostics
        assert "monitoring_enabled" in diagnostics
        assert diagnostics["monitoring_enabled"] is True
        
        logger.info(f"Event loop optimization test completed: {diagnostics}")
    
    @pytest.mark.asyncio
    async def test_profiling_integration(self, setup_performance_systems):
        """Test profiling system integration."""
        profiler = get_profiler()
        memory_profiler = get_memory_profiler()
        tracker = get_tracker()
        
        # Test async profiling
        @profile_async("test_operation")
        async def profiled_operation():
            await asyncio.sleep(0.1)
            return {"status": "success", "data": list(range(1000))}
        
        # Execute profiled operation
        result = await profiled_operation()
        assert result["status"] == "success"
        assert len(result["data"]) == 1000
        
        # Test performance tracking
        async with tracker.track_zone_operation("test_zone", "test_operation"):
            await asyncio.sleep(0.05)
        
        # Get profiling results
        profiler_results = profiler.get_results()
        assert "test_operation" in profiler_results
        assert profiler_results["test_operation"]["call_count"] >= 1
        
        # Get memory profile
        memory_stats = memory_profiler.get_current_memory_usage()
        assert "rss" in memory_stats
        assert "vms" in memory_stats
        assert memory_stats["rss"] > 0
        
        logger.info(f"Profiling test completed: {len(profiler_results)} operations profiled")
    
    @pytest.mark.asyncio
    async def test_full_system_integration(self, setup_performance_systems):
        """Test all performance systems working together in a realistic scenario."""
        # Simulate a complete AICleaner operation cycle
        
        # 1. State management - Load configuration
        config_key = "system_config"
        config_data = {
            "zones": [
                {"id": "living_room", "enabled": True},
                {"id": "kitchen", "enabled": True}
            ],
            "ai_providers": ["openai", "google"],
            "performance": {
                "caching_enabled": True,
                "profiling_enabled": True
            }
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "system_config.json")
            
            # Write configuration with state optimization
            await write_optimized_state(config_key, config_data, config_file, immediate=True)
            
            # 2. AI caching - Simulate AI requests
            cache = get_ai_cache()
            test_prompts = [
                "Analyze living room for cleaning",
                "Check kitchen cleanliness status",
                "Generate cleaning schedule"
            ]
            
            # First pass - cache misses
            for i, prompt in enumerate(test_prompts):
                response_data = {
                    "response_text": f"Analysis complete for request {i}",
                    "model_used": "gpt-4o-mini",
                    "confidence": 0.85 + (i * 0.05)
                }
                await cache.set("openai", "gpt-4o-mini", prompt, response_data)
            
            # Second pass - cache hits
            hit_times = []
            for prompt in test_prompts:
                start_time = time.perf_counter()
                cached_response = await cache.get("openai", "gpt-4o-mini", prompt)
                hit_time = time.perf_counter() - start_time
                hit_times.append(hit_time)
                
                assert cached_response is not None
                assert "Analysis complete" in cached_response["response_text"]
            
            # 3. Serialization - Process large data structures
            large_state = {
                "devices": [{"id": f"device_{i}", "status": "active"} for i in range(100)],
                "metrics": [{"timestamp": time.time(), "value": i} for i in range(500)],
                "config": config_data
            }
            
            serialized = fast_json_dumps(large_state)
            deserialized = fast_json_loads(serialized)
            assert len(deserialized["devices"]) == 100
            assert len(deserialized["metrics"]) == 500
            
            # 4. Performance validation
            cache_stats = cache.get_stats()
            assert cache_stats["hit_rate"] > 0.5  # At least 50% cache hit rate
            
            serializer_metrics = get_serialization_optimizer().get_metrics()
            assert serializer_metrics.total_serializations >= 1
            
            state_cache_stats = get_state_optimizer().get_cache_stats()
            assert state_cache_stats["cache_size"] >= 1
            
            # 5. Performance benchmarks
            avg_cache_hit_time = sum(hit_times) / len(hit_times)
            assert avg_cache_hit_time < 0.001  # Cache hits should be sub-millisecond
            
            logger.info(
                f"Full system integration test completed:\n"
                f"  Cache hit rate: {cache_stats['hit_rate']:.2%}\n"
                f"  Average cache hit time: {avg_cache_hit_time:.6f}s\n"
                f"  Serializations: {serializer_metrics.total_serializations}\n"
                f"  State cache size: {state_cache_stats['cache_size']}"
            )
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, setup_performance_systems):
        """Test performance systems under concurrent load."""
        # Test concurrent operations
        async def concurrent_operation(operation_id: int):
            """Simulate a typical AICleaner operation."""
            
            # AI caching operation
            cache = get_ai_cache()
            prompt = f"Process operation {operation_id}"
            
            # Check cache first
            cached = await cache.get("test_provider", "test_model", prompt)
            if not cached:
                # Simulate cache miss
                response_data = {
                    "response_text": f"Response for operation {operation_id}",
                    "model_used": "test_model"
                }
                await cache.set("test_provider", "test_model", prompt, response_data)
                result = response_data
            else:
                result = cached
            
            # Serialization operation
            data = {"operation_id": operation_id, "result": result, "timestamp": time.time()}
            serialized = fast_json_dumps(data)
            deserialized = fast_json_loads(serialized)
            
            # State operation
            state_key = f"operation_{operation_id}"
            await write_optimized_state(state_key, deserialized)
            
            return deserialized
        
        # Run 20 concurrent operations
        start_time = time.perf_counter()
        tasks = [concurrent_operation(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time
        
        # Validate results
        assert len(results) == 20
        assert all(result["operation_id"] == i for i, result in enumerate(results))
        
        # Performance validation
        avg_operation_time = total_time / 20
        assert avg_operation_time < 0.1  # Each operation should be fast
        
        # Check system health
        cache_stats = get_ai_cache().get_stats()
        event_loop_diagnostics = get_event_loop_optimizer().get_diagnostics()
        
        logger.info(
            f"Load test completed: 20 operations in {total_time:.3f}s\n"
            f"  Average operation time: {avg_operation_time:.4f}s\n"
            f"  Cache hit rate: {cache_stats['hit_rate']:.2%}\n"
            f"  Event loop health: {event_loop_diagnostics['monitoring_enabled']}"
        )
    
    @pytest.mark.asyncio
    async def test_error_handling_and_resilience(self, setup_performance_systems):
        """Test error handling and system resilience."""
        
        # Test cache resilience with invalid data
        cache = get_ai_cache()
        
        try:
            # This should not crash the system
            await cache.set("test", "test", "test", None)
            result = await cache.get("test", "test", "test")
            # System should handle this gracefully
        except Exception as e:
            logger.warning(f"Cache error handled: {e}")
        
        # Test serialization resilience
        serializer = get_serialization_optimizer()
        
        try:
            # Test with non-serializable object
            class NonSerializable:
                def __init__(self):
                    self.file_handle = open(__file__)
            
            non_serializable = NonSerializable()
            serialized = serializer.serialize({"data": non_serializable})
            # Should handle this gracefully or raise appropriate error
        except Exception as e:
            logger.warning(f"Serialization error handled: {e}")
        finally:
            try:
                non_serializable.file_handle.close()
            except:
                pass
        
        # Test state optimizer resilience
        state_optimizer = get_state_optimizer()
        
        # Test with invalid file path
        invalid_result = await read_optimized_state("invalid_key", "/invalid/path/file.json")
        assert invalid_result is None  # Should return None, not crash
        
        logger.info("Error handling and resilience tests completed")


class TestPerformanceBenchmarks:
    """Performance benchmark tests to establish baselines."""
    
    @pytest.mark.asyncio
    async def test_cache_performance_benchmark(self):
        """Benchmark AI cache performance."""
        cache = get_ai_cache()
        clear_ai_cache()
        
        # Benchmark cache miss
        start_time = time.perf_counter()
        result = await cache.get("benchmark", "model", "test_prompt")
        cache_miss_time = time.perf_counter() - start_time
        assert result is None
        
        # Set cache entry
        test_data = {"response": "test response", "metadata": {"tokens": 100}}
        await cache.set("benchmark", "model", "test_prompt", test_data)
        
        # Benchmark cache hit
        start_time = time.perf_counter()
        result = await cache.get("benchmark", "model", "test_prompt")
        cache_hit_time = time.perf_counter() - start_time
        assert result is not None
        
        # Cache hit should be significantly faster than miss
        assert cache_hit_time < cache_miss_time
        assert cache_hit_time < 0.001  # Sub-millisecond
        
        logger.info(
            f"Cache benchmark - Miss: {cache_miss_time:.6f}s, Hit: {cache_hit_time:.6f}s, "
            f"Speedup: {cache_miss_time/cache_hit_time:.1f}x"
        )
    
    @pytest.mark.asyncio
    async def test_serialization_performance_benchmark(self):
        """Benchmark serialization performance."""
        
        # Create test data of varying sizes
        test_sizes = [1, 10, 100, 1000]  # Number of items
        
        for size in test_sizes:
            test_data = {
                "items": [{"id": i, "data": f"item_{i}"} for i in range(size)],
                "metadata": {"size": size, "timestamp": time.time()}
            }
            
            # Benchmark fast serialization
            start_time = time.perf_counter()
            fast_serialized = fast_json_dumps(test_data)
            fast_serialize_time = time.perf_counter() - start_time
            
            start_time = time.perf_counter()
            fast_deserialized = fast_json_loads(fast_serialized)
            fast_deserialize_time = time.perf_counter() - start_time
            
            # Benchmark standard serialization
            start_time = time.perf_counter()
            std_serialized = json.dumps(test_data)
            std_serialize_time = time.perf_counter() - start_time
            
            start_time = time.perf_counter()
            std_deserialized = json.loads(std_serialized)
            std_deserialize_time = time.perf_counter() - start_time
            
            # Verify data integrity
            assert fast_deserialized == std_deserialized
            
            # Calculate speedup
            serialize_speedup = std_serialize_time / fast_serialize_time if fast_serialize_time > 0 else 1
            deserialize_speedup = std_deserialize_time / fast_deserialize_time if fast_deserialize_time > 0 else 1
            
            logger.info(
                f"Serialization benchmark (size {size}):\n"
                f"  Serialize speedup: {serialize_speedup:.2f}x\n"
                f"  Deserialize speedup: {deserialize_speedup:.2f}x"
            )