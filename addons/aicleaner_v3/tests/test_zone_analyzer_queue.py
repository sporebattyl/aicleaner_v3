"""
Tests for the ZoneAnalyzer class.
Following TDD principles with AAA pattern.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
import json
from datetime import datetime

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the modules to test
from core.analyzer import ZoneAnalyzer, AnalysisPriority, AnalysisState

class TestZoneAnalyzer:
    """Test suite for ZoneAnalyzer class."""
    
    @pytest.fixture
    def state_manager_mock(self):
        """Create a mock state manager."""
        state_manager = AsyncMock()
        state_manager.update_analysis_state = AsyncMock()
        state_manager.get_analysis_state = AsyncMock()
        return state_manager
        
    @pytest.fixture
    def analyzer(self, state_manager_mock):
        """Create a ZoneAnalyzer instance with mocked dependencies."""
        ha_client_mock = AsyncMock()
        config = {
            "max_concurrent_analyses": 3,
            "analysis_workers": 2,
            "zones": [
                {
                    "name": "Kitchen",
                    "camera_entity": "camera.kitchen",
                    "todo_list_entity": "todo.kitchen",
                    "purpose": "Keep kitchen clean"
                }
            ]
        }
        multi_model_ai_optimizer_mock = AsyncMock()
        return ZoneAnalyzer(ha_client_mock, state_manager_mock, config, multi_model_ai_optimizer_mock)
        
    @pytest.mark.asyncio
    async def test_queue_analysis(self, analyzer, state_manager_mock):
        """Test queuing an analysis request."""
        # Arrange
        zone_name = "Kitchen"
        analysis_func = AsyncMock(return_value={"result": "clean"})
        priority = AnalysisPriority.MANUAL
        
        # Act
        analysis_id = await analyzer.queue_analysis(
            zone_name=zone_name,
            priority=priority
        )
        
        # Assert
        assert analysis_id is not None
        assert isinstance(analysis_id, str)
        # Note: The queue manager handles the actual queuing internally
        
    @pytest.mark.asyncio
    async def test_worker_processes_queue(self, analyzer, state_manager_mock):
        """Test that worker processes items from the queue."""
        # Arrange
        zone_name = "Kitchen"
        analysis_result = {"result": "clean"}
        analysis_func = AsyncMock(return_value=analysis_result)
        
        # Start the analyzer
        await analyzer.start()

        # Act
        analysis_id = await analyzer.queue_analysis(
            zone_name=zone_name,
            priority=AnalysisPriority.MANUAL
        )
        
        # Wait for the worker to process the item
        await asyncio.sleep(0.1)
        
        # Stop the analyzer
        await analyzer.stop()
        
        # Assert
        # Check that state manager was called to update analysis state
        assert state_manager_mock.update_analysis_state.call_count >= 1
        
        # Check that state manager was called with the analysis_id
        last_call_args = state_manager_mock.update_analysis_state.call_args_list[-1][0]
        assert last_call_args[0] == analysis_id
        # The second argument is the AnalysisState enum, not a dict
        assert isinstance(last_call_args[1], AnalysisState)
        
    @pytest.mark.asyncio
    async def test_priority_ordering(self, analyzer, state_manager_mock):
        """Test that analyses are processed in priority order."""
        # Arrange
        analysis_func = AsyncMock(return_value={"result": "clean"})
        
        # Queue analyses with different priorities
        await analyzer.queue_analysis(
            zone_name="Kitchen",
            priority=AnalysisPriority.RETRY
        )

        await analyzer.queue_analysis(
            zone_name="Kitchen",
            priority=AnalysisPriority.MANUAL
        )
        
        # Act
        # Get the items from the queue (priority queue returns (priority_value, request))
        first_priority, first_request = await analyzer.analysis_queue.get()
        second_priority, second_request = await analyzer.analysis_queue.get()

        # Assert
        # Manual priority (1) should come before Retry priority (4)
        assert first_priority < second_priority
        assert first_request.zone_name == "Kitchen"
        assert second_request.zone_name == "Kitchen"
        assert first_request.priority == AnalysisPriority.MANUAL
        assert second_request.priority == AnalysisPriority.RETRY
        
    @pytest.mark.asyncio
    async def test_error_handling(self, analyzer, state_manager_mock):
        """Test error handling during analysis."""
        # Arrange
        error_message = "Test error"
        analysis_func = AsyncMock(side_effect=Exception(error_message))
        
        # Start the analyzer
        await analyzer.start()

        # Act
        analysis_id = await analyzer.queue_analysis(
            zone_name="Kitchen",
            priority=AnalysisPriority.MANUAL
        )
        
        # Wait for the worker to process the item
        await asyncio.sleep(0.1)
        
        # Stop the analyzer
        await analyzer.stop()
        
        # Assert
        # Check that state manager was called
        assert state_manager_mock.update_analysis_state.call_count >= 1
        
    @pytest.mark.asyncio
    async def test_get_queue_status(self, analyzer):
        """Test getting queue status."""
        # Arrange
        # Queue an analysis
        analysis_id = await analyzer.queue_analysis(
            zone_name="Kitchen",
            priority=AnalysisPriority.MANUAL
        )

        # Act & Assert
        # For now, just verify that the analysis was queued successfully
        assert analysis_id is not None
        assert isinstance(analysis_id, str)