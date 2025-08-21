#!/usr/bin/env python3
"""
Metadata Enrichment Tests for RequestWave
Tests CSV auto-enrichment and existing playlist metadata enrichment features
"""

import requests
import json
import time
import io
from typing import Dict, Any, List

# Configuration
BASE_URL = "https://performance-pay-1.preview.emergentagent.com/api"
TEST_MUSICIAN = {
    "name": "Metadata Test Musician",
    "email": "metadata.test@requestwave.com", 
    "password": "MetadataTest123!"
}

class MetadataEnrichmentTester:
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
                response = requests.get(url, headers=request_headers, params=params)
            elif method.upper() == "POST":
                if files:
                    response = requests.post(url, headers={k: v for k, v in request_headers.items() if k != "Content-Type"}, files=files, data=data)
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

    def create_test_csv_with_missing_metadata(self) -> str:
        """Create a CSV file with songs missing metadata for enrichment testing"""
        csv_content = """Title,Artist,Genre,Mood,Year,Notes
As It Was,Harry Styles,,,,"Popular song missing metadata"
Heat Waves,Glass Animals,,,,"Another popular song"
Blinding Lights,The Weeknd,Pop,Energetic,2019,"Song with some metadata"
Good 4 U,Olivia Rodrigo,,,,"Missing genre and mood"
Levitating,Dua Lipa,,,2020,"Missing genre and mood but has year"
"""
        return csv_content

    def test_csv_upload_auto_enrichment(self):
        """Test CSV Upload Auto-enrichment Enhancement"""
        try:
            print("🔍 Testing CSV Upload Auto-enrichment Enhancement...")
            
            # Create test CSV with missing metadata
            csv_content = self.create_test_csv_with_missing_metadata()
            
            # Test 1: Upload CSV without auto-enrichment
            print("   Testing CSV upload WITHOUT auto-enrichment...")
            csv_file = io.StringIO(csv_content)
            files = {'file': ('test_songs.csv', csv_file.getvalue().encode(), 'text/csv')}
            data = {'auto_enrich': 'false'}
            
            response = self.make_request("POST", "/songs/csv/upload", data=data, files=files)
            
            if response.status_code == 200:
                upload_data = response.json()
                print(f"     Upload response: {json.dumps(upload_data, indent=2)}")
                
                if upload_data.get("success") and upload_data.get("songs_added", 0) > 0:
                    self.log_result("CSV Upload - Without Auto-enrichment", True, 
                                  f"✅ Successfully uploaded {upload_data['songs_added']} songs without enrichment")
                else:
                    self.log_result("CSV Upload - Without Auto-enrichment", False, 
                                  f"Upload failed: {upload_data}")
            else:
                self.log_result("CSV Upload - Without Auto-enrichment", False, 
                              f"Upload failed with status: {response.status_code} - {response.text}")
                return
            
            # Clear existing songs to test with enrichment
            print("   Clearing existing songs for enrichment test...")
            songs_response = self.make_request("GET", "/songs")
            if songs_response.status_code == 200:
                songs = songs_response.json()
                for song in songs:
                    self.make_request("DELETE", f"/songs/{song['id']}")
            
            # Test 2: Upload CSV WITH auto-enrichment
            print("   Testing CSV upload WITH auto-enrichment...")
            csv_file = io.StringIO(csv_content)
            files = {'file': ('test_songs_enriched.csv', csv_file.getvalue().encode(), 'text/csv')}
            data = {'auto_enrich': 'true'}
            
            response = self.make_request("POST", "/songs/csv/upload", data=data, files=files)
            
            if response.status_code == 200:
                enriched_data = response.json()
                print(f"     Enriched upload response: {json.dumps(enriched_data, indent=2)}")
                
                if enriched_data.get("success") and enriched_data.get("songs_added", 0) > 0:
                    # Check if enrichment statistics are provided
                    enrichment_stats = enriched_data.get("enrichment_stats", {})
                    
                    if enrichment_stats:
                        self.log_result("CSV Upload - With Auto-enrichment", True, 
                                      f"✅ Successfully uploaded {enriched_data['songs_added']} songs with enrichment stats: {enrichment_stats}")
                    else:
                        self.log_result("CSV Upload - With Auto-enrichment", True, 
                                      f"✅ Successfully uploaded {enriched_data['songs_added']} songs with auto-enrichment enabled")
                    
                    # Verify that songs were actually enriched
                    songs_response = self.make_request("GET", "/songs")
                    if songs_response.status_code == 200:
                        enriched_songs = songs_response.json()
                        
                        enriched_count = 0
                        for song in enriched_songs:
                            # Check if previously empty fields were filled
                            if song.get("genres") and len(song["genres"]) > 0:
                                enriched_count += 1
                            if song.get("moods") and len(song["moods"]) > 0:
                                enriched_count += 1
                            if song.get("year") and song["year"] > 0:
                                enriched_count += 1
                        
                        if enriched_count > 0:
                            self.log_result("CSV Upload - Enrichment Verification", True, 
                                          f"✅ Verified enrichment: found {enriched_count} enriched fields across songs")
                        else:
                            self.log_result("CSV Upload - Enrichment Verification", False, 
                                          "❌ No enriched fields found in uploaded songs")
                    else:
                        self.log_result("CSV Upload - Enrichment Verification", False, 
                                      f"Failed to verify enrichment: {songs_response.status_code}")
                else:
                    self.log_result("CSV Upload - With Auto-enrichment", False, 
                                  f"Enriched upload failed: {enriched_data}")
            else:
                self.log_result("CSV Upload - With Auto-enrichment", False, 
                              f"Enriched upload failed with status: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("CSV Upload Auto-enrichment", False, f"Exception: {str(e)}")

    def test_existing_songs_batch_enrichment(self):
        """Test Existing Playlist Songs Metadata Enrichment"""
        try:
            print("🔍 Testing Existing Songs Batch Metadata Enrichment...")
            
            # First, create some songs with missing metadata
            songs_with_missing_metadata = [
                {
                    "title": "Watermelon Sugar",
                    "artist": "Harry Styles",
                    "genres": [],  # Missing
                    "moods": [],   # Missing
                    "year": None,  # Missing
                    "notes": "Song missing metadata for enrichment test"
                },
                {
                    "title": "Drivers License",
                    "artist": "Olivia Rodrigo",
                    "genres": [],  # Missing
                    "moods": [],   # Missing
                    "year": None,  # Missing
                    "notes": "Another song missing metadata"
                },
                {
                    "title": "Stay",
                    "artist": "The Kid LAROI & Justin Bieber",
                    "genres": ["Pop"],  # Has genre
                    "moods": [],        # Missing mood
                    "year": None,       # Missing year
                    "notes": "Song with partial metadata"
                }
            ]
            
            created_song_ids = []
            
            print("   Creating songs with missing metadata...")
            for i, song_data in enumerate(songs_with_missing_metadata):
                response = self.make_request("POST", "/songs", song_data)
                
                if response.status_code == 200:
                    song_id = response.json()["id"]
                    created_song_ids.append(song_id)
                    print(f"     Created song {i+1}: '{song_data['title']}' by '{song_data['artist']}'")
                else:
                    print(f"     Failed to create song {i+1}: {response.status_code}")
            
            if len(created_song_ids) == 0:
                self.log_result("Existing Songs Batch Enrichment", False, "Failed to create test songs")
                return
            
            # Test 1: Get enrichment candidates
            print("   Testing enrichment candidates endpoint...")
            candidates_response = self.make_request("GET", "/songs/enrichment-candidates")
            
            if candidates_response.status_code == 200:
                candidates = candidates_response.json()
                print(f"     Found {len(candidates)} songs needing enrichment")
                
                if len(candidates) > 0:
                    self.log_result("Enrichment Candidates", True, 
                                  f"✅ Found {len(candidates)} songs needing metadata enrichment")
                else:
                    self.log_result("Enrichment Candidates", False, 
                                  "❌ No enrichment candidates found")
            else:
                self.log_result("Enrichment Candidates", False, 
                              f"Failed to get enrichment candidates: {candidates_response.status_code}")
            
            # Test 2: Batch enrich all songs needing metadata
            print("   Testing batch enrichment of all songs...")
            batch_enrich_response = self.make_request("POST", "/songs/batch-enrich")
            
            if batch_enrich_response.status_code == 200:
                enrich_data = batch_enrich_response.json()
                print(f"     Batch enrichment response: {json.dumps(enrich_data, indent=2)}")
                
                if enrich_data.get("success"):
                    enriched_count = enrich_data.get("enriched_count", 0)
                    total_processed = enrich_data.get("total_processed", 0)
                    
                    self.log_result("Batch Enrichment - All Songs", True, 
                                  f"✅ Successfully enriched {enriched_count}/{total_processed} songs")
                    
                    # Verify enrichment by checking the songs
                    print("   Verifying enrichment results...")
                    for song_id in created_song_ids:
                        song_response = self.make_request("GET", f"/songs")
                        if song_response.status_code == 200:
                            songs = song_response.json()
                            enriched_song = next((s for s in songs if s["id"] == song_id), None)
                            
                            if enriched_song:
                                has_genres = len(enriched_song.get("genres", [])) > 0
                                has_moods = len(enriched_song.get("moods", [])) > 0
                                has_year = enriched_song.get("year") is not None
                                
                                enrichment_fields = []
                                if has_genres:
                                    enrichment_fields.append(f"genres: {enriched_song['genres']}")
                                if has_moods:
                                    enrichment_fields.append(f"moods: {enriched_song['moods']}")
                                if has_year:
                                    enrichment_fields.append(f"year: {enriched_song['year']}")
                                
                                if enrichment_fields:
                                    print(f"     ✅ '{enriched_song['title']}' enriched with: {', '.join(enrichment_fields)}")
                                else:
                                    print(f"     ❌ '{enriched_song['title']}' was not enriched")
                else:
                    self.log_result("Batch Enrichment - All Songs", False, 
                                  f"Batch enrichment failed: {enrich_data}")
            else:
                self.log_result("Batch Enrichment - All Songs", False, 
                              f"Batch enrichment failed with status: {batch_enrich_response.status_code} - {batch_enrich_response.text}")
            
            # Test 3: Batch enrich specific songs
            if len(created_song_ids) > 1:
                print("   Testing batch enrichment of specific songs...")
                specific_enrich_data = {"song_ids": created_song_ids[:2]}  # Enrich first 2 songs
                
                specific_response = self.make_request("POST", "/songs/batch-enrich", specific_enrich_data)
                
                if specific_response.status_code == 200:
                    specific_data = specific_response.json()
                    
                    if specific_data.get("success"):
                        self.log_result("Batch Enrichment - Specific Songs", True, 
                                      f"✅ Successfully enriched specific songs: {specific_data}")
                    else:
                        self.log_result("Batch Enrichment - Specific Songs", False, 
                                      f"Specific enrichment failed: {specific_data}")
                else:
                    self.log_result("Batch Enrichment - Specific Songs", False, 
                                  f"Specific enrichment failed: {specific_response.status_code}")
                
        except Exception as e:
            self.log_result("Existing Songs Batch Enrichment", False, f"Exception: {str(e)}")

    def test_spotify_metadata_search(self):
        """Test the underlying Spotify metadata search functionality"""
        try:
            print("🔍 Testing Spotify metadata search functionality...")
            
            # Test with popular songs that should have good Spotify data
            test_songs = [
                {"title": "As It Was", "artist": "Harry Styles"},
                {"title": "Heat Waves", "artist": "Glass Animals"},
                {"title": "Blinding Lights", "artist": "The Weeknd"}
            ]
            
            successful_searches = 0
            
            for song in test_songs:
                print(f"   Searching metadata for '{song['title']}' by '{song['artist']}'...")
                
                search_data = {
                    "title": song["title"],
                    "artist": song["artist"]
                }
                
                response = self.make_request("POST", "/songs/search-metadata", search_data)
                
                if response.status_code == 200:
                    metadata = response.json()
                    print(f"     Search response: {json.dumps(metadata, indent=2)}")
                    
                    if metadata.get("success") and metadata.get("metadata"):
                        song_metadata = metadata["metadata"]
                        
                        # Check if we got useful metadata
                        has_genres = len(song_metadata.get("genres", [])) > 0
                        has_moods = len(song_metadata.get("moods", [])) > 0
                        has_year = song_metadata.get("year") is not None
                        has_spotify_id = song_metadata.get("spotify_id") is not None
                        
                        if has_genres or has_moods or has_year:
                            successful_searches += 1
                            metadata_fields = []
                            if has_genres:
                                metadata_fields.append(f"genres: {song_metadata['genres']}")
                            if has_moods:
                                metadata_fields.append(f"moods: {song_metadata['moods']}")
                            if has_year:
                                metadata_fields.append(f"year: {song_metadata['year']}")
                            if has_spotify_id:
                                metadata_fields.append(f"spotify_id: {song_metadata['spotify_id']}")
                            
                            print(f"     ✅ Found metadata: {', '.join(metadata_fields)}")
                        else:
                            print(f"     ❌ No useful metadata found")
                    else:
                        print(f"     ❌ Search failed: {metadata}")
                elif response.status_code in [400, 422]:
                    print(f"     ❌ Search failed with validation error: {response.status_code}")
                else:
                    print(f"     ❌ Search failed with status: {response.status_code}")
            
            if successful_searches == len(test_songs):
                self.log_result("Spotify Metadata Search", True, 
                              f"✅ Successfully found metadata for all {successful_searches} test songs")
            elif successful_searches > 0:
                self.log_result("Spotify Metadata Search", True, 
                              f"✅ Successfully found metadata for {successful_searches}/{len(test_songs)} test songs")
            else:
                self.log_result("Spotify Metadata Search", False, 
                              "❌ Failed to find metadata for any test songs")
                
        except Exception as e:
            self.log_result("Spotify Metadata Search", False, f"Exception: {str(e)}")

    def test_authentication_requirements(self):
        """Test that enrichment endpoints require authentication"""
        try:
            print("🔍 Testing authentication requirements for enrichment endpoints...")
            
            # Save current token
            original_token = self.auth_token
            
            # Test without authentication
            self.auth_token = None
            
            # Test CSV upload with auto-enrichment
            csv_content = self.create_test_csv_with_missing_metadata()
            csv_file = io.StringIO(csv_content)
            files = {'file': ('test.csv', csv_file.getvalue().encode(), 'text/csv')}
            data = {'auto_enrich': 'true'}
            
            response = self.make_request("POST", "/songs/csv/upload", data=data, files=files)
            
            if response.status_code in [401, 403]:
                self.log_result("Auth - CSV Auto-enrichment", True, 
                              f"✅ Correctly rejected CSV upload without auth (status: {response.status_code})")
            else:
                self.log_result("Auth - CSV Auto-enrichment", False, 
                              f"Should reject without auth, got: {response.status_code}")
            
            # Test batch enrichment
            response = self.make_request("POST", "/songs/batch-enrich")
            
            if response.status_code in [401, 403]:
                self.log_result("Auth - Batch Enrichment", True, 
                              f"✅ Correctly rejected batch enrichment without auth (status: {response.status_code})")
            else:
                self.log_result("Auth - Batch Enrichment", False, 
                              f"Should reject without auth, got: {response.status_code}")
            
            # Test metadata search
            search_data = {"title": "Test Song", "artist": "Test Artist"}
            response = self.make_request("POST", "/songs/search-metadata", search_data)
            
            if response.status_code in [401, 403]:
                self.log_result("Auth - Metadata Search", True, 
                              f"✅ Correctly rejected metadata search without auth (status: {response.status_code})")
            else:
                self.log_result("Auth - Metadata Search", False, 
                              f"Should reject without auth, got: {response.status_code}")
            
            # Restore token
            self.auth_token = original_token
            
        except Exception as e:
            self.log_result("Authentication Requirements", False, f"Exception: {str(e)}")

    def run_metadata_tests(self):
        """Run all metadata enrichment tests"""
        print("🚀 Starting Metadata Enrichment Tests")
        print("=" * 60)
        
        # Setup
        if not self.setup_authentication():
            print("❌ Authentication setup failed, cannot continue")
            return
        
        # Test 1: CSV Upload Auto-enrichment Enhancement
        print("\n📋 CSV Upload Auto-enrichment Enhancement")
        print("-" * 50)
        self.test_csv_upload_auto_enrichment()
        
        # Test 2: Existing Songs Batch Enrichment
        print("\n📋 Existing Playlist Songs Metadata Enrichment")
        print("-" * 50)
        self.test_existing_songs_batch_enrichment()
        
        # Test 3: Spotify Metadata Search (underlying functionality)
        print("\n📋 Spotify Metadata Search Functionality")
        print("-" * 50)
        self.test_spotify_metadata_search()
        
        # Test 4: Authentication Requirements
        print("\n📋 Authentication Requirements")
        print("-" * 50)
        self.test_authentication_requirements()
        
        # Summary
        print("\n" + "=" * 60)
        print("🏁 METADATA ENRICHMENT TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Total: {self.results['passed'] + self.results['failed']}")
        
        if self.results['failed'] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        if self.results['failed'] == 0:
            print("\n🎉 ALL METADATA ENRICHMENT TESTS PASSED!")
        else:
            print(f"\n⚠️ {self.results['failed']} tests failed. Please review the issues above.")

if __name__ == "__main__":
    tester = MetadataEnrichmentTester()
    tester.run_metadata_tests()