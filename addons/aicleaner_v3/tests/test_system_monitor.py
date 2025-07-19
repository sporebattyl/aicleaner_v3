"""
Tests for System Monitor
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import asdict

from monitoring.system_monitor import (
    MetricThreshold,
    SystemMetrics,
    AlertRule,
    SystemMonitor,
    get_system_monitor,
    configure_monitoring,
    configure_ha_addon_monitoring
)


class TestMetricThreshold:
    """Test MetricThreshold dataclass."""
    
    def test_metric_threshold_creation(self):
        """Test creating a MetricThreshold."""
        threshold = MetricThreshold(
            warning=70.0,
            critical=90.0,
            name="CPU Usage",
            description="CPU utilization percentage"
        )
        
        assert threshold.warning == 70.0
        assert threshold.critical == 90.0
        assert threshold.name == "CPU Usage"
        assert threshold.description == "CPU utilization percentage"


class TestSystemMetrics:
    """Test SystemMetrics dataclass."""
    
    def test_system_metrics_creation(self):
        """Test creating SystemMetrics."""
        timestamp = datetime.utcnow()
        metrics = SystemMetrics(
            timestamp=timestamp,
            cpu_percent=45.5,
            memory_percent=60.2,
            memory_used_mb=2048.0,
            memory_available_mb=1024.0,
            disk_usage_percent=75.0,
            disk_free_gb=50.0,
            network_bytes_sent=1000000,
            network_bytes_recv=2000000,
            process_count=150,
            load_average_1m=1.5
        )
        
        assert metrics.timestamp == timestamp
        assert metrics.cpu_percent == 45.5
        assert metrics.memory_percent == 60.2
        assert metrics.memory_used_mb == 2048.0
        assert metrics.memory_available_mb == 1024.0
        assert metrics.disk_usage_percent == 75.0
        assert metrics.disk_free_gb == 50.0
        assert metrics.network_bytes_sent == 1000000
        assert metrics.network_bytes_recv == 2000000
        assert metrics.process_count == 150
        assert metrics.load_average_1m == 1.5


class TestAlertRule:
    """Test AlertRule dataclass."""
    
    def test_alert_rule_creation(self):
        """Test creating an AlertRule."""
        rule = AlertRule(
            name="High CPU",
            metric_name="cpu_percent",
            threshold=80.0,
            condition="greater_than",
            duration_seconds=60,
            cooldown_seconds=300,
            enabled=True
        )
        
        assert rule.name == "High CPU"
        assert rule.metric_name == "cpu_percent"
        assert rule.threshold == 80.0
        assert rule.condition == "greater_than"
        assert rule.duration_seconds == 60
        assert rule.cooldown_seconds == 300
        assert rule.enabled is True
        assert rule.last_triggered is None


class TestSystemMonitor:
    """Test SystemMonitor class."""
    
    def test_system_monitor_initialization(self):
        """Test SystemMonitor initialization."""
        monitor = SystemMonitor(
            collection_interval=30,
            retention_hours=24,
            enable_alerts=True
        )
        
        assert monitor.collection_interval == 30
        assert monitor.retention_hours == 24
        assert monitor.enable_alerts is True
        assert len(monitor.metrics_history) == 0
        assert len(monitor.alert_rules) > 0  # Default alert rules
        assert monitor._running is False
    
    def test_default_alert_rules(self):
        """Test that default alert rules are created."""
        monitor = SystemMonitor()
        
        assert len(monitor.alert_rules) == 4  # CPU, Memory, Disk, Load
        
        rule_names = [rule.name for rule in monitor.alert_rules]
        assert "High CPU Usage" in rule_names
        assert "High Memory Usage" in rule_names
        assert "Low Disk Space" in rule_names
        assert "High Load Average" in rule_names
    
    @patch('monitoring.system_monitor.psutil')
    def test_collect_metrics_success(self, mock_psutil):
        """Test successful metrics collection."""
        # Mock psutil functions
        mock_psutil.cpu_percent.return_value = 45.5
        mock_psutil.virtual_memory.return_value = MagicMock(
            percent=65.0, used=2048*1024*1024, available=1024*1024*1024
        )
        mock_psutil.disk_usage.return_value = MagicMock(
            used=50*1024*1024*1024, total=100*1024*1024*1024, 
            free=50*1024*1024*1024
        )
        mock_psutil.net_io_counters.return_value = MagicMock(
            bytes_sent=1000000, bytes_recv=2000000
        )
        mock_psutil.pids.return_value = list(range(150))
        mock_psutil.getloadavg.return_value = [1.5, 1.2, 1.0]
        
        monitor = SystemMonitor()
        metrics = monitor.collect_metrics()
        
        assert isinstance(metrics, SystemMetrics)
        assert metrics.cpu_percent == 45.5
        assert metrics.memory_percent == 65.0
        assert metrics.memory_used_mb == 2048.0
        assert metrics.memory_available_mb == 1024.0
        assert metrics.disk_usage_percent == 50.0
        assert metrics.disk_free_gb == 50.0
        assert metrics.network_bytes_sent == 1000000
        assert metrics.network_bytes_recv == 2000000
        assert metrics.process_count == 150
        assert metrics.load_average_1m == 1.5
    
    @patch('monitoring.system_monitor.psutil')
    def test_collect_metrics_with_errors(self, mock_psutil):
        """Test metrics collection with errors."""
        # Mock psutil to raise exceptions
        mock_psutil.cpu_percent.side_effect = Exception("CPU error")
        
        monitor = SystemMonitor()
        metrics = monitor.collect_metrics()
        
        # Should return empty metrics on error
        assert isinstance(metrics, SystemMetrics)
        assert metrics.cpu_percent == 0.0
        assert metrics.memory_percent == 0.0
    
    def test_check_alerts_disabled(self):
        """Test alert checking when alerts are disabled."""
        monitor = SystemMonitor(enable_alerts=False)
        metrics = SystemMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=95.0,  # High CPU
            memory_percent=50.0,
            memory_used_mb=1000.0,
            memory_available_mb=1000.0,
            disk_usage_percent=50.0,
            disk_free_gb=50.0
        )
        
        # Should not trigger any alerts
        with patch.object(monitor, '_trigger_alert') as mock_trigger:
            monitor.check_alerts(metrics)
            mock_trigger.assert_not_called()
    
    def test_check_alerts_with_violations(self):
        """Test alert checking with threshold violations."""
        monitor = SystemMonitor(enable_alerts=True)
        metrics = SystemMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=95.0,  # Exceeds CPU threshold (85%)
            memory_percent=95.0,  # Exceeds memory threshold (90%)
            memory_used_mb=1000.0,
            memory_available_mb=50.0,
            disk_usage_percent=95.0,  # Exceeds disk threshold (90%)
            disk_free_gb=5.0
        )
        
        with patch.object(monitor, '_trigger_alert') as mock_trigger:
            monitor.check_alerts(metrics)
            
            # Should trigger multiple alerts
            assert mock_trigger.call_count >= 3
    
    def test_check_alerts_cooldown(self):
        """Test alert cooldown functionality."""
        monitor = SystemMonitor(enable_alerts=True)
        
        # Set last triggered time for CPU rule
        cpu_rule = next(rule for rule in monitor.alert_rules if rule.name == "High CPU Usage")
        cpu_rule.last_triggered = datetime.utcnow() - timedelta(seconds=60)  # Recent trigger
        
        metrics = SystemMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=95.0,  # High CPU
            memory_percent=50.0,
            memory_used_mb=1000.0,
            memory_available_mb=1000.0,
            disk_usage_percent=50.0,
            disk_free_gb=50.0
        )
        
        with patch.object(monitor, '_trigger_alert') as mock_trigger:
            monitor.check_alerts(metrics)
            
            # Should not trigger alert due to cooldown
            mock_trigger.assert_not_called()
    
    def test_trigger_alert(self):
        """Test alert triggering."""
        monitor = SystemMonitor()
        rule = AlertRule(
            name="Test Alert",
            metric_name="cpu_percent",
            threshold=80.0,
            condition="greater_than"
        )
        
        metrics = SystemMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=90.0,
            memory_percent=50.0,
            memory_used_mb=1000.0,
            memory_available_mb=1000.0,
            disk_usage_percent=50.0,
            disk_free_gb=50.0
        )
        
        callback_called = False
        callback_data = None
        
        def test_callback(alert_data):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = alert_data
        
        monitor.add_alert_callback(test_callback)
        
        with patch('monitoring.system_monitor.log_security_event') as mock_log:
            monitor._trigger_alert(rule, 90.0, metrics)
            
            assert callback_called
            assert callback_data['alert_name'] == "Test Alert"
            assert callback_data['current_value'] == 90.0
            assert callback_data['threshold'] == 80.0
    
    def test_record_performance(self):
        """Test performance recording."""
        monitor = SystemMonitor()
        
        monitor.record_performance("test_operation", 1.5, status="success")
        
        assert "test_operation" in monitor.performance_metrics
        assert len(monitor.performance_metrics["test_operation"]) == 1
        
        perf_data = monitor.performance_metrics["test_operation"][0]
        assert perf_data["duration"] == 1.5
        assert perf_data["metadata"]["status"] == "success"
    
    def test_get_average_performance(self):
        """Test average performance calculation."""
        monitor = SystemMonitor()
        
        # Record multiple performances
        monitor.record_performance("test_op", 1.0)
        monitor.record_performance("test_op", 2.0)
        monitor.record_performance("test_op", 3.0)
        
        avg = monitor.get_average_performance("test_op")
        assert avg == 2.0
        
        # Test with non-existent operation
        avg = monitor.get_average_performance("nonexistent")
        assert avg is None
    
    def test_update_component_health(self):
        """Test component health updates."""
        monitor = SystemMonitor()
        
        # Test healthy component
        monitor.update_component_health("ai_provider", "healthy", {"status": "ok"})
        
        assert "ai_provider" in monitor.component_health
        assert monitor.component_health["ai_provider"]["status"] == "healthy"
        
        # Test unhealthy component
        with patch('monitoring.system_monitor.log_security_event') as mock_log:
            monitor.update_component_health("database", "error", {"error": "connection failed"})
            
            mock_log.assert_called_once()
            assert monitor.component_health["database"]["status"] == "error"
    
    def test_get_metrics_summary(self):
        """Test metrics summary generation."""
        monitor = SystemMonitor()
        
        # Add some test metrics
        now = datetime.utcnow()
        for i in range(5):
            metrics = SystemMetrics(
                timestamp=now - timedelta(minutes=i*10),
                cpu_percent=50.0 + i * 5,
                memory_percent=60.0 + i * 2,
                memory_used_mb=1000.0,
                memory_available_mb=1000.0,
                disk_usage_percent=70.0,
                disk_free_gb=30.0
            )
            monitor.metrics_history.append(metrics)
        
        summary = monitor.get_metrics_summary(hours=1)
        
        assert summary["period_hours"] == 1
        assert summary["sample_count"] == 5
        assert "averages" in summary
        assert "maximums" in summary
        assert "cpu_percent" in summary["averages"]
        assert "memory_percent" in summary["averages"]
    
    def test_get_health_check(self):
        """Test health check generation."""
        monitor = SystemMonitor()
        
        # Add current metrics
        metrics = SystemMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=45.0,
            memory_percent=65.0,
            memory_used_mb=2000.0,
            memory_available_mb=1000.0,
            disk_usage_percent=75.0,
            disk_free_gb=25.0
        )
        monitor.metrics_history.append(metrics)
        
        health_check = monitor.get_health_check()
        
        assert health_check["status"] == "healthy"
        assert "timestamp" in health_check
        assert "metrics" in health_check
        assert health_check["metrics"]["cpu_percent"] == 45.0
        assert health_check["metrics"]["memory_percent"] == 65.0
    
    def test_get_health_check_with_issues(self):
        """Test health check with system issues."""
        monitor = SystemMonitor()
        
        # Add metrics exceeding thresholds
        metrics = SystemMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=95.0,  # Critical
            memory_percent=85.0,  # Warning
            memory_used_mb=3000.0,
            memory_available_mb=200.0,
            disk_usage_percent=75.0,
            disk_free_gb=25.0
        )
        monitor.metrics_history.append(metrics)
        
        # Add unhealthy component
        monitor.update_component_health("test_comp", "error")
        
        health_check = monitor.get_health_check()
        
        assert health_check["status"] == "critical"
        assert len(health_check["issues"]) >= 2
        assert "CPU Usage" in str(health_check["issues"])
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        monitor = SystemMonitor(collection_interval=1)  # 1 second for testing
        
        # Start monitoring
        task = asyncio.create_task(monitor.start_monitoring())
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        assert monitor._running is True
        
        # Stop monitoring
        monitor.stop_monitoring()
        
        # Wait for task to complete
        try:
            await asyncio.wait_for(task, timeout=2.0)
        except asyncio.TimeoutError:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        assert monitor._running is False


class TestGlobalFunctions:
    """Test global monitoring functions."""
    
    def test_get_system_monitor(self):
        """Test getting global system monitor."""
        # Reset global monitor
        import monitoring.system_monitor
        monitoring.system_monitor._global_monitor = None
        
        monitor = get_system_monitor()
        
        assert isinstance(monitor, SystemMonitor)
        
        # Should return same instance on subsequent calls
        monitor2 = get_system_monitor()
        assert monitor is monitor2
    
    def test_configure_monitoring(self):
        """Test global monitoring configuration."""
        monitor = configure_monitoring(
            collection_interval=45,
            retention_hours=12,
            enable_alerts=False
        )
        
        assert isinstance(monitor, SystemMonitor)
        assert monitor.collection_interval == 45
        assert monitor.retention_hours == 12
        assert monitor.enable_alerts is False
    
    def test_configure_ha_addon_monitoring(self):
        """Test HA addon monitoring configuration."""
        monitor = configure_ha_addon_monitoring()
        
        assert isinstance(monitor, SystemMonitor)
        assert monitor.collection_interval == 60  # Longer for addon
        assert monitor.retention_hours == 12  # Less retention
        assert monitor.enable_alerts is True
        assert len(monitor.alert_callbacks) == 1  # HA alert callback added


class TestIntegrationScenarios:
    """Test integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_monitoring_with_alerts(self):
        """Test monitoring with alert triggering."""
        monitor = SystemMonitor(collection_interval=1, enable_alerts=True)
        
        # Mock metrics collection to return high values
        def mock_collect_metrics():
            return SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_percent=95.0,  # High CPU
                memory_percent=50.0,
                memory_used_mb=1000.0,
                memory_available_mb=1000.0,
                disk_usage_percent=50.0,
                disk_free_gb=50.0
            )
        
        # Track alert callbacks
        alert_triggered = False
        
        def alert_callback(alert_data):
            nonlocal alert_triggered
            alert_triggered = True
        
        monitor.add_alert_callback(alert_callback)
        
        with patch.object(monitor, 'collect_metrics', side_effect=mock_collect_metrics):
            # Start monitoring
            task = asyncio.create_task(monitor.start_monitoring())
            
            # Wait for metrics collection and alert
            await asyncio.sleep(1.5)
            
            # Stop monitoring
            monitor.stop_monitoring()
            
            try:
                await asyncio.wait_for(task, timeout=2.0)
            except asyncio.TimeoutError:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Should have collected metrics and triggered alert
            assert len(monitor.metrics_history) > 0
            assert alert_triggered
    
    def test_performance_tracking_with_slow_operations(self):
        """Test performance tracking with slow operations."""
        monitor = SystemMonitor()
        
        # Record normal operations
        monitor.record_performance("normal_op", 0.1)
        monitor.record_performance("normal_op", 0.12)
        monitor.record_performance("normal_op", 0.08)
        
        # Record slow operation
        with patch('monitoring.system_monitor.log_performance') as mock_log:
            monitor.record_performance("normal_op", 0.5)  # 5x slower than average
            
            # Should log slow operation
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert "normal_op" in args
            assert args[1] == 0.5
            assert kwargs.get('slow_operation') is True