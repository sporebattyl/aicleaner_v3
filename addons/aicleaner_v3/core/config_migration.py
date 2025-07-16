"""
Configuration Migration System for AICleaner

This module handles migration from the old performance_optimization configuration
to the new simplified inference_tuning profile-based configuration.
"""

import logging
import yaml
import os
from typing import Dict, Any, Optional
from datetime import datetime


class ConfigMigration:
    """
    Handles migration from old performance_optimization config to new inference_tuning profiles.
    
    Migration Strategy:
    1. Detect old performance_optimization configuration
    2. Analyze settings to determine appropriate profile
    3. Backup old configuration
    4. Write new simplified configuration
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration migration.
        
        Args:
            config_path: Path to the configuration file
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path
        
    def needs_migration(self, config: Dict[str, Any]) -> bool:
        """
        Check if configuration needs migration.
        
        Args:
            config: Current configuration dictionary
            
        Returns:
            True if migration is needed
        """
        # Check if old performance_optimization exists and new inference_tuning doesn't
        has_old_config = "performance_optimization" in config
        has_new_config = "inference_tuning" in config
        
        return has_old_config and not has_new_config
    
    def analyze_profile(self, perf_config: Dict[str, Any]) -> str:
        """
        Analyze performance_optimization config to determine appropriate profile.
        
        Args:
            perf_config: performance_optimization configuration section
            
        Returns:
            Profile name: auto, resource_efficient, balanced, maximum_performance
        """
        try:
            # Extract key settings
            quantization_enabled = perf_config.get("quantization", {}).get("enabled", False)
            compression_enabled = perf_config.get("compression", {}).get("enabled", False)
            gpu_enabled = perf_config.get("gpu_acceleration", {}).get("enabled", False)
            auto_tuning_enabled = perf_config.get("auto_tuning", {}).get("enabled", False)
            
            # Resource limits
            memory_limit = perf_config.get("resource_management", {}).get("memory_limit_mb", 4096)
            cpu_limit = perf_config.get("resource_management", {}).get("cpu_limit_percent", 80)
            
            # Performance target
            performance_target = perf_config.get("auto_tuning", {}).get("performance_target", "balanced")
            
            # Decision logic based on configuration patterns
            if performance_target == "aggressive" and gpu_enabled and memory_limit > 6144:
                return "maximum_performance"
            elif performance_target == "conservative" or (memory_limit < 2048 and cpu_limit < 60):
                return "resource_efficient"
            elif auto_tuning_enabled and quantization_enabled and compression_enabled:
                return "auto"
            else:
                return "balanced"
                
        except Exception as e:
            self.logger.warning(f"Error analyzing profile, defaulting to 'auto': {e}")
            return "auto"
    
    def create_backup(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create backup of old configuration.
        
        Args:
            config: Current configuration
            
        Returns:
            Updated configuration with backup
        """
        if "performance_optimization" in config:
            # Create backup with timestamp
            timestamp = datetime.now().isoformat()
            backup_key = f"performance_optimization_backup_{timestamp.replace(':', '-')}"
            
            config[backup_key] = config["performance_optimization"].copy()
            self.logger.info(f"Created configuration backup: {backup_key}")
            
        return config
    
    def migrate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform the complete configuration migration.
        
        Args:
            config: Current configuration dictionary
            
        Returns:
            Migrated configuration
        """
        if not self.needs_migration(config):
            self.logger.info("No migration needed")
            return config
        
        try:
            self.logger.info("Starting configuration migration from performance_optimization to inference_tuning")
            
            # Get old configuration
            old_config = config.get("performance_optimization", {})
            
            # Analyze and determine profile
            profile = self.analyze_profile(old_config)
            self.logger.info(f"Determined profile: {profile}")
            
            # Create backup
            config = self.create_backup(config)
            
            # Create new inference_tuning configuration
            new_config = {
                "enabled": True,
                "profile": profile
            }
            
            # Add the new configuration
            config["inference_tuning"] = new_config
            
            # Remove old configuration
            if "performance_optimization" in config:
                del config["performance_optimization"]
            
            self.logger.info(f"Migration completed successfully. New profile: {profile}")
            
            return config
            
        except Exception as e:
            self.logger.error(f"Error during configuration migration: {e}")
            # Return original config if migration fails
            return config
    
    def save_migrated_config(self, config: Dict[str, Any]) -> bool:
        """
        Save the migrated configuration to file.
        
        Args:
            config: Migrated configuration
            
        Returns:
            True if save was successful
        """
        try:
            # Create backup of original file
            backup_path = f"{self.config_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if os.path.exists(self.config_path):
                import shutil
                shutil.copy2(self.config_path, backup_path)
                self.logger.info(f"Created file backup: {backup_path}")
            
            # Write new configuration
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False, indent=2)
            
            self.logger.info(f"Saved migrated configuration to {self.config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving migrated configuration: {e}")
            return False
    
    def perform_migration(self) -> bool:
        """
        Perform complete migration process including file operations.
        
        Returns:
            True if migration was successful
        """
        try:
            # Load current configuration
            if not os.path.exists(self.config_path):
                self.logger.warning(f"Configuration file not found: {self.config_path}")
                return False
            
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if not config:
                self.logger.warning("Empty configuration file")
                return False
            
            # Check if migration is needed
            if not self.needs_migration(config):
                self.logger.info("Configuration is already up to date")
                return True
            
            # Perform migration
            migrated_config = self.migrate_config(config)
            
            # Save migrated configuration
            return self.save_migrated_config(migrated_config)
            
        except Exception as e:
            self.logger.error(f"Error during migration process: {e}")
            return False


def migrate_config_if_needed(config_path: str = "config.yaml") -> bool:
    """
    Convenience function to perform migration if needed.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        True if migration was successful or not needed
    """
    migration = ConfigMigration(config_path)
    return migration.perform_migration()


# Profile definitions for reference
INFERENCE_TUNING_PROFILES = {
    "auto": {
        "description": "Automatically adapt settings based on system capabilities and usage patterns",
        "quantization": "dynamic",
        "compression": "auto",
        "gpu_acceleration": "auto_detect",
        "resource_management": "adaptive"
    },
    "resource_efficient": {
        "description": "Optimize for minimal resource usage, suitable for constrained environments",
        "quantization": "int8",
        "compression": "gzip",
        "gpu_acceleration": False,
        "resource_management": "conservative"
    },
    "balanced": {
        "description": "Balance between performance and resource usage",
        "quantization": "fp16",
        "compression": "auto",
        "gpu_acceleration": "auto_detect",
        "resource_management": "balanced"
    },
    "maximum_performance": {
        "description": "Optimize for maximum performance, requires adequate resources",
        "quantization": "fp16",
        "compression": False,
        "gpu_acceleration": True,
        "resource_management": "aggressive"
    }
}
