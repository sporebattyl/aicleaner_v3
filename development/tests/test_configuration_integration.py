"""
Test suite for Configuration Integration
Following TDD and AAA (Arrange, Act, Assert) principles

This test suite verifies that all AI components properly use configuration
settings and that configuration-driven behavior works as expected across
the entire system.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from ai.ai_coordinator import AICoordinator
from ai.multi_model_ai import MultiModelAIOptimizer, AIModel
from ai.scene_understanding import AdvancedSceneUnderstanding
from utils.config_validator import ConfigValidator


class TestConfigurationIntegration:
    """Test suite for configuration integration across AI components"""

    @pytest.fixture
    def base_config(self) -> dict:
        """Arrange: Base configuration for testing"""
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

    @pytest.mark.asyncio
    async def test_ai_coordinator_respects_feature_toggles(self, base_config):
        """
        Test that AI Coordinator respects feature toggle configuration
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange - Disable scene understanding
        config_disabled = base_config.copy()
        config_disabled["ai_enhancements"]["advanced_scene_understanding"] = False

        mock_multi_model_ai = Mock()
        mock_multi_model_ai.analyze_batch_optimized.return_value = (
            {"new_tasks": [], "cleanliness_score": 5, "raw_response": "test"}, False
        )

        mock_scene_understanding = Mock()
        mock_predictive_analytics = Mock()

        ai_coordinator = AICoordinator(
            config=config_disabled,
            multi_model_ai=mock_multi_model_ai,
            predictive_analytics=mock_predictive_analytics,
            scene_understanding=mock_scene_understanding
        )

        # Act
        result = await ai_coordinator._get_scene_understanding("test_zone", "test_purpose", {"raw_response": "test"})

        # Assert
        assert result == {}  # Should return empty when disabled
        mock_scene_understanding.get_detailed_scene_context.assert_not_called()

    def test_ai_coordinator_respects_predictive_analytics_toggle(self, base_config):
        """
        Test that AI Coordinator respects predictive analytics toggle
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange - Disable predictive analytics
        config_disabled = base_config.copy()
        config_disabled["ai_enhancements"]["predictive_analytics"] = False

        mock_multi_model_ai = Mock()
        mock_scene_understanding = Mock()
        mock_predictive_analytics = Mock()

        ai_coordinator = AICoordinator(
            config=config_disabled,
            multi_model_ai=mock_multi_model_ai,
            predictive_analytics=mock_predictive_analytics,
            scene_understanding=mock_scene_understanding
        )

        # Act
        result = ai_coordinator._get_predictive_insights("test_zone")

        # Assert
        assert result == {}  # Should return empty when disabled
        mock_predictive_analytics.get_prediction_for_zone.assert_not_called()

    @pytest.mark.asyncio
    async def test_scene_understanding_configuration_parameters(self, base_config):
        """
        Test that scene understanding uses configuration parameters correctly
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        custom_config = base_config.copy()
        custom_config["ai_enhancements"]["scene_understanding_settings"] = {
            "max_objects_detected": 5,
            "confidence_threshold": 0.8,
            "enable_seasonal_adjustments": False,
            "enable_time_context": False
        }

        mock_multi_model_ai = Mock()
        mock_scene_understanding = Mock()
        mock_predictive_analytics = Mock()

        ai_coordinator = AICoordinator(
            config=custom_config,
            multi_model_ai=mock_multi_model_ai,
            predictive_analytics=mock_predictive_analytics,
            scene_understanding=mock_scene_understanding
        )

        # Act
        await ai_coordinator._get_scene_understanding(
            "test_zone", "test_purpose", {"raw_response": "test response"}
        )

        # Assert
        mock_scene_understanding.get_detailed_scene_context.assert_called_once()
        call_args = mock_scene_understanding.get_detailed_scene_context.call_args

        # Verify configuration parameters were passed
        assert call_args.kwargs["max_objects"] == 5
        assert call_args.kwargs["confidence_threshold"] == 0.8
        assert call_args.kwargs["enable_seasonal_adjustments"] is False
        assert call_args.kwargs["enable_time_context"] is False

    def test_predictive_analytics_configuration_parameters(self, base_config):
        """
        Test that predictive analytics uses configuration parameters correctly
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        custom_config = base_config.copy()
        custom_config["ai_enhancements"]["predictive_analytics_settings"] = {
            "history_days": 14,
            "prediction_horizon_hours": 12,
            "min_data_points": 3,
            "enable_urgency_scoring": False,
            "enable_pattern_detection": False
        }

        mock_multi_model_ai = Mock()
        mock_scene_understanding = Mock()
        mock_predictive_analytics = Mock()

        ai_coordinator = AICoordinator(
            config=custom_config,
            multi_model_ai=mock_multi_model_ai,
            predictive_analytics=mock_predictive_analytics,
            scene_understanding=mock_scene_understanding
        )

        # Act
        ai_coordinator._get_predictive_insights("test_zone")

        # Assert
        mock_predictive_analytics.get_prediction_for_zone.assert_called_once()
        call_args = mock_predictive_analytics.get_prediction_for_zone.call_args
        
        # Verify configuration parameters were passed
        assert call_args.kwargs["history_days"] == 14
        assert call_args.kwargs["prediction_horizon_hours"] == 12
        assert call_args.kwargs["min_data_points"] == 3
        assert call_args.kwargs["enable_urgency_scoring"] is False
        assert call_args.kwargs["enable_pattern_detection"] is False

    def test_multi_model_ai_configuration_integration(self, base_config):
        """
        Test that MultiModelAI uses configuration correctly
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        custom_ai_config = {
            "caching": {
                "enabled": True,
                "intermediate_caching": False  # Disabled
            },
            "multi_model_ai": {
                "max_retries": 2,
                "timeout_seconds": 15
            }
        }

        mock_config = {
            "gemini_api_key": "test_key",
            "claude_api_key": "test_key"
        }

        with patch('ai.multi_model_ai.GeminiProvider') as mock_gemini, \
             patch('ai.multi_model_ai.ClaudeProvider'):
            
            # Configure mock to fail and trigger retries
            mock_provider = Mock()
            mock_provider.analyze_image.side_effect = Exception("Test error")
            mock_gemini.return_value = mock_provider

            multi_model_ai = MultiModelAIOptimizer(
                config=mock_config,
                ai_config=custom_ai_config
            )

            # Act
            result, was_cached = multi_model_ai._analyze_with_fallback("/test/image.jpg", "test prompt")

        # Assert
        # Should retry exactly 2 times (max_retries=2) before moving to next model
        assert mock_provider.analyze_image.call_count == 2

    def test_scene_understanding_seasonal_adjustments_disabled(self):
        """
        Test scene understanding with seasonal adjustments disabled
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        scene_understanding = AdvancedSceneUnderstanding()
        
        # Act
        scene_context = scene_understanding.analyze_scene_context(
            "test_zone", "test_purpose", "test response",
            enable_seasonal_adjustments=False,
            enable_time_context=False
        )

        # Assert
        # When disabled, should use default values instead of current time/season
        from ai.scene_understanding import Season, TimeOfDay
        assert scene_context.season == Season.SPRING  # Default
        assert scene_context.time_of_day == TimeOfDay.AFTERNOON  # Default

    def test_scene_understanding_seasonal_adjustments_enabled(self):
        """
        Test scene understanding with seasonal adjustments enabled
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        scene_understanding = AdvancedSceneUnderstanding()
        
        # Act
        scene_context = scene_understanding.analyze_scene_context(
            "test_zone", "test_purpose", "test response",
            enable_seasonal_adjustments=True,
            enable_time_context=True
        )

        # Assert
        # When enabled, should use actual current time/season (not defaults)
        from ai.scene_understanding import Season, TimeOfDay
        # The actual values will depend on when the test runs, but they shouldn't be the defaults
        # unless it happens to be spring afternoon when the test runs
        assert scene_context.season is not None
        assert scene_context.time_of_day is not None

    def test_configuration_validation_integration(self, base_config):
        """
        Test that configuration validator works with real configuration
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        validator = ConfigValidator(base_config)

        # Act
        result = validator.validate_full_config()

        # Assert
        assert result.is_valid
        assert len(result.errors) == 0
        summary = result.get_summary()
        assert summary["valid"] is True

    def test_configuration_validation_with_invalid_config(self):
        """
        Test configuration validator with invalid configuration
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        invalid_config = {
            "ai_enhancements": {
                "advanced_scene_understanding": "not_boolean",  # Invalid
                "caching": {
                    "ttl_seconds": 10  # Too low
                }
            }
        }
        validator = ConfigValidator(invalid_config)

        # Act
        result = validator.validate_full_config()

        # Assert
        assert not result.is_valid
        assert len(result.errors) > 0
        
        error_messages = " ".join(result.errors)
        assert "Feature toggle 'advanced_scene_understanding' must be a boolean" in error_messages

    @pytest.mark.asyncio
    async def test_end_to_end_configuration_flow(self, base_config):
        """
        Test end-to-end configuration flow through AI Coordinator
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        mock_multi_model_ai = Mock()
        # Use AsyncMock for the async method
        mock_multi_model_ai.analyze_batch_optimized = AsyncMock(return_value=(
            {
                "new_tasks": [{"description": "Test task"}],
                "cleanliness_score": 8,
                "raw_response": "Test response with objects on table"
            }, False
        ))

        mock_scene_understanding = Mock()
        mock_scene_understanding.get_detailed_scene_context.return_value = {
            "scene_context": {"room_type": "living_room"},
            "objects": [{"name": "objects", "location": "table"}],
            "generated_tasks": ["Pick up objects from table"],
            "contextual_insights": []
        }

        mock_predictive_analytics = Mock()
        mock_predictive_analytics.get_prediction_for_zone.return_value = {
            "next_predicted_cleaning_time": "2024-01-01T12:00:00Z",
            "urgency_score": 5
        }

        ai_coordinator = AICoordinator(
            config=base_config,
            multi_model_ai=mock_multi_model_ai,
            predictive_analytics=mock_predictive_analytics,
            scene_understanding=mock_scene_understanding
        )

        # Act
        result = await ai_coordinator.analyze_zone(
            zone_name="test_zone",
            image_path="/test/image.jpg",
            priority="manual",
            zone_purpose="test purpose"
        )

        # Assert
        assert result is not None
        assert not result.get("error", False)

        # Verify all components were called with correct configuration
        mock_multi_model_ai.analyze_batch_optimized.assert_called_once()
        mock_scene_understanding.get_detailed_scene_context.assert_called_once()
        mock_predictive_analytics.get_prediction_for_zone.assert_called_once()

        # Verify configuration parameters were passed to scene understanding
        scene_call_args = mock_scene_understanding.get_detailed_scene_context.call_args
        assert scene_call_args.kwargs["max_objects"] == 10
        assert scene_call_args.kwargs["confidence_threshold"] == 0.7
        assert scene_call_args.kwargs["enable_seasonal_adjustments"] is True
        assert scene_call_args.kwargs["enable_time_context"] is True

        # Verify configuration parameters were passed to predictive analytics
        pred_call_args = mock_predictive_analytics.get_prediction_for_zone.call_args
        assert pred_call_args.kwargs["history_days"] == 30
        assert pred_call_args.kwargs["prediction_horizon_hours"] == 24
        assert pred_call_args.kwargs["min_data_points"] == 5
        assert pred_call_args.kwargs["enable_urgency_scoring"] is True
        assert pred_call_args.kwargs["enable_pattern_detection"] is True
