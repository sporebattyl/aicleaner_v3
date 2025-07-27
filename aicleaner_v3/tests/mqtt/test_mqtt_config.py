"""
Test MQTT Configuration
Phase 4B: MQTT Discovery System Tests

Unit tests for MQTTConfig validation and helper methods.
"""

import pytest
from pydantic import ValidationError

from mqtt.config import MQTTConfig


class TestMQTTConfig:
    """Test MQTTConfig functionality"""
    
    def test_config_initialization_defaults(self):
        """Test config initialization with defaults"""
        config = MQTTConfig()
        
        assert config.enabled is True
        assert config.broker_host == "localhost"
        assert config.broker_port == 1883
        assert config.discovery_prefix == "homeassistant"
        assert config.device_id == "aicleaner_v3"
        assert config.qos_discovery == 1
        assert config.retain_discovery is True
    
    def test_config_initialization_custom(self):
        """Test config initialization with custom values"""
        config = MQTTConfig(
            broker_host="core-mosquitto",
            broker_port=1884,
            username="test_user",
            password="test_pass",
            device_id="test_device",
            qos_discovery=2
        )
        
        assert config.broker_host == "core-mosquitto"
        assert config.broker_port == 1884
        assert config.username == "test_user"
        assert config.password == "test_pass"
        assert config.device_id == "test_device"
        assert config.qos_discovery == 2
    
    def test_config_from_dict(self):
        """Test creating config from dictionary"""
        config_dict = {
            "broker_host": "test.broker.com",
            "broker_port": 8883,
            "use_tls": True,
            "device_name": "Test Device"
        }
        
        config = MQTTConfig(**config_dict)
        
        assert config.broker_host == "test.broker.com"
        assert config.broker_port == 8883
        assert config.use_tls is True
        assert config.device_name == "Test Device"
    
    # Validation Tests
    
    def test_validate_port_valid(self):
        """Test valid port values"""
        # Test various valid ports
        valid_ports = [1, 1883, 8883, 65535]
        
        for port in valid_ports:
            config = MQTTConfig(broker_port=port)
            assert config.broker_port == port
    
    def test_validate_port_invalid(self):
        """Test invalid port values"""
        invalid_ports = [0, -1, 65536, 100000]
        
        for port in invalid_ports:
            with pytest.raises(ValidationError) as exc_info:
                MQTTConfig(broker_port=port)
            assert "Port must be between 1 and 65535" in str(exc_info.value)
    
    def test_validate_qos_valid(self):
        """Test valid QoS values"""
        valid_qos = [0, 1, 2]
        
        for qos in valid_qos:
            config = MQTTConfig(
                qos_discovery=qos,
                qos_state=qos,
                qos_command=qos
            )
            assert config.qos_discovery == qos
            assert config.qos_state == qos
            assert config.qos_command == qos
    
    def test_validate_qos_invalid(self):
        """Test invalid QoS values"""
        invalid_qos = [-1, 3, 5]
        
        for qos in invalid_qos:
            with pytest.raises(ValidationError) as exc_info:
                MQTTConfig(qos_discovery=qos)
            assert "QoS must be 0, 1, or 2" in str(exc_info.value)
    
    def test_validate_positive_ints_valid(self):
        """Test valid positive integer values"""
        config = MQTTConfig(
            keepalive=120,
            reconnect_delay=10,
            max_reconnect_attempts=20
        )
        
        assert config.keepalive == 120
        assert config.reconnect_delay == 10
        assert config.max_reconnect_attempts == 20
    
    def test_validate_positive_ints_invalid(self):
        """Test invalid positive integer values"""
        invalid_values = [0, -1, -10]
        
        for value in invalid_values:
            with pytest.raises(ValidationError) as exc_info:
                MQTTConfig(keepalive=value)
            assert "Value must be positive" in str(exc_info.value)
    
    # Helper Method Tests
    
    def test_get_broker_url_no_auth(self):
        """Test broker URL generation without authentication"""
        config = MQTTConfig(
            broker_host="test.broker.com",
            broker_port=1883
        )
        
        expected_url = "mqtt://test.broker.com:1883"
        assert config.get_broker_url() == expected_url
    
    def test_get_broker_url_with_auth(self):
        """Test broker URL generation with authentication"""
        config = MQTTConfig(
            broker_host="test.broker.com",
            broker_port=1883,
            username="user",
            password="pass"
        )
        
        expected_url = "mqtt://user:pass@test.broker.com:1883"
        assert config.get_broker_url() == expected_url
    
    def test_get_broker_url_tls(self):
        """Test broker URL generation with TLS"""
        config = MQTTConfig(
            broker_host="secure.broker.com",
            broker_port=8883,
            use_tls=True,
            username="user",
            password="pass"
        )
        
        expected_url = "mqtts://user:pass@secure.broker.com:8883"
        assert config.get_broker_url() == expected_url
    
    def test_get_client_id_default(self):
        """Test default client ID generation"""
        config = MQTTConfig(device_id="test_device")
        
        expected_client_id = "test_device_client"
        assert config.get_client_id() == expected_client_id
    
    def test_get_client_id_custom(self):
        """Test custom client ID"""
        config = MQTTConfig(client_id="custom_client_123")
        
        assert config.get_client_id() == "custom_client_123"
    
    def test_get_discovery_topic(self):
        """Test discovery topic generation"""
        config = MQTTConfig(
            discovery_prefix="homeassistant",
            device_id="aicleaner_v3"
        )
        
        topic = config.get_discovery_topic("sensor", "zone_1_status")
        expected = "homeassistant/sensor/aicleaner_v3/zone_1_status/config"
        assert topic == expected
        
        # Test with custom config type
        topic = config.get_discovery_topic("switch", "zone_1_control", "state")
        expected = "homeassistant/switch/aicleaner_v3/zone_1_control/state"
        assert topic == expected
    
    def test_get_state_topic(self):
        """Test state topic generation"""
        config = MQTTConfig(device_id="test_device")
        
        topic = config.get_state_topic("zone_1_status")
        expected = "test_device/zone_1_status/state"
        assert topic == expected
    
    def test_get_command_topic(self):
        """Test command topic generation"""
        config = MQTTConfig(device_id="test_device")
        
        topic = config.get_command_topic("zone_1_control")
        expected = "test_device/zone_1_control/set"
        assert topic == expected
    
    def test_get_availability_topic(self):
        """Test availability topic generation"""
        config = MQTTConfig(device_id="test_device")
        
        topic = config.get_availability_topic()
        expected = "test_device/availability"
        assert topic == expected
    
    def test_to_connection_dict_no_auth(self):
        """Test connection dict generation without auth"""
        config = MQTTConfig(
            broker_host="test.broker.com",
            broker_port=1883,
            keepalive=60,
            clean_session=True
        )
        
        conn_dict = config.to_connection_dict()
        expected = {
            "host": "test.broker.com",
            "port": 1883,
            "keepalive": 60,
            "clean_session": True
        }
        
        assert conn_dict == expected
    
    def test_to_connection_dict_with_auth(self):
        """Test connection dict generation with auth"""
        config = MQTTConfig(
            broker_host="test.broker.com",
            broker_port=1883,
            username="user",
            password="pass",
            keepalive=120
        )
        
        conn_dict = config.to_connection_dict()
        expected = {
            "host": "test.broker.com",
            "port": 1883,
            "keepalive": 120,
            "clean_session": True,
            "username": "user",
            "password": "pass"
        }
        
        assert conn_dict == expected
    
    # Edge Cases and Error Handling
    
    def test_config_with_empty_strings(self):
        """Test config behavior with empty strings"""
        config = MQTTConfig(
            username="",
            password="",
            client_id=""
        )
        
        # Empty username/password should not be included in connection dict
        conn_dict = config.to_connection_dict()
        assert "username" not in conn_dict
        assert "password" not in conn_dict
        
        # Empty client_id should generate default
        assert config.get_client_id() == "aicleaner_v3_client"
    
    def test_config_validation_combinations(self):
        """Test various configuration combinations"""
        # TLS without certificates (should be valid)
        config = MQTTConfig(use_tls=True)
        assert config.use_tls is True
        
        # Will and authentication
        config = MQTTConfig(
            will_topic="aicleaner/status",
            will_payload="offline",
            username="user",
            password="pass"
        )
        assert config.will_topic == "aicleaner/status"
        assert config.will_payload == "offline"
    
    def test_config_extra_fields_ignored(self):
        """Test that extra fields are ignored"""
        config_dict = {
            "broker_host": "test.com",
            "unknown_field": "should_be_ignored",
            "another_unknown": 123
        }
        
        # Should not raise error due to extra="ignore"
        config = MQTTConfig(**config_dict)
        assert config.broker_host == "test.com"
        # Unknown fields should not be accessible
        assert not hasattr(config, "unknown_field")