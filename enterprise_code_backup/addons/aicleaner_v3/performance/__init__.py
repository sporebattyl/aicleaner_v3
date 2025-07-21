"""
Performance Optimization & Resource Management Module
Phase 5A: Performance Optimization
Phase 5B: Resource Management

This module provides performance monitoring, profiling, optimization tools,
and comprehensive resource management for AICleaner v3.
"""

# Phase 5A: Performance Optimization
from .profiler import PerformanceProfiler, profile_async, profile_sync
from .metrics import PerformanceMetrics, PerformanceTracker
from .optimizer import PerformanceOptimizer
from .event_loop_optimizer import (
    EventLoopOptimizer, get_event_loop_optimizer, 
    start_event_loop_monitoring, stop_event_loop_monitoring,
    optimized_task, run_in_thread
)
from .ai_cache import get_ai_cache, clear_ai_cache, get_ai_cache_stats
from .serialization_optimizer import (
    get_serialization_optimizer, fast_json_dumps, fast_json_loads,
    fast_json_dumps_async, fast_json_loads_async, optimize_json_calls
)
from .state_optimizer import (
    get_state_optimizer, start_state_optimization, stop_state_optimization,
    read_optimized_state, write_optimized_state, flush_optimized_state
)

# Phase 5B: Resource Management
from .memory_manager import (
    get_memory_manager, start_memory_monitoring, stop_memory_monitoring,
    get_current_memory_stats, handle_memory_pressure, register_memory_cache,
    MemoryManager, MemoryStats
)
from .cpu_manager import (
    get_cpu_manager, start_cpu_monitoring, stop_cpu_monitoring,
    get_current_cpu_stats, schedule_cpu_task, handle_cpu_pressure,
    CPUManager, CPUStats, TaskPriority
)
from .disk_manager import (
    get_disk_manager, start_disk_monitoring, stop_disk_monitoring,
    get_current_disk_stats, handle_disk_pressure, analyze_disk_usage,
    DiskManager, DiskStats, DirectoryInfo
)
from .network_manager import (
    get_network_manager, start_network_monitoring, stop_network_monitoring,
    get_optimized_session, make_optimized_request, check_network_connectivity,
    NetworkManager, NetworkStats
)
from .health_monitor import (
    get_health_monitor, start_health_monitoring, stop_health_monitoring,
    check_system_health, get_current_health_status, record_request_performance,
    SystemHealthMonitor, SystemHealthMetrics, HealthStatus, HealthThresholds
)
from .supervisor_integration import (
    get_supervisor_client, start_supervisor_monitoring, stop_supervisor_monitoring,
    get_supervisor_system_resources, check_supervisor_health,
    SupervisorAPIClient, SupervisorResourceManager
)
from .resource_manager import (
    get_unified_resource_manager, start_unified_resource_monitoring, stop_unified_resource_monitoring,
    get_resource_status, enforce_resource_limits, predict_resource_usage,
    UnifiedResourceManager, ResourceLimits, ResourceStatus, ResourceType
)

__all__ = [
    # Phase 5A: Performance Optimization
    'PerformanceProfiler', 
    'profile_async', 
    'profile_sync',
    'PerformanceMetrics',
    'PerformanceTracker', 
    'PerformanceOptimizer',
    'EventLoopOptimizer',
    'get_event_loop_optimizer',
    'start_event_loop_monitoring',
    'stop_event_loop_monitoring',
    'optimized_task',
    'run_in_thread',
    'get_ai_cache',
    'clear_ai_cache',
    'get_ai_cache_stats',
    'get_serialization_optimizer',
    'fast_json_dumps',
    'fast_json_loads',
    'fast_json_dumps_async',
    'fast_json_loads_async',
    'optimize_json_calls',
    'get_state_optimizer',
    'start_state_optimization',
    'stop_state_optimization',
    'read_optimized_state',
    'write_optimized_state',
    'flush_optimized_state',
    
    # Phase 5B: Resource Management
    'get_memory_manager',
    'start_memory_monitoring',
    'stop_memory_monitoring',
    'get_current_memory_stats',
    'handle_memory_pressure',
    'register_memory_cache',
    'MemoryManager',
    'MemoryStats',
    'get_cpu_manager',
    'start_cpu_monitoring',
    'stop_cpu_monitoring',
    'get_current_cpu_stats',
    'schedule_cpu_task',
    'handle_cpu_pressure',
    'CPUManager',
    'CPUStats',
    'TaskPriority',
    'get_disk_manager',
    'start_disk_monitoring',
    'stop_disk_monitoring',
    'get_current_disk_stats',
    'handle_disk_pressure',
    'analyze_disk_usage',
    'DiskManager',
    'DiskStats',
    'DirectoryInfo',
    'get_network_manager',
    'start_network_monitoring',
    'stop_network_monitoring',
    'get_optimized_session',
    'make_optimized_request',
    'check_network_connectivity',
    'NetworkManager',
    'NetworkStats',
    'get_health_monitor',
    'start_health_monitoring',
    'stop_health_monitoring',
    'check_system_health',
    'get_current_health_status',
    'record_request_performance',
    'SystemHealthMonitor',
    'SystemHealthMetrics',
    'HealthStatus',
    'HealthThresholds',
    'get_supervisor_client',
    'start_supervisor_monitoring',
    'stop_supervisor_monitoring',
    'get_supervisor_system_resources',
    'check_supervisor_health',
    'SupervisorAPIClient',
    'SupervisorResourceManager',
    'get_unified_resource_manager',
    'start_unified_resource_monitoring',
    'stop_unified_resource_monitoring',
    'get_resource_status',
    'enforce_resource_limits',
    'predict_resource_usage',
    'UnifiedResourceManager',
    'ResourceLimits',
    'ResourceStatus',
    'ResourceType'
]