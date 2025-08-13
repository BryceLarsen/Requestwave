#!/usr/bin/env python3
"""
USER ACCOUNT INVESTIGATION: brycelarsenmusic@gmail.com

SPECIFIC INVESTIGATION NEEDED:
1. Check User Account Status - verify account exists and password field is set
2. Test Login Functionality - try login with brycelarsenmusic@gmail.com / RequestWave2024!
3. Test Forgot Password Functionality - test POST /api/auth/forgot-password
4. Check Account Integrity - verify user record wasn't corrupted during Pro activation
5. Password Reset Option - verify password reset endpoint functionality

FOCUS: Determine why user cannot login and why forgot password is failing
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://requestwave.app/api"

# Test user credentials
TEST_USER = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class UserAccountInvestigator:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
        self.results = {
            "passed": 0,
            "failed": 0,
            "errors": [],
            "findings": []
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

    def log_finding(self, finding: str):
        """Log investigation finding"""
        print(f"🔍 FINDING: {finding}")
        self.results["findings"].append(finding)

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

    def test_api_health(self):
        """Test API health to ensure backend is accessible"""
        try:
            print("🔍 INVESTIGATION 1: API Health Check")
            print("=" * 80)
            
            response = self.make_request("GET", "/health")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "status" in data and data["status"] == "healthy":
                        self.log_result("API Health Check", True, "Backend API is accessible and healthy")
                        self.log_finding("Backend API is running and accessible at https://requestwave.app/api")
                    else:
                        self.log_result("API Health Check", False, f"Unexpected health response: {data}")
                except:
                    self.log_result("API Health Check", True, "API responding (non-JSON health check)")
            else:
                self.log_result("API Health Check", False, f"API health check failed with status: {response.status_code}")
                self.log_finding(f"Backend API may be down or misconfigured - status code: {response.status_code}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("API Health Check", False, f"Exception: {str(e)}")
            self.log_finding(f"Cannot reach backend API: {str(e)}")

    def test_user_login_attempt(self):
        """Test login functionality with user's credentials"""
        try:
            print("🔍 INVESTIGATION 2: User Login Attempt")
            print("=" * 80)
            
            print(f"📊 Attempting login with: {TEST_USER['email']}")
            print(f"📊 Password: {'*' * len(TEST_USER['password'])}")
            
            login_data = {
                "email": TEST_USER["email"],
                "password": TEST_USER["password"]
            }
            
            response = self.make_request("POST", "/auth/login", login_data)
            
            print(f"📊 Login response status: {response.status_code}")
            print(f"📊 Login response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "token" in data and "musician" in data:
                        self.auth_token = data["token"]
                        self.musician_id = data["musician"]["id"]
                        self.musician_slug = data["musician"]["slug"]
                        
                        self.log_result("User Login", True, f"✅ LOGIN SUCCESSFUL for {data['musician']['name']}")
                        self.log_finding(f"User account exists and password is correct")
                        self.log_finding(f"User ID: {self.musician_id}")
                        self.log_finding(f"User slug: {self.musician_slug}")
                        self.log_finding(f"JWT token generated successfully")
                        
                        # Check musician data
                        musician = data["musician"]
                        print(f"   📊 Musician Name: {musician.get('name')}")
                        print(f"   📊 Musician Email: {musician.get('email')}")
                        print(f"   📊 Musician Slug: {musician.get('slug')}")
                        print(f"   📊 Account Created: {musician.get('created_at', 'Unknown')}")
                        
                        # Check subscription-related fields
                        if 'audience_link_active' in musician:
                            print(f"   📊 Audience Link Active: {musician.get('audience_link_active')}")
                        if 'has_had_trial' in musician:
                            print(f"   📊 Has Had Trial: {musician.get('has_had_trial')}")
                        if 'trial_end' in musician:
                            print(f"   📊 Trial End: {musician.get('trial_end')}")
                        
                    else:
                        self.log_result("User Login", False, f"Login response missing token or musician data: {data}")
                        self.log_finding("Login endpoint returned success but with incomplete data")
                except json.JSONDecodeError:
                    self.log_result("User Login", False, "Login response is not valid JSON")
                    self.log_finding("Login endpoint returned non-JSON response")
                    
            elif response.status_code == 401:
                self.log_result("User Login", False, "❌ LOGIN FAILED - Invalid credentials (401 Unauthorized)")
                self.log_finding("CRITICAL: User credentials are incorrect or account doesn't exist")
                
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", "No error details provided")
                    print(f"   📊 Error details: {error_detail}")
                    self.log_finding(f"Login error details: {error_detail}")
                except:
                    print(f"   📊 Raw response: {response.text}")
                    
            elif response.status_code == 400:
                self.log_result("User Login", False, "❌ LOGIN FAILED - Bad request (400)")
                self.log_finding("Login request format may be incorrect")
                
                try:
                    error_data = response.json()
                    print(f"   📊 Error details: {error_data}")
                    self.log_finding(f"Login validation error: {error_data}")
                except:
                    print(f"   📊 Raw response: {response.text}")
                    
            else:
                self.log_result("User Login", False, f"❌ LOGIN FAILED - Unexpected status code: {response.status_code}")
                self.log_finding(f"Login endpoint returned unexpected status: {response.status_code}")
                print(f"   📊 Response: {response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("User Login", False, f"Exception during login: {str(e)}")
            self.log_finding(f"Login attempt failed with exception: {str(e)}")

    def test_forgot_password_functionality(self):
        """Test forgot password functionality"""
        try:
            print("🔍 INVESTIGATION 3: Forgot Password Functionality")
            print("=" * 80)
            
            print(f"📊 Testing forgot password for: {TEST_USER['email']}")
            
            forgot_password_data = {
                "email": TEST_USER["email"]
            }
            
            response = self.make_request("POST", "/auth/forgot-password", forgot_password_data)
            
            print(f"📊 Forgot password response status: {response.status_code}")
            print(f"📊 Forgot password response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.log_result("Forgot Password", True, "✅ FORGOT PASSWORD REQUEST SUCCESSFUL")
                    self.log_finding("Forgot password endpoint is working correctly")
                    print(f"   📊 Response: {data}")
                    
                    if "message" in data:
                        self.log_finding(f"Forgot password message: {data['message']}")
                        
                except json.JSONDecodeError:
                    self.log_result("Forgot Password", True, "Forgot password request successful (non-JSON response)")
                    self.log_finding("Forgot password endpoint working but returned non-JSON response")
                    
            elif response.status_code == 404:
                self.log_result("Forgot Password", False, "❌ FORGOT PASSWORD FAILED - User not found (404)")
                self.log_finding("CRITICAL: User account does not exist in the system")
                
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", "No error details provided")
                    print(f"   📊 Error details: {error_detail}")
                    self.log_finding(f"Forgot password error: {error_detail}")
                except:
                    print(f"   📊 Raw response: {response.text}")
                    
            elif response.status_code == 400:
                self.log_result("Forgot Password", False, "❌ FORGOT PASSWORD FAILED - Bad request (400)")
                self.log_finding("Forgot password request format may be incorrect")
                
                try:
                    error_data = response.json()
                    print(f"   📊 Error details: {error_data}")
                    self.log_finding(f"Forgot password validation error: {error_data}")
                except:
                    print(f"   📊 Raw response: {response.text}")
                    
            elif response.status_code == 500:
                self.log_result("Forgot Password", False, "❌ FORGOT PASSWORD FAILED - Server error (500)")
                self.log_finding("CRITICAL: Server error during forgot password - possible email service issue")
                
                try:
                    error_data = response.json()
                    print(f"   📊 Error details: {error_data}")
                    self.log_finding(f"Server error details: {error_data}")
                except:
                    print(f"   📊 Raw response: {response.text}")
                    
            else:
                self.log_result("Forgot Password", False, f"❌ FORGOT PASSWORD FAILED - Unexpected status: {response.status_code}")
                self.log_finding(f"Forgot password endpoint returned unexpected status: {response.status_code}")
                print(f"   📊 Response: {response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Forgot Password", False, f"Exception during forgot password: {str(e)}")
            self.log_finding(f"Forgot password attempt failed with exception: {str(e)}")

    def test_subscription_status_if_logged_in(self):
        """Test subscription status if user is logged in"""
        try:
            if not self.auth_token:
                print("🔍 INVESTIGATION 4: Subscription Status (SKIPPED - No Auth Token)")
                print("=" * 80)
                self.log_finding("Cannot check subscription status - user login failed")
                print("   ⚠️  Skipping subscription status check - no authentication token")
                print("=" * 80)
                return
                
            print("🔍 INVESTIGATION 4: Subscription Status Check")
            print("=" * 80)
            
            print(f"📊 Checking subscription status for authenticated user")
            
            response = self.make_request("GET", "/subscription/status")
            
            print(f"📊 Subscription status response: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.log_result("Subscription Status", True, "✅ SUBSCRIPTION STATUS RETRIEVED")
                    self.log_finding("User subscription status is accessible")
                    
                    print(f"   📊 Subscription Status: {json.dumps(data, indent=2)}")
                    
                    # Analyze subscription data
                    plan = data.get("plan", "unknown")
                    audience_link_active = data.get("audience_link_active", False)
                    trial_active = data.get("trial_active", False)
                    
                    self.log_finding(f"User plan: {plan}")
                    self.log_finding(f"Audience link active: {audience_link_active}")
                    self.log_finding(f"Trial active: {trial_active}")
                    
                    if plan == "canceled":
                        self.log_finding("⚠️  User has canceled subscription - may affect access")
                    elif plan == "trial":
                        self.log_finding("User is on trial period")
                    elif plan == "pro":
                        self.log_finding("User has active Pro subscription")
                        
                except json.JSONDecodeError:
                    self.log_result("Subscription Status", False, "Subscription status response is not valid JSON")
                    self.log_finding("Subscription status endpoint returned non-JSON response")
                    
            elif response.status_code == 401:
                self.log_result("Subscription Status", False, "❌ SUBSCRIPTION STATUS FAILED - Unauthorized")
                self.log_finding("JWT token may be invalid or expired")
                
            elif response.status_code == 404:
                self.log_result("Subscription Status", False, "❌ SUBSCRIPTION STATUS FAILED - Endpoint not found")
                self.log_finding("Subscription status endpoint may not exist")
                
            else:
                self.log_result("Subscription Status", False, f"❌ SUBSCRIPTION STATUS FAILED - Status: {response.status_code}")
                self.log_finding(f"Subscription status check failed with status: {response.status_code}")
                print(f"   📊 Response: {response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Subscription Status", False, f"Exception during subscription status check: {str(e)}")
            self.log_finding(f"Subscription status check failed with exception: {str(e)}")

    def test_password_reset_endpoint(self):
        """Test password reset endpoint functionality"""
        try:
            print("🔍 INVESTIGATION 5: Password Reset Endpoint Test")
            print("=" * 80)
            
            print(f"📊 Testing password reset endpoint structure")
            
            # Test with dummy data to see if endpoint exists and what it expects
            test_reset_data = {
                "email": TEST_USER["email"],
                "reset_code": "dummy_code",
                "new_password": "DummyPassword123!"
            }
            
            response = self.make_request("POST", "/auth/reset-password", test_reset_data)
            
            print(f"📊 Password reset response status: {response.status_code}")
            
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    self.log_result("Password Reset Endpoint", True, "✅ PASSWORD RESET ENDPOINT EXISTS")
                    self.log_finding("Password reset endpoint is available and validates input")
                    print(f"   📊 Validation error (expected): {error_data}")
                    
                    if "reset_code" in str(error_data) or "code" in str(error_data):
                        self.log_finding("Password reset requires valid reset code")
                    
                except json.JSONDecodeError:
                    self.log_result("Password Reset Endpoint", True, "Password reset endpoint exists (non-JSON error)")
                    
            elif response.status_code == 404:
                self.log_result("Password Reset Endpoint", False, "❌ PASSWORD RESET ENDPOINT NOT FOUND")
                self.log_finding("CRITICAL: Password reset endpoint does not exist")
                
            elif response.status_code == 422:
                try:
                    error_data = response.json()
                    self.log_result("Password Reset Endpoint", True, "✅ PASSWORD RESET ENDPOINT EXISTS")
                    self.log_finding("Password reset endpoint exists and validates input (422 validation error)")
                    print(f"   📊 Validation details: {error_data}")
                except:
                    self.log_result("Password Reset Endpoint", True, "Password reset endpoint exists")
                    
            elif response.status_code == 500:
                self.log_result("Password Reset Endpoint", False, "❌ PASSWORD RESET SERVER ERROR")
                self.log_finding("Password reset endpoint exists but has server error")
                
            else:
                self.log_result("Password Reset Endpoint", False, f"❌ UNEXPECTED RESPONSE: {response.status_code}")
                self.log_finding(f"Password reset endpoint returned unexpected status: {response.status_code}")
                print(f"   📊 Response: {response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Password Reset Endpoint", False, f"Exception during password reset test: {str(e)}")
            self.log_finding(f"Password reset test failed with exception: {str(e)}")

    def test_user_registration_attempt(self):
        """Test if user can be registered (to check if account exists)"""
        try:
            print("🔍 INVESTIGATION 6: User Account Existence Check")
            print("=" * 80)
            
            print(f"📊 Attempting registration to check if account exists")
            
            # Try to register with same email to see if account exists
            registration_data = {
                "name": "Test Registration",
                "email": TEST_USER["email"],
                "password": "TestPassword123!"
            }
            
            response = self.make_request("POST", "/auth/register", registration_data)
            
            print(f"📊 Registration attempt response: {response.status_code}")
            
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    if "already exists" in str(error_data).lower() or "email" in str(error_data).lower():
                        self.log_result("Account Existence Check", True, "✅ ACCOUNT EXISTS")
                        self.log_finding("User account definitely exists in the database")
                        print(f"   📊 Registration error (expected): {error_data}")
                    else:
                        self.log_result("Account Existence Check", False, f"Unexpected registration error: {error_data}")
                        
                except json.JSONDecodeError:
                    self.log_result("Account Existence Check", True, "Account likely exists (registration blocked)")
                    
            elif response.status_code == 200:
                # This would be unexpected - means account didn't exist
                self.log_result("Account Existence Check", False, "❌ ACCOUNT DOES NOT EXIST")
                self.log_finding("CRITICAL: User account does not exist in the database")
                
                try:
                    data = response.json()
                    print(f"   📊 New account created: {data}")
                    self.log_finding("New account was created - original account missing")
                except:
                    pass
                    
            elif response.status_code == 422:
                try:
                    error_data = response.json()
                    self.log_result("Account Existence Check", True, "Account existence unclear (validation error)")
                    self.log_finding("Registration validation error - account status unclear")
                    print(f"   📊 Validation error: {error_data}")
                except:
                    pass
                    
            else:
                self.log_result("Account Existence Check", False, f"Unexpected registration response: {response.status_code}")
                self.log_finding(f"Registration attempt returned unexpected status: {response.status_code}")
                print(f"   📊 Response: {response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Account Existence Check", False, f"Exception during account existence check: {str(e)}")
            self.log_finding(f"Account existence check failed with exception: {str(e)}")

    def generate_investigation_report(self):
        """Generate comprehensive investigation report"""
        print("\n" + "=" * 100)
        print("🔍 COMPREHENSIVE INVESTIGATION REPORT")
        print("=" * 100)
        
        print(f"\n📊 INVESTIGATION SUMMARY:")
        print(f"   • Tests Passed: {self.results['passed']}")
        print(f"   • Tests Failed: {self.results['failed']}")
        print(f"   • Total Findings: {len(self.results['findings'])}")
        
        print(f"\n🔍 KEY FINDINGS:")
        for i, finding in enumerate(self.results['findings'], 1):
            print(f"   {i}. {finding}")
        
        if self.results['errors']:
            print(f"\n❌ ERRORS ENCOUNTERED:")
            for i, error in enumerate(self.results['errors'], 1):
                print(f"   {i}. {error}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        
        # Analyze findings and provide recommendations
        findings_text = " ".join(self.results['findings']).lower()
        
        if "login successful" in findings_text:
            print("   ✅ User login is working correctly - no authentication issues found")
            print("   ✅ User should be able to access their account normally")
        elif "invalid credentials" in findings_text or "login failed" in findings_text:
            print("   ❌ CRITICAL: User credentials are incorrect or account has issues")
            print("   🔧 RECOMMENDED ACTIONS:")
            print("      - Verify user is using correct password: RequestWave2024!")
            print("      - Check if account was corrupted during Pro activation")
            print("      - Consider manual password reset in database")
            
        if "forgot password" in findings_text and "successful" in findings_text:
            print("   ✅ Forgot password functionality is working")
            print("   💡 User can use forgot password feature to reset their password")
        elif "forgot password" in findings_text and ("failed" in findings_text or "error" in findings_text):
            print("   ❌ CRITICAL: Forgot password functionality is broken")
            print("   🔧 RECOMMENDED ACTIONS:")
            print("      - Check email service configuration")
            print("      - Verify forgot password endpoint implementation")
            print("      - Check database connectivity for password reset tokens")
            
        if "account does not exist" in findings_text:
            print("   ❌ CRITICAL: User account is missing from database")
            print("   🔧 RECOMMENDED ACTIONS:")
            print("      - Check if account was accidentally deleted during Pro activation")
            print("      - Restore account from backup if available")
            print("      - Manual account recreation may be required")
            
        if "subscription" in findings_text and "canceled" in findings_text:
            print("   ⚠️  User has canceled subscription status")
            print("   💡 This may affect access to Pro features but shouldn't prevent login")
            
        print(f"\n🎯 NEXT STEPS:")
        if self.auth_token:
            print("   1. User authentication is working - investigate specific feature issues")
            print("   2. Check Pro feature access and subscription status")
            print("   3. Test playlist creation and other Pro features")
        else:
            print("   1. PRIORITY: Fix user authentication issues")
            print("   2. Investigate database integrity for this user account")
            print("   3. Implement manual password reset if needed")
            print("   4. Test forgot password email delivery")
        
        print("=" * 100)

    def run_full_investigation(self):
        """Run complete investigation"""
        print("🔍 STARTING COMPREHENSIVE USER ACCOUNT INVESTIGATION")
        print(f"📧 Target User: {TEST_USER['email']}")
        print(f"🌐 Backend URL: {self.base_url}")
        print("=" * 100)
        
        # Run all investigation steps
        self.test_api_health()
        self.test_user_login_attempt()
        self.test_forgot_password_functionality()
        self.test_subscription_status_if_logged_in()
        self.test_password_reset_endpoint()
        self.test_user_registration_attempt()
        
        # Generate comprehensive report
        self.generate_investigation_report()

def main():
    """Main execution function"""
    investigator = UserAccountInvestigator()
    investigator.run_full_investigation()

if __name__ == "__main__":
    main()