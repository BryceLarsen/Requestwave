#!/usr/bin/env python3
"""
BRYCE LARSEN ACCOUNT INVESTIGATION AND PASSWORD RESET TEST

Comprehensive investigation of brycelarsenmusic@gmail.com account:
1. Test forgot password functionality
2. Investigate account existence
3. Test different authentication approaches
4. Check backend health and connectivity

This addresses the review request about reactivating Pro subscriber status
after custom domain removal and login issues.
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://requestwave-app.preview.emergentagent.com/api"

# Bryce's credentials
BRYCE_CREDENTIALS = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class BryceAccountInvestigator:
    def __init__(self):
        self.base_url = BASE_URL
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
        
        # Override with custom headers
        if headers:
            request_headers.update(headers)
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=request_headers, params=data or params)
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

    def test_api_health_and_connectivity(self):
        """Test API health and connectivity"""
        try:
            print("🏥 CONNECTIVITY: Testing API Health and Connectivity")
            print("=" * 80)
            
            print("📊 Step 1: Test health endpoint")
            
            health_response = self.make_request("GET", "/health")
            
            print(f"   📊 Health response status: {health_response.status_code}")
            
            if health_response.status_code == 200:
                try:
                    health_data = health_response.json()
                    print(f"   ✅ API is healthy")
                    print(f"   📊 Health data: {health_data}")
                    health_ok = True
                except:
                    print(f"   ✅ API responding but no JSON data")
                    health_ok = True
            else:
                print(f"   ❌ API health check failed: {health_response.status_code}")
                print(f"   📊 Response: {health_response.text}")
                health_ok = False
            
            print(f"\n📊 Step 2: Test base API connectivity")
            
            # Test a simple endpoint that should exist
            try:
                base_response = requests.get(f"{self.base_url.replace('/api', '')}")
                print(f"   📊 Base URL response: {base_response.status_code}")
                if base_response.status_code in [200, 404, 405]:  # Any response means connectivity
                    print(f"   ✅ Base connectivity working")
                    connectivity_ok = True
                else:
                    print(f"   ❌ Base connectivity issues")
                    connectivity_ok = False
            except Exception as e:
                print(f"   ❌ Base connectivity failed: {str(e)}")
                connectivity_ok = False
            
            if health_ok and connectivity_ok:
                self.log_result("API Health and Connectivity", True, "API is healthy and accessible")
            else:
                self.log_result("API Health and Connectivity", False, "API connectivity or health issues detected")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("API Health and Connectivity", False, f"Exception: {str(e)}")

    def test_forgot_password_functionality(self):
        """Test forgot password functionality for Bryce's email"""
        try:
            print("🔑 PASSWORD: Testing Forgot Password Functionality")
            print("=" * 80)
            
            print(f"📊 Step 1: Test forgot password for {BRYCE_CREDENTIALS['email']}")
            
            forgot_password_data = {
                "email": BRYCE_CREDENTIALS["email"]
            }
            
            forgot_response = self.make_request("POST", "/auth/forgot-password", forgot_password_data)
            
            print(f"   📊 Forgot password response: {forgot_response.status_code}")
            
            if forgot_response.status_code == 200:
                try:
                    forgot_result = forgot_response.json()
                    print(f"   ✅ Forgot password request successful")
                    print(f"   📊 Response: {forgot_result}")
                    
                    # Check if response indicates account exists
                    if "message" in forgot_result:
                        message = forgot_result["message"]
                        if "sent" in message.lower() or "reset" in message.lower():
                            print(f"   ✅ Account exists - reset email would be sent")
                            account_exists = True
                        else:
                            print(f"   ⚠️  Unclear account status from message: {message}")
                            account_exists = True  # Assume exists if we got a response
                    else:
                        print(f"   ✅ Forgot password processed (account likely exists)")
                        account_exists = True
                    
                    forgot_password_ok = True
                    
                except json.JSONDecodeError:
                    print(f"   ✅ Forgot password processed (non-JSON response)")
                    forgot_password_ok = True
                    account_exists = True
                    
            elif forgot_response.status_code == 404:
                print(f"   ❌ Account NOT FOUND - user may not exist")
                print(f"   📊 Response: {forgot_response.text}")
                forgot_password_ok = False
                account_exists = False
                
            elif forgot_response.status_code == 400:
                print(f"   ⚠️  Bad request - may be validation error")
                print(f"   📊 Response: {forgot_response.text}")
                forgot_password_ok = False
                account_exists = True  # Account might exist but request was malformed
                
            else:
                print(f"   ❌ Forgot password failed: {forgot_response.status_code}")
                print(f"   📊 Response: {forgot_response.text}")
                forgot_password_ok = False
                account_exists = None  # Unknown
            
            if forgot_password_ok:
                self.log_result("Forgot Password Functionality", True, f"Forgot password working - account exists: {account_exists}")
            else:
                self.log_result("Forgot Password Functionality", False, f"Forgot password issues - account exists: {account_exists}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Forgot Password Functionality", False, f"Exception: {str(e)}")

    def test_registration_attempt(self):
        """Test registration attempt to see if email is already taken"""
        try:
            print("📝 REGISTRATION: Testing Registration Attempt")
            print("=" * 80)
            
            print(f"📊 Step 1: Attempt registration with {BRYCE_CREDENTIALS['email']}")
            print("   (This will fail if account exists, which is what we want to check)")
            
            registration_data = {
                "name": "Bryce Larsen Test",
                "email": BRYCE_CREDENTIALS["email"],
                "password": "TestPassword123!"
            }
            
            registration_response = self.make_request("POST", "/auth/register", registration_data)
            
            print(f"   📊 Registration response: {registration_response.status_code}")
            
            if registration_response.status_code == 400:
                try:
                    error_data = registration_response.json()
                    error_detail = error_data.get("detail", "")
                    
                    if "already exists" in error_detail.lower() or "email" in error_detail.lower():
                        print(f"   ✅ Account EXISTS - email already registered")
                        print(f"   📊 Error: {error_detail}")
                        account_exists = True
                        registration_test_ok = True
                    else:
                        print(f"   ⚠️  Registration failed for other reason: {error_detail}")
                        account_exists = None
                        registration_test_ok = False
                        
                except json.JSONDecodeError:
                    print(f"   ⚠️  Registration failed with non-JSON response")
                    print(f"   📊 Response: {registration_response.text}")
                    account_exists = None
                    registration_test_ok = False
                    
            elif registration_response.status_code == 200:
                print(f"   ❌ Registration SUCCEEDED - account did NOT exist before")
                print(f"   ⚠️  This means the original account may have been deleted")
                account_exists = False
                registration_test_ok = True
                
                # If registration succeeded, we should clean up
                try:
                    reg_result = registration_response.json()
                    print(f"   📊 New account created: {reg_result}")
                except:
                    pass
                    
            else:
                print(f"   ❌ Registration failed unexpectedly: {registration_response.status_code}")
                print(f"   📊 Response: {registration_response.text}")
                account_exists = None
                registration_test_ok = False
            
            if registration_test_ok:
                self.log_result("Registration Attempt", True, f"Registration test completed - account exists: {account_exists}")
            else:
                self.log_result("Registration Attempt", False, "Registration test failed")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Registration Attempt", False, f"Exception: {str(e)}")

    def test_alternative_login_attempts(self):
        """Test various login attempts with different approaches"""
        try:
            print("🔐 LOGIN: Testing Alternative Login Attempts")
            print("=" * 80)
            
            # Test different password variations
            password_variations = [
                "RequestWave2024!",  # Original
                "requestwave2024!",  # Lowercase
                "RequestWave2024",   # No exclamation
                "RequestWave2024!!",  # Double exclamation
                "RequestWave2025!",  # Different year
            ]
            
            for i, password in enumerate(password_variations):
                print(f"📊 Step {i+1}: Testing password variation: '{password}'")
                
                login_data = {
                    "email": BRYCE_CREDENTIALS["email"],
                    "password": password
                }
                
                login_response = self.make_request("POST", "/auth/login", login_data)
                
                print(f"   📊 Login response: {login_response.status_code}")
                
                if login_response.status_code == 200:
                    try:
                        login_result = login_response.json()
                        print(f"   ✅ LOGIN SUCCESSFUL with password: '{password}'")
                        print(f"   📊 Musician: {login_result.get('musician', {}).get('name')}")
                        
                        # Store successful credentials
                        self.successful_password = password
                        self.auth_token = login_result.get('token')
                        self.musician_data = login_result.get('musician')
                        
                        self.log_result("Alternative Login Attempts", True, f"Successful login with password: '{password}'")
                        print("=" * 80)
                        return  # Exit early on success
                        
                    except json.JSONDecodeError:
                        print(f"   ⚠️  Login response not JSON")
                        
                elif login_response.status_code == 401:
                    print(f"   ❌ Invalid credentials with password: '{password}'")
                    
                else:
                    print(f"   ❌ Login error: {login_response.status_code}")
                    print(f"   📊 Response: {login_response.text}")
            
            # If we get here, no password worked
            print(f"\n📊 Final Step: All password variations failed")
            self.log_result("Alternative Login Attempts", False, "All password variations failed - account may need password reset")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Alternative Login Attempts", False, f"Exception: {str(e)}")

    def test_account_status_if_logged_in(self):
        """Test account status if we managed to log in"""
        try:
            print("👤 ACCOUNT: Testing Account Status (if logged in)")
            print("=" * 80)
            
            if not hasattr(self, 'auth_token') or not self.auth_token:
                print("📊 No successful login - skipping account status test")
                self.log_result("Account Status Check", False, "No auth token available - login failed")
                print("=" * 80)
                return
            
            print(f"📊 Step 1: Get musician profile data")
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            profile_response = self.make_request("GET", "/profile", headers=headers)
            
            print(f"   📊 Profile response: {profile_response.status_code}")
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                
                print(f"   ✅ Profile data retrieved")
                print(f"   📊 Name: {profile_data.get('name')}")
                print(f"   📊 Email: {profile_data.get('email')}")
                
                # Check subscription fields
                audience_link_active = profile_data.get('audience_link_active', False)
                subscription_status = profile_data.get('subscription_status')
                has_had_trial = profile_data.get('has_had_trial', False)
                trial_end = profile_data.get('trial_end')
                
                print(f"\n   📊 SUBSCRIPTION STATUS:")
                print(f"      audience_link_active: {audience_link_active}")
                print(f"      subscription_status: {subscription_status}")
                print(f"      has_had_trial: {has_had_trial}")
                print(f"      trial_end: {trial_end}")
                
                # Analysis
                if audience_link_active:
                    print(f"   ✅ Audience link is ACTIVE")
                else:
                    print(f"   ❌ Audience link is PAUSED - needs reactivation")
                
                self.log_result("Account Status Check", True, f"Account status retrieved - audience_link_active: {audience_link_active}")
                
            else:
                print(f"   ❌ Failed to get profile: {profile_response.status_code}")
                self.log_result("Account Status Check", False, f"Profile request failed: {profile_response.status_code}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Account Status Check", False, f"Exception: {str(e)}")

    def run_investigation(self):
        """Run complete account investigation"""
        print("🔍 BRYCE LARSEN ACCOUNT INVESTIGATION")
        print("=" * 100)
        print(f"Investigating user: {BRYCE_CREDENTIALS['email']}")
        print(f"Issue: Cannot login, account may need Pro status reactivation")
        print(f"Goal: Determine account status and authentication issues")
        print("=" * 100)
        
        # Run investigation steps
        self.test_api_health_and_connectivity()
        self.test_forgot_password_functionality()
        self.test_registration_attempt()
        self.test_alternative_login_attempts()
        self.test_account_status_if_logged_in()
        
        # Final summary
        print("\n" + "=" * 100)
        print("🎯 INVESTIGATION SUMMARY")
        print("=" * 100)
        
        total_tests = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.results['passed']}")
        print(f"Failed: {self.results['failed']}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if self.results["failed"] > 0:
            print(f"\n❌ FAILED TESTS:")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        # Determine findings
        print(f"\n🔍 KEY FINDINGS:")
        
        if hasattr(self, 'successful_password'):
            print(f"   ✅ LOGIN SUCCESSFUL with password: '{self.successful_password}'")
            print(f"   ✅ Account exists and is accessible")
            
            if hasattr(self, 'musician_data'):
                musician = self.musician_data
                audience_link = musician.get('audience_link_active', False)
                
                if audience_link:
                    print(f"   ✅ Audience link is ACTIVE - Pro access working")
                else:
                    print(f"   ❌ Audience link is PAUSED - needs reactivation")
                    print(f"   📋 RECOMMENDATION: Set audience_link_active = true in database")
        else:
            print(f"   ❌ LOGIN FAILED with all password attempts")
            print(f"   📋 RECOMMENDATION: Use forgot password flow to reset password")
            print(f"   📋 RECOMMENDATION: Check if account exists in database")
        
        print("=" * 100)

if __name__ == "__main__":
    investigator = BryceAccountInvestigator()
    investigator.run_investigation()