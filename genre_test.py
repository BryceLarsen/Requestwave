#!/usr/bin/env python3
"""
COMPREHENSIVE GENRE SYSTEM TESTING FOR SIMPLIFIED SONGLIST IMPORTS

Testing the updated simplified genre system for songlist imports as requested:

CRITICAL TEST AREAS:
1. Genre List Simplification - confirm CURATED_GENRES has exactly 15 genres
2. Consolidated Genre Detection - test consolidated genres (R&B/Soul, Rap/Hip Hop, Jazz/Standards)
3. Artist-based Detection Updated - verify artists mapped to new consolidated genres
4. Removed Genres - confirm old genres no longer assigned during imports
5. Manual Override Still Works - verify musicians can manually change genres after import

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!

Expected: Simplified 15-genre system working correctly for imports while preserving manual editing flexibility.
"""

import requests
import json
import os
import time
import csv
import io
from typing import Dict, Any, Optional, List

# Configuration
BASE_URL = "https://music-flow-update.preview.emergentagent.com/api"

# Pro account for testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class GenreSystemTester:
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

    def test_login(self):
        """Test login with Pro account"""
        try:
            print("🎵 GENRE SYSTEM TESTING: Login with Pro Account")
            print("=" * 80)
            
            login_data = {
                "email": PRO_MUSICIAN["email"],
                "password": PRO_MUSICIAN["password"]
            }
            
            response = self.make_request("POST", "/auth/login", login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "musician" in data:
                    self.auth_token = data["token"]
                    self.musician_id = data["musician"]["id"]
                    self.musician_slug = data["musician"]["slug"]
                    self.log_result("Pro Account Login", True, f"Logged in as: {data['musician']['name']}")
                    print(f"   📊 Musician ID: {self.musician_id}")
                    print(f"   📊 Musician Slug: {self.musician_slug}")
                else:
                    self.log_result("Pro Account Login", False, f"Missing token or musician in response: {data}")
            else:
                self.log_result("Pro Account Login", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Pro Account Login", False, f"Exception: {str(e)}")

    def test_curated_genres_list_verification(self):
        """Test 1: Verify CURATED_GENRES list contains exactly 15 genres"""
        try:
            print("🎵 TEST 1: Genre List Simplification - Verify 15 Curated Genres")
            print("=" * 80)
            
            # Expected 15 genres from the review request
            expected_genres = [
                "Pop", "Rock", "Country", "R&B/Soul", "Rap/Hip Hop", "Latin", 
                "Christmas", "Irish", "Jazz/Standards", "Funk", "Classic Rock", 
                "Motown", "Classical", "Reggae", "Jam Band"
            ]
            
            print(f"   📊 Expected 15 genres: {expected_genres}")
            
            # Test by creating songs with different artists/titles that should trigger each genre
            test_cases = [
                {"title": "Love Story", "artist": "Taylor Swift", "expected_genre": "Pop"},
                {"title": "Bohemian Rhapsody", "artist": "Queen", "expected_genre": "Classic Rock"},
                {"title": "Friends in Low Places", "artist": "Garth Brooks", "expected_genre": "Country"},
                {"title": "Superstition", "artist": "Stevie Wonder", "expected_genre": "R&B/Soul"},
                {"title": "Lose Yourself", "artist": "Eminem", "expected_genre": "Rap/Hip Hop"},
                {"title": "La Vida Es Un Carnaval", "artist": "Celia Cruz", "expected_genre": "Latin"},
                {"title": "White Christmas", "artist": "Bing Crosby", "expected_genre": "Christmas"},
                {"title": "Whiskey in the Jar", "artist": "The Dubliners", "expected_genre": "Irish"},
                {"title": "Fly Me to the Moon", "artist": "Frank Sinatra", "expected_genre": "Jazz/Standards"},
                {"title": "Get Up (I Feel Like Being a) Sex Machine", "artist": "James Brown", "expected_genre": "Funk"},
                {"title": "My Girl", "artist": "The Temptations", "expected_genre": "Motown"},
                {"title": "Symphony No. 9", "artist": "Beethoven", "expected_genre": "Classical"},
                {"title": "No Woman No Cry", "artist": "Bob Marley", "expected_genre": "Reggae"},
                {"title": "Fire on the Mountain", "artist": "Grateful Dead", "expected_genre": "Jam Band"}
            ]
            
            detected_genres = set()
            correct_detections = 0
            
            # Test each genre detection
            for i, test_case in enumerate(test_cases):
                print(f"   📊 Testing genre detection {i+1}/14: '{test_case['title']}' by {test_case['artist']}")
                
                # Create a test song to see what genre gets assigned
                song_data = {
                    "title": test_case["title"],
                    "artist": test_case["artist"],
                    "genres": [],  # Let the system assign
                    "moods": [],
                    "year": 2020,
                    "notes": f"Genre test song {i+1}"
                }
                
                create_response = self.make_request("POST", "/songs", song_data)
                
                if create_response.status_code == 200:
                    created_song = create_response.json()
                    assigned_genres = created_song.get("genres", [])
                    
                    if assigned_genres:
                        detected_genre = assigned_genres[0]  # Take first genre
                        detected_genres.add(detected_genre)
                        
                        if detected_genre == test_case["expected_genre"]:
                            print(f"      ✅ Correct: {detected_genre}")
                            correct_detections += 1
                        else:
                            print(f"      ❌ Expected: {test_case['expected_genre']}, Got: {detected_genre}")
                    else:
                        print(f"      ❌ No genres assigned")
                    
                    # Clean up test song
                    self.make_request("DELETE", f"/songs/{created_song['id']}")
                else:
                    print(f"      ❌ Failed to create test song: {create_response.status_code}")
            
            # Verify we detected exactly 15 unique genres
            unique_genres_count = len(detected_genres)
            expected_count = 15
            
            print(f"   📊 Detected {unique_genres_count} unique genres: {sorted(detected_genres)}")
            print(f"   📊 Expected {expected_count} genres")
            print(f"   📊 Correct detections: {correct_detections}/{len(test_cases)}")
            
            # Check if all expected genres were detected
            missing_genres = set(expected_genres) - detected_genres
            extra_genres = detected_genres - set(expected_genres)
            
            if missing_genres:
                print(f"   ❌ Missing genres: {missing_genres}")
            if extra_genres:
                print(f"   ❌ Extra genres detected: {extra_genres}")
            
            # Success criteria: 15 unique genres, high accuracy, no missing expected genres
            success = (
                unique_genres_count == expected_count and
                correct_detections >= 12 and  # Allow some flexibility
                len(missing_genres) == 0
            )
            
            if success:
                self.log_result("Genre List Simplification", True, f"✅ CONFIRMED: Exactly 15 curated genres detected with {correct_detections}/{len(test_cases)} correct assignments")
            else:
                issues = []
                if unique_genres_count != expected_count:
                    issues.append(f"wrong genre count ({unique_genres_count} vs {expected_count})")
                if correct_detections < 12:
                    issues.append(f"low accuracy ({correct_detections}/{len(test_cases)})")
                if missing_genres:
                    issues.append(f"missing genres: {missing_genres}")
                
                self.log_result("Genre List Simplification", False, f"❌ ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Genre List Simplification", False, f"Exception: {str(e)}")

    def test_consolidated_genre_detection(self):
        """Test 2: Verify consolidated genre detection (R&B/Soul, Rap/Hip Hop, Jazz/Standards)"""
        try:
            print("🎵 TEST 2: Consolidated Genre Detection")
            print("=" * 80)
            
            # Test consolidated genres specifically
            consolidated_tests = [
                # R&B/Soul consolidation
                {"title": "What's Going On", "artist": "Marvin Gaye", "expected": "R&B/Soul", "old_genres": ["R&B", "Soul"]},
                {"title": "Crazy in Love", "artist": "Beyonce", "expected": "R&B/Soul", "old_genres": ["R&B", "Soul"]},
                {"title": "All of Me", "artist": "John Legend", "expected": "R&B/Soul", "old_genres": ["R&B", "Soul"]},
                
                # Rap/Hip Hop consolidation  
                {"title": "Stan", "artist": "Eminem", "expected": "Rap/Hip Hop", "old_genres": ["Hip Hop", "Rap"]},
                {"title": "God's Plan", "artist": "Drake", "expected": "Rap/Hip Hop", "old_genres": ["Hip Hop", "Rap"]},
                {"title": "HUMBLE.", "artist": "Kendrick Lamar", "expected": "Rap/Hip Hop", "old_genres": ["Hip Hop", "Rap"]},
                
                # Jazz/Standards consolidation
                {"title": "The Way You Look Tonight", "artist": "Frank Sinatra", "expected": "Jazz/Standards", "old_genres": ["Jazz", "Standards"]},
                {"title": "Kind of Blue", "artist": "Miles Davis", "expected": "Jazz/Standards", "old_genres": ["Jazz", "Standards"]},
                {"title": "Summertime", "artist": "Ella Fitzgerald", "expected": "Jazz/Standards", "old_genres": ["Jazz", "Standards"]}
            ]
            
            correct_consolidations = 0
            
            for i, test in enumerate(consolidated_tests):
                print(f"   📊 Testing consolidation {i+1}/9: '{test['title']}' by {test['artist']}")
                print(f"      Expected: {test['expected']} (instead of {test['old_genres']})")
                
                # Create test song
                song_data = {
                    "title": test["title"],
                    "artist": test["artist"],
                    "genres": [],
                    "moods": [],
                    "year": 2020,
                    "notes": f"Consolidation test {i+1}"
                }
                
                create_response = self.make_request("POST", "/songs", song_data)
                
                if create_response.status_code == 200:
                    created_song = create_response.json()
                    assigned_genres = created_song.get("genres", [])
                    
                    if assigned_genres:
                        detected_genre = assigned_genres[0]
                        
                        if detected_genre == test["expected"]:
                            print(f"      ✅ Correct consolidation: {detected_genre}")
                            correct_consolidations += 1
                        else:
                            print(f"      ❌ Wrong genre: {detected_genre} (expected {test['expected']})")
                        
                        # Verify it's NOT using old separate genres
                        if detected_genre in test["old_genres"]:
                            print(f"      ❌ Using old separate genre: {detected_genre}")
                        else:
                            print(f"      ✅ Not using old separate genres: {test['old_genres']}")
                    else:
                        print(f"      ❌ No genres assigned")
                    
                    # Clean up
                    self.make_request("DELETE", f"/songs/{created_song['id']}")
                else:
                    print(f"      ❌ Failed to create song: {create_response.status_code}")
            
            # Success criteria: Most consolidations work correctly
            success_rate = correct_consolidations / len(consolidated_tests)
            success = success_rate >= 0.8  # 80% success rate
            
            if success:
                self.log_result("Consolidated Genre Detection", True, f"✅ CONSOLIDATED GENRES WORKING: {correct_consolidations}/{len(consolidated_tests)} correct ({success_rate:.1%})")
            else:
                self.log_result("Consolidated Genre Detection", False, f"❌ CONSOLIDATION ISSUES: Only {correct_consolidations}/{len(consolidated_tests)} correct ({success_rate:.1%})")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Consolidated Genre Detection", False, f"Exception: {str(e)}")

    def test_artist_based_detection_updated(self):
        """Test 3: Verify artist-based detection maps to new consolidated genres"""
        try:
            print("🎵 TEST 3: Artist-based Detection Updated")
            print("=" * 80)
            
            # Test specific artists mentioned in review request
            artist_tests = [
                # R&B/Soul artists
                {"artist": "Stevie Wonder", "song": "Superstition", "expected": "R&B/Soul"},
                {"artist": "Beyonce", "song": "Single Ladies", "expected": "R&B/Soul"},
                
                # Rap/Hip Hop artists
                {"artist": "Eminem", "song": "Lose Yourself", "expected": "Rap/Hip Hop"},
                {"artist": "Drake", "song": "Hotline Bling", "expected": "Rap/Hip Hop"},
                
                # Jazz/Standards artists
                {"artist": "Frank Sinatra", "song": "My Way", "expected": "Jazz/Standards"},
                {"artist": "Miles Davis", "song": "So What", "expected": "Jazz/Standards"},
                
                # Additional key artists for other genres
                {"artist": "Taylor Swift", "song": "Shake It Off", "expected": "Pop"},
                {"artist": "Queen", "song": "We Will Rock You", "expected": "Classic Rock"},
                {"artist": "Johnny Cash", "song": "Ring of Fire", "expected": "Country"},
                {"artist": "James Brown", "song": "I Got You", "expected": "Funk"},
                {"artist": "The Temptations", "song": "My Girl", "expected": "Motown"},
                {"artist": "Bob Marley", "song": "Three Little Birds", "expected": "Reggae"}
            ]
            
            correct_artist_mappings = 0
            
            for i, test in enumerate(artist_tests):
                print(f"   📊 Testing artist mapping {i+1}/12: {test['artist']} → {test['expected']}")
                
                song_data = {
                    "title": test["song"],
                    "artist": test["artist"],
                    "genres": [],
                    "moods": [],
                    "year": 2020,
                    "notes": f"Artist mapping test {i+1}"
                }
                
                create_response = self.make_request("POST", "/songs", song_data)
                
                if create_response.status_code == 200:
                    created_song = create_response.json()
                    assigned_genres = created_song.get("genres", [])
                    
                    if assigned_genres:
                        detected_genre = assigned_genres[0]
                        
                        if detected_genre == test["expected"]:
                            print(f"      ✅ Correct mapping: {test['artist']} → {detected_genre}")
                            correct_artist_mappings += 1
                        else:
                            print(f"      ❌ Wrong mapping: {test['artist']} → {detected_genre} (expected {test['expected']})")
                    else:
                        print(f"      ❌ No genres assigned for {test['artist']}")
                    
                    # Clean up
                    self.make_request("DELETE", f"/songs/{created_song['id']}")
                else:
                    print(f"      ❌ Failed to create song for {test['artist']}: {create_response.status_code}")
            
            # Success criteria: High accuracy in artist-based detection
            success_rate = correct_artist_mappings / len(artist_tests)
            success = success_rate >= 0.85  # 85% success rate
            
            if success:
                self.log_result("Artist-based Detection Updated", True, f"✅ ARTIST MAPPING UPDATED: {correct_artist_mappings}/{len(artist_tests)} correct ({success_rate:.1%})")
            else:
                self.log_result("Artist-based Detection Updated", False, f"❌ ARTIST MAPPING ISSUES: Only {correct_artist_mappings}/{len(artist_tests)} correct ({success_rate:.1%})")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Artist-based Detection Updated", False, f"Exception: {str(e)}")

    def test_removed_genres_verification(self):
        """Test 4: Verify old genres are no longer assigned during imports"""
        try:
            print("🎵 TEST 4: Removed Genres Verification")
            print("=" * 80)
            
            # Old genres that should no longer be assigned
            removed_genres = [
                "Folk", "Singer-Songwriter", "Blues", "Electronic", "Dance", 
                "Acoustic", "Indie", "Alternative", "Italian"
            ]
            
            print(f"   📊 Checking that these old genres are NOT assigned: {removed_genres}")
            
            # Test songs that might have triggered old genres
            test_songs = [
                {"title": "The Times They Are A-Changin'", "artist": "Bob Dylan", "might_trigger": ["Folk", "Singer-Songwriter"]},
                {"title": "Sweet Home Chicago", "artist": "Robert Johnson", "might_trigger": ["Blues"]},
                {"title": "One More Time", "artist": "Daft Punk", "might_trigger": ["Electronic", "Dance"]},
                {"title": "Blackbird", "artist": "The Beatles", "might_trigger": ["Acoustic"]},
                {"title": "Creep", "artist": "Radiohead", "might_trigger": ["Alternative", "Indie"]},
                {"title": "Con te partirò", "artist": "Andrea Bocelli", "might_trigger": ["Italian"]},
                {"title": "Hurt", "artist": "Johnny Cash", "might_trigger": ["Alternative"]},
                {"title": "Mad World", "artist": "Gary Jules", "might_trigger": ["Alternative", "Indie"]},
                {"title": "Hallelujah", "artist": "Leonard Cohen", "might_trigger": ["Folk", "Singer-Songwriter"]}
            ]
            
            detected_old_genres = set()
            songs_with_old_genres = []
            
            for i, test in enumerate(test_songs):
                print(f"   📊 Testing song {i+1}/9: '{test['title']}' by {test['artist']}")
                
                song_data = {
                    "title": test["title"],
                    "artist": test["artist"],
                    "genres": [],
                    "moods": [],
                    "year": 2020,
                    "notes": f"Removed genre test {i+1}"
                }
                
                create_response = self.make_request("POST", "/songs", song_data)
                
                if create_response.status_code == 200:
                    created_song = create_response.json()
                    assigned_genres = created_song.get("genres", [])
                    
                    print(f"      📊 Assigned genres: {assigned_genres}")
                    
                    # Check if any assigned genres are in the removed list
                    found_old_genres = [g for g in assigned_genres if g in removed_genres]
                    
                    if found_old_genres:
                        print(f"      ❌ Found old genres: {found_old_genres}")
                        detected_old_genres.update(found_old_genres)
                        songs_with_old_genres.append({
                            "song": f"{test['title']} by {test['artist']}",
                            "old_genres": found_old_genres
                        })
                    else:
                        print(f"      ✅ No old genres detected")
                    
                    # Clean up
                    self.make_request("DELETE", f"/songs/{created_song['id']}")
                else:
                    print(f"      ❌ Failed to create song: {create_response.status_code}")
            
            # Success criteria: No old genres should be detected
            success = len(detected_old_genres) == 0
            
            if success:
                self.log_result("Removed Genres Verification", True, f"✅ OLD GENRES REMOVED: No removed genres detected in {len(test_songs)} test songs")
            else:
                self.log_result("Removed Genres Verification", False, f"❌ OLD GENRES STILL PRESENT: Found {detected_old_genres} in songs: {songs_with_old_genres}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Removed Genres Verification", False, f"Exception: {str(e)}")

    def test_manual_override_functionality(self):
        """Test 5: Verify manual override still works - musicians can change genres after import"""
        try:
            print("🎵 TEST 5: Manual Override Still Works")
            print("=" * 80)
            
            # Test manual genre editing after automatic assignment
            print("   📊 Step 1: Create song with automatic genre assignment")
            
            # Create a song that will get automatic genre assignment
            song_data = {
                "title": "Test Song for Manual Override",
                "artist": "Taylor Swift",  # Should get "Pop"
                "genres": [],  # Let system assign
                "moods": [],
                "year": 2023,
                "notes": "Manual override test"
            }
            
            create_response = self.make_request("POST", "/songs", song_data)
            
            if create_response.status_code != 200:
                self.log_result("Manual Override Functionality", False, f"Failed to create test song: {create_response.status_code}")
                return
            
            created_song = create_response.json()
            song_id = created_song["id"]
            original_genres = created_song.get("genres", [])
            
            print(f"      ✅ Created song with automatic genres: {original_genres}")
            
            # Step 2: Test manual override to curated genre
            print("   📊 Step 2: Test manual override to different curated genre")
            
            new_curated_genre = "Country"  # Different from expected "Pop"
            update_data = {
                "title": "Test Song for Manual Override",
                "artist": "Taylor Swift",
                "genres": [new_curated_genre],
                "moods": ["Feel Good"],
                "year": 2023,
                "notes": "Manual override test - updated"
            }
            
            update_response = self.make_request("PUT", f"/songs/{song_id}", update_data)
            
            if update_response.status_code == 200:
                updated_song = update_response.json()
                updated_genres = updated_song.get("genres", [])
                
                if new_curated_genre in updated_genres:
                    print(f"      ✅ Manual override to curated genre successful: {updated_genres}")
                    curated_override_success = True
                else:
                    print(f"      ❌ Manual override failed: {updated_genres}")
                    curated_override_success = False
            else:
                print(f"      ❌ Update request failed: {update_response.status_code}")
                curated_override_success = False
            
            # Step 3: Test manual override to custom genre (not in curated list)
            print("   📊 Step 3: Test manual override to custom genre")
            
            custom_genre = "Experimental Jazz Fusion"  # Not in curated list
            custom_update_data = {
                "title": "Test Song for Manual Override",
                "artist": "Taylor Swift",
                "genres": [custom_genre],
                "moods": ["Feel Good"],
                "year": 2023,
                "notes": "Manual override test - custom genre"
            }
            
            custom_update_response = self.make_request("PUT", f"/songs/{song_id}", custom_update_data)
            
            if custom_update_response.status_code == 200:
                custom_updated_song = custom_update_response.json()
                custom_updated_genres = custom_updated_song.get("genres", [])
                
                if custom_genre in custom_updated_genres:
                    print(f"      ✅ Manual override to custom genre successful: {custom_updated_genres}")
                    custom_override_success = True
                else:
                    print(f"      ❌ Custom genre override failed: {custom_updated_genres}")
                    custom_override_success = False
            else:
                print(f"      ❌ Custom update request failed: {custom_update_response.status_code}")
                custom_override_success = False
            
            # Step 4: Test multiple genres (mix of curated and custom)
            print("   📊 Step 4: Test multiple genres (curated + custom)")
            
            mixed_genres = ["Rock", "Experimental Jazz Fusion", "Pop"]  # Mix of curated and custom
            mixed_update_data = {
                "title": "Test Song for Manual Override",
                "artist": "Taylor Swift",
                "genres": mixed_genres,
                "moods": ["Feel Good"],
                "year": 2023,
                "notes": "Manual override test - mixed genres"
            }
            
            mixed_update_response = self.make_request("PUT", f"/songs/{song_id}", mixed_update_data)
            
            if mixed_update_response.status_code == 200:
                mixed_updated_song = mixed_update_response.json()
                mixed_updated_genres = mixed_updated_song.get("genres", [])
                
                # Check if all genres were preserved
                all_genres_preserved = all(genre in mixed_updated_genres for genre in mixed_genres)
                
                if all_genres_preserved:
                    print(f"      ✅ Mixed genres override successful: {mixed_updated_genres}")
                    mixed_override_success = True
                else:
                    print(f"      ❌ Mixed genres override failed: Expected {mixed_genres}, Got {mixed_updated_genres}")
                    mixed_override_success = False
            else:
                print(f"      ❌ Mixed update request failed: {mixed_update_response.status_code}")
                mixed_override_success = False
            
            # Step 5: Verify changes persist
            print("   📊 Step 5: Verify manual changes persist")
            
            get_response = self.make_request("GET", f"/songs/{song_id}")
            
            if get_response.status_code == 200:
                final_song = get_response.json()
                final_genres = final_song.get("genres", [])
                
                persistence_success = final_genres == mixed_genres
                
                if persistence_success:
                    print(f"      ✅ Manual changes persisted: {final_genres}")
                else:
                    print(f"      ❌ Manual changes not persisted: {final_genres}")
            else:
                print(f"      ❌ Failed to retrieve song: {get_response.status_code}")
                persistence_success = False
            
            # Clean up
            self.make_request("DELETE", f"/songs/{song_id}")
            
            # Success criteria: All manual override tests should pass
            success = (
                curated_override_success and 
                custom_override_success and 
                mixed_override_success and 
                persistence_success
            )
            
            if success:
                self.log_result("Manual Override Functionality", True, f"✅ MANUAL OVERRIDE WORKING: Musicians can change to curated genres, custom genres, and mixed genres")
            else:
                issues = []
                if not curated_override_success:
                    issues.append("curated genre override failed")
                if not custom_override_success:
                    issues.append("custom genre override failed")
                if not mixed_override_success:
                    issues.append("mixed genres override failed")
                if not persistence_success:
                    issues.append("changes don't persist")
                
                self.log_result("Manual Override Functionality", False, f"❌ MANUAL OVERRIDE ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Manual Override Functionality", False, f"Exception: {str(e)}")

    def test_csv_import_with_simplified_genres(self):
        """Test 6: Test CSV import uses simplified genre system"""
        try:
            print("🎵 TEST 6: CSV Import with Simplified Genres")
            print("=" * 80)
            
            # Create test CSV content with songs that should trigger different genres
            csv_content = """Title,Artist,Genre,Mood,Year,Notes
Bohemian Rhapsody,Queen,,Feel Good,1975,Test song 1
What's Going On,Marvin Gaye,,Chill Vibes,1971,Test song 2
Lose Yourself,Eminem,,Bar Anthems,2002,Test song 3
Fly Me to the Moon,Frank Sinatra,,Romantic,1964,Test song 4
White Christmas,Bing Crosby,,Feel Good,1942,Test song 5"""
            
            print("   📊 Creating test CSV with 5 songs (empty genres to test auto-assignment)")
            
            # Create CSV file-like object
            csv_file = io.BytesIO(csv_content.encode('utf-8'))
            
            # Test CSV upload
            files = {'file': ('test_genres.csv', csv_file, 'text/csv')}
            data = {'auto_enrich': 'false'}  # Don't use Spotify enrichment, test our genre system
            
            upload_response = self.make_request("POST", "/songs/csv/upload", data=data, files=files)
            
            print(f"   📊 CSV upload response: {upload_response.status_code}")
            
            if upload_response.status_code == 200:
                upload_result = upload_response.json()
                songs_added = upload_result.get("songs_added", 0)
                
                print(f"      ✅ CSV upload successful: {songs_added} songs added")
                
                # Get the uploaded songs to check their genres
                songs_response = self.make_request("GET", "/songs")
                
                if songs_response.status_code == 200:
                    all_songs = songs_response.json()
                    
                    # Find our test songs
                    test_songs = [s for s in all_songs if "Test song" in s.get("notes", "")]
                    
                    print(f"      📊 Found {len(test_songs)} uploaded test songs")
                    
                    expected_mappings = {
                        "Bohemian Rhapsody": "Classic Rock",
                        "What's Going On": "R&B/Soul", 
                        "Lose Yourself": "Rap/Hip Hop",
                        "Fly Me to the Moon": "Jazz/Standards",
                        "White Christmas": "Christmas"
                    }
                    
                    correct_csv_assignments = 0
                    
                    for song in test_songs:
                        title = song.get("title", "")
                        assigned_genres = song.get("genres", [])
                        expected_genre = expected_mappings.get(title)
                        
                        if expected_genre and assigned_genres:
                            if expected_genre in assigned_genres:
                                print(f"      ✅ {title}: {assigned_genres[0]} (correct)")
                                correct_csv_assignments += 1
                            else:
                                print(f"      ❌ {title}: {assigned_genres[0]} (expected {expected_genre})")
                        else:
                            print(f"      ❌ {title}: No genres assigned or not found")
                    
                    # Clean up test songs
                    for song in test_songs:
                        self.make_request("DELETE", f"/songs/{song['id']}")
                    
                    # Success criteria: Most CSV imports get correct genres
                    csv_success_rate = correct_csv_assignments / len(expected_mappings)
                    csv_success = csv_success_rate >= 0.8
                    
                    if csv_success:
                        self.log_result("CSV Import with Simplified Genres", True, f"✅ CSV IMPORT WORKING: {correct_csv_assignments}/{len(expected_mappings)} correct genre assignments ({csv_success_rate:.1%})")
                    else:
                        self.log_result("CSV Import with Simplified Genres", False, f"❌ CSV IMPORT ISSUES: Only {correct_csv_assignments}/{len(expected_mappings)} correct ({csv_success_rate:.1%})")
                else:
                    self.log_result("CSV Import with Simplified Genres", False, f"Failed to retrieve songs after CSV upload: {songs_response.status_code}")
            else:
                self.log_result("CSV Import with Simplified Genres", False, f"CSV upload failed: {upload_response.status_code}, Response: {upload_response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("CSV Import with Simplified Genres", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all genre system tests"""
        print("🎵 COMPREHENSIVE GENRE SYSTEM TESTING")
        print("=" * 80)
        print("Testing the updated simplified genre system for songlist imports")
        print("=" * 80)
        
        # Login first
        self.test_login()
        
        if not self.auth_token:
            print("❌ Cannot proceed without authentication")
            return
        
        # Run all tests
        self.test_curated_genres_list_verification()
        self.test_consolidated_genre_detection()
        self.test_artist_based_detection_updated()
        self.test_removed_genres_verification()
        self.test_manual_override_functionality()
        self.test_csv_import_with_simplified_genres()
        
        # Print final results
        print("\n" + "=" * 80)
        print("🎵 GENRE SYSTEM TESTING RESULTS")
        print("=" * 80)
        
        total_tests = self.results["passed"] + self.results["failed"]
        success_rate = self.results["passed"] / total_tests if total_tests > 0 else 0
        
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        print(f"📊 SUCCESS RATE: {success_rate:.1%}")
        
        if self.results["failed"] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        if success_rate >= 0.8:
            print(f"\n✅ OVERALL RESULT: Genre system testing SUCCESSFUL ({success_rate:.1%})")
        else:
            print(f"\n❌ OVERALL RESULT: Genre system testing FAILED ({success_rate:.1%})")
        
        print("=" * 80)

if __name__ == "__main__":
    tester = GenreSystemTester()
    tester.run_all_tests()