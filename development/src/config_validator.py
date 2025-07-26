#!/usr/bin/env python3
"""
AICleaner V3 Configuration Validator
Provides comprehensive validation for addon configuration using Home Assistant schemas
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Union
from validation import InputValidator, ValidationError

logger = logging.getLogger(__name__)

class ConfigValidator:
    """Home Assistant addon configuration validator"""
    
    def __init__(self):
        self.required_permissions = {
            'hassio_api': True,
            'homeassistant_api': True,
            'ingress': True,
        }
        
        self.security_settings = {
            'privileged': False,
            'host_network': False,
            'init': False,
        }
    
    def validate_addon_options(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Validate addon options from Home Assistant"""
        if not isinstance(options, dict):
            raise ValidationError("Addon options must be a dictionary")
        
        validated_options = {}
        
        # Essential settings validation
        log_level = options.get('log_level', 'info')
        validated_options['log_level'] = InputValidator.validate_log_level(log_level)
        
        device_id = options.get('device_id', 'aicleaner_v3')
        validated_options['device_id'] = InputValidator.validate_device_id(device_id)
        
        # API Keys validation (optional)
        primary_api_key = options.get('primary_api_key', '')
        validated_options['primary_api_key'] = InputValidator.validate_api_key(
            primary_api_key, allow_empty=True
        )
        
        backup_api_keys = options.get('backup_api_keys', [])
        if not isinstance(backup_api_keys, list):
            raise ValidationError("backup_api_keys must be a list")
        
        validated_backup_keys = []
        for i, key in enumerate(backup_api_keys):
            if key and key.strip():  # Skip empty keys
                try:
                    validated_key = InputValidator.validate_api_key(key, allow_empty=False)
                    if validated_key:
                        validated_backup_keys.append(validated_key)
                except ValidationError as e:
                    raise ValidationError(f"backup_api_keys[{i}]: {str(e)}")
        
        validated_options['backup_api_keys'] = validated_backup_keys
        
        # MQTT Discovery validation
        mqtt_prefix = options.get('mqtt_discovery_prefix', 'homeassistant')
        validated_options['mqtt_discovery_prefix'] = InputValidator.validate_mqtt_discovery_prefix(mqtt_prefix)
        
        # Boolean options validation
        debug_mode = options.get('debug_mode', False)
        if not isinstance(debug_mode, bool):
            raise ValidationError("debug_mode must be a boolean")
        validated_options['debug_mode'] = debug_mode
        
        auto_dashboard = options.get('auto_dashboard', True)
        if not isinstance(auto_dashboard, bool):
            raise ValidationError("auto_dashboard must be a boolean")
        validated_options['auto_dashboard'] = auto_dashboard
        
        return validated_options
    
    def validate_environment_variables(self) -> Dict[str, Any]:
        """Validate critical environment variables"""
        env_validation = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'variables': {}
        }
        
        # Critical Home Assistant variables
        critical_vars = {
            'HASSIO_TOKEN': 'Home Assistant Supervisor API token',
            'DEVICE_ID': 'Device identifier',
        }
        
        for var_name, description in critical_vars.items():
            value = os.getenv(var_name)
            if not value:
                env_validation['errors'].append(f"Missing required environment variable: {var_name} ({description})")
                env_validation['valid'] = False
            else:
                # Validate the value if it exists
                try:
                    if var_name == 'DEVICE_ID':
                        validated_value = InputValidator.validate_device_id(value)
                        env_validation['variables'][var_name] = validated_value
                    elif var_name == 'HASSIO_TOKEN':
                        # Don't store the actual token, just validate format
                        if len(value) < 10:
                            env_validation['warnings'].append(f"{var_name} appears to be too short")
                        env_validation['variables'][var_name] = f"***{value[-4:]}"  # Show last 4 chars
                except ValidationError as e:
                    env_validation['errors'].append(f"Invalid {var_name}: {str(e)}")
                    env_validation['valid'] = False
        
        # Optional variables with validation
        optional_vars = {
            'LOG_LEVEL': ('info', InputValidator.validate_log_level),
            'DEBUG_MODE': ('false', lambda x: x.lower() in ['true', '1', 'yes', 'on']),
            'MQTT_HOST': ('localhost', str),
            'MQTT_PORT': ('1883', lambda x: 1 <= int(x) <= 65535),
            'CORE_SERVICE_URL': ('http://localhost:8000', InputValidator.validate_url),
        }
        
        for var_name, (default_value, validator) in optional_vars.items():
            value = os.getenv(var_name, default_value)
            try:
                if validator == str:
                    validated_value = str(value)
                elif callable(validator):
                    validated_value = validator(value)
                else:
                    validated_value = value
                
                env_validation['variables'][var_name] = validated_value
                
            except (ValidationError, ValueError, TypeError) as e:
                env_validation['warnings'].append(f"Invalid {var_name}: {str(e)}, using default: {default_value}")
                env_validation['variables'][var_name] = default_value
        
        return env_validation
    
    def validate_security_configuration(self) -> Dict[str, Any]:
        """Validate addon security configuration"""
        security_report = {
            'secure': True,
            'issues': [],
            'recommendations': [],
            'permissions': {}
        }
        
        # Check required permissions
        for permission, required in self.required_permissions.items():
            # These would normally be checked against the actual addon config
            # For now, we'll assume they're correctly set since they're in config.yaml
            security_report['permissions'][permission] = {
                'required': required,
                'status': 'assumed_correct'
            }
        
        # Check security settings
        for setting, secure_value in self.security_settings.items():
            # Again, these would be checked against actual running config
            security_report['permissions'][setting] = {
                'secure_value': secure_value,
                'status': 'assumed_correct'
            }
        
        # File permission checks
        critical_paths = ['/data', '/config']
        for path in critical_paths:
            if os.path.exists(path):
                try:
                    stat_info = os.stat(path)
                    # Check if path is writable by addon user
                    if not os.access(path, os.W_OK):
                        security_report['issues'].append(f"Path {path} is not writable by addon")
                        security_report['secure'] = False
                except OSError as e:
                    security_report['issues'].append(f"Cannot check permissions for {path}: {e}")
        
        # Check for common security issues
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
            security_report['recommendations'].append("Debug mode is enabled - disable for production")
        
        # Check for sensitive data in logs
        log_file = '/data/aicleaner.log'
        if os.path.exists(log_file):
            try:
                # Check last few lines for potential sensitive data
                with open(log_file, 'r') as f:
                    lines = f.readlines()[-50:]  # Check last 50 lines
                    
                for line in lines:
                    line_lower = line.lower()
                    if any(word in line_lower for word in ['password', 'token', 'key', 'secret']):
                        if not any(word in line_lower for word in ['***', 'redacted', 'hidden']):
                            security_report['recommendations'].append("Potential sensitive data in logs - review log output")
                            break
                            
            except IOError:
                pass  # Ignore if we can't read the log file
        
        return security_report
    
    def validate_addon_dependencies(self) -> Dict[str, Any]:
        """Validate addon dependencies and requirements"""
        dependency_report = {
            'satisfied': True,
            'missing': [],
            'versions': {},
            'recommendations': []
        }
        
        # Check Python packages
        required_packages = [
            'aiohttp',
            'paho-mqtt', 
            'PyYAML',
            'google-generativeai',
            'psutil'
        ]
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                dependency_report['versions'][package] = 'available'
            except ImportError:
                dependency_report['missing'].append(package)
                dependency_report['satisfied'] = False
        
        # Check Home Assistant services
        ha_services = ['mqtt']  # Services we depend on
        for service in ha_services:
            # This would normally check if the service is available
            # For now, we'll assume it's available since it's listed in config.yaml
            dependency_report['versions'][f'ha_service_{service}'] = 'assumed_available'
        
        return dependency_report
    
    def perform_comprehensive_validation(self) -> Dict[str, Any]:
        """Perform comprehensive addon validation"""
        validation_report = {
            'overall_status': 'valid',
            'timestamp': datetime.utcnow().isoformat(),
            'validations': {}
        }
        
        try:
            # Environment validation
            env_validation = self.validate_environment_variables()
            validation_report['validations']['environment'] = env_validation
            
            if not env_validation['valid']:
                validation_report['overall_status'] = 'invalid'
            
            # Security validation
            security_validation = self.validate_security_configuration()
            validation_report['validations']['security'] = security_validation
            
            if not security_validation['secure']:
                if validation_report['overall_status'] == 'valid':
                    validation_report['overall_status'] = 'warnings'
            
            # Dependency validation
            dependency_validation = self.validate_addon_dependencies()
            validation_report['validations']['dependencies'] = dependency_validation
            
            if not dependency_validation['satisfied']:
                validation_report['overall_status'] = 'invalid'
            
            # Additional validations can be added here
            
        except Exception as e:
            logger.error(f"Error during comprehensive validation: {e}")
            validation_report['overall_status'] = 'error'
            validation_report['error'] = str(e)
        
        return validation_report

# Import datetime at module level
from datetime import datetime