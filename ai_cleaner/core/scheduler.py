"""
Zone analysis scheduling system for AI Cleaner addon.
Manages timed analysis, quiet hours, and adaptive scheduling.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass
from enum import Enum
import crontab

from .config import get_config, AiCleanerConfig, ZoneConfig


logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    """Types of scheduled tasks."""
    ZONE_ANALYSIS = "zone_analysis"
    HEALTH_CHECK = "health_check"
    CLEANUP = "cleanup"


class SchedulePriority(Enum):
    """Priority levels for scheduled tasks."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ScheduledTask:
    """Represents a scheduled task."""
    id: str
    name: str
    task_type: ScheduleType
    callback: Callable
    priority: SchedulePriority
    zone_id: Optional[str] = None
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    enabled: bool = True
    max_retries: int = 3
    current_retries: int = 0
    timeout_seconds: int = 300
    
    def __post_init__(self):
        """Calculate next run time after initialization."""
        if self.next_run is None:
            self.calculate_next_run()
    
    def calculate_next_run(self):
        """Calculate the next run time based on cron or interval."""
        now = datetime.now()
        
        if self.cron_expression:
            try:
                cron = crontab.CronTab(self.cron_expression)
                self.next_run = now + timedelta(seconds=cron.next())
            except Exception as e:
                logger.error(f"Invalid cron expression for task {self.id}: {e}")
                # Fall back to interval if cron fails
                if self.interval_seconds:
                    self.next_run = now + timedelta(seconds=self.interval_seconds)
                else:
                    self.next_run = now + timedelta(hours=1)  # Default fallback
        
        elif self.interval_seconds:
            self.next_run = now + timedelta(seconds=self.interval_seconds)
        
        else:
            # Default to 1 hour if no schedule specified
            self.next_run = now + timedelta(hours=1)
    
    def is_due(self) -> bool:
        """Check if the task is due to run."""
        return self.enabled and self.next_run and datetime.now() >= self.next_run
    
    def mark_completed(self, success: bool = True):
        """Mark task as completed and calculate next run."""
        self.last_run = datetime.now()
        
        if success:
            self.current_retries = 0
        else:
            self.current_retries += 1
        
        # Calculate next run time
        self.calculate_next_run()
    
    def should_retry(self) -> bool:
        """Check if task should be retried after failure."""
        return self.current_retries < self.max_retries


class AdaptiveScheduler:
    """
    Adaptive scheduler that learns from analysis results and adjusts timing.
    """
    
    def __init__(self):
        self.zone_scores: Dict[str, List[float]] = {}  # Historical cleanliness scores
        self.zone_frequency: Dict[str, float] = {}  # Analysis frequency multiplier
        self.learning_rate = 0.1
        self.min_frequency_multiplier = 0.5
        self.max_frequency_multiplier = 3.0
    
    def record_analysis_result(self, zone_id: str, cleanliness_score: float):
        """Record analysis result for adaptive learning."""
        if zone_id not in self.zone_scores:
            self.zone_scores[zone_id] = []
            self.zone_frequency[zone_id] = 1.0
        
        # Keep only last 20 scores for memory efficiency
        self.zone_scores[zone_id].append(cleanliness_score)
        if len(self.zone_scores[zone_id]) > 20:
            self.zone_scores[zone_id].pop(0)
        
        # Adapt frequency based on cleanliness trend
        self._adapt_zone_frequency(zone_id)
    
    def _adapt_zone_frequency(self, zone_id: str):
        """Adapt analysis frequency based on cleanliness trends."""
        scores = self.zone_scores[zone_id]
        if len(scores) < 3:
            return
        
        # Calculate trend - negative means getting dirtier
        recent_avg = sum(scores[-3:]) / 3
        older_avg = sum(scores[-6:-3]) / 3 if len(scores) >= 6 else recent_avg
        trend = recent_avg - older_avg
        
        # Calculate current average cleanliness
        avg_cleanliness = sum(scores) / len(scores)
        
        # Adjust frequency based on:
        # 1. Trend (getting dirtier = more frequent)
        # 2. Average cleanliness (dirtier zones = more frequent)
        # 3. Variability (unstable zones = more frequent)
        variability = max(scores) - min(scores)
        
        # Calculate adjustment
        trend_factor = -trend * 2  # Negative trend increases frequency
        cleanliness_factor = (1 - avg_cleanliness) * 1.5  # Lower cleanliness increases frequency
        variability_factor = variability * 0.5  # Higher variability increases frequency
        
        adjustment = (trend_factor + cleanliness_factor + variability_factor) * self.learning_rate
        
        # Apply adjustment
        current_freq = self.zone_frequency[zone_id]
        new_freq = current_freq + adjustment
        
        # Clamp to reasonable bounds
        self.zone_frequency[zone_id] = max(
            self.min_frequency_multiplier,
            min(self.max_frequency_multiplier, new_freq)
        )
        
        logger.debug(f"Zone {zone_id} frequency adjusted to {self.zone_frequency[zone_id]:.2f}")
    
    def get_zone_frequency_multiplier(self, zone_id: str) -> float:
        """Get frequency multiplier for a zone."""
        return self.zone_frequency.get(zone_id, 1.0)
    
    def get_zone_priority(self, zone_id: str) -> SchedulePriority:
        """Get recommended priority for a zone based on history."""
        if zone_id not in self.zone_scores:
            return SchedulePriority.NORMAL
        
        scores = self.zone_scores[zone_id]
        avg_cleanliness = sum(scores) / len(scores)
        
        if avg_cleanliness < 0.3:
            return SchedulePriority.CRITICAL
        elif avg_cleanliness < 0.5:
            return SchedulePriority.HIGH
        elif avg_cleanliness < 0.7:
            return SchedulePriority.NORMAL
        else:
            return SchedulePriority.LOW


class ZoneScheduler:
    """
    Main scheduler for zone analysis and system tasks.
    """
    
    def __init__(self, config: Optional[AiCleanerConfig] = None):
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)
        
        self.tasks: Dict[str, ScheduledTask] = {}
        self.adaptive_scheduler = AdaptiveScheduler()
        self.running_tasks: Set[str] = set()
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
        self._callbacks: Dict[ScheduleType, Callable] = {}
    
    def register_callback(self, task_type: ScheduleType, callback: Callable):
        """Register callback for a task type."""
        self._callbacks[task_type] = callback
        self.logger.debug(f"Registered callback for {task_type.value}")
    
    def add_task(self, task: ScheduledTask) -> bool:
        """Add a scheduled task."""
        try:
            # Validate callback is registered
            if task.task_type not in self._callbacks:
                self.logger.error(f"No callback registered for task type {task.task_type.value}")
                return False
            
            # Set callback
            task.callback = self._callbacks[task.task_type]
            
            # Add to tasks
            self.tasks[task.id] = task
            
            self.logger.info(f"Added scheduled task: {task.name} (ID: {task.id})")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to add task {task.name}: {e}")
            return False
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        if task_id in self.tasks:
            # Cancel if currently running
            if task_id in self.running_tasks:
                self.logger.warning(f"Removing task {task_id} while it's running")
            
            del self.tasks[task_id]
            self.running_tasks.discard(task_id)
            
            self.logger.info(f"Removed scheduled task: {task_id}")
            return True
        
        return False
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a scheduled task by ID."""
        return self.tasks.get(task_id)
    
    def list_tasks(self) -> List[ScheduledTask]:
        """Get list of all scheduled tasks."""
        return list(self.tasks.values())
    
    def enable_task(self, task_id: str) -> bool:
        """Enable a scheduled task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """Disable a scheduled task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            return True
        return False
    
    def setup_default_tasks(self):
        """Setup default scheduled tasks based on configuration."""
        # Zone analysis tasks
        if self.config.enable_zones:
            for zone in self.config.get_enabled_zones():
                self._create_zone_analysis_task(zone)
        elif self.config.camera_entity:
            # Default zone task
            default_zone = ZoneConfig(
                id="default",
                name="Default Zone",
                camera_entity=self.config.camera_entity,
                priority=3
            )
            self._create_zone_analysis_task(default_zone)
        
        # System health check task
        health_check_task = ScheduledTask(
            id="system_health_check",
            name="System Health Check",
            task_type=ScheduleType.HEALTH_CHECK,
            callback=None,  # Will be set when callback is registered
            priority=SchedulePriority.NORMAL,
            interval_seconds=300,  # 5 minutes
            timeout_seconds=60
        )
        
        if ScheduleType.HEALTH_CHECK in self._callbacks:
            health_check_task.callback = self._callbacks[ScheduleType.HEALTH_CHECK]
            self.tasks[health_check_task.id] = health_check_task
        
        # Cleanup task (runs daily)
        cleanup_task = ScheduledTask(
            id="daily_cleanup",
            name="Daily Cleanup",
            task_type=ScheduleType.CLEANUP,
            callback=None,  # Will be set when callback is registered
            priority=SchedulePriority.LOW,
            cron_expression="0 2 * * *",  # 2 AM daily
            timeout_seconds=300
        )
        
        if ScheduleType.CLEANUP in self._callbacks:
            cleanup_task.callback = self._callbacks[ScheduleType.CLEANUP]
            self.tasks[cleanup_task.id] = cleanup_task
        
        self.logger.info(f"Setup {len(self.tasks)} default scheduled tasks")
    
    def _create_zone_analysis_task(self, zone: ZoneConfig):
        """Create analysis task for a zone."""
        task_id = f"zone_analysis_{zone.id}"
        
        # Calculate interval based on zone priority and adaptive frequency
        base_interval = self.config.analysis_interval
        priority_multiplier = {
            1: 2.0,    # Low priority = less frequent
            2: 1.5,
            3: 1.0,    # Normal priority = base frequency
            4: 0.75,
            5: 0.5     # High priority = more frequent
        }.get(zone.priority, 1.0)
        
        adaptive_multiplier = self.adaptive_scheduler.get_zone_frequency_multiplier(zone.id)
        
        # Final interval (lower = more frequent)
        interval = int(base_interval * priority_multiplier / adaptive_multiplier)
        interval = max(60, min(86400, interval))  # Clamp between 1 minute and 1 day
        
        # Determine priority
        adaptive_priority = self.adaptive_scheduler.get_zone_priority(zone.id)
        
        task = ScheduledTask(
            id=task_id,
            name=f"Zone Analysis - {zone.name}",
            task_type=ScheduleType.ZONE_ANALYSIS,
            callback=None,  # Will be set when callback is registered
            priority=adaptive_priority,
            zone_id=zone.id,
            cron_expression=zone.schedule,  # Use zone-specific schedule if available
            interval_seconds=interval if not zone.schedule else None,
            timeout_seconds=self.config.analysis_timeout
        )
        
        if ScheduleType.ZONE_ANALYSIS in self._callbacks:
            task.callback = self._callbacks[ScheduleType.ZONE_ANALYSIS]
            self.tasks[task_id] = task
    
    def is_quiet_hours(self) -> bool:
        """Check if currently in quiet hours."""
        return self.config.is_in_quiet_hours()
    
    async def start(self):
        """Start the scheduler."""
        if self._running:
            self.logger.warning("Scheduler is already running")
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        self.logger.info("Zone scheduler started")
    
    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Wait for running tasks to complete (with timeout)
        if self.running_tasks:
            self.logger.info(f"Waiting for {len(self.running_tasks)} tasks to complete...")
            
            for _ in range(30):  # Wait up to 30 seconds
                if not self.running_tasks:
                    break
                await asyncio.sleep(1)
        
        self.logger.info("Zone scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                # Get due tasks
                due_tasks = [task for task in self.tasks.values() if task.is_due()]
                
                # Filter out tasks in quiet hours (unless critical)
                if self.is_quiet_hours():
                    due_tasks = [
                        task for task in due_tasks 
                        if task.priority == SchedulePriority.CRITICAL
                    ]
                
                # Sort by priority (critical first)
                due_tasks.sort(key=lambda t: t.priority.value, reverse=True)
                
                # Execute tasks
                for task in due_tasks:
                    if not self._running:
                        break
                    
                    if task.id not in self.running_tasks:
                        asyncio.create_task(self._execute_task(task))
                
                # Sleep before next check
                await asyncio.sleep(10)  # Check every 10 seconds
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        if task.id in self.running_tasks:
            self.logger.debug(f"Task {task.id} is already running, skipping")
            return
        
        self.running_tasks.add(task.id)
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Executing task: {task.name} (ID: {task.id})")
            
            # Execute with timeout
            await asyncio.wait_for(
                task.callback(task.zone_id) if task.zone_id else task.callback(),
                timeout=task.timeout_seconds
            )
            
            # Mark as successful
            task.mark_completed(success=True)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"Task {task.name} completed successfully in {execution_time:.2f}s")
        
        except asyncio.TimeoutError:
            self.logger.error(f"Task {task.name} timed out after {task.timeout_seconds}s")
            task.mark_completed(success=False)
            
            if task.should_retry():
                # Schedule retry in 5 minutes
                task.next_run = datetime.now() + timedelta(minutes=5)
                self.logger.info(f"Task {task.name} scheduled for retry ({task.current_retries}/{task.max_retries})")
        
        except Exception as e:
            self.logger.error(f"Task {task.name} failed: {e}")
            task.mark_completed(success=False)
            
            if task.should_retry():
                # Schedule retry with exponential backoff
                retry_delay = min(300, 60 * (2 ** task.current_retries))  # Max 5 minutes
                task.next_run = datetime.now() + timedelta(seconds=retry_delay)
                self.logger.info(f"Task {task.name} scheduled for retry in {retry_delay}s ({task.current_retries}/{task.max_retries})")
        
        finally:
            self.running_tasks.discard(task.id)
    
    def record_analysis_result(self, zone_id: str, cleanliness_score: float):
        """Record analysis result for adaptive scheduling."""
        self.adaptive_scheduler.record_analysis_result(zone_id, cleanliness_score)
        
        # Update zone task frequency if it exists
        task_id = f"zone_analysis_{zone_id}"
        if task_id in self.tasks:
            # Recalculate interval
            zone_config = self.config.get_zone_by_id(zone_id)
            if zone_config:
                self._update_zone_task_frequency(zone_config)
    
    def _update_zone_task_frequency(self, zone: ZoneConfig):
        """Update zone task frequency based on adaptive learning."""
        task_id = f"zone_analysis_{zone.id}"
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        
        # Don't update if using cron schedule
        if task.cron_expression:
            return
        
        # Calculate new interval
        base_interval = self.config.analysis_interval
        priority_multiplier = {
            1: 2.0, 2: 1.5, 3: 1.0, 4: 0.75, 5: 0.5
        }.get(zone.priority, 1.0)
        
        adaptive_multiplier = self.adaptive_scheduler.get_zone_frequency_multiplier(zone.id)
        
        new_interval = int(base_interval * priority_multiplier / adaptive_multiplier)
        new_interval = max(60, min(86400, new_interval))
        
        # Update task
        if new_interval != task.interval_seconds:
            task.interval_seconds = new_interval
            task.calculate_next_run()
            
            self.logger.info(f"Updated {zone.name} analysis interval to {new_interval}s")
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        now = datetime.now()
        
        return {
            'running': self._running,
            'total_tasks': len(self.tasks),
            'enabled_tasks': len([t for t in self.tasks.values() if t.enabled]),
            'running_tasks': len(self.running_tasks),
            'due_tasks': len([t for t in self.tasks.values() if t.is_due()]),
            'in_quiet_hours': self.is_quiet_hours(),
            'next_task': min(
                (t.next_run for t in self.tasks.values() if t.enabled and t.next_run),
                default=None
            ),
            'zone_frequencies': dict(self.adaptive_scheduler.zone_frequency),
            'tasks': [
                {
                    'id': task.id,
                    'name': task.name,
                    'type': task.task_type.value,
                    'enabled': task.enabled,
                    'next_run': task.next_run.isoformat() if task.next_run else None,
                    'last_run': task.last_run.isoformat() if task.last_run else None,
                    'running': task.id in self.running_tasks,
                    'retries': task.current_retries,
                    'zone_id': task.zone_id
                }
                for task in self.tasks.values()
            ]
        }