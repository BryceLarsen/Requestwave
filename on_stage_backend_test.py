#!/usr/bin/env python3
"""
ON STAGE MODE BACKEND TESTING - UP_NEXT STATUS VALIDATION

Testing the updated On Stage mode backend with the new "up_next" status as requested:

CRITICAL TEST AREAS:
1. Status Validation Fixed - PUT /api/requests/{id}/status accepts "up_next" status
2. Request Status Update - Create test request and update to "up_next" status  
3. Request Filtering - GET /api/requests/updates/{musician_id} returns "up_next" requests
4. Status Persistence - "up_next" status stored and retrieved properly from database
5. Integration Test - Multiple requests with different statuses including "up_next"

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!

Expected: All "up_next" status functionality working correctly for three-section On Stage interface.
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://stagepro-app.preview.emergentagent.com/api"

# Pro account for testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com", 
    "password": "RequestWave2024!"
}

class OnStageBackendTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
        self.test_song_ids = []
        self.test_request_ids = []
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
        if self.auth_token:
            request_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        # Override with custom headers
        if headers:
            request_headers.update(headers)
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=request_headers, params=params)
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

    def setup_test_environment(self):
        """Setup test environment with authentication and test data"""
        try:
            print("🎵 SETUP: Authenticating and preparing test environment")
            print("=" * 80)
            
            # Step 1: Login with Pro account
            print("📊 Step 1: Login with brycelarsenmusic@gmail.com")
            login_data = {
                "email": PRO_MUSICIAN["email"],
                "password": PRO_MUSICIAN["password"]
            }
            
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code != 200:
                self.log_result("Setup - Pro Login", False, f"Failed to login: {login_response.status_code}")
                return False
            
            login_data_response = login_response.json()
            self.auth_token = login_data_response["token"]
            self.musician_id = login_data_response["musician"]["id"]
            self.musician_slug = login_data_response["musician"]["slug"]
            
            print(f"   ✅ Successfully logged in as: {login_data_response['musician']['name']}")
            print(f"   📊 Musician ID: {self.musician_id}")
            print(f"   📊 Musician Slug: {self.musician_slug}")
            
            # Step 2: Get available songs for request testing
            print("📊 Step 2: Get available songs for request testing")
            
            songs_response = self.make_request("GET", "/songs")
            
            if songs_response.status_code != 200:
                self.log_result("Setup - Get Songs", False, f"Failed to get songs: {songs_response.status_code}")
                return False
            
            songs = songs_response.json()
            if len(songs) < 4:
                self.log_result("Setup - Insufficient Songs", False, f"Need at least 4 songs, found {len(songs)}")
                return False
            
            # Store first 4 song IDs for testing
            self.test_song_ids = [songs[i]["id"] for i in range(4)]
            print(f"   ✅ Using {len(self.test_song_ids)} songs for request testing")
            
            print("=" * 80)
            return True
            
        except Exception as e:
            self.log_result("Setup Test Environment", False, f"Exception: {str(e)}")
            return False

    def test_status_validation_fixed(self):
        """Test 1: Status Validation Fixed - PUT /api/requests/{id}/status accepts 'up_next'"""
        try:
            print("🎵 TEST 1: Status Validation Fixed - 'up_next' Status Acceptance")
            print("=" * 80)
            
            # Step 1: Create a test request first
            print("📊 Step 1: Create test request for status validation")
            
            request_data = {
                "song_id": self.test_song_ids[0],
                "requester_name": "Test Requester",
                "requester_email": "test@example.com",
                "dedication": "Testing up_next status validation"
            }
            
            # Create request via public endpoint (no auth needed)
            original_token = self.auth_token
            self.auth_token = None
            
            create_response = self.make_request("POST", f"/musicians/{self.musician_slug}/requests", request_data)
            
            # Restore auth token
            self.auth_token = original_token
            
            if create_response.status_code != 200:
                self.log_result("Status Validation - Create Request", False, f"Failed to create request: {create_response.status_code}")
                return
            
            created_request = create_response.json()
            request_id = created_request["id"]
            self.test_request_ids.append(request_id)
            
            print(f"   ✅ Created test request: {request_id}")
            print(f"   📊 Initial status: {created_request.get('status', 'unknown')}")
            
            # Step 2: Test updating status to 'up_next'
            print("📊 Step 2: Test updating status to 'up_next'")
            
            status_update_data = {
                "status": "up_next"
            }
            
            update_response = self.make_request("PUT", f"/requests/{request_id}/status", status_update_data)
            
            print(f"   📊 Status update response: {update_response.status_code}")
            print(f"   📊 Response body: {update_response.text}")
            
            if update_response.status_code == 200:
                update_result = update_response.json()
                new_status = update_result.get("new_status")
                
                if new_status == "up_next":
                    print(f"   ✅ Status successfully updated to 'up_next'")
                    self.log_result("Status Validation - up_next Acceptance", True, "Backend now accepts 'up_next' status")
                else:
                    print(f"   ❌ Status not updated correctly. Expected: 'up_next', Got: '{new_status}'")
                    self.log_result("Status Validation - up_next Acceptance", False, f"Status update failed - got '{new_status}' instead of 'up_next'")
            else:
                print(f"   ❌ Status update failed with status code: {update_response.status_code}")
                if update_response.status_code == 400:
                    error_detail = update_response.json().get("detail", "Unknown error")
                    print(f"   📊 Error detail: {error_detail}")
                    if "Invalid status" in error_detail:
                        self.log_result("Status Validation - up_next Acceptance", False, "CRITICAL: Backend still does not accept 'up_next' status - validation not fixed")
                    else:
                        self.log_result("Status Validation - up_next Acceptance", False, f"Status update failed: {error_detail}")
                else:
                    self.log_result("Status Validation - up_next Acceptance", False, f"Unexpected error: {update_response.status_code}")
            
            # Step 3: Test other valid statuses still work
            print("📊 Step 3: Verify other valid statuses still work")
            
            other_statuses = ["pending", "accepted", "played", "rejected"]
            other_statuses_working = True
            
            for status in other_statuses:
                status_data = {"status": status}
                test_response = self.make_request("PUT", f"/requests/{request_id}/status", status_data)
                
                if test_response.status_code == 200:
                    print(f"   ✅ Status '{status}' accepted")
                else:
                    print(f"   ❌ Status '{status}' rejected: {test_response.status_code}")
                    other_statuses_working = False
            
            if other_statuses_working:
                print(f"   ✅ All existing statuses still work correctly")
            else:
                print(f"   ❌ Some existing statuses broken")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Status Validation Fixed", False, f"Exception: {str(e)}")

    def test_request_status_update(self):
        """Test 2: Request Status Update - Create request and update to 'up_next'"""
        try:
            print("🎵 TEST 2: Request Status Update - Create and Update to 'up_next'")
            print("=" * 80)
            
            # Step 1: Create a fresh test request
            print("📊 Step 1: Create fresh test request")
            
            request_data = {
                "song_id": self.test_song_ids[1],
                "requester_name": "Up Next Tester",
                "requester_email": "upnext@example.com",
                "dedication": "Testing up_next status update workflow"
            }
            
            # Create request via public endpoint
            original_token = self.auth_token
            self.auth_token = None
            
            create_response = self.make_request("POST", f"/musicians/{self.musician_slug}/requests", request_data)
            
            # Restore auth token
            self.auth_token = original_token
            
            if create_response.status_code != 200:
                self.log_result("Status Update - Create Request", False, f"Failed to create request: {create_response.status_code}")
                return
            
            created_request = create_response.json()
            request_id = created_request["id"]
            self.test_request_ids.append(request_id)
            
            print(f"   ✅ Created test request: {request_id}")
            print(f"   📊 Song: {created_request.get('song_title')} by {created_request.get('song_artist')}")
            print(f"   📊 Initial status: {created_request.get('status')}")
            
            # Step 2: Update status to 'up_next'
            print("📊 Step 2: Update status to 'up_next'")
            
            status_update_data = {
                "status": "up_next"
            }
            
            update_response = self.make_request("PUT", f"/requests/{request_id}/status", status_update_data)
            
            if update_response.status_code == 200:
                update_result = update_response.json()
                
                # The status update endpoint returns a success message, not the full request
                # We need to fetch the request to verify the update
                verify_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
                
                if verify_response.status_code == 200:
                    all_requests = verify_response.json()
                    updated_request = next((r for r in all_requests if r["id"] == request_id), None)
                    
                    if updated_request:
                        # Verify all required fields are present
                        required_fields = ["id", "status", "song_title", "song_artist", "requester_name", "created_at"]
                        missing_fields = [field for field in required_fields if field not in updated_request]
                        
                        if len(missing_fields) == 0:
                            print(f"   ✅ All required fields present in response")
                            
                            if updated_request["status"] == "up_next":
                                print(f"   ✅ Status successfully updated to 'up_next'")
                                print(f"   📊 Request details: {updated_request['song_title']} by {updated_request['song_artist']}")
                                self.log_result("Request Status Update", True, "Successfully created request and updated to 'up_next' status")
                            else:
                                print(f"   ❌ Status not 'up_next': {updated_request['status']}")
                                self.log_result("Request Status Update", False, f"Status update failed - got '{updated_request['status']}'")
                        else:
                            print(f"   ❌ Missing required fields: {missing_fields}")
                            self.log_result("Request Status Update", False, f"Response missing fields: {missing_fields}")
                    else:
                        print(f"   ❌ Updated request not found")
                        self.log_result("Request Status Update", False, "Updated request not found")
                else:
                    print(f"   ❌ Failed to verify update: {verify_response.status_code}")
                    self.log_result("Request Status Update", False, f"Failed to verify update: {verify_response.status_code}")
            else:
                print(f"   ❌ Status update failed: {update_response.status_code}")
                print(f"   📊 Error response: {update_response.text}")
                self.log_result("Request Status Update", False, f"Status update failed: {update_response.status_code}")
            
            # Step 3: Verify status persists by fetching request again
            print("📊 Step 3: Verify status persists by fetching request")
            
            # Get all requests and find our test request
            requests_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
            
            if requests_response.status_code == 200:
                all_requests = requests_response.json()
                test_request = next((r for r in all_requests if r["id"] == request_id), None)
                
                if test_request:
                    if test_request["status"] == "up_next":
                        print(f"   ✅ Status 'up_next' persisted correctly")
                    else:
                        print(f"   ❌ Status not persisted. Expected: 'up_next', Got: '{test_request['status']}'")
                        self.log_result("Request Status Update - Persistence", False, "Status not persisted correctly")
                else:
                    print(f"   ❌ Test request not found in requests list")
                    self.log_result("Request Status Update - Persistence", False, "Request not found after update")
            else:
                print(f"   ❌ Failed to fetch requests: {requests_response.status_code}")
                self.log_result("Request Status Update - Persistence", False, "Could not verify persistence")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Request Status Update", False, f"Exception: {str(e)}")

    def test_request_filtering(self):
        """Test 3: Request Filtering - GET /api/requests/updates/{musician_id} returns 'up_next' requests"""
        try:
            print("🎵 TEST 3: Request Filtering - 'up_next' Requests in Updates Endpoint")
            print("=" * 80)
            
            # Step 1: Create multiple requests with different statuses
            print("📊 Step 1: Create multiple requests with different statuses")
            
            test_requests = [
                {
                    "song_id": self.test_song_ids[0],
                    "requester_name": "Pending User",
                    "requester_email": "pending@example.com",
                    "dedication": "Pending request",
                    "target_status": "pending"
                },
                {
                    "song_id": self.test_song_ids[1], 
                    "requester_name": "Up Next User",
                    "requester_email": "upnext@example.com",
                    "dedication": "Up next request",
                    "target_status": "up_next"
                },
                {
                    "song_id": self.test_song_ids[2],
                    "requester_name": "Played User", 
                    "requester_email": "played@example.com",
                    "dedication": "Played request",
                    "target_status": "played"
                }
            ]
            
            created_request_ids = []
            
            # Create requests via public endpoint
            original_token = self.auth_token
            self.auth_token = None
            
            for req_data in test_requests:
                create_data = {
                    "song_id": req_data["song_id"],
                    "requester_name": req_data["requester_name"],
                    "requester_email": req_data["requester_email"],
                    "dedication": req_data["dedication"]
                }
                
                create_response = self.make_request("POST", f"/musicians/{self.musician_slug}/requests", create_data)
                
                if create_response.status_code == 200:
                    created_request = create_response.json()
                    created_request_ids.append({
                        "id": created_request["id"],
                        "target_status": req_data["target_status"],
                        "requester_name": req_data["requester_name"]
                    })
                    print(f"   ✅ Created request: {req_data['requester_name']} -> {req_data['target_status']}")
                else:
                    print(f"   ❌ Failed to create request for {req_data['requester_name']}: {create_response.status_code}")
            
            # Restore auth token
            self.auth_token = original_token
            
            # Step 2: Update requests to target statuses
            print("📊 Step 2: Update requests to target statuses")
            
            for req_info in created_request_ids:
                if req_info["target_status"] != "pending":  # pending is default
                    status_data = {"status": req_info["target_status"]}
                    update_response = self.make_request("PUT", f"/requests/{req_info['id']}/status", status_data)
                    
                    if update_response.status_code == 200:
                        print(f"   ✅ Updated {req_info['requester_name']} to '{req_info['target_status']}'")
                        self.test_request_ids.append(req_info["id"])
                    else:
                        print(f"   ❌ Failed to update {req_info['requester_name']}: {update_response.status_code}")
            
            # Step 3: Test GET /api/requests/updates/{musician_id} endpoint
            print("📊 Step 3: Test requests updates endpoint")
            
            updates_response = self.make_request("GET", f"/requests/updates/{self.musician_id}")
            
            print(f"   📊 Updates endpoint status: {updates_response.status_code}")
            print(f"   📊 Response preview: {updates_response.text[:200]}...")
            
            if updates_response.status_code == 200:
                try:
                    updates_data = updates_response.json()
                    
                    # Check if response is a dict with 'requests' key or direct list
                    if isinstance(updates_data, dict) and 'requests' in updates_data:
                        requests_list = updates_data['requests']
                        print(f"   📊 Response format: dict with 'requests' key")
                        print(f"   📊 Additional fields: {list(updates_data.keys())}")
                    elif isinstance(updates_data, list):
                        requests_list = updates_data
                        print(f"   📊 Response format: direct list")
                    else:
                        print(f"   ❌ Unexpected response format: {type(updates_data)}")
                        self.log_result("Request Filtering - Response Format", False, "Unexpected response format")
                        return
                    
                    print(f"   ✅ Found {len(requests_list)} requests in updates")
                    
                    # Step 4: Verify 'up_next' requests are included
                    print("📊 Step 4: Verify 'up_next' requests are included")
                    
                    status_counts = {}
                    up_next_requests = []
                    
                    for request in requests_list:
                        status = request.get("status", "unknown")
                        status_counts[status] = status_counts.get(status, 0) + 1
                        
                        if status == "up_next":
                            up_next_requests.append(request)
                    
                    print(f"   📊 Status distribution: {status_counts}")
                    
                    if len(up_next_requests) > 0:
                        print(f"   ✅ Found {len(up_next_requests)} 'up_next' requests")
                        
                        # Verify structure of up_next requests
                        sample_up_next = up_next_requests[0]
                        required_fields = ["id", "status", "song_title", "song_artist", "requester_name"]
                        missing_fields = [field for field in required_fields if field not in sample_up_next]
                        
                        if len(missing_fields) == 0:
                            print(f"   ✅ 'up_next' request structure correct")
                            print(f"   📊 Sample: {sample_up_next['song_title']} by {sample_up_next['song_artist']} (requested by {sample_up_next['requester_name']})")
                            self.log_result("Request Filtering", True, "'up_next' requests properly included in updates endpoint")
                        else:
                            print(f"   ❌ 'up_next' request missing fields: {missing_fields}")
                            self.log_result("Request Filtering", False, f"'up_next' request structure incomplete: {missing_fields}")
                    else:
                        print(f"   ❌ No 'up_next' requests found in updates")
                        self.log_result("Request Filtering", False, "'up_next' requests not included in updates endpoint")
                    
                except json.JSONDecodeError:
                    print(f"   ❌ Updates response is not valid JSON")
                    self.log_result("Request Filtering", False, "Updates endpoint returned invalid JSON")
            else:
                print(f"   ❌ Updates endpoint failed: {updates_response.status_code}")
                self.log_result("Request Filtering", False, f"Updates endpoint failed: {updates_response.status_code}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Request Filtering", False, f"Exception: {str(e)}")

    def test_status_persistence(self):
        """Test 4: Status Persistence - 'up_next' status stored and retrieved properly"""
        try:
            print("🎵 TEST 4: Status Persistence - Database Storage and Retrieval")
            print("=" * 80)
            
            # Step 1: Create request and update to 'up_next'
            print("📊 Step 1: Create request and update to 'up_next'")
            
            request_data = {
                "song_id": self.test_song_ids[3],
                "requester_name": "Persistence Tester",
                "requester_email": "persistence@example.com",
                "dedication": "Testing up_next persistence"
            }
            
            # Create request via public endpoint
            original_token = self.auth_token
            self.auth_token = None
            
            create_response = self.make_request("POST", f"/musicians/{self.musician_slug}/requests", request_data)
            
            # Restore auth token
            self.auth_token = original_token
            
            if create_response.status_code != 200:
                self.log_result("Status Persistence - Create Request", False, f"Failed to create request: {create_response.status_code}")
                return
            
            created_request = create_response.json()
            request_id = created_request["id"]
            self.test_request_ids.append(request_id)
            
            print(f"   ✅ Created test request: {request_id}")
            
            # Update to 'up_next'
            status_update_data = {"status": "up_next"}
            update_response = self.make_request("PUT", f"/requests/{request_id}/status", status_update_data)
            
            if update_response.status_code != 200:
                self.log_result("Status Persistence - Update Status", False, f"Failed to update status: {update_response.status_code}")
                return
            
            print(f"   ✅ Updated status to 'up_next'")
            
            # Step 2: Verify persistence through multiple retrieval methods
            print("📊 Step 2: Verify persistence through multiple retrieval methods")
            
            persistence_tests = []
            
            # Test 1: GET /requests/musician/{musician_id} (all requests)
            all_requests_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
            if all_requests_response.status_code == 200:
                all_requests = all_requests_response.json()
                test_request = next((r for r in all_requests if r["id"] == request_id), None)
                
                if test_request and test_request["status"] == "up_next":
                    persistence_tests.append(("GET /requests/musician", True))
                    print(f"   ✅ Persistence verified via GET /requests/musician")
                else:
                    persistence_tests.append(("GET /requests/musician", False))
                    print(f"   ❌ Persistence failed via GET /requests/musician")
            else:
                persistence_tests.append(("GET /requests/musician", False))
                print(f"   ❌ GET /requests/musician failed: {all_requests_response.status_code}")
            
            # Test 2: GET /requests/updates/{musician_id}
            updates_response = self.make_request("GET", f"/requests/updates/{self.musician_id}")
            if updates_response.status_code == 200:
                updates_data = updates_response.json()
                
                # Handle both response formats
                if isinstance(updates_data, dict) and 'requests' in updates_data:
                    requests_list = updates_data['requests']
                elif isinstance(updates_data, list):
                    requests_list = updates_data
                else:
                    requests_list = []
                
                test_request = next((r for r in requests_list if r["id"] == request_id), None)
                
                if test_request and test_request["status"] == "up_next":
                    persistence_tests.append(("GET /requests/updates", True))
                    print(f"   ✅ Persistence verified via GET /requests/updates")
                else:
                    persistence_tests.append(("GET /requests/updates", False))
                    print(f"   ❌ Persistence failed via GET /requests/updates")
            else:
                persistence_tests.append(("GET /requests/updates", False))
                print(f"   ❌ GET /requests/updates failed: {updates_response.status_code}")
            
            # Step 3: Test status changes and persistence
            print("📊 Step 3: Test status changes and persistence")
            
            # Change to different status and back
            status_changes = ["accepted", "up_next", "played", "up_next"]
            
            for new_status in status_changes:
                change_data = {"status": new_status}
                change_response = self.make_request("PUT", f"/requests/{request_id}/status", change_data)
                
                if change_response.status_code == 200:
                    # Verify the change persisted
                    verify_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
                    if verify_response.status_code == 200:
                        verify_requests = verify_response.json()
                        verify_request = next((r for r in verify_requests if r["id"] == request_id), None)
                        
                        if verify_request and verify_request["status"] == new_status:
                            print(f"   ✅ Status change to '{new_status}' persisted")
                        else:
                            print(f"   ❌ Status change to '{new_status}' not persisted")
                            persistence_tests.append((f"Status change to {new_status}", False))
                    else:
                        print(f"   ❌ Could not verify status change to '{new_status}'")
                        persistence_tests.append((f"Status change to {new_status}", False))
                else:
                    print(f"   ❌ Failed to change status to '{new_status}': {change_response.status_code}")
                    persistence_tests.append((f"Status change to {new_status}", False))
            
            # Final assessment
            successful_tests = [test for test in persistence_tests if test[1]]
            failed_tests = [test for test in persistence_tests if not test[1]]
            
            if len(failed_tests) == 0:
                self.log_result("Status Persistence", True, f"All {len(successful_tests)} persistence tests passed")
            else:
                self.log_result("Status Persistence", False, f"{len(failed_tests)} persistence tests failed: {[test[0] for test in failed_tests]}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Status Persistence", False, f"Exception: {str(e)}")

    def test_integration_three_section_organization(self):
        """Test 5: Integration Test - Multiple requests for three-section On Stage interface"""
        try:
            print("🎵 TEST 5: Integration Test - Three-Section On Stage Organization")
            print("=" * 80)
            
            # Step 1: Create requests for all three sections
            print("📊 Step 1: Create requests for three-section organization")
            
            section_requests = [
                # Up Next section
                {
                    "requester_name": "Up Next User 1",
                    "requester_email": "upnext1@example.com",
                    "dedication": "Ready to play next",
                    "target_status": "up_next",
                    "section": "Up Next"
                },
                {
                    "requester_name": "Up Next User 2", 
                    "requester_email": "upnext2@example.com",
                    "dedication": "Also ready for next",
                    "target_status": "up_next",
                    "section": "Up Next"
                },
                # Active Requests section
                {
                    "requester_name": "Pending User 1",
                    "requester_email": "pending1@example.com", 
                    "dedication": "Waiting for approval",
                    "target_status": "pending",
                    "section": "Active Requests"
                },
                {
                    "requester_name": "Accepted User 1",
                    "requester_email": "accepted1@example.com",
                    "dedication": "Approved and waiting",
                    "target_status": "accepted", 
                    "section": "Active Requests"
                },
                # Completed Requests section
                {
                    "requester_name": "Played User 1",
                    "requester_email": "played1@example.com",
                    "dedication": "Already performed",
                    "target_status": "played",
                    "section": "Completed Requests"
                },
                {
                    "requester_name": "Rejected User 1",
                    "requester_email": "rejected1@example.com",
                    "dedication": "Not available to play",
                    "target_status": "rejected",
                    "section": "Completed Requests"
                }
            ]
            
            created_requests = []
            
            # Create all requests
            original_token = self.auth_token
            self.auth_token = None
            
            for i, req_data in enumerate(section_requests):
                create_data = {
                    "song_id": self.test_song_ids[i % len(self.test_song_ids)],
                    "requester_name": req_data["requester_name"],
                    "requester_email": req_data["requester_email"],
                    "dedication": req_data["dedication"]
                }
                
                create_response = self.make_request("POST", f"/musicians/{self.musician_slug}/requests", create_data)
                
                if create_response.status_code == 200:
                    created_request = create_response.json()
                    created_requests.append({
                        "id": created_request["id"],
                        "target_status": req_data["target_status"],
                        "section": req_data["section"],
                        "requester_name": req_data["requester_name"]
                    })
                    print(f"   ✅ Created request: {req_data['requester_name']} -> {req_data['section']}")
                else:
                    print(f"   ❌ Failed to create request for {req_data['requester_name']}: {create_response.status_code}")
            
            # Restore auth token
            self.auth_token = original_token
            
            # Step 2: Update requests to target statuses
            print("📊 Step 2: Update requests to target statuses")
            
            for req_info in created_requests:
                if req_info["target_status"] != "pending":  # pending is default
                    status_data = {"status": req_info["target_status"]}
                    update_response = self.make_request("PUT", f"/requests/{req_info['id']}/status", status_data)
                    
                    if update_response.status_code == 200:
                        print(f"   ✅ Updated {req_info['requester_name']} to '{req_info['target_status']}'")
                        self.test_request_ids.append(req_info["id"])
                    else:
                        print(f"   ❌ Failed to update {req_info['requester_name']}: {update_response.status_code}")
            
            # Step 3: Retrieve all requests and organize by section
            print("📊 Step 3: Retrieve and organize requests by three sections")
            
            all_requests_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
            
            if all_requests_response.status_code != 200:
                self.log_result("Integration Test - Get Requests", False, f"Failed to get requests: {all_requests_response.status_code}")
                return
            
            all_requests = all_requests_response.json()
            
            # Organize requests by section based on status
            sections = {
                "Up Next": [],
                "Active Requests": [],
                "Completed Requests": []
            }
            
            for request in all_requests:
                status = request.get("status", "unknown")
                
                if status == "up_next":
                    sections["Up Next"].append(request)
                elif status in ["pending", "accepted"]:
                    sections["Active Requests"].append(request)
                elif status in ["played", "rejected"]:
                    sections["Completed Requests"].append(request)
            
            # Step 4: Verify three-section organization
            print("📊 Step 4: Verify three-section organization")
            
            organization_correct = True
            
            for section_name, requests in sections.items():
                print(f"   📊 {section_name}: {len(requests)} requests")
                
                if len(requests) > 0:
                    for request in requests:
                        print(f"      - {request['requester_name']}: {request['song_title']} ({request['status']})")
                
                # Verify we have requests in each section (from our test data)
                expected_counts = {
                    "Up Next": 2,
                    "Active Requests": 2, 
                    "Completed Requests": 2
                }
                
                if len(requests) >= expected_counts.get(section_name, 0):
                    print(f"   ✅ {section_name} section populated correctly")
                else:
                    print(f"   ❌ {section_name} section missing requests")
                    organization_correct = False
            
            # Step 5: Verify 'up_next' status enables three-section workflow
            print("📊 Step 5: Verify 'up_next' status enables three-section workflow")
            
            up_next_requests = sections["Up Next"]
            
            if len(up_next_requests) >= 2:
                print(f"   ✅ 'up_next' section has {len(up_next_requests)} requests")
                
                # Verify all up_next requests have correct status
                all_up_next_correct = all(req["status"] == "up_next" for req in up_next_requests)
                
                if all_up_next_correct:
                    print(f"   ✅ All 'Up Next' requests have correct 'up_next' status")
                    self.log_result("Integration Test - Three-Section Organization", True, "Three-section On Stage organization working correctly with 'up_next' status")
                else:
                    print(f"   ❌ Some 'Up Next' requests have incorrect status")
                    self.log_result("Integration Test - Three-Section Organization", False, "Some 'Up Next' requests have incorrect status")
            else:
                print(f"   ❌ 'Up Next' section has insufficient requests: {len(up_next_requests)}")
                self.log_result("Integration Test - Three-Section Organization", False, "'up_next' status not working for three-section organization")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Integration Test - Three-Section Organization", False, f"Exception: {str(e)}")

    def cleanup_test_data(self):
        """Clean up test requests created during testing"""
        try:
            print("🧹 CLEANUP: Removing test requests")
            print("=" * 80)
            
            cleanup_count = 0
            
            for request_id in self.test_request_ids:
                try:
                    delete_response = self.make_request("DELETE", f"/requests/{request_id}")
                    if delete_response.status_code == 200:
                        cleanup_count += 1
                        print(f"   ✅ Deleted request: {request_id}")
                    else:
                        print(f"   ⚠️  Failed to delete request {request_id}: {delete_response.status_code}")
                except Exception as e:
                    print(f"   ⚠️  Error deleting request {request_id}: {str(e)}")
            
            print(f"   📊 Cleaned up {cleanup_count}/{len(self.test_request_ids)} test requests")
            print("=" * 80)
            
        except Exception as e:
            print(f"   ⚠️  Cleanup error: {str(e)}")

    def run_all_tests(self):
        """Run all On Stage mode backend tests"""
        print("🎵 ON STAGE MODE BACKEND TESTING - UP_NEXT STATUS VALIDATION")
        print("=" * 100)
        print("Testing the updated On Stage mode backend with new 'up_next' status")
        print("=" * 100)
        
        # Setup test environment
        if not self.setup_test_environment():
            print("❌ CRITICAL: Test environment setup failed - cannot proceed")
            return
        
        # Run all tests
        self.test_status_validation_fixed()
        self.test_request_status_update()
        self.test_request_filtering()
        self.test_status_persistence()
        self.test_integration_three_section_organization()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Final results
        print("🎵 ON STAGE MODE TESTING COMPLETE")
        print("=" * 100)
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        print(f"📊 SUCCESS RATE: {(self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100):.1f}%")
        
        if self.results['failed'] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   - {error}")
        
        print("=" * 100)

if __name__ == "__main__":
    tester = OnStageBackendTester()
    tester.run_all_tests()