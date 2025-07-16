"""
Home Assistant Addon Configuration Compliance Validator
Phase 1A: Configuration Schema Consolidation

This module validates the unified configuration schema against Home Assistant
addon standards to ensure full compliance and certification readiness.

Key Features:
- Complete HA addon configuration validation
- Certification compliance checking
- Schema format validation
- Required field verification
- Type validation against HA standards
- Error reporting with HA-specific guidance
"""

import logging
import json
import yaml
import re
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .config_error_reporter import ConfigErrorReporter, ErrorCategory, ErrorSeverity, ErrorContext

class HAComplianceLevel(Enum):
    """Home Assistant compliance levels"""
    BASIC = "basic"
    RECOMMENDED = "recommended"
    CERTIFICATION_READY = "certification_ready"

class HAValidationResult(Enum):
    """HA validation result types"""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"

@dataclass
class HAComplianceIssue:
    """Home Assistant compliance issue"""
    field: str
    issue_type: str
    severity: HAValidationResult
    message: str
    ha_documentation: str
    fix_suggestion: str
    compliance_level: HAComplianceLevel

@dataclass
class HAComplianceReport:
    """Complete HA compliance report"""
    overall_compliance: HAComplianceLevel
    issues: List[HAComplianceIssue] = field(default_factory=list)
    passed_checks: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    certification_ready: bool = False
    validation_time_ms: float = 0.0

class HAComplianceValidator:
    """
    Home Assistant addon configuration compliance validator
    
    Validates configuration against HA addon standards for certification readiness.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_reporter = ConfigErrorReporter()
        
        # HA addon required fields
        self.required_addon_fields = {
            "name": str,
            "version": str,
            "slug": str,
            "description": str,
            "arch": list,
            "startup": str,
            "boot": str,
            "init": bool,
            "options": dict,
            "schema": dict
        }
        
        # HA addon optional fields
        self.optional_addon_fields = {
            "url": str,
            "homeassistant_api": bool,
            "hassio_api": bool,
            "ingress": bool,
            "ingress_port": int,
            "panel_icon": str,
            "panel_title": str,
            "map": list,
            "host_network": bool,
            "services": list,
            "ports": dict,
            "environment": dict,
            "tmpfs": str,
            "devices": list,
            "auto_uart": bool,
            "audio": bool,
            "video": bool,
            "gpio": bool,
            "kernel_modules": bool,
            "udev": bool,
            "apparmor": bool,
            "privileged": list,
            "full_access": bool,
            "stdin": bool,
            "legacy": bool,
            "codenotary": str,
            "hassio_role": str,
            "machine": list,
            "homeassistant": str
        }
        
        # Valid values for specific fields
        self.valid_field_values = {
            "startup": ["application", "system", "services", "once", "initialize"],
            "boot": ["auto", "manual"],
            "arch": ["armhf", "armv7", "aarch64", "amd64", "i386"],
            "hassio_role": ["default", "homeassistant", "manager", "admin"]
        }
        
        # Schema type mappings
        self.schema_types = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "email": str,
            "url": str,
            "password": str,
            "port": int,
            "match": str,
            "list": list,
            "dict": dict
        }
        
        # Initialize validation rules
        self._init_validation_rules()
    
    def _init_validation_rules(self):
        """Initialize HA-specific validation rules"""
        self.validation_rules = {
            "name": {
                "required": True,
                "type": str,
                "min_length": 1,
                "max_length": 100,
                "pattern": r"^[a-zA-Z0-9\s\-_\.]+$"
            },
            "version": {
                "required": True,
                "type": str,
                "pattern": r"^\d+\.\d+\.\d+$"
            },
            "slug": {
                "required": True,
                "type": str,
                "pattern": r"^[a-z0-9_]+$",
                "max_length": 50
            },
            "description": {
                "required": True,
                "type": str,
                "min_length": 10,
                "max_length": 200
            },
            "arch": {
                "required": True,
                "type": list,
                "min_length": 1,
                "valid_values": ["armhf", "armv7", "aarch64", "amd64", "i386"]
            },
            "startup": {
                "required": True,
                "type": str,
                "valid_values": ["application", "system", "services", "once", "initialize"]
            },
            "boot": {
                "required": True,
                "type": str,
                "valid_values": ["auto", "manual"]
            },
            "init": {
                "required": True,
                "type": bool
            },
            "options": {
                "required": True,
                "type": dict
            },
            "schema": {
                "required": True,
                "type": dict
            }
        }
    
    def validate_ha_compliance(self, config: Dict[str, Any]) -> HAComplianceReport:
        """
        Validate complete HA compliance
        
        Args:
            config: Configuration to validate
            
        Returns:
            HAComplianceReport with detailed compliance information
        """
        import time
        start_time = time.time()
        
        report = HAComplianceReport(
            overall_compliance=HAComplianceLevel.BASIC
        )
        
        try:
            # Validate required fields
            self._validate_required_fields(config, report)
            
            # Validate field types and values
            self._validate_field_types(config, report)
            
            # Validate schema structure
            self._validate_schema_structure(config, report)
            
            # Validate options structure
            self._validate_options_structure(config, report)
            
            # Validate security requirements
            self._validate_security_requirements(config, report)
            
            # Validate architecture support
            self._validate_architecture_support(config, report)
            
            # Validate service dependencies
            self._validate_service_dependencies(config, report)
            
            # Validate ingress configuration
            self._validate_ingress_configuration(config, report)
            
            # Determine overall compliance level
            self._determine_compliance_level(report)
            
            # Check certification readiness
            self._check_certification_readiness(report)
            
            report.validation_time_ms = (time.time() - start_time) * 1000
            
            self.logger.info(f"HA compliance validation completed: {report.overall_compliance.value}")
            
        except Exception as e:
            self.logger.error(f"HA compliance validation failed: {str(e)}")
            report.issues.append(HAComplianceIssue(
                field="__validation__",
                issue_type="validation_error",
                severity=HAValidationResult.FAIL,
                message=f"Validation error: {str(e)}",
                ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/",
                fix_suggestion="Check configuration format and try again",
                compliance_level=HAComplianceLevel.BASIC
            ))
        
        return report
    
    def _validate_required_fields(self, config: Dict[str, Any], report: HAComplianceReport):
        """Validate required HA addon fields"""
        for field, expected_type in self.required_addon_fields.items():
            if field not in config:
                report.issues.append(HAComplianceIssue(
                    field=field,
                    issue_type="missing_required_field",
                    severity=HAValidationResult.FAIL,
                    message=f"Required field '{field}' is missing",
                    ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/#add-on-configuration",
                    fix_suggestion=f"Add '{field}' field to configuration",
                    compliance_level=HAComplianceLevel.BASIC
                ))
            else:
                report.passed_checks.append(f"Required field '{field}' present")
    
    def _validate_field_types(self, config: Dict[str, Any], report: HAComplianceReport):
        """Validate field types and values"""
        for field, rules in self.validation_rules.items():
            if field in config:
                value = config[field]
                
                # Type validation
                expected_type = rules["type"]
                if not isinstance(value, expected_type):
                    report.issues.append(HAComplianceIssue(
                        field=field,
                        issue_type="invalid_type",
                        severity=HAValidationResult.FAIL,
                        message=f"Field '{field}' must be of type {expected_type.__name__}",
                        ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/#configuration-schema",
                        fix_suggestion=f"Change '{field}' to {expected_type.__name__} type",
                        compliance_level=HAComplianceLevel.BASIC
                    ))
                    continue
                
                # String length validation
                if isinstance(value, str):
                    if "min_length" in rules and len(value) < rules["min_length"]:
                        report.issues.append(HAComplianceIssue(
                            field=field,
                            issue_type="string_too_short",
                            severity=HAValidationResult.FAIL,
                            message=f"Field '{field}' must be at least {rules['min_length']} characters",
                            ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/",
                            fix_suggestion=f"Provide a longer value for '{field}'",
                            compliance_level=HAComplianceLevel.BASIC
                        ))
                    
                    if "max_length" in rules and len(value) > rules["max_length"]:
                        report.issues.append(HAComplianceIssue(
                            field=field,
                            issue_type="string_too_long",
                            severity=HAValidationResult.FAIL,
                            message=f"Field '{field}' must be no more than {rules['max_length']} characters",
                            ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/",
                            fix_suggestion=f"Shorten the value for '{field}'",
                            compliance_level=HAComplianceLevel.BASIC
                        ))
                    
                    # Pattern validation
                    if "pattern" in rules:
                        pattern = rules["pattern"]
                        if not re.match(pattern, value):
                            report.issues.append(HAComplianceIssue(
                                field=field,
                                issue_type="invalid_pattern",
                                severity=HAValidationResult.FAIL,
                                message=f"Field '{field}' does not match required pattern",
                                ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/",
                                fix_suggestion=f"Ensure '{field}' matches pattern: {pattern}",
                                compliance_level=HAComplianceLevel.BASIC
                            ))
                
                # List validation
                if isinstance(value, list):
                    if "min_length" in rules and len(value) < rules["min_length"]:
                        report.issues.append(HAComplianceIssue(
                            field=field,
                            issue_type="list_too_short",
                            severity=HAValidationResult.FAIL,
                            message=f"Field '{field}' must have at least {rules['min_length']} items",
                            ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/",
                            fix_suggestion=f"Add more items to '{field}'",
                            compliance_level=HAComplianceLevel.BASIC
                        ))
                    
                    if "valid_values" in rules:
                        valid_values = rules["valid_values"]
                        for item in value:
                            if item not in valid_values:
                                report.issues.append(HAComplianceIssue(
                                    field=field,
                                    issue_type="invalid_list_value",
                                    severity=HAValidationResult.FAIL,
                                    message=f"Invalid value '{item}' in '{field}'. Valid values: {valid_values}",
                                    ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/",
                                    fix_suggestion=f"Use only valid values for '{field}': {valid_values}",
                                    compliance_level=HAComplianceLevel.BASIC
                                ))
                
                # Valid values validation
                if "valid_values" in rules and not isinstance(value, list):
                    valid_values = rules["valid_values"]
                    if value not in valid_values:
                        report.issues.append(HAComplianceIssue(
                            field=field,
                            issue_type="invalid_value",
                            severity=HAValidationResult.FAIL,
                            message=f"Invalid value '{value}' for '{field}'. Valid values: {valid_values}",
                            ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/",
                            fix_suggestion=f"Use valid value for '{field}': {valid_values}",
                            compliance_level=HAComplianceLevel.BASIC
                        ))
                
                if not any(issue.field == field for issue in report.issues):
                    report.passed_checks.append(f"Field '{field}' validation passed")
    
    def _validate_schema_structure(self, config: Dict[str, Any], report: HAComplianceReport):
        """Validate schema structure"""
        if "schema" not in config:
            return
        
        schema = config["schema"]
        options = config.get("options", {})
        
        # Check that all options have corresponding schema definitions
        for option_key in options.keys():
            if option_key not in schema:
                report.issues.append(HAComplianceIssue(
                    field=f"schema.{option_key}",
                    issue_type="missing_schema_definition",
                    severity=HAValidationResult.FAIL,
                    message=f"Option '{option_key}' missing schema definition",
                    ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/#configuration-schema",
                    fix_suggestion=f"Add schema definition for '{option_key}'",
                    compliance_level=HAComplianceLevel.BASIC
                ))
        
        # Check that all schema definitions are valid
        for schema_key, schema_def in schema.items():
            if isinstance(schema_def, str):
                # Simple type definition
                if not self._is_valid_schema_type(schema_def):
                    report.issues.append(HAComplianceIssue(
                        field=f"schema.{schema_key}",
                        issue_type="invalid_schema_type",
                        severity=HAValidationResult.FAIL,
                        message=f"Invalid schema type '{schema_def}' for '{schema_key}'",
                        ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/#configuration-schema",
                        fix_suggestion=f"Use valid schema type for '{schema_key}'",
                        compliance_level=HAComplianceLevel.BASIC
                    ))
            elif isinstance(schema_def, dict):
                # Complex type definition
                self._validate_complex_schema(schema_key, schema_def, report)
            elif isinstance(schema_def, list):
                # List type definition
                self._validate_list_schema(schema_key, schema_def, report)
        
        report.passed_checks.append("Schema structure validation completed")
    
    def _validate_options_structure(self, config: Dict[str, Any], report: HAComplianceReport):
        """Validate options structure"""
        if "options" not in config:
            return
        
        options = config["options"]
        
        # Check for required options
        required_options = ["gemini_api_key", "display_name"]
        for required_option in required_options:
            if required_option not in options:
                report.issues.append(HAComplianceIssue(
                    field=f"options.{required_option}",
                    issue_type="missing_required_option",
                    severity=HAValidationResult.FAIL,
                    message=f"Required option '{required_option}' is missing",
                    ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/",
                    fix_suggestion=f"Add '{required_option}' to options",
                    compliance_level=HAComplianceLevel.BASIC
                ))
        
        # Validate option types match schema
        schema = config.get("schema", {})
        for option_key, option_value in options.items():
            if option_key in schema:
                expected_type = self._get_expected_type_from_schema(schema[option_key])
                if expected_type and not isinstance(option_value, expected_type):
                    report.warnings.append(f"Option '{option_key}' type mismatch with schema")
        
        report.passed_checks.append("Options structure validation completed")
    
    def _validate_security_requirements(self, config: Dict[str, Any], report: HAComplianceReport):
        """Validate security requirements"""
        security_checks = [
            ("apparmor", "AppArmor protection"),
            ("privileged", "Privileged access"),
            ("full_access", "Full system access"),
            ("host_network", "Host network access")
        ]
        
        for field, description in security_checks:
            if field in config:
                value = config[field]
                if field == "privileged" and value:
                    report.issues.append(HAComplianceIssue(
                        field=field,
                        issue_type="security_concern",
                        severity=HAValidationResult.WARNING,
                        message=f"{description} enabled - may affect certification",
                        ha_documentation="https://developers.home-assistant.io/docs/add-ons/security/",
                        fix_suggestion=f"Review need for {description}",
                        compliance_level=HAComplianceLevel.CERTIFICATION_READY
                    ))
                elif field == "full_access" and value:
                    report.issues.append(HAComplianceIssue(
                        field=field,
                        issue_type="security_concern",
                        severity=HAValidationResult.WARNING,
                        message=f"{description} enabled - requires justification",
                        ha_documentation="https://developers.home-assistant.io/docs/add-ons/security/",
                        fix_suggestion=f"Provide justification for {description}",
                        compliance_level=HAComplianceLevel.CERTIFICATION_READY
                    ))
        
        report.passed_checks.append("Security requirements validation completed")
    
    def _validate_architecture_support(self, config: Dict[str, Any], report: HAComplianceReport):
        """Validate architecture support"""
        if "arch" not in config:
            return
        
        arch_list = config["arch"]
        recommended_archs = ["amd64", "aarch64", "armv7"]
        
        # Check for recommended architectures
        missing_archs = [arch for arch in recommended_archs if arch not in arch_list]
        if missing_archs:
            report.issues.append(HAComplianceIssue(
                field="arch",
                issue_type="limited_architecture_support",
                severity=HAValidationResult.WARNING,
                message=f"Missing recommended architectures: {missing_archs}",
                ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/#arch",
                fix_suggestion=f"Consider adding support for: {missing_archs}",
                compliance_level=HAComplianceLevel.RECOMMENDED
            ))
        
        # Check for minimum architecture support
        if len(arch_list) < 2:
            report.issues.append(HAComplianceIssue(
                field="arch",
                issue_type="insufficient_architecture_support",
                severity=HAValidationResult.WARNING,
                message="Limited architecture support may affect user adoption",
                ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/#arch",
                fix_suggestion="Add support for more architectures",
                compliance_level=HAComplianceLevel.RECOMMENDED
            ))
        
        report.passed_checks.append("Architecture support validation completed")
    
    def _validate_service_dependencies(self, config: Dict[str, Any], report: HAComplianceReport):
        """Validate service dependencies"""
        if "services" in config:
            services = config["services"]
            for service in services:
                if not self._is_valid_service_dependency(service):
                    report.issues.append(HAComplianceIssue(
                        field="services",
                        issue_type="invalid_service_dependency",
                        severity=HAValidationResult.FAIL,
                        message=f"Invalid service dependency: {service}",
                        ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/#services",
                        fix_suggestion="Use valid service dependency format",
                        compliance_level=HAComplianceLevel.BASIC
                    ))
        
        report.passed_checks.append("Service dependencies validation completed")
    
    def _validate_ingress_configuration(self, config: Dict[str, Any], report: HAComplianceReport):
        """Validate ingress configuration"""
        if config.get("ingress", False):
            # Check for required ingress fields
            if "ingress_port" not in config:
                report.issues.append(HAComplianceIssue(
                    field="ingress_port",
                    issue_type="missing_ingress_port",
                    severity=HAValidationResult.FAIL,
                    message="Ingress enabled but ingress_port not specified",
                    ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/#ingress",
                    fix_suggestion="Add ingress_port when using ingress",
                    compliance_level=HAComplianceLevel.BASIC
                ))
            
            # Check for panel configuration
            if "panel_icon" not in config:
                report.issues.append(HAComplianceIssue(
                    field="panel_icon",
                    issue_type="missing_panel_icon",
                    severity=HAValidationResult.WARNING,
                    message="Panel icon recommended when using ingress",
                    ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/#ingress",
                    fix_suggestion="Add panel_icon for better user experience",
                    compliance_level=HAComplianceLevel.RECOMMENDED
                ))
            
            if "panel_title" not in config:
                report.issues.append(HAComplianceIssue(
                    field="panel_title",
                    issue_type="missing_panel_title",
                    severity=HAValidationResult.WARNING,
                    message="Panel title recommended when using ingress",
                    ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/#ingress",
                    fix_suggestion="Add panel_title for better user experience",
                    compliance_level=HAComplianceLevel.RECOMMENDED
                ))
        
        report.passed_checks.append("Ingress configuration validation completed")
    
    def _is_valid_schema_type(self, schema_type: str) -> bool:
        """Check if schema type is valid"""
        base_types = ["str", "int", "float", "bool", "email", "url", "password", "port", "match"]
        
        # Check base types
        if schema_type in base_types:
            return True
        
        # Check optional types (ending with ?)
        if schema_type.endswith("?") and schema_type[:-1] in base_types:
            return True
        
        # Check range types (int(min,max))
        if re.match(r"^(int|float)\(\d+,\d+\)$", schema_type):
            return True
        
        # Check list types (list(item_type))
        if re.match(r"^list\([^)]+\)$", schema_type):
            return True
        
        return False
    
    def _validate_complex_schema(self, key: str, schema_def: Dict[str, Any], report: HAComplianceReport):
        """Validate complex schema definition"""
        # Recursively validate nested schema
        for nested_key, nested_def in schema_def.items():
            if isinstance(nested_def, str):
                if not self._is_valid_schema_type(nested_def):
                    report.issues.append(HAComplianceIssue(
                        field=f"schema.{key}.{nested_key}",
                        issue_type="invalid_nested_schema_type",
                        severity=HAValidationResult.FAIL,
                        message=f"Invalid schema type '{nested_def}' for '{key}.{nested_key}'",
                        ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/#configuration-schema",
                        fix_suggestion=f"Use valid schema type for '{key}.{nested_key}'",
                        compliance_level=HAComplianceLevel.BASIC
                    ))
    
    def _validate_list_schema(self, key: str, schema_def: List[Any], report: HAComplianceReport):
        """Validate list schema definition"""
        if len(schema_def) != 1:
            report.issues.append(HAComplianceIssue(
                field=f"schema.{key}",
                issue_type="invalid_list_schema",
                severity=HAValidationResult.FAIL,
                message=f"List schema for '{key}' must have exactly one item definition",
                ha_documentation="https://developers.home-assistant.io/docs/add-ons/configuration/#configuration-schema",
                fix_suggestion=f"Provide single item definition for list schema '{key}'",
                compliance_level=HAComplianceLevel.BASIC
            ))
        
        # Validate list item schema
        item_schema = schema_def[0]
        if isinstance(item_schema, dict):
            self._validate_complex_schema(f"{key}[]", item_schema, report)
    
    def _get_expected_type_from_schema(self, schema_def: Any) -> Optional[type]:
        """Get expected Python type from schema definition"""
        if isinstance(schema_def, str):
            base_type = schema_def.rstrip("?")
            return self.schema_types.get(base_type)
        
        return None
    
    def _is_valid_service_dependency(self, service: str) -> bool:
        """Check if service dependency is valid"""
        # Valid service dependency formats
        valid_formats = [
            r"^[a-z_]+$",  # Simple service name
            r"^[a-z_]+:[a-z_]+$",  # Service with requirement
            r"^[a-z_]+:need$",  # Service needed
            r"^[a-z_]+:want$"  # Service wanted
        ]
        
        return any(re.match(pattern, service) for pattern in valid_formats)
    
    def _determine_compliance_level(self, report: HAComplianceReport):
        """Determine overall compliance level"""
        error_count = sum(1 for issue in report.issues if issue.severity == HAValidationResult.FAIL)
        warning_count = sum(1 for issue in report.issues if issue.severity == HAValidationResult.WARNING)
        
        if error_count > 0:
            report.overall_compliance = HAComplianceLevel.BASIC
        elif warning_count > 0:
            report.overall_compliance = HAComplianceLevel.RECOMMENDED
        else:
            report.overall_compliance = HAComplianceLevel.CERTIFICATION_READY
    
    def _check_certification_readiness(self, report: HAComplianceReport):
        """Check certification readiness"""
        # Certification blockers
        certification_blockers = [
            "missing_required_field",
            "invalid_type",
            "invalid_pattern",
            "invalid_schema_type",
            "missing_schema_definition"
        ]
        
        has_blockers = any(
            issue.issue_type in certification_blockers 
            for issue in report.issues
        )
        
        report.certification_ready = not has_blockers
    
    def generate_compliance_report(self, config: Dict[str, Any]) -> str:
        """Generate detailed compliance report"""
        report = self.validate_ha_compliance(config)
        
        lines = [
            "# Home Assistant Addon Compliance Report",
            f"**Overall Compliance Level**: {report.overall_compliance.value.upper()}",
            f"**Certification Ready**: {'Yes' if report.certification_ready else 'No'}",
            f"**Validation Time**: {report.validation_time_ms:.2f}ms",
            "",
            "## Summary",
            f"- **Passed Checks**: {len(report.passed_checks)}",
            f"- **Issues Found**: {len(report.issues)}",
            f"- **Warnings**: {len(report.warnings)}",
            ""
        ]
        
        # Add issues
        if report.issues:
            lines.extend([
                "## Issues Found",
                ""
            ])
            
            for issue in report.issues:
                lines.extend([
                    f"### {issue.field}",
                    f"**Type**: {issue.issue_type}",
                    f"**Severity**: {issue.severity.value.upper()}",
                    f"**Message**: {issue.message}",
                    f"**Fix**: {issue.fix_suggestion}",
                    f"**Documentation**: {issue.ha_documentation}",
                    ""
                ])
        
        # Add passed checks
        if report.passed_checks:
            lines.extend([
                "## Passed Checks",
                ""
            ])
            
            for check in report.passed_checks:
                lines.append(f"- {check}")
            
            lines.append("")
        
        # Add warnings
        if report.warnings:
            lines.extend([
                "## Warnings",
                ""
            ])
            
            for warning in report.warnings:
                lines.append(f"- {warning}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def export_compliance_report(self, config: Dict[str, Any], output_path: str):
        """Export compliance report to file"""
        report_content = self.generate_compliance_report(config)
        
        with open(output_path, 'w') as f:
            f.write(report_content)
        
        self.logger.info(f"HA compliance report exported to {output_path}")

# Example usage following AAA pattern
def example_ha_compliance_validation():
    """Example HA compliance validation"""
    
    # Arrange - Set up test configuration
    test_config = {
        "name": "AICleaner v3",
        "version": "3.0.0",
        "slug": "aicleaner_v3",
        "description": "AI-powered cleaning task management",
        "arch": ["amd64", "aarch64"],
        "startup": "application",
        "boot": "auto",
        "init": False,
        "options": {
            "gemini_api_key": "",
            "display_name": "AI Cleaner"
        },
        "schema": {
            "gemini_api_key": "str",
            "display_name": "str"
        }
    }
    
    validator = HAComplianceValidator()
    
    # Act - Validate compliance
    report = validator.validate_ha_compliance(test_config)
    
    # Assert - Check compliance
    assert report.overall_compliance in [HAComplianceLevel.BASIC, HAComplianceLevel.RECOMMENDED, HAComplianceLevel.CERTIFICATION_READY]
    assert isinstance(report.issues, list)
    assert isinstance(report.passed_checks, list)
    
    print("HA compliance validation example completed successfully")