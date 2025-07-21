"""
Security and authentication for AICleaner v3 Developer API v1
"""

import hashlib
import secrets
import time
import logging
from typing import Dict, Any, Optional, List
from functools import wraps
from datetime import datetime, timedelta

from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from utils.configuration_manager import ConfigurationManager
from utils.manager_registry import get_manager, ManagerNames
from .schemas import APIKeyPermissions, AuthenticationResponse

logger = logging.getLogger(__name__)

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

# Security scheme
security = HTTPBearer(auto_error=False)


class APIKeyManager:
    """Manages API keys and their permissions"""
    
    def __init__(self):
        self._keys: Dict[str, Dict[str, Any]] = {}
        self._load_api_keys()
    
    def _load_api_keys(self):
        """Load API keys from configuration"""
        try:
            config_manager = get_manager(ManagerNames.CONFIGURATION.value)
            if not config_manager:
                logger.warning("ConfigurationManager not available, using default API keys")
                self._create_default_keys()
                return
            
            config = config_manager.load_configuration()
            api_config = config.get('api', {})
            keys_config = api_config.get('keys', {})
            
            if not keys_config:
                logger.info("No API keys configured, creating default keys")
                self._create_default_keys()
                return
            
            self._keys = keys_config
            logger.info(f"Loaded {len(self._keys)} API keys from configuration")
            
        except Exception as e:
            logger.error(f"Failed to load API keys: {e}")
            self._create_default_keys()
    
    def _create_default_keys(self):
        """Create default API keys for initial setup"""
        # Create a master key with full permissions
        master_key = self._generate_api_key()
        master_hash = self._hash_key(master_key)
        
        # Create a read-only key
        readonly_key = self._generate_api_key()
        readonly_hash = self._hash_key(readonly_key)
        
        self._keys = {
            master_hash: {
                "name": "master_key",
                "permissions": {
                    "read_config": True,
                    "write_config": True,
                    "control_managers": True,
                    "system_control": True,
                    "view_metrics": True
                },
                "created_at": datetime.now().isoformat(),
                "rate_limit": "100/minute"
            },
            readonly_hash: {
                "name": "readonly_key",
                "permissions": {
                    "read_config": True,
                    "write_config": False,
                    "control_managers": False,
                    "system_control": False,
                    "view_metrics": True
                },
                "created_at": datetime.now().isoformat(),
                "rate_limit": "60/minute"
            }
        }
        
        logger.warning(f"Created default API keys:")
        logger.warning(f"Master key: {master_key}")
        logger.warning(f"Read-only key: {readonly_key}")
        logger.warning("Store these keys securely and remove this log output in production!")
    
    def _generate_api_key(self) -> str:
        """Generate a new API key"""
        return f"aicv3_{secrets.token_urlsafe(32)}"
    
    def _hash_key(self, key: str) -> str:
        """Hash an API key for storage"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def validate_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Validate an API key and return its configuration"""
        if not key:
            return None
        
        key_hash = self._hash_key(key)
        return self._keys.get(key_hash)
    
    def get_permissions(self, key: str) -> Optional[APIKeyPermissions]:
        """Get permissions for an API key"""
        key_config = self.validate_key(key)
        if not key_config:
            return None
        
        permissions = key_config.get('permissions', {})
        return APIKeyPermissions(**permissions)
    
    def create_key(self, name: str, permissions: Dict[str, bool]) -> str:
        """Create a new API key"""
        new_key = self._generate_api_key()
        key_hash = self._hash_key(new_key)
        
        self._keys[key_hash] = {
            "name": name,
            "permissions": permissions,
            "created_at": datetime.now().isoformat(),
            "rate_limit": "60/minute"
        }
        
        logger.info(f"Created new API key: {name}")
        return new_key
    
    def revoke_key(self, key: str) -> bool:
        """Revoke an API key"""
        key_hash = self._hash_key(key)
        if key_hash in self._keys:
            del self._keys[key_hash]
            logger.info(f"Revoked API key")
            return True
        return False


# Global API key manager instance
api_key_manager = APIKeyManager()


class AuditLogger:
    """Audit logging for API requests"""
    
    def __init__(self):
        self.audit_logger = logging.getLogger("aicleaner.api.audit")
    
    def log_request(self, request: Request, key_id: Optional[str], success: bool, error: Optional[str] = None):
        """Log an API request for audit purposes"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "method": request.method,
            "path": str(request.url.path),
            "query_params": str(request.url.query) if request.url.query else None,
            "client_ip": get_remote_address(request),
            "key_id": key_id,
            "success": success,
            "error": error
        }
        
        if success:
            self.audit_logger.info(f"API_REQUEST {log_data}")
        else:
            self.audit_logger.warning(f"API_REQUEST_FAILED {log_data}")


# Global audit logger instance
audit_logger = AuditLogger()


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """Dependency to get and validate current API user"""
    
    if not credentials:
        audit_logger.log_request(request, None, False, "No credentials provided")
        raise HTTPException(
            status_code=401,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    key_config = api_key_manager.validate_key(credentials.credentials)
    if not key_config:
        audit_logger.log_request(request, None, False, "Invalid API key")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Log successful authentication
    key_name = key_config.get("name", "unknown")
    audit_logger.log_request(request, key_name, True)
    
    return {
        "key_config": key_config,
        "permissions": api_key_manager.get_permissions(credentials.credentials),
        "key_name": key_name
    }


def require_permission(permission: str):
    """Decorator to require specific permission for an endpoint"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs (injected by FastAPI dependency)
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(status_code=500, detail="Authentication context missing")
            
            permissions = current_user.get('permissions')
            if not permissions or not getattr(permissions, permission, False):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission '{permission}' required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def get_rate_limit_key(request: Request) -> str:
    """Get rate limit key for request (IP + API key if available)"""
    ip = get_remote_address(request)
    
    # Try to get API key from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        key = auth_header.split(" ", 1)[1]
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:8]
        return f"{ip}:{key_hash}"
    
    return ip


# Rate limit decorators for different permission levels
def rate_limit_basic():
    """Basic rate limit for read operations"""
    return limiter.limit("60/minute", key_func=get_rate_limit_key)


def rate_limit_privileged():
    """Stricter rate limit for write operations"""
    return limiter.limit("30/minute", key_func=get_rate_limit_key)


def rate_limit_admin():
    """Very strict rate limit for admin operations"""
    return limiter.limit("10/minute", key_func=get_rate_limit_key)


# Exception handlers
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Custom rate limit exceeded handler"""
    audit_logger.log_request(request, None, False, f"Rate limit exceeded: {exc.detail}")
    return HTTPException(
        status_code=429,
        detail={
            "error": "Rate limit exceeded",
            "detail": exc.detail,
            "retry_after": exc.retry_after
        }
    )