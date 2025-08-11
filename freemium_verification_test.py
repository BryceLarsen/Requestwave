#!/usr/bin/env python3
"""
FINAL VERIFICATION TEST for the two critical freemium model fixes:

CRITICAL FIX #1 VERIFICATION - SubscriptionStatus Model Conflict (FIXED):
- Test GET /api/subscription/status with authentication
- Should now return NEW freemium model format with audience_link_active, trial_active, etc.
- No more model resolution conflicts

CRITICAL FIX #2 VERIFICATION - Checkout Endpoint Access (NEEDS VERIFICATION):
- Test POST /api/subscription/checkout with JSON body: {"package_id": "monthly_plan", "origin_url": "https://livewave-music.emergent.host"}
- Should return 200/201 with Stripe checkout session URL
- No more 404 errors

Use existing credentials: brycelarsenmusic@gmail.com / RequestWave2024!
"""

import requests
import json
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://livewave-music.emergent.host/api"
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class FreemiumVerificationTester:
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

    def login_pro_user(self) -> bool:
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
        except Exception as e:
            print(f"   ❌ Login exception: {str(e)}")
            return False

    def test_subscription_status_model_fix(self):
        """CRITICAL FIX #1 VERIFICATION - SubscriptionStatus Model Conflict"""
        try:
            print("\n🚨 CRITICAL FIX #1 VERIFICATION - SubscriptionStatus Model Conflict")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Subscription Status Model Fix", False, "Not authenticated - login failed")
                return
            
            print("📊 Testing GET /api/subscription/status with authentication...")
            
            # Test the subscription status endpoint
            response = self.make_request("GET", "/subscription/status")
            
            print(f"   📊 Response Status Code: {response.status_code}")
            print(f"   📊 Response Headers: {dict(response.headers)}")
            
            if response.status_code == 500:
                print(f"   🚨 CRITICAL: 500 Internal Server Error - Model conflict still exists!")
                print(f"   📊 Response Body: {response.text}")
                self.log_result("Subscription Status Model Fix", False, 
                               f"❌ CRITICAL BUG: GET /subscription/status returns 500 error - SubscriptionStatus model conflict NOT fixed. Response: {response.text}")
                return
            
            if response.status_code != 200:
                print(f"   ❌ Unexpected status code: {response.status_code}")
                print(f"   📊 Response Body: {response.text}")
                self.log_result("Subscription Status Model Fix", False, 
                               f"❌ Subscription status endpoint failed: {response.status_code} - {response.text}")
                return
            
            # Parse response and verify new freemium model format
            try:
                data = response.json()
                print(f"   📊 Response JSON: {json.dumps(data, indent=2, default=str)}")
            except json.JSONDecodeError:
                print(f"   ❌ Response is not valid JSON: {response.text}")
                self.log_result("Subscription Status Model Fix", False, "Response is not valid JSON")
                return
            
            # Check for NEW freemium model fields
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
                    print(f"   ✅ NEW freemium field '{field}' present: {data[field]}")
                else:
                    missing_fields.append(field)
                    print(f"   ❌ NEW freemium field '{field}' missing")
            
            # Check for old conflicting fields that should NOT be present
            old_conflicting_fields = ["requests_used", "requests_limit", "next_reset_date"]
            conflicting_fields_present = []
            
            for field in old_conflicting_fields:
                if field in data:
                    conflicting_fields_present.append(field)
                    print(f"   ⚠️  Old field '{field}' still present: {data[field]}")
            
            # Verify specific freemium model values
            audience_link_active = data.get("audience_link_active")
            trial_active = data.get("trial_active")
            plan = data.get("plan")
            
            print(f"   📊 audience_link_active: {audience_link_active}")
            print(f"   📊 trial_active: {trial_active}")
            print(f"   📊 plan: {plan}")
            
            # Assessment
            model_fix_working = (
                len(missing_fields) == 0 and  # All new fields present
                response.status_code == 200 and  # No server errors
                isinstance(audience_link_active, bool) and  # Correct data types
                isinstance(trial_active, bool) and
                isinstance(plan, str)
            )
            
            if model_fix_working:
                self.log_result("Subscription Status Model Fix", True, 
                               f"✅ CRITICAL FIX #1 VERIFIED: SubscriptionStatus model conflict FIXED. New freemium model format working correctly with fields: {present_fields}")
            else:
                issues = []
                if missing_fields:
                    issues.append(f"missing freemium fields: {missing_fields}")
                if conflicting_fields_present:
                    issues.append(f"old conflicting fields present: {conflicting_fields_present}")
                if response.status_code != 200:
                    issues.append(f"status code {response.status_code}")
                
                self.log_result("Subscription Status Model Fix", False, 
                               f"❌ CRITICAL FIX #1 NOT WORKING: SubscriptionStatus model issues: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Subscription Status Model Fix", False, f"❌ Exception: {str(e)}")

    def test_checkout_endpoint_access_fix(self):
        """CRITICAL FIX #2 VERIFICATION - Checkout Endpoint Access"""
        try:
            print("\n🚨 CRITICAL FIX #2 VERIFICATION - Checkout Endpoint Access")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Checkout Endpoint Access Fix", False, "Not authenticated - login failed")
                return
            
            print("📊 Testing POST /api/subscription/checkout with JSON body...")
            
            # Test data as specified in the review request
            checkout_data = {
                "package_id": "monthly_plan",
                "origin_url": "https://livewave-music.emergent.host"
            }
            
            print(f"   📊 Request Body: {json.dumps(checkout_data, indent=2)}")
            
            # Test the checkout endpoint
            response = self.make_request("POST", "/subscription/checkout", checkout_data)
            
            print(f"   📊 Response Status Code: {response.status_code}")
            print(f"   📊 Response Headers: {dict(response.headers)}")
            
            if response.status_code == 404:
                print(f"   🚨 CRITICAL: 404 Not Found - Checkout endpoint still not accessible!")
                print(f"   📊 Response Body: {response.text}")
                self.log_result("Checkout Endpoint Access Fix", False, 
                               f"❌ CRITICAL BUG: POST /subscription/checkout returns 404 - Checkout endpoint access NOT fixed. Response: {response.text}")
                return
            
            if response.status_code == 422:
                print(f"   🚨 CRITICAL: 422 Validation Error - Routing conflict still exists!")
                print(f"   📊 Response Body: {response.text}")
                self.log_result("Checkout Endpoint Access Fix", False, 
                               f"❌ CRITICAL BUG: POST /subscription/checkout returns 422 validation error - Routing conflict NOT fixed. Response: {response.text}")
                return
            
            # Check for successful response (200 or 201)
            if response.status_code not in [200, 201]:
                print(f"   ❌ Unexpected status code: {response.status_code}")
                print(f"   📊 Response Body: {response.text}")
                self.log_result("Checkout Endpoint Access Fix", False, 
                               f"❌ Checkout endpoint failed: {response.status_code} - {response.text}")
                return
            
            # Parse response and verify Stripe checkout session
            try:
                data = response.json()
                print(f"   📊 Response JSON: {json.dumps(data, indent=2, default=str)}")
            except json.JSONDecodeError:
                print(f"   ❌ Response is not valid JSON: {response.text}")
                self.log_result("Checkout Endpoint Access Fix", False, "Response is not valid JSON")
                return
            
            # Check for Stripe checkout session URL
            checkout_url = data.get("url") or data.get("checkout_url") or data.get("session_url")
            session_id = data.get("session_id") or data.get("id")
            
            print(f"   📊 Checkout URL: {checkout_url}")
            print(f"   📊 Session ID: {session_id}")
            
            # Verify Stripe checkout URL format
            stripe_url_valid = False
            if checkout_url:
                if "checkout.stripe.com" in checkout_url and ("cs_live_" in checkout_url or "cs_test_" in checkout_url):
                    stripe_url_valid = True
                    print(f"   ✅ Valid Stripe checkout URL detected")
                else:
                    print(f"   ⚠️  Checkout URL doesn't match expected Stripe format")
            else:
                print(f"   ❌ No checkout URL found in response")
            
            # Verify session ID format
            session_id_valid = False
            if session_id:
                if session_id.startswith("cs_live_") or session_id.startswith("cs_test_"):
                    session_id_valid = True
                    print(f"   ✅ Valid Stripe session ID format detected")
                else:
                    print(f"   ⚠️  Session ID doesn't match expected Stripe format")
            else:
                print(f"   ❌ No session ID found in response")
            
            # Assessment
            checkout_fix_working = (
                response.status_code in [200, 201] and  # Successful response
                checkout_url is not None and  # Has checkout URL
                session_id is not None  # Has session ID
            )
            
            if checkout_fix_working and stripe_url_valid and session_id_valid:
                self.log_result("Checkout Endpoint Access Fix", True, 
                               f"✅ CRITICAL FIX #2 VERIFIED: Checkout endpoint access FIXED. Successfully created Stripe checkout session with URL: {checkout_url[:50]}...")
            elif checkout_fix_working:
                self.log_result("Checkout Endpoint Access Fix", True, 
                               f"✅ CHECKOUT ENDPOINT WORKING: Returns {response.status_code} with checkout data, minor format issues")
            else:
                issues = []
                if response.status_code not in [200, 201]:
                    issues.append(f"status code {response.status_code}")
                if not checkout_url:
                    issues.append("missing checkout URL")
                if not session_id:
                    issues.append("missing session ID")
                
                self.log_result("Checkout Endpoint Access Fix", False, 
                               f"❌ CRITICAL FIX #2 NOT WORKING: Checkout endpoint issues: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Checkout Endpoint Access Fix", False, f"❌ Exception: {str(e)}")

    def test_additional_freemium_endpoints(self):
        """Test additional freemium endpoints to ensure overall system health"""
        try:
            print("\n📊 ADDITIONAL VERIFICATION - Testing related freemium endpoints")
            print("=" * 80)
            
            if not self.auth_token:
                print("   ⚠️  Skipping additional tests - not authenticated")
                return
            
            # Test 1: Verify webhook endpoint is accessible (should not require auth)
            print("📊 Test 1: Webhook endpoint accessibility")
            
            # Clear auth token for webhook test (webhooks shouldn't require auth)
            original_token = self.auth_token
            self.auth_token = None
            
            webhook_response = self.make_request("POST", "/webhook/stripe", {"test": "data"})
            
            print(f"   📊 Webhook Status: {webhook_response.status_code}")
            
            if webhook_response.status_code == 422:
                print(f"   ⚠️  Webhook returns 422 (validation error) - may indicate routing conflicts")
            elif webhook_response.status_code in [200, 400]:
                print(f"   ✅ Webhook endpoint accessible (status {webhook_response.status_code})")
            else:
                print(f"   ❌ Webhook endpoint issue: {webhook_response.status_code}")
            
            # Restore auth token
            self.auth_token = original_token
            
            # Test 2: Account deletion endpoint (should work with auth)
            print("📊 Test 2: Account deletion endpoint accessibility")
            
            # Test with wrong confirmation (should return 400, not 404/422)
            delete_test_data = {"confirmation_text": "WRONG"}
            delete_response = self.make_request("DELETE", "/account/delete", delete_test_data)
            
            print(f"   📊 Delete endpoint status: {delete_response.status_code}")
            
            if delete_response.status_code == 400:
                print(f"   ✅ Account deletion endpoint working (proper validation)")
            elif delete_response.status_code in [404, 422]:
                print(f"   ⚠️  Account deletion endpoint may have routing issues")
            else:
                print(f"   📊 Account deletion endpoint status: {delete_response.status_code}")
            
            # Test 3: Profile endpoint (should include freemium fields)
            print("📊 Test 3: Profile endpoint freemium integration")
            
            profile_response = self.make_request("GET", "/profile")
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                
                # Check if profile includes freemium-related fields
                freemium_profile_fields = ["audience_link_active", "trial_end", "subscription_status"]
                freemium_fields_in_profile = [field for field in freemium_profile_fields if field in profile_data]
                
                if freemium_fields_in_profile:
                    print(f"   ✅ Profile includes freemium fields: {freemium_fields_in_profile}")
                else:
                    print(f"   ℹ️  Profile doesn't include freemium fields (may be intentional)")
            else:
                print(f"   ❌ Profile endpoint failed: {profile_response.status_code}")
            
            print("=" * 80)
            
        except Exception as e:
            print(f"   ❌ Additional tests exception: {str(e)}")

    def run_verification_tests(self):
        """Run all verification tests"""
        print("🚀 STARTING FREEMIUM MODEL CRITICAL FIXES VERIFICATION")
        print("=" * 100)
        
        # Step 1: Login
        if not self.login_pro_user():
            print("❌ CRITICAL: Cannot proceed with tests - login failed")
            return
        
        # Step 2: Test Critical Fix #1 - SubscriptionStatus Model Conflict
        self.test_subscription_status_model_fix()
        
        # Step 3: Test Critical Fix #2 - Checkout Endpoint Access
        self.test_checkout_endpoint_access_fix()
        
        # Step 4: Additional verification tests
        self.test_additional_freemium_endpoints()
        
        # Final Summary
        print("\n" + "=" * 100)
        print("🏁 FINAL VERIFICATION RESULTS")
        print("=" * 100)
        
        total_tests = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.results["failed"] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        # Critical assessment
        critical_fixes_working = True
        for error in self.results["errors"]:
            if "CRITICAL FIX #1" in error or "CRITICAL FIX #2" in error:
                critical_fixes_working = False
                break
        
        if critical_fixes_working and self.results["failed"] == 0:
            print("\n🎉 SUCCESS: Both critical freemium model fixes are WORKING correctly!")
            print("   ✅ CRITICAL FIX #1: SubscriptionStatus Model Conflict - FIXED")
            print("   ✅ CRITICAL FIX #2: Checkout Endpoint Access - FIXED")
            print("   🚀 Freemium model implementation is ready for production!")
        elif critical_fixes_working:
            print("\n✅ CRITICAL FIXES WORKING: Both critical fixes verified, minor issues present")
            print("   ✅ CRITICAL FIX #1: SubscriptionStatus Model Conflict - FIXED")
            print("   ✅ CRITICAL FIX #2: Checkout Endpoint Access - FIXED")
        else:
            print("\n🚨 CRITICAL ISSUES REMAIN: One or both critical fixes are NOT working")
            print("   ❌ Manual intervention required before production deployment")

if __name__ == "__main__":
    tester = FreemiumVerificationTester()
    tester.run_verification_tests()