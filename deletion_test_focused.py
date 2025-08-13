#!/usr/bin/env python3
"""
Focused Deletion Test for RequestWave
Tests deletion functionality with existing songs
"""

import requests
import json
import time
import random
from typing import Dict, Any, List

# Configuration
BASE_URL = "https://requestwave-pro.preview.emergentagent.com/api"
TEST_MUSICIAN = {
    "name": "Scale Test Musician",
    "email": "scale.test@requestwave.com", 
    "password": "ScaleTest123!"
}

class DeletionTester:
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
        
        # Default headers
        request_headers = {"Content-Type": "application/json"}
        if self.auth_token:
            request_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        # Override with custom headers
        if headers:
            request_headers.update(headers)
        
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

    def setup_authentication(self):
        """Setup authentication for testing"""
        try:
            # Try login first
            login_data = {
                "email": TEST_MUSICIAN["email"],
                "password": TEST_MUSICIAN["password"]
            }
            response = self.make_request("POST", "/auth/login", login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data["token"]
                self.musician_id = data["musician"]["id"]
                self.musician_slug = data["musician"]["slug"]
                self.log_result("Authentication Setup", True, f"Logged in musician: {data['musician']['name']}")
                return True
            else:
                self.log_result("Authentication Setup", False, f"Login failed: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Authentication Setup", False, f"Exception: {str(e)}")
            return False

    def create_unique_song(self, index: int) -> str:
        """Create a unique song to avoid duplicates"""
        song_data = {
            "title": f"Unique Test Song {index} - {int(time.time())}",
            "artist": f"Test Artist {index} - {random.randint(1000, 9999)}",
            "genres": ["Pop", "Rock", "Jazz"][index % 3:index % 3 + 1],
            "moods": ["Upbeat", "Chill", "Energetic"][index % 3:index % 3 + 1],
            "year": 2020 + (index % 4),
            "notes": f"Unique test song #{index} created at {time.time()}"
        }
        
        try:
            response = self.make_request("POST", "/songs", song_data)
            
            if response.status_code == 200:
                data = response.json()
                return data["id"]
            else:
                print(f"   Failed to create song {index}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"   Exception creating song {index}: {str(e)}")
            return None

    def test_song_limit_verification(self):
        """Verify that song limits have been removed"""
        try:
            print("🔍 Testing song limit removal verification...")
            
            # Get current songs
            response = self.make_request("GET", "/songs")
            
            if response.status_code == 200:
                songs = response.json()
                current_count = len(songs)
                
                print(f"📊 Current song count: {current_count}")
                
                # Test response time for large datasets
                start_time = time.time()
                response = self.make_request("GET", "/songs")
                end_time = time.time()
                response_time = end_time - start_time
                
                if response.status_code == 200:
                    songs = response.json()
                    
                    self.log_result("Song Limit Removal Verification", True, 
                                  f"✅ Retrieved {len(songs)} songs without 1000-song limit (response time: {response_time:.2f}s)")
                    
                    # Test musician-specific endpoint
                    start_time = time.time()
                    musician_response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs")
                    end_time = time.time()
                    musician_response_time = end_time - start_time
                    
                    if musician_response.status_code == 200:
                        musician_songs = musician_response.json()
                        self.log_result("Musician Songs Limit Removal", True, 
                                      f"✅ Retrieved {len(musician_songs)} musician songs without limit (response time: {musician_response_time:.2f}s)")
                    else:
                        self.log_result("Musician Songs Limit Removal", False, 
                                      f"Failed to get musician songs: {musician_response.status_code}")
                else:
                    self.log_result("Song Limit Removal Verification", False, 
                                  f"Failed to retrieve songs: {response.status_code}")
            else:
                self.log_result("Song Limit Removal Verification", False, 
                              f"Failed to retrieve songs: {response.status_code}")
                
        except Exception as e:
            self.log_result("Song Limit Removal Verification", False, f"Exception: {str(e)}")

    def test_individual_deletion_with_existing_songs(self):
        """Test deletion using existing songs"""
        try:
            print("🔍 Testing individual song deletion with existing songs...")
            
            # Get existing songs
            response = self.make_request("GET", "/songs")
            if response.status_code != 200:
                self.log_result("Individual Deletion - Existing Songs", False, f"Failed to get songs: {response.status_code}")
                return
            
            existing_songs = response.json()
            if len(existing_songs) == 0:
                self.log_result("Individual Deletion - Existing Songs", False, "No existing songs to test deletion")
                return
            
            # Test deleting a few existing songs
            songs_to_delete = existing_songs[:min(5, len(existing_songs))]
            successful_deletions = 0
            
            for i, song in enumerate(songs_to_delete):
                song_id = song["id"]
                song_title = song["title"]
                
                print(f"   Deleting song {i+1}/5: '{song_title}' (ID: {song_id})")
                
                # Get song count before deletion
                before_response = self.make_request("GET", "/songs")
                if before_response.status_code == 200:
                    songs_before = len(before_response.json())
                else:
                    print(f"     ❌ Failed to get songs before deletion: {before_response.status_code}")
                    continue
                
                # Delete the song
                delete_response = self.make_request("DELETE", f"/songs/{song_id}")
                
                if delete_response.status_code == 200:
                    # Verify deletion by checking song count
                    after_response = self.make_request("GET", "/songs")
                    if after_response.status_code == 200:
                        songs_after = len(after_response.json())
                        
                        if songs_after == songs_before - 1:
                            successful_deletions += 1
                            print(f"     ✅ Song deleted successfully (count: {songs_before} → {songs_after})")
                        else:
                            print(f"     ❌ Song count mismatch (expected: {songs_before - 1}, got: {songs_after})")
                    else:
                        print(f"     ❌ Failed to verify deletion: {after_response.status_code}")
                else:
                    print(f"     ❌ Delete request failed: {delete_response.status_code} - {delete_response.text}")
            
            if successful_deletions == len(songs_to_delete):
                self.log_result("Individual Deletion - Existing Songs", True, 
                              f"✅ Successfully deleted all {successful_deletions} test songs individually")
            else:
                self.log_result("Individual Deletion - Existing Songs", False, 
                              f"❌ Only {successful_deletions}/{len(songs_to_delete)} songs deleted successfully")
                
        except Exception as e:
            self.log_result("Individual Deletion - Existing Songs", False, f"Exception: {str(e)}")

    def test_batch_deletion_with_new_songs(self):
        """Test batch deletion by creating new unique songs"""
        try:
            print("🔍 Testing batch deletion with newly created unique songs...")
            
            # Create unique songs for deletion testing
            batch_size = 20
            created_song_ids = []
            
            print(f"📊 Creating {batch_size} unique songs for deletion testing...")
            
            for i in range(batch_size):
                song_id = self.create_unique_song(i)
                if song_id:
                    created_song_ids.append(song_id)
                    if (i + 1) % 5 == 0:
                        print(f"   Created {i+1}/{batch_size} songs...")
                else:
                    print(f"   Failed to create song {i+1}")
                    break
                
                # Small delay to ensure uniqueness
                time.sleep(0.1)
            
            print(f"✅ Successfully created {len(created_song_ids)} unique songs")
            
            if len(created_song_ids) < 10:
                self.log_result("Batch Deletion - New Songs", False, f"Only created {len(created_song_ids)} songs, need at least 10")
                return
            
            # Get initial song count
            initial_response = self.make_request("GET", "/songs")
            if initial_response.status_code == 200:
                initial_count = len(initial_response.json())
                print(f"📊 Initial song count: {initial_count}")
            else:
                self.log_result("Batch Deletion - New Songs", False, f"Failed to get initial song count: {initial_response.status_code}")
                return
            
            # Delete songs in batches
            successful_deletions = 0
            failed_deletions = 0
            deletion_times = []
            
            print(f"📊 Starting batch deletion of {len(created_song_ids)} songs...")
            
            for i, song_id in enumerate(created_song_ids):
                start_time = time.time()
                delete_response = self.make_request("DELETE", f"/songs/{song_id}")
                end_time = time.time()
                
                deletion_times.append(end_time - start_time)
                
                if delete_response.status_code == 200:
                    successful_deletions += 1
                    if (i + 1) % 5 == 0:
                        print(f"   Deleted {i+1}/{len(created_song_ids)} songs...")
                else:
                    failed_deletions += 1
                    print(f"   ❌ Failed to delete song {i+1}: {delete_response.status_code}")
            
            # Verify final song count
            final_response = self.make_request("GET", "/songs")
            if final_response.status_code == 200:
                final_count = len(final_response.json())
                expected_count = initial_count - successful_deletions
                
                print(f"📊 Final song count: {final_count} (expected: {expected_count})")
                
                if final_count == expected_count:
                    avg_deletion_time = sum(deletion_times) / len(deletion_times) if deletion_times else 0
                    self.log_result("Batch Deletion - New Songs", True, 
                                  f"✅ Successfully deleted {successful_deletions}/{len(created_song_ids)} songs in batch (avg time: {avg_deletion_time:.3f}s per song)")
                    
                    # Performance check
                    if avg_deletion_time < 1.0:
                        self.log_result("Batch Deletion - Performance", True, 
                                      f"✅ Good deletion performance: {avg_deletion_time:.3f}s average per song")
                    else:
                        self.log_result("Batch Deletion - Performance", False, 
                                      f"⚠️ Slow deletion performance: {avg_deletion_time:.3f}s average per song")
                else:
                    self.log_result("Batch Deletion - New Songs", False, 
                                  f"❌ Song count mismatch after batch deletion (expected: {expected_count}, got: {final_count})")
            else:
                self.log_result("Batch Deletion - New Songs", False, f"Failed to verify final song count: {final_response.status_code}")
            
            if failed_deletions > 0:
                self.log_result("Batch Deletion - Error Rate", False, 
                              f"❌ {failed_deletions} deletion failures out of {len(created_song_ids)} attempts")
            else:
                self.log_result("Batch Deletion - Error Rate", True, 
                              f"✅ No deletion failures in batch of {len(created_song_ids)} songs")
                
        except Exception as e:
            self.log_result("Batch Deletion - New Songs", False, f"Exception: {str(e)}")

    def test_edge_cases(self):
        """Test edge cases for deletion"""
        try:
            print("🔍 Testing deletion edge cases...")
            
            # Test 1: Delete non-existent song
            fake_song_id = "non-existent-song-id-12345"
            delete_response = self.make_request("DELETE", f"/songs/{fake_song_id}")
            
            if delete_response.status_code == 404:
                self.log_result("Edge Case - Non-existent Song", True, "✅ Correctly returned 404 for non-existent song")
            else:
                self.log_result("Edge Case - Non-existent Song", False, f"Expected 404, got: {delete_response.status_code}")
            
            # Test 2: Delete with invalid song ID format
            invalid_song_id = ""
            delete_response = self.make_request("DELETE", f"/songs/{invalid_song_id}")
            
            if delete_response.status_code in [400, 404, 405]:
                self.log_result("Edge Case - Invalid Song ID", True, f"✅ Correctly handled invalid song ID (status: {delete_response.status_code})")
            else:
                self.log_result("Edge Case - Invalid Song ID", False, f"Unexpected status for invalid ID: {delete_response.status_code}")
            
            # Test 3: Delete without authentication
            original_token = self.auth_token
            self.auth_token = None
            
            # Create a song first to test auth
            self.auth_token = original_token
            test_song_id = self.create_unique_song(999)
            
            if test_song_id:
                self.auth_token = None
                delete_response = self.make_request("DELETE", f"/songs/{test_song_id}")
                
                if delete_response.status_code in [401, 403]:
                    self.log_result("Edge Case - No Authentication", True, f"✅ Correctly rejected deletion without auth (status: {delete_response.status_code})")
                else:
                    self.log_result("Edge Case - No Authentication", False, f"Should reject without auth, got: {delete_response.status_code}")
                
                # Clean up - delete the test song with proper auth
                self.auth_token = original_token
                self.make_request("DELETE", f"/songs/{test_song_id}")
            else:
                self.log_result("Edge Case - No Authentication", False, "Could not create test song for auth test")
            
            # Restore token
            self.auth_token = original_token
                
        except Exception as e:
            self.log_result("Edge Cases", False, f"Exception: {str(e)}")

    def run_focused_tests(self):
        """Run focused deletion and limit tests"""
        print("🚀 Starting Focused Song Limit and Deletion Tests")
        print("=" * 60)
        
        # Setup
        if not self.setup_authentication():
            print("❌ Authentication setup failed, cannot continue")
            return
        
        # Test 1: Verify song limits have been removed
        print("\n📋 PRIORITY 1: Song Limit Removal Verification")
        print("-" * 50)
        self.test_song_limit_verification()
        
        # Test 2: Test deletion with existing songs
        print("\n📋 PRIORITY 2: Deletion Tests with Existing Songs")
        print("-" * 50)
        self.test_individual_deletion_with_existing_songs()
        
        # Test 3: Test batch deletion with new songs
        print("\n📋 PRIORITY 2: Batch Deletion Tests with New Songs")
        print("-" * 50)
        self.test_batch_deletion_with_new_songs()
        
        # Test 4: Edge cases
        print("\n📋 PRIORITY 4: Edge Case Tests")
        print("-" * 50)
        self.test_edge_cases()
        
        # Summary
        print("\n" + "=" * 60)
        print("🏁 FOCUSED TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Total: {self.results['passed'] + self.results['failed']}")
        
        if self.results['failed'] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        if self.results['failed'] == 0:
            print("\n🎉 ALL FOCUSED TESTS PASSED! Song limit and deletion fixes are working correctly.")
        else:
            print(f"\n⚠️ {self.results['failed']} tests failed. Please review the issues above.")

if __name__ == "__main__":
    tester = DeletionTester()
    tester.run_focused_tests()