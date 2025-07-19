"""
Configuration Integration Helper - Demonstrates integration between ConfigurationManager and ConfigVersioning
"""

import json
import logging
from typing import Dict, Any, Optional, List
from .configuration_manager import ConfigurationManager
from .config_versioning import ConfigVersioning

logger = logging.getLogger(__name__)

class ConfigIntegrationHelper:
    """
    Helper class that demonstrates how to integrate ConfigVersioning with ConfigurationManager
    for Home Assistant addon use cases.
    """
    
    def __init__(self, config_base_dir: str = '/data', options_file_path: str = '/data/options.json'):
        """
        Initialize the integration helper.
        
        Args:
            config_base_dir: Base directory for configuration storage (typically '/data' in HA addon)
            options_file_path: Path to Home Assistant addon options file
        """
        self.config_manager = ConfigurationManager()
        self.versioning_manager = ConfigVersioning(config_base_dir=config_base_dir)
        self.options_file_path = options_file_path
        
    def update_configuration(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates configuration with validation and automatic versioning.
        
        Args:
            new_config: New configuration dictionary to apply
            
        Returns:
            Dictionary with status, message, and optional error details
        """
        try:
            # Validate the new configuration
            if not self.config_manager.validate_configuration(new_config):
                errors = self.config_manager.get_validation_errors()
                return {
                    "status": "error",
                    "message": "Configuration validation failed",
                    "errors": errors
                }
            
            # Save current configuration as backup before applying new one
            current_config = self._load_current_config()
            if current_config:
                backup_path = self.versioning_manager.save_version(current_config)
                if backup_path:
                    logger.info(f"Created configuration backup at: {backup_path}")
            
            # Apply the new configuration
            self._save_current_config(new_config)
            
            return {
                "status": "success",
                "message": "Configuration updated successfully",
                "restart_required": True
            }
            
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return {
                "status": "error",
                "message": f"Failed to update configuration: {str(e)}"
            }
    
    def rollback_configuration(self, version_filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Rolls back configuration to a previous version.
        
        Args:
            version_filename: Specific version to rollback to. If None, uses latest backup.
            
        Returns:
            Dictionary with status, message, and optional error details
        """
        try:
            # Determine which version to rollback to
            if version_filename is None:
                # Use latest backup
                rolled_back_config = self.versioning_manager.get_latest_version()
                if not rolled_back_config:
                    return {
                        "status": "error",
                        "message": "No configuration backups available for rollback"
                    }
                version_filename = "latest backup"
            else:
                # Use specific version
                rolled_back_config = self.versioning_manager.get_version(version_filename)
                if not rolled_back_config:
                    return {
                        "status": "error",
                        "message": f"Configuration version '{version_filename}' not found"
                    }
            
            # Validate the rollback configuration
            if not self.config_manager.validate_configuration(rolled_back_config):
                errors = self.config_manager.get_validation_errors()
                return {
                    "status": "error", 
                    "message": f"Rollback configuration is no longer valid",
                    "errors": errors
                }
            
            # Save current config as backup before rollback
            current_config = self._load_current_config()
            if current_config:
                backup_path = self.versioning_manager.save_version(current_config)
                if backup_path:
                    logger.info(f"Created pre-rollback backup at: {backup_path}")
            
            # Apply the rollback configuration
            self._save_current_config(rolled_back_config)
            
            return {
                "status": "success",
                "message": f"Successfully rolled back to {version_filename}",
                "restart_required": True
            }
            
        except Exception as e:
            logger.error(f"Error rolling back configuration: {e}")
            return {
                "status": "error",
                "message": f"Failed to rollback configuration: {str(e)}"
            }
    
    def list_configuration_versions(self) -> List[Dict[str, Any]]:
        """
        Lists all available configuration versions with metadata.
        
        Returns:
            List of dictionaries containing version information
        """
        try:
            versions = self.versioning_manager.list_versions()
            version_info = []
            
            for version_filename in versions:
                # Extract timestamp from filename
                try:
                    timestamp_str = version_filename.replace('config_', '').replace('.json', '')
                    from datetime import datetime
                    timestamp = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                    
                    version_info.append({
                        "filename": version_filename,
                        "timestamp": timestamp.isoformat(),
                        "formatted_date": timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        "is_latest": len(version_info) == 0  # First item is latest
                    })
                except ValueError:
                    # Skip invalid filenames
                    continue
            
            return version_info
            
        except Exception as e:
            logger.error(f"Error listing configuration versions: {e}")
            return []
    
    def get_configuration_status(self) -> Dict[str, Any]:
        """
        Gets current configuration status and versioning information.
        
        Returns:
            Dictionary with configuration status information
        """
        try:
            current_config = self._load_current_config()
            versions = self.versioning_manager.list_versions()
            
            status = {
                "current_config_valid": False,
                "current_config_loaded": current_config is not None,
                "available_backups": len(versions),
                "latest_backup": versions[0] if versions else None,
                "validation_errors": []
            }
            
            if current_config:
                status["current_config_valid"] = self.config_manager.validate_configuration(current_config)
                if not status["current_config_valid"]:
                    status["validation_errors"] = self.config_manager.get_validation_errors()
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting configuration status: {e}")
            return {
                "error": f"Failed to get configuration status: {str(e)}"
            }
    
    def _load_current_config(self) -> Optional[Dict[str, Any]]:
        """Load current configuration from options file."""
        try:
            with open(self.options_file_path, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load current configuration: {e}")
            return None
    
    def _save_current_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to options file."""
        with open(self.options_file_path, 'w') as f:
            json.dump(config, f, indent=4)