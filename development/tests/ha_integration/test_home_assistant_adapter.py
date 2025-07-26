"""
Test HomeAssistantAdapter Mock Mode Functionality
Phase 4A: Enhanced Home Assistant Integration Tests

Tests for the HomeAssistantAdapter's mock mode behavior to ensure proper
decoupling from Home Assistant dependencies.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from ha_integration.ha_adapter import HomeAssistantAdapter


class TestHomeAssistantAdapter:
    """Test HomeAssistantAdapter mock mode functionality"""
    
    @pytest.fixture
    def mock_adapter(self):
        """Create HomeAssistantAdapter in mock mode"""
        return HomeAssistantAdapter(hass=None)
    
    @pytest.fixture
    def real_adapter(self):
        """Create HomeAssistantAdapter with mock hass instance"""
        mock_hass = Mock()
        return HomeAssistantAdapter(hass=mock_hass)
    
    def test_adapter_initializes_in_mock_mode(self, mock_adapter):
        """Test adapter initializes correctly in mock mode"""
        assert mock_adapter._mock_mode is True
        assert mock_adapter._hass is None
        assert not mock_adapter.is_available()
        assert len(mock_adapter._mock_states) == 0
        assert len(mock_adapter._service_calls) == 0
    
    def test_adapter_initializes_with_hass(self, real_adapter):
        """Test adapter initializes correctly with hass instance"""
        assert real_adapter._mock_mode is False
        assert real_adapter._hass is not None
        assert real_adapter.is_available()
    
    @pytest.mark.asyncio
    async def test_get_state_returns_mock_data(self, mock_adapter):
        """Test get_state returns mock data in mock mode"""
        entity_id = "sensor.test_sensor"
        
        # First call should return default mock state
        state = await mock_adapter.get_state(entity_id)
        
        assert state is not None
        assert state["entity_id"] == entity_id
        assert state["state"] == "unknown"
        assert "attributes" in state
        assert "last_changed" in state
        assert "last_updated" in state
    
    @pytest.mark.asyncio
    async def test_call_service_records_calls_in_mock_mode(self, mock_adapter):
        """Test call_service records calls without errors in mock mode"""
        domain = "light"
        service = "turn_on"
        service_data = {"entity_id": "light.test_light", "brightness": 255}
        
        # Call should succeed and be recorded
        result = await mock_adapter.call_service(domain, service, service_data)
        
        assert result is True
        
        # Check service call was recorded
        service_calls = mock_adapter.get_mock_service_calls()
        assert len(service_calls) == 1
        
        recorded_call = service_calls[0]
        assert recorded_call["domain"] == domain
        assert recorded_call["service"] == service
        assert recorded_call["service_data"] == service_data
        assert "timestamp" in recorded_call
    
    @pytest.mark.asyncio
    async def test_set_state_updates_mock_state(self, mock_adapter):
        """Test set_state updates mock state correctly"""
        entity_id = "sensor.test_sensor"
        state_value = "active"
        attributes = {"friendly_name": "Test Sensor", "unit": "°C"}
        
        # Set state
        result = await mock_adapter.set_state(entity_id, state_value, attributes)
        assert result is True
        
        # Verify state was set
        state = await mock_adapter.get_state(entity_id)
        assert state["entity_id"] == entity_id
        assert state["state"] == state_value
        assert state["attributes"] == attributes
    
    @pytest.mark.asyncio
    async def test_fire_event_in_mock_mode(self, mock_adapter):
        """Test fire_event works in mock mode"""
        event_type = "aicleaner_test_event"
        event_data = {"test_data": "value"}
        
        result = await mock_adapter.fire_event(event_type, event_data)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_entities_returns_mock_entities(self, mock_adapter):
        """Test get_entities returns mock entities"""
        # Set some mock states first
        await mock_adapter.set_state("sensor.temp", "25", {"unit": "°C"})
        await mock_adapter.set_state("light.living_room", "on", {"brightness": 100})
        await mock_adapter.set_state("switch.fan", "off", {})
        
        # Test getting all entities
        all_entities = await mock_adapter.get_entities()
        assert len(all_entities) == 3
        
        # Test getting entities by domain
        sensors = await mock_adapter.get_entities(domain="sensor")
        assert len(sensors) == 1
        assert sensors[0]["entity_id"] == "sensor.temp"
        
        lights = await mock_adapter.get_entities(domain="light")
        assert len(lights) == 1
        assert lights[0]["entity_id"] == "light.living_room"
    
    @pytest.mark.asyncio
    async def test_is_entity_available(self, mock_adapter):
        """Test entity availability checking"""
        # Set up test entities
        await mock_adapter.set_state("sensor.available", "on", {})
        await mock_adapter.set_state("sensor.unavailable", "unavailable", {})
        await mock_adapter.set_state("sensor.unknown", "unknown", {})
        
        # Test availability
        assert await mock_adapter.is_entity_available("sensor.available") is True
        assert await mock_adapter.is_entity_available("sensor.unavailable") is False
        assert await mock_adapter.is_entity_available("sensor.unknown") is False
        assert await mock_adapter.is_entity_available("sensor.nonexistent") is False
    
    def test_mock_data_management(self, mock_adapter):
        """Test mock data management utilities"""
        # Test clear functionality
        mock_adapter.set_mock_state("test.entity", "value", {"attr": "test"})
        mock_adapter._service_calls.append({"test": "call"})
        
        assert len(mock_adapter._mock_states) == 1
        assert len(mock_adapter._service_calls) == 1
        
        mock_adapter.clear_mock_data()
        
        assert len(mock_adapter._mock_states) == 0
        assert len(mock_adapter._service_calls) == 0
    
    def test_get_status(self, mock_adapter):
        """Test adapter status information"""
        status = mock_adapter.get_status()
        
        assert status["mock_mode"] is True
        assert status["ha_available"] is False
        assert status["mock_states_count"] == 0
        assert status["service_calls_count"] == 0
        
        # Add some mock data and check again
        mock_adapter.set_mock_state("test.entity", "value", {})
        mock_adapter._service_calls.append({"test": "call"})
        
        status = mock_adapter.get_status()
        assert status["mock_states_count"] == 1
        assert status["service_calls_count"] == 1
    
    @pytest.mark.asyncio
    async def test_multiple_service_calls_tracked(self, mock_adapter):
        """Test multiple service calls are properly tracked"""
        # Make multiple service calls
        await mock_adapter.call_service("light", "turn_on", {"entity_id": "light.1"})
        await mock_adapter.call_service("light", "turn_off", {"entity_id": "light.2"})
        await mock_adapter.call_service("switch", "toggle", {"entity_id": "switch.1"})
        
        service_calls = mock_adapter.get_mock_service_calls()
        assert len(service_calls) == 3
        
        # Verify call details
        assert service_calls[0]["domain"] == "light"
        assert service_calls[0]["service"] == "turn_on"
        assert service_calls[1]["domain"] == "light"
        assert service_calls[1]["service"] == "turn_off"
        assert service_calls[2]["domain"] == "switch"
        assert service_calls[2]["service"] == "toggle"
    
    @pytest.mark.asyncio
    async def test_error_handling_in_mock_mode(self, mock_adapter):
        """Test error handling doesn't break mock mode"""
        # These should not raise exceptions in mock mode
        result1 = await mock_adapter.get_state("")  # Empty entity ID
        result2 = await mock_adapter.call_service("", "", {})  # Empty domain/service
        result3 = await mock_adapter.set_state("", "", {})  # Empty entity ID
        
        # Mock mode should handle gracefully
        assert result1 is not None  # Should return default mock state
        assert result2 is True      # Should still record the call
        assert result3 is True      # Should still set the state