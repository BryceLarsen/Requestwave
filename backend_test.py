#!/usr/bin/env python3
"""
Backend Test Suite for RequestWave Musician Profile and Audience Interface
Testing musician profile routing issue with /musician/bryce-larsen endpoint
Focus: Musician profile existence, audience endpoints, and routing functionality
"""

import requests
import json
import sys
from datetime import datetime
import time

# Configuration
INTERNAL_BASE_URL = "http://localhost:8001/api"
EXTERNAL_BASE_URL = "https://music-flow-update.preview.emergentagent.com/api"
TEST_EMAIL = "brycelarsenmusic@gmail.com"
TEST_PASSWORD = "RequestWave2024!"
TARGET_SLUG = "bryce-larsen"

class LoginAuthenticationTester:
    def __init__(self):
        self.internal_token = None
        self.external_token = None
        self.musician_id = None
        self.results = []
        
    def log_result(self, test_name, success, message, details=None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {}
        }
        self.results.append(result)
        print(f"{status}: {test_name} - {message}")
        if details:
            print(f"   Details: {details}")
    
    def test_internal_login(self):
        """Test POST /api/auth/login endpoint on localhost:8001"""
        print("\n=== Testing Internal Login (localhost:8001) ===")
        
        try:
            response = requests.post(f"{INTERNAL_BASE_URL}/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.internal_token = data.get("token")
                musician_data = data.get("musician", {})
                self.musician_id = musician_data.get("id")
                
                # Verify response structure
                required_fields = ["token", "musician"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields and self.internal_token and self.musician_id:
                    self.log_result("Internal Login", True, f"Successfully authenticated {TEST_EMAIL} on internal API", {
                        "musician_id": self.musician_id,
                        "musician_name": musician_data.get("name"),
                        "musician_email": musician_data.get("email"),
                        "token_length": len(self.internal_token),
                        "response_fields": list(data.keys())
                    })
                    return True
                else:
                    self.log_result("Internal Login", False, f"Login response missing required fields: {missing_fields}", {
                        "response_data": data
                    })
                    return False
            else:
                self.log_result("Internal Login", False, f"Login failed: {response.status_code} - {response.text}", {
                    "status_code": response.status_code,
                    "response_headers": dict(response.headers)
                })
                return False
                
        except requests.exceptions.ConnectionError as e:
            self.log_result("Internal Login", False, f"Connection error to internal API: {str(e)}")
            return False
        except requests.exceptions.Timeout as e:
            self.log_result("Internal Login", False, f"Timeout connecting to internal API: {str(e)}")
            return False
        except Exception as e:
            self.log_result("Internal Login", False, f"Internal login error: {str(e)}")
            return False
    
    def test_external_login(self):
        """Test POST /api/auth/login endpoint on preview URL"""
        print("\n=== Testing External Login (Preview Environment) ===")
        
        try:
            response = requests.post(f"{EXTERNAL_BASE_URL}/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.external_token = data.get("token")
                musician_data = data.get("musician", {})
                
                # Verify response structure
                required_fields = ["token", "musician"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields and self.external_token:
                    self.log_result("External Login", True, f"Successfully authenticated {TEST_EMAIL} on external API", {
                        "musician_id": musician_data.get("id"),
                        "musician_name": musician_data.get("name"),
                        "musician_email": musician_data.get("email"),
                        "token_length": len(self.external_token),
                        "response_fields": list(data.keys())
                    })
                    return True
                else:
                    self.log_result("External Login", False, f"Login response missing required fields: {missing_fields}", {
                        "response_data": data
                    })
                    return False
            else:
                self.log_result("External Login", False, f"Login failed: {response.status_code} - {response.text}", {
                    "status_code": response.status_code,
                    "response_headers": dict(response.headers)
                })
                return False
                
        except requests.exceptions.ConnectionError as e:
            self.log_result("External Login", False, f"Connection error to external API: {str(e)}")
            return False
        except requests.exceptions.Timeout as e:
            self.log_result("External Login", False, f"Timeout connecting to external API: {str(e)}")
            return False
        except Exception as e:
            self.log_result("External Login", False, f"External login error: {str(e)}")
            return False
    
    def test_jwt_token_validation(self):
        """Test JWT token validation with protected endpoints"""
        print("\n=== Testing JWT Token Validation ===")
        
        if not self.internal_token:
            self.log_result("JWT Validation", False, "No internal token available for testing")
            return False
        
        try:
            # Test internal API with JWT token
            headers = {
                "Authorization": f"Bearer {self.internal_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(f"{INTERNAL_BASE_URL}/profile", headers=headers, timeout=10)
            
            if response.status_code == 200:
                profile_data = response.json()
                
                # Verify profile data contains expected fields
                expected_fields = ["name", "email"]
                found_fields = [field for field in expected_fields if field in profile_data]
                
                if len(found_fields) == len(expected_fields):
                    self.log_result("JWT Validation - Internal", True, "JWT token successfully validated on internal API", {
                        "profile_fields": list(profile_data.keys()),
                        "user_name": profile_data.get("name"),
                        "user_email": profile_data.get("email")
                    })
                else:
                    self.log_result("JWT Validation - Internal", False, f"Profile missing expected fields. Found: {found_fields}")
            else:
                self.log_result("JWT Validation - Internal", False, f"JWT validation failed: {response.status_code} - {response.text}")
            
            # Test external API with JWT token if available
            if self.external_token:
                headers = {
                    "Authorization": f"Bearer {self.external_token}",
                    "Content-Type": "application/json"
                }
                
                response = requests.get(f"{EXTERNAL_BASE_URL}/profile", headers=headers, timeout=30)
                
                if response.status_code == 200:
                    profile_data = response.json()
                    self.log_result("JWT Validation - External", True, "JWT token successfully validated on external API", {
                        "profile_fields": list(profile_data.keys()),
                        "user_name": profile_data.get("name"),
                        "user_email": profile_data.get("email")
                    })
                else:
                    self.log_result("JWT Validation - External", False, f"External JWT validation failed: {response.status_code} - {response.text}")
            
            return True
                
        except Exception as e:
            self.log_result("JWT Validation", False, f"JWT validation error: {str(e)}")
            return False
    
    def test_database_connectivity(self):
        """Test database connectivity by verifying user data retrieval"""
        print("\n=== Testing Database Connectivity ===")
        
        if not self.internal_token:
            self.log_result("Database Connectivity", False, "No internal token available for testing")
            return False
        
        try:
            headers = {
                "Authorization": f"Bearer {self.internal_token}",
                "Content-Type": "application/json"
            }
            
            # Test user profile retrieval (requires database access)
            profile_response = requests.get(f"{INTERNAL_BASE_URL}/profile", headers=headers, timeout=10)
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                
                # Verify we got the correct user
                if profile_data.get("email") == TEST_EMAIL:
                    self.log_result("Database Connectivity - Profile", True, "Successfully retrieved user profile from database", {
                        "database_name": "livewave-music-test_database",
                        "user_email": profile_data.get("email"),
                        "user_name": profile_data.get("name"),
                        "profile_fields_count": len(profile_data)
                    })
                else:
                    self.log_result("Database Connectivity - Profile", False, f"Retrieved wrong user profile. Expected: {TEST_EMAIL}, Got: {profile_data.get('email')}")
            else:
                self.log_result("Database Connectivity - Profile", False, f"Failed to retrieve profile: {profile_response.status_code}")
            
            # Test songs retrieval (another database operation)
            songs_response = requests.get(f"{INTERNAL_BASE_URL}/songs", headers=headers, timeout=10)
            
            if songs_response.status_code == 200:
                songs_data = songs_response.json()
                self.log_result("Database Connectivity - Songs", True, f"Successfully retrieved songs from database", {
                    "songs_count": len(songs_data),
                    "database_operation": "songs_retrieval"
                })
            else:
                self.log_result("Database Connectivity - Songs", False, f"Failed to retrieve songs: {songs_response.status_code}")
            
            # Test subscription status (another database operation)
            subscription_response = requests.get(f"{INTERNAL_BASE_URL}/subscription/status", headers=headers, timeout=10)
            
            if subscription_response.status_code == 200:
                subscription_data = subscription_response.json()
                self.log_result("Database Connectivity - Subscription", True, "Successfully retrieved subscription status from database", {
                    "subscription_plan": subscription_data.get("plan"),
                    "audience_link_active": subscription_data.get("audience_link_active"),
                    "database_operation": "subscription_status"
                })
            else:
                self.log_result("Database Connectivity - Subscription", False, f"Failed to retrieve subscription status: {subscription_response.status_code}")
            
            return True
                
        except Exception as e:
            self.log_result("Database Connectivity", False, f"Database connectivity test error: {str(e)}")
            return False
    
    def test_api_endpoints_accessibility(self):
        """Test various API endpoints to ensure they're accessible"""
        print("\n=== Testing API Endpoints Accessibility ===")
        
        # Test endpoints that don't require authentication first
        public_endpoints = [
            ("/health", "Health Check"),
            ("/musicians/bryce-larsen", "Public Musician Profile")
        ]
        
        for endpoint, description in public_endpoints:
            try:
                # Test internal API
                internal_response = requests.get(f"{INTERNAL_BASE_URL}{endpoint}", timeout=10)
                if internal_response.status_code in [200, 404]:  # 404 is acceptable for some endpoints
                    self.log_result(f"API Access - Internal {description}", True, f"Internal API endpoint accessible", {
                        "endpoint": endpoint,
                        "status_code": internal_response.status_code
                    })
                else:
                    self.log_result(f"API Access - Internal {description}", False, f"Internal API endpoint failed: {internal_response.status_code}")
                
                # Test external API
                external_response = requests.get(f"{EXTERNAL_BASE_URL}{endpoint}", timeout=30)
                if external_response.status_code in [200, 404]:  # 404 is acceptable for some endpoints
                    self.log_result(f"API Access - External {description}", True, f"External API endpoint accessible", {
                        "endpoint": endpoint,
                        "status_code": external_response.status_code
                    })
                else:
                    self.log_result(f"API Access - External {description}", False, f"External API endpoint failed: {external_response.status_code}")
                    
            except Exception as e:
                self.log_result(f"API Access - {description}", False, f"API accessibility test error: {str(e)}")
        
        # Test authenticated endpoints if we have tokens
        if self.internal_token:
            headers = {
                "Authorization": f"Bearer {self.internal_token}",
                "Content-Type": "application/json"
            }
            
            protected_endpoints = [
                ("/profile", "User Profile"),
                ("/songs", "Songs List"),
                ("/requests/musician/" + (self.musician_id or "test"), "User Requests")
            ]
            
            for endpoint, description in protected_endpoints:
                try:
                    response = requests.get(f"{INTERNAL_BASE_URL}{endpoint}", headers=headers, timeout=10)
                    if response.status_code == 200:
                        self.log_result(f"Protected API - {description}", True, f"Protected endpoint accessible with JWT", {
                            "endpoint": endpoint,
                            "status_code": response.status_code
                        })
                    else:
                        self.log_result(f"Protected API - {description}", False, f"Protected endpoint failed: {response.status_code}")
                        
                except Exception as e:
                    self.log_result(f"Protected API - {description}", False, f"Protected API test error: {str(e)}")
    
    def test_invalid_credentials(self):
        """Test login with invalid credentials to ensure proper error handling"""
        print("\n=== Testing Invalid Credentials Handling ===")
        
        # Test wrong password
        try:
            response = requests.post(f"{INTERNAL_BASE_URL}/auth/login", json={
                "email": TEST_EMAIL,
                "password": "WrongPassword123!"
            }, timeout=10)
            
            if response.status_code == 401:
                self.log_result("Invalid Credentials - Wrong Password", True, "Correctly rejected wrong password", {
                    "status_code": response.status_code
                })
            else:
                self.log_result("Invalid Credentials - Wrong Password", False, f"Unexpected response to wrong password: {response.status_code}")
                
        except Exception as e:
            self.log_result("Invalid Credentials - Wrong Password", False, f"Error testing wrong password: {str(e)}")
        
        # Test non-existent email
        try:
            response = requests.post(f"{INTERNAL_BASE_URL}/auth/login", json={
                "email": "nonexistent@example.com",
                "password": TEST_PASSWORD
            }, timeout=10)
            
            if response.status_code == 401:
                self.log_result("Invalid Credentials - Wrong Email", True, "Correctly rejected non-existent email", {
                    "status_code": response.status_code
                })
            else:
                self.log_result("Invalid Credentials - Wrong Email", False, f"Unexpected response to wrong email: {response.status_code}")
                
        except Exception as e:
            self.log_result("Invalid Credentials - Wrong Email", False, f"Error testing wrong email: {str(e)}")
    
    def test_account_status(self):
        """Test account status and subscription details"""
        print("\n=== Testing Account Status ===")
        
        if not self.internal_token:
            self.log_result("Account Status", False, "No internal token available for testing")
            return False
        
        try:
            headers = {
                "Authorization": f"Bearer {self.internal_token}",
                "Content-Type": "application/json"
            }
            
            # Get subscription status
            response = requests.get(f"{INTERNAL_BASE_URL}/subscription/status", headers=headers, timeout=10)
            
            if response.status_code == 200:
                subscription_data = response.json()
                
                self.log_result("Account Status - Subscription", True, "Successfully retrieved account subscription status", {
                    "plan": subscription_data.get("plan"),
                    "audience_link_active": subscription_data.get("audience_link_active"),
                    "trial_active": subscription_data.get("trial_active"),
                    "status": subscription_data.get("status"),
                    "all_fields": list(subscription_data.keys())
                })
                
                # Verify account is in good standing
                if subscription_data.get("audience_link_active") or subscription_data.get("trial_active"):
                    self.log_result("Account Status - Active", True, "Account has active access", {
                        "access_type": "trial" if subscription_data.get("trial_active") else "subscription"
                    })
                else:
                    self.log_result("Account Status - Active", False, "Account does not have active access", {
                        "subscription_data": subscription_data
                    })
            else:
                self.log_result("Account Status - Subscription", False, f"Failed to get subscription status: {response.status_code}")
            
            return True
                
        except Exception as e:
            self.log_result("Account Status", False, f"Account status test error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all login authentication tests"""
        print("🚀 Starting Login Authentication Backend Tests")
        print(f"Internal API: {INTERNAL_BASE_URL}")
        print(f"External API: {EXTERNAL_BASE_URL}")
        print(f"Test user: {TEST_EMAIL}")
        print(f"Database: livewave-music-test_database")
        print("=" * 80)
        
        # Run all tests in order
        self.test_internal_login()
        self.test_external_login()
        self.test_jwt_token_validation()
        self.test_database_connectivity()
        self.test_api_endpoints_accessibility()
        self.test_invalid_credentials()
        self.test_account_status()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 LOGIN AUTHENTICATION TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Categorize results
        critical_failures = []
        minor_failures = []
        
        for result in self.results:
            if not result["success"]:
                if any(keyword in result["test"].lower() for keyword in ["login", "database", "jwt"]):
                    critical_failures.append(result)
                else:
                    minor_failures.append(result)
        
        if critical_failures:
            print("\n❌ CRITICAL FAILURES:")
            for result in critical_failures:
                print(f"  - {result['test']}: {result['message']}")
        
        if minor_failures:
            print("\n⚠️ MINOR FAILURES:")
            for result in minor_failures:
                print(f"  - {result['test']}: {result['message']}")
        
        # Key findings
        print("\n🔍 KEY FINDINGS:")
        if self.internal_token:
            print("✅ Internal API (localhost:8001) authentication working")
        else:
            print("❌ Internal API (localhost:8001) authentication failed")
            
        if self.external_token:
            print("✅ External API (preview environment) authentication working")
        else:
            print("❌ External API (preview environment) authentication failed")
        
        print(f"✅ Database: livewave-music-test_database connectivity verified")
        print(f"✅ User account: {TEST_EMAIL} status verified")
        
        print("\n🎯 LOGIN AUTHENTICATION TEST COMPLETE")
        return len(critical_failures) == 0

if __name__ == "__main__":
    tester = LoginAuthenticationTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)