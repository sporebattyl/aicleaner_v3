"""
Tests for configuration management API endpoints
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from datetime import datetime

from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.v1.endpoints.config import router
from utils.configuration_manager import ConfigurationManager


@pytest.fixture
def app():
    """Create FastAPI app with config router for testing"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_config_manager():
    """Mock configuration manager for testing"""
    with patch('api.v1.endpoints.config.get_manager') as mock_get_manager:
        mock_manager = Mock(spec=ConfigurationManager)
        mock_get_manager.return_value = mock_manager
        yield mock_manager


@pytest.fixture
def mock_current_user():
    """Mock authenticated user with all permissions"""
    return {
        "key_config": {
            "name": "test_key",
            "permissions": {
                "read_config": True,
                "write_config": True,
                "control_managers": True,
                "system_control": True,
                "view_metrics": True
            }
        },
        "permissions": Mock(
            read_config=True,
            write_config=True,
            control_managers=True,
            system_control=True,
            view_metrics=True
        ),
        "key_name": "test_key"
    }


@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    return {
        "mqtt": {
            "broker_address": "localhost",
            "broker_port": 1883,
            "use_tls": False,
            "username": "test_user",
            "password": "test_pass"
        },
        "ai": {
            "providers": ["openai", "anthropic"],
            "default_provider": "openai",
            "rate_limits": {
                "requests_per_minute": 60
            }
        },
        "security": {
            "level": "balanced",
            "encrypt_configs": True,
            "require_tls": False
        },
        "api": {
            "keys": {},
            "rate_limits": {
                "default": "60/minute"
            }
        }
    }


class TestGetConfigurationEndpoint:
    """Test configuration retrieval endpoint"""
    
    @patch('api.v1.endpoints.config.get_current_user')
    def test_get_configuration_json_format(self, mock_auth, client, mock_config_manager, mock_current_user, sample_config):
        """Test getting configuration in JSON format"""
        mock_auth.return_value = mock_current_user
        mock_config_manager.load_configuration.return_value = sample_config
        
        response = client.get("/config")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["format"] == "json"
        assert data["config"] == sample_config
        assert "timestamp" in data
    
    @patch('api.v1.endpoints.config.get_current_user')
    @patch('api.v1.endpoints.config.yaml.dump')
    def test_get_configuration_yaml_format(self, mock_yaml_dump, mock_auth, client, mock_config_manager, mock_current_user, sample_config):
        """Test getting configuration in YAML format"""
        mock_auth.return_value = mock_current_user
        mock_config_manager.load_configuration.return_value = sample_config
        mock_yaml_dump.return_value = "mqtt:\n  broker_address: localhost\n"
        
        response = client.get("/config?format=yaml")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["format"] == "yaml"
        assert isinstance(data["config"], str)
        assert "timestamp" in data
        mock_yaml_dump.assert_called_once_with(sample_config, default_flow_style=False, sort_keys=False)
    
    @patch('api.v1.endpoints.config.get_current_user')
    def test_get_configuration_manager_unavailable(self, mock_auth, client, mock_current_user):
        """Test getting configuration when manager is unavailable"""
        mock_auth.return_value = mock_current_user
        
        with patch('api.v1.endpoints.config.get_manager', return_value=None):
            response = client.get("/config")
            
            assert response.status_code == 500
            assert "Configuration manager not available" in response.json()["detail"]


class TestUpdateConfigurationEndpoint:
    """Test configuration update endpoint"""
    
    @patch('api.v1.endpoints.config.get_current_user')
    @patch('api.v1.endpoints.config._create_config_backup')
    def test_update_configuration_success(self, mock_backup, mock_auth, client, mock_config_manager, mock_current_user, sample_config):
        """Test successful configuration update"""
        mock_auth.return_value = mock_current_user
        mock_config_manager.load_configuration.return_value = sample_config
        mock_config_manager.validate_configuration.return_value = True
        mock_config_manager.save_configuration.return_value = True
        mock_backup.return_value = "/tmp/backup_123.json"
        
        update_request = {
            "config": sample_config,
            "backup_current": True,
            "validate_first": True
        }
        
        response = client.put("/config", json=update_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "successfully" in data["message"]
        assert data["backup_location"] == "/tmp/backup_123.json"
        assert data["validation_results"]["valid"] is True
        
        # Verify manager methods were called
        mock_config_manager.validate_configuration.assert_called_once_with(sample_config)
        mock_config_manager.save_configuration.assert_called_once_with(sample_config)
    
    @patch('api.v1.endpoints.config.get_current_user')
    def test_update_configuration_validation_failed(self, mock_auth, client, mock_config_manager, mock_current_user, sample_config):
        """Test configuration update with validation failure"""
        mock_auth.return_value = mock_current_user
        mock_config_manager.validate_configuration.return_value = False
        mock_config_manager.get_validation_errors.return_value = ["Invalid broker address", "Missing required field"]
        
        update_request = {
            "config": sample_config,
            "backup_current": False,
            "validate_first": True
        }
        
        response = client.put("/config", json=update_request)
        
        assert response.status_code == 400
        assert "Configuration validation failed" in response.json()["detail"]
        assert "Invalid broker address" in response.json()["detail"]
    
    @patch('api.v1.endpoints.config.get_current_user')
    @patch('api.v1.endpoints.config._create_config_backup')
    @patch('api.v1.endpoints.config._restore_config_backup')
    def test_update_configuration_save_failed_with_restore(self, mock_restore, mock_backup, mock_auth, client, mock_config_manager, mock_current_user, sample_config):
        """Test configuration update with save failure and backup restore"""
        mock_auth.return_value = mock_current_user
        mock_config_manager.load_configuration.return_value = sample_config
        mock_config_manager.validate_configuration.return_value = True
        mock_config_manager.save_configuration.side_effect = Exception("Save failed")
        mock_backup.return_value = "/tmp/backup_123.json"
        
        update_request = {
            "config": sample_config,
            "backup_current": True,
            "validate_first": True
        }
        
        response = client.put("/config", json=update_request)
        
        assert response.status_code == 500
        assert "Failed to save configuration" in response.json()["detail"]
        
        # Verify backup restore was attempted
        mock_restore.assert_called_once_with("/tmp/backup_123.json")


class TestValidateConfigurationEndpoint:
    """Test configuration validation endpoint"""
    
    @patch('api.v1.endpoints.config.get_current_user')
    @patch('api.v1.endpoints.config._generate_config_warnings')
    @patch('api.v1.endpoints.config._assess_security_impact')
    def test_validate_configuration_success(self, mock_security, mock_warnings, mock_auth, client, mock_config_manager, mock_current_user, sample_config):
        """Test successful configuration validation"""
        mock_auth.return_value = mock_current_user
        mock_config_manager.validate_configuration.return_value = True
        mock_config_manager.get_validation_errors.return_value = []
        mock_warnings.return_value = ["TLS disabled warning"]
        mock_security.return_value = {"level": "medium", "changes": ["TLS disabled"]}
        
        validation_request = {
            "config": sample_config,
            "strict": True
        }
        
        response = client.post("/config/_validate", json=validation_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert len(data["errors"]) == 0
        assert data["warnings"] == ["TLS disabled warning"]
        assert data["security_impact"]["level"] == "medium"
        assert "timestamp" in data
    
    @patch('api.v1.endpoints.config.get_current_user')
    def test_validate_configuration_with_errors(self, mock_auth, client, mock_config_manager, mock_current_user, sample_config):
        """Test configuration validation with errors"""
        mock_auth.return_value = mock_current_user
        mock_config_manager.validate_configuration.return_value = False
        mock_config_manager.get_validation_errors.return_value = ["Invalid port number", "Missing broker address"]
        
        validation_request = {
            "config": sample_config,
            "strict": False
        }
        
        response = client.post("/config/_validate", json=validation_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False
        assert "Invalid port number" in data["errors"]
        assert "Missing broker address" in data["errors"]


class TestConfigurationSchemaEndpoint:
    """Test configuration schema endpoint"""
    
    @patch('api.v1.endpoints.config.get_current_user')
    def test_get_configuration_schema(self, mock_auth, client, mock_current_user):
        """Test getting configuration schema"""
        mock_auth.return_value = mock_current_user
        
        response = client.get("/config/schema")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "schema" in data
        assert "version" in data
        assert "timestamp" in data
        
        schema = data["schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "mqtt" in schema["properties"]
        assert "ai" in schema["properties"]
        assert "security" in schema["properties"]


class TestConfigurationTemplatesEndpoint:
    """Test configuration templates endpoint"""
    
    @patch('api.v1.endpoints.config.get_current_user')
    def test_get_all_templates(self, mock_auth, client, mock_current_user):
        """Test getting all configuration templates"""
        mock_auth.return_value = mock_current_user
        
        response = client.get("/config/templates")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "templates" in data
        assert "available" in data
        assert "timestamp" in data
        
        templates = data["templates"]
        assert "minimal" in templates
        assert "production" in templates
        assert "development" in templates
        
        # Check template structure
        minimal_template = templates["minimal"]
        assert "description" in minimal_template
        assert "config" in minimal_template
        assert "mqtt" in minimal_template["config"]
    
    @patch('api.v1.endpoints.config.get_current_user')
    def test_get_specific_template(self, mock_auth, client, mock_current_user):
        """Test getting a specific configuration template"""
        mock_auth.return_value = mock_current_user
        
        response = client.get("/config/templates?template_name=production")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "template" in data
        assert "name" in data
        assert data["name"] == "production"
        
        template = data["template"]
        assert "description" in template
        assert "config" in template
        assert template["config"]["security"]["level"] == "paranoid"
    
    @patch('api.v1.endpoints.config.get_current_user')
    def test_get_nonexistent_template(self, mock_auth, client, mock_current_user):
        """Test getting a non-existent template"""
        mock_auth.return_value = mock_current_user
        
        response = client.get("/config/templates?template_name=nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestConfigurationBackupsEndpoint:
    """Test configuration backups endpoint"""
    
    @patch('api.v1.endpoints.config.get_current_user')
    @patch('api.v1.endpoints.config.Path')
    def test_list_backups_success(self, mock_path, mock_auth, client, mock_current_user):
        """Test listing configuration backups"""
        mock_auth.return_value = mock_current_user
        
        # Mock backup directory and files
        mock_backup_dir = Mock()
        mock_backup_dir.exists.return_value = True
        
        mock_file1 = Mock()
        mock_file1.name = "config_backup_20231201_120000.json"
        mock_file1.stat.return_value = Mock(st_size=1024, st_ctime=1701432000, st_mtime=1701432000)
        
        mock_file2 = Mock()
        mock_file2.name = "config_backup_20231130_100000.json"
        mock_file2.stat.return_value = Mock(st_size=2048, st_ctime=1701345600, st_mtime=1701345600)
        
        mock_backup_dir.glob.return_value = [mock_file1, mock_file2]
        mock_path.return_value = mock_backup_dir
        
        response = client.get("/config/backups")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "backups" in data
        assert "total" in data
        assert data["total"] == 2
        
        backups = data["backups"]
        assert len(backups) == 2
        
        # Check backup details
        backup1 = backups[0]  # Should be newest first
        assert backup1["filename"] == "config_backup_20231201_120000.json"
        assert backup1["size_bytes"] == 1024
        assert "created_at" in backup1
    
    @patch('api.v1.endpoints.config.get_current_user')
    @patch('api.v1.endpoints.config.Path')
    def test_list_backups_no_directory(self, mock_path, mock_auth, client, mock_current_user):
        """Test listing backups when directory doesn't exist"""
        mock_auth.return_value = mock_current_user
        
        mock_backup_dir = Mock()
        mock_backup_dir.exists.return_value = False
        mock_path.return_value = mock_backup_dir
        
        response = client.get("/config/backups")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["backups"] == []
        assert data["total"] == 0


class TestConfigurationHelpers:
    """Test configuration helper functions"""
    
    def test_generate_config_warnings(self):
        """Test configuration warnings generation"""
        from api.v1.endpoints.config import _generate_config_warnings
        
        config_with_issues = {
            "mqtt": {
                "broker_address": "localhost",
                "use_tls": False,
                "tls_insecure": True
            },
            "security": {
                "level": "speed"
            },
            "api": {}
        }
        
        warnings = _generate_config_warnings(config_with_issues)
        
        assert any("TLS is disabled" in warning for warning in warnings)
        assert any("Security level is set to 'speed'" in warning for warning in warnings)
        assert any("No API keys configured" in warning for warning in warnings)
    
    def test_assess_security_impact(self):
        """Test security impact assessment"""
        from api.v1.endpoints.config import _assess_security_impact
        
        insecure_config = {
            "mqtt": {
                "use_tls": False,
                "username": ""
            },
            "security": {
                "level": "speed"
            }
        }
        
        impact = _assess_security_impact(insecure_config)
        
        assert impact["level"] == "high"  # TLS disabled should make it high
        assert any("MQTT TLS encryption disabled" in change for change in impact["changes"])
        assert any("Enable TLS encryption" in rec for rec in impact["recommendations"])
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('api.v1.endpoints.config.json.dump')
    def test_create_config_backup(self, mock_json_dump, mock_file, tmpdir):
        """Test configuration backup creation"""
        from api.v1.endpoints.config import _create_config_backup
        
        config = {"test": "data"}
        
        with patch('api.v1.endpoints.config.Path') as mock_path:
            mock_backup_dir = Mock()
            mock_backup_dir.mkdir = Mock()
            mock_path.return_value = mock_backup_dir
            
            backup_path = _create_config_backup(config)
            
            assert backup_path is not None
            assert "config_backup_" in backup_path
            mock_json_dump.assert_called_once_with(config, mock_file.return_value.__enter__.return_value, indent=2)
    
    @patch('builtins.open', new_callable=mock_open, read_data='{"restored": "config"}')
    @patch('api.v1.endpoints.config.json.load')
    @patch('api.v1.endpoints.config.get_manager')
    def test_restore_config_backup(self, mock_get_manager, mock_json_load, mock_file):
        """Test configuration backup restoration"""
        from api.v1.endpoints.config import _restore_config_backup
        
        mock_json_load.return_value = {"restored": "config"}
        mock_config_manager = Mock()
        mock_get_manager.return_value = mock_config_manager
        
        _restore_config_backup("/path/to/backup.json")
        
        mock_config_manager.save_configuration.assert_called_once_with({"restored": "config"})


if __name__ == "__main__":
    pytest.main([__file__])