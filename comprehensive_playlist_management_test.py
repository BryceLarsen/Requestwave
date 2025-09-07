#!/usr/bin/env python3
"""
COMPREHENSIVE PLAYLIST MANAGEMENT SYSTEM TESTING

Testing the comprehensive playlist management system with new UI controls as requested:

SPECIFIC TESTS FROM REVIEW REQUEST:
1. Test playlist rename functionality:
   - Login with brycelarsenmusic@gmail.com / RequestWave2024!
   - Test PUT /playlists/{id}/name with valid name
   - Test empty name validation (should return 400 error)
   - Test very long name (over 100 chars, should return 400 error)

2. Test soft delete functionality:
   - DELETE /playlists/{id} should soft delete (set is_deleted=true)
   - Verify playlist no longer appears in GET /playlists
   - Verify active playlist cleared if it was the deleted one
   - Verify deleted playlist no longer appears in audience playlists

3. Test public/private toggle:
   - PUT /playlists/{id}/visibility with is_public=true/false
   - Verify active playlist cleared when made private
   - Verify audience playlists only show public ones

4. Test ownership and error handling:
   - Test accessing non-existent playlist (should return 404)
   - Verify all endpoints properly check ownership

5. Test optimistic UI support:
   - Verify all operations return proper success messages
   - Test error responses are user-friendly

Focus on verifying the rename, delete, and visibility toggle endpoints work correctly and return proper messages for the UI.
"""

import requests
import json
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://music-flow-update.preview.emergentagent.com/api"

# Pro account for playlist testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class ComprehensivePlaylistTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
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
                response = requests.get(url, headers=request_headers, params=data or params)
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

    def login_pro_account(self):
        """Login with Pro account"""
        try:
            login_data = {
                "email": PRO_MUSICIAN["email"],
                "password": PRO_MUSICIAN["password"]
            }
            
            response = self.make_request("POST", "/auth/login", login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "musician" in data:
                    self.auth_token = data["token"]
                    self.musician_id = data["musician"]["id"]
                    self.musician_slug = data["musician"]["slug"]
                    print(f"✅ Logged in as: {data['musician']['name']}")
                    return True
                else:
                    print(f"❌ Missing token or musician in response: {data}")
                    return False
            else:
                print(f"❌ Login failed: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Login exception: {str(e)}")
            return False

    def test_playlist_rename_with_validation(self):
        """Test playlist rename functionality with comprehensive validation"""
        try:
            print("🎵 TEST 1: Playlist Rename Functionality with Validation")
            print("=" * 80)
            
            # Step 1: Create test playlist
            print("📊 Step 1: Create test playlist for rename testing")
            
            songs_response = self.make_request("GET", "/songs")
            if songs_response.status_code != 200:
                self.log_result("Rename Test - Get Songs", False, f"Failed to get songs: {songs_response.status_code}")
                return
            
            songs = songs_response.json()
            if len(songs) < 2:
                self.log_result("Rename Test - Insufficient Songs", False, f"Need at least 2 songs, found {len(songs)}")
                return
            
            # Create playlist with 2 songs
            test_song_ids = [songs[0]["id"], songs[1]["id"]]
            playlist_data = {
                "name": "Original Rename Test Playlist",
                "song_ids": test_song_ids
            }
            
            create_response = self.make_request("POST", "/playlists", playlist_data)
            if create_response.status_code != 200:
                self.log_result("Rename Test - Create Playlist", False, f"Failed to create playlist: {create_response.status_code}")
                return
            
            created_playlist = create_response.json()
            playlist_id = created_playlist["id"]
            original_name = created_playlist["name"]
            
            print(f"   ✅ Created test playlist: {original_name} with ID: {playlist_id}")
            
            # Step 2: Test valid rename
            print("📊 Step 2: Test PUT /playlists/{id}/name with valid name")
            
            new_name = "Successfully Renamed Playlist"
            rename_data = {"name": new_name}
            
            rename_response = self.make_request("PUT", f"/playlists/{playlist_id}/name", rename_data)
            
            print(f"   📊 Rename response status: {rename_response.status_code}")
            print(f"   📊 Rename response: {rename_response.text}")
            
            if rename_response.status_code == 200:
                rename_result = rename_response.json()
                returned_name = rename_result.get("name")
                success_message = rename_result.get("message")
                updated_at = rename_result.get("updated_at")
                
                if returned_name == new_name:
                    print(f"   ✅ Playlist renamed successfully: '{returned_name}'")
                    valid_rename_success = True
                else:
                    print(f"   ❌ Wrong name returned. Expected: '{new_name}', Got: '{returned_name}'")
                    valid_rename_success = False
                
                if success_message:
                    print(f"   ✅ Success message provided: '{success_message}'")
                    message_provided = True
                else:
                    print(f"   ❌ No success message provided")
                    message_provided = False
                
                if updated_at:
                    print(f"   ✅ updated_at field provided: {updated_at}")
                    updated_at_provided = True
                else:
                    print(f"   ❌ No updated_at field provided")
                    updated_at_provided = False
                    
            else:
                print(f"   ❌ Valid rename failed: {rename_response.status_code}")
                valid_rename_success = False
                message_provided = False
                updated_at_provided = False
            
            # Step 3: Test empty name validation (should return 400 error)
            print("📊 Step 3: Test empty name validation (should return 400 error)")
            
            empty_name_data = {"name": ""}
            empty_response = self.make_request("PUT", f"/playlists/{playlist_id}/name", empty_name_data)
            
            print(f"   📊 Empty name response status: {empty_response.status_code}")
            print(f"   📊 Empty name response: {empty_response.text}")
            
            if empty_response.status_code == 400:
                print(f"   ✅ Empty name correctly rejected with 400 error")
                empty_validation = True
            else:
                print(f"   ❌ Empty name not properly rejected: {empty_response.status_code}")
                empty_validation = False
            
            # Step 4: Test very long name (over 100 chars, should return 400 error)
            print("📊 Step 4: Test very long name (over 100 chars, should return 400 error)")
            
            long_name = "A" * 101  # 101 characters
            long_name_data = {"name": long_name}
            long_response = self.make_request("PUT", f"/playlists/{playlist_id}/name", long_name_data)
            
            print(f"   📊 Long name response status: {long_response.status_code}")
            print(f"   📊 Long name response: {long_response.text}")
            
            if long_response.status_code == 400:
                print(f"   ✅ Long name correctly rejected with 400 error")
                long_validation = True
            else:
                print(f"   ❌ Long name not properly rejected: {long_response.status_code}")
                long_validation = False
            
            # Step 5: Test non-existent playlist (should return 404)
            print("📊 Step 5: Test accessing non-existent playlist (should return 404)")
            
            fake_id = "non-existent-playlist-id"
            fake_rename_data = {"name": "Should Not Work"}
            fake_response = self.make_request("PUT", f"/playlists/{fake_id}/name", fake_rename_data)
            
            print(f"   📊 Non-existent playlist response status: {fake_response.status_code}")
            
            if fake_response.status_code == 404:
                print(f"   ✅ Non-existent playlist correctly returns 404")
                not_found_handling = True
            else:
                print(f"   ❌ Non-existent playlist not handled properly: {fake_response.status_code}")
                not_found_handling = False
            
            # Step 6: Clean up test playlist
            print("📊 Step 6: Clean up test playlist")
            
            delete_response = self.make_request("DELETE", f"/playlists/{playlist_id}")
            if delete_response.status_code == 200:
                print(f"   ✅ Deleted test playlist")
            else:
                print(f"   ⚠️  Failed to delete test playlist: {delete_response.status_code}")
            
            # Final assessment
            all_tests_passed = (valid_rename_success and message_provided and updated_at_provided and 
                              empty_validation and long_validation and not_found_handling)
            
            if all_tests_passed:
                self.log_result("Playlist Rename with Validation", True, 
                              "All rename functionality tests passed with proper validation and error handling")
            else:
                issues = []
                if not valid_rename_success:
                    issues.append("valid rename failed")
                if not message_provided:
                    issues.append("no success message")
                if not updated_at_provided:
                    issues.append("no updated_at field")
                if not empty_validation:
                    issues.append("empty name validation failed")
                if not long_validation:
                    issues.append("long name validation failed")
                if not not_found_handling:
                    issues.append("404 handling failed")
                
                self.log_result("Playlist Rename with Validation", False, 
                              f"Issues found: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Playlist Rename with Validation", False, f"Exception: {str(e)}")

    def test_soft_delete_functionality(self):
        """Test soft delete functionality comprehensively"""
        try:
            print("🎵 TEST 2: Soft Delete Functionality")
            print("=" * 80)
            
            # Step 1: Create test playlist
            print("📊 Step 1: Create test playlist for soft delete testing")
            
            songs_response = self.make_request("GET", "/songs")
            if songs_response.status_code != 200:
                self.log_result("Soft Delete Test - Get Songs", False, f"Failed to get songs: {songs_response.status_code}")
                return
            
            songs = songs_response.json()
            if len(songs) < 2:
                self.log_result("Soft Delete Test - Insufficient Songs", False, f"Need at least 2 songs, found {len(songs)}")
                return
            
            # Create playlist with 2 songs
            test_song_ids = [songs[0]["id"], songs[1]["id"]]
            playlist_data = {
                "name": "Soft Delete Test Playlist",
                "song_ids": test_song_ids
            }
            
            create_response = self.make_request("POST", "/playlists", playlist_data)
            if create_response.status_code != 200:
                self.log_result("Soft Delete Test - Create Playlist", False, f"Failed to create playlist: {create_response.status_code}")
                return
            
            created_playlist = create_response.json()
            playlist_id = created_playlist["id"]
            playlist_name = created_playlist["name"]
            
            print(f"   ✅ Created test playlist: {playlist_name} with ID: {playlist_id}")
            
            # Step 2: Verify playlist appears in GET /playlists before deletion
            print("📊 Step 2: Verify playlist appears in GET /playlists before deletion")
            
            before_delete_response = self.make_request("GET", "/playlists")
            
            if before_delete_response.status_code == 200:
                before_playlists = before_delete_response.json()
                playlist_exists_before = any(p.get("id") == playlist_id for p in before_playlists)
                playlist_count_before = len(before_playlists)
                
                if playlist_exists_before:
                    print(f"   ✅ Playlist exists before deletion (total: {playlist_count_before})")
                    exists_before = True
                else:
                    print(f"   ❌ Playlist not found before deletion")
                    exists_before = False
            else:
                print(f"   ❌ Failed to get playlists before deletion: {before_delete_response.status_code}")
                exists_before = False
                playlist_count_before = 0
            
            # Step 3: Test DELETE /playlists/{id} should soft delete (set is_deleted=true)
            print("📊 Step 3: Test DELETE /playlists/{id} should soft delete")
            
            delete_response = self.make_request("DELETE", f"/playlists/{playlist_id}")
            
            print(f"   📊 Delete response status: {delete_response.status_code}")
            print(f"   📊 Delete response: {delete_response.text}")
            
            if delete_response.status_code == 200:
                delete_result = delete_response.json()
                success_message = delete_result.get("message")
                
                if success_message and playlist_name in success_message:
                    print(f"   ✅ Success message provided: '{success_message}'")
                    delete_message_provided = True
                else:
                    print(f"   ❌ No proper success message provided: '{success_message}'")
                    delete_message_provided = False
                
                delete_success = True
            else:
                print(f"   ❌ Delete failed: {delete_response.status_code}")
                delete_success = False
                delete_message_provided = False
            
            # Step 4: Verify playlist no longer appears in GET /playlists
            print("📊 Step 4: Verify playlist no longer appears in GET /playlists")
            
            after_delete_response = self.make_request("GET", "/playlists")
            
            if after_delete_response.status_code == 200:
                after_playlists = after_delete_response.json()
                playlist_exists_after = any(p.get("id") == playlist_id for p in after_playlists)
                playlist_count_after = len(after_playlists)
                
                if not playlist_exists_after:
                    print(f"   ✅ Playlist no longer appears in playlists list")
                    filtered_from_list = True
                else:
                    print(f"   ❌ Playlist still appears in playlists list")
                    filtered_from_list = False
                
                if playlist_count_after == playlist_count_before - 1:
                    print(f"   ✅ Playlist count decreased: {playlist_count_before} → {playlist_count_after}")
                    count_decreased = True
                else:
                    print(f"   ❌ Playlist count incorrect: {playlist_count_before} → {playlist_count_after}")
                    count_decreased = False
            else:
                print(f"   ❌ Failed to get playlists after deletion: {after_delete_response.status_code}")
                filtered_from_list = False
                count_decreased = False
            
            # Step 5: Verify deleted playlist no longer appears in audience playlists
            print("📊 Step 5: Verify deleted playlist no longer appears in audience playlists")
            
            # Clear auth token for public access
            original_token = self.auth_token
            self.auth_token = None
            
            audience_response = self.make_request("GET", f"/musicians/{self.musician_slug}/playlists")
            
            if audience_response.status_code == 200:
                audience_playlists = audience_response.json()
                playlist_in_audience = any(p.get("id") == playlist_id for p in audience_playlists)
                
                if not playlist_in_audience:
                    print(f"   ✅ Deleted playlist not in audience playlists")
                    filtered_from_audience = True
                else:
                    print(f"   ❌ Deleted playlist still appears in audience playlists")
                    filtered_from_audience = False
            else:
                print(f"   ❌ Failed to get audience playlists: {audience_response.status_code}")
                filtered_from_audience = False
            
            # Restore auth token
            self.auth_token = original_token
            
            # Step 6: Test deleting non-existent playlist (should return 404)
            print("📊 Step 6: Test deleting non-existent playlist (should return 404)")
            
            fake_id = "non-existent-playlist-id"
            fake_response = self.make_request("DELETE", f"/playlists/{fake_id}")
            
            print(f"   📊 Non-existent playlist delete status: {fake_response.status_code}")
            
            if fake_response.status_code == 404:
                print(f"   ✅ Non-existent playlist correctly returns 404")
                not_found_handling = True
            else:
                print(f"   ❌ Non-existent playlist not handled properly: {fake_response.status_code}")
                not_found_handling = False
            
            # Final assessment
            all_tests_passed = (exists_before and delete_success and delete_message_provided and 
                              filtered_from_list and count_decreased and filtered_from_audience and 
                              not_found_handling)
            
            if all_tests_passed:
                self.log_result("Soft Delete Functionality", True, 
                              "All soft delete functionality tests passed with proper filtering and error handling")
            else:
                issues = []
                if not exists_before:
                    issues.append("playlist not found before deletion")
                if not delete_success:
                    issues.append("delete operation failed")
                if not delete_message_provided:
                    issues.append("no success message")
                if not filtered_from_list:
                    issues.append("not filtered from playlists list")
                if not count_decreased:
                    issues.append("playlist count not decreased")
                if not filtered_from_audience:
                    issues.append("not filtered from audience playlists")
                if not not_found_handling:
                    issues.append("404 handling failed")
                
                self.log_result("Soft Delete Functionality", False, 
                              f"Issues found: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Soft Delete Functionality", False, f"Exception: {str(e)}")

    def test_public_private_toggle(self):
        """Test public/private toggle functionality"""
        try:
            print("🎵 TEST 3: Public/Private Toggle Functionality")
            print("=" * 80)
            
            # Step 1: Create test playlist (defaults to private)
            print("📊 Step 1: Create test playlist for visibility testing")
            
            songs_response = self.make_request("GET", "/songs")
            if songs_response.status_code != 200:
                self.log_result("Visibility Test - Get Songs", False, f"Failed to get songs: {songs_response.status_code}")
                return
            
            songs = songs_response.json()
            if len(songs) < 2:
                self.log_result("Visibility Test - Insufficient Songs", False, f"Need at least 2 songs, found {len(songs)}")
                return
            
            # Create playlist with 2 songs
            test_song_ids = [songs[0]["id"], songs[1]["id"]]
            playlist_data = {
                "name": "Visibility Toggle Test Playlist",
                "song_ids": test_song_ids
            }
            
            create_response = self.make_request("POST", "/playlists", playlist_data)
            if create_response.status_code != 200:
                self.log_result("Visibility Test - Create Playlist", False, f"Failed to create playlist: {create_response.status_code}")
                return
            
            created_playlist = create_response.json()
            playlist_id = created_playlist["id"]
            playlist_name = created_playlist["name"]
            
            print(f"   ✅ Created test playlist: {playlist_name} with ID: {playlist_id}")
            
            # Step 2: Test PUT /playlists/{id}/visibility with is_public=true
            print("📊 Step 2: Test PUT /playlists/{id}/visibility with is_public=true")
            
            public_data = {"is_public": True}
            public_response = self.make_request("PUT", f"/playlists/{playlist_id}/visibility", public_data)
            
            print(f"   📊 Make public response status: {public_response.status_code}")
            print(f"   📊 Make public response: {public_response.text}")
            
            if public_response.status_code == 200:
                public_result = public_response.json()
                is_public = public_result.get("is_public")
                success_message = public_result.get("message")
                updated_at = public_result.get("updated_at")
                
                if is_public is True:
                    print(f"   ✅ Playlist made public successfully")
                    make_public_success = True
                else:
                    print(f"   ❌ is_public not set correctly. Got: {is_public}")
                    make_public_success = False
                
                if success_message and "public" in success_message.lower():
                    print(f"   ✅ Success message provided: '{success_message}'")
                    public_message_provided = True
                else:
                    print(f"   ❌ No proper success message provided: '{success_message}'")
                    public_message_provided = False
                
                if updated_at:
                    print(f"   ✅ updated_at field provided: {updated_at}")
                    public_updated_at_provided = True
                else:
                    print(f"   ❌ No updated_at field provided")
                    public_updated_at_provided = False
                    
            else:
                print(f"   ❌ Make public failed: {public_response.status_code}")
                make_public_success = False
                public_message_provided = False
                public_updated_at_provided = False
            
            # Step 3: Verify audience playlists only show public ones
            print("📊 Step 3: Verify audience playlists only show public ones")
            
            # Clear auth token for public access
            original_token = self.auth_token
            self.auth_token = None
            
            audience_response = self.make_request("GET", f"/musicians/{self.musician_slug}/playlists")
            
            if audience_response.status_code == 200:
                audience_playlists = audience_response.json()
                playlist_found = any(p.get("id") == playlist_id for p in audience_playlists)
                
                if playlist_found:
                    print(f"   ✅ Public playlist appears in audience playlists")
                    appears_in_audience = True
                else:
                    print(f"   ❌ Public playlist not found in audience playlists")
                    appears_in_audience = False
            else:
                print(f"   ❌ Failed to get audience playlists: {audience_response.status_code}")
                appears_in_audience = False
            
            # Restore auth token
            self.auth_token = original_token
            
            # Step 4: Test PUT /playlists/{id}/visibility with is_public=false
            print("📊 Step 4: Test PUT /playlists/{id}/visibility with is_public=false")
            
            private_data = {"is_public": False}
            private_response = self.make_request("PUT", f"/playlists/{playlist_id}/visibility", private_data)
            
            print(f"   📊 Make private response status: {private_response.status_code}")
            print(f"   📊 Make private response: {private_response.text}")
            
            if private_response.status_code == 200:
                private_result = private_response.json()
                is_public = private_result.get("is_public")
                success_message = private_result.get("message")
                
                if is_public is False:
                    print(f"   ✅ Playlist made private successfully")
                    make_private_success = True
                else:
                    print(f"   ❌ is_public not set correctly. Got: {is_public}")
                    make_private_success = False
                
                if success_message and "private" in success_message.lower():
                    print(f"   ✅ Success message provided: '{success_message}'")
                    private_message_provided = True
                else:
                    print(f"   ❌ No proper success message provided: '{success_message}'")
                    private_message_provided = False
                    
            else:
                print(f"   ❌ Make private failed: {private_response.status_code}")
                make_private_success = False
                private_message_provided = False
            
            # Step 5: Verify private playlist doesn't appear in audience playlists
            print("📊 Step 5: Verify private playlist doesn't appear in audience playlists")
            
            # Clear auth token for public access
            self.auth_token = None
            
            audience_response2 = self.make_request("GET", f"/musicians/{self.musician_slug}/playlists")
            
            if audience_response2.status_code == 200:
                audience_playlists2 = audience_response2.json()
                playlist_found2 = any(p.get("id") == playlist_id for p in audience_playlists2)
                
                if not playlist_found2:
                    print(f"   ✅ Private playlist filtered out of audience playlists")
                    filtered_from_audience = True
                else:
                    print(f"   ❌ Private playlist still appears in audience playlists")
                    filtered_from_audience = False
            else:
                print(f"   ❌ Failed to get audience playlists: {audience_response2.status_code}")
                filtered_from_audience = False
            
            # Restore auth token
            self.auth_token = original_token
            
            # Step 6: Test invalid visibility data
            print("📊 Step 6: Test invalid visibility data")
            
            invalid_data = {"is_public": "not_a_boolean"}
            invalid_response = self.make_request("PUT", f"/playlists/{playlist_id}/visibility", invalid_data)
            
            print(f"   📊 Invalid data response status: {invalid_response.status_code}")
            
            if invalid_response.status_code == 400:
                print(f"   ✅ Invalid data correctly rejected with 400 error")
                invalid_validation = True
            else:
                print(f"   ❌ Invalid data not properly rejected: {invalid_response.status_code}")
                invalid_validation = False
            
            # Step 7: Test non-existent playlist (should return 404)
            print("📊 Step 7: Test visibility toggle on non-existent playlist (should return 404)")
            
            fake_id = "non-existent-playlist-id"
            fake_data = {"is_public": True}
            fake_response = self.make_request("PUT", f"/playlists/{fake_id}/visibility", fake_data)
            
            print(f"   📊 Non-existent playlist response status: {fake_response.status_code}")
            
            if fake_response.status_code == 404:
                print(f"   ✅ Non-existent playlist correctly returns 404")
                not_found_handling = True
            else:
                print(f"   ❌ Non-existent playlist not handled properly: {fake_response.status_code}")
                not_found_handling = False
            
            # Step 8: Clean up test playlist
            print("📊 Step 8: Clean up test playlist")
            
            delete_response = self.make_request("DELETE", f"/playlists/{playlist_id}")
            if delete_response.status_code == 200:
                print(f"   ✅ Deleted test playlist")
            else:
                print(f"   ⚠️  Failed to delete test playlist: {delete_response.status_code}")
            
            # Final assessment
            all_tests_passed = (make_public_success and public_message_provided and public_updated_at_provided and 
                              appears_in_audience and make_private_success and private_message_provided and 
                              filtered_from_audience and invalid_validation and not_found_handling)
            
            if all_tests_passed:
                self.log_result("Public/Private Toggle", True, 
                              "All visibility toggle functionality tests passed with proper validation and filtering")
            else:
                issues = []
                if not make_public_success:
                    issues.append("make public failed")
                if not public_message_provided:
                    issues.append("no public success message")
                if not public_updated_at_provided:
                    issues.append("no updated_at field")
                if not appears_in_audience:
                    issues.append("public playlist not in audience")
                if not make_private_success:
                    issues.append("make private failed")
                if not private_message_provided:
                    issues.append("no private success message")
                if not filtered_from_audience:
                    issues.append("private playlist still in audience")
                if not invalid_validation:
                    issues.append("invalid data validation failed")
                if not not_found_handling:
                    issues.append("404 handling failed")
                
                self.log_result("Public/Private Toggle", False, 
                              f"Issues found: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Public/Private Toggle", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all comprehensive playlist management tests"""
        print("🎵 COMPREHENSIVE PLAYLIST MANAGEMENT SYSTEM TESTING")
        print("=" * 80)
        print(f"Testing against: {self.base_url}")
        print(f"Test account: {PRO_MUSICIAN['email']}")
        print("=" * 80)
        
        # Login first
        if not self.login_pro_account():
            print("❌ Failed to login - cannot proceed with tests")
            return
        
        # Run all tests as specified in review request
        self.test_playlist_rename_with_validation()
        self.test_soft_delete_functionality()
        self.test_public_private_toggle()
        
        # Print summary
        print("\n" + "=" * 80)
        print("🎵 COMPREHENSIVE PLAYLIST MANAGEMENT TESTING SUMMARY")
        print("=" * 80)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Total: {self.results['passed'] + self.results['failed']}")
        
        if self.results['failed'] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed'])) * 100 if (self.results['passed'] + self.results['failed']) > 0 else 0
        print(f"\n📊 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("🎉 EXCELLENT: Comprehensive playlist management system is working very well!")
        elif success_rate >= 75:
            print("✅ GOOD: Playlist management system is mostly working with minor issues")
        elif success_rate >= 50:
            print("⚠️  NEEDS WORK: Playlist management system has significant issues")
        else:
            print("❌ CRITICAL: Playlist management system has major problems")

if __name__ == "__main__":
    tester = ComprehensivePlaylistTester()
    tester.run_all_tests()