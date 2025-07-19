"""
Home Assistant Ingress Middleware
Phase 4A: Enhanced Home Assistant Integration

FastAPI middleware for handling Home Assistant ingress path rewriting
and seamless UI integration.
"""

import logging
from typing import Callable, Optional
from urllib.parse import urlparse, urljoin
import re

from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .config_schema import HAIntegrationConfig

logger = logging.getLogger(__name__)

class IngressMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for Home Assistant ingress support
    
    Handles path rewriting for React UI assets and API calls when accessed
    via Home Assistant's ingress feature.
    """
    
    def __init__(self, app: ASGIApp, config: HAIntegrationConfig):
        super().__init__(app)
        self.config = config
        self.ingress_enabled = config.enable_ingress
        
        # Regex patterns for different types of requests
        self.static_asset_pattern = re.compile(r'^/static/.*$')
        self.api_pattern = re.compile(r'^/api/.*$')
        self.ws_pattern = re.compile(r'^/ws.*$')
        self.ingress_pattern = re.compile(r'^/api/hassio_ingress/[^/]+(.*)$')
        
        logger.info(f"Ingress middleware initialized (enabled: {self.ingress_enabled})")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process incoming request and handle ingress path rewriting
        
        Args:
            request: Incoming FastAPI request
            call_next: Next middleware/handler in chain
            
        Returns:
            Modified response
        """
        # Skip processing if ingress is disabled
        if not self.ingress_enabled:
            return await call_next(request)
        
        try:
            # Extract ingress information from headers and path
            ingress_info = self._extract_ingress_info(request)
            
            if ingress_info["is_ingress"]:
                logger.debug(f"Processing ingress request: {request.url.path}")
                
                # Handle different types of ingress requests
                modified_request = self._rewrite_request_path(request, ingress_info)
                
                # Process request with modified path
                response = await call_next(modified_request)
                
                # Modify response if needed
                modified_response = self._modify_response(response, ingress_info, request)
                
                return modified_response
            else:
                # Non-ingress request, process normally
                return await call_next(request)
                
        except Exception as e:
            logger.error(f"Ingress middleware error: {e}")
            # On error, pass through to avoid breaking the app
            return await call_next(request)
    
    def _extract_ingress_info(self, request: Request) -> dict:
        """
        Extract ingress information from request headers and path
        
        Args:
            request: FastAPI request
            
        Returns:
            Dictionary with ingress information
        """
        ingress_info = {
            "is_ingress": False,
            "ingress_path": None,
            "original_path": request.url.path,
            "rewritten_path": request.url.path
        }
        
        # Check for HA ingress headers
        ingress_path = request.headers.get("X-Ingress-Path")
        ha_ingress = request.headers.get("X-HA-Ingress", "").lower() == "true"
        
        # Check for ingress in URL path
        ingress_match = self.ingress_pattern.match(request.url.path)
        
        if ingress_path or ha_ingress or ingress_match:
            ingress_info["is_ingress"] = True
            
            if ingress_match:
                # Extract actual path from ingress URL
                ingress_info["ingress_path"] = ingress_match.group(0)
                ingress_info["rewritten_path"] = ingress_match.group(1) or "/"
            elif ingress_path:
                ingress_info["ingress_path"] = ingress_path
                # Remove ingress prefix from path
                if request.url.path.startswith(ingress_path):
                    ingress_info["rewritten_path"] = request.url.path[len(ingress_path):]
                    if not ingress_info["rewritten_path"].startswith("/"):
                        ingress_info["rewritten_path"] = "/" + ingress_info["rewritten_path"]
        
        return ingress_info
    
    def _rewrite_request_path(self, request: Request, ingress_info: dict) -> Request:
        """
        Rewrite request path for ingress
        
        Args:
            request: Original request
            ingress_info: Ingress information
            
        Returns:
            Request with modified path
        """
        # Create new scope with modified path
        scope = request.scope.copy()
        scope["path"] = ingress_info["rewritten_path"]
        scope["raw_path"] = ingress_info["rewritten_path"].encode()
        
        # Update path_info for compatibility
        scope["path_info"] = ingress_info["rewritten_path"]
        
        # Create new request with modified scope
        modified_request = Request(scope, request.receive)
        
        # Copy over important attributes
        modified_request._url = request._url._replace(path=ingress_info["rewritten_path"])
        
        logger.debug(f"Path rewritten: {ingress_info['original_path']} -> {ingress_info['rewritten_path']}")
        
        return modified_request
    
    def _modify_response(self, response: Response, ingress_info: dict, 
                        original_request: Request) -> Response:
        """
        Modify response for ingress compatibility
        
        Args:
            response: Original response
            ingress_info: Ingress information
            original_request: Original request
            
        Returns:
            Modified response
        """
        # Handle HTML responses (main UI)
        if (hasattr(response, 'media_type') and 
            response.media_type and 
            'text/html' in response.media_type):
            
            response = self._modify_html_response(response, ingress_info)
        
        # Handle JSON API responses
        elif (hasattr(response, 'media_type') and 
              response.media_type and 
              'application/json' in response.media_type):
            
            response = self._modify_json_response(response, ingress_info)
        
        # Add ingress headers
        response.headers["X-Ingress-Path"] = ingress_info.get("ingress_path", "")
        response.headers["X-HA-Ingress"] = "true"
        
        return response
    
    def _modify_html_response(self, response: Response, ingress_info: dict) -> Response:
        """
        Modify HTML response to fix asset paths for ingress
        
        Args:
            response: HTML response
            ingress_info: Ingress information
            
        Returns:
            Modified HTML response
        """
        try:
            # This would modify HTML content to fix static asset paths
            # For now, return as-is since Vite handles this automatically
            # with proper base configuration
            
            # TODO: If needed, implement HTML parsing and path rewriting
            # to handle cases where Vite base configuration isn't sufficient
            
            return response
            
        except Exception as e:
            logger.warning(f"HTML response modification failed: {e}")
            return response
    
    def _modify_json_response(self, response: Response, ingress_info: dict) -> Response:
        """
        Modify JSON API response for ingress compatibility
        
        Args:
            response: JSON response
            ingress_info: Ingress information
            
        Returns:
            Modified JSON response
        """
        try:
            # Add ingress information to API responses if needed
            # This allows the frontend to know it's running under ingress
            
            # TODO: Modify JSON responses to include ingress context
            # if the frontend needs this information
            
            return response
            
        except Exception as e:
            logger.warning(f"JSON response modification failed: {e}")
            return response
    
    def _is_static_asset(self, path: str) -> bool:
        """Check if path is for a static asset"""
        return bool(self.static_asset_pattern.match(path))
    
    def _is_api_call(self, path: str) -> bool:
        """Check if path is for an API call"""
        return bool(self.api_pattern.match(path))
    
    def _is_websocket(self, path: str) -> bool:
        """Check if path is for a WebSocket connection"""
        return bool(self.ws_pattern.match(path))

class IngressPathHelper:
    """
    Helper class for working with ingress paths in the application
    """
    
    def __init__(self, config: HAIntegrationConfig):
        self.config = config
        self.ingress_enabled = config.enable_ingress
    
    def get_ingress_url(self, path: str, request: Optional[Request] = None) -> str:
        """
        Get the full ingress URL for a given path
        
        Args:
            path: Relative path
            request: Current request (to extract ingress info)
            
        Returns:
            Full ingress URL
        """
        if not self.ingress_enabled or not request:
            return path
        
        ingress_path = request.headers.get("X-Ingress-Path")
        if ingress_path:
            return urljoin(ingress_path, path.lstrip("/"))
        
        return path
    
    def is_ingress_request(self, request: Request) -> bool:
        """
        Check if request is coming through HA ingress
        
        Args:
            request: FastAPI request
            
        Returns:
            True if ingress request
        """
        return (
            request.headers.get("X-HA-Ingress", "").lower() == "true" or
            request.headers.get("X-Ingress-Path") is not None
        )
    
    def get_base_url(self, request: Request) -> str:
        """
        Get the base URL for the application
        
        Args:
            request: Current request
            
        Returns:
            Base URL (with ingress path if applicable)
        """
        if not self.ingress_enabled:
            return str(request.base_url)
        
        ingress_path = request.headers.get("X-Ingress-Path")
        if ingress_path:
            return f"{request.base_url.scheme}://{request.base_url.netloc}{ingress_path}"
        
        return str(request.base_url)

# FastAPI dependency for injecting ingress helper
def get_ingress_helper(config: HAIntegrationConfig) -> IngressPathHelper:
    """
    FastAPI dependency for getting ingress path helper
    
    Args:
        config: HA integration configuration
        
    Returns:
        IngressPathHelper instance
    """
    return IngressPathHelper(config)

# Utility functions for Vite/React integration

def get_vite_base_config(ingress_path: Optional[str] = None) -> dict:
    """
    Get Vite configuration for ingress support
    
    Args:
        ingress_path: Ingress path prefix
        
    Returns:
        Vite configuration dictionary
    """
    config = {
        "base": ingress_path or "/",
        "build": {
            "assetsDir": "static",
            "outDir": "dist"
        },
        "server": {
            "proxy": {
                "/api": {
                    "target": "http://localhost:8080",
                    "changeOrigin": True,
                    "rewrite": f"(path) => path.replace(/^{ingress_path or ''}\\/api/, '/api')" if ingress_path else None
                }
            }
        }
    }
    
    return config

def update_vite_config_for_ingress(vite_config_path: str, ingress_path: Optional[str] = None):
    """
    Update Vite configuration file for ingress support
    
    Args:
        vite_config_path: Path to vite.config.js
        ingress_path: Ingress path prefix
    """
    try:
        # TODO: Implement actual Vite config file modification
        # This would read the existing vite.config.js, modify the base path,
        # and write it back
        
        logger.info(f"Vite config would be updated for ingress: {ingress_path}")
        
    except Exception as e:
        logger.error(f"Failed to update Vite config: {e}")

# React environment variables for ingress support

def get_react_env_vars(request: Request, config: HAIntegrationConfig) -> dict:
    """
    Get React environment variables for ingress support
    
    Args:
        request: Current request
        config: HA integration configuration
        
    Returns:
        Environment variables dictionary
    """
    helper = IngressPathHelper(config)
    
    env_vars = {
        "REACT_APP_INGRESS_ENABLED": str(config.enable_ingress).lower(),
        "REACT_APP_BASE_URL": helper.get_base_url(request),
        "REACT_APP_API_BASE": helper.get_ingress_url("/api", request),
        "REACT_APP_WS_BASE": helper.get_ingress_url("/ws", request)
    }
    
    if helper.is_ingress_request(request):
        env_vars["REACT_APP_INGRESS_PATH"] = request.headers.get("X-Ingress-Path", "")
        env_vars["REACT_APP_IS_INGRESS"] = "true"
    else:
        env_vars["REACT_APP_IS_INGRESS"] = "false"
    
    return env_vars