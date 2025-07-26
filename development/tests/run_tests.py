#!/usr/bin/env python3
"""
AICleaner v3 Test Runner

Comprehensive test runner for the AICleaner v3 testing infrastructure.
Runs validation tests, integration tests, and generates reports.
"""

import asyncio
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestRunner:
    """Main test runner for AICleaner v3"""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.results: Dict[str, Any] = {}
        
    async def run_validation_tests(self) -> bool:
        """Run architecture validation tests"""
        print("🏗️  Running Architecture Validation...")
        
        try:
            # Import and run validation
            from tests.validate_architecture import ArchitectureValidator
            
            validator = ArchitectureValidator()
            success = await validator.run_all_validations()
            
            self.results['validation'] = {
                'success': success,
                'results': validator.results
            }
            
            return success
            
        except Exception as e:
            print(f"❌ Validation tests failed: {str(e)}")
            self.results['validation'] = {
                'success': False,
                'error': str(e)
            }
            return False
            
    async def run_integration_tests(self) -> bool:
        """Run integration tests"""
        print("\n🔧 Running Integration Tests...")
        
        try:
            # Import and run integration tests
            from tests.integration.test_architecture import run_integration_tests
            
            success = await run_integration_tests()
            
            self.results['integration'] = {
                'success': success
            }
            
            return success
            
        except Exception as e:
            print(f"❌ Integration tests failed: {str(e)}")
            self.results['integration'] = {
                'success': False,
                'error': str(e)
            }
            return False
            
    def run_pytest_tests(self) -> bool:
        """Run pytest if available"""
        print("\n🧪 Running Pytest Tests...")
        
        try:
            # Check if pytest is available
            result = subprocess.run(['python', '-m', 'pytest', '--version'], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                print("⚠️  Pytest not available, skipping...")
                return True
                
            # Run pytest on test directory
            test_cmd = [
                'python', '-m', 'pytest', 
                str(self.test_dir),
                '-v',
                '--tb=short'
            ]
            
            result = subprocess.run(test_cmd, cwd=project_root)
            success = result.returncode == 0
            
            self.results['pytest'] = {
                'success': success,
                'returncode': result.returncode
            }
            
            if success:
                print("✅ Pytest tests passed")
            else:
                print("❌ Pytest tests failed")
                
            return success
            
        except Exception as e:
            print(f"❌ Pytest execution failed: {str(e)}")
            self.results['pytest'] = {
                'success': False,
                'error': str(e)
            }
            return False
            
    def check_test_coverage(self) -> bool:
        """Check test coverage"""
        print("\n📊 Checking Test Coverage...")
        
        test_files = list(self.test_dir.rglob("test_*.py"))
        config_files = list((self.test_dir / "configs").glob("*.yaml"))
        
        coverage_info = {
            'test_files': len(test_files),
            'config_files': len(config_files),
            'test_types': []
        }
        
        # Check test types
        if (self.test_dir / "integration").exists():
            coverage_info['test_types'].append('integration')
        if (self.test_dir / "unit").exists():
            coverage_info['test_types'].append('unit')
        if (self.test_dir / "validate_architecture.py").exists():
            coverage_info['test_types'].append('validation')
            
        print(f"  📁 Test files found: {coverage_info['test_files']}")
        print(f"  📋 Config files found: {coverage_info['config_files']}")
        print(f"  🎯 Test types: {', '.join(coverage_info['test_types'])}")
        
        self.results['coverage'] = coverage_info
        
        # Minimum coverage requirements
        min_requirements = {
            'test_files': 1,
            'config_files': 3,
            'test_types': 2
        }
        
        meets_requirements = all(
            coverage_info[key] >= min_requirements[key] 
            for key in min_requirements
        )
        
        if meets_requirements:
            print("✅ Test coverage meets minimum requirements")
        else:
            print("⚠️  Test coverage below minimum requirements")
            
        return meets_requirements
        
    def print_final_summary(self):
        """Print final test summary"""
        print("\n" + "="*70)
        print("🏁 FINAL TEST SUMMARY")
        print("="*70)
        
        # Overall results
        all_passed = all(
            result.get('success', False) 
            for result in self.results.values() 
            if 'success' in result
        )
        
        print(f"\n📊 Test Results:")
        for test_type, result in self.results.items():
            if 'success' in result:
                status = "✅ PASS" if result['success'] else "❌ FAIL"
                print(f"  {status} {test_type.capitalize()}")
                
                if 'error' in result:
                    print(f"    Error: {result['error']}")
                    
        if 'coverage' in self.results:
            coverage = self.results['coverage']
            print(f"\n📈 Coverage Summary:")
            print(f"  Test Files: {coverage['test_files']}")
            print(f"  Config Files: {coverage['config_files']}")
            print(f"  Test Types: {', '.join(coverage['test_types'])}")
            
        # Final verdict
        if all_passed:
            print(f"\n🎉 ALL TESTS PASSED - Testing infrastructure is ready!")
            print("   You can now run individual test components:")
            print("   - python tests/validate_architecture.py")
            print("   - python tests/integration/test_architecture.py")
            print("   - python -m pytest tests/")
        else:
            print(f"\n⚠️  SOME TESTS FAILED - Check results above")
            print("   Fix failing tests before proceeding with development")
            
        return all_passed
        
    async def run_all_tests(self) -> bool:
        """Run all available tests"""
        print("🚀 Starting AICleaner v3 Comprehensive Test Suite")
        print("="*70)
        
        # Run test coverage check first
        self.check_test_coverage()
        
        # Run all test types
        tests_to_run = [
            ("Architecture Validation", self.run_validation_tests),
            ("Integration Tests", self.run_integration_tests),
        ]
        
        for test_name, test_func in tests_to_run:
            try:
                if asyncio.iscoroutinefunction(test_func):
                    await test_func()
                else:
                    test_func()
            except Exception as e:
                print(f"❌ {test_name} crashed: {str(e)}")
                
        # Run pytest separately (non-async)
        self.run_pytest_tests()
        
        # Print final summary
        return self.print_final_summary()


async def main():
    """Main test runner entry point"""
    runner = TestRunner()
    success = await runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())