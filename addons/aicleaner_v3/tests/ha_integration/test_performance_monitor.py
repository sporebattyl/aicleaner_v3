"""
Test suite for AICleaner v3 Performance Monitor
Tests performance tracking and HA event bus integration.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import time
import asyncio
from homeassistant.core import HomeAssistant

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ha_integration.performance_monitor import PerformanceMonitor


class TestPerformanceMonitor:
    """Test cases for PerformanceMonitor."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = Mock(spec=HomeAssistant)
        hass.bus = Mock()
        hass.bus.async_fire = Mock()
        return hass

    @pytest.fixture
    def performance_monitor(self, mock_hass):
        """Create performance monitor instance."""
        return PerformanceMonitor(mock_hass, "aicleaner_v3")

    def test_performance_monitor_initialization(self, performance_monitor, mock_hass):
        """Test performance monitor initialization."""
        assert performance_monitor.hass == mock_hass
        assert performance_monitor.domain == "aicleaner_v3"

    def test_fire_performance_event(self, performance_monitor, mock_hass):
        """Test firing performance event."""
        operation = "test_operation"
        duration = 1.234567
        
        performance_monitor.fire_performance_event(operation, duration)
        
        expected_event_data = {
            "operation": operation,
            "duration_ms": 1234.57,
        }
        
        mock_hass.bus.async_fire.assert_called_once_with(
            "aicleaner_v3_performance", expected_event_data
        )

    def test_fire_performance_event_rounding(self, performance_monitor, mock_hass):
        """Test duration rounding in performance event."""
        test_cases = [
            (0.001234, 1.23),
            (0.000001, 0.00),
            (1.999999, 2000.00),
            (0.1, 100.00)
        ]
        
        for duration, expected_ms in test_cases:
            mock_hass.bus.async_fire.reset_mock()
            
            performance_monitor.fire_performance_event("test", duration)
            
            call_args = mock_hass.bus.async_fire.call_args
            event_data = call_args[0][1]
            assert event_data["duration_ms"] == expected_ms

    def test_measure_performance_decorator(self, performance_monitor):
        """Test performance measurement decorator."""
        @performance_monitor.measure_performance("test_operation")
        async def test_function():
            await asyncio.sleep(0.001)  # Small delay
            return "result"
        
        # Test that decorator returns a callable
        assert callable(test_function)

    @pytest.mark.asyncio
    async def test_measure_performance_execution(self, performance_monitor, mock_hass):
        """Test performance measurement during execution."""
        @performance_monitor.measure_performance("test_operation")
        async def test_function():
            await asyncio.sleep(0.001)  # Small delay
            return "test_result"
        
        result = await test_function()
        
        # Verify function result
        assert result == "test_result"
        
        # Verify performance event was fired
        mock_hass.bus.async_fire.assert_called_once()
        
        call_args = mock_hass.bus.async_fire.call_args
        event_name = call_args[0][0]
        event_data = call_args[0][1]
        
        assert event_name == "aicleaner_v3_performance"
        assert event_data["operation"] == "test_operation"
        assert event_data["duration_ms"] > 0

    @pytest.mark.asyncio
    async def test_measure_performance_with_exception(self, performance_monitor, mock_hass):
        """Test performance measurement when function raises exception."""
        @performance_monitor.measure_performance("test_operation")
        async def failing_function():
            await asyncio.sleep(0.001)
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            await failing_function()
        
        # Verify performance event was still fired
        mock_hass.bus.async_fire.assert_called_once()
        
        call_args = mock_hass.bus.async_fire.call_args
        event_data = call_args[0][1]
        
        assert event_data["operation"] == "test_operation"
        assert event_data["duration_ms"] > 0

    @pytest.mark.asyncio
    async def test_measure_performance_multiple_calls(self, performance_monitor, mock_hass):
        """Test performance measurement with multiple function calls."""
        @performance_monitor.measure_performance("test_operation")
        async def test_function():
            await asyncio.sleep(0.001)
            return "result"
        
        # Call function multiple times
        for i in range(3):
            await test_function()
        
        # Verify performance events were fired for each call
        assert mock_hass.bus.async_fire.call_count == 3
        
        # Verify each event has correct operation name
        for call in mock_hass.bus.async_fire.call_args_list:
            event_data = call[0][1]
            assert event_data["operation"] == "test_operation"

    @pytest.mark.asyncio
    async def test_measure_performance_different_operations(self, performance_monitor, mock_hass):
        """Test performance measurement with different operation names."""
        @performance_monitor.measure_performance("operation_1")
        async def function_1():
            await asyncio.sleep(0.001)
            return "result_1"
        
        @performance_monitor.measure_performance("operation_2")
        async def function_2():
            await asyncio.sleep(0.001)
            return "result_2"
        
        await function_1()
        await function_2()
        
        assert mock_hass.bus.async_fire.call_count == 2
        
        # Check operation names
        calls = mock_hass.bus.async_fire.call_args_list
        assert calls[0][0][1]["operation"] == "operation_1"
        assert calls[1][0][1]["operation"] == "operation_2"

    def test_measure_performance_preserves_function_metadata(self, performance_monitor):
        """Test that decorator preserves function metadata."""
        @performance_monitor.measure_performance("test_operation")
        async def test_function():
            """Test function docstring."""
            return "result"
        
        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test function docstring."

    @pytest.mark.asyncio
    async def test_measure_performance_with_args_kwargs(self, performance_monitor, mock_hass):
        """Test performance measurement with function arguments."""
        @performance_monitor.measure_performance("test_operation")
        async def test_function(arg1, arg2, kwarg1=None, kwarg2=None):
            await asyncio.sleep(0.001)
            return f"{arg1}-{arg2}-{kwarg1}-{kwarg2}"
        
        result = await test_function("a", "b", kwarg1="c", kwarg2="d")
        
        assert result == "a-b-c-d"
        mock_hass.bus.async_fire.assert_called_once()

    @pytest.mark.asyncio
    async def test_performance_event_timing_accuracy(self, performance_monitor, mock_hass):
        """Test that performance timing is reasonably accurate."""
        expected_sleep_time = 0.01  # 10ms
        
        @performance_monitor.measure_performance("timing_test")
        async def timed_function():
            await asyncio.sleep(expected_sleep_time)
            return "result"
        
        await timed_function()
        
        call_args = mock_hass.bus.async_fire.call_args
        event_data = call_args[0][1]
        measured_ms = event_data["duration_ms"]
        
        # Should be roughly the expected time (with some tolerance)
        expected_ms = expected_sleep_time * 1000
        assert measured_ms >= expected_ms * 0.8  # Allow 20% variance below
        assert measured_ms <= expected_ms * 2.0  # Allow 100% variance above

    def test_multiple_domains(self, mock_hass):
        """Test performance monitors with different domains."""
        monitor1 = PerformanceMonitor(mock_hass, "domain1")
        monitor2 = PerformanceMonitor(mock_hass, "domain2")
        
        monitor1.fire_performance_event("test_op", 0.1)
        monitor2.fire_performance_event("test_op", 0.2)
        
        assert mock_hass.bus.async_fire.call_count == 2
        
        calls = mock_hass.bus.async_fire.call_args_list
        assert calls[0][0][0] == "domain1_performance"
        assert calls[1][0][0] == "domain2_performance"

    @pytest.mark.asyncio
    async def test_concurrent_performance_measurements(self, performance_monitor, mock_hass):
        """Test concurrent performance measurements."""
        @performance_monitor.measure_performance("concurrent_op")
        async def concurrent_function(delay):
            await asyncio.sleep(delay)
            return f"result_{delay}"
        
        # Run multiple concurrent operations
        tasks = [
            concurrent_function(0.001),
            concurrent_function(0.002),
            concurrent_function(0.003)
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert mock_hass.bus.async_fire.call_count == 3
        
        # All should have the same operation name
        for call in mock_hass.bus.async_fire.call_args_list:
            event_data = call[0][1]
            assert event_data["operation"] == "concurrent_op"


class TestPerformanceMonitorIntegration:
    """Integration tests for PerformanceMonitor."""

    @pytest.mark.asyncio
    async def test_real_world_scenario(self, mock_hass):
        """Test realistic usage scenario."""
        monitor = PerformanceMonitor(mock_hass, "aicleaner_v3")
        
        # Simulate various operations
        @monitor.measure_performance("image_analysis")
        async def analyze_image():
            await asyncio.sleep(0.001)
            return {"objects": ["chair", "table"]}
        
        @monitor.measure_performance("task_generation")
        async def generate_tasks():
            await asyncio.sleep(0.001)
            return ["clean table", "organize chair"]
        
        @monitor.measure_performance("notification_send")
        async def send_notification():
            await asyncio.sleep(0.001)
            return "sent"
        
        # Execute operations
        await analyze_image()
        await generate_tasks()
        await send_notification()
        
        # Verify all events were fired
        assert mock_hass.bus.async_fire.call_count == 3
        
        # Check operation names
        calls = mock_hass.bus.async_fire.call_args_list
        operations = [call[0][1]["operation"] for call in calls]
        
        assert "image_analysis" in operations
        assert "task_generation" in operations
        assert "notification_send" in operations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])