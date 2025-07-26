"""
Tests for Configuration Versioning System
"""

import os
import json
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from utils.config_versioning import ConfigVersioning
from utils.config_integration_helper import ConfigIntegrationHelper


class TestConfigVersioning:
    """Test the ConfigVersioning class."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def config_versioning(self, temp_config_dir):
        """Create a ConfigVersioning instance for testing."""
        return ConfigVersioning(config_base_dir=temp_config_dir, max_versions=3)

    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing."""
        return {
            "ai_providers": {
                "openai": {"api_key": "test-key"},
                "anthropic": {"api_key": "test-key-2"}
            },
            "zones": {
                "living_room": {"devices": ["vacuum_1"]},
                "kitchen": {"devices": ["vacuum_2"]}
            }
        }

    def test_init_creates_versions_directory(self, temp_config_dir):
        """Test that initialization creates the versions directory."""
        versioning = ConfigVersioning(config_base_dir=temp_config_dir)
        versions_dir = os.path.join(temp_config_dir, 'config_versions')
        assert os.path.exists(versions_dir)
        assert os.path.isdir(versions_dir)

    def test_init_with_invalid_base_dir_raises_error(self):
        """Test that initialization with invalid base directory raises ValueError."""
        with pytest.raises(ValueError, match="Configuration base directory does not exist"):
            ConfigVersioning(config_base_dir="/nonexistent/directory")

    def test_save_version_creates_file(self, config_versioning, sample_config):
        """Test that save_version creates a properly formatted file."""
        with patch('utils.config_versioning.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 1, 18, 14, 30, 0)
            mock_datetime.now().strftime.return_value = "20250118143000"
            
            filepath = config_versioning.save_version(sample_config)
            
            assert filepath is not None
            assert os.path.exists(filepath)
            assert filepath.endswith("config_20250118143000.json")
            
            # Verify file contents
            with open(filepath, 'r') as f:
                saved_config = json.load(f)
            assert saved_config == sample_config

    def test_save_version_handles_json_error(self, config_versioning):
        """Test that save_version handles JSON serialization errors gracefully."""
        # Create a config with non-serializable data
        invalid_config = {"function": lambda x: x}
        
        filepath = config_versioning.save_version(invalid_config)
        assert filepath is None

    def test_list_versions_returns_sorted_files(self, config_versioning, sample_config):
        """Test that list_versions returns files sorted from newest to oldest."""
        # Save multiple versions with mocked timestamps
        timestamps = ["20250118140000", "20250118143000", "20250118141500"]
        
        for timestamp in timestamps:
            with patch('utils.config_versioning.datetime') as mock_datetime:
                mock_datetime.now().strftime.return_value = timestamp
                config_versioning.save_version(sample_config)
        
        versions = config_versioning.list_versions()
        
        assert len(versions) == 3
        # Should be sorted newest first
        assert versions[0] == "config_20250118143000.json"
        assert versions[1] == "config_20250118141500.json"
        assert versions[2] == "config_20250118140000.json"

    def test_list_versions_handles_missing_directory(self, temp_config_dir):
        """Test that list_versions handles missing versions directory gracefully."""
        # Create versioning instance but remove the directory
        versioning = ConfigVersioning(config_base_dir=temp_config_dir)
        os.rmdir(versioning.versions_dir)
        
        versions = versioning.list_versions()
        assert versions == []

    def test_get_version_retrieves_correct_config(self, config_versioning, sample_config):
        """Test that get_version retrieves the correct configuration."""
        with patch('utils.config_versioning.datetime') as mock_datetime:
            mock_datetime.now().strftime.return_value = "20250118143000"
            config_versioning.save_version(sample_config)
        
        retrieved_config = config_versioning.get_version("config_20250118143000.json")
        assert retrieved_config == sample_config

    def test_get_version_returns_none_for_missing_file(self, config_versioning):
        """Test that get_version returns None for missing files."""
        result = config_versioning.get_version("nonexistent_config.json")
        assert result is None

    def test_get_version_security_check(self, config_versioning):
        """Test that get_version prevents path traversal attacks."""
        result = config_versioning.get_version("../../../etc/passwd")
        assert result is None
        
        result = config_versioning.get_version("config/../secret.json")
        assert result is None

    def test_get_version_handles_invalid_json(self, config_versioning, temp_config_dir):
        """Test that get_version handles invalid JSON gracefully."""
        # Create a file with invalid JSON
        invalid_file = os.path.join(config_versioning.versions_dir, "config_invalid.json")
        with open(invalid_file, 'w') as f:
            f.write("{ invalid json")
        
        result = config_versioning.get_version("config_invalid.json")
        assert result is None

    def test_get_latest_version(self, config_versioning, sample_config):
        """Test that get_latest_version returns the most recent version."""
        # Save multiple versions
        config1 = {"version": 1}
        config2 = {"version": 2}
        
        with patch('utils.config_versioning.datetime') as mock_datetime:
            mock_datetime.now().strftime.return_value = "20250118140000"
            config_versioning.save_version(config1)
            
            mock_datetime.now().strftime.return_value = "20250118143000"
            config_versioning.save_version(config2)
        
        latest = config_versioning.get_latest_version()
        assert latest == config2

    def test_get_latest_version_no_versions(self, config_versioning):
        """Test that get_latest_version returns None when no versions exist."""
        result = config_versioning.get_latest_version()
        assert result is None

    def test_cleanup_versions_removes_old_files(self, config_versioning, sample_config):
        """Test that cleanup removes old versions when max_versions is exceeded."""
        # Create 5 versions (max is 3)
        timestamps = ["20250118140000", "20250118141000", "20250118142000", 
                     "20250118143000", "20250118144000"]
        
        for timestamp in timestamps:
            with patch('utils.config_versioning.datetime') as mock_datetime:
                mock_datetime.now().strftime.return_value = timestamp
                config_versioning.save_version(sample_config)
        
        versions = config_versioning.list_versions()
        
        # Should only keep the 3 newest versions
        assert len(versions) == 3
        assert "config_20250118144000.json" in versions
        assert "config_20250118143000.json" in versions
        assert "config_20250118142000.json" in versions
        assert "config_20250118141000.json" not in versions
        assert "config_20250118140000.json" not in versions


class TestConfigIntegrationHelper:
    """Test the ConfigIntegrationHelper class."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def temp_options_file(self, temp_data_dir):
        """Create a temporary options file."""
        options_file = os.path.join(temp_data_dir, "options.json")
        initial_config = {
            "ai_providers": {
                "openai": {"api_key": "initial-key"}
            }
        }
        with open(options_file, 'w') as f:
            json.dump(initial_config, f)
        return options_file

    @pytest.fixture
    def integration_helper(self, temp_data_dir, temp_options_file):
        """Create a ConfigIntegrationHelper instance for testing."""
        return ConfigIntegrationHelper(
            config_base_dir=temp_data_dir,
            options_file_path=temp_options_file
        )

    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing."""
        return {
            "ai_providers": {
                "openai": {"api_key": "test-key"},
                "anthropic": {"api_key": "test-key-2"}
            },
            "zones": {
                "living_room": {"devices": ["vacuum_1"]}
            }
        }

    def test_update_configuration_success(self, integration_helper, sample_config):
        """Test successful configuration update."""
        with patch.object(integration_helper.config_manager, 'validate_configuration', return_value=True):
            result = integration_helper.update_configuration(sample_config)
            
            assert result["status"] == "success"
            assert result["restart_required"] is True
            assert "successfully" in result["message"].lower()

    def test_update_configuration_validation_failure(self, integration_helper, sample_config):
        """Test configuration update with validation failure."""
        with patch.object(integration_helper.config_manager, 'validate_configuration', return_value=False):
            with patch.object(integration_helper.config_manager, 'get_validation_errors', 
                             return_value=["Invalid API key format"]):
                result = integration_helper.update_configuration(sample_config)
                
                assert result["status"] == "error"
                assert "validation failed" in result["message"].lower()
                assert result["errors"] == ["Invalid API key format"]

    def test_rollback_configuration_to_latest(self, integration_helper, sample_config, temp_options_file):
        """Test rollback to latest configuration."""
        # Set up a backup version
        backup_config = {"version": "backup"}
        integration_helper.versioning_manager.save_version(backup_config)
        
        with patch.object(integration_helper.config_manager, 'validate_configuration', return_value=True):
            result = integration_helper.rollback_configuration()
            
            assert result["status"] == "success"
            assert "latest backup" in result["message"]
            assert result["restart_required"] is True

    def test_rollback_configuration_to_specific_version(self, integration_helper, sample_config):
        """Test rollback to specific version."""
        backup_config = {"version": "specific"}
        
        with patch.object(integration_helper.versioning_manager, 'get_version', 
                         return_value=backup_config):
            with patch.object(integration_helper.config_manager, 'validate_configuration', 
                             return_value=True):
                result = integration_helper.rollback_configuration("config_20250118143000.json")
                
                assert result["status"] == "success"
                assert "config_20250118143000.json" in result["message"]

    def test_rollback_configuration_no_backups(self, integration_helper):
        """Test rollback when no backups are available."""
        result = integration_helper.rollback_configuration()
        
        assert result["status"] == "error"
        assert "no configuration backups" in result["message"].lower()

    def test_rollback_configuration_validation_failure(self, integration_helper):
        """Test rollback when backup configuration is invalid."""
        backup_config = {"invalid": "config"}
        
        with patch.object(integration_helper.versioning_manager, 'get_latest_version', 
                         return_value=backup_config):
            with patch.object(integration_helper.config_manager, 'validate_configuration', 
                             return_value=False):
                with patch.object(integration_helper.config_manager, 'get_validation_errors', 
                                 return_value=["Configuration format changed"]):
                    result = integration_helper.rollback_configuration()
                    
                    assert result["status"] == "error"
                    assert "no longer valid" in result["message"]
                    assert result["errors"] == ["Configuration format changed"]

    def test_list_configuration_versions(self, integration_helper, sample_config):
        """Test listing configuration versions with metadata."""
        # Create some test versions
        with patch('utils.config_versioning.datetime') as mock_datetime:
            mock_datetime.now().strftime.return_value = "20250118143000"
            integration_helper.versioning_manager.save_version(sample_config)
        
        versions = integration_helper.list_configuration_versions()
        
        assert len(versions) >= 1
        version = versions[0]
        assert "filename" in version
        assert "timestamp" in version
        assert "formatted_date" in version
        assert "is_latest" in version
        assert version["filename"] == "config_20250118143000.json"

    def test_get_configuration_status(self, integration_helper, temp_options_file):
        """Test getting configuration status."""
        status = integration_helper.get_configuration_status()
        
        assert "current_config_valid" in status
        assert "current_config_loaded" in status
        assert "available_backups" in status
        assert "latest_backup" in status
        assert "validation_errors" in status

    def test_get_configuration_status_with_invalid_current_config(self, integration_helper):
        """Test status when current configuration is invalid."""
        with patch.object(integration_helper.config_manager, 'validate_configuration', 
                         return_value=False):
            with patch.object(integration_helper.config_manager, 'get_validation_errors', 
                             return_value=["Invalid format"]):
                status = integration_helper.get_configuration_status()
                
                assert status["current_config_valid"] is False
                assert status["validation_errors"] == ["Invalid format"]