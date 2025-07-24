"""
MQTT Configuration Manager
Manages MQTT broker configuration and connection settings
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class MQTTConfigManager:
    """
    Manages MQTT broker configuration and connection settings
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize MQTT Config Manager"""
        self.config_file = Path(config_file) if config_file else None
        self.config = self._load_default_config()
        
        if self.config_file and self.config_file.exists():
            self._load_config()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default MQTT configuration"""
        return {
            "broker": {
                "host": "localhost",
                "port": 1883,
                "username": None,
                "password": None,
                "use_tls": False,
                "tls_ca_cert": None,
                "tls_cert_file": None,
                "tls_key_file": None,
                "keepalive": 60,
                "client_id": "aicleaner_v3"
            },
            "discovery": {
                "prefix": "homeassistant",
                "enabled": True,
                "retain_config": True,
                "retain_state": False
            },
            "topics": {
                "base": "aicleaner_v3",
                "availability": "aicleaner_v3/status",
                "state_suffix": "state",
                "command_suffix": "cmd",
                "attributes_suffix": "attr"
            },
            "qos": {
                "default": 1,
                "discovery": 1,
                "state": 1,
                "command": 1
            },
            "advanced": {
                "max_reconnect_attempts": 10,
                "reconnect_delay": 5,
                "message_timeout": 30,
                "publish_batch_size": 10
            }
        }
    
    def _load_config(self):
        """Load configuration from file"""
        try:
            if self.config_file and self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                
                # Merge with defaults (deep merge)
                self._deep_merge(self.config, file_config)
                logger.info(f"Loaded MQTT config from {self.config_file}")
            
        except Exception as e:
            logger.error(f"Error loading MQTT config: {e}")
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]):
        """Deep merge configuration dictionaries"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def save_config(self) -> bool:
        """Save current configuration to file"""
        try:
            if not self.config_file:
                logger.error("No config file specified")
                return False
            
            # Ensure parent directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            logger.info(f"Saved MQTT config to {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving MQTT config: {e}")
            return False
    
    def get_broker_config(self) -> Dict[str, Any]:
        """Get broker connection configuration"""
        return self.config.get("broker", {})
    
    def get_discovery_config(self) -> Dict[str, Any]:
        """Get discovery configuration"""
        return self.config.get("discovery", {})
    
    def get_topic_config(self) -> Dict[str, Any]:
        """Get topic configuration"""
        return self.config.get("topics", {})
    
    def get_qos_config(self) -> Dict[str, Any]:
        """Get QoS configuration"""
        return self.config.get("qos", {})
    
    def get_advanced_config(self) -> Dict[str, Any]:
        """Get advanced configuration"""
        return self.config.get("advanced", {})
    
    def update_broker_settings(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: Optional[bool] = None
    ) -> bool:
        """Update broker connection settings"""
        try:
            broker_config = self.config.setdefault("broker", {})
            
            if host is not None:
                broker_config["host"] = host
            if port is not None:
                broker_config["port"] = port
            if username is not None:
                broker_config["username"] = username
            if password is not None:
                broker_config["password"] = password
            if use_tls is not None:
                broker_config["use_tls"] = use_tls
            
            logger.info("Updated MQTT broker settings")
            return True
            
        except Exception as e:
            logger.error(f"Error updating broker settings: {e}")
            return False
    
    def update_discovery_settings(
        self,
        prefix: Optional[str] = None,
        enabled: Optional[bool] = None,
        retain_config: Optional[bool] = None,
        retain_state: Optional[bool] = None
    ) -> bool:
        """Update discovery settings"""
        try:
            discovery_config = self.config.setdefault("discovery", {})
            
            if prefix is not None:
                discovery_config["prefix"] = prefix
            if enabled is not None:
                discovery_config["enabled"] = enabled
            if retain_config is not None:
                discovery_config["retain_config"] = retain_config
            if retain_state is not None:
                discovery_config["retain_state"] = retain_state
            
            logger.info("Updated MQTT discovery settings")
            return True
            
        except Exception as e:
            logger.error(f"Error updating discovery settings: {e}")
            return False
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate current configuration"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Validate broker settings
            broker = self.config.get("broker", {})
            
            if not broker.get("host"):
                validation_result["errors"].append("Broker host is required")
                validation_result["valid"] = False
            
            port = broker.get("port", 1883)
            if not isinstance(port, int) or port <= 0 or port > 65535:
                validation_result["errors"].append("Invalid broker port")
                validation_result["valid"] = False
            
            # Validate discovery settings
            discovery = self.config.get("discovery", {})
            prefix = discovery.get("prefix", "")
            if not prefix or not isinstance(prefix, str):
                validation_result["errors"].append("Discovery prefix is required")
                validation_result["valid"] = False
            
            # Validate QoS settings
            qos = self.config.get("qos", {})
            for qos_key, qos_value in qos.items():
                if not isinstance(qos_value, int) or qos_value < 0 or qos_value > 2:
                    validation_result["errors"].append(f"Invalid QoS value for {qos_key}")
                    validation_result["valid"] = False
            
            # Check for TLS configuration consistency
            if broker.get("use_tls") and not any([
                broker.get("tls_ca_cert"),
                broker.get("tls_cert_file"),
                broker.get("tls_key_file")
            ]):
                validation_result["warnings"].append("TLS enabled but no certificates configured")
            
            # Check authentication
            username = broker.get("username")
            password = broker.get("password")
            if (username and not password) or (password and not username):
                validation_result["warnings"].append("Username and password should both be set for authentication")
            
        except Exception as e:
            validation_result["errors"].append(f"Configuration validation error: {e}")
            validation_result["valid"] = False
        
        return validation_result
    
    def get_connection_url(self) -> str:
        """Get MQTT connection URL"""
        broker = self.config.get("broker", {})
        protocol = "mqtts" if broker.get("use_tls") else "mqtt"
        host = broker.get("host", "localhost")
        port = broker.get("port", 1883)
        
        return f"{protocol}://{host}:{port}"
    
    def export_config(self) -> Dict[str, Any]:
        """Export configuration (excluding sensitive data)"""
        export_config = json.loads(json.dumps(self.config))  # Deep copy
        
        # Remove sensitive information
        broker = export_config.get("broker", {})
        if "password" in broker:
            broker["password"] = "***REDACTED***"
        
        return export_config
    
    def get_full_config(self) -> Dict[str, Any]:
        """Get full configuration"""
        return self.config.copy()
    
    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        self.config = self._load_default_config()
        logger.info("Reset MQTT configuration to defaults")
    
    def create_test_config(self) -> Dict[str, Any]:
        """Create configuration for testing"""
        test_config = self._load_default_config()
        test_config["broker"]["host"] = "test.mosquitto.org"
        test_config["broker"]["port"] = 1883
        test_config["discovery"]["prefix"] = "homeassistant_test"
        test_config["topics"]["base"] = "aicleaner_v3_test"
        
        return test_config
