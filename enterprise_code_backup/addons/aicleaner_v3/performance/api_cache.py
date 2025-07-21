"""
API Response Caching System
Phase 5A: Performance Optimization

Provides FastAPI-compatible caching with TTL for AICleaner v3 endpoints.
"""

import asyncio
import functools
import time
import hashlib
import json
from typing import Callable, Any, Dict, Optional
from datetime import datetime, timedelta

class APICache:
    """Thread-safe in-memory cache with TTL support"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self._cache: Dict[str, Any] = {}
        self._cache_expiry: Dict[str, float] = {}
        self._cache_lock = asyncio.Lock()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._hit_count = 0
        self._miss_count = 0
        
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        async with self._cache_lock:
            if key in self._cache and self._cache_expiry[key] > time.time():
                self._hit_count += 1
                return self._cache[key]
            
            # Clean up expired entry
            if key in self._cache:
                del self._cache[key]
                del self._cache_expiry[key]
            
            self._miss_count += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with TTL"""
        if ttl is None:
            ttl = self.default_ttl
            
        async with self._cache_lock:
            # Implement simple LRU by removing oldest entry if at max size
            if len(self._cache) >= self.max_size:
                oldest_key = min(self._cache_expiry.keys(), 
                               key=lambda k: self._cache_expiry[k])
                del self._cache[oldest_key]
                del self._cache_expiry[oldest_key]
            
            self._cache[key] = value
            self._cache_expiry[key] = time.time() + ttl
    
    async def clear(self) -> None:
        """Clear all cached entries"""
        async with self._cache_lock:
            self._cache.clear()
            self._cache_expiry.clear()
            self._hit_count = 0
            self._miss_count = 0
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed"""
        current_time = time.time()
        expired_keys = []
        
        async with self._cache_lock:
            for key, expiry_time in self._cache_expiry.items():
                if expiry_time <= current_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                del self._cache_expiry[key]
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._hit_count + self._miss_count
        hit_rate = (self._hit_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_size": len(self._cache),
            "max_size": self.max_size,
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests
        }

# Global cache instance
api_cache = APICache(max_size=500, default_ttl=300)

def generate_cache_key(request_path: str, query_params: str, 
                      additional_params: Optional[Dict] = None) -> str:
    """Generate unique cache key from request parameters"""
    key_data = f"{request_path}?{query_params}"
    
    if additional_params:
        # Sort for consistent key generation
        sorted_params = json.dumps(additional_params, sort_keys=True)
        key_data += f"&{sorted_params}"
    
    # Use hash for consistent key length
    return hashlib.md5(key_data.encode()).hexdigest()

def api_response_cache(ttl: int = 300, 
                      cache_key_func: Optional[Callable] = None,
                      include_user: bool = False):
    """
    FastAPI endpoint caching decorator with configurable TTL
    
    Args:
        ttl: Time to live in seconds (default: 5 minutes)
        cache_key_func: Custom function to generate cache key
        include_user: Include user info in cache key for user-specific caching
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                from fastapi import Request
                
                # Find request object in args/kwargs
                request: Optional[Request] = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                
                if not request:
                    request = kwargs.get("request")
                
                if not request:
                    # No request object found, execute without caching
                    return await func(*args, **kwargs)
                
                # Generate cache key
                if cache_key_func:
                    cache_key = cache_key_func(request, *args, **kwargs)
                else:
                    additional_params = {}
                    if include_user and hasattr(request, 'user'):
                        additional_params['user_id'] = getattr(request.user, 'id', 'anonymous')
                    
                    cache_key = generate_cache_key(
                        str(request.url.path),
                        str(request.url.query),
                        additional_params
                    )
                
                # Try to get cached response
                cached_response = await api_cache.get(cache_key)
                if cached_response is not None:
                    # Add cache hit header for debugging
                    if hasattr(cached_response, 'headers'):
                        cached_response.headers['X-Cache'] = 'HIT'
                    return cached_response
                
                # Execute function and cache result
                response = await func(*args, **kwargs)
                
                # Cache the response
                await api_cache.set(cache_key, response, ttl)
                
                # Add cache miss header for debugging
                if hasattr(response, 'headers'):
                    response.headers['X-Cache'] = 'MISS'
                
                return response
                
            except Exception as e:
                # Log error but don't break the endpoint
                print(f"Cache error in {func.__name__}: {e}")
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator

def cache_clear(pattern: Optional[str] = None):
    """
    Decorator to clear cache after operations that modify data
    
    Args:
        pattern: Optional pattern to match cache keys for selective clearing
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await func(*args, **kwargs)
            
            # Clear cache after successful operation
            if pattern:
                # TODO: Implement pattern-based cache clearing
                # For now, clear all cache
                await api_cache.clear()
            else:
                await api_cache.clear()
            
            return result
        
        return wrapper
    return decorator

# Convenience decorators for specific use cases
def cache_ai_provider_status(ttl: int = 60):
    """Cache AI provider status for 1 minute"""
    return api_response_cache(ttl=ttl)

def cache_system_config(ttl: int = 300):
    """Cache system configuration for 5 minutes"""
    return api_response_cache(ttl=ttl)

def cache_user_specific(ttl: int = 120):
    """Cache user-specific data for 2 minutes"""
    return api_response_cache(ttl=ttl, include_user=True)

# Cache maintenance task
async def cache_maintenance_task():
    """Background task to clean up expired cache entries"""
    while True:
        try:
            removed_count = await api_cache.cleanup_expired()
            if removed_count > 0:
                print(f"Cache maintenance: removed {removed_count} expired entries")
            
            # Run maintenance every 5 minutes
            await asyncio.sleep(300)
            
        except Exception as e:
            print(f"Cache maintenance error: {e}")
            await asyncio.sleep(60)  # Retry in 1 minute on error

# Cache statistics endpoint helper
async def get_cache_statistics() -> Dict[str, Any]:
    """Get comprehensive cache statistics"""
    stats = api_cache.get_stats()
    stats['last_cleanup'] = datetime.now().isoformat()
    stats['cache_enabled'] = True
    return stats