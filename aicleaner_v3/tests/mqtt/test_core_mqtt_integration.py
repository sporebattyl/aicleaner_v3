"""
Test Core MQTT Integration
Phase 4B: MQTT Discovery System Tests

Integration tests for AICleanerCore and MQTTAdapter interaction.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch

from core.aicleaner_core import AICleanerCore
from ha_integration.ha_adapter import HomeAssistantAdapter
from mqtt.adapter import MQTTAdapter, DeviceInfo
from mqtt.config import MQTTConfig


class TestCoreMQTTIntegration:
    """Test AICleanerCore integration with MQTT adapter"""
    
    @pytest.fixture
    def mock_ha_adapter(self):
        """Create mock HomeAssistantAdapter"""
        return HomeAssistantAdapter(hass=None)  # Mock mode
    
    @pytest.fixture
    def mock_ai_provider(self):
        """Create mock AI provider manager"""
        mock_provider = Mock()
        mock_provider.get_provider_status.return_value = {"status": "active"}
        return mock_provider
    
    @pytest.fixture
    def mock_mqtt_adapter(self):
        """Create mock MQTTAdapter"""
        mock_adapter = MagicMock(spec=MQTTAdapter)
        
        # Configure async methods
        mock_adapter.start = AsyncMock(return_value=True)
        mock_adapter.stop = AsyncMock(return_value=True)
        mock_adapter.publish_discovery_message = AsyncMock(return_value=True)
        mock_adapter.publish_state = AsyncMock(return_value=True)
        mock_adapter.subscribe_to_commands = AsyncMock(return_value=True)
        mock_adapter.unsubscribe_from_commands = AsyncMock(return_value=True)
        
        # Configure status methods
        mock_adapter.is_connected.return_value = True
        mock_adapter.is_running.return_value = True
        
        return mock_adapter
    
    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing"""
        return {
            "zones": [
                {"name": "Living Room", "enabled": True, "devices": ["vacuum_001"]},
                {"name": "Kitchen", "enabled": True, "devices": ["mop_001"]},
                {"name": "Bedroom", "enabled": False, "devices": []}
            ]
        }
    
    @pytest.fixture
    async def aicleaner_core(self, mock_ha_adapter, mock_ai_provider, mock_mqtt_adapter, sample_config):
        """Create AICleanerCore with mocked dependencies"""
        core = AICleanerCore(
            config_data=sample_config,
            ha_adapter=mock_ha_adapter,
            ai_provider_manager=mock_ai_provider,
            mqtt_adapter=mock_mqtt_adapter
        )
        await core.start()
        return core
    
    @pytest.mark.asyncio
    async def test_core_starts_mqtt_adapter(self, mock_ha_adapter, mock_ai_provider, mock_mqtt_adapter, sample_config):
        """Test that core starts MQTT adapter during initialization"""
        core = AICleanerCore(
            config_data=sample_config,
            ha_adapter=mock_ha_adapter,
            ai_provider_manager=mock_ai_provider,
            mqtt_adapter=mock_mqtt_adapter
        )
        
        await core.start()
        
        # Verify MQTT adapter was started
        mock_mqtt_adapter.start.assert_called_once()
        
        # Verify discovery messages were published
        assert mock_mqtt_adapter.publish_discovery_message.call_count > 0
    
    @pytest.mark.asyncio
    async def test_core_stops_mqtt_adapter(self, aicleaner_core, mock_mqtt_adapter):
        """Test that core stops MQTT adapter during shutdown"""
        await aicleaner_core.stop()
        
        # Verify MQTT adapter was stopped
        mock_mqtt_adapter.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_zone_cleaning_publishes_mqtt_state(self, aicleaner_core, mock_mqtt_adapter):
        """Test that zone cleaning operations publish MQTT state updates"""
        zone_id = "zone_1"
        
        # Start cleaning in zone
        result = await aicleaner_core.clean_zone_by_id(zone_id, "normal")
        
        assert result["status"] == "success"
        
        # Verify MQTT state updates were published
        # Should publish states for system, zones, and devices
        assert mock_mqtt_adapter.publish_state.call_count >= 3
        
        # Check specific calls for zone state
        publish_calls = mock_mqtt_adapter.publish_state.call_args_list
        zone_calls = [call for call in publish_calls if zone_id in str(call)]
        assert len(zone_calls) > 0
    
    @pytest.mark.asyncio
    async def test_stop_cleaning_publishes_mqtt_state(self, aicleaner_core, mock_mqtt_adapter):
        """Test that stopping cleaning publishes MQTT state updates"""
        zone_id = "zone_1"
        
        # Start cleaning first
        await aicleaner_core.clean_zone_by_id(zone_id, "normal")
        
        # Reset mock to count only stop operation calls
        mock_mqtt_adapter.publish_state.reset_mock()
        
        # Stop cleaning
        result = await aicleaner_core.stop_cleaning(zone_id)
        
        assert result["status"] == "success"
        
        # Verify MQTT state updates were published for stop operation
        assert mock_mqtt_adapter.publish_state.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_mqtt_discovery_publishing(self, mock_ha_adapter, mock_ai_provider, mock_mqtt_adapter, sample_config):
        """Test that MQTT discovery messages are published correctly"""
        core = AICleanerCore(
            config_data=sample_config,
            ha_adapter=mock_ha_adapter,
            ai_provider_manager=mock_ai_provider,
            mqtt_adapter=mock_mqtt_adapter
        )
        
        await core.start()
        
        # Check that discovery messages were published for zones and devices
        publish_calls = mock_mqtt_adapter.publish_discovery_message.call_args_list
        
        # Should have calls for zones (enabled ones) + devices + system
        # 2 enabled zones + 2 devices + system = at least 5 entities
        assert len(publish_calls) >= 5
        
        # Check component types used
        components_used = [call[0][1] for call in publish_calls]  # Second argument is component
        assert "sensor" in components_used
        assert "switch" in components_used
    
    @pytest.mark.asyncio
    async def test_mqtt_command_subscription(self, mock_ha_adapter, mock_ai_provider, mock_mqtt_adapter, sample_config):
        """Test that MQTT command subscriptions are set up"""
        core = AICleanerCore(
            config_data=sample_config,
            ha_adapter=mock_ha_adapter,
            ai_provider_manager=mock_ai_provider,
            mqtt_adapter=mock_mqtt_adapter
        )
        
        await core.start()
        
        # Check that command subscriptions were set up
        subscribe_calls = mock_mqtt_adapter.subscribe_to_commands.call_args_list
        
        # Should have subscriptions for zones, devices, and system
        assert len(subscribe_calls) >= 3
        
        # Check that callbacks were provided
        for call in subscribe_calls:
            entity_id = call[0][0]  # First argument is entity_id
            callback = call[0][1]   # Second argument is callback
            assert entity_id is not None
            assert callable(callback)
    
    @pytest.mark.asyncio
    async def test_mqtt_zone_command_handling(self, aicleaner_core, mock_mqtt_adapter):
        """Test handling MQTT commands for zone control"""
        zone_id = "zone_1"
        
        # Get the callback that was registered for zone commands
        subscribe_calls = mock_mqtt_adapter.subscribe_to_commands.call_args_list
        zone_callback = None
        
        for call in subscribe_calls:
            entity_id = call[0][0]
            if f"{zone_id}_cleaning" in entity_id:
                zone_callback = call[0][1]
                break
        
        assert zone_callback is not None
        
        # Simulate receiving ON command
        topic = f"test_device/{zone_id}_cleaning/set"
        await zone_callback(topic, "ON")
        
        # Check that zone is now cleaning
        status = aicleaner_core.get_system_status()
        assert status["cleaning_active"] is True
        assert status["zones_cleaning"] > 0
    
    @pytest.mark.asyncio
    async def test_mqtt_system_command_handling(self, aicleaner_core, mock_mqtt_adapter):
        """Test handling MQTT commands for system control"""
        # Stop the system first
        await aicleaner_core.stop()
        
        # Get the callback for system commands
        subscribe_calls = mock_mqtt_adapter.subscribe_to_commands.call_args_list
        system_callback = None
        
        for call in subscribe_calls:
            entity_id = call[0][0]
            if "system_control" in entity_id:
                system_callback = call[0][1]
                break
        
        assert system_callback is not None
        
        # Simulate receiving ON command
        topic = "test_device/system_control/set"
        await system_callback(topic, "ON")
        
        # Check that system is now running
        status = aicleaner_core.get_system_status()
        assert status["running"] is True
    
    @pytest.mark.asyncio
    async def test_core_without_mqtt_adapter(self, mock_ha_adapter, mock_ai_provider, sample_config):
        """Test that core works without MQTT adapter"""
        core = AICleanerCore(
            config_data=sample_config,
            ha_adapter=mock_ha_adapter,
            ai_provider_manager=mock_ai_provider,
            mqtt_adapter=None  # No MQTT adapter
        )
        
        # Should start successfully without MQTT
        success = await core.start()
        assert success is True
        
        # Operations should work without MQTT
        result = await core.clean_zone_by_id("zone_1", "normal")
        assert result["status"] == "success"
        
        # Should stop successfully
        success = await core.stop()
        assert success is True
    
    @pytest.mark.asyncio
    async def test_mqtt_adapter_start_failure(self, mock_ha_adapter, mock_ai_provider, sample_config):
        """Test handling when MQTT adapter fails to start"""
        mock_mqtt_adapter = MagicMock(spec=MQTTAdapter)
        mock_mqtt_adapter.start = AsyncMock(return_value=False)  # Simulate failure
        mock_mqtt_adapter.stop = AsyncMock(return_value=True)
        
        core = AICleanerCore(
            config_data=sample_config,
            ha_adapter=mock_ha_adapter,
            ai_provider_manager=mock_ai_provider,
            mqtt_adapter=mock_mqtt_adapter
        )
        
        # Core should still start even if MQTT fails
        success = await core.start()
        assert success is True
        
        # MQTT start should have been attempted
        mock_mqtt_adapter.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_mqtt_states_method(self, aicleaner_core, mock_mqtt_adapter):
        """Test the update_mqtt_states method"""
        # Call the method directly
        await aicleaner_core.update_mqtt_states()
        
        # Should publish states for system, zones, and devices
        publish_calls = mock_mqtt_adapter.publish_state.call_args_list
        
        # Should have at least one call for each zone, device, and system
        # 2 zones + 2 devices + 1 system = at least 5 calls
        assert len(publish_calls) >= 5
    
    @pytest.mark.asyncio
    async def test_mqtt_state_consistency(self, aicleaner_core, mock_mqtt_adapter):
        """Test that MQTT states are consistent with core state"""
        zone_id = "zone_1"
        
        # Start cleaning
        await aicleaner_core.clean_zone_by_id(zone_id, "deep")
        
        # Get the last state update calls
        publish_calls = mock_mqtt_adapter.publish_state.call_args_list
        
        # Find zone status update
        zone_status_call = None
        zone_switch_call = None
        
        for call in publish_calls:
            entity_id = call[0][0]
            state = call[0][1]
            
            if f"{zone_id}_status" in entity_id:
                zone_status_call = call
            elif f"{zone_id}_cleaning" in entity_id:
                zone_switch_call = call
        
        # Verify zone status shows cleaning
        assert zone_status_call is not None
        assert zone_status_call[0][1] == "cleaning"  # state parameter
        
        # Verify zone switch shows ON
        assert zone_switch_call is not None
        assert zone_switch_call[0][1] == "ON"  # state parameter
    
    @pytest.mark.asyncio
    async def test_mqtt_discovery_for_disabled_zone(self, mock_ha_adapter, mock_ai_provider, mock_mqtt_adapter):
        """Test that disabled zones don't get switch entities"""
        config = {
            "zones": [
                {"name": "Enabled Zone", "enabled": True, "devices": []},
                {"name": "Disabled Zone", "enabled": False, "devices": []}
            ]
        }
        
        core = AICleanerCore(
            config_data=config,
            ha_adapter=mock_ha_adapter,
            ai_provider_manager=mock_ai_provider,
            mqtt_adapter=mock_mqtt_adapter
        )
        
        await core.start()
        
        # Check discovery calls
        discovery_calls = mock_mqtt_adapter.publish_discovery_message.call_args_list
        
        # Count sensor vs switch entities
        sensor_count = sum(1 for call in discovery_calls if call[0][1] == "sensor")
        switch_count = sum(1 for call in discovery_calls if call[0][1] == "switch")
        
        # Should have sensors for both zones, but switch only for enabled zone
        assert sensor_count >= 2  # At least one for each zone
        # Disabled zone shouldn't have switch entity
        enabled_switches = [call for call in discovery_calls 
                          if call[0][1] == "switch" and "zone_1" in str(call)]
        disabled_switches = [call for call in discovery_calls 
                           if call[0][1] == "switch" and "zone_2" in str(call)]
        
        assert len(enabled_switches) > 0
        assert len(disabled_switches) == 0
    
    @pytest.mark.asyncio
    async def test_mqtt_command_payload_formats(self, aicleaner_core, mock_mqtt_adapter):
        """Test handling different MQTT command payload formats"""
        # Get zone command callback
        subscribe_calls = mock_mqtt_adapter.subscribe_to_commands.call_args_list
        zone_callback = None
        
        for call in subscribe_calls:
            entity_id = call[0][0]
            if "zone_1_cleaning" in entity_id:
                zone_callback = call[0][1]
                break
        
        assert zone_callback is not None
        
        topic = "test_device/zone_1_cleaning/set"
        
        # Test string payload
        await zone_callback(topic, "ON")
        assert aicleaner_core._cleaning_active is True
        
        await zone_callback(topic, "OFF")
        assert aicleaner_core._cleaning_active is False
        
        # Test dict payload
        await zone_callback(topic, {"state": "ON"})
        assert aicleaner_core._cleaning_active is True
        
        # Test other payload types
        await zone_callback(topic, True)  # Should convert to "TRUE"
        # No error should occur