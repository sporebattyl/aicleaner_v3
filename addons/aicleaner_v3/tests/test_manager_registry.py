"""
Tests for ManagerRegistry singleton pattern
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch

from utils.manager_registry import (
    ManagerRegistry, 
    ManagerNames, 
    ManagerRegistryContext,
    get_registry,
    get_manager,
    register_manager
)


class MockManager:
    """Mock manager for testing"""
    def __init__(self, name: str = "test"):
        self.name = name
        self.initialized_at = time.time()
        self.shutdown_called = False
    
    def get_status(self):
        return {"name": self.name, "initialized_at": self.initialized_at}
    
    def shutdown(self):
        self.shutdown_called = True


def test_manager_registry_singleton():
    """Test that ManagerRegistry is a true singleton"""
    registry1 = ManagerRegistry()
    registry2 = ManagerRegistry()
    
    assert registry1 is registry2
    assert id(registry1) == id(registry2)


def test_manager_registration_and_retrieval():
    """Test basic manager registration and retrieval"""
    with ManagerRegistryContext() as registry:
        mock_manager = MockManager("test_manager")
        
        # Register manager
        registry.register_manager("test", mock_manager)
        
        # Retrieve manager
        retrieved = registry.get_manager("test")
        assert retrieved is mock_manager
        assert retrieved.name == "test_manager"


def test_get_or_create_manager():
    """Test get_or_create_manager functionality"""
    with ManagerRegistryContext() as registry:
        # First call should create the manager
        manager1 = registry.get_or_create_manager("test", MockManager, "first")
        assert manager1.name == "first"
        
        # Second call should return the same instance
        manager2 = registry.get_or_create_manager("test", MockManager, "second")
        assert manager2 is manager1
        assert manager2.name == "first"  # Should still be the original


def test_thread_safety():
    """Test thread safety of the registry"""
    with ManagerRegistryContext() as registry:
        results = []
        
        def create_manager(thread_id):
            manager = registry.get_or_create_manager("shared", MockManager, f"thread_{thread_id}")
            results.append((thread_id, manager))
        
        # Create multiple threads that try to create the same manager
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_manager, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All threads should have gotten the same manager instance
        managers = [result[1] for result in results]
        first_manager = managers[0]
        
        for manager in managers[1:]:
            assert manager is first_manager
        
        # Only one manager should exist
        assert len(registry.get_all_managers()) == 1


def test_manager_names_constants():
    """Test that ManagerNames constants are properly defined"""
    expected_names = [
        "TIERED_CONFIG",
        "HEALTH_MONITOR", 
        "SECURITY_PRESETS",
        "CONFIGURATION",
        "SECURITY_VALIDATOR",
        "AI_PROVIDER",
        "MQTT_ADAPTER",
        "ZONE_MANAGER",
        "DEVICE_MANAGER"
    ]
    
    for name in expected_names:
        assert hasattr(ManagerNames, name)
        assert isinstance(getattr(ManagerNames, name), ManagerNames)


def test_manager_status():
    """Test manager status reporting"""
    with ManagerRegistryContext() as registry:
        registry.set_addon_root("/test/path")
        
        # Register a few managers
        manager1 = MockManager("manager1")
        manager2 = MockManager("manager2")
        
        registry.register_manager("test1", manager1)
        registry.register_manager("test2", manager2)
        
        status = registry.get_manager_status()
        
        assert status["total_managers"] == 2
        assert "test1" in status["manager_names"]
        assert "test2" in status["manager_names"]
        assert status["addon_root"] == "/test/path"
        assert status["registry_initialized"] is True
        
        # Check individual manager details
        assert "test1" in status["managers"]
        assert "test2" in status["managers"]
        assert status["managers"]["test1"]["type"] == "MockManager"


def test_unregister_manager():
    """Test manager unregistration"""
    with ManagerRegistryContext() as registry:
        mock_manager = MockManager("test")
        
        # Register and verify
        registry.register_manager("test", mock_manager)
        assert registry.get_manager("test") is mock_manager
        
        # Unregister and verify
        result = registry.unregister_manager("test")
        assert result is True
        assert registry.get_manager("test") is None
        
        # Try to unregister non-existent manager
        result = registry.unregister_manager("nonexistent")
        assert result is False


def test_convenience_functions():
    """Test convenience functions work with singleton"""
    with ManagerRegistryContext():
        mock_manager = MockManager("convenience_test")
        
        # Test register_manager convenience function
        register_manager("test", mock_manager)
        
        # Test get_manager convenience function
        retrieved = get_manager("test")
        assert retrieved is mock_manager
        
        # Test get_registry convenience function
        registry = get_registry()
        assert isinstance(registry, ManagerRegistry)


def test_manager_replacement_warning():
    """Test that replacing a manager logs a warning"""
    with ManagerRegistryContext() as registry:
        manager1 = MockManager("first")
        manager2 = MockManager("second")
        
        registry.register_manager("test", manager1)
        
        with patch('utils.manager_registry.logger') as mock_logger:
            registry.register_manager("test", manager2)
            mock_logger.warning.assert_called_once()
        
        # Should now have the second manager
        retrieved = registry.get_manager("test")
        assert retrieved is manager2
        assert retrieved.name == "second"


def test_context_manager():
    """Test ManagerRegistryContext for testing"""
    registry = get_registry()
    
    # Add a manager outside context
    original_manager = MockManager("original")
    registry.register_manager("original", original_manager)
    
    with ManagerRegistryContext() as test_registry:
        # Should be clean inside context
        assert len(test_registry.get_all_managers()) == 0
        
        # Add a test manager
        test_manager = MockManager("test")
        test_registry.register_manager("test", test_manager)
        assert len(test_registry.get_all_managers()) == 1
    
    # Original manager should be restored
    assert registry.get_manager("original") is original_manager
    assert registry.get_manager("test") is None


def test_shutdown_functionality():
    """Test manager shutdown functionality"""
    with ManagerRegistryContext() as registry:
        # Create managers with shutdown capabilities
        manager1 = MockManager("manager1")
        manager2 = MockManager("manager2")
        
        registry.register_manager("test1", manager1)
        registry.register_manager("test2", manager2)
        
        # Verify managers are registered
        assert len(registry.get_all_managers()) == 2
        assert not manager1.shutdown_called
        assert not manager2.shutdown_called
        
        # Shutdown all managers
        registry.shutdown_all_managers()
        
        # Verify shutdown was called and managers were cleared
        assert manager1.shutdown_called
        assert manager2.shutdown_called
        assert len(registry.get_all_managers()) == 0


def test_enhanced_status_reporting():
    """Test enhanced status reporting with performance metrics"""
    with ManagerRegistryContext() as registry:
        registry.set_addon_root("/test/path")
        
        manager = MockManager("enhanced_test")
        registry.register_manager("test", manager)
        
        status = registry.get_manager_status()
        
        # Check enhanced status fields
        assert "timestamp" in status
        assert "memory_usage" in status
        assert status["memory_usage"] > 0
        
        # Check enhanced manager details
        manager_detail = status["managers"]["test"]
        assert "memory_address" in manager_detail
        assert "creation_time" in manager_detail
        assert "status_call_duration_ms" in manager_detail
        assert manager_detail["memory_address"].startswith("0x")


if __name__ == "__main__":
    pytest.main([__file__])