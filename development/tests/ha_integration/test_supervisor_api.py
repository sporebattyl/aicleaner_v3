"""
Test suite for AICleaner v3 Supervisor API
Tests integration with Home Assistant Supervisor API.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import aiohttp
import os
import asyncio

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ha_integration.supervisor_api import SupervisorAPI


class TestSupervisorAPI:
    """Test cases for SupervisorAPI."""

    @pytest.fixture
    def mock_loop(self):
        """Create mock event loop."""
        return asyncio.get_event_loop()

    @pytest.fixture
    def mock_session(self):
        """Create mock aiohttp session."""
        session = Mock(spec=aiohttp.ClientSession)
        session.request = AsyncMock()
        session.close = AsyncMock()
        return session

    @pytest.fixture
    def supervisor_api(self, mock_loop):
        """Create supervisor API instance."""
        with patch.dict(os.environ, {'SUPERVISOR_TOKEN': 'test_token'}):
            return SupervisorAPI(mock_loop)

    @pytest.fixture
    def supervisor_api_no_token(self, mock_loop):
        """Create supervisor API instance without token."""
        with patch.dict(os.environ, {}, clear=True):
            return SupervisorAPI(mock_loop)

    def test_supervisor_api_initialization_with_token(self, supervisor_api):
        """Test supervisor API initialization with token."""
        assert supervisor_api.supervisor_token == "test_token"

    def test_supervisor_api_initialization_without_token(self, supervisor_api_no_token):
        """Test supervisor API initialization without token."""
        assert supervisor_api_no_token.supervisor_token is None

    @pytest.mark.asyncio
    async def test_request_success(self, supervisor_api):
        """Test successful API request."""
        expected_response = {"result": "ok", "data": {"test": "value"}}
        
        # Mock session and response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value=expected_response)
        
        with patch.object(supervisor_api, 'session') as mock_session:
            mock_session.request.return_value.__aenter__.return_value = mock_response
            
            result = await supervisor_api._request("GET", "test/endpoint")
            
            assert result == expected_response
            mock_session.request.assert_called_once_with(
                "GET",
                "http://supervisor/test/endpoint",
                headers={"Authorization": "Bearer test_token"},
                json=None
            )

    @pytest.mark.asyncio
    async def test_request_with_data(self, supervisor_api):
        """Test API request with data."""
        test_data = {"key": "value"}
        expected_response = {"result": "ok"}
        
        # Mock session and response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value=expected_response)
        
        with patch.object(supervisor_api, 'session') as mock_session:
            mock_session.request.return_value.__aenter__.return_value = mock_response
            
            result = await supervisor_api._request("POST", "test/endpoint", test_data)
            
            assert result == expected_response
            mock_session.request.assert_called_once_with(
                "POST",
                "http://supervisor/test/endpoint",
                headers={"Authorization": "Bearer test_token"},
                json=test_data
            )

    @pytest.mark.asyncio
    async def test_request_without_token(self, supervisor_api_no_token):
        """Test API request without token raises error."""
        with pytest.raises(ConnectionRefusedError) as exc_info:
            await supervisor_api_no_token._request("GET", "test/endpoint")
        
        assert "Supervisor API token is not available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_request_client_error(self, supervisor_api):
        """Test API request with client error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = aiohttp.ClientError("Connection failed")
        
        with patch.object(supervisor_api, 'session') as mock_session:
            mock_session.request.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(aiohttp.ClientError):
                await supervisor_api._request("GET", "test/endpoint")

    @pytest.mark.asyncio
    async def test_get_self_info(self, supervisor_api):
        """Test get self info method."""
        expected_response = {
            "result": "ok",
            "data": {
                "name": "AICleaner v3",
                "version": "1.0.0",
                "state": "started"
            }
        }
        
        with patch.object(supervisor_api, '_request', return_value=expected_response) as mock_request:
            result = await supervisor_api.get_self_info()
            
            assert result == expected_response
            mock_request.assert_called_once_with("GET", "addons/self/info")

    @pytest.mark.asyncio
    async def test_restart_addon(self, supervisor_api):
        """Test restart addon method."""
        expected_response = {"result": "ok"}
        
        with patch.object(supervisor_api, '_request', return_value=expected_response) as mock_request:
            result = await supervisor_api.restart_addon()
            
            assert result == expected_response
            mock_request.assert_called_once_with("POST", "addons/self/restart")

    @pytest.mark.asyncio
    async def test_close_session(self, supervisor_api):
        """Test closing session."""
        with patch.object(supervisor_api, 'session') as mock_session:
            await supervisor_api.close()
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_requests(self, supervisor_api):
        """Test multiple API requests."""
        responses = [
            {"result": "ok", "data": {"info": "test"}},
            {"result": "ok"}
        ]
        
        with patch.object(supervisor_api, '_request', side_effect=responses) as mock_request:
            # First request
            result1 = await supervisor_api.get_self_info()
            assert result1 == responses[0]
            
            # Second request
            result2 = await supervisor_api.restart_addon()
            assert result2 == responses[1]
            
            # Verify both requests were made
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_request_url_construction(self, supervisor_api):
        """Test URL construction for different endpoints."""
        test_cases = [
            ("addons/self/info", "http://supervisor/addons/self/info"),
            ("addons/self/restart", "http://supervisor/addons/self/restart"),
            ("test/endpoint", "http://supervisor/test/endpoint"),
            ("api/v1/test", "http://supervisor/api/v1/test")
        ]
        
        for endpoint, expected_url in test_cases:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json = AsyncMock(return_value={"result": "ok"})
            
            with patch.object(supervisor_api, 'session') as mock_session:
                mock_session.request.return_value.__aenter__.return_value = mock_response
                
                await supervisor_api._request("GET", endpoint)
                
                call_args = mock_session.request.call_args
                assert call_args[0][1] == expected_url

    @pytest.mark.asyncio
    async def test_request_headers(self, supervisor_api):
        """Test request headers are set correctly."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value={"result": "ok"})
        
        with patch.object(supervisor_api, 'session') as mock_session:
            mock_session.request.return_value.__aenter__.return_value = mock_response
            
            await supervisor_api._request("GET", "test/endpoint")
            
            call_args = mock_session.request.call_args
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer test_token"


class TestSupervisorAPIIntegration:
    """Integration tests for Supervisor API."""

    @pytest.mark.asyncio
    async def test_supervisor_api_lifecycle(self, mock_loop):
        """Test complete lifecycle of supervisor API."""
        with patch.dict(os.environ, {'SUPERVISOR_TOKEN': 'test_token'}):
            api = SupervisorAPI(mock_loop)
            
            # Test initialization
            assert api.supervisor_token == "test_token"
            
            # Test request flow
            with patch.object(api, '_request') as mock_request:
                mock_request.return_value = {"result": "ok"}
                
                # Test get info
                await api.get_self_info()
                mock_request.assert_called_with("GET", "addons/self/info")
                
                # Test restart
                await api.restart_addon()
                mock_request.assert_called_with("POST", "addons/self/restart")
            
            # Test cleanup
            with patch.object(api, 'session') as mock_session:
                await api.close()
                mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_flow(self, mock_loop):
        """Test error handling in various scenarios."""
        with patch.dict(os.environ, {'SUPERVISOR_TOKEN': 'test_token'}):
            api = SupervisorAPI(mock_loop)
            
            # Test different error types
            error_scenarios = [
                aiohttp.ClientError("Connection failed"),
                aiohttp.ClientTimeout(),
                aiohttp.ClientResponseError(None, None, status=404)
            ]
            
            for error in error_scenarios:
                with patch.object(api, 'session') as mock_session:
                    mock_response = Mock()
                    mock_response.raise_for_status.side_effect = error
                    mock_session.request.return_value.__aenter__.return_value = mock_response
                    
                    with pytest.raises(aiohttp.ClientError):
                        await api._request("GET", "test/endpoint")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])