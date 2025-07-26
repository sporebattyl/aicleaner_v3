"""
Comprehensive Test Suite for Configuration Schema Consolidation
Phase 1A: Configuration Schema Consolidation

This test suite provides comprehensive coverage for the configuration schema
consolidation system following AAA pattern with >95% coverage target.

Test Categories:
- Configuration Schema Validation Tests
- Migration Manager Tests
- Input Sanitization Tests
- Security Validation Tests
- Performance Benchmarking Tests
- Error Handling and Edge Cases
- Component Interface Tests
"""

import pytest
import tempfile
import shutil
import json
import yaml
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Import modules under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config_schema_validator import (
    ConfigSchemaValidator, 
    ValidationResult, 
    ValidationSeverity,
    ValidationIssue,
    ConfigInputSanitizer,
    ConfigSecurityValidator
)
from core.config_migration_manager import (
    ConfigMigrationManager,
    MigrationResult,
    MigrationStage,
    MigrationBackup
)
from core.config_schema import (
    ConfigurationSchemaGenerator,
    UnifiedConfiguration,
    ZoneConfiguration,
    AIEnhancementsSettings
)

class TestConfigSchemaValidator:
    """Test suite for ConfigSchemaValidator following AAA pattern"""
    
    def test_schema_validation_with_valid_config(self):
        """Test schema validation with valid configuration"""
        # Arrange
        valid_config = {
            "display_name": "Test User",
            "gemini_api_key": "test_api_key_123",
            "mqtt": {
                "enabled": False,
                "host": "localhost",
                "port": 1883
            },
            "zones": [{
                "name": "Kitchen",
                "camera_entity": "camera.kitchen",
                "todo_list_entity": "todo.kitchen_tasks"
            }],
            "ai_enhancements": {
                "caching": {
                    "ttl_seconds": 300,
                    "max_cache_entries": 1000
                }
            }
        }
        validator = ConfigSchemaValidator()
        
        # Act
        result = validator.validate(valid_config)
        
        # Assert
        assert isinstance(result, ValidationResult)
        assert result.is_valid
        assert len(result.errors) == 0
        assert result.validation_time_ms < 200  # Performance requirement
    
    def test_schema_validation_with_invalid_api_provider(self):
        """Test schema validation with invalid API provider"""
        # Arrange
        invalid_config = {
            "display_name": "Test User",
            "gemini_api_key": "invalid_key_format",
            "zones": []
        }
        validator = ConfigSchemaValidator()
        
        # Act
        result = validator.validate(invalid_config)
        
        # Assert
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any(error.code == "LIST_TOO_SHORT" for error in result.errors)
        assert any(error.code == "INVALID_API_KEY_FORMAT" for error in result.warnings)
    
    def test_input_sanitization_prevents_injection(self):
        """Test input sanitization prevents injection attacks"""
        # Arrange
        malicious_input = {
            "display_name": "<script>alert('xss')</script>",
            "gemini_api_key": "test_key",
            "zones": [{
                "name": "../../etc/passwd",
                "camera_entity": "javascript:alert('xss')",
                "todo_list_entity": "eval(malicious_code)"
            }]
        }
        sanitizer = ConfigInputSanitizer()
        
        # Act
        sanitized = sanitizer.sanitize(malicious_input)
        injection_issues = sanitizer.detect_injection_attempts(malicious_input)
        
        # Assert
        assert "<script>" not in sanitized["display_name"]
        assert "javascript:" not in sanitized["zones"][0]["camera_entity"]
        assert "eval(" not in sanitized["zones"][0]["todo_list_entity"]
        assert len(injection_issues) > 0
        assert any(issue.code == "INJECTION_DETECTED" for issue in injection_issues)
    
    def test_required_field_validation(self):
        """Test validation of required fields"""
        # Arrange
        incomplete_config = {
            "display_name": "",  # Empty required field
            "zones": []  # Empty required list
        }
        validator = ConfigSchemaValidator()
        
        # Act
        result = validator.validate(incomplete_config)
        
        # Assert
        assert not result.is_valid
        assert any(error.code == "REQUIRED_FIELD_MISSING" for error in result.errors)
        assert any(error.code == "LIST_TOO_SHORT" for error in result.errors)
    
    def test_type_validation_errors(self):
        """Test type validation error detection"""
        # Arrange
        invalid_types_config = {
            "display_name": 123,  # Should be string
            "gemini_api_key": "test_key",
            "mqtt": {
                "enabled": "true",  # Should be boolean
                "port": "1883"  # Should be integer
            },
            "zones": "not_a_list"  # Should be list
        }
        validator = ConfigSchemaValidator()
        
        # Act
        result = validator.validate(invalid_types_config)
        
        # Assert
        assert not result.is_valid
        assert any(error.code == "INVALID_TYPE" for error in result.errors)
        assert len([e for e in result.errors if e.code == "INVALID_TYPE"]) >= 3
    
    def test_numeric_range_validation(self):
        """Test numeric range validation"""
        # Arrange
        out_of_range_config = {
            "display_name": "Test",
            "gemini_api_key": "test_key",
            "mqtt": {
                "port": 70000  # Out of valid port range
            },
            "ai_enhancements": {
                "caching": {
                    "ttl_seconds": 30,  # Below minimum
                    "max_cache_entries": 50000  # Above maximum
                }
            },
            "zones": [{
                "name": "Test",
                "camera_entity": "camera.test",
                "todo_list_entity": "todo.test"
            }]
        }
        validator = ConfigSchemaValidator()
        
        # Act
        result = validator.validate(out_of_range_config)
        
        # Assert
        assert not result.is_valid or len(result.warnings) > 0
        assert any(
            issue.code in ["VALUE_TOO_HIGH", "VALUE_TOO_LOW"] 
            for issue in result.errors + result.warnings
        )
    
    def test_entity_id_format_validation(self):
        """Test Home Assistant entity ID format validation"""
        # Arrange
        invalid_entities_config = {
            "display_name": "Test",
            "gemini_api_key": "test_key",
            "zones": [{
                "name": "Test",
                "camera_entity": "invalid-entity-format",
                "todo_list_entity": "123invalid"
            }]
        }
        validator = ConfigSchemaValidator()
        
        # Act
        result = validator.validate(invalid_entities_config)
        
        # Assert
        assert len(result.warnings) > 0
        assert any(warning.code == "INVALID_ENTITY_FORMAT" for warning in result.warnings)
    
    def test_performance_settings_validation(self):
        """Test performance settings validation"""
        # Arrange
        performance_config = {
            "display_name": "Test",
            "gemini_api_key": "test_key",
            "ai_enhancements": {
                "caching": {
                    "ttl_seconds": 30,  # Very low TTL
                    "max_cache_entries": 15000  # High cache entries
                },
                "local_llm": {
                    "enabled": True,
                    "resource_limits": {
                        "max_memory_usage": 16384  # Very high memory
                    }
                }
            },
            "zones": [{
                "name": "Test",
                "camera_entity": "camera.test",
                "todo_list_entity": "todo.test"
            }]
        }
        validator = ConfigSchemaValidator()
        
        # Act
        result = validator.validate(performance_config)
        
        # Assert
        assert len(result.warnings) > 0
        assert any(warning.code in ["LOW_CACHE_TTL", "HIGH_CACHE_ENTRIES", "HIGH_MEMORY_LIMIT"] for warning in result.warnings)
    
    def test_validation_performance_benchmark(self):
        """Test validation performance meets requirements"""
        # Arrange
        large_config = {
            "display_name": "Performance Test",
            "gemini_api_key": "test_key",
            "ai_enhancements": {
                "caching": {"ttl_seconds": 300},
                "scene_understanding_settings": {"max_objects_detected": 10},
                "predictive_analytics_settings": {"history_days": 30}
            },
            "zones": [
                {
                    "name": f"Zone{i}",
                    "camera_entity": f"camera.zone{i}",
                    "todo_list_entity": f"todo.zone{i}"
                }
                for i in range(100)  # Large number of zones
            ]
        }
        validator = ConfigSchemaValidator()
        
        # Act
        start_time = time.time()
        result = validator.validate(large_config)
        validation_time = (time.time() - start_time) * 1000
        
        # Assert
        assert validation_time < 200  # Must be under 200ms
        assert result.validation_time_ms < 200
        assert result.performance_metrics["performance_acceptable"]

class TestConfigSecurityValidator:
    """Test suite for ConfigSecurityValidator"""
    
    def test_api_key_validation(self):
        """Test API key validation"""
        # Arrange
        security_validator = ConfigSecurityValidator()
        
        test_cases = [
            ("", "MISSING_API_KEY"),
            ("YOUR_GEMINI_API_KEY", "PLACEHOLDER_API_KEY"),
            ("AIzaSyExampleKeyReplaceMeWithYourKey", "PLACEHOLDER_API_KEY"),
            ("invalid_format", "INVALID_API_KEY_FORMAT"),
            ("AIzaSyValidKeyFormat123", None)  # Valid key
        ]
        
        for api_key, expected_error in test_cases:
            # Act
            issues = security_validator._validate_api_key(api_key)
            
            # Assert
            if expected_error:
                assert any(issue.code == expected_error for issue in issues)
            else:
                assert len(issues) == 0
    
    def test_sensitive_data_encryption(self):
        """Test sensitive data encryption"""
        # Arrange
        security_validator = ConfigSecurityValidator()
        config_data = {
            "gemini_api_key": "secret_key_123",
            "mqtt": {"password": "secret_password"},
            "ha_token": "secret_token"
        }
        
        # Act
        encrypted_config = security_validator.encrypt_sensitive_data(config_data)
        
        # Assert
        assert encrypted_config["gemini_api_key"] != "secret_key_123"
        assert encrypted_config["mqtt"]["password"] != "secret_password"
        assert encrypted_config["ha_token"] != "secret_token"
        assert len(encrypted_config["gemini_api_key"]) > 0

class TestConfigMigrationManager:
    """Test suite for ConfigMigrationManager"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.base_path = Path(self.temp_dir)
        
        # Create test configuration files
        self.config_files = {
            "config.yaml": {
                "display_name": "Test User",
                "gemini_api_key": "test_key",
                "zones": [{
                    "name": "Kitchen",
                    "camera_entity": "camera.kitchen",
                    "todo_list_entity": "todo.kitchen"
                }]
            },
            "config.json": {
                "name": "AICleaner v3",
                "version": "3.0.0",
                "slug": "aicleaner_v3",
                "options": {
                    "display_name": "AI Cleaner",
                    "gemini_api_key": "AIzaSyExample"
                },
                "schema": {
                    "display_name": "str",
                    "gemini_api_key": "str"
                }
            }
        }
        
        # Write test files
        for filename, content in self.config_files.items():
            file_path = self.base_path / filename
            if filename.endswith('.json'):
                with open(file_path, 'w') as f:
                    json.dump(content, f)
            else:
                with open(file_path, 'w') as f:
                    yaml.dump(content, f)
    
    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_migration_backup_creation(self):
        """Test migration backup creation"""
        # Arrange
        migration_manager = ConfigMigrationManager(str(self.base_path))
        
        # Act
        backup = migration_manager._create_backup()
        
        # Assert
        assert backup is not None
        assert backup.backup_dir.exists()
        assert len(backup.original_files) > 0
        assert backup.checksum is not None
        assert backup.stage == MigrationStage.BACKUP_CREATED
    
    def test_configuration_merge(self):
        """Test configuration merging"""
        # Arrange
        migration_manager = ConfigMigrationManager(str(self.base_path))
        
        # Act
        merged_config = migration_manager._merge_configurations()
        
        # Assert
        assert merged_config is not None
        assert "display_name" in merged_config
        assert "gemini_api_key" in merged_config
        assert "zones" in merged_config
    
    def test_migration_with_validation_failure(self):
        """Test migration behavior with validation failure"""
        # Arrange
        # Create invalid configuration
        invalid_config = self.base_path / "config.yaml"
        with open(invalid_config, 'w') as f:
            yaml.dump({"invalid": "config"}, f)
        
        migration_manager = ConfigMigrationManager(str(self.base_path))
        
        # Act
        result = migration_manager.migrate_configuration()
        
        # Assert
        assert not result.success
        assert result.stage == MigrationStage.FAILED
        assert result.validation_result is not None
        assert not result.validation_result.is_valid
    
    def test_rollback_functionality(self):
        """Test rollback functionality"""
        # Arrange
        migration_manager = ConfigMigrationManager(str(self.base_path))
        
        # Create backup first
        backup = migration_manager._create_backup()
        assert backup is not None
        
        # Modify original files
        config_file = self.base_path / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump({"modified": "config"}, f)
        
        # Act
        rollback_result = migration_manager.rollback_migration(backup)
        
        # Assert
        assert rollback_result.success
        assert rollback_result.stage == MigrationStage.ROLLBACK_COMPLETE
        
        # Verify original content restored
        with open(config_file, 'r') as f:
            restored_config = yaml.safe_load(f)
        assert restored_config["display_name"] == "Test User"
    
    def test_backup_integrity_verification(self):
        """Test backup integrity verification"""
        # Arrange
        migration_manager = ConfigMigrationManager(str(self.base_path))
        backup = migration_manager._create_backup()
        
        # Act - Verify valid backup
        integrity_valid = migration_manager._verify_backup_integrity(backup)
        
        # Corrupt backup
        backup_file = list(backup.backup_dir.glob("*.yaml"))[0]
        backup_file.write_text("corrupted content")
        
        integrity_invalid = migration_manager._verify_backup_integrity(backup)
        
        # Assert
        assert integrity_valid is True
        assert integrity_invalid is False
    
    def test_migration_performance_requirements(self):
        """Test migration performance meets requirements"""
        # Arrange
        migration_manager = ConfigMigrationManager(str(self.base_path))
        
        # Act
        start_time = time.time()
        result = migration_manager.migrate_configuration()
        migration_time = (time.time() - start_time) * 1000
        
        # Assert
        assert migration_time < 5000  # Must be under 5 seconds
        assert result.migration_time_ms < 5000

class TestConfigurationSchemaGenerator:
    """Test suite for ConfigurationSchemaGenerator"""
    
    def test_addon_schema_generation(self):
        """Test Home Assistant addon schema generation"""
        # Arrange
        generator = ConfigurationSchemaGenerator()
        
        # Act
        schema = generator.generate_addon_schema()
        
        # Assert
        assert "name" in schema
        assert "version" in schema
        assert "slug" in schema
        assert "options" in schema
        assert "schema" in schema
        assert schema["homeassistant_api"] is True
        assert schema["hassio_api"] is True
    
    def test_default_options_generation(self):
        """Test default options generation"""
        # Arrange
        generator = ConfigurationSchemaGenerator()
        
        # Act
        options = generator.generate_default_options()
        
        # Assert
        assert "display_name" in options
        assert "gemini_api_key" in options
        assert "mqtt" in options
        assert "ai_enhancements" in options
        assert "zones" in options
        assert isinstance(options["zones"], list)
    
    def test_validation_schema_generation(self):
        """Test validation schema generation"""
        # Arrange
        generator = ConfigurationSchemaGenerator()
        
        # Act
        schema = generator.generate_validation_schema()
        
        # Assert
        assert "display_name" in schema
        assert schema["display_name"] == "str"
        assert "zones" in schema
        assert isinstance(schema["zones"], list)
        assert "mqtt" in schema
        assert isinstance(schema["mqtt"], dict)

class TestErrorHandlingAndEdgeCases:
    """Test suite for error handling and edge cases"""
    
    def test_empty_configuration_handling(self):
        """Test handling of empty configuration"""
        # Arrange
        validator = ConfigSchemaValidator()
        
        # Act
        result = validator.validate({})
        
        # Assert
        assert not result.is_valid
        assert len(result.errors) > 0
    
    def test_null_values_handling(self):
        """Test handling of null values"""
        # Arrange
        validator = ConfigSchemaValidator()
        config_with_nulls = {
            "display_name": None,
            "gemini_api_key": None,
            "zones": None
        }
        
        # Act
        result = validator.validate(config_with_nulls)
        
        # Assert
        assert not result.is_valid
        assert any(error.code == "REQUIRED_FIELD_MISSING" for error in result.errors)
    
    def test_deeply_nested_configuration(self):
        """Test handling of deeply nested configuration"""
        # Arrange
        validator = ConfigSchemaValidator()
        deep_config = {
            "display_name": "Test",
            "gemini_api_key": "test_key",
            "ai_enhancements": {
                "local_llm": {
                    "preferred_models": {
                        "vision": "model1",
                        "text": "model2"
                    },
                    "resource_limits": {
                        "max_memory_usage": 2048
                    }
                }
            },
            "zones": [{
                "name": "Test",
                "camera_entity": "camera.test",
                "todo_list_entity": "todo.test"
            }]
        }
        
        # Act
        result = validator.validate(deep_config)
        
        # Assert
        assert result.is_valid
        assert result.validation_time_ms < 200
    
    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters"""
        # Arrange
        validator = ConfigSchemaValidator()
        unicode_config = {
            "display_name": "Tëst Üsêr 🏠",
            "gemini_api_key": "test_key",
            "zones": [{
                "name": "Küche",
                "camera_entity": "camera.küche",
                "todo_list_entity": "todo.küche_tasks"
            }]
        }
        
        # Act
        result = validator.validate(unicode_config)
        
        # Assert
        assert result.is_valid
        assert result.validation_time_ms < 200

class TestIntegrationScenarios:
    """Integration test scenarios"""
    
    def test_end_to_end_migration_and_validation(self):
        """Test complete end-to-end migration and validation"""
        # Arrange
        temp_dir = tempfile.mkdtemp()
        base_path = Path(temp_dir)
        
        try:
            # Create test files
            config_yaml = base_path / "config.yaml"
            config_json = base_path / "config.json"
            
            with open(config_yaml, 'w') as f:
                yaml.dump({
                    "display_name": "Test User",
                    "gemini_api_key": "test_key",
                    "zones": [{
                        "name": "Kitchen",
                        "camera_entity": "camera.kitchen",
                        "todo_list_entity": "todo.kitchen"
                    }]
                }, f)
            
            with open(config_json, 'w') as f:
                json.dump({
                    "name": "AICleaner v3",
                    "version": "3.0.0",
                    "options": {
                        "display_name": "AI Cleaner"
                    }
                }, f)
            
            # Act
            migration_manager = ConfigMigrationManager(str(base_path))
            migration_result = migration_manager.migrate_configuration()
            
            # Assert
            assert migration_result.success
            assert migration_result.validation_result.is_valid
            assert migration_result.backup is not None
            
            # Verify unified config exists
            unified_config_path = base_path / "config.yaml"
            assert unified_config_path.exists()
            
        finally:
            shutil.rmtree(temp_dir)

# Performance benchmarking tests
class TestPerformanceBenchmarks:
    """Performance benchmarking tests"""
    
    def test_validation_performance_target(self):
        """Test validation meets performance targets"""
        # Arrange
        validator = ConfigSchemaValidator()
        config = {
            "display_name": "Performance Test",
            "gemini_api_key": "test_key",
            "zones": [{"name": f"Zone{i}", "camera_entity": f"camera.zone{i}", "todo_list_entity": f"todo.zone{i}"} for i in range(10)]
        }
        
        # Act
        results = []
        for _ in range(10):
            start_time = time.time()
            result = validator.validate(config)
            elapsed = (time.time() - start_time) * 1000
            results.append(elapsed)
        
        # Assert
        avg_time = sum(results) / len(results)
        assert avg_time < 200  # Average must be under 200ms
        assert max(results) < 500  # No single validation over 500ms
    
    def test_migration_performance_target(self):
        """Test migration meets performance targets"""
        # Arrange
        temp_dir = tempfile.mkdtemp()
        base_path = Path(temp_dir)
        
        try:
            # Create test files
            for i in range(3):
                config_file = base_path / f"config{i}.yaml"
                with open(config_file, 'w') as f:
                    yaml.dump({"test": f"data{i}"}, f)
            
            # Act
            migration_manager = ConfigMigrationManager(str(base_path))
            start_time = time.time()
            result = migration_manager.migrate_configuration()
            elapsed = (time.time() - start_time) * 1000
            
            # Assert
            assert elapsed < 5000  # Must be under 5 seconds
            
        finally:
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=core", "--cov-report=html", "--cov-report=term-missing", "--cov-fail-under=95"])