"""
AI Provider Request Caching
Phase 5A: Performance Optimization

Implements intelligent caching for AI provider requests to reduce latency
and API costs while maintaining response quality.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional, Union, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import pickle

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache strategy types"""
    LRU = "lru"  # Least Recently Used
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Adaptive based on request patterns


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 1
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl_seconds is None:
            return False
        return (datetime.utcnow() - self.created_at).seconds > self.ttl_seconds
    
    def update_access(self):
        """Update access statistics"""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1
    
    def age_seconds(self) -> int:
        """Get age in seconds"""
        return (datetime.utcnow() - self.created_at).seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "key": self.key,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "ttl_seconds": self.ttl_seconds,
            "size_bytes": self.size_bytes,
            "age_seconds": self.age_seconds()
        }


class AIRequestCache:
    """Intelligent cache for AI provider requests"""
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 3600,  # 1 hour
        strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
        max_memory_mb: int = 100
    ):
        """
        Initialize AI request cache
        
        Args:
            max_size: Maximum number of cache entries
            default_ttl: Default TTL in seconds
            strategy: Cache eviction strategy
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.strategy = strategy
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        self._cache: Dict[str, CacheEntry] = {}
        self._enabled = True
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        # Strategy-specific data
        self._access_order: List[str] = []  # For LRU
        self._request_patterns: Dict[str, List[datetime]] = {}  # For adaptive
        
    def enable(self):
        """Enable caching"""
        self._enabled = True
        logger.info("AI request caching enabled")
    
    def disable(self):
        """Disable caching"""
        self._enabled = False
        logger.info("AI request caching disabled")
    
    def _generate_cache_key(
        self,
        provider: str,
        model: str,
        prompt: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate cache key for request"""
        # Create deterministic hash of request components
        key_data = {
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "parameters": parameters or {}
        }
        
        # Sort parameters for consistency
        if parameters:
            key_data["parameters"] = dict(sorted(parameters.items()))
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def _calculate_ttl(self, key: str, value: Any) -> int:
        """Calculate adaptive TTL based on request patterns"""
        if self.strategy != CacheStrategy.ADAPTIVE:
            return self.default_ttl
        
        # Analyze request patterns for this key type
        pattern_key = key[:8]  # Use prefix for pattern analysis
        patterns = self._request_patterns.get(pattern_key, [])
        
        if len(patterns) < 2:
            return self.default_ttl
        
        # Calculate average request frequency
        now = datetime.utcnow()
        recent_patterns = [p for p in patterns if (now - p).seconds < 3600]  # Last hour
        
        if len(recent_patterns) >= 3:
            # High frequency requests get longer TTL
            avg_interval = sum(
                (recent_patterns[i] - recent_patterns[i-1]).seconds 
                for i in range(1, len(recent_patterns))
            ) / (len(recent_patterns) - 1)
            
            if avg_interval < 300:  # < 5 minutes
                return self.default_ttl * 2  # Longer TTL for frequent requests
            elif avg_interval > 1800:  # > 30 minutes
                return self.default_ttl // 2  # Shorter TTL for infrequent requests
        
        return self.default_ttl
    
    def _calculate_entry_size(self, value: Any) -> int:
        """Calculate approximate size of cache entry"""
        try:
            return len(pickle.dumps(value))
        except Exception:
            # Fallback estimation
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, dict):
                return len(json.dumps(value).encode('utf-8'))
            else:
                return 1024  # Default estimate
    
    def _evict_entries(self):
        """Evict entries based on strategy"""
        if len(self._cache) <= self.max_size and self._get_total_size() <= self.max_memory_bytes:
            return
        
        entries_to_remove = []
        
        if self.strategy == CacheStrategy.LRU:
            # Remove least recently used entries
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k].last_accessed
            )
            entries_to_remove = sorted_keys[:len(self._cache) - self.max_size + 1]
            
        elif self.strategy == CacheStrategy.TTL:
            # Remove expired entries first, then oldest
            now = datetime.utcnow()
            expired_keys = [k for k, entry in self._cache.items() if entry.is_expired()]
            entries_to_remove.extend(expired_keys)
            
            if len(self._cache) - len(expired_keys) > self.max_size:
                remaining_keys = [k for k in self._cache.keys() if k not in expired_keys]
                sorted_keys = sorted(
                    remaining_keys,
                    key=lambda k: self._cache[k].created_at
                )
                entries_to_remove.extend(sorted_keys[:len(remaining_keys) - self.max_size])
                
        elif self.strategy == CacheStrategy.ADAPTIVE:
            # Remove based on access patterns and TTL
            now = datetime.utcnow()
            scored_entries = []
            
            for key, entry in self._cache.items():
                if entry.is_expired():
                    entries_to_remove.append(key)
                    continue
                
                # Calculate eviction score (lower = more likely to evict)
                age_score = entry.age_seconds() / 3600  # Age in hours
                access_score = entry.access_count / max(1, entry.age_seconds() / 3600)  # Access per hour
                size_score = entry.size_bytes / (1024 * 1024)  # Size in MB
                
                total_score = access_score - age_score - size_score
                scored_entries.append((key, total_score))
            
            # Sort by score and remove lowest scoring entries
            scored_entries.sort(key=lambda x: x[1])
            needed_removals = len(self._cache) - len(entries_to_remove) - self.max_size
            if needed_removals > 0:
                entries_to_remove.extend([key for key, _ in scored_entries[:needed_removals]])
        
        # Remove selected entries
        for key in entries_to_remove:
            if key in self._cache:
                del self._cache[key]
                self._evictions += 1
                if key in self._access_order:
                    self._access_order.remove(key)
        
        if entries_to_remove:
            logger.debug(f"Evicted {len(entries_to_remove)} cache entries")
    
    def _get_total_size(self) -> int:
        """Get total cache size in bytes"""
        return sum(entry.size_bytes for entry in self._cache.values())
    
    def _update_access_patterns(self, key: str):
        """Update request patterns for adaptive caching"""
        pattern_key = key[:8]
        if pattern_key not in self._request_patterns:
            self._request_patterns[pattern_key] = []
        
        patterns = self._request_patterns[pattern_key]
        patterns.append(datetime.utcnow())
        
        # Keep only recent patterns (last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self._request_patterns[pattern_key] = [p for p in patterns if p > cutoff]
    
    async def get(
        self,
        provider: str,
        model: str,
        prompt: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Get cached response for AI request"""
        if not self._enabled:
            return None
        
        key = self._generate_cache_key(provider, model, prompt, parameters)
        
        if key not in self._cache:
            self._misses += 1
            return None
        
        entry = self._cache[key]
        
        # Check if expired
        if entry.is_expired():
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            self._misses += 1
            return None
        
        # Update access statistics
        entry.update_access()
        self._hits += 1
        
        # Update access order for LRU
        if self.strategy == CacheStrategy.LRU and key in self._access_order:
            self._access_order.remove(key)
            self._access_order.append(key)
        
        # Update patterns for adaptive caching
        if self.strategy == CacheStrategy.ADAPTIVE:
            self._update_access_patterns(key)
        
        logger.debug(f"Cache hit for AI request: {provider}/{model}")
        return entry.value
    
    async def put(
        self,
        provider: str,
        model: str,
        prompt: str,
        response: Any,
        parameters: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ):
        """Cache AI request response"""
        if not self._enabled:
            return
        
        key = self._generate_cache_key(provider, model, prompt, parameters)
        
        # Calculate entry size
        size_bytes = self._calculate_entry_size(response)
        
        # Skip caching if response is too large
        if size_bytes > self.max_memory_bytes // 10:  # No single entry > 10% of max memory
            logger.warning(f"Skipping cache for large response: {size_bytes} bytes")
            return
        
        # Calculate TTL
        entry_ttl = ttl or self._calculate_ttl(key, response)
        
        # Create cache entry
        entry = CacheEntry(
            key=key,
            value=response,
            ttl_seconds=entry_ttl,
            size_bytes=size_bytes
        )
        
        # Store in cache
        self._cache[key] = entry
        
        # Update access order for LRU
        if self.strategy == CacheStrategy.LRU:
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
        
        # Update patterns for adaptive caching
        if self.strategy == CacheStrategy.ADAPTIVE:
            self._update_access_patterns(key)
        
        # Evict if necessary
        self._evict_entries()
        
        logger.debug(f"Cached AI response: {provider}/{model} (TTL: {entry_ttl}s)")
    
    def invalidate(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        pattern: Optional[str] = None
    ):
        """Invalidate cache entries matching criteria"""
        keys_to_remove = []
        
        for key, entry in self._cache.items():
            should_remove = False
            
            if pattern and pattern in key:
                should_remove = True
            elif provider or model:
                # Need to check cache key components
                # This is a simplified check - in practice you might want to store metadata
                if provider and provider in key:
                    should_remove = True
                elif model and model in key:
                    should_remove = True
            
            if should_remove:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
        
        if keys_to_remove:
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries")
    
    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()
        self._access_order.clear()
        self._request_patterns.clear()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        logger.info("AI request cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "enabled": self._enabled,
            "entries": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": hit_rate,
            "evictions": self._evictions,
            "total_size_mb": self._get_total_size() / (1024 * 1024),
            "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
            "strategy": self.strategy.value,
            "average_entry_size_kb": (
                self._get_total_size() / len(self._cache) / 1024 
                if self._cache else 0
            )
        }
    
    def get_entries_info(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get information about cache entries"""
        sorted_entries = sorted(
            self._cache.values(),
            key=lambda e: e.last_accessed,
            reverse=True
        )
        
        return [entry.to_dict() for entry in sorted_entries[:limit]]


# Global AI cache instance
_global_ai_cache = AIRequestCache()


def get_ai_cache() -> AIRequestCache:
    """Get global AI cache instance"""
    return _global_ai_cache


def cache_ai_request(
    ttl: Optional[int] = None,
    enabled: bool = True
):
    """Decorator for caching AI requests"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if not enabled or not _global_ai_cache._enabled:
                return await func(*args, **kwargs)
            
            # Extract cache key components from arguments
            # This is a simplified version - adjust based on your AI provider interface
            provider = kwargs.get('provider') or (args[0] if args else 'unknown')
            model = kwargs.get('model') or (args[1] if len(args) > 1 else 'unknown')
            prompt = kwargs.get('prompt') or (args[2] if len(args) > 2 else '')
            parameters = kwargs.get('parameters')
            
            # Try to get from cache
            cached_response = await _global_ai_cache.get(provider, model, prompt, parameters)
            if cached_response is not None:
                return cached_response
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            if result is not None:
                await _global_ai_cache.put(provider, model, prompt, result, parameters, ttl)
            
            return result
        
        return wrapper
    return decorator


# Global cache access functions
def get_ai_cache() -> AIRequestCache:
    """
    Get global AI cache instance.
    
    Returns:
        Global AIRequestCache instance
    """
    global _global_ai_cache
    return _global_ai_cache


def clear_ai_cache() -> None:
    """Clear the global AI cache."""
    global _global_ai_cache
    _global_ai_cache.clear()


def get_ai_cache_stats() -> Dict[str, Any]:
    """Get global AI cache statistics."""
    global _global_ai_cache
    return _global_ai_cache.get_stats()