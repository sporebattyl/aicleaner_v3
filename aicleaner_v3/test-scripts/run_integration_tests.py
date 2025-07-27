#!/usr/bin/env python3
"""
Integration Test Runner for AICleaner v3
Comprehensive testing of addon functionality in Docker environment
"""

import json
import logging
import os
import signal
import subprocess
import sys
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import paho.mqtt.client as mqtt
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntegrationTestRunner:
    """Comprehensive integration test runner for AICleaner v3"""
    
    def __init__(self):
        # Test configuration from environment
        self.mqtt_host = os.getenv('MQTT_HOST', 'mosquitto-test')
        self.mqtt_port = int(os.getenv('MQTT_PORT', 1883))
        self.ha_api_host = os.getenv('HA_API_HOST', 'homeassistant')
        self.ha_api_port = int(os.getenv('HA_API_PORT', 8123))
        self.device_id = os.getenv('DEVICE_ID', 'aicleaner_v3_test')
        self.ha_access_token = os.getenv('HA_ACCESS_TOKEN')
        
        # Validate required configuration
        if not self.ha_access_token:
            raise ValueError("HA_ACCESS_TOKEN environment variable is required for real HA API testing")
        
        # Test state
        self.mqtt_client = None
        self.test_results = []
        self.discovery_messages = {}
        self.state_messages = {}
        self.test_start_time = datetime.now()
        
        # Expected entities for validation
        self.expected_entities = [
            f'sensor.{self.device_id}_status',
            f'switch.{self.device_id}_enabled'
        ]
    
    def log_test_result(self, test_name: str, status: str, details: str = None, duration: float = None):
        """Log test result"""
        result = {
            'test_name': test_name,
            'status': status,  # 'PASS', 'FAIL', 'SKIP'
            'details': details,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_emoji = {'PASS': '✅', 'FAIL': '❌', 'SKIP': '⏭️'}.get(status, '❓')
        duration_str = f" ({duration:.2f}s)" if duration else ""
        logger.info(f"{status_emoji} {test_name}: {status}{duration_str}")
        if details:
            logger.info(f"   Details: {details}")
    
    def setup_mqtt_client(self) -> bool:
        """Set up MQTT client for testing"""
        try:
            self.mqtt_client = mqtt.Client()
            # Anonymous connection for testing environment
            # self.mqtt_client.username_pw_set('aicleaner', 'test_password')
            
            # Set up callbacks
            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    logger.info("Test runner connected to MQTT")
                    # Subscribe to all relevant topics
                    client.subscribe("homeassistant/#")
                    client.subscribe(f"aicleaner/{self.device_id}/#")
                else:
                    logger.error(f"MQTT connection failed: {rc}")
            
            def on_message(client, userdata, msg):
                topic = msg.topic
                try:
                    payload = msg.payload.decode('utf-8')
                    
                    # Store discovery messages
                    if topic.startswith('homeassistant/'):
                        self.discovery_messages[topic] = {
                            'payload': payload,
                            'timestamp': datetime.now().isoformat()
                        }
                    
                    # Store state messages
                    elif f'aicleaner/{self.device_id}/state' in topic:
                        try:
                            state_data = json.loads(payload)
                            self.state_messages[topic] = {
                                'data': state_data,
                                'timestamp': datetime.now().isoformat()
                            }
                        except json.JSONDecodeError:
                            pass
                            
                except Exception as e:
                    logger.error(f"Error processing MQTT message: {e}")
            
            self.mqtt_client.on_connect = on_connect
            self.mqtt_client.on_message = on_message
            
            # Connect
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup MQTT client: {e}")
            return False
    
    def test_service_health_checks(self) -> bool:
        """Test that all required services are healthy"""
        test_start = time.time()
        
        try:
            # Test MQTT broker
            mqtt_test = mqtt.Client()
            # Anonymous connection for testing
            # mqtt_test.username_pw_set('aicleaner', 'test_password')
            
            try:
                mqtt_test.connect(self.mqtt_host, self.mqtt_port, 10)
                mqtt_test.disconnect()
                mqtt_healthy = True
            except Exception as e:
                mqtt_healthy = False
                logger.error(f"MQTT health check failed: {e}")
            
            # Test Home Assistant API with authentication
            try:
                headers = {'Authorization': f'Bearer {self.ha_access_token}'}
                response = requests.get(f'http://{self.ha_api_host}:{self.ha_api_port}/api/', 
                                      headers=headers, timeout=10)
                ha_api_healthy = response.status_code == 200
                if ha_api_healthy:
                    logger.info("HA API authenticated successfully")
                else:
                    logger.error(f"HA API returned status {response.status_code}: {response.text}")
            except Exception as e:
                ha_api_healthy = False
                logger.error(f"HA API health check failed: {e}")
            
            duration = time.time() - test_start
            
            if mqtt_healthy and ha_api_healthy:
                self.log_test_result("Service Health Checks", "PASS", 
                                   "All services are healthy", duration)
                return True
            else:
                failed_services = []
                if not mqtt_healthy:
                    failed_services.append("MQTT")
                if not ha_api_healthy:
                    failed_services.append("HA API")
                
                self.log_test_result("Service Health Checks", "FAIL", 
                                   f"Failed services: {', '.join(failed_services)}", duration)
                return False
                
        except Exception as e:
            duration = time.time() - test_start
            self.log_test_result("Service Health Checks", "FAIL", str(e), duration)
            return False
    
    def test_mqtt_discovery_registration(self) -> bool:
        """Test MQTT discovery message registration"""
        test_start = time.time()
        
        try:
            # Wait for discovery messages (up to 60 seconds)
            timeout = 60
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                # Check for expected discovery topics
                status_topic = f'homeassistant/sensor/{self.device_id}/status/config'
                switch_topic = f'homeassistant/switch/{self.device_id}/enabled/config'
                
                if status_topic in self.discovery_messages and switch_topic in self.discovery_messages:
                    break
                
                time.sleep(1)
            
            duration = time.time() - test_start
            
            # Validate discovery messages
            expected_topics = [
                f'homeassistant/sensor/{self.device_id}/status/config',
                f'homeassistant/switch/{self.device_id}/enabled/config'
            ]
            
            found_topics = []
            missing_topics = []
            
            for topic in expected_topics:
                if topic in self.discovery_messages:
                    found_topics.append(topic)
                    
                    # Validate JSON structure
                    try:
                        payload = self.discovery_messages[topic]['payload']
                        config = json.loads(payload)
                        
                        # Check required fields
                        required_fields = ['name', 'unique_id', 'device']
                        missing_fields = [f for f in required_fields if f not in config]
                        
                        if missing_fields:
                            self.log_test_result("MQTT Discovery Registration", "FAIL", 
                                               f"Missing fields in {topic}: {missing_fields}", duration)
                            return False
                            
                    except json.JSONDecodeError as e:
                        self.log_test_result("MQTT Discovery Registration", "FAIL", 
                                           f"Invalid JSON in {topic}: {e}", duration)
                        return False
                else:
                    missing_topics.append(topic)
            
            if missing_topics:
                self.log_test_result("MQTT Discovery Registration", "FAIL", 
                                   f"Missing discovery topics: {missing_topics}", duration)
                return False
            
            self.log_test_result("MQTT Discovery Registration", "PASS", 
                               f"Found {len(found_topics)} discovery messages", duration)
            return True
            
        except Exception as e:
            duration = time.time() - test_start
            self.log_test_result("MQTT Discovery Registration", "FAIL", str(e), duration)
            return False
    
    def test_state_publishing(self) -> bool:
        """Test that addon publishes state correctly"""
        test_start = time.time()
        
        try:
            # Wait for initial state message
            timeout = 30
            start_time = time.time()
            
            state_topic = f'aicleaner/{self.device_id}/state'
            
            while time.time() - start_time < timeout:
                if state_topic in self.state_messages:
                    break
                time.sleep(1)
            
            duration = time.time() - test_start
            
            if state_topic not in self.state_messages:
                self.log_test_result("State Publishing", "FAIL", 
                                   "No state message received", duration)
                return False
            
            # Validate state structure
            state_data = self.state_messages[state_topic]['data']
            required_fields = ['status', 'enabled', 'timestamp']
            missing_fields = [f for f in required_fields if f not in state_data]
            
            if missing_fields:
                self.log_test_result("State Publishing", "FAIL", 
                                   f"Missing state fields: {missing_fields}", duration)
                return False
            
            self.log_test_result("State Publishing", "PASS", 
                               f"Valid state: {state_data['status']}", duration)
            return True
            
        except Exception as e:
            duration = time.time() - test_start
            self.log_test_result("State Publishing", "FAIL", str(e), duration)
            return False
    
    def test_command_handling(self) -> bool:
        """Test MQTT command handling"""
        test_start = time.time()
        
        try:
            if not self.mqtt_client:
                self.log_test_result("Command Handling", "FAIL", "MQTT client not available")
                return False
            
            command_topic = f'aicleaner/{self.device_id}/set'
            state_topic = f'aicleaner/{self.device_id}/state'
            
            # Clear any existing state messages to track new ones
            initial_message_count = len(self.state_messages.get(state_topic, {}))
            
            # Send enable command
            self.mqtt_client.publish(command_topic, "ON")
            
            # Wait for state change with timeout
            timeout = 10
            start_time = time.time()
            on_state_received = False
            
            while time.time() - start_time < timeout:
                if state_topic in self.state_messages:
                    latest_state = self.state_messages[state_topic]['data']
                    if latest_state.get('enabled') == 'ON':
                        on_state_received = True
                        break
                time.sleep(0.5)
            
            if not on_state_received:
                duration = time.time() - test_start
                self.log_test_result("Command Handling", "FAIL", 
                                   "ON command not processed", duration)
                return False
            
            # Now test disable command
            self.mqtt_client.publish(command_topic, "OFF")
            
            # Wait for OFF state change
            start_time = time.time()
            off_state_received = False
            
            while time.time() - start_time < timeout:
                if state_topic in self.state_messages:
                    updated_state = self.state_messages[state_topic]['data']
                    if updated_state.get('enabled') == 'OFF':
                        off_state_received = True
                        break
                time.sleep(0.5)
            
            if not off_state_received:
                duration = time.time() - test_start
                self.log_test_result("Command Handling", "FAIL", 
                                   "OFF command not processed", duration)
                return False
            
            duration = time.time() - test_start
            self.log_test_result("Command Handling", "PASS", 
                               "ON/OFF commands work correctly", duration)
            return True
            
        except Exception as e:
            duration = time.time() - test_start
            self.log_test_result("Command Handling", "FAIL", str(e), duration)
            return False
    
    def test_ha_api_integration(self) -> bool:
        """Test Home Assistant API integration"""
        test_start = time.time()
        
        try:
            # Test basic API connectivity with authentication
            headers = {'Authorization': f'Bearer {self.ha_access_token}'}
            response = requests.get(f'http://{self.ha_api_host}:{self.ha_api_port}/api/config', 
                                  headers=headers, timeout=10)
            
            if response.status_code != 200:
                duration = time.time() - test_start
                self.log_test_result("HA API Integration", "FAIL", 
                                   f"API returned status {response.status_code}: {response.text[:100]}", duration)
                return False
            
            config_data = response.json()
            
            # Validate config response
            if 'version' not in config_data:
                duration = time.time() - test_start
                self.log_test_result("HA API Integration", "FAIL", 
                                   "Invalid config response", duration)
                return False
                
            # Test MQTT integration in Home Assistant
            mqtt_configured = 'mqtt' in config_data.get('components', [])
            
            duration = time.time() - test_start
            ha_version = config_data['version']
            mqtt_status = "MQTT configured" if mqtt_configured else "MQTT not configured"
            
            self.log_test_result("HA API Integration", "PASS", 
                               f"HA {ha_version}, {mqtt_status}", duration)
            return True
            
        except Exception as e:
            duration = time.time() - test_start
            self.log_test_result("HA API Integration", "FAIL", str(e), duration)
            return False
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        skipped_tests = len([r for r in self.test_results if r['status'] == 'SKIP'])
        
        test_duration = datetime.now() - self.test_start_time
        
        report = {
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'skipped': skipped_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'total_duration': str(test_duration),
                'test_start': self.test_start_time.isoformat(),
                'test_end': datetime.now().isoformat()
            },
            'test_results': self.test_results,
            'discovery_messages': len(self.discovery_messages),
            'state_messages': len(self.state_messages),
            'environment': {
                'mqtt_host': self.mqtt_host,
                'ha_api_host': self.ha_api_host,
                'device_id': self.device_id
            }
        }
        
        return report
    
    def save_test_report(self, report: Dict[str, Any]):
        """Save test report to file"""
        try:
            results_dir = '/app/results'
            os.makedirs(results_dir, exist_ok=True)
            
            report_file = os.path.join(results_dir, f'integration_test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Test report saved to: {report_file}")
            
        except Exception as e:
            logger.error(f"Failed to save test report: {e}")
    
    def print_test_summary(self, report: Dict[str, Any]):
        """Print test summary to console"""
        summary = report['summary']
        
        print("\n" + "=" * 70)
        print("🧪 INTEGRATION TEST SUMMARY")
        print("=" * 70)
        print(f"📊 Total Tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"⏭️ Skipped: {summary['skipped']}")
        print(f"📈 Success Rate: {summary['success_rate']:.1f}%")
        print(f"⏱️ Total Duration: {summary['total_duration']}")
        print(f"🏠 Discovery Messages: {report['discovery_messages']}")
        print(f"📊 State Messages: {report['state_messages']}")
        print("=" * 70)
        
        # Print individual test results
        for result in self.test_results:
            status_emoji = {'PASS': '✅', 'FAIL': '❌', 'SKIP': '⏭️'}.get(result['status'], '❓')
            duration = f" ({result['duration']:.2f}s)" if result['duration'] else ""
            print(f"{status_emoji} {result['test_name']}{duration}")
            if result['details']:
                print(f"   📝 {result['details']}")
        
        print("=" * 70)
        
        # Overall result
        if summary['failed'] == 0:
            print("🎉 ALL TESTS PASSED! AICleaner v3 is working correctly.")
        else:
            print(f"⚠️ {summary['failed']} TEST(S) FAILED. Review the failures above.")
        
        print("=" * 70 + "\n")
    
    def run_all_tests(self) -> bool:
        """Run all integration tests"""
        logger.info("🧪 Starting AICleaner v3 Integration Tests")
        logger.info("=" * 60)
        
        # Dependencies are now installed via docker-compose command
        logger.info("Using pre-installed dependencies from container")
        
        # Set up MQTT client
        if not self.setup_mqtt_client():
            self.log_test_result("MQTT Setup", "FAIL", "Could not connect to MQTT broker")
            return False
        
        # Wait for initial MQTT connection to be established
        connection_timeout = 10
        start_time = time.time()
        while time.time() - start_time < connection_timeout:
            if self.mqtt_client and hasattr(self.mqtt_client, '_sock') and self.mqtt_client._sock:
                break
            time.sleep(0.5)
        
        # Give a brief moment for initial message processing
        time.sleep(2)
        
        # Run tests in sequence
        tests = [
            self.test_service_health_checks,
            self.test_mqtt_discovery_registration,
            self.test_state_publishing,
            self.test_command_handling,
            self.test_ha_api_integration
        ]
        
        all_passed = True
        
        for test in tests:
            try:
                result = test()
                if not result:
                    all_passed = False
            except Exception as e:
                logger.error(f"Test {test.__name__} crashed: {e}")
                self.log_test_result(test.__name__, "FAIL", f"Test crashed: {e}")
                all_passed = False
        
        # Clean up
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        
        # Generate and save report
        report = self.generate_test_report()
        self.save_test_report(report)
        self.print_test_summary(report)
        
        return all_passed

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("AICleaner v3 Integration Test Runner")
    logger.info("=" * 50)
    
    # Create and run tests
    test_runner = IntegrationTestRunner()
    
    try:
        success = test_runner.run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error in test runner: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()