"""
Test suite for AICleaner v3 Service Manager
Tests service registration and execution with schema validation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ha_integration.service_manager import AICleanerServiceManager


class TestAICleanerServiceManager:
    """Test cases for AICleanerServiceManager."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = Mock(spec=HomeAssistant)
        hass.services = Mock()
        hass.services.async_register = Mock()
        hass.services.async_remove = Mock()
        return hass

    @pytest.fixture
    def service_manager(self, mock_hass):
        """Create service manager instance."""
        return AICleanerServiceManager(mock_hass, "aicleaner_v3")

    @pytest.fixture
    def mock_service_call(self):
        """Create mock service call."""
        call = Mock(spec=ServiceCall)
        call.data = {"param1": "value1", "param2": 123}
        return call

    @pytest.fixture
    def test_schema(self):
        """Create test schema."""
        return vol.Schema({
            vol.Required("param1"): str,
            vol.Optional("param2", default=100): int,
        })

    def test_service_manager_initialization(self, service_manager, mock_hass):
        """Test service manager initialization."""
        assert service_manager.hass == mock_hass
        assert service_manager.domain == "aicleaner_v3"

    @pytest.mark.asyncio
    async def test_register_service_basic(self, service_manager, mock_hass, test_schema):
        """Test basic service registration."""
        async def test_handler(call):
            return {"result": "success"}

        await service_manager.async_register_service(
            "test_service",
            test_schema,
            test_handler
        )

        mock_hass.services.async_register.assert_called_once()
        call_args = mock_hass.services.async_register.call_args
        assert call_args[0][0] == "aicleaner_v3"  # domain
        assert call_args[0][1] == "test_service"  # service name
        assert call_args[1]["schema"] == test_schema
        assert call_args[1]["supports_response"] == SupportsResponse.NONE

    @pytest.mark.asyncio
    async def test_register_service_with_response(self, service_manager, mock_hass, test_schema):
        """Test service registration with response support."""
        async def test_handler(call):
            return {"result": "success"}

        await service_manager.async_register_service(
            "test_service",
            test_schema,
            test_handler,
            SupportsResponse.ONLY
        )

        call_args = mock_hass.services.async_register.call_args
        assert call_args[1]["supports_response"] == SupportsResponse.ONLY

    @pytest.mark.asyncio
    async def test_service_handler_success(self, service_manager, mock_hass, test_schema, mock_service_call):
        """Test successful service handler execution."""
        handler_called = False
        handler_result = {"result": "success"}

        async def test_handler(call):
            nonlocal handler_called
            handler_called = True
            assert call.data == mock_service_call.data
            return handler_result

        await service_manager.async_register_service(
            "test_service",
            test_schema,
            test_handler,
            SupportsResponse.ONLY
        )

        # Get the registered handler
        registered_handler = mock_hass.services.async_register.call_args[0][2]
        
        # Call the handler
        result = await registered_handler(mock_service_call)
        
        assert handler_called
        assert result == handler_result

    @pytest.mark.asyncio
    async def test_service_handler_validation_error(self, service_manager, mock_hass, test_schema):
        """Test service handler with validation error."""
        async def test_handler(call):
            return {"result": "success"}

        await service_manager.async_register_service(
            "test_service",
            test_schema,
            test_handler
        )

        # Get the registered handler
        registered_handler = mock_hass.services.async_register.call_args[0][2]
        
        # Create call with invalid data
        invalid_call = Mock(spec=ServiceCall)
        invalid_call.data = {"param1": 123}  # Should be string
        
        # Mock schema validation to raise error
        with pytest.raises(HomeAssistantError) as exc_info:
            # This would normally be validated by HA core, but we'll simulate
            test_schema(invalid_call.data)
        
        # Verify the error is a validation error
        assert "expected str" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_service_handler_execution_error(self, service_manager, mock_hass, test_schema, mock_service_call):
        """Test service handler with execution error."""
        async def failing_handler(call):
            raise ValueError("Test error")

        await service_manager.async_register_service(
            "test_service",
            test_schema,
            failing_handler
        )

        # Get the registered handler
        registered_handler = mock_hass.services.async_register.call_args[0][2]
        
        # Call the handler and expect error
        with pytest.raises(HomeAssistantError) as exc_info:
            await registered_handler(mock_service_call)
        
        assert "Error executing service 'test_service'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_remove_service(self, service_manager, mock_hass):
        """Test service removal."""
        await service_manager.async_remove_service("test_service")
        
        mock_hass.services.async_remove.assert_called_once_with(
            "aicleaner_v3", "test_service"
        )

    @pytest.mark.asyncio
    async def test_service_handler_no_response(self, service_manager, mock_hass, test_schema, mock_service_call):
        """Test service handler that doesn't return response."""
        handler_called = False

        async def test_handler(call):
            nonlocal handler_called
            handler_called = True
            # No return value

        await service_manager.async_register_service(
            "test_service",
            test_schema,
            test_handler,
            SupportsResponse.NONE
        )

        # Get the registered handler
        registered_handler = mock_hass.services.async_register.call_args[0][2]
        
        # Call the handler
        result = await registered_handler(mock_service_call)
        
        assert handler_called
        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_service_registration(self, service_manager, mock_hass, test_schema):
        """Test registering multiple services."""
        async def handler1(call):
            return {"service": "1"}

        async def handler2(call):
            return {"service": "2"}

        await service_manager.async_register_service("service1", test_schema, handler1)
        await service_manager.async_register_service("service2", test_schema, handler2)

        assert mock_hass.services.async_register.call_count == 2

        # Check both services were registered
        calls = mock_hass.services.async_register.call_args_list
        assert calls[0][0][1] == "service1"
        assert calls[1][0][1] == "service2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])