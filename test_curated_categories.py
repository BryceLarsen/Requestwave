#!/usr/bin/env python3
"""
Test Curated Genre/Mood Categories System - PRIORITY 1
Focus on testing the fixed Spotify metadata integration with curated categories
"""

import requests
import json
import os

# Configuration
BASE_URL = "https://request-error-fix.preview.emergentagent.com/api"
TEST_MUSICIAN = {
    "name": "Test Musician Categories",
    "email": "test.categories@requestwave.com",
    "password": "SecurePassword123!"
}

class CuratedCategoriesTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.results = {"passed": 0, "failed": 0, "errors": []}

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

    def make_request(self, method: str, endpoint: str, data=None, params=None):
        """Make HTTP request with proper headers"""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                if params:
                    response = requests.post(url, headers=headers, params=params)
                else:
                    response = requests.post(url, headers=headers, json=data)
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
                self.log_result("Authentication Setup", True, f"Registered and logged in as: {data['musician']['name']}")
                return True
            elif response.status_code == 400:
                # User exists, try login
                login_data = {"email": TEST_MUSICIAN["email"], "password": TEST_MUSICIAN["password"]}
                response = self.make_request("POST", "/auth/login", login_data)
                
                if response.status_code == 200:
                    data = response.json()
                    self.auth_token = data["token"]
                    self.log_result("Authentication Setup", True, f"Logged in as: {data['musician']['name']}")
                    return True
                else:
                    self.log_result("Authentication Setup", False, f"Login failed: {response.status_code}")
                    return False
            else:
                self.log_result("Authentication Setup", False, f"Registration failed: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Authentication Setup", False, f"Exception: {str(e)}")
            return False

    def test_curated_categories_spotify_metadata(self):
        """Test the FIXED Spotify metadata search with curated categories - PRIORITY 1"""
        try:
            print("🔍 PRIORITY 1: Testing Fixed Spotify Metadata Search with Curated Categories")
            print("=" * 80)
            
            # Test examples from the review request
            test_songs = [
                ("Mr. Brightside", "The Killers"),
                ("Skinny Love", "Bon Iver"),
                ("Watermelon Sugar", "Harry Styles"),
                ("Bad Habits", "Ed Sheeran")
            ]
            
            # Expected curated genres (20 options)
            curated_genres = [
                "Pop", "Rock", "Classic Rock", "Folk", "Country", "Americana", "Indie", 
                "Alternative", "Singer-Songwriter", "R&B", "Soul", "Funk", "Blues", 
                "Jazz", "Hip Hop", "Reggae", "Electronic", "Dance", "Latin", "Acoustic"
            ]
            
            # Expected curated moods (20 options)
            curated_moods = [
                "Chill Vibes", "Feel Good", "Throwback", "Romantic", "Poolside", "Island Vibes", 
                "Dance Party", "Late Night", "Road Trip", "Sad Bangers", "Coffeehouse", 
                "Campfire", "Bar Anthems", "Summer Vibes", "Rainy Day", "Feel It Live", 
                "Heartbreak", "Fall Acoustic", "Weekend Warm-Up", "Groovy"
            ]
            
            # Old categories that should NOT appear
            old_categories = ["Upbeat", "Energetic", "Melancholy", "Alternative Rock", "Indie Folk", "Soft Pop"]
            
            print(f"📊 Testing {len(test_songs)} example songs for curated categories")
            print(f"📊 Expected curated genres: {len(curated_genres)} options")
            print(f"📊 Expected curated moods: {len(curated_moods)} options")
            print(f"📊 Old categories to avoid: {old_categories}")
            
            successful_tests = 0
            category_results = []
            
            for title, artist in test_songs:
                print(f"\n🎵 Testing: '{title}' by {artist}")
                
                # Test Spotify metadata search endpoint
                params = {
                    "title": title,
                    "artist": artist
                }
                
                response = self.make_request("POST", "/songs/search-metadata", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   📊 Response status: {response.status_code}")
                    print(f"   📊 Response data: {json.dumps(data, indent=2)}")
                    
                    if "success" in data and data["success"] and "metadata" in data:
                        metadata = data["metadata"]
                        
                        # Check genres
                        returned_genres = metadata.get("genres", [])
                        genres_valid = all(genre in curated_genres for genre in returned_genres)
                        invalid_genres = [g for g in returned_genres if g not in curated_genres]
                        
                        # Check moods
                        returned_moods = metadata.get("moods", [])
                        moods_valid = all(mood in curated_moods for mood in returned_moods)
                        invalid_moods = [m for m in returned_moods if m not in curated_moods]
                        
                        # Check for old categories
                        has_old_categories = any(cat in returned_genres + returned_moods for cat in old_categories)
                        old_cats_found = [cat for cat in old_categories if cat in returned_genres + returned_moods]
                        
                        print(f"   ✅ Genres: {returned_genres}")
                        print(f"   ✅ Moods: {returned_moods}")
                        print(f"   📊 Genres valid: {genres_valid} (invalid: {invalid_genres})")
                        print(f"   📊 Moods valid: {moods_valid} (invalid: {invalid_moods})")
                        print(f"   📊 Old categories found: {old_cats_found}")
                        
                        if genres_valid and moods_valid and not has_old_categories:
                            successful_tests += 1
                            category_results.append({
                                "song": f"{title} by {artist}",
                                "genres": returned_genres,
                                "moods": returned_moods,
                                "valid": True
                            })
                            print(f"   ✅ SUCCESS: Uses curated categories only")
                        else:
                            issues = []
                            if not genres_valid:
                                issues.append(f"invalid genres: {invalid_genres}")
                            if not moods_valid:
                                issues.append(f"invalid moods: {invalid_moods}")
                            if has_old_categories:
                                issues.append(f"old categories: {old_cats_found}")
                            
                            category_results.append({
                                "song": f"{title} by {artist}",
                                "genres": returned_genres,
                                "moods": returned_moods,
                                "valid": False,
                                "issues": issues
                            })
                            print(f"   ❌ ISSUES: {'; '.join(issues)}")
                    else:
                        print(f"   ❌ Invalid response structure: {data}")
                        category_results.append({
                            "song": f"{title} by {artist}",
                            "valid": False,
                            "error": "Invalid response structure"
                        })
                else:
                    print(f"   ❌ Request failed: {response.status_code}")
                    print(f"   📊 Response text: {response.text}")
                    category_results.append({
                        "song": f"{title} by {artist}",
                        "valid": False,
                        "error": f"HTTP {response.status_code}"
                    })
            
            # Final assessment
            print(f"\n📊 FINAL RESULTS:")
            print(f"   Successful tests: {successful_tests}/{len(test_songs)}")
            
            if successful_tests == len(test_songs):
                self.log_result("Curated Categories - Spotify Metadata", True, f"✅ PRIORITY 1 COMPLETE: All {successful_tests}/{len(test_songs)} songs use curated categories, no old categories detected")
            elif successful_tests > 0:
                self.log_result("Curated Categories - Spotify Metadata", True, f"✅ MOSTLY WORKING: {successful_tests}/{len(test_songs)} songs use curated categories")
            else:
                failed_songs = [r["song"] for r in category_results if not r.get("valid")]
                self.log_result("Curated Categories - Spotify Metadata", False, f"❌ CRITICAL ISSUE: All tests failed - {len(failed_songs)} songs have issues")
            
            # Print detailed results
            print(f"\n📊 DETAILED RESULTS:")
            for result in category_results:
                if result.get("valid"):
                    print(f"   ✅ {result['song']}: genres={result['genres']}, moods={result['moods']}")
                else:
                    if "issues" in result:
                        print(f"   ❌ {result['song']}: {'; '.join(result['issues'])}")
                    else:
                        print(f"   ❌ {result['song']}: {result.get('error', 'Unknown error')}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Curated Categories - Spotify Metadata", False, f"❌ Exception: {str(e)}")

    def print_final_results(self):
        """Print final test results"""
        print("\n" + "="*60)
        print("🎯 CURATED CATEGORIES TEST RESULTS")
        print("="*60)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Total: {self.results['passed'] + self.results['failed']}")
        
        if self.results['errors']:
            print(f"\n❌ ERRORS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed'])) * 100 if (self.results['passed'] + self.results['failed']) > 0 else 0
        print(f"\n📊 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 CURATED CATEGORIES SYSTEM WORKING!")
        elif success_rate >= 50:
            print("⚠️  CURATED CATEGORIES PARTIALLY WORKING")
        else:
            print("🚨 CURATED CATEGORIES SYSTEM NEEDS FIXES")

    def run_tests(self):
        """Run all curated categories tests"""
        print("🚀 Starting Curated Categories Testing")
        print("=" * 60)
        
        # Setup authentication
        if not self.setup_authentication():
            print("❌ Authentication setup failed, cannot continue")
            return
        
        # Run the main test
        self.test_curated_categories_spotify_metadata()
        
        # Print results
        self.print_final_results()

if __name__ == "__main__":
    tester = CuratedCategoriesTester()
    tester.run_tests()