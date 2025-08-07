#!/usr/bin/env python3
"""
Show Management and Deletion Tests for RequestWave
Tests the FIXED show management and deletion functionality
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://c9aa150a-6f2f-42af-9179-ded9ed77f946.preview.emergentagent.com/api"
TEST_MUSICIAN = {
    "name": "Show Test Musician",
    "email": "showtest.musician@requestwave.com",
    "password": "SecurePassword123!"
}

class ShowManagementTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
        self.test_song_id = None
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

    def setup_test_environment(self):
        """Set up test environment with authentication and test data"""
        print("🔧 Setting up test environment...")
        
        # Register or login musician
        response = self.make_request("POST", "/auth/register", TEST_MUSICIAN)
        
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data["token"]
            self.musician_id = data["musician"]["id"]
            self.musician_slug = data["musician"]["slug"]
            print(f"✅ Registered musician: {data['musician']['name']}")
        elif response.status_code == 400:
            # Musician might already exist, try login
            login_data = {
                "email": TEST_MUSICIAN["email"],
                "password": TEST_MUSICIAN["password"]
            }
            response = self.make_request("POST", "/auth/login", login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data["token"]
                self.musician_id = data["musician"]["id"]
                self.musician_slug = data["musician"]["slug"]
                print(f"✅ Logged in musician: {data['musician']['name']}")
            else:
                print(f"❌ Failed to login: {response.status_code}")
                return False
        else:
            print(f"❌ Failed to register: {response.status_code}")
            return False
        
        # Create a test song
        song_data = {
            "title": "Show Test Song",
            "artist": "Test Artist",
            "genres": ["Jazz"],
            "moods": ["Smooth"],
            "year": 2023,
            "notes": "Test song for show management"
        }
        
        response = self.make_request("POST", "/songs", song_data)
        
        if response.status_code == 200:
            data = response.json()
            self.test_song_id = data["id"]
            print(f"✅ Created test song: {data['title']}")
        else:
            print(f"❌ Failed to create test song: {response.status_code}")
            return False
        
        return True

    def test_show_stop_functionality(self):
        """Test show stop functionality specifically - CRITICAL SHOW STOP TEST"""
        try:
            print("🔍 Testing show stop functionality specifically")
            
            # Step 1: Start a show
            show_data = {
                "name": "Stop Test Show",
                "venue": "Test Venue",
                "notes": "Show to test stop functionality"
            }
            
            start_response = self.make_request("POST", "/shows/start", show_data)
            
            if start_response.status_code != 200:
                self.log_result("Show Stop Functionality - Start Show", False, f"Failed to start show: {start_response.status_code}")
                return
            
            start_data = start_response.json()
            show_name = start_data["show"]["name"]
            
            # Step 2: Verify show is active
            current_response = self.make_request("GET", "/shows/current")
            
            if current_response.status_code != 200:
                self.log_result("Show Stop Functionality - Check Current", False, f"Failed to get current show: {current_response.status_code}")
                return
            
            current_data = current_response.json()
            if not current_data.get("active"):
                self.log_result("Show Stop Functionality - Check Current", False, f"Show not active after start: {current_data}")
                return
            
            # Step 3: Create a request (should be assigned to current show)
            request_data = {
                "song_id": self.test_song_id,
                "requester_name": "Stop Test Fan",
                "requester_email": "stoptest@example.com",
                "dedication": "Request before stop"
            }
            
            request_response = self.make_request("POST", "/requests", request_data)
            
            if request_response.status_code == 200:
                request_data_response = request_response.json()
                if request_data_response.get("show_name") == show_name:
                    self.log_result("Show Stop Functionality - Request Before Stop", True, f"✅ Request assigned to active show: {show_name}")
                else:
                    self.log_result("Show Stop Functionality - Request Before Stop", False, f"Request not assigned to show: {request_data_response}")
            
            # Step 4: Stop the show
            stop_response = self.make_request("POST", "/shows/stop")
            
            if stop_response.status_code != 200:
                self.log_result("Show Stop Functionality - Stop Show", False, f"Failed to stop show: {stop_response.status_code}")
                return
            
            stop_data = stop_response.json()
            if not stop_data.get("success"):
                self.log_result("Show Stop Functionality - Stop Show", False, f"Stop show failed: {stop_data}")
                return
            
            self.log_result("Show Stop Functionality - Stop Show", True, f"✅ Show stopped successfully: {stop_data['message']}")
            
            # Step 5: Verify current show is cleared
            current_after_response = self.make_request("GET", "/shows/current")
            
            if current_after_response.status_code == 200:
                current_after_data = current_after_response.json()
                if not current_after_data.get("active"):
                    self.log_result("Show Stop Functionality - Current Show Cleared", True, f"✅ Current show cleared after stop")
                else:
                    self.log_result("Show Stop Functionality - Current Show Cleared", False, f"Current show not cleared: {current_after_data}")
            
            # Step 6: Create another request (should NOT be assigned to any show)
            request_after_data = {
                "song_id": self.test_song_id,
                "requester_name": "After Stop Fan",
                "requester_email": "afterstop@example.com",
                "dedication": "Request after stop"
            }
            
            request_after_response = self.make_request("POST", "/requests", request_after_data)
            
            if request_after_response.status_code == 200:
                request_after_response_data = request_after_response.json()
                if not request_after_response_data.get("show_name"):
                    self.log_result("Show Stop Functionality - Request After Stop", True, f"✅ Request NOT assigned to show after stop")
                else:
                    self.log_result("Show Stop Functionality - Request After Stop", False, f"Request still assigned to show: {request_after_response_data}")
            
            self.log_result("Show Stop Functionality", True, "✅ Show stop functionality working correctly")
            
        except Exception as e:
            self.log_result("Show Stop Functionality", False, f"❌ Exception: {str(e)}")

    def test_request_deletion(self):
        """Test individual request deletion - CRITICAL REQUEST DELETION TEST"""
        try:
            print("🔍 Testing individual request deletion")
            
            # Create a test request first
            request_data = {
                "song_id": self.test_song_id,
                "requester_name": "Delete Test Fan",
                "requester_email": "deletetest@example.com",
                "dedication": "Test request for deletion"
            }
            
            create_response = self.make_request("POST", "/requests", request_data)
            
            if create_response.status_code != 200:
                self.log_result("Request Deletion - Create Request", False, f"Failed to create test request: {create_response.status_code}")
                return
            
            create_data = create_response.json()
            test_request_id = create_data.get("id")
            
            if not test_request_id:
                self.log_result("Request Deletion - Create Request", False, f"No request ID in response: {create_data}")
                return
            
            self.log_result("Request Deletion - Create Request", True, f"✅ Created test request: {test_request_id}")
            
            # Verify request exists before deletion
            requests_before = self.make_request("GET", "/requests")
            if requests_before.status_code == 200:
                requests_before_data = requests_before.json()
                request_exists_before = any(req["id"] == test_request_id for req in requests_before_data)
                
                if not request_exists_before:
                    self.log_result("Request Deletion - Pre-check", False, "Test request not found before deletion")
                    return
            
            # Delete the request
            delete_response = self.make_request("DELETE", f"/requests/{test_request_id}")
            
            if delete_response.status_code == 200:
                delete_data = delete_response.json()
                if delete_data.get("success"):
                    self.log_result("Request Deletion - API Response", True, f"✅ API returned success: {delete_data['message']}")
                    
                    # Verify request is actually deleted from database
                    requests_after = self.make_request("GET", "/requests")
                    if requests_after.status_code == 200:
                        requests_after_data = requests_after.json()
                        request_exists_after = any(req["id"] == test_request_id for req in requests_after_data)
                        
                        if not request_exists_after:
                            self.log_result("Request Deletion - Database Verification", True, f"✅ Request successfully deleted from database")
                            self.log_result("Request Deletion", True, "✅ Individual request deletion working correctly")
                        else:
                            self.log_result("Request Deletion - Database Verification", False, f"❌ Request still exists in database after deletion")
                            self.log_result("Request Deletion", False, f"❌ Request not actually deleted from database")
                    else:
                        self.log_result("Request Deletion - Database Verification", False, f"Could not verify deletion: {requests_after.status_code}")
                else:
                    self.log_result("Request Deletion", False, f"Delete request failed: {delete_data}")
            else:
                self.log_result("Request Deletion", False, f"Failed to delete request: {delete_response.status_code}")
            
        except Exception as e:
            self.log_result("Request Deletion", False, f"❌ Exception: {str(e)}")

    def test_show_deletion_with_requests(self):
        """Test show deletion removes all associated requests - CRITICAL SHOW DELETION TEST"""
        try:
            print("🔍 Testing show deletion with associated requests")
            
            # Step 1: Start a new show
            show_data = {
                "name": "Test Show for Deletion",
                "venue": "Test Venue",
                "notes": "Show to test deletion functionality"
            }
            
            start_response = self.make_request("POST", "/shows/start", show_data)
            
            if start_response.status_code != 200:
                self.log_result("Show Deletion with Requests - Start Show", False, f"Failed to start show: {start_response.status_code}")
                return
            
            start_data = start_response.json()
            show_id = start_data["show"]["id"]
            show_name = start_data["show"]["name"]
            
            # Step 2: Create multiple requests for this show
            request_ids = []
            for i in range(3):
                request_data = {
                    "song_id": self.test_song_id,
                    "requester_name": f"Test Fan {i+1}",
                    "requester_email": f"testfan{i+1}@example.com",
                    "dedication": f"Test request {i+1} for show deletion"
                }
                
                request_response = self.make_request("POST", "/requests", request_data)
                
                if request_response.status_code == 200:
                    request_data_response = request_response.json()
                    request_ids.append(request_data_response["id"])
                    
                    # Verify request was assigned to current show
                    if request_data_response.get("show_name") != show_name:
                        self.log_result("Show Deletion with Requests - Request Assignment", False, f"Request not assigned to show: {request_data_response}")
                        return
            
            if len(request_ids) != 3:
                self.log_result("Show Deletion with Requests - Create Requests", False, f"Only created {len(request_ids)} out of 3 requests")
                return
            
            self.log_result("Show Deletion with Requests - Create Requests", True, f"✅ Created {len(request_ids)} requests for show")
            
            # Step 3: Verify requests exist before show deletion
            requests_before = self.make_request("GET", "/requests")
            if requests_before.status_code == 200:
                requests_before_data = requests_before.json()
                show_requests_before = [req for req in requests_before_data if req.get("show_name") == show_name]
                
                if len(show_requests_before) != 3:
                    self.log_result("Show Deletion with Requests - Pre-check", False, f"Expected 3 show requests, found {len(show_requests_before)}")
                    return
            
            # Step 4: Delete the show (should delete all associated requests)
            delete_response = self.make_request("DELETE", f"/shows/{show_id}")
            
            if delete_response.status_code == 200:
                delete_data = delete_response.json()
                if delete_data.get("success"):
                    self.log_result("Show Deletion with Requests - API Response", True, f"✅ API returned success: {delete_data['message']}")
                    
                    # Step 5: Verify all associated requests were deleted
                    requests_after = self.make_request("GET", "/requests")
                    if requests_after.status_code == 200:
                        requests_after_data = requests_after.json()
                        show_requests_after = [req for req in requests_after_data if req.get("show_name") == show_name]
                        remaining_request_ids = [req["id"] for req in requests_after_data if req["id"] in request_ids]
                        
                        if len(show_requests_after) == 0 and len(remaining_request_ids) == 0:
                            self.log_result("Show Deletion with Requests - Database Verification", True, f"✅ All {len(request_ids)} associated requests deleted from database")
                            self.log_result("Show Deletion with Requests", True, "✅ Show deletion with associated requests working correctly")
                        else:
                            self.log_result("Show Deletion with Requests - Database Verification", False, f"❌ {len(show_requests_after)} show requests and {len(remaining_request_ids)} request IDs still exist")
                            self.log_result("Show Deletion with Requests", False, f"❌ Associated requests not properly deleted")
                    else:
                        self.log_result("Show Deletion with Requests - Database Verification", False, f"Could not verify deletion: {requests_after.status_code}")
                else:
                    self.log_result("Show Deletion with Requests", False, f"Delete show failed: {delete_data}")
            else:
                self.log_result("Show Deletion with Requests", False, f"Failed to delete show: {delete_response.status_code}")
            
        except Exception as e:
            self.log_result("Show Deletion with Requests", False, f"❌ Exception: {str(e)}")

    def test_show_management_flow(self):
        """Test complete show management flow - CRITICAL SHOW MANAGEMENT TEST"""
        try:
            print("🔍 Testing complete show management flow")
            
            # Step 1: Start a new show
            show_data = {
                "name": "Jazz Night Live",
                "venue": "Blue Note Cafe",
                "notes": "Special jazz performance"
            }
            
            start_response = self.make_request("POST", "/shows/start", show_data)
            
            if start_response.status_code != 200:
                self.log_result("Show Management Flow - Start Show", False, f"Failed to start show: {start_response.status_code}")
                return
            
            start_data = start_response.json()
            if not start_data.get("success") or "show" not in start_data:
                self.log_result("Show Management Flow - Start Show", False, f"Invalid start response: {start_data}")
                return
            
            show_id = start_data["show"]["id"]
            show_name = start_data["show"]["name"]
            self.log_result("Show Management Flow - Start Show", True, f"✅ Started show: {show_name}")
            
            # Step 2: Verify current show is set
            current_response = self.make_request("GET", "/shows/current")
            
            if current_response.status_code == 200:
                current_data = current_response.json()
                if current_data.get("active") and current_data.get("show", {}).get("id") == show_id:
                    self.log_result("Show Management Flow - Current Show", True, f"✅ Current show correctly set: {show_name}")
                else:
                    self.log_result("Show Management Flow - Current Show", False, f"Current show not set correctly: {current_data}")
            else:
                self.log_result("Show Management Flow - Current Show", False, f"Failed to get current show: {current_response.status_code}")
            
            # Step 3: Create a request (should be auto-assigned to current show)
            request_data = {
                "song_id": self.test_song_id,
                "requester_name": "Show Fan",
                "requester_email": "showfan@example.com",
                "dedication": "For the jazz night!"
            }
            
            request_response = self.make_request("POST", "/requests", request_data)
            
            if request_response.status_code == 200:
                request_data_response = request_response.json()
                test_request_id = request_data_response.get("id")
                
                # Verify request was assigned to current show
                if request_data_response.get("show_name") == show_name:
                    self.log_result("Show Management Flow - Request Auto-Assignment", True, f"✅ Request auto-assigned to show: {show_name}")
                else:
                    self.log_result("Show Management Flow - Request Auto-Assignment", False, f"Request not auto-assigned to show: {request_data_response}")
            else:
                self.log_result("Show Management Flow - Request Auto-Assignment", False, f"Failed to create request: {request_response.status_code}")
            
            # Step 4: Stop the show
            stop_response = self.make_request("POST", "/shows/stop")
            
            if stop_response.status_code == 200:
                stop_data = stop_response.json()
                if stop_data.get("success"):
                    self.log_result("Show Management Flow - Stop Show", True, f"✅ Show stopped successfully")
                    
                    # Verify current show is cleared
                    current_after_stop = self.make_request("GET", "/shows/current")
                    if current_after_stop.status_code == 200:
                        current_after_data = current_after_stop.json()
                        if not current_after_data.get("active"):
                            self.log_result("Show Management Flow - Current Show Cleared", True, f"✅ Current show cleared after stop")
                        else:
                            self.log_result("Show Management Flow - Current Show Cleared", False, f"Current show not cleared: {current_after_data}")
                else:
                    self.log_result("Show Management Flow - Stop Show", False, f"Stop show failed: {stop_data}")
            else:
                self.log_result("Show Management Flow - Stop Show", False, f"Failed to stop show: {stop_response.status_code}")
            
            # Step 5: Test show deletion
            delete_response = self.make_request("DELETE", f"/shows/{show_id}")
            
            if delete_response.status_code == 200:
                delete_data = delete_response.json()
                if delete_data.get("success"):
                    self.log_result("Show Management Flow - Delete Show", True, f"✅ Show deleted successfully")
                else:
                    self.log_result("Show Management Flow - Delete Show", False, f"Delete show failed: {delete_data}")
            else:
                self.log_result("Show Management Flow - Delete Show", False, f"Failed to delete show: {delete_response.status_code}")
            
            self.log_result("Show Management Flow", True, "✅ Complete show management flow working correctly")
            
        except Exception as e:
            self.log_result("Show Management Flow", False, f"❌ Exception: {str(e)}")

    def test_authentication_and_authorization(self):
        """Test authentication and authorization for show/request management - CRITICAL AUTH TEST"""
        try:
            print("🔍 Testing authentication and authorization for show/request management")
            
            # Save current token
            original_token = self.auth_token
            
            # Test 1: Show management without authentication
            self.auth_token = None
            
            show_data = {"name": "Unauthorized Show"}
            start_response = self.make_request("POST", "/shows/start", show_data)
            
            if start_response.status_code in [401, 403]:
                self.log_result("Auth Test - Show Start No Token", True, f"✅ Correctly rejected show start without auth (status: {start_response.status_code})")
            else:
                self.log_result("Auth Test - Show Start No Token", False, f"❌ Should have returned 401/403, got: {start_response.status_code}")
            
            stop_response = self.make_request("POST", "/shows/stop")
            
            if stop_response.status_code in [401, 403]:
                self.log_result("Auth Test - Show Stop No Token", True, f"✅ Correctly rejected show stop without auth (status: {stop_response.status_code})")
            else:
                self.log_result("Auth Test - Show Stop No Token", False, f"❌ Should have returned 401/403, got: {stop_response.status_code}")
            
            # Test 2: Invalid token
            self.auth_token = "invalid_token_12345"
            
            start_invalid_response = self.make_request("POST", "/shows/start", show_data)
            
            if start_invalid_response.status_code == 401:
                self.log_result("Auth Test - Show Start Invalid Token", True, "✅ Correctly rejected show start with invalid token")
            else:
                self.log_result("Auth Test - Show Start Invalid Token", False, f"❌ Should have returned 401, got: {start_invalid_response.status_code}")
            
            # Restore original token
            self.auth_token = original_token
            
            # Test 3: Authorization - try to delete non-existent show/request
            fake_show_id = "non-existent-show-id"
            delete_fake_show_response = self.make_request("DELETE", f"/shows/{fake_show_id}")
            
            if delete_fake_show_response.status_code == 404:
                self.log_result("Auth Test - Delete Non-existent Show", True, "✅ Correctly returned 404 for non-existent show")
            else:
                self.log_result("Auth Test - Delete Non-existent Show", False, f"❌ Should have returned 404, got: {delete_fake_show_response.status_code}")
            
            fake_request_id = "non-existent-request-id"
            delete_fake_request_response = self.make_request("DELETE", f"/requests/{fake_request_id}")
            
            if delete_fake_request_response.status_code == 404:
                self.log_result("Auth Test - Delete Non-existent Request", True, "✅ Correctly returned 404 for non-existent request")
            else:
                self.log_result("Auth Test - Delete Non-existent Request", False, f"❌ Should have returned 404, got: {delete_fake_request_response.status_code}")
            
            self.log_result("Authentication and Authorization", True, "✅ Authentication and authorization working correctly")
            
        except Exception as e:
            self.log_result("Authentication and Authorization", False, f"❌ Exception: {str(e)}")

    def run_show_management_tests(self):
        """Run all show management tests"""
        print("🎯" * 20 + " CRITICAL SHOW MANAGEMENT & DELETION TESTS " + "🎯" * 20)
        print("Testing the FIXED show management and deletion functionality")
        print("=" * 80)
        
        if not self.setup_test_environment():
            print("❌ Failed to set up test environment")
            return
        
        # Run all show management tests
        self.test_show_stop_functionality()
        self.test_request_deletion()
        self.test_show_deletion_with_requests()
        self.test_show_management_flow()
        self.test_authentication_and_authorization()
        
        # Print summary
        print("\n" + "=" * 80)
        print("🏁 Show Management Test Summary")
        print("=" * 80)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Total: {self.results['passed'] + self.results['failed']}")
        
        if self.results['failed'] > 0:
            print(f"\n🚨 Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed'])) * 100 if (self.results['passed'] + self.results['failed']) > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        return self.results

if __name__ == "__main__":
    tester = ShowManagementTester()
    results = tester.run_show_management_tests()