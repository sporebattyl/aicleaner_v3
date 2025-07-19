"""
Tests for Simple Rate Limiting System
"""

import time
import pytest
from unittest.mock import MagicMock, patch
from fastapi import Request, Response
from fastapi.testclient import TestClient

from middleware.simple_rate_limiter import (
    SimpleRateLimiter, 
    SimpleRateLimitMiddleware,
    create_addon_rate_limiter,
    create_disabled_rate_limiter,
    create_production_rate_limiter
)


class TestSimpleRateLimiter:
    """Test the SimpleRateLimiter class."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter for testing."""
        return SimpleRateLimiter(requests_per_minute=10, burst_allowance=2, block_duration_seconds=60)

    @pytest.fixture
    def local_network_limiter(self):
        """Create a rate limiter with local network whitelisting."""
        return SimpleRateLimiter(requests_per_minute=5, whitelist_local_network=True)

    def test_local_network_detection(self, local_network_limiter):
        """Test local network IP detection."""
        # Test local network IPs
        assert local_network_limiter._is_local_network("192.168.1.1") is True
        assert local_network_limiter._is_local_network("10.0.0.1") is True
        assert local_network_limiter._is_local_network("172.16.0.1") is True
        assert local_network_limiter._is_local_network("127.0.0.1") is True
        
        # Test public IPs
        assert local_network_limiter._is_local_network("8.8.8.8") is False
        assert local_network_limiter._is_local_network("1.1.1.1") is False
        
        # Test invalid IPs
        assert local_network_limiter._is_local_network("invalid.ip") is False
        assert local_network_limiter._is_local_network("999.999.999.999") is False

    def test_local_network_whitelisting(self, local_network_limiter):
        """Test that local network IPs are whitelisted."""
        # Local IP should always be allowed
        for _ in range(20):  # Way over the limit
            allowed, reason = local_network_limiter.is_allowed("192.168.1.100")
            assert allowed is True
            assert reason == ""

    def test_normal_rate_limiting(self, rate_limiter):
        """Test normal rate limiting behavior."""
        test_ip = "1.2.3.4"
        
        # Should allow requests up to limit + burst
        for i in range(12):  # 10 + 2 burst
            allowed, reason = rate_limiter.is_allowed(test_ip)
            assert allowed is True, f"Request {i+1} should be allowed"
            assert reason == ""
        
        # Next request should be blocked
        allowed, reason = rate_limiter.is_allowed(test_ip)
        assert allowed is False
        assert "Rate limit exceeded" in reason

    def test_warning_threshold(self, rate_limiter):
        """Test warning threshold logging."""
        test_ip = "1.2.3.4"
        
        with patch('middleware.simple_rate_limiter.logger') as mock_logger:
            # Make requests up to warning threshold (80% of 10 = 8)
            for i in range(8):
                rate_limiter.is_allowed(test_ip)
            
            # Should log warning for the 8th request
            mock_logger.info.assert_called_with(f"Rate limit warning for IP {test_ip}: 8/10 requests used")

    def test_blocking_duration(self, rate_limiter):
        """Test IP blocking duration."""
        test_ip = "1.2.3.4"
        
        # Exceed rate limit
        for _ in range(13):  # Over limit + burst
            rate_limiter.is_allowed(test_ip)
        
        # Should be blocked
        allowed, reason = rate_limiter.is_allowed(test_ip)
        assert allowed is False
        assert "IP temporarily blocked" in reason

    def test_block_expiration(self, rate_limiter):
        """Test that blocks expire after the configured duration."""
        test_ip = "1.2.3.4"
        
        # Exceed rate limit to trigger block
        for _ in range(13):
            rate_limiter.is_allowed(test_ip)
        
        # Mock time to simulate block expiration
        with patch('time.time') as mock_time:
            # Initially blocked
            mock_time.return_value = 1000
            allowed, _ = rate_limiter.is_allowed(test_ip)
            assert allowed is False
            
            # After block duration, should be unblocked
            mock_time.return_value = 1000 + 61  # After 61 seconds (block is 60s)
            allowed, _ = rate_limiter.is_allowed(test_ip)
            assert allowed is True

    def test_cleanup_old_data(self, rate_limiter):
        """Test cleanup of old request data."""
        test_ip = "1.2.3.4"
        
        # Add some requests
        rate_limiter.is_allowed(test_ip)
        assert test_ip in rate_limiter.request_times
        
        # Mock time to make requests appear old
        with patch('time.time') as mock_time:
            mock_time.return_value = 10000  # Far in future
            rate_limiter.cleanup_old_data()
        
        # Old data should be cleaned up
        assert test_ip not in rate_limiter.request_times

    def test_statistics(self, rate_limiter):
        """Test statistics reporting."""
        # Make some requests
        rate_limiter.is_allowed("1.2.3.4")
        rate_limiter.is_allowed("1.2.3.5")
        
        stats = rate_limiter.get_stats()
        
        assert stats["active_ips"] == 2
        assert stats["blocked_ips"] == 0
        assert stats["requests_per_minute_limit"] == 10
        assert stats["burst_allowance"] == 2
        assert stats["block_duration_seconds"] == 60
        assert stats["whitelist_local_network"] is True


class TestSimpleRateLimitMiddleware:
    """Test the SimpleRateLimitMiddleware class."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock FastAPI app."""
        return MagicMock()

    @pytest.fixture
    def middleware(self, mock_app):
        """Create middleware for testing."""
        return SimpleRateLimitMiddleware(
            app=mock_app,
            requests_per_minute=5,
            exempt_paths=['/health', '/test']
        )

    @pytest.fixture
    def disabled_middleware(self, mock_app):
        """Create disabled middleware for testing."""
        return SimpleRateLimitMiddleware(app=mock_app, enabled=False)

    def test_disabled_middleware_allows_all(self, disabled_middleware):
        """Test that disabled middleware allows all requests."""
        request = MagicMock(spec=Request)
        request.client.host = "1.2.3.4"
        
        call_next = MagicMock(return_value="response")
        
        # Should bypass rate limiting when disabled
        with patch.object(disabled_middleware, '_get_client_ip', return_value="1.2.3.4"):
            result = disabled_middleware.dispatch(request, call_next)
            assert result == "response"
            call_next.assert_called_once()

    def test_exempt_paths_bypass_rate_limiting(self, middleware):
        """Test that exempt paths bypass rate limiting."""
        request = MagicMock(spec=Request)
        request.url.path = "/health"
        
        call_next = MagicMock(return_value="response")
        
        result = middleware.dispatch(request, call_next)
        assert result == "response"
        call_next.assert_called_once()

    def test_client_ip_extraction(self, middleware):
        """Test client IP extraction from various headers."""
        request = MagicMock(spec=Request)
        
        # Test X-Forwarded-For header
        request.headers.get.side_effect = lambda h: "1.2.3.4, 5.6.7.8" if h == "X-Forwarded-For" else None
        request.client.host = "9.10.11.12"
        
        ip = middleware._get_client_ip(request)
        assert ip == "1.2.3.4"
        
        # Test X-Real-IP header
        request.headers.get.side_effect = lambda h: "5.6.7.8" if h == "X-Real-IP" else None
        ip = middleware._get_client_ip(request)
        assert ip == "5.6.7.8"
        
        # Test direct client IP
        request.headers.get.return_value = None
        ip = middleware._get_client_ip(request)
        assert ip == "9.10.11.12"

    def test_rate_limit_response(self, middleware):
        """Test rate limit exceeded response."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        
        # Mock rate limiter to return blocked
        with patch.object(middleware.rate_limiter, 'is_allowed', return_value=(False, "Rate limit exceeded")):
            with patch.object(middleware, '_get_client_ip', return_value="1.2.3.4"):
                response = middleware.dispatch(request, lambda r: None)
                
                assert response.status_code == 429
                assert "Too Many Requests" in response.body.decode()

    def test_cleanup_timing(self, middleware):
        """Test that cleanup runs at appropriate intervals."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        
        call_next = MagicMock(return_value=MagicMock())
        
        with patch.object(middleware.rate_limiter, 'cleanup_old_data') as mock_cleanup:
            with patch.object(middleware, '_get_client_ip', return_value="192.168.1.1"):  # Local IP
                with patch('time.time') as mock_time:
                    # First call
                    mock_time.return_value = 1000
                    middleware.dispatch(request, call_next)
                    
                    # Second call, 6 minutes later (should trigger cleanup)
                    mock_time.return_value = 1000 + 360
                    middleware.dispatch(request, call_next)
                    
                    mock_cleanup.assert_called_once()


class TestConfigurationHelpers:
    """Test configuration helper functions."""

    def test_create_addon_rate_limiter_defaults(self):
        """Test default addon rate limiter configuration."""
        limiter = create_addon_rate_limiter()
        
        assert limiter.enabled is True
        assert limiter.rate_limiter.requests_per_minute == 60
        assert limiter.rate_limiter.block_duration_seconds == 120
        assert limiter.rate_limiter.whitelist_local_network is True

    def test_create_addon_rate_limiter_development_mode(self):
        """Test development mode configuration."""
        limiter = create_addon_rate_limiter(development_mode=True)
        
        assert limiter.rate_limiter.requests_per_minute == 120
        assert limiter.rate_limiter.block_duration_seconds == 30

    def test_create_addon_rate_limiter_with_options(self):
        """Test configuration with addon options."""
        addon_options = {
            "rate_limit_requests_per_minute": 30,
            "rate_limit_block_duration": 180,
            "rate_limit_whitelist_local": False
        }
        
        limiter = create_addon_rate_limiter(addon_options=addon_options)
        
        assert limiter.rate_limiter.requests_per_minute == 30
        assert limiter.rate_limiter.block_duration_seconds == 180
        assert limiter.rate_limiter.whitelist_local_network is False

    def test_create_disabled_rate_limiter(self):
        """Test disabled rate limiter creation."""
        limiter = create_disabled_rate_limiter()
        
        assert limiter.enabled is False

    def test_create_production_rate_limiter(self):
        """Test production rate limiter configuration."""
        limiter = create_production_rate_limiter()
        
        assert limiter.rate_limiter.requests_per_minute == 30
        assert limiter.rate_limiter.block_duration_seconds == 300
        assert limiter.exempt_paths == ['/health']


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_home_assistant_scenario(self):
        """Test typical Home Assistant addon usage."""
        # Create limiter appropriate for HA addon
        limiter = create_addon_rate_limiter()
        
        # Local network access should be unlimited
        for _ in range(100):
            allowed, _ = limiter.rate_limiter.is_allowed("192.168.1.50")
            assert allowed is True
        
        # External access should be limited
        external_ip = "8.8.8.8"
        allowed_count = 0
        
        for _ in range(80):  # Try many requests
            allowed, _ = limiter.rate_limiter.is_allowed(external_ip)
            if allowed:
                allowed_count += 1
        
        # Should have been limited to requests_per_minute + burst_allowance
        assert allowed_count <= 70  # 60 + 10 burst

    def test_attack_scenario(self):
        """Test response to potential attack scenario."""
        limiter = create_production_rate_limiter()
        attacker_ip = "1.2.3.4"
        
        # Rapid requests from attacker
        allowed_requests = 0
        for _ in range(100):
            allowed, _ = limiter.rate_limiter.is_allowed(attacker_ip)
            if allowed:
                allowed_requests += 1
        
        # Should be limited and then blocked
        assert allowed_requests <= 40  # 30 + 10 burst allowance
        
        # Subsequent requests should be blocked
        allowed, reason = limiter.rate_limiter.is_allowed(attacker_ip)
        assert allowed is False
        assert "blocked" in reason.lower()

    def test_mixed_traffic_scenario(self):
        """Test handling of mixed legitimate and illegitimate traffic."""
        limiter = create_addon_rate_limiter()
        
        # Legitimate local user - should never be blocked
        for _ in range(50):
            allowed, _ = limiter.rate_limiter.is_allowed("192.168.1.100")
            assert allowed is True
        
        # External API calls - moderate usage should be allowed
        api_ip = "203.0.113.1"
        for _ in range(30):  # Under limit
            allowed, _ = limiter.rate_limiter.is_allowed(api_ip)
            assert allowed is True
        
        # Abusive external IP - should get blocked
        abuser_ip = "198.51.100.1"
        for _ in range(80):  # Way over limit
            limiter.rate_limiter.is_allowed(abuser_ip)
        
        # Abuser should be blocked
        allowed, _ = limiter.rate_limiter.is_allowed(abuser_ip)
        assert allowed is False
        
        # But legitimate traffic should continue working
        allowed, _ = limiter.rate_limiter.is_allowed("192.168.1.100")
        assert allowed is True