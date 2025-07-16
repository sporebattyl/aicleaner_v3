"""
Test suite for AI Coordinator
Following TDD and AAA (Arrange, Act, Assert) principles
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from typing import Dict, Any, List

from ai.ai_coordinator import AICoordinator
from ai.multi_model_ai import MultiModelAIOptimizer
from ai.predictive_analytics import PredictiveAnalytics
from ai.scene_understanding import AdvancedSceneUnderstanding


class TestAICoordinator:
    """Test suite for AICoordinator class"""

    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Arrange: Mock configuration for testing"""
        return {
            "ai_enhancements": {
                "advanced_scene_understanding": True,
                "predictive_analytics": True,
                "model_selection": {
                    "detailed_analysis": "gemini-pro",
                    "complex_reasoning": "claude-sonnet",
                    "simple_analysis": "gemini-flash"
                }
            }
        }

    @pytest.fixture
    def mock_multi_model_ai(self) -> Mock:
        """Arrange: Mock MultiModelAIOptimizer"""
        mock = Mock(spec=MultiModelAIOptimizer)
        mock.analyze_batch_optimized = AsyncMock()
        return mock

    @pytest.fixture
    def mock_predictive_analytics(self) -> Mock:
        """Arrange: Mock PredictiveAnalytics"""
        mock = Mock(spec=PredictiveAnalytics)
        mock.get_prediction_for_zone = Mock()
        mock.record_task_completion = Mock()
        return mock

    @pytest.fixture
    def mock_scene_understanding(self) -> Mock:
        """Arrange: Mock AdvancedSceneUnderstanding"""
        mock = Mock(spec=AdvancedSceneUnderstanding)
        mock.get_detailed_scene_context = Mock()
        mock.generate_contextual_insights = Mock()
        return mock

    @pytest.fixture
    def ai_coordinator(self, mock_config, mock_multi_model_ai, 
                      mock_predictive_analytics, mock_scene_understanding) -> AICoordinator:
        """Arrange: Create AICoordinator instance with mocked dependencies"""
        return AICoordinator(
            config=mock_config,
            multi_model_ai=mock_multi_model_ai,
            predictive_analytics=mock_predictive_analytics,
            scene_understanding=mock_scene_understanding
        )

    @pytest.mark.asyncio
    async def test_analyze_zone_success(self, ai_coordinator, mock_multi_model_ai,
                                       mock_predictive_analytics, mock_scene_understanding):
        """
        Test successful zone analysis with all components working
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        zone_name = "test_zone"
        image_path = "/test/image.jpg"
        priority = "manual"
        zone_purpose = "Test zone for cleaning"
        active_tasks = [{"id": "task1", "description": "Clean table"}]
        ignore_rules = ["ignore books"]

        # Mock successful core analysis
        core_analysis_result = {
            "new_tasks": [{"description": "Vacuum floor", "priority": 5}],
            "completed_tasks": [],
            "cleanliness_score": 8,
            "analysis_summary": "Room is mostly clean",
            "raw_response": "The room appears clean with minor tasks needed."
        }
        mock_multi_model_ai.analyze_batch_optimized.return_value = (core_analysis_result, False)

        # Mock scene understanding
        scene_context_result = {
            "scene_context": {"room_type": "living_room", "detected_objects": ["table", "chair"]},
            "contextual_insights": [{"type": "room_specific", "description": "Living room context"}]
        }
        mock_scene_understanding.get_detailed_scene_context.return_value = scene_context_result

        # Mock predictive analytics
        predictive_result = {"next_predicted_cleaning_time": "2024-01-01T12:00:00Z", "urgency_score": 3}
        mock_predictive_analytics.get_prediction_for_zone.return_value = predictive_result

        # Act
        result = await ai_coordinator.analyze_zone(
            zone_name=zone_name,
            image_path=image_path,
            priority=priority,
            zone_purpose=zone_purpose,
            active_tasks=active_tasks,
            ignore_rules=ignore_rules
        )

        # Assert
        assert result is not None
        assert not result.get("error", False)
        assert "timestamp" in result
        assert "core_assessment" in result
        assert "scene_understanding" in result
        assert "predictive_insights" in result
        assert "generated_tasks" in result
        assert result["was_cached"] is False
        assert result["ai_coordinator_version"] == "1.0"

        # Verify all components were called correctly
        mock_multi_model_ai.analyze_batch_optimized.assert_called_once_with(
            image_path, zone_name, zone_purpose, active_tasks, ignore_rules
        )
        mock_scene_understanding.get_detailed_scene_context.assert_called_once()
        # Verify predictive analytics called with configuration parameters
        mock_predictive_analytics.get_prediction_for_zone.assert_called_once_with(
            zone_name,
            history_days=30,
            prediction_horizon_hours=24,
            min_data_points=5,
            enable_urgency_scoring=True,
            enable_pattern_detection=True
        )

    @pytest.mark.asyncio
    async def test_analyze_zone_core_analysis_failure(self, ai_coordinator, mock_multi_model_ai):
        """
        Test zone analysis when core analysis fails
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        zone_name = "test_zone"
        image_path = "/test/image.jpg"
        priority = "scheduled"
        zone_purpose = "Test zone"

        # Mock failed core analysis
        mock_multi_model_ai.analyze_batch_optimized.return_value = (None, False)

        # Act
        result = await ai_coordinator.analyze_zone(
            zone_name=zone_name,
            image_path=image_path,
            priority=priority,
            zone_purpose=zone_purpose
        )

        # Assert
        assert result is not None
        assert result.get("error") is True
        assert "Core analysis failed" in result.get("error_message", "")
        assert result["cleanliness_score"] == 0
        assert result["generated_tasks"] == []

    @pytest.mark.asyncio
    async def test_analyze_zone_with_cached_result(self, ai_coordinator, mock_multi_model_ai,
                                                  mock_predictive_analytics, mock_scene_understanding):
        """
        Test zone analysis with cached core analysis result
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        zone_name = "test_zone"
        image_path = "/test/image.jpg"
        priority = "scheduled"
        zone_purpose = "Test zone"

        # Mock cached core analysis
        core_analysis_result = {
            "new_tasks": [{"description": "Dust shelves", "priority": 3}],
            "completed_tasks": [],
            "cleanliness_score": 7,
            "analysis_summary": "Cached analysis result"
        }
        mock_multi_model_ai.analyze_batch_optimized.return_value = (core_analysis_result, True)

        # Mock other components
        mock_scene_understanding.get_detailed_scene_context.return_value = {}
        mock_predictive_analytics.get_prediction_for_zone.return_value = {}

        # Act
        result = await ai_coordinator.analyze_zone(
            zone_name=zone_name,
            image_path=image_path,
            priority=priority,
            zone_purpose=zone_purpose
        )

        # Assert
        assert result is not None
        assert not result.get("error", False)
        assert result["was_cached"] is True
        assert result["cleanliness_score"] == 7

    def test_select_model_manual_priority(self, ai_coordinator):
        """
        Test model selection for manual priority
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        priority = "manual"

        # Act
        selected_model = ai_coordinator._select_model(priority)

        # Assert
        assert selected_model == "gemini-pro"

    def test_select_model_complex_priority(self, ai_coordinator):
        """
        Test model selection for complex priority
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        priority = "complex"

        # Act
        selected_model = ai_coordinator._select_model(priority)

        # Assert
        assert selected_model == "claude-sonnet"

    def test_select_model_default_priority(self, ai_coordinator):
        """
        Test model selection for default/scheduled priority
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        priority = "scheduled"

        # Act
        selected_model = ai_coordinator._select_model(priority)

        # Assert
        assert selected_model == "gemini-flash"

    def test_create_error_result(self, ai_coordinator):
        """
        Test error result creation
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        error_message = "Test error message"

        # Act
        result = ai_coordinator._create_error_result(error_message)

        # Assert
        assert result["error"] is True
        assert result["error_message"] == error_message
        assert result["cleanliness_score"] == 0
        assert result["generated_tasks"] == []
        assert result["completed_tasks"] == []
        assert "timestamp" in result
        assert result["ai_coordinator_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_analyze_zone_with_scene_understanding_disabled(self, mock_config, mock_multi_model_ai,
                                                                 mock_predictive_analytics, mock_scene_understanding):
        """
        Test zone analysis with scene understanding disabled
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        mock_config["ai_enhancements"]["advanced_scene_understanding"] = False
        ai_coordinator = AICoordinator(
            config=mock_config,
            multi_model_ai=mock_multi_model_ai,
            predictive_analytics=mock_predictive_analytics,
            scene_understanding=mock_scene_understanding
        )

        zone_name = "test_zone"
        image_path = "/test/image.jpg"
        priority = "manual"
        zone_purpose = "Test zone"

        # Mock successful core analysis
        core_analysis_result = {
            "new_tasks": [{"description": "Clean floor", "priority": 5}],
            "completed_tasks": [],
            "cleanliness_score": 6
        }
        mock_multi_model_ai.analyze_batch_optimized.return_value = (core_analysis_result, False)
        mock_predictive_analytics.get_prediction_for_zone.return_value = {}

        # Act
        result = await ai_coordinator.analyze_zone(
            zone_name=zone_name,
            image_path=image_path,
            priority=priority,
            zone_purpose=zone_purpose
        )

        # Assert
        assert result is not None
        assert not result.get("error", False)
        assert result["scene_understanding"] == {}
        mock_scene_understanding.get_detailed_scene_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_analyze_zone_with_predictive_analytics_disabled(self, mock_config, mock_multi_model_ai,
                                                                  mock_predictive_analytics, mock_scene_understanding):
        """
        Test zone analysis with predictive analytics disabled
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        mock_config["ai_enhancements"]["predictive_analytics"] = False
        ai_coordinator = AICoordinator(
            config=mock_config,
            multi_model_ai=mock_multi_model_ai,
            predictive_analytics=mock_predictive_analytics,
            scene_understanding=mock_scene_understanding
        )

        zone_name = "test_zone"
        image_path = "/test/image.jpg"
        priority = "manual"
        zone_purpose = "Test zone"

        # Mock successful core analysis
        core_analysis_result = {
            "new_tasks": [{"description": "Organize books", "priority": 4}],
            "completed_tasks": [],
            "cleanliness_score": 8
        }
        mock_multi_model_ai.analyze_batch_optimized.return_value = (core_analysis_result, False)
        mock_scene_understanding.get_detailed_scene_context.return_value = {}

        # Act
        result = await ai_coordinator.analyze_zone(
            zone_name=zone_name,
            image_path=image_path,
            priority=priority,
            zone_purpose=zone_purpose
        )

        # Assert
        assert result is not None
        assert not result.get("error", False)
        assert result["predictive_insights"] == {}
        mock_predictive_analytics.get_prediction_for_zone.assert_not_called()
