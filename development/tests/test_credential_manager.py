"""
Test suite for Credential Manager
Phase 2A: AI Model Provider Optimization

Tests for secure credential management with API key storage and validation.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, AsyncMock, patch, mock_open
from datetime import datetime, timedelta

from ai.providers.credential_manager import CredentialManager, CredentialInfo


class TestCredentialManager:
    """Test suite for CredentialManager"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        return {
            "openai_api_key": "sk-test-openai-key",
            "anthropic_api_key": "sk-ant-test-key",
            "google_api_key": "test-google-key"
        }
    
    @pytest.fixture
    def credential_manager(self, mock_config, temp_dir):
        """Create credential manager for testing"""
        return CredentialManager(mock_config, temp_dir)
    
    def test_init_creates_manager_with_config(self, mock_config, temp_dir):
        """
        Test: CredentialManager initialization
        
        Arrange: Create mock configuration and temp directory
        Act: Initialize CredentialManager
        Assert: Manager is created with correct configuration
        """
        # Arrange & Act
        manager = CredentialManager(mock_config, temp_dir)
        
        # Assert
        assert manager.config == mock_config
        assert manager.data_path == temp_dir
        assert manager.fernet is not None
        assert manager.credentials == {}
    
    def test_mask_credential_hides_sensitive_data(self, credential_manager):
        """
        Test: Credential masking for display
        
        Arrange: Create credential manager
        Act: Mask different credential formats
        Assert: Credentials are properly masked
        """
        # Arrange
        short_key = "short"
        long_key = "sk-very-long-api-key-that-should-be-masked"
        
        # Act
        masked_short = credential_manager._mask_credential(short_key)
        masked_long = credential_manager._mask_credential(long_key)
        
        # Assert
        assert masked_short == "*" * len(short_key)
        assert masked_long.startswith("sk-v")
        assert masked_long.endswith("sked")
        assert "*" in masked_long
    
    def test_store_credential_saves_encrypted(self, credential_manager):
        """
        Test: Credential storage with encryption
        
        Arrange: Create credential manager
        Act: Store a credential
        Assert: Credential is stored and encrypted
        """
        # Arrange
        provider = "openai"
        credential_type = "api_key"
        value = "sk-test-key-12345"
        
        # Act
        result = credential_manager.store_credential(
            provider, credential_type, value
        )
        
        # Assert
        assert result is True
        credential_key = f"{provider}:{credential_type}"
        assert credential_key in credential_manager.credentials
        stored_cred = credential_manager.credentials[credential_key]
        assert stored_cred["value"] == value
        assert stored_cred["provider"] == provider
        assert stored_cred["credential_type"] == credential_type
    
    def test_get_credential_retrieves_stored_value(self, credential_manager):
        """
        Test: Credential retrieval
        
        Arrange: Store a credential
        Act: Retrieve the credential
        Assert: Correct value is returned
        """
        # Arrange
        provider = "openai"
        credential_type = "api_key"
        value = "sk-test-key-12345"
        credential_manager.store_credential(provider, credential_type, value)
        
        # Act
        retrieved_value = credential_manager.get_credential(provider, credential_type)
        
        # Assert
        assert retrieved_value == value
    
    def test_get_credential_from_ha_secrets(self, credential_manager):
        """
        Test: Credential retrieval from HA secrets
        
        Arrange: Configure HA secrets in config
        Act: Retrieve credential not in storage
        Assert: Value is retrieved from HA secrets
        """
        # Arrange
        provider = "anthropic"
        credential_type = "api_key"
        expected_value = "sk-ant-test-key"
        
        # Act
        retrieved_value = credential_manager.get_credential(provider, credential_type)
        
        # Assert
        assert retrieved_value == expected_value
    
    def test_validate_credential_format(self, credential_manager):
        """
        Test: Credential format validation
        
        Arrange: Create credential manager
        Act: Validate different credential formats
        Assert: Validation works correctly for each provider
        """
        # Arrange & Act & Assert
        
        # OpenAI key validation
        assert credential_manager._validate_credential_format(
            "openai", "api_key", "sk-test-key-12345"
        ) is True
        assert credential_manager._validate_credential_format(
            "openai", "api_key", "invalid-key"
        ) is False
        
        # Anthropic key validation
        assert credential_manager._validate_credential_format(
            "anthropic", "api_key", "sk-ant-test-key-12345"
        ) is True
        assert credential_manager._validate_credential_format(
            "anthropic", "api_key", "invalid-key"
        ) is False
        
        # Google key validation
        assert credential_manager._validate_credential_format(
            "google", "api_key", "AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo"
        ) is True
        assert credential_manager._validate_credential_format(
            "google", "api_key", "short"
        ) is False
    
    @pytest.mark.asyncio
    async def test_validate_openai_credential(self, credential_manager):
        """
        Test: OpenAI credential validation
        
        Arrange: Mock OpenAI client
        Act: Validate OpenAI credential
        Assert: Validation result is correct
        """
        # Arrange
        valid_key = "sk-test-key-12345"
        
        with patch('openai.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_client.models.list.return_value.data = [{"id": "gpt-4"}]
            mock_openai.return_value = mock_client
            
            # Act
            result = await credential_manager._validate_openai_credential(valid_key)
            
            # Assert
            assert result is True
            mock_openai.assert_called_once_with(api_key=valid_key)
    
    @pytest.mark.asyncio
    async def test_validate_anthropic_credential(self, credential_manager):
        """
        Test: Anthropic credential validation
        
        Arrange: Mock Anthropic client
        Act: Validate Anthropic credential
        Assert: Validation result is correct
        """
        # Arrange
        valid_key = "sk-ant-test-key-12345"
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock(text="test")]
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            
            # Act
            result = await credential_manager._validate_anthropic_credential(valid_key)
            
            # Assert
            assert result is True
            mock_anthropic.assert_called_once_with(api_key=valid_key)
    
    @pytest.mark.asyncio
    async def test_validate_google_credential(self, credential_manager):
        """
        Test: Google credential validation
        
        Arrange: Mock Google client
        Act: Validate Google credential
        Assert: Validation result is correct
        """
        # Arrange
        valid_key = "AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo"
        
        with patch('google.generativeai.configure') as mock_configure:
            with patch('google.generativeai.GenerativeModel') as mock_model:
                mock_instance = Mock()
                mock_response = Mock()
                mock_response.text = "test response"
                mock_instance.generate_content.return_value = mock_response
                mock_model.return_value = mock_instance
                
                # Act
                result = await credential_manager._validate_google_credential(valid_key)
                
                # Assert
                assert result is True
                mock_configure.assert_called_once_with(api_key=valid_key)
    
    @pytest.mark.asyncio
    async def test_validate_credential_with_cache(self, credential_manager):
        """
        Test: Credential validation with caching
        
        Arrange: Store credential and validate once
        Act: Validate again within cache TTL
        Assert: Cached result is returned
        """
        # Arrange
        provider = "openai"
        credential_type = "api_key"
        value = "sk-test-key-12345"
        
        credential_manager.store_credential(provider, credential_type, value)
        
        # Mock the validation to return True first time
        with patch.object(credential_manager, '_validate_with_provider', 
                         new_callable=AsyncMock, return_value=True):
            # Act
            result1 = await credential_manager.validate_credential(provider, credential_type)
            result2 = await credential_manager.validate_credential(provider, credential_type)
            
            # Assert
            assert result1 is True
            assert result2 is True
            # Should only call validation once due to caching
            assert credential_manager._validate_with_provider.call_count == 1
    
    def test_list_credentials_returns_masked_info(self, credential_manager):
        """
        Test: List credentials returns masked information
        
        Arrange: Store multiple credentials
        Act: List credentials
        Assert: Masked credentials are returned
        """
        # Arrange
        credential_manager.store_credential("openai", "api_key", "sk-test-key-12345")
        credential_manager.store_credential("anthropic", "api_key", "sk-ant-test-key")
        
        # Act
        credentials = credential_manager.list_credentials()
        
        # Assert
        assert len(credentials) == 2
        for cred in credentials:
            assert isinstance(cred, CredentialInfo)
            assert "*" in cred.masked_value
            assert cred.provider in ["openai", "anthropic"]
            assert cred.credential_type == "api_key"
    
    def test_delete_credential_removes_from_storage(self, credential_manager):
        """
        Test: Delete credential removes from storage
        
        Arrange: Store a credential
        Act: Delete the credential
        Assert: Credential is removed from storage
        """
        # Arrange
        provider = "openai"
        credential_type = "api_key"
        value = "sk-test-key-12345"
        credential_manager.store_credential(provider, credential_type, value)
        
        # Act
        result = credential_manager.delete_credential(provider, credential_type)
        
        # Assert
        assert result is True
        assert credential_manager.get_credential(provider, credential_type) is None
    
    def test_get_credential_stats_returns_summary(self, credential_manager):
        """
        Test: Get credential statistics
        
        Arrange: Store credentials with different statuses
        Act: Get statistics
        Assert: Correct statistics are returned
        """
        # Arrange
        credential_manager.store_credential("openai", "api_key", "sk-test-key-1")
        credential_manager.store_credential("anthropic", "api_key", "sk-ant-test-key")
        
        # Act
        stats = credential_manager.get_credential_stats()
        
        # Assert
        assert stats["total_credentials"] == 2
        assert stats["by_provider"]["openai"] == 1
        assert stats["by_provider"]["anthropic"] == 1
        assert stats["expired_credentials"] == 0
    
    @pytest.mark.asyncio
    async def test_health_check_validates_all_credentials(self, credential_manager):
        """
        Test: Health check validates all stored credentials
        
        Arrange: Store multiple credentials
        Act: Perform health check
        Assert: All credentials are validated
        """
        # Arrange
        credential_manager.store_credential("openai", "api_key", "sk-test-key-1")
        credential_manager.store_credential("anthropic", "api_key", "sk-ant-test-key")
        
        with patch.object(credential_manager, 'validate_credential', 
                         new_callable=AsyncMock, return_value=True):
            # Act
            health_report = await credential_manager.health_check()
            
            # Assert
            assert health_report["overall_health"] == "healthy"
            assert health_report["credential_count"] == 2
            assert len(health_report["validation_results"]) == 2
            assert credential_manager.validate_credential.call_count == 2
    
    @pytest.mark.asyncio
    async def test_health_check_detects_invalid_credentials(self, credential_manager):
        """
        Test: Health check detects invalid credentials
        
        Arrange: Store credentials, mock one as invalid
        Act: Perform health check
        Assert: Invalid credential is detected
        """
        # Arrange
        credential_manager.store_credential("openai", "api_key", "sk-test-key-1")
        credential_manager.store_credential("invalid", "api_key", "invalid-key")
        
        async def mock_validate(provider, credential_type, force_refresh=False):
            return provider == "openai"
        
        with patch.object(credential_manager, 'validate_credential', 
                         side_effect=mock_validate):
            # Act
            health_report = await credential_manager.health_check()
            
            # Assert
            assert health_report["overall_health"] == "degraded"
            assert len(health_report["issues"]) > 0
            assert "Invalid credential" in health_report["issues"][0]
    
    def test_credential_encryption_and_decryption(self, credential_manager, temp_dir):
        """
        Test: Credential encryption and decryption
        
        Arrange: Store credential and save to disk
        Act: Create new manager and load credentials
        Assert: Credentials are properly encrypted/decrypted
        """
        # Arrange
        provider = "openai"
        credential_type = "api_key"
        value = "sk-test-key-12345"
        
        # Store credential
        credential_manager.store_credential(provider, credential_type, value)
        
        # Act - Create new manager instance
        new_manager = CredentialManager({}, temp_dir)
        retrieved_value = new_manager.get_credential(provider, credential_type)
        
        # Assert
        assert retrieved_value == value
    
    def test_credential_expiration_handling(self, credential_manager):
        """
        Test: Expired credentials are handled correctly
        
        Arrange: Store credential with expiration
        Act: Try to retrieve expired credential
        Assert: None is returned for expired credential
        """
        # Arrange
        provider = "openai"
        credential_type = "api_key"
        value = "sk-test-key-12345"
        expired_time = (datetime.now() - timedelta(hours=1)).isoformat()
        
        credential_manager.store_credential(
            provider, credential_type, value, expires_at=expired_time
        )
        
        # Act
        retrieved_value = credential_manager.get_credential(provider, credential_type)
        
        # Assert
        assert retrieved_value is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])