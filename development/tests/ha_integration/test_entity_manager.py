"""
Test suite for AICleaner v3 Entity Manager
Tests entity lifecycle management and HA integration patterns.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ha_integration.entity_manager import AICleanerEntityManager, AICleanerSensor


class TestAICleanerEntityManager:
    """Test cases for AICleanerEntityManager."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = Mock(spec=HomeAssistant)
        return hass

    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator."""
        coordinator = Mock()
        coordinator.async_add_listener = Mock()
        coordinator.data = {}
        return coordinator

    @pytest.fixture
    def entity_manager(self, mock_hass, mock_coordinator):
        """Create entity manager instance."""
        return AICleanerEntityManager(mock_hass, mock_coordinator)

    @pytest.fixture
    def mock_add_entities(self):
        """Create mock add entities callback."""
        return AsyncMock()

    def test_entity_manager_initialization(self, entity_manager, mock_hass, mock_coordinator):
        """Test entity manager initialization."""
        assert entity_manager.hass == mock_hass
        assert entity_manager.coordinator == mock_coordinator
        assert entity_manager._entities == {}
        assert entity_manager.async_add_entities is None

    def test_set_async_add_entities(self, entity_manager, mock_add_entities):
        """Test setting async add entities callback."""
        entity_manager.set_async_add_entities(mock_add_entities)
        assert entity_manager.async_add_entities == mock_add_entities

    @pytest.mark.asyncio
    async def test_add_new_entity(self, entity_manager, mock_add_entities):
        """Test adding a new entity."""
        entity_manager.set_async_add_entities(mock_add_entities)
        
        entity_id = "test_entity"
        name = "Test Entity"
        state = "active"
        attributes = {"test_attr": "test_value"}
        
        await entity_manager.async_add_or_update_entity(entity_id, name, state, attributes)
        
        assert entity_id in entity_manager._entities
        assert isinstance(entity_manager._entities[entity_id], AICleanerSensor)
        mock_add_entities.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_existing_entity(self, entity_manager, mock_add_entities):
        """Test updating an existing entity."""
        entity_manager.set_async_add_entities(mock_add_entities)
        
        # First add entity
        entity_id = "test_entity"
        await entity_manager.async_add_or_update_entity(entity_id, "Test", "initial", {})
        
        # Reset mock
        mock_add_entities.reset_mock()
        
        # Update entity
        new_state = "updated"
        new_attributes = {"updated_attr": "updated_value"}
        
        await entity_manager.async_add_or_update_entity(entity_id, "Test", new_state, new_attributes)
        
        # Should not call add_entities again
        mock_add_entities.assert_not_called()
        
        # Entity should be updated
        entity = entity_manager._entities[entity_id]
        assert entity.state == new_state
        assert entity.extra_state_attributes == new_attributes

    @pytest.mark.asyncio
    async def test_remove_entity(self, entity_manager, mock_add_entities):
        """Test removing an entity."""
        entity_manager.set_async_add_entities(mock_add_entities)
        
        # First add entity
        entity_id = "test_entity"
        await entity_manager.async_add_or_update_entity(entity_id, "Test", "active", {})
        
        # Mock the async_remove method
        entity = entity_manager._entities[entity_id]
        entity.async_remove = AsyncMock()
        
        # Remove entity
        await entity_manager.async_remove_entity(entity_id)
        
        assert entity_id not in entity_manager._entities
        entity.async_remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_nonexistent_entity(self, entity_manager):
        """Test removing a non-existent entity."""
        # Should not raise exception
        await entity_manager.async_remove_entity("nonexistent_entity")


class TestAICleanerSensor:
    """Test cases for AICleanerSensor."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator."""
        coordinator = Mock()
        coordinator.async_add_listener = Mock()
        coordinator.data = {}
        return coordinator

    @pytest.fixture
    def sensor(self, mock_coordinator):
        """Create sensor instance."""
        return AICleanerSensor(
            mock_coordinator,
            "test_sensor",
            "Test Sensor",
            "active",
            {"test_attr": "test_value"}
        )

    def test_sensor_initialization(self, sensor, mock_coordinator):
        """Test sensor initialization."""
        assert sensor.coordinator == mock_coordinator
        assert sensor._entity_id == "test_sensor"
        assert sensor._name == "Test Sensor"
        assert sensor._state == "active"
        assert sensor._attributes == {"test_attr": "test_value"}

    def test_unique_id(self, sensor):
        """Test unique ID generation."""
        assert sensor.unique_id == "aicleaner_test_sensor"

    def test_name_property(self, sensor):
        """Test name property."""
        assert sensor.name == "Test Sensor"

    def test_state_property(self, sensor):
        """Test state property."""
        assert sensor.state == "active"

    def test_extra_state_attributes(self, sensor):
        """Test extra state attributes."""
        assert sensor.extra_state_attributes == {"test_attr": "test_value"}

    def test_update_state(self, sensor):
        """Test updating sensor state."""
        new_state = "updated"
        new_attributes = {"updated_attr": "updated_value"}
        
        sensor.update_state(new_state, new_attributes)
        
        assert sensor.state == new_state
        assert sensor.extra_state_attributes == new_attributes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])