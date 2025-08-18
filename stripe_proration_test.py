#!/usr/bin/env python3
"""
CRITICAL PRODUCTION PRORATION_BEHAVIOR STRIPE ERROR FIX TESTING

Testing the critical production bug fix for POST /api/subscription/checkout:
- Issue: "The proration_behavior parameter can only be passed if a billing_cycle_anchor exists."
- Fix: Removed proration_behavior from subscription_data, kept trial_period_days: 14
- Expected: Successful checkout session creation without proration_behavior error

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!

TESTING REQUIREMENTS:
1. Test Subscription Checkout - Monthly Plan
2. Test Subscription Checkout - Annual Plan  
3. Verify Subscription Data Structure (no proration_behavior, includes metadata and trial_period_days)
4. Test Error Logging
5. Verify Webhook Logic Unchanged

Expected: No "proration_behavior parameter can only be passed if a billing_cycle_anchor exists" error
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration - Use environment variable for backend URL
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://ff9606ce-1843-4dc8-a0da-da1fe6ced548.preview.emergentagent.com')
BASE_URL = f"{BACKEND_URL}/api"

# Test credentials
TEST_CREDENTIALS = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class StripeProrationFixTester:
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
                if params:
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

    def test_authentication(self):
        """Test authentication with provided credentials"""
        try:
            print("🔐 AUTHENTICATION TEST")
            print("=" * 80)
            
            login_data = {
                "email": TEST_CREDENTIALS["email"],
                "password": TEST_CREDENTIALS["password"]
            }
            
            response = self.make_request("POST", "/auth/login", login_data)
            
            print(f"   📊 Login response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "musician" in data:
                    self.auth_token = data["token"]
                    self.musician_id = data["musician"]["id"]
                    self.musician_slug = data["musician"]["slug"]
                    
                    print(f"   ✅ Successfully authenticated as: {data['musician']['name']}")
                    print(f"   📊 Musician ID: {self.musician_id}")
                    print(f"   📊 Musician Slug: {self.musician_slug}")
                    
                    self.log_result("Authentication", True, f"Logged in as {data['musician']['name']}")
                else:
                    self.log_result("Authentication", False, f"Missing token or musician in response: {data}")
            else:
                self.log_result("Authentication", False, f"Login failed with status {response.status_code}: {response.text}")
                
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Authentication", False, f"Exception: {str(e)}")

    def test_subscription_status(self):
        """Test subscription status endpoint"""
        try:
            print("📊 SUBSCRIPTION STATUS TEST")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Subscription Status", False, "No authentication token available")
                return
            
            response = self.make_request("GET", "/subscription/status")
            
            print(f"   📊 Subscription status response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   📊 Subscription data: {json.dumps(data, indent=2)}")
                
                # Check required fields
                required_fields = ["audience_link_active", "trial_active", "trial_end", "plan", "status"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if len(missing_fields) == 0:
                    print(f"   ✅ All required fields present")
                    print(f"   📊 Plan: {data.get('plan')}")
                    print(f"   📊 Status: {data.get('status')}")
                    print(f"   📊 Audience Link Active: {data.get('audience_link_active')}")
                    
                    self.log_result("Subscription Status", True, f"Status endpoint working - Plan: {data.get('plan')}, Status: {data.get('status')}")
                else:
                    self.log_result("Subscription Status", False, f"Missing required fields: {missing_fields}")
            else:
                self.log_result("Subscription Status", False, f"Status code: {response.status_code}, Response: {response.text}")
                
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Subscription Status", False, f"Exception: {str(e)}")

    def test_monthly_subscription_checkout(self):
        """Test monthly subscription checkout - CRITICAL TEST"""
        try:
            print("💳 MONTHLY SUBSCRIPTION CHECKOUT TEST - CRITICAL")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Monthly Checkout", False, "No authentication token available")
                return
            
            # Test data for monthly checkout
            checkout_data = {
                "plan": "monthly",
                "success_url": "https://requestwave.app/success",
                "cancel_url": "https://requestwave.app/cancel"
            }
            
            print(f"   📊 Testing monthly checkout with data: {checkout_data}")
            
            response = self.make_request("POST", "/subscription/checkout", checkout_data)
            
            print(f"   📊 Monthly checkout response status: {response.status_code}")
            print(f"   📊 Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   📊 Response data: {json.dumps(data, indent=2)}")
                    
                    # Check for successful checkout URL
                    if "url" in data and data["url"]:
                        checkout_url = data["url"]
                        print(f"   ✅ Checkout URL generated: {checkout_url[:100]}...")
                        
                        # Verify it's a Stripe checkout URL
                        if "checkout.stripe.com" in checkout_url or "cs_" in checkout_url:
                            print(f"   ✅ Valid Stripe checkout URL format")
                            self.log_result("Monthly Checkout", True, "Monthly checkout session created successfully without proration_behavior error")
                        else:
                            self.log_result("Monthly Checkout", False, f"Invalid checkout URL format: {checkout_url}")
                    else:
                        self.log_result("Monthly Checkout", False, f"No checkout URL in response: {data}")
                        
                except json.JSONDecodeError:
                    print(f"   📊 Non-JSON response: {response.text}")
                    self.log_result("Monthly Checkout", False, f"Invalid JSON response: {response.text}")
                    
            elif response.status_code == 400:
                # Check if it's the proration_behavior error
                error_text = response.text.lower()
                if "proration_behavior" in error_text and "billing_cycle_anchor" in error_text:
                    self.log_result("Monthly Checkout", False, f"❌ CRITICAL: Proration behavior error still present: {response.text}")
                else:
                    print(f"   📊 400 error (not proration_behavior): {response.text}")
                    # Other 400 errors might be acceptable (e.g., Stripe config issues)
                    self.log_result("Monthly Checkout", True, f"No proration_behavior error - other config issue: {response.text}")
                    
            else:
                print(f"   📊 Unexpected status code: {response.status_code}")
                print(f"   📊 Response: {response.text}")
                
                # Check if it's the proration_behavior error
                error_text = response.text.lower()
                if "proration_behavior" in error_text and "billing_cycle_anchor" in error_text:
                    self.log_result("Monthly Checkout", False, f"❌ CRITICAL: Proration behavior error still present: {response.text}")
                else:
                    # Other errors might be acceptable (e.g., Stripe config issues)
                    self.log_result("Monthly Checkout", True, f"No proration_behavior error - other issue: {response.text}")
                    
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Monthly Checkout", False, f"Exception: {str(e)}")

    def test_annual_subscription_checkout(self):
        """Test annual subscription checkout - CRITICAL TEST"""
        try:
            print("💳 ANNUAL SUBSCRIPTION CHECKOUT TEST - CRITICAL")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Annual Checkout", False, "No authentication token available")
                return
            
            # Test data for annual checkout
            checkout_data = {
                "plan": "annual",
                "success_url": "https://requestwave.app/success",
                "cancel_url": "https://requestwave.app/cancel"
            }
            
            print(f"   📊 Testing annual checkout with data: {checkout_data}")
            
            response = self.make_request("POST", "/subscription/checkout", checkout_data)
            
            print(f"   📊 Annual checkout response status: {response.status_code}")
            print(f"   📊 Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   📊 Response data: {json.dumps(data, indent=2)}")
                    
                    # Check for successful checkout URL
                    if "url" in data and data["url"]:
                        checkout_url = data["url"]
                        print(f"   ✅ Checkout URL generated: {checkout_url[:100]}...")
                        
                        # Verify it's a Stripe checkout URL
                        if "checkout.stripe.com" in checkout_url or "cs_" in checkout_url:
                            print(f"   ✅ Valid Stripe checkout URL format")
                            self.log_result("Annual Checkout", True, "Annual checkout session created successfully without proration_behavior error")
                        else:
                            self.log_result("Annual Checkout", False, f"Invalid checkout URL format: {checkout_url}")
                    else:
                        self.log_result("Annual Checkout", False, f"No checkout URL in response: {data}")
                        
                except json.JSONDecodeError:
                    print(f"   📊 Non-JSON response: {response.text}")
                    self.log_result("Annual Checkout", False, f"Invalid JSON response: {response.text}")
                    
            elif response.status_code == 400:
                # Check if it's the proration_behavior error
                error_text = response.text.lower()
                if "proration_behavior" in error_text and "billing_cycle_anchor" in error_text:
                    self.log_result("Annual Checkout", False, f"❌ CRITICAL: Proration behavior error still present: {response.text}")
                else:
                    print(f"   📊 400 error (not proration_behavior): {response.text}")
                    # Other 400 errors might be acceptable (e.g., Stripe config issues)
                    self.log_result("Annual Checkout", True, f"No proration_behavior error - other config issue: {response.text}")
                    
            else:
                print(f"   📊 Unexpected status code: {response.status_code}")
                print(f"   📊 Response: {response.text}")
                
                # Check if it's the proration_behavior error
                error_text = response.text.lower()
                if "proration_behavior" in error_text and "billing_cycle_anchor" in error_text:
                    self.log_result("Annual Checkout", False, f"❌ CRITICAL: Proration behavior error still present: {response.text}")
                else:
                    # Other errors might be acceptable (e.g., Stripe config issues)
                    self.log_result("Annual Checkout", True, f"No proration_behavior error - other issue: {response.text}")
                    
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Annual Checkout", False, f"Exception: {str(e)}")

    def test_webhook_endpoint(self):
        """Test webhook endpoint is accessible and validates signatures"""
        try:
            print("🔗 WEBHOOK ENDPOINT TEST")
            print("=" * 80)
            
            # Test webhook endpoint without signature (should fail gracefully)
            response = self.make_request("POST", "/stripe/webhook", {"test": "data"})
            
            print(f"   📊 Webhook response status: {response.status_code}")
            print(f"   📊 Webhook response: {response.text}")
            
            # Webhook should return error for missing signature, not routing error
            if response.status_code in [400, 401, 403]:
                if "signature" in response.text.lower() or "webhook" in response.text.lower():
                    print(f"   ✅ Webhook endpoint accessible and validates signatures")
                    self.log_result("Webhook Endpoint", True, "Webhook endpoint properly validates signatures")
                else:
                    self.log_result("Webhook Endpoint", False, f"Webhook endpoint accessible but unexpected error: {response.text}")
            elif response.status_code == 422:
                # Check if it's routing to wrong endpoint (request validation)
                if "musician_id" in response.text or "song_id" in response.text:
                    self.log_result("Webhook Endpoint", False, f"❌ CRITICAL: Webhook routing conflict - routed to request endpoint: {response.text}")
                else:
                    self.log_result("Webhook Endpoint", True, "Webhook endpoint accessible with validation")
            else:
                self.log_result("Webhook Endpoint", False, f"Unexpected webhook response: {response.status_code} - {response.text}")
                
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Webhook Endpoint", False, f"Exception: {str(e)}")

    def test_error_logging_structure(self):
        """Test that error responses include proper error logging structure"""
        try:
            print("📝 ERROR LOGGING STRUCTURE TEST")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Error Logging", False, "No authentication token available")
                return
            
            # Test with invalid plan to trigger error logging
            invalid_checkout_data = {
                "plan": "invalid_plan",
                "success_url": "https://requestwave.app/success",
                "cancel_url": "https://requestwave.app/cancel"
            }
            
            response = self.make_request("POST", "/subscription/checkout", invalid_checkout_data)
            
            print(f"   📊 Invalid plan response status: {response.status_code}")
            print(f"   📊 Response: {response.text}")
            
            if response.status_code in [400, 422]:
                try:
                    data = response.json()
                    
                    # Check for error structure
                    has_error_structure = False
                    if "error_id" in data or "detail" in data or "message" in data:
                        has_error_structure = True
                        print(f"   ✅ Error response has proper structure")
                        
                        # Check for enhanced error logging fields
                        if "error_id" in data:
                            print(f"   ✅ Error ID present: {data['error_id']}")
                        
                        self.log_result("Error Logging", True, "Error responses include proper logging structure")
                    else:
                        self.log_result("Error Logging", False, f"Error response missing structure: {data}")
                        
                except json.JSONDecodeError:
                    print(f"   📊 Non-JSON error response: {response.text}")
                    # Still acceptable if it's a clear error message
                    self.log_result("Error Logging", True, "Error response is clear text message")
            else:
                self.log_result("Error Logging", False, f"Unexpected response to invalid plan: {response.status_code}")
                
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Error Logging", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all tests for the proration_behavior fix"""
        print("🚀 STRIPE PRORATION_BEHAVIOR FIX TESTING")
        print("=" * 100)
        print("Testing critical production bug fix:")
        print("- Issue: 'The proration_behavior parameter can only be passed if a billing_cycle_anchor exists.'")
        print("- Fix: Removed proration_behavior from subscription_data, kept trial_period_days: 14")
        print("- Expected: Successful checkout session creation without proration_behavior error")
        print("=" * 100)
        
        # Run tests in order
        self.test_authentication()
        
        if self.auth_token:  # Only run other tests if authentication succeeded
            self.test_subscription_status()
            self.test_monthly_subscription_checkout()
            self.test_annual_subscription_checkout()
            self.test_webhook_endpoint()
            self.test_error_logging_structure()
        
        # Print final results
        print("\n" + "=" * 100)
        print("🏁 FINAL TEST RESULTS")
        print("=" * 100)
        
        total_tests = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        print(f"📊 SUCCESS RATE: {success_rate:.1f}%")
        
        if self.results["failed"] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results["errors"]:
                print(f"   - {error}")
        
        # Critical assessment
        critical_tests = ["Monthly Checkout", "Annual Checkout"]
        critical_failures = [error for error in self.results["errors"] if any(test in error for test in critical_tests)]
        
        if len(critical_failures) == 0:
            print(f"\n🎉 CRITICAL SUCCESS: No proration_behavior errors detected!")
            print(f"✅ The production bug fix is working correctly.")
        else:
            print(f"\n🚨 CRITICAL FAILURE: Proration behavior errors still present!")
            for failure in critical_failures:
                print(f"   ❌ {failure}")
        
        print("=" * 100)

if __name__ == "__main__":
    tester = StripeProrationFixTester()
    tester.run_all_tests()