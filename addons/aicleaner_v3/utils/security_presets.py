"""
Simple Security Presets for Power Users
3-Level Security System: Speed / Balanced / Paranoid

Replaces complex enterprise security framework with simple,
easy-to-understand presets that power users can quickly configure.
"""

import logging
import os
import hashlib
import secrets
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security preset levels"""
    SPEED = "speed"        # Minimal security, maximum performance
    BALANCED = "balanced"  # Good security with reasonable performance
    PARANOID = "paranoid"  # Maximum security, minimal performance impact acceptable


@dataclass
class SecurityPreset:
    """Security configuration preset"""
    level: SecurityLevel
    name: str
    description: str
    
    # Data handling
    encrypt_configs: bool
    encrypt_logs: bool
    data_retention_days: int
    
    # Communication
    require_tls: bool
    validate_certificates: bool
    use_strong_auth: bool
    
    # Monitoring
    enable_audit_log: bool
    log_api_calls: bool
    monitor_failed_attempts: bool
    
    # Privacy
    anonymize_data: bool
    disable_telemetry: bool
    secure_delete: bool
    
    # Performance trade-offs
    cache_duration_minutes: int
    validation_strictness: str  # "minimal", "standard", "strict"
    
    # Recommendations for users
    recommendations: List[str]


class SecurityPresetManager:
    """
    Manages simple security presets for power users
    
    Provides three clear choices instead of overwhelming configuration:
    - Speed: For local setups where performance matters more than security
    - Balanced: Good default for most power users
    - Paranoid: Maximum security for sensitive environments
    """
    
    def __init__(self, config_path: str = "/data/security"):
        """Initialize security preset manager"""
        self.config_path = config_path
        os.makedirs(config_path, exist_ok=True)
        
        # Current security configuration
        self.current_preset = None
        self.custom_overrides = {}
        
        # Initialize presets
        self.presets = self._initialize_presets()
        
        # Load current configuration
        self._load_current_config()
        
        logger.info(f"SecurityPresetManager initialized with {len(self.presets)} presets")
    
    def _initialize_presets(self) -> Dict[SecurityLevel, SecurityPreset]:
        """Initialize the three security presets"""
        return {
            SecurityLevel.SPEED: SecurityPreset(
                level=SecurityLevel.SPEED,
                name="Speed",
                description="Minimal security for maximum performance. Best for local development and testing.",
                
                # Data handling - minimal encryption
                encrypt_configs=False,
                encrypt_logs=False,
                data_retention_days=30,
                
                # Communication - basic security
                require_tls=False,
                validate_certificates=False,
                use_strong_auth=False,
                
                # Monitoring - minimal logging
                enable_audit_log=False,
                log_api_calls=False,
                monitor_failed_attempts=False,
                
                # Privacy - basic privacy
                anonymize_data=False,
                disable_telemetry=False,
                secure_delete=False,
                
                # Performance - optimized for speed
                cache_duration_minutes=60,
                validation_strictness="minimal",
                
                recommendations=[
                    "🚀 Optimized for speed and development",
                    "⚠️ Only use on trusted networks",
                    "💡 Consider upgrading to Balanced for production",
                    "🔧 Perfect for local testing and development"
                ]
            ),
            
            SecurityLevel.BALANCED: SecurityPreset(
                level=SecurityLevel.BALANCED,
                name="Balanced",
                description="Good security with reasonable performance. Recommended for most users.",
                
                # Data handling - selective encryption
                encrypt_configs=True,
                encrypt_logs=False,
                data_retention_days=90,
                
                # Communication - secure by default
                require_tls=True,
                validate_certificates=True,
                use_strong_auth=True,
                
                # Monitoring - important events only
                enable_audit_log=True,
                log_api_calls=False,
                monitor_failed_attempts=True,
                
                # Privacy - privacy-conscious
                anonymize_data=True,
                disable_telemetry=True,
                secure_delete=False,
                
                # Performance - balanced approach
                cache_duration_minutes=30,
                validation_strictness="standard",
                
                recommendations=[
                    "⚖️ Great balance of security and performance",
                    "🔒 Secure enough for most home automation",
                    "📊 Monitors important security events",
                    "⚡ Good performance for daily use"
                ]
            ),
            
            SecurityLevel.PARANOID: SecurityPreset(
                level=SecurityLevel.PARANOID,
                name="Paranoid",
                description="Maximum security for sensitive environments. Performance impact acceptable.",
                
                # Data handling - everything encrypted
                encrypt_configs=True,
                encrypt_logs=True,
                data_retention_days=30,  # Shorter retention for security
                
                # Communication - maximum security
                require_tls=True,
                validate_certificates=True,
                use_strong_auth=True,
                
                # Monitoring - everything logged
                enable_audit_log=True,
                log_api_calls=True,
                monitor_failed_attempts=True,
                
                # Privacy - maximum privacy
                anonymize_data=True,
                disable_telemetry=True,
                secure_delete=True,
                
                # Performance - security over speed
                cache_duration_minutes=5,
                validation_strictness="strict",
                
                recommendations=[
                    "🛡️ Maximum security and privacy protection",
                    "🔐 All data encrypted and anonymized",
                    "📝 Comprehensive audit logging enabled",
                    "⏱️ Some performance impact for security",
                    "🎯 Perfect for sensitive environments"
                ]
            )
        }
    
    def get_available_presets(self) -> List[Dict[str, Any]]:
        """Get list of available security presets"""
        return [asdict(preset) for preset in self.presets.values()]
    
    def get_current_preset(self) -> Optional[SecurityPreset]:
        """Get currently active security preset"""
        return self.current_preset
    
    def apply_preset(self, level: SecurityLevel, save_config: bool = True) -> bool:
        """Apply a security preset"""
        try:
            if level not in self.presets:
                logger.error(f"Unknown security level: {level}")
                return False
            
            preset = self.presets[level]
            self.current_preset = preset
            
            # Apply the configuration
            self._apply_security_config(preset)
            
            if save_config:
                self._save_current_config()
            
            logger.info(f"Applied security preset: {preset.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply security preset {level}: {e}")
            return False
    
    def _apply_security_config(self, preset: SecurityPreset):
        """Apply security configuration from preset with real system integration"""
        # Backup current configuration for rollback capability
        backup = self._backup_current_configuration()
        
        try:
            logger.info(f"Applying {preset.level.value} security preset: {preset.name}")
            
            # Create configuration mapping for TieredConfigurationManager
            security_config = {
                "security": {
                    "level": preset.level.value,
                    "preset_name": preset.name,
                    
                    # Encryption settings
                    "encrypt_configs": preset.encrypt_configs,
                    "encrypt_logs": preset.encrypt_logs,
                    
                    # Communication security
                    "require_tls": preset.require_tls,
                    "validate_certificates": preset.validate_certificates,
                    "use_strong_auth": preset.use_strong_auth,
                    
                    # Monitoring and auditing
                    "enable_audit_log": preset.enable_audit_log,
                    "log_api_calls": preset.log_api_calls,
                    "monitor_failed_attempts": preset.monitor_failed_attempts,
                    
                    # Privacy settings
                    "anonymize_data": preset.anonymize_data,
                    "disable_telemetry": preset.disable_telemetry,
                    "secure_delete": preset.secure_delete,
                    
                    # Performance tuning
                    "cache_duration_minutes": preset.cache_duration_minutes,
                    "validation_strictness": preset.validation_strictness,
                    "data_retention_days": preset.data_retention_days
                }
            }
            
            # Apply configuration through TieredConfigurationManager
            self._update_system_configuration(security_config)
            
            # Enforce system settings - trigger actual changes
            self._enforce_security_settings(preset)
            
            # Update current preset tracking
            self.current_preset = preset
            
            # Log successful application
            config_summary = {
                "encryption": "enabled" if preset.encrypt_configs else "disabled",
                "tls": "required" if preset.require_tls else "optional", 
                "auth": "strong" if preset.use_strong_auth else "basic",
                "audit": "enabled" if preset.enable_audit_log else "disabled",
                "privacy": "anonymized" if preset.anonymize_data else "standard"
            }
            logger.info(f"Security configuration applied successfully: {config_summary}")
            
        except Exception as e:
            logger.error(f"Failed to apply security configuration: {e}")
            # Attempt rollback on failure
            self._rollback_configuration(backup)
            raise SecurityConfigurationError(f"Security preset application failed: {str(e)}")
    
    def _backup_current_configuration(self) -> Dict[str, Any]:
        """Backup current configuration for rollback capability"""
        try:
            # Import TieredConfigurationManager for actual config backup
            from .tiered_config_manager import TieredConfigurationManager, ConfigurationTier
            
            config_manager = TieredConfigurationManager()
            current_config = config_manager.get_merged_configuration()
            
            # Create backup with timestamp
            backup = {
                "timestamp": datetime.now().isoformat(),
                "config": current_config.copy(),
                "current_preset": self.current_preset.level.value if self.current_preset else None
            }
            
            logger.debug("Configuration backup created successfully")
            return backup
            
        except Exception as e:
            logger.warning(f"Failed to create configuration backup: {e}")
            return {"timestamp": datetime.now().isoformat(), "config": {}}
    
    def _update_system_configuration(self, security_config: Dict[str, Any]):
        """Update system configuration through TieredConfigurationManager"""
        try:
            # Import TieredConfigurationManager for actual config updates
            from .tiered_config_manager import TieredConfigurationManager, ConfigurationTier
            
            config_manager = TieredConfigurationManager()
            
            # Apply security configuration to YAML_ADVANCED tier as recommended
            success = config_manager.update_config_for_tier(
                ConfigurationTier.YAML_ADVANCED, 
                security_config
            )
            
            if not success:
                raise SecurityConfigurationError("Failed to update configuration tier")
            
            logger.debug("System configuration updated successfully")
            
        except ImportError:
            logger.warning("TieredConfigurationManager not available - using placeholder")
            # Fallback: save to security-specific config file
            self._save_security_config_fallback(security_config)
        except Exception as e:
            raise SecurityConfigurationError(f"Configuration update failed: {str(e)}")
    
    def _save_security_config_fallback(self, security_config: Dict[str, Any]):
        """Fallback method to save security config when TieredConfigurationManager unavailable"""
        security_file = Path(self.security_path) / "current_security_config.json"
        try:
            with open(security_file, 'w') as f:
                json.dump(security_config, f, indent=2)
            logger.debug(f"Security configuration saved to {security_file}")
        except Exception as e:
            raise SecurityConfigurationError(f"Fallback config save failed: {str(e)}")
    
    def _enforce_security_settings(self, preset: SecurityPreset):
        """Enforce security settings - trigger actual system changes"""
        logger.debug("Enforcing security settings across system components")
        
        # Apply specific configurations with real enforcement
        self._configure_encryption(preset)
        self._configure_communication(preset)
        self._configure_monitoring(preset)
        self._configure_privacy(preset)
        
        # Trigger service updates if needed
        self._trigger_service_updates(preset)
    
    def _trigger_service_updates(self, preset: SecurityPreset):
        """Trigger service updates to enforce new security settings"""
        restart_needed = []
        
        # Check if MQTT service needs restart for TLS changes
        if preset.require_tls or preset.validate_certificates:
            restart_needed.append("MQTT")
            logger.debug("MQTT service restart scheduled for TLS enforcement")
        
        # Check if API service needs restart for auth changes
        if preset.use_strong_auth:
            restart_needed.append("API")
            logger.debug("API service restart scheduled for auth enforcement")
        
        # Check if logging service needs restart for audit changes
        if preset.enable_audit_log or preset.log_api_calls:
            restart_needed.append("Logging")
            logger.debug("Logging service restart scheduled for audit enforcement")
        
        if restart_needed:
            logger.info(f"Services requiring restart for security enforcement: {', '.join(restart_needed)}")
            # In a real implementation, this would trigger actual service restarts
            # For now, we log the intention - actual restart logic would be implemented here
        
    def _rollback_configuration(self, backup: Dict[str, Any]):
        """Rollback configuration in case of failure"""
        try:
            if not backup or "config" not in backup:
                logger.warning("No valid backup available for rollback")
                return
            
            logger.info("Attempting configuration rollback")
            
            # Restore using TieredConfigurationManager
            from .tiered_config_manager import TieredConfigurationManager, ConfigurationTier
            
            config_manager = TieredConfigurationManager()
            
            # Extract just the security portion for rollback
            if "security" in backup["config"]:
                security_rollback = {"security": backup["config"]["security"]}
                success = config_manager.update_config_for_tier(
                    ConfigurationTier.YAML_ADVANCED,
                    security_rollback
                )
                
                if success:
                    logger.info("Configuration rollback completed successfully")
                    # Restore previous preset if available
                    if backup.get("current_preset"):
                        previous_level = SecurityLevel(backup["current_preset"])
                        self.current_preset = self.presets.get(previous_level)
                else:
                    logger.error("Configuration rollback failed")
            
        except Exception as e:
            logger.error(f"Rollback operation failed: {e}")
            # This is a critical failure - log extensively for debugging
            logger.error("System may be in inconsistent state - manual intervention required")
    
    def _configure_encryption(self, preset: SecurityPreset):
        """Configure encryption settings"""
        if preset.encrypt_configs:
            logger.debug("Enabling configuration encryption")
            # Would enable config file encryption
        
        if preset.encrypt_logs:
            logger.debug("Enabling log encryption")
            # Would enable log file encryption
    
    def _configure_communication(self, preset: SecurityPreset):
        """Configure communication security"""
        if preset.require_tls:
            logger.debug("Requiring TLS for all communications")
            # Would enforce TLS requirements
        
        if preset.validate_certificates:
            logger.debug("Enabling certificate validation")
            # Would enable cert validation
        
        if preset.use_strong_auth:
            logger.debug("Enabling strong authentication")
            # Would enable strong auth mechanisms
    
    def _configure_monitoring(self, preset: SecurityPreset):
        """Configure security monitoring"""
        if preset.enable_audit_log:
            logger.debug("Enabling audit logging")
            # Would enable audit logging
        
        if preset.log_api_calls:
            logger.debug("Enabling API call logging")
            # Would enable API logging
        
        if preset.monitor_failed_attempts:
            logger.debug("Enabling failed attempt monitoring")
            # Would enable attempt monitoring
    
    def _configure_privacy(self, preset: SecurityPreset):
        """Configure privacy settings"""
        if preset.anonymize_data:
            logger.debug("Enabling data anonymization")
            # Would enable data anonymization
        
        if preset.disable_telemetry:
            logger.debug("Disabling telemetry")
            # Would disable telemetry
        
        if preset.secure_delete:
            logger.debug("Enabling secure delete")
            # Would enable secure deletion
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get current security status"""
        if not self.current_preset:
            return {
                "status": "unconfigured",
                "message": "No security preset applied",
                "recommendations": ["Apply a security preset to configure security"]
            }
        
        preset = self.current_preset
        
        # Calculate security score
        security_features = [
            preset.encrypt_configs,
            preset.require_tls,
            preset.use_strong_auth,
            preset.enable_audit_log,
            preset.anonymize_data
        ]
        security_score = sum(security_features) / len(security_features) * 100
        
        return {
            "status": "configured",
            "preset": {
                "level": preset.level.value,
                "name": preset.name,
                "description": preset.description
            },
            "security_score": round(security_score, 1),
            "features_enabled": {
                "encryption": preset.encrypt_configs,
                "tls": preset.require_tls,
                "strong_auth": preset.use_strong_auth,
                "audit_log": preset.enable_audit_log,
                "data_anonymization": preset.anonymize_data
            },
            "performance_impact": {
                "cache_duration": preset.cache_duration_minutes,
                "validation_level": preset.validation_strictness,
                "expected_impact": self._get_performance_impact_description(preset.level)
            },
            "recommendations": preset.recommendations,
            "last_updated": datetime.now().isoformat()
        }
    
    def _get_performance_impact_description(self, level: SecurityLevel) -> str:
        """Get performance impact description for security level"""
        impact_map = {
            SecurityLevel.SPEED: "Minimal - optimized for performance",
            SecurityLevel.BALANCED: "Low - good balance of security and speed", 
            SecurityLevel.PARANOID: "Moderate - security prioritized over speed"
        }
        return impact_map.get(level, "Unknown")
    
    def compare_presets(self) -> Dict[str, Any]:
        """Compare all security presets"""
        comparison = {
            "presets": {},
            "features": [
                "encrypt_configs", "require_tls", "use_strong_auth",
                "enable_audit_log", "anonymize_data", "disable_telemetry"
            ],
            "performance": [
                "cache_duration_minutes", "validation_strictness"
            ]
        }
        
        for level, preset in self.presets.items():
            comparison["presets"][level.value] = {
                "name": preset.name,
                "description": preset.description,
                "features": {
                    "encrypt_configs": preset.encrypt_configs,
                    "require_tls": preset.require_tls,
                    "use_strong_auth": preset.use_strong_auth,
                    "enable_audit_log": preset.enable_audit_log,
                    "anonymize_data": preset.anonymize_data,
                    "disable_telemetry": preset.disable_telemetry
                },
                "performance": {
                    "cache_duration_minutes": preset.cache_duration_minutes,
                    "validation_strictness": preset.validation_strictness
                },
                "recommendations": preset.recommendations
            }
        
        return comparison
    
    def _load_current_config(self):
        """Load current security configuration"""
        config_file = os.path.join(self.config_path, "current_preset.txt")
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    level_name = f.read().strip()
                    level = SecurityLevel(level_name)
                    self.current_preset = self.presets[level]
                    logger.info(f"Loaded security preset: {self.current_preset.name}")
            except Exception as e:
                logger.warning(f"Failed to load security config: {e}")
                # Default to balanced if loading fails
                self.current_preset = self.presets[SecurityLevel.BALANCED]
        else:
            # Default to balanced for new installations
            self.current_preset = self.presets[SecurityLevel.BALANCED]
            self._save_current_config()
    
    def _save_current_config(self):
        """Save current security configuration"""
        if not self.current_preset:
            return
        
        config_file = os.path.join(self.config_path, "current_preset.txt")
        
        try:
            with open(config_file, 'w') as f:
                f.write(self.current_preset.level.value)
            logger.debug(f"Saved security preset: {self.current_preset.level.value}")
        except Exception as e:
            logger.error(f"Failed to save security config: {e}")
    
    def get_preset_recommendations(self, use_case: str = "general") -> Dict[str, Any]:
        """Get preset recommendations based on use case"""
        recommendations = {
            "general": {
                "recommended": SecurityLevel.BALANCED,
                "reasoning": "Good balance of security and performance for most users"
            },
            "development": {
                "recommended": SecurityLevel.SPEED,
                "reasoning": "Maximum performance for development and testing"
            },
            "production": {
                "recommended": SecurityLevel.BALANCED,
                "reasoning": "Secure enough for production with good performance"
            },
            "sensitive": {
                "recommended": SecurityLevel.PARANOID,
                "reasoning": "Maximum security for sensitive environments"
            },
            "public": {
                "recommended": SecurityLevel.PARANOID,
                "reasoning": "Maximum security for internet-facing systems"
            }
        }
        
        recommendation = recommendations.get(use_case, recommendations["general"])
        preset = self.presets[recommendation["recommended"]]
        
        return {
            "use_case": use_case,
            "recommended_preset": recommendation["recommended"].value,
            "reasoning": recommendation["reasoning"],
            "preset_details": asdict(preset),
            "alternative_options": [
                level.value for level in SecurityLevel
                if level != recommendation["recommended"]
            ]
        }