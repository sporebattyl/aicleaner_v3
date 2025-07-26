import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import List, Dict, Any

from core.system_monitor import SystemMonitor, HealthCheckResult


@dataclass
class MockHealthCheckResult:
    """Mock health check result for testing."""
    timestamp: str
    health_score: float
    average_response_time: float
    error_rate: float
    resource_pressure: float
    test_duration: float
    details: Dict[str, Any]
    alerts: List[str]
    critical_alerts: List[str]
    performance_warnings: List[str]


class TestAdaptiveMonitoring(unittest.TestCase):
    """Test suite for adaptive monitoring functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {}

    @patch('core.system_monitor.MONITORING_COMPONENTS_AVAILABLE', True)
    @patch('core.system_monitor.ResourceMonitor')
    @patch('core.system_monitor.AlertManager')
    @patch('core.system_monitor.ProductionMonitor')
    def test_adaptive_monitoring_initialization(self, mock_prod_monitor, mock_alert_manager, mock_resource_monitor):
        """Test that adaptive monitoring is properly initialized."""
        # Arrange & Act
        system_monitor = SystemMonitor(self.config)

        # Assert
        self.assertTrue(system_monitor.adaptive_monitoring_enabled)
        self.assertEqual(system_monitor.current_monitoring_frequency, 60)
        self.assertEqual(system_monitor.stability_counter, 0)
        self.assertEqual(system_monitor.stability_threshold, 10)
        self.assertEqual(system_monitor.min_frequency, 30)
        self.assertEqual(system_monitor.max_frequency, 300)
        self.assertEqual(system_monitor.frequency_increase_factor, 0.8)
        self.assertEqual(system_monitor.frequency_decrease_factor, 1.2)

    @patch('core.system_monitor.MONITORING_COMPONENTS_AVAILABLE', True)
    @patch('core.system_monitor.ResourceMonitor')
    @patch('core.system_monitor.AlertManager')
    @patch('core.system_monitor.ProductionMonitor')
    def test_stability_assessment_stable_system(self, mock_prod_monitor, mock_alert_manager, mock_resource_monitor):
        """Test stability assessment for a stable system."""
        # Arrange
        system_monitor = SystemMonitor(self.config)

        # Act - Test stable system metrics
        is_stable = system_monitor._assess_system_stability(
            health_score=85.0,
            avg_response_time=500.0,
            error_rate=0.02,
            resource_pressure=0.5
        )

        # Assert
        self.assertTrue(is_stable)

    @patch('core.system_monitor.MONITORING_COMPONENTS_AVAILABLE', True)
    @patch('core.system_monitor.ResourceMonitor')
    @patch('core.system_monitor.AlertManager')
    @patch('core.system_monitor.ProductionMonitor')
    def test_stability_assessment_unstable_system(self, mock_prod_monitor, mock_alert_manager, mock_resource_monitor):
        """Test stability assessment for an unstable system."""
        # Arrange
        system_monitor = SystemMonitor(self.config)

        # Act - Test unstable system metrics (high error rate)
        is_stable = system_monitor._assess_system_stability(
            health_score=60.0,
            avg_response_time=1500.0,
            error_rate=0.10,
            resource_pressure=0.8
        )

        # Assert
        self.assertFalse(is_stable)

    @patch('core.system_monitor.MONITORING_COMPONENTS_AVAILABLE', True)
    @patch('core.system_monitor.ResourceMonitor')
    @patch('core.system_monitor.AlertManager')
    @patch('core.system_monitor.ProductionMonitor')
    def test_frequency_adjustment_stable_system(self, mock_prod_monitor, mock_alert_manager, mock_resource_monitor):
        """Test frequency adjustment for stable system."""
        # Arrange
        system_monitor = SystemMonitor(self.config)
        system_monitor.logger = MagicMock()
        initial_frequency = system_monitor.current_monitoring_frequency

        # Act - Simulate stable checks until threshold is reached
        for i in range(system_monitor.stability_threshold):
            system_monitor._adjust_monitoring_frequency(is_stable=True)

        # Assert - Frequency should decrease (run less often) after threshold
        self.assertGreater(system_monitor.current_monitoring_frequency, initial_frequency)
        self.assertEqual(system_monitor.stability_counter, 0)  # Counter should reset

    @patch('core.system_monitor.MONITORING_COMPONENTS_AVAILABLE', True)
    @patch('core.system_monitor.ResourceMonitor')
    @patch('core.system_monitor.AlertManager')
    @patch('core.system_monitor.ProductionMonitor')
    def test_frequency_adjustment_unstable_system(self, mock_prod_monitor, mock_alert_manager, mock_resource_monitor):
        """Test frequency adjustment for unstable system."""
        # Arrange
        system_monitor = SystemMonitor(self.config)
        system_monitor.logger = MagicMock()
        initial_frequency = system_monitor.current_monitoring_frequency

        # Act - Simulate unstable system
        system_monitor._adjust_monitoring_frequency(is_stable=False)

        # Assert - Frequency should increase (run more often)
        self.assertLess(system_monitor.current_monitoring_frequency, initial_frequency)
        self.assertEqual(system_monitor.stability_counter, 0)  # Counter should reset

    @patch('core.system_monitor.MONITORING_COMPONENTS_AVAILABLE', True)
    @patch('core.system_monitor.ResourceMonitor')
    @patch('core.system_monitor.AlertManager')
    @patch('core.system_monitor.ProductionMonitor')
    def test_frequency_bounds(self, mock_prod_monitor, mock_alert_manager, mock_resource_monitor):
        """Test that frequency adjustments respect min/max bounds."""
        # Arrange
        system_monitor = SystemMonitor(self.config)
        system_monitor.logger = MagicMock()

        # Act - Force frequency to minimum by simulating many unstable checks
        for _ in range(20):
            system_monitor._adjust_monitoring_frequency(is_stable=False)

        # Assert - Should not go below minimum
        self.assertGreaterEqual(system_monitor.current_monitoring_frequency, system_monitor.min_frequency)

        # Act - Force frequency to maximum by simulating many stable periods
        system_monitor.current_monitoring_frequency = 200  # Start near max
        for _ in range(20):
            for i in range(system_monitor.stability_threshold):
                system_monitor._adjust_monitoring_frequency(is_stable=True)

        # Assert - Should not exceed maximum
        self.assertLessEqual(system_monitor.current_monitoring_frequency, system_monitor.max_frequency)

    @patch('core.system_monitor.MONITORING_COMPONENTS_AVAILABLE', True)
    @patch('core.system_monitor.ResourceMonitor')
    @patch('core.system_monitor.AlertManager')
    @patch('core.system_monitor.ProductionMonitor')
    def test_get_adaptive_monitoring_status(self, mock_prod_monitor, mock_alert_manager, mock_resource_monitor):
        """Test getting adaptive monitoring status."""
        # Arrange
        system_monitor = SystemMonitor(self.config)

        # Act
        status = system_monitor.get_adaptive_monitoring_status()

        # Assert
        self.assertIsInstance(status, dict)
        self.assertIn('adaptive_monitoring_enabled', status)
        self.assertIn('current_frequency', status)
        self.assertIn('stability_counter', status)
        self.assertIn('monitoring_active', status)
        self.assertTrue(status['adaptive_monitoring_enabled'])
        self.assertEqual(status['current_frequency'], 60)
        self.assertEqual(status['stability_counter'], 0)

    @patch('core.system_monitor.MONITORING_COMPONENTS_AVAILABLE', True)
    @patch('core.system_monitor.ResourceMonitor')
    @patch('core.system_monitor.AlertManager')
    @patch('core.system_monitor.ProductionMonitor')
    def test_adaptive_monitoring_loop_integration(self, mock_prod_monitor, mock_alert_manager, mock_resource_monitor):
        """Test the adaptive monitoring loop integration."""
        # Arrange
        system_monitor = SystemMonitor(self.config)
        system_monitor.logger = MagicMock()

        # Mock the health check to return stable results
        mock_health_result = MockHealthCheckResult(
            timestamp="2024-01-01T00:00:00Z",
            health_score=85.0,
            average_response_time=500.0,
            error_rate=0.02,
            resource_pressure=0.5,
            test_duration=30.0,
            details={},
            alerts=[],
            critical_alerts=[],
            performance_warnings=[]
        )
        system_monitor.run_health_check = AsyncMock(return_value=mock_health_result)

        async def run_test():
            # Act - Start monitoring briefly
            system_monitor.monitoring_active = True

            # Create the adaptive monitoring task
            task = asyncio.create_task(system_monitor._adaptive_monitoring_loop())

            # Let it run for a short time
            await asyncio.sleep(0.1)

            # Stop monitoring
            system_monitor.monitoring_active = False

            # Wait for task to complete
            try:
                await asyncio.wait_for(task, timeout=1.0)
            except asyncio.TimeoutError:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Assert - Health check should have been called
            system_monitor.run_health_check.assert_called()

        # Run the async test
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()