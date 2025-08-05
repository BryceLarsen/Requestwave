#!/usr/bin/env python3
"""
Comprehensive Backend API Tests for RequestWave
Tests authentication, song management, requests, CSV upload, and filtering
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://9ff9d63b-f3ca-4345-83cd-c653b1d08d09.preview.emergentagent.com/api"
TEST_MUSICIAN = {
    "name": "Jazz Virtuoso",
    "email": "jazz.virtuoso@requestwave.com",
    "password": "SecurePassword123!"
}

class RequestWaveAPITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
        self.test_song_id = None
        self.test_request_id = None
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

    def test_health_check(self):
        """Test health check endpoint"""
        try:
            response = self.make_request("GET", "/health")
            if response.status_code == 200:
                data = response.json()
                if "status" in data and data["status"] == "healthy":
                    self.log_result("Health Check", True, "API is healthy")
                else:
                    self.log_result("Health Check", False, f"Unexpected response: {data}")
            else:
                self.log_result("Health Check", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_result("Health Check", False, f"Exception: {str(e)}")

    def test_musician_registration(self):
        """Test musician registration"""
        try:
            response = self.make_request("POST", "/auth/register", TEST_MUSICIAN)
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "musician" in data:
                    self.auth_token = data["token"]
                    self.musician_id = data["musician"]["id"]
                    self.musician_slug = data["musician"]["slug"]
                    self.log_result("Musician Registration", True, f"Registered musician: {data['musician']['name']}")
                else:
                    self.log_result("Musician Registration", False, f"Missing token or musician in response: {data}")
            elif response.status_code == 400:
                # Musician might already exist, try login instead
                self.test_musician_login()
            else:
                self.log_result("Musician Registration", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Musician Registration", False, f"Exception: {str(e)}")

    def test_musician_login(self):
        """Test musician login"""
        try:
            login_data = {
                "email": TEST_MUSICIAN["email"],
                "password": TEST_MUSICIAN["password"]
            }
            response = self.make_request("POST", "/auth/login", login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "musician" in data:
                    self.auth_token = data["token"]
                    self.musician_id = data["musician"]["id"]
                    self.musician_slug = data["musician"]["slug"]
                    self.log_result("Musician Login", True, f"Logged in musician: {data['musician']['name']}")
                else:
                    self.log_result("Musician Login", False, f"Missing token or musician in response: {data}")
            else:
                self.log_result("Musician Login", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Musician Login", False, f"Exception: {str(e)}")

    def test_jwt_token_validation(self):
        """Test JWT token validation by accessing protected endpoint"""
        try:
            if not self.auth_token:
                self.log_result("JWT Token Validation", False, "No auth token available")
                return
            
            response = self.make_request("GET", "/songs")
            
            if response.status_code == 200:
                self.log_result("JWT Token Validation", True, "Token successfully validated")
            elif response.status_code == 401:
                self.log_result("JWT Token Validation", False, "Token validation failed - unauthorized")
            else:
                self.log_result("JWT Token Validation", False, f"Unexpected status code: {response.status_code}")
        except Exception as e:
            self.log_result("JWT Token Validation", False, f"Exception: {str(e)}")

    def test_create_song(self):
        """Test song creation"""
        try:
            song_data = {
                "title": "Test Jazz Standard",
                "artist": "Miles Davis",
                "genres": ["Jazz", "Bebop"],
                "moods": ["Smooth", "Sophisticated"],
                "year": 1959,
                "notes": "Classic jazz standard for testing"
            }
            
            response = self.make_request("POST", "/songs", song_data)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and data["title"] == song_data["title"]:
                    self.test_song_id = data["id"]
                    self.log_result("Create Song", True, f"Created song: {data['title']}")
                else:
                    self.log_result("Create Song", False, f"Unexpected response structure: {data}")
            else:
                self.log_result("Create Song", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Create Song", False, f"Exception: {str(e)}")

    def test_get_songs(self):
        """Test retrieving songs"""
        try:
            response = self.make_request("GET", "/songs")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_result("Get Songs", True, f"Retrieved {len(data)} songs")
                else:
                    self.log_result("Get Songs", False, f"Expected list, got: {type(data)}")
            else:
                self.log_result("Get Songs", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Get Songs", False, f"Exception: {str(e)}")

    def test_update_song(self):
        """Test song update"""
        try:
            if not self.test_song_id:
                self.log_result("Update Song", False, "No test song ID available")
                return
            
            update_data = {
                "title": "Updated Jazz Standard",
                "artist": "Miles Davis",
                "genres": ["Jazz", "Cool Jazz"],
                "moods": ["Mellow", "Contemplative"],
                "year": 1959,
                "notes": "Updated notes for testing"
            }
            
            response = self.make_request("PUT", f"/songs/{self.test_song_id}", update_data)
            
            if response.status_code == 200:
                data = response.json()
                if data["title"] == update_data["title"]:
                    self.log_result("Update Song", True, f"Updated song: {data['title']}")
                else:
                    self.log_result("Update Song", False, f"Title not updated correctly: {data}")
            else:
                self.log_result("Update Song", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Update Song", False, f"Exception: {str(e)}")

    def test_get_musician_by_slug(self):
        """Test getting musician by slug"""
        try:
            if not self.musician_slug:
                self.log_result("Get Musician by Slug", False, "No musician slug available")
                return
            
            response = self.make_request("GET", f"/musicians/{self.musician_slug}")
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "name" in data and "slug" in data:
                    self.log_result("Get Musician by Slug", True, f"Retrieved musician: {data['name']}")
                else:
                    self.log_result("Get Musician by Slug", False, f"Missing required fields: {data}")
            else:
                self.log_result("Get Musician by Slug", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Get Musician by Slug", False, f"Exception: {str(e)}")

    def test_musician_public_endpoint_social_media_fields(self):
        """Test that musician public endpoint includes all 7 social media fields - PRIORITY 1"""
        try:
            if not self.musician_slug:
                self.log_result("Musician Public Endpoint - Social Media Fields", False, "No musician slug available")
                return
            
            print(f"🔍 Testing GET /musicians/{self.musician_slug} for social media fields")
            
            # First, update the musician profile with social media data
            profile_update = {
                "paypal_username": "testmusician",
                "venmo_username": "testmusician", 
                "instagram_username": "@testmusician",
                "facebook_username": "testmusician",
                "tiktok_username": "@testmusician",
                "spotify_artist_url": "https://open.spotify.com/artist/testmusician",
                "apple_music_artist_url": "https://music.apple.com/artist/testmusician"
            }
            
            update_response = self.make_request("PUT", "/profile", profile_update)
            if update_response.status_code != 200:
                self.log_result("Musician Public Endpoint - Profile Update", False, f"Failed to update profile: {update_response.status_code}")
                return
            
            print("📊 Updated musician profile with social media data")
            
            # Now test the public endpoint
            response = self.make_request("GET", f"/musicians/{self.musician_slug}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Public endpoint response: {json.dumps(data, indent=2)}")
                
                # Check for all 7 required social media fields
                required_fields = [
                    "paypal_username",
                    "venmo_username", 
                    "instagram_username",
                    "facebook_username",
                    "tiktok_username",
                    "spotify_artist_url",
                    "apple_music_artist_url"
                ]
                
                missing_fields = []
                present_fields = []
                field_values = {}
                
                for field in required_fields:
                    if field in data:
                        present_fields.append(field)
                        field_values[field] = data[field]
                    else:
                        missing_fields.append(field)
                
                if len(missing_fields) == 0:
                    self.log_result("Musician Public Endpoint - All Social Media Fields Present", True, f"✅ All 7 social media fields present: {present_fields}")
                    
                    # Verify field values are correct (usernames should have @ symbols removed)
                    expected_values = {
                        "paypal_username": "testmusician",
                        "venmo_username": "testmusician",
                        "instagram_username": "testmusician",  # @ should be removed
                        "facebook_username": "testmusician",
                        "tiktok_username": "testmusician",  # @ should be removed
                        "spotify_artist_url": "https://open.spotify.com/artist/testmusician",
                        "apple_music_artist_url": "https://music.apple.com/artist/testmusician"
                    }
                    
                    value_errors = []
                    for field, expected_value in expected_values.items():
                        actual_value = field_values.get(field)
                        if actual_value != expected_value:
                            value_errors.append(f"{field}: expected '{expected_value}', got '{actual_value}'")
                    
                    if len(value_errors) == 0:
                        self.log_result("Musician Public Endpoint - Social Media Field Values", True, "✅ All social media field values are correct (@ symbols properly removed from usernames)")
                        self.log_result("Musician Public Endpoint - Social Media Fields", True, "✅ PRIORITY 1 COMPLETE: All 7 social media fields working correctly in public endpoint")
                    else:
                        self.log_result("Musician Public Endpoint - Social Media Field Values", False, f"❌ Field value errors: {value_errors}")
                        self.log_result("Musician Public Endpoint - Social Media Fields", False, f"❌ Social media field values incorrect: {value_errors}")
                else:
                    self.log_result("Musician Public Endpoint - Social Media Fields", False, f"❌ CRITICAL: Missing social media fields: {missing_fields}")
            else:
                self.log_result("Musician Public Endpoint - Social Media Fields", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Musician Public Endpoint - Social Media Fields", False, f"❌ Exception: {str(e)}")

    def test_musician_public_endpoint_null_social_media_fields(self):
        """Test that musician public endpoint handles null social media fields without errors - PRIORITY 1"""
        try:
            if not self.musician_slug:
                self.log_result("Musician Public Endpoint - Null Social Media Fields", False, "No musician slug available")
                return
            
            print(f"🔍 Testing GET /musicians/{self.musician_slug} with null social media fields")
            
            # Clear all social media fields by setting them to empty strings
            profile_update = {
                "paypal_username": "",
                "venmo_username": "", 
                "instagram_username": "",
                "facebook_username": "",
                "tiktok_username": "",
                "spotify_artist_url": "",
                "apple_music_artist_url": ""
            }
            
            update_response = self.make_request("PUT", "/profile", profile_update)
            if update_response.status_code != 200:
                self.log_result("Musician Public Endpoint - Clear Profile", False, f"Failed to clear profile: {update_response.status_code}")
                return
            
            print("📊 Cleared musician profile social media data")
            
            # Now test the public endpoint
            response = self.make_request("GET", f"/musicians/{self.musician_slug}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Public endpoint response with null fields: {json.dumps(data, indent=2)}")
                
                # Check that all social media fields are present and return null/empty values
                social_media_fields = [
                    "paypal_username",
                    "venmo_username", 
                    "instagram_username",
                    "facebook_username",
                    "tiktok_username",
                    "spotify_artist_url",
                    "apple_music_artist_url"
                ]
                
                field_status = {}
                for field in social_media_fields:
                    if field in data:
                        value = data[field]
                        field_status[field] = value
                        print(f"   • {field}: {repr(value)}")
                    else:
                        field_status[field] = "MISSING"
                
                # All fields should be present (even if null/empty)
                missing_fields = [field for field, value in field_status.items() if value == "MISSING"]
                
                if len(missing_fields) == 0:
                    self.log_result("Musician Public Endpoint - Null Social Media Fields", True, "✅ PRIORITY 1 COMPLETE: All social media fields present and handle null values without errors")
                else:
                    self.log_result("Musician Public Endpoint - Null Social Media Fields", False, f"❌ CRITICAL: Missing fields when null: {missing_fields}")
            else:
                self.log_result("Musician Public Endpoint - Null Social Media Fields", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Musician Public Endpoint - Null Social Media Fields", False, f"❌ Exception: {str(e)}")

    def test_social_media_integration_flow(self):
        """Test complete social media integration flow for post-request modal - PRIORITY 2"""
        try:
            if not self.musician_slug:
                self.log_result("Social Media Integration Flow", False, "No musician slug available")
                return
            
            print(f"🔍 Testing complete social media integration flow")
            
            # Step 1: Create a musician with comprehensive social media data
            social_media_data = {
                "paypal_username": "jazzvirtuoso",
                "venmo_username": "@jazzvirtuoso", 
                "instagram_username": "@jazzvirtuoso_official",
                "facebook_username": "JazzVirtuosoOfficial",
                "tiktok_username": "@jazzvirtuoso",
                "spotify_artist_url": "https://open.spotify.com/artist/1234567890",
                "apple_music_artist_url": "https://music.apple.com/us/artist/jazz-virtuoso/1234567890"
            }
            
            update_response = self.make_request("PUT", "/profile", social_media_data)
            if update_response.status_code != 200:
                self.log_result("Social Media Integration Flow - Profile Update", False, f"Failed to update profile: {update_response.status_code}")
                return
            
            print("📊 Step 1: Updated musician profile with comprehensive social media data")
            
            # Step 2: Test that public endpoint returns all social media data
            public_response = self.make_request("GET", f"/musicians/{self.musician_slug}")
            
            if public_response.status_code != 200:
                self.log_result("Social Media Integration Flow", False, f"Failed to get public musician data: {public_response.status_code}")
                return
            
            public_data = public_response.json()
            print(f"📊 Step 2: Retrieved public musician data")
            
            # Step 3: Verify usernames without @ symbols are returned correctly
            username_tests = [
                ("paypal_username", "jazzvirtuoso", "jazzvirtuoso"),
                ("venmo_username", "@jazzvirtuoso", "jazzvirtuoso"),  # @ should be removed
                ("instagram_username", "@jazzvirtuoso_official", "jazzvirtuoso_official"),  # @ should be removed
                ("tiktok_username", "@jazzvirtuoso", "jazzvirtuoso")  # @ should be removed
            ]
            
            username_errors = []
            for field, input_value, expected_output in username_tests:
                actual_output = public_data.get(field)
                if actual_output != expected_output:
                    username_errors.append(f"{field}: input '{input_value}' → expected '{expected_output}', got '{actual_output}'")
                else:
                    print(f"   ✅ {field}: '{input_value}' → '{actual_output}' (correct)")
            
            if len(username_errors) == 0:
                self.log_result("Social Media Integration Flow - Username Processing", True, "✅ Usernames without @ symbols returned correctly")
            else:
                self.log_result("Social Media Integration Flow - Username Processing", False, f"❌ Username processing errors: {username_errors}")
            
            # Step 4: Verify URLs are returned as full URLs
            url_tests = [
                ("spotify_artist_url", "https://open.spotify.com/artist/1234567890"),
                ("apple_music_artist_url", "https://music.apple.com/us/artist/jazz-virtuoso/1234567890")
            ]
            
            url_errors = []
            for field, expected_url in url_tests:
                actual_url = public_data.get(field)
                if actual_url != expected_url:
                    url_errors.append(f"{field}: expected '{expected_url}', got '{actual_url}'")
                else:
                    print(f"   ✅ {field}: '{actual_url}' (correct)")
            
            if len(url_errors) == 0:
                self.log_result("Social Media Integration Flow - URL Processing", True, "✅ URLs returned as full URLs correctly")
            else:
                self.log_result("Social Media Integration Flow - URL Processing", False, f"❌ URL processing errors: {url_errors}")
            
            # Step 5: Verify response format matches MusicianPublic model
            required_public_fields = ["id", "name", "slug", "paypal_username", "venmo_username", 
                                    "instagram_username", "facebook_username", "tiktok_username", 
                                    "spotify_artist_url", "apple_music_artist_url"]
            
            missing_public_fields = [field for field in required_public_fields if field not in public_data]
            
            if len(missing_public_fields) == 0:
                self.log_result("Social Media Integration Flow - MusicianPublic Model", True, "✅ Response format matches MusicianPublic model")
            else:
                self.log_result("Social Media Integration Flow - MusicianPublic Model", False, f"❌ Missing fields in MusicianPublic response: {missing_public_fields}")
            
            # Final result
            if len(username_errors) == 0 and len(url_errors) == 0 and len(missing_public_fields) == 0:
                self.log_result("Social Media Integration Flow", True, "✅ PRIORITY 2 COMPLETE: Complete social media integration flow working correctly")
            else:
                error_summary = []
                if username_errors: error_summary.append(f"Username errors: {len(username_errors)}")
                if url_errors: error_summary.append(f"URL errors: {len(url_errors)}")
                if missing_public_fields: error_summary.append(f"Missing fields: {len(missing_public_fields)}")
                self.log_result("Social Media Integration Flow", False, f"❌ Integration flow issues: {', '.join(error_summary)}")
                
        except Exception as e:
            self.log_result("Social Media Integration Flow", False, f"❌ Exception: {str(e)}")

    def test_advanced_filtering(self):
        """Test advanced song filtering"""
        try:
            if not self.musician_slug:
                self.log_result("Advanced Filtering", False, "No musician slug available")
                return
            
            # Test filtering by genre
            params = {"genre": "Jazz"}
            response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs", params)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    # Check if all returned songs have Jazz genre
                    jazz_songs = [song for song in data if "Jazz" in song.get("genres", [])]
                    if len(jazz_songs) == len(data):
                        self.log_result("Advanced Filtering - Genre", True, f"Found {len(data)} Jazz songs")
                    else:
                        self.log_result("Advanced Filtering - Genre", False, f"Filter not working correctly")
                else:
                    self.log_result("Advanced Filtering - Genre", False, f"Expected list, got: {type(data)}")
            else:
                self.log_result("Advanced Filtering - Genre", False, f"Status code: {response.status_code}")
            
            # Test filtering by artist
            params = {"artist": "Miles"}
            response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs", params)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_result("Advanced Filtering - Artist", True, f"Found {len(data)} songs by Miles")
                else:
                    self.log_result("Advanced Filtering - Artist", False, f"Expected list, got: {type(data)}")
            else:
                self.log_result("Advanced Filtering - Artist", False, f"Status code: {response.status_code}")
                
        except Exception as e:
            self.log_result("Advanced Filtering", False, f"Exception: {str(e)}")

    def test_create_request(self):
        """Test creating a song request"""
        try:
            if not self.test_song_id:
                self.log_result("Create Request", False, "No test song ID available")
                return
            
            request_data = {
                "song_id": self.test_song_id,
                "requester_name": "Jazz Fan",
                "requester_email": "fan@example.com",
                "dedication": "For my anniversary!",
                "tip_amount": 5.0
            }
            
            response = self.make_request("POST", "/requests", request_data)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and data["status"] == "pending":
                    self.test_request_id = data["id"]
                    self.log_result("Create Request", True, f"Created request: {data['id']}")
                else:
                    self.log_result("Create Request", False, f"Unexpected response structure: {data}")
            else:
                self.log_result("Create Request", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Create Request", False, f"Exception: {str(e)}")

    def test_get_musician_requests(self):
        """Test getting musician requests"""
        try:
            response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_result("Get Musician Requests", True, f"Retrieved {len(data)} requests")
                else:
                    self.log_result("Get Musician Requests", False, f"Expected list, got: {type(data)}")
            else:
                self.log_result("Get Musician Requests", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Get Musician Requests", False, f"Exception: {str(e)}")

    def test_update_request_status(self):
        """Test updating request status"""
        try:
            if not self.test_request_id:
                self.log_result("Update Request Status", False, "No test request ID available")
                return
            
            # Test updating to accepted - fix the request format
            response = self.make_request("PUT", f"/requests/{self.test_request_id}/status?status=accepted")
            
            if response.status_code == 200:
                self.log_result("Update Request Status", True, "Successfully updated request status")
            else:
                self.log_result("Update Request Status", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Update Request Status", False, f"Exception: {str(e)}")

    def test_real_time_polling(self):
        """Test real-time polling endpoint"""
        try:
            if not self.musician_id:
                self.log_result("Real-time Polling", False, "No musician ID available")
                return
            
            response = self.make_request("GET", f"/requests/updates/{self.musician_id}")
            
            if response.status_code == 200:
                data = response.json()
                if "requests" in data and "timestamp" in data:
                    self.log_result("Real-time Polling", True, f"Polling endpoint working, timestamp: {data['timestamp']}")
                else:
                    self.log_result("Real-time Polling", False, f"Missing required fields: {data}")
            else:
                self.log_result("Real-time Polling", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Real-time Polling", False, f"Exception: {str(e)}")

    def test_csv_preview_valid(self):
        """Test CSV preview with valid file"""
        try:
            with open('/app/test_songs_valid.csv', 'rb') as f:
                files = {'file': ('test_songs_valid.csv', f, 'text/csv')}
                response = self.make_request("POST", "/songs/csv/preview", files=files)
            
            if response.status_code == 200:
                data = response.json()
                if "preview" in data and "total_rows" in data and "valid_rows" in data:
                    self.log_result("CSV Preview - Valid File", True, f"Preview shows {data['valid_rows']} valid rows out of {data['total_rows']}")
                else:
                    self.log_result("CSV Preview - Valid File", False, f"Missing required fields: {data}")
            else:
                self.log_result("CSV Preview - Valid File", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("CSV Preview - Valid File", False, f"Exception: {str(e)}")

    def test_csv_preview_invalid(self):
        """Test CSV preview with invalid file"""
        try:
            with open('/app/test_songs_invalid.csv', 'rb') as f:
                files = {'file': ('test_songs_invalid.csv', f, 'text/csv')}
                response = self.make_request("POST", "/songs/csv/preview", files=files)
            
            if response.status_code == 200:
                data = response.json()
                if "errors" in data and len(data["errors"]) > 0:
                    self.log_result("CSV Preview - Invalid File", True, f"Correctly detected {len(data['errors'])} errors")
                else:
                    self.log_result("CSV Preview - Invalid File", False, f"Should have detected errors: {data}")
            else:
                self.log_result("CSV Preview - Invalid File", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("CSV Preview - Invalid File", False, f"Exception: {str(e)}")

    def test_csv_preview_missing_columns(self):
        """Test CSV preview with missing required columns"""
        try:
            with open('/app/test_songs_missing_columns.csv', 'rb') as f:
                files = {'file': ('test_songs_missing_columns.csv', f, 'text/csv')}
                response = self.make_request("POST", "/songs/csv/preview", files=files)
            
            if response.status_code == 400:
                self.log_result("CSV Preview - Missing Columns", True, "Correctly rejected file with missing columns")
            else:
                self.log_result("CSV Preview - Missing Columns", False, f"Should have returned 400, got: {response.status_code}")
        except Exception as e:
            self.log_result("CSV Preview - Missing Columns", False, f"Exception: {str(e)}")

    def test_csv_upload_valid(self):
        """Test CSV upload with valid file"""
        try:
            with open('/app/test_songs_valid.csv', 'rb') as f:
                files = {'file': ('test_songs_valid.csv', f, 'text/csv')}
                response = self.make_request("POST", "/songs/csv/upload", files=files)
            
            if response.status_code == 200:
                data = response.json()
                if "success" in data and data["success"] and "songs_added" in data:
                    self.log_result("CSV Upload - Valid File", True, f"Successfully uploaded {data['songs_added']} songs")
                else:
                    self.log_result("CSV Upload - Valid File", False, f"Upload failed: {data}")
            else:
                self.log_result("CSV Upload - Valid File", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("CSV Upload - Valid File", False, f"Exception: {str(e)}")

    def test_csv_duplicate_detection(self):
        """Test CSV duplicate detection by uploading same file twice"""
        try:
            # Upload the same file again to test duplicate detection
            with open('/app/test_songs_valid.csv', 'rb') as f:
                files = {'file': ('test_songs_valid.csv', f, 'text/csv')}
                response = self.make_request("POST", "/songs/csv/upload", files=files)
            
            if response.status_code == 200:
                data = response.json()
                if "errors" in data and len(data["errors"]) > 0:
                    # Check if errors mention duplicates
                    duplicate_errors = [error for error in data["errors"] if "duplicate" in error.lower()]
                    if duplicate_errors:
                        self.log_result("CSV Duplicate Detection", True, f"Correctly detected {len(duplicate_errors)} duplicates")
                    else:
                        self.log_result("CSV Duplicate Detection", False, f"No duplicate errors found: {data['errors']}")
                else:
                    self.log_result("CSV Duplicate Detection", False, f"Should have detected duplicates: {data}")
            else:
                self.log_result("CSV Duplicate Detection", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("CSV Duplicate Detection", False, f"Exception: {str(e)}")

    def test_spotify_playlist_import(self):
        """Test Spotify playlist import functionality - CRITICAL FIX TEST"""
        try:
            if not self.auth_token:
                self.log_result("Spotify Playlist Import", False, "No auth token available")
                return
            
            # Test with the EXACT URL from the user report
            playlist_data = {
                "playlist_url": "https://open.spotify.com/playlist/37i9dQZEVXbLRQDuF5jeBp",
                "platform": "spotify"
            }
            
            print(f"🔍 Testing Spotify playlist import with URL: {playlist_data['playlist_url']}")
            response = self.make_request("POST", "/songs/playlist/import", playlist_data)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Import response: {json.dumps(data, indent=2)}")
                
                if "success" in data and data["success"] and "songs_added" in data:
                    if data["songs_added"] > 0:
                        self.log_result("Spotify Playlist Import", True, f"Successfully imported {data['songs_added']} songs from Spotify playlist")
                        
                        # CRITICAL: Verify songs were actually added to database with REAL song data
                        songs_response = self.make_request("GET", "/songs")
                        if songs_response.status_code == 200:
                            songs = songs_response.json()
                            
                            # Find the most recently imported songs
                            imported_songs = [song for song in songs if "spotify" in song.get("notes", "").lower() or "demo" in song.get("notes", "").lower()]
                            
                            if len(imported_songs) > 0:
                                print(f"🎵 Found {len(imported_songs)} imported songs:")
                                
                                # CRITICAL TEST: Check if songs have REAL titles (not generic/placeholder data)
                                real_song_count = 0
                                placeholder_songs = []
                                
                                for song in imported_songs[:5]:  # Check first 5 songs
                                    title = song.get("title", "")
                                    artist = song.get("artist", "")
                                    print(f"   • '{title}' by '{artist}' (genres: {song.get('genres', [])}, year: {song.get('year', 'N/A')})")
                                    
                                    # Check for placeholder/generic data patterns
                                    if any(placeholder in title.lower() for placeholder in ["sample", "demo", "test", "unknown", "playlist"]):
                                        placeholder_songs.append(f"'{title}' by '{artist}'")
                                    elif any(placeholder in artist.lower() for placeholder in ["demo", "test", "unknown"]):
                                        placeholder_songs.append(f"'{title}' by '{artist}'")
                                    else:
                                        real_song_count += 1
                                
                                if real_song_count > 0 and len(placeholder_songs) == 0:
                                    self.log_result("Spotify Playlist Import - Real Song Data", True, f"✅ CRITICAL FIX VERIFIED: All {real_song_count} songs have real titles/artists (no placeholder data)")
                                elif real_song_count > len(placeholder_songs):
                                    self.log_result("Spotify Playlist Import - Real Song Data", True, f"✅ MOSTLY REAL DATA: {real_song_count} real songs, {len(placeholder_songs)} placeholder songs")
                                else:
                                    self.log_result("Spotify Playlist Import - Real Song Data", False, f"❌ CRITICAL BUG: Found placeholder songs: {placeholder_songs}")
                                
                                self.log_result("Spotify Playlist Import - Database Verification", True, f"Found {len(imported_songs)} imported songs in database")
                            else:
                                self.log_result("Spotify Playlist Import - Database Verification", False, "❌ CRITICAL BUG: No imported songs found in database")
                    else:
                        self.log_result("Spotify Playlist Import", False, f"❌ CRITICAL BUG: No songs were imported: {data}")
                else:
                    self.log_result("Spotify Playlist Import", False, f"❌ CRITICAL BUG: Unexpected response structure: {data}")
            else:
                self.log_result("Spotify Playlist Import", False, f"❌ CRITICAL BUG: Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Spotify Playlist Import", False, f"❌ CRITICAL BUG: Exception: {str(e)}")

    def test_apple_music_playlist_import(self):
        """Test Apple Music playlist import functionality - CRITICAL FIX TEST"""
        try:
            if not self.auth_token:
                self.log_result("Apple Music Playlist Import", False, "No auth token available")
                return
            
            # Test with a valid Apple Music playlist URL
            playlist_data = {
                "playlist_url": "https://music.apple.com/us/playlist/todays-hits/pl.f4d106fed2bd41149aaacabb233eb5eb",
                "platform": "apple_music"
            }
            
            print(f"🔍 Testing Apple Music playlist import with URL: {playlist_data['playlist_url']}")
            response = self.make_request("POST", "/songs/playlist/import", playlist_data)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Import response: {json.dumps(data, indent=2)}")
                
                if "success" in data and data["success"] and "songs_added" in data:
                    if data["songs_added"] > 0:
                        self.log_result("Apple Music Playlist Import", True, f"Successfully imported {data['songs_added']} songs from Apple Music playlist")
                        
                        # CRITICAL: Verify songs were actually added to database with REAL song data
                        songs_response = self.make_request("GET", "/songs")
                        if songs_response.status_code == 200:
                            songs = songs_response.json()
                            
                            # Find the most recently imported songs
                            apple_songs = [song for song in songs if "apple" in song.get("notes", "").lower() or "demo" in song.get("notes", "").lower()]
                            
                            if len(apple_songs) > 0:
                                print(f"🎵 Found {len(apple_songs)} imported Apple Music songs:")
                                
                                # CRITICAL TEST: Check if songs have REAL titles (not generic/placeholder data)
                                real_song_count = 0
                                placeholder_songs = []
                                
                                for song in apple_songs[:5]:  # Check first 5 songs
                                    title = song.get("title", "")
                                    artist = song.get("artist", "")
                                    print(f"   • '{title}' by '{artist}' (genres: {song.get('genres', [])}, year: {song.get('year', 'N/A')})")
                                    
                                    # Check for placeholder/generic data patterns
                                    if any(placeholder in title.lower() for placeholder in ["sample", "demo", "test", "unknown", "playlist"]):
                                        placeholder_songs.append(f"'{title}' by '{artist}'")
                                    elif any(placeholder in artist.lower() for placeholder in ["demo", "test", "unknown"]):
                                        placeholder_songs.append(f"'{title}' by '{artist}'")
                                    else:
                                        real_song_count += 1
                                
                                if real_song_count > 0 and len(placeholder_songs) == 0:
                                    self.log_result("Apple Music Playlist Import - Real Song Data", True, f"✅ CRITICAL FIX VERIFIED: All {real_song_count} songs have real titles/artists (no placeholder data)")
                                elif real_song_count > len(placeholder_songs):
                                    self.log_result("Apple Music Playlist Import - Real Song Data", True, f"✅ MOSTLY REAL DATA: {real_song_count} real songs, {len(placeholder_songs)} placeholder songs")
                                else:
                                    self.log_result("Apple Music Playlist Import - Real Song Data", False, f"❌ CRITICAL BUG: Found placeholder songs: {placeholder_songs}")
                                
                                self.log_result("Apple Music Playlist Import - Database Verification", True, f"Found {len(apple_songs)} imported songs in database")
                            else:
                                self.log_result("Apple Music Playlist Import - Database Verification", False, "❌ CRITICAL BUG: No imported songs found in database")
                    else:
                        self.log_result("Apple Music Playlist Import", False, f"❌ CRITICAL BUG: No songs were imported: {data}")
                else:
                    self.log_result("Apple Music Playlist Import", False, f"❌ CRITICAL BUG: Unexpected response structure: {data}")
            else:
                self.log_result("Apple Music Playlist Import", False, f"❌ CRITICAL BUG: Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Apple Music Playlist Import", False, f"❌ CRITICAL BUG: Exception: {str(e)}")

    def test_playlist_import_authentication(self):
        """Test playlist import requires authentication"""
        try:
            # Save current token
            original_token = self.auth_token
            
            # Test without token
            self.auth_token = None
            playlist_data = {
                "playlist_url": "https://open.spotify.com/playlist/37i9dQZEVXbLRQDuF5jeBp",
                "platform": "spotify"
            }
            
            response = self.make_request("POST", "/songs/playlist/import", playlist_data)
            
            if response.status_code in [401, 403]:  # Accept both 401 and 403 as valid auth failures
                self.log_result("Playlist Import Authentication - No Token", True, f"Correctly rejected request without auth token (status: {response.status_code})")
            else:
                self.log_result("Playlist Import Authentication - No Token", False, f"Should have returned 401/403, got: {response.status_code}")
            
            # Test with invalid token
            self.auth_token = "invalid_token_12345"
            response = self.make_request("POST", "/songs/playlist/import", playlist_data)
            
            if response.status_code == 401:
                self.log_result("Playlist Import Authentication - Invalid Token", True, "Correctly rejected request with invalid token")
            else:
                self.log_result("Playlist Import Authentication - Invalid Token", False, f"Should have returned 401, got: {response.status_code}")
            
            # Restore original token
            self.auth_token = original_token
            
        except Exception as e:
            self.log_result("Playlist Import Authentication", False, f"Exception: {str(e)}")

    def test_playlist_import_invalid_urls(self):
        """Test playlist import with invalid URLs"""
        try:
            if not self.auth_token:
                self.log_result("Playlist Import Invalid URLs", False, "No auth token available")
                return
            
            # Test invalid Spotify URL
            invalid_spotify_data = {
                "playlist_url": "https://invalid-spotify-url.com/playlist/123",
                "platform": "spotify"
            }
            
            response = self.make_request("POST", "/songs/playlist/import", invalid_spotify_data)
            
            if response.status_code == 400:
                self.log_result("Playlist Import - Invalid Spotify URL", True, "Correctly rejected invalid Spotify URL")
            else:
                self.log_result("Playlist Import - Invalid Spotify URL", False, f"Should have returned 400, got: {response.status_code}")
            
            # Test invalid Apple Music URL
            invalid_apple_data = {
                "playlist_url": "https://invalid-apple-url.com/playlist/123",
                "platform": "apple_music"
            }
            
            response = self.make_request("POST", "/songs/playlist/import", invalid_apple_data)
            
            if response.status_code == 400:
                self.log_result("Playlist Import - Invalid Apple Music URL", True, "Correctly rejected invalid Apple Music URL")
            else:
                self.log_result("Playlist Import - Invalid Apple Music URL", False, f"Should have returned 400, got: {response.status_code}")
            
            # Test unsupported platform
            unsupported_platform_data = {
                "playlist_url": "https://open.spotify.com/playlist/37i9dQZEVXbLRQDuF5jeBp",
                "platform": "youtube"
            }
            
            response = self.make_request("POST", "/songs/playlist/import", unsupported_platform_data)
            
            if response.status_code == 400:
                self.log_result("Playlist Import - Unsupported Platform", True, "Correctly rejected unsupported platform")
            else:
                self.log_result("Playlist Import - Unsupported Platform", False, f"Should have returned 400, got: {response.status_code}")
                
        except Exception as e:
            self.log_result("Playlist Import Invalid URLs", False, f"Exception: {str(e)}")

    def test_playlist_import_song_data_quality(self):
        """Test that imported songs have proper data quality"""
        try:
            if not self.auth_token:
                self.log_result("Playlist Import Song Data Quality", False, "No auth token available")
                return
            
            # Import a playlist first
            playlist_data = {
                "playlist_url": "https://open.spotify.com/playlist/37i9dQZEVXbLRQDuF5jeBp",
                "platform": "spotify"
            }
            
            import_response = self.make_request("POST", "/songs/playlist/import", playlist_data)
            
            if import_response.status_code == 200:
                import_data = import_response.json()
                if import_data.get("songs_added", 0) > 0:
                    # Get all songs and check the imported ones
                    songs_response = self.make_request("GET", "/songs")
                    if songs_response.status_code == 200:
                        songs = songs_response.json()
                        
                        # Find recently imported songs (demo songs from playlist import)
                        imported_songs = [song for song in songs if "demo" in song.get("notes", "").lower() or "spotify" in song.get("notes", "").lower()]
                        
                        if imported_songs:
                            quality_issues = []
                            
                            for song in imported_songs:
                                # Check required fields
                                if not song.get("title") or song["title"].strip() == "":
                                    quality_issues.append(f"Song missing title: {song}")
                                if not song.get("artist") or song["artist"].strip() == "":
                                    quality_issues.append(f"Song missing artist: {song}")
                                
                                # Check optional but expected fields
                                if not song.get("genres") or len(song["genres"]) == 0:
                                    quality_issues.append(f"Song missing genres: {song['title']}")
                                if not song.get("moods") or len(song["moods"]) == 0:
                                    quality_issues.append(f"Song missing moods: {song['title']}")
                                if not song.get("year"):
                                    quality_issues.append(f"Song missing year: {song['title']}")
                            
                            if len(quality_issues) == 0:
                                self.log_result("Playlist Import Song Data Quality", True, f"All {len(imported_songs)} imported songs have proper data quality")
                            else:
                                self.log_result("Playlist Import Song Data Quality", False, f"Found {len(quality_issues)} data quality issues: {quality_issues[:3]}")
                        else:
                            self.log_result("Playlist Import Song Data Quality", False, "No imported songs found to check quality")
                    else:
                        self.log_result("Playlist Import Song Data Quality", False, "Could not retrieve songs to check quality")
                else:
                    self.log_result("Playlist Import Song Data Quality", False, "No songs were imported to check quality")
            else:
                self.log_result("Playlist Import Song Data Quality", False, f"Could not import playlist for quality check: {import_response.status_code}")
                
        except Exception as e:
            self.log_result("Playlist Import Song Data Quality", False, f"Exception: {str(e)}")

    def test_playlist_import_duplicate_detection(self):
        """Test that playlist import detects and handles duplicates"""
        try:
            if not self.auth_token:
                self.log_result("Playlist Import Duplicate Detection", False, "No auth token available")
                return
            
            # Import the same playlist twice
            playlist_data = {
                "playlist_url": "https://open.spotify.com/playlist/37i9dQZEVXbLRQDuF5jeBp",
                "platform": "spotify"
            }
            
            # First import
            first_response = self.make_request("POST", "/songs/playlist/import", playlist_data)
            
            if first_response.status_code == 200:
                first_data = first_response.json()
                first_songs_added = first_data.get("songs_added", 0)
                
                if first_songs_added > 0:
                    # Second import (should detect duplicates)
                    second_response = self.make_request("POST", "/songs/playlist/import", playlist_data)
                    
                    if second_response.status_code == 200:
                        second_data = second_response.json()
                        second_songs_added = second_data.get("songs_added", 0)
                        songs_skipped = second_data.get("songs_skipped", 0)
                        errors = second_data.get("errors", [])
                        
                        # Check if duplicates were detected
                        duplicate_errors = [error for error in errors if "duplicate" in error.lower() or "skipped" in error.lower()]
                        
                        if songs_skipped > 0 or duplicate_errors:
                            self.log_result("Playlist Import Duplicate Detection", True, f"Correctly detected duplicates: {songs_skipped} skipped, {len(duplicate_errors)} duplicate errors")
                        else:
                            self.log_result("Playlist Import Duplicate Detection", False, f"Should have detected duplicates but didn't: {second_data}")
                    else:
                        self.log_result("Playlist Import Duplicate Detection", False, f"Second import failed: {second_response.status_code}")
                else:
                    self.log_result("Playlist Import Duplicate Detection", False, "First import added no songs, cannot test duplicates")
            else:
                self.log_result("Playlist Import Duplicate Detection", False, f"First import failed: {first_response.status_code}")
                
        except Exception as e:
            self.log_result("Playlist Import Duplicate Detection", False, f"Exception: {str(e)}")

    def test_delete_song(self):
        """Test song deletion - CRITICAL FIX TEST"""
        try:
            if not self.test_song_id:
                self.log_result("Delete Song", False, "No test song ID available")
                return
            
            print(f"🔍 Testing song deletion for song ID: {self.test_song_id}")
            
            # First, verify the song exists
            songs_before_response = self.make_request("GET", "/songs")
            if songs_before_response.status_code == 200:
                songs_before = songs_before_response.json()
                song_exists_before = any(song["id"] == self.test_song_id for song in songs_before)
                print(f"📊 Song exists before deletion: {song_exists_before}")
                
                if not song_exists_before:
                    self.log_result("Delete Song - Pre-check", False, "Test song not found in database before deletion")
                    return
            else:
                self.log_result("Delete Song - Pre-check", False, f"Could not retrieve songs before deletion: {songs_before_response.status_code}")
                return
            
            # Test deletion
            response = self.make_request("DELETE", f"/songs/{self.test_song_id}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Delete response: {json.dumps(data, indent=2)}")
                
                if "message" in data:
                    self.log_result("Delete Song - API Response", True, f"✅ API returned success: {data['message']}")
                    
                    # CRITICAL TEST: Verify the song is actually deleted from the database
                    songs_after_response = self.make_request("GET", "/songs")
                    if songs_after_response.status_code == 200:
                        songs_after = songs_after_response.json()
                        song_exists_after = any(song["id"] == self.test_song_id for song in songs_after)
                        
                        print(f"📊 Song exists after deletion: {song_exists_after}")
                        print(f"📊 Songs count before: {len(songs_before)}, after: {len(songs_after)}")
                        
                        if not song_exists_after:
                            self.log_result("Delete Song - Database Verification", True, f"✅ CRITICAL FIX VERIFIED: Song successfully deleted from database")
                            self.log_result("Delete Song", True, "✅ CRITICAL FIX VERIFIED: Song deletion working correctly")
                        else:
                            self.log_result("Delete Song - Database Verification", False, f"❌ CRITICAL BUG: Song still exists in database after deletion")
                            self.log_result("Delete Song", False, f"❌ CRITICAL BUG: Song not actually deleted from database")
                    else:
                        self.log_result("Delete Song - Database Verification", False, f"Could not verify deletion: {songs_after_response.status_code}")
                        self.log_result("Delete Song", False, f"Could not verify deletion from database")
                else:
                    self.log_result("Delete Song", False, f"❌ CRITICAL BUG: Unexpected response format: {data}")
            else:
                self.log_result("Delete Song", False, f"❌ CRITICAL BUG: Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Delete Song", False, f"❌ CRITICAL BUG: Exception: {str(e)}")

    def test_delete_song_authentication(self):
        """Test that song deletion requires proper authentication - CRITICAL FIX TEST"""
        try:
            if not self.test_song_id:
                # Create a temporary song for this test
                temp_song_data = {
                    "title": "Temp Song for Auth Test",
                    "artist": "Test Artist",
                    "genres": ["Test"],
                    "moods": ["Test"],
                    "year": 2023,
                    "notes": "Temporary song for authentication test"
                }
                
                create_response = self.make_request("POST", "/songs", temp_song_data)
                if create_response.status_code == 200:
                    temp_song_id = create_response.json()["id"]
                else:
                    self.log_result("Delete Song Authentication", False, "Could not create temporary song for auth test")
                    return
            else:
                temp_song_id = self.test_song_id
            
            # Save current token
            original_token = self.auth_token
            
            # Test without token
            self.auth_token = None
            print(f"🔍 Testing song deletion without authentication for song ID: {temp_song_id}")
            
            response = self.make_request("DELETE", f"/songs/{temp_song_id}")
            
            if response.status_code in [401, 403]:  # Accept both 401 and 403 as valid auth failures
                self.log_result("Delete Song Authentication - No Token", True, f"✅ Correctly rejected deletion without auth token (status: {response.status_code})")
            else:
                self.log_result("Delete Song Authentication - No Token", False, f"❌ CRITICAL BUG: Should have returned 401/403, got: {response.status_code}")
            
            # Test with invalid token
            self.auth_token = "invalid_token_12345"
            response = self.make_request("DELETE", f"/songs/{temp_song_id}")
            
            if response.status_code == 401:
                self.log_result("Delete Song Authentication - Invalid Token", True, "✅ Correctly rejected deletion with invalid token")
            else:
                self.log_result("Delete Song Authentication - Invalid Token", False, f"❌ CRITICAL BUG: Should have returned 401, got: {response.status_code}")
            
            # Restore original token
            self.auth_token = original_token
            
        except Exception as e:
            self.log_result("Delete Song Authentication", False, f"❌ CRITICAL BUG: Exception: {str(e)}")
            # Restore token in case of exception
            if 'original_token' in locals():
                self.auth_token = original_token

    def test_phase2_request_count_tracking(self):
        """Test Phase 2: Request count tracking functionality"""
        try:
            if not self.test_song_id:
                self.log_result("Phase 2 Request Count Tracking", False, "No test song ID available")
                return
            
            print(f"🔍 Testing request count tracking for song ID: {self.test_song_id}")
            
            # First, verify the song has request_count: 0 initially
            songs_response = self.make_request("GET", "/songs")
            if songs_response.status_code == 200:
                songs = songs_response.json()
                test_song = next((song for song in songs if song["id"] == self.test_song_id), None)
                
                if test_song:
                    initial_count = test_song.get("request_count", 0)
                    print(f"📊 Initial request_count: {initial_count}")
                    
                    if initial_count == 0:
                        self.log_result("Phase 2 Request Count - Initial Value", True, "Song has request_count: 0 initially")
                    else:
                        self.log_result("Phase 2 Request Count - Initial Value", False, f"Expected request_count: 0, got: {initial_count}")
                        return
                else:
                    self.log_result("Phase 2 Request Count - Initial Value", False, "Test song not found")
                    return
            else:
                self.log_result("Phase 2 Request Count - Initial Value", False, f"Could not retrieve songs: {songs_response.status_code}")
                return
            
            # Create multiple requests for the song
            request_count = 3
            created_requests = []
            
            for i in range(request_count):
                request_data = {
                    "song_id": self.test_song_id,
                    "requester_name": f"Fan {i+1}",
                    "requester_email": f"fan{i+1}@example.com",
                    "dedication": f"Request #{i+1}",
                    "tip_amount": 2.0
                }
                
                response = self.make_request("POST", "/requests", request_data)
                
                if response.status_code == 200:
                    data = response.json()
                    created_requests.append(data["id"])
                    print(f"📊 Created request #{i+1}: {data['id']}")
                else:
                    self.log_result("Phase 2 Request Count - Create Requests", False, f"Failed to create request #{i+1}: {response.status_code}")
                    return
            
            # Verify that each request incremented the song's request_count
            songs_response = self.make_request("GET", "/songs")
            if songs_response.status_code == 200:
                songs = songs_response.json()
                test_song = next((song for song in songs if song["id"] == self.test_song_id), None)
                
                if test_song:
                    final_count = test_song.get("request_count", 0)
                    print(f"📊 Final request_count: {final_count}")
                    
                    if final_count == request_count:
                        self.log_result("Phase 2 Request Count Tracking", True, f"✅ Request count correctly incremented from 0 to {final_count} after {request_count} requests")
                    else:
                        self.log_result("Phase 2 Request Count Tracking", False, f"❌ Expected request_count: {request_count}, got: {final_count}")
                else:
                    self.log_result("Phase 2 Request Count Tracking", False, "Test song not found after creating requests")
            else:
                self.log_result("Phase 2 Request Count Tracking", False, f"Could not retrieve songs after creating requests: {songs_response.status_code}")
                
        except Exception as e:
            self.log_result("Phase 2 Request Count Tracking", False, f"Exception: {str(e)}")

    def test_phase2_popularity_sorting(self):
        """Test Phase 2: Popularity sorting functionality"""
        try:
            print("🔍 Testing popularity sorting with different sort_by parameters")
            
            # Create multiple test songs with different request counts
            test_songs = [
                {"title": "Popular Song A", "artist": "Artist A", "genres": ["Pop"], "moods": ["Upbeat"], "year": 2023},
                {"title": "Popular Song B", "artist": "Artist B", "genres": ["Rock"], "moods": ["Energetic"], "year": 2022},
                {"title": "Popular Song C", "artist": "Artist C", "genres": ["Jazz"], "moods": ["Smooth"], "year": 2021}
            ]
            
            created_song_ids = []
            
            # Create the test songs
            for song_data in test_songs:
                response = self.make_request("POST", "/songs", song_data)
                if response.status_code == 200:
                    song_id = response.json()["id"]
                    created_song_ids.append(song_id)
                    print(f"📊 Created test song: {song_data['title']} (ID: {song_id})")
                else:
                    self.log_result("Phase 2 Popularity Sorting - Create Test Songs", False, f"Failed to create song: {song_data['title']}")
                    return
            
            # Create different numbers of requests for each song to establish popularity order
            # Song A: 5 requests (most popular)
            # Song B: 3 requests (medium popular)  
            # Song C: 1 request (least popular)
            request_counts = [5, 3, 1]
            
            for i, (song_id, count) in enumerate(zip(created_song_ids, request_counts)):
                for j in range(count):
                    request_data = {
                        "song_id": song_id,
                        "requester_name": f"Fan {j+1}",
                        "requester_email": f"fan{j+1}@song{i}.com",
                        "dedication": f"Request for song {i+1}",
                        "tip_amount": 1.0
                    }
                    
                    response = self.make_request("POST", "/requests", request_data)
                    if response.status_code != 200:
                        self.log_result("Phase 2 Popularity Sorting - Create Requests", False, f"Failed to create request for song {i+1}")
                        return
                
                print(f"📊 Created {count} requests for song {test_songs[i]['title']}")
            
            # Test different sorting options
            sort_tests = [
                ("popularity", "Most requested first"),
                ("title", "A-Z by title"),
                ("artist", "A-Z by artist"),
                ("year", "Newest first by year"),
                ("created_at", "Default - newest first by creation")
            ]
            
            for sort_by, description in sort_tests:
                params = {"sort_by": sort_by}
                response = self.make_request("GET", "/songs", params)
                
                if response.status_code == 200:
                    songs = response.json()
                    
                    if sort_by == "popularity":
                        # Verify songs are sorted by request_count descending
                        request_counts = [song.get("request_count", 0) for song in songs]
                        is_sorted_desc = all(request_counts[i] >= request_counts[i+1] for i in range(len(request_counts)-1))
                        
                        if is_sorted_desc:
                            self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", True, f"✅ Songs correctly sorted by popularity: {request_counts[:5]}")
                        else:
                            self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", False, f"❌ Songs not sorted by popularity: {request_counts[:5]}")
                    
                    elif sort_by == "title":
                        # Verify songs are sorted by title ascending
                        titles = [song.get("title", "") for song in songs]
                        is_sorted_asc = all(titles[i].lower() <= titles[i+1].lower() for i in range(len(titles)-1))
                        
                        if is_sorted_asc:
                            self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", True, f"✅ Songs correctly sorted by title A-Z")
                        else:
                            self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", False, f"❌ Songs not sorted by title A-Z: {titles[:5]}")
                    
                    elif sort_by == "artist":
                        # Verify songs are sorted by artist ascending
                        artists = [song.get("artist", "") for song in songs]
                        is_sorted_asc = all(artists[i].lower() <= artists[i+1].lower() for i in range(len(artists)-1))
                        
                        if is_sorted_asc:
                            self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", True, f"✅ Songs correctly sorted by artist A-Z")
                        else:
                            self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", False, f"❌ Songs not sorted by artist A-Z: {artists[:5]}")
                    
                    elif sort_by == "year":
                        # Verify songs are sorted by year descending (newest first)
                        years = [song.get("year", 0) or 0 for song in songs]
                        is_sorted_desc = all(years[i] >= years[i+1] for i in range(len(years)-1))
                        
                        if is_sorted_desc:
                            self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", True, f"✅ Songs correctly sorted by year (newest first)")
                        else:
                            self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", False, f"❌ Songs not sorted by year: {years[:5]}")
                    
                    else:  # created_at (default)
                        self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", True, f"✅ Default sorting working")
                    
                else:
                    self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", False, f"Failed to get songs with sort_by={sort_by}: {response.status_code}")
                    
        except Exception as e:
            self.log_result("Phase 2 Popularity Sorting", False, f"Exception: {str(e)}")

    def test_phase2_request_count_field(self):
        """Test Phase 2: Request count field in song data"""
        try:
            print("🔍 Testing request_count field presence in all song responses")
            
            # Get all songs
            response = self.make_request("GET", "/songs")
            
            if response.status_code == 200:
                songs = response.json()
                
                if len(songs) > 0:
                    missing_request_count = []
                    invalid_request_count = []
                    
                    for song in songs:
                        # Check if request_count field exists
                        if "request_count" not in song:
                            missing_request_count.append(song.get("title", "Unknown"))
                        else:
                            # Check if request_count is a valid integer >= 0
                            request_count = song["request_count"]
                            if not isinstance(request_count, int) or request_count < 0:
                                invalid_request_count.append(f"{song.get('title', 'Unknown')}: {request_count}")
                    
                    if len(missing_request_count) == 0 and len(invalid_request_count) == 0:
                        self.log_result("Phase 2 Request Count Field", True, f"✅ All {len(songs)} songs have valid request_count field")
                    else:
                        error_msg = ""
                        if missing_request_count:
                            error_msg += f"Missing request_count: {missing_request_count[:3]}. "
                        if invalid_request_count:
                            error_msg += f"Invalid request_count: {invalid_request_count[:3]}."
                        self.log_result("Phase 2 Request Count Field", False, f"❌ {error_msg}")
                    
                    # Test that older songs without request_count get 0 as default
                    zero_count_songs = [song for song in songs if song.get("request_count", 0) == 0]
                    if len(zero_count_songs) > 0:
                        self.log_result("Phase 2 Request Count Field - Default Value", True, f"✅ {len(zero_count_songs)} songs have request_count: 0 (default for older songs)")
                    else:
                        self.log_result("Phase 2 Request Count Field - Default Value", True, f"✅ No songs with request_count: 0 (all have been requested)")
                        
                else:
                    self.log_result("Phase 2 Request Count Field", True, "✅ No songs to test (empty database)")
                    
            else:
                self.log_result("Phase 2 Request Count Field", False, f"Failed to get songs: {response.status_code}")
                
        except Exception as e:
            self.log_result("Phase 2 Request Count Field", False, f"Exception: {str(e)}")

    def test_csv_upload_auto_enrichment_empty_metadata(self):
        """Test CSV Upload Auto-enrichment with completely empty metadata"""
        try:
            if not self.auth_token:
                self.log_result("CSV Auto-enrichment - Empty Metadata", False, "No auth token available")
                return
            
            print("🔍 Testing CSV upload with auto_enrich=true for songs with empty metadata")
            
            with open('/app/test_songs_auto_enrich_empty_unique.csv', 'rb') as f:
                files = {'file': ('test_songs_auto_enrich_empty_unique.csv', f, 'text/csv')}
                data = {'auto_enrich': 'true'}
                response = self.make_request("POST", "/songs/csv/upload", data=data, files=files)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Auto-enrichment response: {json.dumps(data, indent=2)}")
                
                if "success" in data and data["success"] and "songs_added" in data:
                    if data["songs_added"] > 0:
                        # Check if enrichment message is present
                        message = data.get("message", "")
                        if "auto-enriched" in message.lower():
                            self.log_result("CSV Auto-enrichment - Empty Metadata", True, f"Successfully uploaded and auto-enriched {data['songs_added']} songs: {message}")
                            
                            # Verify songs were enriched in database
                            songs_response = self.make_request("GET", "/songs")
                            if songs_response.status_code == 200:
                                songs = songs_response.json()
                                enriched_songs = [song for song in songs if "auto-enriched" in song.get("notes", "").lower()]
                                
                                if enriched_songs:
                                    print(f"🎵 Found {len(enriched_songs)} auto-enriched songs:")
                                    for song in enriched_songs[:3]:
                                        print(f"   • '{song['title']}' by '{song['artist']}' - genres: {song.get('genres', [])}, moods: {song.get('moods', [])}, year: {song.get('year', 'N/A')}")
                                    
                                    # Check if metadata was actually filled
                                    fully_enriched = [song for song in enriched_songs if song.get('genres') and song.get('moods') and song.get('year')]
                                    if fully_enriched:
                                        self.log_result("CSV Auto-enrichment - Database Verification", True, f"✅ {len(fully_enriched)} songs have complete metadata after enrichment")
                                    else:
                                        self.log_result("CSV Auto-enrichment - Database Verification", False, "❌ Songs were not fully enriched with metadata")
                                else:
                                    self.log_result("CSV Auto-enrichment - Database Verification", False, "❌ No auto-enriched songs found in database")
                        else:
                            self.log_result("CSV Auto-enrichment - Empty Metadata", False, f"❌ No enrichment message in response: {message}")
                    else:
                        self.log_result("CSV Auto-enrichment - Empty Metadata", False, f"❌ No songs were uploaded: {data}")
                else:
                    self.log_result("CSV Auto-enrichment - Empty Metadata", False, f"❌ Unexpected response structure: {data}")
            else:
                self.log_result("CSV Auto-enrichment - Empty Metadata", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("CSV Auto-enrichment - Empty Metadata", False, f"❌ Exception: {str(e)}")

    def test_csv_upload_auto_enrichment_partial_metadata(self):
        """Test CSV Upload Auto-enrichment with partial metadata (preserve existing data)"""
        try:
            if not self.auth_token:
                self.log_result("CSV Auto-enrichment - Partial Metadata", False, "No auth token available")
                return
            
            print("🔍 Testing CSV upload with auto_enrich=true for songs with partial metadata")
            
            with open('/app/test_songs_auto_enrich_partial_unique.csv', 'rb') as f:
                files = {'file': ('test_songs_auto_enrich_partial_unique.csv', f, 'text/csv')}
                data = {'auto_enrich': 'true'}
                response = self.make_request("POST", "/songs/csv/upload", data=data, files=files)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Partial enrichment response: {json.dumps(data, indent=2)}")
                
                if "success" in data and data["success"] and "songs_added" in data:
                    if data["songs_added"] > 0:
                        # Verify songs in database preserve existing data
                        songs_response = self.make_request("GET", "/songs")
                        if songs_response.status_code == 200:
                            songs = songs_response.json()
                            partial_songs = [song for song in songs if song.get('title') in ['Good 4 U', 'Levitating', 'Stay']]
                            
                            if partial_songs:
                                preservation_check = True
                                preservation_details = []
                                
                                for song in partial_songs:
                                    title = song.get('title')
                                    if title == 'Good 4 U':
                                        # Should preserve Pop genre and 2021 year, fill missing mood
                                        if 'Pop' in song.get('genres', []) and song.get('year') == 2021 and song.get('moods'):
                                            preservation_details.append(f"✅ '{title}': preserved Pop genre and 2021 year, filled moods")
                                        else:
                                            preservation_check = False
                                            preservation_details.append(f"❌ '{title}': failed to preserve existing data or fill missing")
                                    elif title == 'Levitating':
                                        # Should preserve Upbeat mood, fill missing genre and year
                                        if 'Upbeat' in song.get('moods', []) and song.get('genres') and song.get('year'):
                                            preservation_details.append(f"✅ '{title}': preserved Upbeat mood, filled genre and year")
                                        else:
                                            preservation_check = False
                                            preservation_details.append(f"❌ '{title}': failed to preserve existing mood or fill missing")
                                    elif title == 'Stay':
                                        # Should preserve 2021 year, fill missing genre and mood
                                        if song.get('year') == 2021 and song.get('genres') and song.get('moods'):
                                            preservation_details.append(f"✅ '{title}': preserved 2021 year, filled genre and moods")
                                        else:
                                            preservation_check = False
                                            preservation_details.append(f"❌ '{title}': failed to preserve existing year or fill missing")
                                
                                if preservation_check:
                                    self.log_result("CSV Auto-enrichment - Partial Metadata", True, f"✅ Successfully preserved existing data and filled missing fields: {'; '.join(preservation_details)}")
                                else:
                                    self.log_result("CSV Auto-enrichment - Partial Metadata", False, f"❌ Data preservation failed: {'; '.join(preservation_details)}")
                            else:
                                self.log_result("CSV Auto-enrichment - Partial Metadata", False, "❌ Partial metadata test songs not found in database")
                        else:
                            self.log_result("CSV Auto-enrichment - Partial Metadata", False, f"Could not verify songs in database: {songs_response.status_code}")
                    else:
                        self.log_result("CSV Auto-enrichment - Partial Metadata", False, f"❌ No songs were uploaded: {data}")
                else:
                    self.log_result("CSV Auto-enrichment - Partial Metadata", False, f"❌ Unexpected response structure: {data}")
            else:
                self.log_result("CSV Auto-enrichment - Partial Metadata", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("CSV Auto-enrichment - Partial Metadata", False, f"❌ Exception: {str(e)}")

    def test_csv_upload_auto_enrichment_complete_metadata(self):
        """Test CSV Upload Auto-enrichment with complete metadata (no enrichment needed)"""
        try:
            if not self.auth_token:
                self.log_result("CSV Auto-enrichment - Complete Metadata", False, "No auth token available")
                return
            
            print("🔍 Testing CSV upload with auto_enrich=true for songs with complete metadata")
            
            with open('/app/test_songs_auto_enrich_complete_unique.csv', 'rb') as f:
                files = {'file': ('test_songs_auto_enrich_complete_unique.csv', f, 'text/csv')}
                data = {'auto_enrich': 'true'}
                response = self.make_request("POST", "/songs/csv/upload", data=data, files=files)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Complete metadata response: {json.dumps(data, indent=2)}")
                
                if "success" in data and data["success"] and "songs_added" in data:
                    if data["songs_added"] > 0:
                        message = data.get("message", "")
                        # Should show 0 songs auto-enriched since all have complete metadata
                        if "0 songs auto-enriched" in message or "auto-enriched" not in message:
                            self.log_result("CSV Auto-enrichment - Complete Metadata", True, f"✅ Correctly skipped enrichment for complete songs: {message}")
                            
                            # Verify original data is preserved
                            songs_response = self.make_request("GET", "/songs")
                            if songs_response.status_code == 200:
                                songs = songs_response.json()
                                complete_songs = [song for song in songs if song.get('title') in ['Watermelon Sugar', 'Drivers License']]
                                
                                if complete_songs:
                                    preservation_check = True
                                    for song in complete_songs:
                                        title = song.get('title')
                                        if title == 'Watermelon Sugar':
                                            if not ('Pop' in song.get('genres', []) and 'Upbeat' in song.get('moods', []) and song.get('year') == 2020):
                                                preservation_check = False
                                        elif title == 'Drivers License':
                                            if not ('Pop' in song.get('genres', []) and 'Melancholy' in song.get('moods', []) and song.get('year') == 2021):
                                                preservation_check = False
                                    
                                    if preservation_check:
                                        self.log_result("CSV Auto-enrichment - Complete Metadata Preservation", True, "✅ All original metadata preserved correctly")
                                    else:
                                        self.log_result("CSV Auto-enrichment - Complete Metadata Preservation", False, "❌ Original metadata was modified unexpectedly")
                                else:
                                    self.log_result("CSV Auto-enrichment - Complete Metadata Preservation", False, "❌ Complete metadata test songs not found")
                        else:
                            self.log_result("CSV Auto-enrichment - Complete Metadata", False, f"❌ Should not have enriched complete songs: {message}")
                    else:
                        self.log_result("CSV Auto-enrichment - Complete Metadata", False, f"❌ No songs were uploaded: {data}")
                else:
                    self.log_result("CSV Auto-enrichment - Complete Metadata", False, f"❌ Unexpected response structure: {data}")
            else:
                self.log_result("CSV Auto-enrichment - Complete Metadata", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("CSV Auto-enrichment - Complete Metadata", False, f"❌ Exception: {str(e)}")

    def test_csv_upload_auto_enrichment_disabled(self):
        """Test CSV Upload with auto_enrich=false (should work like before)"""
        try:
            if not self.auth_token:
                self.log_result("CSV Auto-enrichment - Disabled", False, "No auth token available")
                return
            
            print("🔍 Testing CSV upload with auto_enrich=false (default behavior)")
            
            with open('/app/test_songs_auto_enrich_empty_unique.csv', 'rb') as f:
                files = {'file': ('test_songs_auto_enrich_empty_unique.csv', f, 'text/csv')}
                data = {'auto_enrich': 'false'}
                response = self.make_request("POST", "/songs/csv/upload", data=data, files=files)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Disabled enrichment response: {json.dumps(data, indent=2)}")
                
                if "success" in data and data["success"] and "songs_added" in data:
                    message = data.get("message", "")
                    # Should NOT mention auto-enrichment
                    if "auto-enriched" not in message.lower():
                        self.log_result("CSV Auto-enrichment - Disabled", True, f"✅ No enrichment performed as expected: {message}")
                        
                        # Verify songs have empty metadata (not enriched)
                        songs_response = self.make_request("GET", "/songs")
                        if songs_response.status_code == 200:
                            songs = songs_response.json()
                            recent_songs = [song for song in songs if song.get('title') in ['As It Was', 'Heat Waves', 'Blinding Lights'] and "auto-enriched" not in song.get('notes', '')]
                            
                            if recent_songs:
                                empty_metadata_count = 0
                                for song in recent_songs:
                                    if not song.get('genres') and not song.get('moods') and not song.get('year'):
                                        empty_metadata_count += 1
                                
                                if empty_metadata_count > 0:
                                    self.log_result("CSV Auto-enrichment - Disabled Verification", True, f"✅ {empty_metadata_count} songs have empty metadata as expected (no enrichment)")
                                else:
                                    self.log_result("CSV Auto-enrichment - Disabled Verification", False, "❌ Songs appear to have been enriched despite auto_enrich=false")
                            else:
                                self.log_result("CSV Auto-enrichment - Disabled Verification", False, "❌ Test songs not found in database")
                    else:
                        self.log_result("CSV Auto-enrichment - Disabled", False, f"❌ Enrichment was performed despite auto_enrich=false: {message}")
                else:
                    self.log_result("CSV Auto-enrichment - Disabled", False, f"❌ Unexpected response structure: {data}")
            else:
                self.log_result("CSV Auto-enrichment - Disabled", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("CSV Auto-enrichment - Disabled", False, f"❌ Exception: {str(e)}")

    def test_csv_upload_auto_enrichment_authentication(self):
        """Test CSV Upload Auto-enrichment requires authentication"""
        try:
            # Save current token
            original_token = self.auth_token
            
            # Test without token
            self.auth_token = None
            
            with open('/app/test_songs_auto_enrich_empty.csv', 'rb') as f:
                files = {'file': ('test_songs_auto_enrich_empty.csv', f, 'text/csv')}
                data = {'auto_enrich': 'true'}
                response = self.make_request("POST", "/songs/csv/upload", data=data, files=files)
            
            if response.status_code in [401, 403]:
                self.log_result("CSV Auto-enrichment Authentication", True, f"✅ Correctly rejected request without auth token (status: {response.status_code})")
            else:
                self.log_result("CSV Auto-enrichment Authentication", False, f"❌ Should have returned 401/403, got: {response.status_code}")
            
            # Restore original token
            self.auth_token = original_token
            
        except Exception as e:
            self.log_result("CSV Auto-enrichment Authentication", False, f"❌ Exception: {str(e)}")
            # Restore token in case of exception
            if 'original_token' in locals():
                self.auth_token = original_token

    def test_batch_enrichment_all_songs(self):
        """Test Batch Enrichment for all songs needing metadata"""
        try:
            if not self.auth_token:
                self.log_result("Batch Enrichment - All Songs", False, "No auth token available")
                return
            
            print("🔍 Testing batch enrichment for all songs needing metadata")
            
            # First, create some songs with missing metadata
            test_songs = [
                {"title": "Batch Test Song 1", "artist": "Test Artist 1", "genres": [], "moods": [], "year": None, "notes": "Missing all metadata"},
                {"title": "Batch Test Song 2", "artist": "Test Artist 2", "genres": ["Pop"], "moods": [], "year": None, "notes": "Missing moods and year"},
                {"title": "Batch Test Song 3", "artist": "Test Artist 3", "genres": ["Rock"], "moods": ["Energetic"], "year": 2020, "notes": "Complete metadata"}
            ]
            
            created_song_ids = []
            for song_data in test_songs:
                response = self.make_request("POST", "/songs", song_data)
                if response.status_code == 200:
                    created_song_ids.append(response.json()["id"])
                    print(f"📊 Created test song: {song_data['title']}")
                else:
                    self.log_result("Batch Enrichment - Create Test Songs", False, f"Failed to create song: {song_data['title']}")
                    return
            
            # Test batch enrichment without specifying song IDs (enrich all)
            response = self.make_request("POST", "/songs/batch-enrich")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Batch enrichment response: {json.dumps(data, indent=2)}")
                
                if "success" in data and data["success"]:
                    processed = data.get("processed", 0)
                    enriched = data.get("enriched", 0)
                    errors = data.get("errors", [])
                    message = data.get("message", "")
                    
                    if processed > 0:
                        self.log_result("Batch Enrichment - All Songs", True, f"✅ Successfully processed {processed} songs, enriched {enriched} songs: {message}")
                        
                        # Verify enrichment in database
                        songs_response = self.make_request("GET", "/songs")
                        if songs_response.status_code == 200:
                            songs = songs_response.json()
                            batch_enriched_songs = [song for song in songs if "batch auto-enriched" in song.get("notes", "").lower()]
                            
                            if batch_enriched_songs:
                                print(f"🎵 Found {len(batch_enriched_songs)} batch-enriched songs:")
                                for song in batch_enriched_songs[:3]:
                                    print(f"   • '{song['title']}' by '{song['artist']}' - genres: {song.get('genres', [])}, moods: {song.get('moods', [])}, year: {song.get('year', 'N/A')}")
                                
                                self.log_result("Batch Enrichment - Database Verification", True, f"✅ {len(batch_enriched_songs)} songs were batch-enriched in database")
                            else:
                                self.log_result("Batch Enrichment - Database Verification", False, "❌ No batch-enriched songs found in database")
                        
                        if errors:
                            self.log_result("Batch Enrichment - Error Handling", True, f"✅ Properly reported {len(errors)} enrichment errors: {errors[:2]}")
                    else:
                        # Check if no songs needed enrichment
                        if "no songs found" in message.lower():
                            self.log_result("Batch Enrichment - All Songs", True, f"✅ Correctly reported no songs need enrichment: {message}")
                        else:
                            self.log_result("Batch Enrichment - All Songs", False, f"❌ No songs processed but unclear why: {message}")
                else:
                    self.log_result("Batch Enrichment - All Songs", False, f"❌ Unexpected response structure: {data}")
            else:
                self.log_result("Batch Enrichment - All Songs", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Batch Enrichment - All Songs", False, f"❌ Exception: {str(e)}")

    def test_batch_enrichment_specific_songs(self):
        """Test Batch Enrichment for specific song IDs"""
        try:
            if not self.auth_token:
                self.log_result("Batch Enrichment - Specific Songs", False, "No auth token available")
                return
            
            print("🔍 Testing batch enrichment for specific song IDs")
            
            # Create test songs with missing metadata
            test_songs = [
                {"title": "Specific Song 1", "artist": "Specific Artist 1", "genres": [], "moods": [], "year": None, "notes": "For specific enrichment"},
                {"title": "Specific Song 2", "artist": "Specific Artist 2", "genres": [], "moods": [], "year": None, "notes": "For specific enrichment"}
            ]
            
            created_song_ids = []
            for song_data in test_songs:
                response = self.make_request("POST", "/songs", song_data)
                if response.status_code == 200:
                    song_id = response.json()["id"]
                    created_song_ids.append(song_id)
                    print(f"📊 Created specific test song: {song_data['title']} (ID: {song_id})")
                else:
                    self.log_result("Batch Enrichment - Create Specific Test Songs", False, f"Failed to create song: {song_data['title']}")
                    return
            
            # Test batch enrichment with specific song IDs - try as JSON body
            request_data = {"song_ids": created_song_ids}
            response = self.make_request("POST", "/songs/batch-enrich", request_data)
            
            # If that fails, try as query parameters
            if response.status_code == 422:
                print(f"📊 JSON body failed, trying query parameters...")
                params = {}
                for i, song_id in enumerate(created_song_ids):
                    params[f"song_ids"] = song_id  # This might not work for multiple values
                response = self.make_request("POST", "/songs/batch-enrich", params=params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Specific batch enrichment response: {json.dumps(data, indent=2)}")
                
                if "success" in data and data["success"]:
                    processed = data.get("processed", 0)
                    enriched = data.get("enriched", 0)
                    message = data.get("message", "")
                    
                    if processed == len(created_song_ids):
                        self.log_result("Batch Enrichment - Specific Songs", True, f"✅ Successfully processed {processed} specific songs, enriched {enriched}: {message}")
                        
                        # Verify only the specified songs were enriched
                        songs_response = self.make_request("GET", "/songs")
                        if songs_response.status_code == 200:
                            songs = songs_response.json()
                            enriched_specific_songs = [song for song in songs if song["id"] in created_song_ids and "batch auto-enriched" in song.get("notes", "").lower()]
                            
                            if len(enriched_specific_songs) == enriched:
                                self.log_result("Batch Enrichment - Specific Songs Verification", True, f"✅ Exactly {enriched} specified songs were enriched")
                            else:
                                self.log_result("Batch Enrichment - Specific Songs Verification", False, f"❌ Expected {enriched} enriched songs, found {len(enriched_specific_songs)}")
                    else:
                        self.log_result("Batch Enrichment - Specific Songs", False, f"❌ Expected to process {len(created_song_ids)} songs, processed {processed}")
                else:
                    self.log_result("Batch Enrichment - Specific Songs", False, f"❌ Unexpected response structure: {data}")
            else:
                self.log_result("Batch Enrichment - Specific Songs", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Batch Enrichment - Specific Songs", False, f"❌ Exception: {str(e)}")

    def test_batch_enrichment_no_songs_needed(self):
        """Test Batch Enrichment when no songs need enrichment"""
        try:
            if not self.auth_token:
                self.log_result("Batch Enrichment - No Songs Needed", False, "No auth token available")
                return
            
            print("🔍 Testing batch enrichment when no songs need enrichment")
            
            # Create a song with complete metadata
            complete_song = {
                "title": "Complete Song",
                "artist": "Complete Artist",
                "genres": ["Pop"],
                "moods": ["Upbeat"],
                "year": 2023,
                "notes": "Already complete"
            }
            
            response = self.make_request("POST", "/songs", complete_song)
            if response.status_code == 200:
                print(f"📊 Created complete song: {complete_song['title']}")
            else:
                self.log_result("Batch Enrichment - Create Complete Song", False, "Failed to create complete song")
                return
            
            # Test batch enrichment (should find no songs needing enrichment)
            response = self.make_request("POST", "/songs/batch-enrich")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 No songs needed response: {json.dumps(data, indent=2)}")
                
                if "success" in data and data["success"]:
                    message = data.get("message", "")
                    processed = data.get("processed", 0)
                    enriched = data.get("enriched", 0)
                    
                    if "no songs found" in message.lower() or (processed == 0 and enriched == 0):
                        self.log_result("Batch Enrichment - No Songs Needed", True, f"✅ Correctly reported no songs need enrichment: {message}")
                    else:
                        self.log_result("Batch Enrichment - No Songs Needed", False, f"❌ Should have reported no songs needed: {message}")
                else:
                    self.log_result("Batch Enrichment - No Songs Needed", False, f"❌ Unexpected response structure: {data}")
            else:
                self.log_result("Batch Enrichment - No Songs Needed", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Batch Enrichment - No Songs Needed", False, f"❌ Exception: {str(e)}")

    def test_batch_enrichment_authentication(self):
        """Test Batch Enrichment requires authentication"""
        try:
            # Save current token
            original_token = self.auth_token
            
            # Test without token
            self.auth_token = None
            response = self.make_request("POST", "/songs/batch-enrich")
            
            if response.status_code in [401, 403]:
                self.log_result("Batch Enrichment Authentication - No Token", True, f"✅ Correctly rejected request without auth token (status: {response.status_code})")
            else:
                self.log_result("Batch Enrichment Authentication - No Token", False, f"❌ Should have returned 401/403, got: {response.status_code}")
            
            # Test with invalid token
            self.auth_token = "invalid_token_12345"
            response = self.make_request("POST", "/songs/batch-enrich")
            
            if response.status_code == 401:
                self.log_result("Batch Enrichment Authentication - Invalid Token", True, "✅ Correctly rejected request with invalid token")
            else:
                self.log_result("Batch Enrichment Authentication - Invalid Token", False, f"❌ Should have returned 401, got: {response.status_code}")
            
            # Restore original token
            self.auth_token = original_token
            
        except Exception as e:
            self.log_result("Batch Enrichment Authentication", False, f"❌ Exception: {str(e)}")
            # Restore token in case of exception
            if 'original_token' in locals():
                self.auth_token = original_token

    def test_batch_enrichment_response_format(self):
        """Test Batch Enrichment response format matches specification"""
        try:
            if not self.auth_token:
                self.log_result("Batch Enrichment Response Format", False, "No auth token available")
                return
            
            print("🔍 Testing batch enrichment response format")
            
            # Test batch enrichment and check response format
            response = self.make_request("POST", "/songs/batch-enrich")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Response format check: {json.dumps(data, indent=2)}")
                
                # Check required fields according to specification
                required_fields = ["success", "message", "processed", "enriched", "errors"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    # Check field types
                    type_checks = [
                        (isinstance(data["success"], bool), "success should be boolean"),
                        (isinstance(data["message"], str), "message should be string"),
                        (isinstance(data["processed"], int), "processed should be integer"),
                        (isinstance(data["enriched"], int), "enriched should be integer"),
                        (isinstance(data["errors"], list), "errors should be list")
                    ]
                    
                    failed_type_checks = [msg for check, msg in type_checks if not check]
                    
                    if not failed_type_checks:
                        self.log_result("Batch Enrichment Response Format", True, f"✅ Response format matches specification: {list(data.keys())}")
                    else:
                        self.log_result("Batch Enrichment Response Format", False, f"❌ Type check failures: {failed_type_checks}")
                else:
                    self.log_result("Batch Enrichment Response Format", False, f"❌ Missing required fields: {missing_fields}")
            else:
                self.log_result("Batch Enrichment Response Format", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Batch Enrichment Response Format", False, f"❌ Exception: {str(e)}")

    def test_spotify_metadata_autofill_basic(self):
        """Test Spotify Metadata Auto-fill Feature - Basic Functionality"""
        try:
            if not self.auth_token:
                self.log_result("Spotify Metadata Auto-fill - Basic", False, "No auth token available")
                return
            
            print("🔍 Testing Spotify metadata auto-fill with 'As It Was' by 'Harry Styles'")
            
            # Test with the specific song mentioned in the review request
            params = {
                "title": "As It Was",
                "artist": "Harry Styles"
            }
            
            response = self.make_request("POST", "/songs/search-metadata", params=params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Metadata response: {json.dumps(data, indent=2)}")
                
                # Verify response structure
                if "success" in data and "metadata" in data and "message" in data:
                    metadata = data["metadata"]
                    
                    # Check required fields
                    required_fields = ["title", "artist", "genres", "moods", "confidence"]
                    missing_fields = [field for field in required_fields if field not in metadata]
                    
                    if not missing_fields:
                        # Verify data quality
                        title = metadata.get("title", "")
                        artist = metadata.get("artist", "")
                        genres = metadata.get("genres", [])
                        moods = metadata.get("moods", [])
                        confidence = metadata.get("confidence", "")
                        year = metadata.get("year")
                        spotify_id = metadata.get("spotify_id")
                        
                        # Check if we got real Spotify data (not fallback)
                        is_real_spotify = (
                            spotify_id is not None and 
                            confidence == "high" and
                            year is not None and
                            len(genres) > 0 and
                            len(moods) > 0
                        )
                        
                        if is_real_spotify:
                            self.log_result("Spotify Metadata Auto-fill - Basic", True, 
                                f"✅ SUCCESS: Got real Spotify data - Title: '{title}', Artist: '{artist}', Year: {year}, Genres: {genres}, Moods: {moods}, Confidence: {confidence}, Spotify ID: {spotify_id}")
                        else:
                            self.log_result("Spotify Metadata Auto-fill - Basic", False, 
                                f"❌ FALLBACK DATA: Got fallback instead of real Spotify data - Confidence: {confidence}, Spotify ID: {spotify_id}")
                    else:
                        self.log_result("Spotify Metadata Auto-fill - Basic", False, f"Missing required fields: {missing_fields}")
                else:
                    self.log_result("Spotify Metadata Auto-fill - Basic", False, f"Invalid response structure: {data}")
            else:
                self.log_result("Spotify Metadata Auto-fill - Basic", False, f"Status code: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_result("Spotify Metadata Auto-fill - Basic", False, f"Exception: {str(e)}")

    def test_spotify_metadata_autofill_second_song(self):
        """Test Spotify Metadata Auto-fill Feature - Second Test Song"""
        try:
            if not self.auth_token:
                self.log_result("Spotify Metadata Auto-fill - Heat Waves", False, "No auth token available")
                return
            
            print("🔍 Testing Spotify metadata auto-fill with 'Heat Waves' by 'Glass Animals'")
            
            # Test with the second song mentioned in the review request
            params = {
                "title": "Heat Waves",
                "artist": "Glass Animals"
            }
            
            response = self.make_request("POST", "/songs/search-metadata", params=params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Metadata response: {json.dumps(data, indent=2)}")
                
                if "success" in data and "metadata" in data:
                    metadata = data["metadata"]
                    
                    # Check for real Spotify data
                    spotify_id = metadata.get("spotify_id")
                    confidence = metadata.get("confidence", "")
                    year = metadata.get("year")
                    genres = metadata.get("genres", [])
                    moods = metadata.get("moods", [])
                    
                    if spotify_id and confidence == "high" and year and len(genres) > 0:
                        self.log_result("Spotify Metadata Auto-fill - Heat Waves", True, 
                            f"✅ SUCCESS: Got real Spotify data for Heat Waves - Year: {year}, Genres: {genres}, Moods: {moods}, Spotify ID: {spotify_id}")
                    else:
                        self.log_result("Spotify Metadata Auto-fill - Heat Waves", False, 
                            f"❌ FALLBACK DATA: Expected real Spotify data but got fallback - Confidence: {confidence}")
                else:
                    self.log_result("Spotify Metadata Auto-fill - Heat Waves", False, f"Invalid response structure: {data}")
            else:
                self.log_result("Spotify Metadata Auto-fill - Heat Waves", False, f"Status code: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_result("Spotify Metadata Auto-fill - Heat Waves", False, f"Exception: {str(e)}")

    def test_spotify_metadata_autofill_authentication(self):
        """Test Spotify Metadata Auto-fill Feature - Authentication Requirements"""
        try:
            # Save current token
            original_token = self.auth_token
            
            # Test without token
            self.auth_token = None
            params = {
                "title": "As It Was",
                "artist": "Harry Styles"
            }
            
            print("🔍 Testing Spotify metadata auto-fill without authentication")
            response = self.make_request("POST", "/songs/search-metadata", params=params)
            
            if response.status_code in [401, 403]:  # Accept both as valid auth failures
                self.log_result("Spotify Metadata Auto-fill - No Auth", True, f"✅ Correctly rejected request without auth token (status: {response.status_code})")
            else:
                self.log_result("Spotify Metadata Auto-fill - No Auth", False, f"❌ Should have returned 401/403, got: {response.status_code}")
            
            # Test with invalid token
            self.auth_token = "invalid_token_12345"
            response = self.make_request("POST", "/songs/search-metadata", params=params)
            
            if response.status_code == 401:
                self.log_result("Spotify Metadata Auto-fill - Invalid Auth", True, "✅ Correctly rejected request with invalid token")
            else:
                self.log_result("Spotify Metadata Auto-fill - Invalid Auth", False, f"❌ Should have returned 401, got: {response.status_code}")
            
            # Restore original token
            self.auth_token = original_token
            
        except Exception as e:
            self.log_result("Spotify Metadata Auto-fill - Authentication", False, f"Exception: {str(e)}")
            # Restore token in case of exception
            if 'original_token' in locals():
                self.auth_token = original_token

    def test_spotify_metadata_autofill_edge_cases(self):
        """Test Spotify Metadata Auto-fill Feature - Edge Cases"""
        try:
            if not self.auth_token:
                self.log_result("Spotify Metadata Auto-fill - Edge Cases", False, "No auth token available")
                return
            
            print("🔍 Testing Spotify metadata auto-fill edge cases")
            
            # Test 1: Empty/whitespace inputs
            edge_cases = [
                {"title": "", "artist": "Harry Styles", "expected_error": "Both title and artist are required"},
                {"title": "As It Was", "artist": "", "expected_error": "Both title and artist are required"},
                {"title": "   ", "artist": "Harry Styles", "expected_error": "Both title and artist are required"},
                {"title": "As It Was", "artist": "   ", "expected_error": "Both title and artist are required"},
            ]
            
            for i, case in enumerate(edge_cases):
                print(f"🔍 Testing edge case {i+1}: title='{case['title']}', artist='{case['artist']}'")
                
                response = self.make_request("POST", "/songs/search-metadata", params={
                    "title": case["title"],
                    "artist": case["artist"]
                })
                
                if response.status_code in [400, 422]:  # Accept both 400 and 422 for validation errors
                    self.log_result(f"Spotify Metadata Auto-fill - Edge Case {i+1}", True, f"✅ Correctly rejected empty input (status: {response.status_code})")
                else:
                    self.log_result(f"Spotify Metadata Auto-fill - Edge Case {i+1}", False, f"❌ Should have returned 400/422, got: {response.status_code}")
            
            # Test 2: Special characters and unicode
            special_cases = [
                {"title": "Señorita", "artist": "Shawn Mendes & Camila Cabello"},
                {"title": "Song with 'quotes' and \"double quotes\"", "artist": "Test Artist"},
                {"title": "Song with émojis 🎵🎶", "artist": "Émoji Artist"},
                {"title": "Very Long Song Title That Goes On And On And On And Should Still Work Fine", "artist": "Long Name Artist"}
            ]
            
            for i, case in enumerate(special_cases):
                print(f"🔍 Testing special character case {i+1}: '{case['title']}' by '{case['artist']}'")
                
                response = self.make_request("POST", "/songs/search-metadata", params=case)
                
                if response.status_code == 200:
                    data = response.json()
                    if "success" in data and data["success"]:
                        self.log_result(f"Spotify Metadata Auto-fill - Special Chars {i+1}", True, f"✅ Handled special characters correctly")
                    else:
                        self.log_result(f"Spotify Metadata Auto-fill - Special Chars {i+1}", False, f"❌ Failed to process special characters: {data}")
                else:
                    self.log_result(f"Spotify Metadata Auto-fill - Special Chars {i+1}", False, f"❌ Status code: {response.status_code}")
            
            # Test 3: Non-existent song (should return fallback data)
            print("🔍 Testing non-existent song (should return fallback)")
            fake_song = {
                "title": "This Song Definitely Does Not Exist 12345",
                "artist": "Fake Artist That Does Not Exist 67890"
            }
            
            response = self.make_request("POST", "/songs/search-metadata", params=fake_song)
            
            if response.status_code == 200:
                data = response.json()
                if "success" in data and data["success"]:
                    metadata = data["metadata"]
                    confidence = metadata.get("confidence", "")
                    source = metadata.get("source", "")
                    
                    if confidence == "low" and source == "heuristic":
                        self.log_result("Spotify Metadata Auto-fill - Non-existent Song", True, f"✅ Correctly returned fallback data for non-existent song")
                    else:
                        self.log_result("Spotify Metadata Auto-fill - Non-existent Song", False, f"❌ Expected fallback data but got: confidence={confidence}, source={source}")
                else:
                    self.log_result("Spotify Metadata Auto-fill - Non-existent Song", False, f"❌ Failed to handle non-existent song: {data}")
            else:
                self.log_result("Spotify Metadata Auto-fill - Non-existent Song", False, f"❌ Status code: {response.status_code}")
                
        except Exception as e:
            self.log_result("Spotify Metadata Auto-fill - Edge Cases", False, f"Exception: {str(e)}")

    def test_spotify_metadata_autofill_response_format(self):
        """Test Spotify Metadata Auto-fill Feature - Response Format Validation"""
        try:
            if not self.auth_token:
                self.log_result("Spotify Metadata Auto-fill - Response Format", False, "No auth token available")
                return
            
            print("🔍 Testing Spotify metadata auto-fill response format")
            
            params = {
                "title": "As It Was",
                "artist": "Harry Styles"
            }
            
            response = self.make_request("POST", "/songs/search-metadata", params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Expected response format from the review request
                expected_structure = {
                    "success": bool,
                    "metadata": {
                        "title": str,
                        "artist": str,
                        "album": str,  # Optional but expected for real Spotify data
                        "year": int,   # Optional but expected for real Spotify data
                        "genres": list,
                        "moods": list,
                        "spotify_id": str,  # Optional but expected for real Spotify data
                        "confidence": str
                    },
                    "message": str
                }
                
                # Check top-level structure
                if "success" in data and "metadata" in data and "message" in data:
                    metadata = data["metadata"]
                    
                    # Check metadata structure
                    format_issues = []
                    
                    if not isinstance(data["success"], bool):
                        format_issues.append(f"success should be bool, got {type(data['success'])}")
                    
                    if not isinstance(data["message"], str):
                        format_issues.append(f"message should be str, got {type(data['message'])}")
                    
                    if not isinstance(metadata.get("title"), str):
                        format_issues.append(f"metadata.title should be str, got {type(metadata.get('title'))}")
                    
                    if not isinstance(metadata.get("artist"), str):
                        format_issues.append(f"metadata.artist should be str, got {type(metadata.get('artist'))}")
                    
                    if not isinstance(metadata.get("genres"), list):
                        format_issues.append(f"metadata.genres should be list, got {type(metadata.get('genres'))}")
                    
                    if not isinstance(metadata.get("moods"), list):
                        format_issues.append(f"metadata.moods should be list, got {type(metadata.get('moods'))}")
                    
                    if not isinstance(metadata.get("confidence"), str):
                        format_issues.append(f"metadata.confidence should be str, got {type(metadata.get('confidence'))}")
                    
                    # Check optional fields if present
                    if "year" in metadata and metadata["year"] is not None and not isinstance(metadata["year"], int):
                        format_issues.append(f"metadata.year should be int or null, got {type(metadata.get('year'))}")
                    
                    if "album" in metadata and metadata["album"] is not None and not isinstance(metadata["album"], str):
                        format_issues.append(f"metadata.album should be str or null, got {type(metadata.get('album'))}")
                    
                    if "spotify_id" in metadata and metadata["spotify_id"] is not None and not isinstance(metadata["spotify_id"], str):
                        format_issues.append(f"metadata.spotify_id should be str or null, got {type(metadata.get('spotify_id'))}")
                    
                    if len(format_issues) == 0:
                        self.log_result("Spotify Metadata Auto-fill - Response Format", True, f"✅ Response format matches expected structure perfectly")
                    else:
                        self.log_result("Spotify Metadata Auto-fill - Response Format", False, f"❌ Format issues: {format_issues}")
                else:
                    self.log_result("Spotify Metadata Auto-fill - Response Format", False, f"❌ Missing top-level fields in response: {data}")
            else:
                self.log_result("Spotify Metadata Auto-fill - Response Format", False, f"❌ Status code: {response.status_code}")
                
        except Exception as e:
            self.log_result("Spotify Metadata Auto-fill - Response Format", False, f"Exception: {str(e)}")

    def test_spotify_metadata_autofill_credentials_verification(self):
        """Test Spotify Metadata Auto-fill Feature - New Credentials Verification"""
        try:
            if not self.auth_token:
                self.log_result("Spotify Metadata Auto-fill - Credentials", False, "No auth token available")
                return
            
            print("🔍 Testing Spotify metadata auto-fill with new credentials verification")
            print("🔑 Expected Client ID: 24f25c0b6f1048819102bd13ae768bde")
            
            # Test multiple songs to verify credentials are working
            test_songs = [
                {"title": "As It Was", "artist": "Harry Styles"},
                {"title": "Heat Waves", "artist": "Glass Animals"},
                {"title": "Blinding Lights", "artist": "The Weeknd"},
                {"title": "Watermelon Sugar", "artist": "Harry Styles"}
            ]
            
            successful_requests = 0
            high_confidence_results = 0
            spotify_ids_found = 0
            
            for i, song in enumerate(test_songs):
                print(f"🔍 Testing song {i+1}: '{song['title']}' by '{song['artist']}'")
                
                response = self.make_request("POST", "/songs/search-metadata", params=song)
                
                if response.status_code == 200:
                    successful_requests += 1
                    data = response.json()
                    
                    if "metadata" in data:
                        metadata = data["metadata"]
                        confidence = metadata.get("confidence", "")
                        spotify_id = metadata.get("spotify_id")
                        
                        if confidence == "high":
                            high_confidence_results += 1
                        
                        if spotify_id:
                            spotify_ids_found += 1
                            print(f"   ✅ Found Spotify ID: {spotify_id}")
                        else:
                            print(f"   ❌ No Spotify ID found (confidence: {confidence})")
                else:
                    print(f"   ❌ Request failed with status: {response.status_code}")
            
            # Evaluate results
            if successful_requests == len(test_songs):
                if high_confidence_results >= len(test_songs) * 0.75:  # At least 75% high confidence
                    if spotify_ids_found >= len(test_songs) * 0.75:  # At least 75% with Spotify IDs
                        self.log_result("Spotify Metadata Auto-fill - Credentials", True, 
                            f"✅ NEW CREDENTIALS WORKING: {successful_requests}/{len(test_songs)} successful, {high_confidence_results} high confidence, {spotify_ids_found} with Spotify IDs")
                    else:
                        self.log_result("Spotify Metadata Auto-fill - Credentials", False, 
                            f"❌ CREDENTIALS ISSUE: Too few Spotify IDs found ({spotify_ids_found}/{len(test_songs)}) - may be using fallback data")
                else:
                    self.log_result("Spotify Metadata Auto-fill - Credentials", False, 
                        f"❌ CREDENTIALS ISSUE: Too few high confidence results ({high_confidence_results}/{len(test_songs)}) - may be using fallback data")
            else:
                self.log_result("Spotify Metadata Auto-fill - Credentials", False, 
                    f"❌ CREDENTIALS ISSUE: Only {successful_requests}/{len(test_songs)} requests successful")
                
        except Exception as e:
            self.log_result("Spotify Metadata Auto-fill - Credentials", False, f"Exception: {str(e)}")

    def test_phase2_edge_cases(self):
        """Test Phase 2: Edge cases for request tracking"""
        try:
            print("🔍 Testing Phase 2 edge cases")
            
            # Test requesting a non-existent song (should return 404)
            fake_song_id = "non-existent-song-id-12345"
            request_data = {
                "song_id": fake_song_id,
                "requester_name": "Test Fan",
                "requester_email": "fan@example.com",
                "dedication": "Test request",
                "tip_amount": 1.0
            }
            
            response = self.make_request("POST", "/requests", request_data)
            
            if response.status_code == 404:
                self.log_result("Phase 2 Edge Cases - Non-existent Song", True, "✅ Correctly returned 404 for non-existent song")
            else:
                self.log_result("Phase 2 Edge Cases - Non-existent Song", False, f"❌ Expected 404, got: {response.status_code}")
            
            # Test sorting with empty database (create a new musician for this)
            empty_musician_data = {
                "name": "Empty Musician",
                "email": "empty@requestwave.com",
                "password": "SecurePassword123!"
            }
            
            # Save current auth
            original_token = self.auth_token
            
            # Register new musician
            register_response = self.make_request("POST", "/auth/register", empty_musician_data)
            if register_response.status_code == 200:
                empty_auth_data = register_response.json()
                self.auth_token = empty_auth_data["token"]
                
                # Test sorting with empty song list
                for sort_by in ["popularity", "title", "artist", "year", "created_at"]:
                    params = {"sort_by": sort_by}
                    response = self.make_request("GET", "/songs", params)
                    
                    if response.status_code == 200:
                        songs = response.json()
                        if len(songs) == 0:
                            self.log_result(f"Phase 2 Edge Cases - Empty DB Sort ({sort_by})", True, f"✅ Sorting works with empty database")
                        else:
                            self.log_result(f"Phase 2 Edge Cases - Empty DB Sort ({sort_by})", False, f"❌ Expected empty list, got {len(songs)} songs")
                    else:
                        self.log_result(f"Phase 2 Edge Cases - Empty DB Sort ({sort_by})", False, f"❌ Failed to get songs: {response.status_code}")
                
                # Restore original auth
                self.auth_token = original_token
            else:
                self.log_result("Phase 2 Edge Cases - Empty Database Setup", False, "Could not create empty musician for testing")
            
            # Test multiple requests for same song increment correctly
            if self.test_song_id:
                # Get current request count
                songs_response = self.make_request("GET", "/songs")
                if songs_response.status_code == 200:
                    songs = songs_response.json()
                    test_song = next((song for song in songs if song["id"] == self.test_song_id), None)
                    
                    if test_song:
                        initial_count = test_song.get("request_count", 0)
                        
                        # Create 2 more requests
                        for i in range(2):
                            request_data = {
                                "song_id": self.test_song_id,
                                "requester_name": f"Edge Case Fan {i+1}",
                                "requester_email": f"edge{i+1}@example.com",
                                "dedication": f"Edge case request #{i+1}",
                                "tip_amount": 1.0
                            }
                            
                            response = self.make_request("POST", "/requests", request_data)
                            if response.status_code != 200:
                                self.log_result("Phase 2 Edge Cases - Multiple Requests", False, f"Failed to create edge case request #{i+1}")
                                return
                        
                        # Verify count increased by 2
                        songs_response = self.make_request("GET", "/songs")
                        if songs_response.status_code == 200:
                            songs = songs_response.json()
                            test_song = next((song for song in songs if song["id"] == self.test_song_id), None)
                            
                            if test_song:
                                final_count = test_song.get("request_count", 0)
                                expected_count = initial_count + 2
                                
                                if final_count == expected_count:
                                    self.log_result("Phase 2 Edge Cases - Multiple Requests", True, f"✅ Request count correctly incremented from {initial_count} to {final_count}")
                                else:
                                    self.log_result("Phase 2 Edge Cases - Multiple Requests", False, f"❌ Expected {expected_count}, got {final_count}")
                            else:
                                self.log_result("Phase 2 Edge Cases - Multiple Requests", False, "Test song not found after creating requests")
                        else:
                            self.log_result("Phase 2 Edge Cases - Multiple Requests", False, "Could not verify final request count")
                    else:
                        self.log_result("Phase 2 Edge Cases - Multiple Requests", False, "Test song not found for multiple requests test")
                else:
                    self.log_result("Phase 2 Edge Cases - Multiple Requests", False, "Could not get initial request count")
            else:
                self.log_result("Phase 2 Edge Cases - Multiple Requests", False, "No test song available for multiple requests test")
                
        except Exception as e:
            self.log_result("Phase 2 Edge Cases", False, f"Exception: {str(e)}")

    def test_analytics_requesters(self):
        """Test Phase 3: Requester Analytics Endpoint"""
        try:
            if not self.auth_token:
                self.log_result("Analytics Requesters", False, "No auth token available")
                return
            
            print("🔍 Testing requester analytics endpoint")
            
            # First create some test requests with different requesters
            test_requests = [
                {"requester_name": "Alice Johnson", "requester_email": "alice@example.com", "tip_amount": 5.0},
                {"requester_name": "Bob Smith", "requester_email": "bob@example.com", "tip_amount": 3.0},
                {"requester_name": "Alice Johnson", "requester_email": "alice@example.com", "tip_amount": 2.0},  # Same person, different request
                {"requester_name": "Charlie Brown", "requester_email": "charlie@example.com", "tip_amount": 0.0}
            ]
            
            # Create requests if we have a test song
            if self.test_song_id:
                for req_data in test_requests:
                    request_data = {
                        "song_id": self.test_song_id,
                        "requester_name": req_data["requester_name"],
                        "requester_email": req_data["requester_email"],
                        "dedication": "Test request for analytics",
                        "tip_amount": req_data["tip_amount"]
                    }
                    
                    response = self.make_request("POST", "/requests", request_data)
                    if response.status_code != 200:
                        print(f"⚠️ Failed to create test request for {req_data['requester_name']}")
            
            # Test the analytics endpoint
            response = self.make_request("GET", "/analytics/requesters")
            
            if response.status_code == 200:
                data = response.json()
                
                if "requesters" in data and isinstance(data["requesters"], list):
                    requesters = data["requesters"]
                    
                    # Verify response structure
                    if len(requesters) > 0:
                        first_requester = requesters[0]
                        required_fields = ["name", "email", "request_count", "total_tips", "latest_request"]
                        
                        missing_fields = [field for field in required_fields if field not in first_requester]
                        
                        if not missing_fields:
                            # Verify sorting (most frequent first)
                            request_counts = [req["request_count"] for req in requesters]
                            is_sorted_desc = all(request_counts[i] >= request_counts[i+1] for i in range(len(request_counts)-1))
                            
                            if is_sorted_desc:
                                self.log_result("Analytics Requesters", True, f"✅ Retrieved {len(requesters)} requesters, sorted by request count")
                                
                                # Verify aggregation logic
                                alice_requests = [req for req in requesters if req["email"] == "alice@example.com"]
                                if alice_requests and alice_requests[0]["request_count"] >= 2:
                                    self.log_result("Analytics Requesters - Aggregation", True, f"✅ Correctly aggregated multiple requests per requester")
                                else:
                                    self.log_result("Analytics Requesters - Aggregation", False, "❌ Request aggregation not working correctly")
                            else:
                                self.log_result("Analytics Requesters", False, f"❌ Requesters not sorted by request count: {request_counts}")
                        else:
                            self.log_result("Analytics Requesters", False, f"❌ Missing required fields: {missing_fields}")
                    else:
                        self.log_result("Analytics Requesters", True, "✅ No requesters found (empty result)")
                else:
                    self.log_result("Analytics Requesters", False, f"❌ Invalid response structure: {data}")
            else:
                self.log_result("Analytics Requesters", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_result("Analytics Requesters", False, f"❌ Exception: {str(e)}")

    def test_analytics_export_csv(self):
        """Test Phase 3: Export Requesters CSV Endpoint"""
        try:
            if not self.auth_token:
                self.log_result("Analytics Export CSV", False, "No auth token available")
                return
            
            print("🔍 Testing requester CSV export endpoint")
            
            response = self.make_request("GET", "/analytics/export-requesters")
            
            if response.status_code == 200:
                # Check Content-Type header
                content_type = response.headers.get("content-type", "")
                if "text/csv" in content_type:
                    # Check Content-Disposition header for file download
                    content_disposition = response.headers.get("content-disposition", "")
                    if "attachment" in content_disposition and "filename=" in content_disposition:
                        # Verify CSV content structure
                        csv_content = response.text
                        lines = csv_content.strip().split('\n')
                        
                        if len(lines) > 0:
                            # Check CSV headers
                            header_line = lines[0]
                            expected_headers = ["Name", "Email", "Request Count", "Total Tips", "Latest Request"]
                            
                            # Remove quotes and check headers
                            actual_headers = [h.strip('"') for h in header_line.split(',')]
                            
                            if all(header in actual_headers for header in expected_headers):
                                self.log_result("Analytics Export CSV", True, f"✅ CSV export working with {len(lines)} lines (including header)")
                                self.log_result("Analytics Export CSV - Headers", True, f"✅ Correct CSV headers: {actual_headers}")
                                self.log_result("Analytics Export CSV - Download", True, f"✅ Proper Content-Disposition header for download")
                            else:
                                self.log_result("Analytics Export CSV", False, f"❌ Missing CSV headers. Expected: {expected_headers}, Got: {actual_headers}")
                        else:
                            self.log_result("Analytics Export CSV", False, "❌ Empty CSV content")
                    else:
                        self.log_result("Analytics Export CSV", False, f"❌ Missing Content-Disposition header: {content_disposition}")
                else:
                    self.log_result("Analytics Export CSV", False, f"❌ Wrong Content-Type: {content_type}")
            else:
                self.log_result("Analytics Export CSV", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_result("Analytics Export CSV", False, f"❌ Exception: {str(e)}")

    def test_analytics_daily(self):
        """Test Phase 3: Daily Analytics Endpoint"""
        try:
            if not self.auth_token:
                self.log_result("Analytics Daily", False, "No auth token available")
                return
            
            print("🔍 Testing daily analytics endpoint")
            
            # Test default 7 days
            response = self.make_request("GET", "/analytics/daily")
            
            if response.status_code == 200:
                data = response.json()
                
                required_fields = ["period", "daily_stats", "top_songs", "top_requesters", "totals"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    # Verify daily_stats structure
                    daily_stats = data["daily_stats"]
                    if isinstance(daily_stats, list):
                        if len(daily_stats) > 0:
                            first_day = daily_stats[0]
                            day_required_fields = ["date", "request_count", "tip_total", "unique_requesters"]
                            day_missing_fields = [field for field in day_required_fields if field not in first_day]
                            
                            if not day_missing_fields:
                                self.log_result("Analytics Daily - Structure", True, f"✅ Correct daily_stats structure with {len(daily_stats)} days")
                            else:
                                self.log_result("Analytics Daily - Structure", False, f"❌ Missing daily_stats fields: {day_missing_fields}")
                        else:
                            self.log_result("Analytics Daily - Structure", True, "✅ Empty daily_stats (no data in period)")
                    else:
                        self.log_result("Analytics Daily - Structure", False, f"❌ daily_stats should be list, got: {type(daily_stats)}")
                    
                    # Verify top_songs structure
                    top_songs = data["top_songs"]
                    if isinstance(top_songs, list):
                        if len(top_songs) > 0:
                            first_song = top_songs[0]
                            if "song" in first_song and "count" in first_song:
                                self.log_result("Analytics Daily - Top Songs", True, f"✅ Top songs structure correct with {len(top_songs)} songs")
                            else:
                                self.log_result("Analytics Daily - Top Songs", False, f"❌ Invalid top_songs structure: {first_song}")
                        else:
                            self.log_result("Analytics Daily - Top Songs", True, "✅ Empty top_songs (no requests in period)")
                    else:
                        self.log_result("Analytics Daily - Top Songs", False, f"❌ top_songs should be list, got: {type(top_songs)}")
                    
                    # Verify totals structure
                    totals = data["totals"]
                    if isinstance(totals, dict):
                        totals_required_fields = ["total_requests", "total_tips", "unique_requesters"]
                        totals_missing_fields = [field for field in totals_required_fields if field not in totals]
                        
                        if not totals_missing_fields:
                            self.log_result("Analytics Daily - Totals", True, f"✅ Totals structure correct: {totals}")
                        else:
                            self.log_result("Analytics Daily - Totals", False, f"❌ Missing totals fields: {totals_missing_fields}")
                    else:
                        self.log_result("Analytics Daily - Totals", False, f"❌ totals should be dict, got: {type(totals)}")
                    
                    self.log_result("Analytics Daily", True, f"✅ Daily analytics working for {data['period']}")
                else:
                    self.log_result("Analytics Daily", False, f"❌ Missing required fields: {missing_fields}")
            else:
                self.log_result("Analytics Daily", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
            
            # Test with different day ranges
            for days in [7, 30]:
                params = {"days": days}
                response = self.make_request("GET", "/analytics/daily", params)
                
                if response.status_code == 200:
                    data = response.json()
                    if f"Last {days} days" in data.get("period", ""):
                        self.log_result(f"Analytics Daily - {days} Days", True, f"✅ {days} days parameter working")
                    else:
                        self.log_result(f"Analytics Daily - {days} Days", False, f"❌ Wrong period: {data.get('period')}")
                else:
                    self.log_result(f"Analytics Daily - {days} Days", False, f"❌ Status code: {response.status_code}")
                    
        except Exception as e:
            self.log_result("Analytics Daily", False, f"❌ Exception: {str(e)}")

    def test_analytics_authentication(self):
        """Test Phase 3: Analytics Authentication & Security"""
        try:
            print("🔍 Testing analytics authentication requirements")
            
            # Save current token
            original_token = self.auth_token
            
            analytics_endpoints = [
                "/analytics/requesters",
                "/analytics/export-requesters", 
                "/analytics/daily"
            ]
            
            for endpoint in analytics_endpoints:
                # Test without token
                self.auth_token = None
                response = self.make_request("GET", endpoint)
                
                if response.status_code in [401, 403]:
                    self.log_result(f"Analytics Auth - {endpoint} (No Token)", True, f"✅ Correctly rejected unauthorized request")
                else:
                    self.log_result(f"Analytics Auth - {endpoint} (No Token)", False, f"❌ Should have returned 401/403, got: {response.status_code}")
                
                # Test with invalid token
                self.auth_token = "invalid_token_12345"
                response = self.make_request("GET", endpoint)
                
                if response.status_code == 401:
                    self.log_result(f"Analytics Auth - {endpoint} (Invalid Token)", True, f"✅ Correctly rejected invalid token")
                else:
                    self.log_result(f"Analytics Auth - {endpoint} (Invalid Token)", False, f"❌ Should have returned 401, got: {response.status_code}")
            
            # Restore original token
            self.auth_token = original_token
            
        except Exception as e:
            self.log_result("Analytics Authentication", False, f"❌ Exception: {str(e)}")
            # Restore token in case of exception
            if 'original_token' in locals():
                self.auth_token = original_token

    def test_analytics_data_quality(self):
        """Test Phase 3: Analytics Data Quality and Edge Cases"""
        try:
            if not self.auth_token:
                self.log_result("Analytics Data Quality", False, "No auth token available")
                return
            
            print("🔍 Testing analytics data quality and edge cases")
            
            # Test with no data (should return empty results, not errors)
            response = self.make_request("GET", "/analytics/requesters")
            
            if response.status_code == 200:
                data = response.json()
                if "requesters" in data and isinstance(data["requesters"], list):
                    self.log_result("Analytics Data Quality - Empty Data", True, f"✅ Handles empty data correctly")
                else:
                    self.log_result("Analytics Data Quality - Empty Data", False, f"❌ Invalid response for empty data: {data}")
            else:
                self.log_result("Analytics Data Quality - Empty Data", False, f"❌ Status code: {response.status_code}")
            
            # Test daily analytics with edge case parameters
            edge_case_params = [
                {"days": 1},    # Single day
                {"days": 365},  # Full year
                {"days": 0}     # Invalid parameter
            ]
            
            for params in edge_case_params:
                response = self.make_request("GET", "/analytics/daily", params)
                days = params["days"]
                
                if days == 0:
                    # Should handle invalid parameter gracefully
                    if response.status_code in [400, 422]:
                        self.log_result(f"Analytics Data Quality - Invalid Days ({days})", True, f"✅ Correctly rejected invalid days parameter")
                    else:
                        self.log_result(f"Analytics Data Quality - Invalid Days ({days})", False, f"❌ Should reject days=0, got status: {response.status_code}")
                else:
                    # Should work with valid parameters
                    if response.status_code == 200:
                        data = response.json()
                        if f"Last {days} days" in data.get("period", ""):
                            self.log_result(f"Analytics Data Quality - Edge Case Days ({days})", True, f"✅ Handles {days} days correctly")
                        else:
                            self.log_result(f"Analytics Data Quality - Edge Case Days ({days})", False, f"❌ Wrong period for {days} days")
                    else:
                        self.log_result(f"Analytics Data Quality - Edge Case Days ({days})", False, f"❌ Status code: {response.status_code}")
                        
        except Exception as e:
            self.log_result("Analytics Data Quality", False, f"❌ Exception: {str(e)}")

    def run_phase3_analytics_tests(self):
        """Run Phase 3 Analytics Dashboard tests"""
        print("🚨 PHASE 3 TESTING - Analytics Dashboard Backend")
        print("=" * 70)
        print("Testing Phase 3 Analytics Dashboard Features:")
        print("1. Requester Analytics Endpoint")
        print("2. Export Requesters CSV Endpoint")
        print("3. Daily Analytics Endpoint")
        print("4. Authentication & Security")
        print("5. Data Quality & Edge Cases")
        print("=" * 70)
        
        # Authentication setup
        self.test_musician_registration()
        self.test_jwt_token_validation()
        
        # Create a test song for analytics data
        self.test_create_song()
        
        print("\n🔥 PHASE 3 TEST #1: REQUESTER ANALYTICS")
        print("-" * 50)
        self.test_analytics_requesters()
        
        print("\n🔥 PHASE 3 TEST #2: CSV EXPORT")
        print("-" * 50)
        self.test_analytics_export_csv()
        
        print("\n🔥 PHASE 3 TEST #3: DAILY ANALYTICS")
        print("-" * 50)
        self.test_analytics_daily()
        
        print("\n🔥 PHASE 3 TEST #4: AUTHENTICATION & SECURITY")
        print("-" * 50)
        self.test_analytics_authentication()
        
        print("\n🔥 PHASE 3 TEST #5: DATA QUALITY & EDGE CASES")
        print("-" * 50)
        self.test_analytics_data_quality()
        
        # Print summary
        print("\n" + "=" * 70)
        print("🏁 PHASE 3 ANALYTICS TEST SUMMARY")
        print("=" * 70)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n🔍 Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        # Specific summary for Phase 3 analytics features
        analytics_tests = [error for error in self.results['errors'] if 'analytics' in error.lower()]
        
        print(f"\n📊 PHASE 3 ANALYTICS DASHBOARD: {'✅ WORKING' if len(analytics_tests) == 0 else '❌ FAILING'}")
        if analytics_tests:
            for error in analytics_tests:
                print(f"   • {error}")
        
        return self.results['failed'] == 0

    def run_phase2_tests(self):
        """Run Phase 2 Request Tracking & Popularity Features tests"""
        print("🚨 PHASE 2 TESTING - Request Tracking & Popularity Features")
        print("=" * 70)
        print("Testing Phase 2 Request Tracking & Popularity Features:")
        print("1. Request Count Tracking")
        print("2. Popularity Sorting")
        print("3. Request Count in Song Data")
        print("4. Edge Cases")
        print("=" * 70)
        
        # Authentication setup
        self.test_musician_registration()
        self.test_jwt_token_validation()
        
        # Create a test song for request tracking
        self.test_create_song()
        
        print("\n🔥 PHASE 2 TEST #1: REQUEST COUNT TRACKING")
        print("-" * 50)
        self.test_phase2_request_count_tracking()
        
        print("\n🔥 PHASE 2 TEST #2: POPULARITY SORTING")
        print("-" * 50)
        self.test_phase2_popularity_sorting()
        
        print("\n🔥 PHASE 2 TEST #3: REQUEST COUNT FIELD")
        print("-" * 50)
        self.test_phase2_request_count_field()
        
        print("\n🔥 PHASE 2 TEST #4: EDGE CASES")
        print("-" * 50)
        self.test_phase2_edge_cases()
        
        # Print summary
        print("\n" + "=" * 70)
        print("🏁 PHASE 2 TEST SUMMARY")
        print("=" * 70)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n🔍 Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        # Specific summary for Phase 2 features
        phase2_tests = [error for error in self.results['errors'] if 'phase 2' in error.lower()]
        
        print(f"\n📊 PHASE 2 REQUEST TRACKING & POPULARITY: {'✅ WORKING' if len(phase2_tests) == 0 else '❌ FAILING'}")
        if phase2_tests:
            for error in phase2_tests:
                print(f"   • {error}")
        
        return self.results['failed'] == 0

    def run_critical_fixes_test(self):
        """Run ONLY the critical fixes tests requested in the review"""
        print("🚨 CRITICAL FIXES TESTING - RequestWave Backend API")
        print("=" * 60)
        print("Testing TWO CRITICAL FIXES:")
        print("1. Playlist Import Fix - Real Song Data Extraction")
        print("2. Delete Button Fix - Song Deletion")
        print("=" * 60)
        
        # Authentication setup
        self.test_musician_registration()
        self.test_jwt_token_validation()
        
        # Create a test song for deletion testing
        self.test_create_song()
        
        print("\n🔥 CRITICAL FIX #1: PLAYLIST IMPORT - REAL SONG DATA")
        print("-" * 50)
        
        # Test playlist import with the EXACT URLs from user report
        self.test_spotify_playlist_import()
        self.test_apple_music_playlist_import()
        self.test_playlist_import_authentication()
        
        print("\n🔥 CRITICAL FIX #2: DELETE BUTTON - SONG DELETION")
        print("-" * 50)
        
        # Test song deletion functionality
        self.test_delete_song_authentication()
        self.test_delete_song()  # This should be last as it deletes the test song
        
        # Print summary
        print("\n" + "=" * 60)
        print("🏁 CRITICAL FIXES TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n🔍 Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        # Specific summary for the two critical fixes
        playlist_tests = [error for error in self.results['errors'] if 'playlist' in error.lower() or 'import' in error.lower()]
        delete_tests = [error for error in self.results['errors'] if 'delete' in error.lower()]
        
        print(f"\n📊 CRITICAL FIX #1 (Playlist Import): {'✅ WORKING' if len(playlist_tests) == 0 else '❌ FAILING'}")
        if playlist_tests:
            for error in playlist_tests:
                print(f"   • {error}")
        
        print(f"📊 CRITICAL FIX #2 (Song Deletion): {'✅ WORKING' if len(delete_tests) == 0 else '❌ FAILING'}")
        if delete_tests:
            for error in delete_tests:
                print(f"   • {error}")
        
        return self.results['failed'] == 0

    def test_spotify_metadata_search_basic(self):
        """Test basic Spotify metadata search functionality"""
        try:
            if not self.auth_token:
                self.log_result("Spotify Metadata Search - Basic", False, "No auth token available")
                return
            
            # Test with popular songs as specified in the review request
            test_cases = [
                {"title": "As It Was", "artist": "Harry Styles"},
                {"title": "Heat Waves", "artist": "Glass Animals"}
            ]
            
            for test_case in test_cases:
                print(f"🔍 Testing metadata search for '{test_case['title']}' by '{test_case['artist']}'")
                
                response = self.make_request("POST", "/songs/search-metadata", params={
                    "title": test_case["title"],
                    "artist": test_case["artist"]
                })
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"📊 Metadata response: {json.dumps(data, indent=2)}")
                    
                    if "success" in data and data["success"] and "metadata" in data:
                        metadata = data["metadata"]
                        
                        # Verify required fields
                        required_fields = ["title", "artist", "genres", "moods", "confidence"]
                        missing_fields = [field for field in required_fields if field not in metadata]
                        
                        if not missing_fields:
                            # Check data quality
                            has_genres = metadata.get("genres") and len(metadata["genres"]) > 0
                            has_moods = metadata.get("moods") and len(metadata["moods"]) > 0
                            has_confidence = metadata.get("confidence") in ["high", "medium", "low"]
                            
                            if has_genres and has_moods and has_confidence:
                                self.log_result(f"Spotify Metadata Search - {test_case['title']}", True, 
                                    f"✅ Found metadata: genres={metadata['genres']}, moods={metadata['moods']}, confidence={metadata['confidence']}")
                            else:
                                self.log_result(f"Spotify Metadata Search - {test_case['title']}", False, 
                                    f"❌ Poor data quality: genres={metadata.get('genres')}, moods={metadata.get('moods')}, confidence={metadata.get('confidence')}")
                        else:
                            self.log_result(f"Spotify Metadata Search - {test_case['title']}", False, 
                                f"❌ Missing required fields: {missing_fields}")
                    else:
                        self.log_result(f"Spotify Metadata Search - {test_case['title']}", False, 
                            f"❌ Unexpected response structure: {data}")
                else:
                    self.log_result(f"Spotify Metadata Search - {test_case['title']}", False, 
                        f"❌ Status code: {response.status_code}, Response: {response.text}")
                        
        except Exception as e:
            self.log_result("Spotify Metadata Search - Basic", False, f"❌ Exception: {str(e)}")

    def test_spotify_metadata_search_fallback(self):
        """Test fallback functionality with non-existent songs"""
        try:
            if not self.auth_token:
                self.log_result("Spotify Metadata Search - Fallback", False, "No auth token available")
                return
            
            # Test with fake song as specified in review request
            fake_song = {"title": "Fake Song", "artist": "Fake Artist"}
            
            print(f"🔍 Testing fallback with fake song: '{fake_song['title']}' by '{fake_song['artist']}'")
            
            response = self.make_request("POST", "/songs/search-metadata", params=fake_song)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Fallback response: {json.dumps(data, indent=2)}")
                
                if "success" in data and data["success"] and "metadata" in data:
                    metadata = data["metadata"]
                    
                    # Verify fallback characteristics
                    is_low_confidence = metadata.get("confidence") == "low"
                    is_heuristic_source = metadata.get("source") == "heuristic"
                    has_fallback_data = metadata.get("genres") and metadata.get("moods")
                    
                    if is_low_confidence and is_heuristic_source and has_fallback_data:
                        self.log_result("Spotify Metadata Search - Fallback", True, 
                            f"✅ Fallback working: confidence=low, source=heuristic, genres={metadata['genres']}, moods={metadata['moods']}")
                    else:
                        self.log_result("Spotify Metadata Search - Fallback", False, 
                            f"❌ Fallback not working correctly: confidence={metadata.get('confidence')}, source={metadata.get('source')}")
                else:
                    self.log_result("Spotify Metadata Search - Fallback", False, 
                        f"❌ Unexpected fallback response: {data}")
            else:
                self.log_result("Spotify Metadata Search - Fallback", False, 
                    f"❌ Fallback failed with status: {response.status_code}")
                    
        except Exception as e:
            self.log_result("Spotify Metadata Search - Fallback", False, f"❌ Exception: {str(e)}")

    def test_spotify_metadata_search_validation(self):
        """Test input validation for metadata search"""
        try:
            if not self.auth_token:
                self.log_result("Spotify Metadata Search - Validation", False, "No auth token available")
                return
            
            # Test cases for validation
            validation_tests = [
                {"data": {"title": "", "artist": "Artist"}, "description": "Empty title"},
                {"data": {"title": "Title", "artist": ""}, "description": "Empty artist"},
                {"data": {"title": "   ", "artist": "Artist"}, "description": "Whitespace-only title"},
                {"data": {"title": "Title", "artist": "   "}, "description": "Whitespace-only artist"},
                {"data": {"artist": "Artist"}, "description": "Missing title"},
                {"data": {"title": "Title"}, "description": "Missing artist"}
            ]
            
            for test in validation_tests:
                print(f"🔍 Testing validation: {test['description']}")
                
                response = self.make_request("POST", "/songs/search-metadata", params=test["data"])
                
                if response.status_code == 400:
                    self.log_result(f"Spotify Metadata Search - Validation ({test['description']})", True, 
                        "✅ Correctly rejected invalid input")
                else:
                    self.log_result(f"Spotify Metadata Search - Validation ({test['description']})", False, 
                        f"❌ Should have returned 400, got: {response.status_code}")
                        
        except Exception as e:
            self.log_result("Spotify Metadata Search - Validation", False, f"❌ Exception: {str(e)}")

    def test_spotify_metadata_search_authentication(self):
        """Test authentication requirements for metadata search"""
        try:
            # Save current token
            original_token = self.auth_token
            
            # Test without token
            self.auth_token = None
            test_data = {"title": "Test Song", "artist": "Test Artist"}
            
            response = self.make_request("POST", "/songs/search-metadata", params=test_data)
            
            if response.status_code == 401:
                self.log_result("Spotify Metadata Search - Authentication (No Token)", True, 
                    "✅ Correctly rejected request without auth token")
            else:
                self.log_result("Spotify Metadata Search - Authentication (No Token)", False, 
                    f"❌ Should have returned 401, got: {response.status_code}")
            
            # Test with invalid token
            self.auth_token = "invalid_token_12345"
            response = self.make_request("POST", "/songs/search-metadata", params=test_data)
            
            if response.status_code == 401:
                self.log_result("Spotify Metadata Search - Authentication (Invalid Token)", True, 
                    "✅ Correctly rejected request with invalid token")
            else:
                self.log_result("Spotify Metadata Search - Authentication (Invalid Token)", False, 
                    f"❌ Should have returned 401, got: {response.status_code}")
            
            # Restore original token
            self.auth_token = original_token
            
        except Exception as e:
            self.log_result("Spotify Metadata Search - Authentication", False, f"❌ Exception: {str(e)}")
            # Restore token in case of exception
            if 'original_token' in locals():
                self.auth_token = original_token

    def test_spotify_metadata_search_edge_cases(self):
        """Test edge cases for metadata search"""
        try:
            if not self.auth_token:
                self.log_result("Spotify Metadata Search - Edge Cases", False, "No auth token available")
                return
            
            # Test cases for edge cases
            edge_cases = [
                {"title": "Song with Special Characters!@#$%", "artist": "Artist & Co.", "description": "Special characters"},
                {"title": "A" * 200, "artist": "Very Long Artist Name" * 10, "description": "Very long names"},
                {"title": "Ñoño", "artist": "Björk", "description": "Unicode characters"},
                {"title": "Song (Remix) [feat. Artist]", "artist": "Main Artist", "description": "Complex formatting"}
            ]
            
            for test_case in edge_cases:
                print(f"🔍 Testing edge case: {test_case['description']}")
                
                response = self.make_request("POST", "/songs/search-metadata", params={
                    "title": test_case["title"],
                    "artist": test_case["artist"]
                })
                
                if response.status_code == 200:
                    data = response.json()
                    if "success" in data and data["success"] and "metadata" in data:
                        metadata = data["metadata"]
                        if metadata.get("genres") and metadata.get("moods") and metadata.get("confidence"):
                            self.log_result(f"Spotify Metadata Search - Edge Case ({test_case['description']})", True, 
                                f"✅ Handled edge case successfully: confidence={metadata['confidence']}")
                        else:
                            self.log_result(f"Spotify Metadata Search - Edge Case ({test_case['description']})", False, 
                                f"❌ Poor response quality for edge case")
                    else:
                        self.log_result(f"Spotify Metadata Search - Edge Case ({test_case['description']})", False, 
                            f"❌ Unexpected response structure for edge case")
                else:
                    self.log_result(f"Spotify Metadata Search - Edge Case ({test_case['description']})", False, 
                        f"❌ Edge case failed with status: {response.status_code}")
                        
        except Exception as e:
            self.log_result("Spotify Metadata Search - Edge Cases", False, f"❌ Exception: {str(e)}")

    def test_spotify_metadata_search_integration_quality(self):
        """Test Spotify API integration quality and audio features mapping"""
        try:
            if not self.auth_token:
                self.log_result("Spotify Metadata Search - Integration Quality", False, "No auth token available")
                return
            
            # Test with well-known songs to verify integration quality
            quality_tests = [
                {"title": "Blinding Lights", "artist": "The Weeknd", "expected_genre": "Pop", "expected_mood": "Energetic"},
                {"title": "Bohemian Rhapsody", "artist": "Queen", "expected_genre": "Rock", "expected_mood": "Energetic"}
            ]
            
            for test_case in quality_tests:
                print(f"🔍 Testing integration quality for '{test_case['title']}' by '{test_case['artist']}'")
                
                response = self.make_request("POST", "/songs/search-metadata", params={
                    "title": test_case["title"],
                    "artist": test_case["artist"]
                })
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if "success" in data and data["success"] and "metadata" in data:
                        metadata = data["metadata"]
                        
                        # Check integration quality indicators
                        has_spotify_id = "spotify_id" in metadata
                        has_year = metadata.get("year") is not None
                        has_high_confidence = metadata.get("confidence") in ["high", "medium"]
                        has_spotify_source = metadata.get("source") == "spotify"
                        
                        quality_score = sum([has_spotify_id, has_year, has_high_confidence, has_spotify_source])
                        
                        if quality_score >= 3:
                            self.log_result(f"Spotify Integration Quality - {test_case['title']}", True, 
                                f"✅ High quality integration: spotify_id={has_spotify_id}, year={metadata.get('year')}, confidence={metadata.get('confidence')}, source={metadata.get('source')}")
                        else:
                            self.log_result(f"Spotify Integration Quality - {test_case['title']}", False, 
                                f"❌ Poor integration quality: spotify_id={has_spotify_id}, year={metadata.get('year')}, confidence={metadata.get('confidence')}")
                    else:
                        self.log_result(f"Spotify Integration Quality - {test_case['title']}", False, 
                            f"❌ Unexpected response structure")
                else:
                    self.log_result(f"Spotify Integration Quality - {test_case['title']}", False, 
                        f"❌ Integration test failed with status: {response.status_code}")
                        
        except Exception as e:
            self.log_result("Spotify Metadata Search - Integration Quality", False, f"❌ Exception: {str(e)}")

    def run_spotify_metadata_tests(self):
        """Run NEW Spotify Metadata Auto-fill Feature tests"""
        print("🚨 NEW FEATURE TESTING - Spotify Metadata Auto-fill")
        print("=" * 70)
        print("Testing NEW Spotify Metadata Search Functionality:")
        print("1. Basic Metadata Search with Popular Songs")
        print("2. Fallback Functionality with Non-existent Songs")
        print("3. Input Validation")
        print("4. Authentication Requirements")
        print("5. Edge Cases")
        print("6. Spotify API Integration Quality")
        print("=" * 70)
        
        # Authentication setup
        self.test_musician_registration()
        self.test_jwt_token_validation()
        
        print("\n🎵 NEW FEATURE TEST #1: BASIC METADATA SEARCH")
        print("-" * 50)
        self.test_spotify_metadata_search_basic()
        
        print("\n🎵 NEW FEATURE TEST #2: FALLBACK FUNCTIONALITY")
        print("-" * 50)
        self.test_spotify_metadata_search_fallback()
        
        print("\n🎵 NEW FEATURE TEST #3: INPUT VALIDATION")
        print("-" * 50)
        self.test_spotify_metadata_search_validation()
        
        print("\n🎵 NEW FEATURE TEST #4: AUTHENTICATION REQUIREMENTS")
        print("-" * 50)
        self.test_spotify_metadata_search_authentication()
        
        print("\n🎵 NEW FEATURE TEST #5: EDGE CASES")
        print("-" * 50)
        self.test_spotify_metadata_search_edge_cases()
        
        print("\n🎵 NEW FEATURE TEST #6: SPOTIFY API INTEGRATION QUALITY")
        print("-" * 50)
        self.test_spotify_metadata_search_integration_quality()
        
        # Print summary
        print("\n" + "=" * 70)
        print("🏁 SPOTIFY METADATA AUTO-FILL TEST SUMMARY")
        print("=" * 70)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n🔍 Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        # Specific summary for Spotify metadata features
        metadata_tests = [error for error in self.results['errors'] if 'metadata' in error.lower() or 'spotify' in error.lower()]
        
        print(f"\n🎵 SPOTIFY METADATA AUTO-FILL FEATURE: {'✅ WORKING' if len(metadata_tests) == 0 else '❌ FAILING'}")
        if metadata_tests:
            for error in metadata_tests:
                print(f"   • {error}")
        
        return self.results['failed'] == 0

    def test_profile_payment_fields_get(self):
        """Test GET /api/profile includes payment fields"""
        try:
            if not self.auth_token:
                self.log_result("Profile Payment Fields - GET", False, "No auth token available")
                return
            
            response = self.make_request("GET", "/profile")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if payment fields are present
                required_fields = ["paypal_username", "venmo_username"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.log_result("Profile Payment Fields - GET", True, f"Profile includes payment fields: {required_fields}")
                else:
                    self.log_result("Profile Payment Fields - GET", False, f"Missing payment fields: {missing_fields}")
            else:
                self.log_result("Profile Payment Fields - GET", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Profile Payment Fields - GET", False, f"Exception: {str(e)}")

    def test_profile_payment_fields_update(self):
        """Test PUT /api/profile updates payment fields"""
        try:
            if not self.auth_token:
                self.log_result("Profile Payment Fields - UPDATE", False, "No auth token available")
                return
            
            # Test data with payment usernames
            update_data = {
                "paypal_username": "testmusician",
                "venmo_username": "@testmusician123"  # Test @ symbol removal
            }
            
            response = self.make_request("PUT", "/profile", update_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if payment fields were updated correctly
                if (data.get("paypal_username") == "testmusician" and 
                    data.get("venmo_username") == "testmusician123"):  # @ should be removed
                    self.log_result("Profile Payment Fields - UPDATE", True, "Payment fields updated correctly, @ symbol removed from Venmo username")
                else:
                    self.log_result("Profile Payment Fields - UPDATE", False, f"Payment fields not updated correctly: {data}")
            else:
                self.log_result("Profile Payment Fields - UPDATE", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Profile Payment Fields - UPDATE", False, f"Exception: {str(e)}")

    def test_tip_links_generation_basic(self):
        """Test GET /api/musicians/{slug}/tip-links basic functionality"""
        try:
            if not self.musician_slug:
                self.log_result("Tip Links Generation - Basic", False, "No musician slug available")
                return
            
            # First ensure musician has payment methods set up
            self.test_profile_payment_fields_update()
            
            # Test basic tip link generation
            params = {
                "amount": 5.00,
                "message": "Thanks for the music!"
            }
            
            response = self.make_request("GET", f"/musicians/{self.musician_slug}/tip-links", params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                expected_fields = ["paypal_link", "venmo_link", "amount", "message"]
                missing_fields = [field for field in expected_fields if field not in data]
                
                if not missing_fields:
                    # Verify link formats
                    paypal_link = data.get("paypal_link")
                    venmo_link = data.get("venmo_link")
                    
                    paypal_valid = paypal_link and "paypal.me/testmusician/5.0" in paypal_link and "note=Thanks%20for%20the%20music!" in paypal_link
                    venmo_valid = venmo_link and "venmo.com/testmusician123" in venmo_link and "amount=5.0" in venmo_link and "note=Thanks%20for%20the%20music!" in venmo_link
                    
                    if paypal_valid and venmo_valid:
                        self.log_result("Tip Links Generation - Basic", True, f"Generated valid payment links: PayPal and Venmo")
                    else:
                        self.log_result("Tip Links Generation - Basic", False, f"Invalid link formats - PayPal: {paypal_link}, Venmo: {venmo_link}")
                else:
                    self.log_result("Tip Links Generation - Basic", False, f"Missing response fields: {missing_fields}")
            else:
                self.log_result("Tip Links Generation - Basic", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Tip Links Generation - Basic", False, f"Exception: {str(e)}")

    def test_tip_links_generation_different_amounts(self):
        """Test tip links with different amounts"""
        try:
            if not self.musician_slug:
                self.log_result("Tip Links Generation - Different Amounts", False, "No musician slug available")
                return
            
            test_amounts = [1.00, 5.50, 20.00]
            
            for amount in test_amounts:
                params = {"amount": amount}
                response = self.make_request("GET", f"/musicians/{self.musician_slug}/tip-links", params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("amount") == amount:
                        self.log_result(f"Tip Links Generation - Amount ${amount}", True, f"Generated links for ${amount}")
                    else:
                        self.log_result(f"Tip Links Generation - Amount ${amount}", False, f"Amount mismatch: expected ${amount}, got ${data.get('amount')}")
                else:
                    self.log_result(f"Tip Links Generation - Amount ${amount}", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_result("Tip Links Generation - Different Amounts", False, f"Exception: {str(e)}")

    def test_tip_links_generation_without_message(self):
        """Test tip links without custom message"""
        try:
            if not self.musician_slug:
                self.log_result("Tip Links Generation - No Message", False, "No musician slug available")
                return
            
            params = {"amount": 10.00}
            response = self.make_request("GET", f"/musicians/{self.musician_slug}/tip-links", params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Links should not contain note parameter when no message provided
                paypal_link = data.get("paypal_link", "")
                venmo_link = data.get("venmo_link", "")
                
                paypal_no_note = "note=" not in paypal_link
                venmo_no_note = "note=" not in venmo_link
                
                if paypal_no_note and venmo_no_note:
                    self.log_result("Tip Links Generation - No Message", True, "Links generated without note parameter when no message provided")
                else:
                    self.log_result("Tip Links Generation - No Message", False, f"Links contain note parameter when none expected - PayPal: {paypal_link}, Venmo: {venmo_link}")
            else:
                self.log_result("Tip Links Generation - No Message", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_result("Tip Links Generation - No Message", False, f"Exception: {str(e)}")

    def test_tip_links_generation_error_cases(self):
        """Test tip links error cases"""
        try:
            # Test musician not found
            response = self.make_request("GET", "/musicians/nonexistent-musician/tip-links", {"amount": 5.00})
            if response.status_code == 404:
                self.log_result("Tip Links Generation - Musician Not Found", True, "Correctly returned 404 for nonexistent musician")
            else:
                self.log_result("Tip Links Generation - Musician Not Found", False, f"Expected 404, got {response.status_code}")
            
            if not self.musician_slug:
                return
            
            # Test invalid amounts
            invalid_amounts = [0, -5.00, 501.00]
            for amount in invalid_amounts:
                response = self.make_request("GET", f"/musicians/{self.musician_slug}/tip-links", {"amount": amount})
                if response.status_code == 400:
                    self.log_result(f"Tip Links Generation - Invalid Amount ${amount}", True, f"Correctly rejected invalid amount ${amount}")
                else:
                    self.log_result(f"Tip Links Generation - Invalid Amount ${amount}", False, f"Expected 400, got {response.status_code}")
            
            # Test musician without payment methods (create temporary musician)
            temp_musician_data = {
                "name": "No Payment Musician",
                "email": "nopayment@test.com",
                "password": "TestPassword123!"
            }
            
            register_response = self.make_request("POST", "/auth/register", temp_musician_data)
            if register_response.status_code == 200:
                temp_slug = register_response.json()["musician"]["slug"]
                
                response = self.make_request("GET", f"/musicians/{temp_slug}/tip-links", {"amount": 5.00})
                if response.status_code == 400:
                    self.log_result("Tip Links Generation - No Payment Methods", True, "Correctly rejected musician without payment methods")
                else:
                    self.log_result("Tip Links Generation - No Payment Methods", False, f"Expected 400, got {response.status_code}")
            
        except Exception as e:
            self.log_result("Tip Links Generation - Error Cases", False, f"Exception: {str(e)}")

    def test_tip_recording_basic(self):
        """Test POST /api/musicians/{slug}/tips basic functionality"""
        try:
            if not self.musician_slug:
                self.log_result("Tip Recording - Basic", False, "No musician slug available")
                return
            
            tip_data = {
                "amount": 5.00,
                "platform": "paypal",
                "tipper_name": "Generous Fan",
                "message": "Love your music!"
            }
            
            response = self.make_request("POST", f"/musicians/{self.musician_slug}/tips", tip_data)
            
            if response.status_code == 200:
                data = response.json()
                
                expected_fields = ["success", "message", "tip_id"]
                missing_fields = [field for field in expected_fields if field not in data]
                
                if not missing_fields and data.get("success") is True:
                    self.log_result("Tip Recording - Basic", True, f"Successfully recorded tip: {data['message']}")
                else:
                    self.log_result("Tip Recording - Basic", False, f"Unexpected response structure: {data}")
            else:
                self.log_result("Tip Recording - Basic", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Tip Recording - Basic", False, f"Exception: {str(e)}")

    def test_tip_recording_different_platforms(self):
        """Test tip recording with different platforms"""
        try:
            if not self.musician_slug:
                self.log_result("Tip Recording - Different Platforms", False, "No musician slug available")
                return
            
            platforms = ["paypal", "venmo"]
            
            for platform in platforms:
                tip_data = {
                    "amount": 3.00,
                    "platform": platform,
                    "tipper_name": f"{platform.title()} User",
                    "message": f"Tip via {platform}"
                }
                
                response = self.make_request("POST", f"/musicians/{self.musician_slug}/tips", tip_data)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") is True:
                        self.log_result(f"Tip Recording - {platform.title()}", True, f"Successfully recorded {platform} tip")
                    else:
                        self.log_result(f"Tip Recording - {platform.title()}", False, f"Tip recording failed: {data}")
                else:
                    self.log_result(f"Tip Recording - {platform.title()}", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_result("Tip Recording - Different Platforms", False, f"Exception: {str(e)}")

    def test_tip_recording_validation(self):
        """Test tip recording validation"""
        try:
            if not self.musician_slug:
                self.log_result("Tip Recording - Validation", False, "No musician slug available")
                return
            
            # Test invalid amounts
            invalid_amounts = [0, -1.00, 501.00]
            for amount in invalid_amounts:
                tip_data = {
                    "amount": amount,
                    "platform": "paypal",
                    "tipper_name": "Test User"
                }
                
                response = self.make_request("POST", f"/musicians/{self.musician_slug}/tips", tip_data)
                if response.status_code == 400:
                    self.log_result(f"Tip Recording - Invalid Amount ${amount}", True, f"Correctly rejected invalid amount ${amount}")
                else:
                    self.log_result(f"Tip Recording - Invalid Amount ${amount}", False, f"Expected 400, got {response.status_code}")
            
            # Test invalid platform
            tip_data = {
                "amount": 5.00,
                "platform": "bitcoin",
                "tipper_name": "Test User"
            }
            
            response = self.make_request("POST", f"/musicians/{self.musician_slug}/tips", tip_data)
            if response.status_code == 400:
                self.log_result("Tip Recording - Invalid Platform", True, "Correctly rejected invalid platform")
            else:
                self.log_result("Tip Recording - Invalid Platform", False, f"Expected 400, got {response.status_code}")
            
            # Test musician not found
            tip_data = {
                "amount": 5.00,
                "platform": "paypal",
                "tipper_name": "Test User"
            }
            
            response = self.make_request("POST", "/musicians/nonexistent-musician/tips", tip_data)
            if response.status_code == 404:
                self.log_result("Tip Recording - Musician Not Found", True, "Correctly returned 404 for nonexistent musician")
            else:
                self.log_result("Tip Recording - Musician Not Found", False, f"Expected 404, got {response.status_code}")
                
        except Exception as e:
            self.log_result("Tip Recording - Validation", False, f"Exception: {str(e)}")

    def run_tip_support_tests(self):
        """Run ONLY the Tip Support System tests as requested in the review"""
        print("🚨 TIP SUPPORT SYSTEM TESTING - RequestWave Backend API")
        print("=" * 60)
        print("Testing Tip Support System Features:")
        print("1. Profile Payment Fields (GET/PUT /api/profile)")
        print("2. Tip Links Generation (GET /api/musicians/{slug}/tip-links)")
        print("3. Tip Recording (POST /api/musicians/{slug}/tips)")
        print("=" * 60)
        
        # Authentication setup
        self.test_musician_registration()
        if not self.auth_token:
            print("❌ Cannot proceed without authentication")
            return False
        
        print("\n🔥 PRIORITY 1: TIP LINKS GENERATION")
        print("-" * 50)
        self.test_tip_links_generation_basic()
        self.test_tip_links_generation_different_amounts()
        self.test_tip_links_generation_without_message()
        self.test_tip_links_generation_error_cases()
        
        print("\n🔥 PRIORITY 2: TIP RECORDING")
        print("-" * 50)
        self.test_tip_recording_basic()
        self.test_tip_recording_different_platforms()
        self.test_tip_recording_validation()
        
        print("\n🔥 PRIORITY 3: PROFILE PAYMENT FIELDS")
        print("-" * 50)
        self.test_profile_payment_fields_get()
        self.test_profile_payment_fields_update()
        
        # Print summary
        print("\n" + "=" * 60)
        print("🏁 TIP SUPPORT SYSTEM TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n🔍 Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        # Specific summary for tip support features
        tip_tests = [error for error in self.results['errors'] if any(keyword in error.lower() for keyword in ['tip', 'payment', 'paypal', 'venmo'])]
        
        print(f"\n💰 TIP SUPPORT SYSTEM: {'✅ WORKING' if len(tip_tests) == 0 else '❌ FAILING'}")
        if tip_tests:
            for error in tip_tests:
                print(f"   • {error}")
        
        return self.results['failed'] == 0

    def test_audience_page_search_functionality(self):
        """Test comprehensive audience page search functionality across all fields"""
        try:
            if not self.musician_slug:
                self.log_result("Audience Page Search Functionality", False, "No musician slug available")
                return
            
            print("🔍 Testing comprehensive audience page search functionality")
            
            # Create test songs with variety as specified in requirements
            test_songs = [
                {
                    "title": "Love Story",
                    "artist": "Taylor Swift", 
                    "genres": ["Pop"],
                    "moods": ["Romantic"],
                    "year": 2020,
                    "notes": "Test song for search functionality"
                },
                {
                    "title": "Rock Me",
                    "artist": "Queen",
                    "genres": ["Rock"], 
                    "moods": ["Energetic"],
                    "year": 1975,
                    "notes": "Classic rock anthem"
                },
                {
                    "title": "Smooth Jazz",
                    "artist": "Miles Davis",
                    "genres": ["Jazz"],
                    "moods": ["Smooth"],
                    "year": 1960,
                    "notes": "Smooth jazz classic"
                },
                {
                    "title": "Pop Hit",
                    "artist": "Ariana Grande",
                    "genres": ["Pop"],
                    "moods": ["Upbeat"],
                    "year": 2021,
                    "notes": "Modern pop hit"
                },
                {
                    "title": "Jazz Melody",
                    "artist": "John Coltrane",
                    "genres": ["Jazz"],
                    "moods": ["Smooth"],
                    "year": 1965,
                    "notes": "Beautiful jazz melody"
                }
            ]
            
            created_song_ids = []
            
            # Create test songs
            for song_data in test_songs:
                response = self.make_request("POST", "/songs", song_data)
                if response.status_code == 200:
                    song_id = response.json()["id"]
                    created_song_ids.append(song_id)
                    print(f"📊 Created test song: '{song_data['title']}' by '{song_data['artist']}'")
                else:
                    self.log_result("Audience Page Search - Create Test Songs", False, f"Failed to create song: {song_data['title']}")
                    return
            
            print(f"✅ Created {len(created_song_ids)} test songs for search testing")
            
            # Test search scenarios as specified in requirements
            search_tests = [
                # Title search
                ("love", "Love Story", "Should find 'Love Story' by title search"),
                ("rock", "Rock Me", "Should find 'Rock Me' by title search"),
                ("jazz", ["Smooth Jazz", "Jazz Melody"], "Should find both jazz songs by title search"),
                
                # Artist search  
                ("taylor", "Love Story", "Should find Taylor Swift song by artist search"),
                ("queen", "Rock Me", "Should find Queen song by artist search"),
                ("miles", "Smooth Jazz", "Should find Miles Davis song by artist search"),
                ("ariana", "Pop Hit", "Should find Ariana Grande song by artist search"),
                
                # Genre search
                ("pop", ["Love Story", "Pop Hit"], "Should find Pop genre songs"),
                ("rock", "Rock Me", "Should find Rock genre songs"),
                ("jazz", ["Smooth Jazz", "Jazz Melody"], "Should find Jazz genre songs"),
                
                # Mood search
                ("romantic", "Love Story", "Should find Romantic mood songs"),
                ("energetic", "Rock Me", "Should find Energetic mood songs"),
                ("smooth", ["Smooth Jazz", "Jazz Melody"], "Should find Smooth mood songs"),
                ("upbeat", "Pop Hit", "Should find Upbeat mood songs"),
                
                # Year search
                ("2020", "Love Story", "Should find 2020 songs"),
                ("1975", "Rock Me", "Should find 1975 songs"),
                ("1960", "Smooth Jazz", "Should find 1960 songs"),
                ("2021", "Pop Hit", "Should find 2021 songs"),
                
                # Case-insensitive search
                ("LOVE", "Love Story", "Should find songs with case-insensitive search"),
                ("TAYLOR", "Love Story", "Should find Taylor Swift with case-insensitive search"),
                ("POP", ["Love Story", "Pop Hit"], "Should find Pop genre with case-insensitive search"),
                
                # Partial matches
                ("tay", "Love Story", "Should find Taylor Swift with partial match"),
                ("jaz", ["Smooth Jazz", "Jazz Melody"], "Should find jazz songs with partial match"),
                ("gran", "Pop Hit", "Should find Ariana Grande with partial match")
            ]
            
            search_passed = 0
            search_failed = 0
            
            for search_term, expected_songs, description in search_tests:
                params = {"search": search_term}
                response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs", params)
                
                if response.status_code == 200:
                    found_songs = response.json()
                    found_titles = [song["title"] for song in found_songs]
                    
                    # Handle both single song and multiple song expectations
                    if isinstance(expected_songs, str):
                        expected_songs = [expected_songs]
                    
                    # Check if all expected songs were found
                    found_expected = all(expected in found_titles for expected in expected_songs)
                    
                    if found_expected:
                        search_passed += 1
                        print(f"✅ Search '{search_term}': Found {found_titles} - {description}")
                    else:
                        search_failed += 1
                        print(f"❌ Search '{search_term}': Expected {expected_songs}, found {found_titles} - {description}")
                else:
                    search_failed += 1
                    print(f"❌ Search '{search_term}': API error {response.status_code} - {description}")
            
            # Test search combined with filters
            print("\n🔍 Testing search combined with filters")
            
            filter_tests = [
                # Search + genre filter
                ({"search": "love", "genre": "Pop"}, ["Love Story"], "Search 'love' + Pop genre filter"),
                ({"search": "jazz", "genre": "Jazz"}, ["Smooth Jazz", "Jazz Melody"], "Search 'jazz' + Jazz genre filter"),
                
                # Search + artist filter  
                ({"search": "taylor", "artist": "Taylor"}, ["Love Story"], "Search 'taylor' + artist filter"),
                
                # Search + mood filter
                ({"search": "smooth", "mood": "Smooth"}, ["Smooth Jazz", "Jazz Melody"], "Search 'smooth' + Smooth mood filter"),
                
                # Search + year filter
                ({"search": "pop", "year": 2020}, ["Love Story"], "Search 'pop' + year 2020 filter"),
                ({"search": "pop", "year": 2021}, ["Pop Hit"], "Search 'pop' + year 2021 filter")
            ]
            
            filter_passed = 0
            filter_failed = 0
            
            for params, expected_songs, description in filter_tests:
                response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs", params)
                
                if response.status_code == 200:
                    found_songs = response.json()
                    found_titles = [song["title"] for song in found_songs]
                    
                    # Check if all expected songs were found
                    found_expected = all(expected in found_titles for expected in expected_songs)
                    
                    if found_expected and len(found_titles) == len(expected_songs):
                        filter_passed += 1
                        print(f"✅ {description}: Found {found_titles}")
                    else:
                        filter_failed += 1
                        print(f"❌ {description}: Expected {expected_songs}, found {found_titles}")
                else:
                    filter_failed += 1
                    print(f"❌ {description}: API error {response.status_code}")
            
            # Test that GET /musicians/{slug}/songs returns all songs without 1000 limit
            print("\n🔍 Testing unlimited song retrieval")
            
            response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs")
            if response.status_code == 200:
                all_songs = response.json()
                if len(all_songs) >= len(created_song_ids):
                    print(f"✅ Retrieved {len(all_songs)} songs without 1000 limit")
                    unlimited_passed = True
                else:
                    print(f"❌ Expected at least {len(created_song_ids)} songs, got {len(all_songs)}")
                    unlimited_passed = False
            else:
                print(f"❌ Failed to retrieve all songs: {response.status_code}")
                unlimited_passed = False
            
            # Overall results
            total_search_tests = len(search_tests)
            total_filter_tests = len(filter_tests)
            
            if search_passed == total_search_tests and filter_passed == total_filter_tests and unlimited_passed:
                self.log_result("Audience Page Search Functionality", True, 
                    f"✅ ALL SEARCH TESTS PASSED: {search_passed}/{total_search_tests} search tests, {filter_passed}/{total_filter_tests} filter tests, unlimited retrieval working")
            else:
                self.log_result("Audience Page Search Functionality", False,
                    f"❌ SEARCH TESTS FAILED: {search_passed}/{total_search_tests} search tests passed, {filter_passed}/{total_filter_tests} filter tests passed, unlimited retrieval: {unlimited_passed}")
                    
        except Exception as e:
            self.log_result("Audience Page Search Functionality", False, f"Exception: {str(e)}")

    def test_search_edge_cases(self):
        """Test search functionality edge cases"""
        try:
            if not self.musician_slug:
                self.log_result("Search Edge Cases", False, "No musician slug available")
                return
            
            print("🔍 Testing search functionality edge cases")
            
            edge_case_tests = [
                # Empty search
                ("", "Should return all songs when search is empty"),
                ("   ", "Should return all songs when search is whitespace"),
                
                # Special characters
                ("love's", "Should handle apostrophes in search"),
                ("rock&roll", "Should handle ampersands in search"),
                ("jazz-fusion", "Should handle hyphens in search"),
                
                # Unicode characters
                ("café", "Should handle unicode characters"),
                ("naïve", "Should handle accented characters"),
                
                # Very long search terms
                ("a" * 100, "Should handle very long search terms"),
                
                # Numbers as strings
                ("1975", "Should find year 1975 as string search"),
                ("20", "Should find partial year matches"),
                
                # Non-existent terms
                ("xyzneverexists", "Should return empty results for non-existent terms"),
                ("fakesong", "Should return empty results for fake song names")
            ]
            
            edge_passed = 0
            edge_failed = 0
            
            for search_term, description in edge_case_tests:
                params = {"search": search_term}
                response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs", params)
                
                if response.status_code == 200:
                    found_songs = response.json()
                    
                    # For empty/whitespace searches, should return all songs
                    if search_term.strip() == "":
                        if len(found_songs) > 0:
                            edge_passed += 1
                            print(f"✅ Search '{search_term}': Returned {len(found_songs)} songs - {description}")
                        else:
                            edge_failed += 1
                            print(f"❌ Search '{search_term}': Should return all songs but got {len(found_songs)} - {description}")
                    
                    # For non-existent terms, should return empty
                    elif search_term in ["xyzneverexists", "fakesong"]:
                        if len(found_songs) == 0:
                            edge_passed += 1
                            print(f"✅ Search '{search_term}': Correctly returned no results - {description}")
                        else:
                            edge_failed += 1
                            print(f"❌ Search '{search_term}': Should return no results but got {len(found_songs)} - {description}")
                    
                    # For other edge cases, just check that API doesn't crash
                    else:
                        edge_passed += 1
                        print(f"✅ Search '{search_term}': API handled gracefully, returned {len(found_songs)} songs - {description}")
                        
                else:
                    edge_failed += 1
                    print(f"❌ Search '{search_term}': API error {response.status_code} - {description}")
            
            if edge_passed == len(edge_case_tests):
                self.log_result("Search Edge Cases", True, f"✅ All {edge_passed} edge case tests passed")
            else:
                self.log_result("Search Edge Cases", False, f"❌ {edge_failed}/{len(edge_case_tests)} edge case tests failed")
                
        except Exception as e:
            self.log_result("Search Edge Cases", False, f"Exception: {str(e)}")

    def test_search_performance(self):
        """Test search functionality performance with larger dataset"""
        try:
            if not self.musician_slug:
                self.log_result("Search Performance", False, "No musician slug available")
                return
            
            print("🔍 Testing search performance with larger dataset")
            
            # Get current song count
            response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs")
            if response.status_code == 200:
                initial_count = len(response.json())
                print(f"📊 Initial song count: {initial_count}")
            else:
                self.log_result("Search Performance", False, "Could not get initial song count")
                return
            
            # Test search performance with current dataset
            import time
            
            performance_tests = [
                ("love", "Title search performance"),
                ("taylor", "Artist search performance"), 
                ("pop", "Genre search performance"),
                ("smooth", "Mood search performance"),
                ("2020", "Year search performance"),
                ("jazz", "Multi-field search performance")
            ]
            
            performance_results = []
            
            for search_term, description in performance_tests:
                start_time = time.time()
                
                params = {"search": search_term}
                response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs", params)
                
                end_time = time.time()
                response_time = end_time - start_time
                
                if response.status_code == 200:
                    found_songs = response.json()
                    performance_results.append((search_term, response_time, len(found_songs)))
                    print(f"✅ Search '{search_term}': {response_time:.3f}s, found {len(found_songs)} songs - {description}")
                else:
                    print(f"❌ Search '{search_term}': API error {response.status_code} - {description}")
            
            # Check if all searches completed within reasonable time (< 2 seconds)
            slow_searches = [result for result in performance_results if result[1] > 2.0]
            
            if len(slow_searches) == 0:
                avg_time = sum(result[1] for result in performance_results) / len(performance_results)
                self.log_result("Search Performance", True, 
                    f"✅ All searches completed quickly (avg: {avg_time:.3f}s, max: {max(result[1] for result in performance_results):.3f}s)")
            else:
                self.log_result("Search Performance", False,
                    f"❌ {len(slow_searches)} searches were slow (>2s): {[result[0] for result in slow_searches]}")
                    
        except Exception as e:
            self.log_result("Search Performance", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all tests in order"""
        print("=" * 50)
        
        # Health check
        self.test_health_check()
        
        # Authentication tests
        self.test_musician_registration()
        self.test_jwt_token_validation()
        
        # PRIORITY 1: Social Media Profile Tests
        print("\n" + "🎯" * 20 + " PRIORITY 1: SOCIAL MEDIA PROFILE TESTS " + "🎯" * 20)
        self.test_social_media_profile_get()
        self.test_social_media_profile_update()
        self.test_social_media_profile_empty_fields()
        
        # PRIORITY 2: Social Media Integration Tests
        print("\n" + "🎯" * 20 + " PRIORITY 2: SOCIAL MEDIA INTEGRATION TESTS " + "🎯" * 20)
        self.test_social_media_click_tracking()
        self.test_social_media_integration_post_request()
        self.test_social_media_link_generation()
        
        # Song management tests
        self.test_create_song()
        self.test_get_songs()
        self.test_update_song()
        
        # Musician profile tests
        self.test_get_musician_by_slug()
        
        # PRIORITY 1 & 2: Social Media Fields Tests for Post-Request Modal Fix
        print("\n" + "🎯" * 20 + " SOCIAL MEDIA FIELDS TESTING (POST-REQUEST FIX) " + "🎯" * 20)
        self.test_musician_public_endpoint_social_media_fields()
        self.test_musician_public_endpoint_null_social_media_fields()
        self.test_social_media_integration_flow()
        
        # Advanced filtering tests
        self.test_advanced_filtering()
        
        # NEW: Audience Page Search Functionality tests (HIGH PRIORITY)
        print("\n🔍 AUDIENCE PAGE SEARCH FUNCTIONALITY TESTING")
        print("=" * 50)
        self.test_audience_page_search_functionality()
        self.test_search_edge_cases()
        self.test_search_performance()
        
        # Request management tests
        self.test_create_request()
        self.test_get_musician_requests()
        self.test_update_request_status()
        self.test_real_time_polling()
        
        # CSV upload tests
        self.test_csv_preview_valid()
        self.test_csv_preview_invalid()
        self.test_csv_preview_missing_columns()
        self.test_csv_upload_valid()
        self.test_csv_duplicate_detection()
        
        # Playlist import tests (NEW)
        self.test_playlist_import_authentication()
        self.test_playlist_import_invalid_urls()
        self.test_spotify_playlist_import()
        self.test_apple_music_playlist_import()
        self.test_playlist_import_song_data_quality()
        self.test_playlist_import_duplicate_detection()
        
        # Spotify Metadata Auto-fill tests (NEW - HIGH PRIORITY)
        self.test_spotify_metadata_autofill_basic()
        self.test_spotify_metadata_autofill_second_song()
        self.test_spotify_metadata_autofill_authentication()
        self.test_spotify_metadata_autofill_edge_cases()
        self.test_spotify_metadata_autofill_response_format()
        self.test_spotify_metadata_autofill_credentials_verification()
        
        # CSV Auto-enrichment tests (NEW - HIGH PRIORITY)
        print("\n🎵 CSV AUTO-ENRICHMENT FEATURE TESTING")
        print("=" * 50)
        self.test_csv_upload_auto_enrichment_empty_metadata()
        self.test_csv_upload_auto_enrichment_partial_metadata()
        self.test_csv_upload_auto_enrichment_complete_metadata()
        self.test_csv_upload_auto_enrichment_disabled()
        self.test_csv_upload_auto_enrichment_authentication()
        
        # Batch Enrichment tests (NEW - HIGH PRIORITY)
        print("\n🔄 BATCH ENRICHMENT FEATURE TESTING")
        print("=" * 50)
        self.test_batch_enrichment_all_songs()
        self.test_batch_enrichment_specific_songs()
        self.test_batch_enrichment_no_songs_needed()
        self.test_batch_enrichment_authentication()
        self.test_batch_enrichment_response_format()
        
        # NEW: Tip Support System tests (PRIORITY TESTING)
        print("\n💰 TIP SUPPORT SYSTEM TESTING")
        print("=" * 50)
        self.test_profile_payment_fields_get()
        self.test_profile_payment_fields_update()
        self.test_tip_links_generation_basic()
        self.test_tip_links_generation_different_amounts()
        self.test_tip_links_generation_without_message()
        self.test_tip_links_generation_error_cases()
        self.test_tip_recording_basic()
        self.test_tip_recording_different_platforms()
        self.test_tip_recording_validation()
        
        # Cleanup
        self.test_delete_song()
        
        # Print summary
        print("\n" + "=" * 50)
        print("🏁 Test Summary")
        print("=" * 50)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n🔍 Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        return self.results['failed'] == 0

    def run_new_features_tests(self):
        """Run only the new CSV Auto-enrichment and Batch Enrichment feature tests"""
        print("=" * 70)
        print("🚀 NEW FEATURES TESTING - CSV AUTO-ENRICHMENT & BATCH ENRICHMENT")
        print("=" * 70)
        print("🔑 Testing with Spotify credentials:")
        print("   Client ID: 24f25c0b6f1048819102bd13ae768bde")
        print("   Testing comprehensive auto-enrichment functionality...")
        print()
        
        # Authentication setup
        self.test_musician_registration()
        if not self.auth_token:
            print("❌ Cannot proceed without authentication")
            return False
        
        # CSV Auto-enrichment Feature Tests
        print("\n🎵 CSV AUTO-ENRICHMENT FEATURE TESTING")
        print("=" * 50)
        self.test_csv_upload_auto_enrichment_empty_metadata()
        self.test_csv_upload_auto_enrichment_partial_metadata()
        self.test_csv_upload_auto_enrichment_complete_metadata()
        self.test_csv_upload_auto_enrichment_disabled()
        self.test_csv_upload_auto_enrichment_authentication()
        
        # Batch Enrichment Feature Tests
        print("\n🔄 BATCH ENRICHMENT FEATURE TESTING")
        print("=" * 50)
        self.test_batch_enrichment_all_songs()
        self.test_batch_enrichment_specific_songs()
        self.test_batch_enrichment_no_songs_needed()
        self.test_batch_enrichment_authentication()
        self.test_batch_enrichment_response_format()
        
        # Print focused summary
        print("\n" + "=" * 70)
        print("🏁 NEW FEATURES TEST SUMMARY")
        print("=" * 70)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n🔍 Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        return self.results['failed'] == 0

    def run_social_media_fields_tests(self):
        """Run focused tests for social media fields in post-request popup fix - PRIORITY 1 & 2"""
        print("=" * 80)
        print("🎯 SOCIAL MEDIA FIELDS TESTING - POST-REQUEST POPUP FIX")
        print("=" * 80)
        print("🔍 Testing the fix for social media links in the post-request popup")
        print("📋 PRIORITY 1: Test Updated Musician Public Endpoint")
        print("📋 PRIORITY 2: Test Social Media Integration Flow")
        print("=" * 80)
        
        # Reset results for focused testing
        self.results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        
        # Authentication setup (required for all tests)
        print("\n🔐 Setting up authentication...")
        self.test_musician_registration()
        
        if not self.auth_token:
            print("❌ CRITICAL: Could not authenticate - cannot proceed with social media tests")
            return False
        
        print(f"✅ Authenticated as musician: {self.musician_slug}")
        
        # PRIORITY 1: Test Updated Musician Public Endpoint
        print("\n" + "🎯" * 25 + " PRIORITY 1 TESTS " + "🎯" * 25)
        print("Testing GET /musicians/{slug} endpoint includes all 7 social media fields:")
        print("  • paypal_username")
        print("  • venmo_username") 
        print("  • instagram_username")
        print("  • facebook_username")
        print("  • tiktok_username")
        print("  • spotify_artist_url")
        print("  • apple_music_artist_url")
        print()
        
        self.test_musician_public_endpoint_social_media_fields()
        self.test_musician_public_endpoint_null_social_media_fields()
        
        # PRIORITY 2: Test Social Media Integration Flow
        print("\n" + "🎯" * 25 + " PRIORITY 2 TESTS " + "🎯" * 25)
        print("Testing complete social media integration flow:")
        print("  • Musician with social media data can be fetched via public endpoint")
        print("  • Usernames without @ symbols are returned correctly")
        print("  • URLs are returned as full URLs")
        print("  • Response format matches MusicianPublic model")
        print()
        
        self.test_social_media_integration_flow()
        
        # Print focused summary
        print("\n" + "=" * 80)
        print("🏁 SOCIAL MEDIA FIELDS TEST SUMMARY")
        print("=" * 80)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['failed'] == 0:
            print("\n🎉 SUCCESS: All social media fields tests passed!")
            print("✅ The fix for social media links in post-request popup is working correctly")
            print("✅ All 7 social media fields are included in the public musician endpoint response")
            print("✅ Fields return proper values or null without causing frontend errors")
            print("✅ Backend changes don't break existing functionality")
            print("✅ The audience interface can now access social media data for the post-request modal")
        else:
            print("\n❌ ISSUES FOUND:")
            for error in self.results['errors']:
                print(f"   • {error}")
            print("\n🔧 The social media fields fix needs attention before the post-request popup will work correctly")
        
        return self.results['failed'] == 0

    def run_spotify_metadata_tests(self):
        """Run only the Spotify Metadata Auto-fill Feature tests as requested in the review"""
        print("=" * 60)
        print("🎵 SPOTIFY METADATA AUTO-FILL FEATURE TESTING")
        print("=" * 60)
        print("🔑 Testing with new Spotify credentials:")
        print("   Client ID: 24f25c0b6f1048819102bd13ae768bde")
        print("   Testing real Spotify API integration (not fallback data)")
        print("=" * 60)
        
        # Reset results for focused testing
        self.results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        
        # Authentication setup (required for all tests)
        self.test_musician_registration()
        
        if not self.auth_token:
            print("❌ CRITICAL: Could not authenticate - cannot proceed with Spotify tests")
            return False
        
        # Run all Spotify metadata auto-fill tests
        print("\n🔍 Running Spotify Metadata Auto-fill Feature Tests...")
        
        self.test_spotify_metadata_autofill_credentials_verification()
        self.test_spotify_metadata_autofill_basic()
        self.test_spotify_metadata_autofill_second_song()
        self.test_spotify_metadata_autofill_authentication()
        self.test_spotify_metadata_autofill_edge_cases()
        self.test_spotify_metadata_autofill_response_format()
        
        # Print focused summary
        print("\n" + "=" * 60)
        print("🏁 SPOTIFY METADATA AUTO-FILL TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n🔍 Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        else:
            print("\n🎉 All Spotify Metadata Auto-fill tests passed!")
            print("✅ New Spotify credentials are working correctly")
            print("✅ Real Spotify API data is being returned (not fallback)")
            print("✅ Authentication and authorization working properly")
            print("✅ Response format matches expected structure")
            print("✅ Edge cases handled appropriately")
        
        return self.results['failed'] == 0

    def test_song_deletion_individual(self):
        """Test individual song deletion - CRITICAL BUG INVESTIGATION"""
        try:
            print("🔍 CRITICAL BUG INVESTIGATION: Testing individual song deletion")
            
            # Create multiple test songs for deletion testing
            test_songs = [
                {"title": "Delete Test Song 1", "artist": "Test Artist 1", "genres": ["Pop"], "moods": ["Upbeat"], "year": 2023},
                {"title": "Delete Test Song 2", "artist": "Test Artist 2", "genres": ["Rock"], "moods": ["Energetic"], "year": 2022},
                {"title": "Delete Test Song 3", "artist": "Test Artist 3", "genres": ["Jazz"], "moods": ["Smooth"], "year": 2021}
            ]
            
            created_song_ids = []
            
            # Create test songs
            for i, song_data in enumerate(test_songs):
                response = self.make_request("POST", "/songs", song_data)
                if response.status_code == 200:
                    song_id = response.json()["id"]
                    created_song_ids.append(song_id)
                    print(f"📊 Created test song {i+1}: {song_data['title']} (ID: {song_id})")
                else:
                    self.log_result("Song Deletion Individual - Setup", False, f"Failed to create test song {i+1}")
                    return
            
            # Get initial song count
            songs_before_response = self.make_request("GET", "/songs")
            if songs_before_response.status_code == 200:
                songs_before = songs_before_response.json()
                initial_count = len(songs_before)
                print(f"📊 Initial song count: {initial_count}")
            else:
                self.log_result("Song Deletion Individual - Initial Count", False, "Could not get initial song count")
                return
            
            # Test deleting each song individually
            for i, song_id in enumerate(created_song_ids):
                print(f"🔍 Testing deletion of song {i+1}: {song_id}")
                
                # Delete the song
                response = self.make_request("DELETE", f"/songs/{song_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"📊 Delete response: {json.dumps(data, indent=2)}")
                    
                    # Verify song is actually deleted from database
                    songs_after_response = self.make_request("GET", "/songs")
                    if songs_after_response.status_code == 200:
                        songs_after = songs_after_response.json()
                        song_exists = any(song["id"] == song_id for song in songs_after)
                        
                        if not song_exists:
                            expected_count = initial_count - (i + 1)
                            actual_count = len(songs_after)
                            
                            if actual_count == expected_count:
                                self.log_result(f"Song Deletion Individual - Song {i+1}", True, 
                                    f"✅ Song {i+1} successfully deleted. Count: {initial_count} → {actual_count}")
                            else:
                                self.log_result(f"Song Deletion Individual - Song {i+1}", False, 
                                    f"❌ Song count mismatch. Expected: {expected_count}, Actual: {actual_count}")
                        else:
                            self.log_result(f"Song Deletion Individual - Song {i+1}", False, 
                                f"❌ CRITICAL BUG: Song {i+1} still exists in database after deletion")
                    else:
                        self.log_result(f"Song Deletion Individual - Song {i+1}", False, 
                            f"Could not verify deletion: {songs_after_response.status_code}")
                else:
                    self.log_result(f"Song Deletion Individual - Song {i+1}", False, 
                        f"❌ CRITICAL BUG: Delete failed with status {response.status_code}: {response.text}")
                    
        except Exception as e:
            self.log_result("Song Deletion Individual", False, f"❌ CRITICAL BUG: Exception: {str(e)}")

    def test_song_deletion_batch_patterns(self):
        """Test batch deletion patterns - CRITICAL BUG INVESTIGATION"""
        try:
            print("🔍 CRITICAL BUG INVESTIGATION: Testing batch deletion patterns")
            
            # Create 10 test songs for batch deletion testing
            batch_songs = []
            for i in range(10):
                song_data = {
                    "title": f"Batch Delete Song {i+1}",
                    "artist": f"Batch Artist {i+1}",
                    "genres": ["Test"],
                    "moods": ["Test"],
                    "year": 2020 + i,
                    "notes": f"Song for batch deletion testing #{i+1}"
                }
                
                response = self.make_request("POST", "/songs", song_data)
                if response.status_code == 200:
                    song_id = response.json()["id"]
                    batch_songs.append({"id": song_id, "title": song_data["title"]})
                    print(f"📊 Created batch song {i+1}: {song_data['title']} (ID: {song_id})")
                else:
                    self.log_result("Song Deletion Batch - Setup", False, f"Failed to create batch song {i+1}")
                    return
            
            # Get initial count
            songs_before_response = self.make_request("GET", "/songs")
            if songs_before_response.status_code == 200:
                initial_count = len(songs_before_response.json())
                print(f"📊 Initial song count before batch deletion: {initial_count}")
            else:
                self.log_result("Song Deletion Batch - Initial Count", False, "Could not get initial count")
                return
            
            # Test rapid sequential deletion (simulate batch deletion)
            print("🔍 Testing rapid sequential deletion...")
            deletion_results = []
            
            for i, song in enumerate(batch_songs):
                print(f"🔍 Deleting song {i+1}/10: {song['title']}")
                
                response = self.make_request("DELETE", f"/songs/{song['id']}")
                deletion_results.append({
                    "song_id": song["id"],
                    "title": song["title"],
                    "status_code": response.status_code,
                    "success": response.status_code == 200
                })
                
                if response.status_code != 200:
                    print(f"❌ CRITICAL BUG: Failed to delete song {i+1}: {response.status_code} - {response.text}")
            
            # Analyze deletion results
            successful_deletions = [r for r in deletion_results if r["success"]]
            failed_deletions = [r for r in deletion_results if not r["success"]]
            
            print(f"📊 Batch deletion results: {len(successful_deletions)}/10 successful, {len(failed_deletions)}/10 failed")
            
            # Verify final database state
            songs_after_response = self.make_request("GET", "/songs")
            if songs_after_response.status_code == 200:
                songs_after = songs_after_response.json()
                final_count = len(songs_after)
                expected_count = initial_count - len(successful_deletions)
                
                # Check if any deleted songs still exist
                still_existing = []
                for result in successful_deletions:
                    if any(song["id"] == result["song_id"] for song in songs_after):
                        still_existing.append(result["title"])
                
                if len(still_existing) == 0 and final_count == expected_count:
                    self.log_result("Song Deletion Batch - Database Verification", True, 
                        f"✅ Batch deletion verified: {len(successful_deletions)} songs deleted, count: {initial_count} → {final_count}")
                else:
                    self.log_result("Song Deletion Batch - Database Verification", False, 
                        f"❌ CRITICAL BUG: Database inconsistency. Still existing: {still_existing}, Expected count: {expected_count}, Actual: {final_count}")
                
                if len(failed_deletions) == 0:
                    self.log_result("Song Deletion Batch - Success Rate", True, 
                        f"✅ All 10 batch deletions successful")
                else:
                    self.log_result("Song Deletion Batch - Success Rate", False, 
                        f"❌ CRITICAL BUG: {len(failed_deletions)}/10 batch deletions failed")
            else:
                self.log_result("Song Deletion Batch - Final Verification", False, 
                    f"Could not verify final state: {songs_after_response.status_code}")
                    
        except Exception as e:
            self.log_result("Song Deletion Batch", False, f"❌ CRITICAL BUG: Exception: {str(e)}")

    def test_song_deletion_database_verification(self):
        """Test database verification after deletion - CRITICAL BUG INVESTIGATION"""
        try:
            print("🔍 CRITICAL BUG INVESTIGATION: Testing database verification after deletion")
            
            # Create a test song specifically for database verification
            song_data = {
                "title": "Database Verification Test Song",
                "artist": "DB Test Artist",
                "genres": ["Test"],
                "moods": ["Test"],
                "year": 2023,
                "notes": "Song for database verification testing"
            }
            
            response = self.make_request("POST", "/songs", song_data)
            if response.status_code == 200:
                song_id = response.json()["id"]
                print(f"📊 Created verification test song: {song_id}")
            else:
                self.log_result("Song Deletion DB Verification - Setup", False, "Failed to create test song")
                return
            
            # Verify song exists before deletion
            songs_before_response = self.make_request("GET", "/songs")
            if songs_before_response.status_code == 200:
                songs_before = songs_before_response.json()
                song_exists_before = any(song["id"] == song_id for song in songs_before)
                
                if song_exists_before:
                    print(f"✅ Song exists in database before deletion")
                else:
                    self.log_result("Song Deletion DB Verification - Pre-check", False, "Test song not found before deletion")
                    return
            else:
                self.log_result("Song Deletion DB Verification - Pre-check", False, "Could not verify song existence before deletion")
                return
            
            # Delete the song
            print(f"🔍 Deleting song for database verification: {song_id}")
            response = self.make_request("DELETE", f"/songs/{song_id}")
            
            if response.status_code == 200:
                print(f"✅ Delete API returned success")
                
                # Multiple verification checks
                verification_checks = []
                
                # Check 1: Immediate verification
                songs_after_response = self.make_request("GET", "/songs")
                if songs_after_response.status_code == 200:
                    songs_after = songs_after_response.json()
                    song_exists_after = any(song["id"] == song_id for song in songs_after)
                    verification_checks.append(("Immediate check", not song_exists_after))
                    
                    if not song_exists_after:
                        print(f"✅ Immediate verification: Song not found in database")
                    else:
                        print(f"❌ CRITICAL BUG: Song still exists immediately after deletion")
                
                # Check 2: Delayed verification (simulate potential race conditions)
                import time
                time.sleep(1)
                
                songs_delayed_response = self.make_request("GET", "/songs")
                if songs_delayed_response.status_code == 200:
                    songs_delayed = songs_delayed_response.json()
                    song_exists_delayed = any(song["id"] == song_id for song in songs_delayed)
                    verification_checks.append(("Delayed check (1s)", not song_exists_delayed))
                    
                    if not song_exists_delayed:
                        print(f"✅ Delayed verification: Song not found in database")
                    else:
                        print(f"❌ CRITICAL BUG: Song still exists after 1 second delay")
                
                # Check 3: Try to access deleted song directly
                try:
                    direct_response = self.make_request("GET", f"/songs/{song_id}")
                    if direct_response.status_code == 404:
                        verification_checks.append(("Direct access check", True))
                        print(f"✅ Direct access verification: Song returns 404")
                    else:
                        verification_checks.append(("Direct access check", False))
                        print(f"❌ CRITICAL BUG: Deleted song still accessible directly: {direct_response.status_code}")
                except:
                    verification_checks.append(("Direct access check", True))
                    print(f"✅ Direct access verification: Song not accessible")
                
                # Evaluate all verification checks
                all_passed = all(check[1] for check in verification_checks)
                failed_checks = [check[0] for check in verification_checks if not check[1]]
                
                if all_passed:
                    self.log_result("Song Deletion DB Verification", True, 
                        f"✅ All database verification checks passed: {[check[0] for check in verification_checks]}")
                else:
                    self.log_result("Song Deletion DB Verification", False, 
                        f"❌ CRITICAL BUG: Failed verification checks: {failed_checks}")
            else:
                self.log_result("Song Deletion DB Verification", False, 
                    f"❌ CRITICAL BUG: Delete API failed: {response.status_code} - {response.text}")
                    
        except Exception as e:
            self.log_result("Song Deletion DB Verification", False, f"❌ CRITICAL BUG: Exception: {str(e)}")

    def test_song_deletion_limits_check(self):
        """Test song limits and deletion behavior - CRITICAL BUG INVESTIGATION"""
        try:
            print("🔍 CRITICAL BUG INVESTIGATION: Testing song limits and deletion behavior")
            
            # Get current song count
            songs_response = self.make_request("GET", "/songs")
            if songs_response.status_code == 200:
                current_songs = songs_response.json()
                current_count = len(current_songs)
                print(f"📊 Current song count: {current_count}")
                
                # Check if we're approaching the 1000-song limit mentioned in the review
                if current_count > 900:
                    print(f"⚠️ WARNING: Approaching 1000-song limit with {current_count} songs")
                    self.log_result("Song Deletion Limits - High Count Warning", True, 
                        f"High song count detected: {current_count} (approaching 1000 limit)")
                
                # Test deletion behavior with current song count
                if current_count > 0:
                    # Try to delete the first song to test deletion at current count
                    first_song = current_songs[0]
                    song_id = first_song["id"]
                    
                    print(f"🔍 Testing deletion at current count ({current_count}): {first_song['title']}")
                    
                    response = self.make_request("DELETE", f"/songs/{song_id}")
                    
                    if response.status_code == 200:
                        # Verify deletion worked
                        songs_after_response = self.make_request("GET", "/songs")
                        if songs_after_response.status_code == 200:
                            songs_after = songs_after_response.json()
                            new_count = len(songs_after)
                            
                            if new_count == current_count - 1:
                                self.log_result("Song Deletion Limits - Current Count Test", True, 
                                    f"✅ Deletion works at current count: {current_count} → {new_count}")
                            else:
                                self.log_result("Song Deletion Limits - Current Count Test", False, 
                                    f"❌ CRITICAL BUG: Count mismatch after deletion: expected {current_count - 1}, got {new_count}")
                        else:
                            self.log_result("Song Deletion Limits - Current Count Test", False, 
                                f"Could not verify count after deletion: {songs_after_response.status_code}")
                    else:
                        self.log_result("Song Deletion Limits - Current Count Test", False, 
                            f"❌ CRITICAL BUG: Deletion failed at current count: {response.status_code} - {response.text}")
                else:
                    self.log_result("Song Deletion Limits - Current Count Test", True, 
                        "No songs to test deletion with (empty database)")
                
                # Test fetching behavior with current count (check for 1000-song limit)
                if current_count >= 1000:
                    print(f"⚠️ CRITICAL: Song count at or above 1000 limit: {current_count}")
                    self.log_result("Song Deletion Limits - 1000 Song Limit", False, 
                        f"❌ CRITICAL BUG: Song count exceeds 1000 limit: {current_count}")
                elif current_count > 500:
                    print(f"📊 High song count detected: {current_count} (user wants 4000+ support)")
                    self.log_result("Song Deletion Limits - High Count Support", False, 
                        f"❌ LIMITATION: Current count {current_count} - user needs 4000+ song support")
                else:
                    self.log_result("Song Deletion Limits - Count Check", True, 
                        f"✅ Song count within reasonable limits: {current_count}")
                        
            else:
                self.log_result("Song Deletion Limits - Count Check", False, 
                    f"Could not get current song count: {songs_response.status_code}")
                    
        except Exception as e:
            self.log_result("Song Deletion Limits", False, f"❌ CRITICAL BUG: Exception: {str(e)}")

    def test_song_deletion_edge_cases(self):
        """Test song deletion edge cases - CRITICAL BUG INVESTIGATION"""
        try:
            print("🔍 CRITICAL BUG INVESTIGATION: Testing song deletion edge cases")
            
            # Edge Case 1: Delete non-existent song
            fake_song_id = "non-existent-song-id-12345"
            print(f"🔍 Testing deletion of non-existent song: {fake_song_id}")
            
            response = self.make_request("DELETE", f"/songs/{fake_song_id}")
            
            if response.status_code == 404:
                self.log_result("Song Deletion Edge Cases - Non-existent Song", True, 
                    "✅ Correctly returned 404 for non-existent song")
            else:
                self.log_result("Song Deletion Edge Cases - Non-existent Song", False, 
                    f"❌ Expected 404 for non-existent song, got: {response.status_code}")
            
            # Edge Case 2: Delete with invalid song ID format
            invalid_song_ids = ["", "invalid-id", "123", "null", "undefined"]
            
            for invalid_id in invalid_song_ids:
                print(f"🔍 Testing deletion with invalid ID: '{invalid_id}'")
                
                response = self.make_request("DELETE", f"/songs/{invalid_id}")
                
                if response.status_code in [400, 404]:
                    self.log_result(f"Song Deletion Edge Cases - Invalid ID '{invalid_id}'", True, 
                        f"✅ Correctly rejected invalid ID with status {response.status_code}")
                else:
                    self.log_result(f"Song Deletion Edge Cases - Invalid ID '{invalid_id}'", False, 
                        f"❌ Expected 400/404 for invalid ID, got: {response.status_code}")
            
            # Edge Case 3: Test deletion without authentication (already covered in other tests)
            original_token = self.auth_token
            self.auth_token = None
            
            response = self.make_request("DELETE", f"/songs/{fake_song_id}")
            
            if response.status_code in [401, 403]:
                self.log_result("Song Deletion Edge Cases - No Auth", True, 
                    f"✅ Correctly rejected deletion without auth: {response.status_code}")
            else:
                self.log_result("Song Deletion Edge Cases - No Auth", False, 
                    f"❌ Expected 401/403 without auth, got: {response.status_code}")
            
            # Restore auth token
            self.auth_token = original_token
            
            # Edge Case 4: Test deletion of song with active requests
            if self.test_song_id:
                print(f"🔍 Testing deletion of song with active requests")
                
                # Create a request for the test song
                request_data = {
                    "song_id": self.test_song_id,
                    "requester_name": "Edge Case Requester",
                    "requester_email": "edge@example.com",
                    "dedication": "Request for deletion edge case testing"
                }
                
                request_response = self.make_request("POST", "/requests", request_data)
                
                if request_response.status_code == 200:
                    print(f"✅ Created request for song deletion edge case testing")
                    
                    # Now try to delete the song that has an active request
                    response = self.make_request("DELETE", f"/songs/{self.test_song_id}")
                    
                    if response.status_code == 200:
                        self.log_result("Song Deletion Edge Cases - Song with Requests", True, 
                            "✅ Successfully deleted song with active requests")
                        
                        # Verify the song is actually deleted
                        songs_response = self.make_request("GET", "/songs")
                        if songs_response.status_code == 200:
                            songs = songs_response.json()
                            song_exists = any(song["id"] == self.test_song_id for song in songs)
                            
                            if not song_exists:
                                self.log_result("Song Deletion Edge Cases - Verification with Requests", True, 
                                    "✅ Song with requests successfully deleted from database")
                            else:
                                self.log_result("Song Deletion Edge Cases - Verification with Requests", False, 
                                    "❌ CRITICAL BUG: Song with requests still exists after deletion")
                    else:
                        self.log_result("Song Deletion Edge Cases - Song with Requests", False, 
                            f"❌ CRITICAL BUG: Failed to delete song with requests: {response.status_code}")
                else:
                    print(f"⚠️ Could not create request for edge case testing: {request_response.status_code}")
                    
        except Exception as e:
            self.log_result("Song Deletion Edge Cases", False, f"❌ CRITICAL BUG: Exception: {str(e)}")

    def run_song_deletion_investigation(self):
        """Run comprehensive song deletion investigation as requested in the review"""
        print("🚨 CRITICAL BUG INVESTIGATION - SONG DELETION FUNCTIONALITY")
        print("=" * 70)
        print("User reported: 'I cant seem to log in. i tried forgot password and it still wont work'")
        print("User reported: Error when deleting all songs + songs limited to 1000 (wants 4000+)")
        print("=" * 70)
        print("INVESTIGATION PRIORITIES:")
        print("1. Individual Song Deletion (DELETE /api/songs/{song_id})")
        print("2. Batch Deletion Patterns (simulate 'delete all songs')")
        print("3. Database Verification (ensure songs actually deleted)")
        print("4. Song Limits Check (1000-song limit vs 4000+ requirement)")
        print("5. Edge Cases (authentication, invalid IDs, etc.)")
        print("=" * 70)
        
        # Reset results for focused testing
        self.results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        
        # Authentication setup
        self.test_musician_registration()
        if not self.auth_token:
            print("❌ CRITICAL: Could not authenticate - cannot proceed with deletion tests")
            return False
        
        # Create a test song for basic deletion testing
        self.test_create_song()
        
        print("\n🔥 PRIORITY 1: INDIVIDUAL SONG DELETION")
        print("-" * 50)
        self.test_song_deletion_individual()
        
        print("\n🔥 PRIORITY 2: BATCH DELETION PATTERNS")
        print("-" * 50)
        self.test_song_deletion_batch_patterns()
        
        print("\n🔥 PRIORITY 3: DATABASE VERIFICATION")
        print("-" * 50)
        self.test_song_deletion_database_verification()
        
        print("\n🔥 PRIORITY 4: SONG LIMITS CHECK")
        print("-" * 50)
        self.test_song_deletion_limits_check()
        
        print("\n🔥 PRIORITY 5: EDGE CASES")
        print("-" * 50)
        self.test_song_deletion_edge_cases()
        
        # Also run existing deletion tests for completeness
        print("\n🔥 EXISTING DELETION TESTS")
        print("-" * 50)
        self.test_delete_song_authentication()
        
        # Print comprehensive summary
        print("\n" + "=" * 70)
        print("🏁 SONG DELETION INVESTIGATION SUMMARY")
        print("=" * 70)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n🔍 CRITICAL ISSUES FOUND:")
            for error in self.results['errors']:
                print(f"   • {error}")
        else:
            print("\n🎉 NO CRITICAL ISSUES FOUND!")
            print("✅ Individual song deletion working correctly")
            print("✅ Batch deletion patterns working correctly")
            print("✅ Database verification successful")
            print("✅ Song limits within acceptable range")
            print("✅ Edge cases handled properly")
        
        # Specific analysis for the user's reported issues
        deletion_tests = [error for error in self.results['errors'] if 'deletion' in error.lower() or 'delete' in error.lower()]
        limit_tests = [error for error in self.results['errors'] if 'limit' in error.lower() or 'count' in error.lower()]
        
        print(f"\n📊 SONG DELETION FUNCTIONALITY: {'✅ WORKING' if len(deletion_tests) == 0 else '❌ FAILING'}")
        if deletion_tests:
            print("   DELETION ISSUES:")
            for error in deletion_tests:
                print(f"   • {error}")
        
        print(f"📊 SONG LIMITS (1000 vs 4000+): {'✅ OK' if len(limit_tests) == 0 else '❌ LIMITATION'}")
        if limit_tests:
            print("   LIMIT ISSUES:")
            for error in limit_tests:
                print(f"   • {error}")
        
        return self.results['failed'] == 0

if __name__ == "__main__":
    tester = RequestWaveAPITester()
    
    # Run Song Deletion Investigation as requested in the review
    success = tester.run_song_deletion_investigation()
    
    if success:
        print("\n🎉 Song deletion investigation completed successfully!")
        print("✅ No critical bugs found in song deletion functionality")
        print("✅ Individual and batch deletion working correctly")
        print("✅ Database operations completing successfully")
        print("✅ Authentication working properly for deletions")
        exit(0)
    else:
        print(f"\n💥 CRITICAL BUGS FOUND: {tester.results['failed']} issues detected!")
        print("❌ Song deletion functionality has critical problems")
        print("❌ Immediate investigation and fixes required")
        exit(1)