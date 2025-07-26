"""
Tests for the StateManager class.
Following TDD principles and AAA pattern.
"""
import unittest
import asyncio
import json
import os
import tempfile
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone, timedelta

# Import the module to test
from core.state_manager import StateManager

class TestStateManager(unittest.TestCase):
    """Test cases for StateManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Arrange
        # Create temporary file for state
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_file = os.path.join(self.temp_dir.name, "state.json")
        
        # Create state manager
        config = {"state_file": self.state_file}
        self.state_manager = StateManager(config)
        
    def tearDown(self):
        """Tear down test fixtures."""
        # Clean up temporary directory
        self.temp_dir.cleanup()
        
    async def asyncSetUp(self):
        """Set up async test fixtures."""
        # Initialize state manager
        await self.state_manager.initialize()
        
    async def asyncTearDown(self):
        """Tear down async test fixtures."""
        # Shutdown state manager
        await self.state_manager.shutdown()
        
    async def test_update_analysis_state(self):
        """Test updating analysis state."""
        # Arrange
        analysis_id = "test-id"
        state = {
            "id": analysis_id,
            "zone_name": "test_zone",
            "state": "image_captured",
            "start_time": datetime.now(timezone.utc).isoformat()
        }
        
        # Act
        await self.state_manager.update_analysis_state(analysis_id, state)
        
        # Assert
        # Check that the analysis was recorded in the state
        async with self.state_manager.lock:
            analyses = self.state_manager.state.get("analyses", {})
            self.assertIn(analysis_id, analyses)
            result = analyses[analysis_id]
            self.assertEqual(result["id"], analysis_id)
            self.assertEqual(result["zone_name"], "test_zone")
            self.assertEqual(result["current_state"], "IMAGE_CAPTURED")
        
    async def test_record_api_call(self):
        """Test recording API calls."""
        # Arrange
        initial_calls = await self.state_manager.get_api_calls_today()

        # Act
        await self.state_manager.record_api_call("gpt-4", 1000, 0.02)

        # Assert
        updated_calls = await self.state_manager.get_api_calls_today()
        self.assertEqual(updated_calls, initial_calls + 1)
        
    async def test_get_api_calls_today(self):
        """Test getting API calls today."""
        # Arrange
        # Reset API calls
        self.state_manager.state["api_calls"] = {
            "today": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "count": 5
        }
        await self.state_manager.save_state()
        
        # Act
        calls = await self.state_manager.get_api_calls_today()
        
        # Assert
        self.assertEqual(calls, 5)
        
    async def test_api_calls_reset_on_new_day(self):
        """Test API calls reset on new day."""
        # Arrange
        # Set API calls for yesterday
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        self.state_manager.state["api_calls"] = {
            "today": yesterday,
            "count": 10
        }
        await self.state_manager.save_state()
        
        # Act
        calls = await self.state_manager.get_api_calls_today()
        
        # Assert
        self.assertEqual(calls, 0)
        self.assertEqual(
            self.state_manager.state["api_calls"]["today"],
            datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )
        
    async def test_get_cost_estimate_today(self):
        """Test getting cost estimate today."""
        # Arrange
        # Set API calls
        self.state_manager.state["api_calls"] = {
            "today": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "count": 20
        }
        await self.state_manager.save_state()
        
        # Act
        cost = await self.state_manager.get_cost_estimate_today()
        
        # Assert
        # Default cost per call is $0.0025
        self.assertEqual(cost, 20 * 0.0025)
        
    async def test_get_zone_state(self):
        """Test getting zone state."""
        # Arrange
        zone_name = "test_zone"

        # Add some analysis states
        await self.state_manager.update_analysis_state("analysis_1", AnalysisState.IMAGE_CAPTURED, {"zone_name": zone_name})
        await self.state_manager.update_analysis_state("analysis_2", AnalysisState.LOCAL_ANALYSIS_COMPLETE, {"zone_name": zone_name})

        # Act
        zone_state = await self.state_manager.get_zone_state(zone_name)

        # Assert
        self.assertIsNotNone(zone_state)
        self.assertEqual(zone_state["name"], zone_name)
        self.assertIn("last_analysis", zone_state)
        self.assertIn("active_tasks", zone_state)
            
    async def test_cleanup_old_states(self):
        """Test cleaning up old states."""
        # Arrange
        # Add some analysis states
        now = datetime.now(timezone.utc)
        states = [
            {
                "id": f"test-{i}",
                "zone_name": "test_zone",
                "state": "cycle_complete",
                "start_time": (now - timedelta(days=i)).isoformat()
            }
            for i in range(10)
        ]
        
        for state in states:
            await self.state_manager.update_analysis_state(state["id"], state)
            
        # Act
        await self.state_manager.cleanup_old_states()
        
        # Assert
        # Default retention is 7 days
        all_states = await self.state_manager.get_all_analysis_states()
        self.assertEqual(len(all_states), 7)
        
        # Check that oldest states were removed
        for state in all_states:
            start_time = datetime.fromisoformat(state["start_time"])
            self.assertLess((now - start_time).days, 8)
            
    async def test_save_and_load_state(self):
        """Test saving and loading state."""
        # Arrange
        # Modify state
        self.state_manager.state["test_key"] = "test_value"
        
        # Act
        # Save state
        await self.state_manager.save_state()
        
        # Create new state manager with same file
        new_state_manager = StateManager(self.state_file)
        await new_state_manager.initialize()
        
        # Assert
        self.assertEqual(new_state_manager.state["test_key"], "test_value")
        
    async def test_get_analysis_duration_stats(self):
        """Test getting analysis duration stats."""
        # Arrange
        # Add some completed analyses with durations
        now = datetime.now(timezone.utc)
        durations = [5, 10, 15, 20, 25]
        
        for i, duration in enumerate(durations):
            state = {
                "id": f"test-{i}",
                "zone_name": "test_zone",
                "state": "cycle_complete",
                "start_time": (now - timedelta(seconds=duration)).isoformat(),
                "end_time": now.isoformat(),
                "duration": duration
            }
            await self.state_manager.update_analysis_state(state["id"], state)
            
        # Act
        stats = await self.state_manager.get_analysis_duration_stats()
        
        # Assert
        self.assertEqual(stats["average"], sum(durations) / len(durations))
        self.assertEqual(stats["min"], min(durations))
        self.assertEqual(stats["max"], max(durations))
        self.assertEqual(stats["count"], len(durations))


# Run tests
if __name__ == "__main__":
    unittest.main()

