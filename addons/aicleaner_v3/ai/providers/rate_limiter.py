"""
Rate Limiter and Quota Manager for AI Providers
Phase 2A: AI Model Provider Optimization

Provides rate limiting, quota management, and cost tracking for AI providers
with intelligent throttling and budget controls.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int = 60
    tokens_per_minute: int = 10000
    requests_per_hour: int = 3600
    tokens_per_hour: int = 600000
    daily_budget: float = 10.0
    cost_per_request: float = 0.01
    cost_per_token: float = 0.001
    burst_allowance: int = 5
    enable_adaptive_throttling: bool = True


@dataclass
class QuotaInfo:
    """Quota information for a provider"""
    provider: str
    requests_used: int = 0
    tokens_used: int = 0
    cost_used: float = 0.0
    last_reset: str = field(default_factory=lambda: datetime.now().isoformat())
    rate_limit_hit: bool = False
    budget_exceeded: bool = False
    next_reset: Optional[str] = None


@dataclass
class RateLimitResult:
    """Result of rate limit check"""
    allowed: bool
    reason: str = ""
    wait_time: float = 0.0
    quota_remaining: Dict[str, int] = field(default_factory=dict)
    cost_remaining: float = 0.0
    retry_after: Optional[str] = None


class TokenBucket:
    """Token bucket implementation for rate limiting"""
    
    def __init__(self, capacity: int, refill_rate: float, refill_period: float = 60.0):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens added per refill period
            refill_period: Time period for refill (seconds)
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.refill_period = refill_period
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False otherwise
        """
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        
        if elapsed >= self.refill_period:
            periods = elapsed / self.refill_period
            tokens_to_add = int(periods * self.refill_rate)
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill = now
    
    def get_tokens(self) -> int:
        """Get current token count"""
        with self.lock:
            self._refill()
            return self.tokens
    
    def time_until_tokens(self, tokens: int) -> float:
        """Calculate time until specified tokens are available"""
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                return 0.0
            
            tokens_needed = tokens - self.tokens
            periods_needed = tokens_needed / self.refill_rate
            return periods_needed * self.refill_period


class RateLimiter:
    """
    Advanced rate limiter with quota management and cost tracking.
    
    Features:
    - Token bucket algorithm for smooth rate limiting
    - Multiple limit types (requests/min, tokens/min, daily budget)
    - Adaptive throttling based on provider performance
    - Cost tracking and budget enforcement
    - Burst allowance for temporary spikes
    """
    
    def __init__(self, provider: str, config: RateLimitConfig):
        """
        Initialize rate limiter.
        
        Args:
            provider: Provider name
            config: Rate limiting configuration
        """
        self.provider = provider
        self.config = config
        self.logger = logging.getLogger(f"ai_provider.rate_limiter.{provider}")
        
        # Token buckets for different rate limits
        self.request_bucket = TokenBucket(
            capacity=config.requests_per_minute + config.burst_allowance,
            refill_rate=config.requests_per_minute,
            refill_period=60.0
        )
        
        self.token_bucket = TokenBucket(
            capacity=config.tokens_per_minute + (config.burst_allowance * 100),
            refill_rate=config.tokens_per_minute,
            refill_period=60.0
        )
        
        # Quota tracking
        self.quota_info = QuotaInfo(provider=provider)
        
        # Request history for adaptive throttling
        self.request_history = deque(maxlen=100)
        self.error_history = deque(maxlen=50)
        
        # Cost tracking
        self.daily_cost = 0.0
        self.last_reset_date = datetime.now().date()
        
        # Performance metrics
        self.average_response_time = 0.0
        self.error_rate = 0.0
        self.throttle_factor = 1.0
        
        # Locks for thread safety
        self.quota_lock = threading.Lock()
        self.cost_lock = threading.Lock()
        
        self.logger.info(f"Rate limiter initialized for {provider}")
    
    async def check_rate_limit(self, tokens: int = 1) -> RateLimitResult:
        """
        Check if request can proceed based on rate limits.
        
        Args:
            tokens: Number of tokens (estimated) for the request
            
        Returns:
            RateLimitResult with decision and metadata
        """
        # Check daily budget first
        if self.config.daily_budget > 0:
            estimated_cost = (self.config.cost_per_request + 
                            (tokens * self.config.cost_per_token))
            
            with self.cost_lock:
                if self.daily_cost + estimated_cost > self.config.daily_budget:
                    self.quota_info.budget_exceeded = True
                    return RateLimitResult(
                        allowed=False,
                        reason="Daily budget exceeded",
                        cost_remaining=max(0, self.config.daily_budget - self.daily_cost),
                        retry_after=self._get_next_reset_time()
                    )
        
        # Apply adaptive throttling
        if self.config.enable_adaptive_throttling:
            throttle_delay = self._calculate_throttle_delay()
            if throttle_delay > 0:
                return RateLimitResult(
                    allowed=False,
                    reason="Adaptive throttling active",
                    wait_time=throttle_delay
                )
        
        # Check token bucket limits
        if not self.request_bucket.consume(1):
            wait_time = self.request_bucket.time_until_tokens(1)
            return RateLimitResult(
                allowed=False,
                reason="Request rate limit exceeded",
                wait_time=wait_time,
                retry_after=(datetime.now() + timedelta(seconds=wait_time)).isoformat()
            )
        
        if not self.token_bucket.consume(tokens):
            wait_time = self.token_bucket.time_until_tokens(tokens)
            return RateLimitResult(
                allowed=False,
                reason="Token rate limit exceeded",
                wait_time=wait_time,
                retry_after=(datetime.now() + timedelta(seconds=wait_time)).isoformat()
            )
        
        # Update quota info
        with self.quota_lock:
            self.quota_info.requests_used += 1
            self.quota_info.tokens_used += tokens
            self.quota_info.rate_limit_hit = False
        
        # Request allowed
        return RateLimitResult(
            allowed=True,
            quota_remaining={
                "requests": self.request_bucket.get_tokens(),
                "tokens": self.token_bucket.get_tokens()
            },
            cost_remaining=max(0, self.config.daily_budget - self.daily_cost)
        )
    
    def record_request(self, tokens_used: int, cost: float, response_time: float, 
                      error: bool = False):
        """
        Record a completed request for quota and performance tracking.
        
        Args:
            tokens_used: Actual tokens used
            cost: Actual cost of request
            response_time: Response time in seconds
            error: Whether request resulted in error
        """
        now = time.time()
        
        # Update quota tracking
        with self.quota_lock:
            self.quota_info.tokens_used += tokens_used
            self.quota_info.cost_used += cost
        
        # Update daily cost
        with self.cost_lock:
            self._check_daily_reset()
            self.daily_cost += cost
        
        # Record request history
        self.request_history.append({
            "timestamp": now,
            "tokens": tokens_used,
            "cost": cost,
            "response_time": response_time,
            "error": error
        })
        
        # Record error history
        if error:
            self.error_history.append(now)
        
        # Update performance metrics
        self._update_performance_metrics()
        
        self.logger.debug(
            json.dumps({
                "event": "request_recorded",
                "provider": self.provider,
                "tokens_used": tokens_used,
                "cost": cost,
                "response_time": response_time,
                "error": error,
                "daily_cost": self.daily_cost
            })
        )
    
    def _calculate_throttle_delay(self) -> float:
        """Calculate adaptive throttling delay based on provider performance"""
        if not self.request_history:
            return 0.0
        
        # Calculate recent error rate
        recent_errors = len([
            req for req in self.request_history[-10:] 
            if req.get("error", False)
        ])
        recent_error_rate = recent_errors / min(10, len(self.request_history))
        
        # Calculate throttle factor based on error rate
        if recent_error_rate > 0.3:  # 30% error rate
            self.throttle_factor = min(5.0, self.throttle_factor * 1.5)
        elif recent_error_rate < 0.1:  # 10% error rate
            self.throttle_factor = max(1.0, self.throttle_factor * 0.9)
        
        # Calculate delay based on throttle factor
        base_delay = 0.1  # 100ms base delay
        delay = base_delay * (self.throttle_factor - 1)
        
        # Add jitter to prevent thundering herd
        import random
        jitter = random.uniform(0.0, 0.1)
        
        return delay + jitter
    
    def _update_performance_metrics(self):
        """Update performance metrics from request history"""
        if not self.request_history:
            return
        
        # Calculate average response time
        recent_requests = list(self.request_history)[-20:]  # Last 20 requests
        if recent_requests:
            response_times = [req["response_time"] for req in recent_requests]
            self.average_response_time = sum(response_times) / len(response_times)
        
        # Calculate error rate
        if len(self.request_history) >= 10:
            recent_errors = sum(1 for req in recent_requests if req.get("error", False))
            self.error_rate = recent_errors / len(recent_requests)
    
    def _check_daily_reset(self):
        """Check if daily quotas should be reset"""
        today = datetime.now().date()
        
        if today > self.last_reset_date:
            self.daily_cost = 0.0
            self.last_reset_date = today
            
            with self.quota_lock:
                self.quota_info.requests_used = 0
                self.quota_info.tokens_used = 0
                self.quota_info.cost_used = 0.0
                self.quota_info.budget_exceeded = False
                self.quota_info.last_reset = datetime.now().isoformat()
            
            self.logger.info(f"Daily quotas reset for {self.provider}")
    
    def _get_next_reset_time(self) -> str:
        """Get next quota reset time"""
        tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return tomorrow.isoformat()
    
    def get_quota_info(self) -> QuotaInfo:
        """Get current quota information"""
        with self.quota_lock:
            quota_copy = QuotaInfo(
                provider=self.quota_info.provider,
                requests_used=self.quota_info.requests_used,
                tokens_used=self.quota_info.tokens_used,
                cost_used=self.quota_info.cost_used,
                last_reset=self.quota_info.last_reset,
                rate_limit_hit=self.quota_info.rate_limit_hit,
                budget_exceeded=self.quota_info.budget_exceeded,
                next_reset=self._get_next_reset_time()
            )
        return quota_copy
    
    def get_rate_limit_status(self) -> Dict[str, any]:
        """Get comprehensive rate limit status"""
        with self.quota_lock, self.cost_lock:
            return {
                "provider": self.provider,
                "requests_available": self.request_bucket.get_tokens(),
                "tokens_available": self.token_bucket.get_tokens(),
                "requests_used_today": self.quota_info.requests_used,
                "tokens_used_today": self.quota_info.tokens_used,
                "cost_used_today": self.daily_cost,
                "budget_remaining": max(0, self.config.daily_budget - self.daily_cost),
                "budget_utilization": (self.daily_cost / self.config.daily_budget) * 100,
                "rate_limit_hit": self.quota_info.rate_limit_hit,
                "budget_exceeded": self.quota_info.budget_exceeded,
                "throttle_factor": self.throttle_factor,
                "error_rate": self.error_rate,
                "average_response_time": self.average_response_time,
                "next_reset": self._get_next_reset_time()
            }
    
    def get_performance_metrics(self) -> Dict[str, any]:
        """Get performance metrics"""
        return {
            "provider": self.provider,
            "total_requests": len(self.request_history),
            "error_rate": self.error_rate,
            "average_response_time": self.average_response_time,
            "throttle_factor": self.throttle_factor,
            "recent_errors": len(self.error_history),
            "quota_utilization": {
                "requests": (self.quota_info.requests_used / self.config.requests_per_hour) * 100,
                "tokens": (self.quota_info.tokens_used / self.config.tokens_per_hour) * 100,
                "budget": (self.daily_cost / self.config.daily_budget) * 100
            }
        }
    
    def update_config(self, config: RateLimitConfig):
        """Update rate limiting configuration"""
        self.config = config
        
        # Update token buckets
        self.request_bucket = TokenBucket(
            capacity=config.requests_per_minute + config.burst_allowance,
            refill_rate=config.requests_per_minute,
            refill_period=60.0
        )
        
        self.token_bucket = TokenBucket(
            capacity=config.tokens_per_minute + (config.burst_allowance * 100),
            refill_rate=config.tokens_per_minute,
            refill_period=60.0
        )
        
        self.logger.info(f"Rate limiting configuration updated for {self.provider}")
    
    def reset_quotas(self):
        """Manually reset quotas (for testing or administrative purposes)"""
        with self.quota_lock, self.cost_lock:
            self.quota_info.requests_used = 0
            self.quota_info.tokens_used = 0
            self.quota_info.cost_used = 0.0
            self.quota_info.budget_exceeded = False
            self.quota_info.rate_limit_hit = False
            self.quota_info.last_reset = datetime.now().isoformat()
            self.daily_cost = 0.0
            
            # Reset token buckets
            self.request_bucket.tokens = self.request_bucket.capacity
            self.token_bucket.tokens = self.token_bucket.capacity
        
        self.logger.info(f"Quotas manually reset for {self.provider}")
    
    def is_budget_exceeded(self) -> bool:
        """Check if daily budget is exceeded"""
        with self.cost_lock:
            return self.daily_cost >= self.config.daily_budget
    
    def get_wait_time_for_budget(self, estimated_cost: float) -> float:
        """Get wait time until budget allows for a request"""
        with self.cost_lock:
            if self.daily_cost + estimated_cost <= self.config.daily_budget:
                return 0.0
            
            # Calculate seconds until midnight (next budget reset)
            now = datetime.now()
            midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            return (midnight - now).total_seconds()