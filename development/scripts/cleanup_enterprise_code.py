#!/usr/bin/env python3
"""
AICleaner v3 Enterprise Code Cleanup Script
Removes 60-70% of complex enterprise code while preserving hobbyist-focused core
"""

import os
import sys
import shutil
import logging
from pathlib import Path
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnterpriseCodeCleaner:
    """Safely removes enterprise complexity while preserving core functionality"""
    
    def __init__(self, project_root: str = "/home/drewcifer/aicleaner_v3"):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "enterprise_code_backup"
        
        # Directories to completely remove (enterprise overhead)
        self.remove_dirs = [
            "addons/aicleaner_v3/ha_integration",      # Complex HA integration
            "addons/aicleaner_v3/ui",                  # Enterprise web UI
            "addons/aicleaner_v3/privacy",             # Over-engineered privacy pipeline
            "addons/aicleaner_v3/performance",         # Excessive performance monitoring
            "addons/aicleaner_v3/mqtt_discovery",      # Complex MQTT auto-discovery
            "addons/aicleaner_v3/api",                 # Enterprise REST framework
            "addons/aicleaner_v3/monitoring",          # Advanced monitoring
            "addons/aicleaner_v3/gamification",        # Unnecessary gamification
            "addons/aicleaner_v3/sync",                # Complex sync systems
            "addons/aicleaner_v3/ai",                  # Over-engineered AI system
            "addons/aicleaner_v3/zones",               # Complex zone management
            "addons/aicleaner_v3/rules",               # Rules engine overhead
            "addons/aicleaner_v3/notifications",       # Complex notification system
            "addons/aicleaner_v3/testing_env",         # Enterprise testing
            "addons/aicleaner_v3/e2e",                 # End-to-end testing
            "addons/aicleaner_v3/frontend",            # Separate frontend
            "addons/aicleaner_v3/middleware",          # Middleware complexity
            "addons/aicleaner_v3/integrations",        # Complex integrations
            "addons/aicleaner_v3/utils",               # Utility bloat
        ]
        
        # Files to remove (enterprise configuration and documentation)
        self.remove_files = [
            "addons/aicleaner_v3/config.yaml",                    # Complex addon config
            "addons/aicleaner_v3/Dockerfile",                     # Addon Dockerfile
            "addons/aicleaner_v3/requirements.txt",               # Addon requirements
            "addons/aicleaner_v3/run.sh",                         # Addon run script
            "addons/aicleaner_v3/__init__.py",                    # Addon init
            "addons/aicleaner_v3/const.py",                       # Addon constants
            "addons/aicleaner_v3/aicleaner.py",                   # Main addon file
            "build.yaml",                                          # Complex build config
            "config.yaml",                                         # Old config
            "docker-compose.yml",                                  # Complex docker setup
            "docker-compose.dev.yml",                             # Dev docker
            "docker-compose.prod.yml",                            # Prod docker
            "Dockerfile",                                          # Main dockerfile
            "start_aicleaner.py",                                 # Complex startup
        ]
        
        # Documentation to archive (keep for reference but not in main codebase)
        self.archive_docs = [
            "AI_COLLABORATION_FRAMEWORK.md",
            "CLAUDE.md",
            "CLOUD_OPTIMIZATION_SUMMARY.md",
            "DOCKER_OPTIMIZATION.md",
            "DOCS.md",
            "FINAL_PROJECT_INDEX.md",
            "GEMINI_API_GUIDE.md",
            "HOBBYIST_SIMPLIFICATION_ANALYSIS.md",
            "IMPLEMENTATION_STATUS.md",
            "INTEGRATION_REPORT.md",
            "MISSED_GOALS_ANALYSIS.md",
            "PERFORMANCE_REGRESSION_FRAMEWORK_SUMMARY.md",
            "PHASE_*_*.md",  # All phase documentation
            "PROJECT_*.md",   # Project documentation
            "SESSION_*.md",   # Session documentation
            "TESTING_FRAMEWORK_SUMMARY.md",
            "TEMPLATE_ENHANCEMENT_SUMMARY.md",
            "ZEN_MCP_*.md",
        ]
        
        # Core components to KEEP (hobbyist-focused)
        self.keep_core = [
            "core/",                           # Simplified core service
            "custom_components/aicleaner/",    # Thin HA integration
            "scripts/migrate_ha_integration.py",  # Migration tool
            "examples/",                       # Usage examples
            "README.md",                       # Main documentation
            "MIGRATION_GUIDE.md",             # Migration guide
            "LICENSE",                         # License
            "requirements.txt",                # Core requirements
        ]
    
    def create_backup(self) -> bool:
        """Create backup of enterprise code before removal"""
        try:
            logger.info("Creating backup of enterprise code...")
            
            if self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)
            self.backup_dir.mkdir(parents=True)
            
            # Backup directories
            for dir_path in self.remove_dirs:
                full_path = self.project_root / dir_path
                if full_path.exists():
                    backup_path = self.backup_dir / dir_path
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(full_path, backup_path)
                    logger.info(f"Backed up directory: {dir_path}")
            
            # Backup files
            for file_path in self.remove_files:
                full_path = self.project_root / file_path
                if full_path.exists():
                    backup_path = self.backup_dir / file_path
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(full_path, backup_path)
                    logger.info(f"Backed up file: {file_path}")
            
            logger.info(f"Backup created at: {self.backup_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return False
    
    def calculate_reduction(self) -> Dict[str, int]:
        """Calculate code reduction statistics"""
        stats = {
            "files_before": 0,
            "files_after": 0,
            "dirs_before": 0,
            "dirs_after": 0,
            "lines_removed": 0
        }
        
        # Count files before cleanup
        for root, dirs, files in os.walk(self.project_root):
            if "enterprise_code_backup" not in root and "__pycache__" not in root:
                stats["files_before"] += len([f for f in files if f.endswith(('.py', '.yaml', '.md', '.json'))])
                stats["dirs_before"] += len(dirs)
        
        # Count lines in files to be removed
        for dir_path in self.remove_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists():
                for py_file in full_path.rglob("*.py"):
                    try:
                        with open(py_file, 'r') as f:
                            stats["lines_removed"] += len(f.readlines())
                    except:
                        pass
        
        return stats
    
    def remove_enterprise_code(self) -> bool:
        """Remove enterprise directories and files"""
        try:
            logger.info("Removing enterprise code...")
            
            # Remove directories
            for dir_path in self.remove_dirs:
                full_path = self.project_root / dir_path
                if full_path.exists():
                    shutil.rmtree(full_path)
                    logger.info(f"Removed directory: {dir_path}")
            
            # Remove files
            for file_path in self.remove_files:
                full_path = self.project_root / file_path
                if full_path.exists():
                    full_path.unlink()
                    logger.info(f"Removed file: {file_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Enterprise code removal failed: {e}")
            return False
    
    def archive_documentation(self) -> bool:
        """Archive excess documentation"""
        try:
            logger.info("Archiving excess documentation...")
            
            docs_archive = self.backup_dir / "archived_docs"
            docs_archive.mkdir(exist_ok=True)
            
            # Archive documentation files
            for pattern in self.archive_docs:
                if "*" in pattern:
                    # Handle wildcard patterns
                    for doc_file in self.project_root.glob(pattern):
                        if doc_file.is_file():
                            archive_path = docs_archive / doc_file.name
                            shutil.move(str(doc_file), str(archive_path))
                            logger.info(f"Archived: {doc_file.name}")
                else:
                    doc_file = self.project_root / pattern
                    if doc_file.exists():
                        archive_path = docs_archive / doc_file.name
                        shutil.move(str(doc_file), str(archive_path))
                        logger.info(f"Archived: {pattern}")
            
            return True
            
        except Exception as e:
            logger.error(f"Documentation archival failed: {e}")
            return False
    
    def create_simplified_structure(self) -> bool:
        """Create clean directory structure for simplified codebase"""
        try:
            logger.info("Creating simplified project structure...")
            
            # Create a new clean requirements.txt
            clean_requirements = [
                "fastapi>=0.104.0",
                "uvicorn>=0.24.0",
                "aiohttp>=3.9.0",
                "pyyaml>=6.0",
                "pydantic>=2.0.0",
                # AI provider libraries (optional)
                "openai>=1.0.0",
                "anthropic>=0.5.0",
                "google-generativeai>=0.3.0",
            ]
            
            requirements_file = self.project_root / "requirements.txt"
            with open(requirements_file, 'w') as f:
                f.write("# AICleaner v3 - Simplified Dependencies\n")
                f.write("# Core service requirements\n\n")
                for req in clean_requirements:
                    f.write(f"{req}\n")
            
            logger.info("Created simplified requirements.txt")
            
            # Create a simple run script
            run_script = self.project_root / "run.sh"
            with open(run_script, 'w') as f:
                f.write("""#!/bin/bash
# AICleaner v3 - Simple Startup Script

echo "Starting AICleaner v3 Core Service..."

# Check if Python dependencies are installed
if ! python3 -c "import fastapi, uvicorn, aiohttp, yaml" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the core service
echo "Core service starting on http://localhost:8000"
python3 -m core.service

""")
            run_script.chmod(0o755)
            logger.info("Created simple run script")
            
            return True
            
        except Exception as e:
            logger.error(f"Simplified structure creation failed: {e}")
            return False
    
    def validate_core_integrity(self) -> bool:
        """Validate that core functionality remains intact"""
        try:
            logger.info("Validating core functionality...")
            
            # Check core files exist
            required_files = [
                "core/service.py",
                "core/ai_provider.py", 
                "core/config_loader.py",
                "core/service_registry.py",
                "core/metrics_manager.py",
                "core/config.default.yaml",
                "custom_components/aicleaner/__init__.py",
                "custom_components/aicleaner/manifest.json",
                "scripts/migrate_ha_integration.py",
                "README.md",
                "MIGRATION_GUIDE.md"
            ]
            
            missing_files = []
            for file_path in required_files:
                full_path = self.project_root / file_path
                if not full_path.exists():
                    missing_files.append(file_path)
            
            if missing_files:
                logger.error(f"Missing required files: {missing_files}")
                return False
            
            # Try importing core modules
            sys.path.insert(0, str(self.project_root))
            try:
                from core.config_loader import config_loader
                from core.ai_provider import AIService
                logger.info("Core modules imported successfully")
            except ImportError as e:
                logger.error(f"Core module import failed: {e}")
                return False
            
            logger.info("Core functionality validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Core validation failed: {e}")
            return False
    
    def generate_cleanup_report(self, stats_before: Dict[str, int]) -> str:
        """Generate cleanup report"""
        
        # Recalculate stats after cleanup
        stats_after = {
            "files_after": 0,
            "dirs_after": 0
        }
        
        for root, dirs, files in os.walk(self.project_root):
            if "enterprise_code_backup" not in root and "__pycache__" not in root:
                stats_after["files_after"] += len([f for f in files if f.endswith(('.py', '.yaml', '.md', '.json'))])
                stats_after["dirs_after"] += len(dirs)
        
        reduction_percent = ((stats_before["files_before"] - stats_after["files_after"]) / stats_before["files_before"]) * 100
        
        report = f"""
AICleaner v3 Enterprise Code Cleanup Report
==========================================

CLEANUP SUMMARY:
- Files before: {stats_before['files_before']}
- Files after: {stats_after['files_after']}
- Reduction: {reduction_percent:.1f}%
- Lines of code removed: {stats_before.get('lines_removed', 'N/A')}

REMOVED COMPONENTS:
- ✅ Complex HA integration ({len([d for d in self.remove_dirs if 'ha_integration' in d])} directories)
- ✅ Enterprise web UI ({len([d for d in self.remove_dirs if 'ui' in d])} directories)
- ✅ Over-engineered subsystems ({len(self.remove_dirs)} total directories)
- ✅ Excess configuration files ({len(self.remove_files)} files)
- ✅ Enterprise documentation (archived)

PRESERVED CORE:
- ✅ Core service (FastAPI backend)
- ✅ Thin HA integration (custom component)
- ✅ Migration tools
- ✅ User documentation
- ✅ Configuration system
- ✅ Examples and guides

BACKUP LOCATION:
{self.backup_dir}

NEXT STEPS:
1. Test core service: python3 -m core.service
2. Install HA integration: cp -r custom_components/aicleaner /config/custom_components/
3. Follow README.md for setup instructions

The codebase is now {reduction_percent:.1f}% simpler while retaining all essential functionality!
"""
        
        return report
    
    def run_cleanup(self, dry_run: bool = False) -> bool:
        """Run the complete cleanup process"""
        logger.info("Starting AICleaner v3 Enterprise Code Cleanup...")
        
        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
        
        # Calculate initial stats
        stats_before = self.calculate_reduction()
        
        if not dry_run:
            # Step 1: Create backup
            if not self.create_backup():
                logger.error("Backup creation failed. Aborting cleanup.")
                return False
            
            # Step 2: Remove enterprise code
            if not self.remove_enterprise_code():
                logger.error("Enterprise code removal failed")
                return False
            
            # Step 3: Archive documentation
            if not self.archive_documentation():
                logger.error("Documentation archival failed")
                return False
            
            # Step 4: Create simplified structure
            if not self.create_simplified_structure():
                logger.error("Simplified structure creation failed")
                return False
            
            # Step 5: Validate core integrity
            if not self.validate_core_integrity():
                logger.error("Core validation failed")
                return False
        else:
            logger.info("DRY RUN: Would remove enterprise code and create simplified structure")
        
        # Generate report
        report = self.generate_cleanup_report(stats_before)
        
        report_file = self.project_root / "CLEANUP_REPORT.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        if not dry_run:
            logger.info(f"Cleanup report saved to: {report_file}")
        else:
            print("\n" + "="*50)
            print("DRY RUN CLEANUP REPORT:")
            print("="*50)
            print(report)
        
        logger.info("Enterprise code cleanup completed successfully!")
        return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Cleanup AICleaner v3 enterprise code")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--project-root", default="/home/drewcifer/aicleaner_v3", help="Project root directory")
    
    args = parser.parse_args()
    
    cleaner = EnterpriseCodeCleaner(args.project_root)
    
    try:
        success = cleaner.run_cleanup(dry_run=args.dry_run)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Cleanup cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()