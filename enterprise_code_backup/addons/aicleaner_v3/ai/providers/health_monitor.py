"""
Health Monitor for AI Providers
Phase 2A: AI Model Provider Optimization

Provides comprehensive health monitoring with proactive checks, automated failover,
and performance tracking for AI providers.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Callable
import statistics


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthMetric:
    """Individual health metric"""
    name: str
    value: float
    threshold_warning: float
    threshold_critical: float
    unit: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def status(self) -> HealthStatus:
        """Get status based on thresholds"""
        if self.value >= self.threshold_critical:
            return HealthStatus.CRITICAL
        elif self.value >= self.threshold_warning:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY


@dataclass
class HealthAlert:
    """Health alert"""
    provider: str
    metric: str
    status: HealthStatus
    message: str
    value: float
    threshold: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved: bool = False
    resolved_at: Optional[str] = None


@dataclass
class HealthReport:
    """Comprehensive health report"""
    provider: str
    overall_status: HealthStatus
    metrics: Dict[str, HealthMetric]
    alerts: List[HealthAlert]
    last_check: str
    uptime_percentage: float
    performance_score: float
    recommendations: List[str] = field(default_factory=list)


class HealthMonitor:
    """
    Comprehensive health monitoring system for AI providers.
    
    Features:
    - Continuous health monitoring
    - Proactive health checks
    - Performance metrics tracking
    - Automated alerting
    - Failover recommendations
    - Historical health data
    """
    
    def __init__(self, provider: str, config: Dict[str, any]):
        """
        Initialize health monitor.
        
        Args:
            provider: Provider name
            config: Health monitoring configuration
        """
        self.provider = provider
        self.config = config
        self.logger = logging.getLogger(f"ai_provider.health_monitor.{provider}")
        
        # Health monitoring configuration
        self.check_interval = config.get("health_check_interval", 60)
        self.metrics_retention = config.get("metrics_retention_hours", 24)
        self.alert_threshold = config.get("alert_threshold", 0.8)
        
        # Health metrics storage
        self.metrics_history: Dict[str, List[HealthMetric]] = {}
        self.active_alerts: List[HealthAlert] = []
        self.resolved_alerts: List[HealthAlert] = []
        
        # Performance tracking
        self.performance_history: List[Dict[str, any]] = []
        self.uptime_tracking: List[Tuple[datetime, bool]] = []
        
        # Monitoring state
        self.is_monitoring = False
        self.last_check = datetime.now()
        self.monitor_task = None
        
        # Health check functions
        self.health_check_functions: Dict[str, Callable] = {}
        self._register_default_health_checks()
        
        # Thresholds
        self.thresholds = {
            "response_time": {"warning": 5.0, "critical": 10.0},
            "error_rate": {"warning": 0.1, "critical": 0.3},
            "availability": {"warning": 0.95, "critical": 0.9},
            "cost_per_request": {"warning": 0.05, "critical": 0.1},
            "quota_utilization": {"warning": 0.8, "critical": 0.95}
        }
        
        self.logger.info(f"Health monitor initialized for {provider}")
    
    def _register_default_health_checks(self):
        """Register default health check functions"""
        self.health_check_functions = {
            "connectivity": self._check_connectivity,
            "response_time": self._check_response_time,
            "error_rate": self._check_error_rate,
            "quota_status": self._check_quota_status,
            "cost_tracking": self._check_cost_tracking
        }
    
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        if self.is_monitoring:
            self.logger.warning("Health monitoring already started")
            return
        
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info(f"Started health monitoring for {self.provider}")
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info(f"Stopped health monitoring for {self.provider}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                await self.perform_health_check()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def perform_health_check(self) -> HealthReport:
        """
        Perform comprehensive health check.
        
        Returns:
            Health report
        """
        start_time = time.time()
        metrics = {}
        current_alerts = []
        
        # Run all health checks
        for check_name, check_func in self.health_check_functions.items():
            try:
                metric = await check_func()
                if metric:
                    metrics[check_name] = metric
                    
                    # Check for alerts
                    if metric.status != HealthStatus.HEALTHY:
                        alert = HealthAlert(
                            provider=self.provider,
                            metric=check_name,
                            status=metric.status,
                            message=self._generate_alert_message(metric),
                            value=metric.value,
                            threshold=metric.threshold_warning if metric.status == HealthStatus.WARNING else metric.threshold_critical
                        )
                        current_alerts.append(alert)
                        
                        # Check if this is a new alert
                        if not self._is_existing_alert(alert):
                            self.active_alerts.append(alert)
                            await self._send_alert(alert)
                    
            except Exception as e:
                self.logger.error(f"Error in health check {check_name}: {e}")
        
        # Store metrics history
        self._store_metrics_history(metrics)
        
        # Calculate overall status
        overall_status = self._calculate_overall_status(metrics)
        
        # Update uptime tracking
        self.uptime_tracking.append((datetime.now(), overall_status == HealthStatus.HEALTHY))
        
        # Calculate performance score
        performance_score = self._calculate_performance_score(metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, current_alerts)
        
        # Create health report
        report = HealthReport(
            provider=self.provider,
            overall_status=overall_status,
            metrics=metrics,
            alerts=current_alerts,
            last_check=datetime.now().isoformat(),
            uptime_percentage=self._calculate_uptime_percentage(),
            performance_score=performance_score,
            recommendations=recommendations
        )
        
        self.last_check = datetime.now()
        
        # Log health check completion
        self.logger.info(
            json.dumps({
                "event": "health_check_completed",
                "provider": self.provider,
                "overall_status": overall_status.value,
                "metrics_count": len(metrics),
                "alerts_count": len(current_alerts),
                "check_duration": time.time() - start_time,
                "performance_score": performance_score,
                "uptime_percentage": report.uptime_percentage
            })
        )
        
        return report
    
    async def _check_connectivity(self) -> Optional[HealthMetric]:
        """Check provider connectivity"""
        try:
            start_time = time.time()
            
            # This would be implemented by each provider
            # For now, simulate connectivity check
            await asyncio.sleep(0.1)  # Simulate network call
            
            response_time = time.time() - start_time
            
            return HealthMetric(
                name="connectivity",
                value=1.0 if response_time < 5.0 else 0.0,
                threshold_warning=0.5,
                threshold_critical=0.0,
                unit="available"
            )
            
        except Exception as e:
            self.logger.error(f"Connectivity check failed: {e}")
            return HealthMetric(
                name="connectivity",
                value=0.0,
                threshold_warning=0.5,
                threshold_critical=0.0,
                unit="available"
            )
    
    async def _check_response_time(self) -> Optional[HealthMetric]:
        """Check average response time"""
        try:
            # Get recent performance data
            recent_performance = self.performance_history[-10:] if self.performance_history else []
            
            if not recent_performance:
                return None
            
            response_times = [p.get("response_time", 0) for p in recent_performance]
            avg_response_time = statistics.mean(response_times)
            
            return HealthMetric(
                name="response_time",
                value=avg_response_time,
                threshold_warning=self.thresholds["response_time"]["warning"],
                threshold_critical=self.thresholds["response_time"]["critical"],
                unit="seconds"
            )
            
        except Exception as e:
            self.logger.error(f"Response time check failed: {e}")
            return None
    
    async def _check_error_rate(self) -> Optional[HealthMetric]:
        """Check error rate"""
        try:
            # Get recent performance data
            recent_performance = self.performance_history[-20:] if self.performance_history else []
            
            if not recent_performance:
                return None
            
            error_count = sum(1 for p in recent_performance if p.get("error", False))
            error_rate = error_count / len(recent_performance)
            
            return HealthMetric(
                name="error_rate",
                value=error_rate,
                threshold_warning=self.thresholds["error_rate"]["warning"],
                threshold_critical=self.thresholds["error_rate"]["critical"],
                unit="ratio"
            )
            
        except Exception as e:
            self.logger.error(f"Error rate check failed: {e}")
            return None
    
    async def _check_quota_status(self) -> Optional[HealthMetric]:
        """Check quota utilization"""
        try:
            # This would get quota info from rate limiter
            # For now, simulate quota check
            quota_utilization = 0.5  # 50% utilization
            
            return HealthMetric(
                name="quota_utilization",
                value=quota_utilization,
                threshold_warning=self.thresholds["quota_utilization"]["warning"],
                threshold_critical=self.thresholds["quota_utilization"]["critical"],
                unit="ratio"
            )
            
        except Exception as e:
            self.logger.error(f"Quota status check failed: {e}")
            return None
    
    async def _check_cost_tracking(self) -> Optional[HealthMetric]:
        """Check cost per request"""
        try:
            # Get recent performance data
            recent_performance = self.performance_history[-10:] if self.performance_history else []
            
            if not recent_performance:
                return None
            
            costs = [p.get("cost", 0) for p in recent_performance]
            avg_cost = statistics.mean(costs)
            
            return HealthMetric(
                name="cost_per_request",
                value=avg_cost,
                threshold_warning=self.thresholds["cost_per_request"]["warning"],
                threshold_critical=self.thresholds["cost_per_request"]["critical"],
                unit="USD"
            )
            
        except Exception as e:
            self.logger.error(f"Cost tracking check failed: {e}")
            return None
    
    def _store_metrics_history(self, metrics: Dict[str, HealthMetric]):
        """Store metrics in history"""
        for metric_name, metric in metrics.items():
            if metric_name not in self.metrics_history:
                self.metrics_history[metric_name] = []
            
            self.metrics_history[metric_name].append(metric)
            
            # Clean up old metrics
            cutoff_time = datetime.now() - timedelta(hours=self.metrics_retention)
            self.metrics_history[metric_name] = [
                m for m in self.metrics_history[metric_name]
                if datetime.fromisoformat(m.timestamp) > cutoff_time
            ]
    
    def _calculate_overall_status(self, metrics: Dict[str, HealthMetric]) -> HealthStatus:
        """Calculate overall health status"""
        if not metrics:
            return HealthStatus.UNKNOWN
        
        statuses = [metric.status for metric in metrics.values()]
        
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def _calculate_performance_score(self, metrics: Dict[str, HealthMetric]) -> float:
        """Calculate performance score (0-100)"""
        if not metrics:
            return 0.0
        
        score = 0.0
        total_weight = 0.0
        
        # Weight different metrics
        weights = {
            "connectivity": 0.3,
            "response_time": 0.25,
            "error_rate": 0.25,
            "quota_utilization": 0.1,
            "cost_per_request": 0.1
        }
        
        for metric_name, metric in metrics.items():
            weight = weights.get(metric_name, 0.1)
            total_weight += weight
            
            # Convert metric to score (0-100)
            if metric.status == HealthStatus.HEALTHY:
                metric_score = 100.0
            elif metric.status == HealthStatus.WARNING:
                metric_score = 60.0
            else:  # CRITICAL
                metric_score = 20.0
            
            score += metric_score * weight
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _calculate_uptime_percentage(self) -> float:
        """Calculate uptime percentage"""
        if not self.uptime_tracking:
            return 0.0
        
        # Calculate uptime over last 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)
        recent_uptime = [
            (timestamp, is_healthy) for timestamp, is_healthy in self.uptime_tracking
            if timestamp > cutoff_time
        ]
        
        if not recent_uptime:
            return 0.0
        
        healthy_count = sum(1 for _, is_healthy in recent_uptime if is_healthy)
        return (healthy_count / len(recent_uptime)) * 100.0
    
    def _generate_recommendations(self, metrics: Dict[str, HealthMetric], 
                                alerts: List[HealthAlert]) -> List[str]:
        """Generate recommendations based on metrics and alerts"""
        recommendations = []
        
        for alert in alerts:
            if alert.metric == "response_time" and alert.status == HealthStatus.CRITICAL:
                recommendations.append("Consider switching to a faster model or increasing timeout")
            elif alert.metric == "error_rate" and alert.status == HealthStatus.WARNING:
                recommendations.append("Review recent error logs and consider rate limiting")
            elif alert.metric == "quota_utilization" and alert.status == HealthStatus.CRITICAL:
                recommendations.append("Quota nearly exhausted - consider upgrading plan or reducing usage")
            elif alert.metric == "cost_per_request" and alert.status == HealthStatus.WARNING:
                recommendations.append("Cost per request is high - consider optimizing prompts or using cheaper models")
        
        # General recommendations
        if len(alerts) > 2:
            recommendations.append("Multiple health issues detected - consider failover to backup provider")
        
        return recommendations
    
    def _generate_alert_message(self, metric: HealthMetric) -> str:
        """Generate alert message for metric"""
        if metric.status == HealthStatus.WARNING:
            return f"{metric.name} is {metric.value:.2f}{metric.unit} (warning threshold: {metric.threshold_warning:.2f})"
        elif metric.status == HealthStatus.CRITICAL:
            return f"{metric.name} is {metric.value:.2f}{metric.unit} (critical threshold: {metric.threshold_critical:.2f})"
        else:
            return f"{metric.name} is healthy at {metric.value:.2f}{metric.unit}"
    
    def _is_existing_alert(self, alert: HealthAlert) -> bool:
        """Check if alert already exists"""
        for existing_alert in self.active_alerts:
            if (existing_alert.provider == alert.provider and 
                existing_alert.metric == alert.metric and
                existing_alert.status == alert.status and
                not existing_alert.resolved):
                return True
        return False
    
    async def _send_alert(self, alert: HealthAlert):
        """Send alert notification"""
        self.logger.warning(
            json.dumps({
                "event": "health_alert",
                "provider": alert.provider,
                "metric": alert.metric,
                "status": alert.status.value,
                "message": alert.message,
                "value": alert.value,
                "threshold": alert.threshold
            })
        )
        
        # In a real implementation, this would send notifications
        # through various channels (email, Slack, etc.)
    
    def record_performance(self, response_time: float, cost: float, error: bool = False):
        """Record performance data for health monitoring"""
        self.performance_history.append({
            "timestamp": datetime.now().isoformat(),
            "response_time": response_time,
            "cost": cost,
            "error": error
        })
        
        # Clean up old performance data
        cutoff_time = datetime.now() - timedelta(hours=self.metrics_retention)
        self.performance_history = [
            p for p in self.performance_history
            if datetime.fromisoformat(p["timestamp"]) > cutoff_time
        ]
    
    def get_health_report(self) -> HealthReport:
        """Get latest health report"""
        # This would return the most recent health report
        # For now, return a basic report
        return HealthReport(
            provider=self.provider,
            overall_status=HealthStatus.HEALTHY,
            metrics={},
            alerts=self.active_alerts,
            last_check=self.last_check.isoformat(),
            uptime_percentage=self._calculate_uptime_percentage(),
            performance_score=90.0
        )
    
    def get_metric_history(self, metric_name: str, hours: int = 24) -> List[HealthMetric]:
        """Get metric history"""
        if metric_name not in self.metrics_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            metric for metric in self.metrics_history[metric_name]
            if datetime.fromisoformat(metric.timestamp) > cutoff_time
        ]
    
    def resolve_alert(self, alert_id: str):
        """Resolve an active alert"""
        for alert in self.active_alerts:
            if id(alert) == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now().isoformat()
                self.resolved_alerts.append(alert)
                self.active_alerts.remove(alert)
                break
    
    def get_health_summary(self) -> Dict[str, any]:
        """Get health summary"""
        return {
            "provider": self.provider,
            "overall_status": self.get_health_report().overall_status.value,
            "active_alerts": len(self.active_alerts),
            "uptime_percentage": self._calculate_uptime_percentage(),
            "performance_score": self._calculate_performance_score({}),
            "last_check": self.last_check.isoformat(),
            "monitoring_active": self.is_monitoring
        }