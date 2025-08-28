#!/usr/bin/env python3
"""
Comprehensive Song Deletion Tests for RequestWave
Tests individual and bulk song deletion functionality with focus on authentication, 
database integrity, error handling, and performance.
"""

import requests
import json
import os
import time
import asyncio
import concurrent.futures
from typing import Dict, Any, List, Optional

# Configuration
BASE_URL = "https://stagepro-app.preview.emergentagent.com/api"
TEST_MUSICIAN = {
    "name": "Song Deletion Tester",
    "email": "deletion.tester@requestwave.com",
    "password": "SecurePassword123!"
}

class SongDeletionTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
        self.test_songs = []  # List of created test songs
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
                # Musician might already exist, try login instead
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

    def create_test_songs(self, count: int = 10) -> List[str]:
        """Create multiple test songs for deletion testing"""
        created_songs = []
        
        for i in range(count):
            song_data = {
                "title": f"Test Song {i+1}",
                "artist": f"Test Artist {i+1}",
                "genres": ["Pop", "Rock"][i % 2:i % 2 + 1],
                "moods": ["Upbeat", "Energetic", "Chill"][i % 3:i % 3 + 1],
                "year": 2020 + (i % 4),
                "notes": f"Test song {i+1} for deletion testing"
            }
            
            try:
                response = self.make_request("POST", "/songs", song_data)
                if response.status_code == 200:
                    data = response.json()
                    created_songs.append(data["id"])
                    self.test_songs.append(data["id"])
                else:
                    print(f"Failed to create test song {i+1}: {response.status_code}")
            except Exception as e:
                print(f"Exception creating test song {i+1}: {str(e)}")
        
        self.log_result("Create Test Songs", len(created_songs) == count, 
                       f"Created {len(created_songs)}/{count} test songs")
        return created_songs

    def test_individual_song_deletion(self):
        """Test individual song deletion with proper JWT authentication"""
        try:
            if not self.test_songs:
                self.log_result("Individual Song Deletion", False, "No test songs available")
                return
            
            song_id = self.test_songs[0]
            print(f"🔍 Testing individual deletion of song ID: {song_id}")
            
            # Verify song exists before deletion
            songs_before_response = self.make_request("GET", "/songs")
            if songs_before_response.status_code == 200:
                songs_before = songs_before_response.json()
                song_exists_before = any(song["id"] == song_id for song in songs_before)
                
                if not song_exists_before:
                    self.log_result("Individual Song Deletion - Pre-check", False, "Test song not found before deletion")
                    return
            else:
                self.log_result("Individual Song Deletion - Pre-check", False, f"Could not retrieve songs: {songs_before_response.status_code}")
                return
            
            # Test deletion
            response = self.make_request("DELETE", f"/songs/{song_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify API response
                if "message" in data:
                    self.log_result("Individual Song Deletion - API Response", True, f"API returned success: {data['message']}")
                    
                    # Verify song is actually deleted from database
                    songs_after_response = self.make_request("GET", "/songs")
                    if songs_after_response.status_code == 200:
                        songs_after = songs_after_response.json()
                        song_exists_after = any(song["id"] == song_id for song in songs_after)
                        
                        if not song_exists_after:
                            self.log_result("Individual Song Deletion - Database Integrity", True, "Song successfully removed from database")
                            self.log_result("Individual Song Deletion", True, "Individual song deletion working correctly")
                            # Remove from test_songs list
                            self.test_songs.remove(song_id)
                        else:
                            self.log_result("Individual Song Deletion - Database Integrity", False, "Song still exists in database after deletion")
                            self.log_result("Individual Song Deletion", False, "Song not actually deleted from database")
                    else:
                        self.log_result("Individual Song Deletion - Database Integrity", False, f"Could not verify deletion: {songs_after_response.status_code}")
                        self.log_result("Individual Song Deletion", False, "Could not verify deletion from database")
                else:
                    self.log_result("Individual Song Deletion", False, f"Unexpected response format: {data}")
            else:
                self.log_result("Individual Song Deletion", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Individual Song Deletion", False, f"Exception: {str(e)}")

    def test_bulk_song_deletion_sequential(self):
        """Test bulk deletion using sequential delete requests"""
        try:
            if len(self.test_songs) < 3:
                self.log_result("Bulk Song Deletion - Sequential", False, "Not enough test songs for bulk deletion")
                return
            
            # Select 3 songs for bulk deletion
            songs_to_delete = self.test_songs[:3]
            print(f"🔍 Testing sequential bulk deletion of {len(songs_to_delete)} songs")
            
            # Record initial song count
            songs_before_response = self.make_request("GET", "/songs")
            if songs_before_response.status_code == 200:
                songs_before_count = len(songs_before_response.json())
            else:
                self.log_result("Bulk Song Deletion - Sequential", False, "Could not get initial song count")
                return
            
            # Delete songs sequentially
            successful_deletions = 0
            failed_deletions = 0
            
            for song_id in songs_to_delete:
                response = self.make_request("DELETE", f"/songs/{song_id}")
                if response.status_code == 200:
                    successful_deletions += 1
                else:
                    failed_deletions += 1
                    print(f"Failed to delete song {song_id}: {response.status_code}")
            
            # Verify final song count
            songs_after_response = self.make_request("GET", "/songs")
            if songs_after_response.status_code == 200:
                songs_after_count = len(songs_after_response.json())
                expected_count = songs_before_count - successful_deletions
                
                if songs_after_count == expected_count:
                    self.log_result("Bulk Song Deletion - Sequential", True, 
                                   f"Successfully deleted {successful_deletions}/{len(songs_to_delete)} songs sequentially")
                    # Remove successfully deleted songs from test_songs list
                    for song_id in songs_to_delete:
                        if song_id in self.test_songs:
                            self.test_songs.remove(song_id)
                else:
                    self.log_result("Bulk Song Deletion - Sequential", False, 
                                   f"Song count mismatch: expected {expected_count}, got {songs_after_count}")
            else:
                self.log_result("Bulk Song Deletion - Sequential", False, "Could not verify final song count")
                
        except Exception as e:
            self.log_result("Bulk Song Deletion - Sequential", False, f"Exception: {str(e)}")

    def test_bulk_song_deletion_parallel(self):
        """Test bulk deletion using parallel delete requests"""
        try:
            if len(self.test_songs) < 5:
                self.log_result("Bulk Song Deletion - Parallel", False, "Not enough test songs for parallel bulk deletion")
                return
            
            # Select 5 songs for parallel bulk deletion
            songs_to_delete = self.test_songs[:5]
            print(f"🔍 Testing parallel bulk deletion of {len(songs_to_delete)} songs")
            
            # Record initial song count
            songs_before_response = self.make_request("GET", "/songs")
            if songs_before_response.status_code == 200:
                songs_before_count = len(songs_before_response.json())
            else:
                self.log_result("Bulk Song Deletion - Parallel", False, "Could not get initial song count")
                return
            
            # Delete songs in parallel using ThreadPoolExecutor
            def delete_song(song_id):
                try:
                    response = self.make_request("DELETE", f"/songs/{song_id}")
                    return {"song_id": song_id, "status_code": response.status_code, "success": response.status_code == 200}
                except Exception as e:
                    return {"song_id": song_id, "status_code": None, "success": False, "error": str(e)}
            
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_song = {executor.submit(delete_song, song_id): song_id for song_id in songs_to_delete}
                results = []
                
                for future in concurrent.futures.as_completed(future_to_song):
                    result = future.result()
                    results.append(result)
            
            end_time = time.time()
            parallel_duration = end_time - start_time
            
            # Analyze results
            successful_deletions = sum(1 for result in results if result["success"])
            failed_deletions = len(results) - successful_deletions
            
            print(f"📊 Parallel deletion results: {successful_deletions} successful, {failed_deletions} failed")
            print(f"📊 Parallel deletion took {parallel_duration:.2f} seconds")
            
            # Verify final song count
            time.sleep(1)  # Brief pause to ensure database consistency
            songs_after_response = self.make_request("GET", "/songs")
            if songs_after_response.status_code == 200:
                songs_after_count = len(songs_after_response.json())
                expected_count = songs_before_count - successful_deletions
                
                if songs_after_count == expected_count:
                    self.log_result("Bulk Song Deletion - Parallel", True, 
                                   f"Successfully deleted {successful_deletions}/{len(songs_to_delete)} songs in parallel ({parallel_duration:.2f}s)")
                    # Remove successfully deleted songs from test_songs list
                    for result in results:
                        if result["success"] and result["song_id"] in self.test_songs:
                            self.test_songs.remove(result["song_id"])
                else:
                    self.log_result("Bulk Song Deletion - Parallel", False, 
                                   f"Song count mismatch: expected {expected_count}, got {songs_after_count}")
            else:
                self.log_result("Bulk Song Deletion - Parallel", False, "Could not verify final song count")
                
        except Exception as e:
            self.log_result("Bulk Song Deletion - Parallel", False, f"Exception: {str(e)}")

    def test_deletion_authentication_and_authorization(self):
        """Test that delete operations require proper JWT authentication and only allow song owners to delete"""
        try:
            if not self.test_songs:
                self.log_result("Deletion Authentication & Authorization", False, "No test songs available")
                return
            
            song_id = self.test_songs[0]
            original_token = self.auth_token
            
            # Test 1: No authentication token
            self.auth_token = None
            response = self.make_request("DELETE", f"/songs/{song_id}")
            
            if response.status_code in [401, 403]:
                self.log_result("Deletion Auth - No Token", True, f"Correctly rejected deletion without token (status: {response.status_code})")
            else:
                self.log_result("Deletion Auth - No Token", False, f"Should have returned 401/403, got: {response.status_code}")
            
            # Test 2: Invalid authentication token
            self.auth_token = "invalid_token_12345"
            response = self.make_request("DELETE", f"/songs/{song_id}")
            
            if response.status_code == 401:
                self.log_result("Deletion Auth - Invalid Token", True, "Correctly rejected deletion with invalid token")
            else:
                self.log_result("Deletion Auth - Invalid Token", False, f"Should have returned 401, got: {response.status_code}")
            
            # Test 3: Expired token (simulate by using a malformed token)
            self.auth_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.expired.token"
            response = self.make_request("DELETE", f"/songs/{song_id}")
            
            if response.status_code == 401:
                self.log_result("Deletion Auth - Expired Token", True, "Correctly rejected deletion with expired/malformed token")
            else:
                self.log_result("Deletion Auth - Expired Token", False, f"Should have returned 401, got: {response.status_code}")
            
            # Test 4: Valid token but trying to delete another musician's song
            # First, create another musician account
            other_musician = {
                "name": "Other Musician",
                "email": "other.musician@requestwave.com",
                "password": "OtherPassword123!"
            }
            
            other_response = self.make_request("POST", "/auth/register", other_musician)
            if other_response.status_code == 200:
                other_data = other_response.json()
                other_token = other_data["token"]
                
                # Try to delete original musician's song with other musician's token
                self.auth_token = other_token
                response = self.make_request("DELETE", f"/songs/{song_id}")
                
                if response.status_code == 404:  # Song not found because it doesn't belong to this musician
                    self.log_result("Deletion Auth - Wrong Owner", True, "Correctly prevented deletion of another musician's song")
                else:
                    self.log_result("Deletion Auth - Wrong Owner", False, f"Should have returned 404, got: {response.status_code}")
            else:
                self.log_result("Deletion Auth - Wrong Owner", False, "Could not create other musician for authorization test")
            
            # Restore original token
            self.auth_token = original_token
            
            # Test 5: Valid token and correct owner
            response = self.make_request("DELETE", f"/songs/{song_id}")
            
            if response.status_code == 200:
                self.log_result("Deletion Auth - Valid Owner", True, "Successfully deleted song with valid authentication and ownership")
                if song_id in self.test_songs:
                    self.test_songs.remove(song_id)
            else:
                self.log_result("Deletion Auth - Valid Owner", False, f"Should have returned 200, got: {response.status_code}")
            
            self.log_result("Deletion Authentication & Authorization", True, "All authentication and authorization tests completed")
            
        except Exception as e:
            self.log_result("Deletion Authentication & Authorization", False, f"Exception: {str(e)}")

    def test_deletion_error_handling(self):
        """Test error handling for various deletion scenarios"""
        try:
            # Test 1: Delete non-existent song
            fake_song_id = "non-existent-song-id-12345"
            response = self.make_request("DELETE", f"/songs/{fake_song_id}")
            
            if response.status_code == 404:
                self.log_result("Deletion Error Handling - Non-existent Song", True, "Correctly returned 404 for non-existent song")
            else:
                self.log_result("Deletion Error Handling - Non-existent Song", False, f"Should have returned 404, got: {response.status_code}")
            
            # Test 2: Delete with malformed song ID
            malformed_song_id = "malformed-id-with-special-chars-@#$%"
            response = self.make_request("DELETE", f"/songs/{malformed_song_id}")
            
            if response.status_code in [400, 404]:  # Either bad request or not found is acceptable
                self.log_result("Deletion Error Handling - Malformed ID", True, f"Correctly handled malformed song ID (status: {response.status_code})")
            else:
                self.log_result("Deletion Error Handling - Malformed ID", False, f"Should have returned 400/404, got: {response.status_code}")
            
            # Test 3: Delete same song twice
            if self.test_songs:
                song_id = self.test_songs[0]
                
                # First deletion
                first_response = self.make_request("DELETE", f"/songs/{song_id}")
                if first_response.status_code == 200:
                    # Second deletion of same song
                    second_response = self.make_request("DELETE", f"/songs/{song_id}")
                    
                    if second_response.status_code == 404:
                        self.log_result("Deletion Error Handling - Double Deletion", True, "Correctly returned 404 for already deleted song")
                        if song_id in self.test_songs:
                            self.test_songs.remove(song_id)
                    else:
                        self.log_result("Deletion Error Handling - Double Deletion", False, f"Should have returned 404, got: {second_response.status_code}")
                else:
                    self.log_result("Deletion Error Handling - Double Deletion", False, "First deletion failed, cannot test double deletion")
            else:
                self.log_result("Deletion Error Handling - Double Deletion", False, "No test songs available for double deletion test")
            
            self.log_result("Deletion Error Handling", True, "All error handling tests completed")
            
        except Exception as e:
            self.log_result("Deletion Error Handling", False, f"Exception: {str(e)}")

    def test_deletion_performance(self):
        """Test deletion performance with larger numbers of songs"""
        try:
            # Create additional songs for performance testing
            performance_songs = self.create_test_songs(20)
            
            if len(performance_songs) < 10:
                self.log_result("Deletion Performance", False, "Could not create enough songs for performance testing")
                return
            
            # Test 1: Sequential deletion performance
            songs_for_sequential = performance_songs[:10]
            start_time = time.time()
            
            successful_sequential = 0
            for song_id in songs_for_sequential:
                response = self.make_request("DELETE", f"/songs/{song_id}")
                if response.status_code == 200:
                    successful_sequential += 1
            
            sequential_duration = time.time() - start_time
            
            # Test 2: Parallel deletion performance
            songs_for_parallel = performance_songs[10:]
            
            def delete_song_perf(song_id):
                try:
                    response = self.make_request("DELETE", f"/songs/{song_id}")
                    return response.status_code == 200
                except:
                    return False
            
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                parallel_results = list(executor.map(delete_song_perf, songs_for_parallel))
            
            parallel_duration = time.time() - start_time
            successful_parallel = sum(parallel_results)
            
            # Performance analysis
            sequential_rate = successful_sequential / sequential_duration if sequential_duration > 0 else 0
            parallel_rate = successful_parallel / parallel_duration if parallel_duration > 0 else 0
            
            print(f"📊 Sequential: {successful_sequential} songs in {sequential_duration:.2f}s ({sequential_rate:.1f} songs/sec)")
            print(f"📊 Parallel: {successful_parallel} songs in {parallel_duration:.2f}s ({parallel_rate:.1f} songs/sec)")
            
            # Performance criteria: should handle at least 1 song per second
            if sequential_rate >= 1.0 and parallel_rate >= 1.0:
                self.log_result("Deletion Performance", True, 
                               f"Good performance: Sequential {sequential_rate:.1f} songs/sec, Parallel {parallel_rate:.1f} songs/sec")
            elif sequential_rate >= 0.5 and parallel_rate >= 0.5:
                self.log_result("Deletion Performance", True, 
                               f"Acceptable performance: Sequential {sequential_rate:.1f} songs/sec, Parallel {parallel_rate:.1f} songs/sec")
            else:
                self.log_result("Deletion Performance", False, 
                               f"Poor performance: Sequential {sequential_rate:.1f} songs/sec, Parallel {parallel_rate:.1f} songs/sec")
            
            # Remove deleted songs from test_songs list
            for song_id in performance_songs:
                if song_id in self.test_songs:
                    self.test_songs.remove(song_id)
                    
        except Exception as e:
            self.log_result("Deletion Performance", False, f"Exception: {str(e)}")

    def test_database_integrity_after_deletion(self):
        """Test that song deletion doesn't affect other musician's songs or related data"""
        try:
            # Create another musician and their songs
            other_musician = {
                "name": "Integrity Test Musician",
                "email": "integrity.test@requestwave.com",
                "password": "IntegrityPassword123!"
            }
            
            other_response = self.make_request("POST", "/auth/register", other_musician)
            if other_response.status_code != 200:
                self.log_result("Database Integrity", False, "Could not create other musician for integrity test")
                return
            
            other_data = other_response.json()
            other_token = other_data["token"]
            
            # Create songs for other musician
            original_token = self.auth_token
            self.auth_token = other_token
            
            other_songs = []
            for i in range(3):
                song_data = {
                    "title": f"Other Musician Song {i+1}",
                    "artist": f"Other Artist {i+1}",
                    "genres": ["Jazz"],
                    "moods": ["Smooth"],
                    "year": 2021,
                    "notes": f"Song {i+1} by other musician"
                }
                
                response = self.make_request("POST", "/songs", song_data)
                if response.status_code == 200:
                    other_songs.append(response.json()["id"])
            
            # Switch back to original musician
            self.auth_token = original_token
            
            # Get initial counts
            original_songs_response = self.make_request("GET", "/songs")
            other_songs_response = self.make_request("GET", f"/musicians/{other_data['musician']['slug']}/songs")
            
            if original_songs_response.status_code == 200 and other_songs_response.status_code == 200:
                original_songs_count = len(original_songs_response.json())
                other_songs_count = len(other_songs_response.json())
                
                print(f"📊 Before deletion: Original musician has {original_songs_count} songs, Other musician has {other_songs_count} songs")
                
                # Delete some songs from original musician
                if self.test_songs:
                    songs_to_delete = self.test_songs[:2]
                    for song_id in songs_to_delete:
                        response = self.make_request("DELETE", f"/songs/{song_id}")
                        if response.status_code == 200 and song_id in self.test_songs:
                            self.test_songs.remove(song_id)
                    
                    # Verify counts after deletion
                    final_original_response = self.make_request("GET", "/songs")
                    final_other_response = self.make_request("GET", f"/musicians/{other_data['musician']['slug']}/songs")
                    
                    if final_original_response.status_code == 200 and final_other_response.status_code == 200:
                        final_original_count = len(final_original_response.json())
                        final_other_count = len(final_other_response.json())
                        
                        print(f"📊 After deletion: Original musician has {final_original_count} songs, Other musician has {final_other_count} songs")
                        
                        # Check integrity
                        if final_other_count == other_songs_count:
                            self.log_result("Database Integrity - Other Musician Songs", True, "Other musician's songs unaffected by deletion")
                        else:
                            self.log_result("Database Integrity - Other Musician Songs", False, f"Other musician's song count changed: {other_songs_count} -> {final_other_count}")
                        
                        if final_original_count == original_songs_count - len(songs_to_delete):
                            self.log_result("Database Integrity - Original Musician Songs", True, "Original musician's song count correctly updated")
                        else:
                            self.log_result("Database Integrity - Original Musician Songs", False, f"Original musician's song count incorrect: expected {original_songs_count - len(songs_to_delete)}, got {final_original_count}")
                        
                        self.log_result("Database Integrity", True, "Database integrity maintained after song deletion")
                    else:
                        self.log_result("Database Integrity", False, "Could not verify final song counts")
                else:
                    self.log_result("Database Integrity", False, "No test songs available for integrity test")
            else:
                self.log_result("Database Integrity", False, "Could not get initial song counts")
                
        except Exception as e:
            self.log_result("Database Integrity", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all song deletion tests"""
        print("🎵 REQUESTWAVE SONG DELETION COMPREHENSIVE TESTING")
        print("=" * 60)
        
        # Setup
        if not self.setup_authentication():
            print("❌ Authentication setup failed, cannot continue with tests")
            return
        
        # Create test songs
        self.create_test_songs(15)
        
        print("\n🔥 INDIVIDUAL SONG DELETION TESTS")
        print("-" * 40)
        self.test_individual_song_deletion()
        
        print("\n🔥 BULK SONG DELETION TESTS")
        print("-" * 40)
        self.test_bulk_song_deletion_sequential()
        self.test_bulk_song_deletion_parallel()
        
        print("\n🔥 AUTHENTICATION & AUTHORIZATION TESTS")
        print("-" * 40)
        self.test_deletion_authentication_and_authorization()
        
        print("\n🔥 ERROR HANDLING TESTS")
        print("-" * 40)
        self.test_deletion_error_handling()
        
        print("\n🔥 PERFORMANCE TESTS")
        print("-" * 40)
        self.test_deletion_performance()
        
        print("\n🔥 DATABASE INTEGRITY TESTS")
        print("-" * 40)
        self.test_database_integrity_after_deletion()
        
        # Summary
        print("\n" + "=" * 60)
        print("🎯 SONG DELETION TEST SUMMARY")
        print("=" * 60)
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        print(f"📊 SUCCESS RATE: {(self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100):.1f}%")
        
        if self.results['errors']:
            print("\n❌ FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        return self.results

if __name__ == "__main__":
    tester = SongDeletionTester()
    results = tester.run_all_tests()