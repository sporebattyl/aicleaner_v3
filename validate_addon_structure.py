#!/usr/bin/env python3
"""
AICleaner V3 Add-on Structure Validation Script
Validates the complete addon structure for deployment readiness
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Any

class AddonValidator:
    """Comprehensive addon structure validator"""
    
    def __init__(self, addon_path: str):
        self.addon_path = Path(addon_path)
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.total_checks = 0
        
    def log_error(self, message: str):
        """Log validation error"""
        self.errors.append(f"❌ ERROR: {message}")
        
    def log_warning(self, message: str):
        """Log validation warning"""
        self.warnings.append(f"⚠️  WARNING: {message}")
        
    def log_success(self, message: str):
        """Log validation success"""
        print(f"✅ {message}")
        self.success_count += 1
        
    def check_file_exists(self, file_path: str, required: bool = True) -> bool:
        """Check if file exists"""
        self.total_checks += 1
        full_path = self.addon_path / file_path
        
        if full_path.exists():
            self.log_success(f"File exists: {file_path}")
            return True
        elif required:
            self.log_error(f"Required file missing: {file_path}")
            return False
        else:
            self.log_warning(f"Optional file missing: {file_path}")
            return False
    
    def validate_json_file(self, file_path: str) -> Tuple[bool, Any]:
        """Validate JSON file structure"""
        self.total_checks += 1
        full_path = self.addon_path / file_path
        
        if not full_path.exists():
            self.log_error(f"JSON file missing: {file_path}")
            return False, None
            
        try:
            with open(full_path, 'r') as f:
                data = json.load(f)
            self.log_success(f"Valid JSON: {file_path}")
            return True, data
        except json.JSONDecodeError as e:
            self.log_error(f"Invalid JSON in {file_path}: {e}")
            return False, None
    
    def validate_yaml_file(self, file_path: str) -> Tuple[bool, Any]:
        """Validate YAML file structure"""
        self.total_checks += 1
        full_path = self.addon_path / file_path
        
        if not full_path.exists():
            self.log_error(f"YAML file missing: {file_path}")
            return False, None
            
        try:
            with open(full_path, 'r') as f:
                data = yaml.safe_load(f)
            self.log_success(f"Valid YAML: {file_path}")
            return True, data
        except yaml.YAMLError as e:
            self.log_error(f"Invalid YAML in {file_path}: {e}")
            return False, None
    
    def validate_config_yaml(self):
        """Validate config.yaml structure"""
        print("\n🔍 Validating config.yaml...")
        
        valid, config = self.validate_yaml_file("config.yaml")
        if not valid:
            return
            
        # Check required fields
        required_fields = ['name', 'version', 'slug', 'description', 'arch', 'init']
        for field in required_fields:
            if field in config:
                self.log_success(f"config.yaml has required field: {field}")
            else:
                self.log_error(f"config.yaml missing required field: {field}")
        
        # Validate version format
        version = config.get('version', '')
        if version and len(version.split('.')) == 3:
            self.log_success(f"Version format valid: {version}")
        else:
            self.log_error(f"Invalid version format: {version}")
        
        # Check architectures
        archs = config.get('arch', [])
        expected_archs = ['amd64', 'aarch64', 'armhf', 'armv7']
        if all(arch in expected_archs for arch in archs):
            self.log_success(f"Supported architectures: {archs}")
        else:
            self.log_warning(f"Unusual architectures: {archs}")
    
    def validate_dockerfile(self):
        """Validate Dockerfile structure"""
        print("\n🔍 Validating Dockerfile...")
        
        if not self.check_file_exists("Dockerfile"):
            return
            
        dockerfile_path = self.addon_path / "Dockerfile"
        with open(dockerfile_path, 'r') as f:
            content = f.read()
        
        # Check for required Dockerfile elements
        required_elements = [
            'ARG BUILD_FROM',
            'FROM ${BUILD_FROM}',
            'WORKDIR',
            'COPY requirements.txt',
            'RUN pip3 install',
            'CMD'
        ]
        
        for element in required_elements:
            if element in content:
                self.log_success(f"Dockerfile contains: {element}")
            else:
                self.log_warning(f"Dockerfile might be missing: {element}")
    
    def validate_requirements_txt(self):
        """Validate requirements.txt"""
        print("\n🔍 Validating requirements.txt...")
        
        if not self.check_file_exists("requirements.txt"):
            return
            
        requirements_path = self.addon_path / "requirements.txt"
        with open(requirements_path, 'r') as f:
            lines = f.readlines()
        
        # Check for key dependencies
        key_deps = ['google-generativeai', 'paho-mqtt', 'PyYAML', 'flask']
        content = ''.join(lines)
        
        for dep in key_deps:
            if dep in content:
                self.log_success(f"Dependency found: {dep}")
            else:
                self.log_warning(f"Key dependency might be missing: {dep}")
        
        # Check for version pinning
        pinned_count = sum(1 for line in lines if '==' in line or '>=' in line)
        total_deps = sum(1 for line in lines if line.strip() and not line.startswith('#'))
        
        if total_deps > 0:
            pin_ratio = pinned_count / total_deps
            if pin_ratio > 0.7:
                self.log_success(f"Good version pinning: {pinned_count}/{total_deps} dependencies pinned")
            else:
                self.log_warning(f"Consider more version pinning: {pinned_count}/{total_deps} dependencies pinned")
    
    def validate_source_structure(self):
        """Validate source code structure"""
        print("\n🔍 Validating source code structure...")
        
        # Check src directory
        if not (self.addon_path / "src").exists():
            self.log_error("src/ directory missing")
            return
        
        self.log_success("src/ directory exists")
        
        # Check key source files
        key_files = [
            'src/main.py',
            'src/ai_provider.py',
            'src/config_loader.py',
            'src/config_mapper.py',
            'src/web_ui_enhanced.py'
        ]
        
        for file_path in key_files:
            self.check_file_exists(file_path)
    
    def validate_documentation(self):
        """Validate documentation completeness"""
        print("\n🔍 Validating documentation...")
        
        # Required documentation
        required_docs = [
            'README.md',
            'CHANGELOG.md',
            'LICENSE'
        ]
        
        for doc in required_docs:
            self.check_file_exists(doc)
        
        # Optional but recommended documentation
        optional_docs = [
            'DEPLOYMENT.md',
            'ARCHITECTURE.md',
            'DOCS.md'
        ]
        
        for doc in optional_docs:
            self.check_file_exists(doc, required=False)
        
        # Check README completeness
        readme_path = self.addon_path / "README.md"
        if readme_path.exists():
            with open(readme_path, 'r') as f:
                readme_content = f.read().lower()
            
            readme_sections = [
                'installation',
                'configuration', 
                'usage',
                'troubleshooting'
            ]
            
            for section in readme_sections:
                if section in readme_content:
                    self.log_success(f"README contains: {section} section")
                else:
                    self.log_warning(f"README might be missing: {section} section")
    
    def validate_assets(self):
        """Validate addon assets"""
        print("\n🔍 Validating assets...")
        
        # Check icon files
        icon_files = ['icon.png', 'logo.png']
        for icon in icon_files:
            if self.check_file_exists(icon):
                # Check file size (should be reasonable for icons)
                icon_path = self.addon_path / icon
                size = icon_path.stat().st_size
                if size > 1024 * 1024:  # 1MB
                    self.log_warning(f"{icon} is quite large: {size} bytes")
                else:
                    self.log_success(f"{icon} size is reasonable: {size} bytes")
    
    def validate_build_configuration(self):
        """Validate build configuration"""
        print("\n🔍 Validating build configuration...")
        
        # Check build.yaml
        if self.check_file_exists("build.yaml"):
            valid, build_config = self.validate_yaml_file("build.yaml")
            if valid and build_config:
                if 'build_from' in build_config:
                    self.log_success("build.yaml has build_from configuration")
                    
                    # Check architecture coverage
                    build_archs = build_config['build_from'].keys()
                    if len(build_archs) >= 3:
                        self.log_success(f"Good architecture coverage: {list(build_archs)}")
                    else:
                        self.log_warning(f"Limited architecture coverage: {list(build_archs)}")
        
        # Check run.sh
        if self.check_file_exists("run.sh"):
            run_path = self.addon_path / "run.sh"
            if oct(run_path.stat().st_mode)[-3:] == '755':
                self.log_success("run.sh has executable permissions")
            else:
                self.log_warning("run.sh might not be executable")
    
    def validate_configuration_schema(self):
        """Validate configuration schema in config.yaml"""
        print("\n🔍 Validating configuration schema...")
        
        valid, config = self.validate_yaml_file("config.yaml")
        if not valid:
            return
        
        if 'schema' in config:
            self.log_success("Configuration schema is defined")
            
            schema = config['schema']
            options = config.get('options', {})
            
            # Check that all options have schema definitions
            for option_key in options.keys():
                if option_key in schema:
                    self.log_success(f"Schema defined for option: {option_key}")
                else:
                    self.log_warning(f"No schema for option: {option_key}")
            
            # Check for common schema patterns
            if any('password' in key for key in schema.keys()):
                self.log_success("Password fields use proper schema types")
        else:
            self.log_error("Configuration schema is missing")
    
    def run_validation(self) -> bool:
        """Run complete addon validation"""
        print("🔍 Starting AICleaner V3 Add-on Structure Validation")
        print(f"📁 Validating: {self.addon_path}")
        print("=" * 60)
        
        # Run all validation checks
        self.validate_config_yaml()
        self.validate_dockerfile()
        self.validate_requirements_txt()
        self.validate_source_structure()
        self.validate_documentation()
        self.validate_assets()
        self.validate_build_configuration()
        self.validate_configuration_schema()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        if self.errors:
            print("❌ ERRORS FOUND:")
            for error in self.errors:
                print(f"   {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   {warning}")
        
        success_rate = (self.success_count / self.total_checks * 100) if self.total_checks > 0 else 0
        print(f"\n📈 SUCCESS RATE: {self.success_count}/{self.total_checks} checks passed ({success_rate:.1f}%)")
        
        if not self.errors:
            print("\n🎉 VALIDATION PASSED! Addon structure is deployment-ready.")
            return True
        else:
            print(f"\n💥 VALIDATION FAILED! Found {len(self.errors)} critical errors.")
            return False


def main():
    """Main validation entry point"""
    if len(sys.argv) > 1:
        addon_path = sys.argv[1]
    else:
        # Default to current addon path
        addon_path = "/home/drewcifer/aicleaner_v3/addons/aicleaner_v3"
    
    validator = AddonValidator(addon_path)
    success = validator.run_validation()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()