"""
Event Loop Optimization
Phase 5A: Performance Optimization

Optimizes asyncio event loop performance with monitoring, connection pooling,
and I/O operation optimization.
"""

import asyncio
import logging
import time
import threading
import weakref
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import signal
import socket

logger = logging.getLogger(__name__)


@dataclass
class EventLoopMetrics:
    """Event loop performance metrics"""
    slow_callbacks_count: int = 0
    average_callback_time: float = 0.0
    pending_tasks: int = 0
    running_tasks: int = 0
    total_callbacks: int = 0
    blocked_time: float = 0.0
    gc_collections: int = 0
    memory_usage: float = 0.0


class EventLoopOptimizer:
    """
    Optimizes asyncio event loop performance through monitoring and optimization.
    
    Features:
    - Slow callback detection and optimization
    - Task monitoring and management
    - Connection pool optimization
    - I/O operation batching
    - Event loop health monitoring
    """
    
    def __init__(self, 
                 slow_callback_threshold: float = 0.1,
                 max_blocking_time: float = 1.0,
                 enable_monitoring: bool = True):
        """
        Initialize event loop optimizer.
        
        Args:
            slow_callback_threshold: Time in seconds to consider a callback slow
            max_blocking_time: Maximum blocking time before warning
            enable_monitoring: Enable performance monitoring
        """
        self.slow_callback_threshold = slow_callback_threshold
        self.max_blocking_time = max_blocking_time
        self.enable_monitoring = enable_monitoring
        
        # Metrics
        self.metrics = EventLoopMetrics()
        self._start_time = time.time()
        self._callback_times: List[float] = []
        self._slow_callbacks: Dict[str, int] = {}
        
        # Monitoring
        self._monitoring_enabled = False
        self._original_call_soon = None
        self._original_call_later = None
        
        # Task management
        self._managed_tasks: Set[asyncio.Task] = set()
        self._task_monitor_task: Optional[asyncio.Task] = None
        
        # Thread pool for blocking operations
        self._thread_pool: Optional[ThreadPoolExecutor] = None
        self._thread_pool_size = min(32, (4 * (len(asyncio.os.cpu_count()) or 1)))
        
        # Connection pooling
        self._connection_pools: Dict[str, Any] = {}
        
        logger.info("Event loop optimizer initialized")
    
    async def start_monitoring(self) -> None:
        """Start event loop monitoring."""
        if self._monitoring_enabled:
            logger.warning("Event loop monitoring is already enabled")
            return
        
        try:
            loop = asyncio.get_running_loop()
            
            # Install slow callback detection
            if hasattr(loop, 'slow_callback_duration'):
                loop.slow_callback_duration = self.slow_callback_threshold
                logger.info(f"Set slow callback duration to {self.slow_callback_threshold}s")
            
            # Install custom signal handlers for monitoring
            if hasattr(signal, 'SIGUSR1'):  # Unix only
                signal.signal(signal.SIGUSR1, self._dump_event_loop_state)
            
            # Start thread pool
            self._thread_pool = ThreadPoolExecutor(
                max_workers=self._thread_pool_size,
                thread_name_prefix="aicleaner_io"
            )
            
            # Start task monitoring
            self._task_monitor_task = asyncio.create_task(self._monitor_tasks())
            
            self._monitoring_enabled = True
            logger.info("Event loop monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start event loop monitoring: {e}")
            raise
    
    async def stop_monitoring(self) -> None:
        """Stop event loop monitoring."""
        if not self._monitoring_enabled:
            return
        
        try:
            # Stop task monitoring
            if self._task_monitor_task:
                self._task_monitor_task.cancel()
                try:
                    await self._task_monitor_task
                except asyncio.CancelledError:
                    pass
                self._task_monitor_task = None
            
            # Shutdown thread pool
            if self._thread_pool:
                self._thread_pool.shutdown(wait=True)
                self._thread_pool = None
            
            # Cancel managed tasks
            for task in list(self._managed_tasks):
                if not task.done():
                    task.cancel()
            
            if self._managed_tasks:
                await asyncio.gather(*self._managed_tasks, return_exceptions=True)
            
            self._monitoring_enabled = False
            logger.info("Event loop monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping event loop monitoring: {e}")
    
    async def run_in_thread(self, func: Callable, *args, **kwargs) -> Any:
        """
        Run blocking function in thread pool.
        
        Args:
            func: Function to run
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        if not self._thread_pool:
            raise RuntimeError("Thread pool not initialized")
        
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._thread_pool, func, *args, **kwargs)
    
    def create_optimized_task(self, coro, *, name: str = None) -> asyncio.Task:
        """
        Create an optimized task with monitoring.
        
        Args:
            coro: Coroutine to run
            name: Optional task name
            
        Returns:
            Created task
        """
        task = asyncio.create_task(coro, name=name)
        
        # Add to managed tasks
        self._managed_tasks.add(task)
        
        # Add cleanup callback
        task.add_done_callback(self._task_done_callback)
        
        return task
    
    def get_connection_pool(self, pool_id: str, factory: Callable) -> Any:
        """
        Get or create a connection pool.
        
        Args:
            pool_id: Unique pool identifier
            factory: Factory function to create pool
            
        Returns:
            Connection pool
        """
        if pool_id not in self._connection_pools:
            self._connection_pools[pool_id] = factory()
            logger.debug(f"Created connection pool: {pool_id}")
        
        return self._connection_pools[pool_id]
    
    async def optimize_socket(self, sock: socket.socket) -> None:
        """
        Optimize socket settings for performance.
        
        Args:
            sock: Socket to optimize
        """
        try:
            # Enable TCP_NODELAY for low latency
            if sock.family == socket.AF_INET:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            # Set socket buffer sizes
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            
            # Enable keep-alive
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            logger.debug("Socket optimized for performance")
            
        except Exception as e:
            logger.warning(f"Failed to optimize socket: {e}")
    
    async def batch_io_operations(self, operations: List[Callable]) -> List[Any]:
        """
        Batch I/O operations for better performance.
        
        Args:
            operations: List of async callables
            
        Returns:
            List of results
        """
        if not operations:
            return []
        
        # Execute operations concurrently
        tasks = [asyncio.create_task(op()) for op in operations]
        
        try:
            return await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in batched I/O operations: {e}")
            # Cancel remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            raise
    
    def get_metrics(self) -> EventLoopMetrics:
        """Get current event loop metrics."""
        # Update runtime metrics
        loop = asyncio.get_running_loop()
        
        # Count current tasks
        all_tasks = asyncio.all_tasks(loop)
        pending_tasks = sum(1 for task in all_tasks if not task.done())
        running_tasks = len(self._managed_tasks)
        
        # Update metrics
        self.metrics.pending_tasks = pending_tasks
        self.metrics.running_tasks = running_tasks
        
        if self._callback_times:
            self.metrics.average_callback_time = sum(self._callback_times) / len(self._callback_times)
        
        return self.metrics
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """Get detailed diagnostics information."""
        loop = asyncio.get_running_loop()
        
        # Get all tasks
        all_tasks = asyncio.all_tasks(loop)
        
        # Task analysis
        task_states = {}
        for task in all_tasks:
            state = "running" if not task.done() else ("cancelled" if task.cancelled() else "done")
            task_states[state] = task_states.get(state, 0) + 1
        
        # Connection pool info
        pool_info = {}
        for pool_id, pool in self._connection_pools.items():
            if hasattr(pool, '_pool_size'):
                pool_info[pool_id] = {
                    "size": getattr(pool, '_pool_size', 'unknown'),
                    "available": getattr(pool, '_available_connections', 'unknown')
                }
        
        return {
            "uptime": time.time() - self._start_time,
            "monitoring_enabled": self._monitoring_enabled,
            "task_states": task_states,
            "slow_callbacks": dict(self._slow_callbacks),
            "thread_pool_size": self._thread_pool_size if self._thread_pool else 0,
            "connection_pools": pool_info,
            "metrics": self.metrics.__dict__
        }
    
    async def _monitor_tasks(self) -> None:
        """Monitor task performance."""
        while self._monitoring_enabled:
            try:
                # Check for slow or stuck tasks
                current_time = time.time()
                
                for task in list(self._managed_tasks):
                    if task.done():
                        continue
                    
                    # Check if task has been running too long
                    if hasattr(task, '_start_time'):
                        runtime = current_time - task._start_time
                        if runtime > self.max_blocking_time:
                            logger.warning(
                                f"Long-running task detected: {task.get_name()} "
                                f"(runtime: {runtime:.2f}s)"
                            )
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in task monitoring: {e}")
                await asyncio.sleep(10)
    
    def _task_done_callback(self, task: asyncio.Task) -> None:
        """Callback for completed tasks."""
        try:
            self._managed_tasks.discard(task)
            
            # Log task completion
            if task.cancelled():
                logger.debug(f"Task cancelled: {task.get_name()}")
            elif task.exception():
                logger.error(f"Task failed: {task.get_name()}: {task.exception()}")
            else:
                logger.debug(f"Task completed: {task.get_name()}")
                
        except Exception as e:
            logger.error(f"Error in task done callback: {e}")
    
    def _dump_event_loop_state(self, signum, frame) -> None:
        """Signal handler to dump event loop state (debugging)."""
        try:
            loop = asyncio.get_running_loop()
            
            # Get all tasks
            tasks = asyncio.all_tasks(loop)
            
            logger.info("=== Event Loop State Dump ===")
            logger.info(f"Total tasks: {len(tasks)}")
            
            for i, task in enumerate(tasks):
                logger.info(f"Task {i}: {task.get_name()} - {task._state}")
            
            logger.info(f"Metrics: {self.get_metrics()}")
            logger.info("=== End State Dump ===")
            
        except Exception as e:
            logger.error(f"Error dumping event loop state: {e}")


# Global optimizer instance
_event_loop_optimizer: Optional[EventLoopOptimizer] = None


def get_event_loop_optimizer(
    slow_callback_threshold: float = 0.1,
    max_blocking_time: float = 1.0,
    enable_monitoring: bool = True
) -> EventLoopOptimizer:
    """
    Get global event loop optimizer instance.
    
    Args:
        slow_callback_threshold: Time in seconds to consider a callback slow
        max_blocking_time: Maximum blocking time before warning
        enable_monitoring: Enable performance monitoring
        
    Returns:
        EventLoopOptimizer instance
    """
    global _event_loop_optimizer
    
    if _event_loop_optimizer is None:
        _event_loop_optimizer = EventLoopOptimizer(
            slow_callback_threshold=slow_callback_threshold,
            max_blocking_time=max_blocking_time,
            enable_monitoring=enable_monitoring
        )
    
    return _event_loop_optimizer


async def start_event_loop_monitoring() -> None:
    """Start global event loop monitoring."""
    optimizer = get_event_loop_optimizer()
    await optimizer.start_monitoring()


async def stop_event_loop_monitoring() -> None:
    """Stop global event loop monitoring."""
    global _event_loop_optimizer
    if _event_loop_optimizer:
        await _event_loop_optimizer.stop_monitoring()


def optimized_task(name: str = None):
    """
    Decorator to create optimized tasks.
    
    Args:
        name: Optional task name
        
    Returns:
        Decorated coroutine
    """
    def decorator(coro_func):
        async def wrapper(*args, **kwargs):
            optimizer = get_event_loop_optimizer()
            coro = coro_func(*args, **kwargs)
            return await optimizer.create_optimized_task(coro, name=name or coro_func.__name__)
        return wrapper
    return decorator


def run_in_thread(func: Callable):
    """
    Decorator to run function in thread pool.
    
    Args:
        func: Function to run in thread
        
    Returns:
        Async wrapper function
    """
    async def wrapper(*args, **kwargs):
        optimizer = get_event_loop_optimizer()
        return await optimizer.run_in_thread(func, *args, **kwargs)
    return wrapper