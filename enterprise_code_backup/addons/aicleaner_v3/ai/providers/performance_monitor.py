"""
Enhanced Performance Monitoring and Cost Tracking System
Cloud Integration Optimization - Phase 6

Comprehensive performance monitoring with real-time analytics, cost tracking,
and optimization recommendations for cloud API performance management.
"""

import asyncio
import json
import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import threading
import csv
from pathlib import Path

from .enhanced_config import ContentType, ProcessingPriority, ProviderTier
from .content_analyzer import ContentAnalysisResult
from ..base_provider import AIRequest, AIResponse, AIProviderStatus


class MetricType(Enum):
    """Types of metrics being tracked"""
    RESPONSE_TIME = "response_time"
    COST = "cost"
    SUCCESS_RATE = "success_rate"
    QUALITY_SCORE = "quality_score"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CACHE_HIT_RATE = "cache_hit_rate"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """Individual performance metric data point"""
    timestamp: float
    provider_name: str
    content_type: ContentType
    metric_type: MetricType
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostMetric:
    """Cost tracking metric"""
    timestamp: float
    provider_name: str
    content_type: ContentType
    request_cost: float
    cumulative_cost: float
    budget_utilization: float
    cost_per_token: float = 0.0
    tokens_used: int = 0


@dataclass
class PerformanceAlert:
    """Performance alert"""
    timestamp: float
    alert_level: AlertLevel
    provider_name: str
    metric_type: MetricType
    message: str
    current_value: float
    threshold_value: float
    recommendation: str = ""


@dataclass
class PerformanceSummary:
    """Performance summary for a provider"""
    provider_name: str
    time_period: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    total_cost: float
    avg_cost_per_request: float
    success_rate: float
    avg_quality_score: float
    throughput_rpm: float
    cache_hit_rate: float = 0.0


@dataclass
class OptimizationRecommendation:
    """Optimization recommendation"""
    provider_name: str
    recommendation_type: str
    priority: str
    description: str
    estimated_impact: Dict[str, float]  # cost_savings, performance_improvement, etc.
    implementation_steps: List[str]


class EnhancedPerformanceMonitor:
    """
    Enhanced Performance Monitoring and Cost Tracking System.
    
    Features:
    - Real-time performance metrics collection
    - Comprehensive cost tracking and budget management
    - Intelligent alerting with configurable thresholds
    - Performance trend analysis and prediction
    - Optimization recommendations
    - Multi-dimensional analytics (provider, content type, time)
    - Export capabilities for external analysis
    """
    
    def __init__(
        self,
        config: Dict[str, Any] = None,
        data_retention_days: int = 30
    ):
        """
        Initialize Enhanced Performance Monitor.
        
        Args:
            config: Configuration dictionary
            data_retention_days: How long to retain detailed metrics
        """
        self.config = config or {}
        self.data_retention_days = data_retention_days
        self.logger = logging.getLogger("performance_monitor")
        
        # Metrics storage
        self.performance_metrics: List[PerformanceMetric] = []
        self.cost_metrics: List[CostMetric] = []
        self.alerts: List[PerformanceAlert] = []
        
        # Real-time tracking
        self.provider_summaries: Dict[str, PerformanceSummary] = {}
        self.realtime_stats: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=100)))
        
        # Cost tracking
        self.daily_costs: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))  # provider -> date -> cost
        self.monthly_costs: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))  # provider -> month -> cost
        self.budget_limits: Dict[str, float] = {}  # provider -> daily budget
        
        # Alert thresholds
        self.alert_thresholds = self._initialize_alert_thresholds()
        
        # Performance baselines
        self.performance_baselines: Dict[str, Dict[MetricType, float]] = defaultdict(dict)
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Data persistence
        self.data_dir = Path(self.config.get("data_dir", "/data/performance"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Start background tasks
        self._start_background_tasks()
        
        self.logger.info("Enhanced Performance Monitor initialized")
    
    def _initialize_alert_thresholds(self) -> Dict[MetricType, Dict[AlertLevel, float]]:
        """Initialize default alert thresholds"""
        return {
            MetricType.RESPONSE_TIME: {
                AlertLevel.WARNING: 8.0,    # 8 seconds
                AlertLevel.ERROR: 12.0,     # 12 seconds
                AlertLevel.CRITICAL: 20.0   # 20 seconds
            },
            MetricType.SUCCESS_RATE: {
                AlertLevel.WARNING: 0.95,   # 95%
                AlertLevel.ERROR: 0.90,     # 90%
                AlertLevel.CRITICAL: 0.80   # 80%
            },
            MetricType.ERROR_RATE: {
                AlertLevel.WARNING: 0.05,   # 5%
                AlertLevel.ERROR: 0.10,     # 10%
                AlertLevel.CRITICAL: 0.20   # 20%
            },
            MetricType.COST: {
                AlertLevel.WARNING: 0.80,   # 80% of budget
                AlertLevel.ERROR: 0.90,     # 90% of budget
                AlertLevel.CRITICAL: 0.95   # 95% of budget
            }
        }
    
    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        def monitoring_worker():
            while True:
                try:
                    self._update_performance_summaries()
                    self._check_alert_conditions()
                    self._cleanup_old_data()
                    self._update_baselines()
                    time.sleep(60)  # Run every minute
                except Exception as e:
                    self.logger.error(f"Monitoring worker error: {e}")
                    time.sleep(30)  # Retry after 30 seconds on error
        
        def daily_worker():
            while True:
                try:
                    self._generate_daily_reports()
                    self._reset_daily_counters()
                    time.sleep(86400)  # Run daily
                except Exception as e:
                    self.logger.error(f"Daily worker error: {e}")
                    time.sleep(3600)  # Retry after 1 hour on error
        
        monitor_thread = threading.Thread(target=monitoring_worker, daemon=True)
        daily_thread = threading.Thread(target=daily_worker, daemon=True)
        
        monitor_thread.start()
        daily_thread.start()
    
    def record_request_start(
        self,
        provider_name: str,
        request: AIRequest,
        content_analysis: ContentAnalysisResult
    ):
        """Record the start of a request for performance tracking"""
        timestamp = time.time()
        
        with self.lock:
            # Record throughput metric
            self.realtime_stats[provider_name]["request_starts"].append(timestamp)
    
    def record_request_completion(
        self,
        provider_name: str,
        request: AIRequest,
        response: AIResponse,
        content_analysis: ContentAnalysisResult
    ):
        """Record completion of a request with performance and cost metrics"""
        timestamp = time.time()
        
        try:
            with self.lock:
                # Performance metrics
                self._record_performance_metric(
                    provider_name, content_analysis.content_type,
                    MetricType.RESPONSE_TIME, response.response_time
                )
                
                self._record_performance_metric(
                    provider_name, content_analysis.content_type,
                    MetricType.QUALITY_SCORE, response.confidence
                )
                
                success_value = 1.0 if not response.error else 0.0
                self._record_performance_metric(
                    provider_name, content_analysis.content_type,
                    MetricType.SUCCESS_RATE, success_value
                )
                
                # Cost metrics
                if response.cost > 0:
                    self._record_cost_metric(
                        provider_name, content_analysis.content_type,
                        response.cost, content_analysis.size_estimate
                    )
                
                # Real-time stats
                self.realtime_stats[provider_name]["response_times"].append(response.response_time)
                self.realtime_stats[provider_name]["costs"].append(response.cost)
                self.realtime_stats[provider_name]["quality_scores"].append(response.confidence)
                
                if response.cached:
                    self.realtime_stats[provider_name]["cache_hits"].append(1)
                else:
                    self.realtime_stats[provider_name]["cache_hits"].append(0)
            
            self.logger.debug(
                json.dumps({
                    "event": "request_completion_recorded",
                    "provider": provider_name,
                    "content_type": content_analysis.content_type.value,
                    "response_time": response.response_time,
                    "cost": response.cost,
                    "success": not bool(response.error),
                    "cached": response.cached
                })
            )
            
        except Exception as e:
            self.logger.error(f"Error recording request completion: {e}")
    
    def _record_performance_metric(
        self,
        provider_name: str,
        content_type: ContentType,
        metric_type: MetricType,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a performance metric"""
        metric = PerformanceMetric(
            timestamp=time.time(),
            provider_name=provider_name,
            content_type=content_type,
            metric_type=metric_type,
            value=value,
            metadata=metadata or {}
        )
        
        self.performance_metrics.append(metric)
    
    def _record_cost_metric(
        self,
        provider_name: str,
        content_type: ContentType,
        request_cost: float,
        tokens_used: int = 0
    ):
        """Record a cost metric"""
        # Calculate cumulative cost
        today = datetime.now().strftime("%Y-%m-%d")
        self.daily_costs[provider_name][today] += request_cost
        
        month = datetime.now().strftime("%Y-%m")
        self.monthly_costs[provider_name][month] += request_cost
        
        cumulative_cost = self.daily_costs[provider_name][today]
        budget = self.budget_limits.get(provider_name, 100.0)  # Default $100/day
        budget_utilization = cumulative_cost / budget
        
        cost_per_token = request_cost / max(1, tokens_used) if tokens_used > 0 else 0.0
        
        metric = CostMetric(
            timestamp=time.time(),
            provider_name=provider_name,
            content_type=content_type,
            request_cost=request_cost,
            cumulative_cost=cumulative_cost,
            budget_utilization=budget_utilization,
            cost_per_token=cost_per_token,
            tokens_used=tokens_used
        )
        
        self.cost_metrics.append(metric)
    
    def _update_performance_summaries(self):
        """Update performance summaries for all providers"""
        current_time = time.time()
        hour_ago = current_time - 3600  # Last hour
        
        with self.lock:
            for provider_name in set(m.provider_name for m in self.performance_metrics):
                # Get recent metrics
                recent_metrics = [
                    m for m in self.performance_metrics
                    if m.provider_name == provider_name and m.timestamp > hour_ago
                ]
                
                if not recent_metrics:
                    continue
                
                # Calculate summary statistics
                response_times = [m.value for m in recent_metrics if m.metric_type == MetricType.RESPONSE_TIME]
                success_rates = [m.value for m in recent_metrics if m.metric_type == MetricType.SUCCESS_RATE]
                quality_scores = [m.value for m in recent_metrics if m.metric_type == MetricType.QUALITY_SCORE]
                
                # Cost summary
                recent_costs = [
                    c for c in self.cost_metrics
                    if c.provider_name == provider_name and c.timestamp > hour_ago
                ]
                
                total_requests = len(response_times)
                successful_requests = sum(success_rates) if success_rates else 0
                failed_requests = total_requests - successful_requests
                
                # Cache hit rate
                cache_hits = list(self.realtime_stats[provider_name]["cache_hits"])
                cache_hit_rate = statistics.mean(cache_hits) if cache_hits else 0.0
                
                # Throughput (requests per minute)
                throughput_rpm = (total_requests / 60) if total_requests > 0 else 0.0
                
                summary = PerformanceSummary(
                    provider_name=provider_name,
                    time_period="last_hour",
                    total_requests=total_requests,
                    successful_requests=int(successful_requests),
                    failed_requests=failed_requests,
                    avg_response_time=statistics.mean(response_times) if response_times else 0.0,
                    p95_response_time=self._percentile(response_times, 0.95) if response_times else 0.0,
                    p99_response_time=self._percentile(response_times, 0.99) if response_times else 0.0,
                    total_cost=sum(c.request_cost for c in recent_costs),
                    avg_cost_per_request=statistics.mean([c.request_cost for c in recent_costs]) if recent_costs else 0.0,
                    success_rate=statistics.mean(success_rates) if success_rates else 0.0,
                    avg_quality_score=statistics.mean(quality_scores) if quality_scores else 0.0,
                    throughput_rpm=throughput_rpm,
                    cache_hit_rate=cache_hit_rate
                )
                
                self.provider_summaries[provider_name] = summary
    
    def _check_alert_conditions(self):
        """Check for alert conditions and generate alerts"""
        current_time = time.time()
        
        with self.lock:
            for provider_name, summary in self.provider_summaries.items():
                # Response time alerts
                if summary.avg_response_time > 0:
                    self._check_threshold_alert(
                        provider_name, MetricType.RESPONSE_TIME,
                        summary.avg_response_time, "Average response time exceeded threshold"
                    )
                
                # Success rate alerts (inverse logic - lower is worse)
                if summary.total_requests > 5:  # Need minimum requests for meaningful rate
                    success_threshold = self.alert_thresholds[MetricType.SUCCESS_RATE]
                    if summary.success_rate < success_threshold[AlertLevel.CRITICAL]:
                        self._create_alert(
                            provider_name, MetricType.SUCCESS_RATE, AlertLevel.CRITICAL,
                            f"Success rate critically low: {summary.success_rate:.2%}",
                            summary.success_rate, success_threshold[AlertLevel.CRITICAL]
                        )
                    elif summary.success_rate < success_threshold[AlertLevel.ERROR]:
                        self._create_alert(
                            provider_name, MetricType.SUCCESS_RATE, AlertLevel.ERROR,
                            f"Success rate low: {summary.success_rate:.2%}",
                            summary.success_rate, success_threshold[AlertLevel.ERROR]
                        )
                
                # Cost budget alerts
                today = datetime.now().strftime("%Y-%m-%d")
                daily_cost = self.daily_costs[provider_name].get(today, 0.0)
                budget = self.budget_limits.get(provider_name, 100.0)
                
                if budget > 0:
                    budget_utilization = daily_cost / budget
                    cost_threshold = self.alert_thresholds[MetricType.COST]
                    
                    if budget_utilization > cost_threshold[AlertLevel.CRITICAL]:
                        self._create_alert(
                            provider_name, MetricType.COST, AlertLevel.CRITICAL,
                            f"Daily budget critically exceeded: {budget_utilization:.1%} of ${budget}",
                            budget_utilization, cost_threshold[AlertLevel.CRITICAL]
                        )
                    elif budget_utilization > cost_threshold[AlertLevel.WARNING]:
                        self._create_alert(
                            provider_name, MetricType.COST, AlertLevel.WARNING,
                            f"Daily budget warning: {budget_utilization:.1%} of ${budget}",
                            budget_utilization, cost_threshold[AlertLevel.WARNING]
                        )
    
    def _check_threshold_alert(
        self,
        provider_name: str,
        metric_type: MetricType,
        current_value: float,
        message_template: str
    ):
        """Check if current value exceeds alert thresholds"""
        thresholds = self.alert_thresholds.get(metric_type, {})
        
        for level in [AlertLevel.CRITICAL, AlertLevel.ERROR, AlertLevel.WARNING]:
            threshold = thresholds.get(level)
            if threshold and current_value > threshold:
                message = f"{message_template}: {current_value:.2f} > {threshold:.2f}"
                self._create_alert(provider_name, metric_type, level, message, current_value, threshold)
                break  # Only create alert for highest severity level
    
    def _create_alert(
        self,
        provider_name: str,
        metric_type: MetricType,
        level: AlertLevel,
        message: str,
        current_value: float,
        threshold_value: float
    ):
        """Create a new alert"""
        # Check for duplicate recent alerts
        recent_alerts = [
            a for a in self.alerts[-10:]  # Last 10 alerts
            if (a.provider_name == provider_name and 
                a.metric_type == metric_type and 
                a.alert_level == level and
                time.time() - a.timestamp < 600)  # Within last 10 minutes
        ]
        
        if recent_alerts:
            return  # Don't create duplicate alerts
        
        recommendation = self._generate_alert_recommendation(provider_name, metric_type, level, current_value)
        
        alert = PerformanceAlert(
            timestamp=time.time(),
            alert_level=level,
            provider_name=provider_name,
            metric_type=metric_type,
            message=message,
            current_value=current_value,
            threshold_value=threshold_value,
            recommendation=recommendation
        )
        
        self.alerts.append(alert)
        
        # Log alert
        self.logger.log(
            getattr(logging, level.value.upper()),
            json.dumps({
                "event": "performance_alert",
                "provider": provider_name,
                "metric": metric_type.value,
                "level": level.value,
                "message": message,
                "recommendation": recommendation
            })
        )
    
    def _generate_alert_recommendation(
        self,
        provider_name: str,
        metric_type: MetricType,
        level: AlertLevel,
        current_value: float
    ) -> str:
        """Generate recommendation for alert"""
        if metric_type == MetricType.RESPONSE_TIME:
            if level == AlertLevel.CRITICAL:
                return "Consider immediate failover to backup provider or reduce request complexity"
            else:
                return "Monitor provider performance and consider optimization"
        
        elif metric_type == MetricType.SUCCESS_RATE:
            return "Check provider status and consider temporary failover to alternative provider"
        
        elif metric_type == MetricType.COST:
            if level == AlertLevel.CRITICAL:
                return "Immediate cost control required - switch to lower-cost provider or reduce usage"
            else:
                return "Monitor usage patterns and consider cost optimization strategies"
        
        return "Review provider configuration and performance settings"
    
    def _cleanup_old_data(self):
        """Clean up old performance data"""
        cutoff_time = time.time() - (self.data_retention_days * 86400)
        
        with self.lock:
            # Clean performance metrics
            self.performance_metrics = [
                m for m in self.performance_metrics if m.timestamp > cutoff_time
            ]
            
            # Clean cost metrics
            self.cost_metrics = [
                m for m in self.cost_metrics if m.timestamp > cutoff_time
            ]
            
            # Clean alerts (keep for 7 days)
            alert_cutoff = time.time() - (7 * 86400)
            self.alerts = [
                a for a in self.alerts if a.timestamp > alert_cutoff
            ]
    
    def _update_baselines(self):
        """Update performance baselines"""
        # Update baselines weekly
        if time.time() % (7 * 86400) > 86400:  # Not time yet
            return
        
        week_ago = time.time() - (7 * 86400)
        
        with self.lock:
            for provider_name in set(m.provider_name for m in self.performance_metrics):
                # Get week's worth of data
                week_metrics = [
                    m for m in self.performance_metrics
                    if m.provider_name == provider_name and m.timestamp > week_ago
                ]
                
                if not week_metrics:
                    continue
                
                # Calculate baselines for each metric type
                for metric_type in MetricType:
                    values = [m.value for m in week_metrics if m.metric_type == metric_type]
                    if values:
                        self.performance_baselines[provider_name][metric_type] = statistics.median(values)
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(percentile * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _generate_daily_reports(self):
        """Generate daily performance reports"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            report_file = self.data_dir / f"daily_report_{today}.json"
            
            # Generate comprehensive daily report
            report = {
                "date": today,
                "providers": {},
                "summary": {}
            }
            
            # Provider-specific data
            for provider_name in set(m.provider_name for m in self.performance_metrics):
                provider_data = self._generate_provider_daily_report(provider_name)
                report["providers"][provider_name] = provider_data
            
            # Overall summary
            report["summary"] = self._generate_overall_summary()
            
            # Save report
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(f"Daily report generated: {report_file}")
            
        except Exception as e:
            self.logger.error(f"Error generating daily report: {e}")
    
    def _generate_provider_daily_report(self, provider_name: str) -> Dict[str, Any]:
        """Generate daily report for specific provider"""
        yesterday = time.time() - 86400
        
        # Get yesterday's metrics
        daily_metrics = [
            m for m in self.performance_metrics
            if m.provider_name == provider_name and m.timestamp > yesterday
        ]
        
        daily_costs = [
            c for c in self.cost_metrics
            if c.provider_name == provider_name and c.timestamp > yesterday
        ]
        
        # Calculate statistics
        response_times = [m.value for m in daily_metrics if m.metric_type == MetricType.RESPONSE_TIME]
        success_rates = [m.value for m in daily_metrics if m.metric_type == MetricType.SUCCESS_RATE]
        quality_scores = [m.value for m in daily_metrics if m.metric_type == MetricType.QUALITY_SCORE]
        
        return {
            "total_requests": len(response_times),
            "avg_response_time": statistics.mean(response_times) if response_times else 0.0,
            "p95_response_time": self._percentile(response_times, 0.95) if response_times else 0.0,
            "success_rate": statistics.mean(success_rates) if success_rates else 0.0,
            "avg_quality_score": statistics.mean(quality_scores) if quality_scores else 0.0,
            "total_cost": sum(c.request_cost for c in daily_costs),
            "avg_cost_per_request": statistics.mean([c.request_cost for c in daily_costs]) if daily_costs else 0.0,
            "alerts_count": len([a for a in self.alerts if a.provider_name == provider_name and a.timestamp > yesterday])
        }
    
    def _generate_overall_summary(self) -> Dict[str, Any]:
        """Generate overall system summary"""
        yesterday = time.time() - 86400
        
        recent_metrics = [m for m in self.performance_metrics if m.timestamp > yesterday]
        recent_costs = [c for c in self.cost_metrics if c.timestamp > yesterday]
        recent_alerts = [a for a in self.alerts if a.timestamp > yesterday]
        
        return {
            "total_requests": len([m for m in recent_metrics if m.metric_type == MetricType.RESPONSE_TIME]),
            "total_cost": sum(c.request_cost for c in recent_costs),
            "total_alerts": len(recent_alerts),
            "alert_breakdown": {
                level.value: len([a for a in recent_alerts if a.alert_level == level])
                for level in AlertLevel
            }
        }
    
    def _reset_daily_counters(self):
        """Reset daily cost counters (called at midnight)"""
        # Keep only last 30 days of daily cost data
        cutoff_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        with self.lock:
            for provider_name in self.daily_costs:
                dates_to_remove = [
                    date for date in self.daily_costs[provider_name]
                    if date < cutoff_date
                ]
                for date in dates_to_remove:
                    del self.daily_costs[provider_name][date]
    
    def set_budget_limit(self, provider_name: str, daily_budget: float):
        """Set daily budget limit for provider"""
        self.budget_limits[provider_name] = daily_budget
        self.logger.info(f"Set daily budget for {provider_name}: ${daily_budget}")
    
    def set_alert_threshold(self, metric_type: MetricType, level: AlertLevel, value: float):
        """Set custom alert threshold"""
        if metric_type not in self.alert_thresholds:
            self.alert_thresholds[metric_type] = {}
        self.alert_thresholds[metric_type][level] = value
        self.logger.info(f"Set alert threshold for {metric_type.value} {level.value}: {value}")
    
    def get_provider_summary(self, provider_name: str) -> Optional[PerformanceSummary]:
        """Get current performance summary for provider"""
        return self.provider_summaries.get(provider_name)
    
    def get_cost_summary(self, provider_name: str, period: str = "daily") -> Dict[str, Any]:
        """Get cost summary for provider"""
        if period == "daily":
            today = datetime.now().strftime("%Y-%m-%d")
            daily_cost = self.daily_costs[provider_name].get(today, 0.0)
            budget = self.budget_limits.get(provider_name, 100.0)
            
            return {
                "provider": provider_name,
                "period": period,
                "cost": daily_cost,
                "budget": budget,
                "utilization": daily_cost / budget if budget > 0 else 0.0,
                "remaining": max(0, budget - daily_cost)
            }
        
        elif period == "monthly":
            month = datetime.now().strftime("%Y-%m")
            monthly_cost = self.monthly_costs[provider_name].get(month, 0.0)
            
            return {
                "provider": provider_name,
                "period": period,
                "cost": monthly_cost
            }
    
    def get_recent_alerts(self, count: int = 10) -> List[PerformanceAlert]:
        """Get recent alerts"""
        return sorted(self.alerts, key=lambda x: x.timestamp, reverse=True)[:count]
    
    def get_optimization_recommendations(self) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations based on performance data"""
        recommendations = []
        
        for provider_name, summary in self.provider_summaries.items():
            # High response time recommendation
            if summary.avg_response_time > 8.0:
                recommendations.append(OptimizationRecommendation(
                    provider_name=provider_name,
                    recommendation_type="performance",
                    priority="high",
                    description=f"Average response time ({summary.avg_response_time:.1f}s) exceeds optimal threshold",
                    estimated_impact={"performance_improvement": 0.3, "cost_impact": 0.0},
                    implementation_steps=[
                        "Consider switching to faster provider tier",
                        "Implement request timeout optimization",
                        "Enable predictive failover"
                    ]
                ))
            
            # Low cache hit rate recommendation
            if summary.cache_hit_rate < 0.3:
                recommendations.append(OptimizationRecommendation(
                    provider_name=provider_name,
                    recommendation_type="caching",
                    priority="medium",
                    description=f"Low cache hit rate ({summary.cache_hit_rate:.1%}) indicates inefficient caching",
                    estimated_impact={"cost_savings": 0.2, "performance_improvement": 0.15},
                    implementation_steps=[
                        "Review cache TTL settings",
                        "Optimize cache key generation",
                        "Implement cache warming for common requests"
                    ]
                ))
            
            # High cost per request recommendation
            if summary.avg_cost_per_request > 0.02:  # $0.02 threshold
                recommendations.append(OptimizationRecommendation(
                    provider_name=provider_name,
                    recommendation_type="cost",
                    priority="medium",
                    description=f"High average cost per request (${summary.avg_cost_per_request:.4f})",
                    estimated_impact={"cost_savings": 0.25, "performance_impact": -0.05},
                    implementation_steps=[
                        "Consider switching to more cost-efficient provider",
                        "Implement request size optimization",
                        "Enable smart provider selection based on content complexity"
                    ]
                ))
        
        return recommendations
    
    def export_metrics(self, format: str = "csv", start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
        """Export metrics to file"""
        if start_date:
            start_timestamp = datetime.strptime(start_date, "%Y-%m-%d").timestamp()
        else:
            start_timestamp = 0
        
        if end_date:
            end_timestamp = datetime.strptime(end_date, "%Y-%m-%d").timestamp()
        else:
            end_timestamp = time.time()
        
        # Filter metrics by date range
        filtered_metrics = [
            m for m in self.performance_metrics
            if start_timestamp <= m.timestamp <= end_timestamp
        ]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "csv":
            filename = self.data_dir / f"performance_metrics_{timestamp}.csv"
            
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    "timestamp", "provider_name", "content_type", "metric_type", "value"
                ])
                
                for metric in filtered_metrics:
                    writer.writerow([
                        datetime.fromtimestamp(metric.timestamp).isoformat(),
                        metric.provider_name,
                        metric.content_type.value,
                        metric.metric_type.value,
                        metric.value
                    ])
        
        elif format == "json":
            filename = self.data_dir / f"performance_metrics_{timestamp}.json"
            
            export_data = []
            for metric in filtered_metrics:
                export_data.append({
                    "timestamp": metric.timestamp,
                    "datetime": datetime.fromtimestamp(metric.timestamp).isoformat(),
                    "provider_name": metric.provider_name,
                    "content_type": metric.content_type.value,
                    "metric_type": metric.metric_type.value,
                    "value": metric.value,
                    "metadata": metric.metadata
                })
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
        
        self.logger.info(f"Metrics exported to: {filename}")
        return str(filename)
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        recent_time = time.time() - 3600  # Last hour
        recent_alerts = [a for a in self.alerts if a.timestamp > recent_time]
        
        # Count alert levels
        alert_counts = {level.value: 0 for level in AlertLevel}
        for alert in recent_alerts:
            alert_counts[alert.alert_level.value] += 1
        
        # Determine overall health status
        if alert_counts["critical"] > 0:
            health_status = "critical"
        elif alert_counts["error"] > 0:
            health_status = "degraded"
        elif alert_counts["warning"] > 0:
            health_status = "warning"
        else:
            health_status = "healthy"
        
        return {
            "status": health_status,
            "active_providers": len(self.provider_summaries),
            "recent_alerts": alert_counts,
            "total_requests_last_hour": sum(s.total_requests for s in self.provider_summaries.values()),
            "avg_response_time": statistics.mean([
                s.avg_response_time for s in self.provider_summaries.values()
                if s.avg_response_time > 0
            ]) if self.provider_summaries else 0.0,
            "overall_success_rate": statistics.mean([
                s.success_rate for s in self.provider_summaries.values()
                if s.total_requests > 0
            ]) if self.provider_summaries else 0.0
        }
    
    async def shutdown(self):
        """Shutdown performance monitor gracefully"""
        self.logger.info("Shutting down Enhanced Performance Monitor")
        
        # Generate final report
        try:
            self._generate_daily_reports()
        except Exception as e:
            self.logger.error(f"Error generating final report: {e}")
        
        self.logger.info("Enhanced Performance Monitor shutdown complete")