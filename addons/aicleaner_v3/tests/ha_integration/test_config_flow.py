"""
Test suite for AICleaner v3 Config Flow
Tests configuration flow UI integration and options handling.
"""

import pytest
from unittest.mock import Mock, patch
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ha_integration.config_flow import AICleanerConfigFlow, AICleanerOptionsFlowHandler
from const import DOMAIN


class TestAICleanerConfigFlow:
    """Test cases for AICleanerConfigFlow."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        return Mock(spec=HomeAssistant)

    @pytest.fixture
    def config_flow(self, mock_hass):
        """Create config flow instance."""
        flow = AICleanerConfigFlow()
        flow.hass = mock_hass
        return flow

    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry."""
        entry = Mock(spec=config_entries.ConfigEntry)
        entry.data = {"api_key": "test_key"}
        entry.options = {"cleaning_interval": 1800}
        return entry

    def test_config_flow_initialization(self, config_flow):
        """Test config flow initialization."""
        assert config_flow.VERSION == 1
        assert config_flow.CONNECTION_CLASS == config_entries.CONN_CLASS_LOCAL_PUSH

    @pytest.mark.asyncio
    async def test_async_step_user_no_input(self, config_flow):
        """Test user step without input (shows form)."""
        with patch.object(config_flow, '_async_current_entries', return_value=[]):
            result = await config_flow.async_step_user()
            
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "user"
            assert "api_key" in result["data_schema"].schema
            assert "cleaning_interval" in result["data_schema"].schema

    @pytest.mark.asyncio
    async def test_async_step_user_with_input(self, config_flow):
        """Test user step with valid input (creates entry)."""
        user_input = {
            "api_key": "test_api_key",
            "cleaning_interval": 1800
        }
        
        with patch.object(config_flow, '_async_current_entries', return_value=[]):
            result = await config_flow.async_step_user(user_input)
            
            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert result["title"] == "AICleaner v3"
            assert result["data"] == user_input

    @pytest.mark.asyncio
    async def test_async_step_user_already_configured(self, config_flow, mock_config_entry):
        """Test user step when already configured (aborts)."""
        with patch.object(config_flow, '_async_current_entries', return_value=[mock_config_entry]):
            result = await config_flow.async_step_user()
            
            assert result["type"] == FlowResultType.ABORT
            assert result["reason"] == "single_instance_allowed"

    def test_async_get_options_flow(self, mock_config_entry):
        """Test getting options flow."""
        options_flow = AICleanerConfigFlow.async_get_options_flow(mock_config_entry)
        
        assert isinstance(options_flow, AICleanerOptionsFlowHandler)
        assert options_flow.config_entry == mock_config_entry


class TestAICleanerOptionsFlowHandler:
    """Test cases for AICleanerOptionsFlowHandler."""

    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry."""
        entry = Mock(spec=config_entries.ConfigEntry)
        entry.data = {"api_key": "test_key"}
        entry.options = {"api_key": "existing_key", "cleaning_interval": 1800}
        return entry

    @pytest.fixture
    def options_flow(self, mock_config_entry):
        """Create options flow instance."""
        return AICleanerOptionsFlowHandler(mock_config_entry)

    def test_options_flow_initialization(self, options_flow, mock_config_entry):
        """Test options flow initialization."""
        assert options_flow.config_entry == mock_config_entry

    @pytest.mark.asyncio
    async def test_async_step_init_no_input(self, options_flow):
        """Test init step without input (shows form)."""
        result = await options_flow.async_step_init()
        
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"
        assert "api_key" in result["data_schema"].schema
        assert "cleaning_interval" in result["data_schema"].schema

    @pytest.mark.asyncio
    async def test_async_step_init_with_input(self, options_flow):
        """Test init step with valid input (creates entry)."""
        user_input = {
            "api_key": "updated_api_key",
            "cleaning_interval": 2400
        }
        
        result = await options_flow.async_step_init(user_input)
        
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == ""
        assert result["data"] == user_input

    @pytest.mark.asyncio
    async def test_async_step_init_default_values(self, options_flow):
        """Test init step uses existing values as defaults."""
        result = await options_flow.async_step_init()
        
        # Check that default values are loaded from config entry
        schema = result["data_schema"]
        
        # Extract default values from schema
        api_key_default = None
        cleaning_interval_default = None
        
        for key, validator in schema.schema.items():
            if str(key).endswith("'api_key'"):
                api_key_default = key.default()
            elif str(key).endswith("'cleaning_interval'"):
                cleaning_interval_default = key.default()
        
        assert api_key_default == "existing_key"
        assert cleaning_interval_default == 1800

    @pytest.mark.asyncio
    async def test_async_step_init_empty_options(self, mock_config_entry):
        """Test init step with empty options."""
        mock_config_entry.options = {}
        options_flow = AICleanerOptionsFlowHandler(mock_config_entry)
        
        result = await options_flow.async_step_init()
        
        # Should use empty string and default values
        schema = result["data_schema"]
        
        # Extract default values from schema
        api_key_default = None
        cleaning_interval_default = None
        
        for key, validator in schema.schema.items():
            if str(key).endswith("'api_key'"):
                api_key_default = key.default()
            elif str(key).endswith("'cleaning_interval'"):
                cleaning_interval_default = key.default()
        
        assert api_key_default == ""
        assert cleaning_interval_default == 3600

    @pytest.mark.asyncio
    async def test_options_flow_end_to_end(self, options_flow):
        """Test complete options flow."""
        # Step 1: Show form
        result = await options_flow.async_step_init()
        assert result["type"] == FlowResultType.FORM
        
        # Step 2: Submit form
        user_input = {
            "api_key": "new_api_key",
            "cleaning_interval": 3600
        }
        result = await options_flow.async_step_init(user_input)
        
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"] == user_input


class TestConfigFlowIntegration:
    """Integration tests for config flow."""

    @pytest.mark.asyncio
    async def test_config_flow_domain_registration(self):
        """Test that config flow is properly registered with domain."""
        assert AICleanerConfigFlow.domain == DOMAIN

    @pytest.mark.asyncio
    async def test_config_flow_schema_validation(self, mock_hass):
        """Test schema validation in config flow."""
        flow = AICleanerConfigFlow()
        flow.hass = mock_hass
        
        with patch.object(flow, '_async_current_entries', return_value=[]):
            # Test with valid data
            valid_input = {
                "api_key": "valid_key",
                "cleaning_interval": 1800
            }
            result = await flow.async_step_user(valid_input)
            assert result["type"] == FlowResultType.CREATE_ENTRY
            
            # Test with invalid data (negative interval)
            invalid_input = {
                "api_key": "valid_key",
                "cleaning_interval": -100
            }
            
            # The schema should handle validation, but since we're mocking,
            # we'll test the schema directly
            result = await flow.async_step_user()
            schema = result["data_schema"]
            
            # Test schema validation
            with pytest.raises(Exception):
                schema(invalid_input)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])