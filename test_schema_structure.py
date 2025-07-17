#!/usr/bin/env python3
"""
Direct test of the configuration schema structure
Tests the actual schema file directly without dependencies
"""

import sys
from pathlib import Path

def test_schema_file_structure():
    """Test that the config schema file has the expected structure"""
    try:
        schema_path = Path(__file__).parent / "addons" / "aicleaner_v3" / "core" / "config_schema.py"
        
        if not schema_path.exists():
            print(f"❌ Schema file not found at: {schema_path}")
            return False
        
        with open(schema_path, 'r') as f:
            content = f.read()
        
        # Check for simplified classes
        expected_classes = [
            "class LocalLLMSettings:",
            "class MultiModelAISettings:",
            "class AIProviderSettings:",
            "class AIProviderManagerSettings:",
            "class ConfigurationSchemaGenerator:"
        ]
        
        for class_name in expected_classes:
            if class_name in content:
                print(f"✅ Found {class_name}")
            else:
                print(f"❌ Missing {class_name}")
                return False
        
        # Check for simplified LocalLLMSettings
        if 'enabled: bool = True' in content and 'ollama_host: str = "localhost:11434"' in content:
            print("✅ LocalLLMSettings simplified correctly")
        else:
            print("❌ LocalLLMSettings not simplified")
            return False
        
        # Check for priority-based selection
        if 'selection_strategy: str = "priority"' in content:
            print("✅ Priority-based selection configured")
        else:
            print("❌ Priority-based selection not configured")
            return False
        
        # Check for removal of complex features
        removed_features = [
            "performance_tracking",
            "enable_cost_tracking",
            "enable_health_monitoring",
            "enable_performance_optimization",
            "rate_limit_rpm",
            "rate_limit_tpm",
            "daily_budget",
            "cost_per_request",
            "health_check_interval",
            "connection_pool_size"
        ]
        
        removed_count = 0
        for feature in removed_features:
            if feature not in content:
                removed_count += 1
        
        if removed_count >= len(removed_features) * 0.8:  # At least 80% removed
            print(f"✅ Removed {removed_count}/{len(removed_features)} complex features")
        else:
            print(f"❌ Only removed {removed_count}/{len(removed_features)} complex features")
            return False
        
        # Check for preserved essential features
        essential_features = [
            "enabled",
            "priority",
            "model_name",
            "timeout_seconds",
            "max_retries",
            "fallback_enabled",
            "ollama_host",
            "auto_download",
            "enable_fallback"
        ]
        
        preserved_count = 0
        for feature in essential_features:
            if feature in content:
                preserved_count += 1
        
        if preserved_count >= len(essential_features) * 0.9:  # At least 90% preserved
            print(f"✅ Preserved {preserved_count}/{len(essential_features)} essential features")
        else:
            print(f"❌ Only preserved {preserved_count}/{len(essential_features)} essential features")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Schema file structure test failed: {e}")
        return False

def test_provider_priorities():
    """Test provider priority configuration"""
    try:
        schema_path = Path(__file__).parent / "addons" / "aicleaner_v3" / "core" / "config_schema.py"
        
        with open(schema_path, 'r') as f:
            content = f.read()
        
        # Check for correct priority order
        priorities = {
            "openai": "priority=1",
            "anthropic": "priority=2", 
            "google": "priority=3",
            "ollama": "priority=4"
        }
        
        for provider, priority_text in priorities.items():
            if priority_text in content:
                print(f"✅ {provider} has correct priority")
            else:
                print(f"❌ {provider} priority not found or incorrect")
                return False
        
        # Check for Ollama specific configuration
        ollama_checks = [
            'model_name="llava:13b"',
            'base_url="http://localhost:11434"',
            'timeout_seconds=60'
        ]
        
        for check in ollama_checks:
            if check in content:
                print(f"✅ Ollama config: {check}")
            else:
                print(f"❌ Ollama config missing: {check}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Provider priorities test failed: {e}")
        return False

def test_validation_schema():
    """Test validation schema simplification"""
    try:
        schema_path = Path(__file__).parent / "addons" / "aicleaner_v3" / "core" / "config_schema.py"
        
        with open(schema_path, 'r') as f:
            content = f.read()
        
        # Check for validation schema method
        if "def generate_validation_schema()" in content:
            print("✅ Validation schema generator found")
        else:
            print("❌ Validation schema generator not found")
            return False
        
        # Check for simplified validation rules
        if '"selection_strategy": "list(priority)?"' in content:
            print("✅ Validation limited to priority selection")
        else:
            print("❌ Validation not limited to priority selection")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Validation schema test failed: {e}")
        return False

def run_schema_tests():
    """Run all schema structure tests"""
    print("🧪 Starting AICleaner v3 Schema Structure Tests")
    print("=" * 55)
    
    results = []
    
    # Test 1: Schema File Structure
    print("\n1. Testing schema file structure...")
    results.append(test_schema_file_structure())
    
    # Test 2: Provider Priorities
    print("\n2. Testing provider priorities...")
    results.append(test_provider_priorities())
    
    # Test 3: Validation Schema
    print("\n3. Testing validation schema...")
    results.append(test_validation_schema())
    
    # Summary
    print("\n" + "=" * 55)
    print("📊 Schema Structure Test Results")
    print("=" * 55)
    
    test_names = [
        "Schema File Structure",
        "Provider Priorities",
        "Validation Schema"
    ]
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{i+1}. {test_name}: {status}")
    
    print(f"\n📈 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All schema structure tests passed!")
        print("✅ Configuration schema simplified successfully")
        print("✅ Ollama priority configuration preserved")
        print("✅ Essential features maintained")
        print("✅ Complex features removed")
        return True
    else:
        print("⚠️  Some schema structure tests failed.")
        return False

if __name__ == "__main__":
    success = run_schema_tests()
    sys.exit(0 if success else 1)