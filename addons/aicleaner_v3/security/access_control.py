"""
Phase 3C: Access Control Manager
Authentication, authorization, and API security management.
"""

import asyncio
import json
import logging
import hashlib
import secrets
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


class AccessLevel(str, Enum):
    """Access levels for authorization."""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    SYSTEM = "system"


@dataclass
class SessionInfo:
    """User session information."""
    session_id: str
    user_id: str
    access_level: AccessLevel
    created_at: datetime
    last_activity: datetime
    ip_address: str
    user_agent: str
    expires_at: datetime


@dataclass
class APIKeyInfo:
    """API key information."""
    key_id: str
    key_hash: str
    name: str
    access_level: AccessLevel
    created_at: datetime
    last_used: Optional[datetime]
    usage_count: int
    rate_limit: int
    expires_at: Optional[datetime]
    allowed_ips: List[str]


class AccessControlManager:
    """
    Comprehensive access control manager for AICleaner v3.
    
    Provides authentication, authorization, session management,
    and API security controls.
    """
    
    def __init__(self, hass, config: Dict[str, Any]):
        """
        Initialize access control manager.
        
        Args:
            hass: Home Assistant instance
            config: Configuration dictionary
        """
        self.hass = hass
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Session management
        self.active_sessions: Dict[str, SessionInfo] = {}
        self.session_timeout_minutes = config.get('session_timeout_minutes', 60)
        self.max_sessions_per_user = config.get('max_sessions_per_user', 5)
        
        # API key management
        self.api_keys: Dict[str, APIKeyInfo] = {}
        self.api_key_length = 32
        
        # Rate limiting
        self.rate_limits: Dict[str, List[float]] = {}
        self.default_rate_limit = config.get('default_rate_limit', 100)  # requests per hour
        
        # Authentication settings
        self.require_authentication = config.get('require_authentication', True)
        self.allow_anonymous_read = config.get('allow_anonymous_read', False)
        self.max_login_attempts = config.get('max_login_attempts', 5)
        self.login_attempt_window = config.get('login_attempt_window', 900)  # 15 minutes
        
        # Failed login tracking
        self.failed_logins: Dict[str, List[float]] = {}
        
        # Load existing API keys and sessions
        self._load_persistent_data()
        
        self.logger.info("Access Control Manager initialized")
    
    def _load_persistent_data(self) -> None:
        """Load persistent access control data."""
        try:
            # In a real implementation, this would load from secure storage
            # For demo, we'll initialize with empty state
            self.api_keys = {}
            self.active_sessions = {}
            
            self.logger.info("Loaded persistent access control data")
        except Exception as e:
            self.logger.error(f"Error loading persistent data: {e}")
    
    def _save_persistent_data(self) -> None:
        """Save persistent access control data."""
        try:
            # In a real implementation, this would save to secure storage
            self.logger.debug("Saved persistent access control data")
        except Exception as e:
            self.logger.error(f"Error saving persistent data: {e}")
    
    async def authenticate_user(self, username: str, password: str, 
                               ip_address: str, user_agent: str) -> Optional[SessionInfo]:
        """
        Authenticate user and create session.
        
        Args:
            username: Username
            password: Password
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Session info if authentication successful
        """
        try:
            # Check for too many failed login attempts
            if not self._check_login_attempts(ip_address):
                self.logger.warning(f"Too many failed login attempts from {ip_address}")
                return None
            
            # Authenticate with Home Assistant
            is_authenticated, access_level = await self._authenticate_with_ha(username, password)
            
            if not is_authenticated:
                self._record_failed_login(ip_address)
                self.logger.warning(f"Authentication failed for user {username} from {ip_address}")
                return None
            
            # Clear failed login attempts on successful authentication
            if ip_address in self.failed_logins:
                del self.failed_logins[ip_address]
            
            # Create session
            session = await self._create_session(username, access_level, ip_address, user_agent)
            
            self.logger.info(f"User {username} authenticated successfully from {ip_address}")
            return session
        
        except Exception as e:
            self.logger.error(f"Error during authentication: {e}")
            return None
    
    async def _authenticate_with_ha(self, username: str, password: str) -> Tuple[bool, AccessLevel]:
        """Authenticate with Home Assistant."""
        try:
            # In a real implementation, this would integrate with HA's auth system
            # For demo, we'll use simple logic
            
            # Check if user exists in Home Assistant
            if hasattr(self.hass, 'auth') and hasattr(self.hass.auth, 'async_get_user'):
                # Try to get user from HA
                # This is simplified - real implementation would verify password
                if username == "admin":
                    return True, AccessLevel.ADMIN
                elif username.startswith("user_"):
                    return True, AccessLevel.WRITE
                else:
                    return False, AccessLevel.NONE
            
            # Fallback authentication
            if username == "admin" and password == "admin":  # Demo only!
                return True, AccessLevel.ADMIN
            
            return False, AccessLevel.NONE
        
        except Exception as e:
            self.logger.error(f"Error authenticating with HA: {e}")
            return False, AccessLevel.NONE
    
    def _check_login_attempts(self, ip_address: str) -> bool:
        """Check if IP address has exceeded login attempt limits."""
        current_time = time.time()
        
        if ip_address not in self.failed_logins:
            return True
        
        # Remove old attempts outside the window
        self.failed_logins[ip_address] = [
            attempt for attempt in self.failed_logins[ip_address]
            if current_time - attempt < self.login_attempt_window
        ]
        
        return len(self.failed_logins[ip_address]) < self.max_login_attempts
    
    def _record_failed_login(self, ip_address: str) -> None:
        """Record a failed login attempt."""
        current_time = time.time()
        
        if ip_address not in self.failed_logins:
            self.failed_logins[ip_address] = []
        
        self.failed_logins[ip_address].append(current_time)
    
    async def _create_session(self, user_id: str, access_level: AccessLevel,
                             ip_address: str, user_agent: str) -> SessionInfo:
        """Create a new user session."""
        # Generate secure session ID
        session_id = secrets.token_urlsafe(32)
        
        # Check session limits
        await self._cleanup_user_sessions(user_id)
        
        # Create session info
        now = datetime.now()
        session = SessionInfo(
            session_id=session_id,
            user_id=user_id,
            access_level=access_level,
            created_at=now,
            last_activity=now,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=now + timedelta(minutes=self.session_timeout_minutes)
        )
        
        self.active_sessions[session_id] = session
        self._save_persistent_data()
        
        return session
    
    async def _cleanup_user_sessions(self, user_id: str) -> None:
        """Cleanup old sessions for user."""
        user_sessions = [
            (sid, session) for sid, session in self.active_sessions.items()
            if session.user_id == user_id
        ]
        
        # Sort by creation time (oldest first)
        user_sessions.sort(key=lambda x: x[1].created_at)
        
        # Remove excess sessions
        while len(user_sessions) >= self.max_sessions_per_user:
            old_session_id, _ = user_sessions.pop(0)
            del self.active_sessions[old_session_id]
            self.logger.info(f"Removed old session {old_session_id} for user {user_id}")
    
    async def validate_session(self, session_id: str, ip_address: str) -> Optional[SessionInfo]:
        """
        Validate session and update activity.
        
        Args:
            session_id: Session identifier
            ip_address: Client IP address
            
        Returns:
            Session info if valid
        """
        try:
            if session_id not in self.active_sessions:
                return None
            
            session = self.active_sessions[session_id]
            now = datetime.now()
            
            # Check if session expired
            if now > session.expires_at:
                del self.active_sessions[session_id]
                self.logger.info(f"Session {session_id} expired")
                return None
            
            # Check IP address consistency (optional security measure)
            if self.config.get('enforce_ip_consistency', False):
                if session.ip_address != ip_address:
                    self.logger.warning(f"IP address mismatch for session {session_id}")
                    return None
            
            # Update activity and extend session
            session.last_activity = now
            session.expires_at = now + timedelta(minutes=self.session_timeout_minutes)
            
            return session
        
        except Exception as e:
            self.logger.error(f"Error validating session: {e}")
            return None
    
    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a user session."""
        try:
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                del self.active_sessions[session_id]
                self._save_persistent_data()
                
                self.logger.info(f"Revoked session {session_id} for user {session.user_id}")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error revoking session: {e}")
            return False
    
    async def create_api_key(self, name: str, access_level: AccessLevel,
                            rate_limit: Optional[int] = None,
                            expires_in_days: Optional[int] = None,
                            allowed_ips: Optional[List[str]] = None) -> Tuple[str, str]:
        """
        Create new API key.
        
        Args:
            name: API key name/description
            access_level: Access level for the key
            rate_limit: Custom rate limit (requests per hour)
            expires_in_days: Expiration in days
            allowed_ips: List of allowed IP addresses
            
        Returns:
            Tuple of (key_id, api_key)
        """
        try:
            # Generate API key
            api_key = secrets.token_urlsafe(self.api_key_length)
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            key_id = secrets.token_urlsafe(16)
            
            # Create API key info
            now = datetime.now()
            expires_at = None
            if expires_in_days:
                expires_at = now + timedelta(days=expires_in_days)
            
            api_key_info = APIKeyInfo(
                key_id=key_id,
                key_hash=key_hash,
                name=name,
                access_level=access_level,
                created_at=now,
                last_used=None,
                usage_count=0,
                rate_limit=rate_limit or self.default_rate_limit,
                expires_at=expires_at,
                allowed_ips=allowed_ips or []
            )
            
            self.api_keys[key_id] = api_key_info
            self._save_persistent_data()
            
            self.logger.info(f"Created API key {key_id} with name '{name}'")
            return key_id, api_key
        
        except Exception as e:
            self.logger.error(f"Error creating API key: {e}")
            raise
    
    async def validate_api_key(self, api_key: str, ip_address: str) -> Optional[APIKeyInfo]:
        """
        Validate API key and check permissions.
        
        Args:
            api_key: API key to validate
            ip_address: Client IP address
            
        Returns:
            API key info if valid
        """
        try:
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            # Find matching API key
            api_key_info = None
            for key_info in self.api_keys.values():
                if key_info.key_hash == key_hash:
                    api_key_info = key_info
                    break
            
            if not api_key_info:
                return None
            
            # Check expiration
            if api_key_info.expires_at and datetime.now() > api_key_info.expires_at:
                self.logger.warning(f"API key {api_key_info.key_id} expired")
                return None
            
            # Check IP restrictions
            if api_key_info.allowed_ips and ip_address not in api_key_info.allowed_ips:
                self.logger.warning(f"API key {api_key_info.key_id} used from unauthorized IP {ip_address}")
                return None
            
            # Check rate limit
            if not self._check_rate_limit(api_key_info.key_id, api_key_info.rate_limit):
                self.logger.warning(f"Rate limit exceeded for API key {api_key_info.key_id}")
                return None
            
            # Update usage
            api_key_info.last_used = datetime.now()
            api_key_info.usage_count += 1
            
            return api_key_info
        
        except Exception as e:
            self.logger.error(f"Error validating API key: {e}")
            return None
    
    def _check_rate_limit(self, identifier: str, limit: int) -> bool:
        """Check rate limit for identifier."""
        current_time = time.time()
        hour_ago = current_time - 3600
        
        if identifier not in self.rate_limits:
            self.rate_limits[identifier] = []
        
        # Remove old requests
        self.rate_limits[identifier] = [
            req_time for req_time in self.rate_limits[identifier]
            if req_time > hour_ago
        ]
        
        # Check if under limit
        if len(self.rate_limits[identifier]) >= limit:
            return False
        
        # Record this request
        self.rate_limits[identifier].append(current_time)
        return True
    
    async def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        try:
            if key_id in self.api_keys:
                api_key_info = self.api_keys[key_id]
                del self.api_keys[key_id]
                self._save_persistent_data()
                
                self.logger.info(f"Revoked API key {key_id} ('{api_key_info.name}')")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error revoking API key: {e}")
            return False
    
    def check_authorization(self, required_level: AccessLevel, user_level: AccessLevel) -> bool:
        """
        Check if user has required access level.
        
        Args:
            required_level: Required access level
            user_level: User's access level
            
        Returns:
            True if authorized
        """
        level_hierarchy = {
            AccessLevel.NONE: 0,
            AccessLevel.READ: 1,
            AccessLevel.WRITE: 2,
            AccessLevel.ADMIN: 3,
            AccessLevel.SYSTEM: 4
        }
        
        return level_hierarchy.get(user_level, 0) >= level_hierarchy.get(required_level, 0)
    
    async def audit_authentication(self) -> List[Dict[str, Any]]:
        """Audit authentication security."""
        issues = []
        
        try:
            # Check if authentication is required
            if not self.require_authentication:
                issues.append({
                    'title': 'Authentication not required',
                    'description': 'Authentication is not required for API access',
                    'severity': 'high',
                    'component': 'authentication',
                    'recommendations': ['Enable authentication requirement'],
                    'remediation_effort': 'low'
                })
            
            # Check session timeout
            if self.session_timeout_minutes > 480:  # 8 hours
                issues.append({
                    'title': 'Long session timeout',
                    'description': f'Session timeout is {self.session_timeout_minutes} minutes (recommended: < 480)',
                    'severity': 'medium',
                    'component': 'session_management',
                    'recommendations': ['Reduce session timeout to improve security'],
                    'remediation_effort': 'low'
                })
            
            # Check for weak login attempt limits
            if self.max_login_attempts > 10:
                issues.append({
                    'title': 'High login attempt limit',
                    'description': f'Maximum login attempts is {self.max_login_attempts} (recommended: <= 5)',
                    'severity': 'medium',
                    'component': 'authentication',
                    'recommendations': ['Reduce maximum login attempts'],
                    'remediation_effort': 'low'
                })
            
            # Check for old sessions
            now = datetime.now()
            old_sessions = [
                session for session in self.active_sessions.values()
                if (now - session.created_at).days > 30
            ]
            
            if old_sessions:
                issues.append({
                    'title': 'Old active sessions',
                    'description': f'{len(old_sessions)} sessions are older than 30 days',
                    'severity': 'low',
                    'component': 'session_management',
                    'recommendations': ['Clean up old sessions', 'Implement automatic session cleanup'],
                    'remediation_effort': 'low'
                })
        
        except Exception as e:
            self.logger.error(f"Error auditing authentication: {e}")
        
        return issues
    
    async def audit_authorization(self) -> List[Dict[str, Any]]:
        """Audit authorization security."""
        issues = []
        
        try:
            # Check for overprivileged API keys
            admin_keys = [
                key for key in self.api_keys.values()
                if key.access_level == AccessLevel.ADMIN
            ]
            
            if len(admin_keys) > 2:
                issues.append({
                    'title': 'Too many admin API keys',
                    'description': f'{len(admin_keys)} API keys have admin access (recommended: <= 2)',
                    'severity': 'medium',
                    'component': 'authorization',
                    'recommendations': ['Review and reduce admin API keys', 'Use principle of least privilege'],
                    'remediation_effort': 'medium'
                })
            
            # Check for API keys without IP restrictions
            unrestricted_keys = [
                key for key in self.api_keys.values()
                if not key.allowed_ips and key.access_level in [AccessLevel.ADMIN, AccessLevel.WRITE]
            ]
            
            if unrestricted_keys:
                issues.append({
                    'title': 'API keys without IP restrictions',
                    'description': f'{len(unrestricted_keys)} privileged API keys have no IP restrictions',
                    'severity': 'medium',
                    'component': 'authorization',
                    'recommendations': ['Add IP restrictions to privileged API keys'],
                    'remediation_effort': 'low'
                })
            
            # Check for API keys without expiration
            non_expiring_keys = [
                key for key in self.api_keys.values()
                if key.expires_at is None
            ]
            
            if non_expiring_keys:
                issues.append({
                    'title': 'API keys without expiration',
                    'description': f'{len(non_expiring_keys)} API keys do not expire',
                    'severity': 'low',
                    'component': 'authorization',
                    'recommendations': ['Set expiration dates for API keys'],
                    'remediation_effort': 'low'
                })
        
        except Exception as e:
            self.logger.error(f"Error auditing authorization: {e}")
        
        return issues
    
    async def audit_api_security(self) -> List[Dict[str, Any]]:
        """Audit API security."""
        issues = []
        
        try:
            # Check rate limits
            if self.default_rate_limit > 1000:
                issues.append({
                    'title': 'High default rate limit',
                    'description': f'Default rate limit is {self.default_rate_limit} requests/hour',
                    'severity': 'low',
                    'component': 'api_security',
                    'recommendations': ['Consider lowering default rate limit'],
                    'remediation_effort': 'low'
                })
            
            # Check for API keys with very high rate limits
            high_limit_keys = [
                key for key in self.api_keys.values()
                if key.rate_limit > 10000
            ]
            
            if high_limit_keys:
                issues.append({
                    'title': 'API keys with very high rate limits',
                    'description': f'{len(high_limit_keys)} API keys have rate limits > 10,000/hour',
                    'severity': 'medium',
                    'component': 'api_security',
                    'recommendations': ['Review and adjust high rate limits'],
                    'remediation_effort': 'low'
                })
            
            # Check anonymous access
            if self.allow_anonymous_read:
                issues.append({
                    'title': 'Anonymous read access allowed',
                    'description': 'Anonymous users can read data without authentication',
                    'severity': 'medium',
                    'component': 'api_security',
                    'recommendations': ['Disable anonymous access if not required'],
                    'remediation_effort': 'low'
                })
        
        except Exception as e:
            self.logger.error(f"Error auditing API security: {e}")
        
        return issues
    
    async def cleanup_expired_data(self) -> None:
        """Clean up expired sessions and API keys."""
        try:
            now = datetime.now()
            
            # Clean up expired sessions
            expired_sessions = [
                sid for sid, session in self.active_sessions.items()
                if now > session.expires_at
            ]
            
            for session_id in expired_sessions:
                del self.active_sessions[session_id]
            
            # Clean up expired API keys
            expired_keys = [
                key_id for key_id, key_info in self.api_keys.items()
                if key_info.expires_at and now > key_info.expires_at
            ]
            
            for key_id in expired_keys:
                del self.api_keys[key_id]
            
            if expired_sessions or expired_keys:
                self._save_persistent_data()
                self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions and {len(expired_keys)} expired API keys")
        
        except Exception as e:
            self.logger.error(f"Error cleaning up expired data: {e}")
    
    def get_access_stats(self) -> Dict[str, Any]:
        """Get access control statistics."""
        now = datetime.now()
        
        return {
            'active_sessions': len(self.active_sessions),
            'total_api_keys': len(self.api_keys),
            'api_keys_by_level': {
                level.value: len([k for k in self.api_keys.values() if k.access_level == level])
                for level in AccessLevel
            },
            'expired_sessions': len([
                s for s in self.active_sessions.values()
                if now > s.expires_at
            ]),
            'expired_api_keys': len([
                k for k in self.api_keys.values()
                if k.expires_at and now > k.expires_at
            ]),
            'recent_failed_logins': sum(len(attempts) for attempts in self.failed_logins.values()),
            'session_timeout_minutes': self.session_timeout_minutes,
            'max_login_attempts': self.max_login_attempts
        }


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_access_control():
        """Test access control functionality."""
        
        # Mock Home Assistant object
        class MockHass:
            def __init__(self):
                self.data = {}
        
        hass = MockHass()
        config = {
            'session_timeout_minutes': 30,
            'max_login_attempts': 3,
            'require_authentication': True
        }
        
        access_control = AccessControlManager(hass, config)
        
        # Test authentication
        print("Testing authentication...")
        session = await access_control.authenticate_user(
            "admin", "admin", "127.0.0.1", "test-agent"
        )
        
        if session:
            print(f"Authentication successful: {session.session_id}")
            
            # Test session validation
            validated = await access_control.validate_session(session.session_id, "127.0.0.1")
            print(f"Session validation: {'success' if validated else 'failed'}")
        
        # Test API key creation
        print("Testing API key creation...")
        key_id, api_key = await access_control.create_api_key(
            "test-key", AccessLevel.READ, rate_limit=100
        )
        print(f"Created API key: {key_id}")
        
        # Test API key validation
        validated_key = await access_control.validate_api_key(api_key, "127.0.0.1")
        print(f"API key validation: {'success' if validated_key else 'failed'}")
        
        # Test authorization
        authorized = access_control.check_authorization(AccessLevel.READ, AccessLevel.WRITE)
        print(f"Authorization check: {'authorized' if authorized else 'denied'}")
        
        # Get statistics
        stats = access_control.get_access_stats()
        print(f"Access control stats: {stats}")
        
        print("Access control test completed!")
    
    # Run test
    asyncio.run(test_access_control())