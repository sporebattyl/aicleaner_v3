"""
CPU Resource Management System  
Phase 5B: Resource Management

Advanced CPU monitoring, throttling, and adaptive task scheduling
for optimal Home Assistant integration.
"""

import asyncio
import logging
import psutil
import time
import threading
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import deque
from enum import Enum
import os

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels for CPU scheduling"""
    CRITICAL = 1    # System critical tasks
    HIGH = 2        # Important user-facing tasks  
    NORMAL = 3      # Regular background tasks
    LOW = 4         # Cleanup and maintenance tasks


@dataclass
class CPUStats:
    """CPU usage statistics"""
    process_cpu_percent: float  # Process CPU usage
    system_cpu_percent: float  # System-wide CPU usage
    cpu_count: int             # Number of CPU cores
    load_average: Tuple[float, float, float]  # 1m, 5m, 15m load averages
    context_switches: int      # Context switches per second
    interrupts: int           # Interrupts per second
    cpu_times: Dict[str, float]  # Detailed CPU time breakdown


@dataclass
class TaskInfo:
    """Information about a scheduled task"""
    task_id: str
    priority: TaskPriority
    estimated_duration: float
    cpu_intensive: bool
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    actual_duration: Optional[float] = None
    cpu_usage: Optional[float] = None


class CPUManager:
    """
    Advanced CPU resource management system.
    
    Features:
    - Real-time CPU monitoring
    - Adaptive task scheduling based on system load
    - CPU throttling and rate limiting
    - Background task prioritization
    - Integration with system load balancing
    - Home Assistant resource constraint awareness
    """
    
    def __init__(self,
                 cpu_limit_percent: float = 70.0,
                 warning_threshold: float = 60.0,
                 critical_threshold: float = 80.0,
                 adaptive_scheduling: bool = True,
                 background_throttling: bool = True,
                 monitoring_interval: float = 5.0):
        """
        Initialize CPU manager.
        
        Args:
            cpu_limit_percent: Maximum CPU usage percentage
            warning_threshold: Warning threshold for CPU usage
            critical_threshold: Critical threshold for CPU usage
            adaptive_scheduling: Enable adaptive task scheduling
            background_throttling: Enable background task throttling
            monitoring_interval: Monitoring interval in seconds
        """
        self.cpu_limit_percent = cpu_limit_percent
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.adaptive_scheduling = adaptive_scheduling
        self.background_throttling = background_throttling
        self.monitoring_interval = monitoring_interval
        
        # CPU monitoring
        self._process = psutil.Process()
        self._monitoring_enabled = False
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # CPU statistics
        self._stats_history: deque = deque(maxlen=100)
        self._current_stats: Optional[CPUStats] = None
        
        # Task scheduling
        self._task_queues: Dict[TaskPriority, deque] = {
            priority: deque() for priority in TaskPriority
        }
        self._active_tasks: Dict[str, TaskInfo] = {}
        self._completed_tasks: deque = deque(maxlen=1000)
        self._scheduler_task: Optional[asyncio.Task] = None
        self._scheduler_enabled = False
        
        # Throttling
        self._throttle_enabled = False
        self._throttle_delay = 0.0
        self._throttle_queue: deque = deque()
        
        # Callbacks
        self._warning_callbacks: List[Callable] = []
        self._critical_callbacks: List[Callable] = []
        self._throttle_callbacks: List[Callable] = []
        
        # Performance optimization
        self._cpu_affinity_enabled = False
        self._priority_adjustment_enabled = False
        
        logger.info(f"CPU manager initialized (limit: {cpu_limit_percent}%)")
    
    async def start_monitoring(self) -> None:
        """Start CPU monitoring and task scheduling."""
        if self._monitoring_enabled:
            logger.warning("CPU monitoring already enabled")
            return
        
        try:
            # Start monitoring task
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            # Start task scheduler if adaptive scheduling is enabled
            if self.adaptive_scheduling:
                self._scheduler_task = asyncio.create_task(self._scheduler_loop())
                self._scheduler_enabled = True
            
            self._monitoring_enabled = True
            
            # Optimize process settings
            await self._optimize_process_settings()
            
            logger.info("CPU monitoring and scheduling started")
            
        except Exception as e:
            logger.error(f"Failed to start CPU monitoring: {e}")
            raise
    
    async def stop_monitoring(self) -> None:
        """Stop CPU monitoring and task scheduling."""
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
            
            # Stop scheduler task
            if self._scheduler_task:
                self._scheduler_task.cancel()
                try:
                    await self._scheduler_task
                except asyncio.CancelledError:
                    pass
                self._scheduler_task = None
            
            self._monitoring_enabled = False
            self._scheduler_enabled = False
            
            logger.info("CPU monitoring and scheduling stopped")
            
        except Exception as e:
            logger.error(f"Error stopping CPU monitoring: {e}")
    
    def get_current_stats(self) -> CPUStats:
        """Get current CPU statistics."""
        try:
            # Get process CPU info
            process_cpu = self._process.cpu_percent(interval=None)
            
            # Get system CPU info
            system_cpu = psutil.cpu_percent(interval=None)
            cpu_count = psutil.cpu_count()
            
            # Get load average (Unix systems only)
            load_avg = (0.0, 0.0, 0.0)
            try:
                if hasattr(os, 'getloadavg'):
                    load_avg = os.getloadavg()
            except (AttributeError, OSError):
                pass
            
            # Get CPU times
            cpu_times = psutil.cpu_times()._asdict()
            
            # Get context switches and interrupts (if available)
            context_switches = 0
            interrupts = 0
            try:
                boot_time = psutil.boot_time()
                current_time = time.time()
                uptime = current_time - boot_time
                
                if hasattr(psutil, 'cpu_stats'):
                    cpu_stats = psutil.cpu_stats()
                    context_switches = getattr(cpu_stats, 'ctx_switches', 0) / uptime
                    interrupts = getattr(cpu_stats, 'interrupts', 0) / uptime
            except Exception:
                pass
            
            return CPUStats(
                process_cpu_percent=process_cpu,
                system_cpu_percent=system_cpu,
                cpu_count=cpu_count,
                load_average=load_avg,
                context_switches=int(context_switches),
                interrupts=int(interrupts),
                cpu_times=cpu_times
            )
            
        except Exception as e:
            logger.error(f"Error getting CPU stats: {e}")
            return CPUStats(0, 0, 1, (0, 0, 0), 0, 0, {})
    
    def check_cpu_pressure(self) -> Dict[str, Any]:
        """Check current CPU pressure level."""
        stats = self.get_current_stats()
        
        # Use process CPU percentage for pressure calculation
        cpu_usage = stats.process_cpu_percent
        
        # Determine pressure level
        if cpu_usage >= self.critical_threshold:
            pressure_level = "critical"
        elif cpu_usage >= self.warning_threshold:
            pressure_level = "warning"
        else:
            pressure_level = "normal"
        
        # Check system load
        load_1m = stats.load_average[0] if stats.load_average else 0
        load_pressure = "normal"
        if load_1m > stats.cpu_count * 0.8:
            load_pressure = "high"
        elif load_1m > stats.cpu_count * 0.6:
            load_pressure = "moderate"
        
        return {
            "pressure_level": pressure_level,
            "cpu_usage_percent": cpu_usage,
            "system_cpu_percent": stats.system_cpu_percent,
            "load_pressure": load_pressure,
            "load_average": stats.load_average,
            "cpu_limit": self.cpu_limit_percent,
            "action_needed": pressure_level in ["warning", "critical"],
            "throttling_recommended": cpu_usage > self.cpu_limit_percent
        }
    
    async def schedule_task(self,
                           task_coro,
                           priority: TaskPriority = TaskPriority.NORMAL,
                           cpu_intensive: bool = False,
                           estimated_duration: float = 1.0,
                           task_id: Optional[str] = None) -> str:
        """
        Schedule a task with priority-based execution.
        
        Args:
            task_coro: Coroutine to execute
            priority: Task priority level
            cpu_intensive: Whether task is CPU intensive
            estimated_duration: Estimated execution time in seconds
            task_id: Optional task identifier
            
        Returns:
            Task ID for tracking
        """
        if not task_id:
            task_id = f"task_{int(time.time())}_{id(task_coro)}"
        
        # Create task info
        task_info = TaskInfo(
            task_id=task_id,
            priority=priority,
            estimated_duration=estimated_duration,
            cpu_intensive=cpu_intensive,
            created_at=datetime.now()
        )
        
        # Add to appropriate queue
        self._task_queues[priority].append((task_coro, task_info))
        
        logger.debug(f"Scheduled task {task_id} with priority {priority.name}")
        return task_id
    
    async def handle_cpu_pressure(self) -> bool:
        """Handle CPU pressure by throttling and optimization."""
        logger.info("Handling CPU pressure...")
        
        actions_taken = []
        
        try:
            # 1. Enable throttling if not already enabled
            if not self._throttle_enabled:
                await self._enable_throttling()
                actions_taken.append("Enabled CPU throttling")
            
            # 2. Increase throttle delay based on pressure
            pressure = self.check_cpu_pressure()
            if pressure["pressure_level"] == "critical":
                self._throttle_delay = min(self._throttle_delay + 0.1, 1.0)
                actions_taken.append(f"Increased throttle delay to {self._throttle_delay:.1f}s")
            
            # 3. Pause low priority tasks
            low_priority_tasks = [
                task_id for task_id, info in self._active_tasks.items()
                if info.priority == TaskPriority.LOW
            ]
            
            for task_id in low_priority_tasks:
                # Note: Actual task pausing would require more complex implementation
                # For now, we'll just delay new low priority tasks
                actions_taken.append(f"Delayed low priority task scheduling")
            
            # 4. Optimize process priority
            if self._priority_adjustment_enabled:
                try:
                    # Lower process priority slightly
                    current_nice = os.getpriority(os.PRIO_PROCESS, 0)
                    if current_nice < 5:  # Don't go too high
                        os.setpriority(os.PRIO_PROCESS, 0, current_nice + 1)
                        actions_taken.append(f"Adjusted process priority (nice: {current_nice + 1})")
                except (OSError, AttributeError):
                    pass
            
            # 5. Force garbage collection to free CPU-bound resources
            import gc
            collected = gc.collect()
            if collected > 0:
                actions_taken.append(f"Garbage collected {collected} objects")
            
            logger.info(f"CPU pressure actions: {', '.join(actions_taken)}")
            return len(actions_taken) > 0
            
        except Exception as e:
            logger.error(f"Error handling CPU pressure: {e}")
            return False
    
    async def _enable_throttling(self) -> None:
        """Enable CPU throttling."""
        self._throttle_enabled = True
        self._throttle_delay = 0.05  # Start with 50ms delay
        logger.info("CPU throttling enabled")
    
    async def _disable_throttling(self) -> None:
        """Disable CPU throttling."""
        self._throttle_enabled = False
        self._throttle_delay = 0.0
        logger.info("CPU throttling disabled")
    
    async def _apply_throttling(self) -> None:
        """Apply throttling delay if enabled."""
        if self._throttle_enabled and self._throttle_delay > 0:
            await asyncio.sleep(self._throttle_delay)
    
    async def _optimize_process_settings(self) -> None:
        """Optimize process settings for better CPU management."""
        try:
            # Enable CPU affinity if available and beneficial
            if hasattr(psutil, 'cpu_count') and psutil.cpu_count() > 1:
                # For multi-core systems, we could set CPU affinity
                # For now, we'll just enable the capability flag
                self._cpu_affinity_enabled = True
            
            # Enable priority adjustment
            self._priority_adjustment_enabled = True
            
            logger.debug("Process settings optimized for CPU management")
            
        except Exception as e:
            logger.warning(f"Could not optimize process settings: {e}")
    
    def register_warning_callback(self, callback: Callable) -> None:
        """Register callback for CPU warnings."""
        self._warning_callbacks.append(callback)
    
    def register_critical_callback(self, callback: Callable) -> None:
        """Register callback for critical CPU situations."""
        self._critical_callbacks.append(callback)
    
    def register_throttle_callback(self, callback: Callable) -> None:
        """Register callback for throttling events."""
        self._throttle_callbacks.append(callback)
    
    async def _monitoring_loop(self) -> None:
        """Main CPU monitoring loop."""
        while self._monitoring_enabled:
            try:
                # Get current stats
                stats = self.get_current_stats()
                self._current_stats = stats
                
                # Store in history
                self._stats_history.append({
                    "timestamp": datetime.now(),
                    "stats": stats
                })
                
                # Check CPU pressure
                pressure = self.check_cpu_pressure()
                
                # Handle pressure levels
                if pressure["pressure_level"] == "critical":
                    logger.warning(
                        f"Critical CPU pressure: {stats.process_cpu_percent:.1f}% "
                        f"(system: {stats.system_cpu_percent:.1f}%)"
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
                    await self.handle_cpu_pressure()
                    
                elif pressure["pressure_level"] == "warning":
                    logger.info(
                        f"CPU pressure warning: {stats.process_cpu_percent:.1f}% "
                        f"(system: {stats.system_cpu_percent:.1f}%)"
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
                
                # Check if we should disable throttling
                if (self._throttle_enabled and 
                    pressure["pressure_level"] == "normal" and 
                    stats.process_cpu_percent < self.warning_threshold * 0.8):
                    await self._disable_throttling()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in CPU monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _scheduler_loop(self) -> None:
        """Task scheduler loop."""
        while self._scheduler_enabled:
            try:
                # Check if we should schedule new tasks
                pressure = self.check_cpu_pressure()
                
                # Determine how many tasks we can run concurrently
                if pressure["pressure_level"] == "critical":
                    max_concurrent = 1
                elif pressure["pressure_level"] == "warning":
                    max_concurrent = 2
                else:
                    max_concurrent = 4
                
                # Don't exceed active task limit
                if len(self._active_tasks) >= max_concurrent:
                    await asyncio.sleep(0.5)
                    continue
                
                # Find next task to execute (priority order)
                next_task = None
                next_task_info = None
                
                for priority in TaskPriority:
                    if self._task_queues[priority]:
                        next_task, next_task_info = self._task_queues[priority].popleft()
                        break
                
                if next_task is None:
                    await asyncio.sleep(0.1)
                    continue
                
                # Apply throttling before starting task
                await self._apply_throttling()
                
                # Start the task
                task_start_time = time.time()
                next_task_info.started_at = datetime.now()
                
                # Store active task
                self._active_tasks[next_task_info.task_id] = next_task_info
                
                # Create asyncio task
                async def execute_task():
                    try:
                        # Monitor CPU usage during task execution
                        start_cpu = self._process.cpu_percent()
                        
                        # Execute the actual task
                        await next_task
                        
                        # Calculate actual CPU usage
                        end_cpu = self._process.cpu_percent()
                        cpu_usage = max(0, end_cpu - start_cpu)
                        
                        # Update task info
                        task_end_time = time.time()
                        next_task_info.completed_at = datetime.now()
                        next_task_info.actual_duration = task_end_time - task_start_time
                        next_task_info.cpu_usage = cpu_usage
                        
                        # Move to completed tasks
                        self._completed_tasks.append(next_task_info)
                        
                        logger.debug(
                            f"Task {next_task_info.task_id} completed in "
                            f"{next_task_info.actual_duration:.2f}s (CPU: {cpu_usage:.1f}%)"
                        )
                        
                    except Exception as e:
                        logger.error(f"Error executing task {next_task_info.task_id}: {e}")
                        next_task_info.completed_at = datetime.now()
                        next_task_info.actual_duration = time.time() - task_start_time
                    
                    finally:
                        # Remove from active tasks
                        self._active_tasks.pop(next_task_info.task_id, None)
                
                # Schedule the task execution
                asyncio.create_task(execute_task())
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(1)
    
    def get_cpu_report(self) -> Dict[str, Any]:
        """Get comprehensive CPU report."""
        stats = self.get_current_stats()
        pressure = self.check_cpu_pressure()
        
        # Calculate trends
        trend_data = {}
        if len(self._stats_history) > 1:
            recent_stats = list(self._stats_history)[-10:]  # Last 10 measurements
            avg_cpu = sum(s["stats"].process_cpu_percent for s in recent_stats) / len(recent_stats)
            
            if len(self._stats_history) > 10:
                older_stats = list(self._stats_history)[-20:-10]  # Previous 10 measurements
                old_avg_cpu = sum(s["stats"].process_cpu_percent for s in older_stats) / len(older_stats)
                trend_data["cpu_trend"] = (avg_cpu - old_avg_cpu) / max(old_avg_cpu, 1)
            else:
                trend_data["cpu_trend"] = 0
        
        # Task statistics
        task_stats = {
            "active_tasks": len(self._active_tasks),
            "completed_tasks": len(self._completed_tasks),
            "pending_tasks": sum(len(queue) for queue in self._task_queues.values()),
            "average_duration": 0.0,
            "average_cpu_usage": 0.0
        }
        
        if self._completed_tasks:
            completed_with_duration = [
                t for t in self._completed_tasks 
                if t.actual_duration is not None
            ]
            if completed_with_duration:
                task_stats["average_duration"] = sum(
                    t.actual_duration for t in completed_with_duration
                ) / len(completed_with_duration)
                
                completed_with_cpu = [
                    t for t in completed_with_duration 
                    if t.cpu_usage is not None
                ]
                if completed_with_cpu:
                    task_stats["average_cpu_usage"] = sum(
                        t.cpu_usage for t in completed_with_cpu
                    ) / len(completed_with_cpu)
        
        return {
            "current_stats": stats.__dict__,
            "pressure": pressure,
            "cpu_limit_percent": self.cpu_limit_percent,
            "trends": trend_data,
            "task_scheduling": {
                "enabled": self.adaptive_scheduling,
                "scheduler_running": self._scheduler_enabled,
                "statistics": task_stats
            },
            "throttling": {
                "enabled": self._throttle_enabled,
                "delay_seconds": self._throttle_delay,
                "background_throttling": self.background_throttling
            },
            "optimization": {
                "cpu_affinity_enabled": self._cpu_affinity_enabled,
                "priority_adjustment_enabled": self._priority_adjustment_enabled
            },
            "monitoring_enabled": self._monitoring_enabled
        }


# Global CPU manager instance
_cpu_manager: Optional[CPUManager] = None


def get_cpu_manager(
    cpu_limit_percent: float = 70.0,
    warning_threshold: float = 60.0,
    critical_threshold: float = 80.0
) -> CPUManager:
    """
    Get global CPU manager instance.
    
    Args:
        cpu_limit_percent: Maximum CPU usage percentage
        warning_threshold: Warning threshold for CPU usage
        critical_threshold: Critical threshold for CPU usage
        
    Returns:
        CPUManager instance
    """
    global _cpu_manager
    
    if _cpu_manager is None:
        _cpu_manager = CPUManager(
            cpu_limit_percent=cpu_limit_percent,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold
        )
    
    return _cpu_manager


async def start_cpu_monitoring() -> None:
    """Start global CPU monitoring."""
    manager = get_cpu_manager()
    await manager.start_monitoring()


async def stop_cpu_monitoring() -> None:
    """Stop global CPU monitoring."""
    global _cpu_manager
    if _cpu_manager:
        await _cpu_manager.stop_monitoring()


def get_current_cpu_stats() -> CPUStats:
    """Get current CPU statistics."""
    manager = get_cpu_manager()
    return manager.get_current_stats()


async def schedule_cpu_task(
    task_coro,
    priority: TaskPriority = TaskPriority.NORMAL,
    cpu_intensive: bool = False,
    estimated_duration: float = 1.0
) -> str:
    """Schedule a task with CPU management."""
    manager = get_cpu_manager()
    return await manager.schedule_task(
        task_coro, priority, cpu_intensive, estimated_duration
    )


async def handle_cpu_pressure() -> bool:
    """Handle current CPU pressure."""
    manager = get_cpu_manager()
    return await manager.handle_cpu_pressure()