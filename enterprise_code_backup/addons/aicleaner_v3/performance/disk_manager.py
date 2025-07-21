"""
Disk Space Management System
Phase 5B: Resource Management

Advanced disk space monitoring, cleanup automation, and intelligent storage management
for optimal Home Assistant integration.
"""

import asyncio
import logging
import os
import shutil
import time
import psutil
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


@dataclass
class DiskStats:
    """Disk usage statistics"""
    total_gb: float  # Total disk space in GB
    used_gb: float   # Used disk space in GB
    free_gb: float   # Free disk space in GB
    used_percent: float  # Used percentage
    free_percent: float  # Free percentage
    mount_point: str     # Mount point path
    filesystem: str      # Filesystem type
    inode_usage: Optional[float] = None  # Inode usage percentage


@dataclass
class DirectoryInfo:
    """Directory size and cleanup information"""
    path: str
    size_mb: float
    file_count: int
    last_modified: datetime
    is_cache: bool = False
    is_temp: bool = False
    is_log: bool = False
    cleanup_priority: int = 5  # 1=highest, 10=lowest


class DiskManager:
    """
    Advanced disk space management system.
    
    Features:
    - Real-time disk space monitoring
    - Automatic cleanup of cache and temporary files
    - Intelligent space allocation
    - Low disk space alerts and handling
    - Integration with Home Assistant storage management
    - Predictive space usage analysis
    """
    
    def __init__(self,
                 disk_limit_percent: float = 85.0,
                 warning_threshold: float = 75.0,
                 critical_threshold: float = 90.0,
                 auto_cleanup_enabled: bool = True,
                 monitoring_interval: float = 60.0,
                 cleanup_interval: float = 300.0):
        """
        Initialize disk manager.
        
        Args:
            disk_limit_percent: Maximum disk usage percentage
            warning_threshold: Warning threshold for disk usage
            critical_threshold: Critical threshold for disk usage
            auto_cleanup_enabled: Enable automatic cleanup
            monitoring_interval: Monitoring interval in seconds
            cleanup_interval: Cleanup interval in seconds
        """
        self.disk_limit_percent = disk_limit_percent
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.auto_cleanup_enabled = auto_cleanup_enabled
        self.monitoring_interval = monitoring_interval
        self.cleanup_interval = cleanup_interval
        
        # Disk monitoring
        self._monitoring_enabled = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Disk statistics
        self._stats_history: List[DiskStats] = []
        self._max_history_size = 100
        self._current_stats: Optional[DiskStats] = None
        
        # Cleanup configuration
        self._cleanup_directories: List[str] = []
        self._protected_directories: List[str] = []
        self._cleanup_patterns: List[str] = []
        self._last_cleanup: Optional[datetime] = None
        
        # Callbacks for disk events
        self._warning_callbacks: List[Callable] = []
        self._critical_callbacks: List[Callable] = []
        self._cleanup_callbacks: List[Callable] = []
        
        # Cleanup statistics
        self._cleanup_stats = {
            "total_cleanups": 0,
            "files_deleted": 0,
            "space_freed_mb": 0.0,
            "last_cleanup_duration": 0.0
        }
        
        # Root paths for monitoring
        self._monitor_paths = ["/", "/tmp", "/var", "/home"]
        self._addon_data_path = "/data"  # Home Assistant addon data path
        
        # Initialize cleanup directories
        self._initialize_cleanup_config()
        
        logger.info(f"Disk manager initialized (limit: {disk_limit_percent}%)")
    
    async def start_monitoring(self) -> None:
        """Start disk monitoring and cleanup tasks."""
        if self._monitoring_enabled:
            logger.warning("Disk monitoring already enabled")
            return
        
        try:
            # Start monitoring task
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            # Start cleanup task if auto cleanup is enabled
            if self.auto_cleanup_enabled:
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self._monitoring_enabled = True
            
            logger.info("Disk monitoring and cleanup started")
            
        except Exception as e:
            logger.error(f"Failed to start disk monitoring: {e}")
            raise
    
    async def stop_monitoring(self) -> None:
        """Stop disk monitoring and cleanup tasks."""
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
            
            # Stop cleanup task
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
                self._cleanup_task = None
            
            self._monitoring_enabled = False
            
            logger.info("Disk monitoring and cleanup stopped")
            
        except Exception as e:
            logger.error(f"Error stopping disk monitoring: {e}")
    
    def get_current_stats(self) -> DiskStats:
        """Get current disk statistics."""
        try:
            # Get primary disk usage (root filesystem)
            disk_usage = psutil.disk_usage('/')
            
            # Calculate percentages
            total_gb = disk_usage.total / (1024**3)
            used_gb = disk_usage.used / (1024**3)
            free_gb = disk_usage.free / (1024**3)
            used_percent = (disk_usage.used / disk_usage.total) * 100
            free_percent = (disk_usage.free / disk_usage.total) * 100
            
            # Get filesystem info
            mount_point = "/"
            filesystem = "unknown"
            inode_usage = None
            
            try:
                # Get disk partitions to find filesystem type
                partitions = psutil.disk_partitions()
                for partition in partitions:
                    if partition.mountpoint == '/':
                        filesystem = partition.fstype
                        break
            except Exception:
                pass
            
            # Try to get inode usage (Unix systems)
            try:
                statvfs = os.statvfs('/')
                if statvfs.f_files > 0:
                    inode_usage = ((statvfs.f_files - statvfs.f_ffree) / statvfs.f_files) * 100
            except (AttributeError, OSError):
                pass
            
            return DiskStats(
                total_gb=total_gb,
                used_gb=used_gb,
                free_gb=free_gb,
                used_percent=used_percent,
                free_percent=free_percent,
                mount_point=mount_point,
                filesystem=filesystem,
                inode_usage=inode_usage
            )
            
        except Exception as e:
            logger.error(f"Error getting disk stats: {e}")
            return DiskStats(0, 0, 0, 0, 100, "/", "unknown")
    
    def check_disk_pressure(self) -> Dict[str, Any]:
        """Check current disk pressure level."""
        stats = self.get_current_stats()
        
        # Determine pressure level
        if stats.used_percent >= self.critical_threshold:
            pressure_level = "critical"
        elif stats.used_percent >= self.warning_threshold:
            pressure_level = "warning"
        else:
            pressure_level = "normal"
        
        # Check inode pressure if available
        inode_pressure = "normal"
        if stats.inode_usage is not None:
            if stats.inode_usage >= 90:
                inode_pressure = "critical"
            elif stats.inode_usage >= 80:
                inode_pressure = "warning"
        
        return {
            "pressure_level": pressure_level,
            "used_percent": stats.used_percent,
            "free_gb": stats.free_gb,
            "total_gb": stats.total_gb,
            "inode_pressure": inode_pressure,
            "inode_usage": stats.inode_usage,
            "action_needed": pressure_level in ["warning", "critical"],
            "cleanup_recommended": stats.used_percent > self.disk_limit_percent
        }
    
    async def handle_disk_pressure(self) -> bool:
        """Handle disk pressure by cleanup and optimization."""
        logger.info("Handling disk pressure...")
        
        actions_taken = []
        
        try:
            # 1. Immediate cache cleanup
            cache_freed = await self._cleanup_cache_directories()
            if cache_freed > 0:
                actions_taken.append(f"Freed {cache_freed:.1f}MB from cache")
            
            # 2. Temporary file cleanup
            temp_freed = await self._cleanup_temp_directories()
            if temp_freed > 0:
                actions_taken.append(f"Freed {temp_freed:.1f}MB from temp files")
            
            # 3. Log file cleanup
            log_freed = await self._cleanup_log_files()
            if log_freed > 0:
                actions_taken.append(f"Freed {log_freed:.1f}MB from logs")
            
            # 4. Application-specific cleanup
            app_freed = await self._cleanup_application_data()
            if app_freed > 0:
                actions_taken.append(f"Freed {app_freed:.1f}MB from app data")
            
            # 5. Emergency cleanup if still critical
            pressure = self.check_disk_pressure()
            if pressure["pressure_level"] == "critical":
                emergency_freed = await self._emergency_cleanup()
                if emergency_freed > 0:
                    actions_taken.append(f"Emergency cleanup freed {emergency_freed:.1f}MB")
            
            total_freed = cache_freed + temp_freed + log_freed + app_freed
            
            # 6. Update cleanup statistics
            self._cleanup_stats["total_cleanups"] += 1
            self._cleanup_stats["space_freed_mb"] += total_freed
            self._last_cleanup = datetime.now()
            
            logger.info(f"Disk pressure actions: {', '.join(actions_taken)}")
            return len(actions_taken) > 0
            
        except Exception as e:
            logger.error(f"Error handling disk pressure: {e}")
            return False
    
    async def analyze_directory_sizes(self, path: str = "/") -> List[DirectoryInfo]:
        """Analyze directory sizes for cleanup opportunities."""
        directories = []
        
        try:
            # Scan directories for size analysis
            for root, dirs, files in os.walk(path):
                # Skip protected directories
                if any(protected in root for protected in self._protected_directories):
                    continue
                
                # Calculate directory size
                size_bytes = 0
                file_count = len(files)
                last_modified = datetime.fromtimestamp(0)
                
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        stat = os.stat(file_path)
                        size_bytes += stat.st_size
                        file_modified = datetime.fromtimestamp(stat.st_mtime)
                        if file_modified > last_modified:
                            last_modified = file_modified
                    except (OSError, PermissionError):
                        continue
                
                size_mb = size_bytes / (1024 * 1024)
                
                # Classify directory type
                is_cache = any(cache_dir in root.lower() for cache_dir in ["cache", "__pycache__", ".cache"])
                is_temp = any(temp_dir in root.lower() for temp_dir in ["tmp", "temp", "temporary"])
                is_log = any(log_dir in root.lower() for log_dir in ["log", "logs"])
                
                # Determine cleanup priority
                cleanup_priority = self._calculate_cleanup_priority(root, size_mb, last_modified, is_cache, is_temp, is_log)
                
                if size_mb > 1.0:  # Only include directories larger than 1MB
                    directories.append(DirectoryInfo(
                        path=root,
                        size_mb=size_mb,
                        file_count=file_count,
                        last_modified=last_modified,
                        is_cache=is_cache,
                        is_temp=is_temp,
                        is_log=is_log,
                        cleanup_priority=cleanup_priority
                    ))
                
                # Limit depth to avoid excessive scanning
                if root.count(os.sep) - path.count(os.sep) >= 3:
                    dirs.clear()
        
        except Exception as e:
            logger.error(f"Error analyzing directory sizes: {e}")
        
        # Sort by cleanup priority and size
        directories.sort(key=lambda d: (d.cleanup_priority, -d.size_mb))
        return directories
    
    def _initialize_cleanup_config(self) -> None:
        """Initialize cleanup configuration."""
        # Common cleanup directories
        self._cleanup_directories = [
            "/tmp",
            "/var/tmp",
            "/var/cache",
            "/var/log",
            "/home/*/.cache",
            "/home/*/.local/share/Trash",
            f"{self._addon_data_path}/cache",
            f"{self._addon_data_path}/tmp",
            f"{self._addon_data_path}/logs"
        ]
        
        # Protected directories (never delete)
        self._protected_directories = [
            "/bin", "/sbin", "/usr", "/lib", "/lib64",
            "/boot", "/dev", "/proc", "/sys",
            "/etc", "/root/.ssh", "/home/*/.ssh",
            f"{self._addon_data_path}/config"
        ]
        
        # Cleanup file patterns
        self._cleanup_patterns = [
            "*.tmp", "*.temp", "*.cache",
            "*.log.gz", "*.log.[0-9]*",
            "core.*", "*.core",
            "__pycache__/*",
            ".DS_Store", "Thumbs.db"
        ]
    
    def _calculate_cleanup_priority(self, path: str, size_mb: float, last_modified: datetime, 
                                  is_cache: bool, is_temp: bool, is_log: bool) -> int:
        """Calculate cleanup priority for a directory (1=highest, 10=lowest)."""
        priority = 5  # Default priority
        
        # Adjust based on directory type
        if is_temp:
            priority = 1  # Highest priority for temp files
        elif is_cache:
            priority = 2  # High priority for cache files
        elif is_log:
            priority = 3  # Medium-high priority for logs
        
        # Adjust based on age
        age_days = (datetime.now() - last_modified).days
        if age_days > 30:
            priority = max(1, priority - 1)  # Increase priority for old files
        elif age_days < 1:
            priority = min(10, priority + 2)  # Decrease priority for recent files
        
        # Adjust based on size
        if size_mb > 100:
            priority = max(1, priority - 1)  # Increase priority for large directories
        elif size_mb < 10:
            priority = min(10, priority + 1)  # Decrease priority for small directories
        
        # Special cases
        if "addon" in path.lower() and "data" in path.lower():
            priority = min(10, priority + 2)  # Be careful with addon data
        
        return priority
    
    async def _cleanup_cache_directories(self) -> float:
        """Cleanup cache directories and return MB freed."""
        freed_mb = 0.0
        
        cache_paths = [
            "/tmp/__pycache__",
            "/var/cache",
            f"{self._addon_data_path}/cache",
            "/home/*/.cache"
        ]
        
        for cache_path in cache_paths:
            try:
                if os.path.exists(cache_path) and os.path.isdir(cache_path):
                    before_size = self._get_directory_size(cache_path)
                    await self._cleanup_directory(cache_path, max_age_days=7)
                    after_size = self._get_directory_size(cache_path)
                    freed_mb += (before_size - after_size) / (1024 * 1024)
            except Exception as e:
                logger.warning(f"Error cleaning cache {cache_path}: {e}")
        
        return freed_mb
    
    async def _cleanup_temp_directories(self) -> float:
        """Cleanup temporary directories and return MB freed."""
        freed_mb = 0.0
        
        temp_paths = ["/tmp", "/var/tmp", f"{self._addon_data_path}/tmp"]
        
        for temp_path in temp_paths:
            try:
                if os.path.exists(temp_path) and os.path.isdir(temp_path):
                    before_size = self._get_directory_size(temp_path)
                    await self._cleanup_directory(temp_path, max_age_days=1)
                    after_size = self._get_directory_size(temp_path)
                    freed_mb += (before_size - after_size) / (1024 * 1024)
            except Exception as e:
                logger.warning(f"Error cleaning temp {temp_path}: {e}")
        
        return freed_mb
    
    async def _cleanup_log_files(self) -> float:
        """Cleanup old log files and return MB freed."""
        freed_mb = 0.0
        
        log_paths = ["/var/log", f"{self._addon_data_path}/logs"]
        
        for log_path in log_paths:
            try:
                if os.path.exists(log_path) and os.path.isdir(log_path):
                    before_size = self._get_directory_size(log_path)
                    
                    # Clean old log files (keep last 30 days)
                    for root, _, files in os.walk(log_path):
                        for file in files:
                            if file.endswith(('.log.gz', '.log.1', '.log.2', '.log.3')):
                                file_path = os.path.join(root, file)
                                try:
                                    stat = os.stat(file_path)
                                    age_days = (time.time() - stat.st_mtime) / 86400
                                    if age_days > 30:
                                        os.remove(file_path)
                                        self._cleanup_stats["files_deleted"] += 1
                                except (OSError, PermissionError):
                                    continue
                    
                    after_size = self._get_directory_size(log_path)
                    freed_mb += (before_size - after_size) / (1024 * 1024)
            except Exception as e:
                logger.warning(f"Error cleaning logs {log_path}: {e}")
        
        return freed_mb
    
    async def _cleanup_application_data(self) -> float:
        """Cleanup application-specific data and return MB freed."""
        freed_mb = 0.0
        
        try:
            # AICleaner specific cleanup
            aicleaner_data = f"{self._addon_data_path}/aicleaner"
            if os.path.exists(aicleaner_data):
                before_size = self._get_directory_size(aicleaner_data)
                
                # Clean old performance data
                perf_data_path = os.path.join(aicleaner_data, "performance_data")
                if os.path.exists(perf_data_path):
                    await self._cleanup_directory(perf_data_path, max_age_days=7)
                
                # Clean old backup files
                backup_path = os.path.join(aicleaner_data, "backups")
                if os.path.exists(backup_path):
                    await self._cleanup_directory(backup_path, max_age_days=14)
                
                after_size = self._get_directory_size(aicleaner_data)
                freed_mb += (before_size - after_size) / (1024 * 1024)
        
        except Exception as e:
            logger.warning(f"Error cleaning application data: {e}")
        
        return freed_mb
    
    async def _emergency_cleanup(self) -> float:
        """Emergency cleanup when disk is critically full."""
        freed_mb = 0.0
        
        try:
            logger.warning("Performing emergency disk cleanup")
            
            # More aggressive cache cleanup
            for cache_dir in ["/var/cache", "/tmp"]:
                if os.path.exists(cache_dir):
                    before_size = self._get_directory_size(cache_dir)
                    await self._cleanup_directory(cache_dir, max_age_days=0)  # Clean everything
                    after_size = self._get_directory_size(cache_dir)
                    freed_mb += (before_size - after_size) / (1024 * 1024)
            
            # Clean Python bytecode
            for root, dirs, files in os.walk("/"):
                if "__pycache__" in dirs:
                    pycache_path = os.path.join(root, "__pycache__")
                    try:
                        before_size = self._get_directory_size(pycache_path)
                        shutil.rmtree(pycache_path)
                        freed_mb += before_size / (1024 * 1024)
                        self._cleanup_stats["files_deleted"] += 1
                    except (OSError, PermissionError):
                        continue
                
                # Limit emergency cleanup depth
                if root.count(os.sep) >= 5:
                    dirs.clear()
        
        except Exception as e:
            logger.error(f"Error in emergency cleanup: {e}")
        
        return freed_mb
    
    async def _cleanup_directory(self, directory: str, max_age_days: int = 7) -> None:
        """Cleanup files in directory older than max_age_days."""
        try:
            cutoff_time = time.time() - (max_age_days * 86400)
            
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        stat = os.stat(file_path)
                        if stat.st_mtime < cutoff_time:
                            os.remove(file_path)
                            self._cleanup_stats["files_deleted"] += 1
                    except (OSError, PermissionError):
                        continue
                
                # Remove empty directories
                for dir_name in dirs[:]:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(dir_path):
                            os.rmdir(dir_path)
                            dirs.remove(dir_name)
                    except (OSError, PermissionError):
                        continue
        
        except Exception as e:
            logger.warning(f"Error cleaning directory {directory}: {e}")
    
    def _get_directory_size(self, directory: str) -> int:
        """Get total size of directory in bytes."""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, PermissionError):
                        continue
        except Exception:
            pass
        return total_size
    
    def register_warning_callback(self, callback: Callable) -> None:
        """Register callback for disk warnings."""
        self._warning_callbacks.append(callback)
    
    def register_critical_callback(self, callback: Callable) -> None:
        """Register callback for critical disk situations."""
        self._critical_callbacks.append(callback)
    
    def register_cleanup_callback(self, callback: Callable) -> None:
        """Register callback for cleanup events."""
        self._cleanup_callbacks.append(callback)
    
    async def _monitoring_loop(self) -> None:
        """Main disk monitoring loop."""
        while self._monitoring_enabled:
            try:
                # Get current stats
                stats = self.get_current_stats()
                self._current_stats = stats
                
                # Store in history
                self._stats_history.append(stats)
                if len(self._stats_history) > self._max_history_size:
                    self._stats_history = self._stats_history[-self._max_history_size:]
                
                # Check disk pressure
                pressure = self.check_disk_pressure()
                
                # Handle pressure levels
                if pressure["pressure_level"] == "critical":
                    logger.warning(
                        f"Critical disk pressure: {stats.used_percent:.1f}% used "
                        f"({stats.free_gb:.1f}GB free)"
                    )
                    
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
                    if self.auto_cleanup_enabled:
                        await self.handle_disk_pressure()
                    
                elif pressure["pressure_level"] == "warning":
                    logger.info(
                        f"Disk pressure warning: {stats.used_percent:.1f}% used "
                        f"({stats.free_gb:.1f}GB free)"
                    )
                    
                    # Trigger warning callbacks
                    for callback in self._warning_callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(stats)
                            else:
                                callback(stats)
                        except Exception as e:
                            logger.error(f"Error in warning callback: {e}")
                
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in disk monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_loop(self) -> None:
        """Automatic cleanup loop."""
        while self._monitoring_enabled:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                # Check if cleanup is needed
                pressure = self.check_disk_pressure()
                
                if pressure["cleanup_recommended"]:
                    start_time = time.time()
                    await self.handle_disk_pressure()
                    cleanup_duration = time.time() - start_time
                    self._cleanup_stats["last_cleanup_duration"] = cleanup_duration
                    
                    # Trigger cleanup callbacks
                    for callback in self._cleanup_callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(pressure)
                            else:
                                callback(pressure)
                        except Exception as e:
                            logger.error(f"Error in cleanup callback: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)
    
    def get_disk_report(self) -> Dict[str, Any]:
        """Get comprehensive disk report."""
        stats = self.get_current_stats()
        pressure = self.check_disk_pressure()
        
        # Calculate trends
        trend_data = {}
        if len(self._stats_history) > 1:
            recent_stats = self._stats_history[-10:]  # Last 10 measurements
            avg_used = sum(s.used_percent for s in recent_stats) / len(recent_stats)
            
            if len(self._stats_history) > 10:
                older_stats = self._stats_history[-20:-10]  # Previous 10 measurements
                old_avg_used = sum(s.used_percent for s in older_stats) / len(older_stats)
                trend_data["usage_trend"] = (avg_used - old_avg_used) / old_avg_used if old_avg_used > 0 else 0
            else:
                trend_data["usage_trend"] = 0
        
        return {
            "current_stats": stats.__dict__,
            "pressure": pressure,
            "disk_limit_percent": self.disk_limit_percent,
            "trends": trend_data,
            "cleanup": {
                "auto_cleanup_enabled": self.auto_cleanup_enabled,
                "last_cleanup": self._last_cleanup.isoformat() if self._last_cleanup else None,
                "statistics": self._cleanup_stats,
                "protected_directories": len(self._protected_directories),
                "cleanup_directories": len(self._cleanup_directories)
            },
            "monitoring_enabled": self._monitoring_enabled
        }


# Global disk manager instance
_disk_manager: Optional[DiskManager] = None


def get_disk_manager(
    disk_limit_percent: float = 85.0,
    warning_threshold: float = 75.0,
    critical_threshold: float = 90.0
) -> DiskManager:
    """
    Get global disk manager instance.
    
    Args:
        disk_limit_percent: Maximum disk usage percentage
        warning_threshold: Warning threshold for disk usage
        critical_threshold: Critical threshold for disk usage
        
    Returns:
        DiskManager instance
    """
    global _disk_manager
    
    if _disk_manager is None:
        _disk_manager = DiskManager(
            disk_limit_percent=disk_limit_percent,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold
        )
    
    return _disk_manager


async def start_disk_monitoring() -> None:
    """Start global disk monitoring."""
    manager = get_disk_manager()
    await manager.start_monitoring()


async def stop_disk_monitoring() -> None:
    """Stop global disk monitoring."""
    global _disk_manager
    if _disk_manager:
        await _disk_manager.stop_monitoring()


def get_current_disk_stats() -> DiskStats:
    """Get current disk statistics."""
    manager = get_disk_manager()
    return manager.get_current_stats()


async def handle_disk_pressure() -> bool:
    """Handle current disk pressure."""
    manager = get_disk_manager()
    return await manager.handle_disk_pressure()


async def analyze_disk_usage(path: str = "/") -> List[DirectoryInfo]:
    """Analyze disk usage for cleanup opportunities."""
    manager = get_disk_manager()
    return await manager.analyze_directory_sizes(path)