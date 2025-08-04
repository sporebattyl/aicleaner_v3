#!/usr/bin/env python3
"""
Configuration Mapper for AICleaner v3 Home Assistant Addon
Maps simplified Home Assistant addon options to complex internal configuration structure.
"""

import json
import yaml
import os
import sys
from pathlib import Path
from typing import Dict, Any, List


def get_default_options() -> Dict[str, Any]:
    """Return comprehensive default options for the addon."""
    return {
        "log_level": "info",
        "device_id": "aicleaner_v3",
        "primary_api_key": "",
        "backup_api_keys": [],
        "mqtt_discovery_prefix": "homeassistant",
        "mqtt_external_broker": False,
        "mqtt_host": "",
        "mqtt_port": 1883,
        "mqtt_username": "",
        "mqtt_password": "",
        "default_camera": "",
        "default_todo_list": "",
        "enable_zones": False,
        "zones": [],
        "debug_mode": False,
        "auto_dashboard": True
    }

def load_addon_options() -> Dict[str, Any]:
    """Load addon options from Home Assistant options.json file with robust fallbacks."""
    options_file = Path("/data/options.json")
    defaults = get_default_options()
    
    if not options_file.exists():
        print("INFO: No options.json found, using default configuration")
        print("INFO: This is normal for first startup or development environment")
        return defaults
    
    try:
        with open(options_file, 'r') as f:
            loaded_options = json.load(f)
            
        # Merge loaded options with defaults to ensure all keys exist
        merged_options = defaults.copy()
        merged_options.update(loaded_options)
        
        print(f"INFO: Configuration loaded with {len(loaded_options)} user settings")
        return merged_options
        
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in options.json: {e}")
        print("INFO: Using default configuration")
        return defaults
    except Exception as e:
        print(f"ERROR: Failed to load options.json: {e}")
        print("INFO: Using default configuration")
        return defaults


def map_log_level(addon_log_level: str) -> str:
    """Map addon log level to internal format."""
    level_mapping = {
        "debug": "DEBUG",
        "info": "INFO", 
        "warning": "WARNING",
        "error": "ERROR"
    }
    return level_mapping.get(addon_log_level.lower(), "INFO")


def determine_active_provider(primary_api_key: str, backup_api_keys: List[str]) -> str:
    """Determine which AI provider to use based on available API keys."""
    # Check if we have Gemini API key (preferred)
    if primary_api_key.strip():
        return "gemini"
    
    # Check backup keys for other providers
    for key in backup_api_keys:
        if key.strip():
            return "gemini"  # Use gemini for all cloud keys
    
    # Fallback to local Ollama
    return "ollama"


def create_user_config(options: Dict[str, Any]) -> Dict[str, Any]:
    """Create user configuration from addon options with robust defaults."""
    
    # Get defaults for fallback
    defaults = get_default_options()
    
    # Extract values with robust defaults (using defaults dict as fallback)
    log_level = options.get("log_level", defaults["log_level"])
    device_id = options.get("device_id", defaults["device_id"])
    primary_api_key = options.get("primary_api_key", defaults["primary_api_key"])
    backup_api_keys = options.get("backup_api_keys", defaults["backup_api_keys"])
    mqtt_discovery_prefix = options.get("mqtt_discovery_prefix", defaults["mqtt_discovery_prefix"])
    mqtt_external_broker = options.get("mqtt_external_broker", defaults["mqtt_external_broker"])
    mqtt_host = options.get("mqtt_host", defaults["mqtt_host"])
    mqtt_port = options.get("mqtt_port", defaults["mqtt_port"])
    mqtt_username = options.get("mqtt_username", defaults["mqtt_username"])
    mqtt_password = options.get("mqtt_password", defaults["mqtt_password"])
    debug_mode = options.get("debug_mode", defaults["debug_mode"])
    auto_dashboard = options.get("auto_dashboard", defaults["auto_dashboard"])
    
    # Extract entity selections with defaults
    default_camera = options.get("default_camera", defaults["default_camera"])
    default_todo_list = options.get("default_todo_list", defaults["default_todo_list"])
    enable_zones = options.get("enable_zones", defaults["enable_zones"])
    zones = options.get("zones", defaults["zones"])
    
    # Validate and sanitize values
    if not isinstance(backup_api_keys, list):
        backup_api_keys = []
    if not isinstance(zones, list):
        zones = []
    
    # Determine active provider
    active_provider = determine_active_provider(primary_api_key, backup_api_keys)
    
    # Build user configuration
    user_config = {
        "general": {
            "active_provider": active_provider,
            "log_level": "DEBUG" if debug_mode else map_log_level(log_level)
        },
        "mqtt": {
            "auto_discovery": {
                "topic_prefix": mqtt_discovery_prefix
            }
        }
    }
    
    # Add external MQTT broker configuration if enabled
    if mqtt_external_broker and mqtt_host:
        user_config["mqtt"]["broker"] = {
            "host": mqtt_host,
            "port": mqtt_port,
            "external": True
        }
        
        # Add authentication if provided
        if mqtt_username or mqtt_password:
            user_config["mqtt"]["broker"]["auth"] = {
                "username": mqtt_username,
                "password": mqtt_password
            }
    
    # Add entity configuration
    if default_camera or default_todo_list or enable_zones:
        entity_config = {}
        
        # Basic entity selections
        if default_camera:
            entity_config["default_camera"] = default_camera
        if default_todo_list:
            entity_config["default_todo_list"] = default_todo_list
            
        # Zone configuration (advanced mode)
        if enable_zones and zones:
            entity_config["zones"] = []
            for zone in zones:
                if isinstance(zone, dict) and "name" in zone:
                    zone_config = {
                        "name": zone.get("name", ""),
                        "camera_entity": zone.get("camera_entity", ""),
                        "todo_list_entity": zone.get("todo_list_entity", ""),
                        "check_interval_minutes": zone.get("check_interval_minutes", 30),
                        "ignore_rules": zone.get("ignore_rules", [])
                    }
                    entity_config["zones"].append(zone_config)
        
        if entity_config:
            user_config["entities"] = entity_config
    
    # Add AI provider configuration if keys are provided
    if primary_api_key.strip() or backup_api_keys:
        ai_providers = {}
        
        # Configure Gemini if primary key provided
        if primary_api_key.strip():
            ai_providers["gemini"] = {
                "api_key": primary_api_key
            }
        # Only use backup keys if no primary key is provided
        elif backup_api_keys:
            for key in backup_api_keys:
                if key.strip():
                    ai_providers["gemini"] = {
                        "api_key": key
                    }
                    break  # Use first valid backup key
        
        if ai_providers:
            user_config["ai_providers"] = ai_providers
    
    return user_config


def write_user_config(config: Dict[str, Any], target_path: str = "/app/src/app_config.user.yaml"):
    """Write user configuration to YAML file."""
    
    try:
        # Ensure directory exists
        target_dir = Path(target_path).parent
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Write configuration with header
        with open(target_path, 'w') as f:
            f.write("""# ------------------------------------------------------------------------------
# User Configuration - Auto-generated from Home Assistant Addon Options
#
# This file is automatically generated from the addon's configuration options.
# DO NOT EDIT MANUALLY - Use Home Assistant's addon configuration UI instead.
# ------------------------------------------------------------------------------

""")
            yaml.dump(config, f, default_flow_style=False, indent=2)
            
        print(f"✓ User configuration written to {target_path}")
        
    except Exception as e:
        print(f"ERROR: Failed to write user config: {e}")
        sys.exit(1)


def main():
    """Main configuration mapping function."""
    print("Mapping Home Assistant addon options to internal configuration...")
    
    # Load addon options
    options = load_addon_options()
    print(f"Loaded options: {list(options.keys())}")
    
    # Create user configuration
    user_config = create_user_config(options)
    
    # Write user configuration
    write_user_config(user_config)
    
    print("Configuration mapping completed successfully!")


if __name__ == "__main__":
    main()