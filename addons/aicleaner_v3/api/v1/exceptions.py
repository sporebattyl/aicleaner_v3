"""
Custom API exceptions for AICleaner v3 Developer API v1
"""

from typing import Dict, Any, Optional


class APIError(Exception):
    """Base exception for API errors with enhanced context"""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500,
        error_code: Optional[str] = None,
        error_category: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__.upper()
        self.error_category = error_category or "SERVER_ERROR"
        self.details = details or {}


class NotFoundError(APIError):
    """Resource not found error (404)"""
    
    def __init__(
        self, 
        message: str = "Resource not found", 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=404,
            error_code=error_code or "RESOURCE_NOT_FOUND",
            error_category="CLIENT_ERROR",
            details=details
        )


class BadRequestError(APIError):
    """Invalid request error (400)"""
    
    def __init__(
        self, 
        message: str = "Invalid request", 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code=error_code or "INVALID_REQUEST",
            error_category="CLIENT_ERROR",
            details=details
        )


class ValidationError(APIError):
    """Validation error (422)"""
    
    def __init__(
        self, 
        message: str = "Validation failed", 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=422,
            error_code=error_code or "VALIDATION_FAILED",
            error_category="CLIENT_ERROR",
            details=details
        )


class UnauthorizedError(APIError):
    """Authentication required error (401)"""
    
    def __init__(
        self, 
        message: str = "Authentication required", 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code=error_code or "AUTHENTICATION_REQUIRED",
            error_category="AUTHENTICATION_ERROR",
            details=details
        )


class ForbiddenError(APIError):
    """Insufficient permissions error (403)"""
    
    def __init__(
        self, 
        message: str = "Insufficient permissions", 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code=error_code or "INSUFFICIENT_PERMISSIONS",
            error_category="AUTHORIZATION_ERROR",
            details=details
        )


class ConflictError(APIError):
    """Resource conflict error (409)"""
    
    def __init__(
        self, 
        message: str = "Resource conflict", 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=409,
            error_code=error_code or "RESOURCE_CONFLICT",
            error_category="CLIENT_ERROR",
            details=details
        )


class InternalServerError(APIError):
    """Internal server error (500)"""
    
    def __init__(
        self, 
        message: str = "Internal server error", 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=500,
            error_code=error_code or "INTERNAL_SERVER_ERROR",
            error_category="SERVER_ERROR",
            details=details
        )


class ServiceUnavailableError(APIError):
    """Service unavailable error (503)"""
    
    def __init__(
        self, 
        message: str = "Service temporarily unavailable", 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=503,
            error_code=error_code or "SERVICE_UNAVAILABLE",
            error_category="SERVER_ERROR",
            details=details
        )


class ManagerNotFoundError(NotFoundError):
    """Manager not found error"""
    
    def __init__(
        self, 
        manager_name: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Manager '{manager_name}' not found",
            error_code="MANAGER_NOT_FOUND",
            details={"manager_name": manager_name, **(details or {})}
        )


class ConfigurationError(BadRequestError):
    """Configuration error"""
    
    def __init__(
        self, 
        message: str = "Configuration error", 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code or "CONFIGURATION_ERROR",
            details=details
        )