"""
Unified System Monitor for AICleaner

This module consolidates ResourceMonitor, AlertManager, and ProductionMonitor
into a single, unified interface for system monitoring, alerting, and performance tracking.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import statistics

# Import the individual monitoring components as internal dependencies
try:
    from .resource_monitor import ResourceMonitor, ResourceMetrics, ResourceAlert
    from .alert_manager import AlertManager, AlertRule, AlertInstance
    from .production_monitor import ProductionMonitor, PerformanceMetric, PerformanceSample, HealthCheck
    MONITORING_COMPONENTS_AVAILABLE = True
except ImportError:
    # Fallback for different import contexts
    try:
        from core.resource_monitor import ResourceMonitor, ResourceMetrics, ResourceAlert
        from core.alert_manager import AlertManager, AlertRule, AlertInstance
        from core.production_monitor import ProductionMonitor, PerformanceMetric, PerformanceSample, HealthCheck
        MONITORING_COMPONENTS_AVAILABLE = True
    except ImportError:
        MONITORING_COMPONENTS_AVAILABLE = False


@dataclass
class SystemStatus:
    """Unified system status information."""
    timestamp: str
    overall_health: str  # "healthy", "degraded", "unhealthy"
    resource_metrics: Optional[ResourceMetrics] = None
    active_alerts: List[AlertInstance] = None
    performance_summary: Dict[str, Any] = None
    recommendations: List[str] = None


@dataclass
class HealthCheckResult:
    """Health check result with detailed metrics."""
    timestamp: str
    health_score: float  # 0-100
    average_response_time: float  # milliseconds
    error_rate: float  # 0-1
    resource_pressure: float  # 0-1
    test_duration: float  # seconds
    details: Dict[str, Any]
    alerts: List[str] = None
    critical_alerts: List[str] = None  # Critical alerts that need persistent notifications
    performance_warnings: List[str] = None  # Performance warnings for binary sensor


class SystemMonitor:
    """
    Unified System Monitor for AICleaner.
    
    This class consolidates ResourceMonitor, AlertManager, and ProductionMonitor
    into a single, unified interface. The original components are used internally
    but not exposed to the rest of the application.
    
    Features:
    - Real-time resource monitoring
    - Alert management and notifications
    - Performance tracking and analysis
    - Health status reporting
    - Unified configuration and control
    """
    
    def __init__(self, config: Dict[str, Any], data_path: str = "/data/system_monitor"):
        """
        Initialize the unified System Monitor.

        Args:
            config: Configuration dictionary
            data_path: Path to store monitoring data
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.data_path = data_path

        # Perform configuration migration if needed
        self._migrate_config_if_needed()

        # Monitoring state
        self.monitoring_active = False
        self._initialization_complete = False

        # Adaptive monitoring state
        self.adaptive_monitoring_enabled = True
        self.current_monitoring_frequency = 60  # Default 60 seconds
        self.stability_counter = 0
        self.stability_threshold = 10  # Number of stable checks before reducing frequency
        self.min_frequency = 30  # Minimum 30 seconds
        self.max_frequency = 300  # Maximum 5 minutes
        self.frequency_increase_factor = 0.8  # Multiply by this to increase frequency (run more often)
        self.frequency_decrease_factor = 1.2  # Multiply by this to decrease frequency (run less often)
        self._adaptive_monitoring_task = None
        
        # Initialize internal components if available
        if MONITORING_COMPONENTS_AVAILABLE:
            self._resource_monitor = ResourceMonitor(config, f"{data_path}/resources")
            self._alert_manager = AlertManager(config, f"{data_path}/alerts")
            self._production_monitor = ProductionMonitor(f"{data_path}/production")
            
            # Set up alert callback to connect resource monitor to alert manager
            self._resource_monitor.add_alert_callback(self._handle_resource_alert)
        else:
            self.logger.warning("Monitoring components not available - running in fallback mode")
            self._resource_monitor = None
            self._alert_manager = None
            self._production_monitor = None
        
        self.logger.info("System Monitor initialized")

    def _migrate_config_if_needed(self):
        """
        Perform configuration migration from performance_optimization to inference_tuning if needed.
        """
        try:
            # Check if migration is needed
            has_old_config = "performance_optimization" in self.config
            has_new_config = "inference_tuning" in self.config

            if has_old_config and not has_new_config:
                self.logger.info("Migrating configuration from performance_optimization to inference_tuning")

                # Import migration logic
                try:
                    from .config_migration import ConfigMigration
                    migration = ConfigMigration()

                    # Perform in-memory migration
                    migrated_config = migration.migrate_config(self.config)
                    self.config.update(migrated_config)

                    self.logger.info("Configuration migration completed successfully")

                except ImportError:
                    self.logger.warning("Config migration module not available, using fallback")
                    # Simple fallback migration
                    profile = "auto"  # Default profile
                    self.config["inference_tuning"] = {
                        "enabled": True,
                        "profile": profile
                    }
                    # Keep backup of old config
                    self.config[f"performance_optimization_backup"] = self.config.pop("performance_optimization")

        except Exception as e:
            self.logger.error(f"Error during configuration migration: {e}")

    async def start_monitoring(self, interval: int = 60):
        """
        Start unified system monitoring with adaptive frequency.

        Args:
            interval: Initial monitoring interval in seconds (default: 60)
        """
        if self.monitoring_active:
            self.logger.warning("System monitoring already active")
            return

        if not MONITORING_COMPONENTS_AVAILABLE:
            self.logger.warning("Cannot start monitoring - components not available")
            return

        try:
            # Set initial monitoring frequency
            self.current_monitoring_frequency = interval

            # Start internal components with a base interval
            # We'll manage the adaptive frequency ourselves
            await self._resource_monitor.start_monitoring(10)  # Base 10s for resource monitoring
            await self._alert_manager.start()

            self.monitoring_active = True
            self._initialization_complete = True

            # Start adaptive monitoring loop
            if self.adaptive_monitoring_enabled:
                self._adaptive_monitoring_task = asyncio.create_task(self._adaptive_monitoring_loop())
                self.logger.info(f"Adaptive system monitoring started with initial {interval}s interval")
            else:
                self.logger.info(f"System monitoring started with fixed {interval}s interval")

        except Exception as e:
            self.logger.error(f"Failed to start system monitoring: {e}")
            raise
    
    async def stop_monitoring(self):
        """Stop unified system monitoring."""
        if not self.monitoring_active:
            return

        try:
            # Stop adaptive monitoring task
            if self._adaptive_monitoring_task and not self._adaptive_monitoring_task.done():
                self._adaptive_monitoring_task.cancel()
                try:
                    await self._adaptive_monitoring_task
                except asyncio.CancelledError:
                    pass

            # Stop internal components
            if self._resource_monitor:
                await self._resource_monitor.stop_monitoring()
            if self._alert_manager:
                await self._alert_manager.stop()

            self.monitoring_active = False
            self.logger.info("System monitoring stopped")

        except Exception as e:
            self.logger.error(f"Error stopping system monitoring: {e}")
    
    async def get_system_status(self) -> SystemStatus:
        """
        Get comprehensive system status.
        
        Returns:
            SystemStatus object with complete system information
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if not MONITORING_COMPONENTS_AVAILABLE:
            return SystemStatus(
                timestamp=timestamp,
                overall_health="unknown",
                recommendations=["Monitoring components not available"]
            )
        
        try:
            # Get current resource metrics
            resource_metrics = None
            if self._resource_monitor:
                resource_metrics = await self._resource_monitor.get_current_metrics()
            
            # Get active alerts
            active_alerts = []
            if self._alert_manager:
                active_alerts = list(self._alert_manager.get_active_alerts().values())
            
            # Get performance summary
            performance_summary = {}
            if self._production_monitor:
                performance_summary = {
                    "error_count": len(self._production_monitor.error_history),
                    "performance_samples": len(self._production_monitor.performance_history),
                    "health_checks": len(self._production_monitor.health_checks)
                }
            
            # Determine overall health
            overall_health = self._calculate_overall_health(resource_metrics, active_alerts)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(resource_metrics, active_alerts)
            
            return SystemStatus(
                timestamp=timestamp,
                overall_health=overall_health,
                resource_metrics=resource_metrics,
                active_alerts=active_alerts,
                performance_summary=performance_summary,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return SystemStatus(
                timestamp=timestamp,
                overall_health="error",
                recommendations=[f"Error retrieving status: {str(e)}"]
            )
    
    def record_performance(self, metric: PerformanceMetric, value: float, 
                          component: str, operation: str, context: Optional[Dict] = None):
        """
        Record a performance measurement.
        
        Args:
            metric: Performance metric type
            value: Metric value
            component: Component name
            operation: Operation name
            context: Optional context information
        """
        if self._production_monitor:
            self._production_monitor.record_performance(metric, value, component, operation, context)
    
    def capture_error(self, error: Exception, component: str, operation: str, context: Optional[Dict] = None):
        """
        Capture and track an error.
        
        Args:
            error: Exception that occurred
            component: Component where error occurred
            operation: Operation that failed
            context: Optional context information
        """
        if self._production_monitor:
            self._production_monitor.capture_error(error, component, operation, context)
    
    def performance_monitor(self, component: str, operation: str):
        """
        Decorator for automatic performance monitoring.
        
        Args:
            component: Component name
            operation: Operation name
        """
        if self._production_monitor:
            return self._production_monitor.performance_monitor(component, operation)
        else:
            # Return a no-op decorator if production monitor not available
            def decorator(func):
                return func
            return decorator
    
    def add_alert_rule(self, rule: AlertRule):
        """
        Add an alert rule.
        
        Args:
            rule: Alert rule to add
        """
        if self._alert_manager:
            self._alert_manager.add_alert_rule(rule)
    
    def acknowledge_alert(self, alert_id: str):
        """
        Acknowledge an active alert.
        
        Args:
            alert_id: ID of alert to acknowledge
        """
        if self._alert_manager:
            self._alert_manager.acknowledge_alert(alert_id)
    
    async def _handle_resource_alert(self, alert: ResourceAlert):
        """
        Handle resource alerts from the resource monitor.
        
        Args:
            alert: Resource alert to process
        """
        if self._alert_manager:
            await self._alert_manager.process_alert(alert)
    
    def _calculate_overall_health(self, metrics: Optional[ResourceMetrics], 
                                 alerts: List[AlertInstance]) -> str:
        """Calculate overall system health status."""
        if not metrics:
            return "unknown"
        
        # Check for critical alerts
        critical_alerts = [a for a in alerts if a.resource_alert.alert_level.value == "critical"]
        if critical_alerts:
            return "unhealthy"
        
        # Check resource thresholds
        if (metrics.cpu_percent > 90 or 
            metrics.memory_percent > 90 or 
            metrics.disk_usage_percent > 95):
            return "degraded"
        
        # Check for warning alerts
        warning_alerts = [a for a in alerts if a.resource_alert.alert_level.value == "warning"]
        if len(warning_alerts) > 3:
            return "degraded"
        
        return "healthy"
    
    def _generate_recommendations(self, metrics: Optional[ResourceMetrics], 
                                 alerts: List[AlertInstance]) -> List[str]:
        """Generate system recommendations based on current state."""
        recommendations = []
        
        if not metrics:
            return ["Unable to generate recommendations - no metrics available"]
        
        # Resource-based recommendations
        if metrics.memory_percent > 85:
            recommendations.append("Consider reducing memory usage or increasing available memory")
        
        if metrics.cpu_percent > 85:
            recommendations.append("High CPU usage detected - consider optimizing workload")
        
        if metrics.disk_usage_percent > 90:
            recommendations.append("Disk space running low - consider cleanup or expansion")
        
        # Alert-based recommendations
        if len(alerts) > 5:
            recommendations.append("Multiple active alerts - review system configuration")
        
        if not recommendations:
            recommendations.append("System operating normally")
        
        return recommendations

    async def run_health_check(self, ai_client=None, duration_seconds: int = 30) -> HealthCheckResult:
        """
        Run a comprehensive 30-second health check and calculate health score.

        Args:
            ai_client: AI client for inference testing (GeminiClient, OllamaClient, or MultiModelAIOptimizer)
            duration_seconds: Duration of the health check in seconds

        Returns:
            HealthCheckResult with health score (0-100) and detailed metrics
        """
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()

        self.logger.info(f"Starting {duration_seconds}-second health check")

        # Initialize metrics
        response_times = []
        error_count = 0
        total_tests = 0

        # Representative prompt for testing
        test_prompt = "Analyze this room for cleaning tasks. Focus on identifying items that need attention."

        # Test parameters
        test_interval = 2.0  # Test every 2 seconds
        max_tests = duration_seconds // test_interval

        try:
            # Run inference tests for the specified duration
            while (time.time() - start_time) < duration_seconds and total_tests < max_tests:
                total_tests += 1

                # Test inference latency
                inference_start = time.time()
                try:
                    if ai_client:
                        # Test with actual AI client
                        await self._test_ai_inference(ai_client, test_prompt)
                    else:
                        # Simulate inference test if no client available
                        await asyncio.sleep(0.1)  # Simulate 100ms response

                    response_time = (time.time() - inference_start) * 1000  # Convert to ms
                    response_times.append(response_time)

                except Exception as e:
                    error_count += 1
                    self.logger.warning(f"Inference test {total_tests} failed: {e}")

                # Wait for next test
                await asyncio.sleep(test_interval)

            # Calculate metrics
            average_response_time = statistics.mean(response_times) if response_times else 0
            error_rate = error_count / total_tests if total_tests > 0 else 0

            # Get resource pressure
            resource_pressure = await self._calculate_resource_pressure()

            # Calculate health score using weighted average
            health_score = self._calculate_health_score(
                average_response_time, error_rate, resource_pressure
            )

            # Generate alerts based on thresholds
            alerts, critical_alerts, performance_warnings = self._generate_health_alerts(
                health_score, average_response_time, error_rate, resource_pressure
            )

            actual_duration = time.time() - start_time

            result = HealthCheckResult(
                timestamp=timestamp,
                health_score=health_score,
                average_response_time=average_response_time,
                error_rate=error_rate,
                resource_pressure=resource_pressure,
                test_duration=actual_duration,
                details={
                    "total_tests": total_tests,
                    "successful_tests": total_tests - error_count,
                    "failed_tests": error_count,
                    "response_times": response_times,
                    "min_response_time": min(response_times) if response_times else 0,
                    "max_response_time": max(response_times) if response_times else 0,
                    "ai_client_available": ai_client is not None
                },
                alerts=alerts,
                critical_alerts=critical_alerts,
                performance_warnings=performance_warnings
            )

            self.logger.info(f"Health check completed: Score={health_score:.1f}, "
                           f"Avg Response={average_response_time:.1f}ms, "
                           f"Error Rate={error_rate:.2%}")

            return result

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return HealthCheckResult(
                timestamp=timestamp,
                health_score=0,
                average_response_time=0,
                error_rate=1.0,
                resource_pressure=1.0,
                test_duration=time.time() - start_time,
                details={"error": str(e)},
                alerts=["Health check failed due to system error"],
                critical_alerts=["Health check failed due to system error"],
                performance_warnings=[]
            )

    async def _test_ai_inference(self, ai_client, prompt: str):
        """Test AI inference with the provided client."""
        try:
            # Test different types of AI clients
            if hasattr(ai_client, 'analyze_batch_optimized'):
                # MultiModelAIOptimizer
                # Create a dummy image path for testing (we'll handle the case where it doesn't exist)
                test_image = "/tmp/test_health_check.jpg"
                result = ai_client.analyze_batch_optimized(
                    test_image, "test_zone", "health check", [], []
                )
                return result
            elif hasattr(ai_client, 'analyze_image'):
                # GeminiClient or similar
                test_image = "/tmp/test_health_check.jpg"
                result = await ai_client.analyze_image(test_image, prompt)
                return result
            elif hasattr(ai_client, 'generate_tasks'):
                # OllamaClient
                result = await ai_client.generate_tasks(prompt, "test_zone", "health check")
                return result
            else:
                # Generic text generation
                if hasattr(ai_client, 'generate_content'):
                    result = await ai_client.generate_content(prompt)
                    return result
                else:
                    # Fallback - just simulate a successful call
                    await asyncio.sleep(0.05)  # Simulate 50ms processing
                    return {"status": "success", "test": True}
        except Exception as e:
            # Re-raise to be caught by the calling method
            raise e

    async def _calculate_resource_pressure(self) -> float:
        """Calculate current resource pressure (0-1 scale)."""
        try:
            if not self._resource_monitor:
                return 0.5  # Default moderate pressure if no monitoring

            metrics = await self._resource_monitor.get_current_metrics()
            if not metrics:
                return 0.5

            # Calculate pressure based on CPU, memory, and disk usage
            cpu_pressure = min(metrics.cpu_percent / 100.0, 1.0)
            memory_pressure = min(metrics.memory_percent / 100.0, 1.0)
            disk_pressure = min(metrics.disk_usage_percent / 100.0, 1.0)

            # Weighted average (CPU and memory are more important than disk)
            resource_pressure = (cpu_pressure * 0.4 + memory_pressure * 0.4 + disk_pressure * 0.2)

            return min(resource_pressure, 1.0)

        except Exception as e:
            self.logger.warning(f"Error calculating resource pressure: {e}")
            return 0.5  # Default moderate pressure on error

    def _calculate_health_score(self, avg_response_time: float, error_rate: float,
                               resource_pressure: float) -> float:
        """
        Calculate health score (0-100) using weighted average.

        Weights:
        - Average Inference Latency: 60%
        - Error Rate: 30%
        - Resource Pressure: 10%
        """
        # Normalize latency score (lower is better)
        # Assume 500ms is baseline good, 2000ms is poor
        latency_score = max(0, min(100, 100 - ((avg_response_time - 500) / 15)))

        # Normalize error rate score (lower is better)
        error_score = max(0, 100 - (error_rate * 100))

        # Normalize resource pressure score (lower is better)
        resource_score = max(0, 100 - (resource_pressure * 100))

        # Calculate weighted average
        health_score = (
            latency_score * 0.60 +    # 60% weight
            error_score * 0.30 +      # 30% weight
            resource_score * 0.10     # 10% weight
        )

        return max(0, min(100, health_score))

    def _generate_health_alerts(self, health_score: float, avg_response_time: float,
                               error_rate: float, resource_pressure: float) -> tuple[List[str], List[str], List[str]]:
        """
        Generate health alerts categorized by severity.

        Returns:
            Tuple of (all_alerts, critical_alerts, performance_warnings)
        """
        all_alerts = []
        critical_alerts = []
        performance_warnings = []

        # Health score alerts
        if health_score < 30:
            alert = "Critical: System health is severely degraded"
            all_alerts.append(alert)
            critical_alerts.append(alert)
        elif health_score < 60:
            alert = "Warning: System health is below optimal levels"
            all_alerts.append(alert)
            performance_warnings.append(alert)

        # Response time alerts
        if avg_response_time > 2000:
            alert = f"High response time detected: {avg_response_time:.0f}ms"
            all_alerts.append(alert)
            performance_warnings.append(alert)
        elif avg_response_time > 1000:
            alert = f"Elevated response time: {avg_response_time:.0f}ms"
            all_alerts.append(alert)
            performance_warnings.append(alert)

        # Error rate alerts
        if error_rate > 0.2:
            alert = f"High error rate: {error_rate:.1%}"
            all_alerts.append(alert)
            performance_warnings.append(alert)
        elif error_rate > 0.1:
            alert = f"Elevated error rate: {error_rate:.1%}"
            all_alerts.append(alert)
            performance_warnings.append(alert)

        # Resource pressure alerts
        if resource_pressure > 0.9:
            alert = "Critical resource pressure detected"
            all_alerts.append(alert)
            critical_alerts.append(alert)
        elif resource_pressure > 0.8:
            alert = "High resource pressure detected"
            all_alerts.append(alert)
            performance_warnings.append(alert)

        # Check for critical system issues (e.g., Ollama offline)
        critical_system_alerts = self._check_critical_system_status()
        if critical_system_alerts:
            all_alerts.extend(critical_system_alerts)
            critical_alerts.extend(critical_system_alerts)

        return all_alerts, critical_alerts, performance_warnings

    def _check_critical_system_status(self) -> List[str]:
        """Check for critical system issues that require immediate attention."""
        critical_alerts = []

        try:
            # Check if monitoring components are available
            if not MONITORING_COMPONENTS_AVAILABLE:
                critical_alerts.append("Monitoring components are not available")

            # Check if system monitoring is active
            if not self.monitoring_active:
                critical_alerts.append("System monitoring is not active")

            # Check for critical resource alerts
            if self._alert_manager:
                active_alerts = list(self._alert_manager.get_active_alerts().values())
                critical_resource_alerts = [
                    a for a in active_alerts
                    if a.resource_alert.alert_level.value == "critical"
                ]
                if critical_resource_alerts:
                    critical_alerts.append(f"Critical resource alerts active: {len(critical_resource_alerts)}")

            # Check for AI service availability (placeholder for Ollama/Gemini checks)
            # This would typically check if Ollama is responding or if API keys are valid
            ai_service_status = self._check_ai_service_status()
            if ai_service_status:
                critical_alerts.extend(ai_service_status)

        except Exception as e:
            self.logger.error(f"Error checking critical system status: {e}")
            critical_alerts.append("Error checking system status")

        return critical_alerts

    def _check_ai_service_status(self) -> List[str]:
        """Check AI service availability (Ollama, Gemini, etc.)."""
        ai_alerts = []

        try:
            # This is a placeholder for actual AI service health checks
            # In a real implementation, this would:
            # 1. Check if Ollama is responding (HTTP request to /api/tags)
            # 2. Check if Gemini API key is valid
            # 3. Check if local models are loaded

            # For now, we'll simulate some basic checks
            config = self.config or {}

            # Check if any AI configuration exists
            has_gemini = bool(config.get("gemini_api_key"))
            has_ollama = bool(config.get("ollama", {}).get("enabled", False))

            if not has_gemini and not has_ollama:
                ai_alerts.append("No AI services configured (Gemini or Ollama)")

        except Exception as e:
            self.logger.error(f"Error checking AI service status: {e}")
            ai_alerts.append("Error checking AI service status")

        return ai_alerts

    async def _adaptive_monitoring_loop(self):
        """
        Adaptive monitoring loop that adjusts frequency based on system stability.
        """
        self.logger.info("Starting adaptive monitoring loop")

        while self.monitoring_active:
            try:
                # Run health check to assess current system state
                health_result = await self.run_health_check(duration_seconds=30)

                # Assess system stability
                is_stable = self._assess_system_stability(
                    health_result.health_score,
                    health_result.average_response_time,
                    health_result.error_rate,
                    health_result.resource_pressure
                )

                # Adjust monitoring frequency based on stability
                self._adjust_monitoring_frequency(is_stable)

                # Log current state
                self.logger.info(f"Adaptive monitoring check completed: "
                               f"health_score={health_result.health_score:.1f}, "
                               f"stable={is_stable}, "
                               f"next_check_in={self.current_monitoring_frequency:.1f}s, "
                               f"stability_counter={self.stability_counter}")

                # Wait for the current monitoring frequency
                await asyncio.sleep(self.current_monitoring_frequency)

            except asyncio.CancelledError:
                self.logger.info("Adaptive monitoring loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in adaptive monitoring loop: {e}")
                # On error, wait for current frequency before retrying
                await asyncio.sleep(self.current_monitoring_frequency)

        self.logger.info("Adaptive monitoring loop stopped")

    def _assess_system_stability(self, health_score: float, avg_response_time: float,
                                error_rate: float, resource_pressure: float) -> bool:
        """
        Assess if the system is currently stable based on key metrics.

        Args:
            health_score: Overall health score (0-100)
            avg_response_time: Average response time in milliseconds
            error_rate: Error rate (0-1)
            resource_pressure: Resource pressure (0-1)

        Returns:
            True if system is stable, False otherwise
        """
        # Define stability thresholds
        min_health_score = 75  # Health score should be above 75
        max_response_time = 1000  # Response time should be under 1 second
        max_error_rate = 0.05  # Error rate should be under 5%
        max_resource_pressure = 0.7  # Resource pressure should be under 70%

        # Check if all metrics are within stable bounds
        is_stable = (
            health_score >= min_health_score and
            avg_response_time <= max_response_time and
            error_rate <= max_error_rate and
            resource_pressure <= max_resource_pressure
        )

        self.logger.debug(f"Stability assessment: health={health_score:.1f}, "
                         f"response_time={avg_response_time:.1f}ms, "
                         f"error_rate={error_rate:.2%}, "
                         f"resource_pressure={resource_pressure:.2%}, "
                         f"stable={is_stable}")

        return is_stable

    def _adjust_monitoring_frequency(self, is_stable: bool) -> None:
        """
        Adjust monitoring frequency based on system stability.

        Args:
            is_stable: Whether the system is currently stable
        """
        old_frequency = self.current_monitoring_frequency

        if is_stable:
            # System is stable, increment stability counter
            self.stability_counter += 1

            # If we've had enough stable checks, decrease frequency (run less often)
            if self.stability_counter >= self.stability_threshold:
                new_frequency = min(
                    self.current_monitoring_frequency * self.frequency_decrease_factor,
                    self.max_frequency
                )
                if new_frequency != self.current_monitoring_frequency:
                    self.current_monitoring_frequency = new_frequency
                    self.logger.info(f"System stable for {self.stability_counter} checks, "
                                   f"reducing monitoring frequency from {old_frequency:.1f}s "
                                   f"to {new_frequency:.1f}s")
                # Reset counter after adjustment
                self.stability_counter = 0
        else:
            # System is unstable, reset counter and increase frequency (run more often)
            self.stability_counter = 0
            new_frequency = max(
                self.current_monitoring_frequency * self.frequency_increase_factor,
                self.min_frequency
            )
            if new_frequency != self.current_monitoring_frequency:
                self.current_monitoring_frequency = new_frequency
                self.logger.warning(f"System instability detected, "
                                  f"increasing monitoring frequency from {old_frequency:.1f}s "
                                  f"to {new_frequency:.1f}s")
            else:
                self.logger.warning(f"System instability detected, "
                                  f"monitoring frequency already at minimum ({self.min_frequency}s)")

    def get_adaptive_monitoring_status(self) -> Dict[str, Any]:
        """
        Get current adaptive monitoring status for debugging and monitoring.

        Returns:
            Dictionary with current adaptive monitoring state
        """
        return {
            "adaptive_monitoring_enabled": self.adaptive_monitoring_enabled,
            "current_frequency": self.current_monitoring_frequency,
            "stability_counter": self.stability_counter,
            "stability_threshold": self.stability_threshold,
            "min_frequency": self.min_frequency,
            "max_frequency": self.max_frequency,
            "frequency_increase_factor": self.frequency_increase_factor,
            "frequency_decrease_factor": self.frequency_decrease_factor,
            "monitoring_active": self.monitoring_active,
            "adaptive_task_running": (
                self._adaptive_monitoring_task is not None and
                not self._adaptive_monitoring_task.done()
            ) if self._adaptive_monitoring_task else False
        }