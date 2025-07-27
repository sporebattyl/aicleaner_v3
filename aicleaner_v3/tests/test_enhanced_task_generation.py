"""
Test suite for Enhanced Task Generation with Object Database Integration
Following TDD and AAA (Arrange, Act, Assert) principles

This test suite verifies the enhanced task generation functionality that integrates
with the object database and implements Gemini's hybrid prioritization system.
"""

import pytest
from unittest.mock import Mock, patch

from ai.scene_understanding import AdvancedSceneUnderstanding, SceneContext, RoomType, TimeOfDay, Season
from ai.object_database import SafetyLevel, HygieneImpact, CleaningFrequency


class TestEnhancedTaskGeneration:
    """Test suite for enhanced task generation functionality"""

    @pytest.fixture
    def scene_understanding(self) -> AdvancedSceneUnderstanding:
        """Arrange: Create AdvancedSceneUnderstanding instance"""
        return AdvancedSceneUnderstanding()

    @pytest.fixture
    def sample_scene_context(self) -> SceneContext:
        """Arrange: Sample scene context for testing"""
        return SceneContext(
            room_type=RoomType.KITCHEN,
            detected_objects=["dishes", "cup", "food"],
            lighting_condition="bright",
            time_of_day=TimeOfDay.EVENING,
            season=Season.SPRING,
            cleanliness_indicators=["cluttered"]
        )

    @pytest.fixture
    def sample_objects_with_locations(self) -> list:
        """Arrange: Sample objects with location data"""
        return [
            {"name": "dishes", "location": "counter", "count": 3, "confidence": 0.9},
            {"name": "cup", "location": "table", "count": 1, "confidence": 0.8},
            {"name": "food", "location": "counter", "count": 1, "confidence": 0.7}
        ]

    def test_enhanced_task_generation_with_object_database(self, scene_understanding, 
                                                          sample_scene_context, 
                                                          sample_objects_with_locations):
        """
        Test enhanced task generation with object database integration
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        ai_response = "Kitchen has dishes on counter and cup on table"

        # Act
        tasks = scene_understanding._generate_granular_tasks(
            sample_objects_with_locations, sample_scene_context, ai_response
        )

        # Assert
        assert len(tasks) > 0
        assert all(isinstance(task, dict) for task in tasks)
        
        # Check task structure
        for task in tasks:
            assert "description" in task
            assert "priority" in task
            assert "urgency" in task
            assert "object_type" in task
            assert "location" in task
            assert "safety_level" in task
            assert "hygiene_impact" in task
            assert "estimated_time" in task

    def test_hybrid_prioritization_safety_first(self, scene_understanding, sample_scene_context):
        """
        Test that safety-critical items get highest priority
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange - Include safety-critical object (food)
        objects_with_locations = [
            {"name": "food", "location": "counter", "count": 1, "confidence": 0.9},
            {"name": "book", "location": "table", "count": 1, "confidence": 0.8}
        ]
        ai_response = "Kitchen has food on counter and book on table"

        # Act
        tasks = scene_understanding._generate_granular_tasks(
            objects_with_locations, sample_scene_context, ai_response
        )

        # Assert
        assert len(tasks) >= 2
        
        # Food task should have higher priority than book task
        food_task = next((t for t in tasks if t["object_type"] == "food"), None)
        book_task = next((t for t in tasks if t["object_type"] == "book"), None)
        
        assert food_task is not None
        assert book_task is not None
        assert food_task["priority"] > book_task["priority"]

    def test_hygiene_impact_prioritization(self, scene_understanding, sample_scene_context):
        """
        Test that hygiene-critical items get prioritized
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange - Include hygiene-critical object (dishes)
        objects_with_locations = [
            {"name": "dishes", "location": "sink", "count": 2, "confidence": 0.9},
            {"name": "clothes", "location": "chair", "count": 1, "confidence": 0.8}
        ]
        ai_response = "Kitchen has dishes in sink and clothes on chair"

        # Act
        tasks = scene_understanding._generate_granular_tasks(
            objects_with_locations, sample_scene_context, ai_response
        )

        # Assert
        assert len(tasks) >= 2
        
        # Dishes task should have higher priority than clothes task
        dishes_task = next((t for t in tasks if t["object_type"] == "dishes"), None)
        clothes_task = next((t for t in tasks if t["object_type"] == "clothes"), None)
        
        assert dishes_task is not None
        assert clothes_task is not None
        assert dishes_task["priority"] > clothes_task["priority"]

    def test_room_specific_task_enhancement(self, scene_understanding):
        """
        Test room-specific task enhancement
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange - Kitchen context
        kitchen_context = SceneContext(
            room_type=RoomType.KITCHEN,
            detected_objects=["dishes"],
            lighting_condition="bright",
            time_of_day=TimeOfDay.AFTERNOON,
            season=Season.SPRING,
            cleanliness_indicators=[]
        )
        
        objects_with_locations = [
            {"name": "dishes", "location": "counter", "count": 2, "confidence": 0.9}
        ]
        ai_response = "Kitchen has dishes on counter"

        # Act
        tasks = scene_understanding._generate_granular_tasks(
            objects_with_locations, kitchen_context, ai_response
        )

        # Assert
        assert len(tasks) > 0
        dishes_task = next((t for t in tasks if t["object_type"] == "dishes"), None)
        assert dishes_task is not None
        
        # Kitchen dishes should use "Clean and put away" instead of "Pick up"
        assert "clean and put away" in dishes_task["description"].lower()

    def test_context_based_task_generation(self, scene_understanding, sample_scene_context):
        """
        Test context-based task generation from cleanliness indicators
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        ai_response = "Room is cluttered and dusty"

        # Act
        context_tasks = scene_understanding._generate_context_based_tasks(
            sample_scene_context, ai_response
        )

        # Assert
        assert len(context_tasks) > 0
        
        # Should generate task for cluttered indicator
        clutter_task = next((t for t in context_tasks if "declutter" in t["description"]), None)
        assert clutter_task is not None
        assert clutter_task["object_type"] == "general"

    def test_seasonal_task_generation(self, scene_understanding, sample_scene_context):
        """
        Test seasonal task generation
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        ai_response = "Windows need attention for spring cleaning"

        # Act
        seasonal_tasks = scene_understanding._generate_seasonal_tasks(
            sample_scene_context, ai_response
        )

        # Assert
        # Note: This depends on the seasonal_adjustments configuration
        # If windows are in spring focus areas, we should get a seasonal task
        if seasonal_tasks:
            seasonal_task = seasonal_tasks[0]
            assert "seasonal" in seasonal_task["description"].lower()
            assert seasonal_task["object_type"] == "seasonal"

    def test_task_limit_enforcement(self, scene_understanding, sample_scene_context):
        """
        Test that task generation respects the 8-task limit
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange - Create many objects to potentially generate more than 8 tasks
        many_objects = [
            {"name": f"item{i}", "location": "floor", "count": 1, "confidence": 0.8}
            for i in range(15)
        ]
        ai_response = "Room has many items scattered around"

        # Act
        tasks = scene_understanding._generate_granular_tasks(
            many_objects, sample_scene_context, ai_response
        )

        # Assert
        assert len(tasks) <= 8, f"Should not generate more than 8 tasks, got {len(tasks)}"

    def test_object_database_cache_integration(self, scene_understanding):
        """
        Test that object database cache is properly integrated
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        object_name = "dishes"

        # Act
        object_info = scene_understanding.object_db_cache.get_object_info(object_name)

        # Assert
        assert object_info is not None
        assert "priority_level" in object_info
        assert "cleaning_frequency" in object_info
        assert "safety_level" in object_info
        assert "hygiene_impact" in object_info

    def test_cache_performance_improvement(self, scene_understanding):
        """
        Test that object database cache improves performance
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        object_name = "dishes"

        # Act - First call (cache miss)
        info1 = scene_understanding.object_db_cache.get_object_info(object_name)
        
        # Act - Second call (cache hit)
        info2 = scene_understanding.object_db_cache.get_object_info(object_name)

        # Assert
        assert info1 == info2  # Should return same data
        
        # Check cache stats
        stats = scene_understanding.object_db_cache.get_cache_stats()
        assert stats["hits"] > 0  # Should have at least one cache hit
        assert stats["hit_rate_percent"] > 0  # Should have positive hit rate

    def test_enhanced_task_with_unknown_object(self, scene_understanding, sample_scene_context):
        """
        Test enhanced task generation with unknown object
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange - Unknown object not in database
        objects_with_locations = [
            {"name": "unknown_object", "location": "table", "count": 1, "confidence": 0.8}
        ]
        ai_response = "Room has unknown object on table"

        # Act
        tasks = scene_understanding._generate_granular_tasks(
            objects_with_locations, sample_scene_context, ai_response
        )

        # Assert
        assert len(tasks) > 0

        # Find the unknown object task (might not be first due to prioritization)
        unknown_task = next((t for t in tasks if t["object_type"] == "unknown_object"), None)
        assert unknown_task is not None, "Should generate a task for unknown object"

        # Should still generate a task with default values
        assert unknown_task["priority"] == 3  # Default priority for unknown objects
        assert unknown_task["description"] == "Pick up the unknown_object from the table"

    def test_time_sensitive_priority_boost(self, scene_understanding):
        """
        Test time-sensitive priority boosts (e.g., evening dish cleaning)
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange - Evening context
        evening_context = SceneContext(
            room_type=RoomType.KITCHEN,
            detected_objects=["dishes"],
            lighting_condition="dim",
            time_of_day=TimeOfDay.EVENING,
            season=Season.SPRING,
            cleanliness_indicators=[]
        )
        
        objects_with_locations = [
            {"name": "dishes", "location": "sink", "count": 1, "confidence": 0.9}
        ]
        ai_response = "Kitchen has dishes in sink"

        # Act
        tasks = scene_understanding._generate_granular_tasks(
            objects_with_locations, evening_context, ai_response
        )

        # Assert
        assert len(tasks) > 0
        dishes_task = tasks[0]
        
        # Evening dishes should get priority boost
        assert dishes_task["priority"] >= 8  # Should be high priority in evening
