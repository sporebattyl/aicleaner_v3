#!/usr/bin/env python3
"""
AICleaner v3 Architecture Validation Script

This script provides comprehensive validation of the AICleaner v3 architecture,
including health checks, configuration validation, provider connectivity testing,
and performance baseline measurements.
"""

import asyncio
import json
import time
import yaml
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Optional imports - gracefully handle missing dependencies
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    print("Warning: aiohttp not available - network connectivity tests will be skipped")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class ValidationStatus(Enum):
    """Validation result status"""
    PASS = "✅ PASS"
    FAIL = "❌ FAIL"
    WARN = "⚠️  WARN"
    INFO = "ℹ️  INFO"


@dataclass
class ValidationResult:
    """Validation test result"""
    name: str
    status: ValidationStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None


class ArchitectureValidator:
    """Comprehensive architecture validation"""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.test_configs_dir = Path(__file__).parent / "configs"
        
    def add_result(self, name: str, status: ValidationStatus, message: str, 
                   details: Optional[Dict[str, Any]] = None, duration_ms: Optional[float] = None):
        """Add validation result"""
        self.results.append(ValidationResult(name, status, message, details, duration_ms))
        
    async def validate_directory_structure(self) -> bool:
        """Validate project directory structure"""
        print("\n🏗️  Validating Directory Structure...")
        
        required_dirs = [
            "ai",
            "ai/providers", 
            "core",
            "utils",
            "tests",
            "tests/configs",
            "tests/unit",
            "tests/integration"
        ]
        
        all_exist = True
        missing_dirs = []
        
        for dir_path in required_dirs:
            full_path = project_root / dir_path
            if full_path.exists():
                self.add_result(f"Directory: {dir_path}", ValidationStatus.PASS, "Directory exists")
            else:
                self.add_result(f"Directory: {dir_path}", ValidationStatus.FAIL, "Directory missing")
                missing_dirs.append(dir_path)
                all_exist = False
                
        if missing_dirs:
            self.add_result("Directory Structure", ValidationStatus.FAIL, 
                          f"Missing directories: {', '.join(missing_dirs)}")
        else:
            self.add_result("Directory Structure", ValidationStatus.PASS, "All required directories present")
            
        return all_exist
        
    async def validate_test_configurations(self) -> bool:
        """Validate test configuration files"""
        print("\n📋 Validating Test Configurations...")
        
        test_configs = [
            "test_config_basic.yaml",
            "test_config_multi_provider.yaml", 
            "test_config_legacy.yaml"
        ]
        
        all_valid = True
        
        for config_file in test_configs:
            config_path = self.test_configs_dir / config_file
            
            if not config_path.exists():
                self.add_result(f"Config: {config_file}", ValidationStatus.FAIL, "File not found")
                all_valid = False
                continue
                
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    
                # Validate configuration structure
                if config_file == "test_config_legacy.yaml":
                    required_keys = ["ai_model", "openai", "gemini", "local_llm"]
                else:
                    required_keys = ["ai_providers"]
                    
                missing_keys = [key for key in required_keys if key not in config]
                
                if missing_keys:
                    self.add_result(f"Config: {config_file}", ValidationStatus.FAIL, 
                                  f"Missing keys: {', '.join(missing_keys)}")
                    all_valid = False
                else:
                    self.add_result(f"Config: {config_file}", ValidationStatus.PASS, 
                                  "Configuration structure valid")
                    
            except yaml.YAMLError as e:
                self.add_result(f"Config: {config_file}", ValidationStatus.FAIL, 
                              f"YAML parsing error: {str(e)}")
                all_valid = False
            except Exception as e:
                self.add_result(f"Config: {config_file}", ValidationStatus.FAIL, 
                              f"Validation error: {str(e)}")
                all_valid = False
                
        return all_valid
        
    async def validate_provider_connectivity(self) -> bool:
        """Test provider connectivity and capabilities"""
        print("\n🔌 Validating Provider Connectivity...")
        
        if not AIOHTTP_AVAILABLE:
            self.add_result("Provider Connectivity", ValidationStatus.INFO,
                          "aiohttp not available - connectivity tests skipped")
            return True
        
        providers_to_test = [
            {
                "name": "Ollama",
                "url": "http://localhost:11434/api/version",
                "timeout": 5
            },
            {
                "name": "OpenAI API",
                "url": "https://api.openai.com/v1/models",
                "timeout": 10,
                "headers": {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', 'test-key')}"}
            }
        ]
        
        connectivity_results = []
        
        async with aiohttp.ClientSession() as session:
            for provider in providers_to_test:
                start_time = time.time()
                
                try:
                    headers = provider.get("headers", {})
                    timeout = aiohttp.ClientTimeout(total=provider["timeout"])
                    
                    async with session.get(provider["url"], headers=headers, timeout=timeout) as response:
                        duration_ms = (time.time() - start_time) * 1000
                        
                        if response.status == 200:
                            self.add_result(f"Connectivity: {provider['name']}", ValidationStatus.PASS,
                                          f"Connected successfully", duration_ms=duration_ms)
                            connectivity_results.append(True)
                        elif response.status == 401 and provider["name"] == "OpenAI API":
                            self.add_result(f"Connectivity: {provider['name']}", ValidationStatus.WARN,
                                          "Authentication required (expected with test key)", duration_ms=duration_ms)
                            connectivity_results.append(True)  # Expected for test
                        else:
                            self.add_result(f"Connectivity: {provider['name']}", ValidationStatus.FAIL,
                                          f"HTTP {response.status}", duration_ms=duration_ms)
                            connectivity_results.append(False)
                            
                except asyncio.TimeoutError:
                    duration_ms = (time.time() - start_time) * 1000
                    self.add_result(f"Connectivity: {provider['name']}", ValidationStatus.FAIL,
                                  "Connection timeout", duration_ms=duration_ms)
                    connectivity_results.append(False)
                    
                except aiohttp.ClientError as e:
                    duration_ms = (time.time() - start_time) * 1000
                    self.add_result(f"Connectivity: {provider['name']}", ValidationStatus.FAIL,
                                  f"Connection error: {str(e)}", duration_ms=duration_ms)
                    connectivity_results.append(False)
                    
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    self.add_result(f"Connectivity: {provider['name']}", ValidationStatus.FAIL,
                                  f"Unexpected error: {str(e)}", duration_ms=duration_ms)
                    connectivity_results.append(False)
                    
        return any(connectivity_results)  # At least one provider should be reachable
        
    async def validate_fallback_system(self) -> bool:
        """Validate fallback system logic"""
        print("\n🔄 Validating Fallback System...")
        
        # Load multi-provider config
        config_path = self.test_configs_dir / "test_config_multi_provider.yaml"
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            providers = config.get("ai_providers", [])
            
            if len(providers) < 2:
                self.add_result("Fallback System", ValidationStatus.FAIL,
                              "Insufficient providers for fallback testing")
                return False
                
            # Check priority ordering
            priorities = [p.get("priority", 0) for p in providers]
            sorted_priorities = sorted(priorities)
            
            if priorities == sorted_priorities:
                self.add_result("Fallback Priority Order", ValidationStatus.PASS,
                              "Providers correctly ordered by priority")
            else:
                self.add_result("Fallback Priority Order", ValidationStatus.WARN,
                              "Providers not in priority order")
                
            # Check required fields for fallback
            required_fields = ["provider", "enabled", "priority"]
            all_providers_valid = True
            
            for i, provider in enumerate(providers):
                missing_fields = [field for field in required_fields if field not in provider]
                
                if missing_fields:
                    self.add_result(f"Provider {i+1} Validation", ValidationStatus.FAIL,
                                  f"Missing fields: {', '.join(missing_fields)}")
                    all_providers_valid = False
                else:
                    self.add_result(f"Provider {i+1} Validation", ValidationStatus.PASS,
                                  "All required fields present")
                    
            return all_providers_valid
            
        except Exception as e:
            self.add_result("Fallback System", ValidationStatus.FAIL,
                          f"Configuration loading error: {str(e)}")
            return False
            
    async def validate_performance_baseline(self) -> bool:
        """Validate performance baseline requirements"""
        print("\n⚡ Validating Performance Baseline...")
        
        # Test configuration loading performance
        start_time = time.time()
        
        try:
            for config_file in ["test_config_basic.yaml", "test_config_multi_provider.yaml"]:
                config_path = self.test_configs_dir / config_file
                with open(config_path, 'r') as f:
                    yaml.safe_load(f)
                    
            config_load_time = (time.time() - start_time) * 1000
            
            if config_load_time < 100:  # 100ms threshold
                self.add_result("Configuration Loading Performance", ValidationStatus.PASS,
                              f"Loaded in {config_load_time:.2f}ms", duration_ms=config_load_time)
            else:
                self.add_result("Configuration Loading Performance", ValidationStatus.WARN,
                              f"Slow loading: {config_load_time:.2f}ms", duration_ms=config_load_time)
                
        except Exception as e:
            self.add_result("Configuration Loading Performance", ValidationStatus.FAIL,
                          f"Performance test failed: {str(e)}")
            return False
            
        # Test memory usage simulation
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process()
                memory_usage = process.memory_info().rss / 1024 / 1024  # MB
                
                if memory_usage < 100:  # 100MB threshold
                    self.add_result("Memory Usage", ValidationStatus.PASS,
                                  f"Memory usage: {memory_usage:.2f}MB")
                else:
                    self.add_result("Memory Usage", ValidationStatus.WARN,
                                  f"High memory usage: {memory_usage:.2f}MB")
                                  
            except Exception as e:
                self.add_result("Memory Usage", ValidationStatus.WARN,
                              f"Memory test error: {str(e)}")
        else:
            self.add_result("Memory Usage", ValidationStatus.INFO,
                          "psutil not available for memory testing")
            
        return True
        
    async def validate_environment_setup(self) -> bool:
        """Validate environment setup and dependencies"""
        print("\n🌍 Validating Environment Setup...")
        
        # Check Python version
        python_version = sys.version_info
        if python_version >= (3, 11):
            self.add_result("Python Version", ValidationStatus.PASS,
                          f"Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        else:
            self.add_result("Python Version", ValidationStatus.FAIL,
                          f"Python {python_version.major}.{python_version.minor} < 3.11 required")
            
        # Check required packages
        required_packages = ["yaml", "aiohttp", "asyncio"]
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
                self.add_result(f"Package: {package}", ValidationStatus.PASS, "Available")
            except ImportError:
                self.add_result(f"Package: {package}", ValidationStatus.FAIL, "Missing")
                missing_packages.append(package)
                
        # Check environment variables
        env_vars = ["OPENAI_API_KEY", "GEMINI_API_KEY"]
        for var in env_vars:
            value = os.getenv(var)
            if value:
                masked_value = f"{value[:8]}..." if len(value) > 8 else "***"
                self.add_result(f"Environment: {var}", ValidationStatus.PASS,
                              f"Set ({masked_value})")
            else:
                self.add_result(f"Environment: {var}", ValidationStatus.WARN,
                              "Not set (optional for testing)")
                
        return len(missing_packages) == 0
        
    def print_summary(self):
        """Print validation summary"""
        print("\n" + "="*60)
        print("🧪 VALIDATION SUMMARY")
        print("="*60)
        
        # Count results by status
        status_counts = {}
        total_duration = 0
        
        for result in self.results:
            status = result.status
            status_counts[status] = status_counts.get(status, 0) + 1
            if result.duration_ms:
                total_duration += result.duration_ms
                
        # Print status summary
        for status in ValidationStatus:
            count = status_counts.get(status, 0)
            if count > 0:
                print(f"{status.value}: {count}")
                
        print(f"\n📊 Total Tests: {len(self.results)}")
        if total_duration > 0:
            print(f"⏱️  Total Duration: {total_duration:.2f}ms")
            
        # Print detailed results
        print("\n📋 DETAILED RESULTS:")
        print("-" * 60)
        
        for result in self.results:
            duration_str = f" ({result.duration_ms:.2f}ms)" if result.duration_ms else ""
            print(f"{result.status.value} {result.name}: {result.message}{duration_str}")
            
            if result.details:
                for key, value in result.details.items():
                    print(f"    {key}: {value}")
                    
        # Overall assessment
        failed_count = status_counts.get(ValidationStatus.FAIL, 0)
        if failed_count == 0:
            print(f"\n🎉 VALIDATION PASSED - All systems operational!")
            return True
        else:
            print(f"\n⚠️  VALIDATION ISSUES - {failed_count} critical failure(s) detected")
            return False
            
    async def run_all_validations(self) -> bool:
        """Run all validation tests"""
        print("🚀 Starting AICleaner v3 Architecture Validation...")
        print("="*60)
        
        validations = [
            ("Environment Setup", self.validate_environment_setup),
            ("Directory Structure", self.validate_directory_structure),
            ("Test Configurations", self.validate_test_configurations),
            ("Provider Connectivity", self.validate_provider_connectivity),
            ("Fallback System", self.validate_fallback_system),
            ("Performance Baseline", self.validate_performance_baseline),
        ]
        
        overall_success = True
        
        for validation_name, validation_func in validations:
            try:
                success = await validation_func()
                if not success:
                    overall_success = False
            except Exception as e:
                self.add_result(validation_name, ValidationStatus.FAIL, 
                              f"Validation crashed: {str(e)}")
                overall_success = False
                
        return self.print_summary()


async def main():
    """Main validation entry point"""
    validator = ArchitectureValidator()
    success = await validator.run_all_validations()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # Check dependencies and provide helpful messages
    missing_deps = []
    
    if not AIOHTTP_AVAILABLE:
        missing_deps.append("aiohttp (for network connectivity tests)")
    
    try:
        import yaml
    except ImportError:
        missing_deps.append("pyyaml (for configuration parsing)")
        
    if missing_deps:
        print("Optional dependencies missing:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nTo install: pip install aiohttp pyyaml")
        print("Or use system packages: sudo apt install python3-aiohttp python3-yaml")
        print("\nTests will run with limited functionality...\n")
        
    # Run validation
    asyncio.run(main())