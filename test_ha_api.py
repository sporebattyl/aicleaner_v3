#!/usr/bin/env python3
"""
Home Assistant API Testing Script
Automated testing for AICleaner V3 addon once HA is set up
"""

import requests
import json
import time
import sys
from typing import Optional, Dict, Any

class HomeAssistantTester:
    def __init__(self, base_url: str = "http://localhost:8123"):
        self.base_url = base_url
        self.session = requests.Session()
        self.token: Optional[str] = None
        
    def check_ha_availability(self) -> bool:
        """Check if Home Assistant is responding"""
        try:
            response = self.session.get(f"{self.base_url}/api/", timeout=5)
            # HA returns 400, 401, or 415 for API access without auth, which means it's running
            return response.status_code in [400, 401, 415]
        except requests.exceptions.RequestException:
            return False
    
    def set_auth_token(self, token: str):
        """Set the Long-Lived Access Token for API calls"""
        self.token = token
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_api_connection(self) -> Dict[str, Any]:
        """Test basic API connectivity"""
        if not self.token:
            return {"status": "error", "message": "No authentication token provided"}
            
        try:
            response = self.session.get(f"{self.base_url}/api/")
            if response.status_code == 200:
                return {"status": "success", "data": response.json()}
            else:
                return {"status": "error", "code": response.status_code, "message": response.text}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}
    
    def get_addon_entities(self) -> Dict[str, Any]:
        """Get all entities related to AICleaner addon"""
        try:
            response = self.session.get(f"{self.base_url}/api/states")
            if response.status_code == 200:
                entities = response.json()
                aicleaner_entities = [
                    entity for entity in entities 
                    if entity.get('entity_id', '').startswith('sensor.aicleaner') 
                    or entity.get('entity_id', '').startswith('switch.aicleaner')
                    or entity.get('entity_id', '').startswith('binary_sensor.aicleaner')
                ]
                return {"status": "success", "entities": aicleaner_entities, "count": len(aicleaner_entities)}
            else:
                return {"status": "error", "code": response.status_code}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}
    
    def get_addon_services(self) -> Dict[str, Any]:
        """Get all services provided by AICleaner addon"""
        try:
            response = self.session.get(f"{self.base_url}/api/services")
            if response.status_code == 200:
                services = response.json()
                aicleaner_services = [
                    service for domain, service_list in services.items()
                    if domain.startswith('aicleaner')
                    for service in service_list
                ]
                return {"status": "success", "services": aicleaner_services}
            else:
                return {"status": "error", "code": response.status_code}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}
    
    def call_addon_service(self, domain: str, service: str, service_data: Dict = None) -> Dict[str, Any]:
        """Call an AICleaner service"""
        if service_data is None:
            service_data = {}
            
        try:
            response = self.session.post(
                f"{self.base_url}/api/services/{domain}/{service}",
                json=service_data
            )
            return {"status": "success" if response.status_code == 200 else "error", 
                   "code": response.status_code, "response": response.text}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive addon testing"""
        results = {
            "timestamp": time.time(),
            "tests": {}
        }
        
        print("🔍 Starting AICleaner V3 Automated Testing...")
        
        # Test 1: HA Availability
        print("1. Testing Home Assistant availability...")
        ha_available = self.check_ha_availability()
        results["tests"]["ha_availability"] = {"passed": ha_available}
        print(f"   {'✅' if ha_available else '❌'} Home Assistant {'available' if ha_available else 'not available'}")
        
        if not ha_available:
            return results
        
        # Test 2: API Connection (requires token)
        if self.token:
            print("2. Testing API connection...")
            api_test = self.test_api_connection()
            results["tests"]["api_connection"] = api_test
            print(f"   {'✅' if api_test['status'] == 'success' else '❌'} API connection")
            
            # Test 3: Entity Discovery
            print("3. Discovering AICleaner entities...")
            entities_test = self.get_addon_entities()
            results["tests"]["entity_discovery"] = entities_test
            if entities_test["status"] == "success":
                print(f"   ✅ Found {entities_test['count']} AICleaner entities")
            else:
                print("   ❌ Entity discovery failed")
            
            # Test 4: Service Discovery
            print("4. Discovering AICleaner services...")
            services_test = self.get_addon_services()
            results["tests"]["service_discovery"] = services_test
            print(f"   {'✅' if services_test['status'] == 'success' else '❌'} Service discovery")
            
        else:
            print("2-4. Skipping API tests (no authentication token provided)")
            results["tests"]["api_connection"] = {"status": "skipped", "message": "No token provided"}
        
        return results

def main():
    """Main testing function"""
    print("AICleaner V3 Home Assistant API Tester")
    print("=====================================")
    
    tester = HomeAssistantTester()
    
    # Check for token in command line arguments
    if len(sys.argv) > 1:
        token = sys.argv[1]
        tester.set_auth_token(token)
        print(f"Using authentication token: {token[:10]}...")
    else:
        print("No authentication token provided - limited testing available")
        print("Usage: python3 test_ha_api.py [LONG_LIVED_ACCESS_TOKEN]")
    
    # Run tests
    results = tester.run_comprehensive_test()
    
    # Summary
    print("\n📊 Test Summary:")
    passed_tests = sum(1 for test in results["tests"].values() 
                      if isinstance(test, dict) and test.get("status") == "success" or test.get("passed") == True)
    total_tests = len(results["tests"])
    print(f"Passed: {passed_tests}/{total_tests}")
    
    # Save detailed results
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Detailed results saved to test_results.json")

if __name__ == "__main__":
    main()