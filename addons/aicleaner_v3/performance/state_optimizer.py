"""
State Management and Disk I/O Optimization
Phase 5A: Performance Optimization

Optimizes state persistence, configuration management, and disk I/O operations.
"""

import asyncio
import logging
import os
import time
import tempfile
import shutil
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta
import weakref
import hashlib

# Performance optimization imports
from .serialization_optimizer import fast_json_dumps, fast_json_loads
from .event_loop_optimizer import run_in_thread

logger = logging.getLogger(__name__)


@dataclass
class StateMetrics:
    """State management performance metrics"""
    total_reads: int = 0
    total_writes: int = 0
    total_read_time: float = 0.0
    total_write_time: float = 0.0
    average_read_time: float = 0.0
    average_write_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    total_bytes_read: int = 0
    total_bytes_written: int = 0
    fsync_calls: int = 0


class StateOptimizer:
    """
    Optimizes state management and disk I/O operations.
    
    Features:
    - In-memory state caching with intelligent invalidation
    - Batch write operations
    - Atomic file operations with fsync
    - Disk I/O monitoring and optimization
    - Automatic backup and recovery
    - Compression for large state files
    """
    
    def __init__(self,
                 cache_size: int = 1000,
                 batch_write_interval: float = 5.0,
                 enable_compression: bool = True,
                 backup_count: int = 3,
                 fsync_enabled: bool = True):
        """
        Initialize state optimizer.
        
        Args:
            cache_size: Maximum number of cached state entries
            batch_write_interval: Interval in seconds for batch writes
            enable_compression: Enable compression for large files
            backup_count: Number of backup files to keep
            fsync_enabled: Enable fsync for durability
        """
        self.cache_size = cache_size
        self.batch_write_interval = batch_write_interval
        self.enable_compression = enable_compression
        self.backup_count = backup_count
        self.fsync_enabled = fsync_enabled
        
        # Metrics
        self.metrics = StateMetrics()
        
        # In-memory cache
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_dirty: Dict[str, bool] = {}
        
        # Batch write queue
        self._write_queue: Dict[str, Any] = {}
        self._write_queue_lock = asyncio.Lock()
        self._batch_write_task: Optional[asyncio.Task] = None
        
        # File locks for atomic operations
        self._file_locks: Dict[str, asyncio.Lock] = {}
        
        # Change callbacks
        self._change_callbacks: Dict[str, List[Callable]] = {}
        
        logger.info("State optimizer initialized")
    
    async def start(self) -> None:
        """Start the state optimizer."""
        try:
            # Start batch write task
            self._batch_write_task = asyncio.create_task(self._batch_write_loop())
            logger.info("State optimizer started")
        except Exception as e:
            logger.error(f"Failed to start state optimizer: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the state optimizer and flush pending writes."""
        try:
            # Cancel batch write task
            if self._batch_write_task:
                self._batch_write_task.cancel()
                try:
                    await self._batch_write_task
                except asyncio.CancelledError:
                    pass
            
            # Flush any pending writes
            await self._flush_write_queue()
            
            logger.info("State optimizer stopped")
        except Exception as e:
            logger.error(f"Error stopping state optimizer: {e}")
    
    async def read_state(self, key: str, file_path: Optional[str] = None) -> Optional[Any]:
        """
        Read state with caching.
        
        Args:
            key: State key
            file_path: Optional file path for persistent state
            
        Returns:
            State value or None if not found
        """
        start_time = time.perf_counter()
        
        try:
            # Check cache first
            if key in self._cache:
                self.metrics.cache_hits += 1
                return self._cache[key]
            
            self.metrics.cache_misses += 1
            
            # Read from file if path provided
            if file_path:
                value = await self._read_from_file(file_path)
                if value is not None:
                    # Cache the value
                    await self._cache_value(key, value)
                return value
            
            return None
            
        finally:
            read_time = time.perf_counter() - start_time
            self.metrics.total_reads += 1
            self.metrics.total_read_time += read_time
            self.metrics.average_read_time = (
                self.metrics.total_read_time / self.metrics.total_reads
            )
    
    async def write_state(self, 
                         key: str, 
                         value: Any, 
                         file_path: Optional[str] = None,
                         immediate: bool = False) -> bool:
        """
        Write state with batching and caching.
        
        Args:
            key: State key
            value: State value
            file_path: Optional file path for persistent state
            immediate: Write immediately instead of batching
            
        Returns:
            True if write was successful
        """
        start_time = time.perf_counter()
        
        try:
            # Update cache
            await self._cache_value(key, value)
            self._cache_dirty[key] = True
            
            # Trigger change callbacks
            await self._trigger_change_callbacks(key, value)
            
            if file_path:
                if immediate:
                    # Write immediately
                    success = await self._write_to_file(file_path, value)
                    if success:
                        self._cache_dirty[key] = False
                    return success
                else:
                    # Add to batch write queue
                    async with self._write_queue_lock:
                        self._write_queue[key] = {
                            'value': value,
                            'file_path': file_path,
                            'timestamp': time.time()
                        }
            
            return True
            
        finally:
            write_time = time.perf_counter() - start_time
            self.metrics.total_writes += 1
            self.metrics.total_write_time += write_time
            self.metrics.average_write_time = (
                self.metrics.total_write_time / self.metrics.total_writes
            )
    
    async def delete_state(self, key: str, file_path: Optional[str] = None) -> bool:
        """
        Delete state from cache and optionally from file.
        
        Args:
            key: State key
            file_path: Optional file path to delete
            
        Returns:
            True if successful
        """
        try:
            # Remove from cache
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
            self._cache_dirty.pop(key, None)
            
            # Remove from write queue
            async with self._write_queue_lock:
                self._write_queue.pop(key, None)
            
            # Delete file if path provided
            if file_path:
                await self._delete_file(file_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting state {key}: {e}")
            return False
    
    async def flush_state(self, key: Optional[str] = None) -> bool:
        """
        Flush pending writes for a specific key or all keys.
        
        Args:
            key: Optional specific key to flush
            
        Returns:
            True if successful
        """
        try:
            if key:
                # Flush specific key
                async with self._write_queue_lock:
                    if key in self._write_queue:
                        entry = self._write_queue.pop(key)
                        return await self._write_to_file(
                            entry['file_path'], 
                            entry['value']
                        )
                return True
            else:
                # Flush all pending writes
                return await self._flush_write_queue()
        except Exception as e:
            logger.error(f"Error flushing state: {e}")
            return False
    
    def register_change_callback(self, key: str, callback: Callable) -> None:
        """
        Register a callback for state changes.
        
        Args:
            key: State key to monitor
            callback: Callback function
        """
        if key not in self._change_callbacks:
            self._change_callbacks[key] = []
        self._change_callbacks[key].append(callback)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        hit_rate = 0.0
        total_requests = self.metrics.cache_hits + self.metrics.cache_misses
        if total_requests > 0:
            hit_rate = self.metrics.cache_hits / total_requests
        
        return {
            "cache_size": len(self._cache),
            "max_cache_size": self.cache_size,
            "cache_hit_rate": hit_rate,
            "dirty_entries": sum(1 for dirty in self._cache_dirty.values() if dirty),
            "pending_writes": len(self._write_queue)
        }
    
    async def _cache_value(self, key: str, value: Any) -> None:
        """Cache a value with size management."""
        # Remove oldest entries if cache is full
        if len(self._cache) >= self.cache_size and key not in self._cache:
            oldest_key = min(self._cache_timestamps, key=self._cache_timestamps.get)
            self._cache.pop(oldest_key, None)
            self._cache_timestamps.pop(oldest_key, None)
            self._cache_dirty.pop(oldest_key, None)
        
        self._cache[key] = value
        self._cache_timestamps[key] = time.time()
        self._cache_dirty[key] = False
    
    async def _read_from_file(self, file_path: str) -> Optional[Any]:
        """Read state from file with optimization."""
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            
            # Get file lock
            lock = self._get_file_lock(file_path)
            async with lock:
                # Read file in thread pool to avoid blocking
                @run_in_thread
                def read_file():
                    try:
                        file_size = path.stat().st_size
                        with open(path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Update metrics
                        self.metrics.total_bytes_read += file_size
                        
                        # Decompress if needed
                        if self.enable_compression and file_size > 1024:
                            try:
                                import gzip
                                with gzip.open(path, 'rt', encoding='utf-8') as f:
                                    content = f.read()
                            except Exception:
                                # Fall back to regular read if decompression fails
                                pass
                        
                        return fast_json_loads(content)
                    except Exception as e:
                        logger.error(f"Error reading file {file_path}: {e}")
                        return None
                
                return await read_file()
                
        except Exception as e:
            logger.error(f"Error reading state from {file_path}: {e}")
            return None
    
    async def _write_to_file(self, file_path: str, value: Any) -> bool:
        """Write state to file with atomic operations."""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Get file lock
            lock = self._get_file_lock(file_path)
            async with lock:
                # Write file in thread pool to avoid blocking
                @run_in_thread
                def write_file():
                    try:
                        # Serialize data
                        content = fast_json_dumps(value)
                        
                        # Create backup if file exists
                        if path.exists() and self.backup_count > 0:
                            self._create_backup(path)
                        
                        # Write to temporary file first (atomic operation)
                        with tempfile.NamedTemporaryFile(
                            mode='w', 
                            encoding='utf-8',
                            dir=path.parent,
                            delete=False
                        ) as temp_file:
                            
                            # Apply compression if enabled and content is large
                            if self.enable_compression and len(content) > 1024:
                                import gzip
                                temp_path = temp_file.name + '.gz'
                                temp_file.close()
                                with gzip.open(temp_path, 'wt', encoding='utf-8') as gz_file:
                                    gz_file.write(content)
                                os.rename(temp_path, path)
                            else:
                                temp_file.write(content)
                                temp_file.flush()
                                
                                # Force write to disk
                                if self.fsync_enabled:
                                    os.fsync(temp_file.fileno())
                                    self.metrics.fsync_calls += 1
                                
                                temp_file.close()
                                
                                # Atomic move
                                os.rename(temp_file.name, path)
                        
                        # Update metrics
                        file_size = path.stat().st_size
                        self.metrics.total_bytes_written += file_size
                        
                        return True
                        
                    except Exception as e:
                        logger.error(f"Error writing file {file_path}: {e}")
                        return False
                
                return await write_file()
                
        except Exception as e:
            logger.error(f"Error writing state to {file_path}: {e}")
            return False
    
    async def _delete_file(self, file_path: str) -> bool:
        """Delete file with proper cleanup."""
        try:
            path = Path(file_path)
            if path.exists():
                # Get file lock
                lock = self._get_file_lock(file_path)
                async with lock:
                    @run_in_thread
                    def delete_file():
                        path.unlink()
                        return True
                    
                    return await delete_file()
            return True
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False
    
    def _create_backup(self, file_path: Path) -> None:
        """Create backup of existing file."""
        try:
            backup_dir = file_path.parent / ".backups"
            backup_dir.mkdir(exist_ok=True)
            
            # Create timestamped backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"{file_path.name}.{timestamp}"
            
            shutil.copy2(file_path, backup_path)
            
            # Clean up old backups
            self._cleanup_old_backups(backup_dir, file_path.name)
            
        except Exception as e:
            logger.warning(f"Failed to create backup for {file_path}: {e}")
    
    def _cleanup_old_backups(self, backup_dir: Path, filename: str) -> None:
        """Clean up old backup files."""
        try:
            # Find all backups for this file
            pattern = f"{filename}.*"
            backups = list(backup_dir.glob(pattern))
            
            # Sort by modification time (newest first)
            backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            # Remove old backups
            for backup in backups[self.backup_count:]:
                backup.unlink()
                
        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")
    
    def _get_file_lock(self, file_path: str) -> asyncio.Lock:
        """Get or create file lock."""
        if file_path not in self._file_locks:
            self._file_locks[file_path] = asyncio.Lock()
        return self._file_locks[file_path]
    
    async def _trigger_change_callbacks(self, key: str, value: Any) -> None:
        """Trigger registered change callbacks."""
        if key in self._change_callbacks:
            for callback in self._change_callbacks[key]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(key, value)
                    else:
                        callback(key, value)
                except Exception as e:
                    logger.error(f"Error in change callback for {key}: {e}")
    
    async def _batch_write_loop(self) -> None:
        """Background task for batch writing."""
        while True:
            try:
                await asyncio.sleep(self.batch_write_interval)
                await self._flush_write_queue()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch write loop: {e}")
                await asyncio.sleep(1)
    
    async def _flush_write_queue(self) -> bool:
        """Flush all pending writes."""
        try:
            async with self._write_queue_lock:
                if not self._write_queue:
                    return True
                
                # Get all pending writes
                pending_writes = dict(self._write_queue)
                self._write_queue.clear()
            
            # Write all files
            success = True
            for key, entry in pending_writes.items():
                file_success = await self._write_to_file(
                    entry['file_path'], 
                    entry['value']
                )
                if file_success:
                    self._cache_dirty[key] = False
                else:
                    success = False
                    # Re-queue failed write
                    async with self._write_queue_lock:
                        self._write_queue[key] = entry
            
            return success
            
        except Exception as e:
            logger.error(f"Error flushing write queue: {e}")
            return False


# Global state optimizer instance
_state_optimizer: Optional[StateOptimizer] = None


def get_state_optimizer(
    cache_size: int = 1000,
    batch_write_interval: float = 5.0,
    enable_compression: bool = True,
    backup_count: int = 3,
    fsync_enabled: bool = True
) -> StateOptimizer:
    """
    Get global state optimizer instance.
    
    Args:
        cache_size: Maximum number of cached state entries
        batch_write_interval: Interval in seconds for batch writes
        enable_compression: Enable compression for large files
        backup_count: Number of backup files to keep
        fsync_enabled: Enable fsync for durability
        
    Returns:
        StateOptimizer instance
    """
    global _state_optimizer
    
    if _state_optimizer is None:
        _state_optimizer = StateOptimizer(
            cache_size=cache_size,
            batch_write_interval=batch_write_interval,
            enable_compression=enable_compression,
            backup_count=backup_count,
            fsync_enabled=fsync_enabled
        )
    
    return _state_optimizer


async def start_state_optimization() -> None:
    """Start global state optimization."""
    optimizer = get_state_optimizer()
    await optimizer.start()


async def stop_state_optimization() -> None:
    """Stop global state optimization."""
    global _state_optimizer
    if _state_optimizer:
        await _state_optimizer.stop()


# Convenience functions
async def read_optimized_state(key: str, file_path: Optional[str] = None) -> Optional[Any]:
    """Read state using global optimizer."""
    optimizer = get_state_optimizer()
    return await optimizer.read_state(key, file_path)


async def write_optimized_state(key: str, value: Any, file_path: Optional[str] = None, immediate: bool = False) -> bool:
    """Write state using global optimizer."""
    optimizer = get_state_optimizer()
    return await optimizer.write_state(key, value, file_path, immediate)


async def flush_optimized_state(key: Optional[str] = None) -> bool:
    """Flush pending writes using global optimizer."""
    optimizer = get_state_optimizer()
    return await optimizer.flush_state(key)