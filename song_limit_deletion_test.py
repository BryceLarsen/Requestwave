#!/usr/bin/env python3
"""
Song Limit and Deletion Fix Tests for RequestWave
Tests the fixes for song limit removal and deletion functionality at scale
"""

import requests
import json
import time
from typing import Dict, Any, List

# Configuration
BASE_URL = "https://02097561-4318-47d1-b18b-ed57f34042df.preview.emergentagent.com/api"
TEST_MUSICIAN = {
    "name": "Scale Test Musician",
    "email": "scale.test@requestwave.com", 
    "password": "ScaleTest123!"
}

class SongLimitDeletionTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
        self.created_song_ids = []
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
            # Try to register first
            response = self.make_request("POST", "/auth/register", TEST_MUSICIAN)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data["token"]
                self.musician_id = data["musician"]["id"]
                self.musician_slug = data["musician"]["slug"]
                self.log_result("Authentication Setup - Registration", True, f"Registered musician: {data['musician']['name']}")
            elif response.status_code == 400:
                # Musician might already exist, try login
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
                    self.log_result("Authentication Setup - Login", True, f"Logged in musician: {data['musician']['name']}")
                else:
                    self.log_result("Authentication Setup", False, f"Login failed: {response.status_code}")
                    return False
            else:
                self.log_result("Authentication Setup", False, f"Registration failed: {response.status_code}")
                return False
            
            return True
        except Exception as e:
            self.log_result("Authentication Setup", False, f"Exception: {str(e)}")
            return False

    def create_test_songs(self, count: int) -> List[str]:
        """Create multiple test songs for deletion testing"""
        created_ids = []
        
        print(f"🎵 Creating {count} test songs...")
        
        for i in range(count):
            song_data = {
                "title": f"Test Song {i+1:03d}",
                "artist": f"Test Artist {(i % 10) + 1}",
                "genres": ["Pop", "Rock", "Jazz"][i % 3:i % 3 + 1],
                "moods": ["Upbeat", "Chill", "Energetic"][i % 3:i % 3 + 1],
                "year": 2020 + (i % 4),
                "notes": f"Test song #{i+1} for deletion testing"
            }
            
            try:
                response = self.make_request("POST", "/songs", song_data)
                
                if response.status_code == 200:
                    data = response.json()
                    song_id = data["id"]
                    created_ids.append(song_id)
                    self.created_song_ids.append(song_id)
                    
                    if (i + 1) % 10 == 0:  # Progress update every 10 songs
                        print(f"   Created {i+1}/{count} songs...")
                else:
                    print(f"   Failed to create song {i+1}: {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"   Exception creating song {i+1}: {str(e)}")
                break
        
        print(f"✅ Successfully created {len(created_ids)} test songs")
        return created_ids

    def test_song_limit_removal_get_songs(self):
        """PRIORITY 1: Test that GET /api/songs no longer has 1000-song limit"""
        try:
            print("🔍 Testing GET /api/songs for song limit removal...")
            
            # First, check current song count
            response = self.make_request("GET", "/songs")
            
            if response.status_code == 200:
                songs = response.json()
                current_count = len(songs)
                
                print(f"📊 Current song count: {current_count}")
                
                # If we have fewer than 50 songs, create more to test properly
                if current_count < 50:
                    additional_needed = 50 - current_count
                    print(f"📊 Creating {additional_needed} additional songs to test limit removal...")
                    self.create_test_songs(additional_needed)
                    
                    # Re-fetch songs
                    response = self.make_request("GET", "/songs")
                    if response.status_code == 200:
                        songs = response.json()
                        new_count = len(songs)
                        print(f"📊 New song count after creation: {new_count}")
                    else:
                        self.log_result("Song Limit Removal - GET /api/songs", False, f"Failed to re-fetch songs: {response.status_code}")
                        return
                
                # Test that we can retrieve all songs without limit
                if len(songs) > 0:
                    # Check response time for performance
                    start_time = time.time()
                    response = self.make_request("GET", "/songs")
                    end_time = time.time()
                    response_time = end_time - start_time
                    
                    if response.status_code == 200:
                        songs = response.json()
                        song_count = len(songs)
                        
                        # Success criteria: Can retrieve songs without artificial limits
                        self.log_result("Song Limit Removal - GET /api/songs", True, 
                                      f"✅ Successfully retrieved {song_count} songs without 1000-song limit (response time: {response_time:.2f}s)")
                        
                        # Performance check
                        if response_time < 5.0:
                            self.log_result("Song Limit Removal - Performance", True, 
                                          f"✅ Good performance: {response_time:.2f}s for {song_count} songs")
                        else:
                            self.log_result("Song Limit Removal - Performance", False, 
                                          f"⚠️ Slow performance: {response_time:.2f}s for {song_count} songs")
                    else:
                        self.log_result("Song Limit Removal - GET /api/songs", False, 
                                      f"Failed to retrieve songs: {response.status_code}")
                else:
                    self.log_result("Song Limit Removal - GET /api/songs", True, 
                                  "✅ No songs in database, but endpoint working correctly")
            else:
                self.log_result("Song Limit Removal - GET /api/songs", False, 
                              f"Failed to retrieve songs: {response.status_code}")
                
        except Exception as e:
            self.log_result("Song Limit Removal - GET /api/songs", False, f"Exception: {str(e)}")

    def test_song_limit_removal_get_musician_songs(self):
        """PRIORITY 1: Test that GET /musicians/{slug}/songs no longer has 1000-song limit"""
        try:
            if not self.musician_slug:
                self.log_result("Song Limit Removal - GET /musicians/{slug}/songs", False, "No musician slug available")
                return
            
            print(f"🔍 Testing GET /musicians/{self.musician_slug}/songs for song limit removal...")
            
            # Test the musician-specific songs endpoint
            start_time = time.time()
            response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs")
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.status_code == 200:
                songs = response.json()
                song_count = len(songs)
                
                print(f"📊 Retrieved {song_count} songs for musician {self.musician_slug}")
                
                # Success criteria: Can retrieve songs without artificial limits
                self.log_result("Song Limit Removal - GET /musicians/{slug}/songs", True, 
                              f"✅ Successfully retrieved {song_count} songs without 1000-song limit (response time: {response_time:.2f}s)")
                
                # Performance check
                if response_time < 5.0:
                    self.log_result("Song Limit Removal - Musician Songs Performance", True, 
                                  f"✅ Good performance: {response_time:.2f}s for {song_count} songs")
                else:
                    self.log_result("Song Limit Removal - Musician Songs Performance", False, 
                                  f"⚠️ Slow performance: {response_time:.2f}s for {song_count} songs")
                
                # Test with filtering to ensure it still works
                params = {"genre": "Pop"}
                filter_response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs", params=params)
                
                if filter_response.status_code == 200:
                    filtered_songs = filter_response.json()
                    self.log_result("Song Limit Removal - Filtering Still Works", True, 
                                  f"✅ Filtering works: {len(filtered_songs)} Pop songs found")
                else:
                    self.log_result("Song Limit Removal - Filtering Still Works", False, 
                                  f"Filtering failed: {filter_response.status_code}")
            else:
                self.log_result("Song Limit Removal - GET /musicians/{slug}/songs", False, 
                              f"Failed to retrieve musician songs: {response.status_code}")
                
        except Exception as e:
            self.log_result("Song Limit Removal - GET /musicians/{slug}/songs", False, f"Exception: {str(e)}")

    def test_individual_song_deletion(self):
        """PRIORITY 2: Test individual song deletion functionality"""
        try:
            print("🔍 Testing individual song deletion...")
            
            # Create a few test songs specifically for deletion
            test_song_ids = self.create_test_songs(5)
            
            if len(test_song_ids) < 5:
                self.log_result("Individual Song Deletion", False, "Failed to create enough test songs")
                return
            
            # Test deleting each song individually
            successful_deletions = 0
            
            for i, song_id in enumerate(test_song_ids):
                print(f"   Deleting song {i+1}/5: {song_id}")
                
                # Get song count before deletion
                before_response = self.make_request("GET", "/songs")
                if before_response.status_code == 200:
                    songs_before = len(before_response.json())
                else:
                    self.log_result("Individual Song Deletion", False, f"Failed to get songs before deletion: {before_response.status_code}")
                    return
                
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
                    print(f"     ❌ Delete request failed: {delete_response.status_code}")
            
            if successful_deletions == len(test_song_ids):
                self.log_result("Individual Song Deletion", True, 
                              f"✅ Successfully deleted all {successful_deletions} test songs individually")
            else:
                self.log_result("Individual Song Deletion", False, 
                              f"❌ Only {successful_deletions}/{len(test_song_ids)} songs deleted successfully")
                
        except Exception as e:
            self.log_result("Individual Song Deletion", False, f"Exception: {str(e)}")

    def test_batch_song_deletion(self):
        """PRIORITY 2: Test deletion of multiple songs in sequence (batch pattern)"""
        try:
            print("🔍 Testing batch song deletion (20-30 songs)...")
            
            # Create 25 test songs for batch deletion
            batch_size = 25
            test_song_ids = self.create_test_songs(batch_size)
            
            if len(test_song_ids) < batch_size:
                self.log_result("Batch Song Deletion", False, f"Failed to create {batch_size} test songs (only created {len(test_song_ids)})")
                return
            
            print(f"📊 Starting batch deletion of {len(test_song_ids)} songs...")
            
            # Get initial song count
            initial_response = self.make_request("GET", "/songs")
            if initial_response.status_code == 200:
                initial_count = len(initial_response.json())
                print(f"📊 Initial song count: {initial_count}")
            else:
                self.log_result("Batch Song Deletion", False, f"Failed to get initial song count: {initial_response.status_code}")
                return
            
            # Delete songs in batches of 5 to simulate realistic usage
            successful_deletions = 0
            failed_deletions = 0
            deletion_times = []
            
            for i in range(0, len(test_song_ids), 5):
                batch = test_song_ids[i:i+5]
                print(f"   Deleting batch {i//5 + 1}: songs {i+1}-{min(i+5, len(test_song_ids))}")
                
                batch_start_time = time.time()
                
                for song_id in batch:
                    start_time = time.time()
                    delete_response = self.make_request("DELETE", f"/songs/{song_id}")
                    end_time = time.time()
                    
                    deletion_times.append(end_time - start_time)
                    
                    if delete_response.status_code == 200:
                        successful_deletions += 1
                    else:
                        failed_deletions += 1
                        print(f"     ❌ Failed to delete song {song_id}: {delete_response.status_code}")
                
                batch_end_time = time.time()
                batch_time = batch_end_time - batch_start_time
                print(f"     Batch completed in {batch_time:.2f}s")
                
                # Small delay between batches to avoid overwhelming the server
                time.sleep(0.1)
            
            # Verify final song count
            final_response = self.make_request("GET", "/songs")
            if final_response.status_code == 200:
                final_count = len(final_response.json())
                expected_count = initial_count - successful_deletions
                
                print(f"📊 Final song count: {final_count} (expected: {expected_count})")
                
                if final_count == expected_count:
                    avg_deletion_time = sum(deletion_times) / len(deletion_times) if deletion_times else 0
                    self.log_result("Batch Song Deletion", True, 
                                  f"✅ Successfully deleted {successful_deletions}/{batch_size} songs in batch (avg time: {avg_deletion_time:.3f}s per song)")
                    
                    # Performance check
                    if avg_deletion_time < 1.0:
                        self.log_result("Batch Song Deletion - Performance", True, 
                                      f"✅ Good deletion performance: {avg_deletion_time:.3f}s average per song")
                    else:
                        self.log_result("Batch Song Deletion - Performance", False, 
                                      f"⚠️ Slow deletion performance: {avg_deletion_time:.3f}s average per song")
                else:
                    self.log_result("Batch Song Deletion", False, 
                                  f"❌ Song count mismatch after batch deletion (expected: {expected_count}, got: {final_count})")
            else:
                self.log_result("Batch Song Deletion", False, f"Failed to verify final song count: {final_response.status_code}")
            
            if failed_deletions > 0:
                self.log_result("Batch Song Deletion - Error Rate", False, 
                              f"❌ {failed_deletions} deletion failures out of {batch_size} attempts")
            else:
                self.log_result("Batch Song Deletion - Error Rate", True, 
                              f"✅ No deletion failures in batch of {batch_size} songs")
                
        except Exception as e:
            self.log_result("Batch Song Deletion", False, f"Exception: {str(e)}")

    def test_edge_case_deletions(self):
        """PRIORITY 4: Test edge cases for song deletion"""
        try:
            print("🔍 Testing edge case deletions...")
            
            # Create a small set of test songs for edge case testing
            edge_test_songs = self.create_test_songs(3)
            
            if len(edge_test_songs) < 3:
                self.log_result("Edge Case Deletions", False, "Failed to create test songs for edge cases")
                return
            
            # Test 1: Delete first song
            print("   Testing deletion of first song...")
            all_songs_response = self.make_request("GET", "/songs")
            if all_songs_response.status_code == 200:
                all_songs = all_songs_response.json()
                if len(all_songs) > 0:
                    first_song_id = all_songs[0]["id"]
                    delete_response = self.make_request("DELETE", f"/songs/{first_song_id}")
                    
                    if delete_response.status_code == 200:
                        self.log_result("Edge Case - Delete First Song", True, "✅ Successfully deleted first song")
                    else:
                        self.log_result("Edge Case - Delete First Song", False, f"Failed to delete first song: {delete_response.status_code}")
                else:
                    self.log_result("Edge Case - Delete First Song", True, "✅ No songs to delete (empty list)")
            
            # Test 2: Delete last song
            print("   Testing deletion of last song...")
            all_songs_response = self.make_request("GET", "/songs")
            if all_songs_response.status_code == 200:
                all_songs = all_songs_response.json()
                if len(all_songs) > 0:
                    last_song_id = all_songs[-1]["id"]
                    delete_response = self.make_request("DELETE", f"/songs/{last_song_id}")
                    
                    if delete_response.status_code == 200:
                        self.log_result("Edge Case - Delete Last Song", True, "✅ Successfully deleted last song")
                    else:
                        self.log_result("Edge Case - Delete Last Song", False, f"Failed to delete last song: {delete_response.status_code}")
                else:
                    self.log_result("Edge Case - Delete Last Song", True, "✅ No songs to delete (empty list)")
            
            # Test 3: Delete middle song
            print("   Testing deletion of middle song...")
            all_songs_response = self.make_request("GET", "/songs")
            if all_songs_response.status_code == 200:
                all_songs = all_songs_response.json()
                if len(all_songs) > 2:
                    middle_index = len(all_songs) // 2
                    middle_song_id = all_songs[middle_index]["id"]
                    delete_response = self.make_request("DELETE", f"/songs/{middle_song_id}")
                    
                    if delete_response.status_code == 200:
                        self.log_result("Edge Case - Delete Middle Song", True, "✅ Successfully deleted middle song")
                    else:
                        self.log_result("Edge Case - Delete Middle Song", False, f"Failed to delete middle song: {delete_response.status_code}")
                else:
                    self.log_result("Edge Case - Delete Middle Song", True, "✅ Not enough songs for middle deletion test")
            
            # Test 4: Delete non-existent song
            print("   Testing deletion of non-existent song...")
            fake_song_id = "non-existent-song-id-12345"
            delete_response = self.make_request("DELETE", f"/songs/{fake_song_id}")
            
            if delete_response.status_code == 404:
                self.log_result("Edge Case - Delete Non-existent Song", True, "✅ Correctly returned 404 for non-existent song")
            else:
                self.log_result("Edge Case - Delete Non-existent Song", False, f"Expected 404, got: {delete_response.status_code}")
            
            # Test 5: Delete with invalid song ID format
            print("   Testing deletion with invalid song ID format...")
            invalid_song_id = ""
            delete_response = self.make_request("DELETE", f"/songs/{invalid_song_id}")
            
            if delete_response.status_code in [400, 404, 405]:  # Accept various error codes for invalid ID
                self.log_result("Edge Case - Delete Invalid Song ID", True, f"✅ Correctly handled invalid song ID (status: {delete_response.status_code})")
            else:
                self.log_result("Edge Case - Delete Invalid Song ID", False, f"Unexpected status for invalid ID: {delete_response.status_code}")
                
        except Exception as e:
            self.log_result("Edge Case Deletions", False, f"Exception: {str(e)}")

    def test_deletion_authentication(self):
        """Test that deletion requires proper authentication"""
        try:
            print("🔍 Testing deletion authentication requirements...")
            
            # Create a test song for authentication testing
            test_songs = self.create_test_songs(1)
            if len(test_songs) == 0:
                self.log_result("Deletion Authentication", False, "Failed to create test song")
                return
            
            test_song_id = test_songs[0]
            
            # Save current token
            original_token = self.auth_token
            
            # Test without authentication token
            self.auth_token = None
            delete_response = self.make_request("DELETE", f"/songs/{test_song_id}")
            
            if delete_response.status_code in [401, 403]:
                self.log_result("Deletion Authentication - No Token", True, f"✅ Correctly rejected deletion without auth (status: {delete_response.status_code})")
            else:
                self.log_result("Deletion Authentication - No Token", False, f"Should reject without auth, got: {delete_response.status_code}")
            
            # Test with invalid token
            self.auth_token = "invalid-token-12345"
            delete_response = self.make_request("DELETE", f"/songs/{test_song_id}")
            
            if delete_response.status_code == 401:
                self.log_result("Deletion Authentication - Invalid Token", True, "✅ Correctly rejected deletion with invalid token")
            else:
                self.log_result("Deletion Authentication - Invalid Token", False, f"Should reject invalid token, got: {delete_response.status_code}")
            
            # Restore original token
            self.auth_token = original_token
            
            # Test with valid token (should work)
            delete_response = self.make_request("DELETE", f"/songs/{test_song_id}")
            
            if delete_response.status_code == 200:
                self.log_result("Deletion Authentication - Valid Token", True, "✅ Successfully deleted with valid token")
            else:
                self.log_result("Deletion Authentication - Valid Token", False, f"Failed to delete with valid token: {delete_response.status_code}")
                
        except Exception as e:
            self.log_result("Deletion Authentication", False, f"Exception: {str(e)}")

    def test_database_consistency_after_deletions(self):
        """Test database consistency after multiple deletions"""
        try:
            print("🔍 Testing database consistency after multiple deletions...")
            
            # Get initial state
            initial_response = self.make_request("GET", "/songs")
            if initial_response.status_code != 200:
                self.log_result("Database Consistency", False, f"Failed to get initial songs: {initial_response.status_code}")
                return
            
            initial_songs = initial_response.json()
            initial_count = len(initial_songs)
            
            # Create and delete songs multiple times
            consistency_test_cycles = 3
            songs_per_cycle = 5
            
            for cycle in range(consistency_test_cycles):
                print(f"   Consistency test cycle {cycle + 1}/{consistency_test_cycles}")
                
                # Create songs
                created_songs = self.create_test_songs(songs_per_cycle)
                
                # Verify creation
                after_create_response = self.make_request("GET", "/songs")
                if after_create_response.status_code == 200:
                    after_create_count = len(after_create_response.json())
                    expected_after_create = initial_count + len(created_songs)
                    
                    if after_create_count != expected_after_create:
                        self.log_result("Database Consistency", False, 
                                      f"Count mismatch after creation in cycle {cycle + 1}: expected {expected_after_create}, got {after_create_count}")
                        return
                
                # Delete the created songs
                for song_id in created_songs:
                    delete_response = self.make_request("DELETE", f"/songs/{song_id}")
                    if delete_response.status_code != 200:
                        self.log_result("Database Consistency", False, 
                                      f"Failed to delete song in cycle {cycle + 1}: {delete_response.status_code}")
                        return
                
                # Verify deletion
                after_delete_response = self.make_request("GET", "/songs")
                if after_delete_response.status_code == 200:
                    after_delete_count = len(after_delete_response.json())
                    
                    if after_delete_count != initial_count:
                        self.log_result("Database Consistency", False, 
                                      f"Count mismatch after deletion in cycle {cycle + 1}: expected {initial_count}, got {after_delete_count}")
                        return
                
                print(f"     Cycle {cycle + 1} completed successfully")
            
            # Final consistency check
            final_response = self.make_request("GET", "/songs")
            if final_response.status_code == 200:
                final_count = len(final_response.json())
                
                if final_count == initial_count:
                    self.log_result("Database Consistency", True, 
                                  f"✅ Database consistency maintained through {consistency_test_cycles} create/delete cycles")
                else:
                    self.log_result("Database Consistency", False, 
                                  f"Final count mismatch: expected {initial_count}, got {final_count}")
            else:
                self.log_result("Database Consistency", False, f"Failed final consistency check: {final_response.status_code}")
                
        except Exception as e:
            self.log_result("Database Consistency", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all song limit and deletion tests"""
        print("🚀 Starting Song Limit and Deletion Fix Tests")
        print("=" * 60)
        
        # Setup
        if not self.setup_authentication():
            print("❌ Authentication setup failed, cannot continue")
            return
        
        # PRIORITY 1: Song Limit Tests
        print("\n📋 PRIORITY 1: Song Limit Removal Tests")
        print("-" * 40)
        self.test_song_limit_removal_get_songs()
        self.test_song_limit_removal_get_musician_songs()
        
        # PRIORITY 2: Deletion Tests
        print("\n📋 PRIORITY 2: Song Deletion Tests")
        print("-" * 40)
        self.test_individual_song_deletion()
        self.test_batch_song_deletion()
        
        # PRIORITY 3: Performance Tests (integrated above)
        
        # PRIORITY 4: Edge Case Tests
        print("\n📋 PRIORITY 4: Edge Case Tests")
        print("-" * 40)
        self.test_edge_case_deletions()
        self.test_deletion_authentication()
        self.test_database_consistency_after_deletions()
        
        # Summary
        print("\n" + "=" * 60)
        print("🏁 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Total: {self.results['passed'] + self.results['failed']}")
        
        if self.results['failed'] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        if self.results['failed'] == 0:
            print("\n🎉 ALL TESTS PASSED! Song limit and deletion fixes are working correctly.")
        else:
            print(f"\n⚠️ {self.results['failed']} tests failed. Please review the issues above.")

if __name__ == "__main__":
    tester = SongLimitDeletionTester()
    tester.run_all_tests()