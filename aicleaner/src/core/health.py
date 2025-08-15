"""
Health monitoring system for AI Cleaner providers with comprehensive tracking,
circuit breaker patterns, and Home Assistant integration.
"""

import asyncio
import logging
import time
import statistics
from typing import Dict, List, Optional, Callable, Any, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import json

from ..config.schema import AICleanerConfig, HealthConfig
from ..providers.base_provider import LLMProvider, ProviderHealth, ProviderStatus

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states for provider health management."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, requests blocked
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class HealthMetrics:
    """Comprehensive health metrics for a provider."""
    provider_name: str
    current_health: ProviderHealth
    
    # Historical tracking
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    error_rates: deque = field(default_factory=lambda: deque(maxlen=100))
    status_history: deque = field(default_factory=lambda: deque(maxlen=50))
    
    # Circuit breaker state
    circuit_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    circuit_open_time: Optional[float] = None
    
    # Performance metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    
    # Trend analysis
    degradation_trend: bool = False
    improvement_trend: bool = False
    trend_confidence: float = 0.0
    
    def update_health(self, health: ProviderHealth) -> None:
        """Update health metrics with new health check result."""
        self.current_health = health
        self.response_times.append(health.response_time_ms)
        self.error_rates.append(health.error_rate)
        self.status_history.append((time.time(), health.status))
        
        # Update counters
        self.total_requests += 1
        if health.status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]:
            self.successful_requests += 1
            self.success_count += 1
        else:
            self.failed_requests += 1
            self.failure_count += 1
            self.last_failure_time = time.time()
        
        # Calculate average response time
        if self.response_times:
            self.avg_response_time = statistics.mean(self.response_times)
        
        # Analyze trends
        self._analyze_trends()
    
    def _analyze_trends(self) -> None:
        """Analyze health trends over time."""
        if len(self.response_times) < 10:
            return
        
        # Analyze response time trend
        recent_times = list(self.response_times)[-10:]
        older_times = list(self.response_times)[-20:-10] if len(self.response_times) >= 20 else []
        
        if older_times:
            recent_avg = statistics.mean(recent_times)
            older_avg = statistics.mean(older_times)
            
            # Degradation if recent times are significantly higher
            if recent_avg > older_avg * 1.3:
                self.degradation_trend = True
                self.improvement_trend = False
                self.trend_confidence = min(1.0, (recent_avg / older_avg - 1.0) * 2)
            # Improvement if recent times are significantly lower
            elif recent_avg < older_avg * 0.8:
                self.improvement_trend = True
                self.degradation_trend = False
                self.trend_confidence = min(1.0, (1.0 - recent_avg / older_avg) * 2)
            else:
                self.degradation_trend = False
                self.improvement_trend = False
                self.trend_confidence = 0.0
    
    def get_availability(self) -> float:
        """Calculate availability percentage."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        return {
            "provider_name": self.provider_name,
            "current_status": self.current_health.status.value,
            "circuit_state": self.circuit_state.value,
            "availability": self.get_availability(),
            "avg_response_time_ms": self.avg_response_time,
            "total_requests": self.total_requests,
            "success_rate": self.successful_requests / max(self.total_requests, 1),
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "degradation_trend": self.degradation_trend,
            "improvement_trend": self.improvement_trend,
            "trend_confidence": self.trend_confidence,
            "last_check": self.current_health.last_check,
            "error_message": self.current_health.error_message
        }


class CircuitBreaker:
    """Circuit breaker implementation for provider health management."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, 
                 success_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.circuit_open_time: Optional[float] = None
    
    def should_allow_request(self) -> bool:
        """Determine if a request should be allowed through the circuit breaker."""
        current_time = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        elif self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if (self.circuit_open_time and 
                current_time - self.circuit_open_time >= self.recovery_timeout):
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info(f"Circuit breaker transitioning to HALF_OPEN state")
                return True
            return False
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self) -> None:
        """Record a successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit breaker transitioning to CLOSED state")
        else:
            self.failure_count = 0
    
    def record_failure(self) -> None:
        """Record a failed operation."""
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.circuit_open_time = time.time()
            logger.warning(f"Circuit breaker transitioning to OPEN state")
        else:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                self.circuit_open_time = time.time()
                logger.warning(f"Circuit breaker opening due to {self.failure_count} failures")


class HealthMonitor:
    """Comprehensive health monitoring system for AI Cleaner providers."""
    
    def __init__(self, config: AICleanerConfig):
        self.config = config
        self.health_config = config.health
        
        # Health tracking
        self.provider_metrics: Dict[str, HealthMetrics] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Monitoring state
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._health_callbacks: List[Callable[[Dict[str, HealthMetrics]], None]] = []
        
        # Performance aggregation
        self._system_performance_history: deque = deque(maxlen=1000)
        
        logger.info("Health monitoring system initialized")
    
    def register_provider(self, provider_name: str, provider: LLMProvider) -> None:
        """Register a provider for health monitoring."""
        if provider_name not in self.provider_metrics:
            # Initialize with default healthy state
            initial_health = ProviderHealth(
                status=ProviderStatus.HEALTHY,
                response_time_ms=0.0,
                error_rate=0.0,
                last_check=time.time()
            )
            
            self.provider_metrics[provider_name] = HealthMetrics(
                provider_name=provider_name,
                current_health=initial_health
            )
            
            self.circuit_breakers[provider_name] = CircuitBreaker(
                failure_threshold=self.health_config.max_failures,
                recovery_timeout=self.health_config.timeout * 2,
                success_threshold=2
            )
            
            logger.info(f"Registered provider for health monitoring: {provider_name}")
    
    def add_health_callback(self, callback: Callable[[Dict[str, HealthMetrics]], None]) -> None:
        """Add a callback to be notified of health changes."""
        self._health_callbacks.append(callback)
    
    async def start_monitoring(self, provider_registry) -> None:
        """Start background health monitoring."""
        if self._monitoring_task:
            await self.stop_monitoring()
        
        self._shutdown_event.clear()
        self._monitoring_task = asyncio.create_task(
            self._monitoring_loop(provider_registry)
        )
        logger.info("Health monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop background health monitoring."""
        self._shutdown_event.set()
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        
        logger.info("Health monitoring stopped")
    
    async def _monitoring_loop(self, provider_registry) -> None:
        """Main monitoring loop with configurable intervals."""
        while not self._shutdown_event.is_set():
            try:
                # Perform health checks on all registered providers
                health_results = await self._perform_health_checks(provider_registry)
                
                # Update metrics and analyze trends
                await self._update_metrics(health_results)
                
                # Trigger callbacks for health status changes
                await self._notify_health_callbacks()
                
                # Update system performance metrics
                await self._update_system_performance()
                
                # Wait for next check interval
                await asyncio.sleep(self.health_config.check_interval)
                
            except asyncio.CancelledError:
                logger.info("Health monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                # Use shorter interval on error to recover quickly
                await asyncio.sleep(min(self.health_config.check_interval, 30))
    
    async def _perform_health_checks(self, provider_registry) -> Dict[str, ProviderHealth]:
        """Perform health checks on all providers with timeout handling."""
        health_results = {}
        
        # Create health check tasks for all registered providers
        health_tasks = {}
        
        for provider_name in self.provider_metrics.keys():
            provider = provider_registry.get_provider(provider_name)
            if provider:
                # Check circuit breaker before attempting health check
                circuit_breaker = self.circuit_breakers[provider_name]
                if circuit_breaker.should_allow_request():
                    health_tasks[provider_name] = asyncio.create_task(
                        self._safe_health_check(provider, provider_name)
                    )
                else:
                    # Circuit breaker is open, mark as unhealthy
                    health_results[provider_name] = ProviderHealth(
                        status=ProviderStatus.OFFLINE,
                        response_time_ms=0.0,
                        error_rate=1.0,
                        last_check=time.time(),
                        error_message="Circuit breaker open"
                    )
        
        # Wait for all health checks with timeout
        if health_tasks:
            try:
                completed_tasks = await asyncio.wait_for(
                    asyncio.gather(*health_tasks.values(), return_exceptions=True),
                    timeout=self.health_config.timeout * 2
                )
                
                # Process results
                for provider_name, result in zip(health_tasks.keys(), completed_tasks):
                    if isinstance(result, ProviderHealth):
                        health_results[provider_name] = result
                    else:
                        # Health check failed
                        health_results[provider_name] = ProviderHealth(
                            status=ProviderStatus.OFFLINE,
                            response_time_ms=0.0,
                            error_rate=1.0,
                            last_check=time.time(),
                            error_message=f"Health check failed: {result}"
                        )
                        
            except asyncio.TimeoutError:
                logger.error("Health check timeout exceeded")
                # Mark all remaining providers as offline
                for provider_name in health_tasks.keys():
                    if provider_name not in health_results:
                        health_results[provider_name] = ProviderHealth(
                            status=ProviderStatus.OFFLINE,
                            response_time_ms=0.0,
                            error_rate=1.0,
                            last_check=time.time(),
                            error_message="Health check timeout"
                        )
        
        return health_results
    
    async def _safe_health_check(self, provider: LLMProvider, provider_name: str) -> ProviderHealth:
        """Perform a single health check with error handling and circuit breaker updates."""
        start_time = time.time()
        circuit_breaker = self.circuit_breakers[provider_name]
        
        try:
            # Perform health check with timeout
            health = await asyncio.wait_for(
                provider.health_check(),
                timeout=self.health_config.timeout
            )
            
            # Update circuit breaker on success
            if health.status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]:
                circuit_breaker.record_success()
            else:
                circuit_breaker.record_failure()
            
            return health
            
        except asyncio.TimeoutError:
            circuit_breaker.record_failure()
            processing_time = (time.time() - start_time) * 1000
            return ProviderHealth(
                status=ProviderStatus.OFFLINE,
                response_time_ms=processing_time,
                error_rate=1.0,
                last_check=time.time(),
                error_message="Health check timeout"
            )
            
        except Exception as e:
            circuit_breaker.record_failure()
            processing_time = (time.time() - start_time) * 1000
            return ProviderHealth(
                status=ProviderStatus.OFFLINE,
                response_time_ms=processing_time,
                error_rate=1.0,
                last_check=time.time(),
                error_message=str(e)
            )
    
    async def _update_metrics(self, health_results: Dict[str, ProviderHealth]) -> None:
        """Update provider metrics with new health data."""
        for provider_name, health in health_results.items():
            if provider_name in self.provider_metrics:
                metrics = self.provider_metrics[provider_name]
                metrics.update_health(health)
                
                # Update circuit breaker state in metrics
                circuit_breaker = self.circuit_breakers[provider_name]
                metrics.circuit_state = circuit_breaker.state
                
                logger.debug(f"Updated metrics for {provider_name}: "
                           f"{health.status.value}, {health.response_time_ms:.1f}ms")
    
    async def _notify_health_callbacks(self) -> None:
        """Notify registered callbacks of health status changes."""
        try:
            for callback in self._health_callbacks:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self.provider_metrics)
                else:
                    callback(self.provider_metrics)
        except Exception as e:
            logger.error(f"Error in health callback: {e}")
    
    async def _update_system_performance(self) -> None:
        """Update system-wide performance metrics."""
        if not self.provider_metrics:
            return
        
        # Calculate system-wide metrics
        total_availability = 0.0
        total_response_time = 0.0
        healthy_providers = 0
        total_providers = len(self.provider_metrics)
        
        for metrics in self.provider_metrics.values():
            total_availability += metrics.get_availability()
            total_response_time += metrics.avg_response_time
            
            if metrics.current_health.status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]:
                healthy_providers += 1
        
        system_metrics = {
            "timestamp": time.time(),
            "overall_availability": total_availability / max(total_providers, 1),
            "avg_response_time": total_response_time / max(total_providers, 1),
            "healthy_providers": healthy_providers,
            "total_providers": total_providers,
            "system_health": "healthy" if healthy_providers > 0 else "degraded"
        }
        
        self._system_performance_history.append(system_metrics)
    
    def get_provider_health(self, provider_name: str) -> Optional[ProviderHealth]:
        """Get current health status for a specific provider."""
        metrics = self.provider_metrics.get(provider_name)
        return metrics.current_health if metrics else None
    
    def get_all_provider_health(self) -> Dict[str, ProviderHealth]:
        """Get current health status for all providers."""
        return {
            name: metrics.current_health 
            for name, metrics in self.provider_metrics.items()
        }
    
    def get_provider_metrics(self, provider_name: str) -> Optional[HealthMetrics]:
        """Get comprehensive metrics for a specific provider."""
        return self.provider_metrics.get(provider_name)
    
    def get_all_provider_metrics(self) -> Dict[str, HealthMetrics]:
        """Get comprehensive metrics for all providers."""
        return self.provider_metrics.copy()
    
    def get_healthy_providers(self) -> List[str]:
        """Get list of currently healthy providers."""
        healthy = []
        
        for name, metrics in self.provider_metrics.items():
            # Check circuit breaker state
            circuit_breaker = self.circuit_breakers[name]
            if not circuit_breaker.should_allow_request():
                continue
            
            # Check health status
            if metrics.current_health.status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]:
                healthy.append(name)
        
        return healthy
    
    def get_system_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive system performance summary."""
        if not self._system_performance_history:
            return {"status": "no_data"}
        
        latest_metrics = self._system_performance_history[-1]
        
        # Calculate trends if we have enough history
        trends = {}
        if len(self._system_performance_history) >= 10:
            recent_metrics = list(self._system_performance_history)[-10:]
            older_metrics = list(self._system_performance_history)[-20:-10] if len(self._system_performance_history) >= 20 else []
            
            if older_metrics:
                recent_availability = statistics.mean([m["overall_availability"] for m in recent_metrics])
                older_availability = statistics.mean([m["overall_availability"] for m in older_metrics])
                
                recent_response_time = statistics.mean([m["avg_response_time"] for m in recent_metrics])
                older_response_time = statistics.mean([m["avg_response_time"] for m in older_metrics])
                
                trends = {
                    "availability_trend": "improving" if recent_availability > older_availability else "degrading",
                    "response_time_trend": "improving" if recent_response_time < older_response_time else "degrading",
                    "availability_change": recent_availability - older_availability,
                    "response_time_change": recent_response_time - older_response_time
                }
        
        return {
            **latest_metrics,
            "trends": trends,
            "provider_details": {
                name: metrics.get_performance_summary()
                for name, metrics in self.provider_metrics.items()
            }
        }
    
    def get_health_status_for_ha(self) -> Dict[str, Any]:
        """Get health status formatted for Home Assistant integration."""
        system_summary = self.get_system_performance_summary()
        
        # Create Home Assistant compatible sensor data
        ha_data = {
            "state": system_summary.get("system_health", "unknown"),
            "attributes": {
                "friendly_name": "AI Cleaner Health",
                "overall_availability": round(system_summary.get("overall_availability", 0.0) * 100, 2),
                "avg_response_time_ms": round(system_summary.get("avg_response_time", 0.0), 2),
                "healthy_providers": system_summary.get("healthy_providers", 0),
                "total_providers": system_summary.get("total_providers", 0),
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "providers": {}
            }
        }
        
        # Add individual provider status
        for name, metrics in self.provider_metrics.items():
            ha_data["attributes"]["providers"][name] = {
                "status": metrics.current_health.status.value,
                "availability": round(metrics.get_availability() * 100, 2),
                "response_time_ms": round(metrics.avg_response_time, 2),
                "circuit_state": metrics.circuit_state.value,
                "error_message": metrics.current_health.error_message
            }
        
        return ha_data
    
    async def force_health_check(self, provider_registry) -> Dict[str, ProviderHealth]:
        """Force an immediate health check on all providers."""
        logger.info("Performing forced health check on all providers")
        health_results = await self._perform_health_checks(provider_registry)
        await self._update_metrics(health_results)
        await self._notify_health_callbacks()
        return health_results
    
    def reset_circuit_breaker(self, provider_name: str) -> bool:
        """Manually reset circuit breaker for a provider."""
        if provider_name in self.circuit_breakers:
            circuit_breaker = self.circuit_breakers[provider_name]
            circuit_breaker.state = CircuitBreakerState.CLOSED
            circuit_breaker.failure_count = 0
            circuit_breaker.success_count = 0
            circuit_breaker.last_failure_time = None
            circuit_breaker.circuit_open_time = None
            
            logger.info(f"Circuit breaker reset for provider: {provider_name}")
            return True
        
        return False
    
    def export_health_history(self) -> Dict[str, Any]:
        """Export health history for analysis or backup."""
        return {
            "system_performance_history": list(self._system_performance_history),
            "provider_metrics": {
                name: {
                    "provider_name": metrics.provider_name,
                    "current_health": {
                        "status": metrics.current_health.status.value,
                        "response_time_ms": metrics.current_health.response_time_ms,
                        "error_rate": metrics.current_health.error_rate,
                        "last_check": metrics.current_health.last_check,
                        "error_message": metrics.current_health.error_message
                    },
                    "response_times": list(metrics.response_times),
                    "error_rates": list(metrics.error_rates),
                    "status_history": [(ts, status.value) for ts, status in metrics.status_history],
                    "circuit_state": metrics.circuit_state.value,
                    "performance_summary": metrics.get_performance_summary()
                }
                for name, metrics in self.provider_metrics.items()
            },
            "export_timestamp": time.time()
        }