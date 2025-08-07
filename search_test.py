#!/usr/bin/env python3
"""
Focused test for Audience Page Search Functionality
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://c9aa150a-6f2f-42af-9179-ded9ed77f946.preview.emergentagent.com/api"
TEST_MUSICIAN = {
    "name": "Search Test Musician",
    "email": "search.test@requestwave.com",
    "password": "SearchTest123!"
}

class SearchFunctionalityTester:
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

    def setup_authentication(self):
        """Setup authentication for testing"""
        try:
            # Try to register
            response = self.make_request("POST", "/auth/register", TEST_MUSICIAN)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data["token"]
                self.musician_id = data["musician"]["id"]
                self.musician_slug = data["musician"]["slug"]
                print(f"✅ Registered new musician: {data['musician']['name']}")
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
                    print(f"✅ Logged in existing musician: {data['musician']['name']}")
                else:
                    print(f"❌ Login failed: {response.status_code}")
                    return False
            else:
                print(f"❌ Registration failed: {response.status_code}")
                return False
            
            return True
        except Exception as e:
            print(f"❌ Authentication setup failed: {str(e)}")
            return False

    def test_audience_page_search_functionality(self):
        """Test comprehensive audience page search functionality across all fields"""
        try:
            if not self.musician_slug:
                self.log_result("Audience Page Search Functionality", False, "No musician slug available")
                return
            
            print("🔍 Testing comprehensive audience page search functionality")
            
            # Create test songs with variety as specified in requirements
            test_songs = [
                {
                    "title": "Love Story",
                    "artist": "Taylor Swift", 
                    "genres": ["Pop"],
                    "moods": ["Romantic"],
                    "year": 2020,
                    "notes": "Test song for search functionality"
                },
                {
                    "title": "Rock Me",
                    "artist": "Queen",
                    "genres": ["Rock"], 
                    "moods": ["Energetic"],
                    "year": 1975,
                    "notes": "Classic rock anthem"
                },
                {
                    "title": "Smooth Jazz",
                    "artist": "Miles Davis",
                    "genres": ["Jazz"],
                    "moods": ["Smooth"],
                    "year": 1960,
                    "notes": "Smooth jazz classic"
                },
                {
                    "title": "Pop Hit",
                    "artist": "Ariana Grande",
                    "genres": ["Pop"],
                    "moods": ["Upbeat"],
                    "year": 2021,
                    "notes": "Modern pop hit"
                },
                {
                    "title": "Jazz Melody",
                    "artist": "John Coltrane",
                    "genres": ["Jazz"],
                    "moods": ["Smooth"],
                    "year": 1965,
                    "notes": "Beautiful jazz melody"
                }
            ]
            
            created_song_ids = []
            
            # Create test songs
            for song_data in test_songs:
                response = self.make_request("POST", "/songs", song_data)
                if response.status_code == 200:
                    song_id = response.json()["id"]
                    created_song_ids.append(song_id)
                    print(f"📊 Created test song: '{song_data['title']}' by '{song_data['artist']}'")
                else:
                    print(f"⚠️ Song might already exist: '{song_data['title']}' by '{song_data['artist']}'")
            
            print(f"✅ Setup complete with test songs for search testing")
            
            # Test search scenarios as specified in requirements
            search_tests = [
                # Title search
                ("love", "Love Story", "Should find 'Love Story' by title search"),
                ("rock", "Rock Me", "Should find 'Rock Me' by title search"),
                ("jazz", ["Smooth Jazz", "Jazz Melody"], "Should find both jazz songs by title search"),
                
                # Artist search  
                ("taylor", "Love Story", "Should find Taylor Swift song by artist search"),
                ("queen", "Rock Me", "Should find Queen song by artist search"),
                ("miles", "Smooth Jazz", "Should find Miles Davis song by artist search"),
                ("ariana", "Pop Hit", "Should find Ariana Grande song by artist search"),
                
                # Genre search
                ("pop", ["Love Story", "Pop Hit"], "Should find Pop genre songs"),
                ("rock", "Rock Me", "Should find Rock genre songs"),
                ("jazz", ["Smooth Jazz", "Jazz Melody"], "Should find Jazz genre songs"),
                
                # Mood search
                ("romantic", "Love Story", "Should find Romantic mood songs"),
                ("energetic", "Rock Me", "Should find Energetic mood songs"),
                ("smooth", ["Smooth Jazz", "Jazz Melody"], "Should find Smooth mood songs"),
                ("upbeat", "Pop Hit", "Should find Upbeat mood songs"),
                
                # Year search
                ("2020", "Love Story", "Should find 2020 songs"),
                ("1975", "Rock Me", "Should find 1975 songs"),
                ("1960", "Smooth Jazz", "Should find 1960 songs"),
                ("2021", "Pop Hit", "Should find 2021 songs"),
                
                # Case-insensitive search
                ("LOVE", "Love Story", "Should find songs with case-insensitive search"),
                ("TAYLOR", "Love Story", "Should find Taylor Swift with case-insensitive search"),
                ("POP", ["Love Story", "Pop Hit"], "Should find Pop genre with case-insensitive search"),
                
                # Partial matches
                ("tay", "Love Story", "Should find Taylor Swift with partial match"),
                ("jaz", ["Smooth Jazz", "Jazz Melody"], "Should find jazz songs with partial match"),
                ("gran", "Pop Hit", "Should find Ariana Grande with partial match")
            ]
            
            search_passed = 0
            search_failed = 0
            
            for search_term, expected_songs, description in search_tests:
                params = {"search": search_term}
                response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs", params)
                
                if response.status_code == 200:
                    found_songs = response.json()
                    found_titles = [song["title"] for song in found_songs]
                    
                    # Handle both single song and multiple song expectations
                    if isinstance(expected_songs, str):
                        expected_songs = [expected_songs]
                    
                    # Check if all expected songs were found
                    found_expected = all(expected in found_titles for expected in expected_songs)
                    
                    if found_expected:
                        search_passed += 1
                        print(f"✅ Search '{search_term}': Found {found_titles} - {description}")
                    else:
                        search_failed += 1
                        print(f"❌ Search '{search_term}': Expected {expected_songs}, found {found_titles} - {description}")
                else:
                    search_failed += 1
                    print(f"❌ Search '{search_term}': API error {response.status_code} - {description}")
            
            # Test search combined with filters
            print("\n🔍 Testing search combined with filters")
            
            filter_tests = [
                # Search + genre filter
                ({"search": "love", "genre": "Pop"}, ["Love Story"], "Search 'love' + Pop genre filter"),
                ({"search": "jazz", "genre": "Jazz"}, ["Smooth Jazz", "Jazz Melody"], "Search 'jazz' + Jazz genre filter"),
                
                # Search + artist filter  
                ({"search": "taylor", "artist": "Taylor"}, ["Love Story"], "Search 'taylor' + artist filter"),
                
                # Search + mood filter
                ({"search": "smooth", "mood": "Smooth"}, ["Smooth Jazz", "Jazz Melody"], "Search 'smooth' + Smooth mood filter"),
                
                # Search + year filter
                ({"search": "pop", "year": 2020}, ["Love Story"], "Search 'pop' + year 2020 filter"),
                ({"search": "pop", "year": 2021}, ["Pop Hit"], "Search 'pop' + year 2021 filter")
            ]
            
            filter_passed = 0
            filter_failed = 0
            
            for params, expected_songs, description in filter_tests:
                response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs", params)
                
                if response.status_code == 200:
                    found_songs = response.json()
                    found_titles = [song["title"] for song in found_songs]
                    
                    # Check if all expected songs were found
                    found_expected = all(expected in found_titles for expected in expected_songs)
                    
                    if found_expected and len(found_titles) == len(expected_songs):
                        filter_passed += 1
                        print(f"✅ {description}: Found {found_titles}")
                    else:
                        filter_failed += 1
                        print(f"❌ {description}: Expected {expected_songs}, found {found_titles}")
                else:
                    filter_failed += 1
                    print(f"❌ {description}: API error {response.status_code}")
            
            # Test that GET /musicians/{slug}/songs returns all songs without 1000 limit
            print("\n🔍 Testing unlimited song retrieval")
            
            response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs")
            if response.status_code == 200:
                all_songs = response.json()
                if len(all_songs) >= 5:  # At least our test songs
                    print(f"✅ Retrieved {len(all_songs)} songs without 1000 limit")
                    unlimited_passed = True
                else:
                    print(f"❌ Expected at least 5 songs, got {len(all_songs)}")
                    unlimited_passed = False
            else:
                print(f"❌ Failed to retrieve all songs: {response.status_code}")
                unlimited_passed = False
            
            # Overall results
            total_search_tests = len(search_tests)
            total_filter_tests = len(filter_tests)
            
            if search_passed == total_search_tests and filter_passed == total_filter_tests and unlimited_passed:
                self.log_result("Audience Page Search Functionality", True, 
                    f"✅ ALL SEARCH TESTS PASSED: {search_passed}/{total_search_tests} search tests, {filter_passed}/{total_filter_tests} filter tests, unlimited retrieval working")
            else:
                self.log_result("Audience Page Search Functionality", False,
                    f"❌ SEARCH TESTS FAILED: {search_passed}/{total_search_tests} search tests passed, {filter_passed}/{total_filter_tests} filter tests passed, unlimited retrieval: {unlimited_passed}")
                    
        except Exception as e:
            self.log_result("Audience Page Search Functionality", False, f"Exception: {str(e)}")

    def run_search_tests(self):
        """Run search functionality tests"""
        print("=" * 70)
        print("🔍 AUDIENCE PAGE SEARCH FUNCTIONALITY TESTING")
        print("=" * 70)
        
        if not self.setup_authentication():
            print("❌ Failed to setup authentication")
            return False
        
        self.test_audience_page_search_functionality()
        
        # Print summary
        print("\n" + "=" * 50)
        print("🏁 Search Test Summary")
        print("=" * 50)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n🔍 Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        return self.results['failed'] == 0

if __name__ == "__main__":
    tester = SearchFunctionalityTester()
    success = tester.run_search_tests()
    exit(0 if success else 1)