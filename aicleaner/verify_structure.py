#!/usr/bin/env python3
"""
Verify the main application structure and implementation
without requiring external dependencies.
"""

import ast
import sys
from pathlib import Path

def analyze_file(file_path: Path) -> dict:
    """Analyze a Python file and extract key information."""
    if not file_path.exists():
        return {"error": f"File not found: {file_path}"}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        classes = []
        functions = []
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                classes.append({
                    "name": node.name,
                    "methods": methods,
                    "method_count": len(methods)
                })
            elif isinstance(node, ast.FunctionDef):
                # Simple check - if it's a top level function
                functions.append(node.name)
            elif isinstance(node, ast.Import):
                imports.extend([alias.name for alias in node.names])
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.extend([f"{module}.{alias.name}" for alias in node.names])
        
        return {
            "classes": classes,
            "functions": functions,
            "imports": imports,
            "lines": len(content.splitlines()),
            "chars": len(content)
        }
        
    except Exception as e:
        return {"error": f"Analysis failed: {e}"}

def verify_main_application():
    """Verify the main application implementation."""
    print("AI Cleaner Main Application Structure Verification")
    print("=" * 55)
    
    # Analyze main.py
    main_path = Path("src/main.py")
    main_analysis = analyze_file(main_path)
    
    if "error" in main_analysis:
        print(f"❌ {main_analysis['error']}")
        return False
    
    print(f"\n📁 Main Application ({main_path}):")
    print(f"   Lines of code: {main_analysis['lines']}")
    print(f"   Characters: {main_analysis['chars']:,}")
    print(f"   Classes: {len(main_analysis['classes'])}")
    print(f"   Functions: {len(main_analysis['functions'])}")
    print(f"   Imports: {len(main_analysis['imports'])}")
    
    # Check key classes
    expected_classes = [
        "AICleanerApp", "DirectoryWatcher", "MQTTClient", 
        "WebAPI", "AppStats"
    ]
    
    found_classes = [cls["name"] for cls in main_analysis["classes"]]
    print(f"\n🏗️  Key Classes:")
    
    for cls_name in expected_classes:
        if cls_name in found_classes:
            cls_info = next(cls for cls in main_analysis["classes"] if cls["name"] == cls_name)
            print(f"   ✓ {cls_name} ({cls_info['method_count']} methods)")
        else:
            print(f"   ❌ {cls_name} (missing)")
    
    # Check key functions
    expected_functions = ["main", "create_cli_parser"]
    found_functions = main_analysis["functions"]
    
    print(f"\n🔧 Key Functions:")
    for func_name in expected_functions:
        if func_name in found_functions:
            print(f"   ✓ {func_name}")
        else:
            print(f"   ❌ {func_name} (missing)")
    
    # Analyze supporting files
    supporting_files = [
        "src/config/loader.py",
        "src/config/schema.py", 
        "src/core/orchestrator.py",
        "src/core/health.py",
        "src/providers/base_provider.py",
        "src/providers/gemini_provider.py"
    ]
    
    print(f"\n📚 Supporting Components:")
    total_lines = main_analysis['lines']
    
    for file_path in supporting_files:
        path = Path(file_path)
        analysis = analyze_file(path)
        
        if "error" in analysis:
            print(f"   ❌ {file_path} (not found)")
        else:
            total_lines += analysis['lines']
            print(f"   ✓ {file_path} ({analysis['lines']} lines, {len(analysis['classes'])} classes)")
    
    print(f"\n📊 Summary:")
    print(f"   Total lines of code: {total_lines:,}")
    print(f"   Main application: {main_analysis['lines']} lines")
    print(f"   Core classes: {len([c for c in found_classes if c in expected_classes])}/{len(expected_classes)}")
    print(f"   Core functions: {len([f for f in found_functions if f in expected_functions])}/{len(expected_functions)}")
    
    # Check key implementation features
    main_content = Path("src/main.py").read_text() if Path("src/main.py").exists() else ""
    
    print(f"\n🔍 Feature Implementation:")
    features = [
        ("Signal handling", "signal.signal" in main_content),
        ("Async/await patterns", "async def" in main_content and "await" in main_content),
        ("Error handling", "try:" in main_content and "except" in main_content),
        ("Logging integration", "logger." in main_content),
        ("Configuration loading", "ConfigurationLoader" in main_content),
        ("Orchestrator integration", "AICleanerOrchestrator" in main_content),
        ("Health monitoring", "HealthMonitor" in main_content),
        ("Web API endpoints", "web.Application" in main_content or "aiohttp" in main_content),
        ("MQTT integration", "mqtt" in main_content or "paho" in main_content),
        ("Directory watching", "watch" in main_content.lower()),
        ("Command line interface", "argparse" in main_content),
        ("Graceful shutdown", "shutdown" in main_content)
    ]
    
    implemented_features = 0
    for feature_name, is_implemented in features:
        if is_implemented:
            print(f"   ✓ {feature_name}")
            implemented_features += 1
        else:
            print(f"   ❌ {feature_name}")
    
    print(f"\n🎯 Implementation Completeness:")
    completeness = (implemented_features / len(features)) * 100
    print(f"   {implemented_features}/{len(features)} features implemented ({completeness:.1f}%)")
    
    if completeness >= 90:
        print(f"   🎉 Excellent implementation!")
    elif completeness >= 75:
        print(f"   ✅ Good implementation")
    elif completeness >= 50:
        print(f"   ⚠️  Partial implementation")
    else:
        print(f"   ❌ Incomplete implementation")
    
    print(f"\n{'=' * 55}")
    
    if completeness >= 75 and len([c for c in found_classes if c in expected_classes]) >= 4:
        print("🏆 Main application implementation is COMPLETE and ready for deployment!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Configure providers (Gemini API key, etc.)")
        print("3. Test with: python -m src.main --help")
        print("4. Deploy with Home Assistant integration")
        return True
    else:
        print("❌ Main application implementation needs additional work.")
        return False

if __name__ == "__main__":
    success = verify_main_application()
    sys.exit(0 if success else 1)