"""
Tests for manager control API endpoints
"""

import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.v1.endpoints.managers import router
from api.v1.schemas import (
    ManagerListResponse, ManagerDetails, ManagerConfigRequest,
    BulkManagerOperation
)
from utils.manager_registry import ManagerRegistry, ManagerNames


@pytest.fixture
def app():
    """Create FastAPI app with manager router for testing"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_registry():
    """Mock manager registry for testing"""
    with patch('api.v1.endpoints.managers.get_registry') as mock_get_registry:
        mock_registry = Mock(spec=ManagerRegistry)
        mock_get_registry.return_value = mock_registry
        yield mock_registry


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


class TestManagerListEndpoint:
    """Test manager listing endpoint"""
    
    @patch('api.v1.endpoints.managers.get_current_user')
    def test_list_managers_success(self, mock_auth, client, mock_registry, mock_current_user):
        """Test successful manager listing"""
        mock_auth.return_value = mock_current_user
        
        # Mock registry response
        mock_registry.get_manager_status.return_value = {
            "total_managers": 2,
            "managers": {
                "test_manager1": {
                    "type": "MockManager",
                    "module": "test.module",
                    "memory_address": "0x123456",
                    "creation_time": time.time() - 100,
                    "configurable": True,
                    "health_monitoring": False
                },
                "test_manager2": {
                    "type": "AnotherManager", 
                    "module": "test.module2",
                    "memory_address": "0x789abc",
                    "creation_time": time.time() - 50,
                    "configurable": False,
                    "health_monitoring": True
                }
            }
        }
        
        response = client.get("/managers")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_managers"] == 2
        assert len(data["managers"]) == 2
        assert data["registry_status"] == "healthy"
        
        # Check manager details
        manager1 = next(m for m in data["managers"] if m["name"] == "test_manager1")
        assert manager1["type"] == "MockManager"
        assert manager1["configurable"] is True
        assert manager1["uptime_seconds"] is not None
    
    @patch('api.v1.endpoints.managers.get_current_user')
    def test_list_managers_registry_error(self, mock_auth, client, mock_registry, mock_current_user):
        """Test manager listing with registry error"""
        mock_auth.return_value = mock_current_user
        mock_registry.get_manager_status.side_effect = Exception("Registry error")
        
        response = client.get("/managers")
        
        assert response.status_code == 500
        assert "Failed to list managers" in response.json()["detail"]


class TestManagerDetailsEndpoint:
    """Test manager details endpoint"""
    
    @patch('api.v1.endpoints.managers.get_current_user')
    def test_get_manager_details_success(self, mock_auth, client, mock_registry, mock_current_user):
        """Test successful manager details retrieval"""
        mock_auth.return_value = mock_current_user
        
        # Mock manager instance
        mock_manager = Mock()
        mock_manager.get_config.return_value = {"setting1": "value1"}
        mock_manager.get_health.return_value = {"status": "healthy"}
        
        # Add capabilities
        for method in ['get_config', 'set_config', 'get_health', 'restart']:
            setattr(mock_manager, method, Mock())
        
        mock_registry.get_manager.return_value = mock_manager
        mock_registry.get_manager_status.return_value = {
            "managers": {
                "test_manager": {
                    "type": "TestManager",
                    "module": "test.module",
                    "memory_address": "0x123456",
                    "creation_time": time.time() - 100,
                    "status": {"performance": "good"}
                }
            }
        }
        
        response = client.get("/managers/test_manager")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "test_manager"
        assert data["type"] == "TestManager"
        assert data["configuration"] == {"setting1": "value1"}
        assert data["health_status"] == {"status": "healthy"}
        assert "get_config" in data["capabilities"]
        assert "restart" in data["capabilities"]
    
    @patch('api.v1.endpoints.managers.get_current_user')
    def test_get_manager_details_not_found(self, mock_auth, client, mock_registry, mock_current_user):
        """Test manager details for non-existent manager"""
        mock_auth.return_value = mock_current_user
        mock_registry.get_manager.return_value = None
        
        response = client.get("/managers/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestManagerRestartEndpoint:
    """Test manager restart endpoint"""
    
    @patch('api.v1.endpoints.managers.get_current_user')
    @pytest.mark.asyncio
    async def test_restart_manager_success(self, mock_auth, client, mock_registry, mock_current_user):
        """Test successful manager restart"""
        mock_auth.return_value = mock_current_user
        
        # Mock manager with restart capability
        mock_manager = Mock()
        mock_manager.restart = AsyncMock()
        
        mock_registry.get_manager.return_value = mock_manager
        
        response = client.post("/managers/test_manager/_restart")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "restarted successfully" in data["message"]
        assert data["operation_id"] is not None
    
    @patch('api.v1.endpoints.managers.get_current_user')
    def test_restart_manager_not_found(self, mock_auth, client, mock_registry, mock_current_user):
        """Test restart of non-existent manager"""
        mock_auth.return_value = mock_current_user
        mock_registry.get_manager.return_value = None
        
        response = client.post("/managers/nonexistent/_restart")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    @patch('api.v1.endpoints.managers.get_current_user')
    def test_restart_manager_no_capability(self, mock_auth, client, mock_registry, mock_current_user):
        """Test restart of manager without restart capability"""
        mock_auth.return_value = mock_current_user
        
        # Mock manager without restart capability
        mock_manager = Mock(spec=[])  # Empty spec means no methods
        mock_registry.get_manager.return_value = mock_manager
        
        response = client.post("/managers/test_manager/_restart")
        
        assert response.status_code == 400
        assert "does not support restart" in response.json()["detail"]


class TestManagerConfigEndpoints:
    """Test manager configuration endpoints"""
    
    @patch('api.v1.endpoints.managers.get_current_user')
    def test_get_manager_config_success(self, mock_auth, client, mock_registry, mock_current_user):
        """Test successful config retrieval"""
        mock_auth.return_value = mock_current_user
        
        # Mock manager with config capability
        mock_manager = Mock()
        mock_manager.get_config.return_value = {
            "setting1": "value1",
            "setting2": 42,
            "nested": {"key": "value"}
        }
        
        mock_registry.get_manager.return_value = mock_manager
        
        response = client.get("/managers/test_manager/config")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["config"]["setting1"] == "value1"
        assert data["config"]["setting2"] == 42
        assert data["manager"] == "test_manager"
        assert "timestamp" in data
    
    @patch('api.v1.endpoints.managers.get_current_user')
    def test_get_manager_config_no_capability(self, mock_auth, client, mock_registry, mock_current_user):
        """Test config retrieval for manager without config capability"""
        mock_auth.return_value = mock_current_user
        
        # Mock manager without config capability
        mock_manager = Mock(spec=[])
        mock_registry.get_manager.return_value = mock_manager
        
        response = client.get("/managers/test_manager/config")
        
        assert response.status_code == 400
        assert "does not support configuration access" in response.json()["detail"]
    
    @patch('api.v1.endpoints.managers.get_current_user')
    def test_update_manager_config_success(self, mock_auth, client, mock_registry, mock_current_user):
        """Test successful config update"""
        mock_auth.return_value = mock_current_user
        
        # Mock manager with config capabilities
        mock_manager = Mock()
        mock_manager.validate_config.return_value = True
        mock_manager.set_config = Mock()
        mock_manager.restart = Mock()
        
        mock_registry.get_manager.return_value = mock_manager
        
        config_data = {
            "config": {"new_setting": "new_value"},
            "validate_only": False,
            "restart_manager": True
        }
        
        response = client.put("/managers/test_manager/config", json=config_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "Configuration updated" in data["message"]
        
        # Verify manager methods were called
        mock_manager.validate_config.assert_called_once()
        mock_manager.set_config.assert_called_once()
        mock_manager.restart.assert_called_once()
    
    @patch('api.v1.endpoints.managers.get_current_user')
    def test_update_manager_config_validation_only(self, mock_auth, client, mock_registry, mock_current_user):
        """Test config validation without applying changes"""
        mock_auth.return_value = mock_current_user
        
        # Mock manager with validation
        mock_manager = Mock()
        mock_manager.validate_config.return_value = True
        
        mock_registry.get_manager.return_value = mock_manager
        
        config_data = {
            "config": {"test_setting": "test_value"},
            "validate_only": True,
            "restart_manager": False
        }
        
        response = client.put("/managers/test_manager/config", json=config_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "validated"
        assert len(data["validation_errors"]) == 0
        
        # Verify only validation was called
        mock_manager.validate_config.assert_called_once()
        assert not hasattr(mock_manager, 'set_config') or not mock_manager.set_config.called
    
    @patch('api.v1.endpoints.managers.get_current_user')
    def test_update_manager_config_validation_failed(self, mock_auth, client, mock_registry, mock_current_user):
        """Test config update with validation failure"""
        mock_auth.return_value = mock_current_user
        
        # Mock manager with failed validation
        mock_manager = Mock()
        mock_manager.validate_config.return_value = False
        mock_manager.get_validation_errors.return_value = ["Invalid setting", "Missing required field"]
        
        mock_registry.get_manager.return_value = mock_manager
        
        config_data = {
            "config": {"invalid_setting": "bad_value"},
            "validate_only": False,
            "restart_manager": False
        }
        
        response = client.put("/managers/test_manager/config", json=config_data)
        
        assert response.status_code == 400
        assert "Configuration validation failed" in response.json()["detail"]


class TestBulkManagerOperations:
    """Test bulk manager operations"""
    
    @patch('api.v1.endpoints.managers.get_current_user')
    def test_bulk_restart_success(self, mock_auth, client, mock_registry, mock_current_user):
        """Test successful bulk restart operation"""
        mock_auth.return_value = mock_current_user
        
        # Mock managers with restart capability
        mock_manager1 = Mock()
        mock_manager1.restart = Mock()
        mock_manager2 = Mock()
        mock_manager2.restart = Mock()
        
        def mock_get_manager(name):
            if name == "manager1":
                return mock_manager1
            elif name == "manager2":
                return mock_manager2
            return None
        
        mock_registry.get_manager.side_effect = mock_get_manager
        
        bulk_request = {
            "managers": ["manager1", "manager2"],
            "operation": "restart",
            "force": False
        }
        
        response = client.post("/managers/_bulk", json=bulk_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["total_requested"] == 2
        assert len(data["successful"]) == 2
        assert len(data["failed"]) == 0
        assert "manager1" in data["successful"]
        assert "manager2" in data["successful"]
    
    @patch('api.v1.endpoints.managers.get_current_user')
    def test_bulk_operation_partial_failure(self, mock_auth, client, mock_registry, mock_current_user):
        """Test bulk operation with partial failures"""
        mock_auth.return_value = mock_current_user
        
        # Mock managers - one exists, one doesn't
        mock_manager1 = Mock()
        mock_manager1.restart = Mock()
        
        def mock_get_manager(name):
            if name == "manager1":
                return mock_manager1
            return None  # manager2 doesn't exist
        
        mock_registry.get_manager.side_effect = mock_get_manager
        
        bulk_request = {
            "managers": ["manager1", "manager2"],
            "operation": "restart",
            "force": True
        }
        
        response = client.post("/managers/_bulk", json=bulk_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "partial"
        assert data["total_requested"] == 2
        assert len(data["successful"]) == 1
        assert len(data["failed"]) == 1
        assert "manager1" in data["successful"]
        assert data["failed"][0]["manager"] == "manager2"
        assert "not found" in data["failed"][0]["error"]


if __name__ == "__main__":
    pytest.main([__file__])