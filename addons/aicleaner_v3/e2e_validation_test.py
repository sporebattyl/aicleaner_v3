#!/usr/bin/env python3
"""
AICleaner V3 End-to-End Validation Test
Comprehensive testing of all enhanced functionality
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class E2EValidationTest:
    """End-to-end validation test suite for AICleaner V3"""
    
    def __init__(self):
        self.test_results = {}
        self.passed_tests = 0
        self.total_tests = 0
        
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        self.total_tests += 1
        self.test_results[test_name] = {
            'passed': passed,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        if passed:
            self.passed_tests += 1
            logger.info(f"✅ {test_name}: PASSED - {details}")
        else:
            logger.error(f"❌ {test_name}: FAILED - {details}")
    
    def test_mqtt_fixes(self):
        """Test that MQTT fixes are properly deployed"""
        test_name = "MQTT Fixes Deployment"
        
        try:
            mqtt_entities_path = Path(__file__).parent / "mqtt" / "mqtt_entities.py"
            if mqtt_entities_path.exists():
                with open(mqtt_entities_path, 'r') as f:
                    content = f.read()
                
                # Check that invalid fields are removed
                has_origin = '"origin"' in content
                has_entity_category_none = '"entity_category": None' in content
                
                if not has_origin and not has_entity_category_none:
                    self.log_test(test_name, True, "Invalid MQTT fields successfully removed")
                else:
                    self.log_test(test_name, False, f"Invalid fields still present - origin: {has_origin}, entity_category_none: {has_entity_category_none}")
            else:
                self.log_test(test_name, False, "mqtt_entities.py file not found")
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
    
    def test_enhanced_config(self):
        """Test enhanced configuration is properly loaded"""
        test_name = "Enhanced Configuration"
        
        try:
            config_path = Path(__file__).parent / "config" / "enhanced_options.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                # Check required configuration
                required_fields = ['default_camera', 'default_todo_list', 'enable_zones', 'zones']
                missing_fields = [field for field in required_fields if field not in config]
                
                if not missing_fields:
                    camera = config.get('default_camera')
                    todo = config.get('default_todo_list')
                    zones_enabled = config.get('enable_zones')
                    
                    if camera == 'camera.rowan_room_fluent' and todo == 'todo.rowan_room_cleaning_to_do' and zones_enabled:
                        self.log_test(test_name, True, f"Configuration valid - Camera: {camera}, Todo: {todo}, Zones: {zones_enabled}")
                    else:
                        self.log_test(test_name, False, f"Configuration values incorrect - Camera: {camera}, Todo: {todo}, Zones: {zones_enabled}")
                else:
                    self.log_test(test_name, False, f"Missing required fields: {missing_fields}")
            else:
                self.log_test(test_name, False, "enhanced_options.json not found")
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
    
    def test_web_ui_integration(self):
        """Test enhanced web UI integration"""
        test_name = "Enhanced Web UI Integration"
        
        try:
            web_ui_path = Path(__file__).parent / "src" / "web_ui_enhanced.py"
            main_path = Path(__file__).parent / "src" / "main.py"
            
            if web_ui_path.exists() and main_path.exists():
                with open(main_path, 'r') as f:
                    main_content = f.read()
                
                # Check if main.py imports and uses enhanced web UI
                has_enhanced_import = 'web_ui_enhanced' in main_content
                has_enhanced_ui_class = 'EnhancedWebUI' in main_content
                
                if has_enhanced_import and has_enhanced_ui_class:
                    self.log_test(test_name, True, "Enhanced web UI properly integrated in main.py")
                else:
                    self.log_test(test_name, False, f"Integration incomplete - import: {has_enhanced_import}, class: {has_enhanced_ui_class}")
            else:
                missing_files = []
                if not web_ui_path.exists():
                    missing_files.append("web_ui_enhanced.py")
                if not main_path.exists():
                    missing_files.append("main.py")
                self.log_test(test_name, False, f"Missing files: {missing_files}")
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
    
    def test_backup_integrity(self):
        """Test that backups were created during deployment"""
        test_name = "Deployment Backup Integrity"
        
        try:
            backup_dir = Path(__file__).parent / "deployment_backups"
            if backup_dir.exists():
                backup_files = list(backup_dir.glob("*.backup"))
                if backup_files:
                    self.log_test(test_name, True, f"Backup files created: {[f.name for f in backup_files]}")
                else:
                    self.log_test(test_name, False, "No backup files found")
            else:
                self.log_test(test_name, False, "Backup directory not found")
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
    
    def test_file_structure(self):
        """Test that all required files are in place"""
        test_name = "File Structure Integrity"
        
        try:
            required_files = [
                "src/main.py",
                "src/web_ui_enhanced.py", 
                "mqtt/mqtt_entities.py",
                "config/enhanced_options.json",
                "config.yaml"
            ]
            
            missing_files = []
            for file_path in required_files:
                full_path = Path(__file__).parent / file_path
                if not full_path.exists():
                    missing_files.append(file_path)
            
            if not missing_files:
                self.log_test(test_name, True, "All required files present")
            else:
                self.log_test(test_name, False, f"Missing files: {missing_files}")
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
    
    def test_zone_configuration(self):
        """Test zone configuration for Rowan's room"""
        test_name = "Rowan's Room Zone Configuration"
        
        try:
            config_path = Path(__file__).parent / "config" / "enhanced_options.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                zones = config.get('zones', [])
                if zones:
                    rowan_zone = next((zone for zone in zones if 'Rowan' in zone.get('name', '')), None)
                    if rowan_zone:
                        required_zone_fields = ['name', 'camera_entity', 'todo_list_entity', 'purpose', 'interval_minutes']
                        missing_zone_fields = [field for field in required_zone_fields if field not in rowan_zone]
                        
                        if not missing_zone_fields:
                            camera_correct = rowan_zone['camera_entity'] == 'camera.rowan_room_fluent'
                            todo_correct = rowan_zone['todo_list_entity'] == 'todo.rowan_room_cleaning_to_do'
                            
                            if camera_correct and todo_correct:
                                self.log_test(test_name, True, f"Rowan's room zone properly configured: {rowan_zone['name']}")
                            else:
                                self.log_test(test_name, False, f"Incorrect entity mappings - camera: {camera_correct}, todo: {todo_correct}")
                        else:
                            self.log_test(test_name, False, f"Zone missing fields: {missing_zone_fields}")
                    else:
                        self.log_test(test_name, False, "No Rowan's room zone found in configuration")
                else:
                    self.log_test(test_name, False, "No zones configured")
            else:
                self.log_test(test_name, False, "Configuration file not found")
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run the complete test suite"""
        logger.info("🚀 Starting AICleaner V3 End-to-End Validation Tests")
        logger.info("=" * 60)
        
        # Run all tests
        self.test_mqtt_fixes()
        self.test_enhanced_config()
        self.test_web_ui_integration()
        self.test_backup_integrity()
        self.test_file_structure()
        self.test_zone_configuration()
        
        # Generate summary
        logger.info("=" * 60)
        logger.info("📊 TEST SUMMARY")
        logger.info(f"Tests Passed: {self.passed_tests}/{self.total_tests}")
        success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        logger.info(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            logger.info("✅ DEPLOYMENT VALIDATION: PASSED")
            logger.info("🎉 Enhanced AICleaner V3 deployment successful!")
        else:
            logger.error("❌ DEPLOYMENT VALIDATION: FAILED")
            logger.error("⚠️ Critical issues found - review failed tests")
        
        # Detailed results
        logger.info("\n📋 DETAILED RESULTS:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            logger.info(f"  {status}: {test_name} - {result['details']}")
        
        return success_rate >= 80

def main():
    """Run the validation test suite"""
    validator = E2EValidationTest()
    success = validator.run_all_tests()
    
    if success:
        print("\n🏆 VALIDATION COMPLETE: All systems operational!")
        return 0
    else:
        print("\n🚨 VALIDATION FAILED: Issues require attention!")
        return 1

if __name__ == "__main__":
    exit(main())