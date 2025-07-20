"""
Manager control endpoints for AICleaner v3 Developer API v1
"""

import time
import logging
from typing import Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

from utils.manager_registry import ManagerNames
from ..dependencies import ManagerRegistryService, get_manager_service
from ..error_helpers import raise_manager_not_found, raise_operation_failed
from ..schemas import (
    ManagerListResponse, ManagerDetails, ManagerStatus, 
    ManagerConfigRequest, ManagerConfigResponse, OperationResponse,
    BulkManagerOperation, BulkManagerResponse, APIErrorModel,
    common_responses
)
from ..security import (
    get_current_user, require_permission, 
    rate_limit_basic, rate_limit_privileged, rate_limit_admin
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/managers", tags=["managers"])


@router.get(
    "",
    response_model=ManagerListResponse,
    summary="List All Managers",
    description="Retrieves a comprehensive list of all registered managers in the system, including their current status, type, and basic health information. This endpoint is essential for monitoring the overall state of the AICleaner instance.",
    response_description="A list of all registered managers and their status.",
    responses={**common_responses}
)
@rate_limit_basic()
async def list_managers(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    manager_service: ManagerRegistryService = Depends(get_manager_service)
):
    try:
        status = manager_service.get_manager_status()
        
        managers = []
        for name, manager_info in status.get("managers", {}).items():
            uptime = None
            if manager_info.get("creation_time") != "unknown":
                uptime = time.time() - float(manager_info["creation_time"])
            
            manager_status = ManagerStatus(
                name=name,
                type=manager_info["type"],
                status="running",  # Default - would need health check integration
                memory_address=manager_info["memory_address"],
                creation_time=float(manager_info.get("creation_time", 0)),
                uptime_seconds=uptime,
                configurable=manager_info.get("configurable", False),
                health_monitoring=manager_info.get("health_monitoring", False)
            )
            managers.append(manager_status)
        
        return ManagerListResponse(
            total_managers=status["total_managers"],
            managers=managers,
            registry_status="healthy"
        )
        
    except Exception as e:
        logger.error(f"Failed to list managers: {e}")
        raise_operation_failed("list", "managers", str(e))


@router.get(
    "/{manager_name}", 
    response_model=ManagerDetails,
    summary="Get Manager Details",
    description="Retrieves comprehensive details for a specific manager, including configuration, health status, and performance metrics.",
    response_description="Detailed information about the specified manager.",
    responses={**common_responses}
)
@rate_limit_basic()
async def get_manager_details(
    manager_name: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    manager_service: ManagerRegistryService = Depends(get_manager_service)
):
    try:
        manager = manager_service.get_manager(manager_name)
        if not manager:
            raise_manager_not_found(manager_name)
        
        # Get manager info from registry status
        status = manager_service.get_manager_status()
        manager_info = status.get("managers", {}).get(manager_name, {})
        
        if not manager_info:
            raise_manager_not_found(manager_name)
        
        # Calculate uptime
        uptime = None
        if manager_info.get("creation_time") != "unknown":
            uptime = time.time() - float(manager_info["creation_time"])
        
        # Get configuration if available
        configuration = None
        if hasattr(manager, 'get_config'):
            try:
                configuration = manager.get_config()
            except Exception as e:
                logger.warning(f"Failed to get config for {manager_name}: {e}")
        
        # Get health status if available
        health_status = None
        if hasattr(manager, 'get_health'):
            try:
                health_status = manager.get_health()
            except Exception as e:
                logger.warning(f"Failed to get health for {manager_name}: {e}")
        
        # Get capabilities
        capabilities = []
        for method in ['get_config', 'set_config', 'get_health', 'restart', 'shutdown']:
            if hasattr(manager, method):
                capabilities.append(method)
        
        return ManagerDetails(
            name=manager_name,
            type=manager_info["type"],
            module=manager_info["module"],
            status="running",
            memory_address=manager_info["memory_address"],
            creation_time=float(manager_info.get("creation_time", 0)),
            uptime_seconds=uptime,
            configuration=configuration,
            health_status=health_status,
            capabilities=capabilities,
            performance_metrics=manager_info.get("status")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get details for manager {manager_name}: {e}")
        raise_operation_failed("get details for", f"manager '{manager_name}'", str(e))


@router.post(
    "/{manager_name}/_restart", 
    response_model=OperationResponse,
    summary="Restart a Manager",
    description="Gracefully stops and restarts the specified manager. This operation may cause temporary service interruption for the manager's functionality.",
    response_description="Confirmation of the restart operation.",
    responses={**common_responses}
)
@rate_limit_privileged()
@require_permission("control_managers")
async def restart_manager(
    manager_name: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    manager_service: ManagerRegistryService = Depends(get_manager_service)
):
    try:
        manager = manager_service.get_manager(manager_name)
        if not manager:
            raise_manager_not_found(manager_name)
        
        # Check if manager supports restart
        if not hasattr(manager, 'restart') and not hasattr(manager, 'shutdown'):
            raise HTTPException(
                status_code=400, 
                detail=f"Manager '{manager_name}' does not support restart operations"
            )
        
        # Attempt to restart
        try:
            if hasattr(manager, 'restart'):
                await manager.restart() if hasattr(manager.restart, '__await__') else manager.restart()
            else:
                # Fallback: shutdown and re-create
                if hasattr(manager, 'shutdown'):
                    await manager.shutdown() if hasattr(manager.shutdown, '__await__') else manager.shutdown()
                
                # Remove from registry and let it be recreated on next access
                manager_service.unregister_manager(manager_name)
            
            logger.info(f"Successfully restarted manager: {manager_name}")
            return OperationResponse(
                status="success",
                message=f"Manager '{manager_name}' restarted successfully",
                operation_id=f"restart_{manager_name}_{int(time.time())}"
            )
            
        except Exception as e:
            logger.error(f"Failed to restart manager {manager_name}: {e}")
            raise_operation_failed("restart", f"manager '{manager_name}'", str(e))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in restart_manager for {manager_name}: {e}")
        raise_operation_failed("restart", f"manager '{manager_name}'", str(e))


@router.get(
    "/{manager_name}/config",
    summary="Get Manager Configuration",
    description="Retrieves the current configuration for a specific manager, if the manager supports configuration access.",
    response_description="The current configuration of the manager.",
    responses={**common_responses}
)
@rate_limit_basic()
async def get_manager_config(
    manager_name: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    manager_service: ManagerRegistryService = Depends(get_manager_service)
):
    try:
        manager = manager_service.get_manager(manager_name)
        if not manager:
            raise_manager_not_found(manager_name)
        
        if not hasattr(manager, 'get_config'):
            raise HTTPException(
                status_code=400, 
                detail=f"Manager '{manager_name}' does not support configuration access"
            )
        
        try:
            config = manager.get_config()
            return {
                "config": config, 
                "manager": manager_name, 
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get config for {manager_name}: {e}")
            raise_operation_failed("get config for", f"manager '{manager_name}'", str(e))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_manager_config for {manager_name}: {e}")
        raise_operation_failed("get config for", f"manager '{manager_name}'", str(e))


@router.put(
    "/{manager_name}/config", 
    response_model=ManagerConfigResponse,
    summary="Update Manager Configuration",
    description="Updates the manager's configuration and optionally restarts it to apply the new settings. Supports a dry-run validation mode.",
    response_description="The result of the configuration update operation.",
    responses={**common_responses}
)
@rate_limit_privileged()
@require_permission("write_config")
async def update_manager_config(
    manager_name: str,
    config_request: ManagerConfigRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    manager_service: ManagerRegistryService = Depends(get_manager_service)
):
    try:
        manager = manager_service.get_manager(manager_name)
        if not manager:
            raise_manager_not_found(manager_name)
        
        if not hasattr(manager, 'set_config') and not hasattr(manager, 'update_config'):
            raise HTTPException(
                status_code=400, 
                detail=f"Manager '{manager_name}' does not support configuration updates"
            )
        
        validation_errors = []
        
        # Validate configuration if supported
        if hasattr(manager, 'validate_config'):
            try:
                is_valid = manager.validate_config(config_request.config)
                if not is_valid:
                    if hasattr(manager, 'get_validation_errors'):
                        validation_errors = manager.get_validation_errors()
                    else:
                        validation_errors = ["Configuration validation failed"]
            except Exception as e:
                validation_errors = [f"Validation error: {str(e)}"]
        
        # If validation only, return results
        if config_request.validate_only:
            return ManagerConfigResponse(
                status="validated" if not validation_errors else "invalid",
                message="Configuration validation completed",
                config=config_request.config,
                validation_errors=validation_errors
            )
        
        # If validation failed and not validate_only, abort
        if validation_errors:
            raise HTTPException(
                status_code=400, 
                detail=f"Configuration validation failed: {'; '.join(validation_errors)}"
            )
        
        # Apply configuration
        try:
            if hasattr(manager, 'set_config'):
                manager.set_config(config_request.config)
            elif hasattr(manager, 'update_config'):
                manager.update_config(config_request.config)
            
            # Restart manager if requested
            if config_request.restart_manager and hasattr(manager, 'restart'):
                await manager.restart() if hasattr(manager.restart, '__await__') else manager.restart()
            
            logger.info(f"Updated configuration for manager: {manager_name}")
            return ManagerConfigResponse(
                status="success",
                message=f"Configuration updated for '{manager_name}'",
                config=config_request.config,
                validation_errors=[]
            )
            
        except Exception as e:
            logger.error(f"Failed to update config for {manager_name}: {e}")
            raise_operation_failed("update config for", f"manager '{manager_name}'", str(e))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_manager_config for {manager_name}: {e}")
        raise_operation_failed("update config for", f"manager '{manager_name}'", str(e))


@router.post(
    "/_bulk", 
    response_model=BulkManagerResponse,
    summary="Bulk Manager Operation",
    description="Performs a single operation (e.g., restart, stop) on multiple managers at once. Use with caution.",
    response_description="A report detailing which operations succeeded and which failed.",
    responses={**common_responses}
)
@rate_limit_admin()
@require_permission("control_managers")
async def bulk_manager_operation(
    operation_request: BulkManagerOperation,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    manager_service: ManagerRegistryService = Depends(get_manager_service)
):
    try:
        successful = []
        failed = []
        
        for manager_name in operation_request.managers:
            try:
                manager = manager_service.get_manager(manager_name)
                if not manager:
                    failed.append({"manager": manager_name, "error": "Manager not found"})
                    continue
                
                # Perform the requested operation
                if operation_request.operation == "restart":
                    if hasattr(manager, 'restart'):
                        await manager.restart() if hasattr(manager.restart, '__await__') else manager.restart()
                        successful.append(manager_name)
                    else:
                        failed.append({"manager": manager_name, "error": "Restart not supported"})
                
                elif operation_request.operation == "stop":
                    if hasattr(manager, 'shutdown'):
                        await manager.shutdown() if hasattr(manager.shutdown, '__await__') else manager.shutdown()
                        successful.append(manager_name)
                    else:
                        failed.append({"manager": manager_name, "error": "Stop not supported"})
                
                elif operation_request.operation == "reload_config":
                    if hasattr(manager, 'reload_config'):
                        await manager.reload_config() if hasattr(manager.reload_config, '__await__') else manager.reload_config()
                        successful.append(manager_name)
                    else:
                        failed.append({"manager": manager_name, "error": "Config reload not supported"})
                
                else:
                    failed.append({"manager": manager_name, "error": f"Unknown operation: {operation_request.operation}"})
                
            except Exception as e:
                error_msg = str(e) if not operation_request.force else f"Error (forced): {str(e)}"
                failed.append({"manager": manager_name, "error": error_msg})
                if not operation_request.force:
                    break  # Stop on first error unless force=True
        
        status = "success" if not failed else ("partial" if successful else "failed")
        
        logger.info(f"Bulk operation '{operation_request.operation}' completed: {len(successful)} successful, {len(failed)} failed")
        
        return BulkManagerResponse(
            status=status,
            total_requested=len(operation_request.managers),
            successful=successful,
            failed=failed
        )
        
    except Exception as e:
        logger.error(f"Error in bulk_manager_operation: {e}")
        raise_operation_failed("bulk operation", "managers", str(e))