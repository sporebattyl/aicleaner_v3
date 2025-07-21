"""
Phase 3B: Zone Performance Monitoring
Real-time monitoring and analytics for zone performance and health.
"""

import logging
import asyncio
import statistics
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, deque

from .models import Zone, Device, Rule, ZonePerformanceMetrics
from .logger import setup_logger, ZoneMetricsLogger
from .utils import exponential_moving_average, calculate_weighted_average, format_duration


@dataclass
class PerformanceAlert:
    """Performance alert container."""
    zone_id: str
    alert_type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str
    timestamp: datetime
    metric_value: float
    threshold: float
    suggested_action: Optional[str] = None


@dataclass
class MetricSnapshot:
    """Point-in-time metric snapshot."""
    timestamp: datetime
    zone_id: str
    metric_name: str
    value: float
    metadata: Dict[str, Any]


class ZonePerformanceMonitor:
    """
    Real-time performance monitoring and analytics for zones.
    
    Provides comprehensive monitoring of zone health, device performance,
    automation efficiency, and energy consumption with alerting capabilities.
    """
    
    def __init__(self, hass, config: Dict[str, Any]):
        """
        Initialize performance monitor.
        
        Args:
            hass: Home Assistant instance
            config: Configuration dictionary
        """
        self.hass = hass
        self.config = config
        self.logger = setup_logger(__name__)
        self.metrics_logger = ZoneMetricsLogger(self.logger)
        
        # Monitoring configuration
        self.monitoring_interval = config.get('monitoring_interval_seconds', 60)
        self.alert_cooldown_seconds = config.get('alert_cooldown_seconds', 300)
        self.metric_retention_hours = config.get('metric_retention_hours', 24)
        
        # Performance thresholds
        self.thresholds = {
            'device_response_time_ms': 1000,
            'rule_success_rate': 0.8,
            'zone_health_score': 0.7,
            'energy_consumption_watts': 1000,
            'device_availability': 0.9
        }
        
        # Data storage
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.alert_history: Dict[str, List[PerformanceAlert]] = defaultdict(list)
        self.last_alert_times: Dict[str, datetime] = {}
        
        # Monitoring tasks
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
        
        # Statistics tracking
        self.performance_stats: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        self.logger.info("Zone Performance Monitor initialized")
    
    async def start_zone_monitoring(self, zone: Zone) -> None:
        """
        Start monitoring for a specific zone.
        
        Args:
            zone: Zone to monitor
        """
        zone_id = zone.id
        
        if zone_id in self.monitoring_tasks:
            self.logger.warning(f"Monitoring already started for zone '{zone.name}'")
            return
        
        # Create monitoring task
        task = asyncio.create_task(self._monitor_zone_loop(zone))
        self.monitoring_tasks[zone_id] = task
        
        self.logger.info(f"Started monitoring for zone '{zone.name}'")
    
    async def stop_zone_monitoring(self, zone_id: str) -> None:
        """
        Stop monitoring for a specific zone.
        
        Args:
            zone_id: Zone identifier
        """
        if zone_id not in self.monitoring_tasks:
            self.logger.warning(f"No monitoring task found for zone '{zone_id}'")
            return
        
        # Cancel monitoring task
        task = self.monitoring_tasks[zone_id]
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        del self.monitoring_tasks[zone_id]
        
        self.logger.info(f"Stopped monitoring for zone '{zone_id}'")
    
    async def update_zone_metrics(self, zone: Zone) -> None:
        """
        Update performance metrics for a zone.
        
        Args:
            zone: Zone to update metrics for
        """
        try:
            timestamp = datetime.now()
            
            # Collect current metrics
            metrics = await self._collect_zone_metrics(zone)
            
            # Store metric snapshots
            for metric_name, value in metrics.items():
                snapshot = MetricSnapshot(
                    timestamp=timestamp,
                    zone_id=zone.id,
                    metric_name=metric_name,
                    value=value,
                    metadata={'zone_name': zone.name}
                )
                self._store_metric_snapshot(snapshot)
            
            # Update zone performance metrics
            await self._update_zone_performance_metrics(zone, metrics)
            
            # Check for alerts
            await self._check_performance_alerts(zone, metrics)
            
            # Log metrics
            self.metrics_logger.log_zone_metrics(zone.id, zone.name, metrics)
            
            self.logger.debug(f"Updated metrics for zone '{zone.name}'")
        
        except Exception as e:
            self.logger.error(f"Error updating metrics for zone '{zone.name}': {e}")
    
    async def _monitor_zone_loop(self, zone: Zone) -> None:
        """Main monitoring loop for a zone."""
        zone_id = zone.id
        
        while True:
            try:
                # Update metrics
                await self.update_zone_metrics(zone)
                
                # Update performance statistics
                await self._update_performance_statistics(zone)
                
                # Sleep until next monitoring interval
                await asyncio.sleep(self.monitoring_interval)
            
            except asyncio.CancelledError:
                self.logger.info(f"Monitoring cancelled for zone '{zone.name}'")
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop for zone '{zone.name}': {e}")
                await asyncio.sleep(30)  # Short wait before retrying
    
    async def _collect_zone_metrics(self, zone: Zone) -> Dict[str, float]:
        """Collect current performance metrics for a zone."""
        metrics = {}
        
        try:
            # Device metrics
            active_devices = zone.get_active_devices()
            total_devices = len(zone.devices)
            
            metrics['total_devices'] = float(total_devices)
            metrics['active_devices'] = float(len(active_devices))
            metrics['device_availability'] = len(active_devices) / max(total_devices, 1)
            
            # Response time metrics
            if active_devices:
                response_times = [d.response_time_ms for d in active_devices if d.response_time_ms]
                if response_times:
                    metrics['avg_response_time_ms'] = statistics.mean(response_times)
                    metrics['max_response_time_ms'] = max(response_times)
                    metrics['min_response_time_ms'] = min(response_times)
                else:
                    metrics['avg_response_time_ms'] = 0.0
            else:
                metrics['avg_response_time_ms'] = 0.0
            
            # Device reliability
            if zone.devices:
                reliability_scores = [d.reliability_score for d in zone.devices]
                metrics['avg_device_reliability'] = statistics.mean(reliability_scores)
                metrics['min_device_reliability'] = min(reliability_scores)
            else:
                metrics['avg_device_reliability'] = 1.0
                metrics['min_device_reliability'] = 1.0
            
            # Rule performance metrics
            enabled_rules = zone.get_enabled_rules()
            metrics['total_rules'] = float(len(zone.rules))
            metrics['enabled_rules'] = float(len(enabled_rules))
            
            if enabled_rules:
                success_rates = [r.success_rate for r in enabled_rules]
                execution_times = [r.average_execution_time_ms for r in enabled_rules]
                
                metrics['avg_rule_success_rate'] = statistics.mean(success_rates)
                metrics['min_rule_success_rate'] = min(success_rates)
                metrics['avg_rule_execution_time_ms'] = statistics.mean(execution_times)
                metrics['max_rule_execution_time_ms'] = max(execution_times)
            else:
                metrics['avg_rule_success_rate'] = 1.0
                metrics['min_rule_success_rate'] = 1.0
                metrics['avg_rule_execution_time_ms'] = 0.0
                metrics['max_rule_execution_time_ms'] = 0.0
            
            # Energy consumption
            metrics['total_energy_consumption'] = zone.calculate_energy_consumption()
            
            # Overall health score
            metrics['zone_health_score'] = zone.get_zone_health_score()
            
            # Error tracking
            device_errors = sum(d.error_count for d in zone.devices)
            metrics['total_device_errors'] = float(device_errors)
            
            # Activity metrics
            metrics['automation_activity'] = sum(r.execution_count for r in zone.rules)
            
        except Exception as e:
            self.logger.error(f"Error collecting metrics for zone '{zone.name}': {e}")
        
        return metrics
    
    async def _update_zone_performance_metrics(self, zone: Zone, metrics: Dict[str, float]) -> None:
        """Update zone's performance metrics object."""
        try:
            perf_metrics = zone.performance_metrics
            
            # Update device metrics
            perf_metrics.total_devices = int(metrics.get('total_devices', 0))
            perf_metrics.active_devices = int(metrics.get('active_devices', 0))
            perf_metrics.average_response_time_ms = metrics.get('avg_response_time_ms', 0.0)
            
            # Update rule metrics
            perf_metrics.total_rules = int(metrics.get('total_rules', 0))
            perf_metrics.active_rules = int(metrics.get('enabled_rules', 0))
            perf_metrics.rules_success_rate = metrics.get('avg_rule_success_rate', 1.0)
            
            # Update energy metrics
            perf_metrics.total_power_consumption = metrics.get('total_energy_consumption', 0.0)
            
            # Calculate energy efficiency score
            energy_consumption = metrics.get('total_energy_consumption', 0.0)
            device_count = max(metrics.get('active_devices', 1), 1)
            consumption_per_device = energy_consumption / device_count
            
            # Normalize energy efficiency (lower consumption = higher efficiency)
            perf_metrics.energy_efficiency_score = max(0.0, 1.0 - (consumption_per_device / 100.0))
            
            # Update optimization score
            perf_metrics.optimization_score = metrics.get('zone_health_score', 0.0)
            
            # Update activity and satisfaction scores
            perf_metrics.daily_activity_score = min(1.0, metrics.get('automation_activity', 0) / 100.0)
            
            # Calculate user satisfaction based on reliability and performance
            satisfaction_factors = [
                metrics.get('avg_device_reliability', 1.0),
                metrics.get('avg_rule_success_rate', 1.0),
                1.0 - min(1.0, metrics.get('avg_response_time_ms', 0) / 2000.0)  # Penalize slow responses
            ]
            perf_metrics.user_satisfaction_score = calculate_weighted_average(satisfaction_factors)
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics for zone '{zone.name}': {e}")
    
    async def _check_performance_alerts(self, zone: Zone, metrics: Dict[str, float]) -> None:
        """Check metrics against thresholds and generate alerts."""
        try:
            current_time = datetime.now()
            
            # Check each threshold
            for metric_name, threshold in self.thresholds.items():
                if metric_name not in metrics:
                    continue
                
                metric_value = metrics[metric_name]
                alert_key = f"{zone.id}_{metric_name}"
                
                # Check cooldown
                if (alert_key in self.last_alert_times and 
                    (current_time - self.last_alert_times[alert_key]).total_seconds() < self.alert_cooldown_seconds):
                    continue
                
                # Determine if alert should be triggered
                should_alert = False
                severity = 'low'
                
                if metric_name in ['device_response_time_ms', 'energy_consumption_watts']:
                    # Higher values are bad
                    if metric_value > threshold * 2:
                        should_alert = True
                        severity = 'critical'
                    elif metric_value > threshold * 1.5:
                        should_alert = True
                        severity = 'high'
                    elif metric_value > threshold:
                        should_alert = True
                        severity = 'medium'
                        
                else:
                    # Lower values are bad (success rates, health scores, etc.)
                    if metric_value < threshold * 0.5:
                        should_alert = True
                        severity = 'critical'
                    elif metric_value < threshold * 0.7:
                        should_alert = True
                        severity = 'high'
                    elif metric_value < threshold:
                        should_alert = True
                        severity = 'medium'
                
                if should_alert:
                    alert = await self._create_performance_alert(
                        zone, metric_name, metric_value, threshold, severity
                    )
                    await self._handle_performance_alert(alert)
                    self.last_alert_times[alert_key] = current_time
        
        except Exception as e:
            self.logger.error(f"Error checking alerts for zone '{zone.name}': {e}")
    
    async def _create_performance_alert(self, zone: Zone, metric_name: str, 
                                      value: float, threshold: float, severity: str) -> PerformanceAlert:
        """Create a performance alert."""
        
        # Generate appropriate message and suggested action
        if metric_name == 'device_response_time_ms':
            message = f"High device response time: {value:.1f}ms (threshold: {threshold}ms)"
            suggested_action = "Check device connectivity and network performance"
        elif metric_name == 'rule_success_rate':
            message = f"Low rule success rate: {value:.1%} (threshold: {threshold:.1%})"
            suggested_action = "Review rule conditions and device availability"
        elif metric_name == 'zone_health_score':
            message = f"Zone health degraded: {value:.2f} (threshold: {threshold})"
            suggested_action = "Check device status and rule performance"
        elif metric_name == 'energy_consumption_watts':
            message = f"High energy consumption: {value:.1f}W (threshold: {threshold}W)"
            suggested_action = "Review device power usage and optimization settings"
        elif metric_name == 'device_availability':
            message = f"Low device availability: {value:.1%} (threshold: {threshold:.1%})"
            suggested_action = "Check device connectivity and power status"
        else:
            message = f"{metric_name}: {value} (threshold: {threshold})"
            suggested_action = "Review zone configuration"
        
        return PerformanceAlert(
            zone_id=zone.id,
            alert_type=metric_name,
            severity=severity,
            message=message,
            timestamp=datetime.now(),
            metric_value=value,
            threshold=threshold,
            suggested_action=suggested_action
        )
    
    async def _handle_performance_alert(self, alert: PerformanceAlert) -> None:
        """Handle a performance alert."""
        try:
            # Store alert in history
            self.alert_history[alert.zone_id].append(alert)
            
            # Keep only recent alerts
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.alert_history[alert.zone_id] = [
                a for a in self.alert_history[alert.zone_id] 
                if a.timestamp > cutoff_time
            ]
            
            # Log alert
            log_level = {
                'low': logging.INFO,
                'medium': logging.WARNING,
                'high': logging.WARNING,
                'critical': logging.ERROR
            }.get(alert.severity, logging.INFO)
            
            self.logger.log(
                log_level,
                f"Performance Alert [{alert.severity.upper()}]: {alert.message}",
                extra={
                    'zone_id': alert.zone_id,
                    'alert_type': alert.alert_type,
                    'severity': alert.severity,
                    'metric_value': alert.metric_value,
                    'threshold': alert.threshold,
                    'suggested_action': alert.suggested_action
                }
            )
            
            # Notify registered callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"Error in alert callback: {e}")
        
        except Exception as e:
            self.logger.error(f"Error handling performance alert: {e}")
    
    def _store_metric_snapshot(self, snapshot: MetricSnapshot) -> None:
        """Store a metric snapshot in history."""
        key = f"{snapshot.zone_id}_{snapshot.metric_name}"
        self.metric_history[key].append(snapshot)
        
        # Clean old data
        cutoff_time = datetime.now() - timedelta(hours=self.metric_retention_hours)
        while (self.metric_history[key] and 
               self.metric_history[key][0].timestamp < cutoff_time):
            self.metric_history[key].popleft()
    
    async def _update_performance_statistics(self, zone: Zone) -> None:
        """Update performance statistics for trend analysis."""
        try:
            zone_id = zone.id
            
            if zone_id not in self.performance_stats:
                self.performance_stats[zone_id] = {
                    'uptime_start': datetime.now(),
                    'total_monitoring_time': 0.0,
                    'alert_counts': defaultdict(int),
                    'metric_trends': defaultdict(list)
                }
            
            stats = self.performance_stats[zone_id]
            
            # Update monitoring time
            stats['total_monitoring_time'] = (
                datetime.now() - stats['uptime_start']
            ).total_seconds()
            
            # Update metric trends
            for metric_name in ['zone_health_score', 'avg_response_time_ms', 'total_energy_consumption']:
                key = f"{zone_id}_{metric_name}"
                if key in self.metric_history:
                    recent_values = [s.value for s in list(self.metric_history[key])[-10:]]
                    if recent_values:
                        stats['metric_trends'][metric_name] = {
                            'current': recent_values[-1],
                            'average': statistics.mean(recent_values),
                            'trend': 'stable'  # Would calculate actual trend
                        }
        
        except Exception as e:
            self.logger.error(f"Error updating performance statistics: {e}")
    
    def get_zone_metrics_history(self, zone_id: str, metric_name: str, 
                                hours_back: int = 1) -> List[MetricSnapshot]:
        """Get historical metrics for a zone."""
        key = f"{zone_id}_{metric_name}"
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        if key not in self.metric_history:
            return []
        
        return [s for s in self.metric_history[key] if s.timestamp > cutoff_time]
    
    def get_zone_alerts(self, zone_id: str, hours_back: int = 24) -> List[PerformanceAlert]:
        """Get recent alerts for a zone."""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        if zone_id not in self.alert_history:
            return []
        
        return [a for a in self.alert_history[zone_id] if a.timestamp > cutoff_time]
    
    def get_performance_summary(self, zone_id: str) -> Dict[str, Any]:
        """Get performance summary for a zone."""
        summary = {
            'zone_id': zone_id,
            'monitoring_duration': 0.0,
            'total_alerts': 0,
            'recent_alerts': 0,
            'alert_breakdown': defaultdict(int),
            'metric_trends': {},
            'health_status': 'unknown'
        }
        
        try:
            # Get monitoring statistics
            if zone_id in self.performance_stats:
                stats = self.performance_stats[zone_id]
                summary['monitoring_duration'] = stats['total_monitoring_time']
                summary['metric_trends'] = dict(stats['metric_trends'])
            
            # Get alert statistics
            if zone_id in self.alert_history:
                all_alerts = self.alert_history[zone_id]
                summary['total_alerts'] = len(all_alerts)
                
                # Recent alerts (last hour)
                recent_cutoff = datetime.now() - timedelta(hours=1)
                recent_alerts = [a for a in all_alerts if a.timestamp > recent_cutoff]
                summary['recent_alerts'] = len(recent_alerts)
                
                # Alert breakdown by severity
                for alert in all_alerts:
                    summary['alert_breakdown'][alert.severity] += 1
            
            # Determine overall health status
            if summary['recent_alerts'] == 0:
                summary['health_status'] = 'healthy'
            elif summary['recent_alerts'] < 3:
                summary['health_status'] = 'warning'
            else:
                summary['health_status'] = 'critical'
        
        except Exception as e:
            self.logger.error(f"Error generating performance summary: {e}")
        
        return summary
    
    def register_alert_callback(self, callback: Callable[[PerformanceAlert], None]) -> None:
        """Register callback for performance alerts."""
        self.alert_callbacks.append(callback)
    
    def set_threshold(self, metric_name: str, threshold: float) -> None:
        """Set custom threshold for a metric."""
        self.thresholds[metric_name] = threshold
        self.logger.info(f"Updated threshold for {metric_name}: {threshold}")


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    from .models import Zone, Device, Rule, DeviceType
    
    async def test_performance_monitor():
        """Test performance monitoring functionality."""
        
        # Mock Home Assistant object
        class MockHass:
            def __init__(self):
                self.data = {}
        
        hass = MockHass()
        config = {
            'monitoring_interval_seconds': 5,
            'alert_cooldown_seconds': 10
        }
        
        monitor = ZonePerformanceMonitor(hass, config)
        
        # Create test zone with some issues
        zone = Zone(
            id='test_zone',
            name='Test Zone',
            devices=[
                Device(
                    id='slow_device',
                    name='Slow Device',
                    type=DeviceType.LIGHT,
                    response_time_ms=1500,  # Slow response
                    reliability_score=0.6   # Low reliability
                ),
                Device(
                    id='good_device',
                    name='Good Device',
                    type=DeviceType.SENSOR,
                    response_time_ms=200,
                    reliability_score=0.95
                )
            ],
            rules=[
                Rule(
                    id='failing_rule',
                    name='Failing Rule',
                    condition='test',
                    action='test',
                    success_rate=0.5,  # Low success rate
                    execution_count=10
                )
            ]
        )
        
        # Test metric collection
        metrics = await monitor._collect_zone_metrics(zone)
        print(f"Collected metrics: {metrics}")
        
        # Test alert checking
        await monitor._check_performance_alerts(zone, metrics)
        
        # Test monitoring start/stop
        await monitor.start_zone_monitoring(zone)
        await asyncio.sleep(2)  # Let it run briefly
        await monitor.stop_zone_monitoring(zone.id)
        
        # Get performance summary
        summary = monitor.get_performance_summary(zone.id)
        print(f"Performance summary: {summary}")
        
        print("Performance monitor test completed!")
    
    # Run test
    asyncio.run(test_performance_monitor())