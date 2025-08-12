#!/usr/bin/env python3
"""
SUBSCRIPTION CHECKOUT BUG INVESTIGATION

User reports error "Error processing subscription. Please try again." when clicking "Start $39 today" button.

REPRODUCE THE BUG:
1. Authenticate with existing user: brycelarsenmusic@gmail.com / RequestWave2024!
2. Test the exact frontend call: POST /api/subscription/checkout with body:
   - plan: "annual" 
   - success_url: "https://example.com/dashboard?tab=subscription&session_id={CHECKOUT_SESSION_ID}"
   - cancel_url: "https://example.com/dashboard?tab=subscription"
3. Check for specific errors:
   - Authentication issues?
   - Stripe API key causing problems?
   - Validation errors with request format?
   - 500 error vs 400 error?
4. Test with monthly plan as well

EXPECTED BEHAVIOR: 
- Should return either {"checkout_url": "..."} OR a 400 error with clear Stripe error message
- Should NOT return 500 errors or generic error messages

DEBUG INFORMATION NEEDED:
- Exact HTTP status code returned
- Full error response body
- Any backend logs showing Stripe API errors
- Whether the issue is authentication, Stripe configuration, or request validation
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration - Use the exact URL from frontend/.env
BASE_URL = "https://musician-dashboard.preview.emergentagent.com/api"

# Test credentials from review request
TEST_CREDENTIALS = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class SubscriptionCheckoutBugTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
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

    def authenticate_user(self):
        """Step 1: Authenticate with existing user brycelarsenmusic@gmail.com / RequestWave2024!"""
        print("🔐 STEP 1: Authenticating with existing user")
        print("=" * 80)
        
        try:
            login_data = {
                "email": TEST_CREDENTIALS["email"],
                "password": TEST_CREDENTIALS["password"]
            }
            
            response = self.make_request("POST", "/auth/login", login_data)
            
            print(f"📊 Login Status Code: {response.status_code}")
            print(f"📊 Login Response Headers: {dict(response.headers)}")
            print(f"📊 Login Response Body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "musician" in data:
                    self.auth_token = data["token"]
                    self.musician_id = data["musician"]["id"]
                    musician_name = data["musician"]["name"]
                    
                    print(f"✅ Successfully authenticated as: {musician_name}")
                    print(f"✅ Musician ID: {self.musician_id}")
                    print(f"✅ JWT Token (first 50 chars): {self.auth_token[:50]}...")
                    
                    self.log_result("User Authentication", True, f"Successfully logged in as {musician_name}")
                    return True
                else:
                    self.log_result("User Authentication", False, f"Missing token or musician in response: {data}")
                    return False
            else:
                self.log_result("User Authentication", False, f"Login failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("User Authentication", False, f"Exception during login: {str(e)}")
            return False

    def test_annual_plan_checkout(self):
        """Step 2: Test the exact frontend call for annual plan ($39 today)"""
        print("💳 STEP 2: Testing Annual Plan Checkout (Start $39 today)")
        print("=" * 80)
        
        try:
            # Exact request body from review request
            checkout_data = {
                "plan": "annual",
                "success_url": "https://example.com/dashboard?tab=subscription&session_id={CHECKOUT_SESSION_ID}",
                "cancel_url": "https://example.com/dashboard?tab=subscription"
            }
            
            print(f"📊 Request URL: {self.base_url}/subscription/checkout")
            print(f"📊 Request Headers: Authorization: Bearer {self.auth_token[:20]}...")
            print(f"📊 Request Body: {json.dumps(checkout_data, indent=2)}")
            
            response = self.make_request("POST", "/subscription/checkout", checkout_data)
            
            print(f"📊 Response Status Code: {response.status_code}")
            print(f"📊 Response Headers: {dict(response.headers)}")
            print(f"📊 Response Body: {response.text}")
            
            # Analyze the response
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if "checkout_url" in response_data:
                        checkout_url = response_data["checkout_url"]
                        print(f"✅ SUCCESS: Checkout URL generated: {checkout_url}")
                        self.log_result("Annual Plan Checkout", True, f"Successfully created checkout session: {checkout_url[:100]}...")
                        return True
                    else:
                        print(f"❌ ISSUE: Response missing checkout_url field")
                        self.log_result("Annual Plan Checkout", False, f"Response missing checkout_url: {response_data}")
                        return False
                except json.JSONDecodeError:
                    print(f"❌ ISSUE: Response is not valid JSON")
                    self.log_result("Annual Plan Checkout", False, f"Invalid JSON response: {response.text}")
                    return False
                    
            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", "Unknown error")
                    print(f"⚠️  400 ERROR (Expected): {error_detail}")
                    
                    # Check if it's a clear Stripe error message
                    if "stripe" in error_detail.lower() or "api" in error_detail.lower():
                        print(f"✅ EXPECTED: Clear Stripe API error message")
                        self.log_result("Annual Plan Checkout", True, f"Expected 400 error with clear Stripe message: {error_detail}")
                        return True
                    else:
                        print(f"❌ ISSUE: Generic 400 error without clear Stripe message")
                        self.log_result("Annual Plan Checkout", False, f"Generic 400 error: {error_detail}")
                        return False
                except json.JSONDecodeError:
                    print(f"❌ ISSUE: 400 error response is not valid JSON")
                    self.log_result("Annual Plan Checkout", False, f"400 error with invalid JSON: {response.text}")
                    return False
                    
            elif response.status_code == 422:
                try:
                    error_data = response.json()
                    print(f"❌ CRITICAL: 422 Validation Error - {error_data}")
                    print(f"❌ This indicates routing conflicts or parameter injection issues")
                    self.log_result("Annual Plan Checkout", False, f"422 validation error (routing conflict): {error_data}")
                    return False
                except json.JSONDecodeError:
                    print(f"❌ CRITICAL: 422 error with invalid JSON response")
                    self.log_result("Annual Plan Checkout", False, f"422 error with invalid JSON: {response.text}")
                    return False
                    
            elif response.status_code == 500:
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", "Unknown server error")
                    print(f"❌ CRITICAL: 500 Server Error - {error_detail}")
                    print(f"❌ This should NOT happen - indicates backend implementation issue")
                    self.log_result("Annual Plan Checkout", False, f"500 server error (should not happen): {error_detail}")
                    return False
                except json.JSONDecodeError:
                    print(f"❌ CRITICAL: 500 error with invalid JSON response")
                    self.log_result("Annual Plan Checkout", False, f"500 error with invalid JSON: {response.text}")
                    return False
                    
            elif response.status_code == 401 or response.status_code == 403:
                print(f"❌ AUTHENTICATION ISSUE: {response.status_code} - {response.text}")
                self.log_result("Annual Plan Checkout", False, f"Authentication failed: {response.status_code}")
                return False
                
            else:
                print(f"❌ UNEXPECTED STATUS CODE: {response.status_code}")
                self.log_result("Annual Plan Checkout", False, f"Unexpected status code {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ EXCEPTION: {str(e)}")
            self.log_result("Annual Plan Checkout", False, f"Exception during checkout: {str(e)}")
            return False

    def test_monthly_plan_checkout(self):
        """Step 3: Test with monthly plan as well"""
        print("💳 STEP 3: Testing Monthly Plan Checkout")
        print("=" * 80)
        
        try:
            # Test with monthly plan
            checkout_data = {
                "plan": "monthly",
                "success_url": "https://example.com/dashboard?tab=subscription&session_id={CHECKOUT_SESSION_ID}",
                "cancel_url": "https://example.com/dashboard?tab=subscription"
            }
            
            print(f"📊 Request URL: {self.base_url}/subscription/checkout")
            print(f"📊 Request Body: {json.dumps(checkout_data, indent=2)}")
            
            response = self.make_request("POST", "/subscription/checkout", checkout_data)
            
            print(f"📊 Response Status Code: {response.status_code}")
            print(f"📊 Response Body: {response.text}")
            
            # Analyze the response (same logic as annual plan)
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if "checkout_url" in response_data:
                        checkout_url = response_data["checkout_url"]
                        print(f"✅ SUCCESS: Monthly checkout URL generated: {checkout_url}")
                        self.log_result("Monthly Plan Checkout", True, f"Successfully created monthly checkout session")
                        return True
                    else:
                        self.log_result("Monthly Plan Checkout", False, f"Response missing checkout_url: {response_data}")
                        return False
                except json.JSONDecodeError:
                    self.log_result("Monthly Plan Checkout", False, f"Invalid JSON response: {response.text}")
                    return False
                    
            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", "Unknown error")
                    print(f"⚠️  400 ERROR (Expected): {error_detail}")
                    
                    if "stripe" in error_detail.lower() or "api" in error_detail.lower():
                        self.log_result("Monthly Plan Checkout", True, f"Expected 400 error with clear Stripe message: {error_detail}")
                        return True
                    else:
                        self.log_result("Monthly Plan Checkout", False, f"Generic 400 error: {error_detail}")
                        return False
                except json.JSONDecodeError:
                    self.log_result("Monthly Plan Checkout", False, f"400 error with invalid JSON: {response.text}")
                    return False
                    
            elif response.status_code == 422:
                try:
                    error_data = response.json()
                    print(f"❌ CRITICAL: 422 Validation Error - {error_data}")
                    self.log_result("Monthly Plan Checkout", False, f"422 validation error (routing conflict): {error_data}")
                    return False
                except json.JSONDecodeError:
                    self.log_result("Monthly Plan Checkout", False, f"422 error with invalid JSON: {response.text}")
                    return False
                    
            elif response.status_code == 500:
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", "Unknown server error")
                    print(f"❌ CRITICAL: 500 Server Error - {error_detail}")
                    self.log_result("Monthly Plan Checkout", False, f"500 server error (should not happen): {error_detail}")
                    return False
                except json.JSONDecodeError:
                    self.log_result("Monthly Plan Checkout", False, f"500 error with invalid JSON: {response.text}")
                    return False
                    
            else:
                self.log_result("Monthly Plan Checkout", False, f"Unexpected status code {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Monthly Plan Checkout", False, f"Exception during monthly checkout: {str(e)}")
            return False

    def check_stripe_configuration(self):
        """Step 4: Check Stripe configuration and API key issues"""
        print("🔧 STEP 4: Checking Stripe Configuration")
        print("=" * 80)
        
        try:
            # Test subscription status endpoint to see if Stripe is configured
            response = self.make_request("GET", "/subscription/status")
            
            print(f"📊 Subscription Status Code: {response.status_code}")
            print(f"📊 Subscription Status Response: {response.text}")
            
            if response.status_code == 200:
                try:
                    status_data = response.json()
                    print(f"✅ Subscription status endpoint working: {status_data}")
                    self.log_result("Stripe Configuration Check", True, "Subscription status endpoint accessible")
                    return True
                except json.JSONDecodeError:
                    self.log_result("Stripe Configuration Check", False, "Status endpoint returns invalid JSON")
                    return False
            else:
                self.log_result("Stripe Configuration Check", False, f"Status endpoint failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Stripe Configuration Check", False, f"Exception checking Stripe config: {str(e)}")
            return False

    def test_alternative_endpoints(self):
        """Step 5: Test alternative subscription endpoints that might exist"""
        print("🔍 STEP 5: Testing Alternative Subscription Endpoints")
        print("=" * 80)
        
        # List of possible endpoint variations
        endpoint_variations = [
            "/subscription/checkout",
            "/v2/subscription/checkout", 
            "/subscriptions/checkout",
            "/stripe/checkout",
            "/checkout/subscription"
        ]
        
        checkout_data = {
            "plan": "annual",
            "success_url": "https://example.com/dashboard?tab=subscription&session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": "https://example.com/dashboard?tab=subscription"
        }
        
        working_endpoints = []
        
        for endpoint in endpoint_variations:
            try:
                print(f"📊 Testing endpoint: {endpoint}")
                response = self.make_request("POST", endpoint, checkout_data)
                
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
                if response.status_code == 200:
                    working_endpoints.append(endpoint)
                    print(f"   ✅ Working endpoint found!")
                elif response.status_code == 400:
                    working_endpoints.append(f"{endpoint} (400 - expected)")
                    print(f"   ⚠️  400 error (might be expected)")
                elif response.status_code == 422:
                    print(f"   ❌ 422 validation error (routing conflict)")
                elif response.status_code == 404:
                    print(f"   ℹ️  404 not found (expected)")
                else:
                    print(f"   ❌ Unexpected status: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Exception: {str(e)}")
        
        if working_endpoints:
            self.log_result("Alternative Endpoints", True, f"Found working endpoints: {working_endpoints}")
            return True
        else:
            self.log_result("Alternative Endpoints", False, "No working subscription checkout endpoints found")
            return False

    def run_bug_investigation(self):
        """Run the complete bug investigation"""
        print("🚨 SUBSCRIPTION CHECKOUT BUG INVESTIGATION")
        print("=" * 80)
        print(f"Target URL: {self.base_url}")
        print(f"Test User: {TEST_CREDENTIALS['email']}")
        print("=" * 80)
        
        # Step 1: Authenticate
        if not self.authenticate_user():
            print("❌ CRITICAL: Cannot proceed without authentication")
            return
        
        # Step 2: Test annual plan (the failing "Start $39 today" button)
        annual_success = self.test_annual_plan_checkout()
        
        # Step 3: Test monthly plan for comparison
        monthly_success = self.test_monthly_plan_checkout()
        
        # Step 4: Check Stripe configuration
        stripe_config_ok = self.check_stripe_configuration()
        
        # Step 5: Test alternative endpoints
        alternative_endpoints_found = self.test_alternative_endpoints()
        
        # Final Summary
        print("\n" + "=" * 80)
        print("🎯 BUG INVESTIGATION SUMMARY")
        print("=" * 80)
        
        print(f"✅ Tests Passed: {self.results['passed']}")
        print(f"❌ Tests Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n❌ ERRORS FOUND:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        # Root Cause Analysis
        print("\n🔍 ROOT CAUSE ANALYSIS:")
        
        if not annual_success and not monthly_success:
            print("❌ CRITICAL: Both annual and monthly checkout endpoints are failing")
            print("   This indicates a fundamental issue with the subscription checkout system")
            
            if stripe_config_ok:
                print("   • Stripe configuration appears OK (status endpoint works)")
                print("   • Issue is likely in the checkout endpoint implementation")
            else:
                print("   • Stripe configuration may be the root cause")
                
        elif not annual_success and monthly_success:
            print("⚠️  PARTIAL ISSUE: Annual plan failing but monthly works")
            print("   This suggests a plan-specific configuration issue")
            
        elif annual_success and not monthly_success:
            print("⚠️  PARTIAL ISSUE: Monthly plan failing but annual works")
            print("   This suggests a plan-specific configuration issue")
            
        else:
            print("✅ CHECKOUT ENDPOINTS WORKING: Both plans appear to be functional")
            print("   The user's issue may be frontend-related or intermittent")
        
        if alternative_endpoints_found:
            print("ℹ️  Alternative endpoints found - there may be multiple checkout implementations")
        
        print("\n🎯 RECOMMENDATIONS FOR MAIN AGENT:")
        
        if not annual_success:
            print("1. 🔥 HIGH PRIORITY: Fix annual plan checkout endpoint")
            print("   - Check Stripe price ID configuration for annual plan")
            print("   - Verify annual plan amount calculation")
            print("   - Test with valid Stripe API keys")
            
        if self.results['failed'] > self.results['passed']:
            print("2. 🔥 CRITICAL: Multiple subscription endpoints failing")
            print("   - Review Stripe API key configuration")
            print("   - Check for routing conflicts (422 errors)")
            print("   - Verify request parameter validation")
            
        print("3. 📊 TESTING: Re-run this test after fixes to verify resolution")
        
        print("=" * 80)

if __name__ == "__main__":
    tester = SubscriptionCheckoutBugTester()
    tester.run_bug_investigation()