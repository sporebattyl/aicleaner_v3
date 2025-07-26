#!/usr/bin/env python3
"""
AICleaner v3 Release Preparation Script
Final orchestration script for production release readiness

This script coordinates all validation agents and release preparation tasks
to ensure AICleaner v3 is ready for production deployment as a Home Assistant addon.
"""

import os
import sys
import subprocess
import json
import yaml
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class ReleasePreparation:
    def __init__(self):
        self.project_root = project_root
        self.timestamp = datetime.now().isoformat()
        self.release_report = {
            "timestamp": self.timestamp,
            "version": "1.0.0",
            "overall_status": "PENDING",
            "validations": {},
            "tasks_completed": [],
            "issues": [],
            "recommendations": []
        }
        
    def log(self, message, level="INFO"):
        """Log messages with timestamp"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{level}] {message}")
        
    def run_validation_script(self, script_name, description):
        """Run a validation script and capture results"""
        self.log(f"Running {description}...")
        script_path = self.project_root / "scripts" / script_name
        
        try:
            if not script_path.exists():
                raise FileNotFoundError(f"Script not found: {script_path}")
                
            result = subprocess.run(
                [sys.executable, str(script_path)], 
                capture_output=True, 
                text=True, 
                cwd=self.project_root
            )
            
            status = "PASS" if result.returncode == 0 else "FAIL"
            self.release_report["validations"][script_name] = {
                "status": status,
                "description": description,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
            if status == "PASS":
                self.log(f"✅ {description}: PASSED")
                self.release_report["tasks_completed"].append(description)
            else:
                self.log(f"❌ {description}: FAILED")
                self.release_report["issues"].append(f"{description} failed: {result.stderr}")
                
            return status == "PASS"
            
        except Exception as e:
            self.log(f"❌ Error running {description}: {e}", "ERROR")
            self.release_report["validations"][script_name] = {
                "status": "ERROR",
                "description": description,
                "error": str(e)
            }
            self.release_report["issues"].append(f"{description} error: {e}")
            return False
            
    def validate_version_consistency(self):
        """Validate version consistency across all files"""
        self.log("Validating version consistency...")
        
        version_files = [
            ("config.yaml", lambda f: yaml.safe_load(f)["version"]),
            ("addons/aicleaner_v3/config.json", lambda f: json.load(f)["version"]),
            ("addons/aicleaner_v3/core/version.py", lambda f: self._extract_python_version(f.read()))
        ]
        
        versions = {}
        for file_path, extractor in version_files:
            full_path = self.project_root / file_path
            try:
                if full_path.exists():
                    with open(full_path, 'r') as f:
                        versions[file_path] = extractor(f)
                else:
                    self.log(f"⚠️  Version file not found: {file_path}", "WARNING")
                    versions[file_path] = "NOT_FOUND"
            except Exception as e:
                self.log(f"❌ Error reading version from {file_path}: {e}", "ERROR")
                versions[file_path] = "ERROR"
                
        # Check if all versions match
        unique_versions = set(v for v in versions.values() if v not in ["NOT_FOUND", "ERROR"])
        
        if len(unique_versions) == 1:
            version = list(unique_versions)[0]
            self.log(f"✅ Version consistency check: All files show v{version}")
            self.release_report["version"] = version
            return True
        else:
            self.log(f"❌ Version inconsistency detected: {versions}", "ERROR")
            self.release_report["issues"].append(f"Version inconsistency: {versions}")
            return False
            
    def _extract_python_version(self, content):
        """Extract version from Python version.py file"""
        for line in content.split('\n'):
            if '__version__' in line and '=' in line:
                return line.split('=')[1].strip().strip('"\'')
        return "NOT_FOUND"
        
    def validate_documentation(self):
        """Validate that all required documentation exists"""
        self.log("Validating documentation completeness...")
        
        required_docs = [
            "README.md",
            "INSTALL.md", 
            "CONTRIBUTING.md",
            "LICENSE",
            "CHANGELOG.md",
            "DOCKER_OPTIMIZATION.md"
        ]
        
        missing_docs = []
        for doc in required_docs:
            doc_path = self.project_root / doc
            if not doc_path.exists():
                missing_docs.append(doc)
                
        if missing_docs:
            self.log(f"❌ Missing documentation: {missing_docs}", "ERROR")
            self.release_report["issues"].append(f"Missing documentation: {missing_docs}")
            return False
        else:
            self.log("✅ All required documentation present")
            return True
            
    def validate_docker_configuration(self):
        """Validate Docker configuration and build files"""
        self.log("Validating Docker configuration...")
        
        docker_files = [
            "Dockerfile",
            ".dockerignore", 
            "docker-compose.yml",
            "docker-compose.prod.yml",
            "docker-compose.dev.yml",
            "build.yaml"
        ]
        
        missing_files = []
        for file in docker_files:
            file_path = self.project_root / file
            if not file_path.exists():
                missing_files.append(file)
                
        if missing_files:
            self.log(f"❌ Missing Docker files: {missing_files}", "ERROR")
            self.release_report["issues"].append(f"Missing Docker files: {missing_files}")
            return False
        else:
            self.log("✅ All Docker configuration files present")
            return True
            
    def validate_cicd_pipeline(self):
        """Validate CI/CD pipeline configuration"""
        self.log("Validating CI/CD pipeline...")
        
        workflow_files = [
            ".github/workflows/ci.yml",
            ".github/workflows/release.yml", 
            ".github/workflows/security.yml"
        ]
        
        missing_workflows = []
        for workflow in workflow_files:
            workflow_path = self.project_root / workflow
            if not workflow_path.exists():
                missing_workflows.append(workflow)
                
        if missing_workflows:
            self.log(f"❌ Missing CI/CD workflows: {missing_workflows}", "ERROR")
            self.release_report["issues"].append(f"Missing workflows: {missing_workflows}")
            return False
        else:
            self.log("✅ All CI/CD workflows present")
            return True
            
    def run_all_validations(self):
        """Run all validation checks in sequence"""
        self.log("🚀 Starting AICleaner v3 Release Preparation")
        self.log("="*60)
        
        validations_passed = 0
        total_validations = 0
        
        # Core validation checks
        validation_checks = [
            (self.validate_version_consistency, "Version Consistency"),
            (self.validate_documentation, "Documentation Completeness"),
            (self.validate_docker_configuration, "Docker Configuration"),
            (self.validate_cicd_pipeline, "CI/CD Pipeline")
        ]
        
        for check_func, check_name in validation_checks:
            total_validations += 1
            if check_func():
                validations_passed += 1
                
        # External validation scripts
        validation_scripts = [
            ("validate-docker.sh", "Docker Validation"),
            ("production_validation.py", "Production Validation"),
            ("validate_performance.py", "Performance Validation"),
            ("validate_ai_providers.py", "AI Providers Validation")
        ]
        
        for script, description in validation_scripts:
            total_validations += 1
            if self.run_validation_script(script, description):
                validations_passed += 1
                
        # Generate final report
        self.release_report["overall_status"] = "PASS" if validations_passed == total_validations else "FAIL"
        self.release_report["validation_summary"] = {
            "passed": validations_passed,
            "total": total_validations,
            "success_rate": f"{(validations_passed/total_validations)*100:.1f}%"
        }
        
        return validations_passed == total_validations
        
    def generate_release_report(self):
        """Generate comprehensive release readiness report"""
        self.log("\n" + "="*60)
        self.log("📊 AICLEANER v3 RELEASE READINESS REPORT")
        self.log("="*60)
        
        print(f"\n🕐 Timestamp: {self.release_report['timestamp']}")
        print(f"📦 Version: {self.release_report['version']}")
        print(f"📊 Overall Status: {self.release_report['overall_status']}")
        
        summary = self.release_report['validation_summary']
        print(f"✅ Validations Passed: {summary['passed']}/{summary['total']} ({summary['success_rate']})")
        
        if self.release_report['tasks_completed']:
            print(f"\n✅ Completed Tasks:")
            for task in self.release_report['tasks_completed']:
                print(f"   • {task}")
                
        if self.release_report['issues']:
            print(f"\n❌ Issues Found:")
            for issue in self.release_report['issues']:
                print(f"   • {issue}")
                
        # Save report to file
        report_path = self.project_root / "release_readiness_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.release_report, f, indent=2)
        self.log(f"📄 Full report saved to: {report_path}")
        
        return self.release_report['overall_status'] == "PASS"
        
    def run(self):
        """Main execution method"""
        try:
            # Run all validations
            release_ready = self.run_all_validations()
            
            # Generate final report
            report_success = self.generate_release_report()
            
            if release_ready and report_success:
                self.log("\n🎉 AICleaner v3 is READY FOR RELEASE! 🎉")
                self.log("All validation checks passed. Proceed with production deployment.")
                return True
            else:
                self.log("\n⚠️  Release preparation incomplete. Address issues before release.")
                return False
                
        except Exception as e:
            self.log(f"💥 Critical error during release preparation: {e}", "ERROR")
            return False

if __name__ == "__main__":
    release_prep = ReleasePreparation()
    success = release_prep.run()
    sys.exit(0 if success else 1)