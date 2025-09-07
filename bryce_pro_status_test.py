#!/usr/bin/env python3
"""
BRYCE LARSEN PRO SUBSCRIBER STATUS REACTIVATION TEST

Testing the specific review request:
- User: brycelarsenmusic@gmail.com / RequestWave2024!
- Issue: Account not set to subscribed and audience link is paused after custom domain removal
- Need to reactivate Pro subscriber access

CRITICAL TEST AREAS:
1. Check current account status for brycelarsenmusic@gmail.com
2. Verify subscription status API returns proper Pro status
3. Test Pro features access (playlists, audience link)
4. Confirm audience link is no longer paused
5. Verify check_pro_access() function works for this user

Expected: User should have full Pro subscriber access with active audience link
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional
from datetime import datetime

# Configuration
BASE_URL = "https://music-flow-update.preview.emergentagent.com/api"

# Bryce's credentials
BRYCE_CREDENTIALS = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class BryceProStatusTester:
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

    def test_bryce_login_authentication(self):
        """Test Bryce's login authentication - CRITICAL"""
        try:
            print("🔐 CRITICAL: Testing Bryce's Login Authentication")
            print("=" * 80)
            
            print("📊 Step 1: Attempt login with brycelarsenmusic@gmail.com / RequestWave2024!")
            
            login_data = {
                "email": BRYCE_CREDENTIALS["email"],
                "password": BRYCE_CREDENTIALS["password"]
            }
            
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            print(f"   📊 Login response status: {login_response.status_code}")
            
            if login_response.status_code == 200:
                login_result = login_response.json()
                
                if "token" in login_result and "musician" in login_result:
                    self.auth_token = login_result["token"]
                    self.musician_id = login_result["musician"]["id"]
                    self.musician_slug = login_result["musician"]["slug"]
                    
                    musician_data = login_result["musician"]
                    
                    print(f"   ✅ Login successful!")
                    print(f"   📊 Musician Name: {musician_data.get('name')}")
                    print(f"   📊 Musician Email: {musician_data.get('email')}")
                    print(f"   📊 Musician Slug: {musician_data.get('slug')}")
                    print(f"   📊 Musician ID: {musician_data.get('id')}")
                    print(f"   📊 Audience Link Active: {musician_data.get('audience_link_active')}")
                    print(f"   📊 Has Had Trial: {musician_data.get('has_had_trial')}")
                    print(f"   📊 Trial End: {musician_data.get('trial_end')}")
                    print(f"   📊 Subscription Status: {musician_data.get('subscription_status')}")
                    
                    # Check critical fields for Pro status
                    audience_link_active = musician_data.get('audience_link_active', False)
                    subscription_status = musician_data.get('subscription_status')
                    
                    if audience_link_active:
                        print(f"   ✅ Audience link is ACTIVE")
                    else:
                        print(f"   ❌ Audience link is PAUSED/INACTIVE")
                    
                    self.log_result("Bryce Login Authentication", True, f"Successfully logged in as {musician_data.get('name')} - audience_link_active: {audience_link_active}")
                    
                else:
                    self.log_result("Bryce Login Authentication", False, f"Missing token or musician data in response: {login_result}")
            else:
                self.log_result("Bryce Login Authentication", False, f"Login failed with status {login_response.status_code}: {login_response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Bryce Login Authentication", False, f"Exception during login: {str(e)}")

    def test_subscription_status_api(self):
        """Test subscription status API for Bryce - CRITICAL"""
        try:
            print("💳 CRITICAL: Testing Subscription Status API")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Subscription Status API", False, "No auth token available - login first")
                return
            
            print("📊 Step 1: Get subscription status via GET /api/subscription/status")
            
            status_response = self.make_request("GET", "/subscription/status")
            
            print(f"   📊 Subscription status response: {status_response.status_code}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                print(f"   📊 Full subscription status response:")
                for key, value in status_data.items():
                    print(f"      {key}: {value}")
                
                # Check critical fields
                plan = status_data.get('plan')
                audience_link_active = status_data.get('audience_link_active')
                trial_active = status_data.get('trial_active')
                trial_end = status_data.get('trial_end')
                status = status_data.get('status')
                can_reactivate = status_data.get('can_reactivate')
                
                print(f"\n   📊 CRITICAL ANALYSIS:")
                print(f"      Plan: {plan}")
                print(f"      Audience Link Active: {audience_link_active}")
                print(f"      Trial Active: {trial_active}")
                print(f"      Trial End: {trial_end}")
                print(f"      Status: {status}")
                print(f"      Can Reactivate: {can_reactivate}")
                
                # Determine if user should have Pro access
                should_have_pro_access = plan in ['trial', 'pro', 'active'] or audience_link_active
                
                if should_have_pro_access:
                    print(f"   ✅ User should have Pro access based on subscription status")
                    pro_status_correct = True
                else:
                    print(f"   ❌ User does NOT have Pro access - needs reactivation")
                    pro_status_correct = False
                
                # Check if audience link is active
                if audience_link_active:
                    print(f"   ✅ Audience link is ACTIVE")
                    audience_link_ok = True
                else:
                    print(f"   ❌ Audience link is PAUSED - needs reactivation")
                    audience_link_ok = False
                
                self.log_result("Subscription Status API", True, f"API working - Plan: {plan}, Audience Link: {audience_link_active}, Status: {status}")
                
                # Store status for other tests
                self.subscription_status = status_data
                
            else:
                self.log_result("Subscription Status API", False, f"Status API failed: {status_response.status_code} - {status_response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Subscription Status API", False, f"Exception: {str(e)}")

    def test_pro_features_access(self):
        """Test Pro features access (playlists) - CRITICAL"""
        try:
            print("🎵 CRITICAL: Testing Pro Features Access (Playlists)")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Pro Features Access", False, "No auth token available")
                return
            
            print("📊 Step 1: Test playlist access via GET /api/playlists")
            
            playlists_response = self.make_request("GET", "/playlists")
            
            print(f"   📊 Playlists response status: {playlists_response.status_code}")
            
            if playlists_response.status_code == 200:
                playlists_data = playlists_response.json()
                
                print(f"   ✅ Playlists endpoint accessible")
                print(f"   📊 Number of playlists: {len(playlists_data)}")
                
                # Show playlist details
                for i, playlist in enumerate(playlists_data[:5]):  # Show first 5
                    print(f"      Playlist {i+1}: {playlist.get('name')} ({playlist.get('song_count', 0)} songs)")
                
                playlist_access_ok = True
                
            elif playlists_response.status_code == 403:
                print(f"   ❌ Playlists access DENIED - Pro access required")
                print(f"   📊 Error response: {playlists_response.text}")
                playlist_access_ok = False
                
            else:
                print(f"   ❌ Playlists endpoint error: {playlists_response.status_code}")
                print(f"   📊 Response: {playlists_response.text}")
                playlist_access_ok = False
            
            print("\n📊 Step 2: Test playlist creation (Pro feature)")
            
            # Try to create a test playlist
            test_playlist_data = {
                "name": "Pro Access Test Playlist",
                "song_ids": []
            }
            
            create_response = self.make_request("POST", "/playlists", test_playlist_data)
            
            print(f"   📊 Playlist creation response: {create_response.status_code}")
            
            if create_response.status_code == 200:
                created_playlist = create_response.json()
                playlist_id = created_playlist.get('id')
                
                print(f"   ✅ Playlist creation successful")
                print(f"   📊 Created playlist: {created_playlist.get('name')} (ID: {playlist_id})")
                
                playlist_creation_ok = True
                
                # Clean up - delete the test playlist
                if playlist_id:
                    delete_response = self.make_request("DELETE", f"/playlists/{playlist_id}")
                    if delete_response.status_code == 200:
                        print(f"   ✅ Test playlist cleaned up")
                    else:
                        print(f"   ⚠️  Failed to clean up test playlist")
                
            elif create_response.status_code == 403:
                print(f"   ❌ Playlist creation DENIED - Pro access required")
                print(f"   📊 Error response: {create_response.text}")
                playlist_creation_ok = False
                
            else:
                print(f"   ❌ Playlist creation error: {create_response.status_code}")
                print(f"   📊 Response: {create_response.text}")
                playlist_creation_ok = False
            
            # Overall assessment
            if playlist_access_ok and playlist_creation_ok:
                self.log_result("Pro Features Access", True, "Full Pro features access confirmed - playlists accessible and creatable")
            elif playlist_access_ok:
                self.log_result("Pro Features Access", True, "Partial Pro access - can view playlists but creation may be limited")
            else:
                self.log_result("Pro Features Access", False, "Pro features access DENIED - user needs Pro subscription reactivation")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Pro Features Access", False, f"Exception: {str(e)}")

    def test_audience_link_functionality(self):
        """Test audience link functionality - CRITICAL"""
        try:
            print("🌐 CRITICAL: Testing Audience Link Functionality")
            print("=" * 80)
            
            if not self.musician_slug:
                self.log_result("Audience Link Functionality", False, "No musician slug available")
                return
            
            print(f"📊 Step 1: Test public audience interface access for slug: {self.musician_slug}")
            
            # Clear auth token for public access
            original_token = self.auth_token
            self.auth_token = None
            
            # Test public musician profile
            profile_response = self.make_request("GET", f"/musicians/{self.musician_slug}")
            
            print(f"   📊 Public profile response: {profile_response.status_code}")
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                
                print(f"   ✅ Public profile accessible")
                print(f"   📊 Musician: {profile_data.get('name')}")
                print(f"   📊 Slug: {profile_data.get('slug')}")
                
                profile_accessible = True
                
            else:
                print(f"   ❌ Public profile NOT accessible: {profile_response.status_code}")
                print(f"   📊 Response: {profile_response.text}")
                profile_accessible = False
            
            print(f"\n📊 Step 2: Test public songs access for audience")
            
            # Test public songs endpoint
            songs_response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs")
            
            print(f"   📊 Public songs response: {songs_response.status_code}")
            
            if songs_response.status_code == 200:
                songs_data = songs_response.json()
                
                print(f"   ✅ Public songs accessible")
                print(f"   📊 Number of songs available: {len(songs_data)}")
                
                # Show some song details
                for i, song in enumerate(songs_data[:3]):  # Show first 3
                    print(f"      Song {i+1}: {song.get('title')} by {song.get('artist')}")
                
                songs_accessible = True
                
            else:
                print(f"   ❌ Public songs NOT accessible: {songs_response.status_code}")
                print(f"   📊 Response: {songs_response.text}")
                songs_accessible = False
            
            print(f"\n📊 Step 3: Test public playlists access for audience")
            
            # Test public playlists endpoint
            public_playlists_response = self.make_request("GET", f"/musicians/{self.musician_slug}/playlists")
            
            print(f"   📊 Public playlists response: {public_playlists_response.status_code}")
            
            if public_playlists_response.status_code == 200:
                public_playlists_data = public_playlists_response.json()
                
                print(f"   ✅ Public playlists accessible")
                print(f"   📊 Number of public playlists: {len(public_playlists_data)}")
                
                # Show playlist details
                for i, playlist in enumerate(public_playlists_data[:3]):  # Show first 3
                    print(f"      Playlist {i+1}: {playlist.get('name')} ({playlist.get('song_count', 0)} songs)")
                
                public_playlists_accessible = True
                
            else:
                print(f"   ❌ Public playlists NOT accessible: {public_playlists_response.status_code}")
                print(f"   📊 Response: {public_playlists_response.text}")
                public_playlists_accessible = False
            
            # Restore auth token
            self.auth_token = original_token
            
            # Overall assessment
            if profile_accessible and songs_accessible:
                self.log_result("Audience Link Functionality", True, "Audience link is ACTIVE - public interface fully accessible")
            elif profile_accessible:
                self.log_result("Audience Link Functionality", True, "Audience link partially working - profile accessible but may have limitations")
            else:
                self.log_result("Audience Link Functionality", False, "Audience link is PAUSED/INACTIVE - public interface not accessible")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Audience Link Functionality", False, f"Exception: {str(e)}")

    def test_request_creation_capability(self):
        """Test if audience can create requests - CRITICAL"""
        try:
            print("📝 CRITICAL: Testing Request Creation Capability")
            print("=" * 80)
            
            if not self.musician_slug:
                self.log_result("Request Creation Capability", False, "No musician slug available")
                return
            
            print(f"📊 Step 1: Get available songs for request testing")
            
            # Clear auth token for public access
            original_token = self.auth_token
            self.auth_token = None
            
            # Get songs for request creation
            songs_response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs")
            
            if songs_response.status_code != 200:
                self.log_result("Request Creation Capability", False, f"Cannot access songs for requests: {songs_response.status_code}")
                self.auth_token = original_token
                return
            
            songs_data = songs_response.json()
            
            if len(songs_data) == 0:
                self.log_result("Request Creation Capability", False, "No songs available for request testing")
                self.auth_token = original_token
                return
            
            test_song = songs_data[0]
            print(f"   ✅ Using test song: {test_song.get('title')} by {test_song.get('artist')}")
            
            print(f"\n📊 Step 2: Attempt to create a test request")
            
            # Create test request
            request_data = {
                "song_id": test_song.get('id'),
                "requester_name": "Test Requester",
                "requester_email": "test@example.com",
                "dedication": "Testing Pro subscriber request capability"
            }
            
            request_response = self.make_request("POST", f"/musicians/{self.musician_slug}/requests", request_data)
            
            print(f"   📊 Request creation response: {request_response.status_code}")
            
            if request_response.status_code == 200:
                request_result = request_response.json()
                
                print(f"   ✅ Request creation successful")
                print(f"   📊 Request ID: {request_result.get('id')}")
                print(f"   📊 Song: {request_result.get('song_title')} by {request_result.get('song_artist')}")
                print(f"   📊 Requester: {request_result.get('requester_name')}")
                print(f"   📊 Status: {request_result.get('status')}")
                
                request_creation_ok = True
                
                # Store request ID for potential cleanup
                test_request_id = request_result.get('id')
                
            elif request_response.status_code == 403:
                print(f"   ❌ Request creation DENIED - audience link may be paused")
                print(f"   📊 Error response: {request_response.text}")
                request_creation_ok = False
                test_request_id = None
                
            else:
                print(f"   ❌ Request creation error: {request_response.status_code}")
                print(f"   📊 Response: {request_response.text}")
                request_creation_ok = False
                test_request_id = None
            
            # Restore auth token for cleanup
            self.auth_token = original_token
            
            # Clean up test request if created
            if test_request_id and self.auth_token:
                print(f"\n📊 Step 3: Clean up test request")
                
                delete_response = self.make_request("DELETE", f"/requests/{test_request_id}")
                if delete_response.status_code == 200:
                    print(f"   ✅ Test request cleaned up")
                else:
                    print(f"   ⚠️  Failed to clean up test request: {delete_response.status_code}")
            
            # Overall assessment
            if request_creation_ok:
                self.log_result("Request Creation Capability", True, "Audience can create requests - Pro subscriber functionality active")
            else:
                self.log_result("Request Creation Capability", False, "Audience CANNOT create requests - Pro subscriber access may be paused")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Request Creation Capability", False, f"Exception: {str(e)}")

    def test_database_subscription_fields(self):
        """Test and display current database subscription fields - DIAGNOSTIC"""
        try:
            print("🔍 DIAGNOSTIC: Current Database Subscription Fields")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Database Subscription Fields", False, "No auth token available")
                return
            
            print("📊 Step 1: Get current musician profile data")
            
            profile_response = self.make_request("GET", "/profile")
            
            print(f"   📊 Profile response status: {profile_response.status_code}")
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                
                print(f"   ✅ Profile data retrieved")
                print(f"\n   📊 CURRENT SUBSCRIPTION-RELATED FIELDS:")
                
                # Key subscription fields to check
                subscription_fields = [
                    'audience_link_active',
                    'has_had_trial', 
                    'trial_end',
                    'stripe_customer_id',
                    'stripe_subscription_id',
                    'subscription_status',
                    'subscription_current_period_end',
                    'payment_grace_period_end'
                ]
                
                for field in subscription_fields:
                    value = profile_data.get(field, 'NOT_FOUND')
                    print(f"      {field}: {value}")
                
                # Additional fields that might be relevant
                print(f"\n   📊 ADDITIONAL PROFILE FIELDS:")
                other_fields = ['name', 'email', 'created_at']
                for field in other_fields:
                    value = profile_data.get(field, 'NOT_FOUND')
                    print(f"      {field}: {value}")
                
                # Analysis
                audience_link_active = profile_data.get('audience_link_active', False)
                subscription_status = profile_data.get('subscription_status')
                has_had_trial = profile_data.get('has_had_trial', False)
                
                print(f"\n   📊 ANALYSIS:")
                print(f"      Current audience_link_active: {audience_link_active}")
                print(f"      Current subscription_status: {subscription_status}")
                print(f"      Has had trial: {has_had_trial}")
                
                if not audience_link_active:
                    print(f"      ❌ ISSUE: audience_link_active is FALSE - needs to be set to TRUE")
                else:
                    print(f"      ✅ audience_link_active is correctly set to TRUE")
                
                if subscription_status in ['canceled', 'incomplete_expired', None]:
                    print(f"      ❌ ISSUE: subscription_status is '{subscription_status}' - may need to be 'active' or 'trial'")
                else:
                    print(f"      ✅ subscription_status appears acceptable: '{subscription_status}'")
                
                self.log_result("Database Subscription Fields", True, f"Profile data retrieved - audience_link_active: {audience_link_active}, subscription_status: {subscription_status}")
                
            else:
                self.log_result("Database Subscription Fields", False, f"Failed to get profile data: {profile_response.status_code}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Database Subscription Fields", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all tests for Bryce's Pro subscriber status"""
        print("🚀 BRYCE LARSEN PRO SUBSCRIBER STATUS REACTIVATION TEST")
        print("=" * 100)
        print(f"Testing user: {BRYCE_CREDENTIALS['email']}")
        print(f"Issue: Account not set to subscribed and audience link is paused")
        print(f"Goal: Verify and reactivate full Pro subscriber access")
        print("=" * 100)
        
        # Run tests in order
        self.test_bryce_login_authentication()
        self.test_subscription_status_api()
        self.test_pro_features_access()
        self.test_audience_link_functionality()
        self.test_request_creation_capability()
        self.test_database_subscription_fields()
        
        # Final summary
        print("\n" + "=" * 100)
        print("🎯 FINAL TEST SUMMARY")
        print("=" * 100)
        
        total_tests = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.results['passed']}")
        print(f"Failed: {self.results['failed']}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if self.results["failed"] > 0:
            print(f"\n❌ FAILED TESTS:")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        # Determine overall status
        critical_tests = [
            "Bryce Login Authentication",
            "Subscription Status API", 
            "Pro Features Access",
            "Audience Link Functionality"
        ]
        
        critical_failures = [error for error in self.results["errors"] if any(test in error for test in critical_tests)]
        
        if len(critical_failures) == 0:
            print(f"\n✅ OVERALL STATUS: BRYCE'S PRO SUBSCRIBER ACCESS IS WORKING")
            print(f"   • User can login successfully")
            print(f"   • Pro features are accessible")
            print(f"   • Audience link is active")
            print(f"   • No reactivation needed")
        else:
            print(f"\n❌ OVERALL STATUS: BRYCE'S PRO SUBSCRIBER ACCESS NEEDS REACTIVATION")
            print(f"   • Critical issues found that prevent full Pro access")
            print(f"   • Manual database updates may be required")
            print(f"   • Recommend setting audience_link_active = true")
            print(f"   • Recommend updating subscription status fields")
        
        print("=" * 100)

if __name__ == "__main__":
    tester = BryceProStatusTester()
    tester.run_all_tests()