"""
Test MQTT Adapter Mock Mode
Phase 4B: MQTT Discovery System Tests

Unit tests for MQTTAdapter in mock mode.
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock

from mqtt.adapter import MQTTAdapter, DeviceInfo
from mqtt.config import MQTTConfig


class TestMQTTAdapterMock:
    """Test MQTTAdapter in mock mode"""
    
    @pytest.fixture
    def mqtt_config(self):
        """Create test MQTT configuration"""
        return MQTTConfig(
            broker_host="test.broker.com",
            device_id="test_device",
            device_name="Test Device"
        )
    
    @pytest.fixture
    def mock_adapter(self, mqtt_config):
        """Create MQTTAdapter in mock mode"""
        return MQTTAdapter(mqtt_config, mock_mode=True)
    
    def test_adapter_initialization_mock_mode(self, mock_adapter):
        """Test adapter initializes correctly in mock mode"""
        assert mock_adapter.mock_mode is True
        assert mock_adapter._connected is False
        assert mock_adapter._running is False
        assert len(mock_adapter._discovered_entities) == 0
        assert len(mock_adapter._mock_published_messages) == 0
        assert len(mock_adapter._mock_subscriptions) == 0
        assert mock_adapter._client is None  # No real MQTT client in mock mode
    
    @pytest.mark.asyncio
    async def test_start_stop_mock_mode(self, mock_adapter):
        """Test starting and stopping adapter in mock mode"""
        # Test start
        success = await mock_adapter.start()
        assert success is True
        assert mock_adapter._connected is True
        assert mock_adapter._running is True
        
        # Test stop
        success = await mock_adapter.stop()
        assert success is True
        assert mock_adapter._connected is False
        assert mock_adapter._running is False
    
    @pytest.mark.asyncio
    async def test_publish_discovery_message_mock(self, mock_adapter):
        """Test publishing discovery message in mock mode"""
        await mock_adapter.start()
        
        device_info = DeviceInfo(
            entity_id="test_sensor",
            name="Test Sensor",
            device_class="temperature",
            unit_of_measurement="°C"
        )
        
        success = await mock_adapter.publish_discovery_message(device_info, "sensor")
        assert success is True
        
        # Check discovery message was recorded
        messages = mock_adapter.get_mock_published_messages()
        assert len(messages) == 1
        
        message = messages[0]
        assert message["topic"] == "homeassistant/sensor/test_device/test_sensor/config"
        assert message["qos"] == 1
        assert message["retain"] is True
        
        # Parse and validate discovery payload
        config = json.loads(message["payload"])
        assert config["unique_id"] == "test_device_test_sensor"
        assert config["name"] == "Test Sensor"
        assert config["device_class"] == "temperature"
        assert config["unit_of_measurement"] == "°C"
        assert config["state_topic"] == "test_device/test_sensor/state"
        assert config["availability_topic"] == "test_device/availability"
        assert "device" in config
        assert config["device"]["identifiers"] == ["test_device"]
        assert config["device"]["name"] == "Test Device"
    
    @pytest.mark.asyncio
    async def test_publish_discovery_different_components(self, mock_adapter):
        """Test discovery messages for different component types"""
        await mock_adapter.start()
        
        # Test sensor
        sensor_device = DeviceInfo(
            entity_id="temp_sensor",
            name="Temperature Sensor",
            device_class="temperature"
        )
        
        await mock_adapter.publish_discovery_message(sensor_device, "sensor")
        
        # Test binary sensor
        binary_device = DeviceInfo(
            entity_id="motion_sensor",
            name="Motion Sensor",
            device_class="motion"
        )
        
        await mock_adapter.publish_discovery_message(binary_device, "binary_sensor")
        
        # Test switch
        switch_device = DeviceInfo(
            entity_id="test_switch",
            name="Test Switch"
        )
        
        await mock_adapter.publish_discovery_message(switch_device, "switch")
        
        messages = mock_adapter.get_mock_published_messages()
        assert len(messages) == 3
        
        # Check sensor config
        sensor_config = json.loads(messages[0]["payload"])
        assert sensor_config["value_template"] == "{{ value_json.state }}"
        assert "command_topic" not in sensor_config
        
        # Check binary sensor config
        binary_config = json.loads(messages[1]["payload"])
        assert binary_config["value_template"] == "{{ value_json.state }}"
        assert binary_config["payload_on"] == "ON"
        assert binary_config["payload_off"] == "OFF"
        
        # Check switch config
        switch_config = json.loads(messages[2]["payload"])
        assert switch_config["command_topic"] == "test_device/test_switch/set"
        assert switch_config["payload_on"] == "ON"
        assert switch_config["payload_off"] == "OFF"
    
    @pytest.mark.asyncio
    async def test_publish_state_mock(self, mock_adapter):
        """Test publishing state in mock mode"""
        await mock_adapter.start()
        
        # Publish state without attributes
        success = await mock_adapter.publish_state("test_entity", "active")
        assert success is True
        
        # Publish state with attributes
        attributes = {"temperature": 25.5, "unit": "°C"}
        success = await mock_adapter.publish_state("temp_sensor", 25.5, attributes)
        assert success is True
        
        messages = mock_adapter.get_mock_published_messages()
        assert len(messages) == 2
        
        # Check first message
        message1 = messages[0]
        assert message1["topic"] == "test_device/test_entity/state"
        payload1 = json.loads(message1["payload"])
        assert payload1["state"] == "active"
        assert "timestamp" in payload1
        assert "attributes" not in payload1
        
        # Check second message
        message2 = messages[1]
        assert message2["topic"] == "test_device/temp_sensor/state"
        payload2 = json.loads(message2["payload"])
        assert payload2["state"] == 25.5
        assert payload2["attributes"] == attributes
        assert "timestamp" in payload2
    
    @pytest.mark.asyncio
    async def test_subscribe_to_commands_mock(self, mock_adapter):
        """Test subscribing to commands in mock mode"""
        await mock_adapter.start()
        
        # Mock callback function
        callback_calls = []
        
        def test_callback(topic, payload):
            callback_calls.append((topic, payload))
        
        # Subscribe to commands
        success = await mock_adapter.subscribe_to_commands("test_switch", test_callback)
        assert success is True
        
        # Check subscription was recorded
        subscriptions = mock_adapter.get_mock_subscriptions()
        assert len(subscriptions) == 1
        assert subscriptions[0] == "test_device/test_switch/set"
        
        # Check callback was stored
        expected_topic = "test_device/test_switch/set"
        assert expected_topic in mock_adapter._command_callbacks
        assert mock_adapter._command_callbacks[expected_topic] == test_callback
    
    @pytest.mark.asyncio
    async def test_unsubscribe_from_commands_mock(self, mock_adapter):
        """Test unsubscribing from commands in mock mode"""
        await mock_adapter.start()
        
        # Subscribe first
        def test_callback(topic, payload):
            pass
        
        await mock_adapter.subscribe_to_commands("test_switch", test_callback)
        assert len(mock_adapter.get_mock_subscriptions()) == 1
        
        # Unsubscribe
        success = await mock_adapter.unsubscribe_from_commands("test_switch")
        assert success is True
        
        # Check subscription was removed
        subscriptions = mock_adapter.get_mock_subscriptions()
        assert len(subscriptions) == 0
        
        # Check callback was removed
        expected_topic = "test_device/test_switch/set"
        assert expected_topic not in mock_adapter._command_callbacks
    
    def test_status_and_metrics_mock(self, mock_adapter):
        """Test status and metrics in mock mode"""
        status = mock_adapter.get_status()
        
        assert status["connected"] is False  # Not started yet
        assert status["running"] is False
        assert status["mock_mode"] is True
        assert status["connection_attempts"] == 0
        assert status["discovered_entities"] == 0
        assert status["active_subscriptions"] == 0
        assert status["messages_published"] == 0
        assert status["messages_received"] == 0
    
    @pytest.mark.asyncio
    async def test_status_after_operations(self, mock_adapter):
        """Test status after performing operations"""
        await mock_adapter.start()
        
        # Publish discovery and state
        device_info = DeviceInfo(entity_id="test", name="Test")
        await mock_adapter.publish_discovery_message(device_info, "sensor")
        await mock_adapter.publish_state("test", "active")
        
        # Subscribe to commands
        def callback(topic, payload):
            pass
        await mock_adapter.subscribe_to_commands("test", callback)
        
        status = mock_adapter.get_status()
        
        assert status["connected"] is True
        assert status["running"] is True
        assert status["discovered_entities"] == 1
        assert status["active_subscriptions"] == 1
        assert status["messages_published"] == 2  # discovery + state
    
    def test_clear_mock_data(self, mock_adapter):
        """Test clearing mock data"""
        # Add some mock data
        mock_adapter._mock_published_messages.append({"test": "message"})
        mock_adapter._mock_subscriptions.append("test/topic")
        
        assert len(mock_adapter.get_mock_published_messages()) == 1
        assert len(mock_adapter.get_mock_subscriptions()) == 1
        
        # Clear data
        mock_adapter.clear_mock_data()
        
        assert len(mock_adapter.get_mock_published_messages()) == 0
        assert len(mock_adapter.get_mock_subscriptions()) == 0
    
    def test_connection_status_methods(self, mock_adapter):
        """Test connection status methods"""
        # Initially not connected
        assert mock_adapter.is_connected() is False
        assert mock_adapter.is_running() is False
        
        # After start (mock mode always succeeds)
        asyncio.run(mock_adapter.start())
        assert mock_adapter.is_connected() is True
        assert mock_adapter.is_running() is True
        
        # After stop
        asyncio.run(mock_adapter.stop())
        assert mock_adapter.is_connected() is False
        assert mock_adapter.is_running() is False
    
    @pytest.mark.asyncio
    async def test_discovery_config_building(self, mock_adapter):
        """Test internal discovery config building"""
        await mock_adapter.start()
        
        # Test device with all optional fields
        device_info = DeviceInfo(
            entity_id="advanced_sensor",
            name="Advanced Sensor",
            device_class="temperature",
            state_class="measurement",
            unit_of_measurement="°C",
            icon="mdi:thermometer",
            entity_category="diagnostic"
        )
        
        await mock_adapter.publish_discovery_message(device_info, "sensor")
        
        messages = mock_adapter.get_mock_published_messages()
        config = json.loads(messages[0]["payload"])
        
        # Check all fields are included
        assert config["device_class"] == "temperature"
        assert config["state_class"] == "measurement"
        assert config["unit_of_measurement"] == "°C"
        assert config["icon"] == "mdi:thermometer"
        assert config["entity_category"] == "diagnostic"
        
        # Check device info
        device = config["device"]
        assert device["manufacturer"] == "AICleaner"
        assert device["model"] == "AICleaner v3"
        assert device["sw_version"] == "3.0.0"
    
    @pytest.mark.asyncio
    async def test_mock_mode_no_real_mqtt_operations(self, mock_adapter):
        """Test that mock mode doesn't perform real MQTT operations"""
        # Should not create real MQTT client
        assert mock_adapter._client is None
        
        # Operations should work without real connection
        await mock_adapter.start()
        
        device_info = DeviceInfo(entity_id="test", name="Test")
        success = await mock_adapter.publish_discovery_message(device_info, "sensor")
        assert success is True
        
        success = await mock_adapter.publish_state("test", "value")
        assert success is True
        
        def callback(topic, payload):
            pass
        success = await mock_adapter.subscribe_to_commands("test", callback)
        assert success is True
        
        # All operations should succeed without real broker
        assert mock_adapter.is_connected() is True
    
    @pytest.mark.asyncio 
    async def test_entity_tracking(self, mock_adapter):
        """Test that discovered entities are tracked"""
        await mock_adapter.start()
        
        # Publish multiple discovery messages
        devices = [
            DeviceInfo(entity_id="zone_1", name="Zone 1"),
            DeviceInfo(entity_id="zone_2", name="Zone 2"),
            DeviceInfo(entity_id="device_1", name="Device 1")
        ]
        
        for device in devices:
            await mock_adapter.publish_discovery_message(device, "sensor")
        
        # Check entities are tracked
        assert len(mock_adapter._discovered_entities) == 3
        assert "zone_1" in mock_adapter._discovered_entities
        assert "zone_2" in mock_adapter._discovered_entities
        assert "device_1" in mock_adapter._discovered_entities
        
        # Check discovery message details
        zone_1_discovery = mock_adapter._discovered_entities["zone_1"]
        assert zone_1_discovery.component == "sensor"
        assert zone_1_discovery.object_id == "zone_1"
        assert "unique_id" in zone_1_discovery.config
    
    @pytest.mark.asyncio
    async def test_state_tracking(self, mock_adapter):
        """Test that entity states are tracked"""
        await mock_adapter.start()
        
        # Publish states for different entities
        await mock_adapter.publish_state("zone_1", "cleaning", {"mode": "deep"})
        await mock_adapter.publish_state("device_1", "active", {"battery": 85})
        
        # Check states are tracked
        assert len(mock_adapter._entity_states) == 2
        
        zone_1_state = mock_adapter._entity_states["zone_1"]
        assert zone_1_state["state"] == "cleaning"
        assert zone_1_state["attributes"]["mode"] == "deep"
        assert "timestamp" in zone_1_state
        
        device_1_state = mock_adapter._entity_states["device_1"]
        assert device_1_state["state"] == "active"
        assert device_1_state["attributes"]["battery"] == 85