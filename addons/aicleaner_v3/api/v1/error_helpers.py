"""
Error helper functions for AICleaner v3 Developer API v1
"""

from datetime import datetime
from typing import Dict, Any, Optional
from .exceptions import (
    APIError, NotFoundError, BadRequestError, ValidationError,
    UnauthorizedError, ForbiddenError, ConflictError, 
    InternalServerError, ServiceUnavailableError,
    ManagerNotFoundError, ConfigurationError
)


def raise_manager_not_found(manager_name: str) -> None:
    """Raise a standardized manager not found error"""
    raise ManagerNotFoundError(manager_name)


def raise_config_validation_error(errors: list, details: Optional[Dict[str, Any]] = None) -> None:
    """Raise a configuration validation error"""
    error_details = {"validation_errors": errors}
    if details:
        error_details.update(details)
    
    raise ConfigurationError(
        message=f"Configuration validation failed: {'; '.join(errors)}",
        error_code="CONFIG_VALIDATION_FAILED",
        details=error_details
    )


def raise_service_unavailable(service_name: str, reason: Optional[str] = None) -> None:
    """Raise a service unavailable error"""
    message = f"Service '{service_name}' is currently unavailable"
    if reason:
        message += f": {reason}"
    
    raise ServiceUnavailableError(
        message=message,
        error_code="SERVICE_UNAVAILABLE",
        details={"service_name": service_name, "reason": reason}
    )


def raise_permission_denied(permission: str, resource: Optional[str] = None) -> None:
    """Raise a permission denied error"""
    message = f"Permission '{permission}' required"
    if resource:
        message += f" for resource '{resource}'"
    
    raise ForbiddenError(
        message=message,
        error_code="PERMISSION_DENIED",
        details={"required_permission": permission, "resource": resource}
    )


def raise_invalid_input(field: str, value: Any, reason: str) -> None:
    """Raise an invalid input error"""
    raise BadRequestError(
        message=f"Invalid value for field '{field}': {reason}",
        error_code="INVALID_INPUT",
        details={"field": field, "value": str(value), "reason": reason}
    )


def raise_resource_conflict(resource_type: str, identifier: str, reason: str) -> None:
    """Raise a resource conflict error"""
    raise ConflictError(
        message=f"{resource_type} '{identifier}' conflict: {reason}",
        error_code="RESOURCE_CONFLICT",
        details={"resource_type": resource_type, "identifier": identifier, "reason": reason}
    )


def raise_operation_failed(operation: str, target: str, reason: str) -> None:
    """Raise an operation failed error"""
    raise InternalServerError(
        message=f"Failed to {operation} {target}: {reason}",
        error_code="OPERATION_FAILED",
        details={"operation": operation, "target": target, "reason": reason}
    )


def wrap_service_errors(service_name: str):
    """Decorator to wrap service errors in API errors"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except APIError:
                # Re-raise API errors unchanged
                raise
            except KeyError as e:
                # Convert KeyError to NotFoundError
                raise NotFoundError(
                    message=f"Resource not found in {service_name}",
                    error_code="RESOURCE_NOT_FOUND",
                    details={"service": service_name, "key": str(e)}
                )
            except ValueError as e:
                # Convert ValueError to BadRequestError
                raise BadRequestError(
                    message=f"Invalid value in {service_name}: {str(e)}",
                    error_code="INVALID_VALUE",
                    details={"service": service_name, "error": str(e)}
                )
            except Exception as e:
                # Convert unexpected errors to InternalServerError
                raise InternalServerError(
                    message=f"Unexpected error in {service_name}",
                    error_code="UNEXPECTED_SERVICE_ERROR",
                    details={"service": service_name, "error": str(e), "error_type": type(e).__name__}
                )
        return wrapper
    return decorator


def create_error_context(operation: str, resource: str, **kwargs) -> Dict[str, Any]:
    """Create error context dictionary for detailed error reporting"""
    context = {
        "operation": operation,
        "resource": resource,
        "timestamp": str(datetime.now())
    }
    context.update(kwargs)
    return context