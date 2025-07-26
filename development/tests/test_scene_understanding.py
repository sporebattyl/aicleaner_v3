"""
Test suite for Advanced Scene Understanding
Following TDD and AAA (Arrange, Act, Assert) principles
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from ai.scene_understanding import AdvancedSceneUnderstanding, SceneContext, RoomType, TimeOfDay, Season


class TestAdvancedSceneUnderstanding:
    """Test suite for AdvancedSceneUnderstanding class"""

    @pytest.fixture
    def scene_understanding(self) -> AdvancedSceneUnderstanding:
        """Arrange: Create AdvancedSceneUnderstanding instance"""
        with patch('os.makedirs'):  # Mock directory creation
            return AdvancedSceneUnderstanding(data_path="/test/data")

    @pytest.fixture
    def sample_ai_response(self) -> str:
        """Arrange: Sample AI response for testing"""
        return """
        The living room appears moderately clean. There are 3 books on the floor near the sofa,
        and 1 cup on the coffee table. The lighting is good and the room is well-organized overall.
        Some dust is visible on the shelves.
        """

    def test_get_detailed_scene_context_success(self, scene_understanding, sample_ai_response):
        """
        Test successful scene context extraction
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        zone_name = "living_room"
        zone_purpose = "Relaxation and entertainment"
        
        # Mock the analyze_scene_context method
        mock_scene_context = SceneContext(
            room_type=RoomType.LIVING_ROOM,
            detected_objects=["books", "cup", "sofa", "coffee table"],
            lighting_condition="good",
            time_of_day=TimeOfDay.AFTERNOON,
            season=Season.SPRING,
            cleanliness_indicators=["dusty"]
        )
        
        with patch.object(scene_understanding, 'analyze_scene_context', return_value=mock_scene_context):
            with patch.object(scene_understanding, 'generate_contextual_insights', return_value=[]):
                # Act
                result = scene_understanding.get_detailed_scene_context(
                    zone_name, zone_purpose, sample_ai_response
                )

        # Assert
        assert result is not None
        assert "scene_context" in result
        assert "objects" in result
        assert "generated_tasks" in result
        assert "contextual_insights" in result
        
        # Check scene context structure
        scene_context = result["scene_context"]
        assert scene_context["room_type"] == "living_room"
        assert "books" in scene_context["detected_objects"]
        assert scene_context["lighting_condition"] == "good"

    def test_extract_objects_with_locations(self, scene_understanding, sample_ai_response):
        """
        Test object extraction with location information
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange - sample_ai_response fixture provides the input

        # Act
        objects = scene_understanding._extract_objects_with_locations(sample_ai_response, max_objects=10, confidence_threshold=0.7)

        # Assert
        assert len(objects) > 0
        
        # Check for books on floor
        books_found = False
        cup_found = False
        
        for obj in objects:
            if "book" in obj["name"] and "floor" in obj["location"]:
                books_found = True
                assert obj["count"] == 3
            elif "cup" in obj["name"] and "table" in obj["location"]:
                cup_found = True
                assert obj["count"] == 1
        
        assert books_found, "Books on floor should be detected"
        assert cup_found, "Cup on table should be detected"

    def test_generate_granular_tasks(self, scene_understanding):
        """
        Test granular task generation
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        objects_with_locations = [
            {"name": "books", "location": "floor", "count": 3},
            {"name": "cup", "location": "coffee table", "count": 1}
        ]
        
        scene_context = SceneContext(
            room_type=RoomType.LIVING_ROOM,
            detected_objects=["books", "cup"],
            lighting_condition="good",
            time_of_day=TimeOfDay.AFTERNOON,
            season=Season.SPRING,
            cleanliness_indicators=["dusty"]
        )
        
        ai_response = "The room has some dust on surfaces"

        # Act
        tasks = scene_understanding._generate_granular_tasks(
            objects_with_locations, scene_context, ai_response
        )

        # Assert
        assert len(tasks) > 0
        
        # Check for specific tasks
        task_descriptions = [task["description"].lower() if isinstance(task, dict) else task.lower() for task in tasks]
        
        # Should have task for books
        books_task_found = any("3 books" in desc and "floor" in desc for desc in task_descriptions)
        assert books_task_found, "Should generate task for 3 books on floor"
        
        # Should have task for cup
        cup_task_found = any("cup" in desc and "coffee table" in desc for desc in task_descriptions)
        assert cup_task_found, "Should generate task for cup on coffee table"
        
        # Should have dusting task based on cleanliness indicators
        dust_task_found = any("dust" in desc for desc in task_descriptions)
        assert dust_task_found, "Should generate dusting task based on cleanliness indicators"

    def test_generate_granular_tasks_kitchen_context(self, scene_understanding):
        """
        Test task generation with kitchen-specific context
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        objects_with_locations = [
            {"name": "dishes", "location": "counter", "count": 2},
            {"name": "glass", "location": "sink", "count": 1}
        ]
        
        scene_context = SceneContext(
            room_type=RoomType.KITCHEN,
            detected_objects=["dishes", "glass"],
            lighting_condition="bright",
            time_of_day=TimeOfDay.MORNING,
            season=Season.SUMMER,
            cleanliness_indicators=[]
        )
        
        ai_response = "Kitchen with dishes on counter"

        # Act
        tasks = scene_understanding._generate_granular_tasks(
            objects_with_locations, scene_context, ai_response
        )

        # Assert
        assert len(tasks) > 0
        
        task_descriptions = [task["description"].lower() if isinstance(task, dict) else task.lower() for task in tasks]
        
        # Kitchen-specific tasks should use "clean and put away" instead of "pick up"
        dishes_task_found = any("clean and put away" in desc and "dishes" in desc for desc in task_descriptions)
        assert dishes_task_found, "Kitchen dishes should have 'clean and put away' task"

    def test_generate_granular_tasks_bathroom_context(self, scene_understanding):
        """
        Test task generation with bathroom-specific context
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        objects_with_locations = [
            {"name": "towel", "location": "floor", "count": 2}
        ]
        
        scene_context = SceneContext(
            room_type=RoomType.BATHROOM,
            detected_objects=["towel"],
            lighting_condition="dim",
            time_of_day=TimeOfDay.EVENING,
            season=Season.WINTER,
            cleanliness_indicators=[]
        )
        
        ai_response = "Bathroom with towel on floor"

        # Act
        tasks = scene_understanding._generate_granular_tasks(
            objects_with_locations, scene_context, ai_response
        )

        # Assert
        assert len(tasks) > 0
        
        task_descriptions = [task["description"].lower() if isinstance(task, dict) else task.lower() for task in tasks]
        
        # Bathroom-specific tasks should use "hang" for towel
        towel_task_found = any("hang" in desc and "towel" in desc for desc in task_descriptions)
        assert towel_task_found, "Bathroom towel should have 'hang' task"

    def test_get_detailed_scene_context_error_handling(self, scene_understanding):
        """
        Test error handling in get_detailed_scene_context
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        zone_name = "test_zone"
        zone_purpose = "Test purpose"
        invalid_ai_response = None  # This should cause an error

        # Act
        result = scene_understanding.get_detailed_scene_context(
            zone_name, zone_purpose, invalid_ai_response
        )

        # Assert
        assert result is not None
        assert result["scene_context"] == {}
        assert result["objects"] == []
        assert result["generated_tasks"] == []
        assert result["contextual_insights"] == []

    def test_extract_objects_with_locations_empty_response(self, scene_understanding):
        """
        Test object extraction with empty AI response
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        empty_response = ""

        # Act
        objects = scene_understanding._extract_objects_with_locations(empty_response, max_objects=10, confidence_threshold=0.7)

        # Assert
        assert objects == []

    def test_extract_objects_with_locations_no_matches(self, scene_understanding):
        """
        Test object extraction with response containing no location patterns
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        no_location_response = "The room is clean and tidy. Everything looks good."

        # Act
        objects = scene_understanding._extract_objects_with_locations(no_location_response, max_objects=10, confidence_threshold=0.7)

        # Assert
        assert objects == []

    def test_generate_granular_tasks_with_seasonal_context(self, scene_understanding):
        """
        Test task generation with seasonal adjustments
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        objects_with_locations = []
        
        scene_context = SceneContext(
            room_type=RoomType.LIVING_ROOM,
            detected_objects=[],
            lighting_condition="good",
            time_of_day=TimeOfDay.AFTERNOON,
            season=Season.SPRING,
            cleanliness_indicators=[]
        )
        
        # AI response mentioning spring cleaning focus areas
        ai_response = "The room needs attention to windows and air vents for spring cleaning"

        # Mock seasonal adjustments
        with patch.object(scene_understanding, 'seasonal_adjustments', {
            Season.SPRING: {
                'focus_areas': ['windows', 'air vents'],
                'frequency_multiplier': 1.2
            }
        }):
            # Act
            tasks = scene_understanding._generate_granular_tasks(
                objects_with_locations, scene_context, ai_response
            )

        # Assert
        task_descriptions = [task["description"].lower() if isinstance(task, dict) else task.lower() for task in tasks]
        
        # Should include seasonal tasks
        seasonal_task_found = any("seasonal" in desc and "spring" in desc for desc in task_descriptions)
        assert seasonal_task_found, "Should generate seasonal maintenance tasks"

    def test_generate_granular_tasks_limit_enforcement(self, scene_understanding):
        """
        Test that task generation respects the limit of 8 tasks
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange - Create many objects to potentially generate more than 8 tasks
        objects_with_locations = [
            {"name": f"item{i}", "location": "floor", "count": 1}
            for i in range(15)  # 15 objects
        ]
        
        scene_context = SceneContext(
            room_type=RoomType.LIVING_ROOM,
            detected_objects=[f"item{i}" for i in range(15)],
            lighting_condition="good",
            time_of_day=TimeOfDay.AFTERNOON,
            season=Season.SPRING,
            cleanliness_indicators=["dusty", "cluttered", "dirty"]  # 3 more potential tasks
        )
        
        ai_response = "Room with many items"

        # Act
        tasks = scene_understanding._generate_granular_tasks(
            objects_with_locations, scene_context, ai_response
        )

        # Assert
        assert len(tasks) <= 8, "Should not generate more than 8 tasks"
