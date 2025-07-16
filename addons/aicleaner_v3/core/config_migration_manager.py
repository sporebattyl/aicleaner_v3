"""
Configuration Migration Manager for AICleaner v3
Phase 1A: Configuration Schema Consolidation

This module handles migration from multiple configuration files to the unified schema
with comprehensive rollback capabilities and automated backup mechanisms.

Key Features:
- Automated migration from three config files to unified schema
- Comprehensive rollback validation and procedures
- Automated backup mechanisms with versioning
- Migration safety checks and validation
- Performance monitoring during migration
- Detailed logging and error reporting
"""

import logging
import json
import yaml
import shutil
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import hashlib
import os
from enum import Enum

from .config_schema_validator import ConfigSchemaValidator, ValidationResult, ValidationSeverity
from .config_schema import ConfigurationSchemaGenerator

class MigrationStage(Enum):
    """Migration stage tracking"""
    INITIALIZED = "initialized"
    BACKUP_CREATED = "backup_created"
    CONFIGS_MERGED = "configs_merged"
    VALIDATION_PASSED = "validation_passed"
    MIGRATION_COMPLETE = "migration_complete"
    ROLLBACK_INITIATED = "rollback_initiated"
    ROLLBACK_COMPLETE = "rollback_complete"
    FAILED = "failed"

@dataclass
class MigrationBackup:
    """Migration backup information"""
    timestamp: datetime
    backup_dir: Path
    original_files: Dict[str, str]
    checksum: str
    stage: MigrationStage

@dataclass
class MigrationResult:
    """Migration operation result"""
    success: bool
    stage: MigrationStage
    backup: Optional[MigrationBackup]
    validation_result: Optional[ValidationResult]
    migration_time_ms: float
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

class ConfigMigrationManager:
    """
    Comprehensive configuration migration manager
    
    Handles migration from three separate config files to unified schema
    with full rollback capabilities and safety validation.
    """
    
    def __init__(self, base_path: str = "X:/aicleaner_v3/addons/aicleaner_v3"):
        self.base_path = Path(base_path)
        self.logger = logging.getLogger(__name__)
        self.validator = ConfigSchemaValidator()
        self.schema_generator = ConfigurationSchemaGenerator()
        
        # Configuration file paths
        self.config_files = {
            "addon_config_yaml": self.base_path / "config.yaml",
            "addon_config_json": self.base_path / "config.json",
            "root_config_yaml": self.base_path.parent.parent / "config.yaml"
        }
        
        # Backup directory
        self.backup_dir = self.base_path / "config_backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Migration tracking
        self.current_migration: Optional[MigrationBackup] = None
        self.migration_history: List[MigrationBackup] = []
        
    def migrate_configuration(self) -> MigrationResult:
        """
        Perform complete configuration migration with safety checks
        
        Returns:
            MigrationResult with detailed migration information
        """
        start_time = time.time()
        
        try:
            # Stage 1: Initialize migration
            self.logger.info("Starting configuration migration")
            stage = MigrationStage.INITIALIZED
            
            # Stage 2: Create backup
            backup = self._create_backup()
            if not backup:
                return MigrationResult(
                    success=False,
                    stage=MigrationStage.FAILED,
                    backup=None,
                    validation_result=None,
                    migration_time_ms=(time.time() - start_time) * 1000,
                    error_message="Failed to create backup"
                )
            
            stage = MigrationStage.BACKUP_CREATED
            self.current_migration = backup
            
            # Stage 3: Merge configurations
            merged_config = self._merge_configurations()
            if not merged_config:
                return MigrationResult(
                    success=False,
                    stage=MigrationStage.FAILED,
                    backup=backup,
                    validation_result=None,
                    migration_time_ms=(time.time() - start_time) * 1000,
                    error_message="Failed to merge configurations"
                )
            
            stage = MigrationStage.CONFIGS_MERGED
            
            # Stage 4: Validate merged configuration
            validation_result = self.validator.validate(merged_config)
            if not validation_result.is_valid:
                self.logger.error(f"Merged configuration validation failed: {len(validation_result.errors)} errors")
                return MigrationResult(
                    success=False,
                    stage=MigrationStage.FAILED,
                    backup=backup,
                    validation_result=validation_result,
                    migration_time_ms=(time.time() - start_time) * 1000,
                    error_message="Merged configuration validation failed"
                )
            
            stage = MigrationStage.VALIDATION_PASSED
            
            # Stage 5: Write unified configuration
            unified_config = self._create_unified_config(merged_config)
            if not self._write_unified_config(unified_config):
                return MigrationResult(
                    success=False,
                    stage=MigrationStage.FAILED,
                    backup=backup,
                    validation_result=validation_result,
                    migration_time_ms=(time.time() - start_time) * 1000,
                    error_message="Failed to write unified configuration"
                )
            
            stage = MigrationStage.MIGRATION_COMPLETE
            
            # Cleanup old config files (keep as .old)
            self._archive_old_configs()
            
            migration_time = (time.time() - start_time) * 1000
            self.logger.info(f"Configuration migration completed successfully in {migration_time:.2f}ms")
            
            return MigrationResult(
                success=True,
                stage=stage,
                backup=backup,
                validation_result=validation_result,
                migration_time_ms=migration_time,
                warnings=self._get_migration_warnings(validation_result)
            )
            
        except Exception as e:
            self.logger.error(f"Migration failed: {str(e)}")
            
            # Attempt rollback on failure
            if self.current_migration:
                rollback_result = self.rollback_migration(self.current_migration)
                if rollback_result.success:
                    self.logger.info("Rollback completed successfully")
                else:
                    self.logger.error("Rollback failed - manual intervention required")
            
            return MigrationResult(
                success=False,
                stage=MigrationStage.FAILED,
                backup=self.current_migration,
                validation_result=None,
                migration_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
    
    def _create_backup(self) -> Optional[MigrationBackup]:
        """Create comprehensive backup of current configuration"""
        try:
            timestamp = datetime.now()
            backup_name = f"config_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            backup_path = self.backup_dir / backup_name
            backup_path.mkdir(exist_ok=True)
            
            original_files = {}
            
            # Backup each configuration file
            for config_name, config_path in self.config_files.items():
                if config_path.exists():
                    backup_file = backup_path / f"{config_name}_{config_path.name}"
                    shutil.copy2(config_path, backup_file)
                    original_files[config_name] = str(config_path)
                    self.logger.info(f"Backed up {config_path} to {backup_file}")
            
            # Create backup manifest
            manifest = {
                "timestamp": timestamp.isoformat(),
                "original_files": original_files,
                "migration_stage": MigrationStage.BACKUP_CREATED.value,
                "aicleaner_version": "3.0.0"
            }
            
            manifest_path = backup_path / "migration_manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # Calculate checksum
            checksum = self._calculate_backup_checksum(backup_path)
            
            backup = MigrationBackup(
                timestamp=timestamp,
                backup_dir=backup_path,
                original_files=original_files,
                checksum=checksum,
                stage=MigrationStage.BACKUP_CREATED
            )
            
            self.migration_history.append(backup)
            self.logger.info(f"Backup created successfully: {backup_path}")
            
            return backup
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {str(e)}")
            return None
    
    def _merge_configurations(self) -> Optional[Dict[str, Any]]:
        """Merge three configuration files into unified structure"""
        try:
            configurations = {}
            
            # Load all configuration files
            for config_name, config_path in self.config_files.items():
                if config_path.exists():
                    if config_path.suffix == '.json':
                        with open(config_path, 'r') as f:
                            configurations[config_name] = json.load(f)
                    elif config_path.suffix == '.yaml':
                        with open(config_path, 'r') as f:
                            configurations[config_name] = yaml.safe_load(f)
                    
                    self.logger.info(f"Loaded configuration from {config_path}")
            
            # Merge configurations with priority
            merged_config = {}
            
            # Start with defaults
            merged_config.update(self.schema_generator.generate_default_options())
            
            # Priority order: root_config_yaml > addon_config_yaml > addon_config_json
            merge_order = ["addon_config_json", "addon_config_yaml", "root_config_yaml"]
            
            for config_name in merge_order:
                if config_name in configurations:
                    config_data = configurations[config_name]
                    
                    # Handle different configuration structures
                    if config_name == "addon_config_json":
                        # Extract from Home Assistant addon structure
                        if "options" in config_data:
                            merged_config.update(config_data["options"])
                        
                        # Preserve addon metadata
                        merged_config.update({
                            "name": config_data.get("name", "AICleaner v3"),
                            "version": config_data.get("version", "3.0.0"),
                            "slug": config_data.get("slug", "aicleaner_v3"),
                            "description": config_data.get("description", "AI-powered cleaning task management")
                        })
                    
                    elif config_name in ["addon_config_yaml", "root_config_yaml"]:
                        # Direct merge for YAML files
                        if "options" in config_data:
                            merged_config.update(config_data["options"])
                        else:
                            # Handle direct structure
                            self._merge_dict_recursive(merged_config, config_data)
            
            # Normalize configuration structure
            normalized_config = self._normalize_configuration(merged_config)
            
            self.logger.info(f"Configuration merge completed with {len(normalized_config)} top-level keys")
            return normalized_config
            
        except Exception as e:
            self.logger.error(f"Failed to merge configurations: {str(e)}")
            return None
    
    def _merge_dict_recursive(self, target: Dict[str, Any], source: Dict[str, Any]):
        """Recursively merge dictionaries"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_dict_recursive(target[key], value)
            else:
                target[key] = value
    
    def _normalize_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize configuration to unified structure"""
        normalized = config.copy()
        
        # Normalize MQTT settings
        if "mqtt_enabled" in normalized or "enable_mqtt" in normalized:
            mqtt_enabled = normalized.get("mqtt_enabled", normalized.get("enable_mqtt", False))
            mqtt_host = normalized.get("mqtt_host", normalized.get("mqtt_broker_host", "core-mosquitto"))
            mqtt_port = normalized.get("mqtt_port", normalized.get("mqtt_broker_port", 1883))
            mqtt_username = normalized.get("mqtt_username", "")
            mqtt_password = normalized.get("mqtt_password", "")
            
            normalized["mqtt"] = {
                "enabled": mqtt_enabled,
                "host": mqtt_host,
                "port": mqtt_port,
                "username": mqtt_username,
                "password": mqtt_password
            }
            
            # Remove old keys
            for old_key in ["mqtt_enabled", "enable_mqtt", "mqtt_host", "mqtt_broker_host", 
                          "mqtt_port", "mqtt_broker_port", "mqtt_username", "mqtt_password"]:
                normalized.pop(old_key, None)
        
        # Normalize zone configuration
        if "zones" in normalized:
            zones = normalized["zones"]
            for zone in zones:
                if isinstance(zone, dict):
                    # Normalize interval fields
                    if "interval_minutes" in zone and "update_frequency" not in zone:
                        zone["update_frequency"] = zone["interval_minutes"] // 60
                    elif "update_frequency" in zone and "interval_minutes" not in zone:
                        zone["interval_minutes"] = zone["update_frequency"] * 60
        
        return normalized
    
    def _create_unified_config(self, merged_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create unified configuration following Home Assistant addon format"""
        unified = self.schema_generator.generate_addon_schema()
        
        # Update with merged configuration
        unified["options"].update(merged_config)
        
        # Ensure required fields are present
        if "name" not in unified["options"]:
            unified["options"]["name"] = unified["name"]
        
        return unified
    
    def _write_unified_config(self, unified_config: Dict[str, Any]) -> bool:
        """Write unified configuration to file"""
        try:
            # Write main configuration file
            config_path = self.base_path / "config.yaml"
            with open(config_path, 'w') as f:
                yaml.dump(unified_config, f, default_flow_style=False, sort_keys=False, indent=2)
            
            self.logger.info(f"Unified configuration written to {config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write unified configuration: {str(e)}")
            return False
    
    def _archive_old_configs(self):
        """Archive old configuration files"""
        for config_name, config_path in self.config_files.items():
            if config_path.exists() and config_path.name != "config.yaml":
                old_path = config_path.with_suffix(f"{config_path.suffix}.old")
                shutil.move(config_path, old_path)
                self.logger.info(f"Archived {config_path} to {old_path}")
    
    def rollback_migration(self, backup: MigrationBackup) -> MigrationResult:
        """
        Rollback migration using backup
        
        Args:
            backup: Migration backup to restore from
            
        Returns:
            MigrationResult indicating rollback success/failure
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting rollback from backup: {backup.backup_dir}")
            
            # Verify backup integrity
            if not self._verify_backup_integrity(backup):
                return MigrationResult(
                    success=False,
                    stage=MigrationStage.FAILED,
                    backup=backup,
                    validation_result=None,
                    migration_time_ms=(time.time() - start_time) * 1000,
                    error_message="Backup integrity verification failed"
                )
            
            # Restore original files
            for config_name, original_path in backup.original_files.items():
                backup_file = backup.backup_dir / f"{config_name}_{Path(original_path).name}"
                if backup_file.exists():
                    shutil.copy2(backup_file, original_path)
                    self.logger.info(f"Restored {original_path} from backup")
            
            # Remove unified config if it exists
            unified_config_path = self.base_path / "config.yaml"
            if unified_config_path.exists():
                unified_config_path.unlink()
                self.logger.info("Removed unified configuration file")
            
            # Restore .old files
            self._restore_old_configs()
            
            rollback_time = (time.time() - start_time) * 1000
            self.logger.info(f"Rollback completed successfully in {rollback_time:.2f}ms")
            
            return MigrationResult(
                success=True,
                stage=MigrationStage.ROLLBACK_COMPLETE,
                backup=backup,
                validation_result=None,
                migration_time_ms=rollback_time
            )
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {str(e)}")
            return MigrationResult(
                success=False,
                stage=MigrationStage.FAILED,
                backup=backup,
                validation_result=None,
                migration_time_ms=(time.time() - start_time) * 1000,
                error_message=f"Rollback failed: {str(e)}"
            )
    
    def _verify_backup_integrity(self, backup: MigrationBackup) -> bool:
        """Verify backup integrity using checksum"""
        try:
            current_checksum = self._calculate_backup_checksum(backup.backup_dir)
            return current_checksum == backup.checksum
        except Exception as e:
            self.logger.error(f"Backup integrity verification failed: {str(e)}")
            return False
    
    def _restore_old_configs(self):
        """Restore .old configuration files"""
        for config_name, config_path in self.config_files.items():
            old_path = Path(config_path).with_suffix(f"{Path(config_path).suffix}.old")
            if old_path.exists():
                shutil.move(old_path, config_path)
                self.logger.info(f"Restored {config_path} from {old_path}")
            elif not Path(config_path).exists():
                # If the file doesn't exist and there's no .old version, 
                # it might have been removed during migration
                self.logger.warning(f"Neither {config_path} nor {old_path} exists during rollback")
    
    def _calculate_backup_checksum(self, backup_dir: Path) -> str:
        """Calculate checksum for backup directory"""
        hasher = hashlib.sha256()
        
        for file_path in sorted(backup_dir.glob("**/*")):
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    hasher.update(f.read())
        
        return hasher.hexdigest()
    
    def _get_migration_warnings(self, validation_result: ValidationResult) -> List[str]:
        """Extract migration warnings from validation result"""
        warnings = []
        
        if validation_result and validation_result.warnings:
            for warning in validation_result.warnings:
                warnings.append(f"{warning.code}: {warning.message}")
        
        return warnings
    
    def get_migration_history(self) -> List[MigrationBackup]:
        """Get migration history"""
        return self.migration_history.copy()
    
    def cleanup_old_backups(self, keep_count: int = 5) -> int:
        """
        Clean up old backups, keeping only the most recent ones
        
        Args:
            keep_count: Number of backups to keep
            
        Returns:
            Number of backups cleaned up
        """
        try:
            backup_dirs = sorted(
                [d for d in self.backup_dir.iterdir() if d.is_dir()],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            cleaned_count = 0
            for backup_dir in backup_dirs[keep_count:]:
                shutil.rmtree(backup_dir)
                cleaned_count += 1
                self.logger.info(f"Cleaned up old backup: {backup_dir}")
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {str(e)}")
            return 0

# Example usage following AAA pattern
def example_migration_aaa():
    """Example migration following AAA pattern"""
    
    # Arrange - Set up migration manager
    migration_manager = ConfigMigrationManager()
    
    # Act - Perform migration
    result = migration_manager.migrate_configuration()
    
    # Assert - Verify results
    assert isinstance(result, MigrationResult)
    if result.success:
        assert result.stage == MigrationStage.MIGRATION_COMPLETE
        assert result.backup is not None
        assert result.validation_result is not None
        assert result.validation_result.is_valid
    
    print("AAA migration example completed")