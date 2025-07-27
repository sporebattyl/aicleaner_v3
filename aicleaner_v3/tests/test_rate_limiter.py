"""
Test suite for Rate Limiter
Phase 2A: AI Model Provider Optimization

Tests for rate limiting and quota management with cost tracking.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from ai.providers.rate_limiter import RateLimiter, RateLimitConfig, RateLimitResult, TokenBucket


class TestTokenBucket:
    """Test suite for TokenBucket"""
    
    def test_init_creates_bucket_with_capacity(self):
        """
        Test: TokenBucket initialization
        
        Arrange: Create token bucket parameters
        Act: Initialize TokenBucket
        Assert: Bucket is created with correct capacity
        """
        # Arrange
        capacity = 100
        refill_rate = 10
        refill_period = 60
        
        # Act
        bucket = TokenBucket(capacity, refill_rate, refill_period)
        
        # Assert
        assert bucket.capacity == capacity
        assert bucket.refill_rate == refill_rate
        assert bucket.refill_period == refill_period
        assert bucket.tokens == capacity
    
    def test_consume_tokens_reduces_available_tokens(self):
        """
        Test: Token consumption reduces available tokens
        
        Arrange: Create token bucket with tokens
        Act: Consume tokens
        Assert: Available tokens are reduced
        """
        # Arrange
        bucket = TokenBucket(100, 10, 60)
        initial_tokens = bucket.tokens
        
        # Act
        result = bucket.consume(30)
        
        # Assert
        assert result is True
        assert bucket.tokens == initial_tokens - 30
    
    def test_consume_more_tokens_than_available_fails(self):
        """
        Test: Consuming more tokens than available fails
        
        Arrange: Create token bucket with limited tokens
        Act: Try to consume more tokens than available
        Assert: Consumption fails and tokens unchanged
        """
        # Arrange
        bucket = TokenBucket(50, 10, 60)
        initial_tokens = bucket.tokens
        
        # Act
        result = bucket.consume(100)
        
        # Assert
        assert result is False
        assert bucket.tokens == initial_tokens
    
    def test_token_refill_over_time(self):
        """
        Test: Tokens are refilled over time
        
        Arrange: Create token bucket and consume tokens
        Act: Advance time and check refill
        Assert: Tokens are refilled based on elapsed time
        """
        # Arrange
        bucket = TokenBucket(100, 60, 60)  # 60 tokens per 60 seconds
        bucket.consume(50)  # Consume half
        
        # Act - Mock time advancement
        with patch('time.time') as mock_time:
            mock_time.return_value = bucket.last_refill + 60  # 60 seconds later
            bucket._refill()
        
        # Assert
        assert bucket.tokens == 100  # Should be fully refilled
    
    def test_time_until_tokens_calculation(self):
        """
        Test: Time calculation until tokens are available
        
        Arrange: Create token bucket with no tokens
        Act: Calculate time until tokens available
        Assert: Correct time is calculated
        """
        # Arrange
        bucket = TokenBucket(100, 60, 60)  # 60 tokens per 60 seconds
        bucket.tokens = 0
        
        # Act
        time_until = bucket.time_until_tokens(30)
        
        # Assert
        assert time_until == 30.0  # 30 seconds for 30 tokens at 1 token/second


class TestRateLimiter:
    """Test suite for RateLimiter"""
    
    @pytest.fixture
    def rate_config(self):
        """Rate limiting configuration for testing"""
        return RateLimitConfig(
            requests_per_minute=60,
            tokens_per_minute=10000,
            daily_budget=10.0,
            cost_per_request=0.01,
            cost_per_token=0.001
        )
    
    @pytest.fixture
    def rate_limiter(self, rate_config):
        """Create rate limiter for testing"""
        return RateLimiter("test_provider", rate_config)
    
    def test_init_creates_limiter_with_config(self, rate_config):
        """
        Test: RateLimiter initialization
        
        Arrange: Create rate limit configuration
        Act: Initialize RateLimiter
        Assert: Limiter is created with correct configuration
        """
        # Arrange & Act
        limiter = RateLimiter("test_provider", rate_config)
        
        # Assert
        assert limiter.provider == "test_provider"
        assert limiter.config == rate_config
        assert limiter.request_bucket.capacity == rate_config.requests_per_minute + rate_config.burst_allowance
        assert limiter.token_bucket.capacity == rate_config.tokens_per_minute + (rate_config.burst_allowance * 100)
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_allows_within_limits(self, rate_limiter):
        """
        Test: Rate limit check allows requests within limits
        
        Arrange: Create rate limiter with available capacity
        Act: Check rate limit for request
        Assert: Request is allowed
        """
        # Arrange
        tokens = 100
        
        # Act
        result = await rate_limiter.check_rate_limit(tokens)
        
        # Assert
        assert result.allowed is True
        assert result.reason == ""
        assert "requests" in result.quota_remaining
        assert "tokens" in result.quota_remaining
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_blocks_over_budget(self, rate_limiter):
        """
        Test: Rate limit check blocks requests over daily budget
        
        Arrange: Set daily cost to exceed budget
        Act: Check rate limit for expensive request
        Assert: Request is blocked due to budget
        """
        # Arrange
        rate_limiter.daily_cost = 15.0  # Exceeds 10.0 budget
        tokens = 100
        
        # Act
        result = await rate_limiter.check_rate_limit(tokens)
        
        # Assert
        assert result.allowed is False
        assert "budget" in result.reason.lower()
        assert result.cost_remaining <= 0
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_blocks_over_request_limit(self, rate_limiter):
        """
        Test: Rate limit check blocks requests over request limit
        
        Arrange: Exhaust request tokens
        Act: Check rate limit for additional request
        Assert: Request is blocked due to rate limit
        """
        # Arrange
        # Consume all request tokens
        for _ in range(rate_limiter.request_bucket.capacity):
            rate_limiter.request_bucket.consume(1)
        
        # Act
        result = await rate_limiter.check_rate_limit(1)
        
        # Assert
        assert result.allowed is False
        assert "rate limit" in result.reason.lower()
        assert result.wait_time > 0
    
    def test_record_request_updates_metrics(self, rate_limiter):
        """
        Test: Recording request updates metrics
        
        Arrange: Create rate limiter
        Act: Record request with metrics
        Assert: Metrics are updated correctly
        """
        # Arrange
        tokens_used = 500
        cost = 0.05
        response_time = 1.5
        
        # Act
        rate_limiter.record_request(tokens_used, cost, response_time, error=False)
        
        # Assert
        assert rate_limiter.quota_info.tokens_used == tokens_used
        assert rate_limiter.quota_info.cost_used == cost
        assert rate_limiter.daily_cost == cost
        assert len(rate_limiter.request_history) == 1
        assert rate_limiter.request_history[0]["tokens"] == tokens_used
        assert rate_limiter.request_history[0]["cost"] == cost
        assert rate_limiter.request_history[0]["response_time"] == response_time
    
    def test_record_request_tracks_errors(self, rate_limiter):
        """
        Test: Recording request tracks errors
        
        Arrange: Create rate limiter
        Act: Record request with error
        Assert: Error is tracked correctly
        """
        # Arrange
        tokens_used = 500
        cost = 0.05
        response_time = 1.5
        
        # Act
        rate_limiter.record_request(tokens_used, cost, response_time, error=True)
        
        # Assert
        assert len(rate_limiter.error_history) == 1
        assert len(rate_limiter.request_history) == 1
        assert rate_limiter.request_history[0]["error"] is True
    
    def test_daily_reset_clears_quotas(self, rate_limiter):
        """
        Test: Daily reset clears quotas and costs
        
        Arrange: Use some quota and cost
        Act: Trigger daily reset
        Assert: Quotas and costs are reset
        """
        # Arrange
        rate_limiter.quota_info.requests_used = 10
        rate_limiter.quota_info.tokens_used = 1000
        rate_limiter.daily_cost = 5.0
        
        # Act
        rate_limiter._check_daily_reset()
        rate_limiter.last_reset_date = datetime.now().date() - timedelta(days=1)
        rate_limiter._check_daily_reset()
        
        # Assert
        assert rate_limiter.quota_info.requests_used == 0
        assert rate_limiter.quota_info.tokens_used == 0
        assert rate_limiter.daily_cost == 0.0
    
    def test_adaptive_throttling_increases_with_errors(self, rate_limiter):
        """
        Test: Adaptive throttling increases delay with errors
        
        Arrange: Record multiple errors
        Act: Calculate throttle delay
        Assert: Delay increases with error rate
        """
        # Arrange
        # Record multiple errors
        for i in range(5):
            rate_limiter.record_request(100, 0.01, 1.0, error=True)
        
        # Act
        delay = rate_limiter._calculate_throttle_delay()
        
        # Assert
        assert delay > 0.1  # Should be more than base delay
        assert rate_limiter.throttle_factor > 1.0
    
    def test_adaptive_throttling_decreases_with_success(self, rate_limiter):
        """
        Test: Adaptive throttling decreases delay with successful requests
        
        Arrange: Record successful requests after errors
        Act: Calculate throttle delay
        Assert: Delay decreases with lower error rate
        """
        # Arrange
        # First record some errors to increase throttle factor
        for i in range(3):
            rate_limiter.record_request(100, 0.01, 1.0, error=True)
        
        initial_throttle = rate_limiter.throttle_factor
        
        # Then record successful requests
        for i in range(10):
            rate_limiter.record_request(100, 0.01, 1.0, error=False)
        
        # Act
        final_throttle = rate_limiter.throttle_factor
        
        # Assert
        assert final_throttle < initial_throttle
    
    def test_get_quota_info_returns_current_status(self, rate_limiter):
        """
        Test: Get quota info returns current status
        
        Arrange: Use some quota
        Act: Get quota info
        Assert: Current status is returned
        """
        # Arrange
        rate_limiter.quota_info.requests_used = 10
        rate_limiter.quota_info.tokens_used = 1000
        rate_limiter.daily_cost = 2.5
        
        # Act
        quota_info = rate_limiter.get_quota_info()
        
        # Assert
        assert quota_info.provider == "test_provider"
        assert quota_info.requests_used == 10
        assert quota_info.tokens_used == 1000
        assert quota_info.cost_used == 2.5
    
    def test_get_rate_limit_status_returns_comprehensive_info(self, rate_limiter):
        """
        Test: Get rate limit status returns comprehensive information
        
        Arrange: Use some quota and set metrics
        Act: Get rate limit status
        Assert: Comprehensive status is returned
        """
        # Arrange
        rate_limiter.quota_info.requests_used = 10
        rate_limiter.daily_cost = 2.5
        rate_limiter.average_response_time = 1.2
        rate_limiter.error_rate = 0.1
        
        # Act
        status = rate_limiter.get_rate_limit_status()
        
        # Assert
        assert status["provider"] == "test_provider"
        assert status["requests_used_today"] == 10
        assert status["cost_used_today"] == 2.5
        assert status["average_response_time"] == 1.2
        assert status["error_rate"] == 0.1
        assert "budget_remaining" in status
        assert "budget_utilization" in status
    
    def test_get_performance_metrics_returns_detailed_metrics(self, rate_limiter):
        """
        Test: Get performance metrics returns detailed information
        
        Arrange: Record some requests and set metrics
        Act: Get performance metrics
        Assert: Detailed metrics are returned
        """
        # Arrange
        rate_limiter.record_request(100, 0.01, 1.0, error=False)
        rate_limiter.record_request(200, 0.02, 2.0, error=True)
        
        # Act
        metrics = rate_limiter.get_performance_metrics()
        
        # Assert
        assert metrics["provider"] == "test_provider"
        assert metrics["total_requests"] == 2
        assert metrics["error_rate"] > 0
        assert "quota_utilization" in metrics
        assert "requests" in metrics["quota_utilization"]
        assert "tokens" in metrics["quota_utilization"]
        assert "budget" in metrics["quota_utilization"]
    
    def test_update_config_changes_settings(self, rate_limiter):
        """
        Test: Update configuration changes rate limiter settings
        
        Arrange: Create rate limiter with initial config
        Act: Update configuration
        Assert: Settings are updated correctly
        """
        # Arrange
        new_config = RateLimitConfig(
            requests_per_minute=120,
            tokens_per_minute=20000,
            daily_budget=20.0
        )
        
        # Act
        rate_limiter.update_config(new_config)
        
        # Assert
        assert rate_limiter.config.requests_per_minute == 120
        assert rate_limiter.config.tokens_per_minute == 20000
        assert rate_limiter.config.daily_budget == 20.0
    
    def test_reset_quotas_clears_all_metrics(self, rate_limiter):
        """
        Test: Reset quotas clears all metrics
        
        Arrange: Use quotas and set metrics
        Act: Reset quotas
        Assert: All metrics are cleared
        """
        # Arrange
        rate_limiter.quota_info.requests_used = 10
        rate_limiter.quota_info.tokens_used = 1000
        rate_limiter.daily_cost = 5.0
        
        # Act
        rate_limiter.reset_quotas()
        
        # Assert
        assert rate_limiter.quota_info.requests_used == 0
        assert rate_limiter.quota_info.tokens_used == 0
        assert rate_limiter.quota_info.cost_used == 0.0
        assert rate_limiter.daily_cost == 0.0
        assert rate_limiter.quota_info.budget_exceeded is False
        assert rate_limiter.quota_info.rate_limit_hit is False
    
    def test_is_budget_exceeded_checks_budget_status(self, rate_limiter):
        """
        Test: Budget exceeded check works correctly
        
        Arrange: Set daily cost to different levels
        Act: Check budget status
        Assert: Correct status is returned
        """
        # Arrange & Act & Assert
        rate_limiter.daily_cost = 5.0
        assert rate_limiter.is_budget_exceeded() is False
        
        rate_limiter.daily_cost = 10.0
        assert rate_limiter.is_budget_exceeded() is True
        
        rate_limiter.daily_cost = 15.0
        assert rate_limiter.is_budget_exceeded() is True
    
    def test_get_wait_time_for_budget_calculates_correctly(self, rate_limiter):
        """
        Test: Wait time for budget calculation
        
        Arrange: Set daily cost near budget
        Act: Calculate wait time for request
        Assert: Correct wait time is calculated
        """
        # Arrange
        rate_limiter.daily_cost = 9.5  # Close to 10.0 budget
        estimated_cost = 1.0  # Would exceed budget
        
        # Act
        wait_time = rate_limiter.get_wait_time_for_budget(estimated_cost)
        
        # Assert
        assert wait_time > 0  # Should need to wait until next day
        
        # Test with cost that fits in budget
        estimated_cost = 0.3  # Would fit in budget
        wait_time = rate_limiter.get_wait_time_for_budget(estimated_cost)
        assert wait_time == 0  # No wait needed


class TestRateLimitResult:
    """Test rate limit result structure"""
    
    def test_rate_limit_result_creation(self):
        """Test RateLimitResult creation with all fields"""
        result = RateLimitResult(
            allowed=True,
            reason="Request within limits",
            wait_time=0.0,
            quota_remaining={"requests": 50, "tokens": 9000},
            cost_remaining=7.5,
            retry_after=None
        )
        
        assert result.allowed is True
        assert result.reason == "Request within limits"
        assert result.wait_time == 0.0
        assert result.quota_remaining["requests"] == 50
        assert result.cost_remaining == 7.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])