"""
Simple Logging Configuration for AICleaner v3
Production-ready logging optimized for single-user deployment

This module provides a simplified logging system that balances functionality
with performance for resource-constrained environments like Home Assistant addons.

Key Features:
- Lightweight handlers with minimal overhead
- Essential security and audit logging
- Simple configuration for hobbyist users
- Home Assistant integration
- Basic diagnostics and troubleshooting support
"""

import asyncio
import json
import logging
import logging.handlers
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable
from enum import Enum
import queue
import psutil


class LogLevel(Enum):
    """Simplified log levels for single-user deployment"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LogCategory(Enum):
    """Essential log categories"""
    SYSTEM = "system"
    AI_PROVIDER = "ai_provider"
    SECURITY = "security"
    PERFORMANCE = "performance"
    USER_ACTION = "user_action"
    INTEGRATION = "integration"
    ERROR = "error"


@dataclass
class SimpleLogConfig:
    """Simplified logging configuration for single-user deployment"""
    log_directory: str = "logs"
    log_level: LogLevel = LogLevel.INFO
    max_log_size: int = 5 * 1024 * 1024  # 5MB (reduced from 10MB)
    backup_count: int = 3  # Reduced from 5
    enable_console: bool = True
    enable_file: bool = True
    enable_ha_integration: bool = True
    enable_security_logging: bool = True
    enable_performance_logging: bool = False  # Disabled by default for performance
    buffer_size: int = 100  # Reduced from 1000
    flush_interval: float = 10.0  # Increased from 5.0
    compression: bool = True
    
    # Simplified alert thresholds
    error_rate_threshold: float = 0.2  # 20% error rate
    critical_error_count: int = 3
    performance_threshold_ms: int = 5000  # 5 seconds


@dataclass
class LogEntry:
    """Simplified log entry structure"""
    timestamp: datetime
    level: LogLevel
    message: str
    category: LogCategory
    component: str
    correlation_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class SimpleLogHandler:
    """Base class for simplified log handlers"""
    
    def __init__(self, name: str, min_level: LogLevel = LogLevel.INFO):
        self.name = name
        self.min_level = min_level
        self.enabled = True
        self.message_count = 0
        self.error_count = 0
        self.last_message_time = None
    
    def should_process(self, entry: LogEntry) -> bool:
        """Check if log entry should be processed"""
        return self.enabled and entry.level.value >= self.min_level.value
    
    async def handle_log(self, entry: LogEntry) -> bool:
        """Handle log entry - to be implemented by subclasses"""
        if not self.should_process(entry):
            return False
        
        self.message_count += 1
        if entry.level.value >= LogLevel.ERROR.value:
            self.error_count += 1
        self.last_message_time = datetime.now()
        
        return True


class SimpleFileHandler(SimpleLogHandler):
    """Simplified file handler with rotation"""
    
    def __init__(self, name: str, file_path: str, config: SimpleLogConfig):
        super().__init__(name, config.log_level)
        self.file_path = Path(file_path)
        self.max_size = config.max_log_size
        self.backup_count = config.backup_count
        self.compression = config.compression
        self.lock = threading.Lock()
        
        # Create directory
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Set up Python's RotatingFileHandler for simplicity
        self.handler = logging.handlers.RotatingFileHandler(
            filename=str(self.file_path),
            maxBytes=self.max_size,
            backupCount=self.backup_count
        )
        
        # Set up formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.handler.setFormatter(formatter)
    
    async def handle_log(self, entry: LogEntry) -> bool:
        """Handle log entry to file"""
        if not await super().handle_log(entry):
            return False
        
        try:
            # Create log record
            log_record = logging.LogRecord(
                name=entry.component,
                level=entry.level.value,
                pathname="",
                lineno=0,
                msg=self._format_message(entry),
                args=(),
                exc_info=None
            )
            
            with self.lock:
                self.handler.emit(log_record)
            
            return True
        except Exception as e:
            print(f"Error in file handler: {e}")
            return False
    
    def _format_message(self, entry: LogEntry) -> str:
        """Format log message"""
        message_parts = [entry.message]
        
        if entry.category != LogCategory.SYSTEM:
            message_parts.append(f"[{entry.category.value}]")
        
        if entry.correlation_id:
            message_parts.append(f"(ID: {entry.correlation_id[:8]})")
        
        if entry.metadata:
            # Add important metadata
            for key, value in entry.metadata.items():
                if key in ['operation', 'duration', 'error_type']:
                    message_parts.append(f"{key}={value}")
        
        return " ".join(message_parts)


class SimpleConsoleHandler(SimpleLogHandler):
    """Simplified console handler with colors"""
    
    COLORS = {
        LogLevel.DEBUG: '\033[36m',     # Cyan
        LogLevel.INFO: '\033[32m',      # Green
        LogLevel.WARNING: '\033[33m',   # Yellow
        LogLevel.ERROR: '\033[31m',     # Red
        LogLevel.CRITICAL: '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def __init__(self, name: str, config: SimpleLogConfig):
        super().__init__(name, config.log_level)
        self.colored = sys.stderr.isatty()
        self.lock = threading.Lock()
    
    async def handle_log(self, entry: LogEntry) -> bool:
        """Handle log entry to console"""
        if not await super().handle_log(entry):
            return False
        
        try:
            message = self._format_message(entry)
            
            with self.lock:
                print(message, file=sys.stderr if entry.level.value >= LogLevel.WARNING.value else sys.stdout)
            
            return True
        except Exception:
            return False
    
    def _format_message(self, entry: LogEntry) -> str:
        """Format console message"""
        timestamp = entry.timestamp.strftime("%H:%M:%S")
        level_str = entry.level.name.ljust(8)
        
        # Add color if supported
        if self.colored:
            color = self.COLORS.get(entry.level, '')
            level_str = f"{color}{level_str}{self.RESET}"
        
        return f"{timestamp} {level_str} [{entry.component}] {entry.message}"


class SimpleHAHandler(SimpleLogHandler):
    """Simplified Home Assistant logging handler"""
    
    def __init__(self, name: str, config: SimpleLogConfig):
        super().__init__(name, config.log_level)
        self.ha_logger = logging.getLogger("aicleaner")
        self.level_mapping = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL
        }
    
    async def handle_log(self, entry: LogEntry) -> bool:
        """Handle log entry to Home Assistant"""
        if not await super().handle_log(entry):
            return False
        
        try:
            ha_level = self.level_mapping[entry.level]
            message = f"[{entry.component}] {entry.message}"
            
            self.ha_logger.log(ha_level, message, extra={
                'correlation_id': entry.correlation_id,
                'category': entry.category.value
            })
            
            return True
        except Exception:
            return False


class SimpleSecurityHandler(SimpleLogHandler):
    """Simplified security logging handler"""
    
    def __init__(self, name: str, security_log_path: str, config: SimpleLogConfig):
        super().__init__(name, LogLevel.INFO)
        self.security_log_path = Path(security_log_path)
        self.lock = threading.Lock()
        
        # Create security log directory
        self.security_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def handle_log(self, entry: LogEntry) -> bool:
        """Handle security log entry"""
        if not await super().handle_log(entry):
            return False
        
        # Only log security-related entries
        if entry.category != LogCategory.SECURITY:
            return False
        
        try:
            security_entry = {
                "timestamp": entry.timestamp.isoformat(),
                "level": entry.level.name,
                "message": entry.message,
                "component": entry.component,
                "correlation_id": entry.correlation_id,
                "metadata": entry.metadata
            }
            
            with self.lock:
                with open(self.security_log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(security_entry) + '\n')
            
            return True
        except Exception as e:
            print(f"Error in security handler: {e}")
            return False


class SimpleLoggingManager:
    """Simplified logging manager for single-user deployment"""
    
    def __init__(self, config: SimpleLogConfig = None):
        self.config = config or SimpleLogConfig()
        self.handlers: Dict[str, SimpleLogHandler] = {}
        self.log_queue = queue.Queue(maxsize=self.config.buffer_size)
        self.worker_thread = None
        self.shutdown_event = threading.Event()
        self.correlation_counter = 0
        self.correlation_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            "total_messages": 0,
            "messages_by_level": {level: 0 for level in LogLevel},
            "messages_by_category": {category: 0 for category in LogCategory},
            "error_rate": 0.0,
            "last_flush": datetime.now()
        }
        
        # Setup handlers
        self._setup_handlers()
        self._start_worker()
    
    def _setup_handlers(self):
        """Setup log handlers based on configuration"""
        log_dir = Path(self.config.log_directory)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Console handler
        if self.config.enable_console:
            self.handlers["console"] = SimpleConsoleHandler("console", self.config)
        
        # File handler
        if self.config.enable_file:
            self.handlers["file"] = SimpleFileHandler(
                "file", 
                str(log_dir / "aicleaner.log"), 
                self.config
            )
        
        # Home Assistant handler
        if self.config.enable_ha_integration:
            self.handlers["ha"] = SimpleHAHandler("ha", self.config)
        
        # Security handler
        if self.config.enable_security_logging:
            self.handlers["security"] = SimpleSecurityHandler(
                "security", 
                str(log_dir / "security.log"), 
                self.config
            )
    
    def _start_worker(self):
        """Start background worker thread"""
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            name="SimpleLoggingWorker",
            daemon=True
        )
        self.worker_thread.start()
    
    def _worker_loop(self):
        """Main worker loop for processing log entries"""
        while not self.shutdown_event.is_set():
            try:
                try:
                    entry = self.log_queue.get(timeout=self.config.flush_interval)
                except queue.Empty:
                    continue
                
                # Process entry
                asyncio.run(self._process_entry(entry))
                self.log_queue.task_done()
                
            except Exception as e:
                print(f"Error in logging worker: {e}")
    
    async def _process_entry(self, entry: LogEntry):
        """Process a single log entry"""
        try:
            # Update statistics
            self.stats["total_messages"] += 1
            self.stats["messages_by_level"][entry.level] += 1
            self.stats["messages_by_category"][entry.category] += 1
            
            # Calculate error rate
            error_count = (self.stats["messages_by_level"][LogLevel.ERROR] + 
                          self.stats["messages_by_level"][LogLevel.CRITICAL])
            if self.stats["total_messages"] > 0:
                self.stats["error_rate"] = error_count / self.stats["total_messages"]
            
            # Process through handlers
            tasks = []
            for handler in self.handlers.values():
                tasks.append(handler.handle_log(entry))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for alerts
            await self._check_simple_alerts(entry)
            
        except Exception as e:
            print(f"Error processing log entry: {e}")
    
    async def _check_simple_alerts(self, entry: LogEntry):
        """Check for simple alert conditions"""
        # Critical error alert
        if entry.level == LogLevel.CRITICAL:
            print(f"CRITICAL ALERT: {entry.message} in {entry.component}")
        
        # High error rate alert
        if (self.stats["error_rate"] > self.config.error_rate_threshold and 
            self.stats["total_messages"] > 10):
            print(f"HIGH ERROR RATE ALERT: {self.stats['error_rate']:.2%} error rate detected")
        
        # Performance alert
        if ("duration" in entry.metadata and 
            entry.metadata["duration"] > self.config.performance_threshold_ms):
            print(f"PERFORMANCE ALERT: Slow operation ({entry.metadata['duration']}ms) in {entry.component}")
    
    def _get_correlation_id(self) -> str:
        """Get next correlation ID"""
        with self.correlation_lock:
            self.correlation_counter += 1
            return f"c{self.correlation_counter:06d}"
    
    def log(self, level: LogLevel, message: str, component: str = "system", 
            category: LogCategory = LogCategory.SYSTEM, **metadata):
        """Log a message"""
        try:
            entry = LogEntry(
                timestamp=datetime.now(),
                level=level,
                message=message,
                category=category,
                component=component,
                correlation_id=self._get_correlation_id(),
                metadata=metadata
            )
            
            try:
                self.log_queue.put_nowait(entry)
            except queue.Full:
                # Drop oldest entry if queue is full
                try:
                    self.log_queue.get_nowait()
                    self.log_queue.put_nowait(entry)
                except queue.Empty:
                    pass
        except Exception as e:
            print(f"Error logging message: {e}")
    
    def get_logger(self, component: str) -> 'SimpleComponentLogger':
        """Get a component-specific logger"""
        return SimpleComponentLogger(self, component)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        stats = self.stats.copy()
        
        # Add handler stats
        handler_stats = {}
        for name, handler in self.handlers.items():
            handler_stats[name] = {
                "enabled": handler.enabled,
                "message_count": handler.message_count,
                "error_count": handler.error_count,
                "last_message_time": handler.last_message_time
            }
        stats["handlers"] = handler_stats
        
        # Add queue stats
        stats["queue_size"] = self.log_queue.qsize()
        stats["queue_max_size"] = self.config.buffer_size
        
        return stats
    
    def shutdown(self):
        """Shutdown logging manager"""
        self.shutdown_event.set()
        
        # Drain queue
        while not self.log_queue.empty():
            try:
                self.log_queue.get_nowait()
            except queue.Empty:
                break
        
        # Wait for worker to finish
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=3.0)


class SimpleComponentLogger:
    """Simplified component-specific logger"""
    
    def __init__(self, manager: SimpleLoggingManager, component: str):
        self.manager = manager
        self.component = component
    
    def debug(self, message: str, **metadata):
        """Log debug message"""
        self.manager.log(LogLevel.DEBUG, message, self.component, LogCategory.SYSTEM, **metadata)
    
    def info(self, message: str, **metadata):
        """Log info message"""
        self.manager.log(LogLevel.INFO, message, self.component, LogCategory.SYSTEM, **metadata)
    
    def warning(self, message: str, **metadata):
        """Log warning message"""
        self.manager.log(LogLevel.WARNING, message, self.component, LogCategory.SYSTEM, **metadata)
    
    def error(self, message: str, **metadata):
        """Log error message"""
        self.manager.log(LogLevel.ERROR, message, self.component, LogCategory.ERROR, **metadata)
    
    def critical(self, message: str, **metadata):
        """Log critical message"""
        self.manager.log(LogLevel.CRITICAL, message, self.component, LogCategory.ERROR, **metadata)
    
    def security(self, message: str, **metadata):
        """Log security message"""
        self.manager.log(LogLevel.WARNING, message, self.component, LogCategory.SECURITY, **metadata)
    
    def performance(self, message: str, duration: int = None, **metadata):
        """Log performance message"""
        if duration:
            metadata["duration"] = duration
        self.manager.log(LogLevel.INFO, message, self.component, LogCategory.PERFORMANCE, **metadata)


# Global instance
_simple_logging_manager: Optional[SimpleLoggingManager] = None


def get_simple_logger(component: str = "system") -> SimpleComponentLogger:
    """Get simplified component logger"""
    global _simple_logging_manager
    if _simple_logging_manager is None:
        _simple_logging_manager = SimpleLoggingManager()
    return _simple_logging_manager.get_logger(component)


def get_logging_stats() -> Dict[str, Any]:
    """Get logging statistics"""
    global _simple_logging_manager
    if _simple_logging_manager is None:
        return {}
    return _simple_logging_manager.get_stats()


def shutdown_logging():
    """Shutdown logging system"""
    global _simple_logging_manager
    if _simple_logging_manager is not None:
        _simple_logging_manager.shutdown()
        _simple_logging_manager = None


# Convenience functions
def log_info(message: str, component: str = "system", **metadata):
    """Log info message"""
    get_simple_logger(component).info(message, **metadata)


def log_error(message: str, component: str = "system", **metadata):
    """Log error message"""
    get_simple_logger(component).error(message, **metadata)


def log_security(message: str, component: str = "security", **metadata):
    """Log security event"""
    get_simple_logger(component).security(message, **metadata)


def log_performance(message: str, duration: int = None, component: str = "performance", **metadata):
    """Log performance event"""
    get_simple_logger(component).performance(message, duration, **metadata)