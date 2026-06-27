#!/usr/bin/env python3
"""
V2 CHECKOUT ENDPOINT TESTING
Focus: Test the v2 checkout endpoint to complete the freemium subscription routing fixes

PRIORITY 1: Test POST /api/v2/subscription/checkout
- Test with JSON body: {"plan": "monthly", "success_url": "https://livewave-music.emergent.host/dashboard?tab=subscription&session_id={CHECKOUT_SESSION_ID}", "cancel_url": "https://livewave-music.emergent.host/dashboard?tab=subscription"}
- Should return checkout_url and session_id without 422 errors

PRIORITY 2: Test remaining v2 endpoints
- POST /api/v2/subscription/cancel - Test subscription cancellation  
- GET /api/v2/subscription/checkout/status/{session_id} - Test with dummy session ID

Use existing credentials: brycelarsenmusic@gmail.com / RequestWave2024!

Expected Results:
- No 422 validation errors on checkout endpoint
- Proper JSON response with Stripe checkout URL
- All v2 endpoints accessible and functional
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration - Use the correct backend URL from frontend/.env
BASE_URL = "https://chordpro-stage.preview.emergentagent.com/api"

# Pro account credentials
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class V2CheckoutTester:
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

    def make_request(self, method: str, endpoint: str, data: Any = None, headers: Dict = None, params: Dict = None) -> requests.Response:
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
                response = requests.get(url, headers=request_headers, params=params)
            elif method.upper() == "POST":
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

    def login_pro_user(self):
        """Login with Pro user credentials"""
        print("🔐 Logging in with brycelarsenmusic@gmail.com / RequestWave2024!")
        
        login_data = {
            "email": PRO_MUSICIAN["email"],
            "password": PRO_MUSICIAN["password"]
        }
        
        response = self.make_request("POST", "/auth/login", login_data)
        
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data["token"]
            self.musician_id = data["musician"]["id"]
            self.musician_slug = data["musician"]["slug"]
            print(f"   ✅ Successfully logged in as: {data['musician']['name']}")
            print(f"   ✅ Musician ID: {self.musician_id}")
            print(f"   ✅ JWT Token (first 50 chars): {self.auth_token[:50]}...")
            return True
        else:
            print(f"   ❌ Login failed: {response.status_code}, Response: {response.text}")
            return False

    def test_v2_checkout_endpoint(self):
        """PRIORITY 1: Test POST /api/v2/subscription/checkout"""
        print("\n🎯 PRIORITY 1: Testing POST /api/v2/subscription/checkout")
        print("=" * 80)
        
        # Test data as specified in the request
        checkout_data = {
            "plan": "monthly",
            "success_url": "https://livewave-music.emergent.host/dashboard?tab=subscription&session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": "https://livewave-music.emergent.host/dashboard?tab=subscription"
        }
        
        print(f"📊 Request data: {json.dumps(checkout_data, indent=2)}")
        
        response = self.make_request("POST", "/v2/subscription/checkout", checkout_data)
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Response headers: {dict(response.headers)}")
        print(f"📊 Response body: {response.text}")
        
        if response.status_code == 422:
            print("❌ CRITICAL: 422 validation error detected - routing conflict still exists!")
            try:
                error_data = response.json()
                print(f"   Error details: {json.dumps(error_data, indent=2)}")
            except:
                pass
            self.log_result("v2 Checkout Endpoint", False, "422 validation error - routing conflict with legacy endpoints")
            return None
        
        elif response.status_code == 200:
            try:
                result = response.json()
                print(f"📊 Success response structure: {list(result.keys())}")
                
                # Check for expected fields
                if "checkout_url" in result and "session_id" in result:
                    checkout_url = result["checkout_url"]
                    session_id = result["session_id"]
                    
                    print(f"   ✅ Checkout URL: {checkout_url}")
                    print(f"   ✅ Session ID: {session_id}")
                    
                    # Verify it's a valid Stripe checkout URL
                    if "checkout.stripe.com" in checkout_url or "stripe.com" in checkout_url:
                        print(f"   ✅ Valid Stripe checkout URL format")
                        self.log_result("v2 Checkout Endpoint", True, f"Successfully created checkout session with URL: {checkout_url[:100]}...")
                        return session_id
                    else:
                        print(f"   ❌ Invalid checkout URL format: {checkout_url}")
                        self.log_result("v2 Checkout Endpoint", False, "Invalid checkout URL format")
                        return None
                else:
                    print(f"   ❌ Missing checkout_url or session_id in response")
                    self.log_result("v2 Checkout Endpoint", False, "Missing required fields in response")
                    return None
                    
            except json.JSONDecodeError:
                print(f"   ❌ Response is not valid JSON")
                self.log_result("v2 Checkout Endpoint", False, "Response is not valid JSON")
                return None
        
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            self.log_result("v2 Checkout Endpoint", False, f"Unexpected status code: {response.status_code}")
            return None

    def test_v2_checkout_status_endpoint(self, session_id: str = None):
        """PRIORITY 2: Test GET /api/v2/subscription/checkout/status/{session_id}"""
        print("\n🎯 PRIORITY 2: Testing GET /api/v2/subscription/checkout/status/{session_id}")
        print("=" * 80)
        
        # Use provided session_id or create a dummy one
        test_session_id = session_id or "cs_test_dummy_session_id_for_testing"
        
        print(f"📊 Testing with session ID: {test_session_id}")
        
        response = self.make_request("GET", f"/v2/subscription/checkout/status/{test_session_id}")
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Response body: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"📊 Response structure: {list(result.keys())}")
                
                # Check for expected fields
                expected_fields = ["status", "payment_status"]
                missing_fields = [field for field in expected_fields if field not in result]
                
                if len(missing_fields) == 0:
                    print(f"   ✅ All expected fields present: {expected_fields}")
                    print(f"   ✅ Status: {result.get('status')}")
                    print(f"   ✅ Payment status: {result.get('payment_status')}")
                    self.log_result("v2 Checkout Status Endpoint", True, f"Successfully retrieved checkout status")
                else:
                    print(f"   ❌ Missing fields: {missing_fields}")
                    self.log_result("v2 Checkout Status Endpoint", False, f"Missing expected fields: {missing_fields}")
                    
            except json.JSONDecodeError:
                print(f"   ❌ Response is not valid JSON")
                self.log_result("v2 Checkout Status Endpoint", False, "Response is not valid JSON")
        
        elif response.status_code == 404:
            print(f"   ℹ️  Session not found (expected for dummy session)")
            self.log_result("v2 Checkout Status Endpoint", True, "Endpoint accessible - 404 expected for dummy session")
        
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            self.log_result("v2 Checkout Status Endpoint", False, f"Unexpected status code: {response.status_code}")

    def test_v2_cancel_endpoint(self):
        """PRIORITY 2: Test POST /api/v2/subscription/cancel"""
        print("\n🎯 PRIORITY 2: Testing POST /api/v2/subscription/cancel")
        print("=" * 80)
        
        response = self.make_request("POST", "/v2/subscription/cancel")
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Response body: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"📊 Response structure: {list(result.keys())}")
                
                # Check for expected fields
                if "success" in result and "message" in result:
                    print(f"   ✅ Success: {result.get('success')}")
                    print(f"   ✅ Message: {result.get('message')}")
                    self.log_result("v2 Cancel Endpoint", True, f"Cancel endpoint working: {result.get('message')}")
                else:
                    print(f"   ❌ Missing success or message fields")
                    self.log_result("v2 Cancel Endpoint", False, "Missing expected fields in response")
                    
            except json.JSONDecodeError:
                print(f"   ❌ Response is not valid JSON")
                self.log_result("v2 Cancel Endpoint", False, "Response is not valid JSON")
        
        elif response.status_code == 400:
            # Might be expected if no active subscription
            try:
                result = response.json()
                print(f"   ℹ️  Cancel not possible: {result.get('detail', 'No active subscription')}")
                self.log_result("v2 Cancel Endpoint", True, "Endpoint accessible - 400 expected for no active subscription")
            except:
                self.log_result("v2 Cancel Endpoint", True, "Endpoint accessible - 400 expected for no active subscription")
        
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            self.log_result("v2 Cancel Endpoint", False, f"Unexpected status code: {response.status_code}")

    def run_all_tests(self):
        """Run all v2 endpoint tests"""
        print("🚀 Starting V2 Checkout Endpoint Testing")
        print("=" * 80)
        print(f"Backend URL: {self.base_url}")
        print(f"Test User: {PRO_MUSICIAN['email']}")
        print("=" * 80)
        
        # Step 1: Login
        if not self.login_pro_user():
            print("❌ Cannot proceed without authentication")
            return
        
        # Step 2: Test v2 checkout endpoint (PRIORITY 1)
        session_id = self.test_v2_checkout_endpoint()
        
        # Step 3: Test v2 checkout status endpoint (PRIORITY 2)
        self.test_v2_checkout_status_endpoint(session_id)
        
        # Step 4: Test v2 cancel endpoint (PRIORITY 2)
        self.test_v2_cancel_endpoint()
        
        # Final results
        print("\n" + "=" * 80)
        print("🏁 FINAL RESULTS")
        print("=" * 80)
        
        total_tests = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        
        if self.results["failed"] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results["errors"]:
                print(f"   - {error}")
        
        if self.results["passed"] == total_tests:
            print("\n🎉 ALL V2 ENDPOINTS WORKING! Routing conflicts resolved.")
        elif self.results["passed"] >= 2:
            print("\n✅ Most v2 endpoints working. Minor issues detected.")
        else:
            print("\n❌ CRITICAL: Major issues with v2 endpoints. Routing conflicts likely still exist.")

if __name__ == "__main__":
    tester = V2CheckoutTester()
    tester.run_all_tests()