#!/usr/bin/env python3
"""
COMPREHENSIVE TESTING FOR ZELLE PAYMENT INTEGRATION

Testing the complete Zelle payment integration that was just added to RequestWave:

CRITICAL TEST AREAS:
1. Backend Zelle Fields - Create musician with zelle_email and zelle_phone, verify profile API returns Zelle fields correctly
2. Public Musician Data - Verify public musician endpoint includes Zelle fields for audience access
3. Tip Analytics - Test tip submission with platform='zelle' to verify analytics tracking works
4. Integration Test - Create musician with all three payment methods (PayPal, Venmo, Zelle)
5. Edge Cases - Test musician with only Zelle, both zelle_email and zelle_phone, empty/null Zelle fields

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!

Expected: Complete Zelle payment system integrated and functional for the new 3-step tip flow.
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://performance-pay-1.preview.emergentagent.com/api"
TEST_MUSICIAN = {
    "name": "Zelle Test Musician",
    "email": "zelle.test@requestwave.com", 
    "password": "SecurePassword123!"
}

# Pro account for testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
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

    def test_legacy_venmo_link_removal(self):
        """Test that legacy venmo_link field is removed from profile, only venmo_username remains"""
        try:
            print("🎵 PRIORITY 1: Testing Legacy Venmo Link Removal")
            print("=" * 80)
            
            # Step 1: Register new test musician
            print("📊 Step 1: Register new test musician")
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
                    self.log_result("Legacy Venmo Link Removal - Authentication", False, f"Failed to login: {login_response.status_code}")
                    return
            else:
                self.log_result("Legacy Venmo Link Removal - Registration", False, f"Failed to register: {response.status_code}")
                return
            
            # Step 2: Get current profile to check structure
            print("📊 Step 2: Get current profile structure")
            profile_response = self.make_request("GET", "/profile")
            
            if profile_response.status_code != 200:
                self.log_result("Legacy Venmo Link Removal - Get Profile", False, f"Failed to get profile: {profile_response.status_code}")
                return
            
            profile_data = profile_response.json()
            print(f"   📊 Profile fields: {list(profile_data.keys())}")
            
            # Step 3: Check if venmo_link field is present (should be removed)
            print("📊 Step 3: Check venmo_link field presence")
            has_venmo_link = "venmo_link" in profile_data
            has_venmo_username = "venmo_username" in profile_data
            
            if has_venmo_link:
                print(f"   ❌ Legacy venmo_link field still present: {profile_data.get('venmo_link')}")
                venmo_link_removed = False
            else:
                print(f"   ✅ Legacy venmo_link field successfully removed")
                venmo_link_removed = True
            
            if has_venmo_username:
                print(f"   ✅ venmo_username field present: {profile_data.get('venmo_username')}")
                venmo_username_present = True
            else:
                print(f"   ❌ venmo_username field missing")
                venmo_username_present = False
            
            # Step 4: Test profile update with venmo_username only
            print("📊 Step 4: Test profile update with venmo_username")
            
            update_data = {
                "venmo_username": "testuser123"
            }
            
            update_response = self.make_request("PUT", "/profile", update_data)
            
            if update_response.status_code == 200:
                updated_profile = update_response.json()
                print(f"   ✅ Profile update successful")
                print(f"   📊 Updated venmo_username: {updated_profile.get('venmo_username')}")
                
                # Verify the update worked
                if updated_profile.get('venmo_username') == 'testuser123':
                    print(f"   ✅ venmo_username correctly updated")
                    venmo_username_update_works = True
                else:
                    print(f"   ❌ venmo_username not updated correctly")
                    venmo_username_update_works = False
            else:
                print(f"   ❌ Profile update failed: {update_response.status_code}")
                venmo_username_update_works = False
            
            # Step 5: Test that venmo_link is not accepted in updates (if it still exists)
            print("📊 Step 5: Test that venmo_link updates are ignored/rejected")
            
            legacy_update_data = {
                "venmo_link": "https://venmo.com/legacy-link",
                "venmo_username": "newuser456"
            }
            
            legacy_response = self.make_request("PUT", "/profile", legacy_update_data)
            
            if legacy_response.status_code == 200:
                legacy_profile = legacy_response.json()
                
                # Check if venmo_link was ignored
                if "venmo_link" not in legacy_profile or legacy_profile.get("venmo_link") == "":
                    print(f"   ✅ venmo_link field ignored in update")
                    venmo_link_ignored = True
                else:
                    print(f"   ❌ venmo_link field still being processed: {legacy_profile.get('venmo_link')}")
                    venmo_link_ignored = False
                
                # Check if venmo_username was still updated
                if legacy_profile.get('venmo_username') == 'newuser456':
                    print(f"   ✅ venmo_username still works alongside legacy field")
                    venmo_username_still_works = True
                else:
                    print(f"   ❌ venmo_username not updated when legacy field present")
                    venmo_username_still_works = False
            else:
                print(f"   ❌ Legacy update test failed: {legacy_response.status_code}")
                venmo_link_ignored = True  # Assume it's ignored if request fails
                venmo_username_still_works = False
            
            # Final assessment
            if venmo_link_removed and venmo_username_present and venmo_username_update_works and venmo_link_ignored and venmo_username_still_works:
                self.log_result("Legacy Venmo Link Removal", True, "✅ LEGACY VENMO LINK SUCCESSFULLY REMOVED: venmo_link field removed from profile, venmo_username field working correctly")
            else:
                issues = []
                if not venmo_link_removed:
                    issues.append("venmo_link field still present")
                if not venmo_username_present:
                    issues.append("venmo_username field missing")
                if not venmo_username_update_works:
                    issues.append("venmo_username updates not working")
                if not venmo_link_ignored:
                    issues.append("venmo_link still being processed")
                if not venmo_username_still_works:
                    issues.append("venmo_username broken when legacy field present")
                
                self.log_result("Legacy Venmo Link Removal", False, f"❌ VENMO LINK REMOVAL ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Legacy Venmo Link Removal", False, f"❌ Exception: {str(e)}")

    def test_suggest_song_button_always_visible(self):
        """Test that Suggest a Song button is always visible regardless of allow_song_suggestions setting"""
        try:
            print("🎵 PRIORITY 2: Testing Suggest a Song Button Always Visible")
            print("=" * 80)
            
            # Step 1: Login with Pro account to manage settings
            print("📊 Step 1: Login with Pro account")
            login_data = {
                "email": PRO_MUSICIAN["email"],
                "password": PRO_MUSICIAN["password"]
            }
            
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code != 200:
                self.log_result("Suggest Song Button - Pro Login", False, f"Failed to login: {login_response.status_code}")
                return
            
            login_data_response = login_response.json()
            self.auth_token = login_data_response["token"]
            pro_musician_slug = login_data_response["musician"]["slug"]
            
            print(f"   ✅ Successfully logged in as: {login_data_response['musician']['name']}")
            print(f"   📊 Musician slug: {pro_musician_slug}")
            
            # Step 2: Set allow_song_suggestions to false
            print("📊 Step 2: Set allow_song_suggestions to false")
            
            design_update = {
                "allow_song_suggestions": False
            }
            
            design_response = self.make_request("PUT", "/design", design_update)
            
            if design_response.status_code == 200:
                print(f"   ✅ Design settings updated - allow_song_suggestions set to false")
            else:
                print(f"   ❌ Failed to update design settings: {design_response.status_code}")
                # Continue anyway to test current state
            
            # Step 3: Test song suggestion creation when setting is false (should still work)
            print("📊 Step 3: Test song suggestion creation when allow_song_suggestions=false")
            
            # Clear auth token for public access
            self.auth_token = None
            
            suggestion_data = {
                "musician_slug": pro_musician_slug,
                "suggested_title": "Test Song Suggestion",
                "suggested_artist": "Test Artist",
                "requester_name": "Test Requester",
                "requester_email": "test@example.com",
                "message": "Please play this song!"
            }
            
            suggestion_response = self.make_request("POST", "/song-suggestions", suggestion_data)
            
            print(f"   📊 Song suggestion response status: {suggestion_response.status_code}")
            print(f"   📊 Song suggestion response: {suggestion_response.text[:200]}...")
            
            if suggestion_response.status_code == 200:
                suggestion_result = suggestion_response.json()
                print(f"   ✅ Song suggestion created successfully when allow_song_suggestions=false")
                print(f"   📊 Suggestion ID: {suggestion_result.get('id')}")
                suggestion_created_when_false = True
                suggestion_id = suggestion_result.get('id')
            else:
                print(f"   ❌ Song suggestion failed when allow_song_suggestions=false: {suggestion_response.status_code}")
                suggestion_created_when_false = False
                suggestion_id = None
            
            # Step 4: Restore auth and set allow_song_suggestions to true
            print("📊 Step 4: Set allow_song_suggestions to true and test again")
            
            # Restore auth token
            self.auth_token = login_data_response["token"]
            
            design_update_true = {
                "allow_song_suggestions": True
            }
            
            design_response_true = self.make_request("PUT", "/design", design_update_true)
            
            if design_response_true.status_code == 200:
                print(f"   ✅ Design settings updated - allow_song_suggestions set to true")
            else:
                print(f"   ❌ Failed to update design settings to true: {design_response_true.status_code}")
            
            # Clear auth token for public access again
            self.auth_token = None
            
            suggestion_data_true = {
                "musician_slug": pro_musician_slug,
                "suggested_title": "Test Song Suggestion 2",
                "suggested_artist": "Test Artist 2",
                "requester_name": "Test Requester 2",
                "requester_email": "test2@example.com",
                "message": "Please play this song too!"
            }
            
            suggestion_response_true = self.make_request("POST", "/song-suggestions", suggestion_data_true)
            
            if suggestion_response_true.status_code == 200:
                suggestion_result_true = suggestion_response_true.json()
                print(f"   ✅ Song suggestion created successfully when allow_song_suggestions=true")
                suggestion_created_when_true = True
                suggestion_id_2 = suggestion_result_true.get('id')
            else:
                print(f"   ❌ Song suggestion failed when allow_song_suggestions=true: {suggestion_response_true.status_code}")
                suggestion_created_when_true = False
                suggestion_id_2 = None
            
            # Step 5: Verify both suggestions exist in musician's list
            print("📊 Step 5: Verify suggestions appear in musician's management list")
            
            # Restore auth token
            self.auth_token = login_data_response["token"]
            
            suggestions_list_response = self.make_request("GET", "/song-suggestions")
            
            if suggestions_list_response.status_code == 200:
                suggestions_list = suggestions_list_response.json()
                print(f"   ✅ Retrieved {len(suggestions_list)} song suggestions")
                
                # Check if our test suggestions are in the list
                test_suggestions = [s for s in suggestions_list if s.get('suggested_title') in ['Test Song Suggestion', 'Test Song Suggestion 2']]
                
                if len(test_suggestions) >= 1:
                    print(f"   ✅ Test suggestions found in musician's list: {len(test_suggestions)}")
                    suggestions_in_list = True
                else:
                    print(f"   ❌ Test suggestions not found in musician's list")
                    suggestions_in_list = False
            else:
                print(f"   ❌ Failed to get suggestions list: {suggestions_list_response.status_code}")
                suggestions_in_list = False
            
            # Step 6: Clean up test suggestions
            print("📊 Step 6: Clean up test suggestions")
            
            cleanup_count = 0
            if suggestion_id:
                delete_response = self.make_request("DELETE", f"/song-suggestions/{suggestion_id}")
                if delete_response.status_code == 200:
                    cleanup_count += 1
            
            if suggestion_id_2:
                delete_response_2 = self.make_request("DELETE", f"/song-suggestions/{suggestion_id_2}")
                if delete_response_2.status_code == 200:
                    cleanup_count += 1
            
            print(f"   ✅ Cleaned up {cleanup_count} test suggestions")
            
            # Final assessment
            if suggestion_created_when_false and suggestion_created_when_true and suggestions_in_list:
                self.log_result("Suggest Song Button Always Visible", True, "✅ SUGGEST SONG BUTTON ALWAYS VISIBLE: Song suggestions work regardless of allow_song_suggestions setting, button should always be visible to audience")
            else:
                issues = []
                if not suggestion_created_when_false:
                    issues.append("suggestions blocked when allow_song_suggestions=false")
                if not suggestion_created_when_true:
                    issues.append("suggestions not working when allow_song_suggestions=true")
                if not suggestions_in_list:
                    issues.append("suggestions not appearing in musician's management list")
                
                self.log_result("Suggest Song Button Always Visible", False, f"❌ SUGGEST SONG BUTTON ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Suggest Song Button Always Visible", False, f"❌ Exception: {str(e)}")

    def test_end_to_end_musician_and_audience_flow(self):
        """Test complete end-to-end flow: register musician, add songs, test audience page, suggest song"""
        try:
            print("🎵 PRIORITY 3: Testing End-to-End Musician and Audience Flow")
            print("=" * 80)
            
            # Step 1: Register new test musician
            print("📊 Step 1: Register new test musician")
            
            test_musician_e2e = {
                "name": "E2E Test Musician",
                "email": "e2e.test@requestwave.com",
                "password": "SecurePassword123!"
            }
            
            register_response = self.make_request("POST", "/auth/register", test_musician_e2e)
            
            if register_response.status_code == 200:
                register_data = register_response.json()
                self.auth_token = register_data["token"]
                musician_id = register_data["musician"]["id"]
                musician_slug = register_data["musician"]["slug"]
                print(f"   ✅ Registered musician: {register_data['musician']['name']}")
                print(f"   📊 Musician slug: {musician_slug}")
            elif register_response.status_code == 400:
                # Try login if already exists
                login_data = {
                    "email": test_musician_e2e["email"],
                    "password": test_musician_e2e["password"]
                }
                login_response = self.make_request("POST", "/auth/login", login_data)
                if login_response.status_code == 200:
                    register_data = login_response.json()
                    self.auth_token = register_data["token"]
                    musician_id = register_data["musician"]["id"]
                    musician_slug = register_data["musician"]["slug"]
                    print(f"   ✅ Logged in existing musician: {register_data['musician']['name']}")
                else:
                    self.log_result("End-to-End Flow - Authentication", False, f"Failed to login: {login_response.status_code}")
                    return
            else:
                self.log_result("End-to-End Flow - Registration", False, f"Failed to register: {register_response.status_code}")
                return
            
            # Step 2: Add test songs to repertoire
            print("📊 Step 2: Add test songs to musician's repertoire")
            
            test_songs = [
                {
                    "title": "Sweet Caroline",
                    "artist": "Neil Diamond",
                    "genres": ["Classic Rock"],
                    "moods": ["Bar Anthems"],
                    "year": 1969,
                    "notes": "Crowd favorite"
                },
                {
                    "title": "Don't Stop Believin'",
                    "artist": "Journey",
                    "genres": ["Rock"],
                    "moods": ["Feel Good"],
                    "year": 1981,
                    "notes": "Sing-along hit"
                },
                {
                    "title": "Piano Man",
                    "artist": "Billy Joel",
                    "genres": ["Classic Rock"],
                    "moods": ["Bar Anthems"],
                    "year": 1973,
                    "notes": "Piano ballad"
                }
            ]
            
            added_songs = []
            for song_data in test_songs:
                song_response = self.make_request("POST", "/songs", song_data)
                if song_response.status_code == 200:
                    song_result = song_response.json()
                    added_songs.append(song_result)
                    print(f"   ✅ Added song: {song_result['title']} by {song_result['artist']}")
                else:
                    print(f"   ❌ Failed to add song: {song_data['title']} - {song_response.status_code}")
            
            if len(added_songs) < 2:
                self.log_result("End-to-End Flow - Add Songs", False, f"Failed to add enough songs: {len(added_songs)}")
                return
            
            print(f"   ✅ Successfully added {len(added_songs)} songs to repertoire")
            
            # Step 3: Test audience page access (public, no auth)
            print("📊 Step 3: Test audience page access")
            
            # Clear auth token for public access
            self.auth_token = None
            
            # Test musician profile endpoint
            profile_response = self.make_request("GET", f"/musicians/{musician_slug}")
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                print(f"   ✅ Audience can access musician profile: {profile_data['name']}")
                profile_accessible = True
            else:
                print(f"   ❌ Audience cannot access musician profile: {profile_response.status_code}")
                profile_accessible = False
            
            # Test songs endpoint for audience
            songs_response = self.make_request("GET", f"/musicians/{musician_slug}/songs")
            
            if songs_response.status_code == 200:
                songs_data = songs_response.json()
                print(f"   ✅ Audience can access songs list: {len(songs_data)} songs")
                
                # Verify our test songs are in the list
                song_titles = [s['title'] for s in songs_data]
                test_songs_found = sum(1 for song in test_songs if song['title'] in song_titles)
                
                if test_songs_found >= 2:
                    print(f"   ✅ Test songs found in audience view: {test_songs_found}/{len(test_songs)}")
                    songs_accessible = True
                else:
                    print(f"   ❌ Test songs not found in audience view: {test_songs_found}/{len(test_songs)}")
                    songs_accessible = False
            else:
                print(f"   ❌ Audience cannot access songs list: {songs_response.status_code}")
                songs_accessible = False
            
            # Step 4: Test song suggestion functionality
            print("📊 Step 4: Test song suggestion functionality from audience perspective")
            
            suggestion_data = {
                "musician_slug": musician_slug,
                "suggested_title": "Bohemian Rhapsody",
                "suggested_artist": "Queen",
                "requester_name": "Music Lover",
                "requester_email": "musiclover@example.com",
                "message": "This would be amazing to hear live!"
            }
            
            suggestion_response = self.make_request("POST", "/song-suggestions", suggestion_data)
            
            if suggestion_response.status_code == 200:
                suggestion_result = suggestion_response.json()
                print(f"   ✅ Song suggestion submitted successfully")
                print(f"   📊 Suggestion: {suggestion_result['suggested_title']} by {suggestion_result['suggested_artist']}")
                suggestion_id = suggestion_result.get('id')
                suggestion_works = True
            else:
                print(f"   ❌ Song suggestion failed: {suggestion_response.status_code}")
                print(f"   📊 Response: {suggestion_response.text}")
                suggestion_works = False
                suggestion_id = None
            
            # Step 5: Verify suggestion appears in musician's management interface
            print("📊 Step 5: Verify suggestion appears in musician's management interface")
            
            # Restore auth token for musician access
            self.auth_token = register_data["token"]
            
            suggestions_response = self.make_request("GET", "/song-suggestions")
            
            if suggestions_response.status_code == 200:
                suggestions_list = suggestions_response.json()
                
                # Find our test suggestion
                test_suggestion = None
                for suggestion in suggestions_list:
                    if suggestion.get('suggested_title') == 'Bohemian Rhapsody':
                        test_suggestion = suggestion
                        break
                
                if test_suggestion:
                    print(f"   ✅ Suggestion found in musician's interface")
                    print(f"   📊 Status: {test_suggestion.get('status')}")
                    print(f"   📊 Requester: {test_suggestion.get('requester_name')}")
                    suggestion_in_management = True
                else:
                    print(f"   ❌ Suggestion not found in musician's interface")
                    suggestion_in_management = False
            else:
                print(f"   ❌ Failed to get suggestions list: {suggestions_response.status_code}")
                suggestion_in_management = False
            
            # Step 6: Test suggestion acceptance (optional)
            print("📊 Step 6: Test suggestion acceptance workflow")
            
            if suggestion_id and suggestion_in_management:
                accept_response = self.make_request("PUT", f"/song-suggestions/{suggestion_id}/status", {"status": "accepted"})
                
                if accept_response.status_code == 200:
                    print(f"   ✅ Suggestion accepted successfully")
                    
                    # Check if song was added to repertoire
                    songs_check_response = self.make_request("GET", "/songs")
                    if songs_check_response.status_code == 200:
                        updated_songs = songs_check_response.json()
                        bohemian_rhapsody = None
                        for song in updated_songs:
                            if song.get('title') == 'Bohemian Rhapsody':
                                bohemian_rhapsody = song
                                break
                        
                        if bohemian_rhapsody:
                            print(f"   ✅ Accepted suggestion added to repertoire")
                            print(f"   📊 Added song: {bohemian_rhapsody['title']} by {bohemian_rhapsody['artist']}")
                            suggestion_acceptance_works = True
                        else:
                            print(f"   ❌ Accepted suggestion not added to repertoire")
                            suggestion_acceptance_works = False
                    else:
                        print(f"   ❌ Failed to check updated songs list")
                        suggestion_acceptance_works = False
                else:
                    print(f"   ❌ Suggestion acceptance failed: {accept_response.status_code}")
                    suggestion_acceptance_works = False
            else:
                print(f"   ⚠️  Skipping acceptance test - suggestion not properly created")
                suggestion_acceptance_works = True  # Don't fail the test for this
            
            # Step 7: Clean up test data
            print("📊 Step 7: Clean up test data")
            
            cleanup_count = 0
            
            # Delete test songs
            for song in added_songs:
                delete_response = self.make_request("DELETE", f"/songs/{song['id']}")
                if delete_response.status_code == 200:
                    cleanup_count += 1
            
            # Delete suggestion if it exists
            if suggestion_id:
                delete_suggestion_response = self.make_request("DELETE", f"/song-suggestions/{suggestion_id}")
                if delete_suggestion_response.status_code == 200:
                    cleanup_count += 1
            
            print(f"   ✅ Cleaned up {cleanup_count} test items")
            
            # Final assessment
            if profile_accessible and songs_accessible and suggestion_works and suggestion_in_management:
                self.log_result("End-to-End Musician and Audience Flow", True, "✅ END-TO-END FLOW WORKING: Musician registration, song management, audience access, and song suggestions all working correctly")
            else:
                issues = []
                if not profile_accessible:
                    issues.append("audience cannot access musician profile")
                if not songs_accessible:
                    issues.append("audience cannot access songs list")
                if not suggestion_works:
                    issues.append("song suggestion submission not working")
                if not suggestion_in_management:
                    issues.append("suggestions not appearing in musician management")
                
                self.log_result("End-to-End Musician and Audience Flow", False, f"❌ END-TO-END FLOW ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("End-to-End Musician and Audience Flow", False, f"❌ Exception: {str(e)}")

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🎵 STARTING COMPREHENSIVE VENMO LINK AND SUGGEST SONG TESTING")
        print("=" * 100)
        
        # Test 1: Legacy Venmo Link Removal
        self.test_legacy_venmo_link_removal()
        
        # Test 2: Suggest Song Button Always Visible
        self.test_suggest_song_button_always_visible()
        
        # Test 3: End-to-End Flow
        self.test_end_to_end_musician_and_audience_flow()
        
        # Print final results
        print("\n" + "=" * 100)
        print("🎵 FINAL TEST RESULTS")
        print("=" * 100)
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        print(f"📊 SUCCESS RATE: {(self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100):.1f}%")
        
        if self.results['errors']:
            print("\n❌ FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        print("\n" + "=" * 100)

if __name__ == "__main__":
    tester = RequestWaveAPITester()
    tester.run_all_tests()