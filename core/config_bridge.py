"""
AICleaner v3 Configuration Bridge
Handles conversion of Home Assistant Add-on options from /data/options.json
into the AICleaner v3 internal configuration format.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConfigBridge:
    """
    Handles the conversion of Home Assistant Add-on options from /data/options.json
    into the AICleaner v3 internal configuration format.
    """

    # Define a mapping from flat options.json keys to nested internal config paths
    # This mapping needs to be comprehensive based on expected options.json structure
    _OPTION_MAPPING = {
        # General settings
        "active_provider": {"path": ["general", "active_provider"], "type": str},
        "log_level": {"path": ["general", "log_level"], "type": str},

        # AI Provider API Keys (example for OpenAI, Gemini, Ollama)
        "api_key_openai": {"path": ["ai_providers", "openai", "api_key"], "type": str},
        "api_key_gemini": {"path": ["ai_providers", "gemini", "api_key"], "type": str},
        "ollama_base_url": {"path": ["ai_providers", "ollama", "base_url"], "type": str},
        "ollama_default_model": {"path": ["ai_providers", "ollama", "default_model"], "type": str},

        # MQTT Broker settings
        "mqtt_host": {"path": ["mqtt", "broker", "host"], "type": str},
        "mqtt_port": {"path": ["mqtt", "broker", "port"], "type": int},
        "mqtt_username": {"path": ["mqtt", "broker", "username"], "type": str},
        "mqtt_password": {"path": ["mqtt", "broker", "password"], "type": str},
        "mqtt_client_id": {"path": ["mqtt", "broker", "client_id"], "type": str},
        "mqtt_discovery_enabled": {"path": ["mqtt", "auto_discovery", "enabled"], "type": bool},
        "mqtt_discovery_prefix": {"path": ["mqtt", "auto_discovery", "topic_prefix"], "type": str},

        # Service API settings
        "api_port": {"path": ["service", "api", "port"], "type": int},
        "api_key_enabled": {"path": ["service", "api", "api_key_enabled"], "type": bool},
        "api_key": {"path": ["service", "api", "api_key"], "type": str},

        # Performance settings
        "cache_enabled": {"path": ["performance", "cache", "enabled"], "type": bool},
        "metrics_retention_days": {"path": ["performance", "metrics_retention_days"], "type": int},

        # Security settings (if exposed via options.json)
        "key_rotation_enabled": {"path": ["security", "key_rotation_enabled"], "type": bool},
        "default_rotation_days": {"path": ["security", "default_rotation_days"], "type": int},
    }

    def __init__(self, options_file_path: Path = Path("/data/options.json")):
        self.options_file_path = options_file_path
        logger.info(f"ConfigBridge initialized for options file: {self.options_file_path}")

    def load_addon_options(self) -> Dict[str, Any]:
        """
        Loads configuration from the add-on's options.json file and converts it
        to the internal nested configuration format.

        Returns:
            A dictionary representing the configuration derived from options.json,
            formatted to be merged with the main configuration.
        """
        options_data = {}
        try:
            if not self.options_file_path.exists():
                logger.info(f"Add-on options file not found at {self.options_file_path}. Skipping.")
                return {}

            with open(self.options_file_path, 'r') as f:
                options_data = json.load(f)
            logger.info(f"Successfully loaded add-on options from {self.options_file_path}")

        except FileNotFoundError:
            logger.warning(f"Add-on options file not found: {self.options_file_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.options_file_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error reading add-on options: {e}")
            return {}

        transformed_config = {}
        for key, value in options_data.items():
            mapping = self._OPTION_MAPPING.get(key)
            if not mapping:
                logger.debug(f"No mapping found for option key: {key}. Skipping.")
                continue

            path = mapping["path"]
            expected_type = mapping["type"]

            try:
                # Type conversion
                if expected_type == bool:
                    # Handle common string representations of booleans
                    if isinstance(value, str):
                        value = value.lower() in ('true', '1', 't', 'y', 'yes', 'on')
                    else:
                        value = bool(value)
                else:
                    value = expected_type(value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to convert option '{key}' value '{value}' to type {expected_type.__name__}: {e}. Skipping this option.")
                continue

            # Build nested dictionary
            current_level = transformed_config
            for i, p_key in enumerate(path):
                if i == len(path) - 1:
                    current_level[p_key] = value
                else:
                    if not isinstance(current_level.get(p_key), dict):
                        current_level[p_key] = {}
                    current_level = current_level[p_key]

        # Special handling for 'zones' array  
        if 'zones' in options_data:
            zones_list = options_data['zones']
            if isinstance(zones_list, list):
                # Ensure ai_cleaner.zones exists
                transformed_config.setdefault('ai_cleaner', {}).setdefault('zones', {})
                
                for zone_data in zones_list:
                    if isinstance(zone_data, dict):
                        zone_name = zone_data.get('name')
                        if zone_name:
                            try:
                                processed_zone = {
                                    'name': zone_name,
                                    'camera_entity': zone_data.get('camera_entity', ''),
                                    'todo_list_entity': zone_data.get('todo_list_entity', ''),
                                    'purpose': zone_data.get('purpose', ''),
                                    'interval_minutes': int(zone_data.get('interval_minutes', 0)),
                                    'specific_times': zone_data.get('specific_times', []),
                                    'random_offset_minutes': int(zone_data.get('random_offset_minutes', 0)),
                                    'ignore_rules': zone_data.get('ignore_rules', [])
                                }
                                if zone_name in transformed_config['ai_cleaner']['zones']:
                                    logger.warning(f"Duplicate zone name '{zone_name}' found in options.json. Overwriting existing zone.")
                                transformed_config['ai_cleaner']['zones'][zone_name] = processed_zone
                                logger.debug(f"Processed zone '{zone_name}' from options.json")
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Failed to process zone '{zone_name}': {e}. Skipping this zone.")
                        else:
                            logger.warning(f"Zone missing 'name' field in options.json: {zone_data}. Skipping.")
                logger.info(f"Processed {len(transformed_config.get('ai_cleaner', {}).get('zones', {}))} zones from options.json")
            else:
                logger.warning(f"Expected 'zones' to be a list but got {type(zones_list)}. Skipping zones processing.")

        logger.debug(f"Transformed config from options.json: {transformed_config}")
        return transformed_config