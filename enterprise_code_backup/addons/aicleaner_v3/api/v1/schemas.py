"""
Pydantic models for AICleaner v3 Developer API v1
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field
from http import HTTPStatus


class APIErrorDetail(BaseModel):
    """Detailed error information"""
    field: Optional[str] = None
    message: str
    code: str


class APIErrorModel(BaseModel):
    """Enhanced standardized API error response"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[List[APIErrorDetail]] = None  # Add structured details


class EnhancedAPIErrorModel(BaseModel):
    """Comprehensive API error response with full context"""
    message: str
    error_code: Optional[str] = None
    error_category: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    path: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ManagerStatus(BaseModel):
    """Manager status information"""
    name: str
    type: str
    status: str = Field(..., description="running, stopped, error, restarting")
    memory_address: str
    creation_time: float
    uptime_seconds: Optional[float] = None
    health_status: Optional[str] = None
    configurable: bool = False
    health_monitoring: bool = False


class ManagerDetails(BaseModel):
    """Detailed manager information"""
    name: str
    type: str
    module: str
    status: str
    memory_address: str
    creation_time: float
    uptime_seconds: Optional[float] = None
    configuration: Optional[Dict[str, Any]] = None
    health_status: Optional[Dict[str, Any]] = None
    capabilities: List[str] = []
    performance_metrics: Optional[Dict[str, Any]] = None


class ManagerListResponse(BaseModel):
    """Response for listing all managers"""
    total_managers: int
    managers: List[ManagerStatus]
    registry_status: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ManagerConfigRequest(BaseModel):
    """Request model for updating manager configuration"""
    config: Dict[str, Any]
    validate_only: bool = False
    restart_manager: bool = True


class ManagerConfigResponse(BaseModel):
    """Response for manager configuration operations"""
    status: str
    message: str
    config: Optional[Dict[str, Any]] = None
    validation_errors: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.now)


class SystemHealthResponse(BaseModel):
    """System health check response"""
    status: str = Field(..., description="ok, degraded, error")
    version: str = "3.0.0"
    uptime_seconds: float
    managers_healthy: int
    managers_total: int
    timestamp: datetime = Field(default_factory=datetime.now)


class SystemMetricsResponse(BaseModel):
    """System metrics response"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_managers: int
    api_requests_total: int
    api_requests_errors: int
    timestamp: datetime = Field(default_factory=datetime.now)


class SystemReloadResponse(BaseModel):
    """System reload operation response"""
    status: str = "reloading"
    message: str
    managers_reloaded: List[str]
    timestamp: datetime = Field(default_factory=datetime.now)


class ConfigValidationRequest(BaseModel):
    """Configuration validation request"""
    config: Dict[str, Any]
    strict: bool = True


class ConfigValidationResponse(BaseModel):
    """Configuration validation response"""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    security_impact: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ConfigUpdateRequest(BaseModel):
    """Configuration update request"""
    config: Dict[str, Any]
    backup_current: bool = True
    validate_first: bool = True


class ConfigUpdateResponse(BaseModel):
    """Configuration update response"""
    status: str
    message: str
    backup_location: Optional[str] = None
    validation_results: Optional[ConfigValidationResponse] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class APIKeyPermissions(BaseModel):
    """API key permissions model"""
    read_config: bool = True
    write_config: bool = False
    control_managers: bool = False
    system_control: bool = False
    view_metrics: bool = True


class AuthenticationResponse(BaseModel):
    """Authentication check response"""
    authenticated: bool
    key_id: Optional[str] = None
    permissions: Optional[APIKeyPermissions] = None
    rate_limit_remaining: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class OperationResponse(BaseModel):
    """Generic operation response"""
    status: str = Field(..., description="success, error, pending")
    message: str
    operation_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class BulkManagerOperation(BaseModel):
    """Bulk manager operation request"""
    managers: List[str]
    operation: str = Field(..., description="restart, stop, start, reload_config")
    force: bool = False


class BulkManagerResponse(BaseModel):
    """Bulk manager operation response"""
    status: str
    total_requested: int
    successful: List[str]
    failed: List[Dict[str, str]]  # [{"manager": "name", "error": "reason"}]
    timestamp: datetime = Field(default_factory=datetime.now)


# Common OpenAPI response definitions for all endpoints
common_responses = {
    HTTPStatus.BAD_REQUEST.value: {
        "model": EnhancedAPIErrorModel,
        "description": "Bad Request - Invalid input or parameters.",
    },
    HTTPStatus.UNAUTHORIZED.value: {
        "model": EnhancedAPIErrorModel,
        "description": "Unauthorized - Authentication required or failed.",
    },
    HTTPStatus.FORBIDDEN.value: {
        "model": EnhancedAPIErrorModel,
        "description": "Forbidden - Insufficient permissions.",
    },
    HTTPStatus.NOT_FOUND.value: {
        "model": EnhancedAPIErrorModel,
        "description": "Not Found - Resource not found.",
    },
    HTTPStatus.INTERNAL_SERVER_ERROR.value: {
        "model": EnhancedAPIErrorModel,
        "description": "Internal Server Error - Unexpected server error.",
    },
}