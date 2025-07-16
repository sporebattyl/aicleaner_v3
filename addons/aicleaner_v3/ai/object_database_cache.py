"""
Object Database Caching Layer

This module provides a high-performance caching layer for object database lookups
to minimize lookup times and improve overall system performance. The cache uses
LRU (Least Recently Used) eviction policy and supports TTL (Time To Live) for
cache entries.

Features:
- LRU cache with configurable size
- TTL-based cache expiration
- Performance metrics tracking
- Thread-safe operations
- Automatic cache warming for common objects
"""

import time
import threading
from typing import Dict, List, Any, Optional, Tuple
from collections import OrderedDict
import logging

from ai.object_database import ObjectDatabase


class ObjectDatabaseCache:
    """
    High-performance caching layer for object database lookups
    
    This cache improves performance by storing frequently accessed object
    information in memory with LRU eviction and TTL expiration.
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Initialize the object database cache
        
        Args:
            max_size: Maximum number of entries to cache
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.logger = logging.getLogger(__name__)
        
        # Thread-safe cache storage
        self._cache: OrderedDict[str, Tuple[Dict[str, Any], float]] = OrderedDict()
        self._lock = threading.RLock()
        
        # Performance metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        # Initialize object database
        self._object_db = ObjectDatabase()
        
        # Warm cache with common objects
        self._warm_cache()
    
    def _warm_cache(self):
        """
        Pre-populate cache with commonly accessed objects
        
        This improves performance for the most frequently used objects
        by ensuring they're always available in cache.
        """
        common_objects = [
            "dishes", "cup", "plate", "food", "clothes", "towel",
            "book", "shoe", "paper", "bottle", "trash", "toy"
        ]
        
        self.logger.info(f"Warming cache with {len(common_objects)} common objects")
        
        for obj_name in common_objects:
            # This will populate the cache
            self.get_object_info(obj_name)
    
    def get_object_info(self, object_name: str) -> Optional[Dict[str, Any]]:
        """
        Get object information with caching
        
        Args:
            object_name: Name of the object to look up
            
        Returns:
            Dictionary with object information or None if not found
        """
        cache_key = object_name.lower().strip()
        current_time = time.time()
        
        with self._lock:
            # Check if object is in cache and not expired
            if cache_key in self._cache:
                cached_data, timestamp = self._cache[cache_key]
                
                # Check if cache entry is still valid
                if current_time - timestamp < self.ttl_seconds:
                    # Move to end (most recently used)
                    self._cache.move_to_end(cache_key)
                    self._hits += 1
                    self.logger.debug(f"Cache hit for object: {object_name}")
                    return cached_data.copy() if cached_data else None
                else:
                    # Cache entry expired, remove it
                    del self._cache[cache_key]
                    self.logger.debug(f"Cache entry expired for object: {object_name}")
            
            # Cache miss - fetch from database
            self._misses += 1
            self.logger.debug(f"Cache miss for object: {object_name}")
            
            object_info = self._object_db.get_object_info(object_name)
            
            # Store in cache
            self._cache[cache_key] = (object_info, current_time)
            
            # Enforce cache size limit
            if len(self._cache) > self.max_size:
                # Remove least recently used item
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._evictions += 1
                self.logger.debug(f"Evicted cache entry: {oldest_key}")
            
            return object_info.copy() if object_info else None
    
    def get_objects_by_priority(self, min_priority: int = 1) -> List[str]:
        """
        Get objects by priority with caching
        
        Args:
            min_priority: Minimum priority level
            
        Returns:
            List of object names sorted by priority
        """
        # For list operations, we delegate to the database
        # These are less frequently called and more complex to cache
        return self._object_db.get_objects_by_priority(min_priority)
    
    def get_high_priority_objects(self) -> List[str]:
        """
        Get high priority objects with caching
        
        Returns:
            List of high-priority object names
        """
        cache_key = "_high_priority_objects"
        current_time = time.time()
        
        with self._lock:
            if cache_key in self._cache:
                cached_data, timestamp = self._cache[cache_key]
                
                if current_time - timestamp < self.ttl_seconds:
                    self._cache.move_to_end(cache_key)
                    self._hits += 1
                    return cached_data.copy()
                else:
                    del self._cache[cache_key]
            
            # Cache miss
            self._misses += 1
            high_priority_objects = self._object_db.get_high_priority_objects()
            
            # Store in cache
            self._cache[cache_key] = (high_priority_objects, current_time)
            
            return high_priority_objects.copy()
    
    def get_safety_critical_objects(self) -> List[str]:
        """
        Get safety critical objects with caching
        
        Returns:
            List of safety-critical object names
        """
        cache_key = "_safety_critical_objects"
        current_time = time.time()
        
        with self._lock:
            if cache_key in self._cache:
                cached_data, timestamp = self._cache[cache_key]
                
                if current_time - timestamp < self.ttl_seconds:
                    self._cache.move_to_end(cache_key)
                    self._hits += 1
                    return cached_data.copy()
                else:
                    del self._cache[cache_key]
            
            # Cache miss
            self._misses += 1
            safety_critical_objects = self._object_db.get_safety_critical_objects()
            
            # Store in cache
            self._cache[cache_key] = (safety_critical_objects, current_time)
            
            return safety_critical_objects.copy()
    
    def get_hygiene_critical_objects(self) -> List[str]:
        """
        Get hygiene critical objects with caching
        
        Returns:
            List of hygiene-critical object names
        """
        cache_key = "_hygiene_critical_objects"
        current_time = time.time()
        
        with self._lock:
            if cache_key in self._cache:
                cached_data, timestamp = self._cache[cache_key]
                
                if current_time - timestamp < self.ttl_seconds:
                    self._cache.move_to_end(cache_key)
                    self._hits += 1
                    return cached_data.copy()
                else:
                    del self._cache[cache_key]
            
            # Cache miss
            self._misses += 1
            hygiene_critical_objects = self._object_db.get_hygiene_critical_objects()
            
            # Store in cache
            self._cache[cache_key] = (hygiene_critical_objects, current_time)
            
            return hygiene_critical_objects.copy()
    
    def clear_cache(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self.logger.info("Cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics
        
        Returns:
            Dictionary with cache performance metrics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percent": round(hit_rate, 2),
                "evictions": self._evictions,
                "cache_size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds
            }
    
    def get_cache_info(self) -> str:
        """
        Get human-readable cache information
        
        Returns:
            Formatted string with cache statistics
        """
        stats = self.get_cache_stats()
        return (
            f"Object Database Cache Stats:\n"
            f"  Hit Rate: {stats['hit_rate_percent']}% "
            f"({stats['hits']} hits, {stats['misses']} misses)\n"
            f"  Cache Size: {stats['cache_size']}/{stats['max_size']}\n"
            f"  Evictions: {stats['evictions']}\n"
            f"  TTL: {stats['ttl_seconds']}s"
        )
    
    def reset_stats(self):
        """Reset performance statistics"""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            self.logger.info("Cache statistics reset")
    
    def set_ttl(self, ttl_seconds: int):
        """
        Update cache TTL
        
        Args:
            ttl_seconds: New TTL in seconds
        """
        self.ttl_seconds = ttl_seconds
        self.logger.info(f"Cache TTL updated to {ttl_seconds} seconds")
    
    def preload_objects(self, object_names: List[str]):
        """
        Preload specific objects into cache
        
        Args:
            object_names: List of object names to preload
        """
        self.logger.info(f"Preloading {len(object_names)} objects into cache")
        
        for obj_name in object_names:
            self.get_object_info(obj_name)
        
        self.logger.info("Object preloading complete")
