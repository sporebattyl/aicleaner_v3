#!/usr/bin/env python3
"""
AICleaner V3 Error Handler Module
Provides comprehensive error handling, logging, and user notifications
"""

import os
import json
import logging
import traceback
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
from enum import Enum

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for classification"""
    CONFIGURATION = "configuration"
    MQTT = "mqtt"
    API = "api"
    DASHBOARD = "dashboard"
    ENTITY = "entity"
    NETWORK = "network"
    PERMISSION = "permission"
    VALIDATION = "validation"
    SYSTEM = "system"

class AICleaenerError(Exception):
    """Base exception for AICleaner with enhanced context"""
    
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.SYSTEM, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM, user_message: str = None,
                 error_code: str = None, context: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.user_message = user_message or self._generate_user_message()
        self.error_code = error_code or self._generate_error_code()
        self.context = context or {}
        self.timestamp = datetime.utcnow()
    
    def _generate_user_message(self) -> str:
        """Generate user-friendly error message"""
        if self.category == ErrorCategory.MQTT:
            return "MQTT connection issue. Check broker settings and network connectivity."
        elif self.category == ErrorCategory.API:
            return "Home Assistant API error. Check permissions and connectivity."
        elif self.category == ErrorCategory.DASHBOARD:
            return "Dashboard configuration error. Some features may be unavailable."
        elif self.category == ErrorCategory.ENTITY:
            return "Entity access error. Check that cameras and todo lists exist."
        elif self.category == ErrorCategory.CONFIGURATION:
            return "Configuration error. Please check your settings."
        elif self.category == ErrorCategory.VALIDATION:
            return f"Input validation error: {self.message}"
        else:
            return "An unexpected error occurred. Please check the logs for details."
    
    def _generate_error_code(self) -> str:
        """Generate unique error code for tracking"""
        return f"AC_{self.category.value.upper()}_{self.severity.value.upper()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/API responses"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context
        }

class NotificationManager:
    """Manages user notifications for critical events"""
    
    def __init__(self, ha_api_client=None):
        self.ha_api_client = ha_api_client
        self.notification_history = []
        self.max_history = 100
    
    async def send_notification(self, title: str, message: str, 
                               severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                               service_data: Dict[str, Any] = None):
        """Send notification to Home Assistant"""
        try:
            notification_data = {
                "title": f"🤖 AI Cleaner v3: {title}",
                "message": message,
                "data": {
                    "priority": self._severity_to_priority(severity),
                    "tag": "aicleaner_v3",
                    "group": "aicleaner_notifications"
                }
            }
            
            if service_data:
                notification_data["data"].update(service_data)
            
            # Store in history
            self._add_to_history(title, message, severity)
            
            # Send via Home Assistant if available
            if self.ha_api_client:
                await self.ha_api_client.call_service(
                    "persistent_notification", "create", notification_data
                )
                logger.info(f"Sent notification: {title}")
            else:
                logger.warning(f"Cannot send notification (no HA API): {title}")
                
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def _severity_to_priority(self, severity: ErrorSeverity) -> str:
        """Convert severity to notification priority"""
        mapping = {
            ErrorSeverity.LOW: "low",
            ErrorSeverity.MEDIUM: "normal", 
            ErrorSeverity.HIGH: "high",
            ErrorSeverity.CRITICAL: "high"
        }
        return mapping.get(severity, "normal")
    
    def _add_to_history(self, title: str, message: str, severity: ErrorSeverity):
        """Add notification to history"""
        self.notification_history.append({
            "title": title,
            "message": message,
            "severity": severity.value,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Limit history size
        if len(self.notification_history) > self.max_history:
            self.notification_history = self.notification_history[-self.max_history:]
    
    def get_recent_notifications(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent notifications"""
        return self.notification_history[-limit:]

class ErrorHandler:
    """Centralized error handling and logging"""
    
    def __init__(self, notification_manager: NotificationManager = None):
        self.notification_manager = notification_manager or NotificationManager()
        self.error_stats = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "last_reset": datetime.utcnow().isoformat()
        }
        self.error_log_file = "/data/error_log.json"
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure enhanced logging"""
        # Create custom formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        
        # Ensure we have file handler for persistent logging
        if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
            file_handler = logging.FileHandler('/data/aicleaner.log')
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.INFO)
            
            root_logger = logging.getLogger()
            root_logger.addHandler(file_handler)
    
    async def handle_error(self, error: Exception, context: Dict[str, Any] = None,
                          notify_user: bool = None) -> Dict[str, Any]:
        """Central error handling with logging and notifications"""
        
        # Convert to AICleaner error if needed
        if not isinstance(error, AICleaenerError):
            error = self._convert_to_aicleaner_error(error, context)
        
        # Update statistics
        self._update_error_stats(error)
        
        # Log error with full context
        self._log_error(error, context)
        
        # Determine if user should be notified
        should_notify = notify_user if notify_user is not None else self._should_notify_user(error)
        
        # Send notification if needed
        if should_notify:
            await self._notify_user_of_error(error)
        
        # Persist error to file for debugging
        await self._persist_error(error)
        
        return error.to_dict()
    
    def _convert_to_aicleaner_error(self, error: Exception, context: Dict[str, Any] = None) -> AICleaenerError:
        """Convert generic exception to AICleaner error"""
        error_message = str(error)
        category = self._classify_error(error)
        severity = self._determine_severity(error, category)
        
        return AICleaenerError(
            message=error_message,
            category=category,
            severity=severity,
            context=context or {}
        )
    
    def _classify_error(self, error: Exception) -> ErrorCategory:
        """Classify error by type and message"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        if "mqtt" in error_str or "paho" in error_type:
            return ErrorCategory.MQTT
        elif "api" in error_str or "http" in error_str or "connection" in error_str:
            return ErrorCategory.API
        elif "dashboard" in error_str or "lovelace" in error_str:
            return ErrorCategory.DASHBOARD
        elif "entity" in error_str or "state" in error_str:
            return ErrorCategory.ENTITY
        elif "validation" in error_str or "invalid" in error_str:
            return ErrorCategory.VALIDATION
        elif "permission" in error_str or "unauthorized" in error_str:
            return ErrorCategory.PERMISSION
        elif "network" in error_str or "timeout" in error_str:
            return ErrorCategory.NETWORK
        elif "config" in error_str:
            return ErrorCategory.CONFIGURATION
        else:
            return ErrorCategory.SYSTEM
    
    def _determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity based on type and category"""
        error_str = str(error).lower()
        
        # Critical errors
        if any(word in error_str for word in ["critical", "fatal", "crash", "corrupted"]):
            return ErrorSeverity.CRITICAL
        
        # High severity by category
        if category in [ErrorCategory.PERMISSION, ErrorCategory.SYSTEM]:
            return ErrorSeverity.HIGH
        
        # High severity by keywords
        if any(word in error_str for word in ["failed", "unable", "cannot", "denied"]):
            return ErrorSeverity.HIGH
        
        # Medium severity by category
        if category in [ErrorCategory.API, ErrorCategory.MQTT, ErrorCategory.DASHBOARD]:
            return ErrorSeverity.MEDIUM
        
        # Low severity for validation and configuration
        if category in [ErrorCategory.VALIDATION, ErrorCategory.CONFIGURATION]:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    def _update_error_stats(self, error: AICleaenerError):
        """Update error statistics"""
        self.error_stats["total_errors"] += 1
        
        category = error.category.value
        if category not in self.error_stats["errors_by_category"]:
            self.error_stats["errors_by_category"][category] = 0
        self.error_stats["errors_by_category"][category] += 1
        
        severity = error.severity.value
        if severity not in self.error_stats["errors_by_severity"]:
            self.error_stats["errors_by_severity"][severity] = 0
        self.error_stats["errors_by_severity"][severity] += 1
    
    def _log_error(self, error: AICleaenerError, context: Dict[str, Any] = None):
        """Log error with appropriate level and context"""
        log_data = {
            "error_code": error.error_code,
            "category": error.category.value,
            "severity": error.severity.value,
            "message": error.message,
            "context": error.context
        }
        
        if context:
            log_data["additional_context"] = context
        
        log_message = f"[{error.error_code}] {error.message}"
        
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra=log_data)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra=log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra=log_data)
        else:
            logger.info(log_message, extra=log_data)
    
    def _should_notify_user(self, error: AICleaenerError) -> bool:
        """Determine if user should be notified"""
        # Always notify for critical and high severity
        if error.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            return True
        
        # Notify for medium severity in critical categories
        if (error.severity == ErrorSeverity.MEDIUM and 
            error.category in [ErrorCategory.MQTT, ErrorCategory.API, ErrorCategory.DASHBOARD]):
            return True
        
        return False
    
    async def _notify_user_of_error(self, error: AICleaenerError):
        """Send user notification for error"""
        title_map = {
            ErrorCategory.MQTT: "MQTT Connection Issue",
            ErrorCategory.API: "Home Assistant API Error", 
            ErrorCategory.DASHBOARD: "Dashboard Error",
            ErrorCategory.ENTITY: "Entity Access Error",
            ErrorCategory.CONFIGURATION: "Configuration Error",
            ErrorCategory.NETWORK: "Network Error",
            ErrorCategory.PERMISSION: "Permission Error",
            ErrorCategory.VALIDATION: "Input Error",
            ErrorCategory.SYSTEM: "System Error"
        }
        
        title = title_map.get(error.category, "Addon Error")
        
        await self.notification_manager.send_notification(
            title=title,
            message=error.user_message,
            severity=error.severity,
            service_data={
                "error_code": error.error_code,
                "category": error.category.value
            }
        )
    
    async def _persist_error(self, error: AICleaenerError):
        """Persist error to file for debugging"""
        try:
            # Load existing errors
            errors = []
            if os.path.exists(self.error_log_file):
                try:
                    with open(self.error_log_file, 'r') as f:
                        errors = json.load(f)
                except (json.JSONDecodeError, IOError):
                    errors = []
            
            # Add new error
            errors.append(error.to_dict())
            
            # Keep only last 1000 errors
            if len(errors) > 1000:
                errors = errors[-1000:]
            
            # Save back to file
            with open(self.error_log_file, 'w') as f:
                json.dump(errors, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to persist error to file: {e}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return self.error_stats.copy()
    
    def reset_error_stats(self):
        """Reset error statistics"""
        self.error_stats = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "last_reset": datetime.utcnow().isoformat()
        }

def error_handler(category: ErrorCategory = ErrorCategory.SYSTEM, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 notify_user: bool = None):
    """Decorator for automatic error handling"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_handler_instance = getattr(args[0], 'error_handler', None)
                if error_handler_instance:
                    context = {
                        "function": func.__name__,
                        "args": str(args[1:])[:200],  # Limit context size
                        "kwargs": str(kwargs)[:200]
                    }
                    await error_handler_instance.handle_error(e, context, notify_user)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # For sync functions, just log and re-raise
                logger.error(f"Error in {func.__name__}: {e}")
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Health check utilities
class HealthChecker:
    """System health monitoring"""
    
    def __init__(self):
        self.health_status = {
            "mqtt": {"status": "unknown", "last_check": None},
            "api": {"status": "unknown", "last_check": None},
            "dashboard": {"status": "unknown", "last_check": None},
            "entities": {"status": "unknown", "last_check": None}
        }
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Perform comprehensive system health check"""
        health_report = {
            "overall_status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": self.health_status.copy()
        }
        
        # Determine overall status
        unhealthy_checks = [
            check for check in self.health_status.values() 
            if check["status"] in ["error", "degraded"]
        ]
        
        if len(unhealthy_checks) > 0:
            if len(unhealthy_checks) >= len(self.health_status) / 2:
                health_report["overall_status"] = "unhealthy"
            else:
                health_report["overall_status"] = "degraded"
        
        return health_report
    
    def update_component_health(self, component: str, status: str, details: str = None):
        """Update health status for a component"""
        if component in self.health_status:
            self.health_status[component] = {
                "status": status,
                "last_check": datetime.utcnow().isoformat(),
                "details": details
            }