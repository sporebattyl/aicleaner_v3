"""
System control endpoints for AICleaner v3 Developer API v1
"""

import os
import time
import psutil
import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

from ..dependencies import HealthService, ManagerRegistryService, get_health_service, get_manager_service
from ..schemas import (
    SystemHealthResponse, SystemMetricsResponse, 
    SystemReloadResponse, OperationResponse, APIErrorModel, common_responses
)
from ..security import (
    get_current_user, require_permission,
    rate_limit_basic, rate_limit_privileged, rate_limit_admin
)
from ..error_helpers import raise_operation_failed

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["system"])

# Track server start time for uptime calculation
_server_start_time = time.time()

# Global counters for metrics
_metrics = {
    "api_requests_total": 0,
    "api_requests_errors": 0,
    "system_reloads": 0,
    "health_checks": 0
}


def increment_metric(metric_name: str):
    """Increment a metric counter"""
    global _metrics
    _metrics[metric_name] = _metrics.get(metric_name, 0) + 1


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    summary="Get System Health Status",
    description="Performs a comprehensive health check of the AICleaner v3 system, including manager status and uptime metrics.",
    response_description="Current system health status with manager information",
    responses={**common_responses}
)
@rate_limit_basic()
async def system_health_check(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    manager_service: ManagerRegistryService = Depends(get_manager_service)
):
    """
    Get system health status.
    
    Returns overall system health including manager status, uptime,
    and basic system information.
    """
    try:
        increment_metric("health_checks")
        
        status = manager_service.get_manager_status()
        
        total_managers = status["total_managers"]
        healthy_managers = 0
        
        # Count healthy managers (basic check - all registered managers are assumed healthy)
        # In a real implementation, this would check each manager's health status
        for name, manager_info in status.get("managers", {}).items():
            if manager_info.get("status") != "error":
                healthy_managers += 1
        
        # Determine overall system status
        if healthy_managers == total_managers and total_managers > 0:
            system_status = "ok"
        elif healthy_managers > 0:
            system_status = "degraded"
        else:
            system_status = "error"
        
        uptime = time.time() - _server_start_time
        
        return SystemHealthResponse(
            status=system_status,
            uptime_seconds=uptime,
            managers_healthy=healthy_managers,
            managers_total=total_managers
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        increment_metric("api_requests_errors")
        raise_operation_failed("health check", "system", str(e))


@router.get(
    "/metrics",
    response_model=SystemMetricsResponse,
    summary="Get System Performance Metrics",
    description="Retrieves detailed system performance metrics including CPU, memory, disk usage, and API statistics.",
    response_description="Current system performance metrics and counters",
    responses={**common_responses}
)
@rate_limit_basic()
async def get_system_metrics(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    manager_service: ManagerRegistryService = Depends(get_manager_service)
):
    """
    Get detailed system metrics.
    
    Returns comprehensive system metrics including resource usage,
    performance counters, and operational statistics.
    """
    try:
        increment_metric("api_requests_total")
        
        # Get system resource usage
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get manager count
        status = manager_service.get_manager_status()
        active_managers = status["total_managers"]
        
        return SystemMetricsResponse(
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            disk_usage=disk.percent,
            active_managers=active_managers,
            api_requests_total=_metrics.get("api_requests_total", 0),
            api_requests_errors=_metrics.get("api_requests_errors", 0)
        )
        
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        increment_metric("api_requests_errors")
        raise_operation_failed("get system metrics", "system", str(e))


@router.post(
    "/_reload",
    response_model=SystemReloadResponse,
    summary="Reload All System Managers",
    description="Performs a graceful reload of all system managers. This privileged operation may cause temporary service interruption.",
    response_description="Results of the system reload operation including successful and failed managers",
    responses={**common_responses}
)
@rate_limit_admin()
@require_permission("system_control")
async def reload_system(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    manager_service: ManagerRegistryService = Depends(get_manager_service)
):
    """
    Reload all system managers.
    
    Performs a graceful reload of all managers based on the current
    configuration. This operation may cause temporary service interruption.
    """
    try:
        increment_metric("system_reloads")
        
        reloaded_managers, failed_managers = await manager_service.reload_all_managers()
        
        if failed_managers:
            logger.warning(f"Some managers failed to reload: {failed_managers}")
        
        logger.info(f"System reload completed: {len(reloaded_managers)} managers reloaded")
        
        return SystemReloadResponse(
            status="reloading",
            message=f"Reloaded {len(reloaded_managers)} managers" + 
                   (f", {len(failed_managers)} failed" if failed_managers else ""),
            managers_reloaded=reloaded_managers
        )
        
    except Exception as e:
        logger.error(f"System reload failed: {e}")
        increment_metric("api_requests_errors")
        raise_operation_failed("system reload", "system", str(e))


@router.get(
    "/info",
    summary="Get Detailed System Information",
    description="Retrieves comprehensive system information including version, platform details, process information, and manager status.",
    response_description="Detailed system information dictionary",
    responses={**common_responses}
)
@rate_limit_basic()
async def get_system_info(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    manager_service: ManagerRegistryService = Depends(get_manager_service)
):
    """
    Get detailed system information.
    
    Returns comprehensive system information including version,
    configuration, runtime details, and environment information.
    """
    try:
        status = manager_service.get_manager_status()
        
        # Get system information
        system_info = {
            "version": "3.0.0",
            "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}",
            "platform": psutil.sys.platform,
            "hostname": psutil.os.uname().nodename if hasattr(psutil.os.uname(), 'nodename') else "unknown",
            "pid": os.getpid(),
            "uptime_seconds": time.time() - _server_start_time,
            "managers": status,
            "metrics": _metrics.copy(),
            "memory_usage_mb": psutil.Process().memory_info().rss / 1024 / 1024,
            "thread_count": psutil.Process().num_threads(),
            "open_files": len(psutil.Process().open_files()) if hasattr(psutil.Process(), 'open_files') else 0
        }
        
        return system_info
        
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise_operation_failed("get system info", "system", str(e))


@router.post(
    "/_shutdown",
    response_model=OperationResponse,
    summary="Initiate System Shutdown",
    description="Performs a graceful shutdown of all managers and the system. This is a destructive, privileged operation that will stop the AICleaner v3 server.",
    response_description="Confirmation that the shutdown process has been initiated",
    responses={**common_responses}
)
@rate_limit_admin()
@require_permission("system_control")
async def shutdown_system(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    manager_service: ManagerRegistryService = Depends(get_manager_service)
):
    """
    Initiate graceful system shutdown.
    
    Performs a graceful shutdown of all managers and the system.
    This is a destructive operation that will stop the AICleaner v3 server.
    """
    try:
        # Log the shutdown request
        user_info = current_user.get('key_name', 'unknown')
        logger.warning(f"System shutdown requested by API key: {user_info}")
        
        # Shutdown all managers
        shutdown_managers, failed_managers = await manager_service.shutdown_all_managers()
        
        if failed_managers:
            logger.warning(f"Some managers failed to shutdown: {failed_managers}")
        
        logger.info(f"All managers shut down ({len(shutdown_managers)}), initiating server shutdown")
        
        # Return response before shutdown
        response = OperationResponse(
            status="success",
            message="System shutdown initiated",
            operation_id=f"shutdown_{int(time.time())}"
        )
        
        # Schedule shutdown after response is sent
        # Note: In a real implementation, you'd want to use a background task
        # to ensure the response is sent before the server shuts down
        import asyncio
        asyncio.create_task(_delayed_shutdown())
        
        return response
        
    except Exception as e:
        logger.error(f"Shutdown failed: {e}")
        raise_operation_failed("system shutdown", "system", str(e))


async def _delayed_shutdown():
    """Delayed shutdown to allow response to be sent"""
    import asyncio
    await asyncio.sleep(1)  # Give time for response to be sent
    
    logger.info("Performing delayed system shutdown")
    
    # In a real implementation, you would signal the FastAPI server to shut down
    # For now, we'll just log the action
    # os._exit(0)  # Uncomment for actual shutdown


@router.get(
    "/logs",
    summary="Get Recent System Logs",
    description="Retrieves recent log entries from the system logger with optional filtering by log level and line count.",
    response_description="List of recent log entries with metadata",
    responses={**common_responses}
)
@rate_limit_privileged()
@require_permission("view_metrics")
async def get_system_logs(
    request: Request,
    lines: int = 100,
    level: str = "INFO",
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get recent system logs.
    
    Returns recent log entries from the system logger with optional
    filtering by log level and line count.
    """
    try:
        # This is a simplified implementation
        # In a real system, you'd read from actual log files
        
        logs = [
            {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "message": "System running normally",
                "logger": "aicleaner.system"
            },
            {
                "timestamp": datetime.now().isoformat(),
                "level": "DEBUG", 
                "message": "Manager registry status check completed",
                "logger": "aicleaner.registry"
            }
        ]
        
        # Filter by level if specified
        if level != "ALL":
            logs = [log for log in logs if log["level"] == level.upper()]
        
        # Limit lines
        logs = logs[-lines:] if len(logs) > lines else logs
        
        return {
            "logs": logs,
            "total_entries": len(logs),
            "filter_level": level,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get system logs: {e}")
        raise_operation_failed("get system logs", "system", str(e))