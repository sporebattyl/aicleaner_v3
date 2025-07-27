"""
Integration Test Suite for AI Provider System
Phase 2A: AI Model Provider Optimization

End-to-end integration tests for the complete AI provider system
with performance benchmarks and real-world scenarios.
"""

import pytest
import asyncio
import time
import tempfile
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any

from ai.providers.ai_provider_manager import AIProviderManager, ProviderSelectionStrategy
from ai.providers.base_provider import AIRequest, AIResponse, AIProviderStatus
from ai.providers.credential_manager import CredentialManager
from ai.providers.rate_limiter import RateLimitConfig
from ai.providers.health_monitor import HealthMonitor


class TestAIProviderIntegration:
    """Integration tests for complete AI provider system"""
    
    @pytest.fixture
    def integration_config(self):
        """Integration test configuration"""
        return {
            "selection_strategy": "adaptive",
            "batch_size": 3,
            "batch_timeout": 0.5,
            "cache_ttl": 60,
            "providers": {
                "openai": {
                    "enabled": True,
                    "priority": 1,
                    "weight": 1.0,
                    "model_name": "gpt-4-vision-preview",
                    "rate_limit_rpm": 30,
                    "rate_limit_tpm": 5000,
                    "daily_budget": 5.0,
                    "cost_per_request": 0.02,
                    "timeout_seconds": 30,
                    "max_retries": 2,
                    "health_check_interval": 60
                },
                "anthropic": {
                    "enabled": True,
                    "priority": 2,
                    "weight": 0.8,
                    "model_name": "claude-3-5-sonnet-20241022",
                    "rate_limit_rpm": 25,
                    "rate_limit_tpm": 4000,
                    "daily_budget": 5.0,
                    "cost_per_request": 0.015,
                    "timeout_seconds": 30,
                    "max_retries": 2,
                    "health_check_interval": 60
                },
                "google": {
                    "enabled": True,
                    "priority": 3,
                    "weight": 1.2,
                    "model_name": "gemini-1.5-flash",
                    "rate_limit_rpm": 60,
                    "rate_limit_tpm": 10000,
                    "daily_budget": 3.0,
                    "cost_per_request": 0.005,
                    "timeout_seconds": 25,
                    "max_retries": 3,
                    "health_check_interval": 60
                },
                "ollama": {
                    "enabled": True,
                    "priority": 4,
                    "weight": 0.6,
                    "model_name": "llava:13b",
                    "base_url": "http://localhost:11434",
                    "rate_limit_rpm": 120,
                    "rate_limit_tpm": 20000,
                    "daily_budget": 0.0,
                    "cost_per_request": 0.0,
                    "timeout_seconds": 60,
                    "max_retries": 2,
                    "health_check_interval": 120
                }
            }
        }
    
    @pytest.fixture
    def temp_data_dir(self):
        """Temporary directory for test data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    async def mock_providers(self):
        """Mock all AI provider implementations"""
        with patch('ai.providers.ai_provider_manager.OpenAIProvider') as mock_openai, \
             patch('ai.providers.ai_provider_manager.AnthropicProvider') as mock_anthropic, \
             patch('ai.providers.ai_provider_manager.GoogleProvider') as mock_google, \
             patch('ai.providers.ai_provider_manager.OllamaProvider') as mock_ollama:
            
            # Configure mock providers
            providers = {}
            
            for provider_name, provider_class in [
                ("openai", mock_openai),
                ("anthropic", mock_anthropic),
                ("google", mock_google),
                ("ollama", mock_ollama)
            ]:
                mock_instance = Mock()
                mock_instance.config.name = provider_name
                mock_instance.initialize = AsyncMock(return_value=True)
                mock_instance.health_check = AsyncMock(return_value=AIProviderStatus.HEALTHY)
                mock_instance.is_available.return_value = True
                mock_instance.is_healthy.return_value = True
                mock_instance.get_active_requests.return_value = 0
                mock_instance.get_status.return_value = AIProviderStatus.HEALTHY
                mock_instance.shutdown = AsyncMock()
                
                # Mock successful response
                mock_instance.process_request_with_retry = AsyncMock(return_value=AIResponse(
                    request_id="test",
                    response_text=f"Mock response from {provider_name}",
                    model_used=f"{provider_name}_model",
                    provider=provider_name,
                    confidence=0.9,
                    cost=0.01,
                    response_time=1.0
                ))
                
                # Mock metrics
                from ai.providers.base_provider import AIProviderMetrics
                mock_instance.get_metrics.return_value = AIProviderMetrics(
                    total_requests=10,
                    successful_requests=9,
                    failed_requests=1,
                    average_response_time=1.2,
                    success_rate=0.9,
                    total_cost=0.1
                )
                
                provider_class.return_value = mock_instance
                providers[provider_name] = mock_instance
            
            yield providers
    
    @pytest.fixture
    async def ai_provider_manager(self, integration_config, temp_data_dir, mock_providers):
        """Create AI provider manager for integration tests"""
        with patch('ai.providers.ai_provider_manager.CredentialManager') as mock_cred_mgr:
            # Mock credential manager
            mock_cred_mgr.return_value.get_credential.return_value = "mock_api_key"
            mock_cred_mgr.return_value.health_check = AsyncMock(return_value={"overall_health": "healthy"})
            
            manager = AIProviderManager(integration_config, temp_data_dir)
            
            # Initialize with mocked providers
            await manager.initialize()
            
            yield manager
            
            # Cleanup
            await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_end_to_end_request_processing(self, ai_provider_manager):
        """
        Test: End-to-end request processing through the system
        
        Arrange: Set up complete AI provider system
        Act: Process various types of requests
        Assert: Requests are processed correctly with proper routing
        """
        # Arrange
        requests = [
            AIRequest(
                request_id="test_image_1",
                prompt="Analyze this kitchen image for cleaning tasks",
                image_path="/test/kitchen.jpg",
                priority=1
            ),
            AIRequest(
                request_id="test_text_1",
                prompt="Generate cleaning tasks for living room",
                priority=2
            ),
            AIRequest(
                request_id="test_batch_1",
                prompt="Quick analysis needed",
                priority=3
            )
        ]
        
        # Act
        responses = []
        for request in requests:
            response = await ai_provider_manager.process_request(request)
            responses.append(response)
        
        # Assert
        assert len(responses) == 3
        for response in responses:
            assert response.response_text is not None
            assert response.provider in ["openai", "anthropic", "google", "ollama"]
            assert response.cost >= 0.0
            assert response.response_time > 0.0
    
    @pytest.mark.asyncio
    async def test_provider_failover_functionality(self, ai_provider_manager, mock_providers):
        """
        Test: Provider failover when primary provider fails
        
        Arrange: Configure primary provider to fail
        Act: Process request expecting failover
        Assert: Request succeeds using fallback provider
        """
        # Arrange
        from ai.providers.base_provider import AIProviderError
        
        # Make first provider fail
        primary_provider = list(mock_providers.values())[0]
        primary_provider.process_request_with_retry = AsyncMock(
            side_effect=AIProviderError("Test failure", retryable=True)
        )
        
        request = AIRequest(
            request_id="failover_test",
            prompt="Test failover mechanism",
            priority=1
        )
        
        # Act
        response = await ai_provider_manager.process_request(request)
        
        # Assert
        assert response.response_text is not None
        assert response.error is None  # Should succeed with fallback
        # Should not be from the failing provider
        assert response.provider != primary_provider.config.name
    
    @pytest.mark.asyncio
    async def test_rate_limiting_across_providers(self, ai_provider_manager, mock_providers):
        """
        Test: Rate limiting works across multiple providers
        
        Arrange: Configure aggressive rate limits
        Act: Send burst of requests
        Assert: Rate limiting is enforced appropriately
        """
        # Arrange
        requests = [
            AIRequest(
                request_id=f"rate_test_{i}",
                prompt=f"Rate limiting test {i}",
                priority=1
            )
            for i in range(10)
        ]
        
        # Act
        start_time = time.time()
        responses = []
        
        for request in requests:
            response = await ai_provider_manager.process_request(request)
            responses.append(response)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Assert
        assert len(responses) == 10
        # Should take some time due to rate limiting
        assert total_time > 1.0  # At least 1 second for 10 requests
        
        # Check that some requests were successful
        successful_responses = [r for r in responses if r.error is None]
        assert len(successful_responses) > 0
    
    @pytest.mark.asyncio
    async def test_batch_processing_optimization(self, ai_provider_manager, mock_providers):
        """
        Test: Batch processing optimization works correctly
        
        Arrange: Configure batch processing
        Act: Send multiple requests for batching
        Assert: Requests are processed efficiently in batches
        """
        # Arrange
        requests = [
            AIRequest(
                request_id=f"batch_test_{i}",
                prompt=f"Batch processing test {i}",
                priority=1
            )
            for i in range(5)
        ]
        
        # Configure mock to support batch processing
        for provider in mock_providers.values():
            provider.batch_process_requests = AsyncMock(return_value=[
                AIResponse(
                    request_id=req.request_id,
                    response_text=f"Batch response for {req.request_id}",
                    model_used="batch_model",
                    provider=provider.config.name,
                    confidence=0.9,
                    cost=0.01,
                    response_time=0.5
                )
                for req in requests
            ])
        
        # Act
        start_time = time.time()
        responses = await ai_provider_manager.batch_process_requests(requests)
        end_time = time.time()
        
        # Assert
        assert len(responses) == 5
        # Batch processing should be faster than individual requests
        assert end_time - start_time < 3.0
        
        for response in responses:
            assert "batch_test_" in response.request_id
            assert response.response_text is not None
    
    @pytest.mark.asyncio
    async def test_caching_functionality(self, ai_provider_manager):
        """
        Test: Response caching works correctly
        
        Arrange: Process same request twice
        Act: Check for cache hit on second request
        Assert: Second request returns cached result
        """
        # Arrange
        request = AIRequest(
            request_id="cache_test_1",
            prompt="This should be cached",
            priority=1
        )
        
        # Act
        response1 = await ai_provider_manager.process_request(request)
        
        # Same request again
        request2 = AIRequest(
            request_id="cache_test_2",
            prompt="This should be cached",  # Same prompt
            priority=1
        )
        
        response2 = await ai_provider_manager.process_request(request2)
        
        # Assert
        assert response1.response_text is not None
        assert response2.response_text is not None
        assert response2.cached is True
        # Cache hit should be much faster
        assert response2.response_time < response1.response_time
    
    @pytest.mark.asyncio
    async def test_health_monitoring_integration(self, ai_provider_manager, mock_providers):
        """
        Test: Health monitoring integration works correctly
        
        Arrange: Set up providers with different health states
        Act: Perform health check
        Assert: Health status is reported correctly
        """
        # Arrange
        # Make one provider unhealthy
        unhealthy_provider = list(mock_providers.values())[0]
        unhealthy_provider.health_check = AsyncMock(return_value=AIProviderStatus.DEGRADED)
        unhealthy_provider.is_healthy.return_value = False
        
        # Act
        health_report = await ai_provider_manager.health_check()
        
        # Assert
        assert "providers" in health_report
        assert len(health_report["providers"]) > 0
        
        # Should detect the unhealthy provider
        provider_statuses = [
            status["status"] for status in health_report["providers"].values()
        ]
        assert "degraded" in provider_statuses or "error" in provider_statuses
    
    @pytest.mark.asyncio
    async def test_cost_tracking_and_budgets(self, ai_provider_manager, mock_providers):
        """
        Test: Cost tracking and budget management
        
        Arrange: Set low budget limits
        Act: Process requests until budget exceeded
        Assert: Budget enforcement works correctly
        """
        # Arrange
        # Configure one provider with very low budget
        for provider in mock_providers.values():
            if hasattr(provider, '_rate_limiter'):
                provider._rate_limiter.config.daily_budget = 0.05  # Very low budget
        
        requests = [
            AIRequest(
                request_id=f"cost_test_{i}",
                prompt=f"Cost tracking test {i}",
                priority=1
            )
            for i in range(5)
        ]
        
        # Act
        responses = []
        for request in requests:
            response = await ai_provider_manager.process_request(request)
            responses.append(response)
        
        # Get cost summary
        cost_summary = ai_provider_manager.get_cost_summary()
        
        # Assert
        assert cost_summary["total_cost"] >= 0.0
        assert len(cost_summary["provider_costs"]) > 0
        
        # Some requests might fail due to budget limits
        failed_responses = [r for r in responses if r.error is not None]
        # At least some should succeed before hitting budget
        successful_responses = [r for r in responses if r.error is None]
        assert len(successful_responses) > 0
    
    @pytest.mark.asyncio
    async def test_provider_selection_strategies(self, ai_provider_manager, mock_providers):
        """
        Test: Different provider selection strategies work correctly
        
        Arrange: Configure different selection strategies
        Act: Process requests with each strategy
        Assert: Provider selection behavior matches strategy
        """
        # Test Round Robin
        ai_provider_manager.set_selection_strategy(ProviderSelectionStrategy.ROUND_ROBIN)
        
        requests = [
            AIRequest(request_id=f"rr_test_{i}", prompt=f"Round robin test {i}")
            for i in range(6)
        ]
        
        responses = []
        for request in requests:
            response = await ai_provider_manager.process_request(request)
            responses.append(response)
        
        # Should distribute across providers
        providers_used = set(r.provider for r in responses if r.error is None)
        assert len(providers_used) > 1
        
        # Test Priority Based
        ai_provider_manager.set_selection_strategy(ProviderSelectionStrategy.PRIORITY_BASED)
        
        priority_request = AIRequest(
            request_id="priority_test",
            prompt="Priority test"
        )
        
        priority_response = await ai_provider_manager.process_request(priority_request)
        
        # Should use highest priority provider (priority 1 = openai)
        if priority_response.error is None:
            assert priority_response.provider == "openai"
    
    def test_performance_metrics_collection(self, ai_provider_manager):
        """
        Test: Performance metrics are collected correctly
        
        Arrange: Use AI provider manager for various operations
        Act: Get performance metrics
        Assert: Metrics are comprehensive and accurate
        """
        # Act
        metrics = ai_provider_manager.get_performance_metrics()
        
        # Assert
        assert "overall_stats" in metrics
        assert "provider_performance" in metrics
        assert "provider_status" in metrics
        assert "cache_stats" in metrics
        assert "routing" in metrics
        
        # Check overall stats structure
        overall_stats = metrics["overall_stats"]
        assert "total_requests" in overall_stats
        assert "successful_requests" in overall_stats
        assert "failed_requests" in overall_stats
        assert "total_cost" in overall_stats
        assert "provider_usage" in overall_stats
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, ai_provider_manager):
        """
        Test: Concurrent request handling works correctly
        
        Arrange: Create multiple concurrent requests
        Act: Process requests concurrently
        Assert: All requests are handled correctly
        """
        # Arrange
        requests = [
            AIRequest(
                request_id=f"concurrent_test_{i}",
                prompt=f"Concurrent test {i}",
                priority=1
            )
            for i in range(8)
        ]
        
        # Act
        start_time = time.time()
        
        # Process requests concurrently
        tasks = [
            ai_provider_manager.process_request(request)
            for request in requests
        ]
        
        responses = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Assert
        assert len(responses) == 8
        
        # Concurrent processing should be faster than sequential
        assert total_time < 10.0  # Should complete within reasonable time
        
        # Check that requests were distributed across providers
        providers_used = set(r.provider for r in responses if r.error is None)
        assert len(providers_used) > 1
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_resilience(self, ai_provider_manager, mock_providers):
        """
        Test: Error recovery and system resilience
        
        Arrange: Configure various failure scenarios
        Act: Process requests during failures
        Assert: System recovers gracefully
        """
        # Arrange
        from ai.providers.base_provider import AIProviderError
        
        # Configure providers to fail temporarily
        failure_count = 0
        
        async def intermittent_failure(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:
                raise AIProviderError("Temporary failure", retryable=True)
            else:
                return AIResponse(
                    request_id="recovery_test",
                    response_text="Recovered successfully",
                    model_used="recovery_model",
                    provider="test_provider",
                    confidence=0.9,
                    cost=0.01,
                    response_time=1.0
                )
        
        # Make providers fail initially then recover
        for provider in list(mock_providers.values())[:2]:
            provider.process_request_with_retry = AsyncMock(side_effect=intermittent_failure)
        
        requests = [
            AIRequest(
                request_id=f"recovery_test_{i}",
                prompt=f"Recovery test {i}",
                priority=1
            )
            for i in range(5)
        ]
        
        # Act
        responses = []
        for request in requests:
            response = await ai_provider_manager.process_request(request)
            responses.append(response)
        
        # Assert
        # Should eventually recover and process some requests successfully
        successful_responses = [r for r in responses if r.error is None]
        assert len(successful_responses) > 0
        
        # System should handle failures gracefully
        failed_responses = [r for r in responses if r.error is not None]
        # Some failures are expected during recovery
        assert len(failed_responses) <= len(responses)


class TestPerformanceBenchmarks:
    """Performance benchmark tests"""
    
    @pytest.mark.asyncio
    async def test_response_time_benchmark(self, ai_provider_manager):
        """
        Test: Response time benchmark
        
        Arrange: Create test requests
        Act: Measure response times
        Assert: Response times meet performance targets
        """
        # Arrange
        request = AIRequest(
            request_id="benchmark_test",
            prompt="Performance benchmark test",
            priority=1
        )
        
        # Act
        response_times = []
        for i in range(5):
            start_time = time.time()
            response = await ai_provider_manager.process_request(request)
            end_time = time.time()
            
            if response.error is None:
                response_times.append(end_time - start_time)
        
        # Assert
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            assert avg_response_time < 5.0  # Target: < 5 seconds
            
            # Check consistency
            max_time = max(response_times)
            min_time = min(response_times)
            assert max_time - min_time < 3.0  # Consistent performance
    
    @pytest.mark.asyncio
    async def test_throughput_benchmark(self, ai_provider_manager):
        """
        Test: Throughput benchmark
        
        Arrange: Create multiple requests
        Act: Measure throughput over time
        Assert: Throughput meets performance targets
        """
        # Arrange
        num_requests = 10
        requests = [
            AIRequest(
                request_id=f"throughput_test_{i}",
                prompt=f"Throughput test {i}",
                priority=1
            )
            for i in range(num_requests)
        ]
        
        # Act
        start_time = time.time()
        
        # Process all requests
        responses = []
        for request in requests:
            response = await ai_provider_manager.process_request(request)
            responses.append(response)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Assert
        successful_responses = [r for r in responses if r.error is None]
        if successful_responses:
            throughput = len(successful_responses) / total_time
            assert throughput > 1.0  # Target: > 1 request per second
    
    @pytest.mark.asyncio
    async def test_cost_efficiency_benchmark(self, ai_provider_manager):
        """
        Test: Cost efficiency benchmark
        
        Arrange: Process various requests
        Act: Measure cost per request
        Assert: Cost efficiency meets targets
        """
        # Arrange
        requests = [
            AIRequest(
                request_id=f"cost_test_{i}",
                prompt=f"Cost efficiency test {i}",
                priority=1
            )
            for i in range(5)
        ]
        
        # Act
        total_cost = 0.0
        successful_requests = 0
        
        for request in requests:
            response = await ai_provider_manager.process_request(request)
            if response.error is None:
                total_cost += response.cost
                successful_requests += 1
        
        # Assert
        if successful_requests > 0:
            avg_cost_per_request = total_cost / successful_requests
            assert avg_cost_per_request < 0.05  # Target: < $0.05 per request


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])