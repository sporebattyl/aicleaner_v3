#!/usr/bin/env python3
"""
Configuration Mapper for AICleaner v3 Home Assistant Addon
Maps simplified Home Assistant addon options to complex internal configuration structure.
"""

import json
import yaml
import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


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
    
    logger.info(f"[CONFIG_MAPPER] Loading configuration from {options_file}")
    
    if not options_file.exists():
        logger.warning(f"[CONFIG_MAPPER] WARNING: Configuration file {options_file} not found")
        logger.info(f"[CONFIG_MAPPER] Using default configuration")
        return defaults
    
    # Check file size and readability
    file_size = options_file.stat().st_size
    logger.info(f"[CONFIG_MAPPER] Configuration file found, size: {file_size} bytes")
    
    if file_size == 0:
        logger.error(f"[CONFIG_MAPPER] ERROR: Configuration file is empty")
        logger.info(f"[CONFIG_MAPPER] Using default configuration")
        return defaults
    
    try:
        with open(options_file, 'r') as f:
            file_content = f.read()
            logger.info(f"[CONFIG_MAPPER] File content length: {len(file_content)} characters")
            
            # Show first 200 chars for debugging (redacted)
            preview = file_content[:200].replace('"api_key":', '"***"').replace('"password":', '"***"')
            logger.info(f"[CONFIG_MAPPER] Content preview: {preview}{'...' if len(file_content) > 200 else ''}")
            
            loaded_options = json.loads(file_content)
            logger.info(f"[CONFIG_MAPPER] Successfully parsed JSON with {len(loaded_options)} keys")
            
            # Log which options were found vs missing
            for key in defaults.keys():
                if key in loaded_options:
                    if key not in ['primary_api_key', 'backup_api_keys', 'mqtt_password']:
                        logger.info(f"[CONFIG_MAPPER]   ✓ {key}: {loaded_options[key]}")
                    else:
                        logger.info(f"[CONFIG_MAPPER]   ✓ {key}: ***REDACTED***")
                else:
                    logger.info(f"[CONFIG_MAPPER]   ⚠️  {key}: missing, will use default ({defaults[key]})")
            
            # Check for unexpected keys
            extra_keys = set(loaded_options.keys()) - set(defaults.keys())
            if extra_keys:
                logger.info(f"[CONFIG_MAPPER] Extra keys found (will be ignored): {list(extra_keys)}")
            
            # Validate specific problematic fields
            if 'backup_api_keys' in loaded_options:
                backup_keys = loaded_options['backup_api_keys']
                if not isinstance(backup_keys, list):
                    logger.info(f"[CONFIG_MAPPER] ERROR: backup_api_keys is not a list: {type(backup_keys)} = {backup_keys}")
                    logger.info(f"[CONFIG_MAPPER] Converting to empty list")
                    loaded_options['backup_api_keys'] = []
                elif backup_keys == ["str"] or "str" in backup_keys:
                    logger.info(f"[CONFIG_MAPPER] ERROR: backup_api_keys contains literal 'str' value")
                    logger.info(f"[CONFIG_MAPPER] This should be [] (empty array) or actual API keys")
                    loaded_options['backup_api_keys'] = []
        
            # Merge loaded options with defaults to ensure all keys exist
            merged_options = defaults.copy()
            merged_options.update(loaded_options)
            
            logger.info(f"[CONFIG_MAPPER] Configuration loaded successfully with {len(merged_options)} final options")
            return merged_options
        
    except json.JSONDecodeError as e:
        logger.info(f"[CONFIG_MAPPER] ERROR: JSON parsing failed: {e}")
        logger.info(f"[CONFIG_MAPPER] File content that failed to parse (first 500 chars):")
        try:
            with open(options_file, 'r') as f:
                content = f.read(500)
                logger.info(f"[CONFIG_MAPPER] {repr(content)}")
        except Exception:
            logger.info(f"[CONFIG_MAPPER] Could not read file content for debugging")
        logger.info(f"[CONFIG_MAPPER] Using default configuration")
        return defaults
    except Exception as e:
        logger.info(f"[CONFIG_MAPPER] ERROR: Unexpected error loading configuration: {e}")
        logger.info(f"[CONFIG_MAPPER] Using default configuration")
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
    
    logger.info(f"[CONFIG_MAPPER] Writing user configuration to {target_path}")
    
    try:
        # Ensure directory exists
        target_dir = Path(target_path).parent
        logger.info(f"[CONFIG_MAPPER] Ensuring directory exists: {target_dir}")
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate configuration structure before writing
        if not isinstance(config, dict):
            logger.info(f"[CONFIG_MAPPER] ERROR: Configuration is not a dict: {type(config)}")
            sys.exit(1)
        
        logger.info(f"[CONFIG_MAPPER] Configuration structure summary:")
        for key, value in config.items():
            if isinstance(value, dict):
                logger.info(f"[CONFIG_MAPPER]   {key}: dict with {len(value)} keys")
            elif isinstance(value, list):
                logger.info(f"[CONFIG_MAPPER]   {key}: list with {len(value)} items")
            else:
                logger.info(f"[CONFIG_MAPPER]   {key}: {type(value).__name__}")
        
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
        
        # Verify file was written successfully
        if Path(target_path).exists():
            file_size = Path(target_path).stat().st_size
            logger.info(f"[CONFIG_MAPPER] ✓ Configuration file written successfully ({file_size} bytes)")
        else:
            logger.info(f"[CONFIG_MAPPER] ERROR: Configuration file was not created")
            sys.exit(1)
            
    except yaml.YAMLError as e:
        logger.info(f"[CONFIG_MAPPER] ERROR: YAML serialization failed: {e}")
        logger.info(f"[CONFIG_MAPPER] Configuration structure that failed:")
        logger.info(f"[CONFIG_MAPPER] {config}")
        sys.exit(1)
    except OSError as e:
        logger.info(f"[CONFIG_MAPPER] ERROR: File system error: {e}")
        logger.info(f"[CONFIG_MAPPER] Target path: {target_path}")
        logger.info(f"[CONFIG_MAPPER] Target directory: {target_dir}")
        sys.exit(1)
    except Exception as e:
        logger.info(f"[CONFIG_MAPPER] ERROR: Unexpected error writing configuration: {e}")
        logger.info(f"[CONFIG_MAPPER] Configuration: {config}")
        sys.exit(1)


def main():
    """Main configuration mapping function."""
    
    logger.info(f"[CONFIG_MAPPER] ========================================")
    logger.info(f"[CONFIG_MAPPER] AICleaner V3 Configuration Mapper")
    logger.info(f"[CONFIG_MAPPER] ========================================")
    
    try:
        # Load addon options
        logger.info(f"[CONFIG_MAPPER] Step 1: Loading addon options...")
        options = load_addon_options()
        
        if not options:
            logger.info(f"[CONFIG_MAPPER] ERROR: No options loaded")
            sys.exit(1)
        
        # Validate critical options
        logger.info(f"[CONFIG_MAPPER] Step 2: Validating critical configuration...")
        required_keys = ["device_id", "log_level", "mqtt_discovery_prefix"]
        for key in required_keys:
            if key not in options or not options[key]:
                logger.info(f"[CONFIG_MAPPER] ERROR: Required key '{key}' is missing or empty")
                sys.exit(1)
        
        # Create user configuration
        logger.info(f"[CONFIG_MAPPER] Step 3: Creating internal user configuration...")
        user_config = create_user_config(options)
        
        if not user_config:
            logger.info(f"[CONFIG_MAPPER] ERROR: Failed to create user configuration")
            sys.exit(1)
        
        logger.info(f"[CONFIG_MAPPER] Generated configuration sections:")
        for section in user_config.keys():
            logger.info(f"[CONFIG_MAPPER]   - {section}")
        
        # Validate that we have essential configuration
        if "general" not in user_config:
            logger.info(f"[CONFIG_MAPPER] ERROR: Missing 'general' section in configuration")
            sys.exit(1)
        
        if "mqtt" not in user_config:
            logger.info(f"[CONFIG_MAPPER] ERROR: Missing 'mqtt' section in configuration")
            sys.exit(1)
        
        # Write user configuration
        logger.info(f"[CONFIG_MAPPER] Step 4: Writing configuration to file...")
        write_user_config(user_config)
        
        logger.info(f"[CONFIG_MAPPER] ========================================")
        logger.info(f"[CONFIG_MAPPER] Configuration mapping completed successfully!")
        logger.info(f"[CONFIG_MAPPER] ========================================")
        
    except KeyboardInterrupt:
        logger.info(f"[CONFIG_MAPPER] Configuration mapping interrupted by user")
        sys.exit(130)
    except SystemExit:
        # Re-raise SystemExit (from sys.exit calls)
        raise
    except Exception as e:
        logger.info(f"[CONFIG_MAPPER] ========================================")
        logger.info(f"[CONFIG_MAPPER] FATAL ERROR in configuration mapping:")
        logger.info(f"[CONFIG_MAPPER] {type(e).__name__}: {e}")
        logger.info(f"[CONFIG_MAPPER] ========================================")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()