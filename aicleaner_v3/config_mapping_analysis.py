"""
Configuration Mapping Analysis for Phase 1A: Configuration Schema Consolidation

This module analyzes the three existing configuration files and identifies:
1. Overlapping keys and potential conflicts
2. Missing keys and dependencies
3. Schema inconsistencies
4. Mapping for unified configuration

Files analyzed:
- X:\aicleaner_v3\aicleaner_v3\config.yaml (Development config)
- X:\aicleaner_v3\aicleaner_v3\config.json (Home Assistant addon config)
- X:\aicleaner_v3\config.yaml (Root config)
"""

import json
import yaml
from typing import Dict, Any, List, Set, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ConfigMapping:
    """Stores configuration key mapping information"""
    key: str
    source_files: List[str]
    data_types: Set[str]
    default_values: Dict[str, Any]
    conflicts: List[str]
    schema_definition: str

class ConfigurationAnalyzer:
    """Analyzes configuration files and creates unified mapping"""
    
    def __init__(self, base_path: str = "X:/aicleaner_v3"):
        self.base_path = Path(base_path)
        self.config_files = {
            "addon_config_yaml": self.base_path / "aicleaner_v3" / "config.yaml",
            "addon_config_json": self.base_path / "aicleaner_v3" / "config.json",
            "root_config_yaml": self.base_path / "config.yaml"
        }
        self.configurations = {}
        self.mapping = {}
        self.conflicts = []
        self.recommendations = []
        
    def load_configurations(self) -> Dict[str, Dict[str, Any]]:
        """Load all configuration files"""
        
        # Load addon config.yaml
        with open(self.config_files["addon_config_yaml"], 'r') as f:
            self.configurations["addon_config_yaml"] = yaml.safe_load(f)
        
        # Load addon config.json
        with open(self.config_files["addon_config_json"], 'r') as f:
            self.configurations["addon_config_json"] = json.load(f)
        
        # Load root config.yaml
        with open(self.config_files["root_config_yaml"], 'r') as f:
            self.configurations["root_config_yaml"] = yaml.safe_load(f)
        
        return self.configurations
    
    def analyze_key_overlaps(self) -> Dict[str, ConfigMapping]:
        """Analyze key overlaps across configuration files"""
        all_keys = set()
        
        # Collect all keys from all configurations
        for config_name, config_data in self.configurations.items():
            all_keys.update(self._get_all_keys(config_data))
        
        # Analyze each key
        for key in all_keys:
            mapping = self._analyze_key(key)
            self.mapping[key] = mapping
            
        return self.mapping
    
    def _get_all_keys(self, config_data: Dict[str, Any], prefix: str = "") -> Set[str]:
        """Recursively get all keys from configuration"""
        keys = set()
        
        for key, value in config_data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.add(full_key)
            
            if isinstance(value, dict):
                keys.update(self._get_all_keys(value, full_key))
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # Handle lists of dictionaries (like zones)
                for item in value:
                    if isinstance(item, dict):
                        keys.update(self._get_all_keys(item, f"{full_key}[]"))
        
        return keys
    
    def _analyze_key(self, key: str) -> ConfigMapping:
        """Analyze a specific key across all configurations"""
        source_files = []
        data_types = set()
        default_values = {}
        conflicts = []
        
        for config_name, config_data in self.configurations.items():
            value = self._get_nested_value(config_data, key)
            if value is not None:
                source_files.append(config_name)
                data_types.add(type(value).__name__)
                default_values[config_name] = value
        
        # Detect conflicts
        if len(data_types) > 1:
            conflicts.append(f"Data type conflict: {data_types}")
        
        if len(set(str(v) for v in default_values.values())) > 1:
            conflicts.append(f"Default value conflict: {default_values}")
        
        return ConfigMapping(
            key=key,
            source_files=source_files,
            data_types=data_types,
            default_values=default_values,
            conflicts=conflicts,
            schema_definition=self._generate_schema_definition(key, data_types, default_values)
        )
    
    def _get_nested_value(self, config_data: Dict[str, Any], key: str) -> Any:
        """Get value from nested dictionary using dot notation"""
        keys = key.split('.')
        current = config_data
        
        for k in keys:
            if k.endswith('[]'):
                # Handle array notation
                k = k[:-2]
                if k in current and isinstance(current[k], list) and current[k]:
                    current = current[k][0]  # Take first item as example
                else:
                    return None
            else:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return None
        
        return current
    
    def _generate_schema_definition(self, key: str, data_types: Set[str], default_values: Dict[str, Any]) -> str:
        """Generate schema definition for a key"""
        if not data_types:
            return "unknown"
        
        # Determine the most appropriate type
        if "str" in data_types:
            return "str"
        elif "int" in data_types:
            return "int"
        elif "float" in data_types:
            return "float"
        elif "bool" in data_types:
            return "bool"
        elif "list" in data_types:
            return "list"
        elif "dict" in data_types:
            return "dict"
        else:
            return list(data_types)[0]
    
    def generate_unified_schema(self) -> Dict[str, Any]:
        """Generate unified configuration schema"""
        schema = {
            "name": "str",
            "version": "str", 
            "slug": "str",
            "description": "str",
            "display_name": "str",
            "gemini_api_key": "str",
            "ha_token": "str?",
            "ha_api_url": "str?",
            "mqtt_enabled": "bool?",
            "mqtt_host": "str?",
            "mqtt_port": "int?",
            "mqtt_username": "str?",
            "mqtt_password": "password?",
            "ai_enhancements": {
                "advanced_scene_understanding": "bool?",
                "predictive_analytics": "bool?",
                "caching": {
                    "enabled": "bool?",
                    "ttl_seconds": "int?",
                    "intermediate_caching": "bool?",
                    "max_cache_entries": "int?"
                },
                "scene_understanding_settings": {
                    "max_objects_detected": "int?",
                    "max_generated_tasks": "int?",
                    "confidence_threshold": "float?",
                    "enable_seasonal_adjustments": "bool?",
                    "enable_time_context": "bool?"
                },
                "predictive_analytics_settings": {
                    "history_days": "int?",
                    "prediction_horizon_hours": "int?",
                    "min_data_points": "int?",
                    "enable_urgency_scoring": "bool?",
                    "enable_pattern_detection": "bool?"
                },
                "multi_model_ai": {
                    "enable_fallback": "bool?",
                    "max_retries": "int?",
                    "timeout_seconds": "int?",
                    "performance_tracking": "bool?"
                },
                "local_llm": {
                    "enabled": "bool?",
                    "ollama_host": "str?",
                    "preferred_models": {
                        "vision": "str?",
                        "text": "str?",
                        "task_generation": "str?",
                        "fallback": "str?"
                    },
                    "resource_limits": {
                        "max_cpu_usage": "int?",
                        "max_memory_usage": "int?"
                    },
                    "performance_tuning": {
                        "quantization_level": "int?",
                        "batch_size": "int?",
                        "timeout_seconds": "int?"
                    },
                    "auto_download": "bool?",
                    "max_concurrent": "int?"
                }
            },
            "inference_tuning": {
                "enabled": "bool?",
                "profile": "str?"
            },
            "zones": [{
                "name": "str",
                "camera_entity": "str",
                "todo_list_entity": "str",
                "purpose": "str?",
                "interval_minutes": "int?",
                "update_frequency": "int?",
                "icon": "str?",
                "notifications_enabled": "bool?",
                "notification_service": "str?",
                "notification_personality": "str?",
                "notify_on_create": "bool?",
                "notify_on_complete": "bool?",
                "ignore_rules": ["str?"],
                "specific_times": ["str?"],
                "random_offset_minutes": "int?"
            }]
        }
        
        return schema
    
    def identify_conflicts(self) -> List[Dict[str, Any]]:
        """Identify configuration conflicts"""
        conflicts = []
        
        # Check for overlapping keys with different values
        overlapping_keys = [
            "display_name",
            "gemini_api_key", 
            "zones"
        ]
        
        for key in overlapping_keys:
            values = {}
            for config_name, config_data in self.configurations.items():
                value = self._get_nested_value(config_data, key)
                if value is not None:
                    values[config_name] = value
            
            if len(values) > 1:
                unique_values = set(str(v) for v in values.values())
                if len(unique_values) > 1:
                    conflicts.append({
                        "key": key,
                        "type": "value_conflict",
                        "values": values,
                        "resolution": "Use most comprehensive value or merge"
                    })
        
        # Check for schema conflicts
        # config.json uses "options" and "schema" structure
        # config.yaml files use direct key-value structure
        conflicts.append({
            "key": "root_structure",
            "type": "schema_conflict",
            "description": "config.json uses HA addon structure with options/schema, yaml files use direct structure",
            "resolution": "Unified schema should follow HA addon format with comprehensive options"
        })
        
        return conflicts
    
    def generate_recommendations(self) -> List[str]:
        """Generate consolidation recommendations"""
        recommendations = [
            "Consolidate into single config.yaml file following HA addon standards",
            "Use config.json structure as template for HA addon compliance",
            "Merge all AI enhancement settings into unified ai_enhancements section",
            "Standardize zone configuration to include all optional fields",
            "Implement configuration migration for existing setups",
            "Add comprehensive validation for all configuration keys",
            "Create backup mechanism before any configuration changes",
            "Implement rollback capability for failed migrations",
            "Add security validation for API keys and sensitive data",
            "Create user-friendly error messages for configuration issues"
        ]
        
        return recommendations
    
    def create_analysis_report(self) -> Dict[str, Any]:
        """Create comprehensive analysis report"""
        return {
            "configuration_files": list(self.config_files.keys()),
            "total_keys_analyzed": len(self.mapping),
            "conflicts_found": len(self.conflicts),
            "key_mapping": {k: {
                "source_files": v.source_files,
                "data_types": list(v.data_types),
                "conflicts": v.conflicts,
                "schema_definition": v.schema_definition
            } for k, v in self.mapping.items()},
            "identified_conflicts": self.identify_conflicts(),
            "recommendations": self.generate_recommendations(),
            "unified_schema": self.generate_unified_schema()
        }

# Analysis execution
if __name__ == "__main__":
    analyzer = ConfigurationAnalyzer()
    analyzer.load_configurations()
    analyzer.analyze_key_overlaps()
    report = analyzer.create_analysis_report()
    
    # Save analysis report
    with open("config_analysis_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print("Configuration analysis complete. Report saved to config_analysis_report.json")