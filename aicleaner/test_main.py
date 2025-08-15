#!/usr/bin/env python3
"""
Simple test script to verify main application functionality
without requiring external dependencies.
"""

import sys
import asyncio
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all main components can be imported."""
    try:
        # Test configuration components
        from src.config.loader import ConfigurationLoader
        from src.config.schema import AICleanerConfig
        print("✓ Configuration components imported successfully")
        
        # Test core components
        from src.core.orchestrator import AICleanerOrchestrator
        from src.core.health import HealthMonitor
        print("✓ Core components imported successfully")
        
        # Test provider components
        from src.providers.base_provider import LLMProvider
        from src.providers.gemini_provider import GeminiProvider
        print("✓ Provider components imported successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        return False

def test_config_loading():
    """Test configuration loading with defaults."""
    try:
        from src.config.loader import ConfigurationLoader
        
        # Test async config loading in sync context
        async def load_config():
            loader = ConfigurationLoader()
            config = await loader.load_config()
            return config
            
        config = asyncio.run(load_config())
        print(f"✓ Configuration loaded with {len(config.provider_priority)} providers")
        print(f"  - Privacy level: {config.processing.privacy_level}")
        print(f"  - Batch size: {config.processing.batch_size}")
        print(f"  - Health check interval: {config.health.check_interval}s")
        return True
        
    except Exception as e:
        print(f"✗ Config loading test failed: {e}")
        return False

def test_orchestrator_creation():
    """Test orchestrator creation without initialization."""
    try:
        from src.core.orchestrator import AICleanerOrchestrator
        from src.config.loader import ConfigurationLoader
        
        loader = ConfigurationLoader()
        orchestrator = AICleanerOrchestrator(loader)
        print("✓ Orchestrator created successfully")
        print(f"  - Stats initialized: {orchestrator.stats.total_images == 0}")
        print(f"  - Provider registry: {len(orchestrator.provider_registry.providers)} providers")
        return True
        
    except Exception as e:
        print(f"✗ Orchestrator creation test failed: {e}")
        return False

def test_health_monitor():
    """Test health monitor creation."""
    try:
        from src.core.health import HealthMonitor
        from src.config.loader import ConfigurationLoader
        
        async def create_monitor():
            loader = ConfigurationLoader()
            config = await loader.load_config()
            monitor = HealthMonitor(config)
            return monitor
            
        monitor = asyncio.run(create_monitor())
        print("✓ Health monitor created successfully")
        print(f"  - Check interval: {monitor.health_config.check_interval}s")
        print(f"  - Max failures: {monitor.health_config.max_failures}")
        print(f"  - Timeout: {monitor.health_config.timeout}s")
        return True
        
    except Exception as e:
        print(f"✗ Health monitor test failed: {e}")
        return False

def test_main_app_structure():
    """Test main application structure without external dependencies."""
    try:
        # Mock the external dependencies
        import sys
        from unittest.mock import MagicMock
        
        # Mock aiohttp
        sys.modules['aiohttp'] = MagicMock()
        sys.modules['aiohttp.web'] = MagicMock()
        sys.modules['aiohttp.web_request'] = MagicMock()
        sys.modules['aiohttp.web_response'] = MagicMock()
        
        # Mock paho-mqtt
        sys.modules['paho'] = MagicMock()
        sys.modules['paho.mqtt'] = MagicMock()
        sys.modules['paho.mqtt.client'] = MagicMock()
        sys.modules['paho.mqtt.enums'] = MagicMock()
        
        # Now try to import the main components
        from src.main import AICleanerApp, DirectoryWatcher, WebAPI, AppStats
        
        print("✓ Main application components imported successfully")
        print("  - AICleanerApp: Main application coordinator")
        print("  - DirectoryWatcher: Automatic directory monitoring")
        print("  - WebAPI: REST API for Home Assistant integration")
        print("  - AppStats: Runtime statistics tracking")
        
        # Test app creation
        app = AICleanerApp()
        print("✓ AICleanerApp instance created successfully")
        print(f"  - Initialization flag: {app._initialized}")
        print(f"  - Watch directories: {len(app.directory_watcher.watched_directories)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Main app structure test failed: {e}")
        return False

def run_all_tests():
    """Run all tests."""
    print("AI Cleaner Main Application Tests")
    print("=" * 40)
    
    tests = [
        ("Component Imports", test_imports),
        ("Configuration Loading", test_config_loading),  
        ("Orchestrator Creation", test_orchestrator_creation),
        ("Health Monitor", test_health_monitor),
        ("Main App Structure", test_main_app_structure),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"  Failed: {test_name}")
            
    print(f"\n{'=' * 40}")
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Main application is ready for deployment.")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)