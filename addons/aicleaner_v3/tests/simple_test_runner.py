#!/usr/bin/env python3
"""
Simple Test Runner for AICleaner v3 Testing Framework
Validates core testing components without complex dependencies.
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from concrete_test_scenarios import ConcreteTestScenarios

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [TEST_RUNNER] %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleTestRunner:
    """Simple test runner for validating core testing components."""
    
    def __init__(self):
        """Initialize the test runner."""
        self.test_results = {}
        self.start_time = time.time()
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all available tests and return results."""
        logger.info("Starting simple test runner validation")
        
        # Test 1: Concrete Test Scenarios
        self.test_results["concrete_scenarios"] = self._test_concrete_scenarios()
        
        # Test 2: Configuration Export
        self.test_results["configuration_export"] = self._test_configuration_export()
        
        # Test 3: Scenario Export
        self.test_results["scenario_export"] = self._test_scenario_export()
        
        # Test 4: Test Directory Creation
        self.test_results["test_directory_creation"] = self._test_directory_creation()
        
        # Calculate overall results
        overall_results = self._calculate_overall_results()
        
        return overall_results
    
    def _test_concrete_scenarios(self) -> Dict[str, Any]:
        """Test concrete scenarios functionality."""
        logger.info("Testing concrete scenarios functionality")
        
        try:
            scenarios = ConcreteTestScenarios()
            
            # Test scenario listing
            scenario_list = scenarios.list_scenarios()
            config_list = scenarios.list_configurations()
            
            # Test scenario retrieval
            test_scenario = scenarios.get_scenario("basic_installation")
            test_config = scenarios.get_configuration("minimal_config")
            
            result = {
                "status": "passed",
                "scenarios_count": len(scenario_list),
                "configurations_count": len(config_list),
                "sample_scenario_retrieved": test_scenario is not None,
                "sample_config_retrieved": test_config is not None,
                "scenario_names": scenario_list,
                "configuration_names": config_list
            }
            
            logger.info(f"Concrete scenarios test passed: {len(scenario_list)} scenarios, {len(config_list)} configs")
            return result
            
        except Exception as e:
            logger.error(f"Concrete scenarios test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _test_configuration_export(self) -> Dict[str, Any]:
        """Test configuration export functionality."""
        logger.info("Testing configuration export functionality")
        
        try:
            scenarios = ConcreteTestScenarios()
            
            # Export a test configuration
            test_file = "/tmp/test_config_export.json"
            export_success = scenarios.export_configuration_to_file("minimal_config", test_file)
            
            # Verify the file was created and has content
            file_exists = os.path.exists(test_file)
            file_size = os.path.getsize(test_file) if file_exists else 0
            
            # Clean up
            if file_exists:
                os.remove(test_file)
            
            result = {
                "status": "passed" if export_success and file_exists and file_size > 0 else "failed",
                "export_success": export_success,
                "file_created": file_exists,
                "file_size": file_size
            }
            
            logger.info(f"Configuration export test {'passed' if result['status'] == 'passed' else 'failed'}")
            return result
            
        except Exception as e:
            logger.error(f"Configuration export test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _test_scenario_export(self) -> Dict[str, Any]:
        """Test scenario export functionality."""
        logger.info("Testing scenario export functionality")
        
        try:
            scenarios = ConcreteTestScenarios()
            
            # Export a test scenario
            test_file = "/tmp/test_scenario_export.yaml"
            export_success = scenarios.export_scenario_to_file("basic_installation", test_file)
            
            # Verify the file was created and has content
            file_exists = os.path.exists(test_file)
            file_size = os.path.getsize(test_file) if file_exists else 0
            
            # Clean up
            if file_exists:
                os.remove(test_file)
            
            result = {
                "status": "passed" if export_success and file_exists and file_size > 0 else "failed",
                "export_success": export_success,
                "file_created": file_exists,
                "file_size": file_size
            }
            
            logger.info(f"Scenario export test {'passed' if result['status'] == 'passed' else 'failed'}")
            return result
            
        except Exception as e:
            logger.error(f"Scenario export test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _test_directory_creation(self) -> Dict[str, Any]:
        """Test test directory creation functionality."""
        logger.info("Testing test directory creation functionality")
        
        try:
            scenarios = ConcreteTestScenarios()
            
            # Create test directory
            test_dir = scenarios.create_test_files_directory("/tmp")
            
            # Verify directory structure
            test_dir_path = Path(test_dir)
            scenarios_dir = test_dir_path / "scenarios"
            configs_dir = test_dir_path / "configurations"
            readme_file = test_dir_path / "README.md"
            
            directory_exists = test_dir_path.exists()
            scenarios_dir_exists = scenarios_dir.exists()
            configs_dir_exists = configs_dir.exists()
            readme_exists = readme_file.exists()
            
            # Count files
            scenario_files = list(scenarios_dir.glob("*.yaml")) if scenarios_dir_exists else []
            config_files = list(configs_dir.glob("*.json")) if configs_dir_exists else []
            
            # Clean up
            if directory_exists:
                import shutil
                shutil.rmtree(test_dir)
            
            result = {
                "status": "passed" if all([directory_exists, scenarios_dir_exists, configs_dir_exists, readme_exists]) else "failed",
                "directory_created": directory_exists,
                "scenarios_dir_created": scenarios_dir_exists,
                "configs_dir_created": configs_dir_exists,
                "readme_created": readme_exists,
                "scenario_files_count": len(scenario_files),
                "config_files_count": len(config_files)
            }
            
            logger.info(f"Directory creation test {'passed' if result['status'] == 'passed' else 'failed'}")
            return result
            
        except Exception as e:
            logger.error(f"Directory creation test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _calculate_overall_results(self) -> Dict[str, Any]:
        """Calculate overall test results."""
        total_duration = time.time() - self.start_time
        
        passed_tests = sum(1 for result in self.test_results.values() if result.get("status") == "passed")
        failed_tests = sum(1 for result in self.test_results.values() if result.get("status") == "failed")
        total_tests = len(self.test_results)
        
        overall_status = "passed" if failed_tests == 0 else "partial" if passed_tests > 0 else "failed"
        
        return {
            "overall_status": overall_status,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "total_duration": total_duration,
            "test_results": self.test_results,
            "summary": {
                "concrete_scenarios": self.test_results.get("concrete_scenarios", {}).get("status", "unknown"),
                "configuration_export": self.test_results.get("configuration_export", {}).get("status", "unknown"),
                "scenario_export": self.test_results.get("scenario_export", {}).get("status", "unknown"),
                "test_directory_creation": self.test_results.get("test_directory_creation", {}).get("status", "unknown")
            }
        }


def main():
    """Main function to run the simple test runner."""
    logger.info("Starting AICleaner v3 Simple Test Runner")
    
    try:
        runner = SimpleTestRunner()
        results = runner.run_all_tests()
        
        # Print results
        print("\n" + "="*80)
        print("AICLEANER V3 SIMPLE TEST RUNNER RESULTS")
        print("="*80)
        print(f"Overall Status: {results['overall_status'].upper()}")
        print(f"Total Tests: {results['total_tests']}")
        print(f"Passed: {results['passed_tests']}")
        print(f"Failed: {results['failed_tests']}")
        print(f"Success Rate: {results['success_rate']:.1%}")
        print(f"Duration: {results['total_duration']:.2f}s")
        
        print("\nTest Summary:")
        for test_name, status in results['summary'].items():
            status_symbol = "✅" if status == "passed" else "❌" if status == "failed" else "⚠️"
            print(f"  {status_symbol} {test_name}: {status}")
        
        print("\nDetailed Results:")
        print(json.dumps(results, indent=2, default=str))
        print("="*80)
        
        # Return appropriate exit code
        return 0 if results['overall_status'] == "passed" else 1
        
    except Exception as e:
        logger.error(f"Simple test runner failed: {e}")
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)