"""
Tests for Advanced Load Balancing System
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from ai.providers.load_balancer import (
    LoadBalancer,
    LoadBalancingStrategy,
    ProviderMetrics,
    CircuitBreakerState,
    create_single_user_load_balancer,
    create_development_load_balancer,
    create_cost_optimized_load_balancer
)
from ai.providers.base_provider import BaseAIProvider, AIRequest, AIProviderConfiguration, AIProviderStatus


class MockProvider(BaseAIProvider):
    """Mock provider for testing"""
    
    def __init__(self, name: str, priority: int = 1, active_requests: int = 0, 
                 supports_vision: bool = True, status: AIProviderStatus = AIProviderStatus.HEALTHY):
        config = AIProviderConfiguration(
            name=name,
            priority=priority,
            enabled=True
        )
        super().__init__(config)
        self.status = status
        self._active_requests = {f"req_{i}": time.time() for i in range(active_requests)}
        self._supports_vision = supports_vision
    
    async def initialize(self) -> bool:
        return True
    
    async def health_check(self) -> AIProviderStatus:
        return self.status
    
    async def process_request(self, request: AIRequest):
        pass
    
    async def validate_credentials(self) -> bool:
        return True
    
    def get_model_info(self) -> Dict[str, Any]:
        return {"name": self.config.name}
    
    @property
    def capabilities(self) -> Dict[str, bool]:
        return {
            "vision": self._supports_vision,
            "code_generation": True,
            "instruction_following": True,
            "multimodal": self._supports_vision,
            "local_model": self.config.name in ["ollama", "llamacpp_amd"]
        }


class TestProviderMetrics:
    """Test ProviderMetrics class"""
    
    def test_metrics_initialization(self):
        """Test metrics initialization"""
        metrics = ProviderMetrics()
        
        assert metrics.ewma_latency == 1.0
        assert metrics.success_count == 0
        assert metrics.error_count == 0
        assert metrics.total_requests == 0
        assert metrics.health_score == 1.0
        assert metrics.availability_score == 1.0
        assert metrics.reliability_score == 1.0
        assert metrics.total_cost == 0.0
        assert metrics.cost_per_request == 0.0
    
    def test_metrics_update_success(self):
        """Test metrics update for successful request"""
        metrics = ProviderMetrics()
        
        # Update with successful request
        metrics.update_request(success=True, latency=2.0, cost=0.05)
        
        assert metrics.total_requests == 1
        assert metrics.success_count == 1
        assert metrics.error_count == 0
        assert metrics.total_cost == 0.05
        assert metrics.cost_per_request == 0.05
        assert metrics.reliability_score == 1.0
        assert metrics.health_score > 0.5  # Should be high for successful request
    
    def test_metrics_update_failure(self):
        """Test metrics update for failed request"""
        metrics = ProviderMetrics()
        
        # Update with failed request
        metrics.update_request(success=False, latency=10.0, cost=0.0)
        
        assert metrics.total_requests == 1
        assert metrics.success_count == 0
        assert metrics.error_count == 1
        assert metrics.reliability_score == 0.0
        assert metrics.health_score < 0.5  # Should be low for failed request
    
    def test_metrics_ewma_latency(self):
        """Test EWMA latency calculation"""
        metrics = ProviderMetrics()
        
        # First request with 3 second latency
        metrics.update_request(success=True, latency=3.0)
        first_ewma = metrics.ewma_latency
        
        # Second request with 1 second latency
        metrics.update_request(success=True, latency=1.0)
        second_ewma = metrics.ewma_latency
        
        # EWMA should be between the two values, closer to the first due to low alpha
        assert second_ewma < first_ewma
        assert second_ewma > 1.0 / 15.0  # Normalized 1 second
    
    def test_metrics_get_recent_performance(self):
        """Test recent performance calculation"""
        metrics = ProviderMetrics()
        
        # Add some requests
        metrics.update_request(success=True, latency=1.0)
        metrics.update_request(success=True, latency=2.0)
        metrics.update_request(success=False, latency=5.0)
        
        recent = metrics.get_recent_performance()
        
        assert recent["success_rate"] == 2/3
        assert recent["avg_latency"] == (1.0 + 2.0 + 5.0) / 3
        assert recent["request_count"] == 3
    
    def test_metrics_health_score_calculation(self):
        """Test health score calculation"""
        metrics = ProviderMetrics()
        
        # All successful requests with low latency
        for _ in range(10):
            metrics.update_request(success=True, latency=0.5)
        
        # Health score should be high
        assert metrics.health_score > 0.8
        
        # Add some failures
        for _ in range(5):
            metrics.update_request(success=False, latency=10.0)
        
        # Health score should decrease
        assert metrics.health_score < 0.8


class TestCircuitBreakerState:
    """Test CircuitBreakerState class"""
    
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization"""
        cb = CircuitBreakerState()
        
        assert cb.state == "closed"
        assert cb.failure_count == 0
        assert not cb.is_open()
    
    def test_circuit_breaker_open_on_failures(self):
        """Test circuit breaker opens on failures"""
        cb = CircuitBreakerState(max_failures=2)
        
        # First failure
        cb.record_failure()
        assert cb.state == "closed"
        assert not cb.is_open()
        
        # Second failure - should open
        cb.record_failure()
        assert cb.state == "open"
        assert cb.is_open()
    
    def test_circuit_breaker_half_open_transition(self):
        """Test circuit breaker transitions to half-open"""
        cb = CircuitBreakerState(max_failures=1, timeout_duration=0.1)
        
        # Trigger failure to open
        cb.record_failure()
        assert cb.is_open()
        
        # Wait for timeout
        time.sleep(0.2)
        
        # Should transition to half-open
        assert not cb.is_open()
        assert cb.state == "half-open"
    
    def test_circuit_breaker_success_recovery(self):
        """Test circuit breaker recovery on success"""
        cb = CircuitBreakerState(max_failures=1)
        
        # Open the breaker
        cb.record_failure()
        assert cb.is_open()
        
        # Force half-open state
        cb.state = "half-open"
        
        # Record success should close
        cb.record_success()
        assert cb.state == "closed"
        assert cb.failure_count == 0
        assert not cb.is_open()


class TestLoadBalancer:
    """Test LoadBalancer class"""
    
    def test_load_balancer_initialization(self):
        """Test load balancer initialization"""
        lb = LoadBalancer(strategy=LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN)
        
        assert lb.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN
        assert len(lb.provider_metrics) == 0
        assert len(lb.circuit_breakers) == 0
        assert lb.cost_tiers is not None
    
    def test_register_provider(self):
        """Test provider registration"""
        lb = LoadBalancer()
        
        lb.register_provider("test_provider")
        
        assert "test_provider" in lb.provider_metrics
        assert "test_provider" in lb.circuit_breakers
        assert isinstance(lb.provider_metrics["test_provider"], ProviderMetrics)
        assert isinstance(lb.circuit_breakers["test_provider"], CircuitBreakerState)
    
    def test_unregister_provider(self):
        """Test provider unregistration"""
        lb = LoadBalancer()
        
        lb.register_provider("test_provider")
        lb.unregister_provider("test_provider")
        
        assert "test_provider" not in lb.provider_metrics
        assert "test_provider" not in lb.circuit_breakers
    
    def test_update_provider_metrics(self):
        """Test provider metrics update"""
        lb = LoadBalancer()
        
        # Update metrics for non-existent provider (should auto-register)
        lb.update_provider_metrics("test_provider", success=True, latency=1.5, cost=0.02)
        
        assert "test_provider" in lb.provider_metrics
        metrics = lb.provider_metrics["test_provider"]
        assert metrics.total_requests == 1
        assert metrics.success_count == 1
        assert metrics.total_cost == 0.02
    
    def test_select_provider_priority(self):
        """Test priority-based provider selection"""
        lb = LoadBalancer(strategy=LoadBalancingStrategy.PRIORITY)
        
        # Create mock providers with different priorities
        providers = {
            "high_priority": MockProvider("high_priority", priority=1),
            "low_priority": MockProvider("low_priority", priority=3),
            "medium_priority": MockProvider("medium_priority", priority=2)
        }
        
        request = AIRequest(request_id="test", prompt="test prompt")
        
        # Register providers
        for name in providers:
            lb.register_provider(name)
        
        # Should select highest priority (lowest number)
        selected = lb.select_provider(providers, request)
        assert selected == "high_priority"
    
    def test_select_provider_least_connections(self):
        """Test least connections provider selection"""
        lb = LoadBalancer(strategy=LoadBalancingStrategy.LEAST_CONNECTIONS)
        
        # Create mock providers with different active requests
        providers = {
            "busy_provider": MockProvider("busy_provider", active_requests=5),
            "idle_provider": MockProvider("idle_provider", active_requests=0),
            "medium_provider": MockProvider("medium_provider", active_requests=2)
        }
        
        request = AIRequest(request_id="test", prompt="test prompt")
        
        # Register providers
        for name in providers:
            lb.register_provider(name)
        
        # Should select provider with least active requests
        selected = lb.select_provider(providers, request)
        assert selected == "idle_provider"
    
    def test_select_provider_cost_optimized(self):
        """Test cost-optimized provider selection"""
        lb = LoadBalancer(
            strategy=LoadBalancingStrategy.COST_OPTIMIZED,
            cost_tiers={
                "performance": ["expensive_provider"],
                "balanced": ["medium_provider"],
                "economy": ["cheap_provider"]
            }
        )
        
        # Create mock providers
        providers = {
            "expensive_provider": MockProvider("expensive_provider"),
            "medium_provider": MockProvider("medium_provider"),
            "cheap_provider": MockProvider("cheap_provider")
        }
        
        # Register providers with different health scores
        for name in providers:
            lb.register_provider(name)
        
        # Make cheap provider have good health score
        lb.update_provider_metrics("cheap_provider", success=True, latency=1.0)
        
        # Request with economy tier preference
        request = AIRequest(
            request_id="test",
            prompt="test prompt",
            context={"quality_tier": "economy"}
        )
        
        selected = lb.select_provider(providers, request)
        assert selected == "cheap_provider"
    
    def test_select_provider_response_time(self):
        """Test response time-based provider selection"""
        lb = LoadBalancer(strategy=LoadBalancingStrategy.RESPONSE_TIME)
        
        # Create mock providers
        providers = {
            "slow_provider": MockProvider("slow_provider"),
            "fast_provider": MockProvider("fast_provider"),
            "medium_provider": MockProvider("medium_provider")
        }
        
        # Register and update metrics
        for name in providers:
            lb.register_provider(name)
        
        # Update with different latencies
        lb.update_provider_metrics("slow_provider", success=True, latency=5.0)
        lb.update_provider_metrics("fast_provider", success=True, latency=1.0)
        lb.update_provider_metrics("medium_provider", success=True, latency=3.0)
        
        request = AIRequest(request_id="test", prompt="test prompt")
        
        # Should select fastest provider
        selected = lb.select_provider(providers, request)
        assert selected == "fast_provider"
    
    def test_select_provider_vision_capability(self):
        """Test provider selection with vision capability requirement"""
        lb = LoadBalancer()
        
        # Create providers with different vision capabilities
        providers = {
            "vision_provider": MockProvider("vision_provider", supports_vision=True),
            "text_provider": MockProvider("text_provider", supports_vision=False)
        }
        
        # Register providers
        for name in providers:
            lb.register_provider(name)
        
        # Image request
        request = AIRequest(
            request_id="test",
            prompt="Analyze this image",
            image_path="/path/to/image.jpg"
        )
        
        selected = lb.select_provider(providers, request)
        assert selected == "vision_provider"
    
    def test_select_provider_circuit_breaker_filtering(self):
        """Test provider filtering based on circuit breaker state"""
        lb = LoadBalancer()
        
        # Create providers
        providers = {
            "healthy_provider": MockProvider("healthy_provider"),
            "broken_provider": MockProvider("broken_provider")
        }
        
        # Register providers
        for name in providers:
            lb.register_provider(name)
        
        # Trip circuit breaker for broken provider
        cb = lb.circuit_breakers["broken_provider"]
        cb.state = "open"
        cb.last_failure_time = time.time()
        
        request = AIRequest(request_id="test", prompt="test prompt")
        
        # Should only select healthy provider
        selected = lb.select_provider(providers, request)
        assert selected == "healthy_provider"
    
    def test_select_provider_health_score_filtering(self):
        """Test provider filtering based on health score"""
        lb = LoadBalancer()
        
        # Create providers
        providers = {
            "healthy_provider": MockProvider("healthy_provider"),
            "unhealthy_provider": MockProvider("unhealthy_provider")
        }
        
        # Register providers
        for name in providers:
            lb.register_provider(name)
        
        # Make one provider unhealthy
        for _ in range(10):
            lb.update_provider_metrics("unhealthy_provider", success=False, latency=10.0)
        
        # Make other provider healthy
        for _ in range(5):
            lb.update_provider_metrics("healthy_provider", success=True, latency=1.0)
        
        request = AIRequest(request_id="test", prompt="test prompt")
        
        # Should select healthy provider
        selected = lb.select_provider(providers, request)
        assert selected == "healthy_provider"
    
    def test_get_provider_stats(self):
        """Test provider statistics retrieval"""
        lb = LoadBalancer()
        
        lb.register_provider("test_provider")
        lb.update_provider_metrics("test_provider", success=True, latency=2.0, cost=0.03)
        
        stats = lb.get_provider_stats("test_provider")
        
        assert stats["provider_name"] == "test_provider"
        assert stats["total_requests"] == 1
        assert stats["success_count"] == 1
        assert stats["error_count"] == 0
        assert stats["total_cost"] == 0.03
        assert "health_score" in stats
        assert "recent_performance" in stats
    
    def test_get_load_balancer_stats(self):
        """Test load balancer statistics retrieval"""
        lb = LoadBalancer()
        
        lb.register_provider("provider1")
        lb.register_provider("provider2")
        
        lb.update_provider_metrics("provider1", success=True, latency=1.0, cost=0.02)
        lb.update_provider_metrics("provider2", success=True, latency=2.0, cost=0.03)
        
        stats = lb.get_load_balancer_stats()
        
        assert stats["strategy"] == lb.strategy.value
        assert stats["total_providers"] == 2
        assert stats["total_requests"] == 2
        assert stats["total_cost"] == 0.05
        assert "provider_stats" in stats
        assert len(stats["provider_stats"]) == 2
    
    def test_set_strategy(self):
        """Test strategy change"""
        lb = LoadBalancer(strategy=LoadBalancingStrategy.PRIORITY)
        
        assert lb.strategy == LoadBalancingStrategy.PRIORITY
        
        lb.set_strategy(LoadBalancingStrategy.LEAST_CONNECTIONS)
        
        assert lb.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS
    
    def test_update_cost_tiers(self):
        """Test cost tier updates"""
        lb = LoadBalancer()
        
        original_tiers = lb.cost_tiers.copy()
        
        new_tiers = {
            "premium": ["provider1"],
            "standard": ["provider2"],
            "budget": ["provider3"]
        }
        
        lb.update_cost_tiers(new_tiers)
        
        assert lb.cost_tiers == new_tiers
        assert lb.cost_tiers != original_tiers


class TestFactoryFunctions:
    """Test load balancer factory functions"""
    
    def test_create_single_user_load_balancer(self):
        """Test single user load balancer creation"""
        config = {
            "selection_strategy": "least_connections",
            "cost_optimization_tiers": {
                "high": ["provider1"],
                "low": ["provider2"]
            }
        }
        
        lb = create_single_user_load_balancer(config)
        
        assert lb.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS
        assert lb.cost_tiers == config["cost_optimization_tiers"]
    
    def test_create_single_user_load_balancer_defaults(self):
        """Test single user load balancer with defaults"""
        lb = create_single_user_load_balancer()
        
        assert lb.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN
        assert "performance" in lb.cost_tiers
        assert "balanced" in lb.cost_tiers
        assert "economy" in lb.cost_tiers
    
    def test_create_single_user_load_balancer_invalid_strategy(self):
        """Test single user load balancer with invalid strategy"""
        config = {"selection_strategy": "invalid_strategy"}
        
        lb = create_single_user_load_balancer(config)
        
        # Should fall back to default
        assert lb.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN
    
    def test_create_development_load_balancer(self):
        """Test development load balancer creation"""
        lb = create_development_load_balancer()
        
        assert lb.strategy == LoadBalancingStrategy.HEALTH_BASED
        assert isinstance(lb.cost_tiers, dict)
    
    def test_create_cost_optimized_load_balancer(self):
        """Test cost-optimized load balancer creation"""
        custom_tiers = {
            "expensive": ["provider1"],
            "cheap": ["provider2"]
        }
        
        lb = create_cost_optimized_load_balancer(custom_tiers)
        
        assert lb.strategy == LoadBalancingStrategy.COST_OPTIMIZED
        assert lb.cost_tiers == custom_tiers
    
    def test_create_cost_optimized_load_balancer_defaults(self):
        """Test cost-optimized load balancer with defaults"""
        lb = create_cost_optimized_load_balancer()
        
        assert lb.strategy == LoadBalancingStrategy.COST_OPTIMIZED
        assert "performance" in lb.cost_tiers


class TestIntegrationScenarios:
    """Test realistic integration scenarios"""
    
    def test_home_assistant_addon_scenario(self):
        """Test typical Home Assistant addon usage"""
        # Create load balancer for HA addon
        config = {
            "selection_strategy": "weighted_round_robin",
            "cost_optimization_tiers": {
                "performance": ["openai", "anthropic"],
                "balanced": ["google"],
                "economy": ["ollama"]
            }
        }
        
        lb = create_single_user_load_balancer(config)
        
        # Create providers typical for HA addon
        providers = {
            "openai": MockProvider("openai", priority=1),
            "google": MockProvider("google", priority=2),
            "ollama": MockProvider("ollama", priority=3)
        }
        
        # Register providers
        for name in providers:
            lb.register_provider(name)
        
        # Simulate some requests with different outcomes
        requests = [
            AIRequest(request_id="req1", prompt="Clean the kitchen"),
            AIRequest(request_id="req2", prompt="Analyze image", image_path="/path/to/image.jpg"),
            AIRequest(request_id="req3", prompt="Generate tasks", context={"quality_tier": "economy"})
        ]
        
        # Process requests
        for request in requests:
            selected = lb.select_provider(providers, request)
            assert selected is not None
            
            # Simulate processing
            success = True
            latency = 2.0
            cost = 0.01
            
            lb.update_provider_metrics(selected, success, latency, cost)
        
        # Check stats
        stats = lb.get_load_balancer_stats()
        assert stats["total_requests"] >= 3
        assert stats["total_cost"] >= 0.03
    
    def test_provider_failure_handling(self):
        """Test handling of provider failures"""
        lb = LoadBalancer(strategy=LoadBalancingStrategy.HEALTH_BASED)
        
        # Create providers
        providers = {
            "reliable_provider": MockProvider("reliable_provider"),
            "unreliable_provider": MockProvider("unreliable_provider")
        }
        
        # Register providers
        for name in providers:
            lb.register_provider(name)
        
        # Simulate reliable provider success
        for _ in range(10):
            lb.update_provider_metrics("reliable_provider", success=True, latency=1.0)
        
        # Simulate unreliable provider failures
        for _ in range(10):
            lb.update_provider_metrics("unreliable_provider", success=False, latency=10.0)
        
        request = AIRequest(request_id="test", prompt="test")
        
        # Should prefer reliable provider
        selected = lb.select_provider(providers, request)
        assert selected == "reliable_provider"
        
        # Check that unreliable provider has low health score
        unreliable_stats = lb.get_provider_stats("unreliable_provider")
        assert unreliable_stats["health_score"] < 0.5
    
    def test_cost_optimization_scenario(self):
        """Test cost optimization behavior"""
        lb = LoadBalancer(
            strategy=LoadBalancingStrategy.COST_OPTIMIZED,
            cost_tiers={
                "performance": ["expensive"],
                "balanced": ["medium"],
                "economy": ["cheap"]
            }
        )
        
        # Create providers
        providers = {
            "expensive": MockProvider("expensive"),
            "medium": MockProvider("medium"),
            "cheap": MockProvider("cheap")
        }
        
        # Register providers
        for name in providers:
            lb.register_provider(name)
        
        # Make all providers equally healthy
        for name in providers:
            lb.update_provider_metrics(name, success=True, latency=1.0)
        
        # Test requests with different quality tiers
        performance_request = AIRequest(
            request_id="perf", 
            prompt="test",
            context={"quality_tier": "performance"}
        )
        
        economy_request = AIRequest(
            request_id="econ", 
            prompt="test",
            context={"quality_tier": "economy"}
        )
        
        # Should select appropriate providers
        perf_selected = lb.select_provider(providers, performance_request)
        econ_selected = lb.select_provider(providers, economy_request)
        
        assert perf_selected == "expensive"
        assert econ_selected == "cheap"
    
    def test_circuit_breaker_scenario(self):
        """Test circuit breaker behavior"""
        lb = LoadBalancer()
        
        # Create providers
        providers = {
            "failing_provider": MockProvider("failing_provider"),
            "backup_provider": MockProvider("backup_provider")
        }
        
        # Register providers
        for name in providers:
            lb.register_provider(name)
        
        # Trip circuit breaker on failing provider
        for _ in range(5):
            lb.update_provider_metrics("failing_provider", success=False, latency=10.0)
        
        # Circuit breaker should be open
        cb = lb.circuit_breakers["failing_provider"]
        assert cb.is_open()
        
        request = AIRequest(request_id="test", prompt="test")
        
        # Should select backup provider
        selected = lb.select_provider(providers, request)
        assert selected == "backup_provider"
    
    def test_dynamic_weight_adjustment(self):
        """Test dynamic weight adjustment in weighted round robin"""
        lb = LoadBalancer(strategy=LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN)
        
        # Create providers
        providers = {
            "good_provider": MockProvider("good_provider"),
            "bad_provider": MockProvider("bad_provider")
        }
        
        # Register providers
        for name in providers:
            lb.register_provider(name)
        
        # Make one provider perform well
        for _ in range(10):
            lb.update_provider_metrics("good_provider", success=True, latency=1.0)
        
        # Make other provider perform poorly
        for _ in range(10):
            lb.update_provider_metrics("bad_provider", success=False, latency=10.0)
        
        request = AIRequest(request_id="test", prompt="test")
        
        # Run multiple selections - should favor good provider
        selections = []
        for _ in range(20):
            selected = lb.select_provider(providers, request)
            selections.append(selected)
        
        # Good provider should be selected more often
        good_count = selections.count("good_provider")
        bad_count = selections.count("bad_provider")
        
        assert good_count > bad_count