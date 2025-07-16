"""
Performance Benchmarks Test Suite
Following TDD and AAA (Arrange, Act, Assert) principles

This test suite establishes performance benchmarks for:
- Caching performance improvements
- Task generation performance
- Configuration validation overhead
- AI Coordinator orchestration performance

These benchmarks help ensure that our improvements actually improve performance
and don't introduce regressions.
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any

from ai.ai_coordinator import AICoordinator
from ai.multi_model_ai import MultiModelAIOptimizer, AIModel
from ai.scene_understanding import AdvancedSceneUnderstanding
from utils.config_validator import ConfigValidator


class TestPerformanceBenchmarks:
    """Test suite for performance benchmarks"""

    @pytest.fixture
    def performance_config(self) -> dict:
        """Arrange: Configuration optimized for performance testing"""
        return {
            "ha_url": "http://test.local",
            "ha_token": "test_token",
            "ai_enhancements": {
                "advanced_scene_understanding": True,
                "predictive_analytics": True,
                "model_selection": {
                    "detailed_analysis": "gemini-pro",
                    "complex_reasoning": "claude-sonnet",
                    "simple_analysis": "gemini-flash"
                },
                "caching": {
                    "enabled": True,
                    "intermediate_caching": True,
                    "ttl_seconds": 300,
                    "max_cache_entries": 1000
                },
                "scene_understanding_settings": {
                    "max_objects_detected": 10,
                    "max_generated_tasks": 8,
                    "confidence_threshold": 0.7,
                    "enable_seasonal_adjustments": True,
                    "enable_time_context": True
                },
                "predictive_analytics_settings": {
                    "history_days": 30,
                    "prediction_horizon_hours": 24,
                    "min_data_points": 5,
                    "enable_urgency_scoring": True,
                    "enable_pattern_detection": True
                },
                "multi_model_ai": {
                    "enable_fallback": True,
                    "max_retries": 3,
                    "timeout_seconds": 30,
                    "performance_tracking": True
                }
            },
            "zones": [
                {
                    "name": "Test Zone",
                    "camera_entity": "camera.test",
                    "todo_list_entity": "todo.test",
                    "purpose": "Test purpose"
                }
            ]
        }

    @pytest.fixture
    def sample_analysis_result(self) -> dict:
        """Arrange: Sample analysis result for performance testing"""
        return {
            "new_tasks": [
                {"description": f"Task {i}", "priority": i % 5 + 1}
                for i in range(10)
            ],
            "completed_tasks": [],
            "cleanliness_score": 7,
            "analysis_summary": "Performance test analysis",
            "raw_response": "Performance test response with multiple objects on various surfaces",
            "detected_objects": [f"object_{i}" for i in range(20)],
            "cleanliness_assessment": {
                "observations": [f"observation_{i}" for i in range(5)]
            }
        }

    def test_caching_performance_improvement(self, performance_config, sample_analysis_result):
        """
        Benchmark caching performance improvement
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        mock_config = {
            "gemini_api_key": "test_key",
            "claude_api_key": "test_key"
        }

        ai_config = performance_config["ai_enhancements"]

        with patch('ai.multi_model_ai.GeminiProvider'), \
             patch('ai.multi_model_ai.ClaudeProvider'), \
             patch('ai.multi_model_ai.GPTProvider'):

            multi_model_ai = MultiModelAIOptimizer(
                config=mock_config,
                ai_config=ai_config
            )

            # Mock the _analyze_with_fallback to simulate API call delay
            def slow_analyze(*args, **kwargs):
                time.sleep(0.1)  # Simulate 100ms API call
                return sample_analysis_result, False

            with patch.object(multi_model_ai, '_analyze_with_fallback', side_effect=slow_analyze):
                image_path = "/test/image.jpg"
                zone_name = "test_zone"
                zone_purpose = "test purpose"
                active_tasks = []
                ignore_rules = []

                # Act - First call (no cache)
                start_time = time.time()
                result1, was_cached1 = multi_model_ai.analyze_batch_optimized(
                    image_path, zone_name, zone_purpose, active_tasks, ignore_rules
                )
                first_call_time = time.time() - start_time

                # Act - Second call (should use intermediate cache)
                start_time = time.time()
                result2, was_cached2 = multi_model_ai.analyze_batch_optimized(
                    image_path, zone_name, zone_purpose, active_tasks, ignore_rules
                )
                second_call_time = time.time() - start_time

        # Assert
        assert was_cached1 is False  # First call not cached
        assert was_cached2 is True   # Second call should use cache
        
        # Performance assertion: cached call should be significantly faster
        cache_speedup = first_call_time / second_call_time
        assert cache_speedup > 5, f"Cache speedup {cache_speedup:.2f}x should be > 5x"
        
        # Benchmark logging
        print(f"\nCaching Performance Benchmark:")
        print(f"  First call (no cache): {first_call_time:.3f}s")
        print(f"  Second call (cached):  {second_call_time:.3f}s")
        print(f"  Speedup factor:        {cache_speedup:.2f}x")

    def test_task_generation_performance(self):
        """
        Benchmark task generation performance
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        scene_understanding = AdvancedSceneUnderstanding()
        
        # Large AI response to stress test object extraction
        large_ai_response = """
        The room contains many items scattered around. There are 15 books on the floor,
        3 cups on the coffee table, 5 plates in the sink, 2 towels on the bathroom floor,
        4 shoes by the entrance, 6 papers on the desk, 1 laptop on the bed,
        8 clothes items on the chair, 2 bottles on the counter, and 3 magazines on the shelf.
        The room needs significant cleaning and organization.
        """
        
        # Act - Measure task generation performance
        start_time = time.time()
        
        # Run task generation multiple times to get average
        iterations = 10
        for _ in range(iterations):
            result = scene_understanding.get_detailed_scene_context(
                "test_zone", "test_purpose", large_ai_response,
                max_objects=20, confidence_threshold=0.5
            )
        
        total_time = time.time() - start_time
        avg_time_per_call = total_time / iterations

        # Assert
        assert avg_time_per_call < 0.2, f"Task generation should be < 200ms, got {avg_time_per_call:.3f}s"
        assert result is not None
        assert "objects" in result
        assert "generated_tasks" in result
        
        # Benchmark logging
        print(f"\nTask Generation Performance Benchmark:")
        print(f"  Average time per call: {avg_time_per_call:.3f}s")
        print(f"  Total iterations:      {iterations}")
        print(f"  Objects detected:      {len(result.get('objects', []))}")
        print(f"  Tasks generated:       {len(result.get('generated_tasks', []))}")

    def test_configuration_validation_overhead(self, performance_config):
        """
        Benchmark configuration validation overhead
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        validator = ConfigValidator(performance_config)
        
        # Act - Measure validation performance
        start_time = time.time()
        
        # Run validation multiple times to get average
        iterations = 100
        for _ in range(iterations):
            result = validator.validate_full_config()
        
        total_time = time.time() - start_time
        avg_time_per_validation = total_time / iterations

        # Assert
        assert avg_time_per_validation < 0.005, f"Validation should be < 5ms, got {avg_time_per_validation:.3f}s"
        assert result.is_valid
        
        # Benchmark logging
        print(f"\nConfiguration Validation Performance Benchmark:")
        print(f"  Average time per validation: {avg_time_per_validation:.3f}s")
        print(f"  Total iterations:            {iterations}")
        print(f"  Validation overhead:         {avg_time_per_validation * 1000:.2f}ms")

    @pytest.mark.asyncio
    async def test_ai_coordinator_orchestration_performance(self, performance_config, sample_analysis_result):
        """
        Benchmark AI Coordinator orchestration performance
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        mock_multi_model_ai = Mock()
        mock_multi_model_ai.analyze_batch_optimized = AsyncMock(return_value=(sample_analysis_result, False))

        mock_scene_understanding = Mock()
        mock_scene_understanding.get_detailed_scene_context.return_value = {
            "scene_context": {"room_type": "living_room"},
            "objects": [{"name": "test_object", "location": "table"}],
            "generated_tasks": ["Test task"],
            "contextual_insights": []
        }

        mock_predictive_analytics = Mock()
        mock_predictive_analytics.get_prediction_for_zone.return_value = {
            "next_predicted_cleaning_time": "2024-01-01T12:00:00Z",
            "urgency_score": 5
        }

        ai_coordinator = AICoordinator(
            config=performance_config,
            multi_model_ai=mock_multi_model_ai,
            predictive_analytics=mock_predictive_analytics,
            scene_understanding=mock_scene_understanding
        )

        # Act - Measure orchestration performance
        start_time = time.time()
        
        # Run orchestration multiple times to get average
        iterations = 10
        for _ in range(iterations):
            result = await ai_coordinator.analyze_zone(
                zone_name="test_zone",
                image_path="/test/image.jpg",
                priority="manual",
                zone_purpose="test purpose"
            )
        
        total_time = time.time() - start_time
        avg_time_per_orchestration = total_time / iterations

        # Assert
        assert avg_time_per_orchestration < 0.1, f"Orchestration should be < 100ms, got {avg_time_per_orchestration:.3f}s"
        assert result is not None
        assert not result.get("error", False)
        
        # Benchmark logging
        print(f"\nAI Coordinator Orchestration Performance Benchmark:")
        print(f"  Average time per orchestration: {avg_time_per_orchestration:.3f}s")
        print(f"  Total iterations:               {iterations}")
        print(f"  Components orchestrated:        3 (MultiModelAI, SceneUnderstanding, PredictiveAnalytics)")

    def test_memory_usage_benchmark(self, performance_config):
        """
        Benchmark memory usage of key components
        AAA Pattern: Arrange, Act, Assert
        """
        import psutil
        import os
        
        # Arrange
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Act - Create multiple instances to test memory usage
        validators = []
        scene_understanding_instances = []
        
        for i in range(10):
            validators.append(ConfigValidator(performance_config))
            scene_understanding_instances.append(AdvancedSceneUnderstanding())
        
        # Perform operations
        for validator in validators:
            validator.validate_full_config()
        
        for scene in scene_understanding_instances:
            scene.get_detailed_scene_context(
                "test_zone", "test_purpose", "test response"
            )
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Assert
        assert memory_increase < 50, f"Memory increase should be < 50MB, got {memory_increase:.2f}MB"
        
        # Benchmark logging
        print(f"\nMemory Usage Benchmark:")
        print(f"  Initial memory:  {initial_memory:.2f}MB")
        print(f"  Final memory:    {final_memory:.2f}MB")
        print(f"  Memory increase: {memory_increase:.2f}MB")
        print(f"  Instances created: 10 validators + 10 scene understanding")

    def test_concurrent_performance(self, performance_config, sample_analysis_result):
        """
        Benchmark concurrent operations performance
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        mock_config = {"gemini_api_key": "test_key"}
        ai_config = performance_config["ai_enhancements"]

        with patch('ai.multi_model_ai.GeminiProvider'), \
             patch('ai.multi_model_ai.ClaudeProvider'), \
             patch('ai.multi_model_ai.GPTProvider'):

            multi_model_ai = MultiModelAIOptimizer(config=mock_config, ai_config=ai_config)

            # Mock fast analysis
            with patch.object(multi_model_ai, '_analyze_with_fallback', return_value=(sample_analysis_result, False)):
                
                # Act - Measure concurrent performance
                start_time = time.time()
                
                # Simulate concurrent analysis requests
                concurrent_tasks = []
                for i in range(5):
                    task_result = multi_model_ai.analyze_batch_optimized(
                        f"/test/image_{i}.jpg", f"zone_{i}", "test purpose", [], []
                    )
                    concurrent_tasks.append(task_result)
                
                total_time = time.time() - start_time

        # Assert
        assert total_time < 1.0, f"5 concurrent analyses should complete in < 1s, got {total_time:.3f}s"
        assert len(concurrent_tasks) == 5
        
        # Benchmark logging
        print(f"\nConcurrent Performance Benchmark:")
        print(f"  Total time for 5 analyses: {total_time:.3f}s")
        print(f"  Average time per analysis:  {total_time/5:.3f}s")
        print(f"  Throughput:                 {5/total_time:.2f} analyses/second")
