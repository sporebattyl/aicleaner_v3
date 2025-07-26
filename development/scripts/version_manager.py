#!/usr/bin/env python3
"""
Version Manager for AICleaner v3 Home Assistant Add-on
Manages semantic versioning across all project files
"""

import os
import re
import sys
import yaml
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class VersionManager:
    """Manages version across all project files"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.config_file = self.project_root / "config.yaml"
        self.changelog_file = self.project_root / "CHANGELOG.md"
        self.version_files = {
            "config.yaml": self._update_config_version,
            "Dockerfile": self._update_dockerfile_version,
            "README.md": self._update_readme_version,
            "addons/aicleaner_v3/core/version.py": self._update_python_version,
        }
    
    def get_current_version(self) -> str:
        """Get current version from config.yaml"""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
                return config.get('version', '0.0.0')
        except FileNotFoundError:
            print(f"Error: {self.config_file} not found")
            return "0.0.0"
        except yaml.YAMLError as e:
            print(f"Error parsing {self.config_file}: {e}")
            return "0.0.0"
    
    def parse_version(self, version: str) -> Tuple[int, int, int]:
        """Parse semantic version string"""
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-.*)?$', version)
        if not match:
            raise ValueError(f"Invalid version format: {version}")
        
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    
    def increment_version(self, current_version: str, increment_type: str) -> str:
        """Increment version based on type (major, minor, patch)"""
        major, minor, patch = self.parse_version(current_version)
        
        if increment_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif increment_type == "minor":
            minor += 1
            patch = 0
        elif increment_type == "patch":
            patch += 1
        else:
            raise ValueError(f"Invalid increment type: {increment_type}")
        
        return f"{major}.{minor}.{patch}"
    
    def _update_config_version(self, file_path: Path, new_version: str) -> bool:
        """Update version in config.yaml"""
        try:
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
            
            config['version'] = new_version
            
            with open(file_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            return True
        except Exception as e:
            print(f"Error updating {file_path}: {e}")
            return False
    
    def _update_dockerfile_version(self, file_path: Path, new_version: str) -> bool:
        """Update version in Dockerfile labels"""
        try:
            content = file_path.read_text()
            
            # Update version label
            content = re.sub(
                r'io\.hass\.version="[^"]*"',
                f'io.hass.version="{new_version}"',
                content
            )
            
            file_path.write_text(content)
            return True
        except Exception as e:
            print(f"Error updating {file_path}: {e}")
            return False
    
    def _update_readme_version(self, file_path: Path, new_version: str) -> bool:
        """Update version references in README.md"""
        try:
            content = file_path.read_text()
            
            # Update version badge
            content = re.sub(
                r'release/drewcifer/aicleaner_v3\.svg',
                f'release/drewcifer/aicleaner_v3.svg',
                content
            )
            
            file_path.write_text(content)
            return True
        except Exception as e:
            print(f"Error updating {file_path}: {e}")
            return False
    
    def _update_python_version(self, file_path: Path, new_version: str) -> bool:
        """Update version in Python version file"""
        try:
            # Create version file if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            content = f'''"""
AICleaner v3 Version Information
"""

__version__ = "{new_version}"
__build_date__ = "{datetime.now().isoformat()}"
__git_hash__ = "unknown"  # Will be updated during build

def get_version_info():
    """Get version information"""
    return {{
        "version": __version__,
        "build_date": __build_date__,
        "git_hash": __git_hash__
    }}
'''
            
            file_path.write_text(content)
            return True
        except Exception as e:
            print(f"Error updating {file_path}: {e}")
            return False
    
    def update_all_versions(self, new_version: str) -> bool:
        """Update version in all project files"""
        success = True
        
        for file_path, update_func in self.version_files.items():
            full_path = self.project_root / file_path
            
            if full_path.exists() or file_path == "addons/aicleaner_v3/core/version.py":
                if not update_func(full_path, new_version):
                    success = False
                    print(f"Failed to update {file_path}")
                else:
                    print(f"Updated {file_path} to version {new_version}")
            else:
                print(f"Skipping {file_path} (not found)")
        
        return success
    
    def create_changelog_entry(self, version: str, changes: List[str]) -> bool:
        """Create changelog entry for new version"""
        try:
            changelog_path = self.changelog_file
            
            # Read existing changelog or create header
            if changelog_path.exists():
                existing_content = changelog_path.read_text()
            else:
                existing_content = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"
            
            # Create new entry
            date_str = datetime.now().strftime("%Y-%m-%d")
            new_entry = f"## [{version}] - {date_str}\n\n"
            
            if changes:
                for change in changes:
                    new_entry += f"- {change}\n"
            else:
                new_entry += "- Initial release\n"
            
            new_entry += "\n"
            
            # Insert new entry after the header
            lines = existing_content.split('\n')
            header_end = 0
            for i, line in enumerate(lines):
                if line.startswith('## [') or i == len(lines) - 1:
                    header_end = i
                    break
            
            # Insert new entry
            lines.insert(header_end, new_entry)
            
            # Write updated changelog
            changelog_path.write_text('\n'.join(lines))
            print(f"Updated changelog with version {version}")
            return True
            
        except Exception as e:
            print(f"Error updating changelog: {e}")
            return False
    
    def validate_version(self, version: str) -> bool:
        """Validate version format"""
        try:
            self.parse_version(version)
            return True
        except ValueError:
            return False
    
    def get_version_history(self) -> List[str]:
        """Get version history from changelog"""
        try:
            if not self.changelog_file.exists():
                return []
            
            content = self.changelog_file.read_text()
            versions = re.findall(r'## \[([^\]]+)\]', content)
            return versions
        except Exception as e:
            print(f"Error reading version history: {e}")
            return []


def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print("Usage: python version_manager.py <command> [args]")
        print("Commands:")
        print("  current                    - Show current version")
        print("  bump <major|minor|patch>   - Bump version")
        print("  set <version>              - Set specific version")
        print("  history                    - Show version history")
        print("  validate <version>         - Validate version format")
        sys.exit(1)
    
    vm = VersionManager()
    command = sys.argv[1]
    
    if command == "current":
        print(f"Current version: {vm.get_current_version()}")
    
    elif command == "bump":
        if len(sys.argv) < 3:
            print("Usage: python version_manager.py bump <major|minor|patch>")
            sys.exit(1)
        
        increment_type = sys.argv[2]
        current_version = vm.get_current_version()
        new_version = vm.increment_version(current_version, increment_type)
        
        print(f"Bumping version from {current_version} to {new_version}")
        
        # Get changelog entries if provided
        changes = sys.argv[3:] if len(sys.argv) > 3 else []
        
        if vm.update_all_versions(new_version):
            vm.create_changelog_entry(new_version, changes)
            print(f"Successfully bumped version to {new_version}")
        else:
            print("Failed to update all version files")
            sys.exit(1)
    
    elif command == "set":
        if len(sys.argv) < 3:
            print("Usage: python version_manager.py set <version>")
            sys.exit(1)
        
        new_version = sys.argv[2]
        
        if not vm.validate_version(new_version):
            print(f"Invalid version format: {new_version}")
            sys.exit(1)
        
        current_version = vm.get_current_version()
        print(f"Setting version from {current_version} to {new_version}")
        
        # Get changelog entries if provided
        changes = sys.argv[3:] if len(sys.argv) > 3 else []
        
        if vm.update_all_versions(new_version):
            vm.create_changelog_entry(new_version, changes)
            print(f"Successfully set version to {new_version}")
        else:
            print("Failed to update all version files")
            sys.exit(1)
    
    elif command == "history":
        history = vm.get_version_history()
        if history:
            print("Version history:")
            for version in history:
                print(f"  {version}")
        else:
            print("No version history found")
    
    elif command == "validate":
        if len(sys.argv) < 3:
            print("Usage: python version_manager.py validate <version>")
            sys.exit(1)
        
        version = sys.argv[2]
        if vm.validate_version(version):
            print(f"Valid version: {version}")
        else:
            print(f"Invalid version: {version}")
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()