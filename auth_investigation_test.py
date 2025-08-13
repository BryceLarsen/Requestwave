#!/usr/bin/env python3
"""
AUTHENTICATION INVESTIGATION TEST FOR BRYCELARSENMUSIC@GMAIL.COM

Investigating specific authentication issues after API connectivity was restored:

CONTEXT:
- API health endpoint https://requestwave.app/api/health now working (infrastructure fixed)
- User fixed a "name conflict" issue with Emergent support
- User still cannot login with brycelarsenmusic@gmail.com / RequestWave2024!
- Forgot password feature returns error when sending code
- Need to test authentication endpoints specifically

SPECIFIC INVESTIGATION:
1. Test Login Endpoint Specifically
2. Test Forgot Password Endpoint
3. Check User Account After Infrastructure Fix
4. Test Other Auth Endpoints
5. Check for Lock/Block Issues

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration - Use the production URL from frontend/.env
BASE_URL = "https://requestwave.app/api"

# User credentials from review request
USER_CREDENTIALS = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class AuthInvestigationTester:
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
                response = requests.get(url, headers=request_headers, params=data or params, timeout=30)
            elif method.upper() == "POST":
                if files:
                    response = requests.post(url, headers={k: v for k, v in request_headers.items() if k != "Content-Type"}, files=files, data=data, timeout=30)
                elif params:
                    response = requests.post(url, headers=request_headers, params=params, timeout=30)
                else:
                    response = requests.post(url, headers=request_headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=request_headers, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=request_headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response
        except Exception as e:
            print(f"Request failed: {e}")
            raise

    def test_api_health_check(self):
        """Test API health endpoint - should be working after infrastructure fix"""
        try:
            print("🔍 INVESTIGATION 1: Testing API Health Check")
            print("=" * 80)
            
            response = self.make_request("GET", "/health")
            
            print(f"   📊 Health endpoint status: {response.status_code}")
            print(f"   📊 Health endpoint response: {response.text}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "status" in data and data["status"] == "healthy":
                        self.log_result("API Health Check", True, f"✅ API is healthy: {data}")
                    else:
                        self.log_result("API Health Check", False, f"Unexpected health response: {data}")
                except json.JSONDecodeError:
                    self.log_result("API Health Check", False, f"Health response not JSON: {response.text}")
            else:
                self.log_result("API Health Check", False, f"Health check failed with status {response.status_code}: {response.text}")
                
            print("=" * 80)
            
        except Exception as e:
            self.log_result("API Health Check", False, f"Exception: {str(e)}")

    def test_specific_login_endpoint(self):
        """Test Login Endpoint Specifically with exact credentials"""
        try:
            print("🔍 INVESTIGATION 2: Testing Login Endpoint with Exact Credentials")
            print("=" * 80)
            
            print(f"   📊 Testing login with: {USER_CREDENTIALS['email']} / {USER_CREDENTIALS['password']}")
            
            response = self.make_request("POST", "/auth/login", USER_CREDENTIALS)
            
            print(f"   📊 Login endpoint status: {response.status_code}")
            print(f"   📊 Login endpoint response: {response.text}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "token" in data and "musician" in data:
                        self.auth_token = data["token"]
                        self.musician_id = data["musician"]["id"]
                        self.musician_slug = data["musician"]["slug"]
                        
                        print(f"   ✅ Login successful!")
                        print(f"   📊 Musician ID: {self.musician_id}")
                        print(f"   📊 Musician Name: {data['musician']['name']}")
                        print(f"   📊 Musician Slug: {self.musician_slug}")
                        print(f"   📊 Token received: {self.auth_token[:20]}...")
                        
                        self.log_result("Login Endpoint - Exact Credentials", True, f"✅ Login successful for {USER_CREDENTIALS['email']}")
                    else:
                        self.log_result("Login Endpoint - Exact Credentials", False, f"Missing token or musician in response: {data}")
                except json.JSONDecodeError:
                    self.log_result("Login Endpoint - Exact Credentials", False, f"Login response not JSON: {response.text}")
            elif response.status_code == 401:
                self.log_result("Login Endpoint - Exact Credentials", False, f"❌ AUTHENTICATION FAILED: Invalid credentials - {response.text}")
            elif response.status_code == 404:
                self.log_result("Login Endpoint - Exact Credentials", False, f"❌ USER NOT FOUND: Account may not exist - {response.text}")
            elif response.status_code == 500:
                self.log_result("Login Endpoint - Exact Credentials", False, f"❌ SERVER ERROR: Internal server error during login - {response.text}")
            else:
                self.log_result("Login Endpoint - Exact Credentials", False, f"❌ UNEXPECTED ERROR: Status {response.status_code} - {response.text}")
                
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Login Endpoint - Exact Credentials", False, f"Exception: {str(e)}")

    def test_forgot_password_endpoint(self):
        """Test Forgot Password Endpoint"""
        try:
            print("🔍 INVESTIGATION 3: Testing Forgot Password Endpoint")
            print("=" * 80)
            
            forgot_password_data = {
                "email": USER_CREDENTIALS["email"]
            }
            
            print(f"   📊 Testing forgot password for: {USER_CREDENTIALS['email']}")
            
            response = self.make_request("POST", "/auth/forgot-password", forgot_password_data)
            
            print(f"   📊 Forgot password endpoint status: {response.status_code}")
            print(f"   📊 Forgot password endpoint response: {response.text}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   ✅ Forgot password request successful!")
                    print(f"   📊 Response data: {data}")
                    
                    if "message" in data:
                        self.log_result("Forgot Password Endpoint", True, f"✅ Forgot password successful: {data['message']}")
                    else:
                        self.log_result("Forgot Password Endpoint", True, f"✅ Forgot password successful: {data}")
                except json.JSONDecodeError:
                    self.log_result("Forgot Password Endpoint", True, f"✅ Forgot password successful (non-JSON response): {response.text}")
            elif response.status_code == 404:
                self.log_result("Forgot Password Endpoint", False, f"❌ USER NOT FOUND: Email not found in system - {response.text}")
            elif response.status_code == 400:
                self.log_result("Forgot Password Endpoint", False, f"❌ BAD REQUEST: Invalid email format or missing data - {response.text}")
            elif response.status_code == 500:
                self.log_result("Forgot Password Endpoint", False, f"❌ SERVER ERROR: Email sending failed or internal error - {response.text}")
            else:
                self.log_result("Forgot Password Endpoint", False, f"❌ UNEXPECTED ERROR: Status {response.status_code} - {response.text}")
                
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Forgot Password Endpoint", False, f"Exception: {str(e)}")

    def test_user_account_existence(self):
        """Check if user account exists by testing registration endpoint"""
        try:
            print("🔍 INVESTIGATION 4: Testing User Account Existence")
            print("=" * 80)
            
            # Try to register with same email - should fail if account exists
            registration_data = {
                "name": "Test User",
                "email": USER_CREDENTIALS["email"],
                "password": "TestPassword123!"
            }
            
            print(f"   📊 Testing account existence for: {USER_CREDENTIALS['email']}")
            
            response = self.make_request("POST", "/auth/register", registration_data)
            
            print(f"   📊 Registration endpoint status: {response.status_code}")
            print(f"   📊 Registration endpoint response: {response.text}")
            
            if response.status_code == 400:
                try:
                    data = response.json()
                    if "already exists" in str(data).lower() or "email" in str(data).lower():
                        self.log_result("User Account Existence", True, f"✅ Account exists: {data}")
                    else:
                        self.log_result("User Account Existence", False, f"❌ Unexpected 400 error: {data}")
                except json.JSONDecodeError:
                    if "already exists" in response.text.lower() or "email" in response.text.lower():
                        self.log_result("User Account Existence", True, f"✅ Account exists: {response.text}")
                    else:
                        self.log_result("User Account Existence", False, f"❌ Unexpected 400 error: {response.text}")
            elif response.status_code == 200:
                self.log_result("User Account Existence", False, f"❌ ACCOUNT DOES NOT EXIST: Registration succeeded when it should have failed")
            elif response.status_code == 500:
                self.log_result("User Account Existence", False, f"❌ SERVER ERROR: Cannot verify account existence - {response.text}")
            else:
                self.log_result("User Account Existence", False, f"❌ UNEXPECTED ERROR: Status {response.status_code} - {response.text}")
                
            print("=" * 80)
            
        except Exception as e:
            self.log_result("User Account Existence", False, f"Exception: {str(e)}")

    def test_token_validation_if_login_successful(self):
        """Test token validation if login was successful"""
        try:
            print("🔍 INVESTIGATION 5: Testing Token Validation (if login successful)")
            print("=" * 80)
            
            if not self.auth_token:
                print("   ⚠️  No auth token available - login must have failed")
                self.log_result("Token Validation", False, "No auth token available from login")
                print("=" * 80)
                return
            
            print(f"   📊 Testing token validation with token: {self.auth_token[:20]}...")
            
            # Test token by accessing a protected endpoint
            response = self.make_request("GET", "/songs")
            
            print(f"   📊 Protected endpoint status: {response.status_code}")
            print(f"   📊 Protected endpoint response: {response.text[:200]}...")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   ✅ Token validation successful!")
                    print(f"   📊 Retrieved {len(data)} songs")
                    self.log_result("Token Validation", True, f"✅ Token valid - retrieved {len(data)} songs")
                except json.JSONDecodeError:
                    self.log_result("Token Validation", True, f"✅ Token valid (non-JSON response): {response.text[:100]}")
            elif response.status_code == 401:
                self.log_result("Token Validation", False, f"❌ TOKEN INVALID: Unauthorized - {response.text}")
            elif response.status_code == 403:
                self.log_result("Token Validation", False, f"❌ TOKEN FORBIDDEN: Access denied - {response.text}")
            else:
                self.log_result("Token Validation", False, f"❌ UNEXPECTED ERROR: Status {response.status_code} - {response.text}")
                
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Token Validation", False, f"Exception: {str(e)}")

    def test_subscription_status_if_authenticated(self):
        """Test subscription status if authenticated"""
        try:
            print("🔍 INVESTIGATION 6: Testing Subscription Status (if authenticated)")
            print("=" * 80)
            
            if not self.auth_token:
                print("   ⚠️  No auth token available - skipping subscription test")
                self.log_result("Subscription Status", False, "No auth token available")
                print("=" * 80)
                return
            
            print(f"   📊 Testing subscription status for authenticated user")
            
            response = self.make_request("GET", "/subscription/status")
            
            print(f"   📊 Subscription status endpoint status: {response.status_code}")
            print(f"   📊 Subscription status response: {response.text}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   ✅ Subscription status retrieved successfully!")
                    print(f"   📊 Plan: {data.get('plan', 'unknown')}")
                    print(f"   📊 Audience Link Active: {data.get('audience_link_active', 'unknown')}")
                    print(f"   📊 Trial Active: {data.get('trial_active', 'unknown')}")
                    print(f"   📊 Status: {data.get('status', 'unknown')}")
                    
                    self.log_result("Subscription Status", True, f"✅ Subscription status: plan={data.get('plan')}, active={data.get('audience_link_active')}")
                except json.JSONDecodeError:
                    self.log_result("Subscription Status", False, f"❌ Invalid JSON response: {response.text}")
            elif response.status_code == 401:
                self.log_result("Subscription Status", False, f"❌ UNAUTHORIZED: Token invalid for subscription - {response.text}")
            elif response.status_code == 404:
                self.log_result("Subscription Status", False, f"❌ NOT FOUND: Subscription endpoint not found - {response.text}")
            else:
                self.log_result("Subscription Status", False, f"❌ UNEXPECTED ERROR: Status {response.status_code} - {response.text}")
                
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Subscription Status", False, f"Exception: {str(e)}")

    def test_profile_access_if_authenticated(self):
        """Test profile access if authenticated"""
        try:
            print("🔍 INVESTIGATION 7: Testing Profile Access (if authenticated)")
            print("=" * 80)
            
            if not self.auth_token:
                print("   ⚠️  No auth token available - skipping profile test")
                self.log_result("Profile Access", False, "No auth token available")
                print("=" * 80)
                return
            
            print(f"   📊 Testing profile access for authenticated user")
            
            response = self.make_request("GET", "/profile")
            
            print(f"   📊 Profile endpoint status: {response.status_code}")
            print(f"   📊 Profile response: {response.text}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   ✅ Profile retrieved successfully!")
                    print(f"   📊 Name: {data.get('name', 'unknown')}")
                    print(f"   📊 Email: {data.get('email', 'unknown')}")
                    
                    # Check if this matches our expected user
                    if data.get('email') == USER_CREDENTIALS['email']:
                        print(f"   ✅ Profile matches expected user: {USER_CREDENTIALS['email']}")
                        self.log_result("Profile Access", True, f"✅ Profile access successful for {USER_CREDENTIALS['email']}")
                    else:
                        print(f"   ❌ Profile email mismatch: expected {USER_CREDENTIALS['email']}, got {data.get('email')}")
                        self.log_result("Profile Access", False, f"❌ Profile email mismatch")
                        
                except json.JSONDecodeError:
                    self.log_result("Profile Access", False, f"❌ Invalid JSON response: {response.text}")
            elif response.status_code == 401:
                self.log_result("Profile Access", False, f"❌ UNAUTHORIZED: Token invalid for profile - {response.text}")
            elif response.status_code == 404:
                self.log_result("Profile Access", False, f"❌ NOT FOUND: Profile not found - {response.text}")
            else:
                self.log_result("Profile Access", False, f"❌ UNEXPECTED ERROR: Status {response.status_code} - {response.text}")
                
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Profile Access", False, f"Exception: {str(e)}")

    def test_password_reset_flow_if_forgot_password_works(self):
        """Test password reset flow if forgot password endpoint works"""
        try:
            print("🔍 INVESTIGATION 8: Testing Password Reset Flow (if forgot password works)")
            print("=" * 80)
            
            print("   ⚠️  This test requires manual intervention to get reset code from email")
            print("   📊 Testing password reset confirm endpoint with dummy data")
            
            # Test with dummy reset code to see endpoint behavior
            reset_data = {
                "email": USER_CREDENTIALS["email"],
                "reset_code": "123456",  # Dummy code
                "new_password": "NewTestPassword123!"
            }
            
            response = self.make_request("POST", "/auth/reset-password", reset_data)
            
            print(f"   📊 Password reset endpoint status: {response.status_code}")
            print(f"   📊 Password reset response: {response.text}")
            
            if response.status_code == 400:
                if "invalid" in response.text.lower() or "code" in response.text.lower():
                    self.log_result("Password Reset Flow", True, f"✅ Password reset endpoint working (rejected invalid code as expected): {response.text}")
                else:
                    self.log_result("Password Reset Flow", False, f"❌ Unexpected 400 error: {response.text}")
            elif response.status_code == 404:
                self.log_result("Password Reset Flow", False, f"❌ USER NOT FOUND: Email not found for reset - {response.text}")
            elif response.status_code == 200:
                self.log_result("Password Reset Flow", False, f"❌ SECURITY ISSUE: Reset succeeded with dummy code - {response.text}")
            elif response.status_code == 500:
                self.log_result("Password Reset Flow", False, f"❌ SERVER ERROR: Password reset system error - {response.text}")
            else:
                self.log_result("Password Reset Flow", False, f"❌ UNEXPECTED ERROR: Status {response.status_code} - {response.text}")
                
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Password Reset Flow", False, f"Exception: {str(e)}")

    def run_comprehensive_investigation(self):
        """Run comprehensive authentication investigation"""
        print("🔍 COMPREHENSIVE AUTHENTICATION INVESTIGATION")
        print("🔍 User: brycelarsenmusic@gmail.com")
        print("🔍 Context: API connectivity restored, but user still cannot login")
        print("=" * 80)
        
        # Run all investigation tests
        self.test_api_health_check()
        self.test_specific_login_endpoint()
        self.test_forgot_password_endpoint()
        self.test_user_account_existence()
        self.test_token_validation_if_login_successful()
        self.test_subscription_status_if_authenticated()
        self.test_profile_access_if_authenticated()
        self.test_password_reset_flow_if_forgot_password_works()
        
        # Print final summary
        print("\n" + "=" * 80)
        print("🔍 AUTHENTICATION INVESTIGATION SUMMARY")
        print("=" * 80)
        
        total_tests = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.results["errors"]:
            print("\n❌ CRITICAL ISSUES FOUND:")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        # Provide diagnosis
        print("\n🔍 DIAGNOSIS:")
        if self.auth_token:
            print("   ✅ LOGIN WORKING: User can successfully authenticate")
            print("   📊 Issue may be frontend-related or browser cache")
        else:
            print("   ❌ LOGIN FAILING: Authentication system has issues")
            print("   📊 Backend authentication problems confirmed")
        
        print("=" * 80)

if __name__ == "__main__":
    tester = AuthInvestigationTester()
    tester.run_comprehensive_investigation()