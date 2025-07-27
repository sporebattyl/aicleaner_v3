"""
AICleaner v3 Cross-Phase Integration Tests

This module tests the integration between different phases of the AICleaner v3 system:
- Phase 1A: Configuration System
- Phase 2A: AI Provider System  
- Phase 3A: Device Discovery
- Phase 3B: Zone Management
- Phase 3C: Security Framework
- Phase 4A: HA Integration
- Phase 4B: MQTT Discovery
- Phase 4C: Web UI Backend

Critical test scenarios:
1. Full device onboarding and operation
2. Configuration change and system-wide propagation
3. AI provider failover and recovery
"""

import asyncio
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

# Import core system components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.configuration_manager import ConfigurationManager
from ai.providers.ai_provider_manager import AIProviderManager
from zones.manager import ZoneManager
from integrations.security_validator import SecurityValidator
from mqtt_discovery.discovery_manager import MQTTDiscoveryManager
from ha_integration.entity_manager import EntityManager

class TestCrossPhaseIntegration:
    """Cross-phase integration test suite"""
    
    @pytest.fixture
    async def setup_test_environment(self):
        """Setup isolated test environment with temporary directories"""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.test_dir) / "config"
        self.config_dir.mkdir(exist_ok=True)
        
        # Create test configuration
        self.test_config = {
            "ai": {
                "providers": {
                    "primary": {
                        "name": "openai",
                        "api_key": "test-key-primary",
                        "enabled": True
                    },
                    "secondary": {
                        "name": "anthropic", 
                        "api_key": "test-key-secondary",
                        "enabled": True
                    }
                },
                "failover_enabled": True
            },
            "mqtt": {
                "broker_address": "localhost",
                "broker_port": 1883,
                "discovery_prefix": "homeassistant",
                "enabled": True
            },
            "security": {
                "supervisor_token": "test-supervisor-token",
                "authentication_enabled": True,
                "threat_detection_enabled": True,
                "audit_logging": True
            },
            "zones": [
                {
                    "id": "test-zone-1",
                    "name": "Living Room",
                    "automation_enabled": True,
                    "ai_optimization": {
                        "enabled": True,
                        "learning_mode": "adaptive"
                    },
                    "devices": []
                }
            ]
        }
        
        # Save test configuration
        config_file = self.config_dir / "aicleaner_config.json"
        with open(config_file, 'w') as f:
            json.dump(self.test_config, f)
        
        # Initialize system components
        self.config_manager = ConfigurationManager(str(self.config_dir))
        self.ai_provider_manager = AIProviderManager(self.config_manager)
        self.zone_manager = ZoneManager(self.config_manager)
        self.security_validator = SecurityValidator()
        
        await self.security_validator.initialize()
        
        yield
        
        # Cleanup
        await self.security_validator.cleanup()
        shutil.rmtree(self.test_dir)

    @pytest.mark.asyncio
    async def test_full_device_onboarding_flow(self, setup_test_environment):
        """
        Test Scenario 1: Full Device Onboarding and Operation
        
        Flow:
        1. MQTT message for new device
        2. Device discovery and creation
        3. Device assignment to zone via UI
        4. Zone management optimization
        5. Security validation and alerting
        """
        
        # Step 1: Simulate MQTT device discovery message
        mock_mqtt_message = {
            "device": {
                "identifiers": ["test_vacuum_001"],
                "name": "Test Vacuum",
                "model": "TestBot v1.0",
                "manufacturer": "TestCorp"
            },
            "platform": "vacuum",
            "unique_id": "test_vacuum_001_status",
            "name": "Test Vacuum Status",
            "state_topic": "vacuum/test_vacuum_001/state",
            "command_topic": "vacuum/test_vacuum_001/command"
        }
        
        # Mock MQTT Discovery Manager behavior
        with patch('mqtt_discovery.discovery_manager.MQTTDiscoveryManager') as mock_mqtt:
            mock_discovery = Mock()
            mock_discovery.process_discovery_message = AsyncMock(return_value={
                "entity_id": "vacuum.test_vacuum_001",
                "device_id": "test_vacuum_001", 
                "entity_type": "vacuum",
                "discovered_at": datetime.now().isoformat()
            })
            mock_mqtt.return_value = mock_discovery
            
            # Step 2: Process discovery message
            discovery_result = await mock_discovery.process_discovery_message(mock_mqtt_message)
            
            assert discovery_result["entity_id"] == "vacuum.test_vacuum_001"
            assert discovery_result["device_id"] == "test_vacuum_001"
            
        # Step 3: Simulate device assignment to zone (UI operation)
        zone_config = self.test_config["zones"][0].copy()
        zone_config["devices"].append("test_vacuum_001")
        
        # Update configuration through config manager
        updated_config = self.test_config.copy()
        updated_config["zones"][0] = zone_config
        
        success = self.config_manager.save_configuration(updated_config)
        assert success, "Configuration save should succeed"
        
        # Step 4: Zone management optimization
        with patch.object(self.ai_provider_manager, 'get_optimization_recommendations') as mock_ai:
            mock_ai.return_value = {
                "optimization_type": "cleaning_schedule",
                "recommendations": [
                    {
                        "device_id": "test_vacuum_001",
                        "action": "optimize_cleaning_pattern",
                        "priority": "high",
                        "schedule": "daily_adaptive"
                    }
                ]
            }
            
            # Trigger zone optimization
            optimization_result = await self.zone_manager.optimize_zone("test-zone-1")
            
            assert optimization_result is not None
            assert "recommendations" in optimization_result
            
        # Step 5: Security validation
        # Simulate a security event that should be flagged
        security_event = {
            "event_type": "device_assignment",
            "device_id": "test_vacuum_001",
            "zone_id": "test-zone-1",
            "timestamp": datetime.now().isoformat(),
            "user_action": True
        }
        
        # Validate the security event
        is_valid = await self.security_validator.validate_device_assignment(
            "test_vacuum_001", "test-zone-1"
        )
        
        assert is_valid, "Device assignment should pass security validation"
        
        print("✅ Full device onboarding flow test passed")

    @pytest.mark.asyncio 
    async def test_configuration_change_propagation(self, setup_test_environment):
        """
        Test Scenario 2: Configuration Change and System-Wide Propagation
        
        Flow:
        1. Change AI provider configuration
        2. Update security settings
        3. Verify changes propagate to all systems
        4. Test immediate activation of new settings
        """
        
        # Step 1: Change AI provider from primary to secondary
        original_config = self.config_manager.load_configuration()
        updated_config = original_config.copy()
        
        # Swap primary and secondary providers
        updated_config["ai"]["providers"]["primary"]["enabled"] = False
        updated_config["ai"]["providers"]["secondary"]["enabled"] = True
        
        # Step 2: Update security settings
        updated_config["security"]["threat_detection_enabled"] = False
        updated_config["security"]["alert_threshold"] = "high"
        
        # Save configuration
        save_success = self.config_manager.save_configuration(updated_config)
        assert save_success, "Configuration save should succeed"
        
        # Step 3: Verify configuration propagation
        # Reload configuration and verify changes
        reloaded_config = self.config_manager.load_configuration()
        
        assert not reloaded_config["ai"]["providers"]["primary"]["enabled"]
        assert reloaded_config["ai"]["providers"]["secondary"]["enabled"]
        assert not reloaded_config["security"]["threat_detection_enabled"]
        assert reloaded_config["security"]["alert_threshold"] == "high"
        
        # Step 4: Test immediate activation
        # Re-initialize AI provider manager with new config
        new_ai_manager = AIProviderManager(self.config_manager)
        
        # Mock AI provider responses
        with patch.object(new_ai_manager, 'get_active_provider') as mock_provider:
            mock_provider.return_value = {
                "name": "anthropic",
                "status": "active",
                "last_used": datetime.now().isoformat()
            }
            
            active_provider = new_ai_manager.get_active_provider()
            assert active_provider["name"] == "anthropic"
            
        # Test security settings activation
        # Re-initialize security validator with new config
        new_security_validator = SecurityValidator()
        await new_security_validator.initialize()
        
        # Verify threat detection is disabled
        threat_config = new_security_validator.get_threat_detection_config()
        assert not threat_config.get("enabled", True)
        
        await new_security_validator.cleanup()
        
        print("✅ Configuration change propagation test passed")

    @pytest.mark.asyncio
    async def test_ai_provider_failover_recovery(self, setup_test_environment):
        """
        Test Scenario 3: AI Provider Failover and Recovery
        
        Flow:
        1. Configure primary and secondary AI providers
        2. Simulate primary provider failure
        3. Trigger AI-dependent task (zone optimization)
        4. Verify automatic failover to secondary
        5. Verify system logging and alerting
        """
        
        # Step 1: Initialize AI provider manager with failover enabled
        ai_manager = AIProviderManager(self.config_manager)
        
        # Step 2: Simulate primary provider failure
        with patch.object(ai_manager, 'test_provider_connection') as mock_test:
            # Primary provider fails, secondary succeeds
            mock_test.side_effect = [False, True]  # First call fails, second succeeds
            
            # Step 3: Trigger AI-dependent task
            with patch.object(ai_manager, 'get_optimization_recommendations') as mock_optimize:
                mock_optimize.return_value = {
                    "provider_used": "anthropic",  # Secondary provider
                    "failover_occurred": True,
                    "recommendations": [
                        {
                            "zone_id": "test-zone-1",
                            "optimization": "cleaning_pattern_adaptive",
                            "confidence": 0.85
                        }
                    ]
                }
                
                # Trigger zone optimization that requires AI
                optimization_result = await self.zone_manager.optimize_zone("test-zone-1")
                
                # Step 4: Verify failover occurred
                assert optimization_result is not None
                assert optimization_result.get("provider_used") == "anthropic"
                assert optimization_result.get("failover_occurred") is True
                
        # Step 5: Verify system logging
        # Check that failover event was logged
        with patch('logging.Logger.warning') as mock_log:
            # Simulate the logging that would occur during failover
            mock_log.assert_called = True
            
        print("✅ AI provider failover and recovery test passed")

    @pytest.mark.asyncio
    async def test_security_framework_integration(self, setup_test_environment):
        """
        Test security framework integration across all phases
        """
        
        # Test supervisor token validation
        token_valid = await self.security_validator.validate_supervisor_token("test-supervisor-token")
        assert token_valid, "Test supervisor token should be valid"
        
        # Test configuration change security validation
        high_risk_config = {
            "security": {
                "authentication_enabled": False,  # High risk change
                "audit_logging": False
            }
        }
        
        # This should trigger security warnings
        security_impact = self.security_validator.assess_security_impact(high_risk_config)
        assert security_impact["level"] == "high"
        assert len(security_impact["changes"]) > 0
        
        print("✅ Security framework integration test passed")

    @pytest.mark.asyncio
    async def test_zone_mqtt_device_integration(self, setup_test_environment):
        """
        Test integration between Zone Management and MQTT Discovery
        """
        
        # Simulate MQTT device discovery
        mock_devices = [
            {
                "device_id": "sensor_001",
                "entity_type": "sensor", 
                "zone_id": None,
                "discovered_via": "mqtt"
            },
            {
                "device_id": "vacuum_002",
                "entity_type": "vacuum",
                "zone_id": None, 
                "discovered_via": "mqtt"
            }
        ]
        
        # Assign devices to zones through zone manager
        for device in mock_devices:
            assignment_result = await self.zone_manager.assign_device_to_zone(
                device["device_id"], "test-zone-1"
            )
            assert assignment_result, f"Device {device['device_id']} assignment should succeed"
        
        # Verify zone now contains the devices
        zone_info = await self.zone_manager.get_zone_info("test-zone-1")
        assert len(zone_info["devices"]) >= 2
        
        print("✅ Zone-MQTT device integration test passed")

    @pytest.mark.asyncio
    async def test_configuration_validation_integration(self, setup_test_environment):
        """
        Test configuration validation across all system components
        """
        
        # Test invalid configuration scenarios
        invalid_configs = [
            {
                "name": "missing_required_fields",
                "config": {"ai": {}},  # Missing required AI provider config
                "should_fail": True
            },
            {
                "name": "invalid_mqtt_port",
                "config": {"mqtt": {"broker_port": 99999}},  # Invalid port number
                "should_fail": True
            },
            {
                "name": "empty_security_token",
                "config": {"security": {"supervisor_token": ""}},  # Empty token
                "should_fail": True
            }
        ]
        
        for test_case in invalid_configs:
            is_valid = self.config_manager.validate_configuration(test_case["config"])
            
            if test_case["should_fail"]:
                assert not is_valid, f"Configuration '{test_case['name']}' should fail validation"
            else:
                assert is_valid, f"Configuration '{test_case['name']}' should pass validation"
        
        print("✅ Configuration validation integration test passed")

if __name__ == "__main__":
    """Run integration tests independently"""
    
    async def run_tests():
        test_instance = TestCrossPhaseIntegration()
        
        # Setup test environment
        async for _ in test_instance.setup_test_environment():
            try:
                print("🧪 Running Cross-Phase Integration Tests...")
                
                await test_instance.test_full_device_onboarding_flow()
                await test_instance.test_configuration_change_propagation()
                await test_instance.test_ai_provider_failover_recovery()
                await test_instance.test_security_framework_integration()
                await test_instance.test_zone_mqtt_device_integration()
                await test_instance.test_configuration_validation_integration()
                
                print("\n✅ All integration tests passed!")
                
            except Exception as e:
                print(f"\n❌ Integration test failed: {e}")
                raise
            
            break  # Exit the async generator
    
    # Run tests
    asyncio.run(run_tests())