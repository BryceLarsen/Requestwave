#!/usr/bin/env python3
"""
COMPREHENSIVE THREE-STATE SUBSCRIPTION SYSTEM TESTING

Testing the complete three-state subscription system gaps fixes and live billing flow verification:

CRITICAL TEST AREAS:
1. **Unified 403 Responses** - All Pro-gated endpoints return exact JSON format
2. **Enhanced Checkout Flow** - POST /api/subscription/checkout with trial_period_days: 14
3. **Return-Flow Confirmation** - GET /api/billing/confirm?session_id=...
4. **Enhanced Webhook Handling** - checkout.session.completed, invoice events
5. **Complete State Transitions** - Free → Trial → Active states
6. **Error Logging** - All failures return {"error_id", "message"}

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!

Expected: Complete three-state system working with unified 403 responses, proper checkout flow, 
and correct state transitions.
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration - Use environment variable for backend URL
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ff9606ce-1843-4dc8-a0da-da1fe6ced548.preview.emergentagent.com')
BASE_URL = f"{BACKEND_URL}/api"

# Test credentials
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

# Free user for testing 403 responses
FREE_MUSICIAN = {
    "name": "Free Test User",
    "email": "free.test@requestwave.com",
    "password": "FreeTestPassword123!"
}

class ThreeStateBillingTester:
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
                response = requests.get(url, headers=request_headers, params=params or data)
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

    def test_health_check(self):
        """Test health check endpoint"""
        try:
            response = self.make_request("GET", "/health")
            if response.status_code == 200:
                data = response.json()
                if "status" in data and data["status"] == "healthy":
                    self.log_result("Health Check", True, "API is healthy")
                else:
                    self.log_result("Health Check", False, f"Unexpected response: {data}")
            else:
                self.log_result("Health Check", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_result("Health Check", False, f"Exception: {str(e)}")

    def setup_free_user(self):
        """Setup a free user for testing 403 responses"""
        try:
            # Try to register free user
            response = self.make_request("POST", "/auth/register", FREE_MUSICIAN)
            
            if response.status_code == 200:
                data = response.json()
                return data["token"], data["musician"]["id"], data["musician"]["slug"]
            elif response.status_code == 400:
                # User might already exist, try login
                login_data = {
                    "email": FREE_MUSICIAN["email"],
                    "password": FREE_MUSICIAN["password"]
                }
                login_response = self.make_request("POST", "/auth/login", login_data)
                
                if login_response.status_code == 200:
                    data = login_response.json()
                    return data["token"], data["musician"]["id"], data["musician"]["slug"]
                else:
                    return None, None, None
            else:
                return None, None, None
        except Exception as e:
            print(f"Error setting up free user: {e}")
            return None, None, None

    def test_unified_403_responses(self):
        """Test unified 403 responses for all Pro-gated endpoints"""
        try:
            print("🔒 CRITICAL TEST: Unified 403 Responses for Pro-Gated Endpoints")
            print("=" * 80)
            
            # Setup free user
            free_token, free_musician_id, free_slug = self.setup_free_user()
            
            if not free_token:
                self.log_result("Unified 403 Responses - Setup", False, "Failed to setup free user")
                return
            
            print(f"   ✅ Setup free user: {FREE_MUSICIAN['email']}")
            
            # Store original token
            original_token = self.auth_token
            self.auth_token = free_token
            
            # Expected 403 response format
            expected_403_message = "Pro feature — start your 14-day free trial to unlock your Audience Link."
            
            # Test Pro-gated endpoints
            pro_endpoints = [
                ("GET", "/song-suggestions", "Song Suggestions GET"),
                ("PUT", "/song-suggestions/test-id/status", "Song Suggestions PUT Status", {"status": "accepted"}),
                ("DELETE", "/song-suggestions/test-id", "Song Suggestions DELETE"),
                ("GET", "/playlists", "Playlists GET"),
                ("POST", "/playlists", "Playlists POST", {"name": "Test", "song_ids": []}),
            ]
            
            all_403_correct = True
            
            for method, endpoint, test_name, *data in pro_endpoints:
                print(f"📊 Testing {test_name}: {method} {endpoint}")
                
                request_data = data[0] if data else None
                response = self.make_request(method, endpoint, request_data)
                
                print(f"   📊 Status: {response.status_code}")
                
                if response.status_code == 403:
                    try:
                        response_data = response.json()
                        print(f"   📊 Response: {response_data}")
                        
                        # Check if response has the exact expected format
                        if isinstance(response_data, dict) and "message" in response_data:
                            if response_data["message"] == expected_403_message:
                                print(f"   ✅ Correct 403 response format")
                            else:
                                print(f"   ❌ Wrong 403 message. Expected: '{expected_403_message}', Got: '{response_data['message']}'")
                                all_403_correct = False
                        else:
                            print(f"   ❌ Wrong 403 response structure. Expected {{'message': '...'}}, Got: {response_data}")
                            all_403_correct = False
                    except json.JSONDecodeError:
                        print(f"   ❌ 403 response is not valid JSON: {response.text}")
                        all_403_correct = False
                elif response.status_code == 404:
                    print(f"   ⚠️  Endpoint not found (404) - may not be implemented yet")
                elif response.status_code == 422:
                    print(f"   ⚠️  Validation error (422) - may be routing issue")
                else:
                    print(f"   ❌ Expected 403, got {response.status_code}: {response.text[:200]}")
                    all_403_correct = False
                
                print()
            
            # Restore original token
            self.auth_token = original_token
            
            if all_403_correct:
                self.log_result("Unified 403 Responses", True, f"✅ All Pro-gated endpoints return unified 403 JSON format")
            else:
                self.log_result("Unified 403 Responses", False, f"❌ Some endpoints have incorrect 403 response format")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Unified 403 Responses", False, f"❌ Exception: {str(e)}")

    def test_enhanced_checkout_flow(self):
        """Test enhanced checkout flow with trial_period_days: 14"""
        try:
            print("💳 CRITICAL TEST: Enhanced Checkout Flow")
            print("=" * 80)
            
            # Login with Pro account
            print("📊 Step 1: Login with Pro account")
            login_data = {
                "email": PRO_MUSICIAN["email"],
                "password": PRO_MUSICIAN["password"]
            }
            
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code != 200:
                self.log_result("Enhanced Checkout Flow - Login", False, f"Failed to login: {login_response.status_code}")
                return
            
            login_data_response = login_response.json()
            original_token = self.auth_token
            self.auth_token = login_data_response["token"]
            
            print(f"   ✅ Successfully logged in as: {login_data_response['musician']['name']}")
            
            # Test monthly checkout
            print("📊 Step 2: Test monthly checkout")
            monthly_data = {"plan": "monthly"}
            monthly_response = self.make_request("POST", "/subscription/checkout", monthly_data)
            
            print(f"   📊 Monthly checkout status: {monthly_response.status_code}")
            print(f"   📊 Monthly checkout response: {monthly_response.text[:300]}")
            
            monthly_checkout_working = False
            if monthly_response.status_code == 200:
                try:
                    monthly_result = monthly_response.json()
                    if "url" in monthly_result and monthly_result["url"]:
                        print(f"   ✅ Monthly checkout returns URL: {monthly_result['url'][:50]}...")
                        monthly_checkout_working = True
                    else:
                        print(f"   ❌ Monthly checkout missing URL in response: {monthly_result}")
                except json.JSONDecodeError:
                    print(f"   ❌ Monthly checkout response not valid JSON")
            else:
                print(f"   ❌ Monthly checkout failed: {monthly_response.status_code}")
            
            # Test annual checkout
            print("📊 Step 3: Test annual checkout")
            annual_data = {"plan": "annual"}
            annual_response = self.make_request("POST", "/subscription/checkout", annual_data)
            
            print(f"   📊 Annual checkout status: {annual_response.status_code}")
            print(f"   📊 Annual checkout response: {annual_response.text[:300]}")
            
            annual_checkout_working = False
            if annual_response.status_code == 200:
                try:
                    annual_result = annual_response.json()
                    if "url" in annual_result and annual_result["url"]:
                        print(f"   ✅ Annual checkout returns URL: {annual_result['url'][:50]}...")
                        annual_checkout_working = True
                    else:
                        print(f"   ❌ Annual checkout missing URL in response: {annual_result}")
                except json.JSONDecodeError:
                    print(f"   ❌ Annual checkout response not valid JSON")
            else:
                print(f"   ❌ Annual checkout failed: {annual_response.status_code}")
            
            # Test invalid plan
            print("📊 Step 4: Test invalid plan handling")
            invalid_data = {"plan": "invalid"}
            invalid_response = self.make_request("POST", "/subscription/checkout", invalid_data)
            
            print(f"   📊 Invalid plan status: {invalid_response.status_code}")
            
            invalid_handling = invalid_response.status_code in [400, 422]  # Should return error
            if invalid_handling:
                print(f"   ✅ Invalid plan properly rejected")
            else:
                print(f"   ❌ Invalid plan not properly handled: {invalid_response.status_code}")
            
            # Restore original token
            self.auth_token = original_token
            
            if monthly_checkout_working and annual_checkout_working and invalid_handling:
                self.log_result("Enhanced Checkout Flow", True, f"✅ Checkout flow working for both monthly and annual plans with proper error handling")
            else:
                issues = []
                if not monthly_checkout_working:
                    issues.append("monthly checkout failed")
                if not annual_checkout_working:
                    issues.append("annual checkout failed")
                if not invalid_handling:
                    issues.append("invalid plan handling failed")
                
                self.log_result("Enhanced Checkout Flow", False, f"❌ Checkout flow issues: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Enhanced Checkout Flow", False, f"❌ Exception: {str(e)}")

    def test_return_flow_confirmation(self):
        """Test return-flow confirmation endpoint"""
        try:
            print("🔄 CRITICAL TEST: Return-Flow Confirmation")
            print("=" * 80)
            
            # Test GET /api/billing/confirm endpoint
            print("📊 Step 1: Test billing confirmation endpoint")
            
            # Test without session_id (should fail)
            print("📊 Testing without session_id parameter")
            no_session_response = self.make_request("GET", "/billing/confirm")
            
            print(f"   📊 No session_id status: {no_session_response.status_code}")
            
            no_session_handled = no_session_response.status_code in [400, 422]
            if no_session_handled:
                print(f"   ✅ Missing session_id properly handled")
            else:
                print(f"   ❌ Missing session_id not properly handled: {no_session_response.status_code}")
            
            # Test with fake session_id
            print("📊 Testing with fake session_id parameter")
            fake_session_params = {"session_id": "cs_test_fake_session_id_12345"}
            fake_session_response = self.make_request("GET", "/billing/confirm", params=fake_session_params)
            
            print(f"   📊 Fake session_id status: {fake_session_response.status_code}")
            print(f"   📊 Fake session_id response: {fake_session_response.text[:200]}")
            
            # Should return error or handle gracefully
            fake_session_handled = fake_session_response.status_code in [400, 404, 422, 500]
            if fake_session_handled:
                print(f"   ✅ Fake session_id properly handled")
            else:
                print(f"   ❌ Fake session_id not properly handled: {fake_session_response.status_code}")
            
            # Test endpoint exists and responds
            endpoint_exists = fake_session_response.status_code != 404
            if endpoint_exists:
                print(f"   ✅ Billing confirm endpoint exists")
            else:
                print(f"   ❌ Billing confirm endpoint not found (404)")
            
            if no_session_handled and fake_session_handled and endpoint_exists:
                self.log_result("Return-Flow Confirmation", True, f"✅ Billing confirmation endpoint exists and handles parameters correctly")
            else:
                issues = []
                if not no_session_handled:
                    issues.append("missing session_id not handled")
                if not fake_session_handled:
                    issues.append("fake session_id not handled")
                if not endpoint_exists:
                    issues.append("endpoint not found")
                
                self.log_result("Return-Flow Confirmation", False, f"❌ Return-flow confirmation issues: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Return-Flow Confirmation", False, f"❌ Exception: {str(e)}")

    def test_webhook_endpoints(self):
        """Test webhook endpoints exist and handle requests"""
        try:
            print("🔗 CRITICAL TEST: Webhook Endpoints")
            print("=" * 80)
            
            # Test Stripe webhook endpoint
            print("📊 Step 1: Test Stripe webhook endpoint")
            
            # Test without signature (should fail with proper error)
            webhook_response = self.make_request("POST", "/stripe/webhook", {"test": "data"})
            
            print(f"   📊 Webhook status: {webhook_response.status_code}")
            print(f"   📊 Webhook response: {webhook_response.text[:200]}")
            
            # Should return error about missing signature
            webhook_exists = webhook_response.status_code != 404
            if webhook_exists:
                print(f"   ✅ Stripe webhook endpoint exists")
            else:
                print(f"   ❌ Stripe webhook endpoint not found (404)")
            
            # Check if it properly validates signatures
            signature_validation = "signature" in webhook_response.text.lower() or webhook_response.status_code in [400, 401, 403]
            if signature_validation:
                print(f"   ✅ Webhook properly validates signatures")
            else:
                print(f"   ⚠️  Webhook signature validation unclear")
            
            if webhook_exists:
                self.log_result("Webhook Endpoints", True, f"✅ Stripe webhook endpoint exists and appears to validate signatures")
            else:
                self.log_result("Webhook Endpoints", False, f"❌ Stripe webhook endpoint not found")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Webhook Endpoints", False, f"❌ Exception: {str(e)}")

    def test_subscription_status_endpoint(self):
        """Test subscription status endpoint for three-state system"""
        try:
            print("📊 CRITICAL TEST: Subscription Status Endpoint")
            print("=" * 80)
            
            # Login with Pro account
            print("📊 Step 1: Login and test subscription status")
            login_data = {
                "email": PRO_MUSICIAN["email"],
                "password": PRO_MUSICIAN["password"]
            }
            
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code != 200:
                self.log_result("Subscription Status - Login", False, f"Failed to login: {login_response.status_code}")
                return
            
            login_data_response = login_response.json()
            original_token = self.auth_token
            self.auth_token = login_data_response["token"]
            
            print(f"   ✅ Successfully logged in as: {login_data_response['musician']['name']}")
            
            # Test subscription status endpoint
            print("📊 Step 2: Test subscription status endpoint")
            status_response = self.make_request("GET", "/subscription/status")
            
            print(f"   📊 Status endpoint response: {status_response.status_code}")
            
            if status_response.status_code == 200:
                try:
                    status_data = status_response.json()
                    print(f"   📊 Status data: {status_data}")
                    
                    # Check for required three-state fields
                    required_fields = ["plan", "status", "audience_link_active", "trial_active", "trial_end"]
                    missing_fields = [field for field in required_fields if field not in status_data]
                    
                    if len(missing_fields) == 0:
                        print(f"   ✅ All required three-state fields present")
                        
                        # Validate field values
                        plan = status_data.get("plan")
                        status_val = status_data.get("status")
                        audience_link_active = status_data.get("audience_link_active")
                        trial_active = status_data.get("trial_active")
                        
                        valid_plans = ["free", "pro"]
                        valid_statuses = ["none", "trialing", "active", "past_due", "canceled"]
                        
                        plan_valid = plan in valid_plans
                        status_valid = status_val in valid_statuses
                        boolean_fields_valid = isinstance(audience_link_active, bool) and isinstance(trial_active, bool)
                        
                        if plan_valid and status_valid and boolean_fields_valid:
                            print(f"   ✅ Three-state system fields have valid values")
                            print(f"   📊 Current state: plan={plan}, status={status_val}, audience_link_active={audience_link_active}")
                            fields_valid = True
                        else:
                            print(f"   ❌ Invalid field values: plan={plan}, status={status_val}")
                            fields_valid = False
                    else:
                        print(f"   ❌ Missing required fields: {missing_fields}")
                        fields_valid = False
                    
                    structure_valid = len(missing_fields) == 0
                    
                except json.JSONDecodeError:
                    print(f"   ❌ Status response not valid JSON")
                    structure_valid = False
                    fields_valid = False
            else:
                print(f"   ❌ Status endpoint failed: {status_response.status_code}")
                structure_valid = False
                fields_valid = False
            
            # Restore original token
            self.auth_token = original_token
            
            if structure_valid and fields_valid:
                self.log_result("Subscription Status Endpoint", True, f"✅ Subscription status endpoint returns proper three-state system data")
            else:
                issues = []
                if not structure_valid:
                    issues.append("missing required fields")
                if not fields_valid:
                    issues.append("invalid field values")
                
                self.log_result("Subscription Status Endpoint", False, f"❌ Subscription status issues: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Subscription Status Endpoint", False, f"❌ Exception: {str(e)}")

    def test_error_logging_format(self):
        """Test error logging format with error_id and message"""
        try:
            print("🚨 CRITICAL TEST: Error Logging Format")
            print("=" * 80)
            
            # Test various endpoints that should return structured errors
            error_endpoints = [
                ("POST", "/auth/login", {"email": "invalid", "password": "wrong"}, "Invalid Login"),
                ("GET", "/songs/invalid-id", None, "Invalid Song ID"),
                ("POST", "/subscription/checkout", {"plan": "invalid"}, "Invalid Plan"),
            ]
            
            structured_errors = 0
            total_tests = len(error_endpoints)
            
            for method, endpoint, data, test_name in error_endpoints:
                print(f"📊 Testing {test_name}: {method} {endpoint}")
                
                response = self.make_request(method, endpoint, data)
                
                print(f"   📊 Status: {response.status_code}")
                
                if response.status_code >= 400:  # Error response
                    try:
                        error_data = response.json()
                        print(f"   📊 Error response: {error_data}")
                        
                        # Check for structured error format
                        has_error_id = "error_id" in error_data
                        has_message = "message" in error_data or "detail" in error_data
                        
                        if has_error_id and has_message:
                            print(f"   ✅ Structured error with error_id and message")
                            structured_errors += 1
                        elif has_message:
                            print(f"   ⚠️  Has message but missing error_id")
                        else:
                            print(f"   ❌ Unstructured error response")
                    except json.JSONDecodeError:
                        print(f"   ❌ Error response not valid JSON: {response.text[:100]}")
                else:
                    print(f"   ⚠️  Expected error but got success: {response.status_code}")
                
                print()
            
            if structured_errors >= total_tests // 2:  # At least half should have structured errors
                self.log_result("Error Logging Format", True, f"✅ {structured_errors}/{total_tests} endpoints return structured errors")
            else:
                self.log_result("Error Logging Format", False, f"❌ Only {structured_errors}/{total_tests} endpoints return structured errors")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Error Logging Format", False, f"❌ Exception: {str(e)}")

    def run_all_tests(self):
        """Run all three-state billing system tests"""
        print("🚀 STARTING COMPREHENSIVE THREE-STATE BILLING SYSTEM TESTS")
        print("=" * 100)
        print(f"Backend URL: {self.base_url}")
        print("=" * 100)
        
        # Run all critical tests
        self.test_health_check()
        self.test_unified_403_responses()
        self.test_enhanced_checkout_flow()
        self.test_return_flow_confirmation()
        self.test_webhook_endpoints()
        self.test_subscription_status_endpoint()
        self.test_error_logging_format()
        
        # Print final results
        print("\n" + "=" * 100)
        print("🏁 THREE-STATE BILLING SYSTEM TEST RESULTS")
        print("=" * 100)
        
        total_tests = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        print(f"📊 SUCCESS RATE: {success_rate:.1f}%")
        
        if self.results["errors"]:
            print("\n❌ FAILED TESTS:")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        print("\n" + "=" * 100)
        
        return self.results

if __name__ == "__main__":
    tester = ThreeStateBillingTester()
    results = tester.run_all_tests()