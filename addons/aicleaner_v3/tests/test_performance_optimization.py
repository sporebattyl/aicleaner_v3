"""
Performance Optimization Tests for AICleaner Phase 3C.2
Comprehensive testing of performance optimization features including quantization,
resource monitoring, benchmarking, and auto-tuning.
"""

import pytest
import asyncio
import time
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

# Import the components we're testing
try:
    from core.local_model_manager import LocalModelManager, OptimizationConfig, QuantizationLevel, CompressionType
    from core.resource_monitor import ResourceMonitor, ResourceMetrics, ResourceAlert, AlertLevel
    from core.alert_manager import AlertManager, AlertRule, AlertInstance, NotificationChannel
    from core.performance_benchmarks import PerformanceBenchmarks, BenchmarkType, BenchmarkStatus
    from integrations.ollama_client import OllamaClient, OptimizationOptions, ModelOptimizer
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    COMPONENTS_AVAILABLE = False
    pytest.skip(f"Performance optimization components not available: {e}", allow_module_level=True)


class TestLocalModelManagerOptimization:
    """Test suite for Local Model Manager optimization features."""

    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Arrange: Mock configuration for testing."""
        return {
            "local_llm": {
                "enabled": True,
                "ollama_host": "localhost:11434",
                "preferred_models": {
                    "vision": "llava:13b",
                    "text": "mistral:7b"
                },
                "resource_limits": {
                    "max_cpu_usage": 80,
                    "max_memory_usage": 4096
                },
                "performance_tuning": {
                    "quantization_level": 4,
                    "batch_size": 1,
                    "timeout_seconds": 120
                }
            },
            "performance_optimization": {
                "quantization": {
                    "enabled": True,
                    "default_level": "dynamic"
                },
                "gpu_acceleration": {
                    "enabled": False
                },
                "auto_optimization": {
                    "enabled": True
                }
            }
        }

    @pytest.fixture
    def temp_data_path(self):
        """Arrange: Temporary directory for test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def model_manager(self, mock_config, temp_data_path):
        """Arrange: Local Model Manager instance for testing."""
        with patch('core.local_model_manager.OllamaClient'):
            manager = LocalModelManager(mock_config)
            manager.data_path = temp_data_path
            return manager

    def test_optimization_config_initialization(self, model_manager):
        """
        Test optimization configuration initialization.
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange - done in fixture
        
        # Act
        config = model_manager.optimization_config
        
        # Assert
        assert isinstance(config, OptimizationConfig)
        assert config.quantization_level == QuantizationLevel.DYNAMIC
        assert config.auto_optimize is True

    @pytest.mark.asyncio
    async def test_model_optimization_workflow(self, model_manager):
        """
        Test complete model inference configuration workflow.
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        model_name = "test_model"
        model_manager.models[model_name] = Mock()
        model_manager.models[model_name].inference_configured = False
        model_manager.models[model_name].status = Mock()
        model_manager.models[model_name].optimization_history = []

        # Create a config that will trigger all methods
        from core.local_model_manager import OptimizationConfig, QuantizationLevel, CompressionType
        config = OptimizationConfig(
            quantization_level=QuantizationLevel.INT8,
            compression_type=CompressionType.GZIP,
            memory_optimization=True
        )

        with patch.object(model_manager, '_set_quantization_preference') as mock_quantization, \
             patch.object(model_manager, '_set_compression_preference') as mock_compression, \
             patch.object(model_manager, '_apply_memory_optimization') as mock_memory:

            # Act
            result = await model_manager.configure_inference_settings(model_name, config)

            # Assert
            assert result is True
            mock_quantization.assert_called_once()
            mock_compression.assert_called_once()
            mock_memory.assert_called_once()
            assert model_manager.models[model_name].inference_configured is True

    @pytest.mark.asyncio
    async def test_optimization_recommendations(self, model_manager):
        """
        Test optimization recommendations generation.
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        model_name = "test_model"
        model_manager.models[model_name] = Mock()
        model_manager.models[model_name].quantization_level = QuantizationLevel.NONE
        model_manager.models[model_name].compression_type = CompressionType.NONE
        model_manager.models[model_name].inference_configured = False
        model_manager.models[model_name].size_gb = 3.0
        model_manager.models[model_name].performance_metrics = {"last_analysis_time": 65}
        
        with patch.object(model_manager, 'get_resource_metrics') as mock_metrics:
            mock_metrics.return_value = Mock(memory_percent=85)
            
            # Act
            recommendations = await model_manager.get_optimization_recommendations(model_name)
            
            # Assert
            assert "model_name" in recommendations
            assert "recommendations" in recommendations
            assert len(recommendations["recommendations"]) > 0
            assert any("memory" in rec["reason"].lower() for rec in recommendations["recommendations"])

    def test_quantization_level_enum(self):
        """
        Test quantization level enumeration.
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange & Act
        levels = list(QuantizationLevel)
        
        # Assert
        assert QuantizationLevel.NONE in levels
        assert QuantizationLevel.INT4 in levels
        assert QuantizationLevel.INT8 in levels
        assert QuantizationLevel.FP16 in levels
        assert QuantizationLevel.DYNAMIC in levels


class TestResourceMonitor:
    """Test suite for Resource Monitor."""

    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Arrange: Mock configuration for resource monitoring."""
        return {
            "performance_optimization": {
                "monitoring": {
                    "enabled": True,
                    "metrics_retention_hours": 24,
                    "alert_thresholds": {
                        "memory_usage_percent": 90,
                        "cpu_usage_percent": 95,
                        "disk_usage_percent": 95
                    }
                }
            }
        }

    @pytest.fixture
    def temp_data_path(self):
        """Arrange: Temporary directory for test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def resource_monitor(self, mock_config, temp_data_path):
        """Arrange: Resource Monitor instance for testing."""
        return ResourceMonitor(mock_config, temp_data_path)

    @pytest.mark.asyncio
    async def test_resource_metrics_collection(self, resource_monitor):
        """
        Test resource metrics collection.
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange - done in fixture
        
        # Act
        metrics = await resource_monitor.get_current_metrics()
        
        # Assert
        assert isinstance(metrics, ResourceMetrics)
        assert metrics.cpu_percent >= 0
        assert metrics.memory_percent >= 0
        assert metrics.timestamp is not None

    @pytest.mark.asyncio
    async def test_monitoring_start_stop(self, resource_monitor):
        """
        Test monitoring start and stop functionality.
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        assert not resource_monitor.monitoring_active
        
        # Act - Start monitoring
        await resource_monitor.start_monitoring(interval=1)
        
        # Assert - Monitoring started
        assert resource_monitor.monitoring_active
        
        # Act - Stop monitoring
        await resource_monitor.stop_monitoring()
        
        # Assert - Monitoring stopped
        assert not resource_monitor.monitoring_active

    def test_alert_threshold_checking(self, resource_monitor):
        """
        Test alert threshold checking logic.
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        high_cpu_metrics = ResourceMetrics(
            timestamp="2024-01-01T00:00:00Z",
            cpu_percent=98.0,  # Above threshold
            cpu_cores=4,
            memory_percent=50.0,
            memory_used_mb=2048,
            memory_available_mb=2048,
            memory_total_mb=4096,
            disk_usage_percent=50.0,
            disk_used_gb=100,
            disk_free_gb=100,
            disk_io_read_mb_per_sec=10,
            disk_io_write_mb_per_sec=5,
            network_sent_mb_per_sec=1,
            network_recv_mb_per_sec=2
        )
        
        # Act
        resource_monitor._check_thresholds(high_cpu_metrics)
        
        # Assert
        assert len(resource_monitor.alerts_history) > 0
        latest_alert = resource_monitor.alerts_history[-1]
        assert "cpu" in latest_alert.message.lower()

    @pytest.mark.asyncio
    async def test_performance_summary_generation(self, resource_monitor):
        """
        Test performance summary generation.
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange - Add some mock metrics
        for i in range(5):
            metrics = ResourceMetrics(
                timestamp=f"2024-01-01T00:0{i}:00Z",
                cpu_percent=50.0 + i,
                cpu_cores=4,
                memory_percent=60.0 + i,
                memory_used_mb=2048,
                memory_available_mb=2048,
                memory_total_mb=4096,
                disk_usage_percent=70.0,
                disk_used_gb=100,
                disk_free_gb=100,
                disk_io_read_mb_per_sec=10,
                disk_io_write_mb_per_sec=5,
                network_sent_mb_per_sec=1,
                network_recv_mb_per_sec=2
            )
            resource_monitor.metrics_history.append(metrics)
        
        # Act
        summary = await resource_monitor.get_performance_summary()
        
        # Assert
        assert "cpu" in summary
        assert "memory" in summary
        assert "disk" in summary
        assert summary["cpu"]["average_percent"] > 0
        assert summary["memory"]["average_percent"] > 0


class TestAlertManager:
    """Test suite for Alert Manager."""

    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Arrange: Mock configuration for alert management."""
        return {
            "performance_optimization": {
                "monitoring": {
                    "alert_thresholds": {
                        "memory_usage_percent": 90,
                        "cpu_usage_percent": 95
                    }
                }
            }
        }

    @pytest.fixture
    def temp_data_path(self):
        """Arrange: Temporary directory for test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def alert_manager(self, mock_config, temp_data_path):
        """Arrange: Alert Manager instance for testing."""
        return AlertManager(mock_config, temp_data_path)

    @pytest.mark.asyncio
    async def test_alert_rule_management(self, alert_manager):
        """
        Test alert rule creation and management.
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        from core.alert_manager import AlertRule, ResourceType, AlertLevel
        
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            resource_type=ResourceType.CPU,
            threshold_value=90.0,
            comparison_operator=">=",
            alert_level=AlertLevel.WARNING
        )
        
        # Act
        alert_manager.add_alert_rule(rule)
        
        # Assert
        assert "test_rule" in alert_manager.alert_rules
        assert alert_manager.alert_rules["test_rule"].name == "Test Rule"

    @pytest.mark.asyncio
    async def test_alert_processing_workflow(self, alert_manager):
        """
        Test complete alert processing workflow.
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        from core.resource_monitor import ResourceAlert, ResourceType, AlertLevel
        
        resource_alert = ResourceAlert(
            alert_id="test_alert",
            timestamp="2024-01-01T00:00:00Z",
            resource_type=ResourceType.CPU,
            alert_level=AlertLevel.WARNING,
            message="High CPU usage detected",
            current_value=96.0,
            threshold_value=95.0
        )
        
        # Act
        await alert_manager.process_resource_alert(resource_alert)
        
        # Assert
        # Should have created an alert instance for the matching rule
        assert len(alert_manager.active_alerts) > 0 or len(alert_manager.alert_history) > 0

    def test_alert_suppression(self, alert_manager):
        """
        Test alert rule suppression functionality.
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        rule_id = "cpu_high_usage"  # Default rule created in initialization
        
        # Act
        alert_manager.suppress_alert_rule(rule_id, duration_minutes=1)
        
        # Assert
        assert rule_id in alert_manager.alert_suppression

    @pytest.mark.asyncio
    async def test_alert_statistics(self, alert_manager):
        """
        Test alert statistics generation.
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange - done in fixture (default rules are created)
        
        # Act
        stats = await alert_manager.get_alert_statistics()
        
        # Assert
        assert "active_alerts" in stats
        assert "total_alerts" in stats
        assert "configured_rules" in stats
        assert stats["configured_rules"] > 0  # Should have default rules


class TestPerformanceBenchmarks:
    """Test suite for Performance Benchmarks."""

    @pytest.fixture
    def temp_data_path(self):
        """Arrange: Temporary directory for test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def benchmarks(self, temp_data_path):
        """Arrange: Performance Benchmarks instance for testing."""
        return PerformanceBenchmarks(temp_data_path)

    @pytest.mark.asyncio
    async def test_latency_benchmark(self, benchmarks):
        """
        Test latency benchmarking functionality.
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        async def test_function():
            await asyncio.sleep(0.01)  # 10ms delay
            return "test_result"
        
        # Act
        result = await benchmarks.benchmark_latency(
            component="test_component",
            operation="test_operation",
            test_func=test_function,
            iterations=3
        )
        
        # Assert
        assert result.benchmark_type == BenchmarkType.LATENCY
        assert result.status == BenchmarkStatus.COMPLETED
        assert "avg_time" in result.metrics
        assert result.metrics["avg_time"] > 0

    @pytest.mark.asyncio
    async def test_comparative_analysis(self, benchmarks):
        """
        Test comparative analysis between implementations.
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        async def fast_function(data):
            await asyncio.sleep(0.001)  # 1ms
            return f"fast_{data}"
        
        async def slow_function(data):
            await asyncio.sleep(0.01)   # 10ms
            return f"slow_{data}"
        
        test_cases = ["case1", "case2"]
        
        # Act
        result = await benchmarks.benchmark_comparative_analysis(
            component="test_component",
            operation="test_operation",
            local_func=fast_function,
            cloud_func=slow_function,
            test_cases=test_cases,
            iterations=2
        )
        
        # Assert
        assert result.benchmark_type == BenchmarkType.COMPARATIVE
        assert result.status == BenchmarkStatus.COMPLETED
        assert "local_avg_time" in result.metrics
        assert "cloud_avg_time" in result.metrics
        assert "performance_ratio" in result.metrics

    @pytest.mark.asyncio
    async def test_load_testing(self, benchmarks):
        """
        Test load testing functionality.
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        call_count = 0
        
        async def load_test_function():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.001)  # Small delay
            return "result"
        
        # Act
        result = await benchmarks.benchmark_load_test(
            component="test_component",
            operation="test_operation",
            test_func=load_test_function,
            concurrent_users=3,
            duration_seconds=2,
            ramp_up_seconds=1
        )
        
        # Assert
        assert result.benchmark_type == BenchmarkType.LOAD_TEST
        assert result.status == BenchmarkStatus.COMPLETED
        assert "total_requests" in result.metrics
        assert "requests_per_second" in result.metrics
        assert result.metrics["total_requests"] > 0

    def test_benchmark_suite_creation(self, benchmarks):
        """
        Test benchmark suite creation and management.
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        suite_configs = [
            {
                'type': 'latency',
                'component': 'test_component',
                'operation': 'test_operation',
                'test_func': lambda: time.sleep(0.001)
            }
        ]
        
        # Act
        suite = benchmarks.create_benchmark_suite(
            suite_id="test_suite",
            name="Test Suite",
            description="Test benchmark suite",
            benchmark_configs=suite_configs
        )
        
        # Assert
        assert suite.suite_id == "test_suite"
        assert suite.name == "Test Suite"
        assert "test_suite" in benchmarks.benchmark_suites
