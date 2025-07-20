"""
Tests for system control API endpoints
"""

import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.v1.endpoints.system import router, _server_start_time, _metrics
from utils.manager_registry import ManagerRegistry


@pytest.fixture
def app():
    """Create FastAPI app with system router for testing"""
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
    with patch('api.v1.endpoints.system.get_registry') as mock_get_registry:
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


class TestSystemHealthEndpoint:
    """Test system health check endpoint"""
    
    @patch('api.v1.endpoints.system.get_current_user')
    def test_health_check_healthy_system(self, mock_auth, client, mock_registry, mock_current_user):
        """Test health check with healthy system"""
        mock_auth.return_value = mock_current_user
        
        mock_registry.get_manager_status.return_value = {
            "total_managers": 3,
            "managers": {
                "manager1": {"status": "running"},
                "manager2": {"status": "running"},
                "manager3": {"status": "running"}
            }
        }
        
        response = client.get("/system/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ok"
        assert data["version"] == "3.0.0"
        assert data["managers_healthy"] == 3
        assert data["managers_total"] == 3
        assert "uptime_seconds" in data
        assert "timestamp" in data
    
    @patch('api.v1.endpoints.system.get_current_user')
    def test_health_check_degraded_system(self, mock_auth, client, mock_registry, mock_current_user):
        """Test health check with degraded system"""
        mock_auth.return_value = mock_current_user
        
        mock_registry.get_manager_status.return_value = {
            "total_managers": 3,
            "managers": {
                "manager1": {"status": "running"},
                "manager2": {"status": "error"},
                "manager3": {"status": "running"}
            }
        }
        
        response = client.get("/system/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["managers_healthy"] == 2
        assert data["managers_total"] == 3
    
    @patch('api.v1.endpoints.system.get_current_user')
    def test_health_check_no_managers(self, mock_auth, client, mock_registry, mock_current_user):
        """Test health check with no managers"""
        mock_auth.return_value = mock_current_user
        
        mock_registry.get_manager_status.return_value = {
            "total_managers": 0,
            "managers": {}
        }
        
        response = client.get("/system/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "error"
        assert data["managers_healthy"] == 0
        assert data["managers_total"] == 0


class TestSystemMetricsEndpoint:
    """Test system metrics endpoint"""
    
    @patch('api.v1.endpoints.system.get_current_user')
    @patch('api.v1.endpoints.system.psutil')
    def test_get_system_metrics_success(self, mock_psutil, mock_auth, client, mock_registry, mock_current_user):
        """Test successful metrics retrieval"""
        mock_auth.return_value = mock_current_user
        
        # Mock psutil responses
        mock_psutil.cpu_percent.return_value = 45.2
        mock_psutil.virtual_memory.return_value = Mock(percent=62.8)
        mock_psutil.disk_usage.return_value = Mock(percent=34.1)
        
        mock_registry.get_manager_status.return_value = {
            "total_managers": 5
        }
        
        # Reset metrics for clean test
        global _metrics
        original_metrics = _metrics.copy()
        _metrics["api_requests_total"] = 100
        _metrics["api_requests_errors"] = 5
        
        try:
            response = client.get("/system/metrics")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["cpu_usage"] == 45.2
            assert data["memory_usage"] == 62.8
            assert data["disk_usage"] == 34.1
            assert data["active_managers"] == 5
            assert data["api_requests_total"] >= 100  # Will increment during the call
            assert data["api_requests_errors"] == 5
            assert "timestamp" in data
            
        finally:
            # Restore original metrics
            _metrics.clear()
            _metrics.update(original_metrics)
    
    @patch('api.v1.endpoints.system.get_current_user')
    @patch('api.v1.endpoints.system.psutil')
    def test_get_system_metrics_psutil_error(self, mock_psutil, mock_auth, client, mock_registry, mock_current_user):
        """Test metrics retrieval with psutil error"""
        mock_auth.return_value = mock_current_user
        mock_psutil.cpu_percent.side_effect = Exception("CPU error")
        
        response = client.get("/system/metrics")
        
        assert response.status_code == 500
        assert "Failed to get system metrics" in response.json()["detail"]


class TestSystemReloadEndpoint:
    """Test system reload endpoint"""
    
    @patch('api.v1.endpoints.system.get_current_user')
    def test_system_reload_success(self, mock_auth, client, mock_registry, mock_current_user):
        """Test successful system reload"""
        mock_auth.return_value = mock_current_user
        
        # Mock managers with reload capabilities
        mock_manager1 = Mock()
        mock_manager1.reload = Mock()
        mock_manager2 = Mock() 
        mock_manager2.restart = Mock()
        mock_manager3 = Mock()
        mock_manager3.shutdown = Mock()
        
        def mock_get_manager(name):
            if name == "manager1":
                return mock_manager1
            elif name == "manager2":
                return mock_manager2
            elif name == "manager3":
                return mock_manager3
            return None
        
        mock_registry.get_manager_status.return_value = {
            "managers": {
                "manager1": {},
                "manager2": {},
                "manager3": {}
            }
        }
        mock_registry.get_manager.side_effect = mock_get_manager
        
        response = client.post("/system/_reload")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "reloading"
        assert len(data["managers_reloaded"]) == 3
        assert "manager1" in data["managers_reloaded"]
        assert "manager2" in data["managers_reloaded"]
        assert "manager3" in data["managers_reloaded"]
        
        # Verify appropriate methods were called
        mock_manager1.reload.assert_called_once()
        mock_manager2.restart.assert_called_once()
        mock_manager3.shutdown.assert_called_once()
    
    @patch('api.v1.endpoints.system.get_current_user')
    def test_system_reload_partial_failure(self, mock_auth, client, mock_registry, mock_current_user):
        """Test system reload with some manager failures"""
        mock_auth.return_value = mock_current_user
        
        # Mock managers - one will fail
        mock_manager1 = Mock()
        mock_manager1.reload = Mock()
        mock_manager2 = Mock()
        mock_manager2.reload.side_effect = Exception("Reload failed")
        
        def mock_get_manager(name):
            if name == "manager1":
                return mock_manager1
            elif name == "manager2":
                return mock_manager2
            return None
        
        mock_registry.get_manager_status.return_value = {
            "managers": {
                "manager1": {},
                "manager2": {}
            }
        }
        mock_registry.get_manager.side_effect = mock_get_manager
        
        response = client.post("/system/_reload")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "reloading"
        assert len(data["managers_reloaded"]) == 1
        assert "manager1" in data["managers_reloaded"]
        assert "1 failed" in data["message"]


class TestSystemInfoEndpoint:
    """Test system info endpoint"""
    
    @patch('api.v1.endpoints.system.get_current_user')
    @patch('api.v1.endpoints.system.psutil')
    @patch('api.v1.endpoints.system.os')
    def test_get_system_info_success(self, mock_os, mock_psutil, mock_auth, client, mock_registry, mock_current_user):
        """Test successful system info retrieval"""
        mock_auth.return_value = mock_current_user
        
        # Mock system information
        mock_os.getpid.return_value = 12345
        mock_psutil.sys.version_info = Mock(major=3, minor=11, micro=5)
        mock_psutil.sys.platform = "linux"
        
        # Mock uname with nodename attribute
        mock_uname = Mock()
        mock_uname.nodename = "test-server"
        mock_psutil.os.uname.return_value = mock_uname
        
        # Mock process info
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=1024 * 1024 * 100)  # 100MB
        mock_process.num_threads.return_value = 8
        mock_process.open_files.return_value = [Mock(), Mock(), Mock()]  # 3 files
        mock_psutil.Process.return_value = mock_process
        
        mock_registry.get_manager_status.return_value = {
            "total_managers": 3,
            "managers": {"manager1": {}, "manager2": {}, "manager3": {}}
        }
        
        response = client.get("/system/info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["version"] == "3.0.0"
        assert data["python_version"] == "3.11.5"
        assert data["platform"] == "linux"
        assert data["hostname"] == "test-server"
        assert data["pid"] == 12345
        assert "uptime_seconds" in data
        assert "managers" in data
        assert "metrics" in data
        assert data["memory_usage_mb"] == 100.0
        assert data["thread_count"] == 8
        assert data["open_files"] == 3


class TestSystemShutdownEndpoint:
    """Test system shutdown endpoint"""
    
    @patch('api.v1.endpoints.system.get_current_user')
    @patch('api.v1.endpoints.system.asyncio.create_task')
    def test_system_shutdown_success(self, mock_create_task, mock_auth, client, mock_registry, mock_current_user):
        """Test successful system shutdown initiation"""
        mock_auth.return_value = mock_current_user
        
        response = client.post("/system/_shutdown")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "shutdown initiated" in data["message"]
        assert data["operation_id"] is not None
        
        # Verify shutdown was scheduled
        mock_create_task.assert_called_once()
        
        # Verify registry shutdown was called
        mock_registry.shutdown_all_managers.assert_called_once()


class TestSystemLogsEndpoint:
    """Test system logs endpoint"""
    
    @patch('api.v1.endpoints.system.get_current_user')
    def test_get_system_logs_default(self, mock_auth, client, mock_current_user):
        """Test getting system logs with default parameters"""
        mock_auth.return_value = mock_current_user
        
        response = client.get("/system/logs")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "logs" in data
        assert "total_entries" in data
        assert "filter_level" in data
        assert "timestamp" in data
        assert isinstance(data["logs"], list)
    
    @patch('api.v1.endpoints.system.get_current_user')
    def test_get_system_logs_with_filters(self, mock_auth, client, mock_current_user):
        """Test getting system logs with filters"""
        mock_auth.return_value = mock_current_user
        
        response = client.get("/system/logs?lines=50&level=DEBUG")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["filter_level"] == "DEBUG"
        # Note: In the mock implementation, the logs are static
        # In a real implementation, this would filter by level


class TestMetricsTracking:
    """Test internal metrics tracking"""
    
    def test_increment_metric(self):
        """Test metric increment functionality"""
        from api.v1.endpoints.system import increment_metric, _metrics
        
        # Store original value
        original_value = _metrics.get("test_metric", 0)
        
        # Increment metric
        increment_metric("test_metric")
        
        assert _metrics["test_metric"] == original_value + 1
        
        # Increment again
        increment_metric("test_metric")
        
        assert _metrics["test_metric"] == original_value + 2
    
    def test_server_start_time_tracking(self):
        """Test that server start time is tracked"""
        from api.v1.endpoints.system import _server_start_time
        
        assert isinstance(_server_start_time, (int, float))
        assert _server_start_time > 0
        assert _server_start_time <= time.time()


if __name__ == "__main__":
    pytest.main([__file__])