"""
Memory Management System
Phase 5B: Resource Management

Advanced memory monitoring, leak detection, and intelligent memory management
for optimal Home Assistant integration.
"""

import asyncio
import gc
import logging
import psutil
import sys
import time
import tracemalloc
import weakref
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    """Memory usage statistics"""
    rss_mb: float  # Resident Set Size in MB
    vms_mb: float  # Virtual Memory Size in MB
    percent: float  # Memory percentage
    available_mb: float  # Available system memory
    gc_collections: int  # Garbage collection count
    tracked_objects: int  # Number of tracked objects
    largest_objects: List[Dict[str, Any]]  # Largest memory consumers


@dataclass
class MemoryLeak:
    """Memory leak detection result"""
    object_type: str
    count_increase: int
    size_increase_mb: float
    first_seen: datetime
    last_seen: datetime
    severity: str  # low, medium, high, critical


class MemoryManager:
    """
    Advanced memory management system.
    
    Features:
    - Real-time memory monitoring
    - Memory leak detection
    - Automatic garbage collection optimization
    - Smart cache size management
    - Memory pressure handling
    - Integration with Home Assistant resource limits
    """
    
    def __init__(self,
                 memory_limit_mb: Optional[int] = None,
                 warning_threshold: float = 0.8,
                 critical_threshold: float = 0.95,
                 leak_detection_enabled: bool = True,
                 auto_gc_enabled: bool = True,
                 monitoring_interval: float = 30.0):
        """
        Initialize memory manager.
        
        Args:
            memory_limit_mb: Memory limit in MB (None for auto-detection)
            warning_threshold: Warning threshold as fraction of limit
            critical_threshold: Critical threshold as fraction of limit
            leak_detection_enabled: Enable memory leak detection
            auto_gc_enabled: Enable automatic garbage collection
            monitoring_interval: Monitoring interval in seconds
        """
        self.memory_limit_mb = memory_limit_mb
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.leak_detection_enabled = leak_detection_enabled
        self.auto_gc_enabled = auto_gc_enabled
        self.monitoring_interval = monitoring_interval
        
        # Memory monitoring
        self._process = psutil.Process()
        self._monitoring_enabled = False
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Memory statistics
        self._stats_history: List[MemoryStats] = []
        self._max_history_size = 1000
        
        # Leak detection
        self._leak_detection_snapshots: List[Dict[str, Any]] = []
        self._detected_leaks: List[MemoryLeak] = []
        self._object_tracking: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Callbacks for memory events
        self._warning_callbacks: List[Callable] = []
        self._critical_callbacks: List[Callable] = []
        self._leak_callbacks: List[Callable] = []
        
        # Garbage collection optimization
        self._gc_stats = {
            "auto_collections": 0,
            "manual_collections": 0,
            "objects_collected": 0,
            "time_saved": 0.0
        }
        
        # Cache management
        self._managed_caches: Dict[str, Any] = {}
        
        # Auto-detection of memory limit
        if self.memory_limit_mb is None:
            self.memory_limit_mb = self._detect_memory_limit()
        
        logger.info(f"Memory manager initialized (limit: {self.memory_limit_mb}MB)")
    
    async def start_monitoring(self) -> None:
        """Start memory monitoring."""
        if self._monitoring_enabled:
            logger.warning("Memory monitoring already enabled")
            return
        
        try:
            # Start tracemalloc for detailed tracking
            if self.leak_detection_enabled and not tracemalloc.is_tracing():
                tracemalloc.start()
            
            # Start monitoring task
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self._monitoring_enabled = True
            
            logger.info("Memory monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start memory monitoring: {e}")
            raise
    
    async def stop_monitoring(self) -> None:
        """Stop memory monitoring."""
        if not self._monitoring_enabled:
            return
        
        try:
            # Stop monitoring task
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
                self._monitoring_task = None
            
            # Stop tracemalloc
            if tracemalloc.is_tracing():
                tracemalloc.stop()
            
            self._monitoring_enabled = False
            logger.info("Memory monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping memory monitoring: {e}")
    
    def get_current_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        try:
            # Get process memory info
            memory_info = self._process.memory_info()
            memory_percent = self._process.memory_percent()
            
            # Get system memory info
            system_memory = psutil.virtual_memory()
            
            # Get garbage collection info
            gc_stats = gc.get_stats()
            total_collections = sum(stat['collections'] for stat in gc_stats)
            
            # Get tracked objects count
            tracked_objects = 0
            largest_objects = []
            
            if tracemalloc.is_tracing():
                snapshot = tracemalloc.take_snapshot()
                top_stats = snapshot.statistics('lineno')[:10]
                
                tracked_objects = len(snapshot.traces)
                largest_objects = [
                    {
                        "filename": stat.traceback.format()[-1] if stat.traceback else "unknown",
                        "size_mb": stat.size / 1024 / 1024,
                        "count": stat.count
                    }
                    for stat in top_stats
                ]
            
            return MemoryStats(
                rss_mb=memory_info.rss / 1024 / 1024,
                vms_mb=memory_info.vms / 1024 / 1024,
                percent=memory_percent,
                available_mb=system_memory.available / 1024 / 1024,
                gc_collections=total_collections,
                tracked_objects=tracked_objects,
                largest_objects=largest_objects
            )
            
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return MemoryStats(0, 0, 0, 0, 0, 0, [])
    
    def check_memory_pressure(self) -> Dict[str, Any]:
        """Check current memory pressure level."""
        stats = self.get_current_stats()
        
        # Calculate pressure based on limit
        if self.memory_limit_mb:
            usage_ratio = stats.rss_mb / self.memory_limit_mb
        else:
            usage_ratio = stats.percent / 100.0
        
        # Determine pressure level
        if usage_ratio >= self.critical_threshold:
            pressure_level = "critical"
        elif usage_ratio >= self.warning_threshold:
            pressure_level = "warning"
        else:
            pressure_level = "normal"
        
        return {
            "pressure_level": pressure_level,
            "usage_ratio": usage_ratio,
            "current_mb": stats.rss_mb,
            "limit_mb": self.memory_limit_mb,
            "available_mb": stats.available_mb,
            "action_needed": pressure_level in ["warning", "critical"]
        }
    
    async def handle_memory_pressure(self) -> bool:
        """Handle memory pressure by freeing resources."""
        logger.info("Handling memory pressure...")
        
        actions_taken = []
        
        try:
            # 1. Force garbage collection
            if self.auto_gc_enabled:
                collected = await self._force_garbage_collection()
                if collected > 0:
                    actions_taken.append(f"Collected {collected} objects via GC")
            
            # 2. Resize managed caches
            for cache_name, cache in self._managed_caches.items():
                if hasattr(cache, 'reduce_size'):
                    original_size = getattr(cache, 'size', 0)
                    cache.reduce_size(0.5)  # Reduce to 50%
                    new_size = getattr(cache, 'size', 0)
                    actions_taken.append(f"Reduced {cache_name} cache: {original_size} -> {new_size}")
            
            # 3. Clear performance history
            if len(self._stats_history) > 100:
                removed = len(self._stats_history) - 100
                self._stats_history = self._stats_history[-100:]
                actions_taken.append(f"Cleared {removed} old memory stats")
            
            # 4. Clear leak detection snapshots
            if len(self._leak_detection_snapshots) > 10:
                removed = len(self._leak_detection_snapshots) - 10
                self._leak_detection_snapshots = self._leak_detection_snapshots[-10:]
                actions_taken.append(f"Cleared {removed} leak detection snapshots")
            
            logger.info(f"Memory pressure actions: {', '.join(actions_taken)}")
            return len(actions_taken) > 0
            
        except Exception as e:
            logger.error(f"Error handling memory pressure: {e}")
            return False
    
    async def detect_memory_leaks(self) -> List[MemoryLeak]:
        """Detect potential memory leaks."""
        if not self.leak_detection_enabled or not tracemalloc.is_tracing():
            return []
        
        try:
            # Take snapshot
            current_snapshot = tracemalloc.take_snapshot()
            current_time = datetime.now()
            
            # Store snapshot data
            snapshot_data = {
                "timestamp": current_time,
                "snapshot": current_snapshot,
                "stats": current_snapshot.statistics('traceback')
            }
            
            self._leak_detection_snapshots.append(snapshot_data)
            
            # Keep only recent snapshots
            if len(self._leak_detection_snapshots) > 20:
                self._leak_detection_snapshots = self._leak_detection_snapshots[-20:]
            
            # Need at least 2 snapshots to detect leaks
            if len(self._leak_detection_snapshots) < 2:
                return []
            
            # Compare with previous snapshot
            previous_snapshot = self._leak_detection_snapshots[-2]
            
            # Compare statistics
            previous_stats = {stat.traceback: stat for stat in previous_snapshot["stats"]}
            current_stats = {stat.traceback: stat for stat in snapshot_data["stats"]}
            
            detected_leaks = []
            
            for traceback, current_stat in current_stats.items():
                if traceback in previous_stats:
                    previous_stat = previous_stats[traceback]
                    
                    # Check for significant increase
                    count_increase = current_stat.count - previous_stat.count
                    size_increase = (current_stat.size - previous_stat.size) / 1024 / 1024  # MB
                    
                    # Determine if this looks like a leak
                    if count_increase > 100 or size_increase > 10:  # Thresholds
                        # Determine severity
                        if size_increase > 100 or count_increase > 1000:
                            severity = "critical"
                        elif size_increase > 50 or count_increase > 500:
                            severity = "high"
                        elif size_increase > 10 or count_increase > 200:
                            severity = "medium"
                        else:
                            severity = "low"
                        
                        # Create leak object
                        leak = MemoryLeak(
                            object_type=str(traceback.format()[-1]) if traceback else "unknown",
                            count_increase=count_increase,
                            size_increase_mb=size_increase,
                            first_seen=previous_snapshot["timestamp"],
                            last_seen=current_time,
                            severity=severity
                        )
                        
                        detected_leaks.append(leak)
            
            # Update detected leaks list
            self._detected_leaks.extend(detected_leaks)
            
            # Keep only recent leaks
            if len(self._detected_leaks) > 100:
                self._detected_leaks = self._detected_leaks[-100:]
            
            # Trigger leak callbacks
            for leak in detected_leaks:
                for callback in self._leak_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(leak)
                        else:
                            callback(leak)
                    except Exception as e:
                        logger.error(f"Error in leak callback: {e}")
            
            if detected_leaks:
                logger.warning(f"Detected {len(detected_leaks)} potential memory leaks")
            
            return detected_leaks
            
        except Exception as e:
            logger.error(f"Error detecting memory leaks: {e}")
            return []
    
    def register_cache(self, name: str, cache_object: Any) -> None:
        """Register a cache for memory management."""
        self._managed_caches[name] = cache_object
        logger.debug(f"Registered cache for memory management: {name}")
    
    def register_warning_callback(self, callback: Callable) -> None:
        """Register callback for memory warnings."""
        self._warning_callbacks.append(callback)
    
    def register_critical_callback(self, callback: Callable) -> None:
        """Register callback for critical memory situations."""
        self._critical_callbacks.append(callback)
    
    def register_leak_callback(self, callback: Callable) -> None:
        """Register callback for memory leak detection."""
        self._leak_callbacks.append(callback)
    
    async def _force_garbage_collection(self) -> int:
        """Force garbage collection and return number of objects collected."""
        try:
            # Get object count before
            before_counts = [len(gc.get_objects(generation)) for generation in range(3)]
            
            # Force collection for all generations
            collected = 0
            for generation in range(3):
                collected += gc.collect(generation)
            
            # Get object count after
            after_counts = [len(gc.get_objects(generation)) for generation in range(3)]
            
            # Calculate total objects collected
            total_collected = sum(before - after for before, after in zip(before_counts, after_counts))
            
            self._gc_stats["manual_collections"] += 1
            self._gc_stats["objects_collected"] += total_collected
            
            logger.debug(f"Garbage collection freed {total_collected} objects")
            return total_collected
            
        except Exception as e:
            logger.error(f"Error in garbage collection: {e}")
            return 0
    
    def _detect_memory_limit(self) -> int:
        """Auto-detect appropriate memory limit."""
        try:
            # Get total system memory
            system_memory = psutil.virtual_memory()
            total_mb = system_memory.total / 1024 / 1024
            
            # For Home Assistant addon, use conservative limit
            # Typically 25% of system memory or 512MB, whichever is smaller
            limit_mb = min(total_mb * 0.25, 512)
            
            logger.info(f"Auto-detected memory limit: {limit_mb:.0f}MB (system: {total_mb:.0f}MB)")
            return int(limit_mb)
            
        except Exception as e:
            logger.error(f"Error detecting memory limit: {e}")
            return 256  # Conservative fallback
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring_enabled:
            try:
                # Get current stats
                stats = self.get_current_stats()
                
                # Store in history
                self._stats_history.append(stats)
                if len(self._stats_history) > self._max_history_size:
                    self._stats_history = self._stats_history[-self._max_history_size:]
                
                # Check memory pressure
                pressure = self.check_memory_pressure()
                
                # Handle pressure levels
                if pressure["pressure_level"] == "critical":
                    logger.warning(f"Critical memory pressure: {stats.rss_mb:.1f}MB ({pressure['usage_ratio']:.1%})")
                    
                    # Trigger critical callbacks
                    for callback in self._critical_callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(stats)
                            else:
                                callback(stats)
                        except Exception as e:
                            logger.error(f"Error in critical callback: {e}")
                    
                    # Auto-handle pressure
                    await self.handle_memory_pressure()
                    
                elif pressure["pressure_level"] == "warning":
                    logger.info(f"Memory pressure warning: {stats.rss_mb:.1f}MB ({pressure['usage_ratio']:.1%})")
                    
                    # Trigger warning callbacks
                    for callback in self._warning_callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(stats)
                            else:
                                callback(stats)
                        except Exception as e:
                            logger.error(f"Error in warning callback: {e}")
                
                # Detect memory leaks periodically
                if self.leak_detection_enabled and len(self._stats_history) % 10 == 0:
                    await self.detect_memory_leaks()
                
                # Auto garbage collection if enabled
                if self.auto_gc_enabled and stats.rss_mb > self.memory_limit_mb * 0.7:
                    collected = await self._force_garbage_collection()
                    if collected > 0:
                        self._gc_stats["auto_collections"] += 1
                
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in memory monitoring loop: {e}")
                await asyncio.sleep(5)
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory report."""
        stats = self.get_current_stats()
        pressure = self.check_memory_pressure()
        
        # Calculate trends
        trend_data = {}
        if len(self._stats_history) > 1:
            recent_stats = self._stats_history[-10:]  # Last 10 measurements
            avg_rss = sum(s.rss_mb for s in recent_stats) / len(recent_stats)
            
            if len(self._stats_history) > 10:
                older_stats = self._stats_history[-20:-10]  # Previous 10 measurements
                old_avg_rss = sum(s.rss_mb for s in older_stats) / len(older_stats)
                trend_data["rss_trend"] = (avg_rss - old_avg_rss) / old_avg_rss if old_avg_rss > 0 else 0
            else:
                trend_data["rss_trend"] = 0
        
        return {
            "current_stats": stats.__dict__,
            "pressure": pressure,
            "memory_limit_mb": self.memory_limit_mb,
            "trends": trend_data,
            "leak_detection": {
                "enabled": self.leak_detection_enabled,
                "detected_leaks": len(self._detected_leaks),
                "recent_leaks": [leak.__dict__ for leak in self._detected_leaks[-5:]]
            },
            "garbage_collection": self._gc_stats,
            "managed_caches": len(self._managed_caches),
            "monitoring_enabled": self._monitoring_enabled
        }


# Global memory manager instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager(
    memory_limit_mb: Optional[int] = None,
    warning_threshold: float = 0.8,
    critical_threshold: float = 0.95
) -> MemoryManager:
    """
    Get global memory manager instance.
    
    Args:
        memory_limit_mb: Memory limit in MB
        warning_threshold: Warning threshold as fraction of limit
        critical_threshold: Critical threshold as fraction of limit
        
    Returns:
        MemoryManager instance
    """
    global _memory_manager
    
    if _memory_manager is None:
        _memory_manager = MemoryManager(
            memory_limit_mb=memory_limit_mb,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold
        )
    
    return _memory_manager


async def start_memory_monitoring() -> None:
    """Start global memory monitoring."""
    manager = get_memory_manager()
    await manager.start_monitoring()


async def stop_memory_monitoring() -> None:
    """Stop global memory monitoring."""
    global _memory_manager
    if _memory_manager:
        await _memory_manager.stop_monitoring()


def get_current_memory_stats() -> MemoryStats:
    """Get current memory statistics."""
    manager = get_memory_manager()
    return manager.get_current_stats()


async def handle_memory_pressure() -> bool:
    """Handle current memory pressure."""
    manager = get_memory_manager()
    return await manager.handle_memory_pressure()


def register_memory_cache(name: str, cache_object: Any) -> None:
    """Register a cache for memory management."""
    manager = get_memory_manager()
    manager.register_cache(name, cache_object)