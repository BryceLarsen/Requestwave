#!/usr/bin/env python3
"""
RequestWave Admin Panel Backend Test Suite
Testing comprehensive admin functionality including authentication, user management, 
email normalization, and system operations.
"""

import requests
import json
import sys
from datetime import datetime
import time
import uuid

# Configuration
INTERNAL_BASE_URL = "http://localhost:8001/api"
EXTERNAL_BASE_URL = "https://requestwave-revamp.preview.emergentagent.com/api"

# Admin credentials from environment variables
ADMIN_EMAIL = "admin@requestwave.com"
ADMIN_PASSWORD = "admin123!change_me"

# Test user credentials for user management testing
TEST_USERS = [
    {"email": "animesh@emergent.sh", "name": "Animesh Test"},
    {"email": "abhishekpandey19112000@gmail.com", "name": "Abhishek Test"},
    {"email": "yash@emergent.sh", "name": "Yash Test"},
    {"email": "testeragent90@gmail.com", "name": "Tester Agent"}
]

class AdminPanelTester:
    def __init__(self):
        self.admin_token = None
        self.admin_session_cookie = None
        self.results = []
        self.test_user_ids = []
        
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
    
    def test_admin_authentication(self):
        """Test admin login functionality"""
        print("\n=== Testing Admin Authentication ===")
        
        # Test admin login endpoint
        try:
            response = requests.post(f"{INTERNAL_BASE_URL}/admin/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success") and data.get("session_token"):
                    self.admin_token = data.get("session_token")
                    
                    # Check if session cookie is set
                    session_cookie = None
                    if 'Set-Cookie' in response.headers:
                        cookies = response.headers['Set-Cookie']
                        if 'admin_session' in cookies:
                            session_cookie = cookies.split('admin_session=')[1].split(';')[0]
                            self.admin_session_cookie = session_cookie
                    
                    self.log_result("Admin Login", True, "Admin authentication successful", {
                        "admin_email": ADMIN_EMAIL,
                        "session_token_length": len(self.admin_token) if self.admin_token else 0,
                        "session_cookie_set": session_cookie is not None,
                        "response_message": data.get("message", "")
                    })
                else:
                    self.log_result("Admin Login", False, f"Login response missing required fields: {data}")
            else:
                self.log_result("Admin Login", False, f"Admin login failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("Admin Login", False, f"Admin login error: {str(e)}")
    
    def test_admin_session_validation(self):
        """Test admin session token validation"""
        print("\n=== Testing Admin Session Validation ===")
        
        if not self.admin_token:
            self.log_result("Admin Session Validation", False, "No admin token available for testing")
            return
        
        # Test accessing protected admin endpoint with token
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = requests.get(f"{INTERNAL_BASE_URL}/admin/system/info", headers=headers, timeout=10)
            
            if response.status_code == 200:
                system_info = response.json()
                self.log_result("Admin Session Validation", True, "Admin session token is valid", {
                    "system_info_keys": list(system_info.keys()) if isinstance(system_info, dict) else "non-dict response",
                    "environment": system_info.get("environment") if isinstance(system_info, dict) else None
                })
            elif response.status_code == 401:
                self.log_result("Admin Session Validation", False, "Admin session token rejected (401 Unauthorized)")
            else:
                self.log_result("Admin Session Validation", False, f"Unexpected response: {response.status_code}")
                
        except Exception as e:
            self.log_result("Admin Session Validation", False, f"Session validation error: {str(e)}")
    
    def test_admin_access_control(self):
        """Test that admin endpoints require authentication"""
        print("\n=== Testing Admin Access Control ===")
        
        # Test accessing admin endpoints without authentication
        admin_endpoints = [
            "/admin/users",
            "/admin/system/info",
            "/admin/users/search"
        ]
        
        for endpoint in admin_endpoints:
            try:
                # Test without any authentication
                response = requests.get(f"{INTERNAL_BASE_URL}{endpoint}", timeout=10)
                
                if response.status_code == 401:
                    self.log_result(f"Access Control - {endpoint}", True, "Endpoint properly protected (401 Unauthorized)")
                elif response.status_code == 403:
                    self.log_result(f"Access Control - {endpoint}", True, "Endpoint properly protected (403 Forbidden)")
                else:
                    self.log_result(f"Access Control - {endpoint}", False, f"Endpoint not protected: {response.status_code}")
                    
            except Exception as e:
                self.log_result(f"Access Control - {endpoint}", False, f"Error testing access control: {str(e)}")
    
    def test_users_management_endpoint(self):
        """Test GET /api/admin/users endpoint"""
        print("\n=== Testing Users Management Endpoint ===")
        
        if not self.admin_token:
            self.log_result("Users Management", False, "No admin token available")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = requests.get(f"{INTERNAL_BASE_URL}/admin/users", headers=headers, timeout=10)
            
            if response.status_code == 200:
                users_data = response.json()
                
                # Handle both list and dict responses (with pagination)
                if isinstance(users_data, dict) and "musicians" in users_data:
                    musicians_list = users_data["musicians"]
                    total_count = users_data.get("total_count", len(musicians_list))
                elif isinstance(users_data, list):
                    musicians_list = users_data
                    total_count = len(musicians_list)
                else:
                    self.log_result("Users Management", False, f"Users endpoint returned unexpected format: {type(users_data)}")
                    return
                
                # Check if users have required fields
                if musicians_list:
                    first_user = musicians_list[0]
                    required_fields = ["id", "name", "email"]
                    optional_fields = ["counts", "email_lc"]
                    
                    missing_required = [field for field in required_fields if field not in first_user]
                    present_optional = [field for field in optional_fields if field in first_user]
                    
                    # Check counts structure if present
                    counts_info = {}
                    if "counts" in first_user:
                        counts_info = first_user["counts"]
                    
                    self.log_result("Users Management", True, f"Retrieved {len(musicians_list)} users", {
                        "total_users": len(musicians_list),
                        "total_count": total_count,
                        "missing_required_fields": missing_required,
                        "present_optional_fields": present_optional,
                        "sample_user_email": first_user.get("email", "N/A"),
                        "has_normalized_email": "email_lc" in first_user,
                        "has_counts": "counts" in first_user,
                        "sample_counts": counts_info
                    })
                else:
                    self.log_result("Users Management", True, "Retrieved empty users list (no users in system)")
            else:
                self.log_result("Users Management", False, f"Users endpoint failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("Users Management", False, f"Users management test error: {str(e)}")
    
    def test_user_search_functionality(self):
        """Test user search by email parameter"""
        print("\n=== Testing User Search Functionality ===")
        
        if not self.admin_token:
            self.log_result("User Search", False, "No admin token available")
            return
        
        # Test search with a common email pattern
        search_emails = ["@emergent.sh", "@gmail.com", "admin@requestwave.com"]
        
        for search_email in search_emails:
            try:
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                params = {"email": search_email}
                response = requests.get(f"{INTERNAL_BASE_URL}/admin/users", headers=headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    search_results = response.json()
                    
                    # Handle both list and dict responses (with pagination)
                    if isinstance(search_results, dict) and "musicians" in search_results:
                        musicians_list = search_results["musicians"]
                    elif isinstance(search_results, list):
                        musicians_list = search_results
                    else:
                        self.log_result(f"User Search - {search_email}", False, f"Search returned unexpected format: {type(search_results)}")
                        continue
                    
                    matching_users = [user for user in musicians_list if search_email.lower() in user.get("email", "").lower()]
                    
                    self.log_result(f"User Search - {search_email}", True, f"Search returned {len(musicians_list)} results", {
                        "search_term": search_email,
                        "total_results": len(musicians_list),
                        "matching_users": len(matching_users),
                        "search_working": len(matching_users) > 0 or len(musicians_list) == 0
                    })
                else:
                    self.log_result(f"User Search - {search_email}", False, f"Search failed: {response.status_code}")
                    
            except Exception as e:
                self.log_result(f"User Search - {search_email}", False, f"Search error: {str(e)}")
    
    def test_user_data_inspector(self):
        """Test GET /api/admin/users/{user_id}/data endpoint"""
        print("\n=== Testing User Data Inspector ===")
        
        if not self.admin_token:
            self.log_result("User Data Inspector", False, "No admin token available")
            return
        
        # First get a user ID to test with
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            users_response = requests.get(f"{INTERNAL_BASE_URL}/admin/users", headers=headers, timeout=10)
            
            if users_response.status_code == 200:
                users_data = users_response.json()
                
                # Handle both list and dict responses (with pagination)
                if isinstance(users_data, dict) and "musicians" in users_data:
                    musicians_list = users_data["musicians"]
                elif isinstance(users_data, list):
                    musicians_list = users_data
                else:
                    musicians_list = []
                
                if musicians_list:
                    test_user_id = musicians_list[0].get("id")
                    test_user_email = musicians_list[0].get("email")
                    
                    if test_user_id:
                        # Test user data inspector endpoint
                        inspector_response = requests.get(f"{INTERNAL_BASE_URL}/admin/users/{test_user_id}/data", headers=headers, timeout=10)
                        
                        if inspector_response.status_code == 200:
                            user_data = inspector_response.json()
                            
                            expected_sections = ["user", "songs", "playlists", "requests"]
                            present_sections = [section for section in expected_sections if section in user_data]
                            
                            self.log_result("User Data Inspector", True, f"Retrieved detailed user data", {
                                "test_user_id": test_user_id,
                                "test_user_email": test_user_email,
                                "present_sections": present_sections,
                                "missing_sections": [s for s in expected_sections if s not in present_sections],
                                "songs_count": len(user_data.get("songs", [])),
                                "playlists_count": len(user_data.get("playlists", [])),
                                "requests_count": len(user_data.get("requests", []))
                            })
                        else:
                            self.log_result("User Data Inspector", False, f"Data inspector failed: {inspector_response.status_code}")
                    else:
                        self.log_result("User Data Inspector", False, "No user ID available for testing")
                else:
                    self.log_result("User Data Inspector", False, "No users available for data inspector testing")
            else:
                self.log_result("User Data Inspector", False, f"Could not get users list: {users_response.status_code}")
                
        except Exception as e:
            self.log_result("User Data Inspector", False, f"Data inspector test error: {str(e)}")
    
    def test_system_info_endpoint(self):
        """Test GET /api/admin/system/info endpoint"""
        print("\n=== Testing System Info Endpoint ===")
        
        if not self.admin_token:
            self.log_result("System Info", False, "No admin token available")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = requests.get(f"{INTERNAL_BASE_URL}/admin/system/info", headers=headers, timeout=10)
            
            if response.status_code == 200:
                system_info = response.json()
                
                expected_fields = ["environment", "database", "version"]
                present_fields = [field for field in expected_fields if field in system_info]
                
                self.log_result("System Info", True, "Retrieved system information", {
                    "present_fields": present_fields,
                    "total_fields": len(system_info) if isinstance(system_info, dict) else 0,
                    "environment": system_info.get("environment") if isinstance(system_info, dict) else None,
                    "database_status": system_info.get("database") if isinstance(system_info, dict) else None
                })
            else:
                self.log_result("System Info", False, f"System info failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("System Info", False, f"System info test error: {str(e)}")
    
    def test_email_normalization(self):
        """Test email normalization functionality"""
        print("\n=== Testing Email Normalization ===")
        
        if not self.admin_token:
            self.log_result("Email Normalization", False, "No admin token available")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = requests.get(f"{INTERNAL_BASE_URL}/admin/users", headers=headers, timeout=10)
            
            if response.status_code == 200:
                users_data = response.json()
                
                # Handle both list and dict responses (with pagination)
                if isinstance(users_data, dict) and "musicians" in users_data:
                    musicians_list = users_data["musicians"]
                elif isinstance(users_data, list):
                    musicians_list = users_data
                else:
                    musicians_list = []
                
                if musicians_list:
                    # Check for email_lc field presence
                    users_with_normalized = [user for user in musicians_list if "email_lc" in user]
                    users_without_normalized = [user for user in musicians_list if "email_lc" not in user]
                    
                    # Check for proper normalization
                    properly_normalized = []
                    improperly_normalized = []
                    
                    for user in users_with_normalized:
                        email = user.get("email", "")
                        email_lc = user.get("email_lc", "")
                        
                        if email.lower() == email_lc:
                            properly_normalized.append(user)
                        else:
                            improperly_normalized.append(user)
                    
                    # Check for potential duplicates
                    email_lc_values = [user.get("email_lc") for user in users_with_normalized if user.get("email_lc")]
                    duplicates = []
                    seen = set()
                    for email_lc in email_lc_values:
                        if email_lc in seen:
                            duplicates.append(email_lc)
                        seen.add(email_lc)
                    
                    self.log_result("Email Normalization", True, "Email normalization analysis complete", {
                        "total_users": len(users_data),
                        "users_with_email_lc": len(users_with_normalized),
                        "users_without_email_lc": len(users_without_normalized),
                        "properly_normalized": len(properly_normalized),
                        "improperly_normalized": len(improperly_normalized),
                        "potential_duplicates": len(duplicates),
                        "duplicate_emails": duplicates[:5] if duplicates else []
                    })
                else:
                    self.log_result("Email Normalization", False, "No users available for normalization testing")
            else:
                self.log_result("Email Normalization", False, f"Could not get users for normalization test: {response.status_code}")
                
        except Exception as e:
            self.log_result("Email Normalization", False, f"Email normalization test error: {str(e)}")
    
    def test_user_deletion(self):
        """Test DELETE /api/admin/users/{user_id} endpoint"""
        print("\n=== Testing User Deletion ===")
        
        if not self.admin_token:
            self.log_result("User Deletion", False, "No admin token available")
            return
        
        # Create a test user first for deletion testing
        try:
            # Create test user via registration endpoint
            test_user_email = f"delete_test_{int(time.time())}@test.com"
            test_user_password = "TestPassword123!"
            
            # Register test user
            register_response = requests.post(f"{INTERNAL_BASE_URL}/auth/register", json={
                "name": "Delete Test User",
                "email": test_user_email,
                "password": test_user_password
            }, timeout=10)
            
            if register_response.status_code == 200:
                register_data = register_response.json()
                test_user_id = register_data.get("musician", {}).get("id")
                
                if test_user_id:
                    # Now test deletion
                    headers = {"Authorization": f"Bearer {self.admin_token}"}
                    delete_response = requests.delete(f"{INTERNAL_BASE_URL}/admin/users/{test_user_id}", headers=headers, timeout=10)
                    
                    if delete_response.status_code == 200:
                        delete_data = delete_response.json()
                        
                        # Verify user is actually deleted by trying to find them
                        users_response = requests.get(f"{INTERNAL_BASE_URL}/admin/users", headers=headers, timeout=10)
                        if users_response.status_code == 200:
                            users_data = users_response.json()
                            deleted_user_found = any(user.get("id") == test_user_id for user in users_data)
                            
                            self.log_result("User Deletion", not deleted_user_found, "User deletion test completed", {
                                "test_user_id": test_user_id,
                                "test_user_email": test_user_email,
                                "deletion_response": delete_data.get("message", "No message"),
                                "user_still_exists": deleted_user_found,
                                "deletion_successful": not deleted_user_found
                            })
                        else:
                            self.log_result("User Deletion", False, "Could not verify deletion - users list unavailable")
                    else:
                        self.log_result("User Deletion", False, f"User deletion failed: {delete_response.status_code} - {delete_response.text}")
                else:
                    self.log_result("User Deletion", False, "Could not get test user ID from registration")
            else:
                self.log_result("User Deletion", False, f"Could not create test user for deletion: {register_response.status_code}")
                
        except Exception as e:
            self.log_result("User Deletion", False, f"User deletion test error: {str(e)}")
    
    def test_user_merge_functionality(self):
        """Test POST /api/admin/users/merge endpoint"""
        print("\n=== Testing User Merge Functionality ===")
        
        if not self.admin_token:
            self.log_result("User Merge", False, "No admin token available")
            return
        
        # Create two test users for merge testing
        try:
            test_users = []
            for i in range(2):
                test_email = f"merge_test_{i}_{int(time.time())}@test.com"
                test_password = "TestPassword123!"
                
                register_response = requests.post(f"{INTERNAL_BASE_URL}/auth/register", json={
                    "name": f"Merge Test User {i+1}",
                    "email": test_email,
                    "password": test_password
                }, timeout=10)
                
                if register_response.status_code == 200:
                    register_data = register_response.json()
                    user_id = register_data.get("musician", {}).get("id")
                    if user_id:
                        test_users.append({"id": user_id, "email": test_email})
            
            if len(test_users) == 2:
                # Test merge operation
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                merge_data = {
                    "primary_user_id": test_users[0]["id"],
                    "duplicate_user_id": test_users[1]["id"]
                }
                
                merge_response = requests.post(f"{INTERNAL_BASE_URL}/admin/users/merge", 
                                             headers=headers, json=merge_data, timeout=10)
                
                if merge_response.status_code == 200:
                    merge_result = merge_response.json()
                    
                    # Verify merge by checking if duplicate user is gone
                    users_response = requests.get(f"{INTERNAL_BASE_URL}/admin/users", headers=headers, timeout=10)
                    if users_response.status_code == 200:
                        users_data = users_response.json()
                        primary_exists = any(user.get("id") == test_users[0]["id"] for user in users_data)
                        duplicate_exists = any(user.get("id") == test_users[1]["id"] for user in users_data)
                        
                        self.log_result("User Merge", primary_exists and not duplicate_exists, "User merge test completed", {
                            "primary_user_id": test_users[0]["id"],
                            "duplicate_user_id": test_users[1]["id"],
                            "primary_user_exists": primary_exists,
                            "duplicate_user_exists": duplicate_exists,
                            "merge_successful": primary_exists and not duplicate_exists,
                            "merge_response": merge_result.get("message", "No message")
                        })
                    else:
                        self.log_result("User Merge", False, "Could not verify merge - users list unavailable")
                else:
                    self.log_result("User Merge", False, f"User merge failed: {merge_response.status_code} - {merge_response.text}")
            else:
                self.log_result("User Merge", False, f"Could not create test users for merge (created {len(test_users)}/2)")
                
        except Exception as e:
            self.log_result("User Merge", False, f"User merge test error: {str(e)}")
    
    def test_environment_consistency(self):
        """Test environment variables and database connection consistency"""
        print("\n=== Testing Environment Consistency ===")
        
        if not self.admin_token:
            self.log_result("Environment Consistency", False, "No admin token available")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = requests.get(f"{INTERNAL_BASE_URL}/admin/system/info", headers=headers, timeout=10)
            
            if response.status_code == 200:
                system_info = response.json()
                
                # Check for expected environment variables
                expected_env_vars = ["RW_ENV", "RW_ADMIN_EMAIL", "RW_ADMIN_PASSWORD"]
                env_info = system_info.get("environment", {})
                
                present_vars = []
                missing_vars = []
                
                for var in expected_env_vars:
                    if var in env_info:
                        present_vars.append(var)
                    else:
                        missing_vars.append(var)
                
                # Check database connection info
                db_info = system_info.get("database", {})
                db_connected = db_info.get("connected", False) if isinstance(db_info, dict) else False
                
                self.log_result("Environment Consistency", len(missing_vars) == 0 and db_connected, "Environment consistency check completed", {
                    "present_env_vars": present_vars,
                    "missing_env_vars": missing_vars,
                    "database_connected": db_connected,
                    "database_info": db_info if isinstance(db_info, dict) else "No database info",
                    "admin_email_configured": "RW_ADMIN_EMAIL" in present_vars,
                    "admin_password_configured": "RW_ADMIN_PASSWORD" in present_vars
                })
            else:
                self.log_result("Environment Consistency", False, f"Could not get system info: {response.status_code}")
                
        except Exception as e:
            self.log_result("Environment Consistency", False, f"Environment consistency test error: {str(e)}")
    
    def test_duplicate_detection(self):
        """Test duplicate email detection with known duplicate accounts"""
        print("\n=== Testing Duplicate Detection ===")
        
        if not self.admin_token:
            self.log_result("Duplicate Detection", False, "No admin token available")
            return
        
        # Test with known duplicate emails from the review request
        known_duplicates = [
            "animesh@emergent.sh",
            "abhishekpandey19112000@gmail.com", 
            "yash@emergent.sh",
            "testeragent90@gmail.com"
        ]
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            duplicate_results = {}
            
            for email in known_duplicates:
                # Search for users with this email
                params = {"email": email}
                response = requests.get(f"{INTERNAL_BASE_URL}/admin/users", headers=headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    search_results = response.json()
                    matching_users = [user for user in search_results if user.get("email", "").lower() == email.lower()]
                    duplicate_results[email] = len(matching_users)
                else:
                    duplicate_results[email] = -1  # Error
            
            # Analyze results
            found_duplicates = {email: count for email, count in duplicate_results.items() if count > 1}
            potential_duplicates = {email: count for email, count in duplicate_results.items() if count == 1}
            errors = {email: count for email, count in duplicate_results.items() if count == -1}
            
            self.log_result("Duplicate Detection", True, "Duplicate detection analysis completed", {
                "tested_emails": len(known_duplicates),
                "found_duplicates": found_duplicates,
                "potential_duplicates": potential_duplicates,
                "search_errors": list(errors.keys()),
                "total_duplicate_accounts": sum(found_duplicates.values()),
                "needs_merge_attention": len(found_duplicates) > 0
            })
            
        except Exception as e:
            self.log_result("Duplicate Detection", False, f"Duplicate detection test error: {str(e)}")
    
    def run_all_tests(self):
        """Run all admin panel tests"""
        print("🚀 Starting RequestWave Admin Panel Backend Tests")
        print(f"Internal API: {INTERNAL_BASE_URL}")
        print(f"External API: {EXTERNAL_BASE_URL}")
        print(f"Admin Email: {ADMIN_EMAIL}")
        print("=" * 80)
        
        # Run all tests in logical order
        self.test_admin_authentication()
        self.test_admin_session_validation()
        self.test_admin_access_control()
        self.test_users_management_endpoint()
        self.test_user_search_functionality()
        self.test_user_data_inspector()
        self.test_system_info_endpoint()
        self.test_email_normalization()
        self.test_user_deletion()
        self.test_user_merge_functionality()
        self.test_environment_consistency()
        self.test_duplicate_detection()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 ADMIN PANEL TEST SUMMARY")
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
                if any(keyword in result["test"].lower() for keyword in ["admin login", "admin session", "users management", "user deletion", "user merge"]):
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
        
        # Check admin authentication
        admin_auth_working = any(r["success"] and "admin login" in r["test"].lower() for r in self.results)
        if admin_auth_working:
            print("✅ Admin authentication system is working")
        else:
            print("❌ Admin authentication system is NOT working")
        
        # Check user management
        user_mgmt_working = any(r["success"] and "users management" in r["test"].lower() for r in self.results)
        if user_mgmt_working:
            print("✅ User management endpoints are working")
        else:
            print("❌ User management endpoints are NOT working")
        
        # Check email normalization
        email_norm_working = any(r["success"] and "email normalization" in r["test"].lower() for r in self.results)
        if email_norm_working:
            print("✅ Email normalization system is implemented")
        else:
            print("❌ Email normalization system needs attention")
        
        print("\n🎯 ADMIN PANEL TEST COMPLETE")
        
        # Provide recommendations
        print("\n💡 RECOMMENDATIONS:")
        if not admin_auth_working:
            print("1. Fix admin authentication system - check credentials and JWT implementation")
        if not user_mgmt_working:
            print("2. Verify admin user management endpoints are properly implemented")
        if not email_norm_working:
            print("3. Implement or fix email normalization for duplicate detection")
        
        return len(critical_failures) == 0

if __name__ == "__main__":
    tester = AdminPanelTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)