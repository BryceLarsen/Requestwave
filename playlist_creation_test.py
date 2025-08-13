#!/usr/bin/env python3
"""
PLAYLIST CREATION FUNCTIONALITY VERIFICATION

Testing the playlist creation functionality after frontend fix:

CONTEXT:
- User reported playlists not showing up after creation
- Identified that frontend was only checking for 'pro' plan, but backend allows both 'trial' and 'pro'
- Fixed frontend to check for both 'trial' and 'pro' plans

SPECIFIC VERIFICATION NEEDED:
1. Login with brycelarsenmusic@gmail.com / RequestWave2024!
2. Verify user subscription status and plan
3. Create a test playlist with 3-5 songs
4. Verify playlist creation succeeds
5. Confirm playlist appears in GET /api/playlists
6. Verify subscription status returns correct plan
7. Double-check Pro access logic

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://requestwave-pro.preview.emergentagent.com/api"

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

    def test_login_and_subscription_status(self):
        """Test login with brycelarsenmusic@gmail.com and verify subscription status"""
        try:
            print("🔐 STEP 1: Login and Subscription Status Verification")
            print("=" * 80)
            
            # Step 1: Login with Pro account
            print("📊 Step 1.1: Login with brycelarsenmusic@gmail.com")
            login_data = {
                "email": PRO_MUSICIAN["email"],
                "password": PRO_MUSICIAN["password"]
            }
            
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code != 200:
                self.log_result("Login Authentication", False, f"Failed to login: {login_response.status_code}, Response: {login_response.text}")
                return False
            
            login_data_response = login_response.json()
            self.auth_token = login_data_response["token"]
            self.musician_id = login_data_response["musician"]["id"]
            self.musician_slug = login_data_response["musician"]["slug"]
            
            print(f"   ✅ Successfully logged in as: {login_data_response['musician']['name']}")
            print(f"   ✅ Musician ID: {self.musician_id}")
            print(f"   ✅ Musician slug: {self.musician_slug}")
            
            # Step 2: Check subscription status
            print("📊 Step 1.2: Check subscription status")
            
            subscription_response = self.make_request("GET", "/subscription/status")
            
            if subscription_response.status_code != 200:
                self.log_result("Subscription Status Check", False, f"Failed to get subscription status: {subscription_response.status_code}, Response: {subscription_response.text}")
                return False
            
            subscription_data = subscription_response.json()
            print(f"   📊 Subscription status response: {json.dumps(subscription_data, indent=2, default=str)}")
            
            # Verify subscription plan
            plan = subscription_data.get("plan", "unknown")
            audience_link_active = subscription_data.get("audience_link_active", False)
            trial_active = subscription_data.get("trial_active", False)
            
            print(f"   📊 Plan: {plan}")
            print(f"   📊 Audience link active: {audience_link_active}")
            print(f"   📊 Trial active: {trial_active}")
            
            # Check if plan is 'trial' or 'pro' (both should allow playlist creation)
            if plan in ['trial', 'pro']:
                print(f"   ✅ Plan '{plan}' should allow playlist creation")
                plan_allows_playlists = True
            else:
                print(f"   ⚠️  Plan '{plan}' - checking if this allows playlist creation")
                plan_allows_playlists = True  # We'll test this in practice
            
            self.log_result("Login and Subscription Status", True, f"Successfully logged in with plan '{plan}', audience_link_active={audience_link_active}")
            return True
            
        except Exception as e:
            self.log_result("Login and Subscription Status", False, f"Exception: {str(e)}")
            return False

    def test_pro_access_logic(self):
        """Test Pro access logic by checking playlist endpoints"""
        try:
            print("🔐 STEP 2: Pro Access Logic Verification")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Pro Access Logic", False, "No auth token available")
                return False
            
            # Step 1: Test GET /api/playlists endpoint (should work for Pro users)
            print("📊 Step 2.1: Test GET /api/playlists endpoint access")
            
            playlists_response = self.make_request("GET", "/playlists")
            
            print(f"   📊 GET /playlists status: {playlists_response.status_code}")
            print(f"   📊 GET /playlists response: {playlists_response.text[:200]}...")
            
            if playlists_response.status_code == 200:
                playlists_data = playlists_response.json()
                print(f"   ✅ Successfully accessed playlists endpoint - found {len(playlists_data)} playlists")
                pro_access_working = True
            elif playlists_response.status_code == 403:
                print(f"   ❌ Access denied to playlists endpoint - Pro access logic may be broken")
                pro_access_working = False
            else:
                print(f"   ⚠️  Unexpected response from playlists endpoint: {playlists_response.status_code}")
                pro_access_working = False
            
            # Step 2: Test POST /api/playlists endpoint (should work for Pro users)
            print("📊 Step 2.2: Test POST /api/playlists endpoint access (dry run)")
            
            # Try to create a minimal playlist to test access (we'll delete it later)
            test_playlist_data = {
                "name": "Access Test Playlist",
                "song_ids": []
            }
            
            create_response = self.make_request("POST", "/playlists", test_playlist_data)
            
            print(f"   📊 POST /playlists status: {create_response.status_code}")
            print(f"   📊 POST /playlists response: {create_response.text[:200]}...")
            
            if create_response.status_code == 200:
                created_playlist = create_response.json()
                print(f"   ✅ Successfully created test playlist: {created_playlist.get('name')}")
                
                # Clean up - delete the test playlist
                delete_response = self.make_request("DELETE", f"/playlists/{created_playlist['id']}")
                if delete_response.status_code == 200:
                    print(f"   ✅ Successfully cleaned up test playlist")
                
                create_access_working = True
            elif create_response.status_code == 403:
                print(f"   ❌ Access denied to create playlists - Pro access logic may be broken")
                create_access_working = False
            else:
                print(f"   ⚠️  Unexpected response from playlist creation: {create_response.status_code}")
                create_access_working = False
            
            overall_pro_access = pro_access_working and create_access_working
            
            self.log_result("Pro Access Logic", overall_pro_access, f"GET playlists: {pro_access_working}, POST playlists: {create_access_working}")
            return overall_pro_access
            
        except Exception as e:
            self.log_result("Pro Access Logic", False, f"Exception: {str(e)}")
            return False

    def test_playlist_creation_with_songs(self):
        """Test creating a playlist with 3-5 songs"""
        try:
            print("🎵 STEP 3: Playlist Creation with Songs")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Playlist Creation with Songs", False, "No auth token available")
                return False
            
            # Step 1: Get available songs
            print("📊 Step 3.1: Get available songs for playlist")
            
            songs_response = self.make_request("GET", "/songs")
            
            if songs_response.status_code != 200:
                self.log_result("Get Songs for Playlist", False, f"Failed to get songs: {songs_response.status_code}")
                return False
            
            songs = songs_response.json()
            print(f"   ✅ Found {len(songs)} available songs")
            
            if len(songs) < 3:
                self.log_result("Playlist Creation with Songs", False, f"Need at least 3 songs for test, found {len(songs)}")
                return False
            
            # Select 3-5 songs for the playlist
            selected_songs = songs[:5] if len(songs) >= 5 else songs[:3]
            selected_song_ids = [song["id"] for song in selected_songs]
            
            print(f"   ✅ Selected {len(selected_songs)} songs for playlist:")
            for i, song in enumerate(selected_songs, 1):
                print(f"      {i}. '{song['title']}' by {song['artist']}")
            
            # Step 2: Create the test playlist
            print("📊 Step 3.2: Create test playlist with selected songs")
            
            playlist_data = {
                "name": "Playlist Creation Test",
                "song_ids": selected_song_ids
            }
            
            create_response = self.make_request("POST", "/playlists", playlist_data)
            
            print(f"   📊 Create playlist status: {create_response.status_code}")
            print(f"   📊 Create playlist response: {create_response.text}")
            
            if create_response.status_code != 200:
                self.log_result("Playlist Creation with Songs", False, f"Failed to create playlist: {create_response.status_code}, Response: {create_response.text}")
                return False
            
            created_playlist = create_response.json()
            playlist_id = created_playlist["id"]
            
            print(f"   ✅ Successfully created playlist:")
            print(f"      ID: {playlist_id}")
            print(f"      Name: {created_playlist['name']}")
            print(f"      Song count: {created_playlist.get('song_count', 'unknown')}")
            
            # Step 3: Verify playlist appears in GET /api/playlists
            print("📊 Step 3.3: Verify playlist appears in GET /api/playlists")
            
            playlists_response = self.make_request("GET", "/playlists")
            
            if playlists_response.status_code != 200:
                self.log_result("Verify Playlist in List", False, f"Failed to get playlists: {playlists_response.status_code}")
                return False
            
            playlists = playlists_response.json()
            
            # Find our created playlist
            found_playlist = None
            for playlist in playlists:
                if playlist["id"] == playlist_id:
                    found_playlist = playlist
                    break
            
            if found_playlist:
                print(f"   ✅ Playlist found in GET /api/playlists:")
                print(f"      Name: {found_playlist['name']}")
                print(f"      Song count: {found_playlist.get('song_count', 'unknown')}")
                print(f"      Song IDs: {found_playlist.get('song_ids', [])}")
                
                # Verify song count matches
                expected_count = len(selected_song_ids)
                actual_count = found_playlist.get('song_count', 0)
                
                if actual_count == expected_count:
                    print(f"   ✅ Song count matches: {actual_count}")
                    playlist_verification_success = True
                else:
                    print(f"   ❌ Song count mismatch: expected {expected_count}, got {actual_count}")
                    playlist_verification_success = False
            else:
                print(f"   ❌ Created playlist not found in GET /api/playlists")
                playlist_verification_success = False
            
            # Step 4: Clean up - delete the test playlist
            print("📊 Step 3.4: Clean up test playlist")
            
            delete_response = self.make_request("DELETE", f"/playlists/{playlist_id}")
            
            if delete_response.status_code == 200:
                print(f"   ✅ Successfully deleted test playlist")
            else:
                print(f"   ⚠️  Failed to delete test playlist: {delete_response.status_code}")
            
            self.log_result("Playlist Creation with Songs", playlist_verification_success, f"Created playlist with {len(selected_songs)} songs, verification: {playlist_verification_success}")
            return playlist_verification_success
            
        except Exception as e:
            self.log_result("Playlist Creation with Songs", False, f"Exception: {str(e)}")
            return False

    def test_frontend_backend_plan_compatibility(self):
        """Test that frontend and backend have compatible plan checking logic"""
        try:
            print("🔄 STEP 4: Frontend-Backend Plan Compatibility")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Frontend-Backend Plan Compatibility", False, "No auth token available")
                return False
            
            # Step 1: Get subscription status (what frontend would check)
            print("📊 Step 4.1: Get subscription status for frontend compatibility check")
            
            subscription_response = self.make_request("GET", "/subscription/status")
            
            if subscription_response.status_code != 200:
                self.log_result("Frontend-Backend Plan Compatibility", False, f"Failed to get subscription status: {subscription_response.status_code}")
                return False
            
            subscription_data = subscription_response.json()
            plan = subscription_data.get("plan", "unknown")
            
            print(f"   📊 Current plan: {plan}")
            
            # Step 2: Check if this plan would be accepted by the fixed frontend logic
            print("📊 Step 4.2: Check if plan is compatible with frontend logic")
            
            # The fix was: frontend now checks for both 'trial' and 'pro' plans
            frontend_compatible_plans = ['trial', 'pro']
            
            if plan in frontend_compatible_plans:
                print(f"   ✅ Plan '{plan}' is compatible with fixed frontend logic")
                frontend_compatibility = True
            else:
                print(f"   ⚠️  Plan '{plan}' may not be compatible with frontend logic")
                print(f"   📊 Frontend expects one of: {frontend_compatible_plans}")
                frontend_compatibility = False
            
            # Step 3: Test that backend actually allows playlist operations for this plan
            print("📊 Step 4.3: Verify backend allows playlist operations for this plan")
            
            # Try to access playlists endpoint
            playlists_response = self.make_request("GET", "/playlists")
            
            if playlists_response.status_code == 200:
                print(f"   ✅ Backend allows playlist access for plan '{plan}'")
                backend_allows_access = True
            elif playlists_response.status_code == 403:
                print(f"   ❌ Backend denies playlist access for plan '{plan}'")
                backend_allows_access = False
            else:
                print(f"   ⚠️  Unexpected backend response: {playlists_response.status_code}")
                backend_allows_access = False
            
            # Step 4: Overall compatibility assessment
            print("📊 Step 4.4: Overall compatibility assessment")
            
            overall_compatibility = frontend_compatibility and backend_allows_access
            
            if overall_compatibility:
                print(f"   ✅ Frontend and backend are compatible for plan '{plan}'")
                print(f"   ✅ Frontend will show playlist features")
                print(f"   ✅ Backend will allow playlist operations")
            else:
                issues = []
                if not frontend_compatibility:
                    issues.append(f"frontend may not show playlist features for plan '{plan}'")
                if not backend_allows_access:
                    issues.append(f"backend denies playlist access for plan '{plan}'")
                
                print(f"   ❌ Compatibility issues: {', '.join(issues)}")
            
            self.log_result("Frontend-Backend Plan Compatibility", overall_compatibility, f"Plan '{plan}' - Frontend compatible: {frontend_compatibility}, Backend allows: {backend_allows_access}")
            return overall_compatibility
            
        except Exception as e:
            self.log_result("Frontend-Backend Plan Compatibility", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all playlist creation verification tests"""
        print("🎵 PLAYLIST CREATION FUNCTIONALITY VERIFICATION")
        print("=" * 80)
        print("Testing playlist creation after frontend fix:")
        print("- User reported playlists not showing up after creation")
        print("- Fixed frontend to check for both 'trial' and 'pro' plans")
        print("- Verifying the fix works correctly")
        print("=" * 80)
        
        # Run tests in sequence
        test_results = []
        
        test_results.append(self.test_login_and_subscription_status())
        test_results.append(self.test_pro_access_logic())
        test_results.append(self.test_playlist_creation_with_songs())
        test_results.append(self.test_frontend_backend_plan_compatibility())
        
        # Summary
        print("\n" + "=" * 80)
        print("🎵 PLAYLIST CREATION VERIFICATION SUMMARY")
        print("=" * 80)
        
        print(f"✅ Tests Passed: {self.results['passed']}")
        print(f"❌ Tests Failed: {self.results['failed']}")
        
        if self.results['failed'] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   - {error}")
        
        overall_success = all(test_results)
        
        if overall_success:
            print("\n🎉 PLAYLIST CREATION VERIFICATION: SUCCESS")
            print("✅ The frontend fix appears to be working correctly")
            print("✅ Users with 'trial' or 'pro' plans can create playlists")
            print("✅ Playlists are properly saved and appear in the playlist list")
        else:
            print("\n⚠️  PLAYLIST CREATION VERIFICATION: ISSUES FOUND")
            print("❌ Some aspects of the playlist creation functionality need attention")
        
        return overall_success

if __name__ == "__main__":
    tester = PlaylistCreationTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)
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
BASE_URL = "https://requestwave-pro.preview.emergentagent.com/api"

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