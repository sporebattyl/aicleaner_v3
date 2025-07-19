#!/usr/bin/env python3
"""
MQTT discovery syntax validation tests.
Tests that don't require external dependencies.
"""

import sys
import ast
import importlib.util
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def validate_python_syntax(file_path):
    """Validate Python syntax for a file."""
    try:
        with open(file_path, 'r') as f:
            source = f.read()
        
        # Check syntax
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def run_mqtt_syntax_tests():
    """Run MQTT discovery syntax validation tests."""
    print("AICleaner v3 Phase 4B MQTT Discovery Syntax Validation")
    print("=" * 70)
    
    # Test files to validate
    mqtt_discovery_dir = project_root / "mqtt_discovery"
    test_files = [
        mqtt_discovery_dir / "__init__.py",
        mqtt_discovery_dir / "config.py",
        mqtt_discovery_dir / "models.py",
        mqtt_discovery_dir / "client.py",
        mqtt_discovery_dir / "state_manager.py",
        mqtt_discovery_dir / "entity_registrar.py",
        mqtt_discovery_dir / "message_handler.py",
        mqtt_discovery_dir / "discovery_manager.py",
    ]
    
    results = []
    
    for test_file in test_files:
        if not test_file.exists():
            results.append({
                "file": test_file.name,
                "syntax_valid": False,
                "error": "File not found"
            })
            continue
        
        # Validate syntax
        syntax_valid, syntax_error = validate_python_syntax(test_file)
        
        results.append({
            "file": test_file.name,
            "syntax_valid": syntax_valid,
            "syntax_error": syntax_error,
            "path": str(test_file)
        })
    
    # Print results
    passed = 0
    failed = 0
    
    for result in results:
        if result["syntax_valid"]:
            print(f"✅ {result['file']}: PASS")
            passed += 1
        else:
            print(f"❌ {result['file']}: FAIL - {result.get('syntax_error', result.get('error'))}")
            failed += 1
    
    print(f"\nSummary: {passed} passed, {failed} failed")
    
    # Test basic functionality
    print("\n" + "=" * 70)
    print("Basic Functionality Tests")
    print("=" * 70)
    
    # Test imports (without actually importing to avoid dependency issues)
    test_imports = [
        ("mqtt_discovery.config", "MQTTConfig"),
        ("mqtt_discovery.models", "MQTTEntity"),
        ("mqtt_discovery.models", "MQTTDevice"),
        ("mqtt_discovery.client", "MQTTClient"),
        ("mqtt_discovery.state_manager", "StateManager"),
        ("mqtt_discovery.entity_registrar", "EntityRegistrar"),
        ("mqtt_discovery.message_handler", "MessageHandler"),
        ("mqtt_discovery.discovery_manager", "MQTTDiscoveryManager"),
    ]
    
    for module_name, class_name in test_imports:
        try:
            # Just check if the file exists and has the class
            module_path = project_root / (module_name.replace(".", "/") + ".py")
            if module_path.exists():
                with open(module_path, 'r') as f:
                    content = f.read()
                if f"class {class_name}" in content:
                    print(f"✅ {module_name}.{class_name}: Class found")
                    passed += 1
                else:
                    print(f"❌ {module_name}.{class_name}: Class not found")
                    failed += 1
            else:
                print(f"❌ {module_name}: Module file not found")
                failed += 1
        except Exception as e:
            print(f"❌ {module_name}: {e}")
            failed += 1
    
    # Test configuration functionality
    try:
        from mqtt_discovery.config import MQTTConfig
        config = MQTTConfig()
        
        # Test default values
        assert config.BROKER_ADDRESS == "localhost"
        assert config.BROKER_PORT == 1883
        assert config.DISCOVERY_PREFIX == "homeassistant"
        assert config.QOS == 1
        
        print(f"✅ MQTTConfig: Default configuration values correct")
        passed += 1
    except Exception as e:
        print(f"❌ MQTTConfig: {e}")
        failed += 1
    
    # Test data models
    try:
        from mqtt_discovery.models import MQTTEntity, MQTTDevice
        
        # Test MQTTEntity
        entity = MQTTEntity(
            unique_id="test_entity",
            component="sensor",
            config_payload={"name": "Test Sensor"},
            state_topic="test/topic"
        )
        assert entity.unique_id == "test_entity"
        assert entity.component == "sensor"
        assert entity.state_topic == "test/topic"
        
        # Test MQTTDevice
        device = MQTTDevice(
            identifiers=["device_123"],
            name="Test Device",
            model="Test Model",
            manufacturer="Test Manufacturer"
        )
        assert device.identifiers == ["device_123"]
        assert device.name == "Test Device"
        assert len(device.entities) == 0
        
        print(f"✅ MQTT Models: Data classes work correctly")
        passed += 1
    except Exception as e:
        print(f"❌ MQTT Models: {e}")
        failed += 1
    
    print(f"\nTotal Summary: {passed} passed, {failed} failed")
    
    # Test requirements.txt update
    requirements_path = project_root / "requirements.txt"
    if requirements_path.exists():
        with open(requirements_path, 'r') as f:
            requirements_content = f.read()
        
        if "aio-mqtt" in requirements_content:
            print(f"✅ Requirements: aio-mqtt dependency added")
            passed += 1
        else:
            print(f"❌ Requirements: aio-mqtt dependency missing")
            failed += 1
    else:
        print(f"❌ Requirements: requirements.txt not found")
        failed += 1
    
    print(f"\nFinal Summary: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run_mqtt_syntax_tests()
    sys.exit(0 if success else 1)