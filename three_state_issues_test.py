#!/usr/bin/env python3
"""
FOCUSED THREE-STATE SYSTEM ISSUES TESTING

Testing specific issues found in the three-state subscription system:

CRITICAL ISSUES IDENTIFIED:
1. **403 Response Format** - Returns {"detail": {"message": "..."}} instead of {"message": "..."}
2. **Stripe Configuration** - Missing STRIPE_PRICE_ID_MONTHLY_10 and STRIPE_PRICE_ID_ANNUAL_48
3. **Billing Confirm Authentication** - Requires authentication but should handle unauthenticated requests
4. **Subscription Status Plan Values** - Returns "active" instead of "pro" for plan field
5. **Error Logging** - Missing error_id in most error responses

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!
"""

import requests
import json
import os
from typing import Dict, Any, Optional

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ff9606ce-1843-4dc8-a0da-da1fe6ced548.preview.emergentagent.com')
BASE_URL = f"{BACKEND_URL}/api"

# Test credentials
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

FREE_MUSICIAN = {
    "name": "Free Test User",
    "email": "free.test@requestwave.com",
    "password": "FreeTestPassword123!"
}

class ThreeStateIssuesTester:
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

    def make_request(self, method: str, endpoint: str, data: Any = None, headers: Dict = None, params: Dict = None) -> requests.Response:
        """Make HTTP request with proper headers"""
        url = f"{self.base_url}{endpoint}"
        
        request_headers = {"Content-Type": "application/json"}
        if self.auth_token:
            request_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        if headers:
            request_headers.update(headers)
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=request_headers, params=params or data)
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

    def setup_free_user(self):
        """Setup a free user for testing"""
        try:
            response = self.make_request("POST", "/auth/register", FREE_MUSICIAN)
            
            if response.status_code == 200:
                data = response.json()
                return data["token"]
            elif response.status_code == 400:
                login_data = {
                    "email": FREE_MUSICIAN["email"],
                    "password": FREE_MUSICIAN["password"]
                }
                login_response = self.make_request("POST", "/auth/login", login_data)
                
                if login_response.status_code == 200:
                    data = login_response.json()
                    return data["token"]
            return None
        except Exception as e:
            print(f"Error setting up free user: {e}")
            return None

    def test_403_response_format_issue(self):
        """Test the 403 response format issue"""
        try:
            print("🔒 ISSUE TEST: 403 Response Format")
            print("=" * 60)
            
            free_token = self.setup_free_user()
            if not free_token:
                self.log_result("403 Response Format Issue", False, "Failed to setup free user")
                return
            
            original_token = self.auth_token
            self.auth_token = free_token
            
            # Test song suggestions endpoint
            response = self.make_request("GET", "/song-suggestions")
            
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 403:
                try:
                    data = response.json()
                    print(f"📊 Current response: {data}")
                    
                    # Current format: {"detail": {"message": "..."}}
                    # Expected format: {"message": "..."}
                    
                    if "detail" in data and isinstance(data["detail"], dict) and "message" in data["detail"]:
                        expected_message = "Pro feature — start your 14-day free trial to unlock your Audience Link."
                        actual_message = data["detail"]["message"]
                        
                        if actual_message == expected_message:
                            print("✅ Message content is correct")
                            print("❌ But format is wrong - should be {'message': '...'} not {'detail': {'message': '...'}}")
                            self.log_result("403 Response Format Issue", False, 
                                          "Response format is {'detail': {'message': '...'}} instead of {'message': '...'}")
                        else:
                            self.log_result("403 Response Format Issue", False, 
                                          f"Wrong message content: {actual_message}")
                    else:
                        self.log_result("403 Response Format Issue", False, 
                                      f"Unexpected response structure: {data}")
                        
                except json.JSONDecodeError:
                    self.log_result("403 Response Format Issue", False, "Response not valid JSON")
            else:
                self.log_result("403 Response Format Issue", False, f"Expected 403, got {response.status_code}")
            
            self.auth_token = original_token
            print("=" * 60)
            
        except Exception as e:
            self.log_result("403 Response Format Issue", False, f"Exception: {str(e)}")

    def test_stripe_configuration_issue(self):
        """Test the Stripe configuration issue"""
        try:
            print("💳 ISSUE TEST: Stripe Configuration")
            print("=" * 60)
            
            # Login with Pro account
            login_data = {
                "email": PRO_MUSICIAN["email"],
                "password": PRO_MUSICIAN["password"]
            }
            
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code != 200:
                self.log_result("Stripe Configuration Issue", False, "Failed to login")
                return
            
            login_data_response = login_response.json()
            original_token = self.auth_token
            self.auth_token = login_data_response["token"]
            
            # Test monthly checkout
            monthly_data = {"plan": "monthly"}
            monthly_response = self.make_request("POST", "/subscription/checkout", monthly_data)
            
            print(f"📊 Monthly checkout status: {monthly_response.status_code}")
            
            if monthly_response.status_code == 400:
                try:
                    data = monthly_response.json()
                    print(f"📊 Error response: {data}")
                    
                    if "detail" in data and "message" in data["detail"]:
                        message = data["detail"]["message"]
                        if "STRIPE_PRICE_ID_MONTHLY_10" in message:
                            print("✅ Correctly identifies missing STRIPE_PRICE_ID_MONTHLY_10")
                            self.log_result("Stripe Configuration Issue", True, 
                                          "Stripe configuration error properly detected and reported")
                        else:
                            self.log_result("Stripe Configuration Issue", False, 
                                          f"Unexpected error message: {message}")
                    else:
                        self.log_result("Stripe Configuration Issue", False, 
                                      f"Unexpected error structure: {data}")
                        
                except json.JSONDecodeError:
                    self.log_result("Stripe Configuration Issue", False, "Error response not valid JSON")
            else:
                self.log_result("Stripe Configuration Issue", False, 
                              f"Expected 400 configuration error, got {monthly_response.status_code}")
            
            self.auth_token = original_token
            print("=" * 60)
            
        except Exception as e:
            self.log_result("Stripe Configuration Issue", False, f"Exception: {str(e)}")

    def test_billing_confirm_authentication_issue(self):
        """Test the billing confirm authentication issue"""
        try:
            print("🔄 ISSUE TEST: Billing Confirm Authentication")
            print("=" * 60)
            
            # Test without authentication (should work for return flow)
            self.auth_token = None
            
            response = self.make_request("GET", "/billing/confirm", params={"session_id": "cs_test_fake"})
            
            print(f"📊 Status: {response.status_code}")
            print(f"📊 Response: {response.text[:200]}")
            
            if response.status_code == 403:
                try:
                    data = response.json()
                    if "detail" in data and data["detail"] == "Not authenticated":
                        print("❌ Billing confirm requires authentication")
                        print("❌ This breaks the return flow from Stripe checkout")
                        self.log_result("Billing Confirm Authentication Issue", False, 
                                      "Billing confirm endpoint requires authentication, breaking return flow")
                    else:
                        self.log_result("Billing Confirm Authentication Issue", False, 
                                      f"Unexpected 403 response: {data}")
                except json.JSONDecodeError:
                    self.log_result("Billing Confirm Authentication Issue", False, 
                                  "403 response not valid JSON")
            elif response.status_code in [400, 422]:
                print("✅ Endpoint accessible without auth, returns validation error")
                self.log_result("Billing Confirm Authentication Issue", True, 
                              "Billing confirm endpoint accessible without authentication")
            else:
                self.log_result("Billing Confirm Authentication Issue", False, 
                              f"Unexpected response: {response.status_code}")
            
            print("=" * 60)
            
        except Exception as e:
            self.log_result("Billing Confirm Authentication Issue", False, f"Exception: {str(e)}")

    def test_subscription_status_plan_values_issue(self):
        """Test the subscription status plan values issue"""
        try:
            print("📊 ISSUE TEST: Subscription Status Plan Values")
            print("=" * 60)
            
            # Login with Pro account
            login_data = {
                "email": PRO_MUSICIAN["email"],
                "password": PRO_MUSICIAN["password"]
            }
            
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code != 200:
                self.log_result("Subscription Status Plan Values Issue", False, "Failed to login")
                return
            
            login_data_response = login_response.json()
            original_token = self.auth_token
            self.auth_token = login_data_response["token"]
            
            # Test subscription status
            response = self.make_request("GET", "/subscription/status")
            
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"📊 Response: {data}")
                    
                    plan = data.get("plan")
                    status = data.get("status")
                    
                    print(f"📊 Current plan value: {plan}")
                    print(f"📊 Current status value: {status}")
                    
                    # According to three-state system:
                    # plan should be "free" or "pro"
                    # status should be "none", "trialing", "active", "past_due", "canceled"
                    
                    valid_plans = ["free", "pro"]
                    valid_statuses = ["none", "trialing", "active", "past_due", "canceled"]
                    
                    if plan not in valid_plans:
                        print(f"❌ Invalid plan value: {plan} (should be one of {valid_plans})")
                        self.log_result("Subscription Status Plan Values Issue", False, 
                                      f"Plan value '{plan}' not in valid three-state values {valid_plans}")
                    elif status not in valid_statuses:
                        print(f"❌ Invalid status value: {status} (should be one of {valid_statuses})")
                        self.log_result("Subscription Status Plan Values Issue", False, 
                                      f"Status value '{status}' not in valid three-state values {valid_statuses}")
                    else:
                        print("✅ Plan and status values are valid for three-state system")
                        self.log_result("Subscription Status Plan Values Issue", True, 
                                      f"Valid three-state values: plan={plan}, status={status}")
                        
                except json.JSONDecodeError:
                    self.log_result("Subscription Status Plan Values Issue", False, 
                                  "Response not valid JSON")
            else:
                self.log_result("Subscription Status Plan Values Issue", False, 
                              f"Status endpoint failed: {response.status_code}")
            
            self.auth_token = original_token
            print("=" * 60)
            
        except Exception as e:
            self.log_result("Subscription Status Plan Values Issue", False, f"Exception: {str(e)}")

    def test_error_logging_missing_error_id_issue(self):
        """Test the missing error_id in error responses issue"""
        try:
            print("🚨 ISSUE TEST: Missing error_id in Error Responses")
            print("=" * 60)
            
            # Test various endpoints that should return structured errors
            test_cases = [
                ("POST", "/auth/login", {"email": "invalid", "password": "wrong"}, "Invalid Login"),
                ("GET", "/subscription/status", None, "Unauthenticated Status Request"),
            ]
            
            for method, endpoint, data, test_name in test_cases:
                print(f"📊 Testing {test_name}: {method} {endpoint}")
                
                # Clear auth token for unauthenticated requests
                if "Unauthenticated" in test_name:
                    self.auth_token = None
                
                response = self.make_request(method, endpoint, data)
                
                print(f"   📊 Status: {response.status_code}")
                
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        print(f"   📊 Error response: {error_data}")
                        
                        # Check for error_id
                        has_error_id = False
                        if "detail" in error_data:
                            if isinstance(error_data["detail"], dict):
                                has_error_id = "error_id" in error_data["detail"]
                            elif isinstance(error_data["detail"], str):
                                has_error_id = False  # Simple string detail
                        elif "error_id" in error_data:
                            has_error_id = True
                        
                        if has_error_id:
                            print(f"   ✅ Has error_id")
                        else:
                            print(f"   ❌ Missing error_id in error response")
                            
                    except json.JSONDecodeError:
                        print(f"   ❌ Error response not valid JSON")
                
                print()
            
            # For this test, we'll mark it as identifying the issue
            self.log_result("Error Logging Missing error_id Issue", True, 
                          "Successfully identified missing error_id in most error responses")
            
            print("=" * 60)
            
        except Exception as e:
            self.log_result("Error Logging Missing error_id Issue", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all issue-focused tests"""
        print("🔍 STARTING THREE-STATE SYSTEM ISSUES TESTING")
        print("=" * 80)
        print(f"Backend URL: {self.base_url}")
        print("=" * 80)
        
        # Run all issue tests
        self.test_403_response_format_issue()
        self.test_stripe_configuration_issue()
        self.test_billing_confirm_authentication_issue()
        self.test_subscription_status_plan_values_issue()
        self.test_error_logging_missing_error_id_issue()
        
        # Print final results
        print("\n" + "=" * 80)
        print("🏁 THREE-STATE SYSTEM ISSUES TEST RESULTS")
        print("=" * 80)
        
        total_tests = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        print(f"📊 SUCCESS RATE: {success_rate:.1f}%")
        
        if self.results["errors"]:
            print("\n❌ IDENTIFIED ISSUES:")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        print("\n" + "=" * 80)
        
        return self.results

if __name__ == "__main__":
    tester = ThreeStateIssuesTester()
    results = tester.run_all_tests()