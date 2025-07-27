"""
Tests for the ZoneAnalyzer class.
Following TDD principles and AAA pattern.
"""
import unittest
import asyncio
import json
import os
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone
from PIL import Image

# Import the module to test
from core.analyzer import ZoneAnalyzer, AnalysisPriority, AnalysisState

class TestZoneAnalyzer(unittest.TestCase):
    """Test cases for ZoneAnalyzer."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Arrange
        self.ha_client = AsyncMock()
        self.gemini_client = AsyncMock()
        self.state_manager = AsyncMock()
        self.performance_monitor = AsyncMock()
        
        # Mock config
        self.config = {
            "max_concurrent_analyses": 2,
            "analysis_workers": 1,
            "zones": [
                {
                    "name": "test_zone",
                    "camera_entity": "camera.test",
                    "todo_list_entity": "todo.test",
                    "purpose": "Testing",
                    "ignore_rules": ["Ignore this"]
                }
            ]
        }
        
        # Create analyzer
        self.multi_model_ai_optimizer = AsyncMock()
        self.analyzer = ZoneAnalyzer(
            self.ha_client,
            self.state_manager,
            self.config,
            self.multi_model_ai_optimizer
        )
        
    async def asyncSetUp(self):
        """Set up async test fixtures."""
        # Start analyzer
        await self.analyzer.start()
        
    async def asyncTearDown(self):
        """Tear down async test fixtures."""
        # Stop analyzer
        await self.analyzer.stop()
        
    async def test_queue_analysis(self):
        """Test queuing analysis."""
        # Arrange
        zone_name = "test_zone"
        priority = AnalysisPriority.MANUAL
        
        # Act
        analysis_id = await self.analyzer.queue_analysis(zone_name, priority)
        
        # Assert
        self.assertIsNotNone(analysis_id)
        self.assertTrue(isinstance(analysis_id, str))
        self.assertEqual(self.analyzer.queue.qsize(), 1)
        
    @patch('core.analyzer.Image.open')
    async def test_process_analysis(self):
        """Test processing analysis."""
        # Arrange
        # Mock image
        mock_image = MagicMock(spec=Image.Image)
        mock_image.open.return_value = mock_image
        
        # Mock capture_image
        self.ha_client.capture_image.return_value = "/tmp/test.jpg"
        
        # Mock get_todo_list_items
        self.ha_client.get_todo_list_items.return_value = []

        # Mock analyze_batch_optimized to return AI Coordinator format
        self.multi_model_ai_optimizer.analyze_batch_optimized.return_value = (
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "was_cached": False,
                "core_assessment": {
                    "completed_tasks": [],
                    "new_tasks": [{"description": "Clean the table", "priority": 5}, {"description": "Organize books", "priority": 5}],
                    "cleanliness_assessment": {"score": 7, "state": "moderately_clean", "observations": [], "recommendations": []}
                },
                "scene_understanding": {
                    "scene_context": {"room_type": "living_room", "detected_objects": ["table", "books"]},
                    "contextual_insights": []
                },
                "predictive_insights": {"urgency_score": 3, "next_predicted_cleaning_time": "2024-01-01T12:00:00Z"},
                "generated_tasks": [{"description": "Clean the table", "priority": 5}, {"description": "Organize books", "priority": 5}],
                "completed_tasks": [],
                "cleanliness_score": 7,
                "analysis_summary": "Room is moderately clean",
                "ai_coordinator_version": "1.0"
            },
            False  # was_cached
        )
        
        # Create analysis request
        request = {
            "id": "test-id",
            "zone_name": "test_zone",
            "priority": AnalysisPriority.MANUAL.value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Act
        await self.analyzer._process_analysis(request)
        
        # Assert
        # Check state updates
        self.state_manager.update_analysis_state.assert_called()
        
        # Check image capture
        self.ha_client.capture_image.assert_called_once()

        # Check multi-model AI analysis call
        self.multi_model_ai_optimizer.analyze_batch_optimized.assert_called_once()

        # Check task creation
        self.ha_client.add_todo_item.assert_called()
        
        # Check performance metrics
        self.performance_monitor.record_analysis_completed.assert_called_once()
        self.performance_monitor.record_tasks_generated.assert_called_once()
        
    async def test_parse_gemini_json_response(self):
        """Test parsing Gemini JSON response."""
        # Arrange
        # Valid JSON response
        valid_response = '["Clean the table", "Organize books"]'
        
        # Invalid JSON response
        invalid_response = 'This is not JSON'
        
        # Act
        valid_result = self.analyzer._parse_gemini_json_response(valid_response)
        invalid_result = self.analyzer._parse_gemini_json_response(invalid_response)
        
        # Assert
        self.assertIsNotNone(valid_result)
        self.assertEqual(len(valid_result), 2)
        self.assertEqual(valid_result[0], "Clean the table")
        self.assertEqual(valid_result[1], "Organize books")
        
        self.assertIsNone(invalid_result)
        
    def test_get_zone_config(self):
        """Test getting zone configuration."""
        # Arrange
        zone_name = "test_zone"
        non_existent_zone = "non_existent"
        
        # Act
        zone_config = self.analyzer._get_zone_config(zone_name)
        missing_config = self.analyzer._get_zone_config(non_existent_zone)
        
        # Assert
        self.assertIsNotNone(zone_config)
        self.assertEqual(zone_config["name"], zone_name)
        self.assertEqual(zone_config["camera_entity"], "camera.test")
        
        self.assertIsNone(missing_config)


# Run tests
if __name__ == "__main__":
    unittest.main()