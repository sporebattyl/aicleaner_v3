#!/usr/bin/env python3
"""
AICleaner v3 Deployment Validator
Comprehensive validation and testing for live Home Assistant deployments

This validator implements the "Intelligent Simplicity" validation framework:
- Multi-layer validation (unit, integration, scenario, load)
- Edge case coverage for production environments
- Automatic issue detection and reporting
- Performance benchmarking and optimization recommendations
"""

import asyncio
import logging
import json
import time
import aiohttp
import psutil
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import concurrent.futures


class ValidationLevel(Enum):
    """Validation test levels"""
    UNIT = "unit"
    INTEGRATION = "integration"
    SCENARIO = "scenario"
    LOAD = "load"
    STRESS = "stress"


class ValidationResult(Enum):
    """Validation result types"""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class TestResult:
    """Individual test result"""
    test_name: str
    category: str
    level: ValidationLevel
    result: ValidationResult
    duration_ms: int
    message: str
    details: Dict[str, Any]
    recommendations: List[str]
    timestamp: datetime


@dataclass
class ValidationSummary:
    """Overall validation summary"""
    total_tests: int
    passed: int
    warnings: int
    failures: int
    skipped: int
    duration_seconds: float
    overall_result: ValidationResult
    critical_issues: List[str]
    performance_score: float
    recommendations: List[str]


class DeploymentValidator:
    """
    Comprehensive deployment validator for AICleaner v3
    
    Performs multi-level validation testing:
    - Unit tests: Individual component testing
    - Integration tests: Service interaction validation
    - Scenario tests: Real-world usage patterns
    - Load tests: Performance under stress
    - Edge case tests: Failure scenarios and recovery
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.home() / ".homeassistant"
        self.logger = self._setup_logging()
        
        # Test state
        self.test_results: List[TestResult] = []
        self.start_time: Optional[datetime] = None
        self.service_base_url = "http://localhost:8099"
        self.ha_base_url = "http://localhost:8123"
        
        # Performance baseline
        self.performance_baseline: Dict[str, float] = {}
        
        # Test configuration
        self.test_config = self._load_test_config()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the validator"""
        logger = logging.getLogger("aicleaner_validator")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _load_test_config(self) -> Dict[str, Any]:
        """Load test configuration"""
        default_config = {
            "timeouts": {
                "unit_test": 5.0,
                "integration_test": 10.0,
                "scenario_test": 30.0,
                "load_test": 60.0
            },
            "load_testing": {
                "concurrent_requests": 20,
                "test_duration_seconds": 30,
                "ramp_up_seconds": 5
            },
            "performance_thresholds": {
                "response_time_ms": 5000,
                "memory_usage_mb": 512,
                "cpu_usage_percent": 80
            },
            "edge_cases": {
                "network_timeout": 5.0,
                "memory_pressure_mb": 100,
                "disk_space_mb": 50
            }
        }
        
        # Try to load custom config
        config_file = self.config_path / "aicleaner" / "validator_config.yaml"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    custom_config = yaml.safe_load(f)
                    default_config.update(custom_config)
            except Exception as e:
                self.logger.warning(f"Failed to load custom test config: {e}")
        
        return default_config
    
    async def validate_deployment(self, 
                                  validation_levels: List[ValidationLevel] = None,
                                  progress_callback=None) -> ValidationSummary:
        """
        Run comprehensive deployment validation
        
        Args:
            validation_levels: List of validation levels to run (default: all)
            progress_callback: Optional callback for progress updates
        
        Returns:
            ValidationSummary with overall results
        """
        if validation_levels is None:
            validation_levels = list(ValidationLevel)
        
        self.start_time = datetime.now()
        self.test_results = []
        
        self.logger.info("Starting AICleaner v3 deployment validation")
        self.logger.info(f"Validation levels: {[level.value for level in validation_levels]}")
        
        try:
            total_stages = len(validation_levels)
            
            for i, level in enumerate(validation_levels):
                if progress_callback:
                    progress_callback(f"Running {level.value} tests", i / total_stages)
                
                await self._run_validation_level(level)
            
            if progress_callback:
                progress_callback("Generating summary", 1.0)
            
            # Generate summary
            summary = self._generate_summary()
            
            # Save results
            await self._save_results(summary)
            
            self.logger.info(f"Validation completed: {summary.overall_result.value}")
            return summary
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            
            # Return failure summary
            return ValidationSummary(
                total_tests=len(self.test_results),
                passed=0,
                warnings=0,
                failures=len(self.test_results),
                skipped=0,
                duration_seconds=(datetime.now() - self.start_time).total_seconds(),
                overall_result=ValidationResult.FAIL,
                critical_issues=[f"Validation error: {str(e)}"],
                performance_score=0.0,
                recommendations=["Check validator logs for detailed error information"]
            )
    
    async def _run_validation_level(self, level: ValidationLevel) -> None:
        """Run all tests for a specific validation level"""
        self.logger.info(f"Running {level.value} validation tests")
        
        if level == ValidationLevel.UNIT:
            await self._run_unit_tests()
        elif level == ValidationLevel.INTEGRATION:
            await self._run_integration_tests()
        elif level == ValidationLevel.SCENARIO:
            await self._run_scenario_tests()
        elif level == ValidationLevel.LOAD:
            await self._run_load_tests()
        elif level == ValidationLevel.STRESS:
            await self._run_stress_tests()
    
    # Unit Tests
    
    async def _run_unit_tests(self) -> None:
        """Run unit-level validation tests"""
        unit_tests = [
            ("configuration_files", self._test_configuration_files),
            ("security_setup", self._test_security_setup),
            ("file_permissions", self._test_file_permissions),
            ("python_imports", self._test_python_imports),
            ("service_configuration", self._test_service_configuration),
            ("addon_manifest", self._test_addon_manifest)
        ]
        
        await self._run_test_group("Unit Tests", ValidationLevel.UNIT, unit_tests)
    
    async def _test_configuration_files(self) -> TestResult:
        """Test configuration file validity"""
        start_time = time.time()
        
        try:
            config_files = [
                self.config_path / "aicleaner" / "service_config.yaml",
                self.config_path / "aicleaner" / "security" / "security_config.yaml"
            ]
            
            issues = []
            for config_file in config_files:
                if not config_file.exists():
                    issues.append(f"Missing config file: {config_file}")
                    continue
                
                try:
                    with open(config_file, 'r') as f:
                        yaml.safe_load(f)
                except yaml.YAMLError as e:
                    issues.append(f"Invalid YAML in {config_file}: {e}")
            
            duration = int((time.time() - start_time) * 1000)
            
            if not issues:
                return TestResult(
                    test_name="configuration_files",
                    category="Unit Tests",
                    level=ValidationLevel.UNIT,
                    result=ValidationResult.PASS,
                    duration_ms=duration,
                    message="All configuration files are valid",
                    details={"checked_files": len(config_files)},
                    recommendations=[],
                    timestamp=datetime.now()
                )
            else:
                return TestResult(
                    test_name="configuration_files",
                    category="Unit Tests",
                    level=ValidationLevel.UNIT,
                    result=ValidationResult.FAIL,
                    duration_ms=duration,
                    message=f"Configuration file issues: {'; '.join(issues)}",
                    details={"issues": issues},
                    recommendations=["Fix configuration file errors before continuing"],
                    timestamp=datetime.now()
                )
        
        except Exception as e:
            return self._create_error_result("configuration_files", "Unit Tests", str(e))
    
    async def _test_security_setup(self) -> TestResult:
        """Test security configuration"""
        start_time = time.time()
        
        try:
            security_dir = self.config_path / "aicleaner" / "security"
            required_files = ["internal_api.key", "service.token", "security_config.yaml"]
            
            issues = []
            recommendations = []
            
            for file_name in required_files:
                file_path = security_dir / file_name
                
                if not file_path.exists():
                    issues.append(f"Missing security file: {file_name}")
                    continue
                
                # Check file permissions
                file_stat = file_path.stat()
                if file_stat.st_mode & 0o077:
                    issues.append(f"Security file {file_name} has overly permissive permissions")
                    recommendations.append(f"Set secure permissions: chmod 600 {file_path}")
                
                # Check file content (basic validation)
                if file_path.suffix in ['.key', '.token']:
                    content = file_path.read_text().strip()
                    if len(content) < 16:
                        issues.append(f"Security file {file_name} content appears too short")
            
            duration = int((time.time() - start_time) * 1000)
            result = ValidationResult.PASS if not issues else ValidationResult.FAIL
            
            return TestResult(
                test_name="security_setup",
                category="Unit Tests",
                level=ValidationLevel.UNIT,
                result=result,
                duration_ms=duration,
                message=f"Security validation: {'passed' if result == ValidationResult.PASS else 'failed'}",
                details={"issues": issues, "checked_files": len(required_files)},
                recommendations=recommendations,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            return self._create_error_result("security_setup", "Unit Tests", str(e))
    
    # Integration Tests
    
    async def _run_integration_tests(self) -> None:
        """Run integration-level validation tests"""
        integration_tests = [
            ("service_health", self._test_service_health),
            ("api_endpoints", self._test_api_endpoints),
            ("ha_integration", self._test_ha_integration),
            ("provider_connections", self._test_provider_connections),
            ("mqtt_connectivity", self._test_mqtt_connectivity)
        ]
        
        await self._run_test_group("Integration Tests", ValidationLevel.INTEGRATION, integration_tests)
    
    async def _test_service_health(self) -> TestResult:
        """Test service health and availability"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"{self.service_base_url}/health",
                        timeout=self.test_config["timeouts"]["integration_test"]
                    ) as response:
                        duration = int((time.time() - start_time) * 1000)
                        
                        if response.status == 200:
                            health_data = await response.json()
                            
                            return TestResult(
                                test_name="service_health",
                                category="Integration Tests",
                                level=ValidationLevel.INTEGRATION,
                                result=ValidationResult.PASS,
                                duration_ms=duration,
                                message="Service health check passed",
                                details=health_data,
                                recommendations=[],
                                timestamp=datetime.now()
                            )
                        else:
                            return TestResult(
                                test_name="service_health",
                                category="Integration Tests",
                                level=ValidationLevel.INTEGRATION,
                                result=ValidationResult.FAIL,
                                duration_ms=duration,
                                message=f"Service health check failed with status {response.status}",
                                details={"status_code": response.status},
                                recommendations=["Check service logs", "Verify service is running"],
                                timestamp=datetime.now()
                            )
                
                except asyncio.TimeoutError:
                    return TestResult(
                        test_name="service_health",
                        category="Integration Tests",
                        level=ValidationLevel.INTEGRATION,
                        result=ValidationResult.FAIL,
                        duration_ms=int((time.time() - start_time) * 1000),
                        message="Service health check timed out",
                        details={"timeout": self.test_config["timeouts"]["integration_test"]},
                        recommendations=["Check if service is running", "Verify network connectivity"],
                        timestamp=datetime.now()
                    )
        
        except Exception as e:
            return self._create_error_result("service_health", "Integration Tests", str(e))
    
    # Scenario Tests
    
    async def _run_scenario_tests(self) -> None:
        """Run scenario-based validation tests"""
        scenario_tests = [
            ("basic_ai_request", self._test_basic_ai_request),
            ("multi_provider_failover", self._test_multi_provider_failover),
            ("ha_automation_trigger", self._test_ha_automation_trigger),
            ("configuration_reload", self._test_configuration_reload),
            ("service_restart_recovery", self._test_service_restart_recovery)
        ]
        
        await self._run_test_group("Scenario Tests", ValidationLevel.SCENARIO, scenario_tests)
    
    async def _test_basic_ai_request(self) -> TestResult:
        """Test basic AI request functionality"""
        start_time = time.time()
        
        try:
            test_request = {
                "prompt": "Hello, this is a test message",
                "provider": "auto",
                "max_tokens": 50
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.service_base_url}/api/v1/generate",
                    json=test_request,
                    timeout=self.test_config["timeouts"]["scenario_test"]
                ) as response:
                    duration = int((time.time() - start_time) * 1000)
                    
                    if response.status == 200:
                        result_data = await response.json()
                        
                        # Validate response structure
                        required_fields = ["response", "provider", "tokens_used"]
                        missing_fields = [field for field in required_fields if field not in result_data]
                        
                        if missing_fields:
                            return TestResult(
                                test_name="basic_ai_request",
                                category="Scenario Tests",
                                level=ValidationLevel.SCENARIO,
                                result=ValidationResult.WARN,
                                duration_ms=duration,
                                message=f"AI request succeeded but response missing fields: {missing_fields}",
                                details={"missing_fields": missing_fields, "response": result_data},
                                recommendations=["Check response format consistency"],
                                timestamp=datetime.now()
                            )
                        
                        return TestResult(
                            test_name="basic_ai_request",
                            category="Scenario Tests",
                            level=ValidationLevel.SCENARIO,
                            result=ValidationResult.PASS,
                            duration_ms=duration,
                            message="Basic AI request completed successfully",
                            details={
                                "provider_used": result_data.get("provider", "unknown"),
                                "tokens_used": result_data.get("tokens_used", 0),
                                "response_length": len(result_data.get("response", ""))
                            },
                            recommendations=[],
                            timestamp=datetime.now()
                        )
                    
                    else:
                        error_data = {}
                        try:
                            error_data = await response.json()
                        except:
                            pass
                        
                        return TestResult(
                            test_name="basic_ai_request",
                            category="Scenario Tests",
                            level=ValidationLevel.SCENARIO,
                            result=ValidationResult.FAIL,
                            duration_ms=duration,
                            message=f"AI request failed with status {response.status}",
                            details={"status_code": response.status, "error": error_data},
                            recommendations=["Check AI provider configuration", "Verify API keys"],
                            timestamp=datetime.now()
                        )
        
        except Exception as e:
            return self._create_error_result("basic_ai_request", "Scenario Tests", str(e))
    
    # Load Tests
    
    async def _run_load_tests(self) -> None:
        """Run load testing validation"""
        load_tests = [
            ("concurrent_requests", self._test_concurrent_requests),
            ("sustained_load", self._test_sustained_load),
            ("memory_usage_under_load", self._test_memory_usage_under_load),
            ("response_time_consistency", self._test_response_time_consistency)
        ]
        
        await self._run_test_group("Load Tests", ValidationLevel.LOAD, load_tests)
    
    async def _test_concurrent_requests(self) -> TestResult:
        """Test handling of concurrent requests"""
        start_time = time.time()
        
        try:
            concurrent_requests = self.test_config["load_testing"]["concurrent_requests"]
            
            # Create concurrent requests
            tasks = []
            for i in range(concurrent_requests):
                task = self._make_test_request(f"Test request {i}")
                tasks.append(task)
            
            # Execute all requests concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            duration = int((time.time() - start_time) * 1000)
            
            # Analyze results
            successful_requests = sum(1 for result in results if not isinstance(result, Exception))
            failed_requests = len(results) - successful_requests
            
            success_rate = successful_requests / len(results)
            
            if success_rate >= 0.9:  # 90% success rate threshold
                result_status = ValidationResult.PASS
                message = f"Concurrent requests handled successfully ({successful_requests}/{len(results)})"
            elif success_rate >= 0.7:  # 70% success rate threshold
                result_status = ValidationResult.WARN
                message = f"Concurrent requests partially successful ({successful_requests}/{len(results)})"
            else:
                result_status = ValidationResult.FAIL
                message = f"Concurrent requests failed ({successful_requests}/{len(results)})"
            
            recommendations = []
            if success_rate < 0.9:
                recommendations.extend([
                    "Consider increasing service resources",
                    "Check for rate limiting issues",
                    "Review error logs for failure patterns"
                ])
            
            return TestResult(
                test_name="concurrent_requests",
                category="Load Tests",
                level=ValidationLevel.LOAD,
                result=result_status,
                duration_ms=duration,
                message=message,
                details={
                    "concurrent_requests": concurrent_requests,
                    "successful_requests": successful_requests,
                    "failed_requests": failed_requests,
                    "success_rate": success_rate
                },
                recommendations=recommendations,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            return self._create_error_result("concurrent_requests", "Load Tests", str(e))
    
    # Helper Methods
    
    async def _run_test_group(self, group_name: str, level: ValidationLevel, tests: List[Tuple]) -> None:
        """Run a group of tests"""
        self.logger.info(f"Running {group_name}")
        
        for test_name, test_func in tests:
            try:
                self.logger.debug(f"Running test: {test_name}")
                result = await test_func()
                self.test_results.append(result)
                
                # Log result
                level_char = {
                    ValidationResult.PASS: "✓",
                    ValidationResult.WARN: "⚠",
                    ValidationResult.FAIL: "✗",
                    ValidationResult.SKIP: "-"
                }[result.result]
                
                self.logger.info(f"  {level_char} {test_name}: {result.message}")
                
            except Exception as e:
                self.logger.error(f"Test {test_name} crashed: {e}")
                error_result = self._create_error_result(test_name, group_name, str(e))
                self.test_results.append(error_result)
    
    async def _make_test_request(self, prompt: str) -> Dict[str, Any]:
        """Make a test AI request"""
        test_request = {
            "prompt": prompt,
            "provider": "auto",
            "max_tokens": 20
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.service_base_url}/api/v1/generate",
                json=test_request,
                timeout=10.0
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Request failed with status {response.status}")
    
    def _create_error_result(self, test_name: str, category: str, error: str) -> TestResult:
        """Create a test result for an error condition"""
        return TestResult(
            test_name=test_name,
            category=category,
            level=ValidationLevel.UNIT,
            result=ValidationResult.FAIL,
            duration_ms=0,
            message=f"Test error: {error}",
            details={"error": error},
            recommendations=["Check validator logs for more details"],
            timestamp=datetime.now()
        )
    
    def _generate_summary(self) -> ValidationSummary:
        """Generate validation summary from test results"""
        if not self.test_results:
            return ValidationSummary(
                total_tests=0,
                passed=0,
                warnings=0,
                failures=0,
                skipped=0,
                duration_seconds=0.0,
                overall_result=ValidationResult.SKIP,
                critical_issues=["No tests were run"],
                performance_score=0.0,
                recommendations=["Run validation tests"]
            )
        
        # Count results
        passed = sum(1 for r in self.test_results if r.result == ValidationResult.PASS)
        warnings = sum(1 for r in self.test_results if r.result == ValidationResult.WARN)
        failures = sum(1 for r in self.test_results if r.result == ValidationResult.FAIL)
        skipped = sum(1 for r in self.test_results if r.result == ValidationResult.SKIP)
        
        # Calculate duration
        duration_seconds = (datetime.now() - self.start_time).total_seconds()
        
        # Determine overall result
        if failures > 0:
            overall_result = ValidationResult.FAIL
        elif warnings > 0:
            overall_result = ValidationResult.WARN
        else:
            overall_result = ValidationResult.PASS
        
        # Identify critical issues
        critical_issues = [
            result.message for result in self.test_results
            if result.result == ValidationResult.FAIL and "Unit Tests" in result.category
        ]
        
        # Calculate performance score
        performance_score = self._calculate_performance_score()
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        return ValidationSummary(
            total_tests=len(self.test_results),
            passed=passed,
            warnings=warnings,
            failures=failures,
            skipped=skipped,
            duration_seconds=duration_seconds,
            overall_result=overall_result,
            critical_issues=critical_issues,
            performance_score=performance_score,
            recommendations=recommendations
        )
    
    def _calculate_performance_score(self) -> float:
        """Calculate overall performance score (0-100)"""
        if not self.test_results:
            return 0.0
        
        # Weight different result types
        weights = {
            ValidationResult.PASS: 1.0,
            ValidationResult.WARN: 0.7,
            ValidationResult.FAIL: 0.0,
            ValidationResult.SKIP: 0.0
        }
        
        total_weight = 0.0
        max_possible = 0.0
        
        for result in self.test_results:
            weight = weights[result.result]
            
            # Give higher weight to critical tests
            if result.level == ValidationLevel.UNIT:
                multiplier = 2.0
            elif result.level == ValidationLevel.INTEGRATION:
                multiplier = 1.5
            else:
                multiplier = 1.0
            
            total_weight += weight * multiplier
            max_possible += 1.0 * multiplier
        
        if max_possible == 0:
            return 0.0
        
        return (total_weight / max_possible) * 100.0
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = set()
        
        for result in self.test_results:
            recommendations.update(result.recommendations)
        
        return sorted(list(recommendations))
    
    async def _save_results(self, summary: ValidationSummary) -> None:
        """Save validation results to file"""
        try:
            results_dir = self.config_path / "aicleaner" / "validation_results"
            results_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = results_dir / f"validation_{timestamp}.json"
            
            # Prepare data for JSON serialization
            results_data = {
                "summary": asdict(summary),
                "test_results": [asdict(result) for result in self.test_results],
                "test_config": self.test_config,
                "validation_timestamp": datetime.now().isoformat()
            }
            
            # Handle datetime serialization
            def json_serializer(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            with open(results_file, 'w') as f:
                json.dump(results_data, f, indent=2, default=json_serializer)
            
            self.logger.info(f"Validation results saved to {results_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save validation results: {e}")


# Placeholder test methods (to be completed)
async def main():
    """Main entry point for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AICleaner v3 Deployment Validator")
    parser.add_argument("--config", help="Path to Home Assistant config directory")
    parser.add_argument("--levels", nargs="+", choices=[level.value for level in ValidationLevel],
                       help="Validation levels to run")
    parser.add_argument("--output", help="Output file for results")
    
    args = parser.parse_args()
    
    # Setup validator
    config_path = Path(args.config) if args.config else None
    validator = DeploymentValidator(config_path)
    
    # Parse validation levels
    levels = [ValidationLevel(level) for level in args.levels] if args.levels else None
    
    # Progress callback
    def progress_callback(stage, progress):
        print(f"\r{stage}: {progress*100:.1f}%", end="", flush=True)
    
    # Run validation
    summary = await validator.validate_deployment(levels, progress_callback)
    
    print(f"\n\nValidation Summary:")
    print(f"================")
    print(f"Total Tests: {summary.total_tests}")
    print(f"Passed: {summary.passed}")
    print(f"Warnings: {summary.warnings}")
    print(f"Failures: {summary.failures}")
    print(f"Overall Result: {summary.overall_result.value.upper()}")
    print(f"Performance Score: {summary.performance_score:.1f}/100")
    print(f"Duration: {summary.duration_seconds:.1f}s")
    
    if summary.critical_issues:
        print(f"\nCritical Issues:")
        for issue in summary.critical_issues:
            print(f"  - {issue}")
    
    if summary.recommendations:
        print(f"\nRecommendations:")
        for rec in summary.recommendations[:5]:  # Show top 5
            print(f"  - {rec}")
    
    return 0 if summary.overall_result != ValidationResult.FAIL else 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))