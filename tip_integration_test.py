#!/usr/bin/env python3
"""
COMPREHENSIVE TESTING FOR TIP INTEGRATION FIX - ON STAGE REQUEST CARDS

Testing the complete tip integration fix for On Stage request cards as requested:

CRITICAL TEST AREAS:
1. Request Creation with Tips - Test that POST /api/requests now accepts and stores tip_amount field correctly
2. Tip Amount Storage - Create test requests with different tip amounts ($5, $10, $20) and verify they're stored in the request records
3. Request Retrieval - Test GET /api/requests/updates/{musician_id} and verify that returned requests include tip_amount field
4. Zero Tip Handling - Test requests with tip_amount=0 and verify they're handled correctly (no tip display)
5. On Stage Data Flow - Verify that the request data structure now includes tip information that the On Stage interface can display
6. Backward Compatibility - Ensure existing requests without tip_amount still work (default to 0.0)
7. Complete Request Flow Test - Create a test musician, submit requests with various tip amounts, and verify the data flows correctly through the system

Expected: Complete tip integration working for On Stage request cards display.
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://requestwave-2.preview.emergentagent.com/api"
TEST_MUSICIAN = {
    "name": "Tip Integration Test Musician",
    "email": "tip.test@requestwave.com", 
    "password": "SecurePassword123!"
}

class TipIntegrationTester:
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

    def setup_test_musician(self):
        """Set up test musician and songs for testing"""
        try:
            print("🎵 SETUP: Creating Test Musician and Songs")
            print("=" * 80)
            
            # Step 1: Register or login test musician
            print("📊 Step 1: Register/Login test musician")
            response = self.make_request("POST", "/auth/register", TEST_MUSICIAN)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data["token"]
                self.musician_id = data["musician"]["id"]
                self.musician_slug = data["musician"]["slug"]
                print(f"   ✅ Registered musician: {data['musician']['name']}")
            elif response.status_code == 400:
                # Musician might already exist, try login
                login_data = {
                    "email": TEST_MUSICIAN["email"],
                    "password": TEST_MUSICIAN["password"]
                }
                login_response = self.make_request("POST", "/auth/login", login_data)
                if login_response.status_code == 200:
                    data = login_response.json()
                    self.auth_token = data["token"]
                    self.musician_id = data["musician"]["id"]
                    self.musician_slug = data["musician"]["slug"]
                    print(f"   ✅ Logged in existing musician: {data['musician']['name']}")
                else:
                    raise Exception(f"Failed to login: {login_response.status_code}")
            else:
                raise Exception(f"Failed to register: {response.status_code}")
            
            # Step 2: Create test songs
            print("📊 Step 2: Create test songs for requests")
            test_songs = [
                {"title": "Tip Test Song 1", "artist": "Test Artist 1"},
                {"title": "Tip Test Song 2", "artist": "Test Artist 2"},
                {"title": "Tip Test Song 3", "artist": "Test Artist 3"}
            ]
            
            for song_data in test_songs:
                song_response = self.make_request("POST", "/songs", song_data)
                if song_response.status_code == 200:
                    song_result = song_response.json()
                    self.test_song_ids.append(song_result["id"])
                    print(f"   ✅ Created song: {song_data['title']}")
                else:
                    print(f"   ❌ Failed to create song: {song_data['title']}")
            
            if len(self.test_song_ids) >= 3:
                print(f"   ✅ Setup complete: {len(self.test_song_ids)} test songs created")
                return True
            else:
                print(f"   ❌ Setup failed: Only {len(self.test_song_ids)} songs created")
                return False
            
        except Exception as e:
            print(f"   ❌ Setup failed: {str(e)}")
            return False

    def test_request_creation_with_tips(self):
        """Test that POST /api/requests now accepts and stores tip_amount field correctly"""
        try:
            print("🎵 PRIORITY 1: Testing Request Creation with Tips")
            print("=" * 80)
            
            # Test different tip amounts
            tip_amounts = [5.0, 10.0, 20.0, 0.0]
            successful_requests = []
            
            for i, tip_amount in enumerate(tip_amounts):
                print(f"📊 Testing request creation with tip amount: ${tip_amount}")
                
                request_data = {
                    "song_id": self.test_song_ids[0] if self.test_song_ids else "test-song-id",
                    "requester_name": f"Tip Tester {i+1}",
                    "requester_email": f"tipper{i+1}@example.com",
                    "dedication": f"Test request with ${tip_amount} tip",
                    "tip_amount": tip_amount
                }
                
                # Clear auth token for public request creation
                temp_token = self.auth_token
                self.auth_token = None
                
                response = self.make_request("POST", "/requests", request_data)
                
                # Restore auth token
                self.auth_token = temp_token
                
                print(f"   📊 Response status: {response.status_code}")
                print(f"   📊 Response: {response.text[:200]}...")
                
                if response.status_code == 200:
                    request_result = response.json()
                    
                    # Verify tip_amount is in response
                    if "tip_amount" in request_result:
                        stored_tip = request_result["tip_amount"]
                        if stored_tip == tip_amount:
                            print(f"   ✅ Request created with correct tip amount: ${stored_tip}")
                            successful_requests.append(request_result)
                            self.test_request_ids.append(request_result["id"])
                        else:
                            print(f"   ❌ Tip amount mismatch: expected ${tip_amount}, got ${stored_tip}")
                    else:
                        print(f"   ❌ tip_amount field missing from response")
                else:
                    print(f"   ❌ Request creation failed: {response.status_code}")
            
            # Assessment
            if len(successful_requests) == len(tip_amounts):
                self.log_result("Request Creation with Tips", True, f"✅ All {len(tip_amounts)} requests created successfully with correct tip amounts")
            else:
                self.log_result("Request Creation with Tips", False, f"❌ Only {len(successful_requests)}/{len(tip_amounts)} requests created successfully")
            
            print("=" * 80)
            return len(successful_requests) == len(tip_amounts)
            
        except Exception as e:
            self.log_result("Request Creation with Tips", False, f"❌ Exception: {str(e)}")
            return False

    def test_tip_amount_storage(self):
        """Create test requests with different tip amounts and verify they're stored in the request records"""
        try:
            print("🎵 PRIORITY 2: Testing Tip Amount Storage")
            print("=" * 80)
            
            # Create additional requests with specific tip amounts for storage verification
            storage_test_amounts = [15.50, 25.75, 100.00]
            storage_request_ids = []
            
            for i, tip_amount in enumerate(storage_test_amounts):
                print(f"📊 Creating storage test request with tip: ${tip_amount}")
                
                request_data = {
                    "song_id": self.test_song_ids[1] if len(self.test_song_ids) > 1 else self.test_song_ids[0],
                    "requester_name": f"Storage Tester {i+1}",
                    "requester_email": f"storage{i+1}@example.com",
                    "dedication": f"Storage test with ${tip_amount} tip",
                    "tip_amount": tip_amount
                }
                
                # Clear auth token for public request creation
                temp_token = self.auth_token
                self.auth_token = None
                
                response = self.make_request("POST", "/requests", request_data)
                
                # Restore auth token
                self.auth_token = temp_token
                
                if response.status_code == 200:
                    request_result = response.json()
                    storage_request_ids.append(request_result["id"])
                    print(f"   ✅ Storage test request created: {request_result['id']}")
                else:
                    print(f"   ❌ Storage test request failed: {response.status_code}")
            
            # Now verify storage by retrieving musician's requests
            print("📊 Verifying tip amounts are stored correctly")
            
            musician_requests_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
            
            if musician_requests_response.status_code == 200:
                all_requests = musician_requests_response.json()
                print(f"   📊 Retrieved {len(all_requests)} total requests for musician")
                
                # Find our storage test requests and verify tip amounts
                verified_tips = []
                for request in all_requests:
                    if request["id"] in storage_request_ids:
                        stored_tip = request.get("tip_amount", "MISSING")
                        requester_name = request.get("requester_name", "")
                        
                        if "Storage Tester 1" in requester_name and stored_tip == 15.50:
                            verified_tips.append(15.50)
                            print(f"   ✅ Storage Tester 1 tip verified: ${stored_tip}")
                        elif "Storage Tester 2" in requester_name and stored_tip == 25.75:
                            verified_tips.append(25.75)
                            print(f"   ✅ Storage Tester 2 tip verified: ${stored_tip}")
                        elif "Storage Tester 3" in requester_name and stored_tip == 100.00:
                            verified_tips.append(100.00)
                            print(f"   ✅ Storage Tester 3 tip verified: ${stored_tip}")
                        else:
                            print(f"   ❌ Tip amount verification failed for {requester_name}: expected in {storage_test_amounts}, got {stored_tip}")
                
                storage_verification_success = len(verified_tips) == len(storage_test_amounts)
            else:
                print(f"   ❌ Failed to retrieve musician requests: {musician_requests_response.status_code}")
                storage_verification_success = False
            
            # Assessment
            if storage_verification_success:
                self.log_result("Tip Amount Storage", True, f"✅ All {len(storage_test_amounts)} tip amounts stored and retrieved correctly")
            else:
                self.log_result("Tip Amount Storage", False, f"❌ Tip amount storage verification failed: {len(verified_tips)}/{len(storage_test_amounts)} verified")
            
            print("=" * 80)
            return storage_verification_success
            
        except Exception as e:
            self.log_result("Tip Amount Storage", False, f"❌ Exception: {str(e)}")
            return False

    def test_request_retrieval_with_tips(self):
        """Test GET /api/requests/updates/{musician_id} and verify that returned requests include tip_amount field"""
        try:
            print("🎵 PRIORITY 3: Testing Request Retrieval with Tips")
            print("=" * 80)
            
            # Test the On Stage updates endpoint specifically
            print("📊 Testing GET /api/requests/updates/{musician_id} endpoint")
            
            updates_response = self.make_request("GET", f"/requests/updates/{self.musician_id}")
            
            print(f"   📊 Updates endpoint response status: {updates_response.status_code}")
            print(f"   📊 Updates endpoint response: {updates_response.text[:300]}...")
            
            if updates_response.status_code == 200:
                updates_data = updates_response.json()
                
                # Check if response is a dict with 'requests' key or direct list
                if isinstance(updates_data, dict) and 'requests' in updates_data:
                    requests_list = updates_data['requests']
                    print(f"   📊 Updates response format: dict with 'requests' key")
                    print(f"   📊 Additional fields: {list(updates_data.keys())}")
                elif isinstance(updates_data, list):
                    requests_list = updates_data
                    print(f"   📊 Updates response format: direct list")
                else:
                    print(f"   ❌ Unexpected response format: {type(updates_data)}")
                    requests_list = []
                
                print(f"   📊 Found {len(requests_list)} requests in updates response")
                
                # Verify tip_amount field is present in requests
                requests_with_tips = 0
                tip_amounts_found = []
                
                for request in requests_list:
                    if "tip_amount" in request:
                        requests_with_tips += 1
                        tip_amount = request["tip_amount"]
                        tip_amounts_found.append(tip_amount)
                        requester_name = request.get("requester_name", "Unknown")
                        print(f"   ✅ Request has tip_amount field: {requester_name} - ${tip_amount}")
                    else:
                        requester_name = request.get("requester_name", "Unknown")
                        print(f"   ❌ Request missing tip_amount field: {requester_name}")
                
                # Check for our test requests specifically
                test_tip_amounts_found = []
                for request in requests_list:
                    requester_name = request.get("requester_name", "")
                    if "Tip Tester" in requester_name or "Storage Tester" in requester_name:
                        tip_amount = request.get("tip_amount", "MISSING")
                        test_tip_amounts_found.append(tip_amount)
                        print(f"   📊 Test request found: {requester_name} - ${tip_amount}")
                
                updates_endpoint_success = (
                    len(requests_list) > 0 and
                    requests_with_tips == len(requests_list) and
                    len(test_tip_amounts_found) > 0
                )
                
                if updates_endpoint_success:
                    print(f"   ✅ Updates endpoint working: {requests_with_tips}/{len(requests_list)} requests have tip_amount field")
                else:
                    print(f"   ❌ Updates endpoint issues: {requests_with_tips}/{len(requests_list)} requests have tip_amount field")
            else:
                print(f"   ❌ Updates endpoint failed: {updates_response.status_code}")
                updates_endpoint_success = False
            
            # Also test the regular musician requests endpoint for comparison
            print("📊 Testing GET /requests/musician/{musician_id} endpoint for comparison")
            
            musician_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
            
            if musician_response.status_code == 200:
                musician_requests = musician_response.json()
                print(f"   📊 Musician requests endpoint returned {len(musician_requests)} requests")
                
                musician_requests_with_tips = sum(1 for req in musician_requests if "tip_amount" in req)
                print(f"   📊 Musician requests with tip_amount: {musician_requests_with_tips}/{len(musician_requests)}")
                
                musician_endpoint_success = musician_requests_with_tips == len(musician_requests)
            else:
                print(f"   ❌ Musician requests endpoint failed: {musician_response.status_code}")
                musician_endpoint_success = False
            
            # Assessment
            if updates_endpoint_success and musician_endpoint_success:
                self.log_result("Request Retrieval with Tips", True, "✅ Both updates and musician endpoints return requests with tip_amount field")
            elif updates_endpoint_success:
                self.log_result("Request Retrieval with Tips", True, "✅ Updates endpoint returns requests with tip_amount field (primary On Stage endpoint working)")
            else:
                self.log_result("Request Retrieval with Tips", False, "❌ Request retrieval endpoints missing tip_amount field")
            
            print("=" * 80)
            return updates_endpoint_success
            
        except Exception as e:
            self.log_result("Request Retrieval with Tips", False, f"❌ Exception: {str(e)}")
            return False

    def test_zero_tip_handling(self):
        """Test requests with tip_amount=0 and verify they're handled correctly (no tip display)"""
        try:
            print("🎵 PRIORITY 4: Testing Zero Tip Handling")
            print("=" * 80)
            
            # Create requests with tip_amount=0
            print("📊 Creating requests with tip_amount=0")
            
            zero_tip_requests = []
            for i in range(3):
                request_data = {
                    "song_id": self.test_song_ids[0] if self.test_song_ids else "test-song-id",
                    "requester_name": f"Zero Tip Tester {i+1}",
                    "requester_email": f"zerotip{i+1}@example.com",
                    "dedication": f"Test request with zero tip {i+1}",
                    "tip_amount": 0.0
                }
                
                # Clear auth token for public request creation
                temp_token = self.auth_token
                self.auth_token = None
                
                response = self.make_request("POST", "/requests", request_data)
                
                # Restore auth token
                self.auth_token = temp_token
                
                if response.status_code == 200:
                    request_result = response.json()
                    zero_tip_requests.append(request_result)
                    print(f"   ✅ Zero tip request created: {request_result['id']}")
                else:
                    print(f"   ❌ Zero tip request failed: {response.status_code}")
            
            # Test requests without tip_amount field (should default to 0.0)
            print("📊 Creating requests without tip_amount field (backward compatibility)")
            
            no_tip_field_requests = []
            for i in range(2):
                request_data = {
                    "song_id": self.test_song_ids[0] if self.test_song_ids else "test-song-id",
                    "requester_name": f"No Tip Field Tester {i+1}",
                    "requester_email": f"notipfield{i+1}@example.com",
                    "dedication": f"Test request without tip_amount field {i+1}"
                    # Deliberately omit tip_amount field
                }
                
                # Clear auth token for public request creation
                temp_token = self.auth_token
                self.auth_token = None
                
                response = self.make_request("POST", "/requests", request_data)
                
                # Restore auth token
                self.auth_token = temp_token
                
                if response.status_code == 200:
                    request_result = response.json()
                    no_tip_field_requests.append(request_result)
                    print(f"   ✅ No tip field request created: {request_result['id']}")
                    
                    # Verify it defaults to 0.0
                    default_tip = request_result.get("tip_amount", "MISSING")
                    if default_tip == 0.0:
                        print(f"   ✅ Request correctly defaults to tip_amount=0.0")
                    else:
                        print(f"   ❌ Request tip_amount default incorrect: {default_tip}")
                else:
                    print(f"   ❌ No tip field request failed: {response.status_code}")
            
            # Verify zero tip requests are handled correctly in retrieval
            print("📊 Verifying zero tip requests in retrieval endpoints")
            
            updates_response = self.make_request("GET", f"/requests/updates/{self.musician_id}")
            
            if updates_response.status_code == 200:
                updates_data = updates_response.json()
                
                # Handle both response formats
                if isinstance(updates_data, dict) and 'requests' in updates_data:
                    requests_list = updates_data['requests']
                else:
                    requests_list = updates_data
                
                # Find our zero tip test requests
                zero_tip_found = []
                no_tip_field_found = []
                
                for request in requests_list:
                    requester_name = request.get("requester_name", "")
                    tip_amount = request.get("tip_amount", "MISSING")
                    
                    if "Zero Tip Tester" in requester_name:
                        zero_tip_found.append(tip_amount)
                        if tip_amount == 0.0:
                            print(f"   ✅ Zero tip request correctly retrieved: {requester_name} - ${tip_amount}")
                        else:
                            print(f"   ❌ Zero tip request incorrect: {requester_name} - ${tip_amount}")
                    
                    elif "No Tip Field Tester" in requester_name:
                        no_tip_field_found.append(tip_amount)
                        if tip_amount == 0.0:
                            print(f"   ✅ No tip field request correctly retrieved: {requester_name} - ${tip_amount}")
                        else:
                            print(f"   ❌ No tip field request incorrect: {requester_name} - ${tip_amount}")
                
                zero_tip_handling_success = (
                    len(zero_tip_found) >= 3 and all(tip == 0.0 for tip in zero_tip_found) and
                    len(no_tip_field_found) >= 2 and all(tip == 0.0 for tip in no_tip_field_found)
                )
            else:
                print(f"   ❌ Failed to retrieve requests for zero tip verification: {updates_response.status_code}")
                zero_tip_handling_success = False
            
            # Assessment
            if zero_tip_handling_success:
                self.log_result("Zero Tip Handling", True, "✅ Zero tip amounts and missing tip fields handled correctly (default to 0.0)")
            else:
                self.log_result("Zero Tip Handling", False, "❌ Zero tip handling issues found")
            
            print("=" * 80)
            return zero_tip_handling_success
            
        except Exception as e:
            self.log_result("Zero Tip Handling", False, f"❌ Exception: {str(e)}")
            return False

    def test_on_stage_data_flow(self):
        """Verify that the request data structure now includes tip information that the On Stage interface can display"""
        try:
            print("🎵 PRIORITY 5: Testing On Stage Data Flow")
            print("=" * 80)
            
            # Create a comprehensive request with tip for On Stage testing
            print("📊 Creating comprehensive On Stage test request")
            
            on_stage_request_data = {
                "song_id": self.test_song_ids[0] if self.test_song_ids else "test-song-id",
                "requester_name": "On Stage Display Tester",
                "requester_email": "onstage@example.com",
                "dedication": "This request should display tip info on On Stage interface",
                "tip_amount": 15.00
            }
            
            # Clear auth token for public request creation
            temp_token = self.auth_token
            self.auth_token = None
            
            response = self.make_request("POST", "/requests", on_stage_request_data)
            
            # Restore auth token
            self.auth_token = temp_token
            
            if response.status_code == 200:
                on_stage_request = response.json()
                on_stage_request_id = on_stage_request["id"]
                print(f"   ✅ On Stage test request created: {on_stage_request_id}")
            else:
                print(f"   ❌ On Stage test request failed: {response.status_code}")
                return False
            
            # Test the On Stage updates endpoint specifically
            print("📊 Testing On Stage updates endpoint data structure")
            
            updates_response = self.make_request("GET", f"/requests/updates/{self.musician_id}")
            
            if updates_response.status_code == 200:
                updates_data = updates_response.json()
                print(f"   📊 Updates response type: {type(updates_data)}")
                
                # Handle both response formats
                if isinstance(updates_data, dict):
                    print(f"   📊 Updates response keys: {list(updates_data.keys())}")
                    if 'requests' in updates_data:
                        requests_list = updates_data['requests']
                        print(f"   📊 Additional metadata: total_requests={updates_data.get('total_requests')}, last_updated={updates_data.get('last_updated')}")
                    else:
                        requests_list = []
                else:
                    requests_list = updates_data
                
                # Find our On Stage test request
                on_stage_request_found = None
                for request in requests_list:
                    if request.get("requester_name") == "On Stage Display Tester":
                        on_stage_request_found = request
                        break
                
                if on_stage_request_found:
                    print(f"   ✅ On Stage test request found in updates")
                    
                    # Verify all required fields for On Stage display
                    required_fields = [
                        "id", "musician_id", "song_id", "song_title", "song_artist",
                        "requester_name", "requester_email", "dedication", "tip_amount",
                        "status", "created_at"
                    ]
                    
                    missing_fields = []
                    present_fields = []
                    
                    for field in required_fields:
                        if field in on_stage_request_found:
                            present_fields.append(field)
                            value = on_stage_request_found[field]
                            print(f"   ✅ {field}: {value}")
                        else:
                            missing_fields.append(field)
                            print(f"   ❌ {field}: MISSING")
                    
                    # Specifically verify tip_amount
                    tip_amount_correct = on_stage_request_found.get("tip_amount") == 15.00
                    if tip_amount_correct:
                        print(f"   ✅ tip_amount correct for On Stage display: ${on_stage_request_found['tip_amount']}")
                    else:
                        print(f"   ❌ tip_amount incorrect: expected $15.00, got ${on_stage_request_found.get('tip_amount')}")
                    
                    on_stage_data_complete = len(missing_fields) == 0 and tip_amount_correct
                else:
                    print(f"   ❌ On Stage test request not found in updates")
                    on_stage_data_complete = False
            else:
                print(f"   ❌ Updates endpoint failed: {updates_response.status_code}")
                on_stage_data_complete = False
            
            # Test request status updates (On Stage functionality)
            print("📊 Testing request status updates with tip information preserved")
            
            if on_stage_request_found:
                # Update request status to simulate On Stage workflow
                status_update_response = self.make_request("PUT", f"/requests/{on_stage_request_id}/status", {"status": "accepted"})
                
                if status_update_response.status_code == 200:
                    print(f"   ✅ Request status updated successfully")
                    
                    # Verify tip information is preserved after status update
                    updated_response = self.make_request("GET", f"/requests/updates/{self.musician_id}")
                    
                    if updated_response.status_code == 200:
                        updated_data = updated_response.json()
                        
                        # Handle response format
                        if isinstance(updated_data, dict) and 'requests' in updated_data:
                            updated_requests = updated_data['requests']
                        else:
                            updated_requests = updated_data
                        
                        # Find updated request
                        updated_request = None
                        for request in updated_requests:
                            if request.get("id") == on_stage_request_id:
                                updated_request = request
                                break
                        
                        if updated_request:
                            updated_tip = updated_request.get("tip_amount")
                            updated_status = updated_request.get("status")
                            
                            if updated_tip == 15.00 and updated_status == "accepted":
                                print(f"   ✅ Tip information preserved after status update: ${updated_tip}, status={updated_status}")
                                status_update_preserves_tip = True
                            else:
                                print(f"   ❌ Tip information not preserved: tip=${updated_tip}, status={updated_status}")
                                status_update_preserves_tip = False
                        else:
                            print(f"   ❌ Updated request not found")
                            status_update_preserves_tip = False
                    else:
                        print(f"   ❌ Failed to retrieve updated requests: {updated_response.status_code}")
                        status_update_preserves_tip = False
                else:
                    print(f"   ❌ Status update failed: {status_update_response.status_code}")
                    status_update_preserves_tip = False
            else:
                status_update_preserves_tip = False
            
            # Assessment
            if on_stage_data_complete and status_update_preserves_tip:
                self.log_result("On Stage Data Flow", True, "✅ On Stage data flow complete: tip information available and preserved through status updates")
            else:
                issues = []
                if not on_stage_data_complete:
                    issues.append("On Stage data structure incomplete")
                if not status_update_preserves_tip:
                    issues.append("tip information not preserved through status updates")
                
                self.log_result("On Stage Data Flow", False, f"❌ On Stage data flow issues: {', '.join(issues)}")
            
            print("=" * 80)
            return on_stage_data_complete and status_update_preserves_tip
            
        except Exception as e:
            self.log_result("On Stage Data Flow", False, f"❌ Exception: {str(e)}")
            return False

    def test_backward_compatibility(self):
        """Ensure existing requests without tip_amount still work (default to 0.0)"""
        try:
            print("🎵 PRIORITY 6: Testing Backward Compatibility")
            print("=" * 80)
            
            # Simulate existing requests by creating requests without tip_amount
            print("📊 Creating requests without tip_amount to simulate existing data")
            
            legacy_requests = []
            for i in range(3):
                # Create request data without tip_amount field
                request_data = {
                    "song_id": self.test_song_ids[0] if self.test_song_ids else "test-song-id",
                    "requester_name": f"Legacy Request Tester {i+1}",
                    "requester_email": f"legacy{i+1}@example.com",
                    "dedication": f"Legacy request without tip_amount field {i+1}"
                    # Deliberately omit tip_amount
                }
                
                # Clear auth token for public request creation
                temp_token = self.auth_token
                self.auth_token = None
                
                response = self.make_request("POST", "/requests", request_data)
                
                # Restore auth token
                self.auth_token = temp_token
                
                if response.status_code == 200:
                    request_result = response.json()
                    legacy_requests.append(request_result)
                    
                    # Verify it defaults to 0.0
                    tip_amount = request_result.get("tip_amount", "MISSING")
                    if tip_amount == 0.0:
                        print(f"   ✅ Legacy request {i+1} defaults to tip_amount=0.0")
                    else:
                        print(f"   ❌ Legacy request {i+1} tip_amount incorrect: {tip_amount}")
                else:
                    print(f"   ❌ Legacy request {i+1} creation failed: {response.status_code}")
            
            # Test that legacy requests work with all endpoints
            print("📊 Testing legacy requests with all retrieval endpoints")
            
            # Test updates endpoint
            updates_response = self.make_request("GET", f"/requests/updates/{self.musician_id}")
            
            if updates_response.status_code == 200:
                updates_data = updates_response.json()
                
                # Handle response format
                if isinstance(updates_data, dict) and 'requests' in updates_data:
                    requests_list = updates_data['requests']
                else:
                    requests_list = updates_data
                
                # Find legacy requests
                legacy_found_in_updates = []
                for request in requests_list:
                    requester_name = request.get("requester_name", "")
                    if "Legacy Request Tester" in requester_name:
                        tip_amount = request.get("tip_amount", "MISSING")
                        legacy_found_in_updates.append(tip_amount)
                        
                        if tip_amount == 0.0:
                            print(f"   ✅ Legacy request in updates: {requester_name} - ${tip_amount}")
                        else:
                            print(f"   ❌ Legacy request tip incorrect in updates: {requester_name} - ${tip_amount}")
                
                updates_legacy_success = len(legacy_found_in_updates) >= 3 and all(tip == 0.0 for tip in legacy_found_in_updates)
            else:
                print(f"   ❌ Updates endpoint failed: {updates_response.status_code}")
                updates_legacy_success = False
            
            # Test musician requests endpoint
            musician_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
            
            if musician_response.status_code == 200:
                musician_requests = musician_response.json()
                
                # Find legacy requests
                legacy_found_in_musician = []
                for request in musician_requests:
                    requester_name = request.get("requester_name", "")
                    if "Legacy Request Tester" in requester_name:
                        tip_amount = request.get("tip_amount", "MISSING")
                        legacy_found_in_musician.append(tip_amount)
                        
                        if tip_amount == 0.0:
                            print(f"   ✅ Legacy request in musician endpoint: {requester_name} - ${tip_amount}")
                        else:
                            print(f"   ❌ Legacy request tip incorrect in musician endpoint: {requester_name} - ${tip_amount}")
                
                musician_legacy_success = len(legacy_found_in_musician) >= 3 and all(tip == 0.0 for tip in legacy_found_in_musician)
            else:
                print(f"   ❌ Musician requests endpoint failed: {musician_response.status_code}")
                musician_legacy_success = False
            
            # Test status updates on legacy requests
            print("📊 Testing status updates on legacy requests")
            
            if legacy_requests:
                legacy_request_id = legacy_requests[0]["id"]
                
                status_update_response = self.make_request("PUT", f"/requests/{legacy_request_id}/status", {"status": "played"})
                
                if status_update_response.status_code == 200:
                    print(f"   ✅ Legacy request status update successful")
                    
                    # Verify tip_amount is still 0.0 after update
                    updated_response = self.make_request("GET", f"/requests/updates/{self.musician_id}")
                    
                    if updated_response.status_code == 200:
                        updated_data = updated_response.json()
                        
                        # Handle response format
                        if isinstance(updated_data, dict) and 'requests' in updated_data:
                            updated_requests = updated_data['requests']
                        else:
                            updated_requests = updated_data
                        
                        # Find updated legacy request
                        updated_legacy = None
                        for request in updated_requests:
                            if request.get("id") == legacy_request_id:
                                updated_legacy = request
                                break
                        
                        if updated_legacy:
                            updated_tip = updated_legacy.get("tip_amount")
                            updated_status = updated_legacy.get("status")
                            
                            if updated_tip == 0.0 and updated_status == "played":
                                print(f"   ✅ Legacy request maintains tip_amount=0.0 after status update")
                                legacy_status_update_success = True
                            else:
                                print(f"   ❌ Legacy request tip/status incorrect after update: tip=${updated_tip}, status={updated_status}")
                                legacy_status_update_success = False
                        else:
                            print(f"   ❌ Updated legacy request not found")
                            legacy_status_update_success = False
                    else:
                        print(f"   ❌ Failed to retrieve updated legacy requests: {updated_response.status_code}")
                        legacy_status_update_success = False
                else:
                    print(f"   ❌ Legacy request status update failed: {status_update_response.status_code}")
                    legacy_status_update_success = False
            else:
                legacy_status_update_success = False
            
            # Assessment
            if updates_legacy_success and musician_legacy_success and legacy_status_update_success:
                self.log_result("Backward Compatibility", True, "✅ Backward compatibility maintained: existing requests without tip_amount work correctly (default to 0.0)")
            else:
                issues = []
                if not updates_legacy_success:
                    issues.append("updates endpoint legacy compatibility issues")
                if not musician_legacy_success:
                    issues.append("musician endpoint legacy compatibility issues")
                if not legacy_status_update_success:
                    issues.append("legacy request status updates not working")
                
                self.log_result("Backward Compatibility", False, f"❌ Backward compatibility issues: {', '.join(issues)}")
            
            print("=" * 80)
            return updates_legacy_success and musician_legacy_success and legacy_status_update_success
            
        except Exception as e:
            self.log_result("Backward Compatibility", False, f"❌ Exception: {str(e)}")
            return False

    def test_complete_request_flow(self):
        """Complete Request Flow Test - Create a test musician, submit requests with various tip amounts, and verify the data flows correctly through the system"""
        try:
            print("🎵 PRIORITY 7: Testing Complete Request Flow")
            print("=" * 80)
            
            # This test uses the existing setup, so we'll create a comprehensive flow test
            print("📊 Testing complete end-to-end request flow with tips")
            
            # Create requests with various tip amounts for complete flow testing
            flow_test_requests = [
                {"tip": 0.0, "name": "Flow Test No Tip", "dedication": "Testing zero tip flow"},
                {"tip": 5.0, "name": "Flow Test Small Tip", "dedication": "Testing small tip flow"},
                {"tip": 15.0, "name": "Flow Test Medium Tip", "dedication": "Testing medium tip flow"},
                {"tip": 50.0, "name": "Flow Test Large Tip", "dedication": "Testing large tip flow"}
            ]
            
            created_flow_requests = []
            
            # Step 1: Create requests with various tip amounts
            print("📊 Step 1: Creating requests with various tip amounts")
            
            for i, test_case in enumerate(flow_test_requests):
                request_data = {
                    "song_id": self.test_song_ids[i % len(self.test_song_ids)] if self.test_song_ids else "test-song-id",
                    "requester_name": test_case["name"],
                    "requester_email": f"flowtest{i+1}@example.com",
                    "dedication": test_case["dedication"],
                    "tip_amount": test_case["tip"]
                }
                
                # Clear auth token for public request creation
                temp_token = self.auth_token
                self.auth_token = None
                
                response = self.make_request("POST", "/requests", request_data)
                
                # Restore auth token
                self.auth_token = temp_token
                
                if response.status_code == 200:
                    request_result = response.json()
                    created_flow_requests.append(request_result)
                    print(f"   ✅ Flow test request created: {test_case['name']} - ${test_case['tip']}")
                else:
                    print(f"   ❌ Flow test request failed: {test_case['name']} - {response.status_code}")
            
            # Step 2: Verify all requests appear in On Stage updates
            print("📊 Step 2: Verifying all requests appear in On Stage updates")
            
            updates_response = self.make_request("GET", f"/requests/updates/{self.musician_id}")
            
            if updates_response.status_code == 200:
                updates_data = updates_response.json()
                
                # Handle response format
                if isinstance(updates_data, dict) and 'requests' in updates_data:
                    requests_list = updates_data['requests']
                else:
                    requests_list = updates_data
                
                # Find our flow test requests
                flow_requests_found = []
                for request in requests_list:
                    requester_name = request.get("requester_name", "")
                    if "Flow Test" in requester_name:
                        tip_amount = request.get("tip_amount", "MISSING")
                        flow_requests_found.append({
                            "name": requester_name,
                            "tip": tip_amount,
                            "id": request.get("id")
                        })
                        print(f"   ✅ Flow request found in updates: {requester_name} - ${tip_amount}")
                
                all_flow_requests_found = len(flow_requests_found) >= len(flow_test_requests)
            else:
                print(f"   ❌ Updates endpoint failed: {updates_response.status_code}")
                all_flow_requests_found = False
                flow_requests_found = []
            
            # Step 3: Test status updates through On Stage workflow
            print("📊 Step 3: Testing status updates through On Stage workflow")
            
            status_transitions = ["accepted", "up_next", "played"]
            status_update_success = True
            
            if flow_requests_found:
                test_request = flow_requests_found[0]  # Use first request for status testing
                test_request_id = test_request["id"]
                original_tip = test_request["tip"]
                
                for status in status_transitions:
                    status_response = self.make_request("PUT", f"/requests/{test_request_id}/status", {"status": status})
                    
                    if status_response.status_code == 200:
                        print(f"   ✅ Status updated to: {status}")
                        
                        # Verify tip amount is preserved
                        verify_response = self.make_request("GET", f"/requests/updates/{self.musician_id}")
                        
                        if verify_response.status_code == 200:
                            verify_data = verify_response.json()
                            
                            # Handle response format
                            if isinstance(verify_data, dict) and 'requests' in verify_data:
                                verify_requests = verify_data['requests']
                            else:
                                verify_requests = verify_data
                            
                            # Find updated request
                            updated_request = None
                            for request in verify_requests:
                                if request.get("id") == test_request_id:
                                    updated_request = request
                                    break
                            
                            if updated_request:
                                current_tip = updated_request.get("tip_amount")
                                current_status = updated_request.get("status")
                                
                                if current_tip == original_tip and current_status == status:
                                    print(f"   ✅ Tip preserved through status update: ${current_tip}, status={current_status}")
                                else:
                                    print(f"   ❌ Tip/status incorrect: expected ${original_tip}/{status}, got ${current_tip}/{current_status}")
                                    status_update_success = False
                            else:
                                print(f"   ❌ Updated request not found")
                                status_update_success = False
                        else:
                            print(f"   ❌ Failed to verify status update: {verify_response.status_code}")
                            status_update_success = False
                    else:
                        print(f"   ❌ Status update to {status} failed: {status_response.status_code}")
                        status_update_success = False
            else:
                status_update_success = False
            
            # Step 4: Verify tip amounts are correctly displayed across all endpoints
            print("📊 Step 4: Verifying tip amounts across all endpoints")
            
            # Test musician requests endpoint
            musician_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
            
            if musician_response.status_code == 200:
                musician_requests = musician_response.json()
                
                flow_in_musician = []
                for request in musician_requests:
                    requester_name = request.get("requester_name", "")
                    if "Flow Test" in requester_name:
                        tip_amount = request.get("tip_amount", "MISSING")
                        flow_in_musician.append(tip_amount)
                
                musician_endpoint_success = len(flow_in_musician) >= len(flow_test_requests)
                print(f"   📊 Flow requests in musician endpoint: {len(flow_in_musician)}")
            else:
                print(f"   ❌ Musician endpoint failed: {musician_response.status_code}")
                musician_endpoint_success = False
            
            # Step 5: Test tip amount validation and edge cases
            print("📊 Step 5: Testing tip amount validation and edge cases")
            
            # Test negative tip amount (should be rejected or handled)
            negative_tip_data = {
                "song_id": self.test_song_ids[0] if self.test_song_ids else "test-song-id",
                "requester_name": "Negative Tip Tester",
                "requester_email": "negative@example.com",
                "dedication": "Testing negative tip amount",
                "tip_amount": -5.0
            }
            
            # Clear auth token for public request creation
            temp_token = self.auth_token
            self.auth_token = None
            
            negative_response = self.make_request("POST", "/requests", negative_tip_data)
            
            # Restore auth token
            self.auth_token = temp_token
            
            if negative_response.status_code == 200:
                negative_result = negative_response.json()
                negative_tip_stored = negative_result.get("tip_amount", 0)
                
                if negative_tip_stored >= 0:
                    print(f"   ✅ Negative tip handled correctly: stored as ${negative_tip_stored}")
                    negative_tip_handling = True
                else:
                    print(f"   ❌ Negative tip not handled: stored as ${negative_tip_stored}")
                    negative_tip_handling = False
            elif negative_response.status_code == 400:
                print(f"   ✅ Negative tip rejected with validation error (expected)")
                negative_tip_handling = True
            else:
                print(f"   ❌ Negative tip test unexpected response: {negative_response.status_code}")
                negative_tip_handling = False
            
            # Assessment
            complete_flow_success = (
                len(created_flow_requests) >= len(flow_test_requests) and
                all_flow_requests_found and
                status_update_success and
                musician_endpoint_success and
                negative_tip_handling
            )
            
            if complete_flow_success:
                self.log_result("Complete Request Flow", True, f"✅ Complete request flow working: {len(created_flow_requests)} requests created, status updates preserve tips, all endpoints consistent")
            else:
                issues = []
                if len(created_flow_requests) < len(flow_test_requests):
                    issues.append("not all flow test requests created")
                if not all_flow_requests_found:
                    issues.append("not all requests found in updates")
                if not status_update_success:
                    issues.append("status updates don't preserve tips")
                if not musician_endpoint_success:
                    issues.append("musician endpoint inconsistent")
                if not negative_tip_handling:
                    issues.append("negative tip handling issues")
                
                self.log_result("Complete Request Flow", False, f"❌ Complete request flow issues: {', '.join(issues)}")
            
            print("=" * 80)
            return complete_flow_success
            
        except Exception as e:
            self.log_result("Complete Request Flow", False, f"❌ Exception: {str(e)}")
            return False

    def cleanup_test_data(self):
        """Clean up test data created during testing"""
        try:
            print("🧹 CLEANUP: Removing test data")
            print("=" * 80)
            
            # Delete test requests
            if self.test_request_ids:
                for request_id in self.test_request_ids:
                    try:
                        delete_response = self.make_request("DELETE", f"/requests/{request_id}")
                        if delete_response.status_code == 200:
                            print(f"   ✅ Deleted test request: {request_id}")
                        else:
                            print(f"   ⚠️  Could not delete test request {request_id}: {delete_response.status_code}")
                    except:
                        print(f"   ⚠️  Error deleting test request: {request_id}")
            
            # Delete test songs
            if self.test_song_ids:
                for song_id in self.test_song_ids:
                    try:
                        delete_response = self.make_request("DELETE", f"/songs/{song_id}")
                        if delete_response.status_code == 200:
                            print(f"   ✅ Deleted test song: {song_id}")
                        else:
                            print(f"   ⚠️  Could not delete test song {song_id}: {delete_response.status_code}")
                    except:
                        print(f"   ⚠️  Error deleting test song: {song_id}")
            
            print("   🧹 Cleanup completed")
            print("=" * 80)
            
        except Exception as e:
            print(f"   ⚠️  Cleanup error: {str(e)}")

    def run_all_tests(self):
        """Run all tip integration tests in sequence"""
        print("🎵 STARTING COMPREHENSIVE TIP INTEGRATION TESTING FOR ON STAGE REQUEST CARDS")
        print("=" * 100)
        
        # Setup
        if not self.setup_test_musician():
            print("❌ SETUP FAILED - Cannot proceed with tests")
            return
        
        # Test 1: Request Creation with Tips
        self.test_request_creation_with_tips()
        
        # Test 2: Tip Amount Storage
        self.test_tip_amount_storage()
        
        # Test 3: Request Retrieval with Tips
        self.test_request_retrieval_with_tips()
        
        # Test 4: Zero Tip Handling
        self.test_zero_tip_handling()
        
        # Test 5: On Stage Data Flow
        self.test_on_stage_data_flow()
        
        # Test 6: Backward Compatibility
        self.test_backward_compatibility()
        
        # Test 7: Complete Request Flow
        self.test_complete_request_flow()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Print final results
        print("\n" + "=" * 100)
        print("🎵 FINAL TIP INTEGRATION TEST RESULTS")
        print("=" * 100)
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        
        if self.results['passed'] + self.results['failed'] > 0:
            success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100)
            print(f"📊 SUCCESS RATE: {success_rate:.1f}%")
        
        if self.results['errors']:
            print("\n❌ FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        print("\n" + "=" * 100)
        
        # Summary for main agent
        if self.results['failed'] == 0:
            print("🎉 ALL TIP INTEGRATION TESTS PASSED - On Stage request cards tip functionality is working correctly!")
        else:
            print("⚠️  SOME TIP INTEGRATION TESTS FAILED - Review failed tests above for issues to address")

if __name__ == "__main__":
    tester = TipIntegrationTester()
    tester.run_all_tests()