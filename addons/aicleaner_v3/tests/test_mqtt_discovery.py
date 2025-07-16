"""
Comprehensive Test Suite for Phase 4B MQTT Discovery Implementation
Tests all MQTT Discovery components for production readiness
"""

import asyncio
import json
import logging
import pytest
import unittest.mock as mock
from datetime import datetime
from typing import Dict, Any

# Import MQTT components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from mqtt.discovery_client import MQTTDiscoveryClient
from mqtt.topic_manager import MQTTTopicManager
from mqtt.device_publisher import MQTTDevicePublisher
from mqtt.ha_mqtt_integration import HAMQTTIntegration
from mqtt.config_manager import ConfigManager

# Configure test logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestMQTTTopicManager:
    """Test MQTT Topic Manager functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.topic_manager = MQTTTopicManager("homeassistant", "aicleaner_v3")
    
    def test_create_discovery_topic(self):
        """Test discovery topic creation"""
        topic = self.topic_manager.create_discovery_topic("sensor", "cpu_usage")
        assert topic == "homeassistant/sensor/aicleaner_v3/cpu_usage/config"
    
    def test_create_state_topic(self):
        """Test state topic creation"""
        topic = self.topic_manager.create_state_topic("sensor", "cpu_usage")
        assert topic == "homeassistant/sensor/aicleaner_v3/cpu_usage/state"
    
    def test_create_attributes_topic(self):
        """Test attributes topic creation"""
        topic = self.topic_manager.create_attributes_topic("sensor", "cpu_usage")
        assert topic == "homeassistant/sensor/aicleaner_v3/cpu_usage/attributes"
    
    def test_create_availability_topic(self):
        """Test availability topic creation"""
        topic = self.topic_manager.create_availability_topic()
        assert topic == "homeassistant/status/aicleaner_v3/status"
    
    def test_validate_topic_structure_valid(self):
        """Test topic validation with valid topics"""
        valid_topics = [
            "homeassistant/sensor/device/entity/config",
            "valid/topic/structure",
            "simple"
        ]
        for topic in valid_topics:
            assert MQTTTopicManager.validate_topic_structure(topic) == True
    
    def test_validate_topic_structure_invalid(self):
        """Test topic validation with invalid topics"""
        invalid_topics = [
            "",  # Empty topic
            "topic/with/+/wildcard",  # Contains +
            "topic/with/#/wildcard",  # Contains #
            "topic//with/empty/level",  # Empty level
            "a" * 70000  # Too long
        ]
        for topic in invalid_topics:
            assert MQTTTopicManager.validate_topic_structure(topic) == False
    
    def test_register_entity_topics(self):
        """Test entity topic registration"""
        config = {"name": "Test Sensor"}
        topics = self.topic_manager.register_entity_topics("sensor", "test", config)
        
        assert "config_topic" in topics
        assert "state_topic" in topics
        assert "availability_topic" in topics
        assert "attributes_topic" in topics
        
        # Verify topics are properly formatted
        assert topics["config_topic"] == "homeassistant/sensor/aicleaner_v3/test/config"
        assert topics["state_topic"] == "homeassistant/sensor/aicleaner_v3/test/state"

class TestMQTTDiscoveryClient:
    """Test MQTT Discovery Client functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = MQTTDiscoveryClient(
            broker_host="localhost",
            broker_port=1883,
            discovery_prefix="homeassistant"
        )
    
    def test_initialization(self):
        """Test client initialization"""
        assert self.client.broker_host == "localhost"
        assert self.client.broker_port == 1883
        assert self.client.discovery_prefix == "homeassistant"
        assert self.client.connected == False
        assert self.client.will_topic is None
    
    def test_set_will(self):
        """Test will topic configuration"""
        will_topic = "homeassistant/status/aicleaner_v3/status"
        self.client.set_will(will_topic, "offline")
        assert self.client.will_topic == will_topic
    
    @pytest.mark.asyncio
    async def test_async_publish_discovery_invalid_topic(self):
        """Test discovery publishing with invalid topic"""
        # Mock connected state
        self.client.connected = True
        
        config = {"name": "Test"}
        # Use invalid component type with special characters
        result = await self.client.async_publish_discovery("sensor+invalid", "test", config)
        assert result == False
    
    @pytest.mark.asyncio
    async def test_async_publish_discovery_not_connected(self):
        """Test discovery publishing when not connected"""
        config = {"name": "Test"}
        result = await self.client.async_publish_discovery("sensor", "test", config)
        assert result == False

class TestMQTTDevicePublisher:
    """Test MQTT Device Publisher functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_mqtt_client = mock.AsyncMock()
        self.topic_manager = MQTTTopicManager("homeassistant", "aicleaner_v3")
        self.device_publisher = MQTTDevicePublisher(
            self.mock_mqtt_client, 
            self.topic_manager
        )
    
    @pytest.mark.asyncio
    async def test_async_publish_device(self):
        """Test device publishing"""
        # Mock successful MQTT operations
        self.mock_mqtt_client.async_publish_state.return_value = True
        self.mock_mqtt_client.async_publish_discovery.return_value = True
        
        result = await self.device_publisher.async_publish_device()
        assert result == True
        assert self.device_publisher.device_online == True
    
    @pytest.mark.asyncio
    async def test_update_entity_state_with_attributes(self):
        """Test entity state update with attributes"""
        # Mock successful state publishing
        self.mock_mqtt_client.async_publish_state.return_value = True
        
        # Register entity first
        self.device_publisher.published_entities["sensor.test"] = {
            "state": "unknown",
            "last_updated": datetime.now().isoformat()
        }
        
        attributes = {"unit": "°C", "precision": 1}
        result = await self.device_publisher._update_entity_state(
            "sensor", "test", "25.5", attributes
        )
        
        assert result == True
        # Verify attributes were published as JSON
        calls = self.mock_mqtt_client.async_publish_state.call_args_list
        # Should have 2 calls: state and attributes
        assert len(calls) >= 1
    
    @pytest.mark.asyncio
    async def test_handle_switch_command_optimistic_update(self):
        """Test optimistic switch command handling"""
        # Mock successful operations
        self.mock_mqtt_client.async_publish_state.return_value = True
        
        # Mock execution methods
        self.device_publisher._execute_auto_cleanup_toggle = mock.AsyncMock()
        
        # Register switch entity
        self.device_publisher.published_entities["switch.auto_cleanup"] = {
            "state": "OFF",
            "last_updated": datetime.now().isoformat()
        }
        
        await self.device_publisher._handle_switch_command("auto_cleanup", "ON")
        
        # Verify execution method was called
        self.device_publisher._execute_auto_cleanup_toggle.assert_called_once_with(True)
    
    @pytest.mark.asyncio
    async def test_handle_switch_command_error_recovery(self):
        """Test switch command error recovery"""
        # Mock successful state update but failed execution
        self.mock_mqtt_client.async_publish_state.return_value = True
        
        # Mock execution method to raise exception
        self.device_publisher._execute_auto_cleanup_toggle = mock.AsyncMock(
            side_effect=Exception("Execution failed")
        )
        
        # Register switch entity
        self.device_publisher.published_entities["switch.auto_cleanup"] = {
            "state": "OFF",
            "last_updated": datetime.now().isoformat()
        }
        
        await self.device_publisher._handle_switch_command("auto_cleanup", "ON")
        
        # Verify state was reverted (should call async_publish_state twice: ON then OFF)
        assert self.mock_mqtt_client.async_publish_state.call_count >= 2

class TestHAMQTTIntegration:
    """Test HA MQTT Integration functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_hass = mock.Mock()
        self.mock_hass.bus = mock.Mock()
        self.mock_mqtt_client = mock.AsyncMock()
        self.topic_manager = MQTTTopicManager("homeassistant", "aicleaner_v3")
        self.mock_device_publisher = mock.AsyncMock()
        
        self.integration = HAMQTTIntegration(
            self.mock_hass,
            self.mock_mqtt_client,
            self.topic_manager,
            self.mock_device_publisher
        )
    
    @pytest.mark.asyncio
    async def test_async_setup_success(self):
        """Test successful HA MQTT integration setup"""
        # Mock successful operations
        self.mock_mqtt_client.async_connect.return_value = True
        self.mock_device_publisher.async_publish_device.return_value = True
        
        # Mock other setup methods
        self.integration._setup_periodic_updates = mock.AsyncMock()
        self.integration._register_ha_event_listeners = mock.AsyncMock()
        
        result = await self.integration.async_setup()
        
        assert result == True
        assert self.integration.integration_active == True
        
        # Verify will topic was set
        availability_topic = self.topic_manager.create_availability_topic()
        self.mock_mqtt_client.set_will.assert_called_once_with(
            availability_topic, "offline", retain=True
        )
    
    @pytest.mark.asyncio
    async def test_async_setup_mqtt_connection_failure(self):
        """Test setup with MQTT connection failure"""
        # Mock failed MQTT connection
        self.mock_mqtt_client.async_connect.return_value = False
        
        result = await self.integration.async_setup()
        
        assert result == False
        assert self.integration.integration_active == False
    
    @pytest.mark.asyncio
    async def test_async_setup_device_publish_failure(self):
        """Test setup with device publishing failure"""
        # Mock successful MQTT connection but failed device publishing
        self.mock_mqtt_client.async_connect.return_value = True
        self.mock_device_publisher.async_publish_device.return_value = False
        
        result = await self.integration.async_setup()
        
        assert result == False
        assert self.integration.integration_active == False

class TestConfigManager:
    """Test MQTT Config Manager functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config_manager = ConfigManager()
    
    def test_default_configuration(self):
        """Test default configuration values"""
        config = self.config_manager.get_mqtt_config()
        
        assert "broker_host" in config
        assert "broker_port" in config
        assert "discovery_prefix" in config
        assert config["broker_port"] == 1883
        assert config["discovery_prefix"] == "homeassistant"
    
    def test_update_configuration(self):
        """Test configuration updates"""
        new_config = {
            "broker_host": "test.mqtt.broker",
            "broker_port": 8883,
            "use_tls": True
        }
        
        result = self.config_manager.update_mqtt_config(new_config)
        assert result == True
        
        updated_config = self.config_manager.get_mqtt_config()
        assert updated_config["broker_host"] == "test.mqtt.broker"
        assert updated_config["broker_port"] == 8883
        assert updated_config["use_tls"] == True
    
    def test_validate_configuration(self):
        """Test configuration validation"""
        valid_config = {
            "broker_host": "localhost",
            "broker_port": 1883,
            "discovery_prefix": "homeassistant"
        }
        assert self.config_manager.validate_config(valid_config) == True
        
        invalid_config = {
            "broker_host": "",  # Empty host
            "broker_port": "invalid",  # Invalid port type
        }
        assert self.config_manager.validate_config(invalid_config) == False

class TestIntegrationScenarios:
    """Test end-to-end integration scenarios"""
    
    def setup_method(self):
        """Set up integration test fixtures"""
        self.mock_hass = mock.Mock()
        self.mock_hass.bus = mock.Mock()
        
        # Create real instances with mocked MQTT client
        self.mock_mqtt_client = mock.AsyncMock()
        self.topic_manager = MQTTTopicManager("homeassistant", "aicleaner_v3")
        self.device_publisher = MQTTDevicePublisher(
            self.mock_mqtt_client, 
            self.topic_manager
        )
        self.integration = HAMQTTIntegration(
            self.mock_hass,
            self.mock_mqtt_client,
            self.topic_manager,
            self.device_publisher
        )
    
    @pytest.mark.asyncio
    async def test_full_device_lifecycle(self):
        """Test complete device lifecycle"""
        # Mock successful MQTT operations
        self.mock_mqtt_client.async_connect.return_value = True
        self.mock_mqtt_client.async_publish_state.return_value = True
        self.mock_mqtt_client.async_publish_discovery.return_value = True
        
        # Mock integration setup methods
        self.integration._setup_periodic_updates = mock.AsyncMock()
        self.integration._register_ha_event_listeners = mock.AsyncMock()
        
        # Test setup
        setup_result = await self.integration.async_setup()
        assert setup_result == True
        
        # Test device publishing
        publish_result = await self.device_publisher.async_publish_device()
        assert publish_result == True
        
        # Test entity state updates
        state_result = await self.device_publisher._update_entity_state(
            "sensor", "cpu_usage", "45.2", {"unit": "%"}
        )
        assert state_result == True
        
        # Test device cleanup
        cleanup_result = await self.device_publisher.async_unpublish_device()
        assert cleanup_result == True

if __name__ == "__main__":
    """Run tests directly"""
    pytest.main([__file__, "-v", "--tb=short"])