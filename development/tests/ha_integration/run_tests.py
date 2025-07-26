#!/usr/bin/env python3
"""
AICleaner v3 HA Integration Test Runner
Runs comprehensive tests for Phase 4A HA integration components.
"""

import asyncio
import sys
import subprocess
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def run_test_file(test_file_path):
    """Run a specific test file and return results."""
    print(f"\n{'='*80}")
    print(f"Running {test_file_path.name}")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            str(test_file_path), 
            "-v", "--tb=short"
        ], capture_output=True, text=True, cwd=project_root)
        
        duration = time.time() - start_time
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return {
            "file": test_file_path.name,
            "passed": result.returncode == 0,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
    except Exception as e:
        return {
            "file": test_file_path.name,
            "passed": False,
            "duration": time.time() - start_time,
            "error": str(e)
        }

def main():
    """Run all HA integration tests."""
    print("AICleaner v3 HA Integration Test Suite")
    print("=" * 80)
    
    # Find all test files
    test_dir = Path(__file__).parent
    test_files = list(test_dir.glob("test_*.py"))
    
    if not test_files:
        print("No test files found!")
        return 1
    
    print(f"Found {len(test_files)} test files:")
    for test_file in test_files:
        print(f"  - {test_file.name}")
    
    # Run each test file
    results = []
    total_start = time.time()
    
    for test_file in test_files:
        result = run_test_file(test_file)
        results.append(result)
    
    total_duration = time.time() - total_start
    
    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed_count
    
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")
    print(f"Success Rate: {(passed_count / len(results) * 100):.1f}%")
    print(f"Total Duration: {total_duration:.2f}s")
    
    print("\nIndividual Results:")
    for result in results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        duration = result["duration"]
        print(f"  {status} {result['file']} ({duration:.2f}s)")
        
        if not result["passed"] and "error" in result:
            print(f"    Error: {result['error']}")
    
    # Detailed output for failed tests
    failed_results = [r for r in results if not r["passed"]]
    if failed_results:
        print(f"\n{'='*80}")
        print("FAILED TEST DETAILS")
        print(f"{'='*80}")
        
        for result in failed_results:
            print(f"\n{result['file']}:")
            print("-" * 40)
            if "stdout" in result:
                print(result["stdout"])
            if "stderr" in result:
                print("STDERR:", result["stderr"])
    
    return 0 if failed_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())