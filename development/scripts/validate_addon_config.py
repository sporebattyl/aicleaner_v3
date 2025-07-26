#!/usr/bin/env python3
"""
AICleaner v3 Addon Configuration Validation Script
Validates Home Assistant addon configuration and internal configs for production deployment.
"""

import os
import sys
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional


class AddonConfigValidator:
    """Validates HA addon configuration and internal configs for production readiness."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def validate_all(self) -> bool:
        """Run all validation checks."""
        print("🔍 Starting AICleaner v3 Addon Configuration Validation...")
        
        # 1. Validate HA Addon config.yaml
        self.validate_ha_addon_schema()
        
        # 2. Validate internal config structure  
        self.validate_internal_config_schema()
        
        # 3. Cross-validate options mapping
        self.validate_options_mapping()
        
        # 4. Check deployment requirements
        self.validate_deployment_requirements()
        
        # Print results
        self._print_results()
        
        return len(self.errors) == 0
    
    def validate_ha_addon_schema(self):
        """Validate HA addon config.yaml structure and requirements."""
        config_file = self.project_root / "addons" / "aicleaner_v3" / "config.yaml"
        
        if not config_file.exists():
            self.errors.append(f"HA addon config.yaml not found: {config_file}")
            return
            
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            self.errors.append(f"Failed to parse HA addon config.yaml: {e}")
            return
        
        # Check required HA addon fields
        required_fields = ['name', 'version', 'slug', 'description', 'startup', 'arch']
        for field in required_fields:
            if field not in config:
                self.errors.append(f"Missing required HA addon field: {field}")
        
        # Validate options schema
        if 'options' in config and 'schema' in config:
            self._validate_options_schema(config['options'], config['schema'])
        else:
            self.warnings.append("No options/schema section found in HA addon config")
    
    def _validate_options_schema(self, options: Dict, schema: Dict):
        """Validate that options match their schema definitions."""
        for option_key, option_value in options.items():
            if option_key not in schema:
                self.warnings.append(f"Option '{option_key}' not defined in schema")
                continue
                
            schema_def = schema[option_key]
            base_type, is_optional, enum_values = self._parse_schema_type(schema_def)
            actual_type = type(option_value).__name__
            
            # Handle empty strings as optional values
            if option_value == "" and is_optional:
                continue  # Empty string is valid for optional fields
            
            if not self._type_matches(actual_type, base_type, is_optional, enum_values):
                self.errors.append(f"Option '{option_key}' type mismatch: expected {base_type}{'?' if is_optional else ''}, got {actual_type}")
            
            # Validate enum values if specified
            if enum_values and isinstance(option_value, str) and option_value not in enum_values:
                self.errors.append(f"Option '{option_key}' invalid value: '{option_value}' not in {enum_values}")
    
    def validate_internal_config_schema(self):
        """Validate internal config.default.yaml structure."""
        config_file = self.project_root / "core" / "config.default.yaml"
        
        if not config_file.exists():
            self.errors.append(f"Internal config.default.yaml not found: {config_file}")
            return
            
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            self.errors.append(f"Failed to parse config.default.yaml: {e}")
            return
        
        # Validate core sections exist
        required_sections = ['general', 'ai_providers', 'mqtt', 'service']
        for section in required_sections:
            if section not in config:
                self.errors.append(f"Missing required config section: {section}")
        
        # Validate general section
        if 'general' in config:
            general = config['general']
            if 'active_provider' not in general:
                self.errors.append("Missing 'active_provider' in general section")
            elif 'ai_providers' in config and general['active_provider'] not in config['ai_providers']:
                self.errors.append(f"Active provider '{general['active_provider']}' not found in ai_providers")
    
    def validate_options_mapping(self):
        """Validate that HA addon options map correctly to internal config."""
        # Check ConfigBridge implementation
        bridge_file = self.project_root / "core" / "config_bridge.py"
        
        if not bridge_file.exists():
            self.errors.append("ConfigBridge file not found - options mapping cannot be validated")
            return
        
        # Read addon options
        addon_config_file = self.project_root / "addons" / "aicleaner_v3" / "config.yaml"
        try:
            with open(addon_config_file, 'r') as f:
                addon_config = yaml.safe_load(f)
                
            if 'options' in addon_config:
                # Verify common mapping patterns exist
                options = addon_config['options']
                
                # Check that critical options have reasonable defaults
                critical_options = ['active_provider', 'log_level', 'mqtt_host', 'api_port']
                for option in critical_options:
                    if option in options and options[option] in [None, '']:
                        self.warnings.append(f"Critical option '{option}' has empty default value")
                        
        except Exception as e:
            self.errors.append(f"Failed to validate options mapping: {e}")
    
    def validate_deployment_requirements(self):
        """Check for common deployment issues."""
        
        # 1. Check requirements.txt exists and has necessary packages
        requirements_files = [
            self.project_root / "requirements.txt",
            self.project_root / "addons" / "aicleaner_v3" / "requirements.txt",
            self.project_root / "core" / "requirements.txt"
        ]
        
        found_requirements = False
        for req_file in requirements_files:
            if req_file.exists():
                found_requirements = True
                self._validate_requirements_file(req_file)
                
        if not found_requirements:
            self.errors.append("No requirements.txt file found")
        
        # 2. Check Dockerfile exists
        dockerfile = self.project_root / "addons" / "aicleaner_v3" / "Dockerfile"
        if not dockerfile.exists():
            self.errors.append("Dockerfile not found")
        
        # 3. Check for hardcoded paths
        self._check_hardcoded_paths()
    
    def _validate_requirements_file(self, req_file: Path):
        """Validate requirements.txt for common issues."""
        try:
            with open(req_file, 'r') as f:
                requirements = f.read()
                
            # Check for unpinned versions (potential instability)
            lines = [line.strip() for line in requirements.split('\n') if line.strip() and not line.startswith('#')]
            unpinned = [line for line in lines if '==' not in line and '>=' not in line and line != '']
            
            if unpinned:
                self.warnings.append(f"Unpinned dependencies in {req_file}: {', '.join(unpinned[:3])}")
                
        except Exception as e:
            self.warnings.append(f"Could not validate {req_file}: {e}")
    
    def _check_hardcoded_paths(self):
        """Check for hardcoded paths that won't work in containers."""
        problematic_patterns = [
            '/home/',
            '/Users/',
            'C:\\',
            'localhost:1883',  # Should use env var
        ]
        
        config_files = [
            self.project_root / "core" / "config.default.yaml",
            self.project_root / "addons" / "aicleaner_v3" / "config.yaml"
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        content = f.read()
                        
                    for pattern in problematic_patterns:
                        if pattern in content:
                            self.warnings.append(f"Potentially problematic path '{pattern}' found in {config_file}")
                            
                except Exception:
                    pass  # Skip files we can't read
    
    def _parse_schema_type(self, schema_def: str) -> Tuple[str, bool, List[str]]:
        """Parse HA schema type definition to extract type, optional flag, and enum values."""
        if not isinstance(schema_def, str):
            return str(schema_def), False, []
        
        # Check for optional marker
        is_optional = schema_def.endswith('?')
        base_type = schema_def.rstrip('?')
        
        # Check for enum/list options like "list(option1|option2)"
        enum_values = []
        if base_type.startswith('list(') and base_type.endswith(')'):
            enum_part = base_type[5:-1]  # Remove "list(" and ")"
            enum_values = enum_part.split('|')
            base_type = 'str'  # list(options) is actually a string enum
        
        return base_type, is_optional, enum_values
    
    def _type_matches(self, actual: str, expected: str, is_optional: bool = False, enum_values: List[str] = None) -> bool:
        """Check if actual type matches expected schema type."""
        type_mapping = {
            'str': ['str'],
            'int': ['int'],  
            'bool': ['bool'],
            'port': ['int'],
            'password': ['str'],
            'url': ['str'],  # Add url type support
            'list': ['list']
        }
        
        # Handle empty values for optional fields
        if actual == 'str' and is_optional and expected in ['password', 'str', 'url']:
            return True
            
        return actual in type_mapping.get(expected, [expected])
    
    def _print_results(self):
        """Print validation results."""
        print("\n" + "="*50)
        print("🔍 VALIDATION RESULTS")
        print("="*50)
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All validations passed! Configuration is production-ready.")
        elif not self.errors:
            print("\n✅ No critical errors found. Warnings should be reviewed.")
        else:
            print(f"\n❌ Found {len(self.errors)} critical errors that must be fixed.")


def main():
    """Main validation entry point."""
    project_root = Path(__file__).parent.parent  # Go up from scripts/ to project root
    
    validator = AddonConfigValidator(str(project_root))
    success = validator.validate_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()