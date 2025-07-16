"""
Integration Optimizer for AICleaner Phase 3B
Provides cross-component optimization, advanced caching, scalability improvements,
and user experience enhancements
"""
import asyncio
import json
import logging
import time
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, OrderedDict
import threading
import weakref


class CacheStrategy(Enum):
    """Caching strategies"""
    LRU = "lru"
    TTL = "ttl"
    ADAPTIVE = "adaptive"
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"


class OptimizationLevel(Enum):
    """Optimization levels"""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


@dataclass
class CacheConfig:
    """Cache configuration"""
    strategy: CacheStrategy = CacheStrategy.LRU
    max_size: int = 1000
    ttl_seconds: int = 3600
    cleanup_interval: int = 300
    hit_rate_threshold: float = 0.8
    adaptive_resize: bool = True


@dataclass
class OptimizationMetrics:
    """Optimization performance metrics"""
    cache_hit_rate: float = 0.0
    average_response_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_utilization: float = 0.0
    throughput_ops_per_sec: float = 0.0
    error_rate: float = 0.0
    user_satisfaction_score: float = 0.0


class AdvancedCache:
    """Advanced caching system with multiple strategies"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache = OrderedDict()
        self.access_times = {}
        self.hit_count = 0
        self.miss_count = 0
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key in self.cache:
                # Check TTL if applicable
                if self.config.strategy in [CacheStrategy.TTL, CacheStrategy.ADAPTIVE]:
                    if time.time() - self.access_times.get(key, 0) > self.config.ttl_seconds:
                        del self.cache[key]
                        del self.access_times[key]
                        self.miss_count += 1
                        return None
                
                # Update access for LRU
                if self.config.strategy in [CacheStrategy.LRU, CacheStrategy.ADAPTIVE]:
                    self.cache.move_to_end(key)
                
                self.access_times[key] = time.time()
                self.hit_count += 1
                return self.cache[key]
            else:
                self.miss_count += 1
                return None
    
    def put(self, key: str, value: Any) -> None:
        """Put value in cache"""
        with self.lock:
            # Remove oldest items if at capacity
            while len(self.cache) >= self.config.max_size:
                if self.config.strategy == CacheStrategy.LRU:
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
                    del self.access_times[oldest_key]
                else:
                    # For other strategies, remove least recently accessed
                    oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
                    del self.cache[oldest_key]
                    del self.access_times[oldest_key]
            
            self.cache[key] = value
            self.access_times[key] = time.time()
    
    def invalidate(self, key: str) -> bool:
        """Invalidate cache entry"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.access_times[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
    
    def get_hit_rate(self) -> float:
        """Get cache hit rate"""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            return {
                'size': len(self.cache),
                'max_size': self.config.max_size,
                'hit_count': self.hit_count,
                'miss_count': self.miss_count,
                'hit_rate': self.get_hit_rate(),
                'strategy': self.config.strategy.value
            }
    
    def _cleanup_loop(self):
        """Background cleanup loop"""
        while True:
            try:
                time.sleep(self.config.cleanup_interval)
                self._cleanup_expired()
                
                # Adaptive resizing
                if self.config.adaptive_resize:
                    self._adaptive_resize()
                    
            except Exception as e:
                self.logger.error(f"Cache cleanup error: {e}")
    
    def _cleanup_expired(self):
        """Clean up expired entries"""
        if self.config.strategy not in [CacheStrategy.TTL, CacheStrategy.ADAPTIVE]:
            return
            
        current_time = time.time()
        expired_keys = []
        
        with self.lock:
            for key, access_time in self.access_times.items():
                if current_time - access_time > self.config.ttl_seconds:
                    expired_keys.append(key)
            
            for key in expired_keys:
                if key in self.cache:
                    del self.cache[key]
                del self.access_times[key]
    
    def _adaptive_resize(self):
        """Adaptively resize cache based on hit rate"""
        hit_rate = self.get_hit_rate()
        
        if hit_rate < self.config.hit_rate_threshold and self.config.max_size < 10000:
            # Increase cache size if hit rate is low
            self.config.max_size = min(self.config.max_size * 1.2, 10000)
            self.logger.debug(f"Increased cache size to {self.config.max_size}")
        elif hit_rate > 0.95 and self.config.max_size > 100:
            # Decrease cache size if hit rate is very high (over-provisioned)
            self.config.max_size = max(self.config.max_size * 0.9, 100)
            self.logger.debug(f"Decreased cache size to {self.config.max_size}")


class ComponentOptimizer:
    """Cross-component optimization manager"""
    
    def __init__(self):
        self.caches = {}
        self.optimization_rules = {}
        self.performance_history = defaultdict(list)
        self.logger = logging.getLogger(__name__)
        self.metrics = OptimizationMetrics()
        
        # Component references for optimization
        self.components = weakref.WeakValueDictionary()
    
    def register_component(self, name: str, component: Any):
        """Register a component for optimization"""
        self.components[name] = component
        self.logger.info(f"Registered component for optimization: {name}")
    
    def create_cache(self, name: str, config: CacheConfig) -> AdvancedCache:
        """Create and register a cache"""
        cache = AdvancedCache(config)
        self.caches[name] = cache
        self.logger.info(f"Created cache: {name} with strategy {config.strategy.value}")
        return cache
    
    def get_cache(self, name: str) -> Optional[AdvancedCache]:
        """Get a registered cache"""
        return self.caches.get(name)
    
    def optimize_cross_component_calls(self, source: str, target: str, operation: str):
        """Decorator for optimizing cross-component calls"""
        def decorator(func: Callable):
            cache_key = f"{source}_{target}_{operation}"
            cache = self.get_cache(cache_key)
            
            if not cache:
                # Create cache for this operation
                config = CacheConfig(
                    strategy=CacheStrategy.ADAPTIVE,
                    max_size=500,
                    ttl_seconds=1800  # 30 minutes
                )
                cache = self.create_cache(cache_key, config)
            
            async def async_wrapper(*args, **kwargs):
                # Create cache key from arguments
                arg_key = self._create_arg_key(args, kwargs)
                full_key = f"{cache_key}_{arg_key}"
                
                # Try cache first
                cached_result = cache.get(full_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    cache.put(full_key, result)
                    
                    # Record performance
                    duration = time.time() - start_time
                    self.performance_history[cache_key].append({
                        'timestamp': time.time(),
                        'duration': duration,
                        'cache_hit': False
                    })
                    
                    return result
                except Exception as e:
                    self.logger.error(f"Error in {cache_key}: {e}")
                    raise
            
            def sync_wrapper(*args, **kwargs):
                # Similar logic for sync functions
                arg_key = self._create_arg_key(args, kwargs)
                full_key = f"{cache_key}_{arg_key}"
                
                cached_result = cache.get(full_key)
                if cached_result is not None:
                    return cached_result
                
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    cache.put(full_key, result)
                    
                    duration = time.time() - start_time
                    self.performance_history[cache_key].append({
                        'timestamp': time.time(),
                        'duration': duration,
                        'cache_hit': False
                    })
                    
                    return result
                except Exception as e:
                    self.logger.error(f"Error in {cache_key}: {e}")
                    raise
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def _create_arg_key(self, args: tuple, kwargs: dict) -> str:
        """Create a cache key from function arguments"""
        # Create a deterministic key from arguments
        key_data = {
            'args': [str(arg) for arg in args],
            'kwargs': {k: str(v) for k, v in kwargs.items()}
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()[:16]
    
    def batch_optimize(self, operations: List[Callable]) -> List[Any]:
        """Optimize batch operations"""
        # Group similar operations
        grouped_ops = defaultdict(list)
        for op in operations:
            op_type = type(op).__name__
            grouped_ops[op_type].append(op)
        
        results = []
        for op_type, ops in grouped_ops.items():
            # Execute similar operations together for better caching
            for op in ops:
                try:
                    result = op()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Batch operation failed: {e}")
                    results.append(None)
        
        return results
    
    def get_optimization_metrics(self) -> OptimizationMetrics:
        """Get current optimization metrics"""
        # Calculate cache hit rates
        total_hits = sum(cache.hit_count for cache in self.caches.values())
        total_requests = sum(cache.hit_count + cache.miss_count for cache in self.caches.values())
        cache_hit_rate = total_hits / total_requests if total_requests > 0 else 0.0
        
        # Calculate average response time
        all_durations = []
        for history in self.performance_history.values():
            all_durations.extend([entry['duration'] for entry in history[-100:]])  # Last 100 entries
        
        avg_response_time = sum(all_durations) / len(all_durations) if all_durations else 0.0
        
        self.metrics.cache_hit_rate = cache_hit_rate
        self.metrics.average_response_time = avg_response_time
        
        return self.metrics
    
    def generate_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report"""
        metrics = self.get_optimization_metrics()
        
        cache_stats = {}
        for name, cache in self.caches.items():
            cache_stats[name] = cache.get_stats()
        
        performance_summary = {}
        for operation, history in self.performance_history.items():
            recent_history = history[-100:]  # Last 100 operations
            if recent_history:
                durations = [entry['duration'] for entry in recent_history]
                performance_summary[operation] = {
                    'avg_duration': sum(durations) / len(durations),
                    'min_duration': min(durations),
                    'max_duration': max(durations),
                    'operation_count': len(recent_history)
                }
        
        return {
            'optimization_metrics': asdict(metrics),
            'cache_statistics': cache_stats,
            'performance_summary': performance_summary,
            'registered_components': list(self.components.keys()),
            'optimization_recommendations': self._generate_recommendations(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Cache recommendations
        for name, cache in self.caches.items():
            hit_rate = cache.get_hit_rate()
            if hit_rate < 0.5:
                recommendations.append(f"Consider increasing cache size or TTL for {name} (hit rate: {hit_rate:.2%})")
            elif hit_rate > 0.95:
                recommendations.append(f"Cache {name} may be over-provisioned (hit rate: {hit_rate:.2%})")
        
        # Performance recommendations
        for operation, history in self.performance_history.items():
            recent_history = history[-50:]
            if recent_history:
                avg_duration = sum(entry['duration'] for entry in recent_history) / len(recent_history)
                if avg_duration > 1.0:  # More than 1 second
                    recommendations.append(f"Operation {operation} is slow (avg: {avg_duration:.2f}s) - consider optimization")
        
        return recommendations
