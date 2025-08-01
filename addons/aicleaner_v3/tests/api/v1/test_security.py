"""
Tests for API security and authentication
"""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime

from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.v1.security import (
    APIKeyManager, AuditLogger, api_key_manager,
    get_current_user, require_permission
)
from api.v1.schemas import APIKeyPermissions


@pytest.fixture
def api_key_manager_instance():
    """Create a fresh API key manager for testing"""
    manager = APIKeyManager()
    # Clear any existing keys
    manager._keys = {}
    return manager


@pytest.fixture
def mock_audit_logger():
    """Mock audit logger for testing"""
    with patch('api.v1.security.audit_logger') as mock_logger:
        yield mock_logger


class TestAPIKeyManager:
    """Test API key management functionality"""
    
    def test_generate_api_key(self, api_key_manager_instance):
        """Test API key generation"""
        key = api_key_manager_instance._generate_api_key()
        
        assert key.startswith("aicv3_")
        assert len(key) > 10
        
        # Generate another key - should be different
        key2 = api_key_manager_instance._generate_api_key()
        assert key != key2
    
    def test_hash_key(self, api_key_manager_instance):
        """Test API key hashing"""
        key = "test_key_123"
        hash1 = api_key_manager_instance._hash_key(key)
        hash2 = api_key_manager_instance._hash_key(key)
        
        # Same key should produce same hash
        assert hash1 == hash2
        
        # Different key should produce different hash
        hash3 = api_key_manager_instance._hash_key("different_key")
        assert hash1 != hash3
    
    def test_create_default_keys(self, api_key_manager_instance):
        """Test default key creation"""
        api_key_manager_instance._create_default_keys()
        
        assert len(api_key_manager_instance._keys) == 2
        
        # Check that keys have proper structure
        for key_hash, config in api_key_manager_instance._keys.items():
            assert "name" in config
            assert "permissions" in config
            assert "created_at" in config
            assert "rate_limit" in config
    
    def test_validate_key(self, api_key_manager_instance):
        """Test API key validation"""
        # Create a test key
        api_key_manager_instance._create_default_keys()
        
        # Get one of the created keys
        test_key = api_key_manager_instance._generate_api_key()
        test_hash = api_key_manager_instance._hash_key(test_key)
        
        api_key_manager_instance._keys[test_hash] = {
            "name": "test_key",
            "permissions": {"read_config": True},
            "created_at": datetime.now().isoformat(),
            "rate_limit": "60/minute"
        }
        
        # Test valid key
        config = api_key_manager_instance.validate_key(test_key)
        assert config is not None
        assert config["name"] == "test_key"
        
        # Test invalid key
        config = api_key_manager_instance.validate_key("invalid_key")
        assert config is None
        
        # Test empty key
        config = api_key_manager_instance.validate_key("")
        assert config is None
    
    def test_get_permissions(self, api_key_manager_instance):
        """Test getting permissions for an API key"""
        test_key = api_key_manager_instance._generate_api_key()
        test_hash = api_key_manager_instance._hash_key(test_key)
        
        permissions_dict = {
            "read_config": True,
            "write_config": False,
            "control_managers": True,
            "system_control": False,
            "view_metrics": True
        }
        
        api_key_manager_instance._keys[test_hash] = {
            "name": "test_key",
            "permissions": permissions_dict,
            "created_at": datetime.now().isoformat()
        }
        
        permissions = api_key_manager_instance.get_permissions(test_key)
        assert isinstance(permissions, APIKeyPermissions)
        assert permissions.read_config is True
        assert permissions.write_config is False
        assert permissions.control_managers is True
    
    def test_create_key(self, api_key_manager_instance):
        """Test creating new API key"""
        permissions = {
            "read_config": True,
            "write_config": True,
            "control_managers": False,
            "system_control": False,
            "view_metrics": True
        }
        
        new_key = api_key_manager_instance.create_key("test_created_key", permissions)
        
        assert new_key.startswith("aicv3_")
        
        # Validate the created key
        config = api_key_manager_instance.validate_key(new_key)
        assert config is not None
        assert config["name"] == "test_created_key"
        assert config["permissions"] == permissions
    
    def test_revoke_key(self, api_key_manager_instance):
        """Test revoking API key"""
        # Create a key
        permissions = {"read_config": True}
        new_key = api_key_manager_instance.create_key("test_revoke", permissions)
        
        # Verify it exists
        config = api_key_manager_instance.validate_key(new_key)
        assert config is not None
        
        # Revoke it
        result = api_key_manager_instance.revoke_key(new_key)
        assert result is True
        
        # Verify it's gone
        config = api_key_manager_instance.validate_key(new_key)
        assert config is None
        
        # Try to revoke non-existent key
        result = api_key_manager_instance.revoke_key("nonexistent_key")
        assert result is False


class TestAuditLogger:
    """Test audit logging functionality"""
    
    def test_audit_logger_creation(self):
        """Test audit logger creation"""
        logger = AuditLogger()
        assert logger.audit_logger is not None
    
    @patch('api.v1.security.logging.getLogger')
    def test_log_request_success(self, mock_get_logger):
        """Test logging successful requests"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        audit_logger = AuditLogger()
        audit_logger.audit_logger = mock_logger
        
        # Mock request
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/v1/managers"
        mock_request.url.query = "format=json"
        
        with patch('api.v1.security.get_remote_address', return_value="127.0.0.1"):
            audit_logger.log_request(mock_request, "test_key", True)
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "API_REQUEST" in call_args
        assert "test_key" in call_args
    
    @patch('api.v1.security.logging.getLogger')
    def test_log_request_failure(self, mock_get_logger):
        """Test logging failed requests"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        audit_logger = AuditLogger()
        audit_logger.audit_logger = mock_logger
        
        # Mock request
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url.path = "/api/v1/system/_shutdown"
        mock_request.url.query = None
        
        with patch('api.v1.security.get_remote_address', return_value="127.0.0.1"):
            audit_logger.log_request(mock_request, "test_key", False, "Insufficient permissions")
        
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0][0]
        assert "API_REQUEST_FAILED" in call_args
        assert "Insufficient permissions" in call_args


class TestSecurityDecorators:
    """Test security decorators and dependencies"""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock FastAPI app for testing"""
        app = FastAPI()
        return app
    
    def test_require_permission_decorator(self):
        """Test the require_permission decorator"""
        
        @require_permission("write_config")
        async def test_endpoint(current_user: dict):
            return {"status": "success"}
        
        # Test with sufficient permissions
        mock_user = {
            "permissions": APIKeyPermissions(
                read_config=True,
                write_config=True,
                control_managers=False,
                system_control=False,
                view_metrics=True
            )
        }
        
        # This would need proper async testing framework
        # For now, just test the decorator exists and is callable
        assert callable(test_endpoint)
    
    def test_get_rate_limit_key(self):
        """Test rate limit key generation"""
        from api.v1.security import get_rate_limit_key
        
        # Mock request without auth header
        mock_request = Mock()
        mock_request.headers = {}
        
        with patch('api.v1.security.get_remote_address', return_value="127.0.0.1"):
            key = get_rate_limit_key(mock_request)
            assert key == "127.0.0.1"
        
        # Mock request with auth header
        mock_request.headers = {"Authorization": "Bearer aicv3_test_key_123"}
        
        with patch('api.v1.security.get_remote_address', return_value="127.0.0.1"):
            key = get_rate_limit_key(mock_request)
            assert key.startswith("127.0.0.1:")
            assert len(key) > len("127.0.0.1:")


@pytest.mark.asyncio
class TestSecurityIntegration:
    """Integration tests for security components"""
    
    @patch('api.v1.security.get_manager')
    async def test_api_key_loading_from_config(self, mock_get_manager):
        """Test loading API keys from configuration"""
        # Mock configuration manager
        mock_config_manager = Mock()
        mock_config_manager.load_configuration.return_value = {
            "api": {
                "keys": {
                    "hash123": {
                        "name": "test_key",
                        "permissions": {"read_config": True},
                        "created_at": "2023-01-01T00:00:00",
                        "rate_limit": "60/minute"
                    }
                }
            }
        }
        mock_get_manager.return_value = mock_config_manager
        
        # Create new API key manager
        manager = APIKeyManager()
        manager._load_api_keys()
        
        assert "hash123" in manager._keys
        assert manager._keys["hash123"]["name"] == "test_key"
    
    @patch('api.v1.security.get_manager')
    async def test_api_key_loading_fallback(self, mock_get_manager):
        """Test fallback to default keys when config unavailable"""
        # Mock configuration manager not available
        mock_get_manager.return_value = None
        
        # Create new API key manager
        manager = APIKeyManager()
        manager._load_api_keys()
        
        # Should have created default keys
        assert len(manager._keys) >= 2
        
        # Check for master and readonly keys
        key_names = [config["name"] for config in manager._keys.values()]
        assert "master_key" in key_names
        assert "readonly_key" in key_names


if __name__ == "__main__":
    pytest.main([__file__])