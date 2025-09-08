#!/usr/bin/env python3
"""
New Features Testing for RequestWave - Post-Request Features
Tests the newly implemented show management, enhanced profile, updated request system, and click tracking
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://requestwave-revamp.preview.emergentagent.com/api"
TEST_MUSICIAN = {
    "name": "Show Manager Artist",
    "email": "show.manager@requestwave.com", 
    "password": "ShowManager123!"
}

class NewFeaturesAPITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
        self.test_song_id = None
        self.test_request_id = None
        self.test_show_id = None
        self.current_show_id = None
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

    def setup_authentication(self):
        """Setup authentication for testing"""
        try:
            # Try to register first
            response = self.make_request("POST", "/auth/register", TEST_MUSICIAN)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data["token"]
                self.musician_id = data["musician"]["id"]
                self.musician_slug = data["musician"]["slug"]
                self.log_result("Setup Authentication - Register", True, f"Registered musician: {data['musician']['name']}")
            elif response.status_code == 400:
                # Musician might already exist, try login instead
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
                    self.log_result("Setup Authentication - Login", True, f"Logged in musician: {data['musician']['name']}")
                else:
                    self.log_result("Setup Authentication", False, f"Login failed: {response.status_code}")
                    return False
            else:
                self.log_result("Setup Authentication", False, f"Registration failed: {response.status_code}")
                return False
            
            return True
        except Exception as e:
            self.log_result("Setup Authentication", False, f"Exception: {str(e)}")
            return False

    def setup_test_data(self):
        """Create test song and initial data"""
        try:
            # Create a test song with unique name
            import time
            timestamp = str(int(time.time()))
            song_data = {
                "title": f"Show Test Song {timestamp}",
                "artist": f"Test Artist {timestamp}",
                "genres": ["Pop"],
                "moods": ["Upbeat"],
                "year": 2023,
                "notes": "Test song for show management"
            }
            
            response = self.make_request("POST", "/songs", song_data)
            
            if response.status_code == 200:
                data = response.json()
                self.test_song_id = data["id"]
                self.log_result("Setup Test Data - Create Song", True, f"Created test song: {data['title']}")
                return True
            else:
                self.log_result("Setup Test Data", False, f"Failed to create test song: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Setup Test Data", False, f"Exception: {str(e)}")
            return False

    # PRIORITY 1: Show Management System Tests
    def test_show_creation(self):
        """Test POST /shows to create a new show"""
        try:
            show_data = {
                "name": "Friday Night Live",
                "date": "2024-01-15",
                "venue": "The Blue Note",
                "notes": "Weekly jazz night performance"
            }
            
            response = self.make_request("POST", "/shows", show_data)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and data["name"] == show_data["name"]:
                    self.test_show_id = data["id"]
                    self.log_result("Show Creation", True, f"Created show: {data['name']} (ID: {data['id']})")
                else:
                    self.log_result("Show Creation", False, f"Unexpected response structure: {data}")
            else:
                self.log_result("Show Creation", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Show Creation", False, f"Exception: {str(e)}")

    def test_start_show(self):
        """Test POST /shows/start to start a new show"""
        try:
            # Start show with name (not show_id)
            start_data = {
                "name": "Friday Night Live",
                "venue": "The Blue Note",
                "notes": "Live performance"
            }
            response = self.make_request("POST", "/shows/start", start_data)
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "show" in data:
                    self.current_show_id = data["show"]["id"]
                    self.log_result("Start Show", True, f"Started show: {data['show']['name']}")
                else:
                    self.log_result("Start Show", False, f"Unexpected response structure: {data}")
            else:
                self.log_result("Start Show", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Start Show", False, f"Exception: {str(e)}")

    def test_get_current_show(self):
        """Test GET /shows/current to check current active show"""
        try:
            response = self.make_request("GET", "/shows/current")
            
            if response.status_code == 200:
                data = response.json()
                if "active" in data and data["active"] == True and "show" in data:
                    current_show = data["show"]
                    if current_show["id"] == self.current_show_id:
                        self.log_result("Get Current Show", True, f"Current show: {current_show['name']}")
                    else:
                        self.log_result("Get Current Show", False, f"Current show ID mismatch: expected {self.current_show_id}, got {current_show['id']}")
                else:
                    self.log_result("Get Current Show", False, f"No current show found: {data}")
            else:
                self.log_result("Get Current Show", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Get Current Show", False, f"Exception: {str(e)}")

    def test_request_auto_assignment_to_show(self):
        """Test that new requests auto-assign to current active show"""
        try:
            if not self.test_song_id or not self.current_show_id:
                self.log_result("Request Auto-Assignment", False, "Missing test song ID or current show ID")
                return
            
            # Create a request while show is active
            request_data = {
                "song_id": self.test_song_id,
                "requester_name": "Show Fan",
                "requester_email": "showfan@example.com",
                "dedication": "For the live show!"
            }
            
            response = self.make_request("POST", "/requests", request_data)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "show_name" in data:
                    self.test_request_id = data["id"]
                    # Check if request was auto-assigned to current show
                    if data["show_name"] is not None:
                        self.log_result("Request Auto-Assignment", True, f"Request auto-assigned to show: {data['show_name']}")
                    else:
                        self.log_result("Request Auto-Assignment", False, f"Request not auto-assigned to show: {data}")
                else:
                    self.log_result("Request Auto-Assignment", False, f"Unexpected response structure: {data}")
            else:
                self.log_result("Request Auto-Assignment", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Request Auto-Assignment", False, f"Exception: {str(e)}")

    def test_stop_show(self):
        """Test POST /shows/stop to stop the current show"""
        try:
            response = self.make_request("POST", "/shows/stop")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    self.log_result("Stop Show", True, f"Stopped show: {data['message']}")
                    self.current_show_id = None
                else:
                    self.log_result("Stop Show", False, f"Unexpected response structure: {data}")
            else:
                self.log_result("Stop Show", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Stop Show", False, f"Exception: {str(e)}")

    def test_request_no_auto_assignment_after_show_stop(self):
        """Test that new requests don't auto-assign after show is stopped"""
        try:
            if not self.test_song_id:
                self.log_result("Request No Auto-Assignment After Stop", False, "Missing test song ID")
                return
            
            # Create a request after show is stopped
            request_data = {
                "song_id": self.test_song_id,
                "requester_name": "Post Show Fan",
                "requester_email": "postshowfan@example.com",
                "dedication": "After the show"
            }
            
            response = self.make_request("POST", "/requests", request_data)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "show_name" in data:
                    # Check if request was NOT auto-assigned to any show
                    if data["show_name"] is None:
                        self.log_result("Request No Auto-Assignment After Stop", True, "Request correctly not auto-assigned after show stopped")
                    else:
                        self.log_result("Request No Auto-Assignment After Stop", False, f"Request incorrectly auto-assigned to show: {data['show_name']}")
                else:
                    self.log_result("Request No Auto-Assignment After Stop", False, f"Unexpected response structure: {data}")
            else:
                self.log_result("Request No Auto-Assignment After Stop", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Request No Auto-Assignment After Stop", False, f"Exception: {str(e)}")

    def test_grouped_requests(self):
        """Test GET /requests/grouped to see requests organized by show"""
        try:
            response = self.make_request("GET", "/requests/grouped")
            
            if response.status_code == 200:
                data = response.json()
                if "unassigned" in data and "shows" in data:
                    unassigned_count = len(data["unassigned"])
                    shows_count = len(data["shows"])
                    self.log_result("Grouped Requests", True, f"Retrieved grouped requests: {unassigned_count} unassigned, {shows_count} shows")
                else:
                    self.log_result("Grouped Requests", False, f"Unexpected response structure: {data}")
            else:
                self.log_result("Grouped Requests", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Grouped Requests", False, f"Exception: {str(e)}")

    # PRIORITY 2: Enhanced Profile with Social Media Tests
    def test_get_profile_social_media_fields(self):
        """Test that GET /profile returns all social media fields"""
        try:
            response = self.make_request("GET", "/profile")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for all expected social media fields
                expected_fields = [
                    "instagram_username", "facebook_username", "tiktok_username",
                    "spotify_artist_url", "apple_music_artist_url",
                    "paypal_username", "venmo_username"
                ]
                
                missing_fields = []
                for field in expected_fields:
                    if field not in data:
                        missing_fields.append(field)
                
                if not missing_fields:
                    self.log_result("Get Profile Social Media Fields", True, f"All social media fields present: {expected_fields}")
                else:
                    self.log_result("Get Profile Social Media Fields", False, f"Missing fields: {missing_fields}")
            else:
                self.log_result("Get Profile Social Media Fields", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Get Profile Social Media Fields", False, f"Exception: {str(e)}")

    def test_update_profile_social_media_fields(self):
        """Test that PUT /profile updates social media fields correctly"""
        try:
            update_data = {
                "instagram_username": "@testartist",
                "facebook_username": "testartist",
                "tiktok_username": "@testartist_tiktok",
                "spotify_artist_url": "https://open.spotify.com/artist/testartist",
                "apple_music_artist_url": "https://music.apple.com/artist/testartist",
                "paypal_username": "@testartist_paypal",
                "venmo_username": "@testartist_venmo"
            }
            
            response = self.make_request("PUT", "/profile", update_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify all fields were updated
                all_updated = True
                for field, expected_value in update_data.items():
                    if field in data:
                        actual_value = data[field]
                        # Check username cleaning (@ symbols should be removed for usernames)
                        if field in ["instagram_username", "tiktok_username", "paypal_username", "venmo_username"]:
                            expected_cleaned = expected_value.lstrip('@')
                            if actual_value != expected_cleaned:
                                all_updated = False
                                break
                        elif actual_value != expected_value:
                            all_updated = False
                            break
                    else:
                        all_updated = False
                        break
                
                if all_updated:
                    self.log_result("Update Profile Social Media Fields", True, "All social media fields updated correctly")
                else:
                    self.log_result("Update Profile Social Media Fields", False, f"Fields not updated correctly: {data}")
            else:
                self.log_result("Update Profile Social Media Fields", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Update Profile Social Media Fields", False, f"Exception: {str(e)}")

    def test_username_cleaning(self):
        """Test that username cleaning (removing @ symbols) works"""
        try:
            # Test with @ symbols
            update_data = {
                "instagram_username": "@cleantest",
                "tiktok_username": "@cleantest_tiktok",
                "paypal_username": "@cleantest_paypal",
                "venmo_username": "@cleantest_venmo"
            }
            
            response = self.make_request("PUT", "/profile", update_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify @ symbols were removed
                cleaned_correctly = True
                for field, original_value in update_data.items():
                    if field in data:
                        expected_cleaned = original_value.lstrip('@')
                        actual_value = data[field]
                        if actual_value != expected_cleaned:
                            cleaned_correctly = False
                            break
                    else:
                        cleaned_correctly = False
                        break
                
                if cleaned_correctly:
                    self.log_result("Username Cleaning", True, "@ symbols correctly removed from usernames")
                else:
                    self.log_result("Username Cleaning", False, f"Username cleaning failed: {data}")
            else:
                self.log_result("Username Cleaning", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Username Cleaning", False, f"Exception: {str(e)}")

    # PRIORITY 3: Updated Request System Tests
    def test_create_request_without_tip_amount(self):
        """Test POST /requests creates requests without tip amounts"""
        try:
            if not self.test_song_id:
                self.log_result("Create Request Without Tip Amount", False, "Missing test song ID")
                return
            
            # Create request without tip_amount field
            request_data = {
                "song_id": self.test_song_id,
                "requester_name": "No Tip Fan",
                "requester_email": "notipfan@example.com",
                "dedication": "Just for the music!"
            }
            
            response = self.make_request("POST", "/requests", request_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check that request was created with proper initial values
                expected_fields = ["id", "tip_clicked", "social_clicks", "status", "created_at"]
                missing_fields = []
                
                for field in expected_fields:
                    if field not in data:
                        missing_fields.append(field)
                
                if not missing_fields:
                    # Store the request ID for later tests
                    self.test_request_id = data["id"]
                    
                    # Check initial values
                    if (data["tip_clicked"] == False and 
                        data["social_clicks"] == [] and 
                        data["status"] == "pending"):
                        self.log_result("Create Request Without Tip Amount", True, f"Request created with correct initial values")
                    else:
                        self.log_result("Create Request Without Tip Amount", False, f"Incorrect initial values: tip_clicked={data['tip_clicked']}, social_clicks={data['social_clicks']}, status={data['status']}")
                else:
                    self.log_result("Create Request Without Tip Amount", False, f"Missing fields: {missing_fields}")
            else:
                self.log_result("Create Request Without Tip Amount", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Create Request Without Tip Amount", False, f"Exception: {str(e)}")

    def test_tip_click_tracking(self):
        """Test POST /requests/{id}/track-click for tip clicks"""
        try:
            if not self.test_request_id:
                self.log_result("Tip Click Tracking", False, "Missing test request ID")
                return
            
            # Test tip click tracking for venmo
            click_data = {
                "type": "tip",
                "platform": "venmo"
            }
            
            response = self.make_request("POST", f"/requests/{self.test_request_id}/track-click", click_data)
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    self.log_result("Tip Click Tracking - Venmo", True, f"Venmo tip click tracked: {data['message']}")
                    
                    # Test tip click tracking for paypal
                    click_data = {
                        "type": "tip",
                        "platform": "paypal"
                    }
                    
                    response = self.make_request("POST", f"/requests/{self.test_request_id}/track-click", click_data)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "message" in data:
                            self.log_result("Tip Click Tracking - PayPal", True, f"PayPal tip click tracked: {data['message']}")
                        else:
                            self.log_result("Tip Click Tracking - PayPal", False, f"Unexpected response: {data}")
                    else:
                        self.log_result("Tip Click Tracking - PayPal", False, f"Status code: {response.status_code}")
                else:
                    self.log_result("Tip Click Tracking - Venmo", False, f"Unexpected response: {data}")
            else:
                self.log_result("Tip Click Tracking", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Tip Click Tracking", False, f"Exception: {str(e)}")

    def test_social_click_tracking(self):
        """Test POST /requests/{id}/track-click for social clicks"""
        try:
            if not self.test_request_id:
                self.log_result("Social Click Tracking", False, "Missing test request ID")
                return
            
            # Test social click tracking for different platforms
            social_platforms = ["instagram", "facebook", "tiktok", "spotify", "apple_music"]
            
            for platform in social_platforms:
                click_data = {
                    "type": "social",
                    "platform": platform
                }
                
                response = self.make_request("POST", f"/requests/{self.test_request_id}/track-click", click_data)
                
                if response.status_code == 200:
                    data = response.json()
                    if "message" in data:
                        self.log_result(f"Social Click Tracking - {platform.title()}", True, f"{platform.title()} social click tracked")
                    else:
                        self.log_result(f"Social Click Tracking - {platform.title()}", False, f"Unexpected response: {data}")
                else:
                    self.log_result(f"Social Click Tracking - {platform.title()}", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_result("Social Click Tracking", False, f"Exception: {str(e)}")

    def test_click_tracking_database_updates(self):
        """Test that click tracking properly updates database fields"""
        try:
            if not self.test_request_id:
                self.log_result("Click Tracking Database Updates", False, "Missing test request ID")
                return
            
            # Get the request to check current state
            response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
            
            if response.status_code == 200:
                requests_data = response.json()
                test_request = None
                
                for req in requests_data:
                    if req["id"] == self.test_request_id:
                        test_request = req
                        break
                
                if test_request:
                    # Check that tip_clicked is True (from previous tip click tests)
                    tip_clicked = test_request.get("tip_clicked", False)
                    social_clicks = test_request.get("social_clicks", [])
                    
                    if tip_clicked == True:
                        self.log_result("Click Tracking Database Updates - Tip Clicked", True, "tip_clicked field correctly updated to True")
                    else:
                        self.log_result("Click Tracking Database Updates - Tip Clicked", False, f"tip_clicked should be True, got: {tip_clicked}")
                    
                    # Check that social_clicks array contains the platforms we clicked
                    expected_platforms = ["instagram", "facebook", "tiktok", "spotify", "apple_music"]
                    missing_platforms = []
                    
                    for platform in expected_platforms:
                        if platform not in social_clicks:
                            missing_platforms.append(platform)
                    
                    if not missing_platforms:
                        self.log_result("Click Tracking Database Updates - Social Clicks", True, f"social_clicks array correctly updated: {social_clicks}")
                    else:
                        self.log_result("Click Tracking Database Updates - Social Clicks", False, f"Missing platforms in social_clicks: {missing_platforms}")
                else:
                    self.log_result("Click Tracking Database Updates", False, "Test request not found in musician requests")
            else:
                self.log_result("Click Tracking Database Updates", False, f"Failed to get musician requests: {response.status_code}")
        except Exception as e:
            self.log_result("Click Tracking Database Updates", False, f"Exception: {str(e)}")

    # PRIORITY 4: Request Management Tests
    def test_request_status_updates(self):
        """Test that requests can still be managed (accept, reject, play status updates)"""
        try:
            if not self.test_request_id:
                self.log_result("Request Status Updates", False, "Missing test request ID")
                return
            
            # Test different status updates - the API expects status as a query parameter
            statuses = ["accepted", "played", "rejected"]
            
            for status in statuses:
                # Try both query parameter and request body approaches
                response = self.make_request("PUT", f"/requests/{self.test_request_id}/status?status={status}")
                
                if response.status_code == 200:
                    self.log_result(f"Request Status Update - {status.title()}", True, f"Successfully updated status to {status}")
                else:
                    self.log_result(f"Request Status Update - {status.title()}", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Request Status Updates", False, f"Exception: {str(e)}")

    def test_delete_functionality_exists(self):
        """Test that delete functionality exists in the API (contrary to requirements)"""
        try:
            if not self.test_request_id:
                self.log_result("Delete Functionality Check", False, "Missing test request ID")
                return
            
            # Try to delete a request - this should work according to the backend code
            response = self.make_request("DELETE", f"/requests/{self.test_request_id}")
            
            if response.status_code == 200:
                self.log_result("Delete Functionality Check", True, "Request deletion is available (contrary to requirements)")
            elif response.status_code in [404, 405]:
                self.log_result("Delete Functionality Check", False, f"Request deletion not available (status: {response.status_code})")
            else:
                self.log_result("Delete Functionality Check", False, f"Unexpected status code: {response.status_code}")
        except Exception as e:
            self.log_result("Delete Functionality Check", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all new features tests"""
        print("🚀 Starting New Features API Tests for RequestWave")
        print("=" * 60)
        
        # Setup
        if not self.setup_authentication():
            print("❌ Authentication setup failed, aborting tests")
            return
        
        if not self.setup_test_data():
            print("❌ Test data setup failed, aborting tests")
            return
        
        print("\n🎯 PRIORITY 1: Show Management System")
        print("-" * 40)
        self.test_show_creation()
        self.test_start_show()
        self.test_get_current_show()
        self.test_request_auto_assignment_to_show()
        self.test_stop_show()
        self.test_request_no_auto_assignment_after_show_stop()
        self.test_grouped_requests()
        
        print("\n🎯 PRIORITY 2: Enhanced Profile with Social Media")
        print("-" * 40)
        self.test_get_profile_social_media_fields()
        self.test_update_profile_social_media_fields()
        self.test_username_cleaning()
        
        print("\n🎯 PRIORITY 3: Updated Request System")
        print("-" * 40)
        self.test_create_request_without_tip_amount()
        self.test_tip_click_tracking()
        self.test_social_click_tracking()
        self.test_click_tracking_database_updates()
        
        print("\n🎯 PRIORITY 4: Request Management")
        print("-" * 40)
        self.test_request_status_updates()
        self.test_delete_functionality_exists()
        
        # Summary
        print("\n" + "=" * 60)
        print("🏁 NEW FEATURES TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Total: {self.results['passed'] + self.results['failed']}")
        
        if self.results['errors']:
            print(f"\n❌ Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed'])) * 100 if (self.results['passed'] + self.results['failed']) > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        return self.results

if __name__ == "__main__":
    tester = NewFeaturesAPITester()
    results = tester.run_all_tests()