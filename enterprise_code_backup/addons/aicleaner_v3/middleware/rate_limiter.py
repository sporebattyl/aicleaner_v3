"""
API Rate Limiting Middleware for AICleaner v3
"""

import time
import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Callable
from collections import defaultdict, deque
from dataclasses import dataclass, field
from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class RateLimitRule:
    """Defines a rate limiting rule."""
    max_requests: int
    window_seconds: int
    burst_limit: Optional[int] = None  # Allow short bursts above normal rate
    description: str = ""

@dataclass 
class RateLimitConfig:
    """Configuration for rate limiting."""
    # Global rate limits
    global_rate_limit: RateLimitRule = field(default_factory=lambda: RateLimitRule(100, 60, description="Global API rate limit"))
    
    # Per-IP rate limits
    ip_rate_limit: RateLimitRule = field(default_factory=lambda: RateLimitRule(50, 60, 10, description="Per-IP rate limit"))
    
    # Endpoint-specific rate limits
    auth_rate_limit: RateLimitRule = field(default_factory=lambda: RateLimitRule(10, 300, description="Authentication endpoint limit"))
    config_rate_limit: RateLimitRule = field(default_factory=lambda: RateLimitRule(20, 60, description="Configuration endpoint limit"))
    device_rate_limit: RateLimitRule = field(default_factory=lambda: RateLimitRule(30, 60, description="Device management endpoint limit"))
    
    # Security settings
    block_duration_seconds: int = 300  # 5 minutes block for violators
    enable_progressive_penalties: bool = True
    alert_threshold_percentage: float = 0.8  # Alert when 80% of limit reached
    
    # Monitoring settings
    log_violations: bool = True
    log_near_limits: bool = True

class TokenBucket:
    """Token bucket algorithm implementation for rate limiting."""
    
    def __init__(self, max_tokens: int, refill_rate: float, burst_tokens: Optional[int] = None):
        """
        Initialize token bucket.
        
        Args:
            max_tokens: Maximum number of tokens
            refill_rate: Tokens per second refill rate
            burst_tokens: Additional burst tokens allowed
        """
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.burst_tokens = burst_tokens or 0
        self.tokens = float(max_tokens)
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        async with self._lock:
            now = time.time()
            # Add tokens based on time passed
            time_passed = now - self.last_refill
            self.tokens = min(
                self.max_tokens + self.burst_tokens,
                self.tokens + (time_passed * self.refill_rate)
            )
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def get_tokens(self) -> float:
        """Get current token count."""
        return self.tokens

class RateLimitTracker:
    """Tracks rate limiting data and violations."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.ip_buckets: Dict[str, TokenBucket] = {}
        self.blocked_ips: Dict[str, float] = {}  # IP -> unblock_time
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.violation_counts: Dict[str, int] = defaultdict(int)
        self.alerts_sent: Dict[str, float] = {}  # Track alert cooldowns
        
    async def check_rate_limit(self, ip: str, endpoint_type: str) -> Tuple[bool, Optional[str]]:
        """
        Check if request should be rate limited.
        
        Args:
            ip: Client IP address
            endpoint_type: Type of endpoint (auth, config, device, etc.)
            
        Returns:
            Tuple of (allowed, reason if blocked)
        """
        now = time.time()
        
        # Check if IP is currently blocked
        if ip in self.blocked_ips:
            if now < self.blocked_ips[ip]:
                return False, f"IP blocked until {datetime.fromtimestamp(self.blocked_ips[ip])}"
            else:
                # Unblock IP
                del self.blocked_ips[ip]
                logger.info(f"IP {ip} unblocked after timeout")
        
        # Get appropriate rate limit rule
        rule = self._get_rate_limit_rule(endpoint_type)
        
        # Create token bucket for IP if doesn't exist
        if ip not in self.ip_buckets:
            self.ip_buckets[ip] = TokenBucket(
                max_tokens=rule.max_requests,
                refill_rate=rule.max_requests / rule.window_seconds,
                burst_tokens=rule.burst_limit
            )
        
        bucket = self.ip_buckets[ip]
        
        # Check if request can be processed
        if await bucket.consume():
            # Record request
            self.request_history[ip].append(now)
            
            # Check if approaching limit for alerting
            if self.config.log_near_limits:
                tokens_remaining = bucket.get_tokens()
                if tokens_remaining / rule.max_requests < (1 - self.config.alert_threshold_percentage):
                    await self._send_near_limit_alert(ip, endpoint_type, tokens_remaining, rule.max_requests)
            
            return True, None
        else:
            # Rate limit exceeded
            await self._handle_rate_limit_violation(ip, endpoint_type, rule)
            return False, f"Rate limit exceeded for {endpoint_type}: {rule.max_requests} requests per {rule.window_seconds}s"
    
    def _get_rate_limit_rule(self, endpoint_type: str) -> RateLimitRule:
        """Get rate limit rule for endpoint type."""
        endpoint_rules = {
            'auth': self.config.auth_rate_limit,
            'config': self.config.config_rate_limit, 
            'device': self.config.device_rate_limit,
            'api': self.config.ip_rate_limit,
        }
        return endpoint_rules.get(endpoint_type, self.config.global_rate_limit)
    
    async def _handle_rate_limit_violation(self, ip: str, endpoint_type: str, rule: RateLimitRule):
        """Handle rate limit violation."""
        self.violation_counts[ip] += 1
        
        if self.config.log_violations:
            logger.warning(f"Rate limit violation from IP {ip} on {endpoint_type} endpoint. "
                          f"Violation count: {self.violation_counts[ip]}")
        
        # Apply progressive penalties
        if self.config.enable_progressive_penalties:
            violation_count = self.violation_counts[ip]
            if violation_count >= 3:
                # Block IP for configured duration
                block_until = time.time() + self.config.block_duration_seconds
                self.blocked_ips[ip] = block_until
                logger.error(f"IP {ip} blocked until {datetime.fromtimestamp(block_until)} "
                           f"due to {violation_count} rate limit violations")
                
                # Send security alert
                await self._send_security_alert(ip, violation_count)
    
    async def _send_near_limit_alert(self, ip: str, endpoint_type: str, tokens_remaining: float, max_tokens: int):
        """Send alert when approaching rate limit."""
        alert_key = f"{ip}_{endpoint_type}_near_limit"
        now = time.time()
        
        # Cooldown of 60 seconds between alerts
        if alert_key in self.alerts_sent and now - self.alerts_sent[alert_key] < 60:
            return
            
        self.alerts_sent[alert_key] = now
        
        percentage_remaining = (tokens_remaining / max_tokens) * 100
        logger.info(f"IP {ip} approaching rate limit on {endpoint_type}: "
                   f"{percentage_remaining:.1f}% capacity remaining")
    
    async def _send_security_alert(self, ip: str, violation_count: int):
        """Send security alert for repeated violations."""
        alert_key = f"{ip}_security_alert"
        now = time.time()
        
        # Cooldown of 300 seconds between security alerts
        if alert_key in self.alerts_sent and now - self.alerts_sent[alert_key] < 300:
            return
            
        self.alerts_sent[alert_key] = now
        
        logger.error(f"SECURITY ALERT: IP {ip} has {violation_count} rate limit violations "
                    f"and has been temporarily blocked")
    
    def get_stats(self) -> Dict:
        """Get rate limiting statistics."""
        now = time.time()
        
        stats = {
            "active_ips": len(self.ip_buckets),
            "blocked_ips": len([ip for ip, unblock_time in self.blocked_ips.items() if now < unblock_time]),
            "total_violations": sum(self.violation_counts.values()),
            "top_violators": dict(sorted(self.violation_counts.items(), key=lambda x: x[1], reverse=True)[:5]),
            "current_blocks": {
                ip: datetime.fromtimestamp(unblock_time).isoformat() 
                for ip, unblock_time in self.blocked_ips.items() 
                if now < unblock_time
            }
        }
        
        return stats
    
    async def cleanup_old_data(self):
        """Clean up old rate limiting data."""
        now = time.time()
        cutoff_time = now - 3600  # Keep data for 1 hour
        
        # Clean up old request history
        for ip in list(self.request_history.keys()):
            history = self.request_history[ip]
            while history and history[0] < cutoff_time:
                history.popleft()
            if not history:
                del self.request_history[ip]
        
        # Clean up expired IP blocks
        expired_blocks = [ip for ip, unblock_time in self.blocked_ips.items() if now >= unblock_time]
        for ip in expired_blocks:
            del self.blocked_ips[ip]
        
        # Clean up old buckets for IPs with no recent activity
        inactive_ips = []
        for ip, bucket in self.ip_buckets.items():
            if ip in self.request_history:
                continue  # Has recent activity
            if ip not in self.blocked_ips:
                inactive_ips.append(ip)
        
        for ip in inactive_ips:
            del self.ip_buckets[ip]

class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for API rate limiting."""
    
    def __init__(self, app, config: Optional[RateLimitConfig] = None):
        super().__init__(app)
        self.config = config or RateLimitConfig()
        self.tracker = RateLimitTracker(self.config)
        self._cleanup_task = None
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Determine endpoint type
        endpoint_type = self._get_endpoint_type(request.url.path)
        
        # Check rate limit
        allowed, reason = await self.tracker.check_rate_limit(client_ip, endpoint_type)
        
        if not allowed:
            # Rate limit exceeded
            logger.warning(f"Rate limit exceeded for {client_ip} on {request.url.path}: {reason}")
            
            # Return 429 Too Many Requests
            return Response(
                content=json.dumps({
                    "error": "Rate limit exceeded",
                    "message": reason,
                    "retry_after": self.config.block_duration_seconds if client_ip in self.tracker.blocked_ips else 60
                }),
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
                headers={"Retry-After": str(60)}
            )
        
        # Process request normally
        response = await call_next(request)
        
        # Add rate limit headers
        rule = self.tracker._get_rate_limit_rule(endpoint_type)
        bucket = self.tracker.ip_buckets.get(client_ip)
        if bucket:
            remaining = max(0, int(bucket.get_tokens()))
            response.headers["X-RateLimit-Limit"] = str(rule.max_requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + rule.window_seconds))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded IP headers (for reverse proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _get_endpoint_type(self, path: str) -> str:
        """Determine endpoint type from request path."""
        if "/auth" in path or "/login" in path or "/token" in path:
            return "auth"
        elif "/config" in path:
            return "config"
        elif "/device" in path or "/zone" in path:
            return "device"
        else:
            return "api"
    
    async def start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop_cleanup_task(self):
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    async def _cleanup_loop(self):
        """Background task to clean up old rate limiting data."""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                await self.tracker.cleanup_old_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in rate limit cleanup task: {e}")
    
    def get_stats(self) -> Dict:
        """Get rate limiting statistics."""
        return self.tracker.get_stats()

# Configuration helper functions
def load_rate_limit_config(config_file: Optional[str] = None) -> RateLimitConfig:
    """Load rate limit configuration from file or use defaults."""
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Parse configuration
            config = RateLimitConfig()
            
            if 'global_rate_limit' in config_data:
                global_config = config_data['global_rate_limit']
                config.global_rate_limit = RateLimitRule(**global_config)
            
            # Add other configuration parsing as needed
            
            return config
        except Exception as e:
            logger.error(f"Error loading rate limit config from {config_file}: {e}")
    
    # Return default configuration
    return RateLimitConfig()

def create_development_config() -> RateLimitConfig:
    """Create a more permissive configuration for development."""
    return RateLimitConfig(
        global_rate_limit=RateLimitRule(1000, 60, description="Development global limit"),
        ip_rate_limit=RateLimitRule(500, 60, 50, description="Development IP limit"),
        auth_rate_limit=RateLimitRule(100, 300, description="Development auth limit"),
        config_rate_limit=RateLimitRule(200, 60, description="Development config limit"),
        device_rate_limit=RateLimitRule(300, 60, description="Development device limit"),
        block_duration_seconds=60,  # Shorter blocks in development
        enable_progressive_penalties=False,
        log_violations=True,
        log_near_limits=False
    )

def create_production_config() -> RateLimitConfig:
    """Create a strict configuration for production."""
    return RateLimitConfig(
        global_rate_limit=RateLimitRule(100, 60, description="Production global limit"),
        ip_rate_limit=RateLimitRule(50, 60, 10, description="Production IP limit"),
        auth_rate_limit=RateLimitRule(10, 300, description="Production auth limit"),
        config_rate_limit=RateLimitRule(20, 60, description="Production config limit"),
        device_rate_limit=RateLimitRule(30, 60, description="Production device limit"),
        block_duration_seconds=300,  # 5 minute blocks
        enable_progressive_penalties=True,
        alert_threshold_percentage=0.8,
        log_violations=True,
        log_near_limits=True
    )