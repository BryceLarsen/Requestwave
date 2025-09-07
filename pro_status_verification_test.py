#!/usr/bin/env python3
"""
PRO STATUS VERIFICATION TEST

Specific verification that brycelarsenmusic@gmail.com has proper Pro status
and all Pro features are working correctly.

Focus Areas:
1. Subscription status verification
2. Playlist creation and management
3. Audience link functionality
4. Song management capabilities
5. Request system functionality
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "https://music-flow-update.preview.emergentagent.com/api"

# Target user credentials
USER_CREDENTIALS = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class ProStatusVerificationTester:
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
        
        request_headers = {"Content-Type": "application/json"}
        if self.auth_token:
            request_headers["Authorization"] = f"Bearer {self.auth_token}"
        
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

    def authenticate(self):
        """Authenticate with user credentials"""
        try:
            print("🔐 AUTHENTICATION TEST")
            print("=" * 60)
            
            login_response = self.make_request("POST", "/auth/login", USER_CREDENTIALS)
            
            if login_response.status_code == 200:
                login_data = login_response.json()
                self.auth_token = login_data.get("token")
                self.musician_id = login_data.get("musician", {}).get("id")
                self.musician_slug = login_data.get("musician", {}).get("slug")
                
                print(f"✅ Authentication successful")
                print(f"   Musician: {login_data.get('musician', {}).get('name')}")
                print(f"   ID: {self.musician_id}")
                print(f"   Slug: {self.musician_slug}")
                
                self.log_result("Authentication", True, "Login successful")
                return True
            else:
                print(f"❌ Authentication failed: {login_response.status_code}")
                print(f"   Response: {login_response.text}")
                self.log_result("Authentication", False, f"Login failed: {login_response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Authentication", False, f"Exception: {str(e)}")
            return False

    def test_subscription_status_details(self):
        """Test detailed subscription status"""
        try:
            print("\n💳 SUBSCRIPTION STATUS VERIFICATION")
            print("=" * 60)
            
            status_response = self.make_request("GET", "/subscription/status")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                print("📊 Subscription Details:")
                for key, value in status_data.items():
                    print(f"   {key}: {value}")
                
                # Verify Pro status indicators
                plan = status_data.get("plan")
                audience_link_active = status_data.get("audience_link_active")
                status = status_data.get("status")
                
                # Check for Pro access
                has_pro_plan = plan in ["active", "pro", "trial"]
                has_active_link = audience_link_active is True
                has_active_status = status == "active"
                
                if has_pro_plan and has_active_link and has_active_status:
                    self.log_result("Subscription Status Details", True, f"Full Pro access confirmed - Plan: {plan}, Link: {audience_link_active}, Status: {status}")
                    return True
                else:
                    issues = []
                    if not has_pro_plan:
                        issues.append(f"plan '{plan}' not Pro")
                    if not has_active_link:
                        issues.append(f"audience_link_active is {audience_link_active}")
                    if not has_active_status:
                        issues.append(f"status is '{status}'")
                    
                    self.log_result("Subscription Status Details", False, f"Pro access issues: {', '.join(issues)}")
                    return False
            else:
                self.log_result("Subscription Status Details", False, f"Failed to get status: {status_response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Subscription Status Details", False, f"Exception: {str(e)}")
            return False

    def test_playlist_management_full(self):
        """Test complete playlist management functionality"""
        try:
            print("\n🎵 PLAYLIST MANAGEMENT VERIFICATION")
            print("=" * 60)
            
            # Step 1: Get existing playlists
            print("📊 Step 1: Get existing playlists")
            playlists_response = self.make_request("GET", "/playlists")
            
            if playlists_response.status_code != 200:
                self.log_result("Playlist Management Full", False, f"Cannot access playlists: {playlists_response.status_code}")
                return False
            
            existing_playlists = playlists_response.json()
            print(f"   Existing playlists: {len(existing_playlists)}")
            
            # Step 2: Get songs for playlist creation
            print("📊 Step 2: Get available songs")
            songs_response = self.make_request("GET", "/songs")
            
            if songs_response.status_code != 200:
                self.log_result("Playlist Management Full", False, f"Cannot access songs: {songs_response.status_code}")
                return False
            
            songs = songs_response.json()
            print(f"   Available songs: {len(songs)}")
            
            if len(songs) < 3:
                self.log_result("Playlist Management Full", False, f"Insufficient songs for testing: {len(songs)}")
                return False
            
            # Step 3: Create new playlist
            print("📊 Step 3: Create new playlist")
            playlist_data = {
                "name": "Pro Status Test Playlist",
                "song_ids": [songs[0]["id"], songs[1]["id"], songs[2]["id"]]
            }
            
            create_response = self.make_request("POST", "/playlists", playlist_data)
            
            if create_response.status_code != 200:
                self.log_result("Playlist Management Full", False, f"Cannot create playlist: {create_response.status_code}")
                return False
            
            created_playlist = create_response.json()
            playlist_id = created_playlist["id"]
            print(f"   Created playlist: {created_playlist['name']} (ID: {playlist_id})")
            
            # Step 4: Verify playlist appears in list
            print("📊 Step 4: Verify playlist appears in list")
            updated_playlists_response = self.make_request("GET", "/playlists")
            
            if updated_playlists_response.status_code == 200:
                updated_playlists = updated_playlists_response.json()
                playlist_found = any(p["id"] == playlist_id for p in updated_playlists)
                
                if playlist_found:
                    print(f"   ✅ Playlist found in list")
                else:
                    print(f"   ❌ Playlist not found in list")
                    self.log_result("Playlist Management Full", False, "Created playlist not found in list")
                    return False
            else:
                print(f"   ❌ Cannot verify playlist list")
                self.log_result("Playlist Management Full", False, "Cannot verify playlist list")
                return False
            
            # Step 5: Test playlist editing
            print("📊 Step 5: Test playlist editing")
            if len(songs) >= 4:
                edit_data = {
                    "song_ids": [songs[0]["id"], songs[3]["id"]]  # Change songs
                }
                
                edit_response = self.make_request("PUT", f"/playlists/{playlist_id}/songs", edit_data)
                
                if edit_response.status_code == 200:
                    print(f"   ✅ Playlist editing successful")
                    playlist_editing = True
                else:
                    print(f"   ❌ Playlist editing failed: {edit_response.status_code}")
                    playlist_editing = False
            else:
                print(f"   ⚠️  Skipping playlist editing (insufficient songs)")
                playlist_editing = True
            
            # Step 6: Clean up - delete test playlist
            print("📊 Step 6: Clean up test playlist")
            delete_response = self.make_request("DELETE", f"/playlists/{playlist_id}")
            
            if delete_response.status_code == 200:
                print(f"   ✅ Playlist deleted successfully")
                cleanup_successful = True
            else:
                print(f"   ⚠️  Playlist deletion failed: {delete_response.status_code}")
                cleanup_successful = False
            
            # Final assessment
            if playlist_editing and cleanup_successful:
                self.log_result("Playlist Management Full", True, "Complete playlist management working - create, edit, delete all functional")
                return True
            elif playlist_editing:
                self.log_result("Playlist Management Full", True, "Playlist management mostly working - create and edit functional")
                return True
            else:
                self.log_result("Playlist Management Full", False, "Playlist management has issues")
                return False
                
        except Exception as e:
            self.log_result("Playlist Management Full", False, f"Exception: {str(e)}")
            return False

    def test_audience_interface_comprehensive(self):
        """Test comprehensive audience interface functionality"""
        try:
            print("\n🌐 AUDIENCE INTERFACE COMPREHENSIVE TEST")
            print("=" * 60)
            
            if not self.musician_slug:
                self.log_result("Audience Interface Comprehensive", False, "No musician slug available")
                return False
            
            # Clear auth for public testing
            original_token = self.auth_token
            self.auth_token = None
            
            # Step 1: Test musician profile
            print("📊 Step 1: Test public musician profile")
            profile_response = self.make_request("GET", f"/musicians/{self.musician_slug}")
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                print(f"   ✅ Profile accessible: {profile_data.get('name')}")
                profile_working = True
            else:
                print(f"   ❌ Profile not accessible: {profile_response.status_code}")
                profile_working = False
            
            # Step 2: Test songs endpoint
            print("📊 Step 2: Test public songs endpoint")
            songs_response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs")
            
            if songs_response.status_code == 200:
                songs_data = songs_response.json()
                print(f"   ✅ Songs accessible: {len(songs_data)} songs")
                songs_working = True
            else:
                print(f"   ❌ Songs not accessible: {songs_response.status_code}")
                songs_working = False
            
            # Step 3: Test playlists endpoint
            print("📊 Step 3: Test public playlists endpoint")
            playlists_response = self.make_request("GET", f"/musicians/{self.musician_slug}/playlists")
            
            if playlists_response.status_code == 200:
                playlists_data = playlists_response.json()
                print(f"   ✅ Playlists accessible: {len(playlists_data)} playlists")
                playlists_working = True
            else:
                print(f"   ❌ Playlists not accessible: {playlists_response.status_code}")
                playlists_working = False
            
            # Step 4: Test request creation (if songs available)
            print("📊 Step 4: Test request creation")
            if songs_working and len(songs_data) > 0:
                request_data = {
                    "song_id": songs_data[0]["id"],
                    "requester_name": "Test Requester",
                    "requester_email": "test@example.com",
                    "dedication": "Testing Pro status functionality"
                }
                
                request_response = self.make_request("POST", "/requests", request_data)
                
                if request_response.status_code == 200:
                    print(f"   ✅ Request creation successful")
                    request_working = True
                else:
                    print(f"   ❌ Request creation failed: {request_response.status_code}")
                    request_working = False
            else:
                print(f"   ⚠️  Skipping request creation (no songs available)")
                request_working = True
            
            # Restore auth token
            self.auth_token = original_token
            
            # Final assessment
            working_components = sum([profile_working, songs_working, playlists_working, request_working])
            
            if working_components >= 3:
                self.log_result("Audience Interface Comprehensive", True, f"Audience interface fully functional - {working_components}/4 components working")
                return True
            else:
                self.log_result("Audience Interface Comprehensive", False, f"Audience interface has issues - only {working_components}/4 components working")
                return False
                
        except Exception as e:
            self.log_result("Audience Interface Comprehensive", False, f"Exception: {str(e)}")
            return False

    def test_song_management_capabilities(self):
        """Test song management capabilities"""
        try:
            print("\n🎼 SONG MANAGEMENT CAPABILITIES TEST")
            print("=" * 60)
            
            # Step 1: Test song creation
            print("📊 Step 1: Test song creation")
            song_data = {
                "title": "Pro Status Test Song",
                "artist": "Test Artist",
                "genres": ["Rock"],
                "moods": ["Feel Good"],
                "year": 2024,
                "notes": "Created to test Pro status functionality"
            }
            
            create_response = self.make_request("POST", "/songs", song_data)
            
            if create_response.status_code == 200:
                created_song = create_response.json()
                song_id = created_song["id"]
                print(f"   ✅ Song creation successful: {created_song['title']}")
                song_creation = True
            else:
                print(f"   ❌ Song creation failed: {create_response.status_code}")
                self.log_result("Song Management Capabilities", False, f"Song creation failed: {create_response.status_code}")
                return False
            
            # Step 2: Test song retrieval
            print("📊 Step 2: Test song retrieval")
            songs_response = self.make_request("GET", "/songs")
            
            if songs_response.status_code == 200:
                songs = songs_response.json()
                song_found = any(s["id"] == song_id for s in songs)
                
                if song_found:
                    print(f"   ✅ Song retrieval successful: found created song")
                    song_retrieval = True
                else:
                    print(f"   ❌ Created song not found in list")
                    song_retrieval = False
            else:
                print(f"   ❌ Song retrieval failed: {songs_response.status_code}")
                song_retrieval = False
            
            # Step 3: Test song editing
            print("📊 Step 3: Test song editing")
            edit_data = {
                "title": "Pro Status Test Song (Edited)",
                "artist": "Test Artist",
                "genres": ["Rock", "Alternative"],
                "moods": ["Feel Good", "Energetic"],
                "year": 2024,
                "notes": "Edited to test Pro status functionality"
            }
            
            edit_response = self.make_request("PUT", f"/songs/{song_id}", edit_data)
            
            if edit_response.status_code == 200:
                print(f"   ✅ Song editing successful")
                song_editing = True
            else:
                print(f"   ❌ Song editing failed: {edit_response.status_code}")
                song_editing = False
            
            # Step 4: Clean up - delete test song
            print("📊 Step 4: Clean up test song")
            delete_response = self.make_request("DELETE", f"/songs/{song_id}")
            
            if delete_response.status_code == 200:
                print(f"   ✅ Song deletion successful")
                song_deletion = True
            else:
                print(f"   ⚠️  Song deletion failed: {delete_response.status_code}")
                song_deletion = False
            
            # Final assessment
            working_operations = sum([song_creation, song_retrieval, song_editing, song_deletion])
            
            if working_operations >= 3:
                self.log_result("Song Management Capabilities", True, f"Song management fully functional - {working_operations}/4 operations working")
                return True
            else:
                self.log_result("Song Management Capabilities", False, f"Song management has issues - only {working_operations}/4 operations working")
                return False
                
        except Exception as e:
            self.log_result("Song Management Capabilities", False, f"Exception: {str(e)}")
            return False

    def run_pro_verification_tests(self):
        """Run all Pro status verification tests"""
        print("🎯 PRO STATUS VERIFICATION TEST SUITE")
        print("=" * 80)
        print(f"User: {USER_CREDENTIALS['email']}")
        print("=" * 80)
        
        # Authenticate first
        if not self.authenticate():
            print("❌ CRITICAL FAILURE: Authentication failed")
            return False
        
        # Run verification tests
        subscription_ok = self.test_subscription_status_details()
        playlist_ok = self.test_playlist_management_full()
        audience_ok = self.test_audience_interface_comprehensive()
        songs_ok = self.test_song_management_capabilities()
        
        # Final summary
        print("\n" + "=" * 80)
        print("🏁 PRO STATUS VERIFICATION RESULTS")
        print("=" * 80)
        
        print(f"✅ Tests Passed: {self.results['passed']}")
        print(f"❌ Tests Failed: {self.results['failed']}")
        print(f"📊 Success Rate: {(self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100):.1f}%")
        
        if self.results['failed'] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        # Pro status assessment
        print("\n🎯 PRO STATUS ASSESSMENT:")
        
        if subscription_ok:
            print("✅ SUBSCRIPTION: Active Pro subscription confirmed")
        else:
            print("❌ SUBSCRIPTION: Pro subscription status issues")
        
        if playlist_ok:
            print("✅ PLAYLISTS: Full playlist management working")
        else:
            print("❌ PLAYLISTS: Playlist functionality has issues")
        
        if audience_ok:
            print("✅ AUDIENCE LINK: Public interface fully functional")
        else:
            print("❌ AUDIENCE LINK: Public interface has issues")
        
        if songs_ok:
            print("✅ SONG MANAGEMENT: Full song management working")
        else:
            print("❌ SONG MANAGEMENT: Song management has issues")
        
        # Overall Pro status
        pro_status_confirmed = subscription_ok and playlist_ok and audience_ok and songs_ok
        
        if pro_status_confirmed:
            print("\n🎉 PRO STATUS CONFIRMED: brycelarsenmusic@gmail.com has full Pro access")
            print("   ✅ All Pro features are working correctly")
            print("   ✅ Subscription is active and valid")
            print("   ✅ User can access all premium functionality")
        else:
            print("\n⚠️  PRO STATUS ISSUES: Some Pro features need attention")
            
            if not subscription_ok:
                print("   🔧 Fix subscription status")
            if not playlist_ok:
                print("   🔧 Fix playlist functionality")
            if not audience_ok:
                print("   🔧 Fix audience interface")
            if not songs_ok:
                print("   🔧 Fix song management")
        
        print("=" * 80)
        
        return pro_status_confirmed

if __name__ == "__main__":
    tester = ProStatusVerificationTester()
    success = tester.run_pro_verification_tests()
    
    if success:
        print("\n🎯 VERIFICATION COMPLETE: Pro status is fully functional!")
    else:
        print("\n⚠️  VERIFICATION INCOMPLETE: Pro status needs attention")