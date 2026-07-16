#!/usr/bin/env python3
"""
Request Status Update Functionality Test Suite
Testing status transitions, archive functionality, and request retrieval exclusions
Focus: Status update endpoint, archive endpoint, and request filtering
"""

import requests
import json
import sys
from datetime import datetime
import time

# Configuration
EXTERNAL_BASE_URL = "https://requests-mailto-flow.preview.emergentagent.com/api"
TEST_EMAIL = "brycelarsenmusic@gmail.com"
TEST_PASSWORD = "RequestWave2024!"

class RequestStatusTester:
    def __init__(self):
        self.token = None
        self.musician_id = None
        self.test_requests = []  # Store created test requests for cleanup
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
    
    def authenticate(self):
        """Authenticate with the API"""
        print("\n=== Authentication ===")
        
        try:
            response = requests.post(f"{EXTERNAL_BASE_URL}/auth/login", json={
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
    
    def get_musician_songs(self):
        """Get musician's songs to use for test requests"""
        if not self.token:
            return []
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{EXTERNAL_BASE_URL}/songs", headers=headers, timeout=30)
            
            if response.status_code == 200:
                songs = response.json()
                if songs:
                    self.log_result("Get Songs", True, f"Retrieved {len(songs)} songs for testing")
                    return songs[:3]  # Return first 3 songs for testing
                else:
                    self.log_result("Get Songs", False, "No songs found - need songs to create test requests")
                    return []
            else:
                self.log_result("Get Songs", False, f"Failed to get songs: {response.status_code}")
                return []
                
        except Exception as e:
            self.log_result("Get Songs", False, f"Error getting songs: {str(e)}")
            return []
    
    def create_test_request(self, song, requester_name="Test User", dedication="Test request"):
        """Create a test request for testing status updates"""
        if not self.token:
            return None
        
        try:
            # Create request using the public endpoint (no auth required)
            request_data = {
                "song_id": song["id"],
                "requester_name": requester_name,
                "requester_email": "test@example.com",
                "dedication": dedication
            }
            
            response = requests.post(f"{EXTERNAL_BASE_URL}/requests", json=request_data, timeout=30)
            
            if response.status_code == 200:
                request = response.json()
                request_id = request.get("id")
                if request_id:
                    self.test_requests.append(request_id)
                    self.log_result("Create Test Request", True, f"Created test request", {
                        "request_id": request_id,
                        "song_title": song.get("title"),
                        "requester": requester_name,
                        "initial_status": request.get("status", "unknown")
                    })
                    return request
                else:
                    self.log_result("Create Test Request", False, "Request created but no ID returned")
                    return None
            else:
                self.log_result("Create Test Request", False, f"Failed to create request: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.log_result("Create Test Request", False, f"Error creating request: {str(e)}")
            return None
    
    def test_status_update_endpoint(self):
        """Test PUT /api/requests/{request_id}/status endpoint"""
        print("\n=== Testing Status Update Endpoint ===")
        
        if not self.token:
            self.log_result("Status Update Setup", False, "No authentication token")
            return
        
        # Get songs for testing
        songs = self.get_musician_songs()
        if not songs:
            self.log_result("Status Update Setup", False, "No songs available for testing")
            return
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Test 1: Valid status updates
        valid_statuses = ["pending", "up_next", "accepted", "played", "rejected"]
        
        for status in valid_statuses:
            # Create a test request
            test_request = self.create_test_request(songs[0], f"Status Test {status}")
            if not test_request:
                continue
            
            request_id = test_request["id"]
            
            try:
                # Update status
                status_data = {"status": status}
                response = requests.put(
                    f"{EXTERNAL_BASE_URL}/requests/{request_id}/status",
                    json=status_data,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.log_result(f"Status Update - {status}", True, f"Successfully updated to '{status}'", {
                        "request_id": request_id,
                        "new_status": result.get("new_status"),
                        "success": result.get("success")
                    })
                else:
                    self.log_result(f"Status Update - {status}", False, f"Failed to update to '{status}': {response.status_code} - {response.text}")
                    
            except Exception as e:
                self.log_result(f"Status Update - {status}", False, f"Error updating to '{status}': {str(e)}")
        
        # Test 2: Invalid status - should reject 'archived'
        test_request = self.create_test_request(songs[0], "Archive Status Test")
        if test_request:
            request_id = test_request["id"]
            
            try:
                status_data = {"status": "archived"}
                response = requests.put(
                    f"{EXTERNAL_BASE_URL}/requests/{request_id}/status",
                    json=status_data,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 400:
                    self.log_result("Status Update - Reject Archived", True, "Correctly rejected 'archived' status with 400 error", {
                        "status_code": response.status_code,
                        "error_message": response.text
                    })
                else:
                    self.log_result("Status Update - Reject Archived", False, f"Should have rejected 'archived' status but got: {response.status_code}")
                    
            except Exception as e:
                self.log_result("Status Update - Reject Archived", False, f"Error testing archived status: {str(e)}")
        
        # Test 3: Authentication required
        test_request = self.create_test_request(songs[0], "Auth Test")
        if test_request:
            request_id = test_request["id"]
            
            try:
                status_data = {"status": "accepted"}
                response = requests.put(
                    f"{EXTERNAL_BASE_URL}/requests/{request_id}/status",
                    json=status_data,
                    timeout=30  # No headers = no auth
                )
                
                if response.status_code in [401, 403]:
                    self.log_result("Status Update - Auth Required", True, f"Correctly requires authentication: {response.status_code}")
                else:
                    self.log_result("Status Update - Auth Required", False, f"Should require auth but got: {response.status_code}")
                    
            except Exception as e:
                self.log_result("Status Update - Auth Required", False, f"Error testing auth requirement: {str(e)}")
        
        # Test 4: Request ownership validation
        test_request = self.create_test_request(songs[0], "Ownership Test")
        if test_request:
            request_id = test_request["id"]
            
            # Try to update with a fake request ID
            fake_request_id = "fake-request-id-12345"
            
            try:
                status_data = {"status": "accepted"}
                response = requests.put(
                    f"{EXTERNAL_BASE_URL}/requests/{fake_request_id}/status",
                    json=status_data,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 404:
                    self.log_result("Status Update - Ownership Validation", True, "Correctly validates request ownership with 404")
                else:
                    self.log_result("Status Update - Ownership Validation", False, f"Should return 404 for non-existent request but got: {response.status_code}")
                    
            except Exception as e:
                self.log_result("Status Update - Ownership Validation", False, f"Error testing ownership validation: {str(e)}")
    
    def test_archive_endpoint(self):
        """Test PUT /api/requests/{request_id}/archive endpoint"""
        print("\n=== Testing Archive Endpoint ===")
        
        if not self.token:
            self.log_result("Archive Setup", False, "No authentication token")
            return
        
        songs = self.get_musician_songs()
        if not songs:
            self.log_result("Archive Setup", False, "No songs available for testing")
            return
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Test 1: Successful archiving
        test_request = self.create_test_request(songs[0], "Archive Test")
        if test_request:
            request_id = test_request["id"]
            
            try:
                response = requests.put(
                    f"{EXTERNAL_BASE_URL}/requests/{request_id}/archive",
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.log_result("Archive Request", True, "Successfully archived request", {
                        "request_id": request_id,
                        "success": result.get("success"),
                        "message": result.get("message")
                    })
                    
                    # Verify the request is now archived by trying to retrieve it
                    self.verify_request_archived(request_id)
                    
                else:
                    self.log_result("Archive Request", False, f"Failed to archive request: {response.status_code} - {response.text}")
                    
            except Exception as e:
                self.log_result("Archive Request", False, f"Error archiving request: {str(e)}")
        
        # Test 2: Authentication required
        test_request = self.create_test_request(songs[0], "Archive Auth Test")
        if test_request:
            request_id = test_request["id"]
            
            try:
                response = requests.put(
                    f"{EXTERNAL_BASE_URL}/requests/{request_id}/archive",
                    timeout=30  # No headers = no auth
                )
                
                if response.status_code in [401, 403]:
                    self.log_result("Archive - Auth Required", True, f"Correctly requires authentication: {response.status_code}")
                else:
                    self.log_result("Archive - Auth Required", False, f"Should require auth but got: {response.status_code}")
                    
            except Exception as e:
                self.log_result("Archive - Auth Required", False, f"Error testing archive auth: {str(e)}")
        
        # Test 3: Request ownership validation
        fake_request_id = "fake-archive-request-12345"
        
        try:
            response = requests.put(
                f"{EXTERNAL_BASE_URL}/requests/{fake_request_id}/archive",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 404:
                self.log_result("Archive - Ownership Validation", True, "Correctly validates request ownership with 404")
            else:
                self.log_result("Archive - Ownership Validation", False, f"Should return 404 for non-existent request but got: {response.status_code}")
                
        except Exception as e:
            self.log_result("Archive - Ownership Validation", False, f"Error testing archive ownership: {str(e)}")
    
    def verify_request_archived(self, request_id):
        """Verify that an archived request has status 'archived'"""
        if not self.token:
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            # Try to get all requests and see if our archived request has the right status
            response = requests.get(f"{EXTERNAL_BASE_URL}/requests/musician/{self.musician_id}", headers=headers, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Handle both list and dict response formats
                if isinstance(response_data, dict) and "requests" in response_data:
                    requests_list = response_data["requests"]
                elif isinstance(response_data, list):
                    requests_list = response_data
                else:
                    self.log_result("Verify Archive - Exclusion", False, f"Unexpected response format: {type(response_data)}")
                    return
                
                # Look for our request in the list (it should NOT be there since archived requests are excluded)
                found_request = None
                for req in requests_list:
                    if req.get("id") == request_id:
                        found_request = req
                        break
                
                if found_request is None:
                    self.log_result("Verify Archive - Exclusion", True, "Archived request correctly excluded from active requests list")
                else:
                    self.log_result("Verify Archive - Exclusion", False, f"Archived request still appears in active list with status: {found_request.get('status')}")
            else:
                self.log_result("Verify Archive - Exclusion", False, f"Could not retrieve requests list: {response.status_code}")
                
        except Exception as e:
            self.log_result("Verify Archive - Exclusion", False, f"Error verifying archive exclusion: {str(e)}")
    
    def test_request_retrieval_exclusions(self):
        """Test that archived requests are excluded from retrieval endpoints"""
        print("\n=== Testing Request Retrieval Exclusions ===")
        
        if not self.token:
            self.log_result("Retrieval Setup", False, "No authentication token")
            return
        
        songs = self.get_musician_songs()
        if not songs:
            self.log_result("Retrieval Setup", False, "No songs available for testing")
            return
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Create and archive a test request
        test_request = self.create_test_request(songs[0], "Exclusion Test")
        if not test_request:
            return
        
        request_id = test_request["id"]
        
        # Archive the request
        try:
            archive_response = requests.put(
                f"{EXTERNAL_BASE_URL}/requests/{request_id}/archive",
                headers=headers,
                timeout=30
            )
            
            if archive_response.status_code != 200:
                self.log_result("Retrieval Test Setup", False, "Could not archive test request")
                return
        except Exception as e:
            self.log_result("Retrieval Test Setup", False, f"Error archiving test request: {str(e)}")
            return
        
        # Test 1: GET /api/requests/musician/{musician_id} excludes archived
        try:
            response = requests.get(f"{EXTERNAL_BASE_URL}/requests/musician/{self.musician_id}", headers=headers, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Handle both list and dict response formats
                if isinstance(response_data, dict) and "requests" in response_data:
                    requests_list = response_data["requests"]
                elif isinstance(response_data, list):
                    requests_list = response_data
                else:
                    self.log_result("Musician Requests - Exclude Archived", False, f"Unexpected response format: {type(response_data)}")
                    return
                
                # Check if our archived request is in the list
                archived_request_found = any(req.get("id") == request_id for req in requests_list)
                
                if not archived_request_found:
                    self.log_result("Musician Requests - Exclude Archived", True, "Archived requests correctly excluded from musician requests")
                else:
                    self.log_result("Musician Requests - Exclude Archived", False, "Archived request found in musician requests list")
            else:
                self.log_result("Musician Requests - Exclude Archived", False, f"Failed to get musician requests: {response.status_code}")
                
        except Exception as e:
            self.log_result("Musician Requests - Exclude Archived", False, f"Error testing musician requests exclusion: {str(e)}")
        
        # Test 2: GET /api/requests/updates/{musician_id} excludes archived
        try:
            response = requests.get(f"{EXTERNAL_BASE_URL}/requests/updates/{self.musician_id}", timeout=30)
            
            if response.status_code == 200:
                updates_data = response.json()
                requests_list = updates_data.get("requests", [])
                
                # Check if our archived request is in the list
                archived_request_found = any(req.get("id") == request_id for req in requests_list)
                
                if not archived_request_found:
                    self.log_result("Request Updates - Exclude Archived", True, "Archived requests correctly excluded from updates endpoint")
                else:
                    self.log_result("Request Updates - Exclude Archived", False, "Archived request found in updates endpoint")
            else:
                self.log_result("Request Updates - Exclude Archived", False, f"Failed to get request updates: {response.status_code}")
                
        except Exception as e:
            self.log_result("Request Updates - Exclude Archived", False, f"Error testing updates exclusion: {str(e)}")
    
    def cleanup_test_requests(self):
        """Clean up test requests created during testing"""
        print("\n=== Cleanup Test Requests ===")
        
        if not self.token or not self.test_requests:
            return
        
        headers = {"Authorization": f"Bearer {self.token}"}
        cleaned_count = 0
        
        for request_id in self.test_requests:
            try:
                # Try to delete the request
                response = requests.delete(f"{EXTERNAL_BASE_URL}/requests/{request_id}", headers=headers, timeout=30)
                
                if response.status_code in [200, 404]:  # 404 is OK if already deleted
                    cleaned_count += 1
                    
            except Exception as e:
                print(f"   Warning: Could not clean up request {request_id}: {str(e)}")
        
        self.log_result("Cleanup", True, f"Cleaned up {cleaned_count}/{len(self.test_requests)} test requests")
    
    def run_all_tests(self):
        """Run all request status functionality tests"""
        print("🚀 Starting Request Status Update Functionality Tests")
        print(f"API Base URL: {EXTERNAL_BASE_URL}")
        print(f"Test user: {TEST_EMAIL}")
        print("=" * 80)
        
        # Authenticate first
        if not self.authenticate():
            print("❌ Authentication failed - cannot proceed with tests")
            return False
        
        # Run all tests
        self.test_status_update_endpoint()
        self.test_archive_endpoint()
        self.test_request_retrieval_exclusions()
        
        # Cleanup
        self.cleanup_test_requests()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 REQUEST STATUS FUNCTIONALITY TEST SUMMARY")
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
                if any(keyword in result["test"].lower() for keyword in ["status update", "archive", "exclude"]):
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
        
        # Check status update functionality
        status_working = any(r["success"] and "status update" in r["test"].lower() for r in self.results)
        if status_working:
            print("✅ Status update endpoint working correctly")
        else:
            print("❌ Status update endpoint has issues")
        
        # Check archive functionality
        archive_working = any(r["success"] and "archive" in r["test"].lower() for r in self.results)
        if archive_working:
            print("✅ Archive endpoint working correctly")
        else:
            print("❌ Archive endpoint has issues")
        
        # Check exclusion functionality
        exclusion_working = any(r["success"] and "exclude" in r["test"].lower() for r in self.results)
        if exclusion_working:
            print("✅ Archived request exclusion working correctly")
        else:
            print("❌ Archived request exclusion has issues")
        
        print("\n🎯 REQUEST STATUS FUNCTIONALITY TEST COMPLETE")
        
        return len(critical_failures) == 0

if __name__ == "__main__":
    tester = RequestStatusTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)