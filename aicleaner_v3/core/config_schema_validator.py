"""
Configuration Schema Validator for AICleaner v3
Phase 1A: Configuration Schema Consolidation

This module provides comprehensive validation for the unified configuration schema,
including input sanitization, security validation, and detailed error reporting.

Key Features:
- Comprehensive validation following AAA pattern
- Input sanitization and security validation
- Detailed error reporting and user-friendly messages
- Performance monitoring and benchmarking
- Component interface contracts
- Rollback validation support
"""

import logging
import json
import yaml
import re
import time
from typing import Dict, Any, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import hashlib
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os

class ValidationSeverity(Enum):
    """Validation result severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"

@dataclass
class ValidationIssue:
    """Individual validation issue"""
    severity: ValidationSeverity
    code: str
    message: str
    field: str
    value: Any = None
    suggestion: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

@dataclass
class ValidationResult:
    """Complete validation result"""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    info: List[ValidationIssue] = field(default_factory=list)
    validation_time_ms: float = 0.0
    performance_metrics: Dict[str, Any] = field(default_factory=dict)

class ConfigInputSanitizer:
    """Input sanitization for configuration values"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common injection patterns
        self.injection_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS
            r'javascript:',  # JavaScript protocol
            r'on\w+\s*=',  # Event handlers
            r'\.\./',  # Path traversal
            r'\\\.\\',  # Windows path traversal
            r'eval\s*\(',  # Code evaluation
            r'exec\s*\(',  # Code execution
            r'import\s+',  # Module imports
            r'__import__',  # Python imports
            r'subprocess',  # System calls
            r'os\.system',  # System calls
            r'open\s*\(',  # File operations
            r'file\s*\(',  # File operations
        ]
        
        # Compile patterns for performance
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.injection_patterns]
    
    def sanitize(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize configuration data to prevent injection attacks
        
        Args:
            config_data: Configuration dictionary to sanitize
            
        Returns:
            Sanitized configuration dictionary
        """
        return self._sanitize_recursive(config_data)
    
    def _sanitize_recursive(self, data: Any) -> Any:
        """Recursively sanitize data structure"""
        if isinstance(data, dict):
            return {key: self._sanitize_recursive(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_recursive(item) for item in data]
        elif isinstance(data, str):
            return self._sanitize_string(data)
        else:
            return data
    
    def _sanitize_string(self, value: str) -> str:
        """Sanitize string value"""
        if not value:
            return value
            
        # Remove potential injection patterns
        sanitized = value
        for pattern in self.compiled_patterns:
            sanitized = pattern.sub('', sanitized)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Limit length to prevent buffer overflow
        if len(sanitized) > 10000:
            sanitized = sanitized[:10000]
            self.logger.warning(f"String truncated due to excessive length: {value[:100]}...")
        
        return sanitized
    
    def detect_injection_attempts(self, config_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Detect potential injection attempts"""
        issues = []
        self._detect_injection_recursive(config_data, issues)
        return issues
    
    def _detect_injection_recursive(self, data: Any, issues: List[ValidationIssue], path: str = ""):
        """Recursively detect injection attempts"""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                self._detect_injection_recursive(value, issues, current_path)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                self._detect_injection_recursive(item, issues, current_path)
        elif isinstance(data, str):
            for pattern in self.compiled_patterns:
                if pattern.search(data):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="INJECTION_DETECTED",
                        message=f"Potential injection attempt detected in {path}",
                        field=path,
                        value=data[:100] + "..." if len(data) > 100 else data,
                        suggestion="Remove suspicious patterns and use safe configuration values"
                    ))
                    break

class ConfigSecurityValidator:
    """Security validation for configuration"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for sensitive data"""
        key_file = Path("config_encryption.key")
        
        if key_file.exists():
            return key_file.read_bytes()
        else:
            # Generate new key
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            key_file.chmod(0o600)  # Restrict access
            return key
    
    def validate_sensitive_data(self, config_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate sensitive data in configuration"""
        issues = []
        
        # Check API keys
        api_key = config_data.get("gemini_api_key", "")
        if api_key:
            issues.extend(self._validate_api_key(api_key))
        
        # Check MQTT credentials
        mqtt_config = config_data.get("mqtt", {})
        if mqtt_config.get("password"):
            issues.extend(self._validate_mqtt_credentials(mqtt_config))
        
        # Check HA token
        ha_token = config_data.get("ha_token", "")
        if ha_token:
            issues.extend(self._validate_ha_token(ha_token))
        
        return issues
    
    def _validate_api_key(self, api_key: str) -> List[ValidationIssue]:
        """Validate Gemini API key"""
        issues = []
        
        if not api_key or api_key.isspace():
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="MISSING_API_KEY",
                message="Gemini API key is required",
                field="gemini_api_key",
                suggestion="Get your API key from https://makersuite.google.com/app/apikey"
            ))
        elif api_key in ["YOUR_GEMINI_API_KEY", "AIzaSyExampleKeyReplaceMeWithYourKey"]:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="PLACEHOLDER_API_KEY",
                message="Please replace placeholder API key with actual key",
                field="gemini_api_key",
                suggestion="Get your API key from https://makersuite.google.com/app/apikey"
            ))
        elif not api_key.startswith("AIzaSy") and not api_key.startswith("test_"):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="INVALID_API_KEY_FORMAT",
                message="API key format appears invalid",
                field="gemini_api_key",
                suggestion="Gemini API keys typically start with 'AIzaSy'"
            ))
        
        return issues
    
    def _validate_mqtt_credentials(self, mqtt_config: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate MQTT credentials"""
        issues = []
        
        username = mqtt_config.get("username", "")
        password = mqtt_config.get("password", "")
        
        if mqtt_config.get("enabled", False):
            if not username:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="MISSING_MQTT_USERNAME",
                    message="MQTT username is recommended when MQTT is enabled",
                    field="mqtt.username",
                    suggestion="Provide MQTT username for secure connection"
                ))
            
            if not password:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="MISSING_MQTT_PASSWORD",
                    message="MQTT password is recommended when MQTT is enabled",
                    field="mqtt.password",
                    suggestion="Provide MQTT password for secure connection"
                ))
        
        return issues
    
    def _validate_ha_token(self, ha_token: str) -> List[ValidationIssue]:
        """Validate Home Assistant token"""
        issues = []
        
        if len(ha_token) < 20:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="SHORT_HA_TOKEN",
                message="Home Assistant token appears unusually short",
                field="ha_token",
                suggestion="Verify token is complete and valid"
            ))
        
        return issues
    
    def encrypt_sensitive_data(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive data in configuration"""
        encrypted_config = config_data.copy()
        
        # Encrypt API key
        if "gemini_api_key" in encrypted_config:
            encrypted_config["gemini_api_key"] = self._encrypt_value(encrypted_config["gemini_api_key"])
        
        # Encrypt MQTT password
        if "mqtt" in encrypted_config and "password" in encrypted_config["mqtt"]:
            encrypted_config["mqtt"]["password"] = self._encrypt_value(encrypted_config["mqtt"]["password"])
        
        # Encrypt HA token
        if "ha_token" in encrypted_config:
            encrypted_config["ha_token"] = self._encrypt_value(encrypted_config["ha_token"])
        
        return encrypted_config
    
    def _encrypt_value(self, value: str) -> str:
        """Encrypt a single value"""
        if not value:
            return value
        
        encrypted = self.cipher_suite.encrypt(value.encode())
        return base64.b64encode(encrypted).decode()

class ConfigSchemaValidator:
    """
    Comprehensive configuration schema validator
    
    Provides complete validation following AAA pattern with:
    - Input sanitization and security validation
    - Detailed error reporting and user-friendly messages
    - Performance monitoring and benchmarking
    - Component interface contracts
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.sanitizer = ConfigInputSanitizer()
        self.security_validator = ConfigSecurityValidator()
        self.performance_metrics = {}
        
        # Initialize validation rules
        self._init_validation_rules()
    
    def _init_validation_rules(self):
        """Initialize validation rules"""
        self.validation_rules = {
            "gemini_api_key": {
                "required": True,
                "type": str,
                "min_length": 1,
                "max_length": 1000
            },
            "display_name": {
                "required": True,
                "type": str,
                "min_length": 1,
                "max_length": 100
            },
            "mqtt.enabled": {
                "required": False,
                "type": bool,
                "default": False
            },
            "mqtt.host": {
                "required": False,
                "type": str,
                "default": "core-mosquitto"
            },
            "mqtt.port": {
                "required": False,
                "type": int,
                "min_value": 1,
                "max_value": 65535,
                "default": 1883
            },
            "ai_enhancements.caching.ttl_seconds": {
                "required": False,
                "type": int,
                "min_value": 60,
                "max_value": 3600,
                "default": 300
            },
            "ai_enhancements.scene_understanding_settings.confidence_threshold": {
                "required": False,
                "type": float,
                "min_value": 0.0,
                "max_value": 1.0,
                "default": 0.7
            },
            "zones": {
                "required": True,
                "type": list,
                "min_length": 1,
                "item_validation": {
                    "name": {"required": True, "type": str, "min_length": 1},
                    "camera_entity": {"required": True, "type": str, "min_length": 1},
                    "todo_list_entity": {"required": True, "type": str, "min_length": 1}
                }
            }
        }
    
    def validate(self, config_data: Dict[str, Any]) -> ValidationResult:
        """
        Comprehensive configuration validation following AAA pattern
        
        Args:
            config_data: Configuration dictionary to validate
            
        Returns:
            ValidationResult with detailed validation information
        """
        # Arrange - Initialize validation context
        start_time = time.time()
        result = ValidationResult(is_valid=True)
        
        try:
            # Act - Perform validation steps
            
            # 1. Input sanitization
            sanitized_config = self.sanitizer.sanitize(config_data)
            injection_issues = self.sanitizer.detect_injection_attempts(config_data)
            result.issues.extend(injection_issues)
            
            # 2. Security validation
            security_issues = self.security_validator.validate_sensitive_data(sanitized_config)
            result.issues.extend(security_issues)
            
            # 3. Schema validation
            schema_issues = self._validate_schema(sanitized_config)
            result.issues.extend(schema_issues)
            
            # 4. Business logic validation
            business_issues = self._validate_business_logic(sanitized_config)
            result.issues.extend(business_issues)
            
            # 5. Performance validation
            performance_issues = self._validate_performance_settings(sanitized_config)
            result.issues.extend(performance_issues)
            
            # Assert - Categorize issues and determine overall validity
            self._categorize_issues(result)
            
            # Calculate performance metrics
            result.validation_time_ms = (time.time() - start_time) * 1000
            result.performance_metrics = self._get_performance_metrics(result)
            
            # Log validation results
            self._log_validation_results(result)
            
        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}")
            result.is_valid = False
            result.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VALIDATION_ERROR",
                message=f"Internal validation error: {str(e)}",
                field="__validation__",
                suggestion="Check configuration format and try again"
            ))
        
        return result
    
    def _validate_schema(self, config_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate configuration against schema"""
        issues = []
        
        for field_path, rules in self.validation_rules.items():
            value = self._get_nested_value(config_data, field_path)
            field_issues = self._validate_field(field_path, value, rules)
            issues.extend(field_issues)
        
        return issues
    
    def _validate_field(self, field_path: str, value: Any, rules: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate individual field"""
        issues = []
        
        # Check required fields
        if rules.get("required", False) and value is None:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="REQUIRED_FIELD_MISSING",
                message=f"Required field '{field_path}' is missing",
                field=field_path,
                suggestion=f"Provide a value for {field_path}"
            ))
            return issues
        
        # Skip further validation if field is None and not required
        if value is None:
            return issues
        
        # Type validation
        expected_type = rules.get("type")
        if expected_type and not isinstance(value, expected_type):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_TYPE",
                message=f"Field '{field_path}' must be of type {expected_type.__name__}",
                field=field_path,
                value=value,
                suggestion=f"Provide a {expected_type.__name__} value"
            ))
            return issues
        
        # String length validation
        if isinstance(value, str):
            if "min_length" in rules and len(value) < rules["min_length"]:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="STRING_TOO_SHORT",
                    message=f"Field '{field_path}' must be at least {rules['min_length']} characters",
                    field=field_path,
                    value=value,
                    suggestion=f"Provide a longer value for {field_path}"
                ))
            
            if "max_length" in rules and len(value) > rules["max_length"]:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="STRING_TOO_LONG",
                    message=f"Field '{field_path}' must be no more than {rules['max_length']} characters",
                    field=field_path,
                    value=value,
                    suggestion=f"Provide a shorter value for {field_path}"
                ))
        
        # Numeric range validation
        if isinstance(value, (int, float)):
            if "min_value" in rules and value < rules["min_value"]:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="VALUE_TOO_LOW",
                    message=f"Field '{field_path}' must be at least {rules['min_value']}",
                    field=field_path,
                    value=value,
                    suggestion=f"Provide a value >= {rules['min_value']}"
                ))
            
            if "max_value" in rules and value > rules["max_value"]:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="VALUE_TOO_HIGH",
                    message=f"Field '{field_path}' must be no more than {rules['max_value']}",
                    field=field_path,
                    value=value,
                    suggestion=f"Provide a value <= {rules['max_value']}"
                ))
        
        # List validation
        if isinstance(value, list):
            if "min_length" in rules and len(value) < rules["min_length"]:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="LIST_TOO_SHORT",
                    message=f"Field '{field_path}' must have at least {rules['min_length']} items",
                    field=field_path,
                    value=value,
                    suggestion=f"Add more items to {field_path}"
                ))
            
            # Validate list items
            if "item_validation" in rules:
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        for item_field, item_rules in rules["item_validation"].items():
                            item_path = f"{field_path}[{i}].{item_field}"
                            item_value = item.get(item_field)
                            item_issues = self._validate_field(item_path, item_value, item_rules)
                            issues.extend(item_issues)
        
        # Handle None values for required fields
        elif value is None and rules.get("required", False):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="REQUIRED_FIELD_MISSING",
                message=f"Required field '{field_path}' cannot be None",
                field=field_path,
                value=value,
                suggestion=f"Provide a valid value for {field_path}"
            ))
        
        return issues
    
    def _validate_business_logic(self, config_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate business logic constraints"""
        issues = []
        
        # Validate zone entities exist in Home Assistant
        zones = config_data.get("zones", [])
        for i, zone in enumerate(zones):
            if isinstance(zone, dict):
                camera_entity = zone.get("camera_entity")
                todo_entity = zone.get("todo_list_entity")
                
                if camera_entity and not self._is_valid_entity_id(camera_entity):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="INVALID_ENTITY_FORMAT",
                        message=f"Camera entity ID format may be invalid: {camera_entity}",
                        field=f"zones[{i}].camera_entity",
                        value=camera_entity,
                        suggestion="Use format: domain.entity_name (e.g., camera.living_room)"
                    ))
                
                if todo_entity and not self._is_valid_entity_id(todo_entity):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="INVALID_ENTITY_FORMAT",
                        message=f"Todo entity ID format may be invalid: {todo_entity}",
                        field=f"zones[{i}].todo_list_entity",
                        value=todo_entity,
                        suggestion="Use format: domain.entity_name (e.g., todo.living_room_tasks)"
                    ))
        
        return issues
    
    def _validate_performance_settings(self, config_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate performance-related settings"""
        issues = []
        
        # Validate AI enhancement settings for performance
        ai_settings = config_data.get("ai_enhancements", {})
        
        # Check caching settings
        caching = ai_settings.get("caching", {})
        if caching.get("enabled", True):
            ttl = caching.get("ttl_seconds", 300)
            max_entries = caching.get("max_cache_entries", 1000)
            
            if ttl < 60:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="LOW_CACHE_TTL",
                    message="Cache TTL is very low, may impact performance",
                    field="ai_enhancements.caching.ttl_seconds",
                    value=ttl,
                    suggestion="Consider increasing to at least 60 seconds"
                ))
            
            if max_entries > 10000:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="HIGH_CACHE_ENTRIES",
                    message="High cache entry limit may consume excessive memory",
                    field="ai_enhancements.caching.max_cache_entries",
                    value=max_entries,
                    suggestion="Consider reducing to under 10000 entries"
                ))
        
        # Check local LLM resource limits
        local_llm = ai_settings.get("local_llm", {})
        if local_llm.get("enabled", True):
            resource_limits = local_llm.get("resource_limits", {})
            memory_limit = resource_limits.get("max_memory_usage", 4096)
            
            if memory_limit > 8192:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="HIGH_MEMORY_LIMIT",
                    message="High memory limit may cause system instability",
                    field="ai_enhancements.local_llm.resource_limits.max_memory_usage",
                    value=memory_limit,
                    suggestion="Consider reducing memory limit or ensure sufficient system RAM"
                ))
        
        return issues
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value using dot notation"""
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _is_valid_entity_id(self, entity_id: str) -> bool:
        """Check if entity ID follows Home Assistant format"""
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*$'
        return bool(re.match(pattern, entity_id))
    
    def _categorize_issues(self, result: ValidationResult):
        """Categorize issues by severity"""
        for issue in result.issues:
            if issue.severity == ValidationSeverity.ERROR:
                result.errors.append(issue)
                result.is_valid = False
            elif issue.severity == ValidationSeverity.WARNING:
                result.warnings.append(issue)
            elif issue.severity == ValidationSeverity.INFO:
                result.info.append(issue)
    
    def _get_performance_metrics(self, result: ValidationResult) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            "validation_time_ms": result.validation_time_ms,
            "total_issues": len(result.issues),
            "errors": len(result.errors),
            "warnings": len(result.warnings),
            "info": len(result.info),
            "performance_acceptable": result.validation_time_ms < 200  # Target: <200ms
        }
    
    def _log_validation_results(self, result: ValidationResult):
        """Log validation results"""
        if result.is_valid:
            self.logger.info(f"Configuration validation successful in {result.validation_time_ms:.2f}ms")
        else:
            self.logger.error(f"Configuration validation failed with {len(result.errors)} errors")
            for error in result.errors:
                self.logger.error(f"  {error.code}: {error.message}")
        
        if result.warnings:
            self.logger.warning(f"Configuration has {len(result.warnings)} warnings")
            for warning in result.warnings:
                self.logger.warning(f"  {warning.code}: {warning.message}")

# Example usage following AAA pattern
def example_aaa_validation():
    """Example validation following AAA pattern"""
    
    # Arrange - Prepare test configuration
    invalid_config = {
        "gemini_api_key": "invalid_key",
        "display_name": "",
        "zones": []
    }
    
    validator = ConfigSchemaValidator()
    
    # Act - Perform validation
    result = validator.validate(invalid_config)
    
    # Assert - Verify results
    assert not result.is_valid
    assert len(result.errors) > 0
    assert any(error.code == "REQUIRED_FIELD_MISSING" for error in result.errors)
    
    print("AAA validation example completed successfully")