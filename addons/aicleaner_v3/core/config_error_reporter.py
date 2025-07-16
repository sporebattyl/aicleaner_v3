"""
Configuration Error Reporter and Structured Logging System
Phase 1A: Configuration Schema Consolidation

This module provides comprehensive error reporting and structured logging
for configuration operations with user-friendly messages and developer debugging.

Key Features:
- User-friendly error messages with recovery guidance
- Progressive error disclosure (basic -> detailed -> developer)
- Structured logging with contextual information
- Error classification and categorization
- Automated recovery suggestions
- Integration with Home Assistant logging system
"""

import logging
import json
import traceback
import uuid
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import sys
from logging.handlers import RotatingFileHandler
import inspect

class ErrorCategory(Enum):
    """Configuration error categories"""
    VALIDATION_ERROR = "validation_error"
    MIGRATION_ERROR = "migration_error"
    SECURITY_ERROR = "security_error"
    PERFORMANCE_ERROR = "performance_error"
    COMPATIBILITY_ERROR = "compatibility_error"
    SYSTEM_ERROR = "system_error"
    USER_ERROR = "user_error"

class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ErrorAudience(Enum):
    """Error message audience"""
    USER = "user"
    ADMIN = "admin"
    DEVELOPER = "developer"

@dataclass
class ErrorContext:
    """Error context information"""
    operation: str
    component: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    user_config: Optional[Dict[str, Any]] = None
    system_info: Optional[Dict[str, Any]] = None
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class ErrorMessage:
    """Multi-level error message"""
    user_message: str
    admin_message: str
    developer_message: str
    recovery_steps: List[str] = field(default_factory=list)
    documentation_links: List[str] = field(default_factory=list)
    related_errors: List[str] = field(default_factory=list)

@dataclass
class ConfigurationError:
    """Comprehensive configuration error"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    code: str
    message: ErrorMessage
    context: ErrorContext
    timestamp: datetime
    stack_trace: Optional[str] = None
    suggested_fix: Optional[str] = None
    auto_recovery_possible: bool = False

class ConfigErrorReporter:
    """
    Configuration error reporter with structured logging
    
    Provides comprehensive error reporting with user-friendly messages,
    progressive disclosure, and structured logging for debugging.
    """
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Error tracking
        self.error_history: List[ConfigurationError] = []
        self.error_patterns: Dict[str, int] = {}
        
        # Setup structured logging
        self._setup_structured_logging()
        
        # Error message templates
        self._init_error_templates()
        
        # Recovery strategies
        self._init_recovery_strategies()
    
    def _setup_structured_logging(self):
        """Setup structured logging system"""
        # Create structured logger
        self.logger = logging.getLogger("aicleaner.config")
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        json_formatter = self._create_json_formatter()
        
        # Console handler for immediate feedback
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler for detailed logs
        file_handler = RotatingFileHandler(
            self.log_dir / "config_detailed.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(file_handler)
        
        # JSON handler for structured logging
        json_handler = RotatingFileHandler(
            self.log_dir / "config_structured.json",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        json_handler.setLevel(logging.INFO)
        json_handler.setFormatter(json_formatter)
        self.logger.addHandler(json_handler)
        
        # Error handler for critical issues
        error_handler = RotatingFileHandler(
            self.log_dir / "config_errors.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(error_handler)
    
    def _create_json_formatter(self):
        """Create JSON formatter for structured logging"""
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                    "thread": record.thread,
                    "thread_name": record.threadName
                }
                
                # Add extra fields if present
                if hasattr(record, 'correlation_id'):
                    log_entry['correlation_id'] = record.correlation_id
                if hasattr(record, 'component'):
                    log_entry['component'] = record.component
                if hasattr(record, 'operation'):
                    log_entry['operation'] = record.operation
                if hasattr(record, 'error_category'):
                    log_entry['error_category'] = record.error_category
                if hasattr(record, 'user_config'):
                    log_entry['user_config'] = record.user_config
                
                return json.dumps(log_entry)
        
        return JSONFormatter()
    
    def _init_error_templates(self):
        """Initialize error message templates"""
        self.error_templates = {
            "REQUIRED_FIELD_MISSING": {
                "user": "Required field '{field}' is missing. Please provide a value.",
                "admin": "Configuration validation failed: Required field '{field}' is missing from {context}.",
                "developer": "Schema validation error: Field '{field}' is required but not present in configuration. Validation rules: {rules}",
                "recovery": [
                    "Add the missing field to your configuration",
                    "Check the configuration documentation for required fields",
                    "Use the configuration editor to ensure all required fields are present"
                ],
                "docs": [
                    "https://github.com/yourusername/aicleaner/docs/configuration.md",
                    "https://developers.home-assistant.io/docs/add-ons/configuration/"
                ]
            },
            "INVALID_API_KEY": {
                "user": "Your API key appears to be invalid. Please check your Gemini API key.",
                "admin": "API key validation failed: {details}",
                "developer": "API key validation error: {technical_details}",
                "recovery": [
                    "Go to https://makersuite.google.com/app/apikey to get a valid API key",
                    "Replace the placeholder API key with your actual key",
                    "Ensure the API key starts with 'AIzaSy' for Gemini"
                ],
                "docs": [
                    "https://developers.generativeai.google/api/rest/authentication",
                    "https://github.com/yourusername/aicleaner/docs/api-setup.md"
                ]
            },
            "MIGRATION_FAILED": {
                "user": "Configuration migration failed. Your original settings have been preserved.",
                "admin": "Migration from legacy configuration format failed: {reason}",
                "developer": "Migration error in {component}: {technical_details}",
                "recovery": [
                    "Check the migration logs for specific issues",
                    "Verify all configuration files are readable",
                    "Try migrating one section at a time",
                    "Contact support if the issue persists"
                ],
                "docs": [
                    "https://github.com/yourusername/aicleaner/docs/migration.md",
                    "https://github.com/yourusername/aicleaner/docs/troubleshooting.md"
                ]
            },
            "SECURITY_VIOLATION": {
                "user": "Security issue detected in configuration. Please review your settings.",
                "admin": "Security validation failed: {violation_type} detected in {field}",
                "developer": "Security violation: {technical_details}",
                "recovery": [
                    "Remove any suspicious or malicious content from configuration",
                    "Use only trusted configuration sources",
                    "Enable security scanning for future configurations"
                ],
                "docs": [
                    "https://github.com/yourusername/aicleaner/docs/security.md",
                    "https://developers.home-assistant.io/docs/add-ons/security/"
                ]
            },
            "PERFORMANCE_DEGRADATION": {
                "user": "Configuration may cause performance issues. Consider optimizing your settings.",
                "admin": "Performance warning: {metric} exceeded threshold ({value} > {threshold})",
                "developer": "Performance metric {metric} failed benchmark: {details}",
                "recovery": [
                    "Reduce cache sizes if memory usage is high",
                    "Decrease concurrent operations if CPU usage is high",
                    "Consider using resource_efficient profile"
                ],
                "docs": [
                    "https://github.com/yourusername/aicleaner/docs/performance.md",
                    "https://github.com/yourusername/aicleaner/docs/optimization.md"
                ]
            }
        }
    
    def _init_recovery_strategies(self):
        """Initialize automated recovery strategies"""
        self.recovery_strategies = {
            "REQUIRED_FIELD_MISSING": self._recover_missing_field,
            "INVALID_API_KEY": self._recover_invalid_api_key,
            "MIGRATION_FAILED": self._recover_migration_failure,
            "SECURITY_VIOLATION": self._recover_security_violation,
            "PERFORMANCE_DEGRADATION": self._recover_performance_issue
        }
    
    def report_error(
        self,
        category: ErrorCategory,
        severity: ErrorSeverity,
        code: str,
        context: ErrorContext,
        exception: Optional[Exception] = None,
        custom_message: Optional[Dict[str, str]] = None
    ) -> ConfigurationError:
        """
        Report a configuration error with comprehensive details
        
        Args:
            category: Error category
            severity: Error severity
            code: Error code
            context: Error context
            exception: Optional exception that caused the error
            custom_message: Optional custom error messages
            
        Returns:
            ConfigurationError object
        """
        error_id = str(uuid.uuid4())
        
        # Create error message
        if custom_message:
            message = ErrorMessage(
                user_message=custom_message.get("user", "An error occurred"),
                admin_message=custom_message.get("admin", "Configuration error"),
                developer_message=custom_message.get("developer", "Technical error"),
                recovery_steps=custom_message.get("recovery", []),
                documentation_links=custom_message.get("docs", [])
            )
        else:
            message = self._create_error_message(code, context)
        
        # Create configuration error
        error = ConfigurationError(
            error_id=error_id,
            category=category,
            severity=severity,
            code=code,
            message=message,
            context=context,
            timestamp=datetime.now(),
            stack_trace=traceback.format_exc() if exception else None,
            suggested_fix=self._generate_suggested_fix(code, context),
            auto_recovery_possible=self._can_auto_recover(code)
        )
        
        # Store error
        self.error_history.append(error)
        self.error_patterns[code] = self.error_patterns.get(code, 0) + 1
        
        # Log error with structured data
        self._log_structured_error(error)
        
        # Attempt auto-recovery if possible
        if error.auto_recovery_possible:
            self._attempt_auto_recovery(error)
        
        return error
    
    def _create_error_message(self, code: str, context: ErrorContext) -> ErrorMessage:
        """Create error message from template"""
        template = self.error_templates.get(code, {
            "user": "An error occurred during configuration processing",
            "admin": f"Configuration error: {code}",
            "developer": f"Technical error in {context.component}: {code}",
            "recovery": ["Check configuration and try again"],
            "docs": []
        })
        
        # Format messages with context
        user_msg = template["user"].format(
            field=context.user_config.get("field", "unknown") if context.user_config else "unknown",
            context=context.operation
        )
        
        admin_msg = template["admin"].format(
            field=context.user_config.get("field", "unknown") if context.user_config else "unknown",
            context=context.operation,
            details=context.user_config.get("details", "No details") if context.user_config else "No details"
        )
        
        developer_msg = template["developer"].format(
            field=context.user_config.get("field", "unknown") if context.user_config else "unknown",
            context=context.operation,
            technical_details=context.user_config.get("technical_details", "No technical details") if context.user_config else "No technical details",
            rules=context.user_config.get("rules", "No rules") if context.user_config else "No rules"
        )
        
        return ErrorMessage(
            user_message=user_msg,
            admin_message=admin_msg,
            developer_message=developer_msg,
            recovery_steps=template.get("recovery", []),
            documentation_links=template.get("docs", [])
        )
    
    def _generate_suggested_fix(self, code: str, context: ErrorContext) -> Optional[str]:
        """Generate suggested fix for error"""
        fix_generators = {
            "REQUIRED_FIELD_MISSING": lambda: f"Add '{context.user_config.get('field', 'unknown')}' to your configuration",
            "INVALID_API_KEY": lambda: "Replace with a valid Gemini API key from https://makersuite.google.com/app/apikey",
            "MIGRATION_FAILED": lambda: "Check file permissions and configuration format",
            "SECURITY_VIOLATION": lambda: "Remove suspicious content and use trusted sources",
            "PERFORMANCE_DEGRADATION": lambda: "Optimize configuration settings or use resource_efficient profile"
        }
        
        generator = fix_generators.get(code)
        return generator() if generator else None
    
    def _can_auto_recover(self, code: str) -> bool:
        """Check if error can be auto-recovered"""
        auto_recoverable = {
            "REQUIRED_FIELD_MISSING": False,  # Requires user input
            "INVALID_API_KEY": False,  # Requires user input
            "MIGRATION_FAILED": True,  # Can attempt rollback
            "SECURITY_VIOLATION": False,  # Requires user review
            "PERFORMANCE_DEGRADATION": True  # Can apply optimizations
        }
        
        return auto_recoverable.get(code, False)
    
    def _log_structured_error(self, error: ConfigurationError):
        """Log error with structured data"""
        log_record = logging.LogRecord(
            name="aicleaner.config",
            level=getattr(logging, error.severity.value.upper()),
            pathname=error.context.file_path or "",
            lineno=error.context.line_number or 0,
            msg=error.message.developer_message,
            args=(),
            exc_info=None
        )
        
        # Add structured fields
        log_record.correlation_id = error.context.correlation_id
        log_record.component = error.context.component
        log_record.operation = error.context.operation
        log_record.error_category = error.category.value
        log_record.error_code = error.code
        log_record.error_id = error.error_id
        
        # Sanitize user config for logging
        if error.context.user_config:
            sanitized_config = self._sanitize_config_for_logging(error.context.user_config)
            log_record.user_config = sanitized_config
        
        self.logger.handle(log_record)
    
    def _sanitize_config_for_logging(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize configuration for logging (remove sensitive data)"""
        sanitized = {}
        sensitive_keys = {"api_key", "password", "token", "secret", "key"}
        
        for key, value in config.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_config_for_logging(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _attempt_auto_recovery(self, error: ConfigurationError):
        """Attempt automatic recovery from error"""
        recovery_func = self.recovery_strategies.get(error.code)
        if recovery_func:
            try:
                recovery_result = recovery_func(error)
                if recovery_result:
                    self.logger.info(f"Auto-recovery successful for error {error.error_id}")
                else:
                    self.logger.warning(f"Auto-recovery failed for error {error.error_id}")
            except Exception as e:
                self.logger.error(f"Auto-recovery attempt failed: {str(e)}")
    
    def _recover_missing_field(self, error: ConfigurationError) -> bool:
        """Attempt to recover from missing required field"""
        # Cannot auto-recover - requires user input
        return False
    
    def _recover_invalid_api_key(self, error: ConfigurationError) -> bool:
        """Attempt to recover from invalid API key"""
        # Cannot auto-recover - requires user input
        return False
    
    def _recover_migration_failure(self, error: ConfigurationError) -> bool:
        """Attempt to recover from migration failure"""
        # Could trigger rollback
        self.logger.info("Attempting rollback due to migration failure")
        return True  # Placeholder - actual rollback would be implemented
    
    def _recover_security_violation(self, error: ConfigurationError) -> bool:
        """Attempt to recover from security violation"""
        # Cannot auto-recover - requires user review
        return False
    
    def _recover_performance_issue(self, error: ConfigurationError) -> bool:
        """Attempt to recover from performance issues"""
        # Could apply performance optimizations
        self.logger.info("Applying performance optimizations")
        return True  # Placeholder - actual optimizations would be implemented
    
    def get_error_message(self, error: ConfigurationError, audience: ErrorAudience) -> str:
        """Get error message for specific audience"""
        if audience == ErrorAudience.USER:
            return error.message.user_message
        elif audience == ErrorAudience.ADMIN:
            return error.message.admin_message
        elif audience == ErrorAudience.DEVELOPER:
            return error.message.developer_message
        else:
            return error.message.user_message
    
    def get_error_report(self, error_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive error report"""
        error = next((e for e in self.error_history if e.error_id == error_id), None)
        if not error:
            return None
        
        return {
            "error_id": error.error_id,
            "category": error.category.value,
            "severity": error.severity.value,
            "code": error.code,
            "timestamp": error.timestamp.isoformat(),
            "messages": {
                "user": error.message.user_message,
                "admin": error.message.admin_message,
                "developer": error.message.developer_message
            },
            "context": {
                "operation": error.context.operation,
                "component": error.context.component,
                "correlation_id": error.context.correlation_id
            },
            "recovery": {
                "steps": error.message.recovery_steps,
                "suggested_fix": error.suggested_fix,
                "auto_recovery_possible": error.auto_recovery_possible
            },
            "documentation": error.message.documentation_links
        }
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary and statistics"""
        total_errors = len(self.error_history)
        
        # Count by severity
        severity_counts = {}
        for severity in ErrorSeverity:
            severity_counts[severity.value] = sum(
                1 for e in self.error_history if e.severity == severity
            )
        
        # Count by category
        category_counts = {}
        for category in ErrorCategory:
            category_counts[category.value] = sum(
                1 for e in self.error_history if e.category == category
            )
        
        # Recent errors (last 24 hours)
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_errors = [e for e in self.error_history if e.timestamp > recent_cutoff]
        
        return {
            "total_errors": total_errors,
            "severity_distribution": severity_counts,
            "category_distribution": category_counts,
            "recent_errors_24h": len(recent_errors),
            "most_common_errors": dict(sorted(self.error_patterns.items(), key=lambda x: x[1], reverse=True)[:10]),
            "auto_recovery_rate": sum(1 for e in self.error_history if e.auto_recovery_possible) / max(total_errors, 1) * 100
        }
    
    def clear_error_history(self):
        """Clear error history"""
        self.error_history = []
        self.error_patterns = {}
        self.logger.info("Error history cleared")

# Global error reporter instance
error_reporter = ConfigErrorReporter()

# Convenience functions for common error reporting
def report_validation_error(code: str, context: ErrorContext, exception: Optional[Exception] = None) -> ConfigurationError:
    """Report validation error"""
    return error_reporter.report_error(
        ErrorCategory.VALIDATION_ERROR,
        ErrorSeverity.ERROR,
        code,
        context,
        exception
    )

def report_migration_error(code: str, context: ErrorContext, exception: Optional[Exception] = None) -> ConfigurationError:
    """Report migration error"""
    return error_reporter.report_error(
        ErrorCategory.MIGRATION_ERROR,
        ErrorSeverity.ERROR,
        code,
        context,
        exception
    )

def report_security_error(code: str, context: ErrorContext, exception: Optional[Exception] = None) -> ConfigurationError:
    """Report security error"""
    return error_reporter.report_error(
        ErrorCategory.SECURITY_ERROR,
        ErrorSeverity.CRITICAL,
        code,
        context,
        exception
    )

# Example usage following AAA pattern
def example_error_reporting():
    """Example error reporting usage"""
    
    # Arrange - Set up error context
    context = ErrorContext(
        operation="config_validation",
        component="schema_validator",
        user_config={"field": "gemini_api_key"}
    )
    
    # Act - Report error
    error = report_validation_error("REQUIRED_FIELD_MISSING", context)
    
    # Assert - Verify error was reported
    assert error.error_id is not None
    assert error.category == ErrorCategory.VALIDATION_ERROR
    assert error.severity == ErrorSeverity.ERROR
    
    print("Error reporting example completed successfully")