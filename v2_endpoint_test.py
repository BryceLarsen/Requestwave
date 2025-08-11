#!/usr/bin/env python3
"""
V2 Endpoint Routing Test
Focus: Quick test to verify v2 endpoint routing after moving endpoints before router inclusion

Test Requirements:
1. Test GET /api/v2/test - Simple test endpoint
2. Test GET /api/v2/subscription/status with authentication

Use existing credentials: brycelarsenmusic@gmail.com / RequestWave2024!
"""

import requests
import json
import os
from typing import Dict, Any

# Configuration - Use the deployed URL from frontend/.env
BASE_URL = "https://02097561-4318-47d1-b18b-ed57f34042df.preview.emergentagent.com/api"

# Pro account credentials
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class V2EndpointTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }

    def log_result(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"   {message}")
        
        if success:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name}: {message}")

    def make_request(self, method: str, endpoint: str, data: Any = None, headers: Dict = None) -> requests.Response:
        """Make HTTP request with proper headers"""
        url = f"{self.base_url}{endpoint}"
        
        # Default headers
        request_headers = {"Content-Type": "application/json"}
        if self.auth_token:
            request_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        # Override with custom headers
        if headers:
            request_headers.update(headers)
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=request_headers)
            elif method.upper() == "POST":
                response = requests.post(url, headers=request_headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response
        except Exception as e:
            print(f"Request failed: {e}")
            raise

    def login_pro_user(self):
        """Login with Pro user credentials"""
        try:
            print("🔐 Logging in with Pro user credentials...")
            login_data = {
                "email": PRO_MUSICIAN["email"],
                "password": PRO_MUSICIAN["password"]
            }
            
            response = self.make_request("POST", "/auth/login", login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "musician" in data:
                    self.auth_token = data["token"]
                    musician_name = data["musician"]["name"]
                    print(f"   ✅ Successfully logged in as: {musician_name}")
                    print(f"   ✅ JWT Token (first 50 chars): {self.auth_token[:50]}...")
                    return True
                else:
                    print(f"   ❌ Missing token or musician in response: {data}")
                    return False
            else:
                print(f"   ❌ Login failed with status: {response.status_code}")
                print(f"   ❌ Response: {response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Login exception: {str(e)}")
            return False

    def test_v2_test_endpoint(self):
        """Test GET /api/v2/test - Simple test endpoint"""
        try:
            print("\n🧪 Testing GET /api/v2/test endpoint...")
            
            response = self.make_request("GET", "/v2/test")
            
            print(f"   📊 Status Code: {response.status_code}")
            print(f"   📊 Response: {response.text}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Check for expected fields
                    if "message" in data and "timestamp" in data:
                        message = data.get("message", "")
                        timestamp = data.get("timestamp", "")
                        
                        if "v2 routing is working" in message:
                            self.log_result("GET /v2/test", True, f"✅ v2 routing confirmed working. Message: '{message}', Timestamp: {timestamp}")
                        else:
                            self.log_result("GET /v2/test", False, f"❌ Unexpected message: '{message}'")
                    else:
                        self.log_result("GET /v2/test", False, f"❌ Missing expected fields. Response: {data}")
                        
                except json.JSONDecodeError:
                    self.log_result("GET /v2/test", False, f"❌ Response is not valid JSON: {response.text}")
            else:
                self.log_result("GET /v2/test", False, f"❌ Endpoint failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("GET /v2/test", False, f"❌ Exception: {str(e)}")

    def test_v2_subscription_status(self):
        """Test GET /api/v2/subscription/status with authentication"""
        try:
            print("\n🧪 Testing GET /api/v2/subscription/status with authentication...")
            
            if not self.auth_token:
                self.log_result("GET /v2/subscription/status", False, "❌ No authentication token available")
                return
            
            response = self.make_request("GET", "/v2/subscription/status")
            
            print(f"   📊 Status Code: {response.status_code}")
            print(f"   📊 Response: {response.text}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Check for freemium model fields
                    expected_fields = [
                        "plan", "audience_link_active", "trial_active", 
                        "trial_ends_at", "subscription_ends_at", "days_remaining", 
                        "can_reactivate", "grace_period_active", "grace_period_ends_at"
                    ]
                    
                    missing_fields = [field for field in expected_fields if field not in data]
                    present_fields = [field for field in expected_fields if field in data]
                    
                    print(f"   📊 Present fields: {present_fields}")
                    if missing_fields:
                        print(f"   📊 Missing fields: {missing_fields}")
                    
                    # Check key values
                    plan = data.get("plan", "unknown")
                    audience_link_active = data.get("audience_link_active", False)
                    trial_active = data.get("trial_active", False)
                    
                    print(f"   📊 Plan: {plan}")
                    print(f"   📊 Audience Link Active: {audience_link_active}")
                    print(f"   📊 Trial Active: {trial_active}")
                    
                    if len(missing_fields) == 0:
                        self.log_result("GET /v2/subscription/status", True, f"✅ All expected freemium fields present. Plan: {plan}, Active: {audience_link_active}")
                    elif len(present_fields) >= 6:  # Most fields present
                        self.log_result("GET /v2/subscription/status", True, f"✅ Most freemium fields present ({len(present_fields)}/{len(expected_fields)}). Plan: {plan}")
                    else:
                        self.log_result("GET /v2/subscription/status", False, f"❌ Too many missing fields: {missing_fields}")
                        
                except json.JSONDecodeError:
                    self.log_result("GET /v2/subscription/status", False, f"❌ Response is not valid JSON: {response.text}")
            elif response.status_code == 401:
                self.log_result("GET /v2/subscription/status", False, f"❌ Authentication failed - token may be invalid")
            elif response.status_code == 403:
                self.log_result("GET /v2/subscription/status", False, f"❌ Access forbidden - insufficient permissions")
            elif response.status_code == 422:
                self.log_result("GET /v2/subscription/status", False, f"❌ CRITICAL: 422 validation error - routing conflict detected! Response: {response.text}")
            else:
                self.log_result("GET /v2/subscription/status", False, f"❌ Endpoint failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("GET /v2/subscription/status", False, f"❌ Exception: {str(e)}")

    def run_tests(self):
        """Run all v2 endpoint tests"""
        print("🚀 Starting V2 Endpoint Routing Tests")
        print("=" * 80)
        print(f"Base URL: {self.base_url}")
        print(f"Testing with user: {PRO_MUSICIAN['email']}")
        print("=" * 80)
        
        # Step 1: Login
        if not self.login_pro_user():
            print("\n❌ CRITICAL: Cannot proceed without authentication")
            return
        
        # Step 2: Test v2/test endpoint
        self.test_v2_test_endpoint()
        
        # Step 3: Test v2/subscription/status endpoint
        self.test_v2_subscription_status()
        
        # Final Results
        print("\n" + "=" * 80)
        print("🏁 V2 ENDPOINT ROUTING TEST RESULTS")
        print("=" * 80)
        
        total_tests = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        
        if self.results["failed"] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        if success_rate == 100:
            print("\n🎉 ALL V2 ENDPOINTS WORKING! Routing issue resolved.")
        elif success_rate >= 50:
            print("\n⚠️  PARTIAL SUCCESS: Some v2 endpoints working, check failed tests.")
        else:
            print("\n🚨 CRITICAL: V2 endpoint routing still has major issues.")
        
        print("=" * 80)

if __name__ == "__main__":
    tester = V2EndpointTester()
    tester.run_tests()