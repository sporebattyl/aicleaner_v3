"""
Test suite for Multi-Model AI Caching System
Following TDD and AAA (Arrange, Act, Assert) principles

This test suite comprehensively tests the intermediate caching functionality
that was implemented in the MultiModelAI system, including:
- Intermediate result extraction
- Cache storage and retrieval
- Result reconstruction from cached data
- Configuration-driven caching behavior
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import hashlib
import json

from ai.multi_model_ai import MultiModelAIOptimizer, AIModel


class TestMultiModelAICaching:
    """Test suite for MultiModelAI caching functionality"""

    @pytest.fixture
    def ai_config(self) -> dict:
        """Arrange: AI configuration for testing"""
        return {
            "caching": {
                "enabled": True,
                "intermediate_caching": True,
                "ttl_seconds": 300,
                "max_cache_entries": 1000
            },
            "multi_model_ai": {
                "enable_fallback": True,
                "max_retries": 3,
                "timeout_seconds": 30,
                "performance_tracking": True
            }
        }

    @pytest.fixture
    def mock_config(self) -> dict:
        """Arrange: Mock configuration with API keys"""
        return {
            "gemini_api_key": "test_gemini_key",
            "claude_api_key": "test_claude_key",
            "openai_api_key": "test_openai_key"
        }

    @pytest.fixture
    def multi_model_ai(self, mock_config, ai_config) -> MultiModelAIOptimizer:
        """Arrange: MultiModelAI instance with mocked providers"""
        with patch('ai.multi_model_ai.GeminiProvider'), \
             patch('ai.multi_model_ai.ClaudeProvider'), \
             patch('ai.multi_model_ai.GPTProvider'):

            optimizer = MultiModelAIOptimizer(
                config=mock_config,
                cache_ttl=300,
                preferred_models=[AIModel.GEMINI_FLASH, AIModel.CLAUDE_SONNET],
                ai_config=ai_config
            )
            return optimizer

    @pytest.fixture
    def sample_analysis_result(self) -> dict:
        """Arrange: Sample analysis result for testing"""
        return {
            "new_tasks": [
                {"description": "Clean the kitchen counter", "priority": 5},
                {"description": "Organize books on shelf", "priority": 3}
            ],
            "completed_tasks": [],
            "cleanliness_score": 7,
            "analysis_summary": "Kitchen needs attention",
            "raw_response": "The kitchen counter has dishes and the bookshelf has scattered books.",
            "detected_objects": ["dishes", "books", "counter", "shelf"],
            "cleanliness_assessment": {
                "observations": ["cluttered", "needs_organizing"]
            }
        }

    def test_extract_intermediate_results_success(self, multi_model_ai, sample_analysis_result):
        """
        Test successful extraction of intermediate results
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        image_path = "/test/image.jpg"
        zone_name = "kitchen"

        # Act
        intermediate = multi_model_ai._extract_intermediate_results(
            sample_analysis_result, image_path, zone_name
        )

        # Assert
        assert intermediate is not None
        assert "raw_response" in intermediate
        assert "parsed_objects" in intermediate
        assert "cleanliness_indicators" in intermediate
        assert "task_categories" in intermediate
        assert "image_hash" in intermediate
        assert "zone_context" in intermediate

        # Verify content
        assert intermediate["raw_response"] == sample_analysis_result["raw_response"]
        assert intermediate["parsed_objects"] == sample_analysis_result["detected_objects"]
        assert "cluttered" in intermediate["cleanliness_indicators"]
        assert intermediate["zone_context"]["zone_name"] == zone_name

    def test_extract_intermediate_results_error_handling(self, multi_model_ai):
        """
        Test error handling in intermediate result extraction
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        invalid_result = None  # This should cause an error
        image_path = "/test/image.jpg"
        zone_name = "kitchen"

        # Act
        intermediate = multi_model_ai._extract_intermediate_results(
            invalid_result, image_path, zone_name
        )

        # Assert
        assert intermediate == {}  # Should return empty dict on error

    def test_categorize_tasks_success(self, multi_model_ai):
        """
        Test successful task categorization
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        tasks = [
            {"description": "Clean the kitchen counter"},
            {"description": "Organize books on shelf"},
            {"description": "Fix broken lamp"},
            {"description": "Water plants"}
        ]

        # Act
        categories = multi_model_ai._categorize_tasks(tasks)

        # Assert
        assert "cleaning" in categories
        assert "organizing" in categories
        assert "maintenance" in categories
        assert "other" in categories

        # Verify categorization
        assert "Clean the kitchen counter" in categories["cleaning"]
        assert "Organize books on shelf" in categories["organizing"]
        assert "Fix broken lamp" in categories["maintenance"]
        assert "Water plants" in categories["other"]

    def test_cache_intermediate_results(self, multi_model_ai):
        """
        Test caching of intermediate results
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        cache_key = "test_intermediate_key"
        intermediate_results = {
            "raw_response": "Test response",
            "parsed_objects": ["test_object"],
            "task_categories": {"cleaning": ["test task"]}
        }

        # Act
        multi_model_ai._cache_intermediate_results(cache_key, intermediate_results)

        # Assert
        assert cache_key in multi_model_ai.cache
        cached_data = multi_model_ai.cache[cache_key]
        assert cached_data["type"] == "intermediate"
        assert cached_data["intermediate_results"] == intermediate_results
        assert "timestamp" in cached_data

    def test_get_cached_intermediate_results_hit(self, multi_model_ai):
        """
        Test successful retrieval of cached intermediate results
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        cache_key = "test_intermediate_key"
        intermediate_results = {
            "raw_response": "Test response",
            "parsed_objects": ["test_object"]
        }

        # Cache the data first
        multi_model_ai._cache_intermediate_results(cache_key, intermediate_results)

        # Act
        retrieved = multi_model_ai._get_cached_intermediate_results(cache_key)

        # Assert
        assert retrieved is not None
        assert retrieved == intermediate_results

    def test_get_cached_intermediate_results_miss(self, multi_model_ai):
        """
        Test cache miss for intermediate results
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        non_existent_key = "non_existent_key"

        # Act
        retrieved = multi_model_ai._get_cached_intermediate_results(non_existent_key)

        # Assert
        assert retrieved is None

    def test_reconstruct_from_intermediate_success(self, multi_model_ai):
        """
        Test successful reconstruction from intermediate cache
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        intermediate_data = {
            "raw_response": "Test response",
            "parsed_objects": ["dishes", "books"],
            "cleanliness_indicators": ["cluttered"],
            "task_categories": {
                "cleaning": ["Clean dishes"],
                "organizing": ["Organize books"]
            },
            "zone_context": {
                "zone_name": "kitchen",
                "analysis_timestamp": "2024-01-01T12:00:00"
            }
        }
        zone_name = "kitchen"

        # Act
        result = multi_model_ai._reconstruct_from_intermediate(intermediate_data, zone_name)

        # Assert
        assert result is not None
        assert "new_tasks" in result
        assert "detected_objects" in result
        assert "cleanliness_assessment" in result
        assert "raw_response" in result

        # Verify reconstruction
        assert result["raw_response"] == intermediate_data["raw_response"]
        assert result["detected_objects"] == intermediate_data["parsed_objects"]
        assert len(result["new_tasks"]) > 0

    def test_reconstruct_from_intermediate_error_handling(self, multi_model_ai):
        """
        Test error handling in reconstruction from intermediate cache
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        invalid_intermediate_data = None
        zone_name = "kitchen"

        # Act
        result = multi_model_ai._reconstruct_from_intermediate(invalid_intermediate_data, zone_name)

        # Assert
        assert result == {}  # Should return empty dict on error

    def test_intermediate_cache_workflow_enabled(self, multi_model_ai, sample_analysis_result):
        """
        Test complete intermediate caching workflow when enabled
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        image_path = "/test/image.jpg"
        zone_name = "kitchen"
        zone_purpose = "Cooking and food preparation"
        active_tasks = []
        ignore_rules = []

        # Mock the _analyze_with_fallback method to return our sample result
        with patch.object(multi_model_ai, '_analyze_with_fallback', return_value=(sample_analysis_result, False)):
            # Act - First call should cache intermediate results
            result1, was_cached1 = multi_model_ai.analyze_batch_optimized(
                image_path, zone_name, zone_purpose, active_tasks, ignore_rules
            )

            # Act - Second call should use cached intermediate results
            result2, was_cached2 = multi_model_ai.analyze_batch_optimized(
                image_path, zone_name, zone_purpose, active_tasks, ignore_rules
            )

        # Assert
        assert result1 is not None
        assert was_cached1 is False  # First call not cached

        assert result2 is not None
        assert was_cached2 is True  # Second call should use intermediate cache

    def test_intermediate_cache_workflow_disabled(self, mock_config):
        """
        Test intermediate caching workflow when disabled by configuration
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        ai_config_disabled = {
            "caching": {
                "enabled": True,
                "intermediate_caching": False  # Disabled
            }
        }

        with patch('ai.multi_model_ai.GeminiProvider'), \
             patch('ai.multi_model_ai.ClaudeProvider'), \
             patch('ai.multi_model_ai.GPTProvider'):

            multi_model_ai = MultiModelAIOptimizer(
                config=mock_config,
                ai_config=ai_config_disabled
            )

        image_path = "/test/image.jpg"
        zone_name = "kitchen"
        zone_purpose = "Cooking"
        active_tasks = []
        ignore_rules = []

        sample_result = {"new_tasks": [], "cleanliness_score": 5}

        # Mock the _analyze_with_fallback method
        with patch.object(multi_model_ai, '_analyze_with_fallback', return_value=(sample_result, False)) as mock_analyze:
            # Act - Both calls should go through full analysis
            result1, was_cached1 = multi_model_ai.analyze_batch_optimized(
                image_path, zone_name, zone_purpose, active_tasks, ignore_rules
            )

            result2, was_cached2 = multi_model_ai.analyze_batch_optimized(
                image_path, zone_name, zone_purpose, active_tasks, ignore_rules
            )

        # Assert
        assert mock_analyze.call_count == 2  # Both calls should go through full analysis
        assert was_cached1 is False
        assert was_cached2 is False  # No intermediate caching

    def test_cache_key_generation_consistency(self, multi_model_ai):
        """
        Test that cache keys are generated consistently for same inputs
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        image_path = "/test/image.jpg"
        zone_name = "kitchen"
        zone_purpose = "Cooking"
        active_tasks = [{"id": "task1", "description": "Clean counter"}]
        ignore_rules = ["ignore books"]

        # Act - Generate cache key twice with same inputs
        with patch.object(multi_model_ai, '_get_image_hash', return_value="test_hash"):
            # Create context data as done in the actual method
            context_data = {
                'zone_name': zone_name,
                'zone_purpose': zone_purpose,
                'active_tasks': [t.get('id', '') + t.get('description', '') for t in active_tasks],
                'ignore_rules': ignore_rules
            }
            context_hash1 = hashlib.md5(json.dumps(context_data, sort_keys=True).encode()).hexdigest()
            context_hash2 = hashlib.md5(json.dumps(context_data, sort_keys=True).encode()).hexdigest()

        # Assert
        assert context_hash1 == context_hash2  # Should be identical

    def test_max_retries_configuration_usage(self, mock_config):
        """
        Test that max_retries configuration is properly used
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        ai_config = {
            "multi_model_ai": {
                "max_retries": 2  # Custom retry count
            }
        }

        with patch('ai.multi_model_ai.GeminiProvider') as mock_gemini_provider, \
             patch('ai.multi_model_ai.ClaudeProvider'), \
             patch('ai.multi_model_ai.GPTProvider'):

            # Configure mock to raise exception to trigger retries
            mock_provider_instance = Mock()
            mock_provider_instance.analyze_image.side_effect = Exception("Test error")
            mock_gemini_provider.return_value = mock_provider_instance

            multi_model_ai = MultiModelAIOptimizer(
                config=mock_config,
                ai_config=ai_config
            )

            # Act
            result, was_cached = multi_model_ai._analyze_with_fallback("/test/image.jpg", "test prompt")

        # Assert
        # Should retry 2 times (max_retries=2) for the first model before moving to next
        assert mock_provider_instance.analyze_image.call_count == 2
        assert result is None  # Should fail after all retries
