"""
Simple Rate Limiting Middleware for AICleaner v3 Home Assistant Addon
"""

import time
import logging
import ipaddress
from collections import defaultdict, deque
from typing import Dict, Callable, List, Optional
from fastapi import Request, Response, status
from fastapi.middleware.base import BaseHTTPMiddleware
import json

logger = logging.getLogger(__name__)

class SimpleRateLimiter:
    """Simple rate limiter for single-user Home Assistant addon."""
    
    def __init__(self, 
                 requests_per_minute: int = 60, 
                 burst_allowance: int = 10,
                 block_duration_seconds: int = 120,
                 whitelist_local_network: bool = True):
        """
        Initialize simple rate limiter.
        
        Args:
            requests_per_minute: Normal rate limit (default: 60 requests/minute)
            burst_allowance: Extra requests allowed in burst (default: 10)
            block_duration_seconds: How long to block violating IPs (default: 120 seconds)
            whitelist_local_network: Skip rate limiting for local network IPs (default: True)
        """
        self.requests_per_minute = requests_per_minute
        self.burst_allowance = burst_allowance
        self.block_duration_seconds = block_duration_seconds
        self.whitelist_local_network = whitelist_local_network
        self.request_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=requests_per_minute + burst_allowance))
        self.blocked_until: Dict[str, float] = {}
        self.warning_threshold = int(requests_per_minute * 0.8)  # 80% warning threshold
        
    def _is_local_network(self, ip: str) -> bool:
        """Check if IP is from local network."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            local_ranges = [
                ipaddress.ip_network('192.168.0.0/16'),
                ipaddress.ip_network('10.0.0.0/8'), 
                ipaddress.ip_network('172.16.0.0/12'),
                ipaddress.ip_network('127.0.0.0/8')  # localhost
            ]
            return any(ip_obj in network for network in local_ranges)
        except (ValueError, ipaddress.AddressValueError):
            return False
    
    def is_allowed(self, client_ip: str) -> tuple[bool, str]:
        """
        Check if request from client IP is allowed.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            (allowed, reason)
        """
        # Whitelist local network IPs if enabled
        if self.whitelist_local_network and self._is_local_network(client_ip):
            return True, ""
        
        now = time.time()
        
        # Check if IP is currently blocked
        if client_ip in self.blocked_until:
            if now < self.blocked_until[client_ip]:
                remaining = int(self.blocked_until[client_ip] - now)
                return False, f"IP temporarily blocked for {remaining} seconds"
            else:
                # Unblock expired block
                del self.blocked_until[client_ip]
        
        # Get request history for this IP
        requests = self.request_times[client_ip]
        
        # Remove requests older than 1 minute
        minute_ago = now - 60
        while requests and requests[0] < minute_ago:
            requests.popleft()
        
        # Check for warning threshold (80% of normal limit, excluding burst)
        if len(requests) >= self.warning_threshold and len(requests) < self.requests_per_minute:
            logger.info(f"Rate limit warning for IP {client_ip}: {len(requests)}/{self.requests_per_minute} requests used")
        
        # Check if under rate limit
        if len(requests) < self.requests_per_minute + self.burst_allowance:
            # Add this request
            requests.append(now)
            return True, ""
        
        # Rate limit exceeded - block for configured duration
        self.blocked_until[client_ip] = now + self.block_duration_seconds
        logger.warning(f"Rate limit exceeded for IP {client_ip}. Blocked for {self.block_duration_seconds} seconds.")
        
        return False, f"Rate limit exceeded. Too many requests per minute."
    
    def get_stats(self) -> Dict:
        """Get simple statistics."""
        now = time.time()
        active_ips = len([ip for ip, requests in self.request_times.items() if requests])
        blocked_ips = len([ip for ip, until in self.blocked_until.items() if now < until])
        
        return {
            "active_ips": active_ips,
            "blocked_ips": blocked_ips,
            "requests_per_minute_limit": self.requests_per_minute,
            "burst_allowance": self.burst_allowance,
            "block_duration_seconds": self.block_duration_seconds,
            "whitelist_local_network": self.whitelist_local_network
        }
    
    def cleanup_old_data(self):
        """Clean up old data to prevent memory growth."""
        now = time.time()
        minute_ago = now - 60
        
        # Clean up old request times
        for ip in list(self.request_times.keys()):
            requests = self.request_times[ip]
            while requests and requests[0] < minute_ago:
                requests.popleft()
            # Remove empty deques
            if not requests:
                del self.request_times[ip]
        
        # Clean up expired blocks
        expired_blocks = [ip for ip, until in self.blocked_until.items() if now >= until]
        for ip in expired_blocks:
            del self.blocked_until[ip]

class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """Simple FastAPI middleware for basic DoS protection."""
    
    def __init__(self, 
                 app, 
                 enabled: bool = True, 
                 requests_per_minute: int = 60,
                 block_duration_seconds: int = 120,
                 whitelist_local_network: bool = True,
                 exempt_paths: Optional[List[str]] = None):
        """
        Initialize middleware.
        
        Args:
            app: FastAPI app
            enabled: Whether rate limiting is enabled (can disable for development)
            requests_per_minute: Rate limit (default: 60 requests/minute)
            block_duration_seconds: How long to block violating IPs (default: 120 seconds)
            whitelist_local_network: Skip rate limiting for local network IPs (default: True)
            exempt_paths: List of paths exempt from rate limiting (e.g., ['/health', '/'])
        """
        super().__init__(app)
        self.enabled = enabled
        self.exempt_paths = exempt_paths or ['/health', '/', '/api/health']
        self.rate_limiter = SimpleRateLimiter(
            requests_per_minute=requests_per_minute,
            block_duration_seconds=block_duration_seconds,
            whitelist_local_network=whitelist_local_network
        )
        self.last_cleanup = time.time()
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with simple rate limiting."""
        
        # Skip rate limiting if disabled (useful for development)
        if not self.enabled:
            return await call_next(request)
        
        # Skip rate limiting for exempt paths (health checks, etc.)
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Periodic cleanup (every 5 minutes)
        now = time.time()
        if now - self.last_cleanup > 300:
            self.rate_limiter.cleanup_old_data()
            self.last_cleanup = now
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        allowed, reason = self.rate_limiter.is_allowed(client_ip)
        
        if not allowed:
            logger.warning(f"Rate limit block: {client_ip} - {reason}")
            return Response(
                content=json.dumps({
                    "error": "Too Many Requests",
                    "message": reason
                }),
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
                headers={"Retry-After": str(self.rate_limiter.block_duration_seconds)}
            )
        
        # Process request normally
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check common proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Default to direct client IP
        return request.client.host if request.client else "unknown"
    
    def get_stats(self) -> Dict:
        """Get rate limiting statistics."""
        return self.rate_limiter.get_stats()

# Configuration helpers for Home Assistant addon
def create_addon_rate_limiter(development_mode: bool = False, addon_options: Optional[Dict] = None) -> SimpleRateLimitMiddleware:
    """
    Create rate limiter appropriate for Home Assistant addon.
    
    Args:
        development_mode: If True, uses more permissive settings
        addon_options: Home Assistant addon options for configuration
        
    Returns:
        Configured rate limit middleware
    """
    # Default configuration
    config = {
        "requests_per_minute": 60,
        "block_duration_seconds": 120,
        "whitelist_local_network": True,
        "exempt_paths": ['/health', '/', '/api/health']
    }
    
    # Override with addon options if provided
    if addon_options:
        config.update({
            "requests_per_minute": addon_options.get("rate_limit_requests_per_minute", config["requests_per_minute"]),
            "block_duration_seconds": addon_options.get("rate_limit_block_duration", config["block_duration_seconds"]),
            "whitelist_local_network": addon_options.get("rate_limit_whitelist_local", config["whitelist_local_network"])
        })
    
    if development_mode:
        # More permissive for development
        config.update({
            "requests_per_minute": 120,  # Higher limit for development
            "block_duration_seconds": 30,  # Shorter blocks for development
        })
    
    return SimpleRateLimitMiddleware(
        app=None,  # Will be set when added to app
        enabled=True,
        **config
    )

def create_disabled_rate_limiter() -> SimpleRateLimitMiddleware:
    """Create disabled rate limiter for testing or special cases."""
    return SimpleRateLimitMiddleware(
        app=None,
        enabled=False,
        requests_per_minute=0
    )

def create_production_rate_limiter() -> SimpleRateLimitMiddleware:
    """Create strict rate limiter for production use."""
    return SimpleRateLimitMiddleware(
        app=None,
        enabled=True,
        requests_per_minute=30,  # Stricter for production
        block_duration_seconds=300,  # 5 minute blocks
        whitelist_local_network=True,
        exempt_paths=['/health']  # Only essential health checks
    )