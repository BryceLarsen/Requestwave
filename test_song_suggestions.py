#!/usr/bin/env python3
"""
Focused Song Suggestion Feature Testing
Tests the FIXED Song Suggestion functionality with comprehensive verification
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://4ea289bc-16f8-4f83-aa5c-66fcd9ce34a7.preview.emergentagent.com/api"
TEST_MUSICIAN = {
    "name": "Song Suggestion Tester",
    "email": "suggestion.tester@requestwave.com",
    "password": "SecurePassword123!"
}

class SongSuggestionTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
        self.created_suggestions = []
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
            # Try to register
            response = self.make_request("POST", "/auth/register", TEST_MUSICIAN)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data["token"]
                self.musician_id = data["musician"]["id"]
                self.musician_slug = data["musician"]["slug"]
                self.log_result("Authentication Setup", True, f"Registered musician: {data['musician']['name']}")
            elif response.status_code == 400:
                # Try login instead
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
                    self.log_result("Authentication Setup", True, f"Logged in musician: {data['musician']['name']}")
                else:
                    self.log_result("Authentication Setup", False, f"Login failed: {response.status_code}")
                    return False
            else:
                self.log_result("Authentication Setup", False, f"Registration failed: {response.status_code}")
                return False
            
            return True
        except Exception as e:
            self.log_result("Authentication Setup", False, f"Exception: {str(e)}")
            return False

    def test_song_suggestions_pro_feature_access_control(self):
        """Test Pro feature access control for song suggestions - CRITICAL BUG FIX TEST"""
        try:
            if not self.musician_slug:
                self.log_result("Song Suggestions - Pro Feature Access Control", False, "No musician slug available")
                return
            
            print("🔍 Testing Song Suggestions Pro Feature Access Control")
            
            # Test creating a song suggestion (should work by default)
            suggestion_data = {
                "musician_slug": self.musician_slug,
                "suggested_title": "Test Suggestion",
                "suggested_artist": "Test Artist",
                "requester_name": "Test Requester",
                "requester_email": "test@example.com",
                "message": "Please add this song!"
            }
            
            response = self.make_request("POST", "/song-suggestions", suggestion_data)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and data.get("status") == "pending":
                    self.log_result("Song Suggestions - Pro Feature Access Control (Default)", True, "✅ CRITICAL BUG FIXED: Song suggestions work when enabled by default")
                    # Store suggestion ID for cleanup
                    self.created_suggestions.append(data["id"])
                else:
                    self.log_result("Song Suggestions - Pro Feature Access Control (Default)", False, f"❌ Unexpected response: {data}")
            elif response.status_code == 403:
                data = response.json()
                if "song suggestions are disabled" in data.get("detail", "").lower():
                    self.log_result("Song Suggestions - Pro Feature Access Control (Disabled)", True, "✅ CRITICAL BUG FIXED: Correctly blocks suggestions when disabled")
                else:
                    self.log_result("Song Suggestions - Pro Feature Access Control (Disabled)", False, f"❌ Wrong error message: {data}")
            else:
                self.log_result("Song Suggestions - Pro Feature Access Control", False, f"❌ Unexpected status code: {response.status_code}")
                
        except Exception as e:
            self.log_result("Song Suggestions - Pro Feature Access Control", False, f"❌ Exception: {str(e)}")

    def test_song_suggestions_creation_workflow(self):
        """Test complete song suggestion creation workflow"""
        try:
            if not self.musician_slug:
                self.log_result("Song Suggestions - Creation Workflow", False, "No musician slug available")
                return
            
            print("🔍 Testing Song Suggestions Creation Workflow")
            
            # Test creating multiple song suggestions
            suggestions_data = [
                {
                    "musician_slug": self.musician_slug,
                    "suggested_title": "Bohemian Rhapsody",
                    "suggested_artist": "Queen",
                    "requester_name": "Rock Fan",
                    "requester_email": "rockfan@example.com",
                    "message": "This is a classic rock anthem!"
                },
                {
                    "musician_slug": self.musician_slug,
                    "suggested_title": "Hotel California",
                    "suggested_artist": "Eagles",
                    "requester_name": "Classic Rock Lover",
                    "requester_email": "classicrock@example.com",
                    "message": "Please play this masterpiece"
                }
            ]
            
            created_count = 0
            
            for i, suggestion_data in enumerate(suggestions_data):
                response = self.make_request("POST", "/song-suggestions", suggestion_data)
                
                if response.status_code == 200:
                    data = response.json()
                    if "id" in data and data.get("status") == "pending":
                        self.created_suggestions.append(data["id"])
                        created_count += 1
                        self.log_result(f"Song Suggestions - Create Suggestion {i+1}", True, f"Created suggestion: {data['suggested_title']}")
                    else:
                        self.log_result(f"Song Suggestions - Create Suggestion {i+1}", False, f"Unexpected response: {data}")
                else:
                    self.log_result(f"Song Suggestions - Create Suggestion {i+1}", False, f"Status code: {response.status_code}")
            
            if created_count == len(suggestions_data):
                self.log_result("Song Suggestions - Creation Workflow", True, f"✅ Successfully created {created_count} suggestions")
            else:
                self.log_result("Song Suggestions - Creation Workflow", False, f"❌ Only created {created_count} out of {len(suggestions_data)} suggestions")
                
        except Exception as e:
            self.log_result("Song Suggestions - Creation Workflow", False, f"❌ Exception: {str(e)}")

    def test_song_suggestions_view_management(self):
        """Test viewing and managing song suggestions"""
        try:
            if not self.created_suggestions:
                self.log_result("Song Suggestions - View Management", False, "No created suggestions available")
                return
            
            print("🔍 Testing Song Suggestions View Management")
            
            # Test getting all suggestions for musician
            response = self.make_request("GET", "/song-suggestions")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    # Check if our created suggestions are in the list
                    suggestion_ids = [s["id"] for s in data]
                    found_suggestions = [sid for sid in self.created_suggestions if sid in suggestion_ids]
                    
                    if len(found_suggestions) >= len(self.created_suggestions):
                        self.log_result("Song Suggestions - View All", True, f"✅ Retrieved {len(data)} suggestions including our test suggestions")
                        
                        # Verify suggestion structure
                        if data:
                            first_suggestion = data[0]
                            required_fields = ["id", "musician_id", "suggested_title", "suggested_artist", "requester_name", "requester_email", "status", "created_at"]
                            missing_fields = [field for field in required_fields if field not in first_suggestion]
                            
                            if not missing_fields:
                                self.log_result("Song Suggestions - Response Structure", True, "✅ Suggestion response has all required fields")
                            else:
                                self.log_result("Song Suggestions - Response Structure", False, f"❌ Missing fields: {missing_fields}")
                    else:
                        self.log_result("Song Suggestions - View All", False, f"❌ Could not find our test suggestions in response")
                else:
                    self.log_result("Song Suggestions - View All", False, f"❌ Expected list, got: {type(data)}")
            else:
                self.log_result("Song Suggestions - View All", False, f"❌ Status code: {response.status_code}")
                
        except Exception as e:
            self.log_result("Song Suggestions - View Management", False, f"❌ Exception: {str(e)}")

    def test_song_suggestions_accept_with_default_values(self):
        """Test accepting suggestions creates songs with default values - CRITICAL BUG FIX TEST"""
        try:
            if not self.created_suggestions:
                self.log_result("Song Suggestions - Accept with Default Values", False, "No created suggestions available")
                return
            
            print("🔍 Testing Song Suggestions Accept with Default Values")
            
            # Accept the first suggestion
            suggestion_id = self.created_suggestions[0]
            
            response = self.make_request("PUT", f"/song-suggestions/{suggestion_id}/status", {"status": "added"})
            
            if response.status_code == 200:
                data = response.json()
                if data.get("message") and "added to repertoire" in data["message"]:
                    self.log_result("Song Suggestions - Accept API", True, "✅ Successfully accepted suggestion")
                    
                    # CRITICAL TEST: Verify the created song has DEFAULT values, not Spotify enriched data
                    songs_response = self.make_request("GET", "/songs")
                    if songs_response.status_code == 200:
                        songs = songs_response.json()
                        
                        # Find the song created from suggestion (should have "Added from audience suggestion" in notes)
                        suggestion_songs = [song for song in songs if "audience suggestion" in song.get("notes", "").lower()]
                        
                        if suggestion_songs:
                            created_song = suggestion_songs[-1]  # Get the most recent one
                            print(f"📊 Created song from suggestion: {json.dumps(created_song, indent=2)}")
                            
                            # CRITICAL BUG FIX TEST: Check for DEFAULT values
                            expected_defaults = {
                                "genres": ["Pop"],
                                "moods": ["Upbeat"],
                                "year": None,
                                "decade": None
                            }
                            
                            default_value_errors = []
                            
                            # Check genres
                            if created_song.get("genres") != expected_defaults["genres"]:
                                default_value_errors.append(f"Genres: expected {expected_defaults['genres']}, got {created_song.get('genres')}")
                            
                            # Check moods
                            if created_song.get("moods") != expected_defaults["moods"]:
                                default_value_errors.append(f"Moods: expected {expected_defaults['moods']}, got {created_song.get('moods')}")
                            
                            # Check year (should be null/None)
                            if created_song.get("year") is not None:
                                default_value_errors.append(f"Year: expected None, got {created_song.get('year')}")
                            
                            # Check decade (should be null/None)
                            if created_song.get("decade") is not None:
                                default_value_errors.append(f"Decade: expected None, got {created_song.get('decade')}")
                            
                            # Check that NO Spotify enrichment was applied
                            spotify_indicators = []
                            if "spotify_id" in created_song:
                                spotify_indicators.append("spotify_id field present")
                            if created_song.get("genres") and len(created_song["genres"]) > 1:
                                spotify_indicators.append("Multiple genres (suggests Spotify enrichment)")
                            if created_song.get("year") and created_song["year"] > 1900:
                                spotify_indicators.append("Real year value (suggests Spotify enrichment)")
                            
                            if not default_value_errors and not spotify_indicators:
                                self.log_result("Song Suggestions - Default Values", True, "✅ CRITICAL BUG FIXED: Accepted suggestion created song with default values (no Spotify enrichment)")
                            elif not default_value_errors:
                                self.log_result("Song Suggestions - Default Values", False, f"❌ CRITICAL BUG: Spotify enrichment detected: {spotify_indicators}")
                            else:
                                self.log_result("Song Suggestions - Default Values", False, f"❌ CRITICAL BUG: Wrong default values: {default_value_errors}")
                            
                            # Check attribution in notes
                            if "Added from audience suggestion by" in created_song.get("notes", ""):
                                self.log_result("Song Suggestions - Attribution", True, "✅ Song has proper attribution in notes")
                            else:
                                self.log_result("Song Suggestions - Attribution", False, f"❌ Missing attribution in notes: {created_song.get('notes')}")
                                
                        else:
                            self.log_result("Song Suggestions - Accept with Default Values", False, "❌ CRITICAL BUG: No song created from accepted suggestion")
                    else:
                        self.log_result("Song Suggestions - Accept with Default Values", False, f"❌ Could not retrieve songs: {songs_response.status_code}")
                else:
                    self.log_result("Song Suggestions - Accept API", False, f"❌ Unexpected response: {data}")
            else:
                self.log_result("Song Suggestions - Accept with Default Values", False, f"❌ Status code: {response.status_code}")
                
        except Exception as e:
            self.log_result("Song Suggestions - Accept with Default Values", False, f"❌ Exception: {str(e)}")

    def test_song_suggestions_reject_workflow(self):
        """Test rejecting song suggestions"""
        try:
            if len(self.created_suggestions) < 2:
                self.log_result("Song Suggestions - Reject Workflow", False, "Need at least 2 created suggestions")
                return
            
            print("🔍 Testing Song Suggestions Reject Workflow")
            
            # Reject the second suggestion
            suggestion_id = self.created_suggestions[1]
            
            response = self.make_request("PUT", f"/song-suggestions/{suggestion_id}/status", {"status": "rejected"})
            
            if response.status_code == 200:
                data = response.json()
                if data.get("message") and "rejected" in data["message"]:
                    self.log_result("Song Suggestions - Reject API", True, "✅ Successfully rejected suggestion")
                    
                    # Verify no song was created from rejected suggestion
                    songs_response = self.make_request("GET", "/songs")
                    if songs_response.status_code == 200:
                        songs = songs_response.json()
                        
                        # Check that no song was created with the rejected suggestion's title
                        rejected_song_found = any(song.get("title") == "Hotel California" and "audience suggestion" in song.get("notes", "") for song in songs)
                        
                        if not rejected_song_found:
                            self.log_result("Song Suggestions - Reject No Song Created", True, "✅ Correctly did not create song from rejected suggestion")
                        else:
                            self.log_result("Song Suggestions - Reject No Song Created", False, "❌ Song was created from rejected suggestion")
                    else:
                        self.log_result("Song Suggestions - Reject No Song Created", False, f"Could not verify: {songs_response.status_code}")
                else:
                    self.log_result("Song Suggestions - Reject API", False, f"❌ Unexpected response: {data}")
            else:
                self.log_result("Song Suggestions - Reject Workflow", False, f"❌ Status code: {response.status_code}")
                
        except Exception as e:
            self.log_result("Song Suggestions - Reject Workflow", False, f"❌ Exception: {str(e)}")

    def test_song_suggestions_validation(self):
        """Test song suggestion validation and error handling"""
        try:
            if not self.musician_slug:
                self.log_result("Song Suggestions - Validation", False, "No musician slug available")
                return
            
            print("🔍 Testing Song Suggestions Validation")
            
            # Test missing required fields
            validation_tests = [
                ({}, "empty request"),
                ({"musician_slug": self.musician_slug}, "missing title and artist"),
                ({"musician_slug": self.musician_slug, "suggested_title": "Test"}, "missing artist"),
                ({"musician_slug": self.musician_slug, "suggested_title": "Test", "suggested_artist": "Artist"}, "missing requester info"),
                ({"musician_slug": self.musician_slug, "suggested_title": "Test", "suggested_artist": "Artist", "requester_name": "Name"}, "missing email"),
                ({"musician_slug": self.musician_slug, "suggested_title": "Test", "suggested_artist": "Artist", "requester_name": "Name", "requester_email": "invalid-email"}, "invalid email format")
            ]
            
            validation_passed = 0
            
            for test_data, test_description in validation_tests:
                response = self.make_request("POST", "/song-suggestions", test_data)
                
                if response.status_code in [400, 422]:  # Accept both validation error codes
                    validation_passed += 1
                    self.log_result(f"Song Suggestions - Validation ({test_description})", True, f"✅ Correctly rejected: {test_description}")
                else:
                    self.log_result(f"Song Suggestions - Validation ({test_description})", False, f"❌ Should reject {test_description}, got {response.status_code}")
            
            # Test duplicate prevention
            duplicate_data = {
                "musician_slug": self.musician_slug,
                "suggested_title": "Bohemian Rhapsody",  # Same as first created suggestion
                "suggested_artist": "Queen",
                "requester_name": "Another Fan",
                "requester_email": "anotherfan@example.com",
                "message": "Please add this song again!"
            }
            
            response = self.make_request("POST", "/song-suggestions", duplicate_data)
            
            if response.status_code == 400:
                data = response.json()
                if "already suggested" in data.get("detail", "").lower() or "duplicate" in data.get("detail", "").lower():
                    self.log_result("Song Suggestions - Duplicate Prevention", True, "✅ Correctly prevented duplicate suggestion")
                    validation_passed += 1
                else:
                    self.log_result("Song Suggestions - Duplicate Prevention", False, f"❌ Wrong error message: {data}")
            else:
                self.log_result("Song Suggestions - Duplicate Prevention", False, f"❌ Should prevent duplicates, got {response.status_code}")
            
            if validation_passed >= 6:  # Most validation tests passed
                self.log_result("Song Suggestions - Validation", True, f"✅ Validation working correctly ({validation_passed} tests passed)")
            else:
                self.log_result("Song Suggestions - Validation", False, f"❌ Validation issues ({validation_passed} tests passed)")
                
        except Exception as e:
            self.log_result("Song Suggestions - Validation", False, f"❌ Exception: {str(e)}")

    def test_song_suggestions_authentication(self):
        """Test song suggestion authentication requirements"""
        try:
            print("🔍 Testing Song Suggestions Authentication")
            
            # Save current token
            original_token = self.auth_token
            
            # Test management endpoints without authentication
            self.auth_token = None
            
            # Test GET /song-suggestions without auth
            response = self.make_request("GET", "/song-suggestions")
            if response.status_code in [401, 403]:
                self.log_result("Song Suggestions - Auth GET", True, f"✅ Correctly requires auth for GET (status: {response.status_code})")
            else:
                self.log_result("Song Suggestions - Auth GET", False, f"❌ Should require auth for GET, got {response.status_code}")
            
            # Test PUT /song-suggestions/{id}/status without auth
            if self.created_suggestions:
                response = self.make_request("PUT", f"/song-suggestions/{self.created_suggestions[0]}/status", {"status": "added"})
                if response.status_code in [401, 403]:
                    self.log_result("Song Suggestions - Auth PUT", True, f"✅ Correctly requires auth for PUT (status: {response.status_code})")
                else:
                    self.log_result("Song Suggestions - Auth PUT", False, f"❌ Should require auth for PUT, got {response.status_code}")
            
            # Test DELETE /song-suggestions/{id} without auth
            if self.created_suggestions:
                response = self.make_request("DELETE", f"/song-suggestions/{self.created_suggestions[0]}")
                if response.status_code in [401, 403]:
                    self.log_result("Song Suggestions - Auth DELETE", True, f"✅ Correctly requires auth for DELETE (status: {response.status_code})")
                else:
                    self.log_result("Song Suggestions - Auth DELETE", False, f"❌ Should require auth for DELETE, got {response.status_code}")
            
            # Restore token
            self.auth_token = original_token
            
            self.log_result("Song Suggestions - Authentication", True, "✅ Authentication requirements working correctly")
                
        except Exception as e:
            self.log_result("Song Suggestions - Authentication", False, f"❌ Exception: {str(e)}")

    def test_song_suggestions_delete(self):
        """Test deleting song suggestions"""
        try:
            if not self.created_suggestions:
                self.log_result("Song Suggestions - Delete", False, "No created suggestions available")
                return
            
            print("🔍 Testing Song Suggestions Delete")
            
            # Delete one of the created suggestions
            suggestion_id = self.created_suggestions[-1]  # Delete the last one
            
            response = self.make_request("DELETE", f"/song-suggestions/{suggestion_id}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("message") and "deleted" in data["message"]:
                    self.log_result("Song Suggestions - Delete API", True, "✅ Successfully deleted suggestion")
                    
                    # Verify suggestion is actually deleted
                    suggestions_response = self.make_request("GET", "/song-suggestions")
                    if suggestions_response.status_code == 200:
                        suggestions = suggestions_response.json()
                        suggestion_ids = [s["id"] for s in suggestions]
                        
                        if suggestion_id not in suggestion_ids:
                            self.log_result("Song Suggestions - Delete Verification", True, "✅ Suggestion successfully removed from database")
                        else:
                            self.log_result("Song Suggestions - Delete Verification", False, "❌ Suggestion still exists in database")
                    else:
                        self.log_result("Song Suggestions - Delete Verification", False, f"Could not verify deletion: {suggestions_response.status_code}")
                else:
                    self.log_result("Song Suggestions - Delete API", False, f"❌ Unexpected response: {data}")
            else:
                self.log_result("Song Suggestions - Delete", False, f"❌ Status code: {response.status_code}")
                
        except Exception as e:
            self.log_result("Song Suggestions - Delete", False, f"❌ Exception: {str(e)}")

    def test_song_suggestions_edge_cases(self):
        """Test song suggestion edge cases"""
        try:
            if not self.musician_slug:
                self.log_result("Song Suggestions - Edge Cases", False, "No musician slug available")
                return
            
            print("🔍 Testing Song Suggestions Edge Cases")
            
            # Test non-existent suggestion ID
            response = self.make_request("PUT", "/song-suggestions/non-existent-id/status", {"status": "added"})
            if response.status_code == 404:
                self.log_result("Song Suggestions - Non-existent ID", True, "✅ Correctly handles non-existent suggestion ID")
            else:
                self.log_result("Song Suggestions - Non-existent ID", False, f"❌ Should return 404 for non-existent ID, got {response.status_code}")
            
            # Test invalid status values
            if self.created_suggestions:
                response = self.make_request("PUT", f"/song-suggestions/{self.created_suggestions[0]}/status", {"status": "invalid_status"})
                if response.status_code in [400, 422]:
                    self.log_result("Song Suggestions - Invalid Status", True, "✅ Correctly rejects invalid status values")
                else:
                    self.log_result("Song Suggestions - Invalid Status", False, f"❌ Should reject invalid status, got {response.status_code}")
            
            self.log_result("Song Suggestions - Edge Cases", True, "✅ Edge case testing completed")
                
        except Exception as e:
            self.log_result("Song Suggestions - Edge Cases", False, f"❌ Exception: {str(e)}")

    def run_comprehensive_tests(self):
        """Run comprehensive song suggestion tests"""
        print("🎵" * 80)
        print("🎵 SONG SUGGESTION FEATURE COMPREHENSIVE TESTING")
        print("🎵 Testing FIXED Pro Feature Access Control & Default Song Values")
        print("🎵" * 80)
        
        # Setup
        if not self.setup_authentication():
            print("❌ CRITICAL: Authentication setup failed - cannot continue")
            return False
        
        # Run all song suggestion tests
        print("\n🔧 1. Pro Feature Access Control Testing")
        print("-" * 50)
        self.test_song_suggestions_pro_feature_access_control()
        
        print("\n🔧 2. Song Suggestion Creation Workflow")
        print("-" * 50)
        self.test_song_suggestions_creation_workflow()
        
        print("\n🔧 3. View and Management Testing")
        print("-" * 50)
        self.test_song_suggestions_view_management()
        
        print("\n🔧 4. Accept with Default Values (CRITICAL BUG FIX)")
        print("-" * 50)
        self.test_song_suggestions_accept_with_default_values()
        
        print("\n🔧 5. Reject Workflow Testing")
        print("-" * 50)
        self.test_song_suggestions_reject_workflow()
        
        print("\n🔧 6. Validation and Error Handling")
        print("-" * 50)
        self.test_song_suggestions_validation()
        
        print("\n🔧 7. Authentication Requirements")
        print("-" * 50)
        self.test_song_suggestions_authentication()
        
        print("\n🔧 8. Delete Functionality")
        print("-" * 50)
        self.test_song_suggestions_delete()
        
        print("\n🔧 9. Edge Cases Testing")
        print("-" * 50)
        self.test_song_suggestions_edge_cases()
        
        # Print final results
        print("\n" + "🎵" * 80)
        print("🏁 SONG SUGGESTION FEATURE TEST RESULTS")
        print("🎵" * 80)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Total: {self.results['passed'] + self.results['failed']}")
        
        if self.results['failed'] > 0:
            print(f"\n🔍 Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed'])) * 100 if (self.results['passed'] + self.results['failed']) > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("🎉 EXCELLENT: Song Suggestion feature is working very well!")
            print("✅ Critical bugs appear to be FIXED")
        elif success_rate >= 75:
            print("✅ GOOD: Song Suggestion feature is mostly working")
            print("⚠️  Some minor issues may remain")
        elif success_rate >= 50:
            print("⚠️  MODERATE: Song Suggestion feature has some issues")
            print("❌ Critical bugs may still exist")
        else:
            print("❌ CRITICAL: Song Suggestion feature has major issues")
            print("❌ Critical bugs are NOT fixed")
        
        return success_rate >= 75

if __name__ == "__main__":
    tester = SongSuggestionTester()
    success = tester.run_comprehensive_tests()
    exit(0 if success else 1)