#!/usr/bin/env python3
"""
AICleaner v3 Migration Script
Converts complex HA integration configurations to simple thin client format
"""

import os
import sys
import json
import yaml
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class HAIntegrationMigrator:
    """Migrates complex HA integration configs to thin client format"""
    
    def __init__(self, ha_config_dir: str = None):
        self.ha_config_dir = Path(ha_config_dir) if ha_config_dir else Path("/config")
        self.backup_dir = self.ha_config_dir / "aicleaner_migration_backup"
        self.integration_config_file = self.ha_config_dir / "custom_components" / "aicleaner_v3" / "config.yaml"
        self.new_integration_dir = self.ha_config_dir / "custom_components" / "aicleaner"
        
    def analyze_existing_config(self) -> Dict[str, Any]:
        """Analyze existing complex integration configuration"""
        logger.info("Analyzing existing AICleaner v3 configuration...")
        
        analysis = {
            "has_complex_integration": False,
            "core_service_running": False,
            "entities_to_migrate": [],
            "automation_references": [],
            "config_files": [],
            "estimated_complexity": "simple"
        }
        
        # Check for existing custom component
        old_integration_dir = self.ha_config_dir / "custom_components" / "aicleaner_v3"
        if old_integration_dir.exists():
            analysis["has_complex_integration"] = True
            analysis["config_files"].append(str(old_integration_dir))
            logger.info(f"Found existing complex integration at: {old_integration_dir}")
        
        # Check automations.yaml for aicleaner references
        automations_file = self.ha_config_dir / "automations.yaml"
        if automations_file.exists():
            try:
                with open(automations_file, 'r') as f:
                    automations = yaml.safe_load(f) or []
                
                for automation in automations:
                    if isinstance(automation, dict):
                        automation_yaml = yaml.dump(automation)
                        if "aicleaner" in automation_yaml.lower():
                            analysis["automation_references"].append(automation.get("alias", "Unknown"))
                            
            except Exception as e:
                logger.warning(f"Could not parse automations.yaml: {e}")
        
        # Estimate complexity based on findings
        if len(analysis["automation_references"]) > 5:
            analysis["estimated_complexity"] = "complex"
        elif len(analysis["automation_references"]) > 0:
            analysis["estimated_complexity"] = "moderate"
            
        return analysis
    
    def create_backup(self) -> bool:
        """Create backup of existing configuration"""
        try:
            logger.info("Creating backup of existing configuration...")
            
            if not self.backup_dir.exists():
                self.backup_dir.mkdir(parents=True)
            
            # Backup old integration directory
            old_integration_dir = self.ha_config_dir / "custom_components" / "aicleaner_v3"
            if old_integration_dir.exists():
                import shutil
                backup_integration_dir = self.backup_dir / "aicleaner_v3_complex"
                if backup_integration_dir.exists():
                    shutil.rmtree(backup_integration_dir)
                shutil.copytree(old_integration_dir, backup_integration_dir)
                logger.info(f"Backed up complex integration to: {backup_integration_dir}")
            
            # Backup automations
            automations_file = self.ha_config_dir / "automations.yaml"
            if automations_file.exists():
                backup_automations = self.backup_dir / "automations_backup.yaml"
                import shutil
                shutil.copy2(automations_file, backup_automations)
                logger.info(f"Backed up automations to: {backup_automations}")
            
            return True
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return False
    
    def generate_thin_client_config(self) -> Dict[str, Any]:
        """Generate configuration for thin client integration"""
        logger.info("Generating thin client configuration...")
        
        # Default thin client configuration
        config = {
            "host": "localhost",
            "port": 8000,
            "api_key": None,  # Optional for local connections
            "update_interval": 30,  # seconds
            "sensors": {
                "status": True,
                "uptime": True,
                "providers": True
            },
            "services": {
                "analyze_camera": True
            }
        }
        
        # Try to extract settings from existing config
        try:
            # Look for core service configuration
            core_config_file = Path("/home/drewcifer/aicleaner_v3/core/config.user.yaml")
            if core_config_file.exists():
                with open(core_config_file, 'r') as f:
                    core_config = yaml.safe_load(f) or {}
                
                # Extract service configuration
                service_config = core_config.get('service', {}).get('api', {})
                if service_config:
                    config["host"] = service_config.get('host', 'localhost')
                    config["port"] = service_config.get('port', 8000)
                    logger.info(f"Found core service config: {config['host']}:{config['port']}")
            
        except Exception as e:
            logger.warning(f"Could not read core service config: {e}")
        
        return config
    
    def install_thin_client(self, config: Dict[str, Any]) -> bool:
        """Install the new thin client integration"""
        try:
            logger.info("Installing thin client integration...")
            
            # Create new integration directory
            if not self.new_integration_dir.exists():
                self.new_integration_dir.mkdir(parents=True)
            
            # Copy thin client files from our source
            source_dir = Path("/home/drewcifer/aicleaner_v3/custom_components/aicleaner")
            if source_dir.exists():
                import shutil
                for file_path in source_dir.rglob("*"):
                    if file_path.is_file():
                        rel_path = file_path.relative_to(source_dir)
                        dest_path = self.new_integration_dir / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, dest_path)
                
                logger.info(f"Installed thin client to: {self.new_integration_dir}")
            else:
                logger.error(f"Source thin client not found at: {source_dir}")
                return False
            
            # Create default configuration file
            config_file = self.new_integration_dir / "default_config.json"
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Thin client installation failed: {e}")
            return False
    
    def generate_migration_report(self, analysis: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Generate human-readable migration report"""
        
        report = f"""
AICleaner v3 Migration Report
=============================

Migration Date: {import_datetime().now().strftime('%Y-%m-%d %H:%M:%S')}

ANALYSIS SUMMARY:
- Complex Integration Found: {'Yes' if analysis['has_complex_integration'] else 'No'}
- Automation References: {len(analysis['automation_references'])}
- Estimated Complexity: {analysis['estimated_complexity'].title()}

MIGRATION ACTIONS:
✓ Created backup in: {self.backup_dir}
✓ Installed thin client integration
✓ Generated default configuration

NEW CONFIGURATION:
- Core Service: {config['host']}:{config['port']}
- Update Interval: {config['update_interval']} seconds
- API Key Required: {'Yes' if config['api_key'] else 'No (local)'}

NEXT STEPS:
1. Restart Home Assistant
2. Go to Settings > Devices & Services
3. Add "AICleaner" integration
4. Configure connection to core service
5. Update automations to use new service calls:
   - service: aicleaner.analyze_camera
   - entity: sensor.aicleaner_status

AUTOMATION MIGRATION:
The following automations reference AICleaner and may need updates:
"""
        
        for automation in analysis["automation_references"]:
            report += f"- {automation}\n"
        
        if not analysis["automation_references"]:
            report += "- No automations found that reference AICleaner\n"
        
        report += f"""
ROLLBACK INSTRUCTIONS:
If you need to rollback this migration:
1. Remove new integration: {self.new_integration_dir}
2. Restore from backup: {self.backup_dir}/aicleaner_v3_complex
3. Restart Home Assistant

For support, see: https://github.com/username/aicleaner_v3/wiki/Migration-Guide
"""
        
        return report
    
    def run_migration(self, dry_run: bool = False) -> bool:
        """Run the complete migration process"""
        logger.info("Starting AICleaner v3 HA Integration Migration...")
        
        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
        
        # Step 1: Analyze existing configuration
        analysis = self.analyze_existing_config()
        logger.info(f"Analysis complete. Complexity: {analysis['estimated_complexity']}")
        
        if not analysis["has_complex_integration"]:
            logger.info("No complex integration found. Migration not needed.")
            return True
        
        # Step 2: Create backup
        if not dry_run:
            if not self.create_backup():
                logger.error("Backup creation failed. Aborting migration.")
                return False
        else:
            logger.info("DRY RUN: Would create backup")
        
        # Step 3: Generate thin client config
        config = self.generate_thin_client_config()
        
        # Step 4: Install thin client
        if not dry_run:
            if not self.install_thin_client(config):
                logger.error("Thin client installation failed")
                return False
        else:
            logger.info("DRY RUN: Would install thin client")
        
        # Step 5: Generate report
        report = self.generate_migration_report(analysis, config)
        
        report_file = self.backup_dir / "migration_report.txt" if not dry_run else Path("/tmp/aicleaner_migration_report.txt")
        if not dry_run:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Migration report saved to: {report_file}")
        
        if dry_run:
            print("\n" + "="*50)
            print("DRY RUN REPORT:")
            print("="*50)
            print(report)
        
        logger.info("Migration completed successfully!")
        return True


def import_datetime():
    """Import datetime to avoid issues with top-level imports"""
    import datetime
    return datetime


def main():
    parser = argparse.ArgumentParser(description="Migrate AICleaner v3 HA integration to thin client")
    parser.add_argument("--ha-config", default="/config", help="Home Assistant config directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    migrator = HAIntegrationMigrator(args.ha_config)
    
    try:
        success = migrator.run_migration(dry_run=args.dry_run)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()