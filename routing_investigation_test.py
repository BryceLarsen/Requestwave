#!/usr/bin/env python3
"""
ROUTING INVESTIGATION TEST

Comparing internal vs external API access to identify routing issues.
Testing both localhost:8001 (internal) and https://requestwave.app (external)
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
INTERNAL_URL = "http://localhost:8001/api"
EXTERNAL_URL = "https://requestwave.app/api"

# User credentials from review request
USER_CREDENTIALS = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class RoutingInvestigationTester:
    def __init__(self):
        self.results = {
            "internal": {"passed": 0, "failed": 0, "errors": []},
            "external": {"passed": 0, "failed": 0, "errors": []}
        }

    def log_result(self, test_name: str, success: bool, message: str = "", endpoint_type: str = "internal"):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} ({endpoint_type.upper()})")
        if message:
            print(f"   {message}")
        
        if success:
            self.results[endpoint_type]["passed"] += 1
        else:
            self.results[endpoint_type]["failed"] += 1
            self.results[endpoint_type]["errors"].append(f"{test_name}: {message}")

    def make_request(self, method: str, endpoint: str, base_url: str, data: Any = None, headers: Dict = None, timeout: int = 30) -> requests.Response:
        """Make HTTP request with proper headers"""
        url = f"{base_url}{endpoint}"
        
        # Default headers
        request_headers = {"Content-Type": "application/json"}
        
        # Override with custom headers
        if headers:
            request_headers.update(headers)
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=request_headers, timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(url, headers=request_headers, json=data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response
        except Exception as e:
            print(f"Request failed: {e}")
            raise

    def test_health_endpoint(self):
        """Test health endpoint on both internal and external"""
        print("🔍 TESTING HEALTH ENDPOINT")
        print("=" * 60)
        
        # Test internal
        try:
            response = self.make_request("GET", "/health", INTERNAL_URL)
            print(f"   📊 Internal health status: {response.status_code}")
            print(f"   📊 Internal health response: {response.text}")
            
            if response.status_code == 200:
                self.log_result("Health Endpoint", True, f"✅ Internal health working: {response.json()}", "internal")
            else:
                self.log_result("Health Endpoint", False, f"Internal health failed: {response.status_code}", "internal")
        except Exception as e:
            self.log_result("Health Endpoint", False, f"Internal health exception: {str(e)}", "internal")
        
        # Test external
        try:
            response = self.make_request("GET", "/health", EXTERNAL_URL)
            print(f"   📊 External health status: {response.status_code}")
            print(f"   📊 External health response: {response.text}")
            
            if response.status_code == 200:
                self.log_result("Health Endpoint", True, f"✅ External health working: {response.json()}", "external")
            else:
                self.log_result("Health Endpoint", False, f"External health failed: {response.status_code}", "external")
        except Exception as e:
            self.log_result("Health Endpoint", False, f"External health exception: {str(e)}", "external")
        
        print("=" * 60)

    def test_login_endpoint(self):
        """Test login endpoint on both internal and external"""
        print("🔍 TESTING LOGIN ENDPOINT")
        print("=" * 60)
        
        # Test internal
        try:
            response = self.make_request("POST", "/auth/login", INTERNAL_URL, USER_CREDENTIALS)
            print(f"   📊 Internal login status: {response.status_code}")
            print(f"   📊 Internal login response: {response.text}")
            
            if response.status_code == 200:
                self.log_result("Login Endpoint", True, f"✅ Internal login working", "internal")
            elif response.status_code == 401:
                self.log_result("Login Endpoint", False, f"Internal login failed - invalid credentials: {response.text}", "internal")
            else:
                self.log_result("Login Endpoint", False, f"Internal login error: {response.status_code} - {response.text}", "internal")
        except Exception as e:
            self.log_result("Login Endpoint", False, f"Internal login exception: {str(e)}", "internal")
        
        # Test external
        try:
            response = self.make_request("POST", "/auth/login", EXTERNAL_URL, USER_CREDENTIALS)
            print(f"   📊 External login status: {response.status_code}")
            print(f"   📊 External login response: {response.text}")
            
            if response.status_code == 200:
                self.log_result("Login Endpoint", True, f"✅ External login working", "external")
            elif response.status_code == 401:
                self.log_result("Login Endpoint", False, f"External login failed - invalid credentials: {response.text}", "external")
            elif response.status_code == 500:
                self.log_result("Login Endpoint", False, f"External login server error: {response.text}", "external")
            else:
                self.log_result("Login Endpoint", False, f"External login error: {response.status_code} - {response.text}", "external")
        except Exception as e:
            self.log_result("Login Endpoint", False, f"External login exception: {str(e)}", "external")
        
        print("=" * 60)

    def test_forgot_password_endpoint(self):
        """Test forgot password endpoint on both internal and external"""
        print("🔍 TESTING FORGOT PASSWORD ENDPOINT")
        print("=" * 60)
        
        forgot_data = {"email": USER_CREDENTIALS["email"]}
        
        # Test internal
        try:
            response = self.make_request("POST", "/auth/forgot-password", INTERNAL_URL, forgot_data)
            print(f"   📊 Internal forgot password status: {response.status_code}")
            print(f"   📊 Internal forgot password response: {response.text}")
            
            if response.status_code == 200:
                self.log_result("Forgot Password Endpoint", True, f"✅ Internal forgot password working", "internal")
            else:
                self.log_result("Forgot Password Endpoint", False, f"Internal forgot password failed: {response.status_code} - {response.text}", "internal")
        except Exception as e:
            self.log_result("Forgot Password Endpoint", False, f"Internal forgot password exception: {str(e)}", "internal")
        
        # Test external
        try:
            response = self.make_request("POST", "/auth/forgot-password", EXTERNAL_URL, forgot_data)
            print(f"   📊 External forgot password status: {response.status_code}")
            print(f"   📊 External forgot password response: {response.text}")
            
            if response.status_code == 200:
                self.log_result("Forgot Password Endpoint", True, f"✅ External forgot password working", "external")
            elif response.status_code == 500:
                self.log_result("Forgot Password Endpoint", False, f"External forgot password server error: {response.text}", "external")
            else:
                self.log_result("Forgot Password Endpoint", False, f"External forgot password failed: {response.status_code} - {response.text}", "external")
        except Exception as e:
            self.log_result("Forgot Password Endpoint", False, f"External forgot password exception: {str(e)}", "external")
        
        print("=" * 60)

    def test_registration_endpoint(self):
        """Test registration endpoint to check user existence"""
        print("🔍 TESTING REGISTRATION ENDPOINT (User Existence Check)")
        print("=" * 60)
        
        reg_data = {
            "name": "Test User",
            "email": USER_CREDENTIALS["email"],
            "password": "TestPassword123!"
        }
        
        # Test internal
        try:
            response = self.make_request("POST", "/auth/register", INTERNAL_URL, reg_data)
            print(f"   📊 Internal registration status: {response.status_code}")
            print(f"   📊 Internal registration response: {response.text}")
            
            if response.status_code == 400:
                self.log_result("Registration Endpoint", True, f"✅ Internal registration - user exists: {response.text}", "internal")
            elif response.status_code == 200:
                self.log_result("Registration Endpoint", False, f"Internal registration - user does not exist (unexpected)", "internal")
            else:
                self.log_result("Registration Endpoint", False, f"Internal registration error: {response.status_code} - {response.text}", "internal")
        except Exception as e:
            self.log_result("Registration Endpoint", False, f"Internal registration exception: {str(e)}", "internal")
        
        # Test external
        try:
            response = self.make_request("POST", "/auth/register", EXTERNAL_URL, reg_data)
            print(f"   📊 External registration status: {response.status_code}")
            print(f"   📊 External registration response: {response.text}")
            
            if response.status_code == 400:
                self.log_result("Registration Endpoint", True, f"✅ External registration - user exists: {response.text}", "external")
            elif response.status_code == 200:
                self.log_result("Registration Endpoint", False, f"External registration - user does not exist (unexpected)", "external")
            elif response.status_code == 500:
                self.log_result("Registration Endpoint", False, f"External registration server error: {response.text}", "external")
            else:
                self.log_result("Registration Endpoint", False, f"External registration error: {response.status_code} - {response.text}", "external")
        except Exception as e:
            self.log_result("Registration Endpoint", False, f"External registration exception: {str(e)}", "external")
        
        print("=" * 60)

    def run_routing_investigation(self):
        """Run comprehensive routing investigation"""
        print("🔍 ROUTING INVESTIGATION: INTERNAL vs EXTERNAL")
        print("🔍 Internal URL: http://localhost:8001/api")
        print("🔍 External URL: https://requestwave.app/api")
        print("=" * 80)
        
        # Run all tests
        self.test_health_endpoint()
        self.test_login_endpoint()
        self.test_forgot_password_endpoint()
        self.test_registration_endpoint()
        
        # Print final summary
        print("\n" + "=" * 80)
        print("🔍 ROUTING INVESTIGATION SUMMARY")
        print("=" * 80)
        
        # Internal summary
        internal_total = self.results["internal"]["passed"] + self.results["internal"]["failed"]
        internal_success = (self.results["internal"]["passed"] / internal_total * 100) if internal_total > 0 else 0
        
        print(f"📊 INTERNAL ENDPOINT RESULTS:")
        print(f"   Total Tests: {internal_total}")
        print(f"   ✅ Passed: {self.results['internal']['passed']}")
        print(f"   ❌ Failed: {self.results['internal']['failed']}")
        print(f"   📈 Success Rate: {internal_success:.1f}%")
        
        # External summary
        external_total = self.results["external"]["passed"] + self.results["external"]["failed"]
        external_success = (self.results["external"]["passed"] / external_total * 100) if external_total > 0 else 0
        
        print(f"\n📊 EXTERNAL ENDPOINT RESULTS:")
        print(f"   Total Tests: {external_total}")
        print(f"   ✅ Passed: {self.results['external']['passed']}")
        print(f"   ❌ Failed: {self.results['external']['failed']}")
        print(f"   📈 Success Rate: {external_success:.1f}%")
        
        # Print errors
        if self.results["internal"]["errors"]:
            print(f"\n❌ INTERNAL ISSUES:")
            for error in self.results["internal"]["errors"]:
                print(f"   • {error}")
        
        if self.results["external"]["errors"]:
            print(f"\n❌ EXTERNAL ISSUES:")
            for error in self.results["external"]["errors"]:
                print(f"   • {error}")
        
        # Diagnosis
        print(f"\n🔍 DIAGNOSIS:")
        if internal_success > external_success:
            print(f"   ❌ ROUTING ISSUE CONFIRMED: Internal endpoints work better than external")
            print(f"   📊 Internal success: {internal_success:.1f}% vs External success: {external_success:.1f}%")
            print(f"   🔧 Issue likely in proxy/ingress configuration")
        elif internal_success == external_success and internal_success < 100:
            print(f"   ❌ BACKEND ISSUE: Both internal and external have same issues")
            print(f"   📊 Success rate: {internal_success:.1f}%")
            print(f"   🔧 Issue likely in backend code or database")
        else:
            print(f"   ✅ ROUTING OK: Both internal and external working similarly")
            print(f"   📊 Success rate: {internal_success:.1f}%")
        
        print("=" * 80)

if __name__ == "__main__":
    tester = RoutingInvestigationTester()
    tester.run_routing_investigation()