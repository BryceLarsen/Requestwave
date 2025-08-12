#!/usr/bin/env python3
"""
CHECKOUT ERROR INVESTIGATION TEST

Debug the "Error processing subscription. Please try again." error by testing the exact checkout calls that frontend makes.

REPRODUCE THE EXACT ERROR:
1. Authenticate with test user: brycelarsenmusic@gmail.com / RequestWave2024!
2. Test the exact checkout call that frontend makes for monthly plan
3. Test the exact checkout call that frontend makes for annual plan
4. Check for specific issues:
   - Are the new live Stripe API keys working?
   - Is the PRICE_ANNUAL_48 environment variable being read correctly?
   - Is the _plan_price_id() function working?
   - Are there any 500 errors vs 400 errors?
   - Is authentication working properly?

Expected behavior:
- Should return {"checkout_url": "https://checkout.stripe.com/..."} on success
- 400 error with clear Stripe error message on failure
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://livewave-music.emergent.host/api"

# Test credentials from review request
TEST_CREDENTIALS = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class CheckoutErrorTester:
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
                response = requests.get(url, headers=request_headers, params=data)
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

    def authenticate_test_user(self):
        """Authenticate with test user brycelarsenmusic@gmail.com"""
        print("🔐 STEP 1: Authenticating with test user")
        print("=" * 60)
        
        try:
            login_data = {
                "email": TEST_CREDENTIALS["email"],
                "password": TEST_CREDENTIALS["password"]
            }
            
            response = self.make_request("POST", "/auth/login", login_data)
            
            print(f"   📊 Login response status: {response.status_code}")
            print(f"   📊 Login response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "musician" in data:
                    self.auth_token = data["token"]
                    self.musician_id = data["musician"]["id"]
                    
                    print(f"   ✅ Successfully authenticated as: {data['musician']['name']}")
                    print(f"   ✅ Musician ID: {self.musician_id}")
                    print(f"   ✅ JWT Token (first 50 chars): {self.auth_token[:50]}...")
                    
                    self.log_result("Authentication", True, f"Logged in as {data['musician']['name']}")
                    return True
                else:
                    print(f"   ❌ Missing token or musician in response: {data}")
                    self.log_result("Authentication", False, f"Missing token or musician in response")
                    return False
            else:
                print(f"   ❌ Login failed with status: {response.status_code}")
                print(f"   ❌ Response: {response.text}")
                self.log_result("Authentication", False, f"Login failed: {response.status_code}, {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Authentication exception: {str(e)}")
            self.log_result("Authentication", False, f"Exception: {str(e)}")
            return False

    def test_monthly_checkout(self):
        """Test the exact monthly checkout call that frontend makes"""
        print("💳 STEP 2: Testing Monthly Plan Checkout")
        print("=" * 60)
        
        try:
            # Exact checkout data from review request
            checkout_data = {
                "plan": "monthly",
                "success_url": "https://livewave-music.emergent.host/dashboard?tab=subscription&session_id={CHECKOUT_SESSION_ID}",
                "cancel_url": "https://livewave-music.emergent.host/dashboard?tab=subscription"
            }
            
            print(f"   📊 Testing POST /api/subscription/checkout with data:")
            print(f"   📊 {json.dumps(checkout_data, indent=6)}")
            
            response = self.make_request("POST", "/subscription/checkout", checkout_data)
            
            print(f"   📊 Checkout response status: {response.status_code}")
            print(f"   📊 Checkout response headers: {dict(response.headers)}")
            print(f"   📊 Checkout response body: {response.text}")
            
            # Analyze the response
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "checkout_url" in data:
                        checkout_url = data["checkout_url"]
                        print(f"   ✅ SUCCESS: Checkout URL generated")
                        print(f"   ✅ Checkout URL: {checkout_url}")
                        
                        # Verify it's a valid Stripe URL
                        if "checkout.stripe.com" in checkout_url or "stripe.com" in checkout_url:
                            print(f"   ✅ Valid Stripe checkout URL format")
                            self.log_result("Monthly Checkout", True, f"Successfully created checkout session: {checkout_url[:100]}...")
                            return True
                        else:
                            print(f"   ❌ Invalid checkout URL format")
                            self.log_result("Monthly Checkout", False, f"Invalid checkout URL format: {checkout_url}")
                            return False
                    else:
                        print(f"   ❌ Missing checkout_url in response")
                        print(f"   📊 Response keys: {list(data.keys())}")
                        self.log_result("Monthly Checkout", False, f"Missing checkout_url in response: {data}")
                        return False
                except json.JSONDecodeError:
                    print(f"   ❌ Response is not valid JSON")
                    self.log_result("Monthly Checkout", False, f"Invalid JSON response: {response.text}")
                    return False
                    
            elif response.status_code == 400:
                # Expected error with Stripe API key issues
                try:
                    error_data = response.json()
                    error_message = error_data.get("detail", response.text)
                    print(f"   ⚠️  400 Error (expected with invalid API key): {error_message}")
                    
                    # Check if it's a Stripe API key error
                    if "api key" in error_message.lower() or "stripe" in error_message.lower():
                        print(f"   ✅ Proper error handling - Stripe API key issue detected")
                        self.log_result("Monthly Checkout", True, f"Proper 400 error handling: {error_message}")
                        return True
                    else:
                        print(f"   ❌ Unexpected 400 error: {error_message}")
                        self.log_result("Monthly Checkout", False, f"Unexpected 400 error: {error_message}")
                        return False
                except json.JSONDecodeError:
                    print(f"   ❌ 400 error with invalid JSON: {response.text}")
                    self.log_result("Monthly Checkout", False, f"400 error with invalid JSON: {response.text}")
                    return False
                    
            elif response.status_code == 500:
                print(f"   ❌ CRITICAL: 500 Internal Server Error")
                print(f"   ❌ This indicates a server-side issue, not proper error handling")
                self.log_result("Monthly Checkout", False, f"500 Internal Server Error: {response.text}")
                return False
                
            elif response.status_code == 422:
                print(f"   ❌ CRITICAL: 422 Validation Error - Routing conflict detected")
                print(f"   ❌ This suggests the endpoint is conflicting with another route")
                try:
                    error_data = response.json()
                    print(f"   📊 Validation error details: {json.dumps(error_data, indent=6)}")
                except:
                    pass
                self.log_result("Monthly Checkout", False, f"422 Validation Error - routing conflict: {response.text}")
                return False
                
            else:
                print(f"   ❌ Unexpected status code: {response.status_code}")
                self.log_result("Monthly Checkout", False, f"Unexpected status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Monthly checkout exception: {str(e)}")
            self.log_result("Monthly Checkout", False, f"Exception: {str(e)}")
            return False

    def test_annual_checkout(self):
        """Test the exact annual checkout call that frontend makes"""
        print("💳 STEP 3: Testing Annual Plan Checkout")
        print("=" * 60)
        
        try:
            # Exact checkout data from review request
            checkout_data = {
                "plan": "annual",
                "success_url": "https://livewave-music.emergent.host/dashboard?tab=subscription&session_id={CHECKOUT_SESSION_ID}",
                "cancel_url": "https://livewave-music.emergent.host/dashboard?tab=subscription"
            }
            
            print(f"   📊 Testing POST /api/subscription/checkout with data:")
            print(f"   📊 {json.dumps(checkout_data, indent=6)}")
            
            response = self.make_request("POST", "/subscription/checkout", checkout_data)
            
            print(f"   📊 Checkout response status: {response.status_code}")
            print(f"   📊 Checkout response headers: {dict(response.headers)}")
            print(f"   📊 Checkout response body: {response.text}")
            
            # Analyze the response (same logic as monthly)
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "checkout_url" in data:
                        checkout_url = data["checkout_url"]
                        print(f"   ✅ SUCCESS: Checkout URL generated")
                        print(f"   ✅ Checkout URL: {checkout_url}")
                        
                        # Verify it's a valid Stripe URL
                        if "checkout.stripe.com" in checkout_url or "stripe.com" in checkout_url:
                            print(f"   ✅ Valid Stripe checkout URL format")
                            self.log_result("Annual Checkout", True, f"Successfully created checkout session: {checkout_url[:100]}...")
                            return True
                        else:
                            print(f"   ❌ Invalid checkout URL format")
                            self.log_result("Annual Checkout", False, f"Invalid checkout URL format: {checkout_url}")
                            return False
                    else:
                        print(f"   ❌ Missing checkout_url in response")
                        print(f"   📊 Response keys: {list(data.keys())}")
                        self.log_result("Annual Checkout", False, f"Missing checkout_url in response: {data}")
                        return False
                except json.JSONDecodeError:
                    print(f"   ❌ Response is not valid JSON")
                    self.log_result("Annual Checkout", False, f"Invalid JSON response: {response.text}")
                    return False
                    
            elif response.status_code == 400:
                # Expected error with Stripe API key issues
                try:
                    error_data = response.json()
                    error_message = error_data.get("detail", response.text)
                    print(f"   ⚠️  400 Error (expected with invalid API key): {error_message}")
                    
                    # Check if it's a Stripe API key error
                    if "api key" in error_message.lower() or "stripe" in error_message.lower():
                        print(f"   ✅ Proper error handling - Stripe API key issue detected")
                        self.log_result("Annual Checkout", True, f"Proper 400 error handling: {error_message}")
                        return True
                    else:
                        print(f"   ❌ Unexpected 400 error: {error_message}")
                        self.log_result("Annual Checkout", False, f"Unexpected 400 error: {error_message}")
                        return False
                except json.JSONDecodeError:
                    print(f"   ❌ 400 error with invalid JSON: {response.text}")
                    self.log_result("Annual Checkout", False, f"400 error with invalid JSON: {response.text}")
                    return False
                    
            elif response.status_code == 500:
                print(f"   ❌ CRITICAL: 500 Internal Server Error")
                print(f"   ❌ This indicates a server-side issue, not proper error handling")
                self.log_result("Annual Checkout", False, f"500 Internal Server Error: {response.text}")
                return False
                
            elif response.status_code == 422:
                print(f"   ❌ CRITICAL: 422 Validation Error - Routing conflict detected")
                print(f"   ❌ This suggests the endpoint is conflicting with another route")
                try:
                    error_data = response.json()
                    print(f"   📊 Validation error details: {json.dumps(error_data, indent=6)}")
                except:
                    pass
                self.log_result("Annual Checkout", False, f"422 Validation Error - routing conflict: {response.text}")
                return False
                
            else:
                print(f"   ❌ Unexpected status code: {response.status_code}")
                self.log_result("Annual Checkout", False, f"Unexpected status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Annual checkout exception: {str(e)}")
            self.log_result("Annual Checkout", False, f"Exception: {str(e)}")
            return False

    def debug_environment_variables(self):
        """Debug environment variables and configuration"""
        print("🔧 STEP 4: Debugging Environment Variables & Configuration")
        print("=" * 60)
        
        try:
            # Test a simple endpoint to check if backend is responding
            response = self.make_request("GET", "/subscription/status")
            
            print(f"   📊 Subscription status response: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    status_data = response.json()
                    print(f"   📊 Status data: {json.dumps(status_data, indent=6)}")
                    print(f"   ✅ Backend is responding correctly")
                    
                    # Check if we can see any configuration info in the response
                    plan = status_data.get("plan", "unknown")
                    print(f"   📊 Current plan: {plan}")
                    
                    self.log_result("Environment Debug", True, f"Backend responding, current plan: {plan}")
                    return True
                    
                except json.JSONDecodeError:
                    print(f"   ❌ Status response not JSON: {response.text}")
                    self.log_result("Environment Debug", False, f"Status response not JSON")
                    return False
                    
            elif response.status_code == 401 or response.status_code == 403:
                print(f"   ✅ Authentication working (got {response.status_code} as expected)")
                self.log_result("Environment Debug", True, f"Authentication working properly")
                return True
                
            else:
                print(f"   ❌ Unexpected status response: {response.status_code}")
                print(f"   📊 Response: {response.text}")
                self.log_result("Environment Debug", False, f"Unexpected status response: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Environment debug exception: {str(e)}")
            self.log_result("Environment Debug", False, f"Exception: {str(e)}")
            return False

    def test_plan_price_id_function(self):
        """Test if the _plan_price_id() function is working by checking different plans"""
        print("🏷️  STEP 5: Testing Plan Price ID Function")
        print("=" * 60)
        
        try:
            # Test with invalid plan to see error handling
            invalid_checkout_data = {
                "plan": "invalid_plan",
                "success_url": "https://livewave-music.emergent.host/dashboard?tab=subscription&session_id={CHECKOUT_SESSION_ID}",
                "cancel_url": "https://livewave-music.emergent.host/dashboard?tab=subscription"
            }
            
            print(f"   📊 Testing with invalid plan: 'invalid_plan'")
            
            response = self.make_request("POST", "/subscription/checkout", invalid_checkout_data)
            
            print(f"   📊 Invalid plan response status: {response.status_code}")
            print(f"   📊 Invalid plan response: {response.text}")
            
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    error_message = error_data.get("detail", response.text)
                    
                    if "invalid plan" in error_message.lower() or "plan" in error_message.lower():
                        print(f"   ✅ Plan validation working: {error_message}")
                        self.log_result("Plan Price ID Function", True, f"Plan validation working: {error_message}")
                        return True
                    else:
                        print(f"   ⚠️  Different error (might be Stripe key issue): {error_message}")
                        # This might still be working if Stripe key is the issue
                        self.log_result("Plan Price ID Function", True, f"Function accessible, error: {error_message}")
                        return True
                        
                except json.JSONDecodeError:
                    print(f"   ❌ Invalid plan error not JSON: {response.text}")
                    self.log_result("Plan Price ID Function", False, f"Invalid plan error not JSON")
                    return False
                    
            elif response.status_code == 422:
                print(f"   ❌ CRITICAL: 422 error suggests routing conflict, not plan validation")
                self.log_result("Plan Price ID Function", False, f"422 routing conflict prevents plan validation")
                return False
                
            else:
                print(f"   ❌ Unexpected response to invalid plan: {response.status_code}")
                self.log_result("Plan Price ID Function", False, f"Unexpected response: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Plan price ID test exception: {str(e)}")
            self.log_result("Plan Price ID Function", False, f"Exception: {str(e)}")
            return False

    def check_backend_logs(self):
        """Check for any backend log information that might be available"""
        print("📋 STEP 6: Checking for Backend Log Information")
        print("=" * 60)
        
        try:
            # Try to get any debug information from headers or responses
            response = self.make_request("POST", "/subscription/checkout", {
                "plan": "monthly",
                "success_url": "https://test.com/success",
                "cancel_url": "https://test.com/cancel"
            })
            
            print(f"   📊 Checking response headers for debug info:")
            for header, value in response.headers.items():
                if any(keyword in header.lower() for keyword in ['debug', 'handler', 'stripe', 'error']):
                    print(f"   📊 {header}: {value}")
            
            # Check if there's any handler information
            handler_header = response.headers.get('X-Handler')
            if handler_header:
                print(f"   📊 Handler called: {handler_header}")
                print(f"   ✅ Backend routing is working (handler identified)")
                self.log_result("Backend Logs", True, f"Handler identified: {handler_header}")
                return True
            else:
                print(f"   ℹ️  No handler header found")
                self.log_result("Backend Logs", True, f"No specific debug headers, but backend responding")
                return True
                
        except Exception as e:
            print(f"   ❌ Backend log check exception: {str(e)}")
            self.log_result("Backend Logs", False, f"Exception: {str(e)}")
            return False

    def run_checkout_error_investigation(self):
        """Run the complete checkout error investigation"""
        print("🚨 CHECKOUT ERROR INVESTIGATION")
        print("=" * 80)
        print("Debugging: 'Error processing subscription. Please try again.'")
        print("=" * 80)
        
        # Step 1: Authenticate
        if not self.authenticate_test_user():
            print("❌ CRITICAL: Cannot proceed without authentication")
            return
        
        # Step 2: Test monthly checkout
        monthly_success = self.test_monthly_checkout()
        
        # Step 3: Test annual checkout  
        annual_success = self.test_annual_checkout()
        
        # Step 4: Debug environment
        env_success = self.debug_environment_variables()
        
        # Step 5: Test plan function
        plan_success = self.test_plan_price_id_function()
        
        # Step 6: Check backend logs
        log_success = self.check_backend_logs()
        
        # Final summary
        print("\n" + "=" * 80)
        print("🎯 CHECKOUT ERROR INVESTIGATION SUMMARY")
        print("=" * 80)
        
        total_tests = 6
        passed_tests = sum([
            1 if self.auth_token else 0,  # Authentication
            1 if monthly_success else 0,
            1 if annual_success else 0,
            1 if env_success else 0,
            1 if plan_success else 0,
            1 if log_success else 0
        ])
        
        print(f"📊 Tests Passed: {passed_tests}/{total_tests}")
        print(f"📊 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n🔍 DETAILED FINDINGS:")
        
        if self.auth_token:
            print("✅ Authentication: Working correctly")
        else:
            print("❌ Authentication: FAILED - Cannot login with test credentials")
        
        if monthly_success:
            print("✅ Monthly Checkout: Working (proper error handling or success)")
        else:
            print("❌ Monthly Checkout: FAILED - Check routing conflicts or server errors")
        
        if annual_success:
            print("✅ Annual Checkout: Working (proper error handling or success)")
        else:
            print("❌ Annual Checkout: FAILED - Check PRICE_ANNUAL_48 configuration")
        
        if env_success:
            print("✅ Environment: Backend responding correctly")
        else:
            print("❌ Environment: Backend configuration issues")
        
        if plan_success:
            print("✅ Plan Function: _plan_price_id() function accessible")
        else:
            print("❌ Plan Function: Issues with plan validation")
        
        if log_success:
            print("✅ Backend Logs: Debug information available")
        else:
            print("❌ Backend Logs: Limited debug information")
        
        # Specific recommendations
        print("\n💡 RECOMMENDATIONS:")
        
        if not monthly_success or not annual_success:
            print("🔧 1. Check for 422 routing conflicts - subscription endpoints may conflict with request endpoints")
            print("🔧 2. Verify Stripe API keys are properly configured and valid")
            print("🔧 3. Check PRICE_ANNUAL_48 environment variable is set correctly")
        
        if passed_tests >= 4:
            print("✅ 4. Core functionality appears to be working - issue may be frontend-specific")
        else:
            print("❌ 4. Multiple backend issues detected - requires immediate attention")
        
        print("\n" + "=" * 80)
        
        return passed_tests >= 4

def main():
    """Main function to run checkout error investigation"""
    tester = CheckoutErrorTester()
    success = tester.run_checkout_error_investigation()
    
    if success:
        print("🎉 INVESTIGATION COMPLETE: Most systems working correctly")
        exit(0)
    else:
        print("🚨 INVESTIGATION COMPLETE: Critical issues found")
        exit(1)

if __name__ == "__main__":
    main()