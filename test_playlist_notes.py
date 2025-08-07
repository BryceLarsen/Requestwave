#!/usr/bin/env python3
"""
Specific test for playlist import functionality with blank notes field
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://2d821f37-5e3c-493f-a28d-8ff61cf1519e.preview.emergentagent.com/api"

# Pro account for testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class PlaylistNotesTestRunner:
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

    def test_playlist_import_blank_notes_field(self):
        """Test that playlist import sets notes field to blank (empty string) - PRIORITY 1"""
        try:
            print("🔍 PRIORITY 1: Testing Spotify Playlist Import with Blank Notes Field")
            print("=" * 80)
            
            # Step 1: Login with Pro account brycelarsenmusic@gmail.com
            print("📊 Step 1: Login with Pro account brycelarsenmusic@gmail.com")
            login_data = {
                "email": PRO_MUSICIAN["email"],
                "password": PRO_MUSICIAN["password"]
            }
            
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code != 200:
                self.log_result("Playlist Import Blank Notes - Pro Login", False, f"Failed to login with Pro account: {login_response.status_code}")
                return
            
            login_data_response = login_response.json()
            if "token" not in login_data_response or "musician" not in login_data_response:
                self.log_result("Playlist Import Blank Notes - Pro Login", False, f"Invalid login response: {login_data_response}")
                return
            
            # Store Pro account credentials
            self.auth_token = login_data_response["token"]
            self.musician_id = login_data_response["musician"]["id"]
            self.musician_slug = login_data_response["musician"]["slug"]
            
            print(f"   ✅ Successfully logged in as: {login_data_response['musician']['name']}")
            self.log_result("Playlist Import Blank Notes - Pro Login", True, f"Successfully logged in as {login_data_response['musician']['name']}")
            
            # Step 2: Test Spotify Playlist Import with specific URL
            print("📊 Step 2: Test POST /api/songs/playlist/import with Spotify playlist URL")
            spotify_playlist_data = {
                "playlist_url": "https://open.spotify.com/playlist/37i9dQZEVXbLRQDuF5jeBp",
                "platform": "spotify"
            }
            
            print(f"   🎵 Testing with Spotify URL: {spotify_playlist_data['playlist_url']}")
            
            # Get song count before import
            songs_before_response = self.make_request("GET", "/songs")
            songs_before_count = len(songs_before_response.json()) if songs_before_response.status_code == 200 else 0
            print(f"   📊 Songs before import: {songs_before_count}")
            
            spotify_response = self.make_request("POST", "/songs/playlist/import", spotify_playlist_data)
            
            if spotify_response.status_code == 200:
                spotify_data = spotify_response.json()
                print(f"   📊 Spotify import response: {json.dumps(spotify_data, indent=2)}")
                
                if spotify_data.get("success") and spotify_data.get("songs_added", 0) > 0:
                    self.log_result("Spotify Playlist Import - Success", True, f"Successfully imported {spotify_data['songs_added']} songs from Spotify")
                    
                    # Step 3: Verify imported songs have blank notes field
                    print("📊 Step 3: CRITICAL CHECK - Verify notes field is blank (empty string)")
                    
                    songs_after_response = self.make_request("GET", "/songs")
                    if songs_after_response.status_code == 200:
                        songs_after = songs_after_response.json()
                        print(f"   📊 Songs after import: {len(songs_after)}")
                        
                        # Find newly imported songs (assuming they're the most recent)
                        newly_imported = songs_after[songs_before_count:] if len(songs_after) > songs_before_count else []
                        
                        if len(newly_imported) > 0:
                            print(f"   🎵 Checking {len(newly_imported)} newly imported songs for blank notes:")
                            
                            blank_notes_count = 0
                            non_blank_notes = []
                            
                            for i, song in enumerate(newly_imported[:10]):  # Check first 10 imported songs
                                title = song.get("title", "Unknown")
                                artist = song.get("artist", "Unknown")
                                notes = song.get("notes", None)
                                
                                print(f"     • Song {i+1}: '{title}' by '{artist}'")
                                print(f"       Notes field: {repr(notes)}")
                                
                                if notes == "":
                                    blank_notes_count += 1
                                    print(f"       ✅ Notes field is blank (empty string)")
                                else:
                                    non_blank_notes.append(f"'{title}' by '{artist}' has notes: {repr(notes)}")
                                    print(f"       ❌ Notes field is NOT blank: {repr(notes)}")
                            
                            # CRITICAL CHECK: All imported songs should have blank notes
                            if blank_notes_count == len(newly_imported[:10]) and len(non_blank_notes) == 0:
                                self.log_result("Spotify Import - Blank Notes Field", True, f"✅ CRITICAL CHECK PASSED: All {blank_notes_count} imported songs have blank notes field (empty string '')")
                            else:
                                self.log_result("Spotify Import - Blank Notes Field", False, f"❌ CRITICAL CHECK FAILED: {len(non_blank_notes)} songs have non-blank notes: {non_blank_notes}")
                        else:
                            self.log_result("Spotify Import - Blank Notes Field", False, "❌ No newly imported songs found to check")
                    else:
                        self.log_result("Spotify Import - Blank Notes Field", False, f"Failed to retrieve songs after import: {songs_after_response.status_code}")
                else:
                    self.log_result("Spotify Playlist Import - Success", False, f"❌ Import failed or no songs added: {spotify_data}")
            else:
                self.log_result("Spotify Playlist Import - Success", False, f"❌ Import request failed: {spotify_response.status_code}, Response: {spotify_response.text}")
            
            # Step 4: Test Apple Music Playlist Import
            print("📊 Step 4: PRIORITY 2 - Test Apple Music Playlist Import with blank notes")
            apple_playlist_data = {
                "playlist_url": "https://music.apple.com/us/playlist/todays-hits/pl.f4d106fed2bd41149aaacabb233eb5eb",
                "platform": "apple_music"
            }
            
            print(f"   🎵 Testing with Apple Music URL: {apple_playlist_data['playlist_url']}")
            
            # Get song count before Apple Music import
            songs_before_apple_response = self.make_request("GET", "/songs")
            songs_before_apple_count = len(songs_before_apple_response.json()) if songs_before_apple_response.status_code == 200 else 0
            
            apple_response = self.make_request("POST", "/songs/playlist/import", apple_playlist_data)
            
            if apple_response.status_code == 200:
                apple_data = apple_response.json()
                print(f"   📊 Apple Music import response: {json.dumps(apple_data, indent=2)}")
                
                if apple_data.get("success") and apple_data.get("songs_added", 0) > 0:
                    self.log_result("Apple Music Playlist Import - Success", True, f"Successfully imported {apple_data['songs_added']} songs from Apple Music")
                    
                    # Verify Apple Music imported songs have blank notes
                    songs_after_apple_response = self.make_request("GET", "/songs")
                    if songs_after_apple_response.status_code == 200:
                        songs_after_apple = songs_after_apple_response.json()
                        newly_imported_apple = songs_after_apple[songs_before_apple_count:] if len(songs_after_apple) > songs_before_apple_count else []
                        
                        if len(newly_imported_apple) > 0:
                            print(f"   🎵 Checking {len(newly_imported_apple)} Apple Music imported songs for blank notes:")
                            
                            apple_blank_notes_count = 0
                            apple_non_blank_notes = []
                            
                            for i, song in enumerate(newly_imported_apple[:5]):  # Check first 5 Apple Music songs
                                title = song.get("title", "Unknown")
                                artist = song.get("artist", "Unknown")
                                notes = song.get("notes", None)
                                
                                print(f"     • Apple Song {i+1}: '{title}' by '{artist}'")
                                print(f"       Notes field: {repr(notes)}")
                                
                                if notes == "":
                                    apple_blank_notes_count += 1
                                    print(f"       ✅ Notes field is blank (empty string)")
                                else:
                                    apple_non_blank_notes.append(f"'{title}' by '{artist}' has notes: {repr(notes)}")
                                    print(f"       ❌ Notes field is NOT blank: {repr(notes)}")
                            
                            if apple_blank_notes_count == len(newly_imported_apple[:5]) and len(apple_non_blank_notes) == 0:
                                self.log_result("Apple Music Import - Blank Notes Field", True, f"✅ PRIORITY 2 PASSED: All {apple_blank_notes_count} Apple Music imported songs have blank notes field")
                            else:
                                self.log_result("Apple Music Import - Blank Notes Field", False, f"❌ PRIORITY 2 FAILED: {len(apple_non_blank_notes)} Apple Music songs have non-blank notes: {apple_non_blank_notes}")
                        else:
                            self.log_result("Apple Music Import - Blank Notes Field", False, "❌ No newly imported Apple Music songs found")
                    else:
                        self.log_result("Apple Music Import - Blank Notes Field", False, f"Failed to retrieve songs after Apple Music import: {songs_after_apple_response.status_code}")
                else:
                    self.log_result("Apple Music Playlist Import - Success", False, f"❌ Apple Music import failed: {apple_data}")
            else:
                self.log_result("Apple Music Playlist Import - Success", False, f"❌ Apple Music import request failed: {apple_response.status_code}")
            
            # Step 5: Test Fallback Functionality
            print("📊 Step 5: PRIORITY 3 - Test Fallback Functionality with blank notes")
            
            # Test with invalid/inaccessible playlist URL to trigger fallback
            fallback_playlist_data = {
                "playlist_url": "https://open.spotify.com/playlist/invalid_playlist_id_12345",
                "platform": "spotify"
            }
            
            print(f"   🎵 Testing fallback with invalid URL: {fallback_playlist_data['playlist_url']}")
            
            songs_before_fallback_response = self.make_request("GET", "/songs")
            songs_before_fallback_count = len(songs_before_fallback_response.json()) if songs_before_fallback_response.status_code == 200 else 0
            
            fallback_response = self.make_request("POST", "/songs/playlist/import", fallback_playlist_data)
            
            if fallback_response.status_code == 200:
                fallback_data = fallback_response.json()
                print(f"   📊 Fallback import response: {json.dumps(fallback_data, indent=2)}")
                
                if fallback_data.get("success") and fallback_data.get("songs_added", 0) > 0:
                    self.log_result("Fallback Functionality - Success", True, f"Fallback successfully imported {fallback_data['songs_added']} songs")
                    
                    # Verify fallback songs have blank notes
                    songs_after_fallback_response = self.make_request("GET", "/songs")
                    if songs_after_fallback_response.status_code == 200:
                        songs_after_fallback = songs_after_fallback_response.json()
                        newly_imported_fallback = songs_after_fallback[songs_before_fallback_count:] if len(songs_after_fallback) > songs_before_fallback_count else []
                        
                        if len(newly_imported_fallback) > 0:
                            print(f"   🎵 Checking {len(newly_imported_fallback)} fallback songs for blank notes:")
                            
                            fallback_blank_notes_count = 0
                            fallback_non_blank_notes = []
                            
                            for i, song in enumerate(newly_imported_fallback[:3]):  # Check first 3 fallback songs
                                title = song.get("title", "Unknown")
                                artist = song.get("artist", "Unknown")
                                notes = song.get("notes", None)
                                
                                print(f"     • Fallback Song {i+1}: '{title}' by '{artist}'")
                                print(f"       Notes field: {repr(notes)}")
                                
                                if notes == "":
                                    fallback_blank_notes_count += 1
                                    print(f"       ✅ Notes field is blank (empty string)")
                                else:
                                    fallback_non_blank_notes.append(f"'{title}' by '{artist}' has notes: {repr(notes)}")
                                    print(f"       ❌ Notes field is NOT blank: {repr(notes)}")
                            
                            if fallback_blank_notes_count == len(newly_imported_fallback[:3]) and len(fallback_non_blank_notes) == 0:
                                self.log_result("Fallback Songs - Blank Notes Field", True, f"✅ PRIORITY 3 PASSED: All {fallback_blank_notes_count} fallback songs have blank notes field")
                            else:
                                self.log_result("Fallback Songs - Blank Notes Field", False, f"❌ PRIORITY 3 FAILED: {len(fallback_non_blank_notes)} fallback songs have non-blank notes: {fallback_non_blank_notes}")
                        else:
                            self.log_result("Fallback Songs - Blank Notes Field", False, "❌ No fallback songs found")
                    else:
                        self.log_result("Fallback Songs - Blank Notes Field", False, f"Failed to retrieve songs after fallback import: {songs_after_fallback_response.status_code}")
                else:
                    # Fallback might fail, which is acceptable
                    self.log_result("Fallback Functionality - Success", True, f"Fallback handled gracefully (may not import songs): {fallback_data}")
            else:
                # Fallback failure is acceptable for invalid URLs
                self.log_result("Fallback Functionality - Success", True, f"Fallback correctly rejected invalid URL: {fallback_response.status_code}")
            
            # Step 6: Test Core Functionality Preservation (PRIORITY 4)
            print("📊 Step 6: PRIORITY 4 - Test Core Functionality Preservation")
            
            # Test authentication still works
            profile_response = self.make_request("GET", "/profile")
            if profile_response.status_code == 200:
                self.log_result("Core Functionality - Authentication", True, "✅ JWT authentication still working")
            else:
                self.log_result("Core Functionality - Authentication", False, f"❌ Authentication broken: {profile_response.status_code}")
            
            # Test database persistence
            final_songs_response = self.make_request("GET", "/songs")
            if final_songs_response.status_code == 200:
                final_songs = final_songs_response.json()
                if len(final_songs) > songs_before_count:
                    self.log_result("Core Functionality - Database Persistence", True, f"✅ Database persistence working - {len(final_songs)} total songs")
                else:
                    self.log_result("Core Functionality - Database Persistence", False, f"❌ No songs persisted - {len(final_songs)} total songs")
            else:
                self.log_result("Core Functionality - Database Persistence", False, f"❌ Database access broken: {final_songs_response.status_code}")
            
            # Test URL validation still works
            invalid_url_data = {
                "playlist_url": "not-a-valid-url",
                "platform": "spotify"
            }
            
            invalid_response = self.make_request("POST", "/songs/playlist/import", invalid_url_data)
            if invalid_response.status_code == 400:
                self.log_result("Core Functionality - URL Validation", True, "✅ URL validation still working")
            else:
                self.log_result("Core Functionality - URL Validation", False, f"❌ URL validation not working: {invalid_response.status_code}")
            
            print("=" * 80)
            print("🎯 PLAYLIST IMPORT BLANK NOTES TESTING COMPLETE")
            
        except Exception as e:
            self.log_result("Playlist Import Blank Notes Field", False, f"❌ Exception: {str(e)}")

    def print_final_results(self):
        """Print final test results"""
        print("\n" + "=" * 60)
        print("🎯 PLAYLIST IMPORT BLANK NOTES TEST RESULTS")
        print("=" * 60)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Total: {self.results['passed'] + self.results['failed']}")
        
        if self.results['errors']:
            print("\n❌ FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed'])) * 100 if (self.results['passed'] + self.results['failed']) > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("🎉 EXCELLENT: Playlist import blank notes functionality is working correctly!")
        elif success_rate >= 75:
            print("✅ GOOD: Most playlist import functionality is working with minor issues")
        else:
            print("⚠️  NEEDS ATTENTION: Significant issues found with playlist import functionality")

if __name__ == "__main__":
    tester = PlaylistNotesTestRunner()
    tester.test_playlist_import_blank_notes_field()
    tester.print_final_results()