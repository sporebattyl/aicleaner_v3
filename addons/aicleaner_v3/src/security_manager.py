"""
AICleaner v3 Security Manager
Implements hybrid security approach from "Intelligent Simplicity" design

Features:
- Automatic internal security (service keys, API authentication)
- Guided external security (API keys, secrets management)
- Integration with Home Assistant secrets
- Key rotation and validation
- Security monitoring and alerts
"""

import os
import secrets
import hashlib
import hmac
import asyncio
import logging
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class SecurityLevel(Enum):
    """Security monitoring levels"""
    BASIC = "basic"
    DETAILED = "detailed"
    EXPERT = "expert"


class KeyType(Enum):
    """Security key types"""
    INTERNAL_API = "internal_api"
    SERVICE_TOKEN = "service_token"
    ENCRYPTION_KEY = "encryption_key"
    WEBHOOK_SECRET = "webhook_secret"


@dataclass
class SecurityKey:
    """Security key information"""
    key_id: str
    key_type: KeyType
    created_at: datetime
    expires_at: Optional[datetime]
    rotation_interval_days: int
    last_used: Optional[datetime]
    usage_count: int
    is_active: bool


@dataclass
class SecurityEvent:
    """Security event for monitoring"""
    event_id: str
    event_type: str
    severity: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    source: str


class SecurityManager:
    """
    Hybrid security manager implementing "Intelligent Simplicity"
    
    Internal Security (Automatic):
    - Service-to-service authentication keys
    - Internal API tokens
    - Encryption keys for local data
    - Automatic key rotation
    
    External Security (Guided):
    - AI provider API keys
    - External webhook secrets
    - Integration with HA secrets
    - Validation and strength checking
    """
    
    def __init__(self, config_path: Path, config: Dict[str, Any] = None):
        self.config_path = config_path
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Security paths
        self.security_dir = config_path / "aicleaner" / "security"
        self.keys_dir = self.security_dir / "keys"
        self.secrets_file = self.security_dir / "secrets.yaml"
        self.events_file = self.security_dir / "security_events.json"
        
        # Security state
        self.active_keys: Dict[str, SecurityKey] = {}
        self.external_secrets: Dict[str, str] = {}
        self.security_events: List[SecurityEvent] = []
        self.monitoring_level = SecurityLevel.BASIC
        
        # Encryption components
        self._master_key: Optional[bytes] = None
        self._fernet: Optional[Fernet] = None
        
        # Configuration
        self.key_rotation_enabled = self.config.get("key_rotation_enabled", True)
        self.default_rotation_days = self.config.get("default_rotation_days", 30)
        self.max_key_age_days = self.config.get("max_key_age_days", 90)
        
        # Initialize directories
        self._initialize_security_structure()
    
    def _initialize_security_structure(self) -> None:
        """Initialize security directory structure"""
        try:
            self.security_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.keys_dir.mkdir(exist_ok=True, mode=0o700)
            
            # Set directory permissions
            os.chmod(self.security_dir, 0o700)
            os.chmod(self.keys_dir, 0o700)
            
        except Exception as e:
            self.logger.error(f"Failed to initialize security structure: {e}")
            raise
    
    async def initialize(self) -> None:
        """Initialize the security manager"""
        try:
            self.logger.info("Initializing security manager")
            
            # Initialize master encryption key
            await self._initialize_master_key()
            
            # Load existing keys
            await self._load_existing_keys()
            
            # Load external secrets
            await self._load_external_secrets()
            
            # Generate required internal keys if missing
            await self._ensure_internal_keys()
            
            # Start background tasks
            if self.key_rotation_enabled:
                asyncio.create_task(self._key_rotation_loop())
            
            asyncio.create_task(self._security_monitoring_loop())
            
            self.logger.info("Security manager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize security manager: {e}")
            raise
    
    # Internal Security Management (Automatic)
    
    async def generate_internal_key(self, key_type: KeyType, 
                                   rotation_days: Optional[int] = None) -> str:
        """Generate a new internal security key"""
        try:
            if rotation_days is None:
                rotation_days = self.default_rotation_days
            
            # Generate secure key
            if key_type in [KeyType.INTERNAL_API, KeyType.SERVICE_TOKEN]:
                key_value = secrets.token_urlsafe(32)
            elif key_type == KeyType.ENCRYPTION_KEY:
                key_value = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
            elif key_type == KeyType.WEBHOOK_SECRET:
                key_value = secrets.token_hex(32)
            else:
                raise ValueError(f"Unknown key type: {key_type}")
            
            # Create key metadata
            key_id = secrets.token_hex(8)
            security_key = SecurityKey(
                key_id=key_id,
                key_type=key_type,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=rotation_days) if rotation_days > 0 else None,
                rotation_interval_days=rotation_days,
                last_used=None,
                usage_count=0,
                is_active=True
            )
            
            # Store encrypted key
            await self._store_key(key_id, key_value, security_key)
            
            # Track active key
            self.active_keys[key_id] = security_key
            
            # Log security event
            await self._log_security_event(
                "key_generated",
                "info",
                f"Generated new {key_type.value} key",
                {"key_id": key_id, "key_type": key_type.value},
                "security_manager"
            )
            
            self.logger.info(f"Generated new {key_type.value} key: {key_id}")
            return key_id
            
        except Exception as e:
            self.logger.error(f"Failed to generate {key_type.value} key: {e}")
            raise
    
    async def get_internal_key(self, key_id: str) -> Optional[str]:
        """Get an internal key by ID"""
        try:
            if key_id not in self.active_keys:
                return None
            
            security_key = self.active_keys[key_id]
            
            # Check if key is expired
            if security_key.expires_at and datetime.now() > security_key.expires_at:
                self.logger.warning(f"Attempted to use expired key: {key_id}")
                return None
            
            # Load key value
            key_value = await self._load_key(key_id)
            
            # Update usage statistics
            security_key.last_used = datetime.now()
            security_key.usage_count += 1
            
            return key_value
            
        except Exception as e:
            self.logger.error(f"Failed to get key {key_id}: {e}")
            return None
    
    async def rotate_key(self, key_id: str) -> Optional[str]:
        """Rotate an internal key"""
        try:
            if key_id not in self.active_keys:
                self.logger.error(f"Cannot rotate non-existent key: {key_id}")
                return None
            
            old_key = self.active_keys[key_id]
            
            # Generate new key of the same type
            new_key_id = await self.generate_internal_key(
                old_key.key_type,
                old_key.rotation_interval_days
            )
            
            # Deactivate old key
            old_key.is_active = False
            
            # Log rotation event
            await self._log_security_event(
                "key_rotated",
                "info",
                f"Rotated {old_key.key_type.value} key",
                {"old_key_id": key_id, "new_key_id": new_key_id},
                "security_manager"
            )
            
            self.logger.info(f"Rotated key {key_id} -> {new_key_id}")
            return new_key_id
            
        except Exception as e:
            self.logger.error(f"Failed to rotate key {key_id}: {e}")
            return None
    
    # External Security Management (Guided)
    
    async def validate_external_secret(self, secret_name: str, secret_value: str) -> Dict[str, Any]:
        """Validate an external secret (API key, etc.)"""
        validation_result = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "strength_score": 0,
            "recommendations": []
        }
        
        try:
            # Basic validation
            if not secret_value or len(secret_value) < 8:
                validation_result["valid"] = False
                validation_result["errors"].append("Secret is too short (minimum 8 characters)")
                return validation_result
            
            # Strength assessment
            strength_score = self._assess_secret_strength(secret_value)
            validation_result["strength_score"] = strength_score
            
            if strength_score < 30:
                validation_result["warnings"].append("Secret appears weak")
                validation_result["recommendations"].append("Use a stronger secret with more entropy")
            
            # Format-specific validation
            if "openai" in secret_name.lower():
                if not secret_value.startswith("sk-"):
                    validation_result["warnings"].append("OpenAI API key should start with 'sk-'")
            elif "anthropic" in secret_name.lower():
                if not secret_value.startswith("sk-ant-"):
                    validation_result["warnings"].append("Anthropic API key should start with 'sk-ant-'")
            elif "google" in secret_name.lower() or "gemini" in secret_name.lower():
                if len(secret_value) < 32:
                    validation_result["warnings"].append("Google API key appears shorter than expected")
            
            # Common security issues
            if secret_value.lower() in ["password", "secret", "key", "token"]:
                validation_result["valid"] = False
                validation_result["errors"].append("Secret contains common weak values")
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Failed to validate secret {secret_name}: {e}")
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")
            return validation_result
    
    async def store_external_secret(self, secret_name: str, secret_value: str, 
                                   validate: bool = True) -> bool:
        """Store an external secret securely"""
        try:
            # Validate if requested
            if validate:
                validation_result = await self.validate_external_secret(secret_name, secret_value)
                if not validation_result["valid"]:
                    self.logger.error(f"Cannot store invalid secret {secret_name}: {validation_result['errors']}")
                    return False
                
                # Log warnings
                for warning in validation_result["warnings"]:
                    self.logger.warning(f"Secret {secret_name}: {warning}")
            
            # Encrypt and store secret
            encrypted_value = self._encrypt_data(secret_value)
            self.external_secrets[secret_name] = encrypted_value
            
            # Save to file
            await self._save_external_secrets()
            
            # Log security event
            await self._log_security_event(
                "external_secret_stored",
                "info",
                f"Stored external secret: {secret_name}",
                {"secret_name": secret_name},
                "security_manager"
            )
            
            self.logger.info(f"Stored external secret: {secret_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store secret {secret_name}: {e}")
            return False
    
    async def get_external_secret(self, secret_name: str) -> Optional[str]:
        """Get an external secret"""
        try:
            if secret_name not in self.external_secrets:
                return None
            
            # Decrypt and return
            encrypted_value = self.external_secrets[secret_name]
            decrypted_value = self._decrypt_data(encrypted_value)
            
            return decrypted_value
            
        except Exception as e:
            self.logger.error(f"Failed to get secret {secret_name}: {e}")
            return None
    
    # Home Assistant Integration
    
    async def integrate_with_ha_secrets(self) -> Dict[str, Any]:
        """Integrate with Home Assistant secrets system"""
        integration_result = {
            "success": False,
            "secrets_found": 0,
            "secrets_imported": 0,
            "errors": []
        }
        
        try:
            # Look for secrets.yaml in HA config
            ha_secrets_file = self.config_path.parent / "secrets.yaml"
            
            if not ha_secrets_file.exists():
                self.logger.info("No Home Assistant secrets.yaml found")
                integration_result["success"] = True
                return integration_result
            
            # Load HA secrets
            with open(ha_secrets_file, 'r') as f:
                ha_secrets = yaml.safe_load(f) or {}
            
            integration_result["secrets_found"] = len(ha_secrets)
            
            # Import relevant secrets
            ai_related_keys = [
                "openai_api_key", "anthropic_api_key", "google_api_key", 
                "gemini_api_key", "ollama_api_key", "aicleaner_api_key"
            ]
            
            imported_count = 0
            for secret_name, secret_value in ha_secrets.items():
                if any(key in secret_name.lower() for key in ["openai", "anthropic", "google", "gemini", "ai"]):
                    success = await self.store_external_secret(secret_name, secret_value, validate=True)
                    if success:
                        imported_count += 1
                    else:
                        integration_result["errors"].append(f"Failed to import {secret_name}")
            
            integration_result["secrets_imported"] = imported_count
            integration_result["success"] = True
            
            self.logger.info(f"Imported {imported_count}/{integration_result['secrets_found']} HA secrets")
            
        except Exception as e:
            self.logger.error(f"Failed to integrate with HA secrets: {e}")
            integration_result["errors"].append(str(e))
        
        return integration_result
    
    # Security Monitoring
    
    async def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status"""
        try:
            # Count keys by type and status
            key_stats = {}
            for key in self.active_keys.values():
                key_type = key.key_type.value
                if key_type not in key_stats:
                    key_stats[key_type] = {"active": 0, "expired": 0, "total": 0}
                
                key_stats[key_type]["total"] += 1
                
                if key.is_active:
                    if key.expires_at and datetime.now() > key.expires_at:
                        key_stats[key_type]["expired"] += 1
                    else:
                        key_stats[key_type]["active"] += 1
            
            # Check for keys needing rotation
            keys_needing_rotation = []
            for key_id, key in self.active_keys.items():
                if key.expires_at and key.expires_at < datetime.now() + timedelta(days=7):
                    keys_needing_rotation.append(key_id)
            
            # Count external secrets
            external_secret_count = len(self.external_secrets)
            
            # Recent security events
            recent_events = [
                event for event in self.security_events
                if event.timestamp > datetime.now() - timedelta(hours=24)
            ]
            
            return {
                "monitoring_level": self.monitoring_level.value,
                "key_statistics": key_stats,
                "external_secrets": external_secret_count,
                "keys_needing_rotation": len(keys_needing_rotation),
                "recent_events": len(recent_events),
                "key_rotation_enabled": self.key_rotation_enabled,
                "last_rotation_check": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get security status: {e}")
            return {"error": str(e)}
    
    # Helper Methods
    
    async def _initialize_master_key(self) -> None:
        """Initialize master encryption key"""
        master_key_file = self.keys_dir / "master.key"
        
        if master_key_file.exists():
            # Load existing master key
            self._master_key = master_key_file.read_bytes()
        else:
            # Generate new master key
            self._master_key = secrets.token_bytes(32)
            master_key_file.write_bytes(self._master_key)
            os.chmod(master_key_file, 0o600)
        
        # Initialize Fernet cipher
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'aicleaner_v3_salt',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self._master_key))
        self._fernet = Fernet(key)
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt data using master key"""
        if not self._fernet:
            raise RuntimeError("Master key not initialized")
        
        encrypted_bytes = self._fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_bytes).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data using master key"""
        if not self._fernet:
            raise RuntimeError("Master key not initialized")
        
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
        return decrypted_bytes.decode()
    
    def _assess_secret_strength(self, secret: str) -> int:
        """Assess secret strength (0-100 score)"""
        score = 0
        
        # Length bonus
        score += min(len(secret) * 2, 40)
        
        # Character variety
        has_upper = any(c.isupper() for c in secret)
        has_lower = any(c.islower() for c in secret)
        has_digit = any(c.isdigit() for c in secret)
        has_special = any(not c.isalnum() for c in secret)
        
        score += sum([has_upper, has_lower, has_digit, has_special]) * 15
        
        # Entropy estimation (simple)
        unique_chars = len(set(secret))
        score += min(unique_chars * 2, 20)
        
        return min(score, 100)
    
    async def _store_key(self, key_id: str, key_value: str, security_key: SecurityKey) -> None:
        """Store encrypted key and metadata"""
        # Encrypt key value
        encrypted_key = self._encrypt_data(key_value)
        
        # Store encrypted key
        key_file = self.keys_dir / f"{key_id}.key"
        key_file.write_text(encrypted_key)
        os.chmod(key_file, 0o600)
        
        # Store metadata
        metadata_file = self.keys_dir / f"{key_id}.meta"
        metadata = {
            "key_id": security_key.key_id,
            "key_type": security_key.key_type.value,
            "created_at": security_key.created_at.isoformat(),
            "expires_at": security_key.expires_at.isoformat() if security_key.expires_at else None,
            "rotation_interval_days": security_key.rotation_interval_days,
            "is_active": security_key.is_active
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        os.chmod(metadata_file, 0o600)
    
    async def _load_key(self, key_id: str) -> str:
        """Load and decrypt key"""
        key_file = self.keys_dir / f"{key_id}.key"
        
        if not key_file.exists():
            raise FileNotFoundError(f"Key file not found: {key_id}")
        
        encrypted_key = key_file.read_text()
        return self._decrypt_data(encrypted_key)
    
    async def _load_existing_keys(self) -> None:
        """Load existing key metadata"""
        for meta_file in self.keys_dir.glob("*.meta"):
            try:
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                
                # Reconstruct SecurityKey object
                security_key = SecurityKey(
                    key_id=metadata["key_id"],
                    key_type=KeyType(metadata["key_type"]),
                    created_at=datetime.fromisoformat(metadata["created_at"]),
                    expires_at=datetime.fromisoformat(metadata["expires_at"]) if metadata.get("expires_at") else None,
                    rotation_interval_days=metadata["rotation_interval_days"],
                    last_used=None,
                    usage_count=0,
                    is_active=metadata["is_active"]
                )
                
                self.active_keys[metadata["key_id"]] = security_key
                
            except Exception as e:
                self.logger.error(f"Failed to load key metadata from {meta_file}: {e}")
    
    async def _load_external_secrets(self) -> None:
        """Load external secrets from file"""
        if self.secrets_file.exists():
            try:
                with open(self.secrets_file, 'r') as f:
                    self.external_secrets = yaml.safe_load(f) or {}
            except Exception as e:
                self.logger.error(f"Failed to load external secrets: {e}")
    
    async def _save_external_secrets(self) -> None:
        """Save external secrets to file"""
        try:
            with open(self.secrets_file, 'w') as f:
                yaml.dump(self.external_secrets, f, default_flow_style=False)
            
            os.chmod(self.secrets_file, 0o600)
            
        except Exception as e:
            self.logger.error(f"Failed to save external secrets: {e}")
    
    async def _ensure_internal_keys(self) -> None:
        """Ensure required internal keys exist"""
        required_keys = [
            KeyType.INTERNAL_API,
            KeyType.SERVICE_TOKEN,
            KeyType.ENCRYPTION_KEY,
            KeyType.WEBHOOK_SECRET
        ]
        
        for key_type in required_keys:
            # Check if we have an active key of this type
            has_active_key = any(
                key.key_type == key_type and key.is_active 
                for key in self.active_keys.values()
            )
            
            if not has_active_key:
                await self.generate_internal_key(key_type)
    
    async def _log_security_event(self, event_type: str, severity: str, 
                                message: str, details: Dict[str, Any], source: str) -> None:
        """Log a security event"""
        event = SecurityEvent(
            event_id=secrets.token_hex(8),
            event_type=event_type,
            severity=severity,
            message=message,
            details=details,
            timestamp=datetime.now(),
            source=source
        )
        
        self.security_events.append(event)
        
        # Maintain event history (keep last 1000 events)
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]
        
        # Save to file (async)
        asyncio.create_task(self._save_security_events())
    
    async def _save_security_events(self) -> None:
        """Save security events to file"""
        try:
            events_data = [
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "severity": event.severity,
                    "message": event.message,
                    "details": event.details,
                    "timestamp": event.timestamp.isoformat(),
                    "source": event.source
                }
                for event in self.security_events
            ]
            
            with open(self.events_file, 'w') as f:
                json.dump(events_data, f, indent=2)
            
            os.chmod(self.events_file, 0o600)
            
        except Exception as e:
            self.logger.error(f"Failed to save security events: {e}")
    
    async def _key_rotation_loop(self) -> None:
        """Background task for key rotation"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                # Check for keys needing rotation
                for key_id, key in self.active_keys.items():
                    if (key.is_active and key.expires_at and 
                        datetime.now() > key.expires_at):
                        
                        self.logger.info(f"Auto-rotating expired key: {key_id}")
                        await self.rotate_key(key_id)
                
            except Exception as e:
                self.logger.error(f"Key rotation loop error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
    
    async def _security_monitoring_loop(self) -> None:
        """Background task for security monitoring"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Monitor for security issues
                await self._check_security_health()
                
            except Exception as e:
                self.logger.error(f"Security monitoring loop error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    async def _check_security_health(self) -> None:
        """Check overall security health"""
        # Check for expired keys
        expired_keys = [
            key_id for key_id, key in self.active_keys.items()
            if key.is_active and key.expires_at and datetime.now() > key.expires_at
        ]
        
        if expired_keys:
            await self._log_security_event(
                "expired_keys_detected",
                "warning",
                f"Found {len(expired_keys)} expired keys",
                {"expired_key_ids": expired_keys},
                "security_monitor"
            )
        
        # Check file permissions
        security_files = list(self.keys_dir.glob("*")) + [self.secrets_file]
        
        for file_path in security_files:
            if file_path.exists():
                file_stat = file_path.stat()
                if file_stat.st_mode & 0o077:
                    await self._log_security_event(
                        "insecure_permissions",
                        "warning",
                        f"Security file has overly permissive permissions: {file_path}",
                        {"file_path": str(file_path), "permissions": oct(file_stat.st_mode)},
                        "security_monitor"
                    )