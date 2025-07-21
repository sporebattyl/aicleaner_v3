"""
Credential Manager for AI Providers
Phase 2A: AI Model Provider Optimization

Provides secure credential management with API key rotation, validation,
and integration with Home Assistant secrets management.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from cryptography.fernet import Fernet
import hashlib
import secrets


@dataclass
class CredentialInfo:
    """Information about a managed credential"""
    provider: str
    credential_type: str
    masked_value: str
    created_at: str
    expires_at: Optional[str] = None
    last_validated: Optional[str] = None
    validation_status: str = "unknown"
    usage_count: int = 0
    rotation_enabled: bool = False
    metadata: Dict[str, str] = field(default_factory=dict)


class CredentialManager:
    """
    Secure credential management system for AI providers.
    
    Features:
    - Encrypted storage of API keys
    - API key rotation and validation
    - Integration with Home Assistant secrets
    - Usage tracking and monitoring
    - Credential health monitoring
    """
    
    def __init__(self, config: Dict[str, any], data_path: str = "/data"):
        """
        Initialize credential manager.
        
        Args:
            config: Configuration dictionary
            data_path: Path for storing encrypted credentials
        """
        self.config = config
        self.data_path = data_path
        self.logger = logging.getLogger("ai_provider.credential_manager")
        
        # Initialize encryption
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        
        # Credential storage
        self.credentials_file = os.path.join(data_path, "ai_credentials.encrypted")
        self.credentials: Dict[str, Dict[str, any]] = {}
        
        # Validation cache
        self.validation_cache: Dict[str, Tuple[bool, datetime]] = {}
        self.cache_ttl = timedelta(hours=1)
        
        # Load existing credentials
        self._load_credentials()
        
        self.logger.info("Credential manager initialized")
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for credential storage"""
        key_file = os.path.join(self.data_path, "credential_key.key")
        
        if os.path.exists(key_file):
            try:
                with open(key_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                self.logger.error(f"Error reading encryption key: {e}")
        
        # Generate new key
        key = Fernet.generate_key()
        try:
            os.makedirs(self.data_path, exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Secure permissions
            self.logger.info("Created new encryption key for credentials")
        except Exception as e:
            self.logger.error(f"Error saving encryption key: {e}")
        
        return key
    
    def _load_credentials(self):
        """Load encrypted credentials from storage"""
        if not os.path.exists(self.credentials_file):
            return
        
        try:
            with open(self.credentials_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.fernet.decrypt(encrypted_data)
            self.credentials = json.loads(decrypted_data.decode())
            
            self.logger.info(f"Loaded {len(self.credentials)} credential entries")
            
        except Exception as e:
            self.logger.error(f"Error loading credentials: {e}")
            self.credentials = {}
    
    def _save_credentials(self):
        """Save credentials to encrypted storage"""
        try:
            os.makedirs(self.data_path, exist_ok=True)
            
            json_data = json.dumps(self.credentials, indent=2)
            encrypted_data = self.fernet.encrypt(json_data.encode())
            
            with open(self.credentials_file, 'wb') as f:
                f.write(encrypted_data)
            
            os.chmod(self.credentials_file, 0o600)  # Secure permissions
            self.logger.debug("Credentials saved to encrypted storage")
            
        except Exception as e:
            self.logger.error(f"Error saving credentials: {e}")
    
    def _mask_credential(self, credential: str) -> str:
        """Mask credential for logging/display"""
        if len(credential) <= 8:
            return "*" * len(credential)
        return credential[:4] + "*" * (len(credential) - 8) + credential[-4:]
    
    def store_credential(self, provider: str, credential_type: str, value: str,
                        expires_at: Optional[str] = None, metadata: Optional[Dict[str, str]] = None) -> bool:
        """
        Store a credential securely.
        
        Args:
            provider: Provider name (e.g., "openai", "anthropic")
            credential_type: Type of credential (e.g., "api_key", "secret")
            value: Credential value
            expires_at: Optional expiration timestamp
            metadata: Optional metadata
            
        Returns:
            True if stored successfully
        """
        try:
            credential_key = f"{provider}:{credential_type}"
            
            # Validate credential format
            if not self._validate_credential_format(provider, credential_type, value):
                self.logger.error(f"Invalid credential format for {credential_key}")
                return False
            
            # Store credential
            self.credentials[credential_key] = {
                "provider": provider,
                "credential_type": credential_type,
                "value": value,
                "created_at": datetime.now().isoformat(),
                "expires_at": expires_at,
                "last_validated": None,
                "validation_status": "unknown",
                "usage_count": 0,
                "rotation_enabled": False,
                "metadata": metadata or {}
            }
            
            self._save_credentials()
            
            self.logger.info(f"Stored credential: {credential_key} (masked: {self._mask_credential(value)})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing credential: {e}")
            return False
    
    def get_credential(self, provider: str, credential_type: str) -> Optional[str]:
        """
        Get a credential value.
        
        Args:
            provider: Provider name
            credential_type: Credential type
            
        Returns:
            Credential value or None if not found
        """
        credential_key = f"{provider}:{credential_type}"
        
        if credential_key not in self.credentials:
            # Try to get from Home Assistant secrets
            ha_secret = self._get_from_ha_secrets(provider, credential_type)
            if ha_secret:
                return ha_secret
            
            # Try to get from environment variables
            env_var = f"{provider.upper()}_{credential_type.upper()}"
            return os.getenv(env_var)
        
        credential = self.credentials[credential_key]
        
        # Check expiration
        if credential["expires_at"]:
            expires_at = datetime.fromisoformat(credential["expires_at"])
            if datetime.now() > expires_at:
                self.logger.warning(f"Credential expired: {credential_key}")
                return None
        
        # Update usage count
        credential["usage_count"] += 1
        self._save_credentials()
        
        return credential["value"]
    
    def _get_from_ha_secrets(self, provider: str, credential_type: str) -> Optional[str]:
        """Get credential from Home Assistant secrets"""
        try:
            # Try different naming conventions
            secret_names = [
                f"{provider}_{credential_type}",
                f"{provider.upper()}_{credential_type.upper()}",
                f"ai_{provider}_{credential_type}",
                f"AICLEANER_{provider.upper()}_{credential_type.upper()}"
            ]
            
            for secret_name in secret_names:
                secret_value = self.config.get(secret_name)
                if secret_value:
                    self.logger.debug(f"Retrieved credential from HA secrets: {secret_name}")
                    return secret_value
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving from HA secrets: {e}")
            return None
    
    def _validate_credential_format(self, provider: str, credential_type: str, value: str) -> bool:
        """Validate credential format based on provider requirements"""
        if not value or len(value) < 8:
            return False
        
        # Provider-specific validation
        if provider == "openai" and credential_type == "api_key":
            return value.startswith("sk-") and len(value) >= 48
        elif provider == "anthropic" and credential_type == "api_key":
            return value.startswith("sk-ant-") and len(value) >= 50
        elif provider == "google" and credential_type == "api_key":
            return len(value) >= 32 and value.isalnum()
        elif provider == "ollama" and credential_type == "api_key":
            return True  # Ollama might not require API key
        
        return True  # Default validation
    
    async def validate_credential(self, provider: str, credential_type: str, 
                                force_refresh: bool = False) -> bool:
        """
        Validate a credential by testing it with the provider.
        
        Args:
            provider: Provider name
            credential_type: Credential type
            force_refresh: Force validation even if cached
            
        Returns:
            True if credential is valid
        """
        credential_key = f"{provider}:{credential_type}"
        
        # Check cache first
        if not force_refresh and credential_key in self.validation_cache:
            result, timestamp = self.validation_cache[credential_key]
            if datetime.now() - timestamp < self.cache_ttl:
                return result
        
        # Get credential
        credential_value = self.get_credential(provider, credential_type)
        if not credential_value:
            self.logger.warning(f"No credential found for validation: {credential_key}")
            return False
        
        # Validate with provider
        try:
            is_valid = await self._validate_with_provider(provider, credential_value)
            
            # Update cache and stored credential
            self.validation_cache[credential_key] = (is_valid, datetime.now())
            
            if credential_key in self.credentials:
                self.credentials[credential_key]["last_validated"] = datetime.now().isoformat()
                self.credentials[credential_key]["validation_status"] = "valid" if is_valid else "invalid"
                self._save_credentials()
            
            self.logger.info(f"Credential validation result for {credential_key}: {is_valid}")
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Error validating credential {credential_key}: {e}")
            return False
    
    async def _validate_with_provider(self, provider: str, credential: str) -> bool:
        """Validate credential with the actual provider"""
        try:
            if provider == "openai":
                return await self._validate_openai_credential(credential)
            elif provider == "anthropic":
                return await self._validate_anthropic_credential(credential)
            elif provider == "google":
                return await self._validate_google_credential(credential)
            elif provider == "ollama":
                return await self._validate_ollama_credential(credential)
            else:
                self.logger.warning(f"Unknown provider for validation: {provider}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error validating {provider} credential: {e}")
            return False
    
    async def _validate_openai_credential(self, api_key: str) -> bool:
        """Validate OpenAI API key"""
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            
            # Make a simple request to validate
            response = await asyncio.to_thread(
                client.models.list
            )
            return bool(response.data)
            
        except Exception:
            return False
    
    async def _validate_anthropic_credential(self, api_key: str) -> bool:
        """Validate Anthropic API key"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            
            # Make a simple request to validate
            response = await asyncio.to_thread(
                client.messages.create,
                model="claude-3-haiku-20240307",
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}]
            )
            return bool(response.content)
            
        except Exception:
            return False
    
    async def _validate_google_credential(self, api_key: str) -> bool:
        """Validate Google API key"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            # Make a simple request to validate
            model = genai.GenerativeModel('gemini-pro')
            response = await asyncio.to_thread(
                model.generate_content,
                "test"
            )
            return bool(response.text)
            
        except Exception:
            return False
    
    async def _validate_ollama_credential(self, api_key: str) -> bool:
        """Validate Ollama connection"""
        try:
            import aiohttp
            
            # Ollama typically doesn't require API key, just check connection
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:11434/api/tags", timeout=5) as response:
                    return response.status == 200
                    
        except Exception:
            return False
    
    def list_credentials(self) -> List[CredentialInfo]:
        """List all stored credentials (masked)"""
        credentials = []
        
        for key, cred in self.credentials.items():
            credentials.append(CredentialInfo(
                provider=cred["provider"],
                credential_type=cred["credential_type"],
                masked_value=self._mask_credential(cred["value"]),
                created_at=cred["created_at"],
                expires_at=cred.get("expires_at"),
                last_validated=cred.get("last_validated"),
                validation_status=cred.get("validation_status", "unknown"),
                usage_count=cred.get("usage_count", 0),
                rotation_enabled=cred.get("rotation_enabled", False),
                metadata=cred.get("metadata", {})
            ))
        
        return credentials
    
    def delete_credential(self, provider: str, credential_type: str) -> bool:
        """Delete a stored credential"""
        credential_key = f"{provider}:{credential_type}"
        
        if credential_key in self.credentials:
            del self.credentials[credential_key]
            self._save_credentials()
            
            # Clear validation cache
            if credential_key in self.validation_cache:
                del self.validation_cache[credential_key]
            
            self.logger.info(f"Deleted credential: {credential_key}")
            return True
        
        return False
    
    async def rotate_credential(self, provider: str, credential_type: str) -> bool:
        """
        Rotate a credential (placeholder for future implementation).
        
        Args:
            provider: Provider name
            credential_type: Credential type
            
        Returns:
            True if rotation successful
        """
        # This would implement actual credential rotation
        # For now, just log the request
        self.logger.info(f"Credential rotation requested for {provider}:{credential_type}")
        
        # In a real implementation, this would:
        # 1. Generate new credential through provider API
        # 2. Test new credential
        # 3. Replace old credential
        # 4. Invalidate old credential
        
        return False
    
    def get_credential_stats(self) -> Dict[str, any]:
        """Get credential usage statistics"""
        stats = {
            "total_credentials": len(self.credentials),
            "by_provider": {},
            "validation_status": {},
            "expired_credentials": 0
        }
        
        for cred in self.credentials.values():
            provider = cred["provider"]
            status = cred.get("validation_status", "unknown")
            
            stats["by_provider"][provider] = stats["by_provider"].get(provider, 0) + 1
            stats["validation_status"][status] = stats["validation_status"].get(status, 0) + 1
            
            # Check for expired credentials
            if cred.get("expires_at"):
                expires_at = datetime.fromisoformat(cred["expires_at"])
                if datetime.now() > expires_at:
                    stats["expired_credentials"] += 1
        
        return stats
    
    async def health_check(self) -> Dict[str, any]:
        """Perform health check on all credentials"""
        health_report = {
            "overall_health": "healthy",
            "credential_count": len(self.credentials),
            "validation_results": {},
            "issues": []
        }
        
        for key, cred in self.credentials.items():
            provider = cred["provider"]
            credential_type = cred["credential_type"]
            
            try:
                is_valid = await self.validate_credential(provider, credential_type)
                health_report["validation_results"][key] = {
                    "valid": is_valid,
                    "last_validated": cred.get("last_validated"),
                    "usage_count": cred.get("usage_count", 0)
                }
                
                if not is_valid:
                    health_report["issues"].append(f"Invalid credential: {key}")
                    health_report["overall_health"] = "degraded"
                    
            except Exception as e:
                health_report["validation_results"][key] = {
                    "valid": False,
                    "error": str(e)
                }
                health_report["issues"].append(f"Validation error for {key}: {str(e)}")
                health_report["overall_health"] = "degraded"
        
        return health_report