"""
Phase 3B: Zone Configuration Engine
Advanced configuration validation, optimization, and rule execution engine.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from .models import Zone, Device, Rule, DeviceType, RulePriority
from .logger import setup_logger
from .utils import validate_zone_id, validate_device_id, sanitize_name, parse_schedule_expression


class ZoneConfigEngine:
    """
    Advanced configuration engine for zone validation and optimization.
    
    Provides comprehensive configuration validation, rule execution,
    and intelligent configuration recommendations.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize configuration engine.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = setup_logger(__name__)
        
        # Configuration validation rules
        self.validation_rules = self._initialize_validation_rules()
        
        # Device type capabilities mapping
        self.device_capabilities = self._initialize_device_capabilities()
        
        self.logger.info("Zone Configuration Engine initialized")
    
    def _initialize_validation_rules(self) -> Dict[str, Any]:
        """Initialize configuration validation rules."""
        return {
            'zone': {
                'required_fields': ['id', 'name'],
                'optional_fields': ['description', 'location', 'room_type', 'area_size_sqm'],
                'id_format': r'^[a-zA-Z0-9_-]{3,50}$',
                'name_max_length': 100,
                'description_max_length': 500
            },
            'device': {
                'required_fields': ['id', 'name', 'type'],
                'optional_fields': ['manufacturer', 'model', 'ip_address', 'mac_address'],
                'id_format': r'^[a-zA-Z0-9_.-]{3,100}$',
                'name_max_length': 100
            },
            'rule': {
                'required_fields': ['id', 'name', 'condition', 'action'],
                'optional_fields': ['description', 'schedule', 'parameters'],
                'id_format': r'^[a-zA-Z0-9_-]{3,50}$',
                'name_max_length': 100,
                'description_max_length': 300
            }
        }
    
    def _initialize_device_capabilities(self) -> Dict[DeviceType, Dict[str, Any]]:
        """Initialize device type capabilities mapping."""
        return {
            DeviceType.LIGHT: {
                'states': ['on', 'off', 'brightness', 'color'],
                'actions': ['turn_on', 'turn_off', 'set_brightness', 'set_color'],
                'polling_recommended': 'normal'
            },
            DeviceType.SENSOR: {
                'states': ['value', 'unit', 'battery_level'],
                'actions': ['read_value'],
                'polling_recommended': 'low'
            },
            DeviceType.SWITCH: {
                'states': ['on', 'off'],
                'actions': ['turn_on', 'turn_off'],
                'polling_recommended': 'normal'
            },
            DeviceType.CLIMATE: {
                'states': ['temperature', 'humidity', 'mode', 'target_temperature'],
                'actions': ['set_temperature', 'set_mode'],
                'polling_recommended': 'high'
            },
            DeviceType.MEDIA_PLAYER: {
                'states': ['playing', 'volume', 'source'],
                'actions': ['play', 'pause', 'stop', 'set_volume'],
                'polling_recommended': 'normal'
            }
        }
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate zone configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if configuration is valid
        """
        try:
            # Determine configuration type
            if 'devices' in config or 'rules' in config:
                return self._validate_zone_config(config)
            elif 'type' in config and 'id' in config:
                if config.get('condition') and config.get('action'):
                    return self._validate_rule_config(config)
                else:
                    return self._validate_device_config(config)
            else:
                self.logger.error(f"Unknown configuration type: {config}")
                return False
                
        except Exception as e:
            self.logger.error(f"Configuration validation error: {e}")
            return False
    
    def _validate_zone_config(self, config: Dict[str, Any]) -> bool:
        """Validate zone configuration."""
        rules = self.validation_rules['zone']
        
        # Check required fields
        for field in rules['required_fields']:
            if field not in config:
                self.logger.error(f"Missing required zone field: {field}")
                return False
        
        # Validate zone ID
        if not validate_zone_id(config['id']):
            self.logger.error(f"Invalid zone ID format: {config['id']}")
            return False
        
        # Validate name length
        if len(config['name']) > rules['name_max_length']:
            self.logger.error(f"Zone name too long: {len(config['name'])} > {rules['name_max_length']}")
            return False
        
        # Validate devices if present
        if 'devices' in config:
            for device_config in config['devices']:
                if not self._validate_device_config(device_config):
                    return False
        
        # Validate rules if present
        if 'rules' in config:
            for rule_config in config['rules']:
                if not self._validate_rule_config(rule_config):
                    return False
        
        return True
    
    def _validate_device_config(self, config: Dict[str, Any]) -> bool:
        """Validate device configuration."""
        rules = self.validation_rules['device']
        
        # Check required fields
        for field in rules['required_fields']:
            if field not in config:
                self.logger.error(f"Missing required device field: {field}")
                return False
        
        # Validate device ID
        if not validate_device_id(config['id']):
            self.logger.error(f"Invalid device ID format: {config['id']}")
            return False
        
        # Validate device type
        if config['type'] not in [dt.value for dt in DeviceType]:
            self.logger.error(f"Invalid device type: {config['type']}")
            return False
        
        return True
    
    def _validate_rule_config(self, config: Dict[str, Any]) -> bool:
        """Validate rule configuration."""
        rules = self.validation_rules['rule']
        
        # Check required fields
        for field in rules['required_fields']:
            if field not in config:
                self.logger.error(f"Missing required rule field: {field}")
                return False
        
        # Validate rule ID format
        if not validate_zone_id(config['id']):  # Use same validation as zones
            self.logger.error(f"Invalid rule ID format: {config['id']}")
            return False
        
        # Validate schedule if present
        if 'schedule' in config and config['schedule']:
            if not parse_schedule_expression(config['schedule']):
                self.logger.error(f"Invalid schedule expression: {config['schedule']}")
                return False
        
        return True
    
    def optimize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize configuration for better performance.
        
        Args:
            config: Configuration to optimize
            
        Returns:
            Optimized configuration
        """
        optimized_config = config.copy()
        
        try:
            # Optimize device configurations
            if 'devices' in optimized_config:
                optimized_config['devices'] = [
                    self._optimize_device_config(device_config)
                    for device_config in optimized_config['devices']
                ]
            
            # Optimize rule configurations
            if 'rules' in optimized_config:
                optimized_config['rules'] = self._optimize_rules(optimized_config['rules'])
            
            # Add recommended zone settings
            optimized_config = self._add_zone_recommendations(optimized_config)
            
            self.logger.info(f"Configuration optimized for zone: {config.get('name', 'Unknown')}")
            
        except Exception as e:
            self.logger.error(f"Configuration optimization error: {e}")
            return config  # Return original if optimization fails
        
        return optimized_config
    
    def _optimize_device_config(self, device_config: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize individual device configuration."""
        optimized = device_config.copy()
        
        device_type = DeviceType(device_config.get('type', DeviceType.UNKNOWN))
        
        # Set recommended polling frequency
        if device_type in self.device_capabilities:
            capabilities = self.device_capabilities[device_type]
            if 'polling_frequency' not in optimized:
                optimized['polling_frequency'] = capabilities['polling_recommended']
        
        # Sanitize name
        if 'name' in optimized:
            optimized['name'] = sanitize_name(optimized['name'])
        
        # Set default capabilities based on device type
        if 'capabilities' not in optimized:
            optimized['capabilities'] = {}
        
        if device_type in self.device_capabilities:
            capabilities = self.device_capabilities[device_type]
            for state in capabilities.get('states', []):
                if state not in optimized['capabilities']:
                    optimized['capabilities'][state] = True
        
        return optimized
    
    def _optimize_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize automation rules."""
        optimized_rules = []
        
        # Sort rules by priority (higher priority first)
        sorted_rules = sorted(rules, key=lambda r: r.get('priority', RulePriority.NORMAL), reverse=True)
        
        for rule_config in sorted_rules:
            optimized_rule = rule_config.copy()
            
            # Sanitize rule name
            if 'name' in optimized_rule:
                optimized_rule['name'] = sanitize_name(optimized_rule['name'])
            
            # Set default parameters if not present
            if 'parameters' not in optimized_rule:
                optimized_rule['parameters'] = {}
            
            # Add execution timeout if not specified
            if 'timeout_seconds' not in optimized_rule['parameters']:
                optimized_rule['parameters']['timeout_seconds'] = 30
            
            optimized_rules.append(optimized_rule)
        
        return optimized_rules
    
    def _add_zone_recommendations(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Add recommended zone settings."""
        if 'configuration' not in config:
            config['configuration'] = {}
        
        # Set default optimization settings
        if 'auto_optimization' not in config:
            config['auto_optimization'] = True
        
        # Set monitoring intervals based on zone complexity
        device_count = len(config.get('devices', []))
        rule_count = len(config.get('rules', []))
        
        if device_count > 10 or rule_count > 5:
            config['configuration']['monitoring_interval'] = 60  # More frequent for complex zones
        else:
            config['configuration']['monitoring_interval'] = 300  # Standard interval
        
        return config
    
    async def execute_rule_action(self, zone: Zone, rule: Rule) -> bool:
        """
        Execute a rule's action.
        
        Args:
            zone: Zone containing the rule
            rule: Rule to execute
            
        Returns:
            True if execution successful
        """
        try:
            self.logger.info(f"Executing rule '{rule.name}' in zone '{zone.name}'")
            
            # Parse action and parameters
            action_parts = rule.action.split('.')
            if len(action_parts) < 2:
                self.logger.error(f"Invalid action format: {rule.action}")
                return False
            
            target_type = action_parts[0]  # 'device' or 'zone'
            action_name = action_parts[1]
            
            if target_type == 'device':
                return await self._execute_device_action(zone, rule, action_name)
            elif target_type == 'zone':
                return await self._execute_zone_action(zone, rule, action_name)
            else:
                self.logger.error(f"Unknown action target type: {target_type}")
                return False
        
        except Exception as e:
            self.logger.error(f"Rule execution error for '{rule.name}': {e}")
            return False
    
    async def _execute_device_action(self, zone: Zone, rule: Rule, action_name: str) -> bool:
        """Execute device-specific action."""
        target_device_id = rule.parameters.get('device_id')
        if not target_device_id:
            self.logger.error(f"No target device specified for rule '{rule.name}'")
            return False
        
        # Find target device
        target_device = None
        for device in zone.devices:
            if device.id == target_device_id:
                target_device = device
                break
        
        if not target_device:
            self.logger.error(f"Target device '{target_device_id}' not found in zone '{zone.name}'")
            return False
        
        # Execute action based on device type and action name
        if action_name == 'turn_on':
            target_device.update_state({'on': True})
        elif action_name == 'turn_off':
            target_device.update_state({'on': False})
        elif action_name == 'set_brightness':
            brightness = rule.parameters.get('brightness', 255)
            target_device.update_state({'brightness': brightness})
        elif action_name == 'set_temperature':
            temperature = rule.parameters.get('temperature', 21)
            target_device.update_state({'target_temperature': temperature})
        else:
            self.logger.warning(f"Unknown device action: {action_name}")
            return False
        
        self.logger.info(f"Executed {action_name} on device '{target_device.name}'")
        return True
    
    async def _execute_zone_action(self, zone: Zone, rule: Rule, action_name: str) -> bool:
        """Execute zone-level action."""
        if action_name == 'activate':
            zone.is_active = True
        elif action_name == 'deactivate':
            zone.is_active = False
        elif action_name == 'optimize':
            # Trigger optimization (would integrate with optimization engine)
            self.logger.info(f"Optimization triggered for zone '{zone.name}'")
        else:
            self.logger.warning(f"Unknown zone action: {action_name}")
            return False
        
        self.logger.info(f"Executed {action_name} on zone '{zone.name}'")
        return True
    
    def generate_config_template(self, zone_type: str = 'generic') -> Dict[str, Any]:
        """
        Generate configuration template for common zone types.
        
        Args:
            zone_type: Type of zone (bedroom, kitchen, living_room, etc.)
            
        Returns:
            Configuration template
        """
        base_template = {
            'id': f'{zone_type}_zone',
            'name': f'{zone_type.replace("_", " ").title()} Zone',
            'description': f'Automated {zone_type} zone configuration',
            'room_type': zone_type,
            'devices': [],
            'rules': [],
            'is_active': True,
            'auto_optimization': True
        }
        
        # Add zone-specific recommendations
        if zone_type == 'bedroom':
            base_template['rules'].extend([
                {
                    'id': 'bedtime_routine',
                    'name': 'Bedtime Routine',
                    'condition': 'time.is_between("22:00", "23:59")',
                    'action': 'device.set_brightness',
                    'parameters': {'device_id': 'bedroom_light', 'brightness': 30}
                }
            ])
        elif zone_type == 'living_room':
            base_template['rules'].extend([
                {
                    'id': 'movie_mode',
                    'name': 'Movie Mode',
                    'condition': 'device.media_player.state == "playing"',
                    'action': 'device.turn_off',
                    'parameters': {'device_id': 'ceiling_light'}
                }
            ])
        
        return base_template
    
    def export_config(self, zone: Zone, format: str = 'json') -> str:
        """
        Export zone configuration in specified format.
        
        Args:
            zone: Zone to export
            format: Export format ('json', 'yaml')
            
        Returns:
            Serialized configuration
        """
        config_dict = zone.to_dict()
        
        if format == 'json':
            return json.dumps(config_dict, indent=2, default=str)
        elif format == 'yaml':
            try:
                import yaml
                return yaml.dump(config_dict, default_flow_style=False)
            except ImportError:
                self.logger.warning("PyYAML not available, falling back to JSON")
                return json.dumps(config_dict, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_config_engine():
        """Test configuration engine functionality."""
        
        config = {}
        engine = ZoneConfigEngine(config)
        
        # Test zone configuration validation
        valid_zone_config = {
            'id': 'test_living_room',
            'name': 'Test Living Room',
            'description': 'Test zone for validation',
            'devices': [
                {
                    'id': 'light.living_room',
                    'name': 'Living Room Light',
                    'type': 'light'
                }
            ],
            'rules': [
                {
                    'id': 'evening_lights',
                    'name': 'Evening Lights',
                    'condition': 'time.is_after("18:00")',
                    'action': 'device.turn_on'
                }
            ]
        }
        
        # Validate configuration
        is_valid = engine.validate_config(valid_zone_config)
        print(f"Configuration valid: {is_valid}")
        
        # Optimize configuration
        optimized_config = engine.optimize_config(valid_zone_config)
        print(f"Optimized configuration: {optimized_config}")
        
        # Generate template
        template = engine.generate_config_template('bedroom')
        print(f"Bedroom template: {template}")
        
        print("Configuration engine test completed!")
    
    # Run test
    asyncio.run(test_config_engine())