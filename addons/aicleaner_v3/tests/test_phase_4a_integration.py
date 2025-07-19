"""
Test Suite for Phase 4A: Enhanced Home Assistant Integration
"""

import asyncio
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime

# Import the modules we're testing
from ha_integration.entity_manager import EnhancedAICleanerEntityManager, EntityConfig, EntityType
from ha_integration.device_discovery import HADeviceDiscovery, DeviceType, DiscoveredDevice
from ha_integration.event_bridge import HAEventBridge, EventType, BridgedEvent

class TestEnhancedEntityManager:
    """Test the enhanced entity manager"""
    
    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance"""
        hass = Mock()
        hass.services = Mock()
        hass.services.async_register = AsyncMock()
        hass.states = Mock()
        hass.bus = Mock()
        hass.helpers = Mock()
        return hass
    
    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator"""
        coordinator = Mock()
        return coordinator
    
    @pytest.fixture
    def entity_manager(self, mock_hass, mock_coordinator):
        """Create entity manager instance"""
        return EnhancedAICleanerEntityManager(mock_hass, mock_coordinator)
    
    @pytest.mark.asyncio
    async def test_initialization(self, entity_manager):
        """Test entity manager initialization"""
        # Test successful initialization
        await entity_manager.async_initialize()
        
        # Verify services were registered
        assert entity_manager.hass.services.async_register.call_count >= 4
        
        # Verify core entities were created
        assert len(entity_manager._entity_configs) > 0
        assert "sensor.aicleaner_v3_system_health" in entity_manager._entity_configs
        assert "sensor.aicleaner_v3_total_requests" in entity_manager._entity_configs
        assert "switch.aicleaner_v3_system_enabled" in entity_manager._entity_configs
    
    @pytest.mark.asyncio
    async def test_entity_creation(self, entity_manager):
        """Test entity creation"""
        # Create a test entity config
        config = EntityConfig(
            entity_id="sensor.test_sensor",
            name="Test Sensor",
            entity_type=EntityType.SENSOR,
            state="test_value",
            attributes={"test_attr": "test_value"},
            icon="mdi:test",
            unique_id="test_sensor_unique"
        )
        
        # Create the entity
        await entity_manager.create_entity(config)
        
        # Verify entity was created
        assert "sensor.test_sensor" in entity_manager._entity_configs
        assert "sensor.test_sensor" in entity_manager._entities
        
        # Verify entity configuration
        created_config = entity_manager._entity_configs["sensor.test_sensor"]
        assert created_config.name == "Test Sensor"
        assert created_config.state == "test_value"
        assert created_config.attributes["test_attr"] == "test_value"
    
    @pytest.mark.asyncio
    async def test_entity_state_update(self, entity_manager):
        """Test entity state updates"""
        # Create a test entity first
        config = EntityConfig(
            entity_id="sensor.test_sensor",
            name="Test Sensor",
            entity_type=EntityType.SENSOR,
            state="initial_value",
            attributes={"test_attr": "initial_value"},
            unique_id="test_sensor_unique"
        )
        
        await entity_manager.create_entity(config)
        
        # Update the entity state
        await entity_manager.update_entity_state(
            "sensor.test_sensor",
            "updated_value",
            {"test_attr": "updated_value", "new_attr": "new_value"}
        )
        
        # Verify state was updated
        entity = entity_manager._entities["sensor.test_sensor"]
        assert entity._state == "updated_value"
        assert entity._attributes["test_attr"] == "updated_value"
        assert entity._attributes["new_attr"] == "new_value"
    
    @pytest.mark.asyncio
    async def test_provider_entities_creation(self, entity_manager):
        """Test provider entities creation"""
        # Mock provider data
        providers = [
            {
                "name": "OpenAI",
                "enabled": True,
                "status": "healthy",
                "health": True,
                "active_requests": 5,
                "priority": 1
            },
            {
                "name": "Anthropic",
                "enabled": False,
                "status": "disabled",
                "health": False,
                "active_requests": 0,
                "priority": 2
            }
        ]
        
        # Create provider entities
        await entity_manager.create_provider_entities(providers)
        
        # Verify provider entities were created
        assert "sensor.aicleaner_v3_provider_openai_status" in entity_manager._entity_configs
        assert "switch.aicleaner_v3_provider_openai_enabled" in entity_manager._entity_configs
        assert "sensor.aicleaner_v3_provider_anthropic_status" in entity_manager._entity_configs
        assert "switch.aicleaner_v3_provider_anthropic_enabled" in entity_manager._entity_configs
        
        # Verify provider entity states
        openai_status = entity_manager._entity_configs["sensor.aicleaner_v3_provider_openai_status"]
        assert openai_status.state == "healthy"
        assert openai_status.attributes["enabled"] == True
        
        anthropic_switch = entity_manager._entity_configs["switch.aicleaner_v3_provider_anthropic_enabled"]
        assert anthropic_switch.state == False
    
    @pytest.mark.asyncio
    async def test_service_call_handlers(self, entity_manager):
        """Test service call handlers"""
        # Initialize entity manager
        await entity_manager.async_initialize()
        
        # Create a mock service call
        service_call = Mock()
        service_call.data = {"provider_id": "openai", "action": "enable"}
        
        # Test provider control handler
        result = await entity_manager._handle_control_provider(service_call)
        assert result["success"] == True
        assert "openai" in result["message"]
        
        # Test zone control handler
        service_call.data = {"zone_id": "living_room", "action": "disable"}
        result = await entity_manager._handle_control_zone(service_call)
        assert result["success"] == True
        assert "living_room" in result["message"]
        
        # Test strategy handler
        service_call.data = {"strategy": "cost_optimized"}
        result = await entity_manager._handle_set_strategy(service_call)
        assert result["success"] == True
        assert "cost_optimized" in result["message"]

class TestDeviceDiscovery:
    """Test the device discovery service"""
    
    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance"""
        hass = Mock()
        hass.bus = Mock()
        hass.bus.async_listen = Mock()
        hass.states = Mock()
        hass.helpers = Mock()
        hass.helpers.area_registry = Mock()
        return hass
    
    @pytest.fixture
    def mock_registries(self):
        """Create mock registries"""
        device_registry = Mock()
        entity_registry = Mock()
        
        # Mock entity entries
        entity_entry = Mock()
        entity_entry.entity_id = "light.living_room"
        entity_entry.name = "Living Room Light"
        entity_entry.domain = "light"
        entity_entry.device_id = "device_123"
        
        entity_registry.entities = {"light.living_room": entity_entry}
        
        # Mock device entries
        device_entry = Mock()
        device_entry.area_id = "area_123"
        device_registry.async_get = Mock(return_value=device_entry)
        
        return device_registry, entity_registry
    
    @pytest.fixture
    def device_discovery(self, mock_hass):
        """Create device discovery instance"""
        return HADeviceDiscovery(mock_hass)
    
    @pytest.mark.asyncio
    async def test_device_type_detection(self, device_discovery):
        """Test device type detection"""
        # Test light entity
        device_type = device_discovery._get_device_type("light.living_room")
        assert device_type == DeviceType.LIGHT
        
        # Test sensor entity
        device_type = device_discovery._get_device_type("sensor.temperature")
        assert device_type == DeviceType.SENSOR
        
        # Test switch entity
        device_type = device_discovery._get_device_type("switch.outlet")
        assert device_type == DeviceType.SWITCH
        
        # Test unknown entity
        device_type = device_discovery._get_device_type("unknown.entity")
        assert device_type is None
    
    @pytest.mark.asyncio
    async def test_capability_extraction(self, device_discovery):
        """Test capability extraction"""
        # Mock state with brightness capability
        state = Mock()
        state.attributes = {"brightness": 255, "rgb_color": [255, 0, 0]}
        
        capabilities = device_discovery._extract_capabilities(state)
        assert "brightness" in capabilities
        assert "color" in capabilities
        
        # Mock state with temperature capability
        state.attributes = {"temperature": 22.5, "battery_level": 85}
        capabilities = device_discovery._extract_capabilities(state)
        assert "temperature" in capabilities
        assert "battery" in capabilities
    
    @pytest.mark.asyncio
    async def test_automation_eligibility(self, device_discovery):
        """Test automation eligibility checks"""
        # Test eligible entity
        state = Mock()
        state.attributes = {}
        assert device_discovery._is_automation_eligible("light.living_room", state) == True
        
        # Test non-eligible entity (sun)
        assert device_discovery._is_automation_eligible("sun.sun", state) == False
        
        # Test disabled entity
        state.attributes = {"disabled": True}
        assert device_discovery._is_automation_eligible("light.bedroom", state) == False
    
    def test_device_filtering_methods(self, device_discovery):
        """Test device filtering methods"""
        # Create mock discovered devices
        device1 = DiscoveredDevice(
            entity_id="light.living_room",
            name="Living Room Light",
            device_type=DeviceType.LIGHT,
            domain="light",
            state="on",
            attributes={},
            area_name="Living Room",
            automation_eligible=True
        )
        
        device2 = DiscoveredDevice(
            entity_id="sensor.temperature",
            name="Temperature Sensor",
            device_type=DeviceType.SENSOR,
            domain="sensor",
            state="22.5",
            attributes={},
            area_name="Living Room",
            automation_eligible=True
        )
        
        device3 = DiscoveredDevice(
            entity_id="switch.outlet",
            name="Outlet Switch",
            device_type=DeviceType.SWITCH,
            domain="switch",
            state="off",
            attributes={},
            area_name="Kitchen",
            automation_eligible=False
        )
        
        # Add devices to discovery
        device_discovery.discovered_devices = {
            device1.entity_id: device1,
            device2.entity_id: device2,
            device3.entity_id: device3
        }
        
        # Test filtering by type
        lights = device_discovery.get_devices_by_type(DeviceType.LIGHT)
        assert len(lights) == 1
        assert lights[0].entity_id == "light.living_room"
        
        # Test filtering by area
        living_room_devices = device_discovery.get_devices_by_area("Living Room")
        assert len(living_room_devices) == 2
        
        # Test automation eligible devices
        eligible_devices = device_discovery.get_automation_eligible_devices()
        assert len(eligible_devices) == 2
        
        # Test device statistics
        stats = device_discovery.get_device_statistics()
        assert stats["total_devices"] == 3
        assert stats["automation_eligible"] == 2
        assert stats["by_type"]["light"] == 1
        assert stats["by_area"]["Living Room"] == 2

class TestEventBridge:
    """Test the event bridge"""
    
    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance"""
        hass = Mock()
        hass.bus = Mock()
        hass.bus.async_listen = Mock()
        hass.services = Mock()
        hass.services.async_call = AsyncMock()
        return hass
    
    @pytest.fixture
    def event_bridge(self, mock_hass):
        """Create event bridge instance"""
        return HAEventBridge(mock_hass)
    
    @pytest.mark.asyncio
    async def test_initialization(self, event_bridge):
        """Test event bridge initialization"""
        await event_bridge.async_initialize()
        
        # Verify Home Assistant listeners were set up
        assert event_bridge.hass.bus.async_listen.call_count >= 5
        
        # Verify web event handlers were set up
        assert len(event_bridge.event_listeners) >= 6
        assert "provider_control" in event_bridge.event_listeners
        assert "zone_control" in event_bridge.event_listeners
    
    @pytest.mark.asyncio
    async def test_event_creation(self, event_bridge):
        """Test bridged event creation"""
        # Create a test event
        event = BridgedEvent(
            event_type=EventType.STATE_CHANGED,
            timestamp=datetime.now(),
            source="home_assistant",
            data={"entity_id": "light.living_room", "state": "on"},
            entity_id="light.living_room"
        )
        
        # Test event dictionary conversion
        event_dict = event.to_dict()
        assert event_dict["event_type"] == "state_changed"
        assert event_dict["source"] == "home_assistant"
        assert event_dict["data"]["entity_id"] == "light.living_room"
        assert event_dict["entity_id"] == "light.living_room"
    
    @pytest.mark.asyncio
    async def test_web_event_handling(self, event_bridge):
        """Test web event handling"""
        # Initialize event bridge
        await event_bridge.async_initialize()
        
        # Test provider control event
        await event_bridge.handle_web_event(
            "provider_control",
            {"provider_id": "openai", "action": "enable"}
        )
        
        # Verify service call was made
        event_bridge.hass.services.async_call.assert_called_with(
            "aicleaner_v3",
            "control_provider",
            {"provider_id": "openai", "action": "enable"}
        )
        
        # Test zone control event
        await event_bridge.handle_web_event(
            "zone_control",
            {"zone_id": "living_room", "action": "disable"}
        )
        
        # Verify service call was made
        assert event_bridge.hass.services.async_call.call_count == 2
    
    def test_entity_relevance_check(self, event_bridge):
        """Test entity relevance checking"""
        # Test AICleaner entities
        assert event_bridge._is_relevant_entity("sensor.aicleaner_v3_system_health") == True
        assert event_bridge._is_relevant_entity("switch.aicleaner_v3_system_enabled") == True
        
        # Test relevant automation entities
        assert event_bridge._is_relevant_entity("light.living_room") == True
        assert event_bridge._is_relevant_entity("switch.outlet") == True
        assert event_bridge._is_relevant_entity("sensor.temperature") == True
        
        # Test irrelevant entities
        assert event_bridge._is_relevant_entity("sun.sun") == False
        assert event_bridge._is_relevant_entity("weather.home") == False
    
    def test_websocket_client_management(self, event_bridge):
        """Test WebSocket client management"""
        # Create mock clients
        client1 = Mock()
        client2 = Mock()
        
        # Add clients
        event_bridge.add_websocket_client(client1)
        event_bridge.add_websocket_client(client2)
        
        assert len(event_bridge.websocket_clients) == 2
        
        # Remove client
        event_bridge.remove_websocket_client(client1)
        assert len(event_bridge.websocket_clients) == 1
        assert client2 in event_bridge.websocket_clients
    
    def test_event_history_management(self, event_bridge):
        """Test event history management"""
        # Create test events
        events = []
        for i in range(10):
            event = BridgedEvent(
                event_type=EventType.STATE_CHANGED,
                timestamp=datetime.now(),
                source="test",
                data={"test": f"event_{i}"}
            )
            events.append(event)
        
        # Add events to history
        for event in events:
            asyncio.create_task(event_bridge._add_event_to_history(event))
        
        # Test history retrieval
        history = event_bridge.get_event_history(limit=5)
        assert len(history) <= 5
        
        # Test statistics
        stats = event_bridge.get_event_statistics()
        assert stats["total_events"] >= 0
        assert "event_types" in stats
        assert "sources" in stats

# Integration test
class TestPhase4AIntegration:
    """Test the complete Phase 4A integration"""
    
    @pytest.fixture
    def mock_hass(self):
        """Create a comprehensive mock Home Assistant instance"""
        hass = Mock()
        hass.services = Mock()
        hass.services.async_register = AsyncMock()
        hass.services.async_call = AsyncMock()
        hass.bus = Mock()
        hass.bus.async_listen = Mock()
        hass.states = Mock()
        hass.helpers = Mock()
        hass.helpers.area_registry = Mock()
        return hass
    
    @pytest.fixture
    def integrated_system(self, mock_hass):
        """Create an integrated system with all components"""
        coordinator = Mock()
        
        # Create all components
        entity_manager = EnhancedAICleanerEntityManager(mock_hass, coordinator)
        device_discovery = HADeviceDiscovery(mock_hass)
        event_bridge = HAEventBridge(mock_hass)
        
        return {
            "entity_manager": entity_manager,
            "device_discovery": device_discovery,
            "event_bridge": event_bridge,
            "hass": mock_hass
        }
    
    @pytest.mark.asyncio
    async def test_complete_integration(self, integrated_system):
        """Test complete Phase 4A integration"""
        entity_manager = integrated_system["entity_manager"]
        device_discovery = integrated_system["device_discovery"]
        event_bridge = integrated_system["event_bridge"]
        
        # Initialize all components
        await entity_manager.async_initialize()
        await event_bridge.async_initialize()
        
        # Verify all components initialized successfully
        assert len(entity_manager._entity_configs) > 0
        assert len(event_bridge.event_listeners) > 0
        
        # Test provider entity creation and management
        providers = [
            {
                "name": "OpenAI",
                "enabled": True,
                "status": "healthy",
                "health": True,
                "active_requests": 3,
                "priority": 1
            }
        ]
        
        await entity_manager.create_provider_entities(providers)
        
        # Test web event handling through event bridge
        await event_bridge.handle_web_event(
            "provider_control",
            {"provider_id": "openai", "action": "disable"}
        )
        
        # Verify service call was made
        assert event_bridge.hass.services.async_call.called
        
        # Test device discovery integration
        device_type = device_discovery._get_device_type("light.living_room")
        assert device_type == DeviceType.LIGHT
        
        # Test event history
        history = event_bridge.get_event_history(limit=10)
        assert isinstance(history, list)
        
        # Test statistics
        entity_stats = entity_manager.get_entity_count()
        device_stats = device_discovery.get_device_statistics()
        event_stats = event_bridge.get_event_statistics()
        
        assert entity_stats > 0
        assert isinstance(device_stats, dict)
        assert isinstance(event_stats, dict)

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])