#!/usr/bin/env python3
"""
AICleaner V3 Real Home Assistant Addon Validation
Validates that the addon is ready for installation on real HA server
"""

import json
import os
import yaml
from pathlib import Path
from typing import Dict, List, Any

class RealHAAddonValidator:
    def __init__(self):
        self.addon_path = Path("addons/aicleaner_v3")
        self.validation_results = []
        
    def validate_config_json(self) -> bool:
        """Validate the main addon config.json file"""
        config_path = self.addon_path / "config.json"
        
        if not config_path.exists():
            self.validation_results.append("❌ CRITICAL: config.json not found")
            return False
            
        try:
            with open(config_path) as f:
                config = json.load(f)
                
            # Required fields for HA addon
            required_fields = ["name", "version", "slug", "description", "arch", "startup"]
            missing_fields = [field for field in required_fields if field not in config]
            
            if missing_fields:
                self.validation_results.append(f"❌ Missing required fields: {missing_fields}")
                return False
                
            # Validate specific field values
            if config.get("startup") not in ["before", "after", "once", "application"]:
                self.validation_results.append("❌ Invalid startup type")
                return False
                
            # Check architecture support
            supported_archs = config.get("arch", [])
            if "amd64" not in supported_archs:
                self.validation_results.append("⚠️ AMD64 architecture not supported (needed for your AMD 8845HS)")
                
            self.validation_results.append("✅ config.json is valid")
            return True
            
        except json.JSONDecodeError as e:
            self.validation_results.append(f"❌ config.json has JSON errors: {e}")
            return False
            
    def validate_dockerfile(self) -> bool:
        """Validate Dockerfile exists and has proper structure"""
        dockerfile_path = self.addon_path / "Dockerfile"
        
        if not dockerfile_path.exists():
            self.validation_results.append("❌ CRITICAL: Dockerfile not found")
            return False
            
        try:
            with open(dockerfile_path) as f:
                content = f.read()
                
            # Check for required Dockerfile elements
            required_elements = ["FROM", "WORKDIR", "COPY", "CMD"]
            missing_elements = [elem for elem in required_elements if elem not in content]
            
            if missing_elements:
                self.validation_results.append(f"❌ Dockerfile missing: {missing_elements}")
                return False
                
            self.validation_results.append("✅ Dockerfile is valid")
            return True
            
        except Exception as e:
            self.validation_results.append(f"❌ Dockerfile validation error: {e}")
            return False
            
    def validate_run_script(self) -> bool:
        """Validate run.sh script exists and is executable"""
        run_script = self.addon_path / "run.sh"
        
        if not run_script.exists():
            self.validation_results.append("❌ CRITICAL: run.sh not found")
            return False
            
        # Check if it's executable (or at least readable)
        if not os.access(run_script, os.R_OK):
            self.validation_results.append("⚠️ run.sh may not be readable")
            
        self.validation_results.append("✅ run.sh exists")
        return True
        
    def validate_requirements(self) -> bool:
        """Validate requirements.txt exists and has necessary packages"""
        req_path = self.addon_path / "requirements.txt"
        
        if not req_path.exists():
            self.validation_results.append("❌ requirements.txt not found")
            return False
            
        try:
            with open(req_path) as f:
                requirements = f.read().strip().split('\n')
                
            # Check for essential packages
            essential_packages = ["google-generativeai", "aiohttp", "pyyaml"]
            requirements_lower = [req.lower().split('==')[0].split('>=')[0] for req in requirements if req.strip()]
            
            missing_packages = []
            for package in essential_packages:
                if not any(package in req for req in requirements_lower):
                    missing_packages.append(package)
                    
            if missing_packages:
                self.validation_results.append(f"⚠️ Potentially missing packages: {missing_packages}")
            else:
                self.validation_results.append("✅ Requirements look good")
                
            return True
            
        except Exception as e:
            self.validation_results.append(f"❌ Requirements validation error: {e}")
            return False
            
    def validate_source_structure(self) -> bool:
        """Validate source code structure"""
        src_path = self.addon_path / "src"
        
        if not src_path.exists():
            self.validation_results.append("❌ CRITICAL: src/ directory not found")
            return False
            
        # Check for main entry point
        main_files = ["main.py", "app.py", "__init__.py"]
        has_main = any((src_path / main_file).exists() for main_file in main_files)
        
        if not has_main:
            self.validation_results.append("❌ No main entry point found in src/")
            return False
            
        self.validation_results.append("✅ Source structure looks good")
        return True
        
    def check_ha_integration_readiness(self) -> bool:
        """Check if addon is ready for HA integration"""
        config_path = self.addon_path / "config.json"
        
        if not config_path.exists():
            return False
            
        try:
            with open(config_path) as f:
                config = json.load(f)
                
            # Check HA-specific features
            ha_features = []
            
            if config.get("homeassistant_api"):
                ha_features.append("✅ Home Assistant API access enabled")
            else:
                ha_features.append("⚠️ Home Assistant API access not enabled")
                
            if config.get("hassio_api"):
                ha_features.append("✅ Hassio API access enabled")
            else:
                ha_features.append("⚠️ Hassio API access not enabled")
                
            if config.get("ingress"):
                ha_features.append("✅ Ingress (web interface) enabled")
            else:
                ha_features.append("ℹ️ No web interface (ingress disabled)")
                
            self.validation_results.extend(ha_features)
            return True
            
        except Exception as e:
            self.validation_results.append(f"❌ HA integration check failed: {e}")
            return False
            
    def create_installation_guide(self) -> str:
        """Create installation guide for real HA server"""
        guide = """
📋 AICleaner V3 Installation Guide for Real Home Assistant
==========================================================

🔧 INSTALLATION STEPS:

1. **Copy Addon to HA Server:**
   ```bash
   # On your HA server, navigate to:
   cd /usr/share/hassio/addons/local/
   
   # Create directory and copy files:
   sudo mkdir -p aicleaner_v3
   sudo cp -r /path/to/your/addons/aicleaner_v3/* aicleaner_v3/
   ```

2. **Set Permissions:**
   ```bash
   sudo chown -R root:root aicleaner_v3/
   sudo chmod +x aicleaner_v3/run.sh
   ```

3. **Restart Home Assistant:**
   ```bash
   # Via UI: Configuration > Server Controls > Restart
   # Or via command:
   ha core restart
   ```

4. **Install Addon:**
   - Go to Supervisor > Add-on Store
   - Scroll to "Local add-ons" section
   - Find "AI Cleaner v3"
   - Click Install

5. **Configure Addon:**
   - Add your Gemini API key
   - Configure camera entities
   - Set up zones and rules
   - Click "Save" and "Start"

🚨 REQUIREMENTS:
- Home Assistant OS or Supervised installation
- Local add-ons support enabled
- Gemini API key required
- Camera entities must exist

📱 TESTING CHECKLIST:
□ Addon appears in local add-ons
□ Installation completes without errors
□ Configuration interface loads
□ Addon starts successfully
□ Web interface accessible (if ingress enabled)
□ Logs show proper initialization
"""
        return guide

    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run all validation checks"""
        print("🔍 AICleaner V3 Real HA Addon Validation")
        print("=" * 50)
        
        # Run all validation checks
        validations = [
            ("Config JSON", self.validate_config_json),
            ("Dockerfile", self.validate_dockerfile),
            ("Run Script", self.validate_run_script),
            ("Requirements", self.validate_requirements),
            ("Source Structure", self.validate_source_structure),
            ("HA Integration", self.check_ha_integration_readiness)
        ]
        
        results = {"validations": {}, "overall_status": "PASS"}
        
        for name, validator in validations:
            print(f"\n🔧 Validating {name}...")
            try:
                result = validator()
                results["validations"][name] = result
                if not result:
                    results["overall_status"] = "FAIL"
            except Exception as e:
                print(f"❌ Validation error for {name}: {e}")
                results["validations"][name] = False
                results["overall_status"] = "FAIL"
        
        # Print results
        print(f"\n📊 VALIDATION RESULTS:")
        print("-" * 30)
        for result in self.validation_results:
            print(result)
            
        print(f"\n🎯 OVERALL STATUS: {results['overall_status']}")
        
        if results["overall_status"] == "PASS":
            print("\n🎉 Addon is ready for real Home Assistant installation!")
            
            # Generate installation guide
            guide = self.create_installation_guide()
            
            # Save guide to file
            with open("REAL_HA_INSTALLATION_GUIDE.md", "w") as f:
                f.write(guide)
                
            print("\n📖 Installation guide saved to: REAL_HA_INSTALLATION_GUIDE.md")
        else:
            print("\n⚠️ Please fix validation issues before real HA installation")
            
        return results

def main():
    validator = RealHAAddonValidator()
    results = validator.run_comprehensive_validation()
    return results

if __name__ == "__main__":
    main()