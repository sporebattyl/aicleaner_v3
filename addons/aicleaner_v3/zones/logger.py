"""
Phase 3B: Zone Configuration Logging
Structured logging system for zone management operations.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


def setup_logger(name: str, level: int = logging.INFO, log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up structured logger for zone management.
    
    Args:
        name: Logger name
        level: Logging level
        log_file: Optional log file path
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Create formatter
    formatter = ZoneStructuredFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


class ZoneStructuredFormatter(logging.Formatter):
    """
    Structured JSON formatter for zone logging.
    Implements the 6-section framework logging requirements.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as structured JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted JSON log string
        """
        # Base log structure
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add zone-specific context if available
        if hasattr(record, 'zone_id'):
            log_data['zone_id'] = record.zone_id
        if hasattr(record, 'zone_name'):
            log_data['zone_name'] = record.zone_name
        if hasattr(record, 'device_id'):
            log_data['device_id'] = record.device_id
        if hasattr(record, 'rule_id'):
            log_data['rule_id'] = record.rule_id
        if hasattr(record, 'operation'):
            log_data['operation'] = record.operation
        if hasattr(record, 'execution_time_ms'):
            log_data['execution_time_ms'] = record.execution_time_ms
        if hasattr(record, 'performance_metrics'):
            log_data['performance_metrics'] = record.performance_metrics
        if hasattr(record, 'error_context'):
            log_data['error_context'] = record.error_context
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'message', 'exc_info', 'exc_text', 
                          'stack_info'] and not key.startswith('_'):
                if not hasattr(record, key) or key not in log_data:
                    try:
                        # Only add serializable values
                        json.dumps(value)
                        log_data[key] = value
                    except (TypeError, ValueError):
                        log_data[key] = str(value)
        
        return json.dumps(log_data, ensure_ascii=False)


class ZoneContextLogger:
    """
    Context-aware logger for zone operations.
    Automatically adds zone context to log messages.
    """
    
    def __init__(self, logger: logging.Logger, zone_id: Optional[str] = None, 
                 zone_name: Optional[str] = None):
        """
        Initialize context logger.
        
        Args:
            logger: Base logger
            zone_id: Zone ID for context
            zone_name: Zone name for context
        """
        self.logger = logger
        self.zone_id = zone_id
        self.zone_name = zone_name
        self.context = {}
    
    def set_context(self, **kwargs) -> None:
        """Set additional context for logging."""
        self.context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear logging context."""
        self.context.clear()
    
    def _add_context(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add zone context to extra parameters."""
        context_extra = {}
        
        if self.zone_id:
            context_extra['zone_id'] = self.zone_id
        if self.zone_name:
            context_extra['zone_name'] = self.zone_name
        
        context_extra.update(self.context)
        
        if extra:
            context_extra.update(extra)
        
        return context_extra
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message with zone context."""
        self.logger.debug(message, extra=self._add_context(extra))
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log info message with zone context."""
        self.logger.info(message, extra=self._add_context(extra))
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message with zone context."""
        self.logger.warning(message, extra=self._add_context(extra))
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log error message with zone context."""
        self.logger.error(message, extra=self._add_context(extra))
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log critical message with zone context."""
        self.logger.critical(message, extra=self._add_context(extra))
    
    def exception(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log exception with zone context."""
        self.logger.exception(message, extra=self._add_context(extra))


class ZoneOperationLogger:
    """
    Logger for tracking zone operations with timing and performance metrics.
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize operation logger.
        
        Args:
            logger: Base logger
        """
        self.logger = logger
    
    async def log_operation(self, operation: str, zone_id: str, zone_name: str,
                          operation_func, *args, **kwargs) -> Any:
        """
        Log operation execution with timing and result.
        
        Args:
            operation: Operation name
            zone_id: Zone ID
            zone_name: Zone name
            operation_func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        start_time = datetime.now()
        
        # Log operation start
        self.logger.info(
            f"Starting {operation}",
            extra={
                'zone_id': zone_id,
                'zone_name': zone_name,
                'operation': operation,
                'status': 'started'
            }
        )
        
        try:
            # Execute operation
            if asyncio.iscoroutinefunction(operation_func):
                result = await operation_func(*args, **kwargs)
            else:
                result = operation_func(*args, **kwargs)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log successful completion
            self.logger.info(
                f"Completed {operation}",
                extra={
                    'zone_id': zone_id,
                    'zone_name': zone_name,
                    'operation': operation,
                    'status': 'completed',
                    'execution_time_ms': execution_time,
                    'success': True
                }
            )
            
            return result
            
        except Exception as e:
            # Calculate execution time for failed operation
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log operation failure
            self.logger.error(
                f"Failed {operation}: {str(e)}",
                extra={
                    'zone_id': zone_id,
                    'zone_name': zone_name,
                    'operation': operation,
                    'status': 'failed',
                    'execution_time_ms': execution_time,
                    'success': False,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )
            
            raise


class ZoneMetricsLogger:
    """
    Logger for zone performance metrics and analytics.
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize metrics logger.
        
        Args:
            logger: Base logger
        """
        self.logger = logger
    
    def log_zone_metrics(self, zone_id: str, zone_name: str, metrics: Dict[str, Any]) -> None:
        """
        Log zone performance metrics.
        
        Args:
            zone_id: Zone ID
            zone_name: Zone name
            metrics: Performance metrics dictionary
        """
        self.logger.info(
            f"Zone metrics update",
            extra={
                'zone_id': zone_id,
                'zone_name': zone_name,
                'operation': 'metrics_update',
                'performance_metrics': metrics
            }
        )
    
    def log_device_metrics(self, zone_id: str, device_id: str, 
                          device_name: str, metrics: Dict[str, Any]) -> None:
        """
        Log device performance metrics within a zone.
        
        Args:
            zone_id: Zone ID
            device_id: Device ID
            device_name: Device name
            metrics: Device metrics dictionary
        """
        self.logger.info(
            f"Device metrics update",
            extra={
                'zone_id': zone_id,
                'device_id': device_id,
                'device_name': device_name,
                'operation': 'device_metrics_update',
                'performance_metrics': metrics
            }
        )
    
    def log_rule_execution(self, zone_id: str, rule_id: str, rule_name: str,
                          success: bool, execution_time_ms: float, 
                          error_message: Optional[str] = None) -> None:
        """
        Log automation rule execution.
        
        Args:
            zone_id: Zone ID
            rule_id: Rule ID
            rule_name: Rule name
            success: Whether execution was successful
            execution_time_ms: Execution time in milliseconds
            error_message: Error message if execution failed
        """
        level = logging.INFO if success else logging.ERROR
        message = f"Rule execution {'succeeded' if success else 'failed'}"
        
        extra = {
            'zone_id': zone_id,
            'rule_id': rule_id,
            'rule_name': rule_name,
            'operation': 'rule_execution',
            'success': success,
            'execution_time_ms': execution_time_ms
        }
        
        if error_message:
            extra['error_message'] = error_message
        
        self.logger.log(level, message, extra=extra)
    
    def log_optimization_result(self, zone_id: str, zone_name: str,
                              optimization_type: str, improvements: Dict[str, Any]) -> None:
        """
        Log zone optimization results.
        
        Args:
            zone_id: Zone ID
            zone_name: Zone name
            optimization_type: Type of optimization performed
            improvements: Dictionary of improvements made
        """
        self.logger.info(
            f"Zone optimization completed: {optimization_type}",
            extra={
                'zone_id': zone_id,
                'zone_name': zone_name,
                'operation': 'optimization',
                'optimization_type': optimization_type,
                'improvements': improvements
            }
        )


# Pre-configured loggers for different components
zone_manager_logger = setup_logger('zones.manager')
zone_config_logger = setup_logger('zones.config')
zone_optimization_logger = setup_logger('zones.optimization')
zone_monitoring_logger = setup_logger('zones.monitoring')
zone_ha_integration_logger = setup_logger('zones.ha_integration')


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test_logging():
        """Test logging functionality."""
        
        # Test basic structured logging
        logger = setup_logger('test.zones')
        logger.info("Test message", extra={
            'zone_id': 'living_room',
            'operation': 'test',
            'execution_time_ms': 150.5
        })
        
        # Test context logger
        context_logger = ZoneContextLogger(logger, zone_id='kitchen', zone_name='Kitchen')
        context_logger.set_context(user_id='user123', session_id='sess456')
        context_logger.info("Context test message")
        
        # Test operation logger
        operation_logger = ZoneOperationLogger(logger)
        
        async def test_operation():
            await asyncio.sleep(0.1)
            return "Operation completed"
        
        result = await operation_logger.log_operation(
            'test_operation', 'bedroom', 'Bedroom', test_operation
        )
        
        # Test metrics logger
        metrics_logger = ZoneMetricsLogger(logger)
        metrics_logger.log_zone_metrics('bathroom', 'Bathroom', {
            'device_count': 3,
            'average_response_time': 125.3,
            'energy_consumption': 45.7
        })
        
        print("Logging tests completed!")
    
    # Run tests
    asyncio.run(test_logging())