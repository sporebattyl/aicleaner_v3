#!/usr/bin/env python3
"""
Simple test runner for Phase 4A HA integration tests
Since pytest is not available in the system environment, this provides basic test validation.
"""

import sys
import asyncio
import inspect
from unittest.mock import Mock, AsyncMock
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_test_function(test_func, *args, **kwargs):
    """Run a single test function and return result"""
    try:
        if inspect.iscoroutinefunction(test_func):
            # Async test function
            result = asyncio.run(test_func(*args, **kwargs))
        else:
            # Sync test function
            result = test_func(*args, **kwargs)
        return True, None
    except Exception as e:
        return False, str(e)

def test_imports():
    """Test that all modules can be imported correctly"""
    print("Testing module imports...")
    
    try:
        # Core modules
        from core.aicleaner_core import AICleanerCore
        from ha_integration.ha_adapter import HomeAssistantAdapter
        from ha_integration.service_handler import ServiceHandler
        print("✓ Core modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_ha_adapter_mock_mode():
    """Test HomeAssistantAdapter mock mode functionality"""
    print("Testing HomeAssistantAdapter mock mode...")
    
    from ha_integration.ha_adapter import HomeAssistantAdapter
    
    # Test initialization
    adapter = HomeAssistantAdapter(hass=None)
    assert adapter._mock_mode is True
    assert adapter._hass is None
    assert not adapter.is_available()
    
    # Test mock state operations
    entity_id = "sensor.test"
    adapter.set_mock_state(entity_id, "active", {"unit": "test"})
    
    mock_states = adapter._mock_states
    assert entity_id in mock_states
    assert mock_states[entity_id]["state"] == "active"
    
    print("✓ HomeAssistantAdapter mock mode tests passed")
    return True

def test_aicleaner_core_basic():
    """Test AICleanerCore basic functionality"""
    print("Testing AICleanerCore basic functionality...")
    
    from core.aicleaner_core import AICleanerCore
    from ha_integration.ha_adapter import HomeAssistantAdapter
    
    # Create mock dependencies
    ha_adapter = HomeAssistantAdapter(hass=None)
    mock_ai_provider = Mock()
    
    config_data = {
        "zones": [
            {"name": "Living Room", "enabled": True, "devices": ["vacuum_001"]},
            {"name": "Kitchen", "enabled": True, "devices": ["mop_001"]}
        ]
    }
    
    # Test initialization
    core = AICleanerCore(
        config_data=config_data,
        ha_adapter=ha_adapter,
        ai_provider_manager=mock_ai_provider
    )
    
    assert core.config == config_data
    assert core.ha_adapter == ha_adapter
    assert not core._running
    
    # Test zone listing
    zones = core.list_zones()
    assert len(zones) == 2
    assert zones[0]["name"] == "Living Room"
    assert zones[0]["enabled"] is True
    
    print("✓ AICleanerCore basic tests passed")
    return True

async def test_aicleaner_core_async():
    """Test AICleanerCore async functionality"""
    print("Testing AICleanerCore async functionality...")
    
    from core.aicleaner_core import AICleanerCore
    from ha_integration.ha_adapter import HomeAssistantAdapter
    
    # Create mock dependencies
    ha_adapter = HomeAssistantAdapter(hass=None)
    mock_ai_provider = Mock()
    mock_ai_provider.get_provider_status.return_value = {"status": "active"}
    
    config_data = {
        "zones": [
            {"name": "Living Room", "enabled": True, "devices": ["vacuum_001"]}
        ]
    }
    
    # Test core startup
    core = AICleanerCore(
        config_data=config_data,
        ha_adapter=ha_adapter,
        ai_provider_manager=mock_ai_provider
    )
    
    await core.start()
    assert core._running is True
    assert core._system_status == "ready"
    
    # Test zone cleaning
    result = await core.clean_zone_by_id("zone_1", "normal")
    assert result["status"] == "success"
    assert result["zone_id"] == "zone_1"
    
    # Test system status
    status = core.get_system_status()
    assert status["running"] is True
    assert status["total_zones"] == 1
    
    await core.stop()
    assert core._running is False
    
    print("✓ AICleanerCore async tests passed")
    return True

def test_service_handler_basic():
    """Test ServiceHandler basic functionality"""
    print("Testing ServiceHandler basic functionality...")
    
    from ha_integration.service_handler import ServiceHandler
    from ha_integration.ha_client import HAClient
    from ha_integration.config_schema import HAIntegrationConfig
    from core.aicleaner_core import AICleanerCore
    from ha_integration.ha_adapter import HomeAssistantAdapter
    
    # Create mock dependencies
    mock_ha_client = Mock(spec=HAClient)
    ha_config = HAIntegrationConfig(
        enabled=True,
        websocket_url="ws://test/websocket",
        rest_api_url="http://test/api",
        service_domain="aicleaner",
        entity_prefix="aicleaner_"
    )
    
    mock_core = Mock(spec=AICleanerCore)
    mock_core.clean_zone_by_id = AsyncMock(return_value={
        "status": "success",
        "zone_id": "test_zone"
    })
    
    # Test initialization
    handler = ServiceHandler(
        ha_client=mock_ha_client,
        config=ha_config,
        aicleaner_core=mock_core
    )
    
    assert handler.ha_client == mock_ha_client
    assert handler.config == ha_config
    assert handler.aicleaner_core == mock_core
    
    print("✓ ServiceHandler basic tests passed")
    return True

async def test_service_handler_async():
    """Test ServiceHandler async functionality"""
    print("Testing ServiceHandler async functionality...")
    
    from ha_integration.service_handler import ServiceHandler
    from ha_integration.ha_client import HAClient
    from ha_integration.config_schema import HAIntegrationConfig
    from core.aicleaner_core import AICleanerCore
    
    # Create mock dependencies
    mock_ha_client = Mock(spec=HAClient)
    ha_config = HAIntegrationConfig(
        enabled=True,
        websocket_url="ws://test/websocket",
        rest_api_url="http://test/api",
        service_domain="aicleaner",
        entity_prefix="aicleaner_"
    )
    
    mock_core = Mock(spec=AICleanerCore)
    mock_core.clean_zone_by_id = AsyncMock(return_value={
        "status": "success",
        "zone_id": "living_room"
    })
    
    handler = ServiceHandler(
        ha_client=mock_ha_client,
        config=ha_config,
        aicleaner_core=mock_core
    )
    
    # Test service call handling
    service_data = {
        "zone_id": "living_room",
        "cleaning_mode": "deep"
    }
    
    result = await handler.handle_start_cleaning(service_data)
    assert result["status"] == "success"
    assert result["zone_id"] == "living_room"
    
    # Verify mock was called correctly
    mock_core.clean_zone_by_id.assert_called_once_with("living_room", "deep", None)
    
    print("✓ ServiceHandler async tests passed")
    return True

def main():
    """Run all tests"""
    print("Phase 4A: Enhanced Home Assistant Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Module Imports", test_imports),
        ("HomeAssistantAdapter Mock Mode", test_ha_adapter_mock_mode),
        ("AICleanerCore Basic", test_aicleaner_core_basic),
        ("AICleanerCore Async", test_aicleaner_core_async),
        ("ServiceHandler Basic", test_service_handler_basic),
        ("ServiceHandler Async", test_service_handler_async),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\nRunning: {test_name}")
        try:
            success, error = run_test_function(test_func)
            if success:
                passed += 1
            else:
                failed += 1
                print(f"✗ {test_name} failed: {error}")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All Phase 4A integration tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())