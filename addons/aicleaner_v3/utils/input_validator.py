"""
Enhanced Input Validation and Sanitization for AICleaner
Comprehensive input validation, sanitization, and security measures
"""

import re
import json
import html
import urllib.parse
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class SanitizationLevel(Enum):
    """Sanitization levels"""
    BASIC = "basic"
    STRICT = "strict"
    PARANOID = "paranoid"


@dataclass
class ValidationRule:
    """Validation rule definition"""
    field_name: str
    required: bool = True
    data_type: type = str
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    custom_validator: Optional[callable] = None


class InputValidator:
    """
    Comprehensive input validation and sanitization system
    
    Features:
    - Type validation
    - Length validation
    - Pattern matching
    - Whitelist validation
    - Custom validation functions
    - Input sanitization
    - XSS prevention
    - SQL injection prevention
    - Path traversal prevention
    - Command injection prevention
    """
    
    def __init__(self, sanitization_level: SanitizationLevel = SanitizationLevel.STRICT):
        """
        Initialize input validator
        
        Args:
            sanitization_level: Level of sanitization to apply
        """
        self.sanitization_level = sanitization_level
        
        # Common validation patterns
        self.patterns = {
            "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "api_key": r"^[A-Za-z0-9_-]{20,}$",
            "zone_name": r"^[a-zA-Z0-9_-]{1,50}$",
            "entity_id": r"^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$",
            "url": r"^https?://[^\s/$.?#].[^\s]*$",
            "filename": r"^[a-zA-Z0-9._-]+$",
            "safe_string": r"^[a-zA-Z0-9\s._-]+$"
        }
        
        # Dangerous patterns to detect
        self.dangerous_patterns = {
            "sql_injection": [
                r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
                r"(--|#|/\*|\*/)",
                r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
                r"(\'\s*(OR|AND)\s*\'\w*\'\s*=\s*\'\w*\')"
            ],
            "xss": [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"on\w+\s*=",
                r"<iframe[^>]*>.*?</iframe>"
            ],
            "command_injection": [
                r"[;&|`$(){}[\]\\]",
                r"\b(rm|del|format|shutdown|reboot|kill)\b",
                r"(>|>>|<|<<|\|)"
            ],
            "path_traversal": [
                r"\.\.[\\/]",
                r"[\\/]\.\.[\\/]",
                r"~[\\/]",
                r"\$\{.*\}"
            ]
        }
        
        # Setup validation rules for AICleaner configuration
        self.config_rules = self._setup_config_validation_rules()
    
    def _setup_config_validation_rules(self) -> Dict[str, ValidationRule]:
        """Setup validation rules for AICleaner configuration"""
        return {
            "gemini_api_key": ValidationRule(
                field_name="gemini_api_key",
                required=True,
                data_type=str,
                min_length=20,
                max_length=200,
                pattern=self.patterns["api_key"]
            ),
            "claude_api_key": ValidationRule(
                field_name="claude_api_key",
                required=False,
                data_type=str,
                min_length=20,
                max_length=200,
                pattern=self.patterns["api_key"]
            ),
            "openai_api_key": ValidationRule(
                field_name="openai_api_key",
                required=False,
                data_type=str,
                min_length=20,
                max_length=200,
                pattern=self.patterns["api_key"]
            ),
            "display_name": ValidationRule(
                field_name="display_name",
                required=True,
                data_type=str,
                min_length=1,
                max_length=100,
                pattern=self.patterns["safe_string"]
            ),
            "zone_name": ValidationRule(
                field_name="name",
                required=True,
                data_type=str,
                min_length=1,
                max_length=50,
                pattern=self.patterns["zone_name"]
            ),
            "camera_entity": ValidationRule(
                field_name="camera_entity",
                required=True,
                data_type=str,
                min_length=5,
                max_length=100,
                pattern=self.patterns["entity_id"]
            ),
            "todo_list_entity": ValidationRule(
                field_name="todo_list_entity",
                required=True,
                data_type=str,
                min_length=5,
                max_length=100,
                pattern=self.patterns["entity_id"]
            ),
            "notification_service": ValidationRule(
                field_name="notification_service",
                required=False,
                data_type=str,
                min_length=5,
                max_length=100,
                pattern=self.patterns["entity_id"]
            ),
            "update_frequency": ValidationRule(
                field_name="update_frequency",
                required=False,
                data_type=int,
                custom_validator=lambda x: 1 <= x <= 1440  # 1 minute to 24 hours
            ),
            "notification_personality": ValidationRule(
                field_name="notification_personality",
                required=False,
                data_type=str,
                allowed_values=["default", "snarky", "jarvis", "roaster", "butler", "coach", "zen"]
            )
        }
    
    def validate_field(self, field_name: str, value: Any, rule: ValidationRule) -> Tuple[bool, str]:
        """
        Validate a single field against its rule
        
        Args:
            field_name: Name of the field
            value: Value to validate
            rule: Validation rule to apply
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if required
            if rule.required and (value is None or value == ""):
                return False, f"{field_name} is required"
            
            # Skip validation for optional empty fields
            if not rule.required and (value is None or value == ""):
                return True, ""
            
            # Type validation
            if not isinstance(value, rule.data_type):
                try:
                    # Try to convert
                    if rule.data_type == int:
                        value = int(value)
                    elif rule.data_type == float:
                        value = float(value)
                    elif rule.data_type == str:
                        value = str(value)
                    elif rule.data_type == bool:
                        value = bool(value)
                except (ValueError, TypeError):
                    return False, f"{field_name} must be of type {rule.data_type.__name__}"
            
            # String-specific validations
            if isinstance(value, str):
                # Length validation
                if rule.min_length is not None and len(value) < rule.min_length:
                    return False, f"{field_name} must be at least {rule.min_length} characters"
                
                if rule.max_length is not None and len(value) > rule.max_length:
                    return False, f"{field_name} must be at most {rule.max_length} characters"
                
                # Pattern validation
                if rule.pattern and not re.match(rule.pattern, value):
                    return False, f"{field_name} format is invalid"
                
                # Check for dangerous patterns
                if self._contains_dangerous_patterns(value):
                    return False, f"{field_name} contains potentially dangerous content"
            
            # Allowed values validation
            if rule.allowed_values is not None and value not in rule.allowed_values:
                return False, f"{field_name} must be one of: {', '.join(map(str, rule.allowed_values))}"
            
            # Custom validation
            if rule.custom_validator and not rule.custom_validator(value):
                return False, f"{field_name} failed custom validation"
            
            return True, ""
            
        except Exception as e:
            return False, f"Validation error for {field_name}: {str(e)}"
    
    def _contains_dangerous_patterns(self, value: str) -> bool:
        """Check if value contains dangerous patterns"""
        for category, patterns in self.dangerous_patterns.items():
            for pattern in patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    return True
        return False
    
    def sanitize_string(self, value: str) -> str:
        """
        Sanitize string input based on sanitization level
        
        Args:
            value: String to sanitize
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return str(value)
        
        # Basic sanitization
        sanitized = value.strip()
        
        if self.sanitization_level in [SanitizationLevel.STRICT, SanitizationLevel.PARANOID]:
            # HTML escape
            sanitized = html.escape(sanitized)
            
            # URL encode special characters
            sanitized = urllib.parse.quote(sanitized, safe='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~')
            
            # Remove null bytes
            sanitized = sanitized.replace('\x00', '')
            
            # Remove control characters
            sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\t\n\r')
        
        if self.sanitization_level == SanitizationLevel.PARANOID:
            # Additional paranoid sanitization
            # Remove potentially dangerous characters
            dangerous_chars = ['<', '>', '"', "'", '&', '`', '$', '(', ')', '{', '}', '[', ']', '|', ';']
            for char in dangerous_chars:
                sanitized = sanitized.replace(char, '')
        
        return sanitized
    
    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate complete AICleaner configuration
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Tuple of (is_valid, error_messages, sanitized_config)
        """
        errors = []
        sanitized_config = {}
        
        # Validate top-level fields
        for field_name, rule in self.config_rules.items():
            if field_name in ["zone_name", "camera_entity", "todo_list_entity", "notification_service", "update_frequency", "notification_personality"]:
                continue  # These are zone-specific
            
            value = config.get(field_name)
            is_valid, error_msg = self.validate_field(field_name, value, rule)
            
            if not is_valid:
                errors.append(error_msg)
            else:
                # Sanitize and store
                if isinstance(value, str):
                    sanitized_config[field_name] = self.sanitize_string(value)
                else:
                    sanitized_config[field_name] = value
        
        # Validate zones
        zones = config.get("zones", [])
        if not isinstance(zones, list):
            errors.append("zones must be a list")
        elif len(zones) == 0:
            errors.append("At least one zone must be configured")
        else:
            sanitized_zones = []
            for i, zone in enumerate(zones):
                if not isinstance(zone, dict):
                    errors.append(f"Zone {i} must be a dictionary")
                    continue
                
                sanitized_zone = {}
                zone_errors = []
                
                # Validate zone fields
                zone_rules = {
                    "name": self.config_rules["zone_name"],
                    "camera_entity": self.config_rules["camera_entity"],
                    "todo_list_entity": self.config_rules["todo_list_entity"],
                    "notification_service": self.config_rules["notification_service"],
                    "update_frequency": self.config_rules["update_frequency"],
                    "notification_personality": self.config_rules["notification_personality"]
                }
                
                for field_name, rule in zone_rules.items():
                    value = zone.get(field_name)
                    is_valid, error_msg = self.validate_field(f"Zone {i} {field_name}", value, rule)
                    
                    if not is_valid:
                        zone_errors.append(error_msg)
                    else:
                        # Sanitize and store
                        if isinstance(value, str):
                            sanitized_zone[field_name] = self.sanitize_string(value)
                        else:
                            sanitized_zone[field_name] = value
                
                # Copy other zone fields with sanitization
                for key, value in zone.items():
                    if key not in zone_rules:
                        if isinstance(value, str):
                            sanitized_zone[key] = self.sanitize_string(value)
                        else:
                            sanitized_zone[key] = value
                
                if zone_errors:
                    errors.extend(zone_errors)
                else:
                    sanitized_zones.append(sanitized_zone)
            
            sanitized_config["zones"] = sanitized_zones
        
        # Copy other configuration fields with sanitization
        for key, value in config.items():
            if key not in self.config_rules and key != "zones":
                if isinstance(value, str):
                    sanitized_config[key] = self.sanitize_string(value)
                else:
                    sanitized_config[key] = value
        
        is_valid = len(errors) == 0
        return is_valid, errors, sanitized_config
    
    def validate_api_input(self, data: Dict[str, Any], expected_fields: List[str]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate API input data
        
        Args:
            data: Input data to validate
            expected_fields: List of expected field names
            
        Returns:
            Tuple of (is_valid, error_messages, sanitized_data)
        """
        errors = []
        sanitized_data = {}
        
        # Check for unexpected fields
        for field in data.keys():
            if field not in expected_fields:
                errors.append(f"Unexpected field: {field}")
        
        # Validate and sanitize expected fields
        for field in expected_fields:
            value = data.get(field)
            
            if value is not None:
                # Basic validation
                if isinstance(value, str):
                    # Check for dangerous patterns
                    if self._contains_dangerous_patterns(value):
                        errors.append(f"Field {field} contains potentially dangerous content")
                    else:
                        sanitized_data[field] = self.sanitize_string(value)
                else:
                    sanitized_data[field] = value
        
        is_valid = len(errors) == 0
        return is_valid, errors, sanitized_data
    
    def validate_file_path(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate file path for security
        
        Args:
            file_path: File path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(file_path, str):
            return False, "File path must be a string"
        
        # Check for path traversal
        if ".." in file_path:
            return False, "Path traversal detected"
        
        # Check for absolute paths (should be relative)
        if file_path.startswith("/") or (len(file_path) > 1 and file_path[1] == ":"):
            return False, "Absolute paths not allowed"
        
        # Check for dangerous characters
        dangerous_chars = ['<', '>', '|', ':', '*', '?', '"']
        for char in dangerous_chars:
            if char in file_path:
                return False, f"Dangerous character '{char}' in file path"
        
        # Check filename pattern
        filename = file_path.split('/')[-1]
        if not re.match(self.patterns["filename"], filename):
            return False, "Invalid filename format"
        
        return True, ""
    
    def create_validation_report(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create comprehensive validation report
        
        Args:
            config: Configuration to validate
            
        Returns:
            Validation report
        """
        is_valid, errors, sanitized_config = self.validate_configuration(config)
        
        return {
            "timestamp": "2025-06-29T00:00:00Z",
            "is_valid": is_valid,
            "error_count": len(errors),
            "errors": errors,
            "sanitization_level": self.sanitization_level.value,
            "fields_validated": len(self.config_rules),
            "zones_validated": len(config.get("zones", [])),
            "security_checks_passed": not any(self._contains_dangerous_patterns(str(v)) for v in config.values() if isinstance(v, str)),
            "sanitized_config": sanitized_config if is_valid else None
        }
