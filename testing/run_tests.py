#!/usr/bin/env python3
"""
AICleaner v3 Test Runner
Main entry point for the comprehensive testing framework

Usage:
    python -m testing.run_tests --all
    python -m testing.run_tests --performance
    python -m testing.run_tests --integration
    python -m testing.run_tests --security
    python -m testing.run_tests --help
"""

import argparse
import sys
import os
import time
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from addons.aicleaner_v3.core.simple_logging import get_simple_logger
from addons.aicleaner_v3.core.logging_init import initialize_logging

# Import test modules
from .test_performance import run_performance_benchmarks
from .test_integration_ha import run_ha_integration_tests
from .test_security import run_security_checks
from .generate_report import create_all_reports, create_report

logger = get_simple_logger("test_runner")


class TestRunner:
    """Main test runner for AICleaner v3"""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None
        self.test_environment = self._detect_environment()
        
    def _detect_environment(self) -> str:
        """Detect the test environment"""
        if os.getenv('HASSIO_TOKEN') or os.getenv('SUPERVISOR_TOKEN'):
            return 'hassio'
        elif os.getenv('DOCKER_CONTAINER'):
            return 'docker'
        elif 'pytest' in sys.modules:
            return 'pytest'
        else:
            return 'development'
    
    def run_performance_tests(self) -> bool:
        """Run performance benchmarks"""
        logger.info("Starting performance tests...")
        
        try:
            perf_results = run_performance_benchmarks()
            self.results.update(perf_results)
            
            # Count pass/fail
            passed = len([v for v in perf_results.values() if isinstance(v, dict) and v.get("status") == "PASS"])
            failed = len([v for v in perf_results.values() if isinstance(v, dict) and v.get("status") == "FAIL"])
            
            logger.info(f"Performance tests completed: {passed} passed, {failed} failed")
            return failed == 0
            
        except Exception as e:
            logger.error(f"Performance tests failed: {e}")
            self.results["performance_error"] = {
                "status": "FAIL",
                "error": str(e)
            }
            return False
    
    def run_integration_tests(self) -> bool:
        """Run Home Assistant integration tests"""
        logger.info("Starting integration tests...")
        
        try:
            integration_results = run_ha_integration_tests()
            self.results["integration"] = integration_results
            
            # Count pass/fail
            passed = len([r for r in integration_results if r.get("status") == "PASS"])
            failed = len([r for r in integration_results if r.get("status") == "FAIL"])
            skipped = len([r for r in integration_results if r.get("status") == "SKIP"])
            
            logger.info(f"Integration tests completed: {passed} passed, {failed} failed, {skipped} skipped")
            return failed == 0
            
        except Exception as e:
            logger.error(f"Integration tests failed: {e}")
            self.results["integration"] = [{
                "test": "Integration Test Framework",
                "status": "FAIL",
                "reason": str(e)
            }]
            return False
    
    def run_security_tests(self) -> bool:
        """Run security vulnerability scans"""
        logger.info("Starting security tests...")
        
        try:
            # Use project root for security scanning
            project_root = Path(__file__).parent.parent
            security_results = run_security_checks(str(project_root))
            self.results["security"] = security_results
            
            # Count by severity
            high_issues = len([r for r in security_results if r.get("severity") == "High"])
            medium_issues = len([r for r in security_results if r.get("severity") == "Medium"])
            low_issues = len([r for r in security_results if r.get("severity") == "Low"])
            
            logger.info(f"Security tests completed: {high_issues} high, {medium_issues} medium, {low_issues} low severity issues")
            return high_issues == 0  # Only fail on high severity issues
            
        except Exception as e:
            logger.error(f"Security tests failed: {e}")
            self.results["security"] = [{
                "check": "Security Test Framework",
                "severity": "High",
                "file": "test_framework",
                "details": f"Security tests failed: {str(e)}"
            }]
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all test suites"""
        logger.info("Starting comprehensive test suite...")
        
        self.start_time = time.time()
        
        # Add test metadata
        self.results["test_metadata"] = {
            "start_time": self.start_time,
            "environment": self.test_environment,
            "python_version": sys.version,
            "platform": sys.platform,
            "working_directory": os.getcwd()
        }
        
        test_results = {}
        
        # Run performance tests
        try:
            test_results["performance"] = self.run_performance_tests()
        except Exception as e:
            logger.error(f"Performance test suite failed: {e}")
            test_results["performance"] = False
        
        # Run integration tests
        try:
            test_results["integration"] = self.run_integration_tests()
        except Exception as e:
            logger.error(f"Integration test suite failed: {e}")
            test_results["integration"] = False
        
        # Run security tests
        try:
            test_results["security"] = self.run_security_tests()
        except Exception as e:
            logger.error(f"Security test suite failed: {e}")
            test_results["security"] = False
        
        self.end_time = time.time()
        self.results["test_metadata"]["end_time"] = self.end_time
        self.results["test_metadata"]["duration"] = self.end_time - self.start_time
        
        logger.info(f"Test suite completed in {self.end_time - self.start_time:.2f} seconds")
        return test_results
    
    def generate_reports(self, output_format: str = "all", output_file: str = None) -> List[str]:
        """Generate test reports"""
        logger.info("Generating test reports...")
        
        try:
            if output_format == "all":
                reports = create_all_reports(self.results, output_file)
            else:
                report_path = create_report(self.results, output_format, output_file)
                reports = [report_path] if report_path else []
            
            logger.info(f"Generated {len(reports)} reports")
            return reports
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return []
    
    def print_summary(self, test_results: Dict[str, bool]):
        """Print test summary to console"""
        print("\n" + "="*60)
        print("           AICleaner v3 Test Summary")
        print("="*60)
        
        overall_status = "PASS" if all(test_results.values()) else "FAIL"
        status_color = "\033[92m" if overall_status == "PASS" else "\033[91m"
        reset_color = "\033[0m"
        
        print(f"Overall Status: {status_color}{overall_status}{reset_color}")
        print(f"Test Environment: {self.test_environment}")
        print(f"Duration: {self.results.get('test_metadata', {}).get('duration', 0):.2f} seconds")
        print()
        
        # Individual test results
        for test_name, passed in test_results.items():
            status = "PASS" if passed else "FAIL"
            color = "\033[92m" if passed else "\033[91m"
            print(f"{test_name.title()} Tests: {color}{status}{reset_color}")
        
        print()
        
        # Quick stats
        if "integration" in self.results:
            integration_results = self.results["integration"]
            if isinstance(integration_results, list):
                passed = len([r for r in integration_results if r.get("status") == "PASS"])
                failed = len([r for r in integration_results if r.get("status") == "FAIL"])
                print(f"Integration: {passed} passed, {failed} failed")
        
        if "security" in self.results:
            security_results = self.results["security"]
            if isinstance(security_results, list):
                total_issues = len(security_results)
                high_issues = len([r for r in security_results if r.get("severity") == "High"])
                print(f"Security: {total_issues} issues found ({high_issues} high severity)")
        
        print("="*60)
        
        if not all(test_results.values()):
            print("❌ Some tests failed. Check the detailed report for more information.")
        else:
            print("✅ All tests passed! AICleaner v3 is ready for production.")
        
        print("="*60)


def main():
    """Main entry point for the test runner"""
    parser = argparse.ArgumentParser(
        description="AICleaner v3 Testing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m testing.run_tests --all                    # Run all tests
  python -m testing.run_tests --performance            # Run only performance tests
  python -m testing.run_tests --integration            # Run only integration tests
  python -m testing.run_tests --security               # Run only security tests
  python -m testing.run_tests --all --report-format json  # Generate JSON report
  python -m testing.run_tests --all --output-file my_report  # Custom output filename
        """
    )
    
    # Test selection arguments
    parser.add_argument('--all', action='store_true', 
                       help='Run all test suites (default if no specific tests chosen)')
    parser.add_argument('--performance', action='store_true',
                       help='Run performance benchmarks')
    parser.add_argument('--integration', action='store_true',
                       help='Run Home Assistant integration tests')
    parser.add_argument('--security', action='store_true',
                       help='Run security vulnerability scans')
    
    # Report generation arguments
    parser.add_argument('--report-format', choices=['markdown', 'json', 'html', 'all'],
                       default='all', help='Report format (default: all)')
    parser.add_argument('--output-file', help='Output file basename (without extension)')
    parser.add_argument('--no-report', action='store_true',
                       help='Skip report generation')
    
    # Other options
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress non-error output')
    
    args = parser.parse_args()
    
    # Initialize logging
    try:
        initialize_logging()
    except Exception as e:
        print(f"Warning: Could not initialize logging: {e}")
    
    # Determine which tests to run
    run_all = args.all or not any([args.performance, args.integration, args.security])
    
    # Initialize test runner
    runner = TestRunner()
    
    # Run selected tests
    test_results = {}
    
    try:
        if run_all:
            test_results = runner.run_all_tests()
        else:
            if args.performance:
                test_results["performance"] = runner.run_performance_tests()
            if args.integration:
                test_results["integration"] = runner.run_integration_tests()
            if args.security:
                test_results["security"] = runner.run_security_tests()
        
        # Generate reports unless disabled
        if not args.no_report:
            reports = runner.generate_reports(args.report_format, args.output_file)
            if reports and not args.quiet:
                print("\nGenerated reports:")
                for report in reports:
                    print(f"  - {report}")
        
        # Print summary
        if not args.quiet:
            runner.print_summary(test_results)
        
        # Exit with appropriate code
        if all(test_results.values()):
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test run failed: {e}")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()