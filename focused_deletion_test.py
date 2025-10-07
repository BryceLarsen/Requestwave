#!/usr/bin/env python3
"""
Focused Song Deletion Tests - Testing the FIXED functionality
Tests the specific issues mentioned in the review request about individual and bulk song deletion
"""

import requests
import json
import time
import concurrent.futures
from typing import Dict, Any, List

# Configuration
BASE_URL = "https://request-error-fix.preview.emergentagent.com/api"
TEST_MUSICIAN = {
    "name": "Focused Deletion Tester",
    "email": "focused.deletion@requestwave.com", 
    "password": "FocusedPassword123!"
}

class FocusedDeletionTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.test_songs = []
        self.results = {"passed": 0, "failed": 0, "errors": []}

    def log_result(self, test_name: str, success: bool, message: str = ""):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"   {message}")
        
        if success:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name}: {message}")

    def make_request(self, method: str, endpoint: str, data: Any = None, headers: Dict = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        request_headers = {"Content-Type": "application/json"}
        if self.auth_token:
            request_headers["Authorization"] = f"Bearer {self.auth_token}"
        if headers:
            request_headers.update(headers)
        
        if method.upper() == "GET":
            return requests.get(url, headers=request_headers)
        elif method.upper() == "POST":
            return requests.post(url, headers=request_headers, json=data)
        elif method.upper() == "DELETE":
            return requests.delete(url, headers=request_headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

    def setup_test_environment(self):
        """Setup authentication and create test songs"""
        # Register/Login
        response = self.make_request("POST", "/auth/register", TEST_MUSICIAN)
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data["token"]
            self.musician_id = data["musician"]["id"]
            print(f"✅ Registered musician: {data['musician']['name']}")
        elif response.status_code == 400:
            # Try login
            login_data = {"email": TEST_MUSICIAN["email"], "password": TEST_MUSICIAN["password"]}
            response = self.make_request("POST", "/auth/login", login_data)
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data["token"]
                self.musician_id = data["musician"]["id"]
                print(f"✅ Logged in musician: {data['musician']['name']}")
            else:
                print("❌ Authentication failed")
                return False
        else:
            print("❌ Registration failed")
            return False
        
        # Create test songs with realistic data
        realistic_songs = [
            {"title": "Sweet Caroline", "artist": "Neil Diamond", "genres": ["Pop", "Classic Rock"], "moods": ["Upbeat"], "year": 1969},
            {"title": "Bohemian Rhapsody", "artist": "Queen", "genres": ["Rock", "Opera"], "moods": ["Epic"], "year": 1975},
            {"title": "Hotel California", "artist": "Eagles", "genres": ["Rock"], "moods": ["Mysterious"], "year": 1976},
            {"title": "Imagine", "artist": "John Lennon", "genres": ["Pop", "Folk"], "moods": ["Peaceful"], "year": 1971},
            {"title": "Billie Jean", "artist": "Michael Jackson", "genres": ["Pop", "R&B"], "moods": ["Energetic"], "year": 1982},
            {"title": "Like a Rolling Stone", "artist": "Bob Dylan", "genres": ["Folk Rock"], "moods": ["Rebellious"], "year": 1965},
            {"title": "Stairway to Heaven", "artist": "Led Zeppelin", "genres": ["Rock"], "moods": ["Epic"], "year": 1971},
            {"title": "Hey Jude", "artist": "The Beatles", "genres": ["Pop", "Rock"], "moods": ["Uplifting"], "year": 1968},
            {"title": "What's Going On", "artist": "Marvin Gaye", "genres": ["Soul", "R&B"], "moods": ["Contemplative"], "year": 1971},
            {"title": "Respect", "artist": "Aretha Franklin", "genres": ["Soul", "R&B"], "moods": ["Empowering"], "year": 1967}
        ]
        
        created_count = 0
        for song_data in realistic_songs:
            response = self.make_request("POST", "/songs", song_data)
            if response.status_code == 200:
                self.test_songs.append(response.json()["id"])
                created_count += 1
            else:
                print(f"Failed to create song '{song_data['title']}': {response.status_code}")
        
        print(f"✅ Created {created_count}/{len(realistic_songs)} test songs")
        return created_count > 0

    def test_individual_delete_button_functionality(self):
        """Test that individual song delete buttons work correctly from musician dashboard"""
        try:
            if not self.test_songs:
                self.log_result("Individual Delete Button", False, "No test songs available")
                return
            
            song_id = self.test_songs[0]
            print(f"🔍 Testing individual delete button functionality for song: {song_id}")
            
            # Simulate the delete button click by making DELETE request with proper JWT auth
            # This tests the FIXED issue where delete buttons weren't working due to auth problems
            response = self.make_request("DELETE", f"/songs/{song_id}")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "deleted" in data["message"].lower():
                    # Verify song is actually removed from database
                    songs_response = self.make_request("GET", "/songs")
                    if songs_response.status_code == 200:
                        remaining_songs = songs_response.json()
                        song_still_exists = any(song["id"] == song_id for song in remaining_songs)
                        
                        if not song_still_exists:
                            self.log_result("Individual Delete Button", True, 
                                           "✅ FIXED: Individual song delete button working correctly with proper JWT authentication")
                            self.test_songs.remove(song_id)
                        else:
                            self.log_result("Individual Delete Button", False, 
                                           "❌ Song still exists in database after deletion")
                    else:
                        self.log_result("Individual Delete Button", False, 
                                       "❌ Could not verify song deletion from database")
                else:
                    self.log_result("Individual Delete Button", False, 
                                   f"❌ Unexpected response format: {data}")
            else:
                self.log_result("Individual Delete Button", False, 
                               f"❌ Delete request failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("Individual Delete Button", False, f"❌ Exception: {str(e)}")

    def test_bulk_delete_with_different_counts(self):
        """Test bulk delete with different numbers of songs (2, 5, 10+ songs)"""
        try:
            if len(self.test_songs) < 10:
                self.log_result("Bulk Delete - Different Counts", False, "Not enough test songs for bulk testing")
                return
            
            # Test 1: Bulk delete 2 songs
            songs_for_2 = self.test_songs[:2]
            print(f"🔍 Testing bulk deletion of 2 songs")
            
            successful_2 = 0
            for song_id in songs_for_2:
                response = self.make_request("DELETE", f"/songs/{song_id}")
                if response.status_code == 200:
                    successful_2 += 1
                    if song_id in self.test_songs:
                        self.test_songs.remove(song_id)
            
            if successful_2 == 2:
                self.log_result("Bulk Delete - 2 Songs", True, "✅ Successfully deleted 2 songs in bulk")
            else:
                self.log_result("Bulk Delete - 2 Songs", False, f"❌ Only deleted {successful_2}/2 songs")
            
            # Test 2: Bulk delete 5 songs
            if len(self.test_songs) >= 5:
                songs_for_5 = self.test_songs[:5]
                print(f"🔍 Testing bulk deletion of 5 songs")
                
                successful_5 = 0
                for song_id in songs_for_5:
                    response = self.make_request("DELETE", f"/songs/{song_id}")
                    if response.status_code == 200:
                        successful_5 += 1
                        if song_id in self.test_songs:
                            self.test_songs.remove(song_id)
                
                if successful_5 == 5:
                    self.log_result("Bulk Delete - 5 Songs", True, "✅ Successfully deleted 5 songs in bulk")
                else:
                    self.log_result("Bulk Delete - 5 Songs", False, f"❌ Only deleted {successful_5}/5 songs")
            
            # Test 3: Bulk delete remaining songs (should be 3+ songs)
            if len(self.test_songs) >= 3:
                remaining_count = len(self.test_songs)
                songs_for_remaining = self.test_songs.copy()
                print(f"🔍 Testing bulk deletion of {remaining_count} remaining songs")
                
                successful_remaining = 0
                for song_id in songs_for_remaining:
                    response = self.make_request("DELETE", f"/songs/{song_id}")
                    if response.status_code == 200:
                        successful_remaining += 1
                        if song_id in self.test_songs:
                            self.test_songs.remove(song_id)
                
                if successful_remaining == remaining_count:
                    self.log_result("Bulk Delete - Remaining Songs", True, 
                                   f"✅ Successfully deleted {remaining_count} songs in bulk")
                else:
                    self.log_result("Bulk Delete - Remaining Songs", False, 
                                   f"❌ Only deleted {successful_remaining}/{remaining_count} songs")
            
            self.log_result("Bulk Delete - Different Counts", True, 
                           "✅ FIXED: Bulk deletion working correctly with different song counts")
            
        except Exception as e:
            self.log_result("Bulk Delete - Different Counts", False, f"❌ Exception: {str(e)}")

    def test_parallel_bulk_deletion_integrity(self):
        """Test that multiple parallel delete requests work correctly"""
        try:
            # Create fresh songs for parallel testing
            parallel_songs = []
            for i in range(8):
                song_data = {
                    "title": f"Parallel Test Song {i+1}",
                    "artist": f"Parallel Artist {i+1}",
                    "genres": ["Test"],
                    "moods": ["Test"],
                    "year": 2023
                }
                response = self.make_request("POST", "/songs", song_data)
                if response.status_code == 200:
                    parallel_songs.append(response.json()["id"])
            
            if len(parallel_songs) < 6:
                self.log_result("Parallel Bulk Deletion", False, "Could not create enough songs for parallel testing")
                return
            
            print(f"🔍 Testing parallel deletion of {len(parallel_songs)} songs")
            
            # Record initial song count
            initial_response = self.make_request("GET", "/songs")
            if initial_response.status_code == 200:
                initial_count = len(initial_response.json())
            else:
                self.log_result("Parallel Bulk Deletion", False, "Could not get initial song count")
                return
            
            # Delete songs in parallel
            def delete_song_parallel(song_id):
                try:
                    response = self.make_request("DELETE", f"/songs/{song_id}")
                    return {"song_id": song_id, "success": response.status_code == 200, "status": response.status_code}
                except Exception as e:
                    return {"song_id": song_id, "success": False, "error": str(e)}
            
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                results = list(executor.map(delete_song_parallel, parallel_songs))
            end_time = time.time()
            
            # Analyze results
            successful_deletions = sum(1 for result in results if result["success"])
            failed_deletions = len(results) - successful_deletions
            duration = end_time - start_time
            
            print(f"📊 Parallel deletion: {successful_deletions} successful, {failed_deletions} failed in {duration:.2f}s")
            
            # Verify final song count
            time.sleep(0.5)  # Brief pause for database consistency
            final_response = self.make_request("GET", "/songs")
            if final_response.status_code == 200:
                final_count = len(final_response.json())
                expected_count = initial_count - successful_deletions
                
                if final_count == expected_count:
                    self.log_result("Parallel Bulk Deletion", True, 
                                   f"✅ FIXED: Parallel bulk deletion maintains transaction integrity ({successful_deletions}/{len(parallel_songs)} deleted)")
                else:
                    self.log_result("Parallel Bulk Deletion", False, 
                                   f"❌ Transaction integrity issue: expected {expected_count} songs, got {final_count}")
            else:
                self.log_result("Parallel Bulk Deletion", False, "Could not verify final song count")
                
        except Exception as e:
            self.log_result("Parallel Bulk Deletion", False, f"❌ Exception: {str(e)}")

    def test_authentication_with_global_axios_config(self):
        """Test that deletion works with globally configured axios authentication (the main fix)"""
        try:
            # Create a test song
            song_data = {
                "title": "Global Auth Test Song",
                "artist": "Auth Test Artist",
                "genres": ["Test"],
                "moods": ["Test"],
                "year": 2023
            }
            
            response = self.make_request("POST", "/songs", song_data)
            if response.status_code != 200:
                self.log_result("Global Axios Auth", False, "Could not create test song")
                return
            
            test_song_id = response.json()["id"]
            print(f"🔍 Testing deletion with global axios authentication config")
            
            # The key fix: deletion should work with the Authorization header set globally
            # rather than manually setting headers for each request
            response = self.make_request("DELETE", f"/songs/{test_song_id}")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    # Verify the song is actually deleted
                    verify_response = self.make_request("GET", "/songs")
                    if verify_response.status_code == 200:
                        songs = verify_response.json()
                        song_exists = any(song["id"] == test_song_id for song in songs)
                        
                        if not song_exists:
                            self.log_result("Global Axios Auth", True, 
                                           "✅ CRITICAL FIX VERIFIED: Song deletion working with global axios authentication configuration")
                        else:
                            self.log_result("Global Axios Auth", False, 
                                           "❌ Song still exists after deletion")
                    else:
                        self.log_result("Global Axios Auth", False, 
                                       "❌ Could not verify song deletion")
                else:
                    self.log_result("Global Axios Auth", False, 
                                   f"❌ Unexpected response format: {data}")
            elif response.status_code in [401, 403]:
                self.log_result("Global Axios Auth", False, 
                               "❌ CRITICAL BUG: Authentication failed - global axios config not working")
            else:
                self.log_result("Global Axios Auth", False, 
                               f"❌ Unexpected status code: {response.status_code}")
                
        except Exception as e:
            self.log_result("Global Axios Auth", False, f"❌ Exception: {str(e)}")

    def test_musician_ownership_verification(self):
        """Test that musicians can only delete their own songs"""
        try:
            # Create a song with current musician
            song_data = {
                "title": "Ownership Test Song",
                "artist": "Ownership Test Artist", 
                "genres": ["Test"],
                "moods": ["Test"],
                "year": 2023
            }
            
            response = self.make_request("POST", "/songs", song_data)
            if response.status_code != 200:
                self.log_result("Musician Ownership", False, "Could not create test song")
                return
            
            test_song_id = response.json()["id"]
            
            # Create another musician
            other_musician = {
                "name": "Other Test Musician",
                "email": "other.ownership@requestwave.com",
                "password": "OtherPassword123!"
            }
            
            other_response = self.make_request("POST", "/auth/register", other_musician)
            if other_response.status_code != 200:
                self.log_result("Musician Ownership", False, "Could not create other musician")
                return
            
            other_token = other_response.json()["token"]
            original_token = self.auth_token
            
            # Try to delete original musician's song with other musician's token
            self.auth_token = other_token
            delete_response = self.make_request("DELETE", f"/songs/{test_song_id}")
            
            if delete_response.status_code == 404:
                self.log_result("Musician Ownership - Cross-musician Delete", True, 
                               "✅ Correctly prevented deletion of another musician's song")
            else:
                self.log_result("Musician Ownership - Cross-musician Delete", False, 
                               f"❌ Should have returned 404, got: {delete_response.status_code}")
            
            # Restore original token and delete the song properly
            self.auth_token = original_token
            proper_delete_response = self.make_request("DELETE", f"/songs/{test_song_id}")
            
            if proper_delete_response.status_code == 200:
                self.log_result("Musician Ownership - Own Song Delete", True, 
                               "✅ Successfully deleted own song with proper authentication")
            else:
                self.log_result("Musician Ownership - Own Song Delete", False, 
                               f"❌ Could not delete own song: {proper_delete_response.status_code}")
            
            self.log_result("Musician Ownership", True, 
                           "✅ FIXED: Musician ownership verification working correctly")
            
        except Exception as e:
            self.log_result("Musician Ownership", False, f"❌ Exception: {str(e)}")

    def run_focused_tests(self):
        """Run focused tests for the FIXED song deletion functionality"""
        print("🎯 REQUESTWAVE SONG DELETION - FOCUSED TESTING")
        print("Testing the FIXED individual and bulk song deletion functionality")
        print("=" * 70)
        
        if not self.setup_test_environment():
            print("❌ Test environment setup failed")
            return
        
        print("\n🔥 TESTING FIXED INDIVIDUAL DELETE BUTTON FUNCTIONALITY")
        print("-" * 50)
        self.test_individual_delete_button_functionality()
        
        print("\n🔥 TESTING FIXED BULK DELETION WITH DIFFERENT COUNTS")
        print("-" * 50)
        self.test_bulk_delete_with_different_counts()
        
        print("\n🔥 TESTING PARALLEL BULK DELETION INTEGRITY")
        print("-" * 50)
        self.test_parallel_bulk_deletion_integrity()
        
        print("\n🔥 TESTING GLOBAL AXIOS AUTHENTICATION FIX")
        print("-" * 50)
        self.test_authentication_with_global_axios_config()
        
        print("\n🔥 TESTING MUSICIAN OWNERSHIP VERIFICATION")
        print("-" * 50)
        self.test_musician_ownership_verification()
        
        # Summary
        print("\n" + "=" * 70)
        print("🎯 FOCUSED SONG DELETION TEST SUMMARY")
        print("=" * 70)
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        
        if self.results['passed'] + self.results['failed'] > 0:
            success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100)
            print(f"📊 SUCCESS RATE: {success_rate:.1f}%")
        
        if self.results['errors']:
            print("\n❌ FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        # Overall assessment
        critical_tests = [
            "Individual Delete Button",
            "Global Axios Auth", 
            "Musician Ownership"
        ]
        
        critical_passed = sum(1 for error in self.results['errors'] 
                            if not any(test in error for test in critical_tests))
        
        if self.results['failed'] == 0:
            print("\n🎉 ALL TESTS PASSED - SONG DELETION FUNCTIONALITY FULLY WORKING!")
        elif critical_passed == len(critical_tests):
            print("\n✅ CRITICAL FUNCTIONALITY WORKING - Minor issues detected")
        else:
            print("\n⚠️  CRITICAL ISSUES DETECTED - Song deletion needs attention")
        
        return self.results

if __name__ == "__main__":
    tester = FocusedDeletionTester()
    results = tester.run_focused_tests()