"""
Test suite for Configuration Validator
Following TDD and AAA (Arrange, Act, Assert) principles
"""

import pytest
from utils.config_validator import ConfigValidator, ValidationResult, ValidationLevel


class TestConfigValidator:
    """Test suite for ConfigValidator class"""

    @pytest.fixture
    def valid_config(self) -> dict:
        """Arrange: Valid configuration for testing"""
        return {
            "ha_url": "http://homeassistant.local:8123",
            "ha_token": "test_token",
            "analysis_workers": 2,
            "max_concurrent_analyses": 3,
            "ai_enhancements": {
                "advanced_scene_understanding": True,
                "predictive_analytics": True,
                "model_selection": {
                    "detailed_analysis": "gemini-pro",
                    "complex_reasoning": "claude-sonnet",
                    "simple_analysis": "gemini-flash"
                },
                "caching": {
                    "enabled": True,
                    "intermediate_caching": True,
                    "ttl_seconds": 300,
                    "max_cache_entries": 1000
                },
                "scene_understanding_settings": {
                    "max_objects_detected": 10,
                    "max_generated_tasks": 8,
                    "confidence_threshold": 0.7,
                    "enable_seasonal_adjustments": True,
                    "enable_time_context": True
                },
                "predictive_analytics_settings": {
                    "history_days": 30,
                    "prediction_horizon_hours": 24,
                    "min_data_points": 5,
                    "enable_urgency_scoring": True,
                    "enable_pattern_detection": True
                },
                "multi_model_ai": {
                    "enable_fallback": True,
                    "max_retries": 3,
                    "timeout_seconds": 30,
                    "performance_tracking": True
                }
            },
            "zones": [
                {
                    "name": "Living Room",
                    "camera_entity": "camera.living_room",
                    "todo_list_entity": "todo.living_room",
                    "purpose": "Living room for relaxation"
                }
            ]
        }

    @pytest.fixture
    def invalid_config(self) -> dict:
        """Arrange: Invalid configuration for testing"""
        return {
            # Missing required fields
            "ai_enhancements": {
                "advanced_scene_understanding": "not_a_boolean",  # Invalid type
                "model_selection": {
                    "detailed_analysis": "invalid_model"  # Invalid model
                },
                "caching": {
                    "ttl_seconds": 50  # Too low
                },
                "scene_understanding_settings": {
                    "confidence_threshold": 1.5  # Out of range
                },
                "predictive_analytics_settings": {
                    "history_days": 400  # Too high
                },
                "multi_model_ai": {
                    "max_retries": 15  # Too high
                }
            },
            "zones": []  # Empty zones
        }

    def test_valid_configuration_passes(self, valid_config):
        """
        Test that a valid configuration passes validation
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        validator = ConfigValidator(valid_config)

        # Act
        result = validator.validate_full_config()

        # Assert
        assert result.is_valid
        assert len(result.errors) == 0
        assert isinstance(result.get_summary(), dict)

    def test_invalid_configuration_fails(self, invalid_config):
        """
        Test that an invalid configuration fails validation
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        validator = ConfigValidator(invalid_config)

        # Act
        result = validator.validate_full_config()

        # Assert
        assert not result.is_valid
        assert len(result.errors) > 0
        
        # Check for specific errors
        error_messages = " ".join(result.errors)
        assert "Missing required core setting: ha_url" in error_messages
        assert "Missing required core setting: ha_token" in error_messages
        assert "No zones configured" in error_messages

    def test_missing_ai_enhancements_section(self):
        """
        Test validation with missing ai_enhancements section
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        config = {
            "ha_url": "http://test.local",
            "ha_token": "test_token",
            "zones": [
                {
                    "name": "Test Zone",
                    "camera_entity": "camera.test",
                    "todo_list_entity": "todo.test",
                    "purpose": "Test purpose"
                }
            ]
        }
        validator = ConfigValidator(config)

        # Act
        result = validator.validate_full_config()

        # Assert
        assert result.is_valid  # Should be valid with warnings
        assert len(result.warnings) > 0
        warning_messages = " ".join(result.warnings)
        assert "ai_enhancements section is missing" in warning_messages

    def test_feature_toggle_validation(self):
        """
        Test feature toggle validation
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        config = {
            "ha_url": "http://test.local",
            "ha_token": "test_token",
            "ai_enhancements": {
                "advanced_scene_understanding": "not_boolean",  # Invalid
                "predictive_analytics": True  # Valid
            },
            "zones": [{"name": "Test", "camera_entity": "cam", "todo_list_entity": "todo", "purpose": "test"}]
        }
        validator = ConfigValidator(config)

        # Act
        result = validator.validate_full_config()

        # Assert
        assert not result.is_valid
        error_messages = " ".join(result.errors)
        assert "Feature toggle 'advanced_scene_understanding' must be a boolean" in error_messages

    def test_model_selection_validation(self):
        """
        Test model selection validation
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        config = {
            "ha_url": "http://test.local",
            "ha_token": "test_token",
            "ai_enhancements": {
                "model_selection": {
                    "detailed_analysis": "invalid_model",
                    "complex_reasoning": "claude-sonnet"  # Valid
                }
            },
            "zones": [{"name": "Test", "camera_entity": "cam", "todo_list_entity": "todo", "purpose": "test"}]
        }
        validator = ConfigValidator(config)

        # Act
        result = validator.validate_full_config()

        # Assert
        assert not result.is_valid
        error_messages = " ".join(result.errors)
        assert "Invalid model 'invalid_model'" in error_messages

    def test_caching_configuration_validation(self):
        """
        Test caching configuration validation
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        config = {
            "ha_url": "http://test.local",
            "ha_token": "test_token",
            "ai_enhancements": {
                "caching": {
                    "enabled": "not_boolean",  # Invalid
                    "ttl_seconds": 50,  # Too low
                    "max_cache_entries": 50  # Too low
                }
            },
            "zones": [{"name": "Test", "camera_entity": "cam", "todo_list_entity": "todo", "purpose": "test"}]
        }
        validator = ConfigValidator(config)

        # Act
        result = validator.validate_full_config()

        # Assert
        assert not result.is_valid
        error_messages = " ".join(result.errors)
        warning_messages = " ".join(result.warnings)
        
        assert "Caching setting 'enabled' must be a boolean" in error_messages
        assert "ttl_seconds should be between 60 and 3600" in warning_messages
        assert "max_cache_entries should be between 100 and 10000" in warning_messages

    def test_scene_understanding_validation(self):
        """
        Test scene understanding configuration validation
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        config = {
            "ha_url": "http://test.local",
            "ha_token": "test_token",
            "ai_enhancements": {
                "scene_understanding_settings": {
                    "max_objects_detected": 100,  # Too high
                    "confidence_threshold": 1.5,  # Out of range
                    "enable_seasonal_adjustments": "not_boolean"  # Invalid type
                }
            },
            "zones": [{"name": "Test", "camera_entity": "cam", "todo_list_entity": "todo", "purpose": "test"}]
        }
        validator = ConfigValidator(config)

        # Act
        result = validator.validate_full_config()

        # Assert
        assert not result.is_valid
        error_messages = " ".join(result.errors)
        warning_messages = " ".join(result.warnings)
        
        assert "confidence_threshold must be a number between 0.0 and 1.0" in error_messages
        assert "enable_seasonal_adjustments' must be a boolean" in error_messages
        assert "max_objects_detected should be an integer between 1 and 50" in warning_messages

    def test_zones_validation(self):
        """
        Test zones configuration validation
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        config = {
            "ha_url": "http://test.local",
            "ha_token": "test_token",
            "zones": [
                {
                    "name": "Valid Zone",
                    "camera_entity": "camera.valid",
                    "todo_list_entity": "todo.valid",
                    "purpose": "Valid purpose"
                },
                {
                    "name": "",  # Empty name
                    "camera_entity": "camera.invalid"
                    # Missing required fields
                },
                "not_a_dict"  # Invalid type
            ]
        }
        validator = ConfigValidator(config)

        # Act
        result = validator.validate_full_config()

        # Assert
        assert not result.is_valid
        error_messages = " ".join(result.errors)
        
        assert "Zone 1 field 'name' cannot be empty" in error_messages
        assert "Zone 1 missing required field: todo_list_entity" in error_messages
        assert "Zone 1 missing required field: purpose" in error_messages
        assert "Zone 2 must be a dictionary" in error_messages

    def test_recommendations_generation(self, valid_config):
        """
        Test that recommendations are generated appropriately
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        validator = ConfigValidator(valid_config)

        # Act
        result = validator.validate_full_config()

        # Assert
        assert len(result.recommendations) > 0
        recommendation_messages = " ".join(result.recommendations)
        assert "Caching is enabled - this will improve performance" in recommendation_messages

    def test_validation_result_summary(self, valid_config):
        """
        Test ValidationResult summary functionality
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        validator = ConfigValidator(valid_config)

        # Act
        result = validator.validate_full_config()
        summary = result.get_summary()

        # Assert
        assert isinstance(summary, dict)
        assert "valid" in summary
        assert "error_count" in summary
        assert "warning_count" in summary
        assert "info_count" in summary
        assert "recommendation_count" in summary
        assert "errors" in summary
        assert "warnings" in summary
        assert "info" in summary
        assert "recommendations" in summary

    def test_empty_configuration(self):
        """
        Test validation with completely empty configuration
        AAA Pattern: Arrange, Act, Assert
        """
        # Arrange
        config = {}
        validator = ConfigValidator(config)

        # Act
        result = validator.validate_full_config()

        # Assert
        assert not result.is_valid
        assert len(result.errors) > 0
        error_messages = " ".join(result.errors)
        assert "Missing required core setting: ha_url" in error_messages
        assert "Missing required core setting: ha_token" in error_messages
        assert "No zones configured" in error_messages
