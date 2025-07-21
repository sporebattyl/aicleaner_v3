"""
AICleaner v3 Backup Manager
Comprehensive state management and disaster recovery

Features:
- Configuration backup and restore
- Performance state preservation
- System state recovery
- Migration assistance between HA installations
- Automated backup scheduling
- Backup validation and integrity checking
"""

import os
import asyncio
import logging
import json
import yaml
import tarfile
import shutil
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import tempfile


class BackupType(Enum):
    """Backup types"""
    MINIMAL = "minimal"
    FULL = "full"
    MIGRATION = "migration"
    AUTOMATIC = "automatic"


class RecoveryMode(Enum):
    """Recovery modes"""
    MINIMAL_RECOVERY = "minimal"
    FULL_RECOVERY = "full"
    MIGRATION_MODE = "migration"


@dataclass
class BackupInfo:
    """Backup information metadata"""
    backup_id: str
    backup_type: BackupType
    created_at: datetime
    ha_environment: str
    ha_version: str
    aicleaner_version: str
    file_count: int
    size_bytes: int
    checksum: str
    description: str
    components: List[str]


@dataclass
class RestoreResult:
    """Result of restore operation"""
    success: bool
    restored_components: List[str]
    failed_components: List[str]
    warnings: List[str]
    errors: List[str]
    recovery_mode: RecoveryMode


class BackupManager:
    """
    Comprehensive backup and recovery manager implementing disaster recovery
    
    Backup Components:
    - Configuration files (service_config.yaml, security configs)
    - Security keys and secrets (encrypted)
    - Performance optimization settings
    - Provider configurations
    - Service registry state
    - Performance learning data
    - Metrics history
    
    Recovery Modes:
    - Minimal: Essential configuration only
    - Full: Complete state restoration
    - Migration: Transfer between HA installations
    """
    
    def __init__(self, config_path: Path, config: Dict[str, Any] = None):
        self.config_path = config_path
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Backup paths
        self.backup_root = config_path / "aicleaner" / "backups"
        self.temp_dir = config_path / "aicleaner" / "temp"
        
        # Configuration
        self.max_backups = self.config.get("max_backups", 10)
        self.auto_backup_enabled = self.config.get("auto_backup_enabled", True)
        self.auto_backup_interval_hours = self.config.get("auto_backup_interval_hours", 24)
        self.compression_enabled = self.config.get("compression_enabled", True)
        
        # State
        self.backup_history: List[BackupInfo] = []
        self.last_backup_time: Optional[datetime] = None
        
        # Initialize directories
        self._initialize_backup_structure()
    
    def _initialize_backup_structure(self) -> None:
        """Initialize backup directory structure"""
        try:
            self.backup_root.mkdir(parents=True, exist_ok=True, mode=0o750)
            self.temp_dir.mkdir(parents=True, exist_ok=True, mode=0o750)
            
            # Set directory permissions
            os.chmod(self.backup_root, 0o750)
            os.chmod(self.temp_dir, 0o750)
            
        except Exception as e:
            self.logger.error(f"Failed to initialize backup structure: {e}")
            raise
    
    async def initialize(self) -> None:
        """Initialize the backup manager"""
        try:
            self.logger.info("Initializing backup manager")
            
            # Load existing backup history
            await self._load_backup_history()
            
            # Start automatic backup task if enabled
            if self.auto_backup_enabled:
                asyncio.create_task(self._automatic_backup_loop())
            
            # Cleanup old backups
            await self._cleanup_old_backups()
            
            self.logger.info("Backup manager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize backup manager: {e}")
            raise
    
    # Backup Operations
    
    async def create_backup(self, backup_type: BackupType = BackupType.FULL, 
                           description: str = "") -> Optional[str]:
        """
        Create a new backup
        
        Args:
            backup_type: Type of backup to create
            description: Optional description for the backup
        
        Returns:
            Backup ID if successful, None if failed
        """
        try:
            backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.logger.info(f"Creating {backup_type.value} backup: {backup_id}")
            
            # Create temporary working directory
            temp_backup_dir = self.temp_dir / backup_id
            temp_backup_dir.mkdir(exist_ok=True)
            
            try:
                # Collect components based on backup type
                components = await self._collect_backup_components(backup_type, temp_backup_dir)
                
                if not components:
                    self.logger.error("No components collected for backup")
                    return None
                
                # Create backup metadata
                backup_info = BackupInfo(
                    backup_id=backup_id,
                    backup_type=backup_type,
                    created_at=datetime.now(),
                    ha_environment=await self._detect_ha_environment(),
                    ha_version=await self._get_ha_version(),
                    aicleaner_version="3.0.0",
                    file_count=len(list(temp_backup_dir.rglob("*"))),
                    size_bytes=self._get_directory_size(temp_backup_dir),
                    checksum="",  # Will be calculated after compression
                    description=description or f"Automatic {backup_type.value} backup",
                    components=components
                )
                
                # Create backup archive
                backup_file = await self._create_backup_archive(temp_backup_dir, backup_info)
                
                if not backup_file:
                    self.logger.error("Failed to create backup archive")
                    return None
                
                # Calculate and update checksum
                backup_info.checksum = await self._calculate_file_checksum(backup_file)
                backup_info.size_bytes = backup_file.stat().st_size
                
                # Update backup history
                self.backup_history.append(backup_info)
                await self._save_backup_history()
                
                # Update last backup time
                self.last_backup_time = datetime.now()
                
                self.logger.info(f"Backup created successfully: {backup_id} ({backup_info.size_bytes} bytes)")
                return backup_id
                
            finally:
                # Cleanup temporary directory
                if temp_backup_dir.exists():
                    shutil.rmtree(temp_backup_dir)
        
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return None
    
    async def restore_backup(self, backup_id: str, recovery_mode: RecoveryMode = RecoveryMode.FULL_RECOVERY,
                           force: bool = False) -> RestoreResult:
        """
        Restore from backup
        
        Args:
            backup_id: ID of backup to restore
            recovery_mode: Mode of recovery to perform
            force: Force restore without validation
        
        Returns:
            RestoreResult with operation details
        """
        result = RestoreResult(
            success=False,
            restored_components=[],
            failed_components=[],
            warnings=[],
            errors=[],
            recovery_mode=recovery_mode
        )
        
        try:
            self.logger.info(f"Starting {recovery_mode.value} restore from backup: {backup_id}")
            
            # Find backup info
            backup_info = None
            for info in self.backup_history:
                if info.backup_id == backup_id:
                    backup_info = info
                    break
            
            if not backup_info:
                result.errors.append(f"Backup not found: {backup_id}")
                return result
            
            # Validate backup integrity
            if not force:
                is_valid, validation_errors = await self._validate_backup(backup_info)
                if not is_valid:
                    result.errors.extend(validation_errors)
                    return result
            
            # Extract backup
            temp_restore_dir = self.temp_dir / f"restore_{backup_id}"
            backup_file = self.backup_root / f"{backup_id}.tar.gz"
            
            try:
                await self._extract_backup_archive(backup_file, temp_restore_dir)
                
                # Perform restore based on recovery mode
                if recovery_mode == RecoveryMode.MINIMAL_RECOVERY:
                    await self._perform_minimal_restore(temp_restore_dir, result)
                elif recovery_mode == RecoveryMode.FULL_RECOVERY:
                    await self._perform_full_restore(temp_restore_dir, result)
                elif recovery_mode == RecoveryMode.MIGRATION_MODE:
                    await self._perform_migration_restore(temp_restore_dir, result)
                
                # Validate restored state
                if result.restored_components:
                    validation_success = await self._validate_restored_state(result.restored_components)
                    if not validation_success:
                        result.warnings.append("Restored state validation failed")
                
                result.success = len(result.failed_components) == 0
                
                if result.success:
                    self.logger.info(f"Restore completed successfully: {len(result.restored_components)} components")
                else:
                    self.logger.warning(f"Restore completed with errors: {len(result.failed_components)} failed")
                
            finally:
                # Cleanup temporary directory
                if temp_restore_dir.exists():
                    shutil.rmtree(temp_restore_dir)
        
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            result.errors.append(str(e))
        
        return result
    
    async def list_backups(self) -> List[BackupInfo]:
        """List all available backups"""
        # Refresh backup history from disk
        await self._load_backup_history()
        return sorted(self.backup_history, key=lambda x: x.created_at, reverse=True)
    
    async def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup"""
        try:
            # Find backup info
            backup_info = None
            for i, info in enumerate(self.backup_history):
                if info.backup_id == backup_id:
                    backup_info = info
                    del self.backup_history[i]
                    break
            
            if not backup_info:
                self.logger.error(f"Backup not found: {backup_id}")
                return False
            
            # Delete backup file
            backup_file = self.backup_root / f"{backup_id}.tar.gz"
            if backup_file.exists():
                backup_file.unlink()
            
            # Update backup history
            await self._save_backup_history()
            
            self.logger.info(f"Deleted backup: {backup_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete backup {backup_id}: {e}")
            return False
    
    # Component Collection Methods
    
    async def _collect_backup_components(self, backup_type: BackupType, 
                                       output_dir: Path) -> List[str]:
        """Collect components for backup"""
        components = []
        
        try:
            # Always include basic configuration
            if await self._backup_configuration(output_dir):
                components.append("configuration")
            
            # Always include security (encrypted)
            if await self._backup_security(output_dir):
                components.append("security")
            
            # Include additional components based on backup type
            if backup_type in [BackupType.FULL, BackupType.MIGRATION]:
                if await self._backup_performance_state(output_dir):
                    components.append("performance_state")
                
                if await self._backup_system_state(output_dir):
                    components.append("system_state")
                
                if await self._backup_metrics_history(output_dir):
                    components.append("metrics_history")
                
                if await self._backup_provider_configs(output_dir):
                    components.append("provider_configs")
            
            # Migration-specific components
            if backup_type == BackupType.MIGRATION:
                if await self._backup_migration_metadata(output_dir):
                    components.append("migration_metadata")
            
            return components
            
        except Exception as e:
            self.logger.error(f"Failed to collect backup components: {e}")
            return []
    
    async def _backup_configuration(self, output_dir: Path) -> bool:
        """Backup configuration files"""
        try:
            config_dir = output_dir / "configuration"
            config_dir.mkdir(exist_ok=True)
            
            # Service configuration
            service_config_source = self.config_path / "aicleaner" / "service_config.yaml"
            if service_config_source.exists():
                shutil.copy2(service_config_source, config_dir / "service_config.yaml")
            
            # Installation record
            install_record_source = self.config_path / "aicleaner" / "installation.json"
            if install_record_source.exists():
                shutil.copy2(install_record_source, config_dir / "installation.json")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to backup configuration: {e}")
            return False
    
    async def _backup_security(self, output_dir: Path) -> bool:
        """Backup security components (encrypted)"""
        try:
            security_dir = output_dir / "security"
            security_dir.mkdir(exist_ok=True)
            
            # Security configuration (safe to backup)
            security_config_source = self.config_path / "aicleaner" / "security" / "security_config.yaml"
            if security_config_source.exists():
                shutil.copy2(security_config_source, security_dir / "security_config.yaml")
            
            # External secrets (encrypted in original system)
            secrets_source = self.config_path / "aicleaner" / "security" / "secrets.yaml"
            if secrets_source.exists():
                shutil.copy2(secrets_source, security_dir / "secrets.yaml")
            
            # Note: Internal keys are NOT backed up for security reasons
            # They will be regenerated on restore
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to backup security: {e}")
            return False
    
    async def _backup_performance_state(self, output_dir: Path) -> bool:
        """Backup performance optimization state"""
        try:
            perf_dir = output_dir / "performance"
            perf_dir.mkdir(exist_ok=True)
            
            # Performance configurations and learning data
            perf_sources = [
                "performance_config.yaml",
                "optimization_history.json",
                "performance_cache.json"
            ]
            
            for source_name in perf_sources:
                source_path = self.config_path / "aicleaner" / "performance" / source_name
                if source_path.exists():
                    shutil.copy2(source_path, perf_dir / source_name)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to backup performance state: {e}")
            return False
    
    async def _backup_system_state(self, output_dir: Path) -> bool:
        """Backup system state"""
        try:
            system_dir = output_dir / "system"
            system_dir.mkdir(exist_ok=True)
            
            # Service registry state, circuit breaker states, etc.
            system_sources = [
                "service_registry.json",
                "circuit_breakers.json",
                "failover_state.json"
            ]
            
            for source_name in system_sources:
                source_path = self.config_path / "aicleaner" / "system" / source_name
                if source_path.exists():
                    shutil.copy2(source_path, system_dir / source_name)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to backup system state: {e}")
            return False
    
    async def _backup_metrics_history(self, output_dir: Path) -> bool:
        """Backup metrics and monitoring history"""
        try:
            metrics_dir = output_dir / "metrics"
            metrics_dir.mkdir(exist_ok=True)
            
            # Metrics history files
            metrics_sources = [
                "metrics_history.json",
                "performance_metrics.json",
                "usage_statistics.json"
            ]
            
            for source_name in metrics_sources:
                source_path = self.config_path / "aicleaner" / "metrics" / source_name
                if source_path.exists():
                    shutil.copy2(source_path, metrics_dir / source_name)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to backup metrics history: {e}")
            return False
    
    async def _backup_provider_configs(self, output_dir: Path) -> bool:
        """Backup AI provider configurations"""
        try:
            providers_dir = output_dir / "providers"
            providers_dir.mkdir(exist_ok=True)
            
            # Provider configuration files
            provider_config_source = self.config_path / "aicleaner" / "providers"
            if provider_config_source.exists():
                for config_file in provider_config_source.glob("*.yaml"):
                    shutil.copy2(config_file, providers_dir / config_file.name)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to backup provider configs: {e}")
            return False
    
    async def _backup_migration_metadata(self, output_dir: Path) -> bool:
        """Backup migration-specific metadata"""
        try:
            migration_dir = output_dir / "migration"
            migration_dir.mkdir(exist_ok=True)
            
            # Migration metadata
            migration_data = {
                "source_environment": await self._detect_ha_environment(),
                "source_ha_version": await self._get_ha_version(),
                "source_python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
                "export_timestamp": datetime.now().isoformat(),
                "migration_notes": "Full system export for migration to new HA installation",
                "compatibility_info": {
                    "min_ha_version": "2023.1.0",
                    "min_python_version": "3.9"
                }
            }
            
            with open(migration_dir / "migration_metadata.json", 'w') as f:
                json.dump(migration_data, f, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to backup migration metadata: {e}")
            return False
    
    # Restore Methods
    
    async def _perform_minimal_restore(self, restore_dir: Path, result: RestoreResult) -> None:
        """Perform minimal recovery (essential configuration only)"""
        try:
            # Restore basic configuration
            config_dir = restore_dir / "configuration"
            if config_dir.exists():
                await self._restore_configuration(config_dir, result)
            
            # Restore security configuration (without keys)
            security_dir = restore_dir / "security"
            if security_dir.exists():
                await self._restore_security_config(security_dir, result)
            
        except Exception as e:
            result.errors.append(f"Minimal restore failed: {e}")
    
    async def _perform_full_restore(self, restore_dir: Path, result: RestoreResult) -> None:
        """Perform full recovery (complete state restoration)"""
        try:
            # Restore all components
            component_dirs = [
                ("configuration", self._restore_configuration),
                ("security", self._restore_security_full),
                ("performance", self._restore_performance_state),
                ("system", self._restore_system_state),
                ("metrics", self._restore_metrics_history),
                ("providers", self._restore_provider_configs)
            ]
            
            for dir_name, restore_func in component_dirs:
                component_dir = restore_dir / dir_name
                if component_dir.exists():
                    await restore_func(component_dir, result)
            
        except Exception as e:
            result.errors.append(f"Full restore failed: {e}")
    
    async def _perform_migration_restore(self, restore_dir: Path, result: RestoreResult) -> None:
        """Perform migration restore (with compatibility handling)"""
        try:
            # Check migration metadata first
            migration_dir = restore_dir / "migration"
            if migration_dir.exists():
                await self._validate_migration_compatibility(migration_dir, result)
            
            # Perform full restore with migration adaptations
            await self._perform_full_restore(restore_dir, result)
            
            # Post-migration adjustments
            await self._apply_migration_adjustments(result)
            
        except Exception as e:
            result.errors.append(f"Migration restore failed: {e}")
    
    # Helper Methods
    
    async def _create_backup_archive(self, source_dir: Path, backup_info: BackupInfo) -> Optional[Path]:
        """Create compressed backup archive"""
        try:
            archive_path = self.backup_root / f"{backup_info.backup_id}.tar.gz"
            
            # Create backup metadata file
            metadata_file = source_dir / "backup_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(asdict(backup_info), f, indent=2, default=str)
            
            # Create compressed archive
            with tarfile.open(archive_path, 'w:gz' if self.compression_enabled else 'w') as tar:
                tar.add(source_dir, arcname=backup_info.backup_id)
            
            return archive_path
            
        except Exception as e:
            self.logger.error(f"Failed to create backup archive: {e}")
            return None
    
    async def _extract_backup_archive(self, archive_path: Path, output_dir: Path) -> None:
        """Extract backup archive"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with tarfile.open(archive_path, 'r:*') as tar:
            tar.extractall(output_dir)
    
    def _get_directory_size(self, directory: Path) -> int:
        """Get total size of directory in bytes"""
        total_size = 0
        for path in directory.rglob("*"):
            if path.is_file():
                total_size += path.stat().st_size
        return total_size
    
    async def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    async def _validate_backup(self, backup_info: BackupInfo) -> Tuple[bool, List[str]]:
        """Validate backup integrity"""
        errors = []
        
        try:
            backup_file = self.backup_root / f"{backup_info.backup_id}.tar.gz"
            
            # Check file exists
            if not backup_file.exists():
                errors.append(f"Backup file not found: {backup_file}")
                return False, errors
            
            # Verify checksum
            actual_checksum = await self._calculate_file_checksum(backup_file)
            if actual_checksum != backup_info.checksum:
                errors.append(f"Backup integrity check failed: checksum mismatch")
                return False, errors
            
            # Verify archive can be opened
            try:
                with tarfile.open(backup_file, 'r:*') as tar:
                    tar.getmembers()
            except Exception as e:
                errors.append(f"Backup archive is corrupted: {e}")
                return False, errors
            
            return True, []
            
        except Exception as e:
            errors.append(f"Backup validation failed: {e}")
            return False, errors
    
    async def _load_backup_history(self) -> None:
        """Load backup history from disk"""
        history_file = self.backup_root / "backup_history.json"
        
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    history_data = json.load(f)
                
                self.backup_history = []
                for item in history_data:
                    backup_info = BackupInfo(
                        backup_id=item["backup_id"],
                        backup_type=BackupType(item["backup_type"]),
                        created_at=datetime.fromisoformat(item["created_at"]),
                        ha_environment=item["ha_environment"],
                        ha_version=item["ha_version"],
                        aicleaner_version=item["aicleaner_version"],
                        file_count=item["file_count"],
                        size_bytes=item["size_bytes"],
                        checksum=item["checksum"],
                        description=item["description"],
                        components=item["components"]
                    )
                    self.backup_history.append(backup_info)
                    
            except Exception as e:
                self.logger.error(f"Failed to load backup history: {e}")
                self.backup_history = []
    
    async def _save_backup_history(self) -> None:
        """Save backup history to disk"""
        history_file = self.backup_root / "backup_history.json"
        
        try:
            history_data = [asdict(info) for info in self.backup_history]
            
            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Failed to save backup history: {e}")
    
    async def _cleanup_old_backups(self) -> None:
        """Cleanup old backups based on retention policy"""
        if len(self.backup_history) <= self.max_backups:
            return
        
        # Sort by creation date and keep only the newest backups
        sorted_backups = sorted(self.backup_history, key=lambda x: x.created_at, reverse=True)
        backups_to_delete = sorted_backups[self.max_backups:]
        
        for backup_info in backups_to_delete:
            await self.delete_backup(backup_info.backup_id)
            self.logger.info(f"Deleted old backup: {backup_info.backup_id}")
    
    async def _automatic_backup_loop(self) -> None:
        """Background task for automatic backups"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                # Check if backup is due
                if self.last_backup_time:
                    time_since_backup = datetime.now() - self.last_backup_time
                    if time_since_backup.total_seconds() < self.auto_backup_interval_hours * 3600:
                        continue
                
                # Create automatic backup
                backup_id = await self.create_backup(
                    BackupType.AUTOMATIC,
                    "Automatic scheduled backup"
                )
                
                if backup_id:
                    self.logger.info(f"Automatic backup created: {backup_id}")
                else:
                    self.logger.error("Automatic backup failed")
                
            except Exception as e:
                self.logger.error(f"Automatic backup loop error: {e}")
                await asyncio.sleep(3600)  # Wait an hour before retry
    
    async def _detect_ha_environment(self) -> str:
        """Detect Home Assistant environment type"""
        # This is a simplified implementation
        # In practice, would use the same detection logic as installer
        if Path("/usr/sbin/hassos-config").exists():
            return "haos"
        elif Path("/usr/bin/ha").exists():
            return "supervised"
        elif Path("/.dockerenv").exists():
            return "container"
        else:
            return "core"
    
    async def _get_ha_version(self) -> str:
        """Get Home Assistant version"""
        # This is a simplified implementation
        version_file = self.config_path / ".HA_VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        return "unknown"