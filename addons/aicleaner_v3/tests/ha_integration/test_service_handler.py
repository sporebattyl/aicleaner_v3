"""
Test ServiceHandler Functionality
Phase 4A: Enhanced Home Assistant Integration Tests

Tests for the ServiceHandler that processes Home Assistant service calls
and integrates with AICleanerCore.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from ha_integration.service_handler import ServiceHandler
from ha_integration.ha_client import HAClient
from ha_integration.config_schema import HAIntegrationConfig
from core.aicleaner_core import AICleanerCore
from ha_integration.ha_adapter import HomeAssistantAdapter


class TestServiceHandler:
    """Test ServiceHandler HA service call processing"""
    
    @pytest.fixture
    def mock_ha_client(self):
        """Create mock HAClient"""
        mock_client = Mock(spec=HAClient)
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.disconnect = AsyncMock()
        mock_client.subscribe_events = AsyncMock()
        return mock_client
    
    @pytest.fixture
    def ha_config(self):
        """Create HA integration configuration"""
        return HAIntegrationConfig(
            enabled=True,
            websocket_url="ws://test/websocket",
            rest_api_url="http://test/api",
            service_domain="aicleaner",
            entity_prefix="aicleaner_"
        )
    
    @pytest.fixture
    async def mock_aicleaner_core(self):
        """Create mock AICleanerCore"""
        mock_core = Mock(spec=AICleanerCore)
        
        # Mock common methods
        mock_core.clean_zone_by_id = AsyncMock()
        mock_core.clean_all_zones = AsyncMock()
        mock_core.stop_cleaning = AsyncMock()
        mock_core.list_zones = Mock()
        mock_core.get_system_status = Mock()
        
        # Set up default return values
        mock_core.clean_zone_by_id.return_value = {
            "status": "success",
            "message": "Cleaning started in zone test_zone",
            "zone_id": "test_zone"
        }
        
        mock_core.clean_all_zones.return_value = {
            "status": "success", 
            "message": "Cleaning started in all zones"
        }
        
        mock_core.stop_cleaning.return_value = {
            "status": "success",
            "message": "Cleaning stopped"
        }
        
        return mock_core
    
    @pytest.fixture
    def service_handler(self, mock_ha_client, ha_config, mock_aicleaner_core):
        """Create ServiceHandler instance for testing"""
        return ServiceHandler(
            ha_client=mock_ha_client,
            config=ha_config,
            aicleaner_core=mock_aicleaner_core
        )
    
    def test_service_handler_initialization(self, service_handler, mock_ha_client, ha_config, mock_aicleaner_core):
        """Test ServiceHandler initializes correctly"""
        assert service_handler.ha_client == mock_ha_client
        assert service_handler.config == ha_config
        assert service_handler.aicleaner_core == mock_aicleaner_core
        assert len(service_handler.registered_services) == 0
        assert len(service_handler.service_handlers) == 0
        assert len(service_handler.service_call_history) == 0
    
    @pytest.mark.asyncio
    async def test_handle_start_cleaning_with_zone(self, service_handler, mock_aicleaner_core):
        """Test handling start_cleaning service call with specific zone"""
        service_data = {
            "zone_id": "living_room",
            "cleaning_mode": "deep",
            "duration": 45
        }
        
        result = await service_handler.handle_start_cleaning(service_data)
        
        # Verify AICleanerCore was called correctly
        mock_aicleaner_core.clean_zone_by_id.assert_called_once_with(
            "living_room", "deep", 45
        )
        
        # Verify result
        assert result["status"] == "success"
        assert result["zone_id"] == "living_room"
    
    @pytest.mark.asyncio
    async def test_handle_start_cleaning_all_zones(self, service_handler, mock_aicleaner_core):
        """Test handling start_cleaning service call for all zones"""
        service_data = {
            "cleaning_mode": "normal"
        }
        
        result = await service_handler.handle_start_cleaning(service_data)
        
        # Verify AICleanerCore was called correctly
        mock_aicleaner_core.clean_all_zones.assert_called_once_with("normal")
        
        # Verify result
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_handle_start_cleaning_with_defaults(self, service_handler, mock_aicleaner_core):
        """Test handling start_cleaning with default parameters"""
        service_data = {}
        
        result = await service_handler.handle_start_cleaning(service_data)
        
        # Should call clean_all_zones with default mode
        mock_aicleaner_core.clean_all_zones.assert_called_once_with("normal")
    
    @pytest.mark.asyncio
    async def test_handle_stop_cleaning_specific_zone(self, service_handler, mock_aicleaner_core):
        """Test handling stop_cleaning for specific zone"""
        service_data = {"zone_id": "kitchen"}
        
        result = await service_handler.handle_stop_cleaning(service_data)
        
        # Verify AICleanerCore was called correctly
        mock_aicleaner_core.stop_cleaning.assert_called_once_with("kitchen")
        
        # Verify result
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_handle_stop_cleaning_all_zones(self, service_handler, mock_aicleaner_core):
        """Test handling stop_cleaning for all zones"""
        service_data = {}
        
        result = await service_handler.handle_stop_cleaning(service_data)
        
        # Verify AICleanerCore was called correctly
        mock_aicleaner_core.stop_cleaning.assert_called_once_with(None)
        
        # Verify result
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_handle_service_call_error_handling(self, service_handler, mock_aicleaner_core):
        """Test error handling in service calls"""
        # Make AICleanerCore raise an exception
        mock_aicleaner_core.clean_zone_by_id.side_effect = Exception("Test error")
        
        service_data = {"zone_id": "test_zone"}
        result = await service_handler.handle_start_cleaning(service_data)
        
        # Should return error response
        assert result["status"] == "error"
        assert "Test error" in result["message"]
        assert result["zone_id"] == "test_zone"
    
    @pytest.mark.asyncio
    async def test_service_handler_without_aicleaner_core(self, mock_ha_client, ha_config):
        """Test ServiceHandler behavior when AICleanerCore is not available"""
        handler = ServiceHandler(
            ha_client=mock_ha_client,
            config=ha_config,
            aicleaner_core=None
        )
        
        service_data = {"zone_id": "test_zone"}
        result = await handler.handle_start_cleaning(service_data)
        
        # Should return simulation mode response
        assert result["status"] == "success"
        assert "simulation mode" in result["message"]
        assert "not initialized" in result["note"]
    
    @pytest.mark.asyncio
    async def test_aicleaner_core_returns_error(self, service_handler, mock_aicleaner_core):
        """Test handling when AICleanerCore returns error status"""
        # Configure mock to return error
        mock_aicleaner_core.clean_zone_by_id.return_value = {
            "status": "error",
            "message": "Zone not found",
            "zone_id": "invalid_zone"
        }
        
        service_data = {"zone_id": "invalid_zone"}
        result = await service_handler.handle_start_cleaning(service_data)
        
        # Should pass through the error from AICleanerCore
        assert result["status"] == "error"
        assert result["message"] == "Zone not found"
        assert result["zone_id"] == "invalid_zone"
    
    def test_service_call_logging(self, service_handler):
        """Test service call history logging"""
        service_name = "start_cleaning"
        service_data = {"zone_id": "test"}
        
        # Log a service call
        service_handler._log_service_call(service_name, service_data)
        
        # Check history
        assert len(service_handler.service_call_history) == 1
        
        logged_call = service_handler.service_call_history[0]
        assert logged_call["service"] == service_name
        assert logged_call["data"] == service_data
        assert "timestamp" in logged_call
    
    def test_service_call_history_limit(self, service_handler):
        """Test service call history respects maximum size"""
        # Set small limit for testing
        service_handler.max_history_size = 3
        
        # Log more calls than the limit
        for i in range(5):
            service_handler._log_service_call(f"service_{i}", {"test": i})
        
        # Should only keep the most recent calls
        assert len(service_handler.service_call_history) == 3
        
        # Should have the last 3 calls
        assert service_handler.service_call_history[0]["service"] == "service_2"
        assert service_handler.service_call_history[1]["service"] == "service_3"
        assert service_handler.service_call_history[2]["service"] == "service_4"
    
    @pytest.mark.asyncio
    async def test_cleaning_mode_parameter_handling(self, service_handler, mock_aicleaner_core):
        """Test different cleaning mode parameters"""
        test_modes = ["normal", "deep", "quick", "eco"]
        
        for mode in test_modes:
            service_data = {"cleaning_mode": mode, "zone_id": "test_zone"}
            
            await service_handler.handle_start_cleaning(service_data)
            
            # Verify correct mode was passed to AICleanerCore
            mock_aicleaner_core.clean_zone_by_id.assert_called_with(
                "test_zone", mode, None
            )
            
            # Reset mock for next iteration
            mock_aicleaner_core.clean_zone_by_id.reset_mock()
    
    @pytest.mark.asyncio
    async def test_duration_parameter_handling(self, service_handler, mock_aicleaner_core):
        """Test duration parameter handling"""
        service_data = {
            "zone_id": "test_zone",
            "cleaning_mode": "normal",
            "duration": 60
        }
        
        await service_handler.handle_start_cleaning(service_data)
        
        # Verify duration was passed correctly
        mock_aicleaner_core.clean_zone_by_id.assert_called_once_with(
            "test_zone", "normal", 60
        )
    
    @pytest.mark.asyncio
    async def test_concurrent_service_calls(self, service_handler, mock_aicleaner_core):
        """Test handling multiple concurrent service calls"""
        import asyncio
        
        # Create multiple service calls
        calls = [
            service_handler.handle_start_cleaning({"zone_id": f"zone_{i}"})
            for i in range(3)
        ]
        
        # Execute concurrently
        results = await asyncio.gather(*calls)
        
        # All should succeed
        for result in results:
            assert result["status"] == "success"
        
        # AICleanerCore should have been called for each
        assert mock_aicleaner_core.clean_zone_by_id.call_count == 3
    
    def test_get_registered_services(self, service_handler):
        """Test getting registered services (when implemented)"""
        # This tests the interface even if not fully implemented
        assert hasattr(service_handler, 'registered_services')
        assert isinstance(service_handler.registered_services, dict)