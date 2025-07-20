"""
Main API router for AICleaner v3 Developer API v1
"""

import logging
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from .endpoints import managers, system, config
from .security import (
    limiter, rate_limit_handler, audit_logger,
    get_current_user, api_key_manager
)
from .schemas import APIErrorModel, AuthenticationResponse, EnhancedAPIErrorModel
from .exceptions import (
    APIError, NotFoundError, BadRequestError, ValidationError,
    UnauthorizedError, ForbiddenError, ConflictError, 
    InternalServerError, ServiceUnavailableError
)

logger = logging.getLogger(__name__)

# Create main API router
api_router = APIRouter(prefix="/api/v1", tags=["api_v1"])

# Include endpoint routers
api_router.include_router(managers.router)
api_router.include_router(system.router)
api_router.include_router(config.router)


@api_router.get("/", include_in_schema=False)
async def api_root():
    """API root endpoint with basic information"""
    return {
        "name": "AICleaner v3 Developer API",
        "version": "1.0.0",
        "description": "RESTful API for programmatic control of AICleaner v3",
        "timestamp": datetime.now().isoformat(),
        "documentation": "/docs",
        "endpoints": {
            "managers": "/api/v1/managers",
            "system": "/api/v1/system", 
            "config": "/api/v1/config",
            "auth": "/api/v1/auth"
        }
    }


@api_router.get("/auth/check", response_model=AuthenticationResponse)
async def check_authentication(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Check authentication status and permissions.
    
    Validates the provided API key and returns authentication status
    along with associated permissions and rate limit information.
    """
    try:
        permissions = current_user.get('permissions')
        key_name = current_user.get('key_name')
        
        return AuthenticationResponse(
            authenticated=True,
            key_id=key_name,
            permissions=permissions,
            rate_limit_remaining=None  # Would need rate limiter integration
        )
        
    except Exception as e:
        logger.error(f"Authentication check failed: {e}")
        raise HTTPException(status_code=500, detail="Authentication check failed")


@api_router.get("/auth/permissions")
async def get_permissions(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Get detailed permissions for the current API key.
    
    Returns comprehensive permission information including
    specific capabilities and access levels.
    """
    try:
        permissions = current_user.get('permissions')
        key_config = current_user.get('key_config', {})
        
        return {
            "permissions": permissions.dict() if permissions else {},
            "key_name": current_user.get('key_name'),
            "created_at": key_config.get('created_at'),
            "rate_limit": key_config.get('rate_limit', 'default'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get permissions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get permissions")


# Exception handlers
@api_router.exception_handler(RateLimitExceeded)
async def api_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded exceptions"""
    return await rate_limit_handler(request, exc)


@api_router.exception_handler(HTTPException)
async def api_http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with standardized error format"""
    
    # Log the error for audit purposes
    audit_logger.log_request(
        request, 
        None,  # Would need to extract key_id from request context
        False, 
        f"HTTP {exc.status_code}: {exc.detail}"
    )
    
    error_response = APIErrorModel(
        error=exc.detail,
        detail=getattr(exc, 'detail', None),
        code=str(exc.status_code)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )


@api_router.exception_handler(Exception)
async def api_general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with standardized error format"""
    
    logger.error(f"Unhandled exception in API: {exc}", exc_info=True)
    
    # Log the error for audit purposes
    audit_logger.log_request(
        request,
        None,
        False,
        f"Internal error: {str(exc)[:100]}"
    )
    
    error_response = APIErrorModel(
        error="Internal server error",
        detail="An unexpected error occurred",
        code="500"
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.dict()
    )


# Request ID Middleware
async def add_request_id_middleware(request: Request, call_next):
    """Add unique request ID to each request for error tracing"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Enhanced Exception Handlers
def create_enhanced_error_response(
    request: Request,
    exception: APIError,
    request_id: Optional[str] = None
) -> JSONResponse:
    """Create standardized error response using EnhancedAPIErrorModel"""
    return JSONResponse(
        status_code=exception.status_code,
        content=EnhancedAPIErrorModel(
            message=exception.message,
            error_code=exception.error_code,
            error_category=exception.error_category,
            request_id=request_id or getattr(request.state, 'request_id', None),
            path=str(request.url.path),
            details=exception.details
        ).dict()
    )


def register_exception_handlers(app):
    """Register all custom exception handlers with the FastAPI app"""
    
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        """Handle custom API errors"""
        request_id = getattr(request.state, 'request_id', None)
        
        # Log error with context
        logger.error(
            f"API Error [{request_id}]: {exc.error_code} - {exc.message}",
            extra={
                "request_id": request_id,
                "error_code": exc.error_code,
                "error_category": exc.error_category,
                "path": request.url.path,
                "method": request.method,
                "details": exc.details
            },
            exc_info=True
        )
        
        return create_enhanced_error_response(request, exc, request_id)
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle FastAPI HTTPExceptions and convert to enhanced format"""
        request_id = getattr(request.state, 'request_id', None)
        
        # Convert HTTPException to APIError format
        api_error = APIError(
            message=str(exc.detail),
            status_code=exc.status_code,
            error_code=f"HTTP_{exc.status_code}",
            error_category="CLIENT_ERROR" if 400 <= exc.status_code < 500 else "SERVER_ERROR"
        )
        
        # Log the error
        logger.warning(
            f"HTTP Exception [{request_id}]: {exc.status_code} - {exc.detail}",
            extra={
                "request_id": request_id,
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return create_enhanced_error_response(request, api_error, request_id)
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions"""
        request_id = getattr(request.state, 'request_id', None)
        
        # Log the unexpected error with full traceback
        logger.critical(
            f"Unexpected Exception [{request_id}]: {type(exc).__name__} - {str(exc)}",
            extra={
                "request_id": request_id,
                "exception_type": type(exc).__name__,
                "path": request.url.path,
                "method": request.method
            },
            exc_info=True
        )
        
        # Create generic internal server error
        api_error = InternalServerError(
            message="An unexpected error occurred",
            error_code="UNEXPECTED_ERROR",
            details={"exception_type": type(exc).__name__}
        )
        
        return create_enhanced_error_response(request, api_error, request_id)


# Middleware to add rate limiter to app
def add_rate_limiter_to_app(app):
    """Add the rate limiter to the FastAPI app"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)


# Enhanced middleware setup
def add_enhanced_middleware_to_app(app):
    """Add enhanced middleware including request ID and exception handlers"""
    # Add request ID middleware
    app.middleware("http")(add_request_id_middleware)
    
    # Register exception handlers
    register_exception_handlers(app)


# Health check for the API specifically
@api_router.get("/health", include_in_schema=False)
async def api_health():
    """Quick health check for the API itself"""
    return {
        "status": "healthy",
        "api_version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }