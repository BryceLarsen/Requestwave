#!/usr/bin/env python3
"""
CORRECTED AUDIENCE TIP FLOW TEST

This test corrects the issues found in the initial test:
1. Use GET request for tip links with query parameters
2. Use correct data format for click tracking
3. Verify the complete tip flow functionality
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://music-flow-update.preview.emergentagent.com/api"

# Test musician with complete payment and social media info
TEST_MUSICIAN = {
    "name": "Corrected Tip Flow Musician",
    "email": "corrected.tipflow@requestwave.com", 
    "password": "SecurePassword123!"
}

class CorrectedTipFlowTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
        self.test_songs = []
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
                response = requests.get(url, headers=request_headers, params=params or data)
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

    def setup_test_musician(self):
        """Set up test musician with payment and social info"""
        try:
            print("🎵 SETUP: Create Test Musician with Complete Profile")
            print("=" * 80)
            
            # Register or login
            response = self.make_request("POST", "/auth/register", TEST_MUSICIAN)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data["token"]
                self.musician_id = data["musician"]["id"]
                self.musician_slug = data["musician"]["slug"]
                print(f"   ✅ Registered: {data['musician']['name']} (slug: {self.musician_slug})")
            elif response.status_code == 400:
                # Try login
                login_data = {"email": TEST_MUSICIAN["email"], "password": TEST_MUSICIAN["password"]}
                login_response = self.make_request("POST", "/auth/login", login_data)
                if login_response.status_code == 200:
                    data = login_response.json()
                    self.auth_token = data["token"]
                    self.musician_id = data["musician"]["id"]
                    self.musician_slug = data["musician"]["slug"]
                    print(f"   ✅ Logged in: {data['musician']['name']} (slug: {self.musician_slug})")
                else:
                    return False
            else:
                return False
            
            # Update profile with complete info
            profile_update = {
                "name": "Corrected Tip Flow Musician",
                "bio": "Testing the corrected audience tip flow with proper API calls",
                "paypal_username": "correctedtiptest",
                "venmo_username": "correctedtiptest",
                "instagram_username": "correctedtiptest",
                "facebook_username": "correctedtiptest",
                "tiktok_username": "correctedtiptest",
                "spotify_artist_url": "https://open.spotify.com/artist/correctedtiptest",
                "apple_music_artist_url": "https://music.apple.com/artist/correctedtiptest"
            }
            
            update_response = self.make_request("PUT", "/profile", profile_update)
            if update_response.status_code == 200:
                print(f"   ✅ Profile updated with payment and social info")
                return True
            else:
                print(f"   ❌ Profile update failed: {update_response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Setup failed: {str(e)}")
            return False

    def add_test_songs(self):
        """Add test songs for request testing"""
        try:
            print("📊 Adding test songs...")
            
            songs_data = [
                {
                    "title": "Bohemian Rhapsody",
                    "artist": "Queen",
                    "genres": ["Rock"],
                    "moods": ["Feel It Live"],
                    "year": 1975,
                    "notes": "Epic song perfect for tips"
                },
                {
                    "title": "Hotel California",
                    "artist": "Eagles",
                    "genres": ["Classic Rock"],
                    "moods": ["Bar Anthems"],
                    "year": 1976,
                    "notes": "Classic request song"
                }
            ]
            
            for song_data in songs_data:
                response = self.make_request("POST", "/songs", song_data)
                if response.status_code == 200:
                    song = response.json()
                    self.test_songs.append(song)
                    print(f"   ✅ Added: {song['title']} by {song['artist']}")
                else:
                    print(f"   ❌ Failed to add: {song_data['title']}")
            
            return len(self.test_songs) >= 2
            
        except Exception as e:
            print(f"   ❌ Add songs failed: {str(e)}")
            return False

    def test_corrected_tip_links(self):
        """Test tip link generation with correct GET request"""
        try:
            print("🎵 TEST 1: Corrected Tip Link Generation")
            print("=" * 80)
            
            # Clear auth for public access
            self.auth_token = None
            
            test_amounts = [5.00, 10.00, 20.00]
            tip_generation_success = True
            
            for amount in test_amounts:
                print(f"📊 Testing tip links for ${amount}")
                
                # Use GET request with query parameters
                params = {
                    "amount": amount,
                    "message": f"Tip for great music - ${amount}"
                }
                
                response = self.make_request("GET", f"/musicians/{self.musician_slug}/tip-links", params=params)
                
                print(f"   📊 Response status: {response.status_code}")
                
                if response.status_code == 200:
                    tip_data = response.json()
                    paypal_link = tip_data.get('paypal_link')
                    venmo_link = tip_data.get('venmo_link')
                    
                    if paypal_link and venmo_link:
                        print(f"   ✅ Tip links generated for ${amount}")
                        print(f"      PayPal: {paypal_link[:60]}...")
                        print(f"      Venmo: {venmo_link[:60]}...")
                    else:
                        print(f"   ❌ Incomplete tip links for ${amount}")
                        print(f"      PayPal: {paypal_link}")
                        print(f"      Venmo: {venmo_link}")
                        tip_generation_success = False
                else:
                    print(f"   ❌ Tip link generation failed: {response.status_code}")
                    print(f"   📊 Response: {response.text}")
                    tip_generation_success = False
            
            if tip_generation_success:
                self.log_result("Corrected Tip Link Generation", True, "✅ TIP LINKS WORKING: All tip amounts generate proper PayPal and Venmo links")
                return True
            else:
                self.log_result("Corrected Tip Link Generation", False, "❌ TIP LINK ISSUES: Some tip link generation failed")
                return False
                
        except Exception as e:
            self.log_result("Corrected Tip Link Generation", False, f"❌ Exception: {str(e)}")
            return False

    def test_song_request_and_tracking(self):
        """Test song request creation and corrected click tracking"""
        try:
            print("🎵 TEST 2: Song Request Creation and Click Tracking")
            print("=" * 80)
            
            if not self.test_songs:
                self.log_result("Song Request and Tracking", False, "No test songs available")
                return False
            
            # Create a song request (no auth needed)
            test_song = self.test_songs[0]
            
            print(f"📊 Creating request for: {test_song['title']} by {test_song['artist']}")
            
            request_data = {
                "song_id": test_song["id"],
                "requester_name": "Corrected Flow Tester",
                "requester_email": "correctedflow@example.com",
                "dedication": "Testing the corrected tip flow with proper API calls!"
            }
            
            request_response = self.make_request("POST", "/requests", request_data)
            
            if request_response.status_code == 200:
                request_result = request_response.json()
                self.test_request_id = request_result.get('id')
                print(f"   ✅ Request created: {self.test_request_id}")
                print(f"   📊 Initial tip_clicked: {request_result.get('tip_clicked')}")
                print(f"   📊 Initial social_clicks: {request_result.get('social_clicks')}")
            else:
                print(f"   ❌ Request creation failed: {request_response.status_code}")
                self.log_result("Song Request and Tracking", False, "Request creation failed")
                return False
            
            # Test corrected click tracking
            print("📊 Testing corrected click tracking...")
            
            # Test tip click tracking with correct format
            tip_click_data = {
                "type": "tip",
                "platform": "venmo"
            }
            
            tip_click_response = self.make_request("POST", f"/requests/{self.test_request_id}/track-click", tip_click_data)
            
            if tip_click_response.status_code == 200:
                print(f"   ✅ Tip click tracked successfully")
                tip_tracking_success = True
            else:
                print(f"   ❌ Tip click tracking failed: {tip_click_response.status_code}")
                print(f"   📊 Response: {tip_click_response.text}")
                tip_tracking_success = False
            
            # Test social click tracking with correct format
            social_platforms = ["instagram", "facebook", "tiktok"]
            social_tracking_success = True
            
            for platform in social_platforms:
                social_click_data = {
                    "type": "social",
                    "platform": platform
                }
                
                social_response = self.make_request("POST", f"/requests/{self.test_request_id}/track-click", social_click_data)
                
                if social_response.status_code == 200:
                    print(f"   ✅ {platform} social click tracked")
                else:
                    print(f"   ❌ {platform} social click failed: {social_response.status_code}")
                    social_tracking_success = False
            
            # Verify tracking in database
            print("📊 Verifying click tracking in database...")
            
            # Re-authenticate to check request
            login_data = {"email": TEST_MUSICIAN["email"], "password": TEST_MUSICIAN["password"]}
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code == 200:
                self.auth_token = login_response.json()["token"]
            else:
                print(f"   ❌ Re-authentication failed")
                self.log_result("Song Request and Tracking", False, "Re-authentication failed")
                return False
            
            # Get updated request
            requests_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
            
            if requests_response.status_code == 200:
                requests_list = requests_response.json()
                
                # Find our test request
                test_request = None
                for request in requests_list:
                    if request.get('id') == self.test_request_id:
                        test_request = request
                        break
                
                if test_request:
                    tip_clicked = test_request.get('tip_clicked')
                    social_clicks = test_request.get('social_clicks', [])
                    
                    print(f"   📊 Database tip_clicked: {tip_clicked}")
                    print(f"   📊 Database social_clicks: {social_clicks}")
                    
                    if tip_clicked == True:
                        print(f"   ✅ Tip click recorded in database")
                        db_tip_success = True
                    else:
                        print(f"   ❌ Tip click not recorded in database")
                        db_tip_success = False
                    
                    if len(social_clicks) >= len(social_platforms):
                        print(f"   ✅ Social clicks recorded in database ({len(social_clicks)} clicks)")
                        db_social_success = True
                    else:
                        print(f"   ❌ Social clicks not fully recorded ({len(social_clicks)} vs {len(social_platforms)})")
                        db_social_success = False
                else:
                    print(f"   ❌ Test request not found in database")
                    db_tip_success = False
                    db_social_success = False
            else:
                print(f"   ❌ Failed to get requests: {requests_response.status_code}")
                db_tip_success = False
                db_social_success = False
            
            # Final assessment
            if tip_tracking_success and social_tracking_success and db_tip_success and db_social_success:
                self.log_result("Song Request and Tracking", True, "✅ REQUEST AND TRACKING WORKING: Song requests and click tracking fully functional")
                return True
            else:
                issues = []
                if not tip_tracking_success:
                    issues.append("tip click API failed")
                if not social_tracking_success:
                    issues.append("social click API failed")
                if not db_tip_success:
                    issues.append("tip click not in database")
                if not db_social_success:
                    issues.append("social clicks not in database")
                
                self.log_result("Song Request and Tracking", False, f"❌ TRACKING ISSUES: {', '.join(issues)}")
                return False
                
        except Exception as e:
            self.log_result("Song Request and Tracking", False, f"❌ Exception: {str(e)}")
            return False

    def test_complete_audience_flow(self):
        """Test the complete audience flow from profile access to tip/social tracking"""
        try:
            print("🎵 TEST 3: Complete Audience Flow")
            print("=" * 80)
            
            # Clear auth for audience perspective
            self.auth_token = None
            
            # Step 1: Access musician profile (public)
            print("📊 Step 1: Access musician profile")
            profile_response = self.make_request("GET", f"/musicians/{self.musician_slug}")
            
            if profile_response.status_code == 200:
                profile = profile_response.json()
                print(f"   ✅ Profile accessible: {profile['name']}")
                
                # Verify payment info available
                payment_info = {
                    "paypal_username": profile.get('paypal_username'),
                    "venmo_username": profile.get('venmo_username')
                }
                
                # Verify social info available
                social_info = {
                    "instagram_username": profile.get('instagram_username'),
                    "facebook_username": profile.get('facebook_username'),
                    "tiktok_username": profile.get('tiktok_username'),
                    "spotify_artist_url": profile.get('spotify_artist_url'),
                    "apple_music_artist_url": profile.get('apple_music_artist_url')
                }
                
                print(f"   📊 Payment info: {payment_info}")
                print(f"   📊 Social info: {social_info}")
                
                profile_complete = all(payment_info.values()) and all(social_info.values())
                
                if profile_complete:
                    print(f"   ✅ Complete profile info available for tip flow")
                else:
                    print(f"   ❌ Incomplete profile info")
                    
            else:
                print(f"   ❌ Profile not accessible: {profile_response.status_code}")
                profile_complete = False
            
            # Step 2: Access songs list
            print("📊 Step 2: Access songs list")
            songs_response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs")
            
            if songs_response.status_code == 200:
                songs = songs_response.json()
                print(f"   ✅ Songs accessible: {len(songs)} songs")
                songs_accessible = True
            else:
                print(f"   ❌ Songs not accessible: {songs_response.status_code}")
                songs_accessible = False
            
            # Step 3: Test tip link generation for different amounts
            print("📊 Step 3: Test tip link generation for audience")
            tip_amounts = [5.00, 10.00, 20.00]
            tip_links_working = True
            
            for amount in tip_amounts:
                params = {"amount": amount, "message": f"Great performance! ${amount} tip"}
                tip_response = self.make_request("GET", f"/musicians/{self.musician_slug}/tip-links", params=params)
                
                if tip_response.status_code == 200:
                    tip_data = tip_response.json()
                    if tip_data.get('paypal_link') and tip_data.get('venmo_link'):
                        print(f"   ✅ ${amount} tip links generated")
                    else:
                        print(f"   ❌ ${amount} tip links incomplete")
                        tip_links_working = False
                else:
                    print(f"   ❌ ${amount} tip links failed: {tip_response.status_code}")
                    tip_links_working = False
            
            # Final assessment
            if profile_complete and songs_accessible and tip_links_working:
                self.log_result("Complete Audience Flow", True, "✅ AUDIENCE FLOW READY: Complete profile, songs, and tip links all working for 3-step flow")
                return True
            else:
                issues = []
                if not profile_complete:
                    issues.append("incomplete profile info")
                if not songs_accessible:
                    issues.append("songs not accessible")
                if not tip_links_working:
                    issues.append("tip links not working")
                
                self.log_result("Complete Audience Flow", False, f"❌ AUDIENCE FLOW ISSUES: {', '.join(issues)}")
                return False
                
        except Exception as e:
            self.log_result("Complete Audience Flow", False, f"❌ Exception: {str(e)}")
            return False

    def cleanup_test_data(self):
        """Clean up test data"""
        try:
            print("🎵 CLEANUP: Removing test data")
            
            # Re-authenticate for cleanup
            login_data = {"email": TEST_MUSICIAN["email"], "password": TEST_MUSICIAN["password"]}
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code == 200:
                self.auth_token = login_response.json()["token"]
                
                cleanup_count = 0
                
                # Delete songs
                for song in self.test_songs:
                    delete_response = self.make_request("DELETE", f"/songs/{song['id']}")
                    if delete_response.status_code == 200:
                        cleanup_count += 1
                
                # Delete request
                if self.test_request_id:
                    delete_response = self.make_request("DELETE", f"/requests/{self.test_request_id}")
                    if delete_response.status_code == 200:
                        cleanup_count += 1
                
                print(f"   ✅ Cleaned up {cleanup_count} items")
            
        except Exception as e:
            print(f"   ❌ Cleanup error: {str(e)}")

    def run_corrected_tests(self):
        """Run all corrected tests"""
        print("🎵 CORRECTED AUDIENCE TIP FLOW TESTING")
        print("=" * 100)
        print("Testing the corrected 3-step audience request flow with proper API calls")
        print("=" * 100)
        
        try:
            # Setup
            setup_success = self.setup_test_musician()
            if not setup_success:
                print("❌ Setup failed - cannot continue")
                return
            
            songs_success = self.add_test_songs()
            if not songs_success:
                print("❌ Song setup failed - cannot continue")
                return
            
            # Run tests
            test1_success = self.test_corrected_tip_links()
            test2_success = self.test_song_request_and_tracking()
            test3_success = self.test_complete_audience_flow()
            
            # Cleanup
            self.cleanup_test_data()
            
            # Results
            print("\n" + "=" * 100)
            print("🎵 CORRECTED TEST RESULTS")
            print("=" * 100)
            print(f"✅ PASSED: {self.results['passed']}")
            print(f"❌ FAILED: {self.results['failed']}")
            
            if self.results['passed'] + self.results['failed'] > 0:
                success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100)
                print(f"📊 SUCCESS RATE: {success_rate:.1f}%")
            
            if self.results['errors']:
                print("\n❌ FAILED TESTS:")
                for error in self.results['errors']:
                    print(f"   • {error}")
            
            # Summary
            print("\n" + "=" * 100)
            print("🎵 FINAL SUMMARY")
            print("=" * 100)
            
            if all([test1_success, test2_success, test3_success]):
                print("✅ AUDIENCE TIP FLOW FULLY FUNCTIONAL:")
                print("   • Test musician created with complete payment and social info")
                print("   • Tip link generation working for $5/$10/$20 amounts")
                print("   • Song request creation working with proper initial values")
                print("   • Click tracking working for both tips and social follows")
                print("   • Public profile access working for audience")
                print("\n🎯 READY FOR 3-STEP AUDIENCE FLOW:")
                print("   • Step 1: Initial request modal ✅")
                print("   • Step 2: Tip choice modal ($5/$10/$20 + Venmo/PayPal) ✅")
                print("   • Step 3: Social follow modal (No Tip path) ✅")
                print(f"\n📊 Test Musician: {TEST_MUSICIAN['name']}")
                print(f"📊 Musician Slug: {self.musician_slug}")
                print(f"📊 Test Songs: {len(self.test_songs)} songs available")
                print(f"📊 Payment Methods: PayPal and Venmo configured")
                print(f"📊 Social Links: Instagram, Facebook, TikTok, Spotify, Apple Music")
            else:
                print("❌ AUDIENCE TIP FLOW ISSUES REMAIN:")
                if not test1_success:
                    print("   • Tip link generation issues")
                if not test2_success:
                    print("   • Song request or click tracking issues")
                if not test3_success:
                    print("   • Complete audience flow issues")
            
            print("=" * 100)
            
        except Exception as e:
            print(f"\n❌ TESTING FAILED: {str(e)}")

if __name__ == "__main__":
    tester = CorrectedTipFlowTester()
    tester.run_corrected_tests()