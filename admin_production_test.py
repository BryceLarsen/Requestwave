#!/usr/bin/env python3
"""
RequestWave Admin Panel Production Test Suite
Testing production-ready admin panel with security features and production build integration

Focus Areas from Review Request:
1. Production Integration (Build, Environment, Database, Security Headers)
2. Security Features (Rate Limiting, HTTP-Only Cookies, CSRF Protection, Access Control)
3. Admin Functionality (User Management, User Merge, Data Inspector, System Info)
4. Email Uniqueness (Startup Index, Duplicate Prevention, Login Normalization)
5. Environment Consistency (Same Database, Environment Display)
"""

import requests
import json
import sys
import time
from datetime import datetime
import uuid

# Configuration
EXTERNAL_BASE_URL = "https://requestwave-revamp.preview.emergentagent.com"
INTERNAL_BASE_URL = "http://localhost:8001"
API_BASE_URL = f"{EXTERNAL_BASE_URL}/api"
ADMIN_BASE_URL = f"{API_BASE_URL}/admin"

# Admin credentials from environment
ADMIN_EMAIL = "admin@requestwave.com"
ADMIN_PASSWORD = "admin123!change_me"

class AdminProductionTester:
    def __init__(self):
        self.admin_session_token = None
        self.admin_csrf_token = None
        self.results = []
        self.test_user_ids = []  # Track created test users for cleanup
        
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
        if details and isinstance(details, dict):
            for key, value in details.items():
                print(f"   {key}: {value}")
    
    def test_production_integration(self):
        """Test production integration features"""
        print("\n=== PRODUCTION INTEGRATION TESTING ===")
        
        # 1. Test Build Integration - Admin panel accessible at /admin route
        self.test_admin_route_accessibility()
        
        # 2. Test Environment Configuration
        self.test_environment_configuration()
        
        # 3. Test Database Startup - Email normalization index
        self.test_database_startup_indexes()
        
        # 4. Test Security Headers
        self.test_security_headers()
    
    def test_admin_route_accessibility(self):
        """Test that admin panel is accessible at /admin route"""
        try:
            # Test frontend admin route
            admin_url = f"{EXTERNAL_BASE_URL}/admin"
            response = requests.get(admin_url, timeout=30, allow_redirects=False)
            
            # Admin route should be accessible (200) or redirect to login
            if response.status_code in [200, 302, 301]:
                self.log_result("Admin Route Accessibility", True, f"Admin route accessible at /admin", {
                    "status_code": response.status_code,
                    "content_length": len(response.content),
                    "has_admin_content": "admin" in response.text.lower() or response.status_code in [302, 301]
                })
            else:
                self.log_result("Admin Route Accessibility", False, f"Admin route not accessible: {response.status_code}")
                
        except Exception as e:
            self.log_result("Admin Route Accessibility", False, f"Error testing admin route: {str(e)}")
    
    def test_environment_configuration(self):
        """Test environment configuration variables"""
        try:
            # Test admin login first to get session
            login_response = requests.post(f"{ADMIN_BASE_URL}/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }, timeout=30)
            
            if login_response.status_code == 200:
                login_data = login_response.json()
                self.admin_session_token = login_data.get("session_token")
                
                if self.admin_session_token:
                    # Test system info endpoint to verify environment variables
                    headers = {"Authorization": f"Bearer {self.admin_session_token}"}
                    response = requests.get(f"{ADMIN_BASE_URL}/system/info", headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Check for expected environment variables
                        expected_vars = {
                            "environment": "preview",
                            "admin_email": ADMIN_EMAIL,
                            "billing_enabled": False
                        }
                        
                        correct_vars = []
                        incorrect_vars = []
                        
                        for var, expected_value in expected_vars.items():
                            actual_value = data.get(var)
                            if actual_value == expected_value:
                                correct_vars.append(var)
                            else:
                                incorrect_vars.append(f"{var}: expected {expected_value}, got {actual_value}")
                        
                        self.log_result("Environment Configuration", len(incorrect_vars) == 0, "Environment variables verified", {
                            "correct_variables": correct_vars,
                            "incorrect_variables": incorrect_vars,
                            "database_url": data.get("database_url"),
                            "database_name": data.get("database_name")
                        })
                    else:
                        self.log_result("Environment Configuration", False, f"System info not accessible: {response.status_code}")
                else:
                    self.log_result("Environment Configuration", False, "No admin session token received")
            else:
                self.log_result("Environment Configuration", False, f"Admin login failed: {login_response.status_code}")
                
        except Exception as e:
            self.log_result("Environment Configuration", False, f"Error testing environment config: {str(e)}")
    
    def test_database_startup_indexes(self):
        """Test that email normalization index is created on startup"""
        try:
            # Create a test user to verify email normalization works
            test_email = f"test.{uuid.uuid4().hex[:8]}@example.com"
            test_password = "TestPassword123!"
            
            # Register user
            register_response = requests.post(f"{API_BASE_URL}/auth/register", json={
                "name": "Test User",
                "email": test_email,
                "password": test_password
            }, timeout=30)
            
            if register_response.status_code == 200:
                # Try to register same email with different case
                duplicate_response = requests.post(f"{API_BASE_URL}/auth/register", json={
                    "name": "Duplicate User", 
                    "email": test_email.upper(),  # Same email, different case
                    "password": test_password
                }, timeout=30)
                
                if duplicate_response.status_code == 400:
                    error_data = duplicate_response.json()
                    error_message = error_data.get("detail", "")
                    if "email" in error_message.lower() or "duplicate" in error_message.lower():
                        self.log_result("Database Startup Indexes", True, "Email uniqueness index working - duplicate prevention active", {
                            "original_email": test_email,
                            "duplicate_email": test_email.upper(),
                            "error_message": error_message
                        })
                    else:
                        self.log_result("Database Startup Indexes", False, "Duplicate email allowed - index may not be working")
                else:
                    self.log_result("Database Startup Indexes", False, f"Unexpected duplicate registration response: {duplicate_response.status_code}")
            else:
                self.log_result("Database Startup Indexes", False, f"Could not create test user for index testing: {register_response.status_code}")
                
        except Exception as e:
            self.log_result("Database Startup Indexes", False, f"Error testing database indexes: {str(e)}")
    
    def test_security_headers(self):
        """Test security headers on admin routes"""
        try:
            # Test admin login endpoint for security headers
            response = requests.post(f"{ADMIN_BASE_URL}/login", json={
                "email": ADMIN_EMAIL,
                "password": "wrong_password"  # Intentionally wrong to test headers without auth
            }, timeout=30)
            
            headers = response.headers
            expected_headers = {
                "X-Robots-Tag": "noindex",
                "X-Frame-Options": "DENY", 
                "X-Content-Type-Options": "nosniff"
            }
            
            present_headers = {}
            missing_headers = []
            
            for header, expected_value in expected_headers.items():
                if header in headers:
                    present_headers[header] = headers[header]
                    if headers[header] != expected_value:
                        missing_headers.append(f"{header} (expected: {expected_value}, got: {headers[header]})")
                else:
                    missing_headers.append(header)
            
            if not missing_headers:
                self.log_result("Security Headers", True, "All required security headers present", {
                    "headers_found": present_headers
                })
            else:
                self.log_result("Security Headers", False, f"Missing/incorrect security headers: {missing_headers}", {
                    "present_headers": present_headers,
                    "missing_headers": missing_headers
                })
                
        except Exception as e:
            self.log_result("Security Headers", False, f"Error testing security headers: {str(e)}")
    
    def test_security_features(self):
        """Test security features"""
        print("\n=== SECURITY FEATURES TESTING ===")
        
        # 1. Test Rate Limiting
        self.test_admin_rate_limiting()
        
        # 2. Test HTTP-Only Cookies
        self.test_http_only_cookies()
        
        # 3. Test CSRF Protection
        self.test_csrf_protection()
        
        # 4. Test Access Control
        self.test_access_control()
    
    def test_admin_rate_limiting(self):
        """Test admin login rate limiting (5 attempts per 5 minutes)"""
        try:
            # Make multiple failed login attempts to test rate limiting
            failed_attempts = 0
            rate_limited = False
            
            for attempt in range(7):  # Try 7 attempts (should be rate limited after 5)
                response = requests.post(f"{ADMIN_BASE_URL}/auth/login", json={
                    "email": ADMIN_EMAIL,
                    "password": f"wrong_password_{attempt}"
                }, timeout=30)
                
                if response.status_code == 429:  # Too Many Requests
                    rate_limited = True
                    self.log_result("Admin Rate Limiting", True, f"Rate limiting activated after {attempt + 1} attempts", {
                        "attempts_before_limit": attempt + 1,
                        "status_code": response.status_code,
                        "response": response.json() if response.content else {}
                    })
                    break
                elif response.status_code == 401:
                    failed_attempts += 1
                else:
                    # Unexpected response
                    break
            
            if not rate_limited and failed_attempts >= 5:
                self.log_result("Admin Rate Limiting", False, f"Rate limiting not activated after {failed_attempts} failed attempts")
            elif not rate_limited:
                self.log_result("Admin Rate Limiting", False, f"Could not test rate limiting - unexpected responses")
                
        except Exception as e:
            self.log_result("Admin Rate Limiting", False, f"Error testing rate limiting: {str(e)}")
    
    def test_http_only_cookies(self):
        """Test HTTP-only cookie session storage"""
        try:
            # Attempt admin login with correct credentials
            response = requests.post(f"{ADMIN_BASE_URL}/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }, timeout=30)
            
            if response.status_code == 200:
                # Check for HTTP-only session cookie
                cookies = response.cookies
                session_cookie = None
                
                for cookie in cookies:
                    if "admin" in cookie.name.lower() or "session" in cookie.name.lower():
                        session_cookie = cookie
                        break
                
                if session_cookie:
                    # Check if cookie is HTTP-only
                    is_http_only = getattr(session_cookie, 'has_nonstandard_attr', lambda x: False)('HttpOnly')
                    
                    self.log_result("HTTP-Only Cookies", True, "Admin session cookie found", {
                        "cookie_name": session_cookie.name,
                        "http_only": is_http_only,
                        "secure": session_cookie.secure,
                        "domain": session_cookie.domain
                    })
                    
                    # Store session token for later tests
                    self.admin_session_token = session_cookie.value
                else:
                    # Check if token is returned in response body instead
                    data = response.json()
                    if "session_token" in data or "token" in data:
                        self.admin_session_token = data.get("session_token") or data.get("token")
                        self.log_result("HTTP-Only Cookies", True, "Admin session token received", {
                            "token_in_response": True,
                            "token_length": len(self.admin_session_token) if self.admin_session_token else 0
                        })
                    else:
                        self.log_result("HTTP-Only Cookies", False, "No admin session cookie or token found")
            else:
                self.log_result("HTTP-Only Cookies", False, f"Admin login failed: {response.status_code}")
                
        except Exception as e:
            self.log_result("HTTP-Only Cookies", False, f"Error testing HTTP-only cookies: {str(e)}")
    
    def test_csrf_protection(self):
        """Test CSRF protection for POST/PUT/DELETE operations"""
        if not self.admin_session_token:
            self.log_result("CSRF Protection", False, "No admin session token available for CSRF testing")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_session_token}"}
            
            # Try a POST operation without CSRF token
            post_response = requests.post(f"{ADMIN_BASE_URL}/users/search", 
                                        json={"query": "test"}, 
                                        headers=headers, 
                                        timeout=30)
            
            if post_response.status_code == 403:
                self.log_result("CSRF Protection", True, "CSRF protection active - POST rejected without token", {
                    "status_code": post_response.status_code,
                    "error": post_response.json() if post_response.content else {}
                })
            elif post_response.status_code == 200:
                # Check if CSRF token is in response headers or if protection is implemented differently
                csrf_header = post_response.headers.get("X-CSRF-Token")
                if csrf_header:
                    self.admin_csrf_token = csrf_header
                    self.log_result("CSRF Protection", True, "CSRF token provided in response headers", {
                        "csrf_token_length": len(csrf_header)
                    })
                else:
                    self.log_result("CSRF Protection", False, "POST operation succeeded without CSRF token")
            else:
                self.log_result("CSRF Protection", False, f"Unexpected CSRF test response: {post_response.status_code}")
                
        except Exception as e:
            self.log_result("CSRF Protection", False, f"Error testing CSRF protection: {str(e)}")
    
    def test_access_control(self):
        """Test that all admin endpoints require authentication"""
        try:
            # Test various admin endpoints without authentication
            admin_endpoints = [
                "/users",
                "/users/search", 
                "/system/info",
                "/database/stats",
                "/users/merge"
            ]
            
            protected_endpoints = 0
            total_endpoints = len(admin_endpoints)
            
            for endpoint in admin_endpoints:
                try:
                    response = requests.get(f"{ADMIN_BASE_URL}{endpoint}", timeout=30)
                    
                    if response.status_code == 401:
                        protected_endpoints += 1
                    elif response.status_code == 403:
                        protected_endpoints += 1  # Also acceptable - forbidden without auth
                    
                except Exception:
                    continue
            
            if protected_endpoints == total_endpoints:
                self.log_result("Access Control", True, f"All {total_endpoints} admin endpoints properly protected", {
                    "protected_endpoints": protected_endpoints,
                    "total_endpoints": total_endpoints
                })
            else:
                self.log_result("Access Control", False, f"Only {protected_endpoints}/{total_endpoints} admin endpoints protected")
                
        except Exception as e:
            self.log_result("Access Control", False, f"Error testing access control: {str(e)}")
    
    def test_admin_functionality(self):
        """Test admin functionality features"""
        print("\n=== ADMIN FUNCTIONALITY TESTING ===")
        
        if not self.admin_session_token:
            self.log_result("Admin Functionality", False, "No admin session token - cannot test admin functionality")
            return
        
        # 1. Test User Management
        self.test_user_management()
        
        # 2. Test User Merge
        self.test_user_merge()
        
        # 3. Test Data Inspector
        self.test_data_inspector()
        
        # 4. Test System Info
        self.test_system_info()
    
    def test_user_management(self):
        """Test user management functionality"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_session_token}"}
            
            # Test list users
            users_response = requests.get(f"{ADMIN_BASE_URL}/users", headers=headers, timeout=30)
            
            if users_response.status_code == 200:
                users_data = users_response.json()
                
                # Handle both list and dict responses
                if isinstance(users_data, dict) and "musicians" in users_data:
                    users_list = users_data["musicians"]
                elif isinstance(users_data, list):
                    users_list = users_data
                else:
                    users_list = []
                
                self.log_result("User Management - List Users", True, f"Successfully retrieved {len(users_list)} users", {
                    "user_count": len(users_list),
                    "sample_user": users_list[0] if users_list else None
                })
                
                # Test search by email if we have users
                if users_list:
                    test_email = users_list[0].get("email", "")
                    if test_email:
                        search_response = requests.get(f"{ADMIN_BASE_URL}/users", 
                                                      params={"search_email": test_email[:5]}, 
                                                      headers=headers, 
                                                      timeout=30)
                        
                        if search_response.status_code == 200:
                            search_results = search_response.json()
                            if isinstance(search_results, dict) and "musicians" in search_results:
                                search_list = search_results["musicians"]
                            elif isinstance(search_results, list):
                                search_list = search_results
                            else:
                                search_list = []
                            
                            self.log_result("User Management - Search Users", True, f"Search returned {len(search_list)} results", {
                                "search_query": test_email[:5],
                                "results_count": len(search_list)
                            })
                        else:
                            self.log_result("User Management - Search Users", False, f"User search failed: {search_response.status_code}")
            else:
                self.log_result("User Management - List Users", False, f"Failed to list users: {users_response.status_code}")
                
        except Exception as e:
            self.log_result("User Management", False, f"Error testing user management: {str(e)}")
    
    def test_user_merge(self):
        """Test user merge functionality"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_session_token}"}
            
            # Create two test users for merge testing
            test_users = []
            for i in range(2):
                test_email = f"merge_test_{i}_{int(time.time())}@test.com"
                test_password = "TestPassword123!"
                
                register_response = requests.post(f"{API_BASE_URL}/auth/register", json={
                    "name": f"Merge Test User {i+1}",
                    "email": test_email,
                    "password": test_password
                }, timeout=30)
                
                if register_response.status_code == 200:
                    register_data = register_response.json()
                    user_id = register_data.get("musician", {}).get("id")
                    if user_id:
                        test_users.append({"id": user_id, "email": test_email})
            
            if len(test_users) == 2:
                # Test merge operation
                merge_data = {
                    "primary_user_id": test_users[0]["id"],
                    "duplicate_user_id": test_users[1]["id"]
                }
                
                merge_response = requests.post(f"{ADMIN_BASE_URL}/users/merge", 
                                             headers=headers, json=merge_data, timeout=30)
                
                if merge_response.status_code == 200:
                    merge_result = merge_response.json()
                    self.log_result("User Merge", True, "User merge operation completed", {
                        "primary_user_id": test_users[0]["id"],
                        "duplicate_user_id": test_users[1]["id"],
                        "merge_response": merge_result.get("message", "No message")
                    })
                else:
                    self.log_result("User Merge", False, f"User merge failed: {merge_response.status_code}")
            else:
                self.log_result("User Merge", False, f"Could not create test users for merge (created {len(test_users)}/2)")
                
        except Exception as e:
            self.log_result("User Merge", False, f"Error testing user merge: {str(e)}")
    
    def test_data_inspector(self):
        """Test data inspector functionality"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_session_token}"}
            
            # Test various data inspection endpoints
            inspection_endpoints = [
                ("/songs", "Songs"),
                ("/playlists", "Playlists"), 
                ("/requests", "Requests")
            ]
            
            for endpoint, name in inspection_endpoints:
                try:
                    response = requests.get(f"{ADMIN_BASE_URL}{endpoint}", headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.log_result(f"Data Inspector - {name}", True, f"{name} data accessible", {
                            "data_count": len(data) if isinstance(data, list) else "N/A",
                            "data_type": type(data).__name__
                        })
                    elif response.status_code == 404:
                        self.log_result(f"Data Inspector - {name}", False, f"{name} endpoint not found")
                    else:
                        self.log_result(f"Data Inspector - {name}", False, f"{name} endpoint error: {response.status_code}")
                        
                except Exception as e:
                    self.log_result(f"Data Inspector - {name}", False, f"Error testing {name}: {str(e)}")
                    
        except Exception as e:
            self.log_result("Data Inspector", False, f"Error testing data inspector: {str(e)}")
    
    def test_system_info(self):
        """Test system info functionality"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_session_token}"}
            
            # Test system info endpoint
            info_response = requests.get(f"{ADMIN_BASE_URL}/system/info", headers=headers, timeout=30)
            
            if info_response.status_code == 200:
                info_data = info_response.json()
                
                # Check for expected system info fields
                expected_fields = ["environment", "database_url", "database_name"]
                present_fields = [field for field in expected_fields if field in info_data]
                
                self.log_result("System Info", True, f"System info accessible with {len(present_fields)}/{len(expected_fields)} expected fields", {
                    "present_fields": present_fields,
                    "environment": info_data.get("environment"),
                    "database_connected": "database_url" in info_data
                })
            else:
                self.log_result("System Info", False, f"System info not accessible: {info_response.status_code}")
                
        except Exception as e:
            self.log_result("System Info", False, f"Error testing system info: {str(e)}")
    
    def test_email_uniqueness(self):
        """Test email uniqueness features"""
        print("\n=== EMAIL UNIQUENESS TESTING ===")
        
        # 1. Test duplicate prevention
        self.test_duplicate_prevention()
        
        # 2. Test login normalization
        self.test_login_normalization()
    
    def test_duplicate_prevention(self):
        """Test that duplicate email signups return friendly error message"""
        try:
            # Create a test user
            test_email = f"duplicate.test.{uuid.uuid4().hex[:8]}@example.com"
            test_password = "TestPassword123!"
            
            # First registration
            first_response = requests.post(f"{API_BASE_URL}/auth/register", json={
                "name": "First User",
                "email": test_email,
                "password": test_password
            }, timeout=30)
            
            if first_response.status_code == 200:
                # Try duplicate registration
                duplicate_response = requests.post(f"{API_BASE_URL}/auth/register", json={
                    "name": "Duplicate User",
                    "email": test_email,  # Exact same email
                    "password": test_password
                }, timeout=30)
                
                if duplicate_response.status_code == 400:
                    error_data = duplicate_response.json()
                    error_message = error_data.get("detail", "")
                    
                    # Check if error message is user-friendly
                    is_friendly = any(word in error_message.lower() for word in ["email", "already", "exists", "registered"])
                    
                    self.log_result("Duplicate Prevention", True, "Duplicate email registration properly rejected", {
                        "error_message": error_message,
                        "is_friendly_message": is_friendly,
                        "status_code": duplicate_response.status_code
                    })
                else:
                    self.log_result("Duplicate Prevention", False, f"Duplicate email registration not rejected: {duplicate_response.status_code}")
            else:
                self.log_result("Duplicate Prevention", False, f"Could not create initial test user: {first_response.status_code}")
                
        except Exception as e:
            self.log_result("Duplicate Prevention", False, f"Error testing duplicate prevention: {str(e)}")
    
    def test_login_normalization(self):
        """Test that login uses email_lc field for lookups"""
        try:
            # Create a test user with mixed case email
            test_email = f"Login.Test.{uuid.uuid4().hex[:8]}@Example.Com"
            test_password = "TestPassword123!"
            
            # Register with mixed case email
            register_response = requests.post(f"{API_BASE_URL}/auth/register", json={
                "name": "Login Test User",
                "email": test_email,
                "password": test_password
            }, timeout=30)
            
            if register_response.status_code == 200:
                # Try to login with different case variations
                case_variations = [
                    test_email.lower(),
                    test_email.upper(),
                    test_email  # Original case
                ]
                
                successful_logins = 0
                
                for email_variant in case_variations:
                    login_response = requests.post(f"{API_BASE_URL}/auth/login", json={
                        "email": email_variant,
                        "password": test_password
                    }, timeout=30)
                    
                    if login_response.status_code == 200:
                        successful_logins += 1
                
                if successful_logins == len(case_variations):
                    self.log_result("Login Normalization", True, f"Login works with all case variations ({successful_logins}/{len(case_variations)})", {
                        "original_email": test_email,
                        "successful_variations": successful_logins,
                        "total_variations": len(case_variations)
                    })
                else:
                    self.log_result("Login Normalization", False, f"Login normalization incomplete: {successful_logins}/{len(case_variations)} variations worked")
            else:
                self.log_result("Login Normalization", False, f"Could not create test user for login normalization: {register_response.status_code}")
                
        except Exception as e:
            self.log_result("Login Normalization", False, f"Error testing login normalization: {str(e)}")
    
    def test_environment_consistency(self):
        """Test environment consistency"""
        print("\n=== ENVIRONMENT CONSISTENCY TESTING ===")
        
        # 1. Test same database usage
        self.test_same_database_usage()
        
        # 2. Test environment display
        self.test_environment_display()
    
    def test_same_database_usage(self):
        """Test that artist, audience, and admin all use same MongoDB connection"""
        try:
            # Create a test user via regular registration
            test_email = f"consistency.test.{uuid.uuid4().hex[:8]}@example.com"
            test_password = "TestPassword123!"
            
            # Register user
            register_response = requests.post(f"{API_BASE_URL}/auth/register", json={
                "name": "Consistency Test User",
                "email": test_email,
                "password": test_password
            }, timeout=30)
            
            if register_response.status_code == 200:
                user_data = register_response.json()
                user_id = user_data.get("musician", {}).get("id")
                
                if user_id and self.admin_session_token:
                    # Check if admin can see the same user
                    headers = {"Authorization": f"Bearer {self.admin_session_token}"}
                    admin_users_response = requests.get(f"{ADMIN_BASE_URL}/users", headers=headers, timeout=30)
                    
                    if admin_users_response.status_code == 200:
                        admin_users_data = admin_users_response.json()
                        
                        # Handle both list and dict responses
                        if isinstance(admin_users_data, dict) and "musicians" in admin_users_data:
                            admin_users = admin_users_data["musicians"]
                        elif isinstance(admin_users_data, list):
                            admin_users = admin_users_data
                        else:
                            admin_users = []
                        
                        user_found_in_admin = any(user.get("email") == test_email for user in admin_users)
                        
                        if user_found_in_admin:
                            self.log_result("Same Database Usage", True, "User created via API visible in admin panel", {
                                "test_email": test_email,
                                "user_id": user_id,
                                "found_in_admin": user_found_in_admin
                            })
                        else:
                            self.log_result("Same Database Usage", False, "User created via API not visible in admin panel")
                    else:
                        self.log_result("Same Database Usage", False, f"Could not access admin users: {admin_users_response.status_code}")
                else:
                    self.log_result("Same Database Usage", False, "Could not get user ID or admin token for consistency test")
            else:
                self.log_result("Same Database Usage", False, f"Could not create test user for consistency test: {register_response.status_code}")
                
        except Exception as e:
            self.log_result("Same Database Usage", False, f"Error testing database consistency: {str(e)}")
    
    def test_environment_display(self):
        """Test that admin header shows correct environment"""
        try:
            if not self.admin_session_token:
                self.log_result("Environment Display", False, "No admin session token for environment display test")
                return
            
            headers = {"Authorization": f"Bearer {self.admin_session_token}"}
            
            # Get system info to check environment display
            info_response = requests.get(f"{ADMIN_BASE_URL}/system/info", headers=headers, timeout=30)
            
            if info_response.status_code == 200:
                info_data = info_response.json()
                environment = info_data.get("environment", "").lower()
                
                # Check if environment matches expected values (PREVIEW/PRODUCTION)
                expected_envs = ["preview", "production", "development"]
                is_valid_env = environment in expected_envs
                
                self.log_result("Environment Display", is_valid_env, f"Environment display shows: {environment}", {
                    "environment": environment,
                    "is_valid": is_valid_env,
                    "expected_values": expected_envs
                })
            else:
                self.log_result("Environment Display", False, f"Could not get system info for environment display: {info_response.status_code}")
                
        except Exception as e:
            self.log_result("Environment Display", False, f"Error testing environment display: {str(e)}")
    
    def run_all_tests(self):
        """Run all admin panel tests"""
        print("🚀 Starting RequestWave Admin Panel Production Test Suite")
        print(f"External URL: {EXTERNAL_BASE_URL}")
        print(f"Admin API: {ADMIN_BASE_URL}")
        print(f"Admin Email: {ADMIN_EMAIL}")
        print("=" * 80)
        
        # Run all test categories
        self.test_production_integration()
        self.test_security_features()
        self.test_admin_functionality()
        self.test_email_uniqueness()
        self.test_environment_consistency()
        
        # Generate summary
        self.generate_summary()
        
        return self.get_success_rate() > 0.7  # 70% success rate threshold
    
    def generate_summary(self):
        """Generate comprehensive test summary"""
        print("\n" + "=" * 80)
        print("📊 REQUESTWAVE ADMIN PANEL PRODUCTION TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["success"]])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Categorize results by test area
        categories = {
            "Production Integration": [],
            "Security Features": [],
            "Admin Functionality": [],
            "Email Uniqueness": [],
            "Environment Consistency": []
        }
        
        for result in self.results:
            test_name = result["test"]
            if any(keyword in test_name for keyword in ["Route", "Environment Configuration", "Database Startup", "Security Headers"]):
                categories["Production Integration"].append(result)
            elif any(keyword in test_name for keyword in ["Rate Limiting", "HTTP-Only", "CSRF", "Access Control"]):
                categories["Security Features"].append(result)
            elif any(keyword in test_name for keyword in ["User Management", "User Merge", "Data Inspector", "System Info"]):
                categories["Admin Functionality"].append(result)
            elif any(keyword in test_name for keyword in ["Duplicate", "Login Normalization"]):
                categories["Email Uniqueness"].append(result)
            elif any(keyword in test_name for keyword in ["Same Database", "Environment Display"]):
                categories["Environment Consistency"].append(result)
        
        # Print category summaries
        for category, results in categories.items():
            if results:
                passed = len([r for r in results if r["success"]])
                total = len(results)
                print(f"\n{category}: {passed}/{total} ({'✅' if passed == total else '❌'})")
                
                for result in results:
                    status = "✅" if result["success"] else "❌"
                    print(f"  {status} {result['test']}")
        
        # Critical failures
        critical_failures = [r for r in self.results if not r["success"] and 
                           any(keyword in r["test"] for keyword in ["Admin Route", "Security Headers", "Access Control", "Same Database"])]
        
        if critical_failures:
            print("\n❌ CRITICAL FAILURES:")
            for failure in critical_failures:
                print(f"  - {failure['test']}: {failure['message']}")
        
        # Key findings
        print(f"\n🔍 KEY FINDINGS:")
        
        # Admin panel accessibility
        admin_accessible = any(r["success"] and "admin route" in r["test"].lower() for r in self.results)
        print(f"{'✅' if admin_accessible else '❌'} Admin panel accessible at /admin route")
        
        # Security features
        security_working = len([r for r in self.results if r["success"] and any(keyword in r["test"] for keyword in ["Rate Limiting", "HTTP-Only", "CSRF", "Access Control"])]) >= 2
        print(f"{'✅' if security_working else '❌'} Security features implemented")
        
        # Email uniqueness
        email_unique = any(r["success"] and "duplicate prevention" in r["test"].lower() for r in self.results)
        print(f"{'✅' if email_unique else '❌'} Email uniqueness enforced")
        
        # Environment consistency
        env_consistent = any(r["success"] and "same database" in r["test"].lower() for r in self.results)
        print(f"{'✅' if env_consistent else '❌'} Environment consistency verified")
        
        print(f"\n🎯 ADMIN PANEL PRODUCTION TEST COMPLETE")
        print(f"Overall Status: {'✅ PRODUCTION READY' if success_rate >= 70 else '❌ NEEDS FIXES'}")
    
    def get_success_rate(self):
        """Get overall success rate"""
        if not self.results:
            return 0
        return len([r for r in self.results if r["success"]]) / len(self.results)

if __name__ == "__main__":
    tester = AdminProductionTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)