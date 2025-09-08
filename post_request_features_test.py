#!/usr/bin/env python3
"""
Comprehensive Backend API Tests for RequestWave Post-Request Features
Tests the new post-request features as specified in the review request:
- Updated Request Model & Creation
- Click Tracking System  
- Show Management for Artists
- Request Management
- Updated Profile with Social Media
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://requestwave-revamp.preview.emergentagent.com/api"
TEST_MUSICIAN = {
    "name": "Post Request Tester",
    "email": "post.request.tester@requestwave.com", 
    "password": "SecurePassword123!"
}

class PostRequestFeaturesTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
        self.test_song_id = None
        self.test_request_id = None
        self.test_show_id = None
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
        """Setup test environment with authentication and test data"""
        print("🔧 Setting up test environment...")
        
        # Register or login musician
        try:
            response = self.make_request("POST", "/auth/register", TEST_MUSICIAN)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data["token"]
                self.musician_id = data["musician"]["id"]
                self.musician_slug = data["musician"]["slug"]
                print(f"✅ Registered new musician: {data['musician']['name']}")
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
                    print(f"✅ Logged in existing musician: {data['musician']['name']}")
                else:
                    print(f"❌ Failed to login: {response.status_code}")
                    return False
            else:
                print(f"❌ Failed to register: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Setup failed: {str(e)}")
            return False
        
        # Create a test song
        try:
            song_data = {
                "title": f"Test Song for Post-Request Features {int(time.time())}",
                "artist": "Test Artist",
                "genres": ["Pop"],
                "moods": ["Upbeat"],
                "year": 2024,
                "notes": "Test song for post-request feature testing"
            }
            
            response = self.make_request("POST", "/songs", song_data)
            
            if response.status_code == 200:
                data = response.json()
                self.test_song_id = data["id"]
                print(f"✅ Created test song: {data['title']} (ID: {self.test_song_id})")
            else:
                print(f"❌ Failed to create test song: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Failed to create test song: {str(e)}")
            return False
        
        return True

    # PRIORITY 1: Updated Request Model & Creation
    def test_updated_request_model_creation(self):
        """Test POST /requests endpoint with new simplified model (removed tip_amount)"""
        try:
            if not self.test_song_id:
                self.log_result("Updated Request Model Creation", False, "No test song ID available")
                return
            
            # Test new simplified request model without tip_amount
            request_data = {
                "song_id": self.test_song_id,
                "requester_name": "John Doe",
                "requester_email": "john.doe@example.com",
                "dedication": "Happy anniversary to my wife!"
            }
            
            print(f"🔍 Testing POST /requests with simplified model (no tip_amount)")
            response = self.make_request("POST", "/requests", request_data)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Request response: {json.dumps(data, indent=2)}")
                
                # Verify required fields are present
                required_fields = ["id", "musician_id", "song_id", "song_title", "song_artist", 
                                 "requester_name", "requester_email", "dedication", "status", "created_at"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.test_request_id = data["id"]
                    
                    # Verify initial values
                    if (data.get("tip_clicked") == False and 
                        data.get("social_clicks") == [] and
                        data.get("show_name") is None and
                        data.get("status") == "pending"):
                        
                        self.log_result("Updated Request Model Creation", True, 
                                      f"✅ Request created with correct initial values: tip_clicked=False, social_clicks=[], show_name=None, status=pending")
                    else:
                        self.log_result("Updated Request Model Creation", False, 
                                      f"❌ Incorrect initial values: tip_clicked={data.get('tip_clicked')}, social_clicks={data.get('social_clicks')}, show_name={data.get('show_name')}")
                else:
                    self.log_result("Updated Request Model Creation", False, f"❌ Missing required fields: {missing_fields}")
            else:
                self.log_result("Updated Request Model Creation", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Updated Request Model Creation", False, f"❌ Exception: {str(e)}")

    def test_request_datetime_tracking(self):
        """Test that requests are created with proper date/time tracking"""
        try:
            if not self.test_request_id:
                self.log_result("Request DateTime Tracking", False, "No test request ID available")
                return
            
            # Get the created request and verify datetime fields
            response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
            
            if response.status_code == 200:
                requests_data = response.json()
                test_request = next((req for req in requests_data if req["id"] == self.test_request_id), None)
                
                if test_request:
                    created_at = test_request.get("created_at")
                    
                    if created_at:
                        # Verify created_at is a valid ISO datetime string
                        from datetime import datetime
                        try:
                            parsed_datetime = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            self.log_result("Request DateTime Tracking", True, 
                                          f"✅ Request has valid created_at timestamp: {created_at}")
                        except ValueError:
                            self.log_result("Request DateTime Tracking", False, 
                                          f"❌ Invalid datetime format: {created_at}")
                    else:
                        self.log_result("Request DateTime Tracking", False, "❌ Missing created_at field")
                else:
                    self.log_result("Request DateTime Tracking", False, "❌ Test request not found")
            else:
                self.log_result("Request DateTime Tracking", False, f"❌ Status code: {response.status_code}")
        except Exception as e:
            self.log_result("Request DateTime Tracking", False, f"❌ Exception: {str(e)}")

    # PRIORITY 2: Click Tracking System
    def test_tip_click_tracking(self):
        """Test POST /requests/{request_id}/track-click for tip clicks"""
        try:
            if not self.test_request_id:
                self.log_result("Tip Click Tracking", False, "No test request ID available")
                return
            
            # Test tracking tip click for Venmo
            tip_click_data = {
                "type": "tip",
                "platform": "venmo"
            }
            
            print(f"🔍 Testing POST /requests/{self.test_request_id}/track-click for tip")
            response = self.make_request("POST", f"/requests/{self.test_request_id}/track-click", tip_click_data)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Tip click response: {json.dumps(data, indent=2)}")
                
                # Verify the request was updated
                verify_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
                if verify_response.status_code == 200:
                    requests_data = verify_response.json()
                    updated_request = next((req for req in requests_data if req["id"] == self.test_request_id), None)
                    
                    if updated_request and updated_request.get("tip_clicked") == True:
                        self.log_result("Tip Click Tracking", True, "✅ Tip click successfully tracked, tip_clicked=True")
                    else:
                        self.log_result("Tip Click Tracking", False, f"❌ tip_clicked not updated: {updated_request.get('tip_clicked') if updated_request else 'request not found'}")
                else:
                    self.log_result("Tip Click Tracking", False, "❌ Could not verify tip click update")
            else:
                self.log_result("Tip Click Tracking", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
                
            # Test tracking tip click for PayPal
            tip_click_paypal = {
                "type": "tip", 
                "platform": "paypal"
            }
            
            response = self.make_request("POST", f"/requests/{self.test_request_id}/track-click", tip_click_paypal)
            
            if response.status_code == 200:
                self.log_result("Tip Click Tracking - PayPal", True, "✅ PayPal tip click tracking works")
            else:
                self.log_result("Tip Click Tracking - PayPal", False, f"❌ PayPal tip click failed: {response.status_code}")
                
        except Exception as e:
            self.log_result("Tip Click Tracking", False, f"❌ Exception: {str(e)}")

    def test_social_click_tracking(self):
        """Test POST /requests/{request_id}/track-click for social clicks"""
        try:
            if not self.test_request_id:
                self.log_result("Social Click Tracking", False, "No test request ID available")
                return
            
            # Test tracking social clicks for different platforms
            social_platforms = ["instagram", "facebook", "tiktok", "spotify", "apple_music"]
            
            for platform in social_platforms:
                social_click_data = {
                    "type": "social",
                    "platform": platform
                }
                
                print(f"🔍 Testing social click tracking for {platform}")
                response = self.make_request("POST", f"/requests/{self.test_request_id}/track-click", social_click_data)
                
                if response.status_code == 200:
                    self.log_result(f"Social Click Tracking - {platform.title()}", True, f"✅ {platform} social click tracked")
                else:
                    self.log_result(f"Social Click Tracking - {platform.title()}", False, f"❌ {platform} social click failed: {response.status_code}")
            
            # Verify all social clicks were recorded
            verify_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
            if verify_response.status_code == 200:
                requests_data = verify_response.json()
                updated_request = next((req for req in requests_data if req["id"] == self.test_request_id), None)
                
                if updated_request:
                    social_clicks = updated_request.get("social_clicks", [])
                    print(f"📊 Social clicks recorded: {social_clicks}")
                    
                    if len(social_clicks) == len(social_platforms):
                        self.log_result("Social Click Tracking - Verification", True, 
                                      f"✅ All {len(social_platforms)} social clicks recorded: {social_clicks}")
                    else:
                        self.log_result("Social Click Tracking - Verification", False, 
                                      f"❌ Expected {len(social_platforms)} social clicks, got {len(social_clicks)}: {social_clicks}")
                else:
                    self.log_result("Social Click Tracking - Verification", False, "❌ Request not found for verification")
            else:
                self.log_result("Social Click Tracking - Verification", False, "❌ Could not verify social clicks")
                
        except Exception as e:
            self.log_result("Social Click Tracking", False, f"❌ Exception: {str(e)}")

    # PRIORITY 3: Show Management for Artists
    def test_create_show(self):
        """Test POST /shows endpoint to create shows"""
        try:
            show_data = {
                "name": "Test Concert",
                "date": "2024-12-31",
                "venue": "Test Venue",
                "notes": "New Year's Eve concert"
            }
            
            print(f"🔍 Testing POST /shows")
            response = self.make_request("POST", "/shows", show_data)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Show creation response: {json.dumps(data, indent=2)}")
                
                required_fields = ["id", "musician_id", "name", "date", "venue", "notes", "created_at"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.test_show_id = data["id"]
                    self.log_result("Create Show", True, f"✅ Show created successfully: {data['name']}")
                else:
                    self.log_result("Create Show", False, f"❌ Missing fields: {missing_fields}")
            else:
                self.log_result("Create Show", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Create Show", False, f"❌ Exception: {str(e)}")

    def test_get_shows(self):
        """Test GET /shows endpoint to list artist shows"""
        try:
            print(f"🔍 Testing GET /shows")
            response = self.make_request("GET", "/shows")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Shows list response: {json.dumps(data, indent=2)}")
                
                if isinstance(data, list):
                    if len(data) > 0:
                        # Verify show structure
                        show = data[0]
                        required_fields = ["id", "musician_id", "name", "created_at"]
                        missing_fields = [field for field in required_fields if field not in show]
                        
                        if not missing_fields:
                            self.log_result("Get Shows", True, f"✅ Retrieved {len(data)} shows with correct structure")
                        else:
                            self.log_result("Get Shows", False, f"❌ Show missing fields: {missing_fields}")
                    else:
                        self.log_result("Get Shows", True, "✅ Shows endpoint works (empty list)")
                else:
                    self.log_result("Get Shows", False, f"❌ Expected list, got: {type(data)}")
            else:
                self.log_result("Get Shows", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Get Shows", False, f"❌ Exception: {str(e)}")

    def test_assign_request_to_show(self):
        """Test PUT /requests/{request_id}/assign-show to assign requests to shows"""
        try:
            if not self.test_request_id or not self.test_show_id:
                self.log_result("Assign Request to Show", False, "Missing test request ID or show ID")
                return
            
            assign_data = {
                "show_name": "Test Concert"
            }
            
            print(f"🔍 Testing PUT /requests/{self.test_request_id}/assign-show")
            response = self.make_request("PUT", f"/requests/{self.test_request_id}/assign-show", assign_data)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Assign show response: {json.dumps(data, indent=2)}")
                
                # Verify the request was assigned to the show
                verify_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
                if verify_response.status_code == 200:
                    requests_data = verify_response.json()
                    updated_request = next((req for req in requests_data if req["id"] == self.test_request_id), None)
                    
                    if updated_request and updated_request.get("show_name"):
                        self.log_result("Assign Request to Show", True, 
                                      f"✅ Request assigned to show: {updated_request.get('show_name')}")
                    else:
                        self.log_result("Assign Request to Show", False, 
                                      f"❌ show_name not updated: {updated_request.get('show_name') if updated_request else 'request not found'}")
                else:
                    self.log_result("Assign Request to Show", False, "❌ Could not verify show assignment")
            else:
                self.log_result("Assign Request to Show", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Assign Request to Show", False, f"❌ Exception: {str(e)}")

    def test_get_requests_grouped_by_show(self):
        """Test GET /requests/grouped to get requests grouped by show and date"""
        try:
            print(f"🔍 Testing GET /requests/grouped")
            response = self.make_request("GET", "/requests/grouped")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Grouped requests response: {json.dumps(data, indent=2)}")
                
                # Verify the response structure
                if isinstance(data, dict):
                    # Should have groups like "unassigned", show names, or date groups
                    if len(data) > 0:
                        self.log_result("Get Requests Grouped by Show", True, 
                                      f"✅ Requests grouped successfully: {list(data.keys())}")
                    else:
                        self.log_result("Get Requests Grouped by Show", True, "✅ Grouped requests endpoint works (empty groups)")
                else:
                    self.log_result("Get Requests Grouped by Show", False, f"❌ Expected dict, got: {type(data)}")
            else:
                self.log_result("Get Requests Grouped by Show", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Get Requests Grouped by Show", False, f"❌ Exception: {str(e)}")

    # PRIORITY 4: Request Management
    def test_archive_request(self):
        """Test PUT /requests/{request_id}/archive to archive requests"""
        try:
            if not self.test_request_id:
                self.log_result("Archive Request", False, "No test request ID available")
                return
            
            print(f"🔍 Testing PUT /requests/{self.test_request_id}/archive")
            response = self.make_request("PUT", f"/requests/{self.test_request_id}/archive")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Archive response: {json.dumps(data, indent=2)}")
                
                # Verify the request status was updated to archived
                verify_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
                if verify_response.status_code == 200:
                    requests_data = verify_response.json()
                    archived_request = next((req for req in requests_data if req["id"] == self.test_request_id), None)
                    
                    if archived_request and archived_request.get("status") == "archived":
                        self.log_result("Archive Request", True, "✅ Request successfully archived")
                    else:
                        self.log_result("Archive Request", False, 
                                      f"❌ Request status not updated to archived: {archived_request.get('status') if archived_request else 'request not found'}")
                else:
                    self.log_result("Archive Request", False, "❌ Could not verify archive status")
            else:
                self.log_result("Archive Request", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Archive Request", False, f"❌ Exception: {str(e)}")

    def test_delete_request(self):
        """Test DELETE /requests/{request_id} to delete requests"""
        try:
            # Create a new request for deletion test
            if not self.test_song_id:
                self.log_result("Delete Request", False, "No test song ID available")
                return
            
            request_data = {
                "song_id": self.test_song_id,
                "requester_name": "Delete Test User",
                "requester_email": "delete.test@example.com",
                "dedication": "This request will be deleted"
            }
            
            create_response = self.make_request("POST", "/requests", request_data)
            if create_response.status_code != 200:
                self.log_result("Delete Request", False, "Could not create request for deletion test")
                return
            
            delete_request_id = create_response.json()["id"]
            
            print(f"🔍 Testing DELETE /requests/{delete_request_id}")
            response = self.make_request("DELETE", f"/requests/{delete_request_id}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Delete response: {json.dumps(data, indent=2)}")
                
                # Verify the request was actually deleted
                verify_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
                if verify_response.status_code == 200:
                    requests_data = verify_response.json()
                    deleted_request = next((req for req in requests_data if req["id"] == delete_request_id), None)
                    
                    if deleted_request is None:
                        self.log_result("Delete Request", True, "✅ Request successfully deleted")
                    else:
                        self.log_result("Delete Request", False, "❌ Request still exists after deletion")
                else:
                    self.log_result("Delete Request", False, "❌ Could not verify deletion")
            else:
                self.log_result("Delete Request", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Delete Request", False, f"❌ Exception: {str(e)}")

    def test_bulk_request_actions(self):
        """Test POST /requests/bulk-action for bulk operations"""
        try:
            # Create multiple requests for bulk testing
            if not self.test_song_id:
                self.log_result("Bulk Request Actions", False, "No test song ID available")
                return
            
            bulk_request_ids = []
            for i in range(3):
                request_data = {
                    "song_id": self.test_song_id,
                    "requester_name": f"Bulk Test User {i+1}",
                    "requester_email": f"bulk.test{i+1}@example.com",
                    "dedication": f"Bulk test request {i+1}"
                }
                
                response = self.make_request("POST", "/requests", request_data)
                if response.status_code == 200:
                    bulk_request_ids.append(response.json()["id"])
                else:
                    self.log_result("Bulk Request Actions", False, f"Could not create bulk test request {i+1}")
                    return
            
            # Test bulk status update
            bulk_data = {
                "request_ids": bulk_request_ids,
                "action": "archive"
            }
            
            print(f"🔍 Testing POST /requests/bulk-action")
            response = self.make_request("POST", "/requests/bulk-action", bulk_data)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Bulk action response: {json.dumps(data, indent=2)}")
                
                # Verify all requests were updated
                verify_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
                if verify_response.status_code == 200:
                    requests_data = verify_response.json()
                    updated_requests = [req for req in requests_data if req["id"] in bulk_request_ids]
                    
                    if len(updated_requests) == len(bulk_request_ids):
                        all_archived = all(req.get("status") == "archived" for req in updated_requests)
                        if all_archived:
                            self.log_result("Bulk Request Actions", True, f"✅ Bulk archive successful for {len(bulk_request_ids)} requests")
                        else:
                            self.log_result("Bulk Request Actions", False, "❌ Not all requests updated to archived status")
                    else:
                        self.log_result("Bulk Request Actions", False, f"❌ Could not find all updated requests: {len(updated_requests)}/{len(bulk_request_ids)}")
                else:
                    self.log_result("Bulk Request Actions", False, "❌ Could not verify bulk update")
            else:
                self.log_result("Bulk Request Actions", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Bulk Request Actions", False, f"❌ Exception: {str(e)}")

    def test_request_status_updates(self):
        """Test status updates (pending, accepted, played, rejected, archived)"""
        try:
            # Create a request for status testing
            if not self.test_song_id:
                self.log_result("Request Status Updates", False, "No test song ID available")
                return
            
            request_data = {
                "song_id": self.test_song_id,
                "requester_name": "Status Test User",
                "requester_email": "status.test@example.com",
                "dedication": "Testing status updates"
            }
            
            create_response = self.make_request("POST", "/requests", request_data)
            if create_response.status_code != 200:
                self.log_result("Request Status Updates", False, "Could not create request for status testing")
                return
            
            status_request_id = create_response.json()["id"]
            
            # Test different status updates (excluding archived which has its own endpoint)
            statuses = ["accepted", "played", "rejected"]
            
            for status in statuses:
                print(f"🔍 Testing status update to: {status}")
                response = self.make_request("PUT", f"/requests/{status_request_id}/status?status={status}")
                
                if response.status_code == 200:
                    # Verify status was updated
                    verify_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
                    if verify_response.status_code == 200:
                        requests_data = verify_response.json()
                        updated_request = next((req for req in requests_data if req["id"] == status_request_id), None)
                        
                        if updated_request and updated_request.get("status") == status:
                            self.log_result(f"Request Status Update - {status.title()}", True, f"✅ Status updated to {status}")
                        else:
                            self.log_result(f"Request Status Update - {status.title()}", False, 
                                          f"❌ Status not updated to {status}: {updated_request.get('status') if updated_request else 'request not found'}")
                    else:
                        self.log_result(f"Request Status Update - {status.title()}", False, "❌ Could not verify status update")
                else:
                    self.log_result(f"Request Status Update - {status.title()}", False, f"❌ Status code: {response.status_code}")
                    
        except Exception as e:
            self.log_result("Request Status Updates", False, f"❌ Exception: {str(e)}")

    # PRIORITY 5: Updated Profile with Social Media
    def test_profile_social_media_fields(self):
        """Test GET /profile includes new social media fields"""
        try:
            print(f"🔍 Testing GET /profile for social media fields")
            response = self.make_request("GET", "/profile")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Profile response: {json.dumps(data, indent=2)}")
                
                # Check for new social media fields
                social_media_fields = [
                    "instagram_username", "facebook_username", "tiktok_username", 
                    "spotify_artist_url", "apple_music_artist_url"
                ]
                
                missing_fields = [field for field in social_media_fields if field not in data]
                
                if not missing_fields:
                    self.log_result("Profile Social Media Fields", True, 
                                  f"✅ All social media fields present: {social_media_fields}")
                else:
                    self.log_result("Profile Social Media Fields", False, 
                                  f"❌ Missing social media fields: {missing_fields}")
            else:
                self.log_result("Profile Social Media Fields", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Profile Social Media Fields", False, f"❌ Exception: {str(e)}")

    def test_profile_social_media_updates(self):
        """Test PUT /profile updates social media usernames and URLs properly"""
        try:
            # Test updating social media fields with @ symbols (should be cleaned)
            profile_update = {
                "instagram_username": "@testmusician",
                "facebook_username": "testmusician",
                "tiktok_username": "@testmusician_tiktok",
                "spotify_artist_url": "https://open.spotify.com/artist/testmusician",
                "apple_music_artist_url": "https://music.apple.com/artist/testmusician"
            }
            
            print(f"🔍 Testing PUT /profile with social media updates")
            response = self.make_request("PUT", "/profile", profile_update)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Profile update response: {json.dumps(data, indent=2)}")
                
                # Verify @ symbols were removed from usernames
                if (data.get("instagram_username") == "testmusician" and
                    data.get("facebook_username") == "testmusician" and
                    data.get("tiktok_username") == "testmusician_tiktok" and
                    data.get("spotify_artist_url") == "https://open.spotify.com/artist/testmusician" and
                    data.get("apple_music_artist_url") == "https://music.apple.com/artist/testmusician"):
                    
                    self.log_result("Profile Social Media Updates", True, 
                                  "✅ Social media fields updated correctly, @ symbols removed from usernames")
                else:
                    self.log_result("Profile Social Media Updates", False, 
                                  f"❌ Social media fields not updated correctly: instagram={data.get('instagram_username')}, tiktok={data.get('tiktok_username')}")
            else:
                self.log_result("Profile Social Media Updates", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Profile Social Media Updates", False, f"❌ Exception: {str(e)}")

    def test_profile_username_cleaning(self):
        """Test that username cleaning (removing @ symbols) works properly"""
        try:
            # Test with various @ symbol patterns
            test_cases = [
                {"input": "@username", "expected": "username"},
                {"input": "username", "expected": "username"},
                {"input": "@user@name", "expected": "user@name"},  # Only first @ should be removed
                {"input": "", "expected": ""}
            ]
            
            for i, test_case in enumerate(test_cases):
                profile_update = {
                    "instagram_username": test_case["input"]
                }
                
                response = self.make_request("PUT", "/profile", profile_update)
                
                if response.status_code == 200:
                    data = response.json()
                    actual = data.get("instagram_username", "")
                    
                    if actual == test_case["expected"]:
                        self.log_result(f"Username Cleaning Test {i+1}", True, 
                                      f"✅ '{test_case['input']}' → '{actual}'")
                    else:
                        self.log_result(f"Username Cleaning Test {i+1}", False, 
                                      f"❌ '{test_case['input']}' → '{actual}', expected '{test_case['expected']}'")
                else:
                    self.log_result(f"Username Cleaning Test {i+1}", False, f"❌ Status code: {response.status_code}")
                    
        except Exception as e:
            self.log_result("Profile Username Cleaning", False, f"❌ Exception: {str(e)}")

    def run_all_tests(self):
        """Run all post-request feature tests"""
        print("🚀 Starting Post-Request Features Testing...")
        print("=" * 60)
        
        # Setup
        if not self.setup_test_environment():
            print("❌ Failed to setup test environment")
            return
        
        print("\n" + "=" * 60)
        print("🎯 PRIORITY 1: Updated Request Model & Creation")
        print("=" * 60)
        self.test_updated_request_model_creation()
        self.test_request_datetime_tracking()
        
        print("\n" + "=" * 60)
        print("🎯 PRIORITY 2: Click Tracking System")
        print("=" * 60)
        self.test_tip_click_tracking()
        self.test_social_click_tracking()
        
        print("\n" + "=" * 60)
        print("🎯 PRIORITY 3: Show Management for Artists")
        print("=" * 60)
        self.test_create_show()
        self.test_get_shows()
        self.test_assign_request_to_show()
        self.test_get_requests_grouped_by_show()
        
        print("\n" + "=" * 60)
        print("🎯 PRIORITY 4: Request Management")
        print("=" * 60)
        self.test_archive_request()
        self.test_delete_request()
        self.test_bulk_request_actions()
        self.test_request_status_updates()
        
        print("\n" + "=" * 60)
        print("🎯 PRIORITY 5: Updated Profile with Social Media")
        print("=" * 60)
        self.test_profile_social_media_fields()
        self.test_profile_social_media_updates()
        self.test_profile_username_cleaning()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 POST-REQUEST FEATURES TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📈 Success Rate: {(self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100):.1f}%")
        
        if self.results['errors']:
            print(f"\n❌ Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        return self.results

if __name__ == "__main__":
    tester = PostRequestFeaturesTester()
    results = tester.run_all_tests()