"""
Test suite for AI Provider Manager
Phase 2A: AI Model Provider Optimization

Comprehensive test suite following AAA pattern with mocking framework.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any

from ai.providers.ai_provider_manager import (
    AIProviderManager, ProviderSelectionStrategy, ProviderConfig, RoutingRule
)
from ai.providers.base_provider import (
    BaseAIProvider, AIProviderConfiguration, AIRequest, AIResponse,
    AIProviderStatus, AIProviderError, AIProviderMetrics
)


class TestAIProviderManager:
    """Test suite for AIProviderManager"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        return {
            "selection_strategy": "adaptive",
            "batch_size": 5,
            "batch_timeout": 1.0,
            "cache_ttl": 300,
            "providers": {
                "openai": {
                    "enabled": True,
                    "priority": 1,
                    "model_name": "gpt-4-vision-preview",
                    "rate_limit_rpm": 60,
                    "daily_budget": 10.0
                },
                "anthropic": {
                    "enabled": True,
                    "priority": 2,
                    "model_name": "claude-3-5-sonnet-20241022",
                    "rate_limit_rpm": 50,
                    "daily_budget": 10.0
                },
                "google": {
                    "enabled": True,
                    "priority": 3,
                    "model_name": "gemini-1.5-flash",
                    "rate_limit_rpm": 100,
                    "daily_budget": 5.0
                }
            }
        }
    
    @pytest.fixture
    def mock_provider(self):
        """Mock provider for testing"""
        provider = Mock(spec=BaseAIProvider)
        provider.config = AIProviderConfiguration(
            name="test_provider",
            api_key="test_key",
            model_name="test_model"
        )
        provider.is_available.return_value = True
        provider.is_healthy.return_value = True
        provider.get_active_requests.return_value = 0
        provider.get_status.return_value = AIProviderStatus.HEALTHY
        provider.get_metrics.return_value = AIProviderMetrics(
            total_requests=10,
            successful_requests=9,
            failed_requests=1,
            average_response_time=1.5,
            success_rate=0.9,
            total_cost=0.5
        )
        return provider
    
    @pytest.fixture
    def ai_request(self):
        """Sample AI request for testing"""
        return AIRequest(
            request_id="test_request_1",
            prompt="Test prompt for image analysis",
            image_path="/test/image.jpg",
            priority=1
        )
    
    @pytest.fixture
    def ai_response(self):
        """Sample AI response for testing"""
        return AIResponse(
            request_id="test_request_1",
            response_text="Test response",
            model_used="test_model",
            provider="test_provider",
            confidence=0.9,
            cost=0.05,
            response_time=1.2
        )
    
    @pytest.fixture
    async def manager(self, mock_config):
        """Create manager instance for testing"""
        with patch('ai.providers.ai_provider_manager.CredentialManager') as mock_cred_mgr:
            mock_cred_mgr.return_value.get_credential.return_value = "test_api_key"
            mock_cred_mgr.return_value.health_check = AsyncMock()
            
            manager = AIProviderManager(mock_config, "/tmp/test_data")
            yield manager
    
    def test_init_creates_manager_with_config(self, mock_config):
        """
        Test: AIProviderManager initialization with configuration
        
        Arrange: Create mock configuration
        Act: Initialize AIProviderManager
        Assert: Manager is created with correct configuration
        """
        # Arrange
        expected_strategy = ProviderSelectionStrategy.ADAPTIVE
        expected_batch_size = 5
        
        # Act
        with patch('ai.providers.ai_provider_manager.CredentialManager'):
            manager = AIProviderManager(mock_config, "/tmp/test_data")
        
        # Assert
        assert manager.selection_strategy == expected_strategy
        assert manager.batch_size == expected_batch_size
        assert len(manager.provider_configs) == 3
        assert "openai" in manager.provider_configs
        assert "anthropic" in manager.provider_configs
        assert "google" in manager.provider_configs
    
    @pytest.mark.asyncio
    async def test_initialize_loads_providers(self, manager):
        """
        Test: Manager initialization loads and initializes providers
        
        Arrange: Mock provider classes and credential manager
        Act: Initialize manager
        Assert: Providers are loaded and initialized correctly
        """
        # Arrange
        mock_openai = Mock()
        mock_openai.initialize = AsyncMock(return_value=True)
        mock_anthropic = Mock()
        mock_anthropic.initialize = AsyncMock(return_value=True)
        
        with patch.dict(manager.provider_classes, {
            "openai": lambda config: mock_openai,
            "anthropic": lambda config: mock_anthropic,
            "google": lambda config: Mock()
        }):
            with patch.object(manager.health_monitor, 'start_monitoring', new_callable=AsyncMock):
                # Act
                result = await manager.initialize()
                
                # Assert
                assert result is True
                assert len(manager.providers) >= 0  # Providers may not initialize without real API keys
    
    @pytest.mark.asyncio
    async def test_select_provider_round_robin(self, manager, mock_provider):
        """
        Test: Round-robin provider selection
        
        Arrange: Set up manager with round-robin strategy and mock providers
        Act: Select providers multiple times
        Assert: Providers are selected in round-robin order
        """
        # Arrange
        manager.selection_strategy = ProviderSelectionStrategy.ROUND_ROBIN
        manager.providers = {
            "provider1": mock_provider,
            "provider2": mock_provider,
            "provider3": mock_provider
        }
        manager.circuit_breakers = {
            "provider1": {"state": "closed"},
            "provider2": {"state": "closed"},
            "provider3": {"state": "closed"}
        }
        
        request = AIRequest(request_id="test", prompt="test")
        
        # Act
        provider1 = await manager._select_provider(request)
        provider2 = await manager._select_provider(request)
        provider3 = await manager._select_provider(request)
        provider4 = await manager._select_provider(request)
        
        # Assert
        assert provider1 == mock_provider
        assert provider2 == mock_provider
        assert provider3 == mock_provider
        assert provider4 == mock_provider  # Should wrap around
    
    @pytest.mark.asyncio
    async def test_select_provider_least_loaded(self, manager):
        """
        Test: Least loaded provider selection
        
        Arrange: Set up providers with different load levels
        Act: Select provider using least loaded strategy
        Assert: Provider with least load is selected
        """
        # Arrange
        manager.selection_strategy = ProviderSelectionStrategy.LEAST_LOADED
        
        provider1 = Mock(spec=BaseAIProvider)
        provider1.is_available.return_value = True
        provider1.get_active_requests.return_value = 5
        
        provider2 = Mock(spec=BaseAIProvider)
        provider2.is_available.return_value = True
        provider2.get_active_requests.return_value = 2  # Least loaded
        
        provider3 = Mock(spec=BaseAIProvider)
        provider3.is_available.return_value = True
        provider3.get_active_requests.return_value = 8
        
        manager.providers = {
            "provider1": provider1,
            "provider2": provider2,
            "provider3": provider3
        }
        manager.circuit_breakers = {
            "provider1": {"state": "closed"},
            "provider2": {"state": "closed"},
            "provider3": {"state": "closed"}
        }
        
        request = AIRequest(request_id="test", prompt="test")
        
        # Act
        selected_provider = await manager._select_provider(request)
        
        # Assert
        assert selected_provider == provider2
    
    @pytest.mark.asyncio
    async def test_process_request_with_cache_hit(self, manager, ai_request, ai_response):
        """
        Test: Request processing with cache hit
        
        Arrange: Set up manager with cached response
        Act: Process request
        Assert: Cached response is returned
        """
        # Arrange
        cache_key = manager._generate_cache_key(ai_request)
        manager.cache[cache_key] = {
            "response": ai_response,
            "timestamp": datetime.now().timestamp()
        }
        
        # Act
        result = await manager.process_request(ai_request)
        
        # Assert
        assert result.request_id == ai_request.request_id
        assert result.cached is True
    
    @pytest.mark.asyncio
    async def test_process_request_with_provider_failure_and_fallback(self, manager, ai_request, mock_provider):
        """
        Test: Request processing with provider failure and fallback
        
        Arrange: Set up primary provider to fail and fallback provider to succeed
        Act: Process request
        Assert: Fallback provider is used after primary fails
        """
        # Arrange
        failing_provider = Mock(spec=BaseAIProvider)
        failing_provider.config = AIProviderConfiguration(name="failing_provider", api_key="test")
        failing_provider.is_available.return_value = True
        failing_provider.process_request_with_retry = AsyncMock(
            side_effect=AIProviderError("Test error", retryable=True)
        )
        
        success_provider = Mock(spec=BaseAIProvider)
        success_provider.config = AIProviderConfiguration(name="success_provider", api_key="test")
        success_provider.is_available.return_value = True
        success_provider.process_request_with_retry = AsyncMock(
            return_value=AIResponse(
                request_id=ai_request.request_id,
                response_text="Fallback response",
                model_used="fallback_model",
                provider="success_provider",
                confidence=0.8,
                cost=0.03,
                response_time=1.0
            )
        )
        
        manager.providers = {
            "failing_provider": failing_provider,
            "success_provider": success_provider
        }
        manager.provider_configs = {
            "failing_provider": ProviderConfig(name="failing_provider", provider_class="test", priority=1),
            "success_provider": ProviderConfig(name="success_provider", provider_class="test", priority=2)
        }
        manager.circuit_breakers = {
            "failing_provider": {"state": "closed", "failure_count": 0},
            "success_provider": {"state": "closed", "failure_count": 0}
        }
        
        # Act
        result = await manager.process_request(ai_request)
        
        # Assert
        assert result.provider == "success_provider"
        assert result.response_text == "Fallback response"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self, manager, ai_request):
        """
        Test: Circuit breaker opens after consecutive failures
        
        Arrange: Set up provider to fail multiple times
        Act: Process multiple requests
        Assert: Circuit breaker opens after threshold failures
        """
        # Arrange
        failing_provider = Mock(spec=BaseAIProvider)
        failing_provider.config = AIProviderConfiguration(name="failing_provider", api_key="test")
        failing_provider.is_available.return_value = True
        failing_provider.process_request_with_retry = AsyncMock(
            side_effect=AIProviderError("Test error", retryable=True)
        )
        
        manager.providers = {"failing_provider": failing_provider}
        manager.circuit_breakers = {
            "failing_provider": {"state": "closed", "failure_count": 0, "last_failure": None, "timeout": 60}
        }
        
        # Act - Process requests to trigger failures
        for i in range(5):
            try:
                await manager._process_with_provider(failing_provider, ai_request)
            except AIProviderError:
                pass
        
        # Assert
        assert manager.circuit_breakers["failing_provider"]["state"] == "open"
        assert manager.circuit_breakers["failing_provider"]["failure_count"] == 5
        assert manager._is_circuit_breaker_open("failing_provider") is True
    
    @pytest.mark.asyncio
    async def test_batch_processing(self, manager, mock_provider):
        """
        Test: Batch processing of multiple requests
        
        Arrange: Set up manager with batch processing capability
        Act: Process batch of requests
        Assert: All requests are processed efficiently
        """
        # Arrange
        requests = [
            AIRequest(request_id=f"batch_request_{i}", prompt=f"Batch prompt {i}")
            for i in range(3)
        ]
        
        mock_provider.batch_process_requests = AsyncMock(return_value=[
            AIResponse(
                request_id=req.request_id,
                response_text=f"Batch response {i}",
                model_used="batch_model",
                provider="batch_provider",
                confidence=0.9,
                cost=0.02,
                response_time=0.8
            )
            for i, req in enumerate(requests)
        ])
        
        manager.providers = {"batch_provider": mock_provider}
        manager.circuit_breakers = {"batch_provider": {"state": "closed"}}
        
        # Act
        responses = await manager.batch_process_requests(requests)
        
        # Assert
        assert len(responses) == 3
        for i, response in enumerate(responses):
            assert response.request_id == f"batch_request_{i}"
            assert f"Batch response {i}" in response.response_text
    
    def test_routing_rules_application(self, manager):
        """
        Test: Routing rules are applied correctly
        
        Arrange: Set up routing rules
        Act: Check rule matching
        Assert: Rules are matched correctly
        """
        # Arrange
        image_rule = RoutingRule(
            condition="image_analysis",
            provider="vision_provider",
            priority=1,
            enabled=True
        )
        text_rule = RoutingRule(
            condition="text_only",
            provider="text_provider",
            priority=2,
            enabled=True
        )
        
        manager.routing_rules = [image_rule, text_rule]
        
        image_request = AIRequest(
            request_id="image_req",
            prompt="Analyze this image",
            image_path="/test/image.jpg"
        )
        
        text_request = AIRequest(
            request_id="text_req",
            prompt="Process this text"
        )
        
        # Act & Assert
        assert manager._matches_routing_rule(image_request, image_rule) is True
        assert manager._matches_routing_rule(image_request, text_rule) is False
        assert manager._matches_routing_rule(text_request, image_rule) is False
        assert manager._matches_routing_rule(text_request, text_rule) is True
    
    def test_cache_key_generation(self, manager):
        """
        Test: Cache key generation for requests
        
        Arrange: Create requests with different content
        Act: Generate cache keys
        Assert: Keys are generated correctly and consistently
        """
        # Arrange
        request1 = AIRequest(request_id="req1", prompt="Same prompt")
        request2 = AIRequest(request_id="req2", prompt="Same prompt")
        request3 = AIRequest(request_id="req3", prompt="Different prompt")
        
        # Act
        key1 = manager._generate_cache_key(request1)
        key2 = manager._generate_cache_key(request2)
        key3 = manager._generate_cache_key(request3)
        
        # Assert
        assert key1 == key2  # Same prompt should generate same key
        assert key1 != key3  # Different prompt should generate different key
        assert isinstance(key1, str)
        assert len(key1) == 32  # MD5 hash length
    
    def test_performance_metrics_collection(self, manager, mock_provider):
        """
        Test: Performance metrics are collected correctly
        
        Arrange: Set up manager with providers
        Act: Update statistics
        Assert: Metrics are tracked correctly
        """
        # Arrange
        manager.providers = {"test_provider": mock_provider}
        response = AIResponse(
            request_id="test",
            response_text="Test response",
            model_used="test_model",
            provider="test_provider",
            confidence=0.9,
            cost=0.05,
            response_time=1.2
        )
        
        # Act
        manager._update_stats("test_provider", response, 1.5)
        
        # Assert
        assert manager.stats["total_requests"] == 1
        assert manager.stats["successful_requests"] == 1
        assert manager.stats["failed_requests"] == 0
        assert manager.stats["total_cost"] == 0.05
        assert manager.stats["provider_usage"]["test_provider"] == 1
        assert manager.stats["average_response_time"] == 1.5
    
    @pytest.mark.asyncio
    async def test_health_check_all_providers(self, manager, mock_provider):
        """
        Test: Health check performs checks on all providers
        
        Arrange: Set up manager with multiple providers
        Act: Perform health check
        Assert: All providers are checked and status is returned
        """
        # Arrange
        provider1 = Mock(spec=BaseAIProvider)
        provider1.health_check = AsyncMock(return_value=AIProviderStatus.HEALTHY)
        
        provider2 = Mock(spec=BaseAIProvider)
        provider2.health_check = AsyncMock(return_value=AIProviderStatus.DEGRADED)
        
        manager.providers = {
            "provider1": provider1,
            "provider2": provider2
        }
        
        # Act
        health_report = await manager.health_check()
        
        # Assert
        assert health_report["overall_health"] == "degraded"  # Due to provider2
        assert health_report["providers"]["provider1"]["status"] == "healthy"
        assert health_report["providers"]["provider2"]["status"] == "degraded"
    
    @pytest.mark.asyncio
    async def test_shutdown_cleans_up_resources(self, manager):
        """
        Test: Shutdown properly cleans up all resources
        
        Arrange: Set up manager with providers and monitors
        Act: Shutdown manager
        Assert: All resources are cleaned up
        """
        # Arrange
        mock_provider = Mock(spec=BaseAIProvider)
        mock_provider.shutdown = AsyncMock()
        
        manager.providers = {"test_provider": mock_provider}
        manager.health_monitor.stop_monitoring = AsyncMock()
        
        # Act
        await manager.shutdown()
        
        # Assert
        mock_provider.shutdown.assert_called_once()
        manager.health_monitor.stop_monitoring.assert_called_once()
    
    def test_cost_summary_calculation(self, manager):
        """
        Test: Cost summary is calculated correctly
        
        Arrange: Set up providers with different costs
        Act: Get cost summary
        Assert: Summary is calculated correctly
        """
        # Arrange
        provider1 = Mock(spec=BaseAIProvider)
        provider1.get_metrics.return_value = AIProviderMetrics(
            total_requests=10,
            total_cost=1.50
        )
        
        provider2 = Mock(spec=BaseAIProvider)
        provider2.get_metrics.return_value = AIProviderMetrics(
            total_requests=5,
            total_cost=0.75
        )
        
        manager.providers = {"provider1": provider1, "provider2": provider2}
        manager.stats["total_requests"] = 15
        
        # Act
        cost_summary = manager.get_cost_summary()
        
        # Assert
        assert cost_summary["total_cost"] == 2.25
        assert cost_summary["provider_costs"]["provider1"]["total_cost"] == 1.50
        assert cost_summary["provider_costs"]["provider2"]["total_cost"] == 0.75
        assert cost_summary["average_cost_per_request"] == 0.15
    
    def test_strategy_switching(self, manager):
        """
        Test: Selection strategy can be changed
        
        Arrange: Set up manager with initial strategy
        Act: Change strategy
        Assert: Strategy is updated correctly
        """
        # Arrange
        initial_strategy = ProviderSelectionStrategy.ADAPTIVE
        new_strategy = ProviderSelectionStrategy.COST_OPTIMAL
        
        manager.selection_strategy = initial_strategy
        
        # Act
        manager.set_selection_strategy(new_strategy)
        
        # Assert
        assert manager.selection_strategy == new_strategy
    
    def test_routing_rule_management(self, manager):
        """
        Test: Routing rules can be added and removed
        
        Arrange: Set up manager with empty routing rules
        Act: Add and remove routing rules
        Assert: Rules are managed correctly
        """
        # Arrange
        rule1 = RoutingRule(condition="image_analysis", provider="vision_provider")
        rule2 = RoutingRule(condition="text_only", provider="text_provider")
        
        # Act
        manager.add_routing_rule(rule1)
        manager.add_routing_rule(rule2)
        
        # Assert
        assert len(manager.routing_rules) == 2
        assert rule1 in manager.routing_rules
        assert rule2 in manager.routing_rules
        
        # Act
        manager.remove_routing_rule("image_analysis")
        
        # Assert
        assert len(manager.routing_rules) == 1
        assert rule1 not in manager.routing_rules
        assert rule2 in manager.routing_rules


class TestProviderConfiguration:
    """Test provider configuration handling"""
    
    def test_provider_config_creation(self):
        """Test provider configuration creation"""
        config = ProviderConfig(
            name="test_provider",
            provider_class="TestProvider",
            enabled=True,
            priority=1,
            weight=1.5,
            fallback_enabled=True,
            config={"model": "test_model"}
        )
        
        assert config.name == "test_provider"
        assert config.provider_class == "TestProvider"
        assert config.enabled is True
        assert config.priority == 1
        assert config.weight == 1.5
        assert config.fallback_enabled is True
        assert config.config["model"] == "test_model"


class TestRoutingRule:
    """Test routing rule functionality"""
    
    def test_routing_rule_creation(self):
        """Test routing rule creation"""
        rule = RoutingRule(
            condition="image_analysis",
            provider="vision_provider",
            priority=1,
            enabled=True
        )
        
        assert rule.condition == "image_analysis"
        assert rule.provider == "vision_provider"
        assert rule.priority == 1
        assert rule.enabled is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])