"""
Advanced Load Balancing for AI Providers
Phase 5A: Advanced Load Balancing Implementation

Intelligent load balancing algorithms optimized for single-user Home Assistant addon.
Focuses on practical algorithms that improve response time, reliability, and cost efficiency.
"""

import asyncio
import logging
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

from .base_provider import BaseAIProvider, AIRequest, AIResponse, AIProviderStatus
from utils.unified_logger import get_logger, log_performance
from monitoring.system_monitor import get_system_monitor

logger = get_logger(__name__)

# Configuration constants
EWMA_ALPHA = 0.2  # Exponentially Weighted Moving Average smoothing factor
MIN_HEALTH_SCORE = 0.5  # Minimum health score for provider selection
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 3  # Failures before opening circuit breaker
CIRCUIT_BREAKER_TIMEOUT = 30  # Seconds before trying half-open state
COST_TIER_FALLBACK_ENABLED = True  # Allow fallback to lower cost tiers

class LoadBalancingStrategy(Enum):
    """Available load balancing strategies"""
    PRIORITY = "priority"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    COST_OPTIMIZED = "cost_optimized"
    RESPONSE_TIME = "response_time"
    HEALTH_BASED = "health_based"

@dataclass
class ProviderMetrics:
    """Real-time performance and health metrics for a provider"""
    # Performance metrics
    ewma_latency: float = 1.0  # Exponentially weighted moving average latency (normalized)
    success_count: int = 0
    error_count: int = 0
    total_requests: int = 0
    
    # Health and reliability
    health_score: float = 1.0  # Combined health score (0.0 to 1.0)
    availability_score: float = 1.0  # Availability over time window
    reliability_score: float = 1.0  # Success rate over time window
    
    # Cost metrics
    total_cost: float = 0.0
    cost_per_request: float = 0.0
    
    # Timing
    last_request_time: float = 0.0
    last_success_time: float = 0.0
    last_failure_time: float = 0.0
    
    # Window-based metrics (for calculating recent performance)
    recent_requests: List[Tuple[float, bool, float]] = field(default_factory=list)  # (timestamp, success, latency)
    
    def update_request(self, success: bool, latency: float, cost: float = 0.0):
        """Update metrics after a request"""
        current_time = time.time()
        
        # Update basic counters
        self.total_requests += 1
        if success:
            self.success_count += 1
            self.last_success_time = current_time
        else:
            self.error_count += 1
            self.last_failure_time = current_time
        
        # Update EWMA latency (normalized to 0-1 range, assuming max 15s)
        normalized_latency = min(latency / 15.0, 1.0)
        self.ewma_latency = (EWMA_ALPHA * normalized_latency) + (1 - EWMA_ALPHA) * self.ewma_latency
        
        # Update cost metrics
        self.total_cost += cost
        self.cost_per_request = self.total_cost / max(1, self.total_requests)
        
        # Update recent requests (keep last 50 requests for windowed calculations)
        self.recent_requests.append((current_time, success, latency))
        if len(self.recent_requests) > 50:
            self.recent_requests.pop(0)
        
        # Update calculated metrics
        self._calculate_health_score()
        self.last_request_time = current_time
    
    def _calculate_health_score(self):
        """Calculate combined health score from various metrics"""
        if self.total_requests == 0:
            self.health_score = 1.0
            self.availability_score = 1.0
            self.reliability_score = 1.0
            return
        
        # Calculate reliability score (success rate)
        self.reliability_score = self.success_count / self.total_requests
        
        # Calculate availability score (considering recent requests)
        recent_window = time.time() - 300  # Last 5 minutes
        recent_successes = sum(1 for ts, success, _ in self.recent_requests 
                             if ts >= recent_window and success)
        recent_total = sum(1 for ts, _, _ in self.recent_requests if ts >= recent_window)
        
        if recent_total > 0:
            self.availability_score = recent_successes / recent_total
        else:
            self.availability_score = self.reliability_score
        
        # Combined health score: weighted average of reliability, availability, and latency
        latency_score = 1.0 - self.ewma_latency  # Lower latency = higher score
        self.health_score = (
            0.4 * self.reliability_score +
            0.3 * self.availability_score +
            0.3 * latency_score
        )
    
    def get_recent_performance(self, window_seconds: int = 300) -> Dict[str, float]:
        """Get performance metrics for recent time window"""
        cutoff_time = time.time() - window_seconds
        recent = [(ts, success, latency) for ts, success, latency in self.recent_requests 
                 if ts >= cutoff_time]
        
        if not recent:
            return {
                "success_rate": self.reliability_score,
                "avg_latency": self.ewma_latency * 15.0,  # Denormalize
                "request_count": 0
            }
        
        successes = sum(1 for _, success, _ in recent if success)
        total = len(recent)
        avg_latency = sum(latency for _, _, latency in recent) / total
        
        return {
            "success_rate": successes / total,
            "avg_latency": avg_latency,
            "request_count": total
        }

@dataclass
class CircuitBreakerState:
    """Circuit breaker state for a provider"""
    state: str = "closed"  # closed, open, half-open
    failure_count: int = 0
    last_failure_time: float = 0.0
    timeout_duration: float = CIRCUIT_BREAKER_TIMEOUT
    max_failures: int = CIRCUIT_BREAKER_FAILURE_THRESHOLD
    
    def is_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self.state == "open":
            # Check if timeout has elapsed
            if time.time() - self.last_failure_time >= self.timeout_duration:
                self.state = "half-open"
                logger.info(f"Circuit breaker transitioning to half-open state")
                return False
            return True
        return False
    
    def record_success(self):
        """Record successful request"""
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0
            logger.info(f"Circuit breaker closed after successful request")
        elif self.state == "closed":
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.max_failures:
            if self.state != "open":
                self.state = "open"
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
        elif self.state == "half-open":
            self.state = "open"
            logger.warning(f"Circuit breaker re-opened from half-open state")

class LoadBalancer:
    """
    Advanced load balancer for AI providers optimized for single-user Home Assistant addon.
    """
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN,
                 cost_tiers: Dict[str, List[str]] = None):
        self.strategy = strategy
        self.cost_tiers = cost_tiers or {
            "performance": ["openai", "anthropic"],
            "balanced": ["google"],
            "economy": ["ollama", "llamacpp_amd"]
        }
        
        # Provider tracking
        self.provider_metrics: Dict[str, ProviderMetrics] = {}
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        
        # Strategy-specific state
        self._round_robin_index = 0
        self._last_cleanup = time.time()
        
        # Performance monitoring
        self.system_monitor = get_system_monitor()
        
        logger.info(f"Load balancer initialized with strategy: {strategy.value}")
    
    def register_provider(self, provider_name: str):
        """Register a new provider for load balancing"""
        if provider_name not in self.provider_metrics:
            self.provider_metrics[provider_name] = ProviderMetrics()
            self.circuit_breakers[provider_name] = CircuitBreakerState()
            logger.info(f"Registered provider for load balancing: {provider_name}")
    
    def unregister_provider(self, provider_name: str):
        """Unregister a provider from load balancing"""
        self.provider_metrics.pop(provider_name, None)
        self.circuit_breakers.pop(provider_name, None)
        logger.info(f"Unregistered provider from load balancing: {provider_name}")
    
    def update_provider_metrics(self, provider_name: str, success: bool, 
                              latency: float, cost: float = 0.0):
        """Update provider metrics after a request"""
        if provider_name not in self.provider_metrics:
            self.register_provider(provider_name)
        
        # Update metrics
        self.provider_metrics[provider_name].update_request(success, latency, cost)
        
        # Update circuit breaker
        if success:
            self.circuit_breakers[provider_name].record_success()
        else:
            self.circuit_breakers[provider_name].record_failure()
        
        # Log performance if significantly different from average
        recent_perf = self.provider_metrics[provider_name].get_recent_performance()
        if recent_perf["request_count"] > 5:  # Only log if we have sufficient data
            if success and latency > recent_perf["avg_latency"] * 2:
                log_performance(f"slow_request_{provider_name}", latency, 
                              provider=provider_name, slow_request=True)
            elif not success:
                log_performance(f"failed_request_{provider_name}", latency,
                              provider=provider_name, failed_request=True)
    
    def select_provider(self, providers: Dict[str, BaseAIProvider], 
                       request: AIRequest) -> Optional[str]:
        """
        Select the best provider for the request based on configured strategy.
        
        Args:
            providers: Available providers
            request: The request to process
            
        Returns:
            Selected provider name or None if no suitable provider found
        """
        # Periodic cleanup
        if time.time() - self._last_cleanup > 300:  # Every 5 minutes
            self._cleanup_old_metrics()
            self._last_cleanup = time.time()
        
        # Get available providers
        available_providers = self._get_available_providers(providers, request)
        
        if not available_providers:
            logger.warning("No available providers for request")
            return None
        
        # Select based on strategy
        if self.strategy == LoadBalancingStrategy.PRIORITY:
            return self._select_by_priority(available_providers, providers)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._select_by_weighted_round_robin(available_providers)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._select_by_least_connections(available_providers, providers)
        elif self.strategy == LoadBalancingStrategy.COST_OPTIMIZED:
            return self._select_by_cost_optimization(available_providers, request)
        elif self.strategy == LoadBalancingStrategy.RESPONSE_TIME:
            return self._select_by_response_time(available_providers)
        elif self.strategy == LoadBalancingStrategy.HEALTH_BASED:
            return self._select_by_health_score(available_providers)
        else:
            # Default to weighted round robin
            return self._select_by_weighted_round_robin(available_providers)
    
    def _get_available_providers(self, providers: Dict[str, BaseAIProvider], 
                               request: AIRequest) -> List[str]:
        """Get list of available providers for the request"""
        available = []
        
        for name, provider in providers.items():
            # Check if provider is enabled and healthy
            if not provider.is_available():
                continue
            
            # Check circuit breaker
            if name in self.circuit_breakers and self.circuit_breakers[name].is_open():
                continue
            
            # Check provider capabilities
            if not self._provider_supports_request(provider, request):
                continue
            
            # Check health score
            if name in self.provider_metrics:
                if self.provider_metrics[name].health_score < MIN_HEALTH_SCORE:
                    continue
            
            available.append(name)
        
        return available
    
    def _provider_supports_request(self, provider: BaseAIProvider, request: AIRequest) -> bool:
        """Check if provider supports the request type"""
        capabilities = provider.capabilities
        
        # Check vision capability for image requests
        if (request.image_path or request.image_data) and not capabilities.get("vision", False):
            return False
        
        # Check other capabilities as needed
        # (Can be extended for specific request types)
        
        return True
    
    def _select_by_priority(self, available_providers: List[str], 
                          providers: Dict[str, BaseAIProvider]) -> Optional[str]:
        """Select provider by priority (lowest number = highest priority)"""
        if not available_providers:
            return None
        
        # Sort by provider priority
        sorted_providers = sorted(available_providers, 
                                key=lambda name: providers[name].config.priority)
        
        selected = sorted_providers[0]
        logger.debug(f"Priority selection: {selected}")
        return selected
    
    def _select_by_weighted_round_robin(self, available_providers: List[str]) -> Optional[str]:
        """Select provider using weighted round robin with dynamic weights"""
        if not available_providers:
            return None
        
        # Calculate weights based on health scores
        weights = []
        for name in available_providers:
            if name in self.provider_metrics:
                # Weight based on health score
                health_score = self.provider_metrics[name].health_score
                # Boost weight for healthier providers
                weight = max(0.1, health_score ** 2)  # Quadratic scaling
            else:
                weight = 1.0  # Default weight for new providers
            
            weights.append(weight)
        
        # Weighted random selection
        selected = random.choices(available_providers, weights=weights, k=1)[0]
        logger.debug(f"Weighted round robin selection: {selected}")
        return selected
    
    def _select_by_least_connections(self, available_providers: List[str], 
                                   providers: Dict[str, BaseAIProvider]) -> Optional[str]:
        """Select provider with least active connections"""
        if not available_providers:
            return None
        
        # Sort by active connections (ascending)
        sorted_providers = sorted(available_providers, 
                                key=lambda name: providers[name].get_active_requests())
        
        selected = sorted_providers[0]
        active_requests = providers[selected].get_active_requests()
        logger.debug(f"Least connections selection: {selected} (active: {active_requests})")
        return selected
    
    def _select_by_cost_optimization(self, available_providers: List[str], 
                                   request: AIRequest) -> Optional[str]:
        """Select provider based on cost optimization strategy"""
        if not available_providers:
            return None
        
        # Get desired quality tier from request context
        quality_tier = request.context.get("quality_tier", "balanced") if request.context else "balanced"
        
        # Try to find providers in the desired tier
        tier_order = ["performance", "balanced", "economy"]
        
        # Start from requested tier and fall back to lower tiers if needed
        try:
            start_index = tier_order.index(quality_tier)
        except ValueError:
            start_index = 1  # Default to balanced
        
        for i in range(start_index, len(tier_order)):
            current_tier = tier_order[i]
            tier_providers = [p for p in available_providers 
                            if p in self.cost_tiers.get(current_tier, [])]
            
            if tier_providers:
                # Select best provider from this tier based on health score
                best_provider = max(tier_providers, 
                                  key=lambda p: self.provider_metrics.get(p, ProviderMetrics()).health_score)
                logger.debug(f"Cost optimization selection: {best_provider} from tier {current_tier}")
                return best_provider
        
        # If no provider found in any tier, fall back to best available
        if COST_TIER_FALLBACK_ENABLED:
            return self._select_by_health_score(available_providers)
        
        return None
    
    def _select_by_response_time(self, available_providers: List[str]) -> Optional[str]:
        """Select provider with best response time"""
        if not available_providers:
            return None
        
        # Sort by EWMA latency (ascending - lower is better)
        sorted_providers = sorted(available_providers, 
                                key=lambda name: self.provider_metrics.get(name, ProviderMetrics()).ewma_latency)
        
        selected = sorted_providers[0]
        latency = self.provider_metrics.get(selected, ProviderMetrics()).ewma_latency
        logger.debug(f"Response time selection: {selected} (EWMA latency: {latency:.3f})")
        return selected
    
    def _select_by_health_score(self, available_providers: List[str]) -> Optional[str]:
        """Select provider with highest health score"""
        if not available_providers:
            return None
        
        # Sort by health score (descending - higher is better)
        sorted_providers = sorted(available_providers, 
                                key=lambda name: self.provider_metrics.get(name, ProviderMetrics()).health_score,
                                reverse=True)
        
        selected = sorted_providers[0]
        health_score = self.provider_metrics.get(selected, ProviderMetrics()).health_score
        logger.debug(f"Health-based selection: {selected} (health score: {health_score:.3f})")
        return selected
    
    def _cleanup_old_metrics(self):
        """Clean up old metrics data to prevent memory growth"""
        cutoff_time = time.time() - 3600  # Keep last hour of data
        
        for provider_name, metrics in self.provider_metrics.items():
            # Clean up old recent_requests
            metrics.recent_requests = [
                (ts, success, latency) for ts, success, latency in metrics.recent_requests
                if ts >= cutoff_time
            ]
            
            # Recalculate health score after cleanup
            metrics._calculate_health_score()
        
        logger.debug("Cleaned up old metrics data")
    
    def get_provider_stats(self, provider_name: str) -> Dict[str, Any]:
        """Get detailed statistics for a provider"""
        if provider_name not in self.provider_metrics:
            return {}
        
        metrics = self.provider_metrics[provider_name]
        circuit_breaker = self.circuit_breakers.get(provider_name, CircuitBreakerState())
        recent_perf = metrics.get_recent_performance()
        
        return {
            "provider_name": provider_name,
            "health_score": round(metrics.health_score, 3),
            "reliability_score": round(metrics.reliability_score, 3),
            "availability_score": round(metrics.availability_score, 3),
            "ewma_latency": round(metrics.ewma_latency * 15.0, 3),  # Denormalized
            "total_requests": metrics.total_requests,
            "success_count": metrics.success_count,
            "error_count": metrics.error_count,
            "total_cost": round(metrics.total_cost, 4),
            "cost_per_request": round(metrics.cost_per_request, 4),
            "circuit_breaker_state": circuit_breaker.state,
            "recent_performance": {
                "success_rate": round(recent_perf["success_rate"], 3),
                "avg_latency": round(recent_perf["avg_latency"], 3),
                "request_count": recent_perf["request_count"]
            }
        }
    
    def get_load_balancer_stats(self) -> Dict[str, Any]:
        """Get overall load balancer statistics"""
        total_requests = sum(metrics.total_requests for metrics in self.provider_metrics.values())
        total_cost = sum(metrics.total_cost for metrics in self.provider_metrics.values())
        
        # Calculate average health score
        health_scores = [metrics.health_score for metrics in self.provider_metrics.values()]
        avg_health_score = sum(health_scores) / len(health_scores) if health_scores else 0.0
        
        # Count circuit breaker states
        circuit_states = {}
        for cb in self.circuit_breakers.values():
            circuit_states[cb.state] = circuit_states.get(cb.state, 0) + 1
        
        return {
            "strategy": self.strategy.value,
            "total_providers": len(self.provider_metrics),
            "total_requests": total_requests,
            "total_cost": round(total_cost, 4),
            "average_health_score": round(avg_health_score, 3),
            "circuit_breaker_states": circuit_states,
            "cost_tiers": self.cost_tiers,
            "provider_stats": {
                name: self.get_provider_stats(name)
                for name in self.provider_metrics.keys()
            }
        }
    
    def set_strategy(self, strategy: LoadBalancingStrategy):
        """Change the load balancing strategy"""
        old_strategy = self.strategy
        self.strategy = strategy
        logger.info(f"Load balancing strategy changed from {old_strategy.value} to {strategy.value}")
    
    def update_cost_tiers(self, cost_tiers: Dict[str, List[str]]):
        """Update cost tier configuration"""
        self.cost_tiers = cost_tiers
        logger.info(f"Cost tiers updated: {cost_tiers}")

# Factory functions for different deployment scenarios
def create_single_user_load_balancer(config: Dict[str, Any] = None) -> LoadBalancer:
    """Create load balancer optimized for single-user Home Assistant addon"""
    config = config or {}
    
    strategy_name = config.get("selection_strategy", "weighted_round_robin")
    try:
        strategy = LoadBalancingStrategy(strategy_name)
    except ValueError:
        logger.warning(f"Unknown strategy '{strategy_name}', using weighted_round_robin")
        strategy = LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN
    
    cost_tiers = config.get("cost_optimization_tiers", {
        "performance": ["openai", "anthropic"],
        "balanced": ["google"],
        "economy": ["ollama", "llamacpp_amd"]
    })
    
    return LoadBalancer(strategy=strategy, cost_tiers=cost_tiers)

def create_development_load_balancer() -> LoadBalancer:
    """Create load balancer for development environment with debug-friendly settings"""
    return LoadBalancer(
        strategy=LoadBalancingStrategy.HEALTH_BASED,
        cost_tiers={
            "performance": ["openai", "anthropic"],
            "balanced": ["google"],
            "economy": ["ollama", "llamacpp_amd"]
        }
    )

def create_cost_optimized_load_balancer(cost_tiers: Dict[str, List[str]] = None) -> LoadBalancer:
    """Create load balancer optimized for cost efficiency"""
    return LoadBalancer(
        strategy=LoadBalancingStrategy.COST_OPTIMIZED,
        cost_tiers=cost_tiers or {
            "performance": ["openai", "anthropic"],
            "balanced": ["google"],
            "economy": ["ollama", "llamacpp_amd"]
        }
    )