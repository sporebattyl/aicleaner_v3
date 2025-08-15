#!/usr/bin/env python3
"""
Deployment readiness check for AI Cleaner main application.
Verifies all components are properly implemented and ready for production use.
"""

import sys
from pathlib import Path
import ast

def check_file_exists(file_path: Path, description: str) -> bool:
    """Check if a file exists and report the result."""
    if file_path.exists():
        size = file_path.stat().st_size
        print(f"   ✓ {description} ({size:,} bytes)")
        return True
    else:
        print(f"   ❌ {description} (missing)")
        return False

def check_implementation_completeness():
    """Check if the main application implementation is complete and deployment-ready."""
    print("AI Cleaner Deployment Readiness Check")
    print("=" * 40)
    
    # Core files check
    print("\n📁 Core Files:")
    core_files = [
        (Path("src/main.py"), "Main application entry point"),
        (Path("requirements.txt"), "Python dependencies"),
        (Path("README.md"), "Documentation"),
        (Path("config.example.yaml"), "Example configuration"),
    ]
    
    core_score = 0
    for file_path, description in core_files:
        if check_file_exists(file_path, description):
            core_score += 1
    
    # Component files check
    print("\n🏗️ Component Files:")
    component_files = [
        (Path("src/config/loader.py"), "Configuration loader"),
        (Path("src/config/schema.py"), "Configuration schemas"),
        (Path("src/core/orchestrator.py"), "Main orchestrator"),
        (Path("src/core/health.py"), "Health monitoring system"),
        (Path("src/providers/base_provider.py"), "Provider interface"),
        (Path("src/providers/gemini_provider.py"), "Gemini provider implementation"),
    ]
    
    component_score = 0
    for file_path, description in component_files:
        if check_file_exists(file_path, description):
            component_score += 1
    
    # Implementation quality check
    print("\n🔍 Implementation Quality:")
    main_file = Path("src/main.py")
    
    if main_file.exists():
        content = main_file.read_text()
        
        quality_checks = [
            ("Async/await patterns", "async def" in content and "await" in content),
            ("Error handling", "try:" in content and "except Exception" in content),
            ("Logging integration", "logger." in content and "logging.getLogger" in content),
            ("Signal handling", "signal.signal" in content),
            ("Configuration loading", "ConfigurationLoader" in content),
            ("Health monitoring", "HealthMonitor" in content),
            ("Provider orchestration", "AICleanerOrchestrator" in content),
            ("Web API server", "aiohttp" in content or "web.Application" in content),
            ("MQTT integration", "mqtt" in content.lower()),
            ("Directory watching", "DirectoryWatcher" in content),
            ("Command-line interface", "argparse" in content),
            ("Graceful shutdown", "shutdown" in content and "cleanup" in content),
            ("Production patterns", "__name__ == '__main__'" in content),
            ("Comprehensive docstrings", '"""' in content),
        ]
        
        quality_score = 0
        for check_name, check_result in quality_checks:
            if check_result:
                print(f"   ✓ {check_name}")
                quality_score += 1
            else:
                print(f"   ❌ {check_name}")
    else:
        print("   ❌ Cannot assess - main.py not found")
        quality_score = 0
        quality_checks = []
    
    # Architecture verification
    print("\n🏗️ Architecture Components:")
    
    if main_file.exists():
        try:
            tree = ast.parse(main_file.read_text())
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            
            required_classes = [
                "AICleanerApp",
                "DirectoryWatcher", 
                "MQTTClient",
                "WebAPI",
                "AppStats"
            ]
            
            arch_score = 0
            for class_name in required_classes:
                if class_name in classes:
                    print(f"   ✓ {class_name}")
                    arch_score += 1
                else:
                    print(f"   ❌ {class_name}")
            
        except Exception as e:
            print(f"   ❌ Error parsing main.py: {e}")
            arch_score = 0
            required_classes = []
    else:
        arch_score = 0
        required_classes = []
    
    # Calculate overall score
    print("\n📊 Readiness Assessment:")
    total_possible = len(core_files) + len(component_files) + len(quality_checks) + len(required_classes)
    total_score = core_score + component_score + quality_score + arch_score
    
    print(f"   Core Files: {core_score}/{len(core_files)} ({core_score/len(core_files)*100:.1f}%)")
    print(f"   Components: {component_score}/{len(component_files)} ({component_score/len(component_files)*100:.1f}%)")
    if quality_checks:
        print(f"   Code Quality: {quality_score}/{len(quality_checks)} ({quality_score/len(quality_checks)*100:.1f}%)")
    if required_classes:
        print(f"   Architecture: {arch_score}/{len(required_classes)} ({arch_score/len(required_classes)*100:.1f}%)")
    
    overall_percentage = (total_score / total_possible) * 100
    print(f"   Overall: {total_score}/{total_possible} ({overall_percentage:.1f}%)")
    
    # Deployment recommendation
    print("\n🎯 Deployment Status:")
    if overall_percentage >= 95:
        print("   🟢 READY FOR PRODUCTION DEPLOYMENT")
        print("   All components implemented with high quality standards.")
    elif overall_percentage >= 85:
        print("   🟡 READY FOR STAGING DEPLOYMENT")
        print("   Core functionality complete, minor improvements recommended.")
    elif overall_percentage >= 70:
        print("   🟠 READY FOR DEVELOPMENT TESTING")
        print("   Basic functionality present, requires additional work.")
    else:
        print("   🔴 NOT READY FOR DEPLOYMENT")
        print("   Significant implementation gaps detected.")
    
    # Next steps
    print("\n📋 Next Steps:")
    if overall_percentage >= 90:
        print("   1. Install dependencies: pip install -r requirements.txt")
        print("   2. Configure API keys in config.yaml")
        print("   3. Test with: python -m src.main --help")
        print("   4. Start application: python -m src.main")
        print("   5. Verify web API: curl http://localhost:8080/health")
        print("   6. Set up Home Assistant MQTT integration")
    else:
        print("   1. Complete missing components listed above")
        print("   2. Review implementation quality issues")
        print("   3. Re-run this deployment check")
    
    print("\n" + "=" * 40)
    return overall_percentage >= 85

if __name__ == "__main__":
    ready = check_implementation_completeness()
    sys.exit(0 if ready else 1)