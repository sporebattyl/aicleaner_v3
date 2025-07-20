"""
Configuration management endpoints for AICleaner v3 Developer API v1
"""

import json
import yaml
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..dependencies import ConfigurationService, SecurityService, get_configuration_service, get_security_service
from ..error_helpers import raise_operation_failed, raise_invalid_input
from ..schemas import (
    common_responses,
    ConfigValidationRequest, ConfigValidationResponse,
    ConfigUpdateRequest, ConfigUpdateResponse,
    OperationResponse, APIErrorModel
)
from ..security import (
    get_current_user, require_permission,
    rate_limit_basic, rate_limit_privileged, rate_limit_admin
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/config", tags=["configuration"])

# --- Pydantic Models for Responses ---

class FullConfigurationResponse(BaseModel):
    config: Union[Dict[str, Any], str] = Field(..., description="The full configuration, either as a JSON object or a YAML string.")
    format: str = Field(..., description="The format of the configuration ('json' or 'yaml').")
    timestamp: datetime = Field(default_factory=datetime.now, description="The timestamp of when the configuration was retrieved.")

class ConfigurationSchemaResponse(BaseModel):
    schema: Dict[str, Any] = Field(..., description="The JSON schema for the configuration.")
    version: str = Field(..., description="The version of the schema.")
    timestamp: datetime = Field(default_factory=datetime.now, description="The timestamp of when the schema was retrieved.")

class TemplateDetail(BaseModel):
    description: str = Field(..., description="A description of the configuration template.")
    config: Dict[str, Any] = Field(..., description="The template configuration data.")

class ConfigurationTemplatesResponse(BaseModel):
    templates: Optional[Dict[str, TemplateDetail]] = Field(None, description="A dictionary of all available templates.")
    available: Optional[List[str]] = Field(None, description="A list of available template names.")
    template: Optional[TemplateDetail] = Field(None, description="The details of the requested template.")
    name: Optional[str] = Field(None, description="The name of the requested template.")
    timestamp: datetime = Field(default_factory=datetime.now, description="The timestamp of the response.")

class BackupDetail(BaseModel):
    filename: str = Field(..., description="The name of the backup file.")
    path: str = Field(..., description="The full path to the backup file.")
    size_bytes: int = Field(..., description="The size of the backup file in bytes.")
    created_at: str = Field(..., description="The creation timestamp of the backup file.")
    modified_at: str = Field(..., description="The last modification timestamp of the backup file.")

class ConfigurationBackupsResponse(BaseModel):
    backups: List[BackupDetail] = Field(..., description="A list of available configuration backups.")
    total: int = Field(..., description="The total number of backups found.")
    timestamp: datetime = Field(default_factory=datetime.now, description="The timestamp of when the backup list was retrieved.")


@router.get(
    "",
    response_model=FullConfigurationResponse,
    summary="Get Full System Configuration",
    description="Retrieves the entire system configuration. Supports both structured (JSON) and raw (YAML) formats.",
    response_description="The complete system configuration in the specified format.",
    responses={**common_responses}
)
@rate_limit_basic()
async def get_full_configuration(
    request: Request,
    format: str = "json",
    current_user: Dict[str, Any] = Depends(get_current_user),
    config_service: ConfigurationService = Depends(get_configuration_service)
):
    try:
        config = config_service.config_manager.load_configuration()
        
        if format.lower() == "yaml":
            yaml_content = yaml.dump(config, default_flow_style=False, sort_keys=False)
            return FullConfigurationResponse(
                config=yaml_content,
                format="yaml",
                timestamp=datetime.now()
            )
        else:
            return FullConfigurationResponse(
                config=config,
                format="json",
                timestamp=datetime.now()
            )
        
    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        raise_operation_failed("get", "configuration", str(e))


@router.put(
    "", 
    response_model=ConfigUpdateResponse,
    summary="Update Full System Configuration",
    description="Replaces the entire system configuration. This is a high-privilege operation that can affect all system components. Supports backup and validation.",
    response_description="Confirmation of the configuration update, including backup and validation status.",
    responses={**common_responses}
)
@rate_limit_admin()
@require_permission("write_config")
async def update_full_configuration(
    config_request: ConfigUpdateRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    config_service: ConfigurationService = Depends(get_configuration_service)
):
    try:
        backup_location = None
        validation_results = None
        
        # Create backup if requested
        if config_request.backup_current:
            try:
                current_config = config_service.config_manager.load_configuration()
                backup_location = _create_config_backup(current_config)
                logger.info(f"Configuration backup created at: {backup_location}")
            except Exception as e:
                logger.warning(f"Failed to create backup: {e}")
                if config_request.backup_current:  # If backup was required but failed
                    raise_operation_failed("create", "configuration backup", str(e))
        
        # Validate configuration if requested
        if config_request.validate_first:
            is_valid = config_service.config_manager.validate_configuration(config_request.config)
            errors = config_service.config_manager.get_validation_errors() if hasattr(config_service.config_manager, 'get_validation_errors') else []
            
            validation_results = ConfigValidationResponse(
                valid=is_valid,
                errors=errors
            )
            
            if not is_valid:
                raise_invalid_input("config", "provided configuration", f"validation failed: {'; '.join(errors)}")
        
        # Save the new configuration
        try:
            success = config_service.config_manager.save_configuration(config_request.config)
            if not success:
                raise Exception("Configuration save operation returned False")
            
            logger.info("Configuration updated successfully via API")
            
            return ConfigUpdateResponse(
                status="success",
                message="Configuration updated successfully",
                backup_location=backup_location,
                validation_results=validation_results
            )
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            
            # Attempt to restore backup if available
            if backup_location and config_request.backup_current:
                try:
                    _restore_config_backup(backup_location)
                    logger.info(f"Configuration restored from backup: {backup_location}")
                except Exception as restore_error:
                    logger.error(f"Failed to restore backup: {restore_error}")
            
            raise_operation_failed("save", "configuration", str(e))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_full_configuration: {e}")
        raise_operation_failed("update", "full configuration", str(e))


@router.post(
    "/_validate", 
    response_model=ConfigValidationResponse,
    summary="Validate Configuration",
    description="Performs comprehensive validation of a provided configuration without applying it, including syntax, semantics, and security impact assessment.",
    response_description="The results of the validation, including errors, warnings, and security impact.",
    responses={**common_responses}
)
@rate_limit_privileged()
async def validate_configuration(
    validation_request: ConfigValidationRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    config_service: ConfigurationService = Depends(get_configuration_service),
    security_service: SecurityService = Depends(get_security_service)
):
    try:
        # Perform validation
        is_valid = config_service.config_manager.validate_configuration(validation_request.config)
        errors = []
        warnings = []
        
        # Get validation errors if available
        if hasattr(config_service.config_manager, 'get_validation_errors'):
            errors = config_service.config_manager.get_validation_errors()
        
        # Generate warnings
        warnings = _generate_config_warnings(validation_request.config)
        
        # Assess security impact using SecurityService
        security_impact = _assess_security_impact(validation_request.config)
        
        return ConfigValidationResponse(
            valid=is_valid,
            errors=errors,
            warnings=warnings,
            security_impact=security_impact
        )
        
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise_operation_failed("validate", "configuration", str(e))


@router.get(
    "/schema",
    response_model=ConfigurationSchemaResponse,
    summary="Get Configuration Schema",
    description="Returns the JSON schema that describes the valid configuration structure and constraints for the AICleaner v3 system.",
    response_description="The JSON schema for system configuration.",
    responses={**common_responses}
)
@rate_limit_basic()
async def get_configuration_schema(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        # This would return the actual configuration schema
        # For now, returning a simplified schema structure
        schema = {
            "type": "object",
            "properties": {
                "ai": {
                    "type": "object",
                    "properties": {
                        "providers": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "default_provider": {"type": "string"},
                        "rate_limits": {"type": "object"}
                    }
                },
                "mqtt": {
                    "type": "object",
                    "properties": {
                        "broker_address": {"type": "string"},
                        "broker_port": {"type": "integer", "minimum": 1, "maximum": 65535},
                        "use_tls": {"type": "boolean"},
                        "username": {"type": "string"},
                        "password": {"type": "string"}
                    },
                    "required": ["broker_address", "broker_port"]
                },
                "security": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "string", "enum": ["speed", "balanced", "paranoid"]},
                        "encrypt_configs": {"type": "boolean"},
                        "require_tls": {"type": "boolean"}
                    }
                },
                "api": {
                    "type": "object",
                    "properties": {
                        "keys": {"type": "object"},
                        "rate_limits": {"type": "object"}
                    }
                }
            },
            "required": ["mqtt"]
        }
        
        return ConfigurationSchemaResponse(
            schema=schema,
            version="1.0",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to get configuration schema: {e}")
        raise_operation_failed("get", "configuration schema", str(e))


@router.get(
    "/templates",
    response_model=ConfigurationTemplatesResponse,
    summary="Get Configuration Templates",
    description="Returns pre-defined configuration templates for common use cases. Can fetch all templates or a specific one by name.",
    response_description="A list of available templates or the content of a specific template.",
    responses={**common_responses, 404: {"description": "Template not found"}}
)
@rate_limit_basic()
async def get_configuration_templates(
    request: Request,
    template_name: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        templates = {
            "minimal": {
                "description": "Minimal configuration for basic operation",
                "config": {
                    "mqtt": {
                        "broker_address": "localhost",
                        "broker_port": 1883,
                        "use_tls": False
                    },
                    "ai": {
                        "providers": ["openai"],
                        "default_provider": "openai"
                    },
                    "security": {
                        "level": "balanced"
                    }
                }
            },
            "production": {
                "description": "Production-ready configuration with security",
                "config": {
                    "mqtt": {
                        "broker_address": "mqtt.example.com",
                        "broker_port": 8883,
                        "use_tls": True,
                        "username": "your_username",
                        "password": "your_password"
                    },
                    "ai": {
                        "providers": ["openai", "anthropic"],
                        "default_provider": "openai",
                        "rate_limits": {
                            "requests_per_minute": 60
                        }
                    },
                    "security": {
                        "level": "paranoid",
                        "encrypt_configs": True,
                        "require_tls": True
                    },
                    "api": {
                        "keys": {},
                        "rate_limits": {
                            "default": "60/minute"
                        }
                    }
                }
            },
            "development": {
                "description": "Development configuration with relaxed security",
                "config": {
                    "mqtt": {
                        "broker_address": "localhost",
                        "broker_port": 1883,
                        "use_tls": False
                    },
                    "ai": {
                        "providers": ["openai", "ollama"],
                        "default_provider": "ollama"
                    },
                    "security": {
                        "level": "speed",
                        "encrypt_configs": False
                    }
                }
            }
        }
        
        if template_name:
            if template_name not in templates:
                raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
            return ConfigurationTemplatesResponse(
                template=templates[template_name],
                name=template_name,
                timestamp=datetime.now()
            )
        
        return ConfigurationTemplatesResponse(
            templates=templates,
            available=list(templates.keys()),
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get configuration templates: {e}")
        raise_operation_failed("get", "configuration templates", str(e))


@router.get(
    "/backups",
    response_model=ConfigurationBackupsResponse,
    summary="List Configuration Backups",
    description="Returns a list of available configuration backups with metadata including creation time, size, and filename.",
    response_description="A list of available configuration backups.",
    responses={**common_responses}
)
@rate_limit_basic()
async def list_configuration_backups(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        backup_dir = Path("/tmp/aicleaner_config_backups")  # In real impl, use proper backup location
        
        if not backup_dir.exists():
            return ConfigurationBackupsResponse(
                backups=[],
                total=0,
                timestamp=datetime.now()
            )
        
        backups = []
        for backup_file in backup_dir.glob("config_backup_*.json"):
            try:
                stat = backup_file.stat()
                backups.append(BackupDetail(
                    filename=backup_file.name,
                    path=str(backup_file),
                    size_bytes=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat()
                ))
            except Exception as e:
                logger.warning(f"Failed to get backup info for {backup_file}: {e}")
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        
        return ConfigurationBackupsResponse(
            backups=backups,
            total=len(backups),
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to list configuration backups: {e}")
        raise_operation_failed("list", "configuration backups", str(e))


def _create_config_backup(config: Dict[str, Any]) -> str:
    """Create a backup of the current configuration"""
    backup_dir = Path("/tmp/aicleaner_config_backups")
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"config_backup_{timestamp}.json"
    
    with open(backup_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    return str(backup_file)


def _restore_config_backup(backup_path: str):
    """Restore configuration from backup"""
    from utils.manager_registry import get_registry
    from utils.manager_registry import ManagerNames
    
    backup_file = Path(backup_path)
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    
    with open(backup_file, 'r') as f:
        config = json.load(f)
    
    # Use registry directly since this is a utility function
    registry = get_registry()
    config_manager = registry.get_manager(ManagerNames.CONFIGURATION.value)
    if config_manager:
        config_manager.save_configuration(config)


def _generate_config_warnings(config: Dict[str, Any]) -> List[str]:
    """Generate configuration warnings"""
    warnings = []
    
    mqtt_config = config.get('mqtt', {})
    if mqtt_config and not mqtt_config.get('use_tls', False):
        warnings.append("MQTT TLS is disabled - communication will be unencrypted")
    
    security_config = config.get('security', {})
    if security_config and security_config.get('level') == 'speed':
        warnings.append("Security level is set to 'speed' - reduced security measures")
    
    api_config = config.get('api', {})
    if api_config and not api_config.get('keys'):
        warnings.append("No API keys configured - API will be inaccessible")
    
    return warnings


def _assess_security_impact(config: Dict[str, Any]) -> Dict[str, Any]:
    """Assess security impact of configuration"""
    impact = {
        "level": "low",
        "changes": [],
        "recommendations": []
    }
    
    mqtt_config = config.get('mqtt', {})
    if mqtt_config and not mqtt_config.get('use_tls', False):
        impact["level"] = "high"
        impact["changes"].append("MQTT TLS encryption disabled")
        impact["recommendations"].append("Enable TLS encryption for secure communication")
    
    security_config = config.get('security', {})
    if security_config and security_config.get('level') == 'speed':
        if impact["level"] != "high":
            impact["level"] = "medium"
        impact["changes"].append("Security level set to 'speed'")
        impact["recommendations"].append("Consider using 'balanced' or 'paranoid' security level")
    
    return impact