import os
from logging import getLogger
from typing import Optional, Dict, Any

logger = getLogger(__name__)

class MQTTConfig:
    """Configuration for MQTT discovery integrated with unified configuration system."""
    
    def __init__(self, config_manager=None, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize MQTT configuration.
        
        Args:
            config_manager: Unified configuration manager instance
            config_dict: Direct configuration dictionary (for testing)
        """
        if config_dict:
            # Direct configuration provided (testing/override)
            mqtt_config = config_dict
        elif config_manager:
            # Use unified configuration manager
            full_config = config_manager.load_configuration()
            mqtt_config = full_config.get('mqtt', {})
        else:
            # Fallback to environment variables (deprecated)
            logger.warning("MQTT Config: Using deprecated environment variable fallback. Consider using unified configuration.")
            mqtt_config = {
                'broker_address': os.getenv("MQTT_BROKER_ADDRESS", "localhost"),
                'broker_port': int(os.getenv("MQTT_BROKER_PORT", "1883")),
                'username': os.getenv("MQTT_USERNAME"),
                'password': os.getenv("MQTT_PASSWORD"),
                'discovery_prefix': os.getenv("MQTT_DISCOVERY_PREFIX", "homeassistant"),
                'qos': int(os.getenv("MQTT_QOS", "1")),
                'use_tls': os.getenv("MQTT_USE_TLS", "false").lower() == "true",
                'tls_ca_cert': os.getenv("MQTT_TLS_CA_CERT"),
                'tls_cert_file': os.getenv("MQTT_TLS_CERT_FILE"),
                'tls_key_file': os.getenv("MQTT_TLS_KEY_FILE"),
                'tls_insecure': os.getenv("MQTT_TLS_INSECURE", "false").lower() == "true"
            }
        
        # Set configuration values
        self.BROKER_ADDRESS: str = mqtt_config.get('broker_address', 'localhost')
        self.BROKER_PORT: int = mqtt_config.get('broker_port', 1883)
        self.USERNAME: Optional[str] = mqtt_config.get('username')
        self.PASSWORD: Optional[str] = mqtt_config.get('password')
        self.DISCOVERY_PREFIX: str = mqtt_config.get('discovery_prefix', 'homeassistant')
        self.QOS: int = mqtt_config.get('qos', 1)
        self.USE_TLS: bool = mqtt_config.get('use_tls', False)
        self.TLS_CA_CERT: Optional[str] = mqtt_config.get('tls_ca_cert')
        self.TLS_CERT_FILE: Optional[str] = mqtt_config.get('tls_cert_file')
        self.TLS_KEY_FILE: Optional[str] = mqtt_config.get('tls_key_file')
        self.TLS_INSECURE: bool = mqtt_config.get('tls_insecure', False)
        
        logger.info(f"MQTT Config initialized: broker={self.BROKER_ADDRESS}:{self.BROKER_PORT}, tls={self.USE_TLS}")
    
    @classmethod
    def from_environment(cls) -> 'MQTTConfig':
        """
        Create MQTTConfig from environment variables (deprecated).
        
        Returns:
            MQTTConfig instance
        """
        logger.warning("MQTTConfig.from_environment() is deprecated. Use unified configuration manager.")
        return cls()
    
    def validate(self) -> bool:
        """
        Validate MQTT configuration.
        
        Returns:
            True if configuration is valid
        """
        if not self.BROKER_ADDRESS:
            logger.error("MQTT broker address is required")
            return False
        
        if not (1 <= self.BROKER_PORT <= 65535):
            logger.error(f"MQTT broker port {self.BROKER_PORT} is invalid")
            return False
        
        if self.QOS not in [0, 1, 2]:
            logger.error(f"MQTT QoS {self.QOS} is invalid")
            return False
        
        if not self.DISCOVERY_PREFIX:
            logger.error("MQTT discovery prefix is required")
            return False
        
        # Validate TLS configuration
        if self.USE_TLS:
            if self.TLS_CA_CERT and not os.path.exists(self.TLS_CA_CERT):
                logger.error(f"MQTT TLS CA certificate file not found: {self.TLS_CA_CERT}")
                return False
            
            if self.TLS_CERT_FILE and not os.path.exists(self.TLS_CERT_FILE):
                logger.error(f"MQTT TLS certificate file not found: {self.TLS_CERT_FILE}")
                return False
            
            if self.TLS_KEY_FILE and not os.path.exists(self.TLS_KEY_FILE):
                logger.error(f"MQTT TLS key file not found: {self.TLS_KEY_FILE}")
                return False
        
        return True

    def log_config(self):
        """Log current MQTT configuration (hiding sensitive data)."""
        logger.info("MQTT Configuration loaded:")
        logger.info(f"  Broker Address: {self.BROKER_ADDRESS}")
        logger.info(f"  Broker Port: {self.BROKER_PORT}")
        logger.info(f"  Username: {'set' if self.USERNAME else 'not set'}")
        logger.info(f"  Password: {'set' if self.PASSWORD else 'not set'}")
        logger.info(f"  Discovery Prefix: {self.DISCOVERY_PREFIX}")
        logger.info(f"  QoS: {self.QOS}")
        logger.info(f"  TLS Enabled: {self.USE_TLS}")
        if self.USE_TLS:
            logger.info(f"  TLS CA Cert: {'set' if self.TLS_CA_CERT else 'not set'}")
            logger.info(f"  TLS Cert File: {'set' if self.TLS_CERT_FILE else 'not set'}")
            logger.info(f"  TLS Key File: {'set' if self.TLS_KEY_FILE else 'not set'}")
            logger.info(f"  TLS Insecure: {self.TLS_INSECURE}")