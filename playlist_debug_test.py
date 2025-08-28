#!/usr/bin/env python3
"""
PLAYLIST CREATION DEBUG TEST
Debug the playlist creation error for Pro account: brycelarsenmusic@gmail.com
"""

import requests
import json
import os
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://stagepro-app.preview.emergentagent.com/api"

# Pro account credentials
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class PlaylistDebugTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
        self.test_song_ids = []

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
            print(f"❌ Request failed: {e}")
            raise

    def debug_login_pro_account(self):
        """Step 1: Login with Pro account"""
        print("🔍 STEP 1: Login with Pro account")
        print(f"   Email: {PRO_MUSICIAN['email']}")
        
        try:
            response = self.make_request("POST", "/auth/login", PRO_MUSICIAN)
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data["token"]
                self.musician_id = data["musician"]["id"]
                self.musician_slug = data["musician"]["slug"]
                print(f"   ✅ Login successful")
                print(f"   Musician ID: {self.musician_id}")
                print(f"   Musician Slug: {self.musician_slug}")
                return True
            else:
                print(f"   ❌ Login failed: {response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Login exception: {str(e)}")
            return False

    def debug_pro_access_verification(self):
        """Step 2: Verify Pro access is working"""
        print("\n🔍 STEP 2: Verify Pro access is working")
        
        try:
            # Check subscription status
            response = self.make_request("GET", "/subscription/status")
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Subscription status retrieved")
                print(f"   Plan: {data.get('plan', 'unknown')}")
                print(f"   Can make request: {data.get('can_make_request', 'unknown')}")
                print(f"   Full response: {json.dumps(data, indent=4, default=str)}")
                
                # Check if user has Pro access
                plan = data.get('plan', '')
                if plan in ['trial', 'pro']:
                    print(f"   ✅ User has Pro access (plan: {plan})")
                    return True
                else:
                    print(f"   ❌ User does NOT have Pro access (plan: {plan})")
                    return False
            else:
                print(f"   ❌ Failed to get subscription status: {response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Pro access verification exception: {str(e)}")
            return False

    def debug_create_test_songs(self):
        """Step 3: Create some test songs for playlist"""
        print("\n🔍 STEP 3: Create test songs for playlist")
        
        test_songs = [
            {
                "title": "Test Song 1",
                "artist": "Test Artist 1",
                "genres": ["Pop"],
                "moods": ["Upbeat"],
                "year": 2023,
                "notes": "Test song for playlist"
            },
            {
                "title": "Test Song 2", 
                "artist": "Test Artist 2",
                "genres": ["Rock"],
                "moods": ["Energetic"],
                "year": 2022,
                "notes": "Another test song for playlist"
            }
        ]
        
        for i, song_data in enumerate(test_songs):
            try:
                response = self.make_request("POST", "/songs", song_data)
                
                print(f"   Song {i+1} Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    song_id = data["id"]
                    self.test_song_ids.append(song_id)
                    print(f"   ✅ Created song: '{song_data['title']}' (ID: {song_id})")
                else:
                    print(f"   ❌ Failed to create song {i+1}: {response.text}")
            except Exception as e:
                print(f"   ❌ Exception creating song {i+1}: {str(e)}")
        
        print(f"   Created {len(self.test_song_ids)} test songs")
        return len(self.test_song_ids) > 0

    def debug_playlist_creation_empty(self):
        """Step 4: Test playlist creation with empty song list"""
        print("\n🔍 STEP 4: Test playlist creation with empty song list")
        
        playlist_data = {
            "name": "Debug Test Playlist (Empty)",
            "song_ids": []
        }
        
        try:
            response = self.make_request("POST", "/playlists", playlist_data)
            
            print(f"   Status Code: {response.status_code}")
            print(f"   Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Empty playlist created successfully")
                print(f"   Response: {json.dumps(data, indent=4, default=str)}")
                return True
            else:
                print(f"   ❌ EXACT ERROR RESPONSE:")
                print(f"   Status: {response.status_code}")
                print(f"   Headers: {dict(response.headers)}")
                print(f"   Body: {response.text}")
                
                # Try to parse as JSON for better formatting
                try:
                    error_data = response.json()
                    print(f"   JSON Error: {json.dumps(error_data, indent=4)}")
                except:
                    print(f"   Raw Error: {response.text}")
                
                return False
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
            return False

    def debug_playlist_creation_with_songs(self):
        """Step 5: Test playlist creation with song IDs"""
        print("\n🔍 STEP 5: Test playlist creation with song IDs")
        
        if not self.test_song_ids:
            print("   ⚠️ No test songs available, skipping this test")
            return False
        
        playlist_data = {
            "name": "Debug Test Playlist (With Songs)",
            "song_ids": self.test_song_ids
        }
        
        try:
            response = self.make_request("POST", "/playlists", playlist_data)
            
            print(f"   Status Code: {response.status_code}")
            print(f"   Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Playlist with songs created successfully")
                print(f"   Response: {json.dumps(data, indent=4, default=str)}")
                return True
            else:
                print(f"   ❌ EXACT ERROR RESPONSE:")
                print(f"   Status: {response.status_code}")
                print(f"   Headers: {dict(response.headers)}")
                print(f"   Body: {response.text}")
                
                # Try to parse as JSON for better formatting
                try:
                    error_data = response.json()
                    print(f"   JSON Error: {json.dumps(error_data, indent=4)}")
                except:
                    print(f"   Raw Error: {response.text}")
                
                return False
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
            return False

    def debug_playlist_endpoint_exists(self):
        """Step 6: Check if playlist endpoint exists"""
        print("\n🔍 STEP 6: Check if playlist endpoint exists")
        
        try:
            # Try GET /playlists to see if endpoint exists
            response = self.make_request("GET", "/playlists")
            
            print(f"   GET /playlists Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Playlist endpoint exists and returns data")
                print(f"   Response: {json.dumps(data, indent=4, default=str)}")
                return True
            elif response.status_code == 404:
                print(f"   ❌ Playlist endpoint does NOT exist (404)")
                return False
            elif response.status_code in [401, 403]:
                print(f"   ✅ Playlist endpoint exists but requires auth (status: {response.status_code})")
                return True
            else:
                print(f"   ⚠️ Playlist endpoint exists but returned: {response.status_code}")
                print(f"   Response: {response.text}")
                return True
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
            return False

    def debug_check_server_logs(self):
        """Step 7: Additional debugging info"""
        print("\n🔍 STEP 7: Additional debugging info")
        
        print(f"   Base URL: {self.base_url}")
        print(f"   Auth Token Present: {bool(self.auth_token)}")
        print(f"   Auth Token (first 20 chars): {self.auth_token[:20] if self.auth_token else 'None'}...")
        print(f"   Musician ID: {self.musician_id}")
        print(f"   Test Song IDs: {self.test_song_ids}")

    def run_debug_tests(self):
        """Run all debug tests"""
        print("=" * 80)
        print("PLAYLIST CREATION DEBUG TEST")
        print("=" * 80)
        
        # Step 1: Login
        if not self.debug_login_pro_account():
            print("\n❌ CRITICAL: Cannot proceed without login")
            return
        
        # Step 2: Verify Pro access
        if not self.debug_pro_access_verification():
            print("\n⚠️ WARNING: User may not have Pro access")
        
        # Step 3: Create test songs
        self.debug_create_test_songs()
        
        # Step 4: Check if endpoint exists
        self.debug_playlist_endpoint_exists()
        
        # Step 5: Test empty playlist creation
        empty_result = self.debug_playlist_creation_empty()
        
        # Step 6: Test playlist creation with songs
        songs_result = self.debug_playlist_creation_with_songs()
        
        # Step 7: Additional debugging
        self.debug_check_server_logs()
        
        # Summary
        print("\n" + "=" * 80)
        print("DEBUG SUMMARY")
        print("=" * 80)
        print(f"✅ Login successful: Yes")
        print(f"✅ Pro access verified: {self.debug_pro_access_verification()}")
        print(f"✅ Test songs created: {len(self.test_song_ids)}")
        print(f"❌ Empty playlist creation: {'Success' if empty_result else 'FAILED'}")
        print(f"❌ Playlist with songs creation: {'Success' if songs_result else 'FAILED'}")
        
        if not empty_result and not songs_result:
            print("\n🚨 CRITICAL ISSUE: Both playlist creation attempts failed")
            print("   This confirms the user's report of 'error creating playlist'")
        elif empty_result and not songs_result:
            print("\n⚠️ PARTIAL ISSUE: Empty playlists work, but playlists with songs fail")
        elif not empty_result and songs_result:
            print("\n⚠️ PARTIAL ISSUE: Playlists with songs work, but empty playlists fail")
        else:
            print("\n✅ SUCCESS: Both playlist creation methods work")

if __name__ == "__main__":
    tester = PlaylistDebugTester()
    tester.run_debug_tests()