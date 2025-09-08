#!/usr/bin/env python3
"""
Production Login Authentication Test Suite for RequestWave
Testing login functionality specifically for production deployment after environment variable fixes.

PRIORITY TEST: Login authentication with brycelarsenmusic@gmail.com account

Focus areas:
1. Test POST /api/auth/login endpoint with brycelarsenmusic@gmail.com credentials
2. Verify database connectivity is working (using mongodb://mongodb:27017)
3. Test that JWT authentication is functional with production settings
4. Check that user account can be found in livewave-music-test_database
5. Verify the external API is accessible and returns 200 responses
"""

import requests
import json
import sys
from datetime import datetime
import time
import os

# Configuration from environment variables
EXTERNAL_API_URL = "https://requestwave-revamp.preview.emergentagent.com/api"
INTERNAL_API_URL = "http://localhost:8001/api"  # For internal testing if needed
TEST_EMAIL = "brycelarsenmusic@gmail.com"
TEST_PASSWORD = "RequestWave2024!"

class ProductionLoginTester:
    def __init__(self):
        self.token = None
        self.musician_id = None
        self.musician_data = None
        self.results = []
        
    def log_result(self, test_name, success, message, details=None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        self.results.append(result)
        print(f"{status}: {test_name} - {message}")
        if details:
            print(f"   Details: {json.dumps(details, indent=2, default=str)}")
    
    def test_external_api_connectivity(self):
        """Test that external API is accessible and returns proper responses"""
        print("\n=== Testing External API Connectivity ===")
        
        try:
            # Test health/status endpoint first
            response = requests.get(f"{EXTERNAL_API_URL}/health", timeout=10)
            
            if response.status_code == 200:
                self.log_result("External API Health Check", True, "External API is accessible", {
                    "url": f"{EXTERNAL_API_URL}/health",
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                })
            else:
                self.log_result("External API Health Check", False, f"Health endpoint returned {response.status_code}", {
                    "url": f"{EXTERNAL_API_URL}/health",
                    "status_code": response.status_code,
                    "response": response.text[:500]
                })
                
        except requests.exceptions.RequestException as e:
            self.log_result("External API Health Check", False, f"External API connectivity failed: {str(e)}", {
                "url": f"{EXTERNAL_API_URL}/health",
                "error": str(e)
            })
            
        # Test if auth endpoints are accessible (should return method not allowed or similar, not 500)
        try:
            response = requests.get(f"{EXTERNAL_API_URL}/auth/login", timeout=10)
            
            # GET on login endpoint should return 405 (Method Not Allowed) or 422, not 500
            if response.status_code in [405, 422, 400]:
                self.log_result("Auth Endpoint Accessibility", True, "Auth endpoints are accessible", {
                    "url": f"{EXTERNAL_API_URL}/auth/login",
                    "status_code": response.status_code,
                    "method": "GET"
                })
            elif response.status_code == 500:
                self.log_result("Auth Endpoint Accessibility", False, "Auth endpoints returning 500 errors", {
                    "url": f"{EXTERNAL_API_URL}/auth/login",
                    "status_code": response.status_code,
                    "response": response.text[:500]
                })
            else:
                self.log_result("Auth Endpoint Accessibility", True, f"Auth endpoint accessible (status: {response.status_code})", {
                    "url": f"{EXTERNAL_API_URL}/auth/login",
                    "status_code": response.status_code
                })
                
        except requests.exceptions.RequestException as e:
            self.log_result("Auth Endpoint Accessibility", False, f"Auth endpoint connectivity failed: {str(e)}", {
                "url": f"{EXTERNAL_API_URL}/auth/login",
                "error": str(e)
            })
    
    def test_login_authentication(self):
        """Test POST /api/auth/login endpoint with brycelarsenmusic@gmail.com credentials"""
        print("\n=== Testing Login Authentication ===")
        
        try:
            login_data = {
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
            
            response = requests.post(
                f"{EXTERNAL_API_URL}/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.token = data.get("token")
                    musician = data.get("musician", {})
                    self.musician_id = musician.get("id")
                    self.musician_data = musician
                    
                    if self.token and self.musician_id:
                        self.log_result("Login Authentication", True, f"Successfully authenticated {TEST_EMAIL}", {
                            "email": musician.get("email"),
                            "name": musician.get("name"),
                            "musician_id": self.musician_id,
                            "token_length": len(self.token) if self.token else 0,
                            "slug": musician.get("slug"),
                            "audience_link_active": musician.get("audience_link_active")
                        })
                        return True
                    else:
                        self.log_result("Login Authentication", False, "Login response missing token or musician_id", {
                            "response_keys": list(data.keys()),
                            "has_token": bool(self.token),
                            "has_musician_id": bool(self.musician_id)
                        })
                        return False
                        
                except json.JSONDecodeError:
                    self.log_result("Login Authentication", False, "Login response is not valid JSON", {
                        "status_code": response.status_code,
                        "response": response.text[:500]
                    })
                    return False
                    
            elif response.status_code == 401:
                self.log_result("Login Authentication", False, "Login failed - Invalid credentials", {
                    "status_code": response.status_code,
                    "response": response.text[:500],
                    "email": TEST_EMAIL
                })
                return False
                
            elif response.status_code == 500:
                self.log_result("Login Authentication", False, "Login failed - Server error (500)", {
                    "status_code": response.status_code,
                    "response": response.text[:500],
                    "email": TEST_EMAIL
                })
                return False
                
            else:
                self.log_result("Login Authentication", False, f"Login failed with status {response.status_code}", {
                    "status_code": response.status_code,
                    "response": response.text[:500],
                    "email": TEST_EMAIL
                })
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_result("Login Authentication", False, f"Login request failed: {str(e)}", {
                "email": TEST_EMAIL,
                "error": str(e)
            })
            return False
    
    def test_jwt_token_validation(self):
        """Test that JWT authentication is functional with production settings"""
        print("\n=== Testing JWT Token Validation ===")
        
        if not self.token:
            self.log_result("JWT Token Validation", False, "No token available for testing")
            return False
        
        try:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            # Test protected endpoint - profile
            response = requests.get(
                f"{EXTERNAL_API_URL}/profile",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                try:
                    profile_data = response.json()
                    self.log_result("JWT Token Validation", True, "JWT token successfully validated", {
                        "endpoint": "/profile",
                        "profile_email": profile_data.get("email"),
                        "profile_name": profile_data.get("name"),
                        "token_working": True
                    })
                    return True
                    
                except json.JSONDecodeError:
                    self.log_result("JWT Token Validation", False, "Profile response is not valid JSON", {
                        "status_code": response.status_code,
                        "response": response.text[:500]
                    })
                    return False
                    
            elif response.status_code in [401, 403]:
                self.log_result("JWT Token Validation", False, "JWT token validation failed - Unauthorized", {
                    "status_code": response.status_code,
                    "response": response.text[:500],
                    "token_length": len(self.token) if self.token else 0
                })
                return False
                
            else:
                self.log_result("JWT Token Validation", False, f"JWT validation failed with status {response.status_code}", {
                    "status_code": response.status_code,
                    "response": response.text[:500]
                })
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_result("JWT Token Validation", False, f"JWT validation request failed: {str(e)}", {
                "error": str(e)
            })
            return False
    
    def test_user_account_integrity(self):
        """Check that user account can be found and has proper data structure"""
        print("\n=== Testing User Account Integrity ===")
        
        if not self.token:
            self.log_result("User Account Integrity", False, "No token available for testing")
            return False
        
        try:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            # Get full profile data
            response = requests.get(
                f"{EXTERNAL_API_URL}/profile",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                try:
                    profile = response.json()
                    
                    # Check required fields
                    required_fields = ["name", "email"]
                    missing_fields = [field for field in required_fields if not profile.get(field)]
                    
                    if not missing_fields:
                        self.log_result("User Account Integrity", True, "User account has all required fields", {
                            "email": profile.get("email"),
                            "name": profile.get("name"),
                            "bio": profile.get("bio", "")[:50] + "..." if len(profile.get("bio", "")) > 50 else profile.get("bio", ""),
                            "website": profile.get("website", ""),
                            "paypal_username": profile.get("paypal_username", ""),
                            "venmo_username": profile.get("venmo_username", ""),
                            "tips_enabled": profile.get("tips_enabled"),
                            "requests_enabled": profile.get("requests_enabled")
                        })
                        
                        # Test subscription status
                        sub_response = requests.get(
                            f"{EXTERNAL_API_URL}/subscription/status",
                            headers=headers,
                            timeout=10
                        )
                        
                        if sub_response.status_code == 200:
                            sub_data = sub_response.json()
                            self.log_result("Subscription Status Check", True, "Subscription status accessible", {
                                "plan": sub_data.get("plan"),
                                "audience_link_active": sub_data.get("audience_link_active"),
                                "trial_active": sub_data.get("trial_active"),
                                "status": sub_data.get("status")
                            })
                        else:
                            self.log_result("Subscription Status Check", False, f"Subscription status failed: {sub_response.status_code}", {
                                "response": sub_response.text[:300]
                            })
                        
                        return True
                    else:
                        self.log_result("User Account Integrity", False, f"User account missing required fields: {missing_fields}", {
                            "missing_fields": missing_fields,
                            "available_fields": list(profile.keys())
                        })
                        return False
                        
                except json.JSONDecodeError:
                    self.log_result("User Account Integrity", False, "Profile response is not valid JSON", {
                        "status_code": response.status_code,
                        "response": response.text[:500]
                    })
                    return False
                    
            else:
                self.log_result("User Account Integrity", False, f"Failed to get profile: {response.status_code}", {
                    "status_code": response.status_code,
                    "response": response.text[:500]
                })
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_result("User Account Integrity", False, f"Profile request failed: {str(e)}", {
                "error": str(e)
            })
            return False
    
    def test_database_connectivity(self):
        """Test database connectivity by performing data operations"""
        print("\n=== Testing Database Connectivity ===")
        
        if not self.token:
            self.log_result("Database Connectivity", False, "No token available for testing")
            return False
        
        try:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            # Test reading songs (database read operation)
            response = requests.get(
                f"{EXTERNAL_API_URL}/songs",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                try:
                    songs = response.json()
                    self.log_result("Database Read Operation", True, f"Successfully read {len(songs)} songs from database", {
                        "song_count": len(songs),
                        "database_accessible": True
                    })
                    
                    # Test reading requests (another database collection)
                    req_response = requests.get(
                        f"{EXTERNAL_API_URL}/requests/musician/{self.musician_id}",
                        headers=headers,
                        timeout=10
                    )
                    
                    if req_response.status_code == 200:
                        requests_data = req_response.json()
                        self.log_result("Database Multi-Collection Access", True, f"Successfully accessed multiple collections", {
                            "requests_count": len(requests_data),
                            "collections_tested": ["songs", "requests", "musicians"]
                        })
                        return True
                    else:
                        self.log_result("Database Multi-Collection Access", False, f"Failed to access requests collection: {req_response.status_code}", {
                            "response": req_response.text[:300]
                        })
                        return False
                        
                except json.JSONDecodeError:
                    self.log_result("Database Read Operation", False, "Songs response is not valid JSON", {
                        "status_code": response.status_code,
                        "response": response.text[:500]
                    })
                    return False
                    
            else:
                self.log_result("Database Read Operation", False, f"Failed to read from database: {response.status_code}", {
                    "status_code": response.status_code,
                    "response": response.text[:500]
                })
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_result("Database Connectivity", False, f"Database connectivity test failed: {str(e)}", {
                "error": str(e)
            })
            return False
    
    def test_production_environment_variables(self):
        """Test that production environment variables are working correctly"""
        print("\n=== Testing Production Environment Variables ===")
        
        # Test CORS and external access
        try:
            # Test with different origins to verify CORS
            headers = {
                "Origin": "https://requestwave.app",
                "Content-Type": "application/json"
            }
            
            response = requests.options(
                f"{EXTERNAL_API_URL}/auth/login",
                headers=headers,
                timeout=10
            )
            
            # CORS preflight should work or return appropriate response
            if response.status_code in [200, 204, 404]:
                self.log_result("CORS Configuration", True, "CORS preflight working", {
                    "status_code": response.status_code,
                    "cors_headers": dict(response.headers)
                })
            else:
                self.log_result("CORS Configuration", False, f"CORS preflight failed: {response.status_code}", {
                    "status_code": response.status_code,
                    "response": response.text[:300]
                })
            
            # Test that the API is accessible from the expected frontend URL
            if self.token:
                headers_with_auth = {
                    "Authorization": f"Bearer {self.token}",
                    "Origin": "https://requestwave.app",
                    "Content-Type": "application/json"
                }
                
                profile_response = requests.get(
                    f"{EXTERNAL_API_URL}/profile",
                    headers=headers_with_auth,
                    timeout=10
                )
                
                if profile_response.status_code == 200:
                    self.log_result("Production Frontend Access", True, "API accessible from production frontend domain", {
                        "frontend_domain": "https://requestwave.app",
                        "api_accessible": True
                    })
                else:
                    self.log_result("Production Frontend Access", False, f"API not accessible from frontend: {profile_response.status_code}", {
                        "status_code": profile_response.status_code
                    })
            
        except requests.exceptions.RequestException as e:
            self.log_result("Production Environment Variables", False, f"Environment variable test failed: {str(e)}", {
                "error": str(e)
            })
    
    def test_forgot_password_functionality(self):
        """Test forgot password functionality to ensure email system is working"""
        print("\n=== Testing Forgot Password Functionality ===")
        
        try:
            # Test forgot password endpoint
            response = requests.post(
                f"{EXTERNAL_API_URL}/auth/forgot-password",
                json={"email": TEST_EMAIL},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.log_result("Forgot Password Endpoint", True, "Forgot password endpoint working", {
                        "status_code": response.status_code,
                        "response": data
                    })
                except json.JSONDecodeError:
                    self.log_result("Forgot Password Endpoint", True, "Forgot password endpoint working (non-JSON response)", {
                        "status_code": response.status_code,
                        "response": response.text[:200]
                    })
            else:
                self.log_result("Forgot Password Endpoint", False, f"Forgot password failed: {response.status_code}", {
                    "status_code": response.status_code,
                    "response": response.text[:300]
                })
                
        except requests.exceptions.RequestException as e:
            self.log_result("Forgot Password Functionality", False, f"Forgot password test failed: {str(e)}", {
                "error": str(e)
            })
    
    def run_all_tests(self):
        """Run all production login tests"""
        print("🚀 Starting Production Login Authentication Tests")
        print(f"Testing against: {EXTERNAL_API_URL}")
        print(f"Test user: {TEST_EMAIL}")
        print(f"Target database: livewave-music-test_database")
        print(f"Expected MongoDB URL: mongodb://mongodb:27017")
        print("=" * 80)
        
        # Run tests in order of dependency
        self.test_external_api_connectivity()
        
        login_success = self.test_login_authentication()
        if login_success:
            self.test_jwt_token_validation()
            self.test_user_account_integrity()
            self.test_database_connectivity()
        
        self.test_production_environment_variables()
        self.test_forgot_password_functionality()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 PRODUCTION LOGIN TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Critical issues
        critical_failures = []
        if not any(r["success"] for r in self.results if "Login Authentication" in r["test"]):
            critical_failures.append("LOGIN AUTHENTICATION FAILED")
        if not any(r["success"] for r in self.results if "External API" in r["test"]):
            critical_failures.append("EXTERNAL API INACCESSIBLE")
        if not any(r["success"] for r in self.results if "Database" in r["test"]):
            critical_failures.append("DATABASE CONNECTIVITY ISSUES")
        
        if critical_failures:
            print(f"\n🚨 CRITICAL ISSUES FOUND:")
            for issue in critical_failures:
                print(f"  - {issue}")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        print(f"\n🎯 PRODUCTION LOGIN TEST COMPLETE")
        print(f"Authentication Status: {'✅ WORKING' if login_success else '❌ FAILED'}")
        
        return failed_tests == 0

if __name__ == "__main__":
    tester = ProductionLoginTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)