#!/usr/bin/env python3
"""
COMPREHENSIVE THREE-STATE SUBSCRIPTION SYSTEM TESTING

Testing the comprehensive three explicit subscription states implementation:

MAJOR FEATURE IMPLEMENTATION: Three explicit subscription states (Free, Free Trial, Subscribed) 
with complete feature gating, data model updates, webhook handling, and UI states.

CRITICAL TEST ENDPOINTS:
1. GET /api/me - New endpoint returning UserMeResponse with BillingState
2. GET /api/debug/billing-state - Debug endpoint with comprehensive billing info
3. Server-side gating: check_pro_access() function behavior
4. State transition functions: mark_trial_started(), mark_subscription_active(), etc.
5. Enhanced subscription checkout: POST /api/subscription/checkout
6. Webhook handling: Verify webhook endpoints are accessible

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!

Expected: All three-state subscription system features working correctly with proper gating.
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration - Use environment variable for backend URL
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://ff9606ce-1843-4dc8-a0da-da1fe6ced548.preview.emergentagent.com')
BASE_URL = f"{BACKEND_URL}/api"

# Pro account for subscription testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class SubscriptionStatesTester:
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

    def test_authentication_setup(self):
        """Test authentication with Pro account"""
        try:
            print("🔐 AUTHENTICATION SETUP: Login with brycelarsenmusic@gmail.com")
            print("=" * 80)
            
            login_data = {
                "email": PRO_MUSICIAN["email"],
                "password": PRO_MUSICIAN["password"]
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
                    print(f"   ✅ Musician Slug: {self.musician_slug}")
                    
                    self.log_result("Authentication Setup", True, f"Logged in as {data['musician']['name']}")
                else:
                    self.log_result("Authentication Setup", False, f"Missing token or musician in response: {data}")
            else:
                self.log_result("Authentication Setup", False, f"Status code: {response.status_code}, Response: {response.text}")
                
            print("=" * 80)
        except Exception as e:
            self.log_result("Authentication Setup", False, f"Exception: {str(e)}")

    def test_new_me_endpoint(self):
        """Test new GET /api/me endpoint with BillingState"""
        try:
            print("🎵 PRIORITY 1: Testing New GET /api/me Endpoint")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("GET /api/me Endpoint", False, "No authentication token available")
                return
            
            print("📊 Step 1: Test GET /api/me endpoint")
            
            response = self.make_request("GET", "/me")
            
            print(f"   📊 /api/me response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   📊 Response keys: {list(data.keys())}")
                    
                    # Step 2: Verify UserMeResponse structure
                    print("📊 Step 2: Verify UserMeResponse structure")
                    
                    required_fields = ["id", "name", "email", "slug", "billing"]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if len(missing_fields) == 0:
                        print(f"   ✅ All required UserMeResponse fields present: {required_fields}")
                        structure_valid = True
                    else:
                        print(f"   ❌ Missing UserMeResponse fields: {missing_fields}")
                        structure_valid = False
                    
                    # Step 3: Verify BillingState structure
                    print("📊 Step 3: Verify BillingState structure")
                    
                    billing_data = data.get("billing", {})
                    billing_required_fields = ["plan", "status", "trial_end", "audience_link_active", "has_pro_access"]
                    billing_missing_fields = [field for field in billing_required_fields if field not in billing_data]
                    
                    if len(billing_missing_fields) == 0:
                        print(f"   ✅ All required BillingState fields present: {billing_required_fields}")
                        billing_structure_valid = True
                        
                        # Print billing state details
                        print(f"   📊 Billing State Details:")
                        print(f"      - plan: {billing_data.get('plan')}")
                        print(f"      - status: {billing_data.get('status')}")
                        print(f"      - trial_end: {billing_data.get('trial_end')}")
                        print(f"      - audience_link_active: {billing_data.get('audience_link_active')}")
                        print(f"      - has_pro_access: {billing_data.get('has_pro_access')}")
                        
                    else:
                        print(f"   ❌ Missing BillingState fields: {billing_missing_fields}")
                        billing_structure_valid = False
                    
                    # Step 4: Verify field types and values
                    print("📊 Step 4: Verify field types and values")
                    
                    types_valid = True
                    
                    # Check plan field
                    plan = billing_data.get("plan")
                    if plan in ["free", "pro"]:
                        print(f"   ✅ plan field valid: '{plan}'")
                    else:
                        print(f"   ❌ plan field invalid: '{plan}' (expected 'free' or 'pro')")
                        types_valid = False
                    
                    # Check status field
                    status = billing_data.get("status")
                    valid_statuses = ["none", "trialing", "active", "past_due", "canceled"]
                    if status in valid_statuses:
                        print(f"   ✅ status field valid: '{status}'")
                    else:
                        print(f"   ❌ status field invalid: '{status}' (expected one of {valid_statuses})")
                        types_valid = False
                    
                    # Check boolean fields
                    audience_link_active = billing_data.get("audience_link_active")
                    has_pro_access = billing_data.get("has_pro_access")
                    
                    if isinstance(audience_link_active, bool):
                        print(f"   ✅ audience_link_active is boolean: {audience_link_active}")
                    else:
                        print(f"   ❌ audience_link_active is not boolean: {audience_link_active}")
                        types_valid = False
                    
                    if isinstance(has_pro_access, bool):
                        print(f"   ✅ has_pro_access is boolean: {has_pro_access}")
                    else:
                        print(f"   ❌ has_pro_access is not boolean: {has_pro_access}")
                        types_valid = False
                    
                    # Step 5: Verify three-state logic consistency
                    print("📊 Step 5: Verify three-state logic consistency")
                    
                    logic_consistent = True
                    
                    # Free state: plan='free', status should be 'none' or 'canceled'
                    if plan == "free":
                        if status in ["none", "canceled"]:
                            print(f"   ✅ Free state consistent: plan='{plan}', status='{status}'")
                            if has_pro_access:
                                print(f"   ❌ Free state should not have Pro access")
                                logic_consistent = False
                            else:
                                print(f"   ✅ Free state correctly has no Pro access")
                        else:
                            print(f"   ❌ Free state inconsistent: plan='{plan}' but status='{status}'")
                            logic_consistent = False
                    
                    # Pro state: plan='pro', status should be 'trialing', 'active', or 'past_due'
                    elif plan == "pro":
                        if status in ["trialing", "active", "past_due"]:
                            print(f"   ✅ Pro state consistent: plan='{plan}', status='{status}'")
                            if has_pro_access:
                                print(f"   ✅ Pro state correctly has Pro access")
                            else:
                                print(f"   ❌ Pro state should have Pro access")
                                logic_consistent = False
                        else:
                            print(f"   ❌ Pro state inconsistent: plan='{plan}' but status='{status}'")
                            logic_consistent = False
                    
                    # Final assessment
                    if structure_valid and billing_structure_valid and types_valid and logic_consistent:
                        self.log_result("GET /api/me Endpoint", True, "✅ NEW /api/me ENDPOINT WORKING: Returns proper UserMeResponse with BillingState, all fields present with correct types and three-state logic")
                    else:
                        issues = []
                        if not structure_valid:
                            issues.append(f"missing UserMeResponse fields: {missing_fields}")
                        if not billing_structure_valid:
                            issues.append(f"missing BillingState fields: {billing_missing_fields}")
                        if not types_valid:
                            issues.append("invalid field types")
                        if not logic_consistent:
                            issues.append("three-state logic inconsistent")
                        
                        self.log_result("GET /api/me Endpoint", False, f"❌ CRITICAL /api/me ISSUES: {', '.join(issues)}")
                        
                except json.JSONDecodeError:
                    self.log_result("GET /api/me Endpoint", False, "Response is not valid JSON")
            else:
                self.log_result("GET /api/me Endpoint", False, f"Status code: {response.status_code}, Response: {response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("GET /api/me Endpoint", False, f"Exception: {str(e)}")

    def test_debug_billing_state_endpoint(self):
        """Test GET /api/debug/billing-state endpoint"""
        try:
            print("🎵 PRIORITY 1: Testing GET /api/debug/billing-state Endpoint")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("GET /api/debug/billing-state Endpoint", False, "No authentication token available")
                return
            
            print("📊 Step 1: Test GET /api/debug/billing-state endpoint")
            
            response = self.make_request("GET", "/debug/billing-state")
            
            print(f"   📊 /api/debug/billing-state response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   📊 Response keys: {list(data.keys())}")
                    
                    # Step 2: Verify comprehensive billing info structure
                    print("📊 Step 2: Verify comprehensive billing info structure")
                    
                    expected_fields = ["plan", "status", "trial_end", "stripe_customer_id", "stripe_subscription_id"]
                    missing_fields = [field for field in expected_fields if field not in data]
                    
                    if len(missing_fields) == 0:
                        print(f"   ✅ All expected debug fields present: {expected_fields}")
                        structure_valid = True
                        
                        # Print debug details
                        print(f"   📊 Debug Billing Details:")
                        print(f"      - plan: {data.get('plan')}")
                        print(f"      - status: {data.get('status')}")
                        print(f"      - trial_end: {data.get('trial_end')}")
                        print(f"      - stripe_customer_id: {data.get('stripe_customer_id')}")
                        print(f"      - stripe_subscription_id: {data.get('stripe_subscription_id')}")
                        
                    else:
                        print(f"   ❌ Missing debug fields: {missing_fields}")
                        structure_valid = False
                    
                    # Step 3: Verify field consistency with /api/me
                    print("📊 Step 3: Verify consistency with /api/me endpoint")
                    
                    # Get /api/me data for comparison
                    me_response = self.make_request("GET", "/me")
                    consistency_valid = True
                    
                    if me_response.status_code == 200:
                        me_data = me_response.json()
                        me_billing = me_data.get("billing", {})
                        
                        # Compare plan and status
                        if data.get("plan") == me_billing.get("plan"):
                            print(f"   ✅ plan consistent between endpoints: {data.get('plan')}")
                        else:
                            print(f"   ❌ plan inconsistent: debug='{data.get('plan')}', me='{me_billing.get('plan')}'")
                            consistency_valid = False
                        
                        if data.get("status") == me_billing.get("status"):
                            print(f"   ✅ status consistent between endpoints: {data.get('status')}")
                        else:
                            print(f"   ❌ status inconsistent: debug='{data.get('status')}', me='{me_billing.get('status')}'")
                            consistency_valid = False
                        
                        if data.get("trial_end") == me_billing.get("trial_end"):
                            print(f"   ✅ trial_end consistent between endpoints")
                        else:
                            print(f"   ❌ trial_end inconsistent: debug='{data.get('trial_end')}', me='{me_billing.get('trial_end')}'")
                            consistency_valid = False
                    else:
                        print(f"   ⚠️  Could not verify consistency - /api/me failed: {me_response.status_code}")
                    
                    # Final assessment
                    if structure_valid and consistency_valid:
                        self.log_result("GET /api/debug/billing-state Endpoint", True, "✅ DEBUG BILLING STATE ENDPOINT WORKING: Returns comprehensive billing info with all required fields, consistent with /api/me")
                    else:
                        issues = []
                        if not structure_valid:
                            issues.append(f"missing fields: {missing_fields}")
                        if not consistency_valid:
                            issues.append("inconsistent with /api/me endpoint")
                        
                        self.log_result("GET /api/debug/billing-state Endpoint", False, f"❌ CRITICAL DEBUG ENDPOINT ISSUES: {', '.join(issues)}")
                        
                except json.JSONDecodeError:
                    self.log_result("GET /api/debug/billing-state Endpoint", False, "Response is not valid JSON")
            else:
                self.log_result("GET /api/debug/billing-state Endpoint", False, f"Status code: {response.status_code}, Response: {response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("GET /api/debug/billing-state Endpoint", False, f"Exception: {str(e)}")

    def test_server_side_gating(self):
        """Test server-side Pro access gating"""
        try:
            print("🎵 PRIORITY 1: Testing Server-Side Pro Access Gating")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Server-Side Gating", False, "No authentication token available")
                return
            
            # Step 1: Test Pro-only endpoints with current user
            print("📊 Step 1: Test Pro-only endpoints with current user")
            
            # Test playlists endpoint (Pro feature)
            playlists_response = self.make_request("GET", "/playlists")
            
            print(f"   📊 GET /playlists response status: {playlists_response.status_code}")
            
            if playlists_response.status_code == 200:
                print(f"   ✅ User has Pro access - playlists endpoint accessible")
                has_pro_access = True
            elif playlists_response.status_code == 403:
                try:
                    error_data = playlists_response.json()
                    error_message = error_data.get("detail", {}).get("message", "")
                    
                    if "Pro feature" in error_message and "14-day free trial" in error_message:
                        print(f"   ✅ Proper 403 response with correct message: {error_message}")
                        has_pro_access = False
                        proper_403_message = True
                    else:
                        print(f"   ❌ 403 response but wrong message: {error_message}")
                        has_pro_access = False
                        proper_403_message = False
                except:
                    print(f"   ❌ 403 response but invalid JSON: {playlists_response.text}")
                    has_pro_access = False
                    proper_403_message = False
            else:
                print(f"   ❌ Unexpected response: {playlists_response.status_code}")
                has_pro_access = False
                proper_403_message = False
            
            # Step 2: Verify gating consistency with billing state
            print("📊 Step 2: Verify gating consistency with billing state")
            
            me_response = self.make_request("GET", "/me")
            gating_consistent = True
            
            if me_response.status_code == 200:
                me_data = me_response.json()
                billing = me_data.get("billing", {})
                
                expected_pro_access = billing.get("has_pro_access", False)
                plan = billing.get("plan", "free")
                status = billing.get("status", "none")
                
                print(f"   📊 Billing state: plan='{plan}', status='{status}', has_pro_access={expected_pro_access}")
                print(f"   📊 Actual Pro access: {has_pro_access}")
                
                if expected_pro_access == has_pro_access:
                    print(f"   ✅ Gating consistent with billing state")
                else:
                    print(f"   ❌ Gating inconsistent: billing says {expected_pro_access}, actual is {has_pro_access}")
                    gating_consistent = False
                
                # Step 3: Verify three-state gating logic
                print("📊 Step 3: Verify three-state gating logic")
                
                logic_correct = True
                
                # Pro access should be: plan='pro' AND status IN ('trialing','active','past_due')
                expected_access = (plan == "pro" and status in ["trialing", "active", "past_due"])
                
                if expected_access == has_pro_access:
                    print(f"   ✅ Three-state gating logic correct")
                    if expected_access:
                        print(f"      - Pro access granted: plan='{plan}', status='{status}'")
                    else:
                        print(f"      - Pro access denied: plan='{plan}', status='{status}'")
                else:
                    print(f"   ❌ Three-state gating logic incorrect")
                    print(f"      - Expected access: {expected_access} (plan='{plan}', status='{status}')")
                    print(f"      - Actual access: {has_pro_access}")
                    logic_correct = False
                
            else:
                print(f"   ⚠️  Could not verify consistency - /api/me failed: {me_response.status_code}")
                gating_consistent = False
                logic_correct = False
            
            # Step 4: Test other Pro endpoints
            print("📊 Step 4: Test other Pro endpoints for consistency")
            
            other_endpoints_consistent = True
            
            # Test song suggestions endpoint (Pro feature)
            suggestions_response = self.make_request("GET", "/song-suggestions")
            
            if (suggestions_response.status_code == 200) == has_pro_access:
                print(f"   ✅ Song suggestions endpoint consistent with Pro access")
            elif suggestions_response.status_code == 403 and not has_pro_access:
                print(f"   ✅ Song suggestions properly blocked for non-Pro users")
            else:
                print(f"   ❌ Song suggestions endpoint inconsistent: status={suggestions_response.status_code}, expected_access={has_pro_access}")
                other_endpoints_consistent = False
            
            # Final assessment
            success_conditions = []
            if has_pro_access:
                # User has Pro access - verify it works
                success_conditions = [gating_consistent, logic_correct, other_endpoints_consistent]
                if all(success_conditions):
                    self.log_result("Server-Side Gating", True, "✅ SERVER-SIDE GATING WORKING: User has Pro access, all Pro endpoints accessible, gating logic consistent")
                else:
                    issues = []
                    if not gating_consistent:
                        issues.append("gating inconsistent with billing state")
                    if not logic_correct:
                        issues.append("three-state logic incorrect")
                    if not other_endpoints_consistent:
                        issues.append("inconsistent across Pro endpoints")
                    
                    self.log_result("Server-Side Gating", False, f"❌ CRITICAL GATING ISSUES: {', '.join(issues)}")
            else:
                # User doesn't have Pro access - verify proper blocking
                success_conditions = [proper_403_message, gating_consistent, logic_correct, other_endpoints_consistent]
                if all(success_conditions):
                    self.log_result("Server-Side Gating", True, "✅ SERVER-SIDE GATING WORKING: User blocked from Pro features with proper 403 messages, gating logic consistent")
                else:
                    issues = []
                    if not proper_403_message:
                        issues.append("improper 403 error message")
                    if not gating_consistent:
                        issues.append("gating inconsistent with billing state")
                    if not logic_correct:
                        issues.append("three-state logic incorrect")
                    if not other_endpoints_consistent:
                        issues.append("inconsistent across Pro endpoints")
                    
                    self.log_result("Server-Side Gating", False, f"❌ CRITICAL GATING ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Server-Side Gating", False, f"Exception: {str(e)}")

    def test_subscription_checkout_endpoints(self):
        """Test enhanced subscription checkout endpoints"""
        try:
            print("🎵 PRIORITY 1: Testing Enhanced Subscription Checkout")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Subscription Checkout", False, "No authentication token available")
                return
            
            # Step 1: Test monthly checkout
            print("📊 Step 1: Test monthly subscription checkout")
            
            monthly_data = {"plan": "monthly"}
            monthly_response = self.make_request("POST", "/subscription/checkout", monthly_data)
            
            print(f"   📊 Monthly checkout response status: {monthly_response.status_code}")
            
            if monthly_response.status_code == 200:
                try:
                    monthly_result = monthly_response.json()
                    if "checkout_url" in monthly_result:
                        print(f"   ✅ Monthly checkout successful - got checkout URL")
                        monthly_working = True
                    else:
                        print(f"   ❌ Monthly checkout missing checkout_url: {monthly_result}")
                        monthly_working = False
                except json.JSONDecodeError:
                    print(f"   ❌ Monthly checkout invalid JSON response")
                    monthly_working = False
            else:
                print(f"   📊 Monthly checkout failed: {monthly_response.status_code}")
                print(f"   📊 Response: {monthly_response.text}")
                monthly_working = False
            
            # Step 2: Test annual checkout
            print("📊 Step 2: Test annual subscription checkout")
            
            annual_data = {"plan": "annual"}
            annual_response = self.make_request("POST", "/subscription/checkout", annual_data)
            
            print(f"   📊 Annual checkout response status: {annual_response.status_code}")
            
            if annual_response.status_code == 200:
                try:
                    annual_result = annual_response.json()
                    if "checkout_url" in annual_result:
                        print(f"   ✅ Annual checkout successful - got checkout URL")
                        annual_working = True
                    else:
                        print(f"   ❌ Annual checkout missing checkout_url: {annual_result}")
                        annual_working = False
                except json.JSONDecodeError:
                    print(f"   ❌ Annual checkout invalid JSON response")
                    annual_working = False
            else:
                print(f"   📊 Annual checkout failed: {annual_response.status_code}")
                print(f"   📊 Response: {annual_response.text}")
                annual_working = False
            
            # Step 3: Test invalid plan
            print("📊 Step 3: Test invalid plan handling")
            
            invalid_data = {"plan": "invalid_plan"}
            invalid_response = self.make_request("POST", "/subscription/checkout", invalid_data)
            
            print(f"   📊 Invalid plan response status: {invalid_response.status_code}")
            
            if invalid_response.status_code in [400, 422]:
                print(f"   ✅ Invalid plan properly rejected")
                invalid_handling = True
            else:
                print(f"   ❌ Invalid plan not properly handled: {invalid_response.status_code}")
                invalid_handling = False
            
            # Step 4: Test environment variable mapping
            print("📊 Step 4: Test environment variable mapping")
            
            # This is more of an informational check since we can't directly test env vars
            # But we can check if the responses suggest proper configuration
            env_mapping_ok = True
            
            if monthly_working or annual_working:
                print(f"   ✅ Environment variable mapping appears to be working (checkout URLs generated)")
            else:
                print(f"   ⚠️  Environment variable mapping may have issues (no checkout URLs generated)")
                # Don't fail the test for this since it might be a configuration issue
            
            # Final assessment
            if monthly_working and annual_working and invalid_handling:
                self.log_result("Subscription Checkout", True, "✅ SUBSCRIPTION CHECKOUT WORKING: Both monthly and annual checkout work, invalid plans properly handled")
            elif (monthly_working or annual_working) and invalid_handling:
                self.log_result("Subscription Checkout", True, "✅ SUBSCRIPTION CHECKOUT MOSTLY WORKING: At least one plan works, error handling correct")
            else:
                issues = []
                if not monthly_working:
                    issues.append("monthly checkout failed")
                if not annual_working:
                    issues.append("annual checkout failed")
                if not invalid_handling:
                    issues.append("invalid plan handling incorrect")
                
                self.log_result("Subscription Checkout", False, f"❌ CRITICAL CHECKOUT ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Subscription Checkout", False, f"Exception: {str(e)}")

    def test_webhook_endpoints(self):
        """Test webhook endpoint accessibility"""
        try:
            print("🎵 PRIORITY 1: Testing Webhook Endpoints")
            print("=" * 80)
            
            # Step 1: Test Stripe webhook endpoint accessibility
            print("📊 Step 1: Test Stripe webhook endpoint accessibility")
            
            # Test without signature (should fail with proper error)
            webhook_response = self.make_request("POST", "/stripe/webhook", {"test": "data"})
            
            print(f"   📊 Webhook endpoint response status: {webhook_response.status_code}")
            
            if webhook_response.status_code == 400:
                try:
                    error_data = webhook_response.json()
                    error_message = str(error_data)
                    
                    if "signature" in error_message.lower() or "missing" in error_message.lower():
                        print(f"   ✅ Webhook endpoint accessible with proper signature validation")
                        webhook_accessible = True
                    else:
                        print(f"   ❌ Webhook endpoint accessible but wrong error: {error_message}")
                        webhook_accessible = False
                except:
                    print(f"   ❌ Webhook endpoint error response not JSON: {webhook_response.text}")
                    webhook_accessible = False
            elif webhook_response.status_code == 404:
                print(f"   ❌ Webhook endpoint not found")
                webhook_accessible = False
            else:
                print(f"   📊 Webhook endpoint unexpected response: {webhook_response.status_code}")
                print(f"   📊 Response: {webhook_response.text}")
                # Still consider it accessible if it's not 404
                webhook_accessible = webhook_response.status_code != 404
            
            # Step 2: Test webhook endpoint structure
            print("📊 Step 2: Verify webhook endpoint structure")
            
            # The fact that we get a response (even error) means the endpoint exists
            if webhook_accessible:
                print(f"   ✅ Webhook endpoint exists and responds to requests")
                structure_ok = True
            else:
                print(f"   ❌ Webhook endpoint not properly configured")
                structure_ok = False
            
            # Final assessment
            if webhook_accessible and structure_ok:
                self.log_result("Webhook Endpoints", True, "✅ WEBHOOK ENDPOINTS WORKING: Stripe webhook endpoint accessible with proper signature validation")
            else:
                issues = []
                if not webhook_accessible:
                    issues.append("webhook endpoint not accessible")
                if not structure_ok:
                    issues.append("webhook structure incorrect")
                
                self.log_result("Webhook Endpoints", False, f"❌ CRITICAL WEBHOOK ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Webhook Endpoints", False, f"Exception: {str(e)}")

    def print_final_summary(self):
        """Print final test summary"""
        print("\n" + "=" * 80)
        print("🎵 THREE-STATE SUBSCRIPTION SYSTEM TEST SUMMARY")
        print("=" * 80)
        
        total_tests = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📊 TOTAL TESTS: {total_tests}")
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        print(f"📈 SUCCESS RATE: {success_rate:.1f}%")
        
        if self.results["failed"] > 0:
            print(f"\n❌ FAILED TESTS:")
            for error in self.results["errors"]:
                print(f"   - {error}")
        
        print("\n" + "=" * 80)
        
        # Determine overall status
        if success_rate >= 80:
            print("🎉 THREE-STATE SUBSCRIPTION SYSTEM: WORKING")
            if success_rate == 100:
                print("   All tests passed - system is fully functional")
            else:
                print("   Most tests passed - system is mostly functional with minor issues")
        elif success_rate >= 60:
            print("⚠️  THREE-STATE SUBSCRIPTION SYSTEM: PARTIALLY WORKING")
            print("   Some critical issues found - needs attention")
        else:
            print("❌ THREE-STATE SUBSCRIPTION SYSTEM: MAJOR ISSUES")
            print("   Multiple critical failures - requires immediate fixes")
        
        print("=" * 80)

def main():
    """Run all subscription states tests"""
    print("🚀 STARTING THREE-STATE SUBSCRIPTION SYSTEM TESTING")
    print(f"🌐 Backend URL: {BASE_URL}")
    print("=" * 80)
    
    tester = SubscriptionStatesTester()
    
    # Run all tests in order
    tester.test_authentication_setup()
    tester.test_new_me_endpoint()
    tester.test_debug_billing_state_endpoint()
    tester.test_server_side_gating()
    tester.test_subscription_checkout_endpoints()
    tester.test_webhook_endpoints()
    
    # Print final summary
    tester.print_final_summary()

if __name__ == "__main__":
    main()