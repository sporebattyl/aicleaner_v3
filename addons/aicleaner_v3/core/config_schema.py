"""
Unified Configuration Schema for AICleaner v3
Phase 1A: Configuration Schema Consolidation

This module defines the complete unified configuration schema that consolidates
all three configuration files into a single, comprehensive schema following
Home Assistant addon standards.

Key Features:
- Complete schema definition with all required and optional fields
- Home Assistant addon compliance (config.json format)
- Comprehensive validation rules and constraints
- Clear component interfaces
- Type safety with proper annotations
- Default values and validation ranges
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import os

class ConfigurationProfile(Enum):
    """Performance optimization profiles for inference tuning"""
    AUTO = "auto"
    RESOURCE_EFFICIENT = "resource_efficient"
    BALANCED = "balanced"
    MAXIMUM_PERFORMANCE = "maximum_performance"

class NotificationPersonality(Enum):
    """Available notification personalities"""
    DEFAULT = "default"
    SNARKY = "snarky"
    JARVIS = "jarvis"
    ROASTER = "roaster"
    BUTLER = "butler"
    COACH = "coach"
    ZEN = "zen"

@dataclass
class CachingSettings:
    """AI model caching configuration"""
    enabled: bool = True
    ttl_seconds: int = 300
    intermediate_caching: bool = True
    max_cache_entries: int = 1000

@dataclass
class SceneUnderstandingSettings:
    """Scene understanding AI configuration"""
    max_objects_detected: int = 10
    max_generated_tasks: int = 8
    confidence_threshold: float = 0.7
    enable_seasonal_adjustments: bool = True
    enable_time_context: bool = True

@dataclass
class PredictiveAnalyticsSettings:
    """Predictive analytics configuration"""
    history_days: int = 30
    prediction_horizon_hours: int = 24
    min_data_points: int = 5
    enable_urgency_scoring: bool = True
    enable_pattern_detection: bool = True

@dataclass
class MultiModelAISettings:
    """Simplified Multi-model AI configuration for single-user context"""
    enable_fallback: bool = True
    max_retries: int = 3
    timeout_seconds: int = 30

@dataclass
class AIProviderSettings:
    """Simplified AI Provider configuration for single-user context"""
    enabled: bool = True
    priority: int = 1
    model_name: str = ""
    base_url: Optional[str] = None
    timeout_seconds: int = 30
    max_retries: int = 3
    max_concurrent_requests: int = 1
    fallback_enabled: bool = True

@dataclass
class AIProviderManagerSettings:
    """Simplified AI Provider Manager configuration for single-user context"""
    selection_strategy: str = "priority"
    
    # Provider configurations
    openai: AIProviderSettings = field(default_factory=lambda: AIProviderSettings(
        enabled=True,
        priority=1,
        model_name="gpt-4-vision-preview"
    ))
    
    anthropic: AIProviderSettings = field(default_factory=lambda: AIProviderSettings(
        enabled=True,
        priority=2,
        model_name="claude-3-5-sonnet-20241022"
    ))
    
    google: AIProviderSettings = field(default_factory=lambda: AIProviderSettings(
        enabled=True,
        priority=3,
        model_name="gemini-1.5-flash"
    ))
    
    ollama: AIProviderSettings = field(default_factory=lambda: AIProviderSettings(
        enabled=True,
        priority=4,
        model_name="llava:13b",
        base_url="http://localhost:11434",
        timeout_seconds=60
    ))

@dataclass
class LocalLLMSettings:
    """Simplified Local LLM configuration for single-user context"""
    enabled: bool = True
    ollama_host: str = "localhost:11434"
    auto_download: bool = True
    max_concurrent: int = 1

@dataclass
class AIEnhancementsSettings:
    """AI enhancements configuration"""
    advanced_scene_understanding: bool = True
    predictive_analytics: bool = True
    caching: CachingSettings = field(default_factory=CachingSettings)
    scene_understanding_settings: SceneUnderstandingSettings = field(default_factory=SceneUnderstandingSettings)
    predictive_analytics_settings: PredictiveAnalyticsSettings = field(default_factory=PredictiveAnalyticsSettings)
    multi_model_ai: MultiModelAISettings = field(default_factory=MultiModelAISettings)
    local_llm: LocalLLMSettings = field(default_factory=LocalLLMSettings)
    # Phase 2A: AI Provider Manager Settings
    ai_provider_manager: AIProviderManagerSettings = field(default_factory=AIProviderManagerSettings)

@dataclass
class InferenceTuningSettings:
    """Inference tuning configuration"""
    enabled: bool = True
    profile: ConfigurationProfile = ConfigurationProfile.AUTO

@dataclass
class ZoneConfiguration:
    """Zone configuration"""
    name: str
    camera_entity: str
    todo_list_entity: str
    purpose: Optional[str] = None
    interval_minutes: Optional[int] = None
    update_frequency: Optional[int] = None
    icon: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    notification_service: Optional[str] = None
    notification_personality: Optional[NotificationPersonality] = None
    notify_on_create: Optional[bool] = None
    notify_on_complete: Optional[bool] = None
    ignore_rules: Optional[List[str]] = None
    specific_times: Optional[List[str]] = None
    random_offset_minutes: Optional[int] = None

@dataclass
class MQTTSettings:
    """MQTT configuration"""
    enabled: bool = False
    host: str = "core-mosquitto"
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None

@dataclass
class UnifiedConfiguration:
    """
    Unified configuration schema that consolidates all three config files
    Following Home Assistant addon standards
    """
    # Required Home Assistant addon fields
    name: str
    version: str
    slug: str
    description: str
    
    # Required application fields
    display_name: str
    gemini_api_key: str
    
    # Optional Home Assistant fields
    ha_token: Optional[str] = None
    ha_api_url: Optional[str] = None
    
    # MQTT configuration
    mqtt: MQTTSettings = field(default_factory=MQTTSettings)
    
    # AI enhancements
    ai_enhancements: AIEnhancementsSettings = field(default_factory=AIEnhancementsSettings)
    
    # Inference tuning
    inference_tuning: InferenceTuningSettings = field(default_factory=InferenceTuningSettings)
    
    # Zones configuration
    zones: List[ZoneConfiguration] = field(default_factory=list)

class ConfigurationSchemaGenerator:
    """Generate Home Assistant addon configuration schema"""
    
    @staticmethod
    def generate_addon_schema() -> Dict[str, Any]:
        """Generate complete Home Assistant addon configuration schema"""
        return {
            "name": "AICleaner v3",
            "version": "3.0.0",
            "slug": "aicleaner_v3",
            "description": "AI-powered cleaning task management using Gemini Vision API",
            "url": "https://github.com/yourusername/aicleaner",
            "arch": ["armhf", "armv7", "aarch64", "amd64", "i386"],
            "startup": "application",
            "boot": "auto",
            "init": False,
            "homeassistant_api": True,
            "hassio_api": True,
            "ingress": True,
            "ingress_port": 8099,
            "panel_icon": "mdi:robot-vacuum",
            "panel_title": "AI Cleaner",
            "map": ["config:rw", "ssl"],
            "host_network": False,
            "services": ["mqtt:need"],
            "ports": {
                "8099/tcp": 8099
            },
            "options": ConfigurationSchemaGenerator.generate_default_options(),
            "schema": ConfigurationSchemaGenerator.generate_validation_schema()
        }
    
    @staticmethod
    def generate_default_options() -> Dict[str, Any]:
        """Generate default configuration options"""
        return {
            "display_name": "AI Cleaner",
            "gemini_api_key": "",
            "ha_token": "",
            "ha_api_url": "http://supervisor/core/api",
            "mqtt": {
                "enabled": False,
                "host": "core-mosquitto",
                "port": 1883,
                "username": "",
                "password": ""
            },
            "ai_enhancements": {
                "advanced_scene_understanding": True,
                "predictive_analytics": True,
                "caching": {
                    "enabled": True,
                    "ttl_seconds": 300,
                    "intermediate_caching": True,
                    "max_cache_entries": 1000
                },
                "scene_understanding_settings": {
                    "max_objects_detected": 10,
                    "max_generated_tasks": 8,
                    "confidence_threshold": 0.7,
                    "enable_seasonal_adjustments": True,
                    "enable_time_context": True
                },
                "predictive_analytics_settings": {
                    "history_days": 30,
                    "prediction_horizon_hours": 24,
                    "min_data_points": 5,
                    "enable_urgency_scoring": True,
                    "enable_pattern_detection": True
                },
                "multi_model_ai": {
                    "enable_fallback": True,
                    "max_retries": 3,
                    "timeout_seconds": 30
                },
                "local_llm": {
                    "enabled": True,
                    "ollama_host": "localhost:11434",
                    "auto_download": True,
                    "max_concurrent": 1
                },
                "ai_provider_manager": {
                    "selection_strategy": "priority",
                    "openai": {
                        "enabled": True,
                        "priority": 1,
                        "model_name": "gpt-4-vision-preview",
                        "timeout_seconds": 30,
                        "max_retries": 3,
                        "max_concurrent_requests": 1,
                        "fallback_enabled": True
                    },
                    "anthropic": {
                        "enabled": True,
                        "priority": 2,
                        "model_name": "claude-3-5-sonnet-20241022",
                        "timeout_seconds": 30,
                        "max_retries": 3,
                        "max_concurrent_requests": 1,
                        "fallback_enabled": True
                    },
                    "google": {
                        "enabled": True,
                        "priority": 3,
                        "model_name": "gemini-1.5-flash",
                        "timeout_seconds": 25,
                        "max_retries": 3,
                        "max_concurrent_requests": 1,
                        "fallback_enabled": True
                    },
                    "ollama": {
                        "enabled": True,
                        "priority": 4,
                        "model_name": "llava:13b",
                        "base_url": "http://localhost:11434",
                        "timeout_seconds": 60,
                        "max_retries": 2,
                        "max_concurrent_requests": 1,
                        "fallback_enabled": True
                    }
                }
            },
            "inference_tuning": {
                "enabled": True,
                "profile": "auto"
            },
            "zones": []
        }
    
    @staticmethod
    def generate_validation_schema() -> Dict[str, Any]:
        """Generate validation schema for Home Assistant"""
        return {
            "display_name": "str",
            "gemini_api_key": "str",
            "ha_token": "str?",
            "ha_api_url": "str?",
            "mqtt": {
                "enabled": "bool?",
                "host": "str?",
                "port": "port?",
                "username": "str?",
                "password": "password?"
            },
            "ai_enhancements": {
                "advanced_scene_understanding": "bool?",
                "predictive_analytics": "bool?",
                "caching": {
                    "enabled": "bool?",
                    "ttl_seconds": "int(60,3600)?",
                    "intermediate_caching": "bool?",
                    "max_cache_entries": "int(100,10000)?"
                },
                "scene_understanding_settings": {
                    "max_objects_detected": "int(1,50)?",
                    "max_generated_tasks": "int(1,20)?",
                    "confidence_threshold": "float(0.0,1.0)?",
                    "enable_seasonal_adjustments": "bool?",
                    "enable_time_context": "bool?"
                },
                "predictive_analytics_settings": {
                    "history_days": "int(1,365)?",
                    "prediction_horizon_hours": "int(1,168)?",
                    "min_data_points": "int(1,100)?",
                    "enable_urgency_scoring": "bool?",
                    "enable_pattern_detection": "bool?"
                },
                "multi_model_ai": {
                    "enable_fallback": "bool?",
                    "max_retries": "int(1,10)?",
                    "timeout_seconds": "int(5,300)?"
                },
                "local_llm": {
                    "enabled": "bool?",
                    "ollama_host": "str?",
                    "auto_download": "bool?",
                    "max_concurrent": "int(1,10)?"
                },
                "ai_provider_manager": {
                    "selection_strategy": "list(priority)?",
                    "openai": {
                        "enabled": "bool?",
                        "priority": "int(1,10)?",
                        "model_name": "str?",
                        "timeout_seconds": "int(5,300)?",
                        "max_retries": "int(0,10)?",
                        "max_concurrent_requests": "int(1,20)?",
                        "fallback_enabled": "bool?"
                    },
                    "anthropic": {
                        "enabled": "bool?",
                        "priority": "int(1,10)?",
                        "model_name": "str?",
                        "timeout_seconds": "int(5,300)?",
                        "max_retries": "int(0,10)?",
                        "max_concurrent_requests": "int(1,20)?",
                        "fallback_enabled": "bool?"
                    },
                    "google": {
                        "enabled": "bool?",
                        "priority": "int(1,10)?",
                        "model_name": "str?",
                        "timeout_seconds": "int(5,300)?",
                        "max_retries": "int(0,10)?",
                        "max_concurrent_requests": "int(1,20)?",
                        "fallback_enabled": "bool?"
                    },
                    "ollama": {
                        "enabled": "bool?",
                        "priority": "int(1,10)?",
                        "model_name": "str?",
                        "base_url": "str?",
                        "timeout_seconds": "int(5,300)?",
                        "max_retries": "int(0,10)?",
                        "max_concurrent_requests": "int(1,20)?",
                        "fallback_enabled": "bool?"
                    }
                }
            },
            "inference_tuning": {
                "enabled": "bool?",
                "profile": "list(auto|resource_efficient|balanced|maximum_performance)?"
            },
            "zones": [
                {
                    "name": "str",
                    "camera_entity": "str",
                    "todo_list_entity": "str",
                    "purpose": "str?",
                    "interval_minutes": "int(5,1440)?",
                    "update_frequency": "int(1,168)?",
                    "icon": "str?",
                    "notifications_enabled": "bool?",
                    "notification_service": "str?",
                    "notification_personality": "list(default|snarky|jarvis|roaster|butler|coach|zen)?",
                    "notify_on_create": "bool?",
                    "notify_on_complete": "bool?",
                    "ignore_rules": ["str?"],
                    "specific_times": ["str?"],
                    "random_offset_minutes": "int(0,120)?"
                }
            ]
        }

def create_unified_config_file(output_path: str = "config.yaml") -> None:
    """Create unified configuration file"""
    schema_generator = ConfigurationSchemaGenerator()
    unified_config = schema_generator.generate_addon_schema()
    
    # Write to YAML format for Home Assistant addon
    import yaml
    with open(output_path, 'w') as f:
        yaml.dump(unified_config, f, default_flow_style=False, sort_keys=False, indent=2)
    
    print(f"Unified configuration schema created at: {output_path}")

if __name__ == "__main__":
    create_unified_config_file()