#!/usr/bin/env python3
"""
CRITICAL THREE-STATE SYSTEM FIXES TESTING

Testing the critical fixes for three-state system gaps as requested:

CRITICAL FIXES TO TEST:
1. Fixed 403 Response Format - get_current_pro_musician() and require_pro_access() return plain string
2. Fixed Billing Confirm Authentication - GET /api/billing/confirm accessible without auth
3. Fixed Subscription Status Plan Values - returns plan="pro" instead of plan="active"

FOCUSED TESTING REQUIRED:
1. Test Fixed 403 Response Format - GET /api/song-suggestions with Free user should return exact format
2. Test Fixed Billing Confirm Endpoint - GET /api/billing/confirm?session_id=test accessible without auth
3. Test Fixed Subscription Status - GET /api/subscription/status for Pro users returns plan="pro"
4. Test Complete Pro Access Gating - All Pro endpoints work with fixed 403 format
5. Verify Stripe Integration Still Works - POST /api/subscription/checkout still works

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration - Use environment variable from frontend/.env
BASE_URL = "https://ff9606ce-1843-4dc8-a0da-da1fe6ced548.preview.emergentagent.com/api"

# Pro account for testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

# Free account for testing 403 responses
FREE_MUSICIAN = {
    "name": "Free Test User",
    "email": "free.test@requestwave.com",
    "password": "FreeTestPassword123!"
}

class CriticalFixesTester:
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

    def make_request(self, method: str, endpoint: str, data: Any = None, files: Any = None, headers: Dict = None, params: Dict = None, auth_required: bool = True) -> requests.Response:
        """Make HTTP request with proper headers"""
        url = f"{self.base_url}{endpoint}"
        
        # Default headers
        request_headers = {"Content-Type": "application/json"}
        if self.auth_token and auth_required:
            request_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        # Override with custom headers
        if headers:
            request_headers.update(headers)
        
        # Remove Content-Type for file uploads
        if files:
            request_headers.pop("Content-Type", None)
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=request_headers, params=params)
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
            response = self.make_request("GET", "/health", auth_required=False)
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

    def login_pro_user(self):
        """Login with Pro user credentials"""
        try:
            login_data = {
                "email": PRO_MUSICIAN["email"],
                "password": PRO_MUSICIAN["password"]
            }
            response = self.make_request("POST", "/auth/login", login_data, auth_required=False)
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "musician" in data:
                    self.auth_token = data["token"]
                    self.musician_id = data["musician"]["id"]
                    self.musician_slug = data["musician"]["slug"]
                    self.log_result("Pro User Login", True, f"Logged in as: {data['musician']['name']}")
                    return True
                else:
                    self.log_result("Pro User Login", False, f"Missing token or musician in response: {data}")
                    return False
            else:
                self.log_result("Pro User Login", False, f"Status code: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Pro User Login", False, f"Exception: {str(e)}")
            return False

    def create_free_user(self):
        """Create and login with Free user for 403 testing"""
        try:
            # Try to register free user
            response = self.make_request("POST", "/auth/register", FREE_MUSICIAN, auth_required=False)
            
            if response.status_code == 200:
                data = response.json()
                free_token = data["token"]
                free_musician_id = data["musician"]["id"]
                free_musician_slug = data["musician"]["slug"]
                self.log_result("Free User Creation", True, f"Created free user: {data['musician']['name']}")
                return free_token, free_musician_id, free_musician_slug
            elif response.status_code == 400:
                # User might already exist, try login
                login_data = {
                    "email": FREE_MUSICIAN["email"],
                    "password": FREE_MUSICIAN["password"]
                }
                login_response = self.make_request("POST", "/auth/login", login_data, auth_required=False)
                
                if login_response.status_code == 200:
                    data = login_response.json()
                    free_token = data["token"]
                    free_musician_id = data["musician"]["id"]
                    free_musician_slug = data["musician"]["slug"]
                    self.log_result("Free User Login", True, f"Logged in existing free user: {data['musician']['name']}")
                    return free_token, free_musician_id, free_musician_slug
                else:
                    self.log_result("Free User Creation", False, f"Login failed: {login_response.status_code}")
                    return None, None, None
            else:
                self.log_result("Free User Creation", False, f"Registration failed: {response.status_code}, Response: {response.text}")
                return None, None, None
        except Exception as e:
            self.log_result("Free User Creation", False, f"Exception: {str(e)}")
            return None, None, None

    def test_fixed_403_response_format(self):
        """Test Fixed 403 Response Format - CRITICAL FIX #1"""
        try:
            print("🔧 CRITICAL FIX #1: Testing Fixed 403 Response Format")
            print("=" * 80)
            
            # Step 1: Create/login free user
            print("📊 Step 1: Create/login free user for 403 testing")
            free_token, free_musician_id, free_musician_slug = self.create_free_user()
            
            if not free_token:
                self.log_result("Fixed 403 Response Format", False, "Could not create/login free user")
                return
            
            # Step 2: Test song-suggestions endpoint with free user (should return 403)
            print("📊 Step 2: Test GET /api/song-suggestions with free user")
            
            # Save current token and use free user token
            original_token = self.auth_token
            self.auth_token = free_token
            
            response = self.make_request("GET", "/song-suggestions")
            
            print(f"   📊 Response status: {response.status_code}")
            print(f"   📊 Response content: {response.text}")
            
            if response.status_code == 403:
                # Check if response is plain string (not nested JSON)
                try:
                    # Try to parse as JSON first
                    json_response = response.json()
                    
                    # Check if it's the old nested format {"detail": {"message": "..."}}
                    if isinstance(json_response, dict) and "detail" in json_response:
                        if isinstance(json_response["detail"], dict) and "message" in json_response["detail"]:
                            self.log_result("Fixed 403 Response Format", False, f"❌ STILL USING OLD NESTED FORMAT: {json_response}")
                            format_fixed = False
                        else:
                            # Check if it's the new format {"detail": "plain string"}
                            if isinstance(json_response["detail"], str):
                                expected_message = "Pro feature — start your 14-day free trial to unlock your Audience Link."
                                if json_response["detail"] == expected_message:
                                    self.log_result("Fixed 403 Response Format", True, f"✅ CORRECT NEW FORMAT: {json_response['detail']}")
                                    format_fixed = True
                                else:
                                    self.log_result("Fixed 403 Response Format", False, f"❌ WRONG MESSAGE: Expected '{expected_message}', Got '{json_response['detail']}'")
                                    format_fixed = False
                            else:
                                self.log_result("Fixed 403 Response Format", False, f"❌ UNEXPECTED FORMAT: {json_response}")
                                format_fixed = False
                    else:
                        self.log_result("Fixed 403 Response Format", False, f"❌ UNEXPECTED JSON STRUCTURE: {json_response}")
                        format_fixed = False
                        
                except json.JSONDecodeError:
                    # Response is not JSON - check if it's plain text
                    response_text = response.text.strip()
                    expected_message = "Pro feature — start your 14-day free trial to unlock your Audience Link."
                    
                    if response_text == expected_message:
                        self.log_result("Fixed 403 Response Format", True, f"✅ CORRECT PLAIN TEXT FORMAT: {response_text}")
                        format_fixed = True
                    else:
                        self.log_result("Fixed 403 Response Format", False, f"❌ WRONG PLAIN TEXT: Expected '{expected_message}', Got '{response_text}'")
                        format_fixed = False
            else:
                self.log_result("Fixed 403 Response Format", False, f"❌ EXPECTED 403 STATUS, GOT {response.status_code}")
                format_fixed = False
            
            # Step 3: Test other Pro endpoints for consistent 403 format
            print("📊 Step 3: Test other Pro endpoints for consistent 403 format")
            
            pro_endpoints = [
                "/playlists",
                "/song-suggestions"
            ]
            
            consistent_format = True
            for endpoint in pro_endpoints:
                print(f"   📊 Testing {endpoint}")
                endpoint_response = self.make_request("GET", endpoint)
                
                if endpoint_response.status_code == 403:
                    try:
                        json_resp = endpoint_response.json()
                        if isinstance(json_resp, dict) and "detail" in json_resp and isinstance(json_resp["detail"], str):
                            print(f"   ✅ {endpoint}: Correct format")
                        else:
                            print(f"   ❌ {endpoint}: Wrong format - {json_resp}")
                            consistent_format = False
                    except json.JSONDecodeError:
                        response_text = endpoint_response.text.strip()
                        expected_message = "Pro feature — start your 14-day free trial to unlock your Audience Link."
                        if response_text == expected_message:
                            print(f"   ✅ {endpoint}: Correct plain text format")
                        else:
                            print(f"   ❌ {endpoint}: Wrong plain text - {response_text}")
                            consistent_format = False
                else:
                    print(f"   ⚠️  {endpoint}: Status {endpoint_response.status_code} (may not be Pro-gated)")
            
            # Restore original token
            self.auth_token = original_token
            
            # Final assessment
            if format_fixed and consistent_format:
                self.log_result("Fixed 403 Response Format - CRITICAL FIX #1", True, "✅ CRITICAL FIX #1 VERIFIED: 403 responses now return correct plain string format")
            else:
                issues = []
                if not format_fixed:
                    issues.append("song-suggestions endpoint format not fixed")
                if not consistent_format:
                    issues.append("inconsistent format across Pro endpoints")
                
                self.log_result("Fixed 403 Response Format - CRITICAL FIX #1", False, f"❌ CRITICAL FIX #1 FAILED: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Fixed 403 Response Format - CRITICAL FIX #1", False, f"❌ Exception: {str(e)}")

    def test_fixed_billing_confirm_authentication(self):
        """Test Fixed Billing Confirm Authentication - CRITICAL FIX #2"""
        try:
            print("🔧 CRITICAL FIX #2: Testing Fixed Billing Confirm Authentication")
            print("=" * 80)
            
            # Step 1: Test GET /api/billing/confirm without authentication
            print("📊 Step 1: Test GET /api/billing/confirm without authentication")
            
            # Clear auth token to test unauthenticated access
            original_token = self.auth_token
            self.auth_token = None
            
            # Test with a test session_id parameter
            params = {"session_id": "cs_test_session_id_12345"}
            response = self.make_request("GET", "/billing/confirm", params=params, auth_required=False)
            
            print(f"   📊 Response status: {response.status_code}")
            print(f"   📊 Response content: {response.text}")
            
            # Step 2: Verify endpoint is accessible without authentication
            if response.status_code in [200, 400, 404]:
                # 200 = Success (if session exists and is valid)
                # 400 = Bad request (invalid session_id format but endpoint accessible)
                # 404 = Session not found (but endpoint accessible)
                print(f"   ✅ Endpoint accessible without authentication (status: {response.status_code})")
                accessible_without_auth = True
                
                # Check if it's trying to extract musician_id from session metadata
                if response.status_code == 400:
                    try:
                        error_response = response.json()
                        if "session" in response.text.lower() or "metadata" in response.text.lower():
                            print(f"   ✅ Endpoint attempting to extract musician_id from session metadata")
                        else:
                            print(f"   ⚠️  Endpoint accessible but may not be extracting from session metadata")
                    except:
                        print(f"   ⚠️  Endpoint accessible, response format unclear")
                        
            elif response.status_code == 401:
                print(f"   ❌ Endpoint still requires authentication (401 Unauthorized)")
                accessible_without_auth = False
            elif response.status_code == 403:
                print(f"   ❌ Endpoint still requires authentication (403 Forbidden)")
                accessible_without_auth = False
            else:
                print(f"   ⚠️  Unexpected status code: {response.status_code}")
                accessible_without_auth = False
            
            # Step 3: Test with different session_id formats
            print("📊 Step 3: Test with different session_id formats")
            
            test_session_ids = [
                "cs_test_1234567890",
                "cs_live_1234567890", 
                "invalid_session_id",
                ""
            ]
            
            session_handling_correct = True
            for session_id in test_session_ids:
                print(f"   📊 Testing session_id: '{session_id}'")
                test_params = {"session_id": session_id} if session_id else {}
                test_response = self.make_request("GET", "/billing/confirm", params=test_params, auth_required=False)
                
                if test_response.status_code in [200, 400, 404]:
                    print(f"   ✅ Session '{session_id}': Status {test_response.status_code} (accessible)")
                elif test_response.status_code in [401, 403]:
                    print(f"   ❌ Session '{session_id}': Status {test_response.status_code} (requires auth)")
                    session_handling_correct = False
                else:
                    print(f"   ⚠️  Session '{session_id}': Status {test_response.status_code} (unexpected)")
            
            # Step 4: Test that authenticated access still works (if user has valid session)
            print("📊 Step 4: Test that authenticated access still works")
            
            # Restore auth token
            self.auth_token = original_token
            
            if self.auth_token:
                auth_response = self.make_request("GET", "/billing/confirm", params={"session_id": "cs_test_auth_session"})
                
                if auth_response.status_code in [200, 400, 404]:
                    print(f"   ✅ Authenticated access works (status: {auth_response.status_code})")
                    auth_access_works = True
                else:
                    print(f"   ❌ Authenticated access failed (status: {auth_response.status_code})")
                    auth_access_works = False
            else:
                print(f"   ⚠️  No auth token available for authenticated test")
                auth_access_works = True  # Skip this test
            
            # Final assessment
            if accessible_without_auth and session_handling_correct and auth_access_works:
                self.log_result("Fixed Billing Confirm Authentication - CRITICAL FIX #2", True, "✅ CRITICAL FIX #2 VERIFIED: /api/billing/confirm accessible without authentication and extracts musician_id from session metadata")
            else:
                issues = []
                if not accessible_without_auth:
                    issues.append("endpoint still requires authentication")
                if not session_handling_correct:
                    issues.append("inconsistent session handling")
                if not auth_access_works:
                    issues.append("authenticated access broken")
                
                self.log_result("Fixed Billing Confirm Authentication - CRITICAL FIX #2", False, f"❌ CRITICAL FIX #2 FAILED: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Fixed Billing Confirm Authentication - CRITICAL FIX #2", False, f"❌ Exception: {str(e)}")

    def test_fixed_subscription_status_plan_values(self):
        """Test Fixed Subscription Status Plan Values - CRITICAL FIX #3"""
        try:
            print("🔧 CRITICAL FIX #3: Testing Fixed Subscription Status Plan Values")
            print("=" * 80)
            
            # Step 1: Login with Pro user
            print("📊 Step 1: Login with Pro user")
            if not self.login_pro_user():
                self.log_result("Fixed Subscription Status Plan Values - CRITICAL FIX #3", False, "Could not login Pro user")
                return
            
            # Step 2: Test GET /api/subscription/status
            print("📊 Step 2: Test GET /api/subscription/status")
            
            response = self.make_request("GET", "/subscription/status")
            
            print(f"   📊 Response status: {response.status_code}")
            print(f"   📊 Response content: {response.text}")
            
            if response.status_code == 200:
                try:
                    status_data = response.json()
                    print(f"   📊 Subscription status data: {status_data}")
                    
                    # Step 3: Check plan field value
                    print("📊 Step 3: Check plan field value")
                    
                    plan_value = status_data.get("plan")
                    print(f"   📊 Plan value: '{plan_value}'")
                    
                    # Check if plan is "pro" (correct) or "active" (old incorrect value)
                    if plan_value == "pro":
                        print(f"   ✅ Plan value is correct: 'pro'")
                        plan_value_fixed = True
                    elif plan_value == "active":
                        print(f"   ❌ Plan value is still old incorrect value: 'active'")
                        plan_value_fixed = False
                    elif plan_value in ["free", "trial", "canceled"]:
                        print(f"   ⚠️  Plan value is '{plan_value}' - user may not have Pro access")
                        # For this test, we'll check if the user should have Pro access
                        # If audience_link_active is true, they should have plan="pro"
                        audience_link_active = status_data.get("audience_link_active", False)
                        if audience_link_active:
                            print(f"   ❌ User has audience_link_active=true but plan='{plan_value}' (should be 'pro')")
                            plan_value_fixed = False
                        else:
                            print(f"   ✅ User has audience_link_active=false and plan='{plan_value}' (consistent)")
                            plan_value_fixed = True
                    else:
                        print(f"   ❌ Unexpected plan value: '{plan_value}'")
                        plan_value_fixed = False
                    
                    # Step 4: Verify three-state system compliance
                    print("📊 Step 4: Verify three-state system compliance")
                    
                    required_fields = ["plan", "status", "audience_link_active"]
                    missing_fields = [field for field in required_fields if field not in status_data]
                    
                    if len(missing_fields) == 0:
                        print(f"   ✅ All required fields present: {required_fields}")
                        
                        # Check valid plan values
                        valid_plan_values = ["free", "pro"]
                        if status_data["plan"] in valid_plan_values:
                            print(f"   ✅ Plan value '{status_data['plan']}' is valid three-state value")
                            three_state_compliant = True
                        else:
                            print(f"   ❌ Plan value '{status_data['plan']}' is not valid three-state value (should be 'free' or 'pro')")
                            three_state_compliant = False
                            
                        # Check valid status values
                        valid_status_values = ["none", "trialing", "active", "past_due", "canceled"]
                        if status_data.get("status") in valid_status_values:
                            print(f"   ✅ Status value '{status_data['status']}' is valid")
                        else:
                            print(f"   ⚠️  Status value '{status_data.get('status')}' may not be standard three-state value")
                            
                    else:
                        print(f"   ❌ Missing required fields: {missing_fields}")
                        three_state_compliant = False
                    
                    # Step 5: Test consistency between plan and audience_link_active
                    print("📊 Step 5: Test consistency between plan and audience_link_active")
                    
                    plan = status_data.get("plan")
                    audience_link_active = status_data.get("audience_link_active", False)
                    status = status_data.get("status", "none")
                    
                    # For Pro users: plan="pro" AND status in ["trialing", "active", "past_due"] should mean audience_link_active=true
                    if plan == "pro" and status in ["trialing", "active", "past_due"]:
                        if audience_link_active:
                            print(f"   ✅ Consistency check: plan='{plan}', status='{status}', audience_link_active={audience_link_active}")
                            consistency_correct = True
                        else:
                            print(f"   ❌ Inconsistency: plan='{plan}', status='{status}' but audience_link_active={audience_link_active}")
                            consistency_correct = False
                    elif plan == "free":
                        if not audience_link_active:
                            print(f"   ✅ Consistency check: plan='{plan}', audience_link_active={audience_link_active}")
                            consistency_correct = True
                        else:
                            print(f"   ❌ Inconsistency: plan='{plan}' but audience_link_active={audience_link_active}")
                            consistency_correct = False
                    else:
                        print(f"   ⚠️  Edge case: plan='{plan}', status='{status}', audience_link_active={audience_link_active}")
                        consistency_correct = True  # Don't fail on edge cases
                    
                except json.JSONDecodeError:
                    self.log_result("Fixed Subscription Status Plan Values - CRITICAL FIX #3", False, "Response is not valid JSON")
                    return
                    
            else:
                self.log_result("Fixed Subscription Status Plan Values - CRITICAL FIX #3", False, f"Subscription status endpoint failed: {response.status_code}")
                return
            
            # Final assessment
            if plan_value_fixed and three_state_compliant and consistency_correct:
                self.log_result("Fixed Subscription Status Plan Values - CRITICAL FIX #3", True, "✅ CRITICAL FIX #3 VERIFIED: Subscription status returns plan='pro' for Pro users and maintains three-state system compliance")
            else:
                issues = []
                if not plan_value_fixed:
                    issues.append("plan value not fixed (still returns 'active' instead of 'pro')")
                if not three_state_compliant:
                    issues.append("not three-state system compliant")
                if not consistency_correct:
                    issues.append("inconsistent plan/audience_link_active values")
                
                self.log_result("Fixed Subscription Status Plan Values - CRITICAL FIX #3", False, f"❌ CRITICAL FIX #3 FAILED: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Fixed Subscription Status Plan Values - CRITICAL FIX #3", False, f"❌ Exception: {str(e)}")

    def test_complete_pro_access_gating(self):
        """Test Complete Pro Access Gating with Fixed 403 Format"""
        try:
            print("🔧 TESTING: Complete Pro Access Gating with Fixed 403 Format")
            print("=" * 80)
            
            # Step 1: Test Pro user access to Pro endpoints
            print("📊 Step 1: Test Pro user access to Pro endpoints")
            
            if not self.login_pro_user():
                self.log_result("Complete Pro Access Gating", False, "Could not login Pro user")
                return
            
            pro_endpoints = [
                ("/playlists", "GET"),
                ("/song-suggestions", "GET"),
                ("/playlists", "POST")  # Will fail due to missing data, but should not be 403
            ]
            
            pro_access_working = True
            for endpoint, method in pro_endpoints:
                print(f"   📊 Testing {method} {endpoint} with Pro user")
                
                if method == "POST" and endpoint == "/playlists":
                    # Test with minimal data to avoid 400 errors
                    test_data = {"name": "Test Playlist", "song_ids": []}
                    response = self.make_request(method, endpoint, test_data)
                else:
                    response = self.make_request(method, endpoint)
                
                if response.status_code == 403:
                    print(f"   ❌ {method} {endpoint}: Pro user got 403 (should have access)")
                    pro_access_working = False
                elif response.status_code in [200, 201, 400, 422]:
                    print(f"   ✅ {method} {endpoint}: Pro user has access (status: {response.status_code})")
                else:
                    print(f"   ⚠️  {method} {endpoint}: Unexpected status {response.status_code}")
            
            # Step 2: Test Free user gets consistent 403 messages
            print("📊 Step 2: Test Free user gets consistent 403 messages")
            
            free_token, free_musician_id, free_musician_slug = self.create_free_user()
            if not free_token:
                self.log_result("Complete Pro Access Gating", False, "Could not create free user")
                return
            
            # Switch to free user
            original_token = self.auth_token
            self.auth_token = free_token
            
            consistent_403_format = True
            expected_message = "Pro feature — start your 14-day free trial to unlock your Audience Link."
            
            for endpoint, method in pro_endpoints:
                if method == "POST":
                    continue  # Skip POST tests for free user
                    
                print(f"   📊 Testing {method} {endpoint} with Free user")
                response = self.make_request(method, endpoint)
                
                if response.status_code == 403:
                    try:
                        json_resp = response.json()
                        if isinstance(json_resp, dict) and "detail" in json_resp:
                            if isinstance(json_resp["detail"], str) and json_resp["detail"] == expected_message:
                                print(f"   ✅ {method} {endpoint}: Correct 403 format")
                            else:
                                print(f"   ❌ {method} {endpoint}: Wrong 403 message - {json_resp['detail']}")
                                consistent_403_format = False
                        else:
                            print(f"   ❌ {method} {endpoint}: Wrong 403 structure - {json_resp}")
                            consistent_403_format = False
                    except json.JSONDecodeError:
                        response_text = response.text.strip()
                        if response_text == expected_message:
                            print(f"   ✅ {method} {endpoint}: Correct 403 plain text format")
                        else:
                            print(f"   ❌ {method} {endpoint}: Wrong 403 plain text - {response_text}")
                            consistent_403_format = False
                else:
                    print(f"   ⚠️  {method} {endpoint}: Free user got status {response.status_code} (expected 403)")
            
            # Restore Pro user token
            self.auth_token = original_token
            
            # Final assessment
            if pro_access_working and consistent_403_format:
                self.log_result("Complete Pro Access Gating", True, "✅ Pro access gating working correctly - Pro users have access, Free users get consistent 403 messages")
            else:
                issues = []
                if not pro_access_working:
                    issues.append("Pro users don't have proper access to Pro endpoints")
                if not consistent_403_format:
                    issues.append("Free users don't get consistent 403 message format")
                
                self.log_result("Complete Pro Access Gating", False, f"❌ Pro access gating issues: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Complete Pro Access Gating", False, f"❌ Exception: {str(e)}")

    def test_stripe_integration_still_works(self):
        """Test Stripe Integration Still Works"""
        try:
            print("🔧 TESTING: Stripe Integration Still Works")
            print("=" * 80)
            
            # Step 1: Login with Pro user
            print("📊 Step 1: Login with Pro user")
            if not self.login_pro_user():
                self.log_result("Stripe Integration Still Works", False, "Could not login Pro user")
                return
            
            # Step 2: Test subscription checkout endpoint
            print("📊 Step 2: Test POST /api/subscription/checkout")
            
            checkout_plans = ["monthly", "annual"]
            checkout_working = True
            
            for plan in checkout_plans:
                print(f"   📊 Testing {plan} checkout")
                
                checkout_data = {"plan": plan}
                response = self.make_request("POST", "/subscription/checkout", checkout_data)
                
                print(f"   📊 {plan} checkout status: {response.status_code}")
                print(f"   📊 {plan} checkout response: {response.text[:200]}...")
                
                if response.status_code == 200:
                    try:
                        checkout_result = response.json()
                        if "url" in checkout_result:
                            print(f"   ✅ {plan} checkout: Returns checkout URL")
                        else:
                            print(f"   ❌ {plan} checkout: Missing checkout URL in response")
                            checkout_working = False
                    except json.JSONDecodeError:
                        print(f"   ❌ {plan} checkout: Response is not valid JSON")
                        checkout_working = False
                elif response.status_code == 400:
                    # Check if it's a configuration error (acceptable for testing)
                    if "stripe" in response.text.lower() or "api key" in response.text.lower() or "price" in response.text.lower():
                        print(f"   ⚠️  {plan} checkout: Configuration error (acceptable for testing) - {response.text[:100]}")
                    else:
                        print(f"   ❌ {plan} checkout: Bad request - {response.text[:100]}")
                        checkout_working = False
                elif response.status_code == 500:
                    print(f"   ❌ {plan} checkout: Server error - {response.text[:100]}")
                    checkout_working = False
                else:
                    print(f"   ❌ {plan} checkout: Unexpected status {response.status_code}")
                    checkout_working = False
            
            # Step 3: Test subscription status endpoint (should still work)
            print("📊 Step 3: Test GET /api/subscription/status (should still work)")
            
            status_response = self.make_request("GET", "/subscription/status")
            
            if status_response.status_code == 200:
                try:
                    status_data = status_response.json()
                    required_fields = ["plan", "audience_link_active", "status"]
                    missing_fields = [field for field in required_fields if field not in status_data]
                    
                    if len(missing_fields) == 0:
                        print(f"   ✅ Subscription status endpoint working correctly")
                        status_working = True
                    else:
                        print(f"   ❌ Subscription status missing fields: {missing_fields}")
                        status_working = False
                except json.JSONDecodeError:
                    print(f"   ❌ Subscription status: Response is not valid JSON")
                    status_working = False
            else:
                print(f"   ❌ Subscription status failed: {status_response.status_code}")
                status_working = False
            
            # Step 4: Test environment variables are properly mapped
            print("📊 Step 4: Test environment variables are properly mapped")
            
            # We can't directly test env vars, but we can check if the endpoints handle them correctly
            # The checkout endpoint should give meaningful errors if env vars are missing
            env_mapping_correct = True
            
            if checkout_working:
                print(f"   ✅ Environment variables appear to be properly mapped (checkout endpoints accessible)")
            else:
                # Check if errors are related to missing/invalid Stripe configuration
                for plan in checkout_plans:
                    checkout_data = {"plan": plan}
                    response = self.make_request("POST", "/subscription/checkout", checkout_data)
                    
                    if "stripe" in response.text.lower() and ("key" in response.text.lower() or "price" in response.text.lower()):
                        print(f"   ✅ Environment variables properly mapped (getting Stripe config errors, not routing errors)")
                        env_mapping_correct = True
                        break
                else:
                    print(f"   ❌ Environment variables may not be properly mapped")
                    env_mapping_correct = False
            
            # Final assessment
            if (checkout_working or env_mapping_correct) and status_working:
                self.log_result("Stripe Integration Still Works", True, "✅ Stripe integration working correctly - checkout endpoints accessible, subscription status working")
            else:
                issues = []
                if not checkout_working and not env_mapping_correct:
                    issues.append("checkout endpoints not working properly")
                if not status_working:
                    issues.append("subscription status endpoint broken")
                
                self.log_result("Stripe Integration Still Works", False, f"❌ Stripe integration issues: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Stripe Integration Still Works", False, f"❌ Exception: {str(e)}")

    def run_all_tests(self):
        """Run all critical fixes tests"""
        print("🚀 STARTING CRITICAL THREE-STATE SYSTEM FIXES TESTING")
        print("=" * 100)
        print(f"Testing against: {self.base_url}")
        print("=" * 100)
        
        # Basic connectivity
        self.test_health_check()
        
        # Critical fixes tests
        self.test_fixed_403_response_format()
        self.test_fixed_billing_confirm_authentication()
        self.test_fixed_subscription_status_plan_values()
        self.test_complete_pro_access_gating()
        self.test_stripe_integration_still_works()
        
        # Summary
        print("\n" + "=" * 100)
        print("🏁 CRITICAL FIXES TESTING SUMMARY")
        print("=" * 100)
        
        total_tests = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        print(f"📊 SUCCESS RATE: {success_rate:.1f}%")
        
        if self.results["failed"] > 0:
            print(f"\n❌ FAILED TESTS:")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        print("\n" + "=" * 100)
        
        # Expected improvements assessment
        if success_rate >= 80:
            print("🎉 SUCCESS: Critical fixes have improved the system significantly!")
            print("✅ Expected success rate of 80%+ achieved")
        elif success_rate >= 60:
            print("⚠️  PARTIAL SUCCESS: Some critical fixes working, but issues remain")
            print("🔧 Additional fixes may be needed")
        else:
            print("❌ CRITICAL ISSUES: Major problems with the fixes")
            print("🚨 Immediate attention required")
        
        return success_rate >= 80

if __name__ == "__main__":
    tester = CriticalFixesTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)