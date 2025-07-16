"""
Enhanced Logging System for AICleaner v3
Phase 1C: Logging System Enhancement

This module provides a comprehensive structured logging system with multiple handlers,
advanced filtering, log rotation, security logging, performance monitoring,
and Home Assistant integration.

Key Features:
- Multiple log handlers (file, console, Home Assistant, external)
- Advanced log formatting and filtering
- Log rotation and archival
- Security logging and audit trails
- Performance monitoring integration
- Log analysis and alerting
- Home Assistant logging integration
- Real-time log streaming
- Log aggregation and correlation
"""

import asyncio
import json
import logging
import logging.handlers
import gzip
import shutil
import sys
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Set
from urllib.parse import urlparse
import socket
import traceback
import re
import hashlib
import os
import stat
from contextlib import contextmanager
import queue

# Performance imports
import psutil
import memory_profiler


class LogLevel(Enum):
    """Enhanced log levels"""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    SECURITY = 60
    AUDIT = 70


class LogCategory(Enum):
    """Log categories for classification"""
    SYSTEM = "system"
    CONFIGURATION = "configuration"
    AI_PROVIDER = "ai_provider"
    PERFORMANCE = "performance"
    SECURITY = "security"
    AUDIT = "audit"
    USER_ACTION = "user_action"
    INTEGRATION = "integration"
    HEALTH = "health"
    ERROR = "error"
    DEBUG = "debug"


class LogOrigin(Enum):
    """Log origin sources"""
    CORE = "core"
    AI_ENGINE = "ai_engine"
    HOME_ASSISTANT = "home_assistant"
    USER_INTERFACE = "user_interface"
    API = "api"
    SCHEDULER = "scheduler"
    NOTIFICATION = "notification"
    EXTERNAL = "external"


@dataclass
class LogContext:
    """Enhanced log context information"""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    component: Optional[str] = None
    operation: Optional[str] = None
    transaction_id: Optional[str] = None
    origin: LogOrigin = LogOrigin.CORE
    category: LogCategory = LogCategory.SYSTEM
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None
    span_id: Optional[str] = None


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: datetime
    level: LogLevel
    message: str
    context: LogContext
    logger_name: str
    module: str
    function: str
    line_number: int
    thread_id: int
    thread_name: str
    process_id: int
    exception_info: Optional[str] = None
    stack_trace: Optional[str] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    security_context: Optional[Dict[str, Any]] = None


@dataclass
class LogFilter:
    """Log filtering configuration"""
    min_level: LogLevel = LogLevel.INFO
    max_level: LogLevel = LogLevel.CRITICAL
    categories: Optional[Set[LogCategory]] = None
    origins: Optional[Set[LogOrigin]] = None
    components: Optional[Set[str]] = None
    tags: Optional[Set[str]] = None
    regex_pattern: Optional[str] = None
    exclude_patterns: Optional[List[str]] = None
    time_range: Optional[Tuple[datetime, datetime]] = None


class LogHandler(ABC):
    """Abstract base class for log handlers"""
    
    def __init__(self, name: str, log_filter: LogFilter = None):
        self.name = name
        self.filter = log_filter or LogFilter()
        self.enabled = True
        self.stats = {
            "messages_processed": 0,
            "messages_filtered": 0,
            "errors": 0,
            "last_message_time": None
        }
    
    @abstractmethod
    async def handle_log(self, entry: LogEntry) -> bool:
        """Handle a log entry"""
        pass
    
    def should_process(self, entry: LogEntry) -> bool:
        """Check if log entry should be processed by this handler"""
        if not self.enabled:
            return False
        
        # Level filtering
        if entry.level.value < self.filter.min_level.value:
            return False
        if entry.level.value > self.filter.max_level.value:
            return False
        
        # Category filtering
        if (self.filter.categories and 
            entry.context.category not in self.filter.categories):
            return False
        
        # Origin filtering
        if (self.filter.origins and 
            entry.context.origin not in self.filter.origins):
            return False
        
        # Component filtering
        if (self.filter.components and entry.context.component and
            entry.context.component not in self.filter.components):
            return False
        
        # Tag filtering
        if (self.filter.tags and 
            not entry.context.tags.intersection(self.filter.tags)):
            return False
        
        # Regex filtering
        if self.filter.regex_pattern:
            if not re.search(self.filter.regex_pattern, entry.message):
                return False
        
        # Exclude patterns
        if self.filter.exclude_patterns:
            for pattern in self.filter.exclude_patterns:
                if re.search(pattern, entry.message):
                    return False
        
        # Time range filtering
        if self.filter.time_range:
            start_time, end_time = self.filter.time_range
            if not (start_time <= entry.timestamp <= end_time):
                return False
        
        return True


class FileLogHandler(LogHandler):
    """File-based log handler with rotation"""
    
    def __init__(self, name: str, file_path: str, max_size: int = 10*1024*1024,
                 backup_count: int = 5, compression: bool = True,
                 log_filter: LogFilter = None):
        super().__init__(name, log_filter)
        self.file_path = Path(file_path)
        self.max_size = max_size
        self.backup_count = backup_count
        self.compression = compression
        self.current_size = 0
        self.lock = threading.Lock()
        
        # Create directory if it doesn't exist
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Set up rotating file handler
        self._setup_rotation()
    
    def _setup_rotation(self):
        """Setup log rotation"""
        if self.file_path.exists():
            self.current_size = self.file_path.stat().st_size
    
    async def handle_log(self, entry: LogEntry) -> bool:
        """Handle log entry to file"""
        try:
            if not self.should_process(entry):
                self.stats["messages_filtered"] += 1
                return False
            
            # Format log entry
            log_line = self._format_entry(entry)
            
            with self.lock:
                # Check if rotation is needed
                if self.current_size + len(log_line.encode()) > self.max_size:
                    await self._rotate_logs()
                
                # Write to file
                with open(self.file_path, 'a', encoding='utf-8') as f:
                    f.write(log_line + '\n')
                    f.flush()
                
                self.current_size += len(log_line.encode())
            
            self.stats["messages_processed"] += 1
            self.stats["last_message_time"] = datetime.now()
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Error in FileLogHandler: {e}")  # Fallback logging
            return False
    
    def _format_entry(self, entry: LogEntry) -> str:
        """Format log entry for file output"""
        return json.dumps({
            "timestamp": entry.timestamp.isoformat(),
            "level": entry.level.name,
            "message": entry.message,
            "logger": entry.logger_name,
            "module": entry.module,
            "function": entry.function,
            "line": entry.line_number,
            "thread": entry.thread_name,
            "process": entry.process_id,
            "correlation_id": entry.context.correlation_id,
            "session_id": entry.context.session_id,
            "component": entry.context.component,
            "operation": entry.context.operation,
            "origin": entry.context.origin.value,
            "category": entry.context.category.value,
            "tags": list(entry.context.tags),
            "metadata": entry.context.metadata,
            "exception": entry.exception_info,
            "performance": entry.performance_metrics,
            "security": entry.security_context
        }, separators=(',', ':'))
    
    async def _rotate_logs(self):
        """Rotate log files"""
        try:
            # Move current file to backup
            for i in range(self.backup_count - 1, 0, -1):
                old_backup = self.file_path.with_suffix(f'.{i}.log')
                new_backup = self.file_path.with_suffix(f'.{i+1}.log')
                
                if old_backup.exists():
                    if new_backup.exists():
                        new_backup.unlink()
                    old_backup.rename(new_backup)
                    
                    # Compress if enabled
                    if self.compression and i == self.backup_count - 1:
                        await self._compress_file(new_backup)
            
            # Move current file to .1
            if self.file_path.exists():
                backup_file = self.file_path.with_suffix('.1.log')
                if backup_file.exists():
                    backup_file.unlink()
                self.file_path.rename(backup_file)
            
            self.current_size = 0
            
        except Exception as e:
            print(f"Error rotating logs: {e}")
    
    async def _compress_file(self, file_path: Path):
        """Compress log file"""
        try:
            compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            file_path.unlink()
        except Exception as e:
            print(f"Error compressing file {file_path}: {e}")


class ConsoleLogHandler(LogHandler):
    """Console log handler with color support"""
    
    COLOR_CODES = {
        LogLevel.TRACE: '\033[90m',     # Bright black
        LogLevel.DEBUG: '\033[36m',     # Cyan
        LogLevel.INFO: '\033[32m',      # Green
        LogLevel.WARNING: '\033[33m',   # Yellow
        LogLevel.ERROR: '\033[31m',     # Red
        LogLevel.CRITICAL: '\033[35m',  # Magenta
        LogLevel.SECURITY: '\033[41m',  # Red background
        LogLevel.AUDIT: '\033[44m',     # Blue background
    }
    RESET_CODE = '\033[0m'
    
    def __init__(self, name: str, colored: bool = True, log_filter: LogFilter = None):
        super().__init__(name, log_filter)
        self.colored = colored
        self.lock = threading.Lock()
    
    async def handle_log(self, entry: LogEntry) -> bool:
        """Handle log entry to console"""
        try:
            if not self.should_process(entry):
                self.stats["messages_filtered"] += 1
                return False
            
            # Format log entry
            log_line = self._format_entry(entry)
            
            with self.lock:
                print(log_line, file=sys.stderr if entry.level.value >= LogLevel.WARNING.value else sys.stdout)
            
            self.stats["messages_processed"] += 1
            self.stats["last_message_time"] = datetime.now()
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            return False
    
    def _format_entry(self, entry: LogEntry) -> str:
        """Format log entry for console output"""
        # Base format
        timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        level_str = entry.level.name.ljust(8)
        
        # Add color if enabled
        if self.colored and sys.stderr.isatty():
            color = self.COLOR_CODES.get(entry.level, '')
            level_str = f"{color}{level_str}{self.RESET_CODE}"
        
        # Build log line
        log_parts = [
            timestamp,
            level_str,
            f"[{entry.context.component or entry.module}]",
            entry.message
        ]
        
        # Add correlation ID for debugging
        if entry.context.correlation_id and entry.level.value <= LogLevel.DEBUG.value:
            log_parts.append(f"(ID: {entry.context.correlation_id[:8]})")
        
        return " ".join(log_parts)


class HomeAssistantLogHandler(LogHandler):
    """Home Assistant logging integration handler"""
    
    def __init__(self, name: str, ha_logger_name: str = "aicleaner",
                 log_filter: LogFilter = None):
        super().__init__(name, log_filter)
        self.ha_logger = logging.getLogger(ha_logger_name)
        self.level_mapping = {
            LogLevel.TRACE: logging.DEBUG,
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
            LogLevel.SECURITY: logging.ERROR,
            LogLevel.AUDIT: logging.INFO
        }
    
    async def handle_log(self, entry: LogEntry) -> bool:
        """Handle log entry to Home Assistant logger"""
        try:
            if not self.should_process(entry):
                self.stats["messages_filtered"] += 1
                return False
            
            # Map to HA log level
            ha_level = self.level_mapping.get(entry.level, logging.INFO)
            
            # Format message for HA
            message = self._format_entry(entry)
            
            # Log to HA
            self.ha_logger.log(ha_level, message, extra={
                'correlation_id': entry.context.correlation_id,
                'component': entry.context.component,
                'operation': entry.context.operation,
                'category': entry.context.category.value,
                'origin': entry.context.origin.value
            })
            
            self.stats["messages_processed"] += 1
            self.stats["last_message_time"] = datetime.now()
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            return False
    
    def _format_entry(self, entry: LogEntry) -> str:
        """Format log entry for Home Assistant"""
        message_parts = [entry.message]
        
        if entry.context.component:
            message_parts.append(f"[{entry.context.component}]")
        
        if entry.context.operation:
            message_parts.append(f"({entry.context.operation})")
        
        return " ".join(message_parts)


class SecurityLogHandler(LogHandler):
    """Security-focused log handler with tamper detection"""
    
    def __init__(self, name: str, security_log_path: str, 
                 encryption_key: Optional[str] = None,
                 log_filter: LogFilter = None):
        super().__init__(name, log_filter)
        self.security_log_path = Path(security_log_path)
        self.encryption_key = encryption_key
        self.hash_chain = []
        self.lock = threading.Lock()
        
        # Create security log directory with restricted permissions
        self.security_log_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        # Initialize hash chain
        self._init_hash_chain()
    
    def _init_hash_chain(self):
        """Initialize hash chain for tamper detection"""
        try:
            if self.security_log_path.exists():
                # Read existing hash chain
                with open(self.security_log_path, 'r') as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line)
                            if 'hash' in entry:
                                self.hash_chain.append(entry['hash'])
        except Exception:
            # Start fresh if file is corrupted
            self.hash_chain = []
    
    async def handle_log(self, entry: LogEntry) -> bool:
        """Handle security log entry with integrity protection"""
        try:
            if not self.should_process(entry):
                self.stats["messages_filtered"] += 1
                return False
            
            # Only log security-relevant entries
            if entry.context.category not in [LogCategory.SECURITY, LogCategory.AUDIT]:
                return False
            
            # Create security log entry
            security_entry = self._create_security_entry(entry)
            
            with self.lock:
                # Write with restricted permissions
                with open(self.security_log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(security_entry) + '\n')
                    f.flush()
                
                # Set restrictive permissions
                os.chmod(self.security_log_path, stat.S_IRUSR | stat.S_IWUSR)
            
            self.stats["messages_processed"] += 1
            self.stats["last_message_time"] = datetime.now()
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            return False
    
    def _create_security_entry(self, entry: LogEntry) -> Dict[str, Any]:
        """Create security log entry with integrity hash"""
        # Base security entry
        security_entry = {
            "timestamp": entry.timestamp.isoformat(),
            "level": entry.level.name,
            "message": entry.message,
            "correlation_id": entry.context.correlation_id,
            "component": entry.context.component,
            "operation": entry.context.operation,
            "category": entry.context.category.value,
            "user_id": entry.context.user_id,
            "session_id": entry.context.session_id,
            "security_context": entry.security_context,
            "metadata": entry.context.metadata
        }
        
        # Calculate hash for integrity
        entry_str = json.dumps(security_entry, sort_keys=True)
        previous_hash = self.hash_chain[-1] if self.hash_chain else "genesis"
        current_hash = hashlib.sha256(f"{previous_hash}{entry_str}".encode()).hexdigest()
        
        security_entry["hash"] = current_hash
        security_entry["previous_hash"] = previous_hash
        
        self.hash_chain.append(current_hash)
        
        return security_entry


class PerformanceLogHandler(LogHandler):
    """Performance monitoring log handler"""
    
    def __init__(self, name: str, performance_log_path: str,
                 log_filter: LogFilter = None):
        super().__init__(name, log_filter)
        self.performance_log_path = Path(performance_log_path)
        self.metrics_buffer = deque(maxlen=1000)
        self.lock = threading.Lock()
        
        # Create performance log directory
        self.performance_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def handle_log(self, entry: LogEntry) -> bool:
        """Handle performance log entry"""
        try:
            if not self.should_process(entry):
                self.stats["messages_filtered"] += 1
                return False
            
            # Only log entries with performance metrics
            if not entry.performance_metrics:
                return False
            
            # Create performance entry
            perf_entry = self._create_performance_entry(entry)
            
            with self.lock:
                # Add to buffer
                self.metrics_buffer.append(perf_entry)
                
                # Write to file
                with open(self.performance_log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(perf_entry) + '\n')
            
            self.stats["messages_processed"] += 1
            self.stats["last_message_time"] = datetime.now()
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            return False
    
    def _create_performance_entry(self, entry: LogEntry) -> Dict[str, Any]:
        """Create performance log entry"""
        return {
            "timestamp": entry.timestamp.isoformat(),
            "correlation_id": entry.context.correlation_id,
            "component": entry.context.component,
            "operation": entry.context.operation,
            "metrics": entry.performance_metrics,
            "message": entry.message
        }
    
    def get_performance_summary(self, time_window: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Get performance summary for time window"""
        cutoff_time = datetime.now() - time_window
        
        relevant_entries = [
            entry for entry in self.metrics_buffer
            if datetime.fromisoformat(entry['timestamp']) > cutoff_time
        ]
        
        if not relevant_entries:
            return {"message": "No performance data available"}
        
        # Calculate aggregated metrics
        summary = {
            "time_window": str(time_window),
            "entry_count": len(relevant_entries),
            "components": defaultdict(int),
            "operations": defaultdict(int),
            "avg_response_time": 0,
            "max_response_time": 0,
            "min_response_time": float('inf')
        }
        
        total_response_time = 0
        response_time_count = 0
        
        for entry in relevant_entries:
            # Count components and operations
            if entry.get('component'):
                summary["components"][entry['component']] += 1
            if entry.get('operation'):
                summary["operations"][entry['operation']] += 1
            
            # Aggregate response times
            metrics = entry.get('metrics', {})
            if 'response_time' in metrics:
                rt = metrics['response_time']
                total_response_time += rt
                response_time_count += 1
                summary["max_response_time"] = max(summary["max_response_time"], rt)
                summary["min_response_time"] = min(summary["min_response_time"], rt)
        
        if response_time_count > 0:
            summary["avg_response_time"] = total_response_time / response_time_count
            if summary["min_response_time"] == float('inf'):
                summary["min_response_time"] = 0
        
        return summary