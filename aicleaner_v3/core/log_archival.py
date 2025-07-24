"""
Log Archival and Retention System for AICleaner v3
Phase 1C: Logging System Enhancement

This module provides comprehensive log archival, retention management,
compression, and cleanup functionality for the enhanced logging system.

Key Features:
- Automated log archival with configurable retention policies
- Compression and deduplication
- Storage optimization
- Archive integrity verification
- Cleanup and purging of old logs
- Archive search and retrieval
- Storage usage monitoring
"""

import asyncio
import gzip
import hashlib
import json
import shutil
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import zipfile
import tarfile
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import schedule


@dataclass
class ArchivePolicy:
    """Log archive policy configuration"""
    name: str
    retention_days: int
    compression: bool = True
    compression_type: str = "gzip"  # gzip, zip, tar.gz
    deduplicate: bool = True
    archive_interval: str = "daily"  # hourly, daily, weekly, monthly
    storage_location: Optional[str] = None
    max_archive_size: Optional[int] = None
    verify_integrity: bool = True
    cleanup_after_archive: bool = True


@dataclass
class ArchiveEntry:
    """Archive entry metadata"""
    archive_id: str
    original_file: str
    archive_file: str
    created_date: datetime
    original_size: int
    compressed_size: int
    compression_ratio: float
    checksum: str
    policy_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ArchiveStats:
    """Archive statistics"""
    total_archives: int
    total_original_size: int
    total_compressed_size: int
    compression_ratio: float
    oldest_archive: Optional[datetime]
    newest_archive: Optional[datetime]
    storage_usage: int
    policies_stats: Dict[str, Dict[str, Any]]


class ArchiveDatabase:
    """Archive metadata database"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize archive database"""
        with self.lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS archives (
                        archive_id TEXT PRIMARY KEY,
                        original_file TEXT NOT NULL,
                        archive_file TEXT NOT NULL,
                        created_date TEXT NOT NULL,
                        original_size INTEGER NOT NULL,
                        compressed_size INTEGER NOT NULL,
                        compression_ratio REAL NOT NULL,
                        checksum TEXT NOT NULL,
                        policy_name TEXT NOT NULL,
                        metadata TEXT
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_created_date 
                    ON archives(created_date)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_policy 
                    ON archives(policy_name)
                """)
                
                conn.commit()
            finally:
                conn.close()
    
    def add_archive(self, entry: ArchiveEntry):
        """Add archive entry to database"""
        with self.lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute("""
                    INSERT INTO archives VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.archive_id,
                    entry.original_file,
                    entry.archive_file,
                    entry.created_date.isoformat(),
                    entry.original_size,
                    entry.compressed_size,
                    entry.compression_ratio,
                    entry.checksum,
                    entry.policy_name,
                    json.dumps(entry.metadata)
                ))
                conn.commit()
            finally:
                conn.close()
    
    def get_archive(self, archive_id: str) -> Optional[ArchiveEntry]:
        """Get archive entry by ID"""
        with self.lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                cursor = conn.execute("""
                    SELECT * FROM archives WHERE archive_id = ?
                """, (archive_id,))
                
                row = cursor.fetchone()
                if row:
                    return ArchiveEntry(
                        archive_id=row[0],
                        original_file=row[1],
                        archive_file=row[2],
                        created_date=datetime.fromisoformat(row[3]),
                        original_size=row[4],
                        compressed_size=row[5],
                        compression_ratio=row[6],
                        checksum=row[7],
                        policy_name=row[8],
                        metadata=json.loads(row[9]) if row[9] else {}
                    )
                return None
            finally:
                conn.close()
    
    def list_archives(self, policy_name: Optional[str] = None,
                     start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None) -> List[ArchiveEntry]:
        """List archives with optional filtering"""
        with self.lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                query = "SELECT * FROM archives WHERE 1=1"
                params = []
                
                if policy_name:
                    query += " AND policy_name = ?"
                    params.append(policy_name)
                
                if start_date:
                    query += " AND created_date >= ?"
                    params.append(start_date.isoformat())
                
                if end_date:
                    query += " AND created_date <= ?"
                    params.append(end_date.isoformat())
                
                query += " ORDER BY created_date DESC"
                
                cursor = conn.execute(query, params)
                
                archives = []
                for row in cursor.fetchall():
                    archives.append(ArchiveEntry(
                        archive_id=row[0],
                        original_file=row[1],
                        archive_file=row[2],
                        created_date=datetime.fromisoformat(row[3]),
                        original_size=row[4],
                        compressed_size=row[5],
                        compression_ratio=row[6],
                        checksum=row[7],
                        policy_name=row[8],
                        metadata=json.loads(row[9]) if row[9] else {}
                    ))
                
                return archives
            finally:
                conn.close()
    
    def remove_archive(self, archive_id: str):
        """Remove archive entry from database"""
        with self.lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute("DELETE FROM archives WHERE archive_id = ?", (archive_id,))
                conn.commit()
            finally:
                conn.close()
    
    def get_stats(self) -> ArchiveStats:
        """Get archive statistics"""
        with self.lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                # Overall stats
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_archives,
                        SUM(original_size) as total_original_size,
                        SUM(compressed_size) as total_compressed_size,
                        MIN(created_date) as oldest_archive,
                        MAX(created_date) as newest_archive
                    FROM archives
                """)
                
                row = cursor.fetchone()
                total_archives = row[0] or 0
                total_original_size = row[1] or 0
                total_compressed_size = row[2] or 0
                oldest_archive = datetime.fromisoformat(row[3]) if row[3] else None
                newest_archive = datetime.fromisoformat(row[4]) if row[4] else None
                
                compression_ratio = (
                    (total_original_size - total_compressed_size) / total_original_size
                    if total_original_size > 0 else 0
                )
                
                # Per-policy stats
                cursor = conn.execute("""
                    SELECT 
                        policy_name,
                        COUNT(*) as count,
                        SUM(original_size) as original_size,
                        SUM(compressed_size) as compressed_size
                    FROM archives
                    GROUP BY policy_name
                """)
                
                policies_stats = {}
                for row in cursor.fetchall():
                    policy_name = row[0]
                    count = row[1]
                    orig_size = row[2]
                    comp_size = row[3]
                    
                    policies_stats[policy_name] = {
                        "count": count,
                        "original_size": orig_size,
                        "compressed_size": comp_size,
                        "compression_ratio": (
                            (orig_size - comp_size) / orig_size
                            if orig_size > 0 else 0
                        )
                    }
                
                return ArchiveStats(
                    total_archives=total_archives,
                    total_original_size=total_original_size,
                    total_compressed_size=total_compressed_size,
                    compression_ratio=compression_ratio,
                    oldest_archive=oldest_archive,
                    newest_archive=newest_archive,
                    storage_usage=total_compressed_size,
                    policies_stats=policies_stats
                )
            finally:
                conn.close()


class LogArchiver:
    """Log archival system"""
    
    def __init__(self, archive_dir: str = "archives", db_path: str = "archives/archive.db"):
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        self.database = ArchiveDatabase(db_path)
        self.policies: Dict[str, ArchivePolicy] = {}
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="LogArchiver")
        self.scheduler_thread = None
        self.shutdown_event = threading.Event()
        
        # Default policies
        self._setup_default_policies()
        
        # Start scheduler
        self._start_scheduler()
    
    def _setup_default_policies(self):
        """Setup default archive policies"""
        # Daily archive policy
        daily_policy = ArchivePolicy(
            name="daily",
            retention_days=30,
            compression=True,
            compression_type="gzip",
            archive_interval="daily",
            verify_integrity=True
        )
        self.add_policy(daily_policy)
        
        # Weekly archive policy for older logs
        weekly_policy = ArchivePolicy(
            name="weekly",
            retention_days=365,
            compression=True,
            compression_type="tar.gz",
            archive_interval="weekly",
            verify_integrity=True
        )
        self.add_policy(weekly_policy)
        
        # Security logs policy (longer retention)
        security_policy = ArchivePolicy(
            name="security",
            retention_days=2555,  # 7 years
            compression=True,
            compression_type="zip",
            archive_interval="daily",
            verify_integrity=True,
            cleanup_after_archive=False  # Keep originals for security
        )
        self.add_policy(security_policy)
    
    def add_policy(self, policy: ArchivePolicy):
        """Add archive policy"""
        self.policies[policy.name] = policy
    
    def remove_policy(self, policy_name: str):
        """Remove archive policy"""
        self.policies.pop(policy_name, None)
    
    def _start_scheduler(self):
        """Start archive scheduler"""
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="ArchiveScheduler",
            daemon=True
        )
        self.scheduler_thread.start()
    
    def _scheduler_loop(self):
        """Archive scheduler loop"""
        # Schedule archive jobs
        schedule.every().hour.do(self._run_hourly_archives)
        schedule.every().day.at("02:00").do(self._run_daily_archives)
        schedule.every().week.do(self._run_weekly_archives)
        schedule.every().day.at("03:00").do(self._cleanup_old_archives)
        
        while not self.shutdown_event.is_set():
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def _run_hourly_archives(self):
        """Run hourly archive jobs"""
        for policy in self.policies.values():
            if policy.archive_interval == "hourly":
                self.executor.submit(self._archive_by_policy, policy)
    
    def _run_daily_archives(self):
        """Run daily archive jobs"""
        for policy in self.policies.values():
            if policy.archive_interval == "daily":
                self.executor.submit(self._archive_by_policy, policy)
    
    def _run_weekly_archives(self):
        """Run weekly archive jobs"""
        for policy in self.policies.values():
            if policy.archive_interval == "weekly":
                self.executor.submit(self._archive_by_policy, policy)
    
    def _archive_by_policy(self, policy: ArchivePolicy):
        """Archive logs according to policy"""
        try:
            # Find log files to archive
            log_files = self._find_archivable_files(policy)
            
            for log_file in log_files:
                self.archive_file(log_file, policy.name)
                
        except Exception as e:
            print(f"Error archiving with policy {policy.name}: {e}")
    
    def _find_archivable_files(self, policy: ArchivePolicy) -> List[Path]:
        """Find files that should be archived according to policy"""
        archivable_files = []
        
        # Look for log files in common locations
        log_locations = [
            Path("logs"),
            self.archive_dir.parent / "logs",
            Path("/var/log/aicleaner"),
            Path("/tmp/aicleaner/logs")
        ]
        
        cutoff_time = datetime.now() - timedelta(days=1)  # Archive files older than 1 day
        
        for location in log_locations:
            if not location.exists():
                continue
            
            for log_file in location.glob("*.log*"):
                if log_file.is_file():
                    # Check file age
                    file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    
                    if file_mtime < cutoff_time:
                        # Check if already archived
                        if not self._is_already_archived(log_file):
                            archivable_files.append(log_file)
        
        return archivable_files
    
    def _is_already_archived(self, file_path: Path) -> bool:
        """Check if file is already archived"""
        archives = self.database.list_archives()
        for archive in archives:
            if archive.original_file == str(file_path):
                return True
        return False
    
    async def archive_file(self, file_path: Union[str, Path], policy_name: str) -> Optional[ArchiveEntry]:
        """Archive a single file"""
        try:
            file_path = Path(file_path)
            policy = self.policies.get(policy_name)
            
            if not policy or not file_path.exists():
                return None
            
            # Generate archive ID and paths
            archive_id = f"{policy_name}_{file_path.stem}_{int(time.time())}"
            archive_file = self._get_archive_path(archive_id, policy)
            
            # Calculate original file checksum
            original_checksum = self._calculate_checksum(file_path)
            original_size = file_path.stat().st_size
            
            # Create archive
            if policy.compression:
                compressed_size = await self._compress_file(file_path, archive_file, policy.compression_type)
            else:
                shutil.copy2(file_path, archive_file)
                compressed_size = archive_file.stat().st_size
            
            # Verify integrity if enabled
            if policy.verify_integrity:
                if not await self._verify_archive_integrity(file_path, archive_file, policy.compression_type):
                    # Remove failed archive
                    if archive_file.exists():
                        archive_file.unlink()
                    raise Exception("Archive integrity verification failed")
            
            # Calculate compression ratio
            compression_ratio = (original_size - compressed_size) / original_size if original_size > 0 else 0
            
            # Create archive entry
            archive_entry = ArchiveEntry(
                archive_id=archive_id,
                original_file=str(file_path),
                archive_file=str(archive_file),
                created_date=datetime.now(),
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compression_ratio,
                checksum=original_checksum,
                policy_name=policy_name,
                metadata={
                    "compression_type": policy.compression_type if policy.compression else "none",
                    "original_mtime": file_path.stat().st_mtime
                }
            )
            
            # Save to database
            self.database.add_archive(archive_entry)
            
            # Clean up original file if policy allows
            if policy.cleanup_after_archive:
                file_path.unlink()
            
            return archive_entry
            
        except Exception as e:
            print(f"Error archiving file {file_path}: {e}")
            return None
    
    def _get_archive_path(self, archive_id: str, policy: ArchivePolicy) -> Path:
        """Get archive file path"""
        if policy.storage_location:
            base_dir = Path(policy.storage_location)
        else:
            base_dir = self.archive_dir
        
        # Organize by date
        date_dir = base_dir / datetime.now().strftime("%Y/%m/%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Add appropriate extension
        if policy.compression:
            if policy.compression_type == "gzip":
                extension = ".log.gz"
            elif policy.compression_type == "zip":
                extension = ".log.zip"
            elif policy.compression_type == "tar.gz":
                extension = ".log.tar.gz"
            else:
                extension = ".log.gz"
        else:
            extension = ".log"
        
        return date_dir / f"{archive_id}{extension}"
    
    async def _compress_file(self, source_file: Path, target_file: Path, compression_type: str) -> int:
        """Compress file and return compressed size"""
        if compression_type == "gzip":
            with open(source_file, 'rb') as f_in:
                with gzip.open(target_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        
        elif compression_type == "zip":
            with zipfile.ZipFile(target_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(source_file, source_file.name)
        
        elif compression_type == "tar.gz":
            with tarfile.open(target_file, 'w:gz') as tar:
                tar.add(source_file, arcname=source_file.name)
        
        else:
            raise ValueError(f"Unsupported compression type: {compression_type}")
        
        return target_file.stat().st_size
    
    async def _verify_archive_integrity(self, original_file: Path, archive_file: Path, compression_type: str) -> bool:
        """Verify archive integrity"""
        try:
            # Create temporary file for decompression
            temp_file = archive_file.parent / f"{archive_file.stem}_verify.tmp"
            
            try:
                # Decompress based on type
                if compression_type == "gzip":
                    with gzip.open(archive_file, 'rb') as f_in:
                        with open(temp_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                
                elif compression_type == "zip":
                    with zipfile.ZipFile(archive_file, 'r') as zipf:
                        with zipf.open(zipf.namelist()[0]) as f_in:
                            with open(temp_file, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                
                elif compression_type == "tar.gz":
                    with tarfile.open(archive_file, 'r:gz') as tar:
                        member = tar.getmembers()[0]
                        with tar.extractfile(member) as f_in:
                            with open(temp_file, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                
                # Compare checksums
                original_checksum = self._calculate_checksum(original_file)
                decompressed_checksum = self._calculate_checksum(temp_file)
                
                return original_checksum == decompressed_checksum
                
            finally:
                # Clean up temp file
                if temp_file.exists():
                    temp_file.unlink()
                    
        except Exception:
            return False
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate file checksum"""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    async def extract_archive(self, archive_id: str, extract_to: Optional[str] = None) -> Optional[Path]:
        """Extract archive by ID"""
        try:
            archive_entry = self.database.get_archive(archive_id)
            if not archive_entry:
                return None
            
            archive_file = Path(archive_entry.archive_file)
            if not archive_file.exists():
                return None
            
            # Determine extraction path
            if extract_to:
                extract_path = Path(extract_to)
            else:
                extract_path = archive_file.parent / f"extracted_{archive_id}"
            
            extract_path.mkdir(parents=True, exist_ok=True)
            
            # Extract based on compression type
            compression_type = archive_entry.metadata.get("compression_type", "none")
            
            if compression_type == "gzip":
                extracted_file = extract_path / Path(archive_entry.original_file).name
                with gzip.open(archive_file, 'rb') as f_in:
                    with open(extracted_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                return extracted_file
            
            elif compression_type == "zip":
                with zipfile.ZipFile(archive_file, 'r') as zipf:
                    zipf.extractall(extract_path)
                    return extract_path / zipf.namelist()[0]
            
            elif compression_type == "tar.gz":
                with tarfile.open(archive_file, 'r:gz') as tar:
                    tar.extractall(extract_path)
                    return extract_path / tar.getnames()[0]
            
            else:
                # No compression, just copy
                extracted_file = extract_path / Path(archive_entry.original_file).name
                shutil.copy2(archive_file, extracted_file)
                return extracted_file
                
        except Exception as e:
            print(f"Error extracting archive {archive_id}: {e}")
            return None
    
    def _cleanup_old_archives(self):
        """Clean up old archives based on retention policies"""
        try:
            for policy_name, policy in self.policies.items():
                cutoff_date = datetime.now() - timedelta(days=policy.retention_days)
                
                # Get old archives
                old_archives = [
                    archive for archive in self.database.list_archives(policy_name)
                    if archive.created_date < cutoff_date
                ]
                
                # Remove old archives
                for archive in old_archives:
                    try:
                        # Remove archive file
                        archive_file = Path(archive.archive_file)
                        if archive_file.exists():
                            archive_file.unlink()
                        
                        # Remove from database
                        self.database.remove_archive(archive.archive_id)
                        
                    except Exception as e:
                        print(f"Error removing old archive {archive.archive_id}: {e}")
                        
        except Exception as e:
            print(f"Error during archive cleanup: {e}")
    
    def search_archives(self, query: str, policy_name: Optional[str] = None,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> List[ArchiveEntry]:
        """Search archives by filename or metadata"""
        archives = self.database.list_archives(policy_name, start_date, end_date)
        
        matching_archives = []
        for archive in archives:
            # Search in filename
            if query.lower() in archive.original_file.lower():
                matching_archives.append(archive)
                continue
            
            # Search in archive filename
            if query.lower() in archive.archive_file.lower():
                matching_archives.append(archive)
                continue
            
            # Search in metadata
            metadata_str = json.dumps(archive.metadata).lower()
            if query.lower() in metadata_str:
                matching_archives.append(archive)
        
        return matching_archives
    
    def get_stats(self) -> ArchiveStats:
        """Get archive statistics"""
        return self.database.get_stats()
    
    def get_storage_usage(self) -> Dict[str, Any]:
        """Get detailed storage usage information"""
        stats = self.get_stats()
        
        # Calculate disk usage
        total_disk_usage = 0
        for archive_file in self.archive_dir.rglob("*"):
            if archive_file.is_file():
                total_disk_usage += archive_file.stat().st_size
        
        # Get available disk space
        disk_usage = shutil.disk_usage(self.archive_dir)
        
        return {
            "archive_storage_usage": stats.storage_usage,
            "disk_storage_usage": total_disk_usage,
            "available_space": disk_usage.free,
            "total_space": disk_usage.total,
            "used_percentage": (disk_usage.used / disk_usage.total) * 100,
            "compression_savings": stats.total_original_size - stats.total_compressed_size,
            "compression_ratio": stats.compression_ratio
        }
    
    def shutdown(self):
        """Shutdown archiver"""
        self.shutdown_event.set()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5.0)
        
        self.executor.shutdown(wait=True)


# Global archiver instance
_log_archiver: Optional[LogArchiver] = None


def get_log_archiver() -> LogArchiver:
    """Get global log archiver instance"""
    global _log_archiver
    if _log_archiver is None:
        _log_archiver = LogArchiver()
    return _log_archiver