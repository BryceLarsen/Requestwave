#!/usr/bin/env python3
"""
CRITICAL FIXES TESTING - Freemium Model Routing Conflicts
Focus: Test the two specific critical fixes identified in the review request:

CRITICAL FIX #1 - Subscription Status Endpoint Routing Conflict (RESOLVED):
- Test GET /api/subscription/status with valid authentication 
- Verify there's no longer a routing conflict between duplicate endpoints
- Should return freemium model subscription status with fields like audience_link_active, trial_active, etc.

CRITICAL FIX #2 - Checkout Endpoint Parameter Injection (RESOLVED):
- Test POST /api/subscription/checkout with proper JSON body containing package_id and origin_url
- Should no longer return 422 parameter injection errors
- Should successfully create Stripe checkout session

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://livewave-music.emergent.host/api"

# Test credentials provided in review request
TEST_CREDENTIALS = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class FreemiumCriticalFixesTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
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

    def make_request(self, method: str, endpoint: str, data: Any = None, files: Any = None, headers: Dict = None, params: Dict = None) -> requests.Response:
        """Make HTTP request with proper headers"""
        url = f"{self.base_url}{endpoint}"
        
        # Default headers
        request_headers = {"Content-Type": "application/json"}
        if self.auth_token:
            request_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        # Override with custom headers
        if headers:
            request_headers.update(headers)
        
        # Remove Content-Type for file uploads
        if files:
            request_headers.pop("Content-Type", None)
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=request_headers, params=data or params)
            elif method.upper() == "POST":
                if files:
                    response = requests.post(url, headers={k: v for k, v in request_headers.items() if k != "Content-Type"}, files=files, data=data)
                elif params:
                    response = requests.post(url, headers=request_headers, params=params)
                else:
                    response = requests.post(url, headers=request_headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=request_headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=request_headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response
        except Exception as e:
            print(f"Request failed: {e}")
            raise

    def login_test_user(self):
        """Login with test credentials"""
        try:
            print("🔐 Logging in with test credentials: brycelarsenmusic@gmail.com")
            
            login_data = {
                "email": TEST_CREDENTIALS["email"],
                "password": TEST_CREDENTIALS["password"]
            }
            
            response = self.make_request("POST", "/auth/login", login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "musician" in data:
                    self.auth_token = data["token"]
                    self.musician_id = data["musician"]["id"]
                    self.musician_slug = data["musician"]["slug"]
                    print(f"   ✅ Successfully logged in as: {data['musician']['name']}")
                    print(f"   ✅ Musician ID: {self.musician_id}")
                    print(f"   ✅ JWT Token (first 50 chars): {self.auth_token[:50]}...")
                    self.log_result("Test User Login", True, f"Logged in as {data['musician']['name']}")
                    return True
                else:
                    self.log_result("Test User Login", False, f"Missing token or musician in response: {data}")
                    return False
            else:
                self.log_result("Test User Login", False, f"Status code: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Test User Login", False, f"Exception: {str(e)}")
            return False

    def test_critical_fix_1_subscription_status_routing(self):
        """CRITICAL FIX #1: Test Subscription Status Endpoint Routing Conflict Resolution"""
        try:
            print("\n🚨 CRITICAL FIX #1: Testing Subscription Status Endpoint Routing Conflict Resolution")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Critical Fix #1 - Subscription Status Routing", False, "No authentication token available")
                return
            
            print("📊 Testing GET /api/subscription/status with valid authentication")
            print(f"   📊 Using JWT Token: {self.auth_token[:50]}...")
            print(f"   📊 Musician ID: {self.musician_id}")
            
            # Test the subscription status endpoint
            response = self.make_request("GET", "/subscription/status")
            
            print(f"   📊 Response Status Code: {response.status_code}")
            print(f"   📊 Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   📊 Response JSON: {json.dumps(data, indent=2, default=str)}")
                    
                    # Check for freemium model fields
                    expected_freemium_fields = [
                        "audience_link_active", 
                        "trial_active", 
                        "plan"
                    ]
                    
                    missing_fields = []
                    present_fields = []
                    
                    for field in expected_freemium_fields:
                        if field in data:
                            present_fields.append(field)
                            print(f"   ✅ Found expected field '{field}': {data[field]}")
                        else:
                            missing_fields.append(field)
                            print(f"   ❌ Missing expected field: {field}")
                    
                    # Check response structure
                    all_fields = list(data.keys())
                    print(f"   📊 All response fields: {all_fields}")
                    
                    if len(missing_fields) == 0:
                        self.log_result("Critical Fix #1 - Subscription Status Routing", True, 
                                      f"✅ ROUTING CONFLICT RESOLVED: GET /subscription/status returns freemium model data with all expected fields: {present_fields}")
                    else:
                        self.log_result("Critical Fix #1 - Subscription Status Routing", False, 
                                      f"❌ Missing freemium model fields: {missing_fields}. Present fields: {present_fields}")
                
                except json.JSONDecodeError:
                    self.log_result("Critical Fix #1 - Subscription Status Routing", False, 
                                  f"❌ Response is not valid JSON: {response.text}")
            
            elif response.status_code == 422:
                print(f"   🚨 422 Validation Error - Potential routing conflict still exists")
                print(f"   📊 Response body: {response.text}")
                self.log_result("Critical Fix #1 - Subscription Status Routing", False, 
                              f"❌ ROUTING CONFLICT NOT RESOLVED: Still getting 422 validation errors, indicating endpoint is being routed to wrong handler")
            
            elif response.status_code == 401 or response.status_code == 403:
                print(f"   🚨 Authentication Error: {response.status_code}")
                print(f"   📊 Response body: {response.text}")
                self.log_result("Critical Fix #1 - Subscription Status Routing", False, 
                              f"❌ Authentication failed: {response.status_code} - {response.text}")
            
            else:
                print(f"   🚨 Unexpected Status Code: {response.status_code}")
                print(f"   📊 Response body: {response.text}")
                self.log_result("Critical Fix #1 - Subscription Status Routing", False, 
                              f"❌ Unexpected response: {response.status_code} - {response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Critical Fix #1 - Subscription Status Routing", False, f"❌ Exception: {str(e)}")

    def test_critical_fix_2_checkout_parameter_injection(self):
        """CRITICAL FIX #2: Test Checkout Endpoint Parameter Injection Resolution"""
        try:
            print("\n🚨 CRITICAL FIX #2: Testing Checkout Endpoint Parameter Injection Resolution")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Critical Fix #2 - Checkout Parameter Injection", False, "No authentication token available")
                return
            
            print("📊 Testing POST /api/subscription/checkout with proper JSON body")
            print(f"   📊 Using JWT Token: {self.auth_token[:50]}...")
            print(f"   📊 Musician ID: {self.musician_id}")
            
            # Prepare checkout request data as specified in review request
            checkout_data = {
                "package_id": "monthly_plan",
                "origin_url": "https://livewave-music.emergent.host"
            }
            
            print(f"   📊 Request Body: {json.dumps(checkout_data, indent=2)}")
            
            # Test the checkout endpoint
            response = self.make_request("POST", "/subscription/checkout", checkout_data)
            
            print(f"   📊 Response Status Code: {response.status_code}")
            print(f"   📊 Response Headers: {dict(response.headers)}")
            print(f"   📊 Response Body: {response.text}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   📊 Response JSON: {json.dumps(data, indent=2, default=str)}")
                    
                    # Check for successful Stripe checkout session creation
                    expected_checkout_fields = ["url", "session_id"]
                    
                    missing_fields = []
                    present_fields = []
                    
                    for field in expected_checkout_fields:
                        if field in data:
                            present_fields.append(field)
                            print(f"   ✅ Found expected field '{field}': {data[field][:100]}..." if len(str(data[field])) > 100 else f"   ✅ Found expected field '{field}': {data[field]}")
                        else:
                            missing_fields.append(field)
                            print(f"   ❌ Missing expected field: {field}")
                    
                    # Verify Stripe checkout URL format
                    checkout_url = data.get("url", "")
                    if "checkout.stripe.com" in checkout_url:
                        print(f"   ✅ Valid Stripe checkout URL format")
                        stripe_url_valid = True
                    else:
                        print(f"   ❌ Invalid Stripe checkout URL format: {checkout_url}")
                        stripe_url_valid = False
                    
                    if len(missing_fields) == 0 and stripe_url_valid:
                        self.log_result("Critical Fix #2 - Checkout Parameter Injection", True, 
                                      f"✅ PARAMETER INJECTION RESOLVED: POST /subscription/checkout successfully creates Stripe checkout session with fields: {present_fields}")
                    else:
                        issues = []
                        if missing_fields:
                            issues.append(f"missing fields: {missing_fields}")
                        if not stripe_url_valid:
                            issues.append("invalid Stripe URL format")
                        
                        self.log_result("Critical Fix #2 - Checkout Parameter Injection", False, 
                                      f"❌ Checkout response issues: {', '.join(issues)}")
                
                except json.JSONDecodeError:
                    self.log_result("Critical Fix #2 - Checkout Parameter Injection", False, 
                                  f"❌ Response is not valid JSON: {response.text}")
            
            elif response.status_code == 422:
                print(f"   🚨 422 Validation Error - Parameter injection issue may still exist")
                try:
                    error_data = response.json()
                    print(f"   📊 Error details: {json.dumps(error_data, indent=2)}")
                    
                    # Check if it's expecting request creation fields (indicating routing conflict)
                    error_detail = error_data.get("detail", [])
                    if isinstance(error_detail, list):
                        error_fields = [item.get("loc", [])[-1] if item.get("loc") else "unknown" for item in error_detail]
                        print(f"   📊 Fields causing validation errors: {error_fields}")
                        
                        # Check if it's expecting request creation fields instead of checkout fields
                        request_creation_fields = ["musician_id", "song_id", "requester_name", "requester_email"]
                        if any(field in error_fields for field in request_creation_fields):
                            self.log_result("Critical Fix #2 - Checkout Parameter Injection", False, 
                                          f"❌ PARAMETER INJECTION NOT RESOLVED: Endpoint still expects request creation fields {error_fields} instead of checkout fields")
                        else:
                            self.log_result("Critical Fix #2 - Checkout Parameter Injection", False, 
                                          f"❌ Validation error with checkout fields: {error_fields}")
                    else:
                        self.log_result("Critical Fix #2 - Checkout Parameter Injection", False, 
                                      f"❌ 422 validation error: {error_detail}")
                
                except json.JSONDecodeError:
                    self.log_result("Critical Fix #2 - Checkout Parameter Injection", False, 
                                  f"❌ 422 error with non-JSON response: {response.text}")
            
            elif response.status_code == 401 or response.status_code == 403:
                print(f"   🚨 Authentication Error: {response.status_code}")
                print(f"   📊 Response body: {response.text}")
                self.log_result("Critical Fix #2 - Checkout Parameter Injection", False, 
                              f"❌ Authentication failed: {response.status_code} - {response.text}")
            
            else:
                print(f"   🚨 Unexpected Status Code: {response.status_code}")
                print(f"   📊 Response body: {response.text}")
                self.log_result("Critical Fix #2 - Checkout Parameter Injection", False, 
                              f"❌ Unexpected response: {response.status_code} - {response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Critical Fix #2 - Checkout Parameter Injection", False, f"❌ Exception: {str(e)}")

    def run_critical_fixes_tests(self):
        """Run all critical fixes tests"""
        print("🚨 FREEMIUM MODEL CRITICAL FIXES TESTING")
        print("=" * 80)
        print("Testing two specific critical fixes:")
        print("1. Subscription Status Endpoint Routing Conflict")
        print("2. Checkout Endpoint Parameter Injection")
        print("=" * 80)
        
        # Step 1: Login with test credentials
        if not self.login_test_user():
            print("❌ Cannot proceed without authentication")
            return
        
        # Step 2: Test Critical Fix #1
        self.test_critical_fix_1_subscription_status_routing()
        
        # Step 3: Test Critical Fix #2
        self.test_critical_fix_2_checkout_parameter_injection()
        
        # Final Results
        print("\n" + "=" * 80)
        print("🏁 CRITICAL FIXES TEST RESULTS")
        print("=" * 80)
        print(f"✅ Tests Passed: {self.results['passed']}")
        print(f"❌ Tests Failed: {self.results['failed']}")
        
        if self.results['failed'] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        if self.results['passed'] == 2 and self.results['failed'] == 0:
            print("\n🎉 ALL CRITICAL FIXES VERIFIED: Both routing conflicts have been resolved!")
        elif self.results['passed'] > 0:
            print(f"\n⚠️  PARTIAL SUCCESS: {self.results['passed']}/2 critical fixes verified")
        else:
            print("\n🚨 CRITICAL ISSUES REMAIN: Both fixes need additional work")
        
        print("=" * 80)

def main():
    """Main test execution"""
    tester = FreemiumCriticalFixesTester()
    tester.run_critical_fixes_tests()

if __name__ == "__main__":
    main()