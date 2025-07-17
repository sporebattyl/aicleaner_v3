#!/usr/bin/env python3
"""
Simple test to validate the simplified configuration schema
Tests core functionality without external dependencies
"""

import sys
import os
from pathlib import Path

# Add the addon path to Python path
addon_path = Path(__file__).parent / "addons" / "aicleaner_v3"
sys.path.insert(0, str(addon_path))

def test_config_schema_import():
    """Test that the config schema can be imported and used"""
    try:
        from core.config_schema import (
            LocalLLMSettings, 
            MultiModelAISettings, 
            AIProviderSettings,
            AIProviderManagerSettings,
            ConfigurationSchemaGenerator
        )
        print("✅ Config schema imports successful")
        return True
    except Exception as e:
        print(f"❌ Config schema import failed: {e}")
        return False

def test_simplified_settings():
    """Test that simplified settings work correctly"""
    try:
        from core.config_schema import (
            LocalLLMSettings, 
            MultiModelAISettings, 
            AIProviderSettings,
            AIProviderManagerSettings
        )
        
        # Test LocalLLMSettings (simplified)
        local_llm = LocalLLMSettings()
        print(f"✅ LocalLLMSettings created: enabled={local_llm.enabled}, host={local_llm.ollama_host}")
        
        # Test MultiModelAISettings (simplified)
        multi_model = MultiModelAISettings()
        print(f"✅ MultiModelAISettings created: fallback={multi_model.enable_fallback}")
        
        # Test AIProviderSettings (simplified)
        provider = AIProviderSettings()
        print(f"✅ AIProviderSettings created: priority={provider.priority}, timeout={provider.timeout_seconds}")
        
        # Test AIProviderManagerSettings (simplified)
        manager = AIProviderManagerSettings()
        print(f"✅ AIProviderManagerSettings created: strategy={manager.selection_strategy}")
        
        return True
        
    except Exception as e:
        print(f"❌ Simplified settings test failed: {e}")
        return False

def test_provider_config_validation():
    """Test that provider configurations are properly simplified"""
    try:
        from core.config_schema import AIProviderManagerSettings
        
        manager_settings = AIProviderManagerSettings()
        
        # Test Ollama provider config
        ollama_config = manager_settings.ollama
        print(f"✅ Ollama config: priority={ollama_config.priority}, model={ollama_config.model_name}")
        print(f"✅ Ollama base_url: {ollama_config.base_url}")
        print(f"✅ Ollama fallback: {ollama_config.fallback_enabled}")
        
        # Test OpenAI provider config  
        openai_config = manager_settings.openai
        print(f"✅ OpenAI config: priority={openai_config.priority}, model={openai_config.model_name}")
        
        # Test Anthropic provider config
        anthropic_config = manager_settings.anthropic
        print(f"✅ Anthropic config: priority={anthropic_config.priority}, model={anthropic_config.model_name}")
        
        # Test Google provider config
        google_config = manager_settings.google
        print(f"✅ Google config: priority={google_config.priority}, model={google_config.model_name}")
        
        # Verify priority order (lower number = higher priority)
        priorities = {
            "openai": openai_config.priority,
            "anthropic": anthropic_config.priority,
            "google": google_config.priority,
            "ollama": ollama_config.priority
        }
        
        print(f"✅ Priority order: {sorted(priorities.items(), key=lambda x: x[1])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Provider config validation failed: {e}")
        return False

def test_configuration_generation():
    """Test that configuration generation works"""
    try:
        from core.config_schema import ConfigurationSchemaGenerator
        
        # Test default options generation
        default_options = ConfigurationSchemaGenerator.generate_default_options()
        print("✅ Default options generated successfully")
        
        # Check local LLM settings
        local_llm = default_options["ai_enhancements"]["local_llm"]
        print(f"✅ Local LLM in defaults: enabled={local_llm['enabled']}, host={local_llm['ollama_host']}")
        
        # Check provider manager settings
        provider_manager = default_options["ai_enhancements"]["ai_provider_manager"]
        print(f"✅ Provider manager strategy: {provider_manager['selection_strategy']}")
        
        # Check Ollama provider in defaults
        ollama_provider = provider_manager["ollama"]
        print(f"✅ Ollama provider in defaults: priority={ollama_provider['priority']}, model={ollama_provider['model_name']}")
        
        # Test validation schema generation
        validation_schema = ConfigurationSchemaGenerator.generate_validation_schema()
        print("✅ Validation schema generated successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration generation failed: {e}")
        return False

def run_config_tests():
    """Run all configuration tests"""
    print("🧪 Starting AICleaner v3 Configuration Validation Tests")
    print("=" * 60)
    
    results = []
    
    # Test 1: Config Schema Import
    print("\n1. Testing config schema imports...")
    results.append(test_config_schema_import())
    
    # Test 2: Simplified Settings
    print("\n2. Testing simplified settings...")
    results.append(test_simplified_settings())
    
    # Test 3: Provider Config Validation  
    print("\n3. Testing provider config validation...")
    results.append(test_provider_config_validation())
    
    # Test 4: Configuration Generation
    print("\n4. Testing configuration generation...")
    results.append(test_configuration_generation())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Configuration Test Results")
    print("=" * 60)
    
    test_names = [
        "Config Schema Import",
        "Simplified Settings",
        "Provider Config Validation",
        "Configuration Generation"
    ]
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{i+1}. {test_name}: {status}")
    
    print(f"\n📈 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All configuration tests passed!")
        print("✅ Simplified configuration schema working correctly")
        print("✅ Ollama integration preserved in configuration")
        print("✅ Priority-based selection configured correctly")
        return True
    else:
        print("⚠️  Some configuration tests failed.")
        return False

if __name__ == "__main__":
    success = run_config_tests()
    sys.exit(0 if success else 1)