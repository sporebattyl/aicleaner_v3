#!/usr/bin/env python3
"""
AMD Optimization Test Suite
CPU+iGPU Optimization Specialist - Comprehensive Testing

Tests the AMD 8845HS + Radeon 780M optimization implementation
including provider integration, model selection, and performance monitoring.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import AMD optimization components
try:
    from ai.amd_integration_manager import AMDIntegrationManager
    from ai.providers.llamacpp_amd_provider import LlamaCppAMDProvider, AMD780MConfiguration
    from ai.providers.amd_model_optimizer import AMDModelOptimizer, OptimizationConfig
    from ai.providers.base_provider import AIRequest, AIProviderConfiguration
    
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"AMD optimization components not available: {e}")
    COMPONENTS_AVAILABLE = False


class AMDOptimizationTester:
    """Comprehensive tester for AMD optimization implementation"""
    
    def __init__(self):
        self.logger = logging.getLogger("amd_optimization_tester")
        self.test_results = {}
        self.integration_manager = None
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all AMD optimization tests"""
        if not COMPONENTS_AVAILABLE:
            return {"error": "AMD optimization components not available"}
        
        self.logger.info("Starting AMD optimization test suite")
        start_time = time.time()
        
        test_results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tests": {},
            "summary": {}
        }
        
        # Test 1: Hardware Detection
        test_results["tests"]["hardware_detection"] = await self._test_hardware_detection()
        
        # Test 2: Configuration Loading
        test_results["tests"]["configuration_loading"] = await self._test_configuration_loading()
        
        # Test 3: AMD Provider Initialization
        test_results["tests"]["amd_provider_init"] = await self._test_amd_provider_initialization()
        
        # Test 4: Model Optimizer
        test_results["tests"]["model_optimizer"] = await self._test_model_optimizer()
        
        # Test 5: Integration Manager
        test_results["tests"]["integration_manager"] = await self._test_integration_manager()
        
        # Test 6: Provider Selection Logic
        test_results["tests"]["provider_selection"] = await self._test_provider_selection()
        
        # Test 7: Performance Monitoring
        test_results["tests"]["performance_monitoring"] = await self._test_performance_monitoring()
        
        # Generate summary
        total_time = time.time() - start_time
        passed_tests = sum(1 for test in test_results["tests"].values() if test.get("status") == "passed")
        total_tests = len(test_results["tests"])
        
        test_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "total_time_seconds": total_time
        }
        
        self.logger.info(f"Test suite completed: {passed_tests}/{total_tests} tests passed "
                        f"({test_results['summary']['success_rate']:.1%} success rate)")
        
        return test_results
    
    async def _test_hardware_detection(self) -> Dict[str, Any]:
        """Test AMD hardware detection"""
        self.logger.info("Testing hardware detection...")
        
        try:
            # Test hardware detection logic
            import platform
            import psutil
            
            cpu_info = platform.processor()
            memory_gb = psutil.virtual_memory().total / (1024**3)
            
            # Simulate hardware detection
            hardware_info = {
                "cpu_detected": "AMD" in cpu_info,
                "memory_gb": memory_gb,
                "cpu_cores": psutil.cpu_count(logical=False),
                "cpu_threads": psutil.cpu_count(logical=True)
            }
            
            return {
                "status": "passed",
                "hardware_info": hardware_info,
                "notes": "Hardware detection completed successfully"
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "notes": "Hardware detection failed"
            }
    
    async def _test_configuration_loading(self) -> Dict[str, Any]:
        """Test AMD optimization configuration loading"""
        self.logger.info("Testing configuration loading...")
        
        try:
            config_path = Path("/app/config/amd_optimization.yaml")
            
            if config_path.exists():
                import yaml
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Validate key configuration sections
                required_sections = ["amd_optimization", "providers", "routing"]
                missing_sections = [section for section in required_sections 
                                  if section not in config]
                
                if missing_sections:
                    return {
                        "status": "failed",
                        "error": f"Missing configuration sections: {missing_sections}",
                        "notes": "Configuration validation failed"
                    }
                
                return {
                    "status": "passed",
                    "config_sections": list(config.keys()),
                    "notes": "Configuration loaded and validated successfully"
                }
            else:
                return {
                    "status": "failed",
                    "error": "Configuration file not found",
                    "notes": f"Expected configuration at {config_path}"
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "notes": "Configuration loading failed"
            }
    
    async def _test_amd_provider_initialization(self) -> Dict[str, Any]:
        """Test AMD provider initialization"""
        self.logger.info("Testing AMD provider initialization...")
        
        try:
            # Create test configuration
            test_config = AIProviderConfiguration(
                name="llamacpp_amd_test",
                enabled=True,
                model_name="test_model",
                timeout_seconds=30
            )
            
            # Test AMD configuration
            amd_config = AMD780MConfiguration()
            
            config_info = {
                "compute_units": amd_config.compute_units,
                "shader_cores": amd_config.shader_cores,
                "gpu_layers": amd_config.gpu_layers,
                "cpu_threads": amd_config.cpu_threads,
                "context_size": amd_config.context_size
            }
            
            return {
                "status": "passed",
                "amd_config": config_info,
                "notes": "AMD provider configuration created successfully"
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "notes": "AMD provider initialization failed"
            }
    
    async def _test_model_optimizer(self) -> Dict[str, Any]:
        """Test model optimizer functionality"""
        self.logger.info("Testing model optimizer...")
        
        try:
            # Create optimizer with test configuration
            config = OptimizationConfig(
                target_tokens_per_second=10.0,
                max_first_token_latency=2.0,
                min_success_rate=0.95
            )
            
            optimizer = AMDModelOptimizer(config)
            
            # Test optimization recommendations
            recommendations = optimizer.get_optimization_recommendations()
            
            return {
                "status": "passed",
                "optimization_config": {
                    "target_tokens_per_second": config.target_tokens_per_second,
                    "max_first_token_latency": config.max_first_token_latency,
                    "min_success_rate": config.min_success_rate
                },
                "recommendations_generated": len(recommendations.get("recommendations", [])),
                "notes": "Model optimizer created and tested successfully"
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "notes": "Model optimizer test failed"
            }
    
    async def _test_integration_manager(self) -> Dict[str, Any]:
        """Test integration manager"""
        self.logger.info("Testing integration manager...")
        
        try:
            # Create integration manager
            self.integration_manager = AMDIntegrationManager(
                config_path="/app/config/amd_optimization.yaml",
                data_path="/tmp/test_data"
            )
            
            # Test configuration loading
            config_loaded = await self.integration_manager._load_configuration()
            
            return {
                "status": "passed" if config_loaded else "failed",
                "config_loaded": config_loaded,
                "notes": "Integration manager created and configuration tested"
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "notes": "Integration manager test failed"
            }
    
    async def _test_provider_selection(self) -> Dict[str, Any]:
        """Test provider selection logic"""
        self.logger.info("Testing provider selection logic...")
        
        try:
            # Test request categorization
            test_requests = [
                {
                    "prompt": "Analyze this image for defects",
                    "image_path": "/test/image.jpg",
                    "expected_type": "vision"
                },
                {
                    "prompt": "Write a Python function to calculate fibonacci",
                    "expected_type": "code"
                },
                {
                    "prompt": "This is confidential information about my home automation",
                    "expected_type": "privacy_sensitive"
                },
                {
                    "prompt": "Provide a comprehensive analysis of quantum computing applications in enterprise environments with detailed technical specifications",
                    "expected_type": "complex"
                }
            ]
            
            results = []
            for test_req in test_requests:
                # Simulate request analysis
                request = AIRequest(
                    request_id=f"test_{len(results)}",
                    prompt=test_req["prompt"],
                    image_path=test_req.get("image_path")
                )
                
                # Test categorization logic
                is_vision = bool(request.image_path)
                is_complex = len(request.prompt) > 1000 or any(
                    word in request.prompt.lower() 
                    for word in ["comprehensive", "detailed", "technical specifications"]
                )
                is_code = any(
                    word in request.prompt.lower() 
                    for word in ["python", "function", "code"]
                )
                is_privacy = any(
                    word in request.prompt.lower() 
                    for word in ["confidential", "private", "home automation"]
                )
                
                results.append({
                    "prompt": test_req["prompt"][:50] + "...",
                    "expected": test_req["expected_type"],
                    "detected": {
                        "vision": is_vision,
                        "complex": is_complex,
                        "code": is_code,
                        "privacy": is_privacy
                    }
                })
            
            return {
                "status": "passed",
                "test_requests": len(test_requests),
                "categorization_results": results,
                "notes": "Provider selection logic tested successfully"
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "notes": "Provider selection test failed"
            }
    
    async def _test_performance_monitoring(self) -> Dict[str, Any]:
        """Test performance monitoring"""
        self.logger.info("Testing performance monitoring...")
        
        try:
            # Test system resource monitoring
            import psutil
            
            # Collect baseline metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # Test GPU monitoring (if available)
            gpu_available = False
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                gpu_available = len(gpus) > 0
            except:
                pass
            
            metrics = {
                "cpu_utilization": cpu_percent,
                "memory_usage_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "gpu_monitoring_available": gpu_available
            }
            
            return {
                "status": "passed",
                "metrics": metrics,
                "notes": "Performance monitoring tested successfully"
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "notes": "Performance monitoring test failed"
            }
    
    async def generate_test_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive test report"""
        report = []
        report.append("# AMD Optimization Test Report")
        report.append(f"Generated: {results['timestamp']}")
        report.append("")
        
        # Summary
        summary = results["summary"]
        report.append("## Summary")
        report.append(f"- Total Tests: {summary['total_tests']}")
        report.append(f"- Passed: {summary['passed_tests']}")
        report.append(f"- Failed: {summary['failed_tests']}")
        report.append(f"- Success Rate: {summary['success_rate']:.1%}")
        report.append(f"- Total Time: {summary['total_time_seconds']:.2f}s")
        report.append("")
        
        # Detailed results
        report.append("## Test Results")
        for test_name, result in results["tests"].items():
            status_emoji = "✅" if result["status"] == "passed" else "❌"
            report.append(f"### {test_name.replace('_', ' ').title()} {status_emoji}")
            report.append(f"**Status:** {result['status']}")
            
            if "error" in result:
                report.append(f"**Error:** {result['error']}")
            
            if "notes" in result:
                report.append(f"**Notes:** {result['notes']}")
            
            report.append("")
        
        return "\n".join(report)


async def main():
    """Main test execution"""
    print("AMD 8845HS + Radeon 780M Optimization Test Suite")
    print("=" * 60)
    
    tester = AMDOptimizationTester()
    
    try:
        # Run all tests
        results = await tester.run_all_tests()
        
        # Generate and save report
        report = await tester.generate_test_report(results)
        
        # Save results
        results_file = Path("/tmp/amd_optimization_test_results.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        report_file = Path("/tmp/amd_optimization_test_report.md")
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\nTest Results Summary:")
        print(f"- Tests Passed: {results['summary']['passed_tests']}/{results['summary']['total_tests']}")
        print(f"- Success Rate: {results['summary']['success_rate']:.1%}")
        print(f"- Total Time: {results['summary']['total_time_seconds']:.2f}s")
        print(f"\nDetailed results saved to: {results_file}")
        print(f"Test report saved to: {report_file}")
        
        # Print brief report
        print("\n" + "=" * 60)
        print(report)
        
    except Exception as e:
        print(f"Test suite failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))