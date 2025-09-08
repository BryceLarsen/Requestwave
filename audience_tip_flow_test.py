#!/usr/bin/env python3
"""
COMPREHENSIVE TESTING FOR AUDIENCE-SIDE TIP FLOW

Testing the new 3-step audience request flow:
1. Create test musician with payment information (venmo_username, paypal_username) and social media links
2. Add 2-3 songs to their repertoire for testing song requests
3. Test song request creation to verify the backend accepts and processes requests correctly
4. Verify payment info - confirm the musician profile has the payment and social media information needed for the new tip flow

The goal is to create a complete test musician profile that can be used to test the new 3-step audience request flow:
- Step 1: Initial request modal (existing)  
- Step 2: Tip choice modal with $5/$10/$20 options and Venmo/PayPal choice
- Step 3: Social follow modal (for "No Tip" path)

Focus on setting up the test data needed to properly demonstrate and validate the new audience-side flow.
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://requestwave-revamp.preview.emergentagent.com/api"

# Test musician with complete payment and social media info
TEST_MUSICIAN = {
    "name": "Tip Flow Test Musician",
    "email": "tipflow.test@requestwave.com", 
    "password": "SecurePassword123!"
}

class AudienceTipFlowTester:
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

    def test_create_musician_with_payment_info(self):
        """Test creating a musician with complete payment and social media information"""
        try:
            print("🎵 STEP 1: Create Test Musician with Payment Information")
            print("=" * 80)
            
            # Step 1: Register new test musician
            print("📊 Step 1.1: Register new test musician")
            response = self.make_request("POST", "/auth/register", TEST_MUSICIAN)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data["token"]
                self.musician_id = data["musician"]["id"]
                self.musician_slug = data["musician"]["slug"]
                print(f"   ✅ Registered musician: {data['musician']['name']}")
                print(f"   📊 Musician ID: {self.musician_id}")
                print(f"   📊 Musician slug: {self.musician_slug}")
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
                    print(f"   📊 Musician ID: {self.musician_id}")
                    print(f"   📊 Musician slug: {self.musician_slug}")
                else:
                    self.log_result("Create Musician - Authentication", False, f"Failed to login: {login_response.status_code}")
                    return False
            else:
                self.log_result("Create Musician - Registration", False, f"Failed to register: {response.status_code}")
                return False
            
            # Step 2: Update profile with complete payment and social media information
            print("📊 Step 1.2: Update profile with payment and social media information")
            
            profile_update = {
                "name": "Tip Flow Test Musician",
                "bio": "A test musician for validating the new audience tip flow with payment integration",
                "website": "https://tipflowtest.com",
                # Payment information for tip flow
                "paypal_username": "tipflowtest",
                "venmo_username": "tipflowtest",
                # Social media information for follow flow
                "instagram_username": "tipflowtest",
                "facebook_username": "tipflowtest",
                "tiktok_username": "tipflowtest",
                "spotify_artist_url": "https://open.spotify.com/artist/tipflowtest",
                "apple_music_artist_url": "https://music.apple.com/artist/tipflowtest"
            }
            
            update_response = self.make_request("PUT", "/profile", profile_update)
            
            if update_response.status_code == 200:
                updated_profile = update_response.json()
                print(f"   ✅ Profile updated successfully")
                
                # Verify all payment fields are set
                payment_fields = ["paypal_username", "venmo_username"]
                social_fields = ["instagram_username", "facebook_username", "tiktok_username", "spotify_artist_url", "apple_music_artist_url"]
                
                payment_complete = True
                social_complete = True
                
                for field in payment_fields:
                    if updated_profile.get(field) == profile_update[field]:
                        print(f"   ✅ {field}: {updated_profile.get(field)}")
                    else:
                        print(f"   ❌ {field}: Expected '{profile_update[field]}', got '{updated_profile.get(field)}'")
                        payment_complete = False
                
                for field in social_fields:
                    if updated_profile.get(field) == profile_update[field]:
                        print(f"   ✅ {field}: {updated_profile.get(field)}")
                    else:
                        print(f"   ❌ {field}: Expected '{profile_update[field]}', got '{updated_profile.get(field)}'")
                        social_complete = False
                
                if payment_complete and social_complete:
                    self.log_result("Create Musician with Payment Info", True, "✅ MUSICIAN CREATED: Complete payment and social media information successfully added")
                    return True
                else:
                    issues = []
                    if not payment_complete:
                        issues.append("payment information incomplete")
                    if not social_complete:
                        issues.append("social media information incomplete")
                    self.log_result("Create Musician with Payment Info", False, f"❌ PROFILE UPDATE ISSUES: {', '.join(issues)}")
                    return False
            else:
                self.log_result("Create Musician with Payment Info", False, f"Failed to update profile: {update_response.status_code}")
                return False
            
        except Exception as e:
            self.log_result("Create Musician with Payment Info", False, f"❌ Exception: {str(e)}")
            return False

    def test_add_test_songs(self):
        """Add 2-3 songs to the musician's repertoire for testing"""
        try:
            print("🎵 STEP 2: Add Test Songs to Repertoire")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Add Test Songs", False, "No authentication token available")
                return False
            
            # Define test songs with variety for request testing
            test_songs_data = [
                {
                    "title": "Sweet Caroline",
                    "artist": "Neil Diamond",
                    "genres": ["Classic Rock"],
                    "moods": ["Bar Anthems"],
                    "year": 1969,
                    "notes": "Crowd favorite - perfect for audience requests"
                },
                {
                    "title": "Don't Stop Believin'",
                    "artist": "Journey",
                    "genres": ["Rock"],
                    "moods": ["Feel Good"],
                    "year": 1981,
                    "notes": "Ultimate sing-along song"
                },
                {
                    "title": "Piano Man",
                    "artist": "Billy Joel",
                    "genres": ["Classic Rock"],
                    "moods": ["Bar Anthems"],
                    "year": 1973,
                    "notes": "Piano ballad - great for tips"
                }
            ]
            
            added_songs = []
            for song_data in test_songs_data:
                print(f"📊 Adding song: {song_data['title']} by {song_data['artist']}")
                
                song_response = self.make_request("POST", "/songs", song_data)
                
                if song_response.status_code == 200:
                    song_result = song_response.json()
                    added_songs.append(song_result)
                    print(f"   ✅ Added: {song_result['title']} by {song_result['artist']} (ID: {song_result['id']})")
                else:
                    print(f"   ❌ Failed to add: {song_data['title']} - Status: {song_response.status_code}")
                    print(f"   📊 Response: {song_response.text}")
            
            self.test_songs = added_songs
            
            if len(added_songs) >= 2:
                self.log_result("Add Test Songs", True, f"✅ SONGS ADDED: Successfully added {len(added_songs)} songs to repertoire for request testing")
                
                # Verify songs are accessible via public endpoint
                print("📊 Step 2.1: Verify songs accessible via public endpoint")
                
                # Clear auth for public access test
                temp_token = self.auth_token
                self.auth_token = None
                
                public_songs_response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs")
                
                # Restore auth
                self.auth_token = temp_token
                
                if public_songs_response.status_code == 200:
                    public_songs = public_songs_response.json()
                    public_song_titles = [s['title'] for s in public_songs]
                    
                    test_songs_found = 0
                    for song in added_songs:
                        if song['title'] in public_song_titles:
                            test_songs_found += 1
                            print(f"   ✅ {song['title']} visible to audience")
                        else:
                            print(f"   ❌ {song['title']} not visible to audience")
                    
                    if test_songs_found == len(added_songs):
                        print(f"   ✅ All {len(added_songs)} songs accessible to audience")
                        return True
                    else:
                        print(f"   ❌ Only {test_songs_found}/{len(added_songs)} songs accessible to audience")
                        return False
                else:
                    print(f"   ❌ Public songs endpoint failed: {public_songs_response.status_code}")
                    return False
            else:
                self.log_result("Add Test Songs", False, f"❌ INSUFFICIENT SONGS: Only added {len(added_songs)} songs, need at least 2")
                return False
            
        except Exception as e:
            self.log_result("Add Test Songs", False, f"❌ Exception: {str(e)}")
            return False

    def test_song_request_creation(self):
        """Test song request creation from audience perspective"""
        try:
            print("🎵 STEP 3: Test Song Request Creation")
            print("=" * 80)
            
            if not self.test_songs or len(self.test_songs) == 0:
                self.log_result("Song Request Creation", False, "No test songs available for request testing")
                return False
            
            # Clear auth token for audience perspective
            self.auth_token = None
            
            # Test creating a request for the first song
            test_song = self.test_songs[0]
            
            print(f"📊 Step 3.1: Create request for '{test_song['title']}' by {test_song['artist']}")
            
            request_data = {
                "song_id": test_song["id"],
                "requester_name": "Tip Flow Tester",
                "requester_email": "tipflowtester@example.com",
                "dedication": "Testing the new tip flow - this song would be perfect for tips!"
            }
            
            # Create request via public endpoint
            request_response = self.make_request("POST", "/requests", request_data)
            
            print(f"   📊 Request response status: {request_response.status_code}")
            print(f"   📊 Request response: {request_response.text[:300]}...")
            
            if request_response.status_code == 200:
                request_result = request_response.json()
                self.test_request_id = request_result.get('id')
                
                print(f"   ✅ Request created successfully")
                print(f"   📊 Request ID: {self.test_request_id}")
                print(f"   📊 Song: {request_result.get('song_title')} by {request_result.get('song_artist')}")
                print(f"   📊 Requester: {request_result.get('requester_name')}")
                print(f"   📊 Status: {request_result.get('status')}")
                print(f"   📊 Created: {request_result.get('created_at')}")
                
                # Verify initial values for tip flow
                tip_clicked = request_result.get('tip_clicked', None)
                social_clicks = request_result.get('social_clicks', None)
                show_name = request_result.get('show_name', None)
                
                print(f"   📊 Tip clicked: {tip_clicked}")
                print(f"   📊 Social clicks: {social_clicks}")
                print(f"   📊 Show name: {show_name}")
                
                # Verify expected initial values
                initial_values_correct = (
                    tip_clicked == False and
                    social_clicks == [] and
                    show_name is None
                )
                
                if initial_values_correct:
                    print(f"   ✅ Initial values correct for tip flow tracking")
                    request_creation_success = True
                else:
                    print(f"   ❌ Initial values incorrect - tip_clicked: {tip_clicked}, social_clicks: {social_clicks}, show_name: {show_name}")
                    request_creation_success = False
                
            else:
                print(f"   ❌ Request creation failed: {request_response.status_code}")
                print(f"   📊 Error response: {request_response.text}")
                request_creation_success = False
            
            # Step 3.2: Verify request appears in musician's interface
            print(f"📊 Step 3.2: Verify request appears in musician's interface")
            
            # Restore auth for musician access
            # Need to login again since we cleared the token
            login_data = {
                "email": TEST_MUSICIAN["email"],
                "password": TEST_MUSICIAN["password"]
            }
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code == 200:
                login_result = login_response.json()
                self.auth_token = login_result["token"]
                print(f"   ✅ Re-authenticated as musician")
            else:
                print(f"   ❌ Failed to re-authenticate: {login_response.status_code}")
                self.log_result("Song Request Creation", False, "Failed to re-authenticate for verification")
                return False
            
            # Get musician's requests
            requests_response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
            
            if requests_response.status_code == 200:
                requests_list = requests_response.json()
                print(f"   ✅ Retrieved {len(requests_list)} requests from musician interface")
                
                # Find our test request
                test_request = None
                for request in requests_list:
                    if request.get('id') == self.test_request_id:
                        test_request = request
                        break
                
                if test_request:
                    print(f"   ✅ Test request found in musician interface")
                    print(f"   📊 Request details: {test_request.get('song_title')} by {test_request.get('song_artist')}")
                    print(f"   📊 Requester: {test_request.get('requester_name')} ({test_request.get('requester_email')})")
                    print(f"   📊 Dedication: {test_request.get('dedication')}")
                    request_in_interface = True
                else:
                    print(f"   ❌ Test request not found in musician interface")
                    request_in_interface = False
            else:
                print(f"   ❌ Failed to get musician requests: {requests_response.status_code}")
                request_in_interface = False
            
            if request_creation_success and request_in_interface:
                self.log_result("Song Request Creation", True, "✅ REQUEST CREATION WORKING: Song requests created successfully with proper initial values for tip flow")
                return True
            else:
                issues = []
                if not request_creation_success:
                    issues.append("request creation failed or initial values incorrect")
                if not request_in_interface:
                    issues.append("request not appearing in musician interface")
                
                self.log_result("Song Request Creation", False, f"❌ REQUEST CREATION ISSUES: {', '.join(issues)}")
                return False
            
        except Exception as e:
            self.log_result("Song Request Creation", False, f"❌ Exception: {str(e)}")
            return False

    def test_payment_info_verification(self):
        """Verify the musician profile has all payment and social media information needed for tip flow"""
        try:
            print("🎵 STEP 4: Verify Payment Info for Tip Flow")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Payment Info Verification", False, "No authentication token available")
                return False
            
            # Step 4.1: Get musician profile (authenticated)
            print("📊 Step 4.1: Get musician profile for payment verification")
            
            profile_response = self.make_request("GET", "/profile")
            
            if profile_response.status_code != 200:
                self.log_result("Payment Info Verification", False, f"Failed to get profile: {profile_response.status_code}")
                return False
            
            profile_data = profile_response.json()
            
            # Step 4.2: Verify payment fields
            print("📊 Step 4.2: Verify payment fields for tip flow")
            
            required_payment_fields = {
                "paypal_username": "tipflowtest",
                "venmo_username": "tipflowtest"
            }
            
            payment_verification = True
            for field, expected_value in required_payment_fields.items():
                actual_value = profile_data.get(field)
                if actual_value == expected_value:
                    print(f"   ✅ {field}: {actual_value}")
                else:
                    print(f"   ❌ {field}: Expected '{expected_value}', got '{actual_value}'")
                    payment_verification = False
            
            # Step 4.3: Verify social media fields
            print("📊 Step 4.3: Verify social media fields for follow flow")
            
            required_social_fields = {
                "instagram_username": "tipflowtest",
                "facebook_username": "tipflowtest", 
                "tiktok_username": "tipflowtest",
                "spotify_artist_url": "https://open.spotify.com/artist/tipflowtest",
                "apple_music_artist_url": "https://music.apple.com/artist/tipflowtest"
            }
            
            social_verification = True
            for field, expected_value in required_social_fields.items():
                actual_value = profile_data.get(field)
                if actual_value == expected_value:
                    print(f"   ✅ {field}: {actual_value}")
                else:
                    print(f"   ❌ {field}: Expected '{expected_value}', got '{actual_value}'")
                    social_verification = False
            
            # Step 4.4: Test public profile access (for audience tip flow)
            print("📊 Step 4.4: Test public profile access for audience tip flow")
            
            # Clear auth for public access
            temp_token = self.auth_token
            self.auth_token = None
            
            public_profile_response = self.make_request("GET", f"/musicians/{self.musician_slug}")
            
            # Restore auth
            self.auth_token = temp_token
            
            if public_profile_response.status_code == 200:
                public_profile = public_profile_response.json()
                print(f"   ✅ Public profile accessible")
                
                # Verify payment fields are available to audience
                public_payment_fields = ["paypal_username", "venmo_username"]
                public_social_fields = ["instagram_username", "facebook_username", "tiktok_username", "spotify_artist_url", "apple_music_artist_url"]
                
                public_payment_available = True
                public_social_available = True
                
                for field in public_payment_fields:
                    if public_profile.get(field):
                        print(f"   ✅ Public {field}: {public_profile.get(field)}")
                    else:
                        print(f"   ❌ Public {field}: Not available")
                        public_payment_available = False
                
                for field in public_social_fields:
                    if public_profile.get(field):
                        print(f"   ✅ Public {field}: {public_profile.get(field)}")
                    else:
                        print(f"   ❌ Public {field}: Not available")
                        public_social_available = False
                
                public_access_success = public_payment_available and public_social_available
            else:
                print(f"   ❌ Public profile not accessible: {public_profile_response.status_code}")
                public_access_success = False
            
            # Step 4.5: Test tip link generation (if available)
            print("📊 Step 4.5: Test tip link generation")
            
            tip_test_amounts = [5.00, 10.00, 20.00]
            tip_generation_success = True
            
            for amount in tip_test_amounts:
                tip_data = {
                    "amount": amount,
                    "message": f"Test tip for ${amount}"
                }
                
                tip_response = self.make_request("POST", f"/musicians/{self.musician_slug}/tip-links", tip_data)
                
                if tip_response.status_code == 200:
                    tip_result = tip_response.json()
                    paypal_link = tip_result.get('paypal_link')
                    venmo_link = tip_result.get('venmo_link')
                    
                    if paypal_link and venmo_link:
                        print(f"   ✅ Tip links generated for ${amount}")
                        print(f"      PayPal: {paypal_link[:50]}...")
                        print(f"      Venmo: {venmo_link[:50]}...")
                    else:
                        print(f"   ❌ Incomplete tip links for ${amount}")
                        tip_generation_success = False
                else:
                    print(f"   ❌ Tip link generation failed for ${amount}: {tip_response.status_code}")
                    tip_generation_success = False
            
            # Final assessment
            if payment_verification and social_verification and public_access_success and tip_generation_success:
                self.log_result("Payment Info Verification", True, "✅ PAYMENT INFO COMPLETE: All payment and social media information available for 3-step tip flow")
                return True
            else:
                issues = []
                if not payment_verification:
                    issues.append("payment fields incomplete")
                if not social_verification:
                    issues.append("social media fields incomplete")
                if not public_access_success:
                    issues.append("public profile access issues")
                if not tip_generation_success:
                    issues.append("tip link generation issues")
                
                self.log_result("Payment Info Verification", False, f"❌ PAYMENT INFO ISSUES: {', '.join(issues)}")
                return False
            
        except Exception as e:
            self.log_result("Payment Info Verification", False, f"❌ Exception: {str(e)}")
            return False

    def test_click_tracking_system(self):
        """Test the click tracking system for tips and social follows"""
        try:
            print("🎵 STEP 5: Test Click Tracking System")
            print("=" * 80)
            
            if not self.test_request_id:
                self.log_result("Click Tracking System", False, "No test request available for click tracking")
                return False
            
            # Clear auth for audience perspective
            self.auth_token = None
            
            # Step 5.1: Test tip click tracking
            print("📊 Step 5.1: Test tip click tracking")
            
            tip_platforms = ["venmo", "paypal"]
            tip_tracking_success = True
            
            for platform in tip_platforms:
                print(f"   Testing {platform} tip click tracking...")
                
                click_data = {
                    "platform": platform
                }
                
                click_response = self.make_request("POST", f"/requests/{self.test_request_id}/track-click", click_data)
                
                if click_response.status_code == 200:
                    print(f"   ✅ {platform} tip click tracked successfully")
                else:
                    print(f"   ❌ {platform} tip click tracking failed: {click_response.status_code}")
                    tip_tracking_success = False
            
            # Step 5.2: Test social click tracking
            print("📊 Step 5.2: Test social click tracking")
            
            social_platforms = ["instagram", "facebook", "tiktok", "spotify", "apple_music"]
            social_tracking_success = True
            
            for platform in social_platforms:
                print(f"   Testing {platform} social click tracking...")
                
                click_data = {
                    "platform": platform
                }
                
                click_response = self.make_request("POST", f"/requests/{self.test_request_id}/track-click", click_data)
                
                if click_response.status_code == 200:
                    print(f"   ✅ {platform} social click tracked successfully")
                else:
                    print(f"   ❌ {platform} social click tracking failed: {click_response.status_code}")
                    social_tracking_success = False
            
            # Step 5.3: Verify click tracking in database
            print("📊 Step 5.3: Verify click tracking in database")
            
            # Re-authenticate as musician to check request details
            login_data = {
                "email": TEST_MUSICIAN["email"],
                "password": TEST_MUSICIAN["password"]
            }
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code == 200:
                login_result = login_response.json()
                self.auth_token = login_result["token"]
            else:
                print(f"   ❌ Failed to re-authenticate for verification")
                self.log_result("Click Tracking System", False, "Failed to re-authenticate for click verification")
                return False
            
            # Get updated request details
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
                    
                    print(f"   📊 Tip clicked: {tip_clicked}")
                    print(f"   📊 Social clicks: {social_clicks}")
                    
                    # Verify tracking worked
                    if tip_clicked == True:
                        print(f"   ✅ Tip click tracking verified in database")
                        tip_db_success = True
                    else:
                        print(f"   ❌ Tip click not recorded in database")
                        tip_db_success = False
                    
                    if len(social_clicks) >= len(social_platforms):
                        print(f"   ✅ Social click tracking verified in database ({len(social_clicks)} clicks)")
                        social_db_success = True
                    else:
                        print(f"   ❌ Social clicks not fully recorded in database ({len(social_clicks)} vs {len(social_platforms)})")
                        social_db_success = False
                else:
                    print(f"   ❌ Test request not found for verification")
                    tip_db_success = False
                    social_db_success = False
            else:
                print(f"   ❌ Failed to get requests for verification: {requests_response.status_code}")
                tip_db_success = False
                social_db_success = False
            
            # Final assessment
            if tip_tracking_success and social_tracking_success and tip_db_success and social_db_success:
                self.log_result("Click Tracking System", True, "✅ CLICK TRACKING WORKING: Both tip and social click tracking functional")
                return True
            else:
                issues = []
                if not tip_tracking_success:
                    issues.append("tip click tracking API issues")
                if not social_tracking_success:
                    issues.append("social click tracking API issues")
                if not tip_db_success:
                    issues.append("tip click database recording issues")
                if not social_db_success:
                    issues.append("social click database recording issues")
                
                self.log_result("Click Tracking System", False, f"❌ CLICK TRACKING ISSUES: {', '.join(issues)}")
                return False
            
        except Exception as e:
            self.log_result("Click Tracking System", False, f"❌ Exception: {str(e)}")
            return False

    def cleanup_test_data(self):
        """Clean up all test data created during testing"""
        try:
            print("🎵 CLEANUP: Removing Test Data")
            print("=" * 80)
            
            cleanup_count = 0
            
            if self.auth_token:
                # Delete test songs
                for song in self.test_songs:
                    delete_response = self.make_request("DELETE", f"/songs/{song['id']}")
                    if delete_response.status_code == 200:
                        cleanup_count += 1
                        print(f"   ✅ Deleted song: {song['title']}")
                    else:
                        print(f"   ❌ Failed to delete song: {song['title']}")
                
                # Delete test request
                if self.test_request_id:
                    delete_request_response = self.make_request("DELETE", f"/requests/{self.test_request_id}")
                    if delete_request_response.status_code == 200:
                        cleanup_count += 1
                        print(f"   ✅ Deleted test request")
                    else:
                        print(f"   ❌ Failed to delete test request")
            
            print(f"   📊 Cleaned up {cleanup_count} test items")
            
        except Exception as e:
            print(f"   ❌ Cleanup error: {str(e)}")

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🎵 STARTING AUDIENCE TIP FLOW TESTING")
        print("=" * 100)
        print("Testing the new 3-step audience request flow:")
        print("- Step 1: Initial request modal (existing)")
        print("- Step 2: Tip choice modal with $5/$10/$20 options and Venmo/PayPal choice")
        print("- Step 3: Social follow modal (for 'No Tip' path)")
        print("=" * 100)
        
        try:
            # Test 1: Create musician with payment info
            success1 = self.test_create_musician_with_payment_info()
            
            # Test 2: Add test songs
            success2 = self.test_add_test_songs() if success1 else False
            
            # Test 3: Test song request creation
            success3 = self.test_song_request_creation() if success2 else False
            
            # Test 4: Verify payment info
            success4 = self.test_payment_info_verification() if success1 else False
            
            # Test 5: Test click tracking system
            success5 = self.test_click_tracking_system() if success3 else False
            
            # Cleanup
            self.cleanup_test_data()
            
            # Print final results
            print("\n" + "=" * 100)
            print("🎵 FINAL TEST RESULTS")
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
            
            # Summary for main agent
            print("\n" + "=" * 100)
            print("🎵 SUMMARY FOR MAIN AGENT")
            print("=" * 100)
            
            if all([success1, success2, success3, success4, success5]):
                print("✅ AUDIENCE TIP FLOW READY: Complete test musician profile created with:")
                print("   • Payment information (PayPal and Venmo usernames)")
                print("   • Social media links (Instagram, Facebook, TikTok, Spotify, Apple Music)")
                print("   • Test songs in repertoire for request testing")
                print("   • Working song request creation system")
                print("   • Functional click tracking for tips and social follows")
                print("\n🎯 READY FOR 3-STEP FLOW TESTING:")
                print("   • Step 1: Initial request modal ✅")
                print("   • Step 2: Tip choice modal ($5/$10/$20 + Venmo/PayPal) ✅")
                print("   • Step 3: Social follow modal (No Tip path) ✅")
                print(f"\n📊 Test Musician: {TEST_MUSICIAN['name']} (slug: {self.musician_slug})")
                print(f"📊 Test Songs: {len(self.test_songs)} songs available")
                print(f"📊 Test Request: Created and tracked successfully")
            else:
                print("❌ AUDIENCE TIP FLOW SETUP INCOMPLETE:")
                if not success1:
                    print("   • Musician creation with payment info failed")
                if not success2:
                    print("   • Test songs addition failed")
                if not success3:
                    print("   • Song request creation failed")
                if not success4:
                    print("   • Payment info verification failed")
                if not success5:
                    print("   • Click tracking system failed")
                print("\n🔧 REQUIRES FIXES BEFORE TIP FLOW TESTING")
            
            print("=" * 100)
            
        except Exception as e:
            print(f"\n❌ TESTING FAILED WITH EXCEPTION: {str(e)}")
            self.log_result("Overall Testing", False, f"Exception during testing: {str(e)}")

if __name__ == "__main__":
    tester = AudienceTipFlowTester()
    tester.run_all_tests()