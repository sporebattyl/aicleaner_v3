#!/usr/bin/env python3
"""
Quick Test Script for AICleaner v3 Testing Infrastructure

A simple script to verify the testing infrastructure is working correctly
without requiring the full project structure.
"""

import os
import sys
import yaml
from pathlib import Path

def main():
    """Quick test of testing infrastructure"""
    print("🧪 AICleaner v3 Testing Infrastructure Quick Test")
    print("=" * 50)
    
    test_dir = Path(__file__).parent
    passed = 0
    failed = 0
    
    # Test 1: Check directory structure
    print("\n1. Testing Directory Structure...")
    required_dirs = ["configs", "unit", "integration"]
    for dir_name in required_dirs:
        dir_path = test_dir / dir_name
        if dir_path.exists():
            print(f"   ✅ {dir_name}/ exists")
            passed += 1
        else:
            print(f"   ❌ {dir_name}/ missing")
            failed += 1
    
    # Test 2: Check configuration files
    print("\n2. Testing Configuration Files...")
    config_files = [
        "test_config_basic.yaml",
        "test_config_multi_provider.yaml", 
        "test_config_legacy.yaml",
        "test_config_edge_cases.yaml"
    ]
    
    configs_dir = test_dir / "configs"
    for config_file in config_files:
        config_path = configs_dir / config_file
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    yaml.safe_load(f)
                print(f"   ✅ {config_file} valid")
                passed += 1
            except Exception as e:
                print(f"   ❌ {config_file} invalid: {e}")
                failed += 1
        else:
            print(f"   ❌ {config_file} missing")
            failed += 1
    
    # Test 3: Check test scripts
    print("\n3. Testing Test Scripts...")
    test_scripts = [
        "validate_architecture.py",
        "run_tests.py",
        "integration/test_architecture.py",
        "unit/test_config_validation.py"
    ]
    
    for script in test_scripts:
        script_path = test_dir / script
        if script_path.exists() and os.access(script_path, os.X_OK):
            print(f"   ✅ {script} exists and executable")
            passed += 1
        elif script_path.exists():
            print(f"   ⚠️  {script} exists but not executable")
            passed += 1
        else:
            print(f"   ❌ {script} missing")
            failed += 1
    
    # Test 4: Test basic functionality
    print("\n4. Testing Basic Functionality...")
    
    # Test YAML loading
    try:
        config_path = configs_dir / "test_config_basic.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if "ai_providers" in config and len(config["ai_providers"]) > 0:
            print("   ✅ YAML configuration loading works")
            passed += 1
        else:
            print("   ❌ YAML configuration structure invalid")
            failed += 1
            
    except Exception as e:
        print(f"   ❌ YAML loading failed: {e}")
        failed += 1
    
    # Test Python imports
    try:
        import asyncio
        import json
        import time
        print("   ✅ Core Python modules available")
        passed += 1
    except Exception as e:
        print(f"   ❌ Core Python modules missing: {e}")
        failed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 QUICK TEST SUMMARY")
    print("=" * 50)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All quick tests passed!")
        print("Testing infrastructure is ready for use.")
        print("\nNext steps:")
        print("  1. Run: python3 tests/validate_architecture.py")
        print("  2. Create main project directories (ai/, core/, utils/)")
        print("  3. Run: python3 tests/run_tests.py")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed.")
        print("Fix issues before proceeding.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)