"""
Unified Logging System for AICleaner v3
Provides standardized logging with correlation IDs and structured format
"""

import json
import logging
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Union
from contextlib import contextmanager
from threading import local
import traceback

# Thread-local storage for correlation context
_context = local()

class CorrelationIDFilter(logging.Filter):
    """Filter to add correlation ID to log records."""
    
    def filter(self, record):
        # Add correlation ID from context if available
        record.correlation_id = getattr(_context, 'correlation_id', 'no-correlation')
        record.component = getattr(_context, 'component', 'unknown')
        record.user_id = getattr(_context, 'user_id', 'system')
        return True

class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for consistent log format."""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record):
        # Base log structure
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "correlation_id": getattr(record, 'correlation_id', 'no-correlation'),
            "component": getattr(record, 'component', 'unknown'),
            "user_id": getattr(record, 'user_id', 'system')
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields if enabled
        if self.include_extra:
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                              'filename', 'module', 'lineno', 'funcName', 'created', 
                              'msecs', 'relativeCreated', 'thread', 'threadName', 
                              'processName', 'process', 'correlation_id', 'component', 'user_id']:
                    extra_fields[key] = value
            
            if extra_fields:
                log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)

class UnifiedLogger:
    """Centralized logger configuration and management."""
    
    def __init__(self, 
                 name: str = "aicleaner",
                 level: Union[str, int] = logging.INFO,
                 console_output: bool = True,
                 file_output: Optional[str] = None,
                 structured_format: bool = True):
        """
        Initialize unified logger.
        
        Args:
            name: Logger name
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console_output: Whether to log to console
            file_output: File path for file logging (optional)
            structured_format: Whether to use structured JSON format
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.structured_format = structured_format
        
        # Set level
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        self.logger.setLevel(level)
        
        # Clear existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Add correlation ID filter
        correlation_filter = CorrelationIDFilter()
        
        # Console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.addFilter(correlation_filter)
            
            if structured_format:
                console_handler.setFormatter(StructuredFormatter())
            else:
                console_handler.setFormatter(
                    logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s'
                    )
                )
            
            self.logger.addHandler(console_handler)
        
        # File handler
        if file_output:
            file_handler = logging.FileHandler(file_output)
            file_handler.addFilter(correlation_filter)
            
            if structured_format:
                file_handler.setFormatter(StructuredFormatter())
            else:
                file_handler.setFormatter(
                    logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s'
                    )
                )
            
            self.logger.addHandler(file_handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance."""
        return self.logger

# Global logger instance
_global_logger: Optional[UnifiedLogger] = None

def configure_logging(name: str = "aicleaner",
                     level: Union[str, int] = logging.INFO,
                     console_output: bool = True,
                     file_output: Optional[str] = None,
                     structured_format: bool = True) -> UnifiedLogger:
    """
    Configure global logging for the application.
    
    Args:
        name: Logger name
        level: Logging level
        console_output: Whether to log to console
        file_output: File path for file logging
        structured_format: Whether to use structured JSON format
        
    Returns:
        Configured UnifiedLogger instance
    """
    global _global_logger
    _global_logger = UnifiedLogger(
        name=name,
        level=level,
        console_output=console_output,
        file_output=file_output,
        structured_format=structured_format
    )
    return _global_logger

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get logger instance with unified configuration.
    
    Args:
        name: Logger name (optional, uses global if not provided)
        
    Returns:
        Configured logger instance
    """
    if name:
        return logging.getLogger(name)
    
    if _global_logger:
        return _global_logger.get_logger()
    
    # Fallback to basic configuration
    logger = logging.getLogger("aicleaner")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger

def set_correlation_id(correlation_id: str):
    """Set correlation ID for current thread."""
    _context.correlation_id = correlation_id

def set_component(component: str):
    """Set component name for current thread."""
    _context.component = component

def set_user_id(user_id: str):
    """Set user ID for current thread."""
    _context.user_id = user_id

def get_correlation_id() -> str:
    """Get current correlation ID."""
    return getattr(_context, 'correlation_id', 'no-correlation')

def clear_context():
    """Clear all context variables."""
    _context.correlation_id = None
    _context.component = None
    _context.user_id = None

@contextmanager
def log_context(correlation_id: Optional[str] = None, 
                component: Optional[str] = None,
                user_id: Optional[str] = None):
    """
    Context manager for setting logging context.
    
    Args:
        correlation_id: Correlation ID (auto-generated if not provided)
        component: Component name
        user_id: User ID
    """
    # Save previous context
    old_correlation_id = getattr(_context, 'correlation_id', None)
    old_component = getattr(_context, 'component', None)
    old_user_id = getattr(_context, 'user_id', None)
    
    try:
        # Set new context
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())[:8]
        
        set_correlation_id(correlation_id)
        if component:
            set_component(component)
        if user_id:
            set_user_id(user_id)
        
        yield correlation_id
    
    finally:
        # Restore previous context
        if old_correlation_id:
            _context.correlation_id = old_correlation_id
        else:
            _context.correlation_id = None
            
        if old_component:
            _context.component = old_component
        else:
            _context.component = None
            
        if old_user_id:
            _context.user_id = old_user_id
        else:
            _context.user_id = None

def log_performance(operation: str, duration: float, **kwargs):
    """
    Log performance metrics in structured format.
    
    Args:
        operation: Operation name
        duration: Duration in seconds
        **kwargs: Additional metrics
    """
    logger = get_logger()
    
    metrics = {
        "operation": operation,
        "duration_seconds": duration,
        "performance_log": True,
        **kwargs
    }
    
    logger.info(f"Performance: {operation} completed in {duration:.3f}s", extra=metrics)

def log_security_event(event_type: str, 
                      severity: str,
                      details: Dict[str, Any],
                      ip_address: Optional[str] = None):
    """
    Log security events in structured format.
    
    Args:
        event_type: Type of security event
        severity: Severity level (low, medium, high, critical)
        details: Event details
        ip_address: IP address if relevant
    """
    logger = get_logger()
    
    security_data = {
        "security_event": True,
        "event_type": event_type,
        "severity": severity,
        "details": details,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    if ip_address:
        security_data["ip_address"] = ip_address
    
    # Log at appropriate level based on severity
    if severity in ['critical', 'high']:
        logger.error(f"Security Event: {event_type}", extra=security_data)
    elif severity == 'medium':
        logger.warning(f"Security Event: {event_type}", extra=security_data)
    else:
        logger.info(f"Security Event: {event_type}", extra=security_data)

def log_api_request(method: str,
                   path: str,
                   status_code: int,
                   duration: float,
                   ip_address: Optional[str] = None,
                   user_agent: Optional[str] = None):
    """
    Log API requests in structured format.
    
    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration: Request duration in seconds
        ip_address: Client IP address
        user_agent: User agent string
    """
    logger = get_logger()
    
    api_data = {
        "api_request": True,
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_seconds": duration
    }
    
    if ip_address:
        api_data["ip_address"] = ip_address
    if user_agent:
        api_data["user_agent"] = user_agent
    
    # Log level based on status code
    if status_code >= 500:
        logger.error(f"API {method} {path} - {status_code}", extra=api_data)
    elif status_code >= 400:
        logger.warning(f"API {method} {path} - {status_code}", extra=api_data)
    else:
        logger.info(f"API {method} {path} - {status_code}", extra=api_data)

# Home Assistant addon specific configuration
def configure_ha_addon_logging(log_level: str = "INFO",
                              enable_debug: bool = False) -> UnifiedLogger:
    """
    Configure logging specifically for Home Assistant addon environment.
    
    Args:
        log_level: Logging level for the addon
        enable_debug: Whether to enable debug logging
        
    Returns:
        Configured logger
    """
    # In HA addon, typically log to stdout which HA captures
    level = logging.DEBUG if enable_debug else getattr(logging, log_level.upper())
    
    return configure_logging(
        name="aicleaner",
        level=level,
        console_output=True,
        file_output=None,  # HA handles file logging
        structured_format=True  # Structured logs are easier for HA to parse
    )

# Component-specific logger factories
def get_ai_logger() -> logging.Logger:
    """Get logger for AI components."""
    with log_context(component="ai"):
        return get_logger("aicleaner.ai")

def get_security_logger() -> logging.Logger:
    """Get logger for security components."""
    with log_context(component="security"):
        return get_logger("aicleaner.security")

def get_zone_logger() -> logging.Logger:
    """Get logger for zone management."""
    with log_context(component="zones"):
        return get_logger("aicleaner.zones")

def get_device_logger() -> logging.Logger:
    """Get logger for device management."""
    with log_context(component="devices"):
        return get_logger("aicleaner.devices")

def get_config_logger() -> logging.Logger:
    """Get logger for configuration management."""
    with log_context(component="config"):
        return get_logger("aicleaner.config")

def get_api_logger() -> logging.Logger:
    """Get logger for API components."""
    with log_context(component="api"):
        return get_logger("aicleaner.api")