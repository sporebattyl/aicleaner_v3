#!/usr/bin/env python3
"""
Demo script to test the testing framework without dependencies
"""

import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_framework_components():
    """Test that all framework components can be imported"""
    print("Testing AICleaner v3 Testing Framework Components...")
    print("=" * 60)
    
    try:
        # Test importing individual components
        from testing.test_performance import PerformanceTester
        print("✅ Performance testing module imported successfully")
        
        from testing.test_integration_ha import HAIntegrationTester
        print("✅ Integration testing module imported successfully")
        
        from testing.test_security import SecurityTester
        print("✅ Security testing module imported successfully")
        
        from testing.generate_report import TestReportGenerator
        print("✅ Report generator module imported successfully")
        
        # Test basic functionality
        print("\n" + "=" * 60)
        print("Testing Basic Functionality...")
        print("=" * 60)
        
        # Test report generation
        sample_results = {
            "performance": {
                "logging_performance": {"status": "PASS", "value": "1.2s"},
                "memory_usage": {"status": "WARN", "value": "45MB", "reason": "Higher than expected"}
            },
            "integration": [
                {"test": "HA API Connectivity", "status": "PASS", "response_time": 0.5},
                {"test": "Service Registration", "status": "FAIL", "reason": "Service not found"}
            ],
            "security": [
                {"check": "Hardcoded Secret", "severity": "High", "file": "config.py", "line": 42, "details": "API key found"}
            ]
        }
        
        generator = TestReportGenerator()
        
        # Generate sample reports
        md_report = generator.generate_markdown_report(sample_results, "demo_report.md")
        json_report = generator.generate_json_report(sample_results, "demo_report.json")
        html_report = generator.generate_html_report(sample_results, "demo_report.html")
        
        print(f"✅ Generated demo Markdown report: {md_report}")
        print(f"✅ Generated demo JSON report: {json_report}")
        print(f"✅ Generated demo HTML report: {html_report}")
        
        # Test security scanner (basic functionality)
        security_tester = SecurityTester(".")
        print("✅ Security scanner initialized successfully")
        
        # Test basic security check (file permissions)
        permission_issues = security_tester.check_file_permissions()
        print(f"✅ File permission check completed: {len(permission_issues)} issues found")
        
        print("\n" + "=" * 60)
        print("Framework Test Summary")
        print("=" * 60)
        print("✅ All framework components loaded successfully")
        print("✅ Basic functionality tests passed")
        print("✅ Report generation working")
        print("✅ Security scanning functional")
        print("\nThe AICleaner v3 Testing Framework is ready for use!")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def show_usage_examples():
    """Show usage examples"""
    print("\n" + "=" * 60)
    print("Usage Examples")
    print("=" * 60)
    
    examples = [
        "# Run all tests:",
        "python -m testing.run_tests --all",
        "",
        "# Run performance tests only:",
        "python -m testing.run_tests --performance",
        "",
        "# Run with Home Assistant integration:",
        "export HA_URL='http://localhost:8123'",
        "export HA_ACCESS_TOKEN='your-token-here'",
        "python -m testing.run_tests --integration",
        "",
        "# Run security scan:",
        "python -m testing.run_tests --security",
        "",
        "# Generate specific report format:",
        "python -m testing.run_tests --all --report-format json",
        "",
        "# Custom output filename:",
        "python -m testing.run_tests --all --output-file my_test_report"
    ]
    
    for example in examples:
        print(example)

if __name__ == "__main__":
    print("AICleaner v3 Testing Framework Demo")
    print("=" * 60)
    
    success = test_framework_components()
    
    if success:
        show_usage_examples()
        print("\n✅ Framework demo completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Framework demo failed!")
        sys.exit(1)