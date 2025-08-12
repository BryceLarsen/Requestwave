#!/usr/bin/env python3
"""
PLAYLIST CREATION FUNCTIONALITY TESTING

Testing the specific issue reported by user brycelarsenmusic@gmail.com:
- User selects 5 songs and tries to create a new playlist
- The playlist is not showing up in the "All Playlists" tab
- The playlist is not appearing in the existing playlists dropdown
- Seems like playlists are not being saved properly

SPECIFIC TESTS NEEDED:
1. Test playlist creation flow step by step
2. Test playlist persistence
3. Test Pro access requirements
4. Debug any errors

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!
"""

import requests
import json
import time
from typing import Dict, Any, Optional, List

# Configuration
BASE_URL = "https://musician-dashboard.preview.emergentagent.com/api"

# Pro account for playlist testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class PlaylistCreationTester:
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

    def test_login_with_pro_account(self):
        """Test login with brycelarsenmusic@gmail.com"""
        try:
            print("🔐 STEP 1: Login with Pro Account")
            print("=" * 60)
            
            login_data = {
                "email": PRO_MUSICIAN["email"],
                "password": PRO_MUSICIAN["password"]
            }
            
            response = self.make_request("POST", "/auth/login", login_data)
            
            print(f"   📊 Login response status: {response.status_code}")
            print(f"   📊 Login response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "musician" in data:
                    self.auth_token = data["token"]
                    self.musician_id = data["musician"]["id"]
                    self.musician_slug = data["musician"]["slug"]
                    
                    print(f"   ✅ Successfully logged in as: {data['musician']['name']}")
                    print(f"   ✅ Musician ID: {self.musician_id}")
                    print(f"   ✅ Musician slug: {self.musician_slug}")
                    
                    self.log_result("Pro Account Login", True, f"Logged in as {data['musician']['name']}")
                    return True
                else:
                    self.log_result("Pro Account Login", False, f"Missing token or musician in response: {data}")
                    return False
            else:
                self.log_result("Pro Account Login", False, f"Status code: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Pro Account Login", False, f"Exception: {str(e)}")
            return False

    def test_pro_subscription_status(self):
        """Test Pro subscription status"""
        try:
            print("🔐 STEP 2: Verify Pro Subscription Status")
            print("=" * 60)
            
            if not self.auth_token:
                self.log_result("Pro Subscription Status", False, "No auth token available")
                return False
            
            response = self.make_request("GET", "/subscription/status")
            
            print(f"   📊 Subscription status response: {response.status_code}")
            print(f"   📊 Subscription response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if user has Pro access
                plan = data.get("plan", "unknown")
                audience_link_active = data.get("audience_link_active", False)
                
                print(f"   📊 Plan: {plan}")
                print(f"   📊 Audience link active: {audience_link_active}")
                
                if plan in ["trial", "pro", "active"] or audience_link_active:
                    self.log_result("Pro Subscription Status", True, f"User has Pro access: plan={plan}, audience_link_active={audience_link_active}")
                    return True
                else:
                    self.log_result("Pro Subscription Status", False, f"User does not have Pro access: plan={plan}, audience_link_active={audience_link_active}")
                    return False
            else:
                self.log_result("Pro Subscription Status", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Pro Subscription Status", False, f"Exception: {str(e)}")
            return False

    def test_get_existing_songs(self):
        """Get user's existing songs for playlist creation"""
        try:
            print("🎵 STEP 3: Get User's Existing Songs")
            print("=" * 60)
            
            if not self.auth_token:
                self.log_result("Get Existing Songs", False, "No auth token available")
                return []
            
            response = self.make_request("GET", "/songs")
            
            print(f"   📊 Songs response status: {response.status_code}")
            
            if response.status_code == 200:
                songs = response.json()
                print(f"   ✅ Found {len(songs)} songs in user's library")
                
                # Show first few songs
                for i, song in enumerate(songs[:5]):
                    print(f"   📊 Song {i+1}: '{song.get('title', 'Unknown')}' by {song.get('artist', 'Unknown')}")
                
                if len(songs) >= 5:
                    self.log_result("Get Existing Songs", True, f"Found {len(songs)} songs, sufficient for playlist creation")
                    return songs
                else:
                    self.log_result("Get Existing Songs", False, f"Only {len(songs)} songs found, need at least 5 for testing")
                    return songs
            else:
                print(f"   📊 Songs response: {response.text}")
                self.log_result("Get Existing Songs", False, f"Status code: {response.status_code}")
                return []
                
        except Exception as e:
            self.log_result("Get Existing Songs", False, f"Exception: {str(e)}")
            return []

    def test_playlist_creation_step_by_step(self, songs: List[Dict]):
        """Test playlist creation flow step by step"""
        try:
            print("🎵 STEP 4: Test Playlist Creation Flow")
            print("=" * 60)
            
            if not self.auth_token:
                self.log_result("Playlist Creation Flow", False, "No auth token available")
                return None
            
            if len(songs) < 5:
                self.log_result("Playlist Creation Flow", False, f"Need at least 5 songs, only have {len(songs)}")
                return None
            
            # Select 5 songs for the playlist
            selected_songs = songs[:5]
            song_ids = [song["id"] for song in selected_songs]
            
            print(f"   📊 Selected 5 songs for playlist:")
            for i, song in enumerate(selected_songs):
                print(f"   📊   {i+1}. '{song.get('title')}' by {song.get('artist')}")
            
            # Create playlist data
            playlist_name = f"Test Playlist - {int(time.time())}"
            playlist_data = {
                "name": playlist_name,
                "song_ids": song_ids
            }
            
            print(f"   📊 Creating playlist: {playlist_name}")
            print(f"   📊 Playlist data: {json.dumps(playlist_data, indent=2)}")
            
            # Make the playlist creation request
            response = self.make_request("POST", "/playlists", playlist_data)
            
            print(f"   📊 Playlist creation response status: {response.status_code}")
            print(f"   📊 Playlist creation response: {response.text}")
            
            if response.status_code == 200:
                created_playlist = response.json()
                
                print(f"   ✅ Playlist created successfully!")
                print(f"   📊 Created playlist ID: {created_playlist.get('id')}")
                print(f"   📊 Created playlist name: {created_playlist.get('name')}")
                print(f"   📊 Created playlist song count: {created_playlist.get('song_count')}")
                
                # Verify the response structure
                required_fields = ["id", "name", "song_count"]
                missing_fields = [field for field in required_fields if field not in created_playlist]
                
                if len(missing_fields) == 0:
                    self.log_result("Playlist Creation Flow", True, f"Playlist '{playlist_name}' created successfully with {len(song_ids)} songs")
                    return created_playlist
                else:
                    self.log_result("Playlist Creation Flow", False, f"Playlist created but missing fields: {missing_fields}")
                    return created_playlist
            elif response.status_code == 403:
                self.log_result("Playlist Creation Flow", False, "Access denied - Pro subscription required")
                return None
            else:
                self.log_result("Playlist Creation Flow", False, f"Status code: {response.status_code}, Response: {response.text}")
                return None
                
        except Exception as e:
            self.log_result("Playlist Creation Flow", False, f"Exception: {str(e)}")
            return None

    def test_playlist_appears_in_all_playlists(self, created_playlist: Dict):
        """Test if playlist appears in GET /api/playlists"""
        try:
            print("🎵 STEP 5: Test Playlist Appears in All Playlists Tab")
            print("=" * 60)
            
            if not self.auth_token:
                self.log_result("Playlist in All Playlists", False, "No auth token available")
                return False
            
            if not created_playlist:
                self.log_result("Playlist in All Playlists", False, "No created playlist to test")
                return False
            
            created_playlist_id = created_playlist.get("id")
            created_playlist_name = created_playlist.get("name")
            
            print(f"   📊 Looking for playlist: {created_playlist_name} (ID: {created_playlist_id})")
            
            # Get all playlists
            response = self.make_request("GET", "/playlists")
            
            print(f"   📊 Get playlists response status: {response.status_code}")
            
            if response.status_code == 200:
                all_playlists = response.json()
                
                print(f"   📊 Found {len(all_playlists)} total playlists:")
                for i, playlist in enumerate(all_playlists):
                    print(f"   📊   {i+1}. '{playlist.get('name')}' (ID: {playlist.get('id')}, Songs: {playlist.get('song_count', 0)})")
                
                # Look for our created playlist
                found_playlist = None
                for playlist in all_playlists:
                    if playlist.get("id") == created_playlist_id:
                        found_playlist = playlist
                        break
                
                if found_playlist:
                    print(f"   ✅ Created playlist found in All Playlists!")
                    print(f"   📊 Found playlist: {found_playlist}")
                    
                    # Verify the data matches
                    if (found_playlist.get("name") == created_playlist_name and 
                        found_playlist.get("song_count") == created_playlist.get("song_count")):
                        self.log_result("Playlist in All Playlists", True, f"Playlist '{created_playlist_name}' correctly appears in All Playlists tab")
                        return True
                    else:
                        self.log_result("Playlist in All Playlists", False, f"Playlist found but data mismatch: {found_playlist}")
                        return False
                else:
                    print(f"   ❌ Created playlist NOT found in All Playlists!")
                    self.log_result("Playlist in All Playlists", False, f"Playlist '{created_playlist_name}' does not appear in All Playlists tab")
                    return False
            else:
                print(f"   📊 Get playlists response: {response.text}")
                self.log_result("Playlist in All Playlists", False, f"Failed to get playlists: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Playlist in All Playlists", False, f"Exception: {str(e)}")
            return False

    def test_playlist_persistence_after_creation(self, created_playlist: Dict):
        """Test playlist persistence by creating multiple playlists"""
        try:
            print("🎵 STEP 6: Test Playlist Persistence")
            print("=" * 60)
            
            if not self.auth_token:
                self.log_result("Playlist Persistence", False, "No auth token available")
                return False
            
            if not created_playlist:
                self.log_result("Playlist Persistence", False, "No created playlist to test")
                return False
            
            # Get songs again for second playlist
            songs_response = self.make_request("GET", "/songs")
            if songs_response.status_code != 200:
                self.log_result("Playlist Persistence", False, "Failed to get songs for second playlist")
                return False
            
            songs = songs_response.json()
            if len(songs) < 3:
                self.log_result("Playlist Persistence", False, "Not enough songs for second playlist")
                return False
            
            # Create a second playlist
            second_playlist_name = f"Second Test Playlist - {int(time.time())}"
            second_playlist_data = {
                "name": second_playlist_name,
                "song_ids": [songs[0]["id"], songs[1]["id"], songs[2]["id"]]
            }
            
            print(f"   📊 Creating second playlist: {second_playlist_name}")
            
            second_response = self.make_request("POST", "/playlists", second_playlist_data)
            
            print(f"   📊 Second playlist creation status: {second_response.status_code}")
            
            if second_response.status_code == 200:
                second_playlist = second_response.json()
                print(f"   ✅ Second playlist created: {second_playlist.get('name')}")
                
                # Wait a moment for persistence
                time.sleep(1)
                
                # Check if both playlists exist
                all_playlists_response = self.make_request("GET", "/playlists")
                
                if all_playlists_response.status_code == 200:
                    all_playlists = all_playlists_response.json()
                    
                    # Look for both playlists
                    first_found = any(p.get("id") == created_playlist.get("id") for p in all_playlists)
                    second_found = any(p.get("id") == second_playlist.get("id") for p in all_playlists)
                    
                    print(f"   📊 First playlist found: {first_found}")
                    print(f"   📊 Second playlist found: {second_found}")
                    
                    if first_found and second_found:
                        self.log_result("Playlist Persistence", True, "Both playlists persist correctly after creation")
                        
                        # Clean up second playlist
                        delete_response = self.make_request("DELETE", f"/playlists/{second_playlist.get('id')}")
                        if delete_response.status_code == 200:
                            print(f"   ✅ Cleaned up second test playlist")
                        
                        return True
                    else:
                        self.log_result("Playlist Persistence", False, f"Playlist persistence failed: first={first_found}, second={second_found}")
                        return False
                else:
                    self.log_result("Playlist Persistence", False, "Failed to retrieve playlists for persistence check")
                    return False
            else:
                print(f"   📊 Second playlist response: {second_response.text}")
                self.log_result("Playlist Persistence", False, f"Failed to create second playlist: {second_response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Playlist Persistence", False, f"Exception: {str(e)}")
            return False

    def test_playlist_in_dropdown_context(self, created_playlist: Dict):
        """Test if playlist appears in contexts where dropdowns would use it"""
        try:
            print("🎵 STEP 7: Test Playlist in Dropdown Context")
            print("=" * 60)
            
            if not self.auth_token:
                self.log_result("Playlist in Dropdown", False, "No auth token available")
                return False
            
            if not created_playlist:
                self.log_result("Playlist in Dropdown", False, "No created playlist to test")
                return False
            
            created_playlist_id = created_playlist.get("id")
            created_playlist_name = created_playlist.get("name")
            
            # Test 1: Check if playlist appears in authenticated playlists endpoint
            print(f"   📊 Test 1: Check authenticated playlists endpoint")
            
            auth_playlists_response = self.make_request("GET", "/playlists")
            
            if auth_playlists_response.status_code == 200:
                auth_playlists = auth_playlists_response.json()
                
                found_in_auth = any(p.get("id") == created_playlist_id for p in auth_playlists)
                print(f"   📊 Found in authenticated endpoint: {found_in_auth}")
                
                if found_in_auth:
                    print(f"   ✅ Playlist appears in authenticated playlists endpoint")
                else:
                    print(f"   ❌ Playlist missing from authenticated playlists endpoint")
            else:
                print(f"   ❌ Failed to get authenticated playlists: {auth_playlists_response.status_code}")
                found_in_auth = False
            
            # Test 2: Check if we can retrieve the specific playlist
            print(f"   📊 Test 2: Check specific playlist retrieval")
            
            # Try to get the specific playlist (if such endpoint exists)
            specific_playlist_response = self.make_request("GET", f"/playlists/{created_playlist_id}")
            
            if specific_playlist_response.status_code == 200:
                specific_playlist = specific_playlist_response.json()
                print(f"   ✅ Can retrieve specific playlist: {specific_playlist.get('name')}")
                specific_retrieval_works = True
            elif specific_playlist_response.status_code == 404:
                print(f"   ❌ Specific playlist not found (404)")
                specific_retrieval_works = False
            else:
                print(f"   📊 Specific playlist endpoint status: {specific_playlist_response.status_code}")
                specific_retrieval_works = False
            
            # Test 3: Check if playlist can be used for filtering (simulates dropdown usage)
            print(f"   📊 Test 3: Check playlist can be used for filtering")
            
            # Clear auth for public access (simulating audience interface)
            original_token = self.auth_token
            self.auth_token = None
            
            # Try to use the playlist for filtering songs (public endpoint)
            filter_response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs", params={"playlist": created_playlist_id})
            
            print(f"   📊 Playlist filtering response status: {filter_response.status_code}")
            
            if filter_response.status_code == 200:
                filtered_songs = filter_response.json()
                print(f"   ✅ Playlist can be used for filtering: {len(filtered_songs)} songs returned")
                filtering_works = True
            else:
                print(f"   ❌ Playlist filtering failed: {filter_response.status_code}")
                filtering_works = False
            
            # Restore auth token
            self.auth_token = original_token
            
            # Final assessment
            if found_in_auth and (specific_retrieval_works or filtering_works):
                self.log_result("Playlist in Dropdown", True, f"Playlist '{created_playlist_name}' appears in dropdown contexts and can be used")
                return True
            else:
                issues = []
                if not found_in_auth:
                    issues.append("not in authenticated playlists")
                if not specific_retrieval_works:
                    issues.append("cannot retrieve specifically")
                if not filtering_works:
                    issues.append("cannot be used for filtering")
                
                self.log_result("Playlist in Dropdown", False, f"Playlist dropdown issues: {', '.join(issues)}")
                return False
                
        except Exception as e:
            self.log_result("Playlist in Dropdown", False, f"Exception: {str(e)}")
            return False

    def test_cleanup_created_playlist(self, created_playlist: Dict):
        """Clean up the test playlist"""
        try:
            print("🧹 STEP 8: Clean Up Test Playlist")
            print("=" * 60)
            
            if not self.auth_token or not created_playlist:
                print("   ℹ️  No cleanup needed")
                return True
            
            playlist_id = created_playlist.get("id")
            playlist_name = created_playlist.get("name")
            
            print(f"   📊 Deleting test playlist: {playlist_name}")
            
            delete_response = self.make_request("DELETE", f"/playlists/{playlist_id}")
            
            print(f"   📊 Delete response status: {delete_response.status_code}")
            
            if delete_response.status_code == 200:
                print(f"   ✅ Test playlist deleted successfully")
                
                # Verify deletion
                verify_response = self.make_request("GET", "/playlists")
                if verify_response.status_code == 200:
                    remaining_playlists = verify_response.json()
                    still_exists = any(p.get("id") == playlist_id for p in remaining_playlists)
                    
                    if not still_exists:
                        print(f"   ✅ Playlist deletion verified")
                        return True
                    else:
                        print(f"   ⚠️  Playlist still exists after deletion")
                        return False
                else:
                    print(f"   ⚠️  Could not verify deletion")
                    return True  # Assume it worked
            else:
                print(f"   ⚠️  Failed to delete playlist: {delete_response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ⚠️  Cleanup exception: {str(e)}")
            return False

    def run_comprehensive_playlist_test(self):
        """Run the comprehensive playlist creation test"""
        print("🎵 COMPREHENSIVE PLAYLIST CREATION TEST")
        print("=" * 80)
        print(f"Testing playlist creation issue for user: {PRO_MUSICIAN['email']}")
        print("=" * 80)
        
        # Step 1: Login
        if not self.test_login_with_pro_account():
            print("❌ CRITICAL: Cannot proceed without login")
            return
        
        # Step 2: Verify Pro access
        if not self.test_pro_subscription_status():
            print("❌ CRITICAL: User does not have Pro access for playlist creation")
            return
        
        # Step 3: Get existing songs
        songs = self.test_get_existing_songs()
        if len(songs) < 5:
            print("❌ CRITICAL: Not enough songs for playlist creation test")
            return
        
        # Step 4: Create playlist
        created_playlist = self.test_playlist_creation_step_by_step(songs)
        if not created_playlist:
            print("❌ CRITICAL: Playlist creation failed")
            return
        
        # Step 5: Test if playlist appears in All Playlists
        appears_in_all = self.test_playlist_appears_in_all_playlists(created_playlist)
        
        # Step 6: Test playlist persistence
        persistence_works = self.test_playlist_persistence_after_creation(created_playlist)
        
        # Step 7: Test playlist in dropdown context
        dropdown_works = self.test_playlist_in_dropdown_context(created_playlist)
        
        # Step 8: Cleanup
        self.test_cleanup_created_playlist(created_playlist)
        
        # Final Results
        print("\n" + "=" * 80)
        print("🎵 PLAYLIST CREATION TEST RESULTS")
        print("=" * 80)
        
        print(f"✅ Tests Passed: {self.results['passed']}")
        print(f"❌ Tests Failed: {self.results['failed']}")
        
        if self.results['failed'] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   - {error}")
        
        # Specific issue analysis
        print("\n🔍 ISSUE ANALYSIS:")
        print("=" * 40)
        
        if not appears_in_all:
            print("❌ CONFIRMED: Playlists are NOT showing up in 'All Playlists' tab")
        else:
            print("✅ RESOLVED: Playlists ARE showing up in 'All Playlists' tab")
        
        if not dropdown_works:
            print("❌ CONFIRMED: Playlists are NOT appearing in existing playlists dropdown")
        else:
            print("✅ RESOLVED: Playlists ARE appearing in existing playlists dropdown")
        
        if not persistence_works:
            print("❌ CONFIRMED: Playlists are NOT being saved properly")
        else:
            print("✅ RESOLVED: Playlists ARE being saved properly")
        
        # Overall assessment
        if appears_in_all and dropdown_works and persistence_works:
            print("\n🎉 OVERALL: Playlist creation functionality is WORKING correctly")
        else:
            print("\n⚠️  OVERALL: Playlist creation functionality has ISSUES that need to be addressed")

if __name__ == "__main__":
    tester = PlaylistCreationTester()
    tester.run_comprehensive_playlist_test()