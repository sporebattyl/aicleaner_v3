#!/usr/bin/env python3
"""
Syntax validation tests for HA integration components.
Simple tests that don't require external dependencies.
"""

import sys
import ast
import importlib.util
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def validate_python_syntax(file_path):
    """Validate Python syntax for a file."""
    try:
        with open(file_path, 'r') as f:
            source = f.read()
        
        # Check syntax
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def validate_imports(file_path):
    """Validate that file imports work (basic validation)."""
    try:
        spec = importlib.util.spec_from_file_location("test_module", file_path)
        if spec is None:
            return False, "Could not create module spec"
        
        # Don't actually import to avoid dependency issues
        return True, None
    except Exception as e:
        return False, f"Import error: {e}"

def run_syntax_tests():
    """Run syntax validation tests."""
    print("AICleaner v3 HA Integration Syntax Validation")
    print("=" * 60)
    
    # Test files to validate
    ha_integration_dir = project_root / "ha_integration"
    test_files = [
        ha_integration_dir / "entity_manager.py",
        ha_integration_dir / "service_manager.py", 
        ha_integration_dir / "config_flow.py",
        ha_integration_dir / "supervisor_api.py",
        ha_integration_dir / "performance_monitor.py"
    ]
    
    results = []
    
    for test_file in test_files:
        if not test_file.exists():
            results.append({
                "file": test_file.name,
                "syntax_valid": False,
                "error": "File not found"
            })
            continue
        
        # Validate syntax
        syntax_valid, syntax_error = validate_python_syntax(test_file)
        
        results.append({
            "file": test_file.name,
            "syntax_valid": syntax_valid,
            "syntax_error": syntax_error,
            "path": str(test_file)
        })
    
    # Print results
    passed = 0
    failed = 0
    
    for result in results:
        if result["syntax_valid"]:
            print(f"✅ {result['file']}: PASS")
            passed += 1
        else:
            print(f"❌ {result['file']}: FAIL - {result.get('syntax_error', result.get('error'))}")
            failed += 1
    
    print(f"\nSummary: {passed} passed, {failed} failed")
    
    # Test basic functionality
    print("\n" + "=" * 60)
    print("Basic Functionality Tests")
    print("=" * 60)
    
    # Test const.py
    try:
        from const import DOMAIN
        print(f"✅ const.py: DOMAIN = '{DOMAIN}'")
    except Exception as e:
        print(f"❌ const.py: {e}")
        failed += 1
    
    # Test basic imports (without actually importing HA dependencies)
    test_imports = [
        ("ha_integration.entity_manager", "AICleanerEntityManager"),
        ("ha_integration.service_manager", "AICleanerServiceManager"),
        ("ha_integration.supervisor_api", "SupervisorAPI"),
        ("ha_integration.performance_monitor", "PerformanceMonitor")
    ]
    
    for module_name, class_name in test_imports:
        try:
            # Just check if the file exists and has the class
            module_path = project_root / (module_name.replace(".", "/") + ".py")
            if module_path.exists():
                with open(module_path, 'r') as f:
                    content = f.read()
                if f"class {class_name}" in content:
                    print(f"✅ {module_name}.{class_name}: Class found")
                    passed += 1
                else:
                    print(f"❌ {module_name}.{class_name}: Class not found")
                    failed += 1
            else:
                print(f"❌ {module_name}: Module file not found")
                failed += 1
        except Exception as e:
            print(f"❌ {module_name}: {e}")
            failed += 1
    
    print(f"\nTotal Summary: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run_syntax_tests()
    sys.exit(0 if success else 1)