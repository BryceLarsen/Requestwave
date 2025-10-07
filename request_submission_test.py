#!/usr/bin/env python3
"""
Request Submission Test Suite - Testing Datetime Bug Fix
Testing the audience song request submission functionality after fixing the datetime bug 
in get_subscription_status function (lines 945-946 in server.py).

CONTEXT: Fixed critical bug where current_period_start was set to raw signup_date string 
instead of parsed signup_dt datetime object, causing TypeError during request submission.

Focus Areas:
1. POST /api/requests endpoint with valid song request data
2. Full request submission flow for different musician accounts 
3. Subscription status checking works correctly
4. Request limits and validation 
5. Verify the fix doesn't break existing functionality
"""

import requests
import json
import sys
from datetime import datetime
import time

# Configuration - Use external URL for testing
BACKEND_URL = "https://request-error-fix.preview.emergentagent.com/api"
TEST_MUSICIAN_ID = "a39296f0-20da-4516-85d1-56af59eb772f"  # Bryce Larsen
TEST_SONG_ID = "4e23f254-db09-480a-93c2-17019e9fca0e"  # We Don't Talk About Bruno
TEST_EMAIL = "brycelarsenmusic@gmail.com"
TEST_PASSWORD = "RequestWave2024!"

class RequestSubmissionTester:
    def __init__(self):
        self.token = None
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
            print(f"   Details: {json.dumps(details, indent=2, default=str)}")
    
    def authenticate(self):
        """Authenticate with the backend API"""
        print("\n=== Authentication ===")
        
        try:
            response = requests.post(f"{BACKEND_URL}/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                musician_data = data.get("musician", {})
                self.musician_id = musician_data.get("id")
                
                self.log_result("Authentication", True, f"Successfully authenticated {TEST_EMAIL}", {
                    "musician_id": self.musician_id,
                    "musician_name": musician_data.get("name"),
                    "token_length": len(self.token) if self.token else 0
                })
                return True
            else:
                self.log_result("Authentication", False, f"Login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Authentication", False, f"Auth error: {str(e)}")
            return False
    
    def test_subscription_status_endpoint(self):
        """Test GET /api/subscription/status endpoint - this is where the datetime bug was occurring"""
        print("\n=== Testing Subscription Status Endpoint (Datetime Bug Fix) ===")
        
        if not self.token:
            self.log_result("Subscription Status", False, "No authentication token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{BACKEND_URL}/subscription/status", headers=headers, timeout=30)
            
            if response.status_code == 200:
                status_data = response.json()
                
                # Verify the response structure
                required_fields = ["plan", "can_make_request"]
                missing_fields = [field for field in required_fields if field not in status_data]
                
                if not missing_fields:
                    self.log_result("Subscription Status", True, "Subscription status endpoint working correctly", {
                        "plan": status_data.get("plan"),
                        "can_make_request": status_data.get("can_make_request"),
                        "requests_used": status_data.get("requests_used"),
                        "requests_limit": status_data.get("requests_limit"),
                        "trial_ends_at": status_data.get("trial_ends_at"),
                        "next_reset_date": status_data.get("next_reset_date")
                    })
                    return True
                else:
                    self.log_result("Subscription Status", False, f"Missing required fields: {missing_fields}")
                    return False
            else:
                self.log_result("Subscription Status", False, f"Status endpoint failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Subscription Status", False, f"Error testing subscription status: {str(e)}")
            return False
    
    def test_musician_profile_access(self):
        """Test accessing the musician profile to verify it exists"""
        print(f"\n=== Testing Musician Profile Access (ID: {TEST_MUSICIAN_ID}) ===")
        
        try:
            # Try to access musician by slug first
            response = requests.get(f"{BACKEND_URL}/musicians/bryce-larsen", timeout=30)
            
            if response.status_code == 200:
                musician_data = response.json()
                actual_musician_id = musician_data.get("id")
                
                self.log_result("Musician Profile Access", True, "Successfully accessed musician profile", {
                    "musician_id": actual_musician_id,
                    "name": musician_data.get("name"),
                    "slug": musician_data.get("slug"),
                    "requests_enabled": musician_data.get("requests_enabled"),
                    "tips_enabled": musician_data.get("tips_enabled"),
                    "id_matches_test": actual_musician_id == TEST_MUSICIAN_ID
                })
                
                # Update TEST_MUSICIAN_ID if different
                if actual_musician_id != TEST_MUSICIAN_ID:
                    global TEST_MUSICIAN_ID
                    TEST_MUSICIAN_ID = actual_musician_id
                    print(f"   Updated TEST_MUSICIAN_ID to: {TEST_MUSICIAN_ID}")
                
                return True
            else:
                self.log_result("Musician Profile Access", False, f"Could not access musician profile: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Musician Profile Access", False, f"Error accessing musician profile: {str(e)}")
            return False
    
    def test_songs_availability(self):
        """Test that songs are available for the musician"""
        print(f"\n=== Testing Songs Availability ===")
        
        try:
            response = requests.get(f"{BACKEND_URL}/musicians/bryce-larsen/songs", timeout=30)
            
            if response.status_code == 200:
                songs_data = response.json()
                
                if isinstance(songs_data, list) and len(songs_data) > 0:
                    # Look for the specific test song or use the first available song
                    test_song = None
                    for song in songs_data:
                        if song.get("id") == TEST_SONG_ID:
                            test_song = song
                            break
                    
                    if not test_song:
                        test_song = songs_data[0]  # Use first available song
                        global TEST_SONG_ID
                        TEST_SONG_ID = test_song.get("id")
                        print(f"   Updated TEST_SONG_ID to: {TEST_SONG_ID}")
                    
                    self.log_result("Songs Availability", True, f"Found {len(songs_data)} songs available", {
                        "total_songs": len(songs_data),
                        "test_song_id": TEST_SONG_ID,
                        "test_song_title": test_song.get("title"),
                        "test_song_artist": test_song.get("artist"),
                        "original_song_found": any(s.get("id") == "4e23f254-db09-480a-93c2-17019e9fca0e" for s in songs_data)
                    })
                    return True
                else:
                    self.log_result("Songs Availability", False, "No songs available for musician")
                    return False
            else:
                self.log_result("Songs Availability", False, f"Could not get songs: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Songs Availability", False, f"Error getting songs: {str(e)}")
            return False
    
    def test_request_submission_basic(self):
        """Test basic request submission - this is where the datetime bug was causing 500 errors"""
        print(f"\n=== Testing Basic Request Submission (Datetime Bug Fix) ===")
        
        if not TEST_SONG_ID:
            self.log_result("Basic Request Submission", False, "No test song ID available")
            return False
        
        try:
            request_data = {
                "song_id": TEST_SONG_ID,
                "requester_name": "Test Audience Member",
                "requester_email": "test.audience@example.com",
                "dedication": "Testing the datetime bug fix!",
                "tip_amount": 0.0
            }
            
            response = requests.post(f"{BACKEND_URL}/requests", json=request_data, timeout=30)
            
            if response.status_code == 200:
                request_response = response.json()
                
                self.log_result("Basic Request Submission", True, "Successfully submitted song request", {
                    "request_id": request_response.get("id"),
                    "song_title": request_response.get("song_title"),
                    "song_artist": request_response.get("song_artist"),
                    "requester_name": request_response.get("requester_name"),
                    "status": request_response.get("status"),
                    "created_at": request_response.get("created_at"),
                    "musician_id": request_response.get("musician_id")
                })
                return request_response.get("id")
            else:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("detail", error_detail)
                except:
                    pass
                
                self.log_result("Basic Request Submission", False, f"Request submission failed: {response.status_code}", {
                    "status_code": response.status_code,
                    "error_detail": error_detail,
                    "request_data": request_data
                })
                return False
                
        except Exception as e:
            self.log_result("Basic Request Submission", False, f"Error submitting request: {str(e)}")
            return False
    
    def test_request_submission_with_musician_slug(self):
        """Test request submission using the musician-specific endpoint"""
        print(f"\n=== Testing Request Submission via Musician Slug Endpoint ===")
        
        if not TEST_SONG_ID:
            self.log_result("Musician Slug Request Submission", False, "No test song ID available")
            return False
        
        try:
            request_data = {
                "song_id": TEST_SONG_ID,
                "requester_name": "Test Audience Member 2",
                "requester_email": "test.audience2@example.com",
                "dedication": "Testing musician slug endpoint!",
                "tip_amount": 5.0
            }
            
            response = requests.post(f"{BACKEND_URL}/musicians/bryce-larsen/requests", json=request_data, timeout=30)
            
            if response.status_code == 200:
                request_response = response.json()
                
                self.log_result("Musician Slug Request Submission", True, "Successfully submitted request via musician slug", {
                    "request_id": request_response.get("id"),
                    "song_title": request_response.get("song_title"),
                    "song_artist": request_response.get("song_artist"),
                    "tip_amount": request_response.get("tip_amount"),
                    "endpoint_used": "/musicians/bryce-larsen/requests"
                })
                return request_response.get("id")
            else:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("detail", error_detail)
                except:
                    pass
                
                self.log_result("Musician Slug Request Submission", False, f"Musician slug request failed: {response.status_code}", {
                    "status_code": response.status_code,
                    "error_detail": error_detail
                })
                return False
                
        except Exception as e:
            self.log_result("Musician Slug Request Submission", False, f"Error with musician slug request: {str(e)}")
            return False
    
    def test_request_validation(self):
        """Test request validation with invalid data"""
        print(f"\n=== Testing Request Validation ===")
        
        test_cases = [
            {
                "name": "Missing Song ID",
                "data": {
                    "requester_name": "Test User",
                    "requester_email": "test@example.com",
                    "dedication": "Test"
                },
                "expected_status": [400, 422]
            },
            {
                "name": "Invalid Song ID",
                "data": {
                    "song_id": "invalid-song-id-12345",
                    "requester_name": "Test User",
                    "requester_email": "test@example.com",
                    "dedication": "Test"
                },
                "expected_status": [404]
            },
            {
                "name": "Missing Requester Name",
                "data": {
                    "song_id": TEST_SONG_ID,
                    "requester_email": "test@example.com",
                    "dedication": "Test"
                },
                "expected_status": [400, 422]
            }
        ]
        
        validation_results = []
        
        for test_case in test_cases:
            try:
                response = requests.post(f"{BACKEND_URL}/requests", json=test_case["data"], timeout=30)
                
                if response.status_code in test_case["expected_status"]:
                    validation_results.append(True)
                    self.log_result(f"Validation - {test_case['name']}", True, f"Correctly rejected invalid data: {response.status_code}")
                else:
                    validation_results.append(False)
                    self.log_result(f"Validation - {test_case['name']}", False, f"Unexpected status: {response.status_code}, expected: {test_case['expected_status']}")
                    
            except Exception as e:
                validation_results.append(False)
                self.log_result(f"Validation - {test_case['name']}", False, f"Error testing validation: {str(e)}")
        
        all_passed = all(validation_results)
        self.log_result("Request Validation Overall", all_passed, f"Validation tests: {sum(validation_results)}/{len(validation_results)} passed")
        return all_passed
    
    def test_backend_logs_check(self):
        """Check backend logs for any remaining errors"""
        print(f"\n=== Checking Backend Logs ===")
        
        try:
            # Check supervisor backend logs
            import subprocess
            result = subprocess.run(
                ["tail", "-n", "50", "/var/log/supervisor/backend.err.log"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                log_content = result.stdout
                
                # Look for error patterns
                error_patterns = [
                    "TypeError",
                    "AttributeError", 
                    "datetime",
                    "current_period_start",
                    "signup_date",
                    "500 Internal Server Error"
                ]
                
                found_errors = []
                for pattern in error_patterns:
                    if pattern.lower() in log_content.lower():
                        found_errors.append(pattern)
                
                if found_errors:
                    self.log_result("Backend Logs Check", False, f"Found error patterns in logs: {found_errors}", {
                        "error_patterns": found_errors,
                        "log_sample": log_content[-500:] if log_content else "No log content"
                    })
                else:
                    self.log_result("Backend Logs Check", True, "No error patterns found in recent backend logs", {
                        "log_lines_checked": len(log_content.split('\n')) if log_content else 0
                    })
                    
                return len(found_errors) == 0
            else:
                self.log_result("Backend Logs Check", False, f"Could not read backend logs: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_result("Backend Logs Check", False, f"Error checking backend logs: {str(e)}")
            return False
    
    def test_multiple_requests_flow(self):
        """Test submitting multiple requests to verify the fix works consistently"""
        print(f"\n=== Testing Multiple Requests Flow ===")
        
        if not TEST_SONG_ID:
            self.log_result("Multiple Requests Flow", False, "No test song ID available")
            return False
        
        successful_requests = 0
        total_requests = 3
        
        for i in range(total_requests):
            try:
                request_data = {
                    "song_id": TEST_SONG_ID,
                    "requester_name": f"Test User {i+1}",
                    "requester_email": f"test{i+1}@example.com",
                    "dedication": f"Test request #{i+1} - datetime bug fix verification",
                    "tip_amount": float(i * 2)
                }
                
                response = requests.post(f"{BACKEND_URL}/requests", json=request_data, timeout=30)
                
                if response.status_code == 200:
                    successful_requests += 1
                    print(f"   ✅ Request {i+1}/3 successful")
                else:
                    print(f"   ❌ Request {i+1}/3 failed: {response.status_code}")
                
                # Small delay between requests
                time.sleep(0.5)
                
            except Exception as e:
                print(f"   ❌ Request {i+1}/3 error: {str(e)}")
        
        success_rate = (successful_requests / total_requests) * 100
        
        self.log_result("Multiple Requests Flow", successful_requests == total_requests, 
                       f"Successfully submitted {successful_requests}/{total_requests} requests", {
                           "success_rate": f"{success_rate:.1f}%",
                           "successful_requests": successful_requests,
                           "total_requests": total_requests
                       })
        
        return successful_requests == total_requests
    
    def run_all_tests(self):
        """Run all request submission tests"""
        print("🚀 Starting Request Submission Tests - Datetime Bug Fix Verification")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Test Musician ID: {TEST_MUSICIAN_ID}")
        print(f"Test Song ID: {TEST_SONG_ID}")
        print("=" * 80)
        
        # Run tests in order
        auth_success = self.authenticate()
        if not auth_success:
            print("❌ Authentication failed - cannot continue with tests")
            return False
        
        self.test_subscription_status_endpoint()
        self.test_musician_profile_access()
        self.test_songs_availability()
        
        # Core request submission tests
        basic_request_id = self.test_request_submission_basic()
        slug_request_id = self.test_request_submission_with_musician_slug()
        
        self.test_request_validation()
        self.test_multiple_requests_flow()
        self.test_backend_logs_check()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 REQUEST SUBMISSION TEST SUMMARY")
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
                if any(keyword in result["test"].lower() for keyword in ["basic request submission", "subscription status", "datetime"]):
                    critical_failures.append(result)
                else:
                    minor_failures.append(result)
        
        if critical_failures:
            print("\n❌ CRITICAL FAILURES (Datetime Bug Related):")
            for result in critical_failures:
                print(f"  - {result['test']}: {result['message']}")
        
        if minor_failures:
            print("\n⚠️ MINOR FAILURES:")
            for result in minor_failures:
                print(f"  - {result['test']}: {result['message']}")
        
        # Key findings
        print("\n🔍 KEY FINDINGS:")
        
        # Check if datetime bug is fixed
        datetime_fixed = any(r["success"] and "subscription status" in r["test"].lower() for r in self.results)
        if datetime_fixed:
            print("✅ Datetime bug in get_subscription_status function appears to be FIXED")
        else:
            print("❌ Datetime bug in get_subscription_status function may still exist")
        
        # Check if request submission works
        request_working = any(r["success"] and "basic request submission" in r["test"].lower() for r in self.results)
        if request_working:
            print("✅ Audience song request submission is WORKING")
        else:
            print("❌ Audience song request submission is NOT working")
        
        # Check if validation works
        validation_working = any(r["success"] and "validation overall" in r["test"].lower() for r in self.results)
        if validation_working:
            print("✅ Request validation is working correctly")
        else:
            print("❌ Request validation has issues")
        
        print("\n🎯 REQUEST SUBMISSION TEST COMPLETE")
        
        # Final assessment
        if len(critical_failures) == 0:
            print("\n🎉 SUCCESS: The datetime bug fix appears to be working correctly!")
            print("   Audience members should now be able to submit song requests without 500 errors.")
        else:
            print("\n⚠️ ISSUES FOUND: There are still critical issues that need attention.")
            print("   The datetime bug may not be fully resolved.")
        
        return len(critical_failures) == 0

if __name__ == "__main__":
    tester = RequestSubmissionTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)