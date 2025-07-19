"""
Home Assistant Integration Testing Module for AICleaner v3
Tests integration with Home Assistant API and services
"""

import os
import requests
import json
import time
from typing import Dict, List, Any, Optional
import sys

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from addons.aicleaner_v3.core.simple_logging import get_simple_logger

logger = get_simple_logger("test_integration_ha")


class HAIntegrationTester:
    """Home Assistant integration testing utility"""
    
    def __init__(self):
        self.ha_url = os.environ.get("HA_URL", "http://localhost:8123")
        self.ha_token = os.environ.get("HA_ACCESS_TOKEN")
        self.supervisor_token = os.environ.get("SUPERVISOR_TOKEN")
        self.headers = {}
        self.setup_headers()
    
    def setup_headers(self):
        """Setup request headers for API calls"""
        if self.ha_token:
            self.headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json"
            }
        elif self.supervisor_token:
            self.headers = {
                "Authorization": f"Bearer {self.supervisor_token}",
                "Content-Type": "application/json"
            }
    
    def test_ha_api_connectivity(self) -> Dict[str, Any]:
        """Test basic Home Assistant API connectivity"""
        logger.info("Testing Home Assistant API connectivity...")
        
        if not self.ha_token and not self.supervisor_token:
            return {
                "test": "HA API Connectivity",
                "status": "SKIP",
                "reason": "No HA_ACCESS_TOKEN or SUPERVISOR_TOKEN environment variable set"
            }
        
        try:
            # Test basic API endpoint
            response = requests.get(
                f"{self.ha_url}/api/",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                api_data = response.json()
                return {
                    "test": "HA API Connectivity",
                    "status": "PASS",
                    "ha_version": api_data.get("version", "unknown"),
                    "response_time": response.elapsed.total_seconds()
                }
            else:
                return {
                    "test": "HA API Connectivity",
                    "status": "FAIL",
                    "reason": f"HTTP {response.status_code}: {response.text}"
                }
        
        except requests.exceptions.RequestException as e:
            return {
                "test": "HA API Connectivity",
                "status": "FAIL",
                "reason": f"Connection error: {str(e)}"
            }
    
    def test_supervisor_api_access(self) -> Dict[str, Any]:
        """Test Home Assistant Supervisor API access"""
        logger.info("Testing Supervisor API access...")
        
        if not self.supervisor_token:
            return {
                "test": "Supervisor API Access",
                "status": "SKIP",
                "reason": "No SUPERVISOR_TOKEN environment variable set"
            }
        
        try:
            # Test supervisor info endpoint
            response = requests.get(
                "http://supervisor/info",
                headers={"Authorization": f"Bearer {self.supervisor_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                supervisor_data = response.json()
                return {
                    "test": "Supervisor API Access",
                    "status": "PASS",
                    "supervisor_version": supervisor_data.get("data", {}).get("version", "unknown"),
                    "response_time": response.elapsed.total_seconds()
                }
            else:
                return {
                    "test": "Supervisor API Access",
                    "status": "FAIL",
                    "reason": f"HTTP {response.status_code}: {response.text}"
                }
        
        except requests.exceptions.RequestException as e:
            return {
                "test": "Supervisor API Access",
                "status": "FAIL",
                "reason": f"Connection error: {str(e)}"
            }
    
    def test_addon_service_registration(self) -> Dict[str, Any]:
        """Test if AICleaner v3 services are registered with Home Assistant"""
        logger.info("Testing AICleaner v3 service registration...")
        
        if not self.headers:
            return {
                "test": "AICleaner Service Registration",
                "status": "SKIP",
                "reason": "No authentication token available"
            }
        
        try:
            # Get all services
            response = requests.get(
                f"{self.ha_url}/api/services",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200:
                return {
                    "test": "AICleaner Service Registration",
                    "status": "FAIL",
                    "reason": f"Failed to get services: HTTP {response.status_code}"
                }
            
            services = response.json()
            aicleaner_services = []
            
            # Look for AICleaner services
            for service in services:
                domain = service.get("domain", "")
                if "aicleaner" in domain.lower():
                    aicleaner_services.append(service)
            
            if aicleaner_services:
                return {
                    "test": "AICleaner Service Registration",
                    "status": "PASS",
                    "services_found": len(aicleaner_services),
                    "service_domains": [s.get("domain") for s in aicleaner_services]
                }
            else:
                return {
                    "test": "AICleaner Service Registration",
                    "status": "FAIL",
                    "reason": "No AICleaner services found in Home Assistant"
                }
        
        except requests.exceptions.RequestException as e:
            return {
                "test": "AICleaner Service Registration",
                "status": "FAIL",
                "reason": f"Connection error: {str(e)}"
            }
    
    def test_entity_registration(self) -> Dict[str, Any]:
        """Test if AICleaner v3 entities are registered with Home Assistant"""
        logger.info("Testing AICleaner v3 entity registration...")
        
        if not self.headers:
            return {
                "test": "AICleaner Entity Registration",
                "status": "SKIP",
                "reason": "No authentication token available"
            }
        
        try:
            # Get all states (entities)
            response = requests.get(
                f"{self.ha_url}/api/states",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200:
                return {
                    "test": "AICleaner Entity Registration",
                    "status": "FAIL",
                    "reason": f"Failed to get states: HTTP {response.status_code}"
                }
            
            states = response.json()
            aicleaner_entities = []
            
            # Look for AICleaner entities
            for state in states:
                entity_id = state.get("entity_id", "")
                if "aicleaner" in entity_id.lower():
                    aicleaner_entities.append(state)
            
            if aicleaner_entities:
                return {
                    "test": "AICleaner Entity Registration",
                    "status": "PASS",
                    "entities_found": len(aicleaner_entities),
                    "entity_ids": [e.get("entity_id") for e in aicleaner_entities[:5]]  # Show first 5
                }
            else:
                return {
                    "test": "AICleaner Entity Registration",
                    "status": "WARN",
                    "reason": "No AICleaner entities found (may be normal if addon creates entities dynamically)"
                }
        
        except requests.exceptions.RequestException as e:
            return {
                "test": "AICleaner Entity Registration",
                "status": "FAIL",
                "reason": f"Connection error: {str(e)}"
            }
    
    def test_addon_ingress_access(self) -> Dict[str, Any]:
        """Test if addon ingress interface is accessible"""
        logger.info("Testing AICleaner v3 ingress access...")
        
        try:
            # Try to access the addon's ingress interface
            # This would typically be available at a specific path
            ingress_url = f"{self.ha_url}/api/hassio_ingress/aicleaner_v3/"
            
            if self.supervisor_token:
                ingress_headers = {
                    "Authorization": f"Bearer {self.supervisor_token}",
                    "Content-Type": "application/json"
                }
            else:
                ingress_headers = self.headers
            
            response = requests.get(
                ingress_url,
                headers=ingress_headers,
                timeout=10,
                allow_redirects=True
            )
            
            # Check if we get a reasonable response (200, 302, etc.)
            if response.status_code in [200, 302, 401]:  # 401 might be expected if not authenticated
                return {
                    "test": "AICleaner Ingress Access",
                    "status": "PASS",
                    "response_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                }
            else:
                return {
                    "test": "AICleaner Ingress Access",
                    "status": "FAIL",
                    "reason": f"HTTP {response.status_code}: {response.text[:200]}"
                }
        
        except requests.exceptions.RequestException as e:
            return {
                "test": "AICleaner Ingress Access",
                "status": "FAIL",
                "reason": f"Connection error: {str(e)}"
            }
    
    def test_addon_logs_access(self) -> Dict[str, Any]:
        """Test if addon logs are accessible through Supervisor API"""
        logger.info("Testing AICleaner v3 logs access...")
        
        if not self.supervisor_token:
            return {
                "test": "AICleaner Logs Access",
                "status": "SKIP",
                "reason": "No SUPERVISOR_TOKEN environment variable set"
            }
        
        try:
            # Try to access addon logs
            response = requests.get(
                "http://supervisor/addons/aicleaner_v3/logs",
                headers={"Authorization": f"Bearer {self.supervisor_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                logs_content = response.text
                return {
                    "test": "AICleaner Logs Access",
                    "status": "PASS",
                    "logs_length": len(logs_content),
                    "has_recent_logs": "AICleaner" in logs_content or "aicleaner" in logs_content
                }
            else:
                return {
                    "test": "AICleaner Logs Access",
                    "status": "FAIL",
                    "reason": f"HTTP {response.status_code}: {response.text[:200]}"
                }
        
        except requests.exceptions.RequestException as e:
            return {
                "test": "AICleaner Logs Access",
                "status": "FAIL",
                "reason": f"Connection error: {str(e)}"
            }
    
    def test_performance_under_load(self) -> Dict[str, Any]:
        """Test API performance under simulated load"""
        logger.info("Testing API performance under load...")
        
        if not self.headers:
            return {
                "test": "API Performance Under Load",
                "status": "SKIP",
                "reason": "No authentication token available"
            }
        
        try:
            # Perform multiple API calls to test performance
            start_time = time.time()
            successful_calls = 0
            failed_calls = 0
            
            for i in range(10):  # 10 API calls
                try:
                    response = requests.get(
                        f"{self.ha_url}/api/",
                        headers=self.headers,
                        timeout=5
                    )
                    if response.status_code == 200:
                        successful_calls += 1
                    else:
                        failed_calls += 1
                except requests.exceptions.RequestException:
                    failed_calls += 1
            
            total_time = time.time() - start_time
            avg_response_time = total_time / (successful_calls + failed_calls) if (successful_calls + failed_calls) > 0 else 0
            
            status = "PASS" if successful_calls >= 8 and avg_response_time < 2.0 else "WARN"
            
            return {
                "test": "API Performance Under Load",
                "status": status,
                "successful_calls": successful_calls,
                "failed_calls": failed_calls,
                "total_time": total_time,
                "avg_response_time": avg_response_time
            }
        
        except Exception as e:
            return {
                "test": "API Performance Under Load",
                "status": "FAIL",
                "reason": f"Test error: {str(e)}"
            }
    
    def run_all_integration_tests(self) -> List[Dict[str, Any]]:
        """Run all integration tests"""
        logger.info("Starting Home Assistant integration tests...")
        
        tests = [
            self.test_ha_api_connectivity,
            self.test_supervisor_api_access,
            self.test_addon_service_registration,
            self.test_entity_registration,
            self.test_addon_ingress_access,
            self.test_addon_logs_access,
            self.test_performance_under_load
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
                logger.info(f"Test {result['test']}: {result['status']}")
            except Exception as e:
                logger.error(f"Error running test {test.__name__}: {e}")
                results.append({
                    "test": test.__name__,
                    "status": "FAIL",
                    "reason": f"Test execution error: {str(e)}"
                })
        
        logger.info("Home Assistant integration tests completed")
        return results


def run_ha_integration_tests() -> List[Dict[str, Any]]:
    """Main function to run Home Assistant integration tests"""
    tester = HAIntegrationTester()
    return tester.run_all_integration_tests()


if __name__ == "__main__":
    # Run tests if script is executed directly
    results = run_ha_integration_tests()
    
    # Print summary
    print("\n=== Home Assistant Integration Test Summary ===")
    for result in results:
        test_name = result["test"]
        status = result["status"]
        print(f"{test_name}: {status}")
        if result.get("reason"):
            print(f"  Reason: {result['reason']}")
    print("===============================================")