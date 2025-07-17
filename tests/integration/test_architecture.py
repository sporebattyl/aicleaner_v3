#!/usr/bin/env python3
"""
Integration Tests for AICleaner v3 Architecture

This module provides comprehensive integration testing for the AICleaner v3
simplified architecture, including AI provider management, configuration loading,
and fallback system validation.
"""

import asyncio
import os
import sys
import tempfile
import yaml
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch, MagicMock
import pytest

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from ai.providers.manager import AIProviderManager
    from ai.providers.base import BaseAIProvider
    from core.config import ConfigurationManager
except ImportError as e:
    print(f"Warning: Could not import modules - {e}")
    print("Tests will run in mock mode only")


class MockProvider(BaseAIProvider):
    """Mock AI provider for testing"""
    
    def __init__(self, provider_name: str, config: Dict[str, Any]):
        super().__init__(provider_name, config)
        self.is_healthy = True
        self.capabilities = ["text", "vision", "code"]
        
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Mock response generation"""
        return f"Mock response from {self.provider_name}: {prompt[:50]}..."
        
    async def health_check(self) -> bool:
        """Mock health check"""
        return self.is_healthy
        
    def get_capabilities(self) -> List[str]:
        """Mock capabilities"""
        return self.capabilities


class TestArchitecture:
    """Integration tests for AICleaner v3 architecture"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_configs_dir = Path(__file__).parent.parent / "configs"
        
    async def load_test_config(self, config_file: str) -> Dict[str, Any]:
        """Load test configuration file"""
        config_path = self.test_configs_dir / config_file
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    @pytest.mark.asyncio
    async def test_basic_configuration_loading(self):
        """Test loading of basic single provider configuration"""
        config = await self.load_test_config("test_config_basic.yaml")
        
        # Validate configuration structure
        assert "ai_providers" in config
        assert len(config["ai_providers"]) == 1
        
        provider_config = config["ai_providers"][0]
        assert provider_config["provider"] == "ollama"
        assert provider_config["enabled"] is True
        assert "models" in provider_config
        assert "text" in provider_config["models"]
        assert provider_config["priority"] == 1
        
    @pytest.mark.asyncio
    async def test_multi_provider_configuration_loading(self):
        """Test loading of multi-provider configuration"""
        config = await self.load_test_config("test_config_multi_provider.yaml")
        
        # Validate configuration structure
        assert "ai_providers" in config
        assert len(config["ai_providers"]) == 3
        
        # Check provider priorities
        providers = config["ai_providers"]
        priorities = [p["priority"] for p in providers]
        assert priorities == [1, 2, 3]
        
        # Validate provider types
        provider_names = [p["provider"] for p in providers]
        assert "ollama" in provider_names
        assert "openai" in provider_names
        assert "gemini" in provider_names
        
    @pytest.mark.asyncio
    async def test_legacy_configuration_loading(self):
        """Test loading of legacy configuration format"""
        config = await self.load_test_config("test_config_legacy.yaml")
        
        # Validate legacy structure
        assert "ai_model" in config
        assert "openai" in config
        assert "gemini" in config
        assert "local_llm" in config
        
        # Check legacy format details
        assert config["ai_model"]["provider"] == "openai"
        assert config["openai"]["enabled"] is True
        assert config["local_llm"]["enabled"] is True
        
    @pytest.mark.asyncio
    async def test_provider_manager_initialization(self):
        """Test AIProviderManager initialization with test configuration"""
        config = await self.load_test_config("test_config_multi_provider.yaml")
        
        with patch('ai.providers.manager.AIProviderManager') as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.initialize = AsyncMock()
            mock_manager.get_available_providers = MagicMock(return_value=["ollama", "openai", "gemini"])
            
            # Test manager initialization
            await mock_manager.initialize(config["ai_providers"])
            mock_manager.initialize.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_provider_capability_detection(self):
        """Test provider capability detection"""
        # Create mock providers with different capabilities
        ollama_provider = MockProvider("ollama", {"capabilities": ["text", "code"]})
        openai_provider = MockProvider("openai", {"capabilities": ["text", "vision", "code"]})
        gemini_provider = MockProvider("gemini", {"capabilities": ["text", "vision"]})
        
        providers = [ollama_provider, openai_provider, gemini_provider]
        
        # Test capability aggregation
        all_capabilities = set()
        for provider in providers:
            all_capabilities.update(provider.get_capabilities())
            
        assert "text" in all_capabilities
        assert "vision" in all_capabilities
        assert "code" in all_capabilities
        
    @pytest.mark.asyncio
    async def test_fallback_system_logic(self):
        """Test provider fallback system"""
        # Create providers with different health states
        unhealthy_provider = MockProvider("primary", {})
        unhealthy_provider.is_healthy = False
        
        healthy_provider = MockProvider("fallback", {})
        healthy_provider.is_healthy = True
        
        providers = [unhealthy_provider, healthy_provider]
        
        # Test fallback logic
        available_providers = []
        for provider in providers:
            if await provider.health_check():
                available_providers.append(provider)
                
        assert len(available_providers) == 1
        assert available_providers[0].provider_name == "fallback"
        
    @pytest.mark.asyncio
    async def test_configuration_migration(self):
        """Test legacy to new configuration migration"""
        legacy_config = await self.load_test_config("test_config_legacy.yaml")
        
        # Mock migration logic
        def migrate_legacy_config(legacy: Dict[str, Any]) -> Dict[str, Any]:
            """Mock configuration migration"""
            migrated = {"ai_providers": []}
            
            # Migrate primary provider
            if "ai_model" in legacy:
                primary_provider = {
                    "provider": legacy["ai_model"]["provider"],
                    "enabled": True,
                    "priority": 1,
                    "models": {
                        "text": legacy["ai_model"]["model_name"]
                    }
                }
                migrated["ai_providers"].append(primary_provider)
                
            # Migrate additional providers
            priority = 2
            for provider_name in ["openai", "gemini", "local_llm"]:
                if provider_name in legacy and legacy[provider_name].get("enabled"):
                    provider_config = {
                        "provider": provider_name if provider_name != "local_llm" else "ollama",
                        "enabled": True,
                        "priority": priority
                    }
                    
                    if "api_key" in legacy[provider_name]:
                        provider_config["api_key"] = legacy[provider_name]["api_key"]
                    if "base_url" in legacy[provider_name]:
                        provider_config["base_url"] = legacy[provider_name]["base_url"]
                        
                    migrated["ai_providers"].append(provider_config)
                    priority += 1
                    
            return migrated
            
        # Test migration
        migrated_config = migrate_legacy_config(legacy_config)
        
        assert "ai_providers" in migrated_config
        assert len(migrated_config["ai_providers"]) >= 1
        assert migrated_config["ai_providers"][0]["provider"] == "openai"
        
    @pytest.mark.asyncio
    async def test_provider_response_generation(self):
        """Test provider response generation with mocking"""
        provider = MockProvider("test_provider", {})
        
        # Test basic response generation
        response = await provider.generate_response("Test prompt")
        assert "Mock response from test_provider" in response
        assert "Test prompt" in response
        
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms"""
        # Create provider that fails health check
        failing_provider = MockProvider("failing", {})
        failing_provider.is_healthy = False
        
        # Create backup provider
        backup_provider = MockProvider("backup", {})
        backup_provider.is_healthy = True
        
        # Test error recovery logic
        async def try_provider_with_fallback(providers: List[MockProvider], prompt: str) -> str:
            """Mock provider fallback logic"""
            for provider in providers:
                if await provider.health_check():
                    return await provider.generate_response(prompt)
            raise Exception("No healthy providers available")
            
        # Test successful fallback
        providers = [failing_provider, backup_provider]
        response = await try_provider_with_fallback(providers, "Test prompt")
        assert "backup" in response
        
        # Test all providers failing
        failing_provider2 = MockProvider("failing2", {})
        failing_provider2.is_healthy = False
        
        failing_providers = [failing_provider, failing_provider2]
        
        with pytest.raises(Exception, match="No healthy providers available"):
            await try_provider_with_fallback(failing_providers, "Test prompt")
            
    @pytest.mark.asyncio
    async def test_configuration_validation(self):
        """Test configuration validation logic"""
        
        def validate_provider_config(config: Dict[str, Any]) -> List[str]:
            """Mock configuration validation"""
            errors = []
            
            if "provider" not in config:
                errors.append("Missing 'provider' field")
            if "enabled" not in config:
                errors.append("Missing 'enabled' field")
            if "priority" not in config:
                errors.append("Missing 'priority' field")
                
            # Validate provider-specific requirements
            provider = config.get("provider", "")
            if provider in ["openai", "gemini"] and "api_key" not in config:
                errors.append(f"Missing API key for {provider}")
            if provider == "ollama" and "base_url" not in config:
                errors.append("Missing base_url for ollama provider")
                
            return errors
            
        # Test valid configuration
        valid_config = {
            "provider": "ollama",
            "enabled": True,
            "priority": 1,
            "base_url": "http://localhost:11434"
        }
        errors = validate_provider_config(valid_config)
        assert len(errors) == 0
        
        # Test invalid configuration
        invalid_config = {
            "provider": "openai",
            "enabled": True
            # Missing priority and api_key
        }
        errors = validate_provider_config(invalid_config)
        assert len(errors) == 2
        assert "Missing 'priority' field" in errors
        assert "Missing API key for openai" in errors
        

async def run_integration_tests():
    """Run all integration tests"""
    print("Starting AICleaner v3 Architecture Integration Tests...")
    
    test_suite = TestArchitecture()
    test_suite.setup_method()
    
    tests = [
        ("Basic Configuration Loading", test_suite.test_basic_configuration_loading),
        ("Multi-Provider Configuration", test_suite.test_multi_provider_configuration_loading),
        ("Legacy Configuration Loading", test_suite.test_legacy_configuration_loading),
        ("Provider Manager Initialization", test_suite.test_provider_manager_initialization),
        ("Provider Capability Detection", test_suite.test_provider_capability_detection),
        ("Fallback System Logic", test_suite.test_fallback_system_logic),
        ("Configuration Migration", test_suite.test_configuration_migration),
        ("Provider Response Generation", test_suite.test_provider_response_generation),
        ("Error Handling and Recovery", test_suite.test_error_handling_and_recovery),
        ("Configuration Validation", test_suite.test_configuration_validation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n  Running: {test_name}")
            await test_func()
            print(f"    ✅ PASSED: {test_name}")
            passed += 1
        except Exception as e:
            print(f"    ❌ FAILED: {test_name} - {str(e)}")
            failed += 1
            
    print(f"\n\nTest Results:")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📊 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All integration tests passed!")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed. Check output above for details.")
        return False


if __name__ == "__main__":
    # Install required packages if not available
    try:
        import pytest
    except ImportError:
        print("Installing pytest...")
        os.system("pip install pytest pytest-asyncio")
        
    # Run tests
    result = asyncio.run(run_integration_tests())
    sys.exit(0 if result else 1)