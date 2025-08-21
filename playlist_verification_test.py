#!/usr/bin/env python3
"""
PLAYLIST EDITING BACKEND VERIFICATION TEST

Quick verification of playlist editing backend after frontend implementation as requested:

SPECIFIC TESTS:
1. Login with brycelarsenmusic@gmail.com / RequestWave2024!
2. Create a test playlist with 4 songs and verify response includes updated_at field
3. Test GET /playlists/{playlist_id} still works and returns songs in correct order
4. Test PUT /playlists/{playlist_id}/songs still works and verify updated_at changes

This is a focused smoke test to confirm backend is ready for frontend testing.
"""

import requests
import json
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://performance-pay-1.preview.emergentagent.com/api"

# Pro account credentials for testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class PlaylistVerificationTester:
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

    def make_request(self, method: str, endpoint: str, data: Any = None, params: Dict = None) -> requests.Response:
        """Make HTTP request with proper headers"""
        url = f"{self.base_url}{endpoint}"
        
        # Default headers
        request_headers = {"Content-Type": "application/json"}
        if self.auth_token:
            request_headers["Authorization"] = f"Bearer {self.auth_token}"
        
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

    def test_login_with_pro_account(self):
        """Test 1: Login with brycelarsenmusic@gmail.com / RequestWave2024!"""
        try:
            print("🎵 TEST 1: Login with Pro Account")
            print("=" * 60)
            
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
                    
                    print(f"   ✅ Successfully logged in as: {data['musician']['name']}")
                    print(f"   📊 Musician ID: {self.musician_id}")
                    print(f"   📊 Musician Slug: {self.musician_slug}")
                    
                    self.log_result("Pro Account Login", True, f"Logged in as {data['musician']['name']}")
                else:
                    self.log_result("Pro Account Login", False, f"Missing token or musician in response: {data}")
            else:
                self.log_result("Pro Account Login", False, f"Status code: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_result("Pro Account Login", False, f"Exception: {str(e)}")

    def test_create_playlist_with_4_songs(self):
        """Test 2: Create a test playlist with 4 songs and verify response includes updated_at field"""
        try:
            print("\n🎵 TEST 2: Create Playlist with 4 Songs")
            print("=" * 60)
            
            if not self.auth_token:
                self.log_result("Create Playlist with 4 Songs", False, "No auth token available")
                return
            
            # Step 1: Get available songs
            print("📊 Step 1: Get available songs")
            songs_response = self.make_request("GET", "/songs")
            
            if songs_response.status_code != 200:
                self.log_result("Create Playlist with 4 Songs", False, f"Failed to get songs: {songs_response.status_code}")
                return
            
            songs = songs_response.json()
            if len(songs) < 4:
                self.log_result("Create Playlist with 4 Songs", False, f"Need at least 4 songs, found {len(songs)}")
                return
            
            # Use first 4 songs
            test_song_ids = [songs[i]["id"] for i in range(4)]
            song_titles = [f"{songs[i]['title']} by {songs[i]['artist']}" for i in range(4)]
            
            print(f"   ✅ Found {len(songs)} total songs")
            print(f"   📊 Using 4 songs for playlist:")
            for i, title in enumerate(song_titles):
                print(f"      {i+1}. {title}")
            
            # Step 2: Create playlist with 4 songs
            print("📊 Step 2: Create playlist with 4 songs")
            
            playlist_data = {
                "name": "Verification Test Playlist (4 songs)",
                "song_ids": test_song_ids
            }
            
            create_response = self.make_request("POST", "/playlists", playlist_data)
            
            if create_response.status_code != 200:
                self.log_result("Create Playlist with 4 Songs", False, f"Failed to create playlist: {create_response.status_code}, Response: {create_response.text}")
                return
            
            created_playlist = create_response.json()
            
            print(f"   ✅ Created playlist: {created_playlist['name']}")
            print(f"   📊 Playlist ID: {created_playlist['id']}")
            print(f"   📊 Song count: {created_playlist.get('song_count', 'N/A')}")
            
            # Step 3: Verify response includes updated_at field
            print("📊 Step 3: Verify response includes updated_at field")
            
            has_updated_at = "updated_at" in created_playlist
            has_created_at = "created_at" in created_playlist
            
            if has_updated_at:
                print(f"   ✅ updated_at field present: {created_playlist['updated_at']}")
            else:
                print(f"   ❌ updated_at field missing")
            
            if has_created_at:
                print(f"   ✅ created_at field present: {created_playlist['created_at']}")
            else:
                print(f"   ❌ created_at field missing")
            
            # Store playlist ID for next tests
            self.test_playlist_id = created_playlist["id"]
            self.test_song_ids = test_song_ids
            
            if has_updated_at and has_created_at:
                self.log_result("Create Playlist with 4 Songs", True, f"Playlist created successfully with updated_at and created_at fields")
            else:
                missing_fields = []
                if not has_updated_at:
                    missing_fields.append("updated_at")
                if not has_created_at:
                    missing_fields.append("created_at")
                self.log_result("Create Playlist with 4 Songs", False, f"Missing fields: {', '.join(missing_fields)}")
                
        except Exception as e:
            self.log_result("Create Playlist with 4 Songs", False, f"Exception: {str(e)}")

    def test_get_playlist_detail(self):
        """Test 3: Test GET /playlists/{playlist_id} still works and returns songs in correct order"""
        try:
            print("\n🎵 TEST 3: GET Playlist Detail")
            print("=" * 60)
            
            if not hasattr(self, 'test_playlist_id'):
                self.log_result("GET Playlist Detail", False, "No test playlist available")
                return
            
            # Step 1: Get playlist detail
            print("📊 Step 1: Get playlist detail")
            
            detail_response = self.make_request("GET", f"/playlists/{self.test_playlist_id}")
            
            print(f"   📊 GET playlist detail status: {detail_response.status_code}")
            
            if detail_response.status_code != 200:
                self.log_result("GET Playlist Detail", False, f"GET playlist detail failed: {detail_response.status_code}, Response: {detail_response.text}")
                return
            
            detail_data = detail_response.json()
            
            print(f"   ✅ GET playlist detail successful")
            print(f"   📊 Response keys: {list(detail_data.keys())}")
            
            # Step 2: Verify response structure
            print("📊 Step 2: Verify response structure")
            
            required_fields = ["id", "name", "song_ids", "songs", "song_count", "created_at", "updated_at"]
            missing_fields = [field for field in required_fields if field not in detail_data]
            
            if len(missing_fields) == 0:
                print(f"   ✅ All required fields present")
                structure_valid = True
            else:
                print(f"   ❌ Missing fields: {missing_fields}")
                structure_valid = False
            
            # Step 3: Verify songs are in correct order
            print("📊 Step 3: Verify songs are in correct order")
            
            returned_song_ids = detail_data.get("song_ids", [])
            expected_song_ids = self.test_song_ids
            
            order_correct = returned_song_ids == expected_song_ids
            
            if order_correct:
                print(f"   ✅ Song IDs in correct order")
                print(f"   📊 Expected: {expected_song_ids}")
                print(f"   📊 Returned: {returned_song_ids}")
            else:
                print(f"   ❌ Song order incorrect")
                print(f"   📊 Expected: {expected_song_ids}")
                print(f"   📊 Returned: {returned_song_ids}")
            
            # Step 4: Verify song details are included
            print("📊 Step 4: Verify song details are included")
            
            returned_songs = detail_data.get("songs", [])
            songs_count_correct = len(returned_songs) == 4
            
            if songs_count_correct:
                print(f"   ✅ Correct number of song details: {len(returned_songs)}")
                
                # Show first song as example
                if len(returned_songs) > 0:
                    sample_song = returned_songs[0]
                    print(f"   📊 Sample song: {sample_song.get('title')} by {sample_song.get('artist')}")
            else:
                print(f"   ❌ Wrong number of song details. Expected: 4, Got: {len(returned_songs)}")
            
            if structure_valid and order_correct and songs_count_correct:
                self.log_result("GET Playlist Detail", True, f"GET playlist detail working correctly - returns ordered songs with full details")
            else:
                issues = []
                if not structure_valid:
                    issues.append(f"missing fields: {missing_fields}")
                if not order_correct:
                    issues.append("song order incorrect")
                if not songs_count_correct:
                    issues.append("wrong song count")
                
                self.log_result("GET Playlist Detail", False, f"Issues: {', '.join(issues)}")
                
        except Exception as e:
            self.log_result("GET Playlist Detail", False, f"Exception: {str(e)}")

    def test_put_playlist_songs_reorder(self):
        """Test 4: Test PUT /playlists/{playlist_id}/songs still works and verify updated_at changes"""
        try:
            print("\n🎵 TEST 4: PUT Playlist Songs Reorder")
            print("=" * 60)
            
            if not hasattr(self, 'test_playlist_id'):
                self.log_result("PUT Playlist Songs Reorder", False, "No test playlist available")
                return
            
            # Step 1: Get current playlist state
            print("📊 Step 1: Get current playlist state")
            
            current_response = self.make_request("GET", f"/playlists/{self.test_playlist_id}")
            
            if current_response.status_code != 200:
                self.log_result("PUT Playlist Songs Reorder", False, f"Failed to get current playlist: {current_response.status_code}")
                return
            
            current_data = current_response.json()
            original_song_ids = current_data.get("song_ids", [])
            original_updated_at = current_data.get("updated_at")
            
            print(f"   ✅ Current playlist state retrieved")
            print(f"   📊 Original song order: {original_song_ids}")
            print(f"   📊 Original updated_at: {original_updated_at}")
            
            # Wait a moment to ensure updated_at will change
            time.sleep(1)
            
            # Step 2: Reorder songs (reverse the order)
            print("📊 Step 2: Reorder songs (reverse the order)")
            
            reordered_song_ids = list(reversed(original_song_ids))
            
            reorder_data = {
                "song_ids": reordered_song_ids
            }
            
            print(f"   📊 New song order: {reordered_song_ids}")
            
            reorder_response = self.make_request("PUT", f"/playlists/{self.test_playlist_id}/songs", reorder_data)
            
            print(f"   📊 PUT reorder status: {reorder_response.status_code}")
            
            if reorder_response.status_code != 200:
                self.log_result("PUT Playlist Songs Reorder", False, f"PUT reorder failed: {reorder_response.status_code}, Response: {reorder_response.text}")
                return
            
            reorder_result = reorder_response.json()
            new_updated_at = reorder_result.get("updated_at")
            
            print(f"   ✅ PUT reorder successful")
            print(f"   📊 New updated_at: {new_updated_at}")
            
            # Step 3: Verify updated_at changed
            print("📊 Step 3: Verify updated_at changed")
            
            updated_at_changed = new_updated_at != original_updated_at
            
            if updated_at_changed:
                print(f"   ✅ updated_at changed successfully")
                print(f"   📊 Before: {original_updated_at}")
                print(f"   📊 After:  {new_updated_at}")
            else:
                print(f"   ❌ updated_at did not change: {original_updated_at}")
            
            # Step 4: Verify new order is correct
            print("📊 Step 4: Verify new order is correct")
            
            returned_song_ids = reorder_result.get("song_ids", [])
            order_correct = returned_song_ids == reordered_song_ids
            
            if order_correct:
                print(f"   ✅ Song order correct after reordering")
            else:
                print(f"   ❌ Song order incorrect after reordering")
                print(f"   📊 Expected: {reordered_song_ids}")
                print(f"   📊 Returned: {returned_song_ids}")
            
            # Step 5: Verify GET endpoint reflects the change
            print("📊 Step 5: Verify GET endpoint reflects the change")
            
            verify_response = self.make_request("GET", f"/playlists/{self.test_playlist_id}")
            
            if verify_response.status_code == 200:
                verify_data = verify_response.json()
                verify_song_ids = verify_data.get("song_ids", [])
                get_reflects_change = verify_song_ids == reordered_song_ids
                
                if get_reflects_change:
                    print(f"   ✅ GET endpoint reflects the reorder change")
                else:
                    print(f"   ❌ GET endpoint doesn't reflect change")
                    print(f"   📊 Expected: {reordered_song_ids}")
                    print(f"   📊 GET result: {verify_song_ids}")
            else:
                print(f"   ❌ GET verification failed: {verify_response.status_code}")
                get_reflects_change = False
            
            if updated_at_changed and order_correct and get_reflects_change:
                self.log_result("PUT Playlist Songs Reorder", True, f"PUT playlist songs reorder working correctly - updates order and updated_at field")
            else:
                issues = []
                if not updated_at_changed:
                    issues.append("updated_at not changed")
                if not order_correct:
                    issues.append("song order incorrect")
                if not get_reflects_change:
                    issues.append("GET doesn't reflect change")
                
                self.log_result("PUT Playlist Songs Reorder", False, f"Issues: {', '.join(issues)}")
                
        except Exception as e:
            self.log_result("PUT Playlist Songs Reorder", False, f"Exception: {str(e)}")

    def cleanup_test_playlist(self):
        """Clean up the test playlist"""
        try:
            if hasattr(self, 'test_playlist_id'):
                print("\n🧹 CLEANUP: Deleting test playlist")
                
                delete_response = self.make_request("DELETE", f"/playlists/{self.test_playlist_id}")
                
                if delete_response.status_code == 200:
                    print(f"   ✅ Test playlist deleted successfully")
                else:
                    print(f"   ⚠️  Failed to delete test playlist: {delete_response.status_code}")
        except Exception as e:
            print(f"   ⚠️  Exception during cleanup: {str(e)}")

    def run_verification_tests(self):
        """Run all verification tests"""
        print("🎵 PLAYLIST EDITING BACKEND VERIFICATION")
        print("=" * 80)
        print("Quick smoke test to verify playlist editing backend after frontend implementation")
        print("=" * 80)
        
        # Run tests in sequence
        self.test_login_with_pro_account()
        
        if self.auth_token:  # Only continue if login successful
            self.test_create_playlist_with_4_songs()
            self.test_get_playlist_detail()
            self.test_put_playlist_songs_reorder()
            
            # Cleanup
            self.cleanup_test_playlist()
        
        # Print summary
        print("\n" + "=" * 80)
        print("🎵 VERIFICATION SUMMARY")
        print("=" * 80)
        
        total_tests = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.results['passed']} ✅")
        print(f"Failed: {self.results['failed']} ❌")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if self.results["failed"] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        if success_rate >= 75:
            print(f"\n✅ VERIFICATION RESULT: Backend playlist editing functionality is working correctly")
            print(f"   Ready for frontend testing!")
        else:
            print(f"\n❌ VERIFICATION RESULT: Backend has issues that need to be addressed")
            print(f"   Frontend testing should wait until backend issues are resolved")
        
        print("=" * 80)

if __name__ == "__main__":
    tester = PlaylistVerificationTester()
    tester.run_verification_tests()