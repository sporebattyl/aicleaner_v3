#!/usr/bin/env python3
"""
AICleaner V3 Input Validation Module
Provides comprehensive validation for user inputs and configurations
"""

import re
import logging
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom validation error with user-friendly messages"""
    pass

class InputValidator:
    """Comprehensive input validator for AICleaner addon"""
    
    # Valid entity ID pattern (follows Home Assistant conventions)
    ENTITY_ID_PATTERN = re.compile(r'^[a-z_][a-z0-9_]*\.[a-z0-9_]+$')
    
    # Device ID pattern (alphanumeric + underscores)
    DEVICE_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_]+$')
    
    # Zone name pattern (printable characters, reasonable length)
    ZONE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_\.]{1,50}$')
    
    # API key pattern (base64-like characters)
    API_KEY_PATTERN = re.compile(r'^[A-Za-z0-9\-_]{10,100}$')
    
    @staticmethod
    def validate_entity_id(entity_id: str, entity_type: str = "entity") -> str:
        """Validate Home Assistant entity ID format"""
        if not isinstance(entity_id, str):
            raise ValidationError(f"Entity ID must be a string, got {type(entity_id)}")
            
        if not entity_id:
            raise ValidationError(f"Entity ID cannot be empty")
            
        if len(entity_id) > 100:
            raise ValidationError(f"Entity ID too long (max 100 characters)")
            
        if not InputValidator.ENTITY_ID_PATTERN.match(entity_id):
            raise ValidationError(f"Invalid entity ID format: {entity_id}. Must match pattern: domain.entity_name")
            
        # Validate specific entity types
        if entity_type == "camera" and not entity_id.startswith("camera."):
            raise ValidationError(f"Camera entity must start with 'camera.', got: {entity_id}")
            
        if entity_type == "todo" and not entity_id.startswith("todo."):
            raise ValidationError(f"Todo list entity must start with 'todo.', got: {entity_id}")
            
        return entity_id.lower().strip()
    
    @staticmethod
    def validate_zone_name(name: str) -> str:
        """Validate zone name"""
        if not isinstance(name, str):
            raise ValidationError(f"Zone name must be a string, got {type(name)}")
            
        name = name.strip()
        if not name:
            raise ValidationError("Zone name cannot be empty")
            
        if len(name) > 50:
            raise ValidationError("Zone name too long (max 50 characters)")
            
        if not InputValidator.ZONE_NAME_PATTERN.match(name):
            raise ValidationError("Zone name contains invalid characters. Use only letters, numbers, spaces, hyphens, underscores, and dots")
            
        return name
    
    @staticmethod
    def validate_zone_purpose(purpose: str) -> str:
        """Validate zone purpose description"""
        if not isinstance(purpose, str):
            raise ValidationError(f"Zone purpose must be a string, got {type(purpose)}")
            
        purpose = purpose.strip()
        if len(purpose) > 200:
            raise ValidationError("Zone purpose too long (max 200 characters)")
            
        # Remove any potentially dangerous characters
        purpose = re.sub(r'[<>"\'\\\x00-\x1f\x7f-\x9f]', '', purpose)
        
        return purpose
    
    @staticmethod
    def validate_interval_minutes(interval: Union[int, str]) -> int:
        """Validate check interval in minutes"""
        try:
            interval = int(interval)
        except (ValueError, TypeError):
            raise ValidationError("Interval must be a valid number")
            
        if interval < 1:
            raise ValidationError("Interval must be at least 1 minute")
            
        if interval > 1440:  # 24 hours
            raise ValidationError("Interval cannot exceed 1440 minutes (24 hours)")
            
        return interval
    
    @staticmethod
    def validate_ignore_rules(rules: List[str]) -> List[str]:
        """Validate ignore rules list"""
        if not isinstance(rules, list):
            raise ValidationError(f"Ignore rules must be a list, got {type(rules)}")
            
        if len(rules) > 20:
            raise ValidationError("Too many ignore rules (max 20)")
            
        validated_rules = []
        for i, rule in enumerate(rules):
            if not isinstance(rule, str):
                raise ValidationError(f"Ignore rule {i+1} must be a string")
                
            rule = rule.strip()
            if not rule:
                continue  # Skip empty rules
                
            if len(rule) > 100:
                raise ValidationError(f"Ignore rule {i+1} too long (max 100 characters)")
                
            # Remove potentially dangerous characters
            rule = re.sub(r'[<>"\'\\\x00-\x1f\x7f-\x9f]', '', rule)
            validated_rules.append(rule)
            
        return validated_rules
    
    @staticmethod
    def validate_device_id(device_id: str) -> str:
        """Validate device ID"""
        if not isinstance(device_id, str):
            raise ValidationError(f"Device ID must be a string, got {type(device_id)}")
            
        device_id = device_id.strip()
        if not device_id:
            raise ValidationError("Device ID cannot be empty")
            
        if len(device_id) > 50:
            raise ValidationError("Device ID too long (max 50 characters)")
            
        if not InputValidator.DEVICE_ID_PATTERN.match(device_id):
            raise ValidationError("Device ID must contain only letters, numbers, and underscores")
            
        return device_id.lower()
    
    @staticmethod
    def validate_api_key(api_key: str, allow_empty: bool = True) -> Optional[str]:
        """Validate API key format"""
        if not api_key or not api_key.strip():
            if allow_empty:
                return None
            raise ValidationError("API key cannot be empty")
            
        if not isinstance(api_key, str):
            raise ValidationError(f"API key must be a string, got {type(api_key)}")
            
        api_key = api_key.strip()
        
        if len(api_key) < 10:
            raise ValidationError("API key too short (minimum 10 characters)")
            
        if len(api_key) > 100:
            raise ValidationError("API key too long (maximum 100 characters)")
            
        if not InputValidator.API_KEY_PATTERN.match(api_key):
            raise ValidationError("API key contains invalid characters")
            
        return api_key
    
    @staticmethod
    def validate_mqtt_discovery_prefix(prefix: str) -> str:
        """Validate MQTT discovery prefix"""
        if not isinstance(prefix, str):
            raise ValidationError(f"MQTT discovery prefix must be a string, got {type(prefix)}")
            
        prefix = prefix.strip()
        if not prefix:
            raise ValidationError("MQTT discovery prefix cannot be empty")
            
        if len(prefix) > 50:
            raise ValidationError("MQTT discovery prefix too long (max 50 characters)")
            
        # Must be valid MQTT topic segment
        if not re.match(r'^[a-zA-Z0-9_-]+$', prefix):
            raise ValidationError("MQTT discovery prefix contains invalid characters. Use only letters, numbers, hyphens, and underscores")
            
        return prefix.lower()
    
    @staticmethod
    def validate_log_level(log_level: str) -> str:
        """Validate log level"""
        valid_levels = ['debug', 'info', 'warning', 'error']
        
        if not isinstance(log_level, str):
            raise ValidationError(f"Log level must be a string, got {type(log_level)}")
            
        log_level = log_level.lower().strip()
        
        if log_level not in valid_levels:
            raise ValidationError(f"Invalid log level: {log_level}. Must be one of: {', '.join(valid_levels)}")
            
        return log_level
    
    @staticmethod
    def validate_zone_configuration(zone_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complete zone configuration"""
        if not isinstance(zone_data, dict):
            raise ValidationError("Zone data must be a dictionary")
            
        validated_zone = {}
        
        # Required fields
        if 'name' not in zone_data:
            raise ValidationError("Zone name is required")
        validated_zone['name'] = InputValidator.validate_zone_name(zone_data['name'])
        
        # Optional fields with validation
        if 'camera_entity' in zone_data and zone_data['camera_entity']:
            validated_zone['camera_entity'] = InputValidator.validate_entity_id(
                zone_data['camera_entity'], 'camera'
            )
        
        if 'todo_list_entity' in zone_data and zone_data['todo_list_entity']:
            validated_zone['todo_list_entity'] = InputValidator.validate_entity_id(
                zone_data['todo_list_entity'], 'todo'
            )
        
        if 'purpose' in zone_data:
            validated_zone['purpose'] = InputValidator.validate_zone_purpose(zone_data['purpose'])
        
        # Interval with default
        interval = zone_data.get('interval_minutes', 60)
        validated_zone['interval_minutes'] = InputValidator.validate_interval_minutes(interval)
        
        # Ignore rules with default
        ignore_rules = zone_data.get('ignore_rules', [])
        validated_zone['ignore_rules'] = InputValidator.validate_ignore_rules(ignore_rules)
        
        return validated_zone
    
    @staticmethod
    def validate_zones_list(zones_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate list of zone configurations"""
        if not isinstance(zones_data, list):
            raise ValidationError("Zones data must be a list")
            
        if len(zones_data) > 50:
            raise ValidationError("Too many zones (maximum 50)")
            
        validated_zones = []
        zone_names = set()
        
        for i, zone_data in enumerate(zones_data):
            try:
                validated_zone = InputValidator.validate_zone_configuration(zone_data)
                
                # Check for duplicate names
                zone_name = validated_zone['name'].lower()
                if zone_name in zone_names:
                    raise ValidationError(f"Duplicate zone name: {validated_zone['name']}")
                zone_names.add(zone_name)
                
                validated_zones.append(validated_zone)
                
            except ValidationError as e:
                raise ValidationError(f"Zone {i+1}: {str(e)}")
                
        return validated_zones
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe file operations"""
        if not isinstance(filename, str):
            raise ValidationError("Filename must be a string")
            
        # Remove directory traversal attempts
        filename = filename.replace('..', '').replace('/', '').replace('\\', '')
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*\x00-\x1f\x7f-\x9f]', '', filename)
        
        # Limit length
        if len(filename) > 100:
            filename = filename[:100]
            
        if not filename.strip():
            raise ValidationError("Invalid filename")
            
        return filename.strip()
    
    @staticmethod
    def validate_url(url: str, schemes: List[str] = None) -> str:
        """Validate URL format and scheme"""
        if not isinstance(url, str):
            raise ValidationError("URL must be a string")
            
        url = url.strip()
        if not url:
            raise ValidationError("URL cannot be empty")
            
        try:
            parsed = urlparse(url)
        except Exception:
            raise ValidationError("Invalid URL format")
            
        if not parsed.scheme or not parsed.netloc:
            raise ValidationError("URL must have scheme and netloc")
            
        if schemes and parsed.scheme not in schemes:
            raise ValidationError(f"URL scheme must be one of: {', '.join(schemes)}")
            
        return url