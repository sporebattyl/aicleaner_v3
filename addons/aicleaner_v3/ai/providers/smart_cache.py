"""
Smart Caching Layer
Cloud Integration Optimization - Phase 3

Intelligent caching system with Privacy Pipeline integration, content-aware
caching strategies, and optimized cache invalidation for cloud API optimization.
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import tempfile
import threading

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .enhanced_config import ContentType, ProcessingPriority
from .content_analyzer import ContentAnalysisResult
from ..base_provider import AIRequest, AIResponse


class CacheStrategy(Enum):
    """Cache strategy types"""
    AGGRESSIVE = "aggressive"      # Cache everything aggressively
    CONSERVATIVE = "conservative"  # Cache only safe, non-sensitive content
    PRIVACY_AWARE = "privacy_aware" # Cache with privacy considerations
    PERFORMANCE = "performance"    # Cache for maximum performance
    COST_OPTIMIZED = "cost_optimized" # Cache to minimize costs


class CacheInvalidationReason(Enum):
    """Reasons for cache invalidation"""
    TTL_EXPIRED = "ttl_expired"
    PRIVACY_UPDATE = "privacy_update"
    PROVIDER_FAILURE = "provider_failure"
    MANUAL_CLEAR = "manual_clear"
    SIZE_LIMIT = "size_limit"
    QUALITY_THRESHOLD = "quality_threshold"


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    response: AIResponse
    content_analysis: ContentAnalysisResult
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl_seconds: int = 3600
    privacy_safe: bool = True
    provider_used: str = ""
    cost_saved: float = 0.0
    size_bytes: int = 0
    tags: Set[str] = field(default_factory=set)


@dataclass
class CacheStats:
    """Cache performance statistics"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_invalidations: int = 0
    total_cost_saved: float = 0.0
    total_time_saved: float = 0.0
    hit_rate: float = 0.0
    avg_response_time: float = 0.0
    cache_size_bytes: int = 0
    cache_entries: int = 0


class SmartCache:
    """
    Smart Caching Layer for AI Provider optimization.
    
    Features:
    - Content-aware caching strategies
    - Privacy Pipeline integration
    - Multi-tier caching (memory + distributed)
    - Intelligent cache invalidation
    - Cost and performance optimization
    - Cache warming and preloading
    """
    
    def __init__(
        self,
        config: Dict[str, Any] = None,
        strategy: CacheStrategy = CacheStrategy.PRIVACY_AWARE,
        redis_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Smart Cache.
        
        Args:
            config: Cache configuration
            strategy: Caching strategy to use
            redis_config: Redis configuration for distributed caching
        """
        self.config = config or {}
        self.strategy = strategy
        self.logger = logging.getLogger("smart_cache")
        
        # Cache storage
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.distributed_cache = None
        
        # Cache configuration
        self.max_memory_size = self.config.get("max_memory_size", 100 * 1024 * 1024)  # 100MB
        self.default_ttl = self.config.get("default_ttl", 3600)  # 1 hour
        self.max_entries = self.config.get("max_entries", 10000)
        
        # Privacy Pipeline integration
        self.privacy_pipeline_enabled = self.config.get("privacy_pipeline_enabled", True)
        self.privacy_safe_only = self.config.get("privacy_safe_only", True)
        
        # Performance tracking
        self.stats = CacheStats()
        self.lock = threading.RLock()
        
        # Content-type specific TTL configurations
        self.content_ttl_config = self._initialize_content_ttl()
        
        # Initialize Redis if available and configured
        if REDIS_AVAILABLE and redis_config:
            self._initialize_redis(redis_config)
        
        # Start background maintenance
        self._start_maintenance_tasks()
        
        self.logger.info(f"Smart Cache initialized with strategy: {strategy.value}")
    
    def _initialize_content_ttl(self) -> Dict[ContentType, int]:
        """Initialize content-type specific TTL configurations"""
        return {
            ContentType.TEXT: 3600,           # 1 hour for text
            ContentType.IMAGE: 7200,          # 2 hours for images
            ContentType.CODE: 1800,           # 30 minutes for code (changes frequently)
            ContentType.MULTIMODAL: 1800,     # 30 minutes for complex content
            ContentType.DOCUMENT: 14400,      # 4 hours for documents
            ContentType.STRUCTURED_DATA: 7200, # 2 hours for structured data
        }
    
    def _initialize_redis(self, redis_config: Dict[str, Any]):
        """Initialize Redis distributed cache"""
        try:
            self.distributed_cache = redis.Redis(
                host=redis_config.get("host", "localhost"),
                port=redis_config.get("port", 6379),
                db=redis_config.get("db", 0),
                password=redis_config.get("password"),
                decode_responses=False,  # We'll handle encoding ourselves
                socket_timeout=redis_config.get("timeout", 5),
                socket_connect_timeout=redis_config.get("connect_timeout", 5)
            )
            
            # Test connection
            self.distributed_cache.ping()
            self.logger.info("Redis distributed cache initialized successfully")
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize Redis: {e}")
            self.distributed_cache = None
    
    def _start_maintenance_tasks(self):
        """Start background maintenance tasks"""
        def maintenance_worker():
            while True:
                try:
                    self._cleanup_expired_entries()
                    self._enforce_size_limits()
                    self._update_statistics()
                    time.sleep(300)  # Run every 5 minutes
                except Exception as e:
                    self.logger.error(f"Cache maintenance error: {e}")
                    time.sleep(60)  # Retry after 1 minute on error
        
        maintenance_thread = threading.Thread(target=maintenance_worker, daemon=True)
        maintenance_thread.start()
    
    async def get(
        self,
        request: AIRequest,
        content_analysis: ContentAnalysisResult
    ) -> Optional[AIResponse]:
        """
        Get cached response for request.
        
        Args:
            request: AI request
            content_analysis: Content analysis result
            
        Returns:
            Cached response if available, None otherwise
        """
        cache_key = self._generate_cache_key(request, content_analysis)
        
        with self.lock:
            self.stats.total_requests += 1
        
        try:
            # Check memory cache first
            entry = await self._get_from_memory(cache_key)
            if not entry:
                # Check distributed cache
                entry = await self._get_from_distributed(cache_key)
                if entry:
                    # Promote to memory cache
                    await self._store_in_memory(cache_key, entry)
            
            if entry:
                # Validate cache entry
                if self._is_entry_valid(entry, content_analysis):
                    # Update access tracking
                    entry.last_accessed = time.time()
                    entry.access_count += 1
                    
                    with self.lock:
                        self.stats.cache_hits += 1
                        self.stats.total_cost_saved += entry.cost_saved
                        self.stats.total_time_saved += entry.response.response_time
                    
                    # Mark response as cached
                    cached_response = self._create_cached_response(entry.response)
                    
                    self.logger.info(
                        json.dumps({
                            "event": "cache_hit",
                            "cache_key": cache_key[:16],
                            "content_type": content_analysis.content_type.value,
                            "provider": entry.provider_used,
                            "cost_saved": entry.cost_saved,
                            "time_saved": entry.response.response_time
                        })
                    )
                    
                    return cached_response
                else:
                    # Invalid entry, remove it
                    await self._invalidate_entry(cache_key, CacheInvalidationReason.QUALITY_THRESHOLD)
            
            # Cache miss
            with self.lock:
                self.stats.cache_misses += 1
            
            return None
            
        except Exception as e:
            self.logger.error(f"Cache get error: {e}")
            return None
    
    async def put(
        self,
        request: AIRequest,
        response: AIResponse,
        content_analysis: ContentAnalysisResult
    ) -> bool:
        """
        Store response in cache.
        
        Args:
            request: Original AI request
            response: AI response to cache
            content_analysis: Content analysis result
            
        Returns:
            True if cached successfully, False otherwise
        """
        try:
            # Check if content should be cached
            if not self._should_cache_content(content_analysis, response):
                return False
            
            cache_key = self._generate_cache_key(request, content_analysis)
            
            # Create cache entry
            entry = CacheEntry(
                key=cache_key,
                response=response,
                content_analysis=content_analysis,
                created_at=time.time(),
                last_accessed=time.time(),
                ttl_seconds=self._get_ttl_for_content(content_analysis),
                privacy_safe=not content_analysis.privacy_sensitive,
                provider_used=response.provider,
                cost_saved=response.cost,
                size_bytes=self._estimate_entry_size(response),
                tags=self._generate_cache_tags(content_analysis, request)
            )
            
            # Store in memory cache
            await self._store_in_memory(cache_key, entry)
            
            # Store in distributed cache if available
            if self.distributed_cache:
                await self._store_in_distributed(cache_key, entry)
            
            self.logger.info(
                json.dumps({
                    "event": "cache_store",
                    "cache_key": cache_key[:16],
                    "content_type": content_analysis.content_type.value,
                    "provider": response.provider,
                    "ttl_seconds": entry.ttl_seconds,
                    "privacy_safe": entry.privacy_safe,
                    "cost": response.cost
                })
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Cache put error: {e}")
            return False
    
    def _should_cache_content(
        self,
        content_analysis: ContentAnalysisResult,
        response: AIResponse
    ) -> bool:
        """Determine if content should be cached based on strategy and analysis"""
        
        # Never cache if response has error
        if response.error:
            return False
        
        # Strategy-based decisions
        if self.strategy == CacheStrategy.CONSERVATIVE:
            # Only cache non-sensitive, high-confidence content
            if content_analysis.privacy_sensitive or content_analysis.confidence < 0.8:
                return False
        
        elif self.strategy == CacheStrategy.PRIVACY_AWARE:
            # Respect privacy settings
            if self.privacy_safe_only and content_analysis.privacy_sensitive:
                return False
        
        elif self.strategy == CacheStrategy.PERFORMANCE:
            # Cache everything for performance (unless explicitly privacy sensitive)
            if content_analysis.privacy_sensitive and "privacy_sensitive" in content_analysis.processing_hints:
                return False
        
        # Content-type specific rules
        if content_analysis.content_type == ContentType.CODE:
            # Cache code only if it's not configuration or sensitive
            if any(hint in content_analysis.processing_hints for hint in ["privacy_sensitive", "require_privacy_pipeline"]):
                return False
        
        # Quality threshold
        if response.confidence < 0.7:
            return False
        
        return True
    
    def _get_ttl_for_content(self, content_analysis: ContentAnalysisResult) -> int:
        """Get TTL for content based on type and characteristics"""
        base_ttl = self.content_ttl_config.get(content_analysis.content_type, self.default_ttl)
        
        # Adjust based on content characteristics
        if content_analysis.privacy_sensitive:
            base_ttl = min(base_ttl, 1800)  # Max 30 minutes for sensitive content
        
        if content_analysis.complexity_score > 0.8:
            base_ttl = int(base_ttl * 1.5)  # Cache complex content longer
        
        if content_analysis.confidence < 0.8:
            base_ttl = int(base_ttl * 0.5)  # Cache low-confidence content shorter
        
        return base_ttl
    
    def _generate_cache_key(
        self,
        request: AIRequest,
        content_analysis: ContentAnalysisResult
    ) -> str:
        """Generate cache key for request and content analysis"""
        key_components = []
        
        # Content hash
        content_hash = hashlib.sha256(request.prompt.encode()).hexdigest()[:32]
        key_components.append(f"content:{content_hash}")
        
        # Content type
        key_components.append(f"type:{content_analysis.content_type.value}")
        
        # Image hash if present
        if request.image_path:
            image_hash = hashlib.sha256(str(request.image_path).encode()).hexdigest()[:16]
            key_components.append(f"img:{image_hash}")
        elif request.image_data:
            image_hash = hashlib.sha256(request.image_data).hexdigest()[:16]
            key_components.append(f"imgdata:{image_hash}")
        
        # Model parameters (if they affect output)
        if request.model_name:
            key_components.append(f"model:{request.model_name}")
        if request.temperature:
            key_components.append(f"temp:{request.temperature}")
        if request.max_tokens:
            key_components.append(f"tokens:{request.max_tokens}")
        
        # Privacy considerations
        if content_analysis.privacy_sensitive:
            key_components.append("privacy:sensitive")
        
        return "|".join(key_components)
    
    def _generate_cache_tags(
        self,
        content_analysis: ContentAnalysisResult,
        request: AIRequest
    ) -> Set[str]:
        """Generate tags for cache entry categorization"""
        tags = set()
        
        # Content type tags
        tags.add(f"content_type:{content_analysis.content_type.value}")
        for secondary_type in content_analysis.secondary_types:
            tags.add(f"secondary:{secondary_type}")
        
        # Complexity tags
        if content_analysis.complexity_score > 0.8:
            tags.add("complexity:high")
        elif content_analysis.complexity_score < 0.3:
            tags.add("complexity:low")
        else:
            tags.add("complexity:medium")
        
        # Privacy tags
        if content_analysis.privacy_sensitive:
            tags.add("privacy:sensitive")
        else:
            tags.add("privacy:safe")
        
        # Size tags
        if content_analysis.size_estimate > 2000:
            tags.add("size:large")
        elif content_analysis.size_estimate < 100:
            tags.add("size:small")
        else:
            tags.add("size:medium")
        
        # Request tags
        if request.priority:
            tags.add(f"priority:{request.priority}")
        
        return tags
    
    async def _get_from_memory(self, cache_key: str) -> Optional[CacheEntry]:
        """Get entry from memory cache"""
        with self.lock:
            entry = self.memory_cache.get(cache_key)
            if entry and not self._is_entry_expired(entry):
                return entry
        return None
    
    async def _get_from_distributed(self, cache_key: str) -> Optional[CacheEntry]:
        """Get entry from distributed cache"""
        if not self.distributed_cache:
            return None
        
        try:
            data = self.distributed_cache.get(f"aicache:{cache_key}")
            if data:
                entry = pickle.loads(data)
                if not self._is_entry_expired(entry):
                    return entry
                else:
                    # Remove expired entry
                    self.distributed_cache.delete(f"aicache:{cache_key}")
        except Exception as e:
            self.logger.warning(f"Distributed cache get error: {e}")
        
        return None
    
    async def _store_in_memory(self, cache_key: str, entry: CacheEntry):
        """Store entry in memory cache"""
        with self.lock:
            self.memory_cache[cache_key] = entry
    
    async def _store_in_distributed(self, cache_key: str, entry: CacheEntry):
        """Store entry in distributed cache"""
        if not self.distributed_cache:
            return
        
        try:
            data = pickle.dumps(entry)
            self.distributed_cache.setex(
                f"aicache:{cache_key}",
                entry.ttl_seconds,
                data
            )
        except Exception as e:
            self.logger.warning(f"Distributed cache store error: {e}")
    
    def _is_entry_valid(self, entry: CacheEntry, content_analysis: ContentAnalysisResult) -> bool:
        """Check if cache entry is valid for current request"""
        # Check expiration
        if self._is_entry_expired(entry):
            return False
        
        # Check content type consistency
        if entry.content_analysis.content_type != content_analysis.content_type:
            return False
        
        # Check privacy consistency
        if content_analysis.privacy_sensitive and not entry.privacy_safe:
            return False
        
        # Check confidence threshold
        if entry.response.confidence < 0.7:
            return False
        
        return True
    
    def _is_entry_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired"""
        return time.time() - entry.created_at > entry.ttl_seconds
    
    def _create_cached_response(self, original_response: AIResponse) -> AIResponse:
        """Create a cached version of the response"""
        cached_response = AIResponse(
            request_id=original_response.request_id,
            response_text=original_response.response_text,
            model_used=original_response.model_used,
            provider=original_response.provider,
            confidence=original_response.confidence,
            cost=0.0,  # No cost for cached response
            response_time=0.001,  # Minimal time for cache hit
            cached=True,
            error=original_response.error,
            metadata=original_response.metadata.copy(),
            created_at=datetime.now().isoformat()
        )
        
        # Add cache metadata
        cached_response.metadata.update({
            "cache_hit": True,
            "original_cost": original_response.cost,
            "original_response_time": original_response.response_time,
            "cache_retrieval_time": time.time()
        })
        
        return cached_response
    
    def _estimate_entry_size(self, response: AIResponse) -> int:
        """Estimate memory size of cache entry"""
        size = len(response.response_text.encode('utf-8'))
        size += len(json.dumps(response.metadata).encode('utf-8'))
        size += 1024  # Overhead for entry structure
        return size
    
    async def _invalidate_entry(self, cache_key: str, reason: CacheInvalidationReason):
        """Invalidate cache entry"""
        with self.lock:
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]
                self.stats.cache_invalidations += 1
        
        if self.distributed_cache:
            try:
                self.distributed_cache.delete(f"aicache:{cache_key}")
            except Exception as e:
                self.logger.warning(f"Distributed cache invalidation error: {e}")
        
        self.logger.debug(f"Cache entry invalidated: {cache_key[:16]}... (reason: {reason.value})")
    
    def _cleanup_expired_entries(self):
        """Clean up expired cache entries"""
        with self.lock:
            expired_keys = [
                key for key, entry in self.memory_cache.items()
                if self._is_entry_expired(entry)
            ]
            
            for key in expired_keys:
                del self.memory_cache[key]
                self.stats.cache_invalidations += 1
        
        if expired_keys:
            self.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _enforce_size_limits(self):
        """Enforce memory cache size limits"""
        with self.lock:
            current_size = sum(entry.size_bytes for entry in self.memory_cache.values())
            
            if current_size > self.max_memory_size or len(self.memory_cache) > self.max_entries:
                # Remove least recently used entries
                sorted_entries = sorted(
                    self.memory_cache.items(),
                    key=lambda x: x[1].last_accessed
                )
                
                entries_to_remove = len(sorted_entries) - self.max_entries + 100  # Remove extra for buffer
                if current_size > self.max_memory_size:
                    entries_to_remove = max(entries_to_remove, len(sorted_entries) // 4)  # Remove 25%
                
                for i in range(min(entries_to_remove, len(sorted_entries))):
                    key, _ = sorted_entries[i]
                    del self.memory_cache[key]
                    self.stats.cache_invalidations += 1
                
                if entries_to_remove > 0:
                    self.logger.info(f"Removed {entries_to_remove} cache entries to enforce size limits")
    
    def _update_statistics(self):
        """Update cache statistics"""
        with self.lock:
            if self.stats.total_requests > 0:
                self.stats.hit_rate = self.stats.cache_hits / self.stats.total_requests
            
            self.stats.cache_entries = len(self.memory_cache)
            self.stats.cache_size_bytes = sum(entry.size_bytes for entry in self.memory_cache.values())
            
            if self.stats.cache_hits > 0:
                self.stats.avg_response_time = self.stats.total_time_saved / self.stats.cache_hits
    
    async def invalidate_by_provider(self, provider_name: str):
        """Invalidate all cache entries for a specific provider"""
        invalidated_count = 0
        
        with self.lock:
            keys_to_remove = [
                key for key, entry in self.memory_cache.items()
                if entry.provider_used == provider_name
            ]
            
            for key in keys_to_remove:
                del self.memory_cache[key]
                invalidated_count += 1
                self.stats.cache_invalidations += 1
        
        # Also invalidate in distributed cache
        if self.distributed_cache:
            try:
                # This is a simplified approach - in production, you'd want to use cache tagging
                pass
            except Exception as e:
                self.logger.warning(f"Distributed cache provider invalidation error: {e}")
        
        self.logger.info(f"Invalidated {invalidated_count} cache entries for provider: {provider_name}")
    
    async def invalidate_by_tags(self, tags: Set[str]):
        """Invalidate cache entries matching any of the provided tags"""
        invalidated_count = 0
        
        with self.lock:
            keys_to_remove = [
                key for key, entry in self.memory_cache.items()
                if entry.tags.intersection(tags)
            ]
            
            for key in keys_to_remove:
                del self.memory_cache[key]
                invalidated_count += 1
                self.stats.cache_invalidations += 1
        
        self.logger.info(f"Invalidated {invalidated_count} cache entries with tags: {tags}")
    
    async def warm_cache(self, requests: List[Tuple[AIRequest, ContentAnalysisResult]]):
        """Warm cache with pre-computed responses"""
        # This would be implemented to pre-populate cache with common requests
        pass
    
    def get_stats(self) -> CacheStats:
        """Get current cache statistics"""
        with self.lock:
            return CacheStats(
                total_requests=self.stats.total_requests,
                cache_hits=self.stats.cache_hits,
                cache_misses=self.stats.cache_misses,
                cache_invalidations=self.stats.cache_invalidations,
                total_cost_saved=self.stats.total_cost_saved,
                total_time_saved=self.stats.total_time_saved,
                hit_rate=self.stats.hit_rate,
                avg_response_time=self.stats.avg_response_time,
                cache_size_bytes=self.stats.cache_size_bytes,
                cache_entries=self.stats.cache_entries
            )
    
    def clear_all(self):
        """Clear all cache entries"""
        with self.lock:
            invalidated_count = len(self.memory_cache)
            self.memory_cache.clear()
            self.stats.cache_invalidations += invalidated_count
        
        if self.distributed_cache:
            try:
                # Clear distributed cache (this is a simplified approach)
                for key in self.distributed_cache.scan_iter(match="aicache:*"):
                    self.distributed_cache.delete(key)
            except Exception as e:
                self.logger.warning(f"Distributed cache clear error: {e}")
        
        self.logger.info(f"Cleared all cache entries ({invalidated_count} entries)")
    
    async def shutdown(self):
        """Shutdown cache gracefully"""
        self.logger.info("Shutting down Smart Cache")
        
        if self.distributed_cache:
            try:
                self.distributed_cache.close()
            except Exception as e:
                self.logger.warning(f"Error closing distributed cache: {e}")
        
        with self.lock:
            self.memory_cache.clear()
        
        self.logger.info("Smart Cache shutdown complete")