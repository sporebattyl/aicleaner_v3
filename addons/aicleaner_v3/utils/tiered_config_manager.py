"""
Tiered Configuration Manager for Power Users
3-Tier System: UI Basics → YAML Advanced → API Programmatic

Implements progressive disclosure to hide complexity while maintaining
advanced capabilities for power users.
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigurationTier(Enum):
    """Configuration complexity tiers"""
    UI_BASIC = "ui_basic"          # Simple UI settings only
    YAML_ADVANCED = "yaml_advanced"  # Full YAML configuration
    API_PROGRAMMATIC = "api_programmatic"  # Script/API access


@dataclass
class TierSettings:
    """Settings for each configuration tier"""
    enabled: bool = True
    fields_visible: List[str] = None
    readonly_fields: List[str] = None
    validation_level: str = "standard"  # basic, standard, strict


class TieredConfigurationManager:
    """
    Power-user focused configuration manager with 3-tier progressive disclosure:
    
    Tier 1 (UI Basic): Essential settings for getting started
    - AI provider selection
    - Basic MQTT settings
    - Simple zone configuration
    
    Tier 2 (YAML Advanced): Full configuration flexibility
    - Complete YAML editing
    - Advanced performance tuning
    - Security presets
    - Custom automation rules
    
    Tier 3 (API Programmatic): Script/automation access
    - REST API configuration
    - Bulk operations
    - Integration scripting
    - Advanced debugging
    """
    
    def __init__(self, config_path: str = "/data/config"):
        """Initialize tiered configuration manager"""
        self.config_path = Path(config_path)
        self.config_path.mkdir(parents=True, exist_ok=True)
        
        # Configuration files for each tier
        self.ui_config_file = self.config_path / "ui_basic.json"
        self.yaml_config_file = self.config_path / "advanced.yaml" 
        self.api_config_file = self.config_path / "api_config.json"
        
        # Merged configuration cache
        self._merged_config = None
        self._config_dirty = True
        
        # Tier definitions
        self.tier_settings = {
            ConfigurationTier.UI_BASIC: TierSettings(
                enabled=True,
                fields_visible=[
                    "ai.primary_provider", "ai.api_key", "ai.model",
                    "mqtt.broker_host", "mqtt.broker_port", "mqtt.use_tls",
                    "zones.basic", "notifications.enabled"
                ],
                readonly_fields=[],
                validation_level="basic"
            ),
            ConfigurationTier.YAML_ADVANCED: TierSettings(
                enabled=True,
                fields_visible=["*"],  # All fields visible
                readonly_fields=["system.version", "system.install_date"],
                validation_level="standard"
            ),
            ConfigurationTier.API_PROGRAMMATIC: TierSettings(
                enabled=True,
                fields_visible=["*"],
                readonly_fields=["system.version"],
                validation_level="strict"
            )
        }
        
        logger.info(f"TieredConfigurationManager initialized at {config_path}")
    
    def get_config_for_tier(self, tier: ConfigurationTier) -> Dict[str, Any]:
        """Get configuration filtered for specific tier"""
        full_config = self.get_merged_configuration()
        tier_config = self._filter_config_for_tier(full_config, tier)
        
        # Add tier metadata
        tier_config["_tier_info"] = {
            "current_tier": tier.value,
            "available_tiers": [t.value for t in ConfigurationTier],
            "tier_settings": asdict(self.tier_settings[tier])
        }
        
        return tier_config
    
    def _filter_config_for_tier(self, config: Dict[str, Any], tier: ConfigurationTier) -> Dict[str, Any]:
        """Filter configuration based on tier visibility rules"""
        settings = self.tier_settings[tier]
        
        if "*" in settings.fields_visible:
            # Show all fields for advanced tiers
            filtered = config.copy()
        else:
            # Filter to only visible fields for basic tier
            filtered = {}
            for field_path in settings.fields_visible:
                self._add_field_to_config(filtered, config, field_path)
        
        # Mark readonly fields
        if settings.readonly_fields:
            if "_readonly" not in filtered:
                filtered["_readonly"] = []
            filtered["_readonly"].extend(settings.readonly_fields)
        
        return filtered
    
    def _add_field_to_config(self, target: Dict[str, Any], source: Dict[str, Any], field_path: str):
        """Add a specific field path to target config from source"""
        parts = field_path.split(".")
        
        # Navigate to the field in source
        current_source = source
        for part in parts[:-1]:
            if part in current_source and isinstance(current_source[part], dict):
                current_source = current_source[part]
            else:
                return  # Field path doesn't exist
        
        # Create nested structure in target
        current_target = target
        for part in parts[:-1]:
            if part not in current_target:
                current_target[part] = {}
            current_target = current_target[part]
        
        # Copy the final value
        final_key = parts[-1]
        if final_key in current_source:
            if final_key == "basic" and parts[0] == "zones":
                # Special handling for zones.basic - simplified zone config
                current_target[final_key] = self._get_basic_zones_config(source)
            else:
                current_target[final_key] = current_source[final_key]
    
    def _get_basic_zones_config(self, full_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get simplified zone configuration for UI tier"""
        zones = full_config.get("zones", [])
        basic_zones = []
        
        for zone in zones:
            basic_zone = {
                "name": zone.get("name", ""),
                "enabled": zone.get("enabled", True),
                "camera_entity": zone.get("camera_entity", ""),
                "todo_list_entity": zone.get("todo_list_entity", ""),
                "notifications_enabled": zone.get("notifications_enabled", True)
            }
            basic_zones.append(basic_zone)
        
        return basic_zones
    
    def update_config_for_tier(self, tier: ConfigurationTier, updates: Dict[str, Any]) -> bool:
        """Update configuration from specific tier"""
        try:
            # Remove tier metadata from updates
            if "_tier_info" in updates:
                del updates["_tier_info"]
            if "_readonly" in updates:
                del updates["_readonly"]
            
            # Validate updates for this tier
            validation_errors = self._validate_tier_updates(tier, updates)
            if validation_errors:
                logger.error(f"Validation errors for tier {tier.value}: {validation_errors}")
                return False
            
            # Save to appropriate file based on tier
            if tier == ConfigurationTier.UI_BASIC:
                self._save_ui_config(updates)
            elif tier == ConfigurationTier.YAML_ADVANCED:
                self._save_yaml_config(updates)
            elif tier == ConfigurationTier.API_PROGRAMMATIC:
                self._save_api_config(updates)
            
            # Mark merged config as dirty
            self._config_dirty = True
            
            logger.info(f"Configuration updated for tier {tier.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update config for tier {tier.value}: {e}")
            return False
    
    def _validate_tier_updates(self, tier: ConfigurationTier, updates: Dict[str, Any]) -> List[str]:
        """Validate configuration updates for specific tier"""
        errors = []
        settings = self.tier_settings[tier]
        
        # Check readonly fields
        if settings.readonly_fields:
            for field_path in settings.readonly_fields:
                if self._field_exists_in_updates(updates, field_path):
                    errors.append(f"Field {field_path} is readonly for tier {tier.value}")
        
        # Tier-specific validation
        if tier == ConfigurationTier.UI_BASIC:
            errors.extend(self._validate_ui_config(updates))
        elif tier == ConfigurationTier.YAML_ADVANCED:
            errors.extend(self._validate_yaml_config(updates))
        elif tier == ConfigurationTier.API_PROGRAMMATIC:
            errors.extend(self._validate_api_config(updates))
        
        return errors
    
    def _field_exists_in_updates(self, updates: Dict[str, Any], field_path: str) -> bool:
        """Check if a field path exists in the updates"""
        parts = field_path.split(".")
        current = updates
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False
        
        return True
    
    def _validate_ui_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate UI tier configuration"""
        errors = []
        
        # Basic AI provider validation
        if "ai" in config:
            ai_config = config["ai"]
            if "primary_provider" in ai_config:
                valid_providers = ["openai", "anthropic", "google", "ollama"]
                if ai_config["primary_provider"] not in valid_providers:
                    errors.append(f"Invalid AI provider. Must be one of: {valid_providers}")
            
            if "api_key" in ai_config and not ai_config["api_key"]:
                errors.append("AI API key cannot be empty")
        
        # Basic MQTT validation
        if "mqtt" in config:
            mqtt_config = config["mqtt"]
            if "broker_port" in mqtt_config:
                port = mqtt_config["broker_port"]
                if not isinstance(port, int) or port < 1 or port > 65535:
                    errors.append("MQTT broker port must be between 1 and 65535")
        
        return errors
    
    def _validate_yaml_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate YAML tier configuration"""
        errors = []
        
        # More comprehensive validation for advanced tier
        # Include all UI validations plus advanced checks
        errors.extend(self._validate_ui_config(config))
        
        # Advanced security validation
        if "security" in config:
            security_config = config["security"]
            if "privacy_level" in security_config:
                valid_levels = ["speed", "balanced", "paranoid"]
                if security_config["privacy_level"] not in valid_levels:
                    errors.append(f"Invalid privacy level. Must be one of: {valid_levels}")
        
        # Performance validation
        if "performance" in config:
            perf_config = config["performance"]
            if "max_concurrent_tasks" in perf_config:
                max_tasks = perf_config["max_concurrent_tasks"]
                if not isinstance(max_tasks, int) or max_tasks < 1 or max_tasks > 100:
                    errors.append("Max concurrent tasks must be between 1 and 100")
        
        return errors
    
    def _validate_api_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate API tier configuration"""
        errors = []
        
        # Strictest validation for API tier
        errors.extend(self._validate_yaml_config(config))
        
        # API-specific validation
        if "api" in config:
            api_config = config["api"]
            if "rate_limit" in api_config:
                rate_limit = api_config["rate_limit"]
                if not isinstance(rate_limit, int) or rate_limit < 1:
                    errors.append("API rate limit must be a positive integer")
        
        return errors
    
    def _save_ui_config(self, config: Dict[str, Any]):
        """Save UI tier configuration to JSON"""
        with open(self.ui_config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _save_yaml_config(self, config: Dict[str, Any]):
        """Save YAML tier configuration"""
        with open(self.yaml_config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
    
    def _save_api_config(self, config: Dict[str, Any]):
        """Save API tier configuration to JSON"""
        with open(self.api_config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def get_merged_configuration(self) -> Dict[str, Any]:
        """Get merged configuration from all tiers"""
        if not self._config_dirty and self._merged_config:
            return self._merged_config
        
        # Start with defaults
        merged = self._get_default_configuration()
        
        # Layer configurations: UI → YAML → API (API has highest priority)
        if self.ui_config_file.exists():
            try:
                with open(self.ui_config_file, 'r') as f:
                    ui_config = json.load(f)
                    merged = self._deep_merge(merged, ui_config)
            except Exception as e:
                logger.warning(f"Error loading UI config: {e}")
        
        if self.yaml_config_file.exists():
            try:
                with open(self.yaml_config_file, 'r') as f:
                    yaml_config = yaml.safe_load(f)
                    if yaml_config:
                        merged = self._deep_merge(merged, yaml_config)
            except Exception as e:
                logger.warning(f"Error loading YAML config: {e}")
        
        if self.api_config_file.exists():
            try:
                with open(self.api_config_file, 'r') as f:
                    api_config = json.load(f)
                    merged = self._deep_merge(merged, api_config)
            except Exception as e:
                logger.warning(f"Error loading API config: {e}")
        
        # Cache the result
        self._merged_config = merged
        self._config_dirty = False
        
        return merged
    
    def _deep_merge(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _get_default_configuration(self) -> Dict[str, Any]:
        """Get default configuration structure"""
        return {
            "ai": {
                "primary_provider": "openai",
                "api_key": "",
                "model": "gpt-4o",
                "fallback_providers": ["anthropic", "google"],
                "timeout": 30
            },
            "mqtt": {
                "broker_host": "localhost",
                "broker_port": 1883,
                "use_tls": False,
                "discovery_prefix": "homeassistant",
                "qos": 1
            },
            "zones": [],
            "notifications": {
                "enabled": True,
                "service": "notify.mobile_app",
                "personality": "default"
            },
            "security": {
                "privacy_level": "balanced",
                "data_retention_days": 90,
                "encrypt_config": False
            },
            "performance": {
                "max_concurrent_tasks": 5,
                "cache_duration": 300,
                "enable_profiling": False
            },
            "api": {
                "enabled": False,
                "rate_limit": 100,
                "require_auth": True
            },
            "system": {
                "version": "3.0.0",
                "install_date": None,
                "last_update": None
            }
        }
    
    def get_tier_capabilities(self, tier: ConfigurationTier) -> Dict[str, Any]:
        """Get capabilities and limitations for a specific tier"""
        settings = self.tier_settings[tier]
        
        return {
            "tier": tier.value,
            "enabled": settings.enabled,
            "description": self._get_tier_description(tier),
            "visible_fields": settings.fields_visible,
            "readonly_fields": settings.readonly_fields,
            "validation_level": settings.validation_level,
            "recommended_for": self._get_tier_recommendations(tier)
        }
    
    def _get_tier_description(self, tier: ConfigurationTier) -> str:
        """Get human-readable description for tier"""
        descriptions = {
            ConfigurationTier.UI_BASIC: "Essential settings for getting started. Simple UI controls for common tasks.",
            ConfigurationTier.YAML_ADVANCED: "Full configuration flexibility with YAML editing. Advanced performance tuning and security options.",
            ConfigurationTier.API_PROGRAMMATIC: "Script and automation access with REST API. Bulk operations and advanced debugging capabilities."
        }
        return descriptions.get(tier, "Unknown tier")
    
    def _get_tier_recommendations(self, tier: ConfigurationTier) -> List[str]:
        """Get recommendations for when to use each tier"""
        recommendations = {
            ConfigurationTier.UI_BASIC: [
                "First-time setup",
                "Basic configuration changes",
                "Users who prefer graphical interfaces"
            ],
            ConfigurationTier.YAML_ADVANCED: [
                "Power users who want full control",
                "Complex multi-zone setups", 
                "Custom automation rules",
                "Performance optimization"
            ],
            ConfigurationTier.API_PROGRAMMATIC: [
                "Automation and scripting",
                "Bulk configuration changes",
                "Integration with other systems",
                "Advanced debugging and troubleshooting"
            ]
        }
        return recommendations.get(tier, [])
    
    def export_configuration(self, tier: Optional[ConfigurationTier] = None) -> Dict[str, Any]:
        """Export configuration for backup or migration"""
        if tier:
            return {
                "tier": tier.value,
                "config": self.get_config_for_tier(tier),
                "capabilities": self.get_tier_capabilities(tier),
                "export_timestamp": None  # Would be set in production
            }
        else:
            return {
                "merged_config": self.get_merged_configuration(),
                "tier_configs": {
                    tier.value: self.get_config_for_tier(tier)
                    for tier in ConfigurationTier
                },
                "export_timestamp": None
            }
    
    def get_configuration_health(self) -> Dict[str, Any]:
        """Get health status of configuration system"""
        health = {
            "status": "healthy",
            "issues": [],
            "recommendations": []
        }
        
        # Check file accessibility
        for tier, file_path in [
            (ConfigurationTier.UI_BASIC, self.ui_config_file),
            (ConfigurationTier.YAML_ADVANCED, self.yaml_config_file),
            (ConfigurationTier.API_PROGRAMMATIC, self.api_config_file)
        ]:
            if file_path.exists():
                try:
                    # Try to read the file
                    if file_path.suffix == '.json':
                        with open(file_path, 'r') as f:
                            json.load(f)
                    elif file_path.suffix == '.yaml':
                        with open(file_path, 'r') as f:
                            yaml.safe_load(f)
                except Exception as e:
                    health["issues"].append(f"Cannot read {tier.value} config: {e}")
                    health["status"] = "degraded"
        
        # Check for configuration conflicts
        try:
            merged = self.get_merged_configuration()
            if not merged.get("ai", {}).get("api_key"):
                health["recommendations"].append("Configure AI API key for optimal functionality")
        except Exception as e:
            health["issues"].append(f"Cannot merge configurations: {e}")
            health["status"] = "error"
        
        return health