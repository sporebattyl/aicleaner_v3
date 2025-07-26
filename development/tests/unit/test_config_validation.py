#!/usr/bin/env python3
"""
Unit Tests for Configuration Validation

Tests the configuration validation logic in isolation.
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, Any, List


class TestConfigValidation:
    """Unit tests for configuration validation"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_configs_dir = Path(__file__).parent.parent / "configs"
        
    def validate_provider_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate a single provider configuration"""
        errors = []
        
        # Required fields
        required_fields = ["provider", "enabled", "priority"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
                
        # Provider-specific validation
        provider = config.get("provider", "")
        
        if provider in ["openai", "gemini", "anthropic"] and "api_key" not in config:
            errors.append(f"Missing API key for {provider}")
            
        if provider == "ollama" and "base_url" not in config:
            errors.append("Ollama provider requires base_url")
            
        # Priority validation
        priority = config.get("priority")
        if priority is not None and (not isinstance(priority, int) or priority < 1):
            errors.append("Priority must be a positive integer")
            
        # Timeout validation
        timeout = config.get("timeout")
        if timeout is not None and (not isinstance(timeout, int) or timeout < 1):
            errors.append("Timeout must be a positive integer")
            
        return errors
        
    def validate_full_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate full configuration structure"""
        errors = []
        
        # Check for ai_providers or legacy format
        if "ai_providers" in config:
            # New format validation
            providers = config["ai_providers"]
            if not isinstance(providers, list):
                errors.append("ai_providers must be a list")
                return errors
                
            if len(providers) == 0:
                errors.append("At least one provider must be configured")
                
            # Validate each provider
            priorities = []
            for i, provider in enumerate(providers):
                provider_errors = self.validate_provider_config(provider)
                for error in provider_errors:
                    errors.append(f"Provider {i+1}: {error}")
                    
                # Check for duplicate priorities
                priority = provider.get("priority")
                if priority in priorities:
                    errors.append(f"Duplicate priority {priority} found")
                priorities.append(priority)
                
        elif "ai_model" in config:
            # Legacy format validation
            ai_model = config["ai_model"]
            if not isinstance(ai_model, dict):
                errors.append("ai_model must be a dictionary")
            elif "provider" not in ai_model:
                errors.append("ai_model missing provider field")
                
        else:
            errors.append("Configuration must contain either 'ai_providers' or 'ai_model'")
            
        return errors
        
    def test_valid_basic_config(self):
        """Test validation of valid basic configuration"""
        config_path = self.test_configs_dir / "test_config_basic.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        errors = self.validate_full_config(config)
        assert len(errors) == 0, f"Valid config should have no errors: {errors}"
        
    def test_valid_multi_provider_config(self):
        """Test validation of valid multi-provider configuration"""
        config_path = self.test_configs_dir / "test_config_multi_provider.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        errors = self.validate_full_config(config)
        assert len(errors) == 0, f"Valid config should have no errors: {errors}"
        
    def test_valid_legacy_config(self):
        """Test validation of valid legacy configuration"""
        config_path = self.test_configs_dir / "test_config_legacy.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        errors = self.validate_full_config(config)
        assert len(errors) == 0, f"Valid legacy config should have no errors: {errors}"
        
    def test_invalid_config_missing_required_fields(self):
        """Test validation of configuration missing required fields"""
        invalid_config = {
            "ai_providers": [
                {
                    "provider": "ollama"
                    # Missing enabled and priority
                }
            ]
        }
        
        errors = self.validate_full_config(invalid_config)
        assert len(errors) > 0, "Invalid config should have errors"
        assert any("Missing required field: enabled" in error for error in errors)
        assert any("Missing required field: priority" in error for error in errors)
        
    def test_invalid_provider_missing_api_key(self):
        """Test validation of provider missing required API key"""
        invalid_config = {
            "ai_providers": [
                {
                    "provider": "openai",
                    "enabled": True,
                    "priority": 1
                    # Missing api_key
                }
            ]
        }
        
        errors = self.validate_full_config(invalid_config)
        assert len(errors) > 0, "Invalid config should have errors"
        assert any("Missing API key for openai" in error for error in errors)
        
    def test_invalid_priority_values(self):
        """Test validation of invalid priority values"""
        invalid_configs = [
            # Negative priority
            {
                "ai_providers": [
                    {
                        "provider": "ollama",
                        "enabled": True,
                        "priority": -1,
                        "base_url": "http://localhost:11434"
                    }
                ]
            },
            # Zero priority
            {
                "ai_providers": [
                    {
                        "provider": "ollama", 
                        "enabled": True,
                        "priority": 0,
                        "base_url": "http://localhost:11434"
                    }
                ]
            },
            # Non-integer priority
            {
                "ai_providers": [
                    {
                        "provider": "ollama",
                        "enabled": True,
                        "priority": "high",
                        "base_url": "http://localhost:11434"
                    }
                ]
            }
        ]
        
        for config in invalid_configs:
            errors = self.validate_full_config(config)
            assert len(errors) > 0, f"Invalid priority should cause errors: {config}"
            
    def test_duplicate_priorities(self):
        """Test validation of duplicate priority values"""
        invalid_config = {
            "ai_providers": [
                {
                    "provider": "ollama",
                    "enabled": True,
                    "priority": 1,
                    "base_url": "http://localhost:11434"
                },
                {
                    "provider": "openai",
                    "enabled": True,
                    "priority": 1,  # Duplicate priority
                    "api_key": "test-key"
                }
            ]
        }
        
        errors = self.validate_full_config(invalid_config)
        assert len(errors) > 0, "Duplicate priorities should cause errors"
        assert any("Duplicate priority 1 found" in error for error in errors)
        
    def test_empty_providers_list(self):
        """Test validation of empty providers list"""
        invalid_config = {
            "ai_providers": []
        }
        
        errors = self.validate_full_config(invalid_config)
        assert len(errors) > 0, "Empty providers list should cause errors"
        assert any("At least one provider must be configured" in error for error in errors)
        
    def test_missing_base_url_for_ollama(self):
        """Test validation of Ollama provider missing base_url"""
        invalid_config = {
            "ai_providers": [
                {
                    "provider": "ollama",
                    "enabled": True,
                    "priority": 1
                    # Missing base_url
                }
            ]
        }
        
        errors = self.validate_full_config(invalid_config)
        assert len(errors) > 0, "Ollama without base_url should cause errors"
        assert any("Ollama provider requires base_url" in error for error in errors)


if __name__ == "__main__":
    # Run tests directly if executed as script
    pytest.main([__file__, "-v"])