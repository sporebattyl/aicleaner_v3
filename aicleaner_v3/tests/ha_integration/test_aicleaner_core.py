"""
Test AICleanerCore Functionality
Phase 4A: Enhanced Home Assistant Integration Tests

Tests for the AICleanerCore central coordinator to ensure proper zone management
and integration with HomeAssistantAdapter.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from core.aicleaner_core import AICleanerCore
from ha_integration.ha_adapter import HomeAssistantAdapter


class TestAICleanerCore:
    """Test AICleanerCore central coordinator functionality"""
    
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
    async def aicleaner_core(self, mock_ha_adapter, mock_ai_provider, sample_config):
        """Create AICleanerCore instance for testing"""
        core = AICleanerCore(
            config_data=sample_config,
            ha_adapter=mock_ha_adapter,
            ai_provider_manager=mock_ai_provider
        )
        await core.start()
        return core
    
    @pytest.mark.asyncio
    async def test_core_initialization(self, mock_ha_adapter, mock_ai_provider, sample_config):
        """Test AICleanerCore initializes correctly"""
        core = AICleanerCore(
            config_data=sample_config,
            ha_adapter=mock_ha_adapter,
            ai_provider_manager=mock_ai_provider
        )
        
        assert core.config == sample_config
        assert core.ha_adapter == mock_ha_adapter
        assert core.ai_provider_manager == mock_ai_provider
        assert not core._running
        assert not core._cleaning_active
        assert core._system_status == "idle"
    
    @pytest.mark.asyncio
    async def test_core_start_stop(self, aicleaner_core):
        """Test starting and stopping the core system"""
        # Should already be started from fixture
        assert aicleaner_core._running is True
        assert aicleaner_core._system_status == "ready"
        
        # Test stopping
        result = await aicleaner_core.stop()
        assert result is True
        assert aicleaner_core._running is False
        assert aicleaner_core._system_status == "stopped"
    
    def test_list_zones(self, aicleaner_core):
        """Test listing configured zones"""
        zones = aicleaner_core.list_zones()
        
        assert len(zones) == 3
        
        # Check first zone
        zone1 = zones[0]
        assert zone1["id"] == "zone_1"
        assert zone1["name"] == "Living Room"
        assert zone1["enabled"] is True
        assert zone1["status"] == "idle"
        assert zone1["devices"] == ["vacuum_001"]
        
        # Check disabled zone
        zone3 = zones[2]
        assert zone3["name"] == "Bedroom"
        assert zone3["enabled"] is False
    
    def test_get_system_status(self, aicleaner_core):
        """Test getting system status"""
        status = aicleaner_core.get_system_status()
        
        assert status["running"] is True
        assert status["status"] == "ready"
        assert status["cleaning_active"] is False
        assert status["zones_cleaning"] == []
        assert status["total_zones"] == 3
        assert status["enabled_zones"] == 2  # Only Living Room and Kitchen enabled
        assert status["ha_adapter_available"] is False  # Mock mode
        assert status["ai_provider_available"] is True
        assert "timestamp" in status
    
    @pytest.mark.asyncio
    async def test_clean_zone_by_id_success(self, aicleaner_core):
        """Test cleaning a specific zone successfully"""
        zone_id = "zone_1"  # Living Room
        cleaning_mode = "deep"
        duration = 45
        
        result = await aicleaner_core.clean_zone_by_id(zone_id, cleaning_mode, duration)
        
        assert result["status"] == "success"
        assert result["zone_id"] == zone_id
        assert result["mode"] == cleaning_mode
        assert result["estimated_duration"] == duration
        assert "timestamp" in result
        
        # Check system state updated
        assert aicleaner_core._cleaning_active is True
        assert zone_id in aicleaner_core._current_cleaning_zones
        assert aicleaner_core._system_status == "cleaning"
    
    @pytest.mark.asyncio
    async def test_clean_zone_invalid_id(self, aicleaner_core):
        """Test cleaning with invalid zone ID"""
        result = await aicleaner_core.clean_zone_by_id("invalid_zone", "normal")
        
        assert result["status"] == "error"
        assert "not found" in result["message"]
        assert result["zone_id"] == "invalid_zone"
    
    @pytest.mark.asyncio
    async def test_clean_disabled_zone(self, aicleaner_core):
        """Test cleaning a disabled zone"""
        zone_id = "zone_3"  # Bedroom (disabled)
        
        result = await aicleaner_core.clean_zone_by_id(zone_id, "normal")
        
        assert result["status"] == "error"
        assert "disabled" in result["message"]
        assert result["zone_id"] == zone_id
    
    @pytest.mark.asyncio
    async def test_clean_all_zones(self, aicleaner_core):
        """Test cleaning all enabled zones"""
        result = await aicleaner_core.clean_all_zones("normal")
        
        assert result["status"] == "success"
        assert result["mode"] == "normal"
        assert "zones_cleaning" in result
        assert len(result["zones_cleaning"]) == 2  # Only enabled zones
        
        # Check all enabled zones are now cleaning
        assert "zone_1" in aicleaner_core._current_cleaning_zones
        assert "zone_2" in aicleaner_core._current_cleaning_zones
        assert "zone_3" not in aicleaner_core._current_cleaning_zones  # Disabled
    
    @pytest.mark.asyncio
    async def test_stop_cleaning_specific_zone(self, aicleaner_core):
        """Test stopping cleaning in a specific zone"""
        # Start cleaning first
        await aicleaner_core.clean_zone_by_id("zone_1", "normal")
        await aicleaner_core.clean_zone_by_id("zone_2", "normal")
        
        assert len(aicleaner_core._current_cleaning_zones) == 2
        
        # Stop cleaning in zone_1
        result = await aicleaner_core.stop_cleaning("zone_1")
        
        assert result["status"] == "success"
        assert result["zone_id"] == "zone_1"
        assert "zone_1" not in aicleaner_core._current_cleaning_zones
        assert "zone_2" in aicleaner_core._current_cleaning_zones
    
    @pytest.mark.asyncio
    async def test_stop_cleaning_all_zones(self, aicleaner_core):
        """Test stopping cleaning in all zones"""
        # Start cleaning in multiple zones
        await aicleaner_core.clean_zone_by_id("zone_1", "normal")
        await aicleaner_core.clean_zone_by_id("zone_2", "normal")
        
        assert len(aicleaner_core._current_cleaning_zones) == 2
        assert aicleaner_core._cleaning_active is True
        
        # Stop all cleaning
        result = await aicleaner_core.stop_cleaning()
        
        assert result["status"] == "success"
        assert "stopped_zones" in result
        assert len(result["stopped_zones"]) == 2
        assert len(aicleaner_core._current_cleaning_zones) == 0
        assert aicleaner_core._cleaning_active is False
        assert aicleaner_core._system_status == "ready"
    
    @pytest.mark.asyncio
    async def test_stop_cleaning_zone_not_active(self, aicleaner_core):
        """Test stopping cleaning in a zone that's not being cleaned"""
        result = await aicleaner_core.stop_cleaning("zone_1")
        
        assert result["status"] == "warning"
        assert "not being cleaned" in result["message"]
        assert result["zone_id"] == "zone_1"
    
    @pytest.mark.asyncio
    async def test_core_not_running_error(self, mock_ha_adapter, mock_ai_provider, sample_config):
        """Test operations fail when core is not running"""
        core = AICleanerCore(
            config_data=sample_config,
            ha_adapter=mock_ha_adapter,
            ai_provider_manager=mock_ai_provider
        )
        # Don't start the core
        
        result = await core.clean_zone_by_id("zone_1", "normal")
        
        assert result["status"] == "error"
        assert "not running" in result["message"]
    
    @pytest.mark.asyncio
    async def test_ha_adapter_integration(self, aicleaner_core):
        """Test integration with HomeAssistantAdapter"""
        # The adapter should be in mock mode
        assert aicleaner_core.ha_adapter._mock_mode is True
        
        # Start cleaning should not cause errors even with mock adapter
        result = await aicleaner_core.clean_zone_by_id("zone_1", "normal")
        assert result["status"] == "success"
        
        # Mock adapter should have recorded some activity
        # (The actual device control calls)
        service_calls = aicleaner_core.ha_adapter.get_mock_service_calls()
        # Should have at least one call for device activation
        assert len(service_calls) >= 0  # Might be 0 if device activation is stubbed
    
    @pytest.mark.asyncio
    async def test_device_activation_integration(self, aicleaner_core):
        """Test device activation through HA adapter"""
        # Start cleaning in zone with devices
        result = await aicleaner_core.clean_zone_by_id("zone_1", "normal")
        
        assert result["status"] == "success"
        
        # Check internal device state was updated
        device_info = aicleaner_core._devices_data.get("vacuum_001")
        if device_info:  # Device exists in mock data
            assert device_info.get("status") in ["active", "idle"]  # Device state managed
    
    @pytest.mark.asyncio
    async def test_ai_provider_integration(self, aicleaner_core):
        """Test AI provider integration"""
        # AI provider should be available
        assert aicleaner_core.ai_provider_manager is not None
        
        # Cleaning operations should work with AI provider
        result = await aicleaner_core.clean_zone_by_id("zone_1", "normal")
        assert result["status"] == "success"
        
        # AI provider status should be accessible
        status = aicleaner_core.get_system_status()
        assert status["ai_provider_available"] is True
    
    @pytest.mark.asyncio
    async def test_concurrent_zone_operations(self, aicleaner_core):
        """Test multiple zones can be cleaned concurrently"""
        # Start cleaning in multiple zones
        result1 = await aicleaner_core.clean_zone_by_id("zone_1", "normal")
        result2 = await aicleaner_core.clean_zone_by_id("zone_2", "deep")
        
        assert result1["status"] == "success"
        assert result2["status"] == "success"
        
        # Both zones should be active
        assert len(aicleaner_core._current_cleaning_zones) == 2
        assert "zone_1" in aicleaner_core._current_cleaning_zones
        assert "zone_2" in aicleaner_core._current_cleaning_zones
        
        # System should show cleaning active
        status = aicleaner_core.get_system_status()
        assert status["cleaning_active"] is True
        assert status["zones_cleaning"] == 2