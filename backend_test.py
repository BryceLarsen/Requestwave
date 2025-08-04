#!/usr/bin/env python3
"""
Comprehensive Backend API Tests for RequestWave
Tests authentication, song management, requests, CSV upload, and filtering
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://9107567e-848c-44f8-b0e6-9b09dbdb10e6.preview.emergentagent.com/api"
TEST_MUSICIAN = {
    "name": "Jazz Virtuoso",
    "email": "jazz.virtuoso@requestwave.com",
    "password": "SecurePassword123!"
}

class RequestWaveAPITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
        self.test_song_id = None
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

    def make_request(self, method: str, endpoint: str, data: Any = None, files: Any = None, headers: Dict = None) -> requests.Response:
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
                response = requests.get(url, headers=request_headers, params=data)
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

    def test_health_check(self):
        """Test health check endpoint"""
        try:
            response = self.make_request("GET", "/health")
            if response.status_code == 200:
                data = response.json()
                if "status" in data and data["status"] == "healthy":
                    self.log_result("Health Check", True, "API is healthy")
                else:
                    self.log_result("Health Check", False, f"Unexpected response: {data}")
            else:
                self.log_result("Health Check", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_result("Health Check", False, f"Exception: {str(e)}")

    def test_musician_registration(self):
        """Test musician registration"""
        try:
            response = self.make_request("POST", "/auth/register", TEST_MUSICIAN)
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "musician" in data:
                    self.auth_token = data["token"]
                    self.musician_id = data["musician"]["id"]
                    self.musician_slug = data["musician"]["slug"]
                    self.log_result("Musician Registration", True, f"Registered musician: {data['musician']['name']}")
                else:
                    self.log_result("Musician Registration", False, f"Missing token or musician in response: {data}")
            elif response.status_code == 400:
                # Musician might already exist, try login instead
                self.test_musician_login()
            else:
                self.log_result("Musician Registration", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Musician Registration", False, f"Exception: {str(e)}")

    def test_musician_login(self):
        """Test musician login"""
        try:
            login_data = {
                "email": TEST_MUSICIAN["email"],
                "password": TEST_MUSICIAN["password"]
            }
            response = self.make_request("POST", "/auth/login", login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "musician" in data:
                    self.auth_token = data["token"]
                    self.musician_id = data["musician"]["id"]
                    self.musician_slug = data["musician"]["slug"]
                    self.log_result("Musician Login", True, f"Logged in musician: {data['musician']['name']}")
                else:
                    self.log_result("Musician Login", False, f"Missing token or musician in response: {data}")
            else:
                self.log_result("Musician Login", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Musician Login", False, f"Exception: {str(e)}")

    def test_jwt_token_validation(self):
        """Test JWT token validation by accessing protected endpoint"""
        try:
            if not self.auth_token:
                self.log_result("JWT Token Validation", False, "No auth token available")
                return
            
            response = self.make_request("GET", "/songs")
            
            if response.status_code == 200:
                self.log_result("JWT Token Validation", True, "Token successfully validated")
            elif response.status_code == 401:
                self.log_result("JWT Token Validation", False, "Token validation failed - unauthorized")
            else:
                self.log_result("JWT Token Validation", False, f"Unexpected status code: {response.status_code}")
        except Exception as e:
            self.log_result("JWT Token Validation", False, f"Exception: {str(e)}")

    def test_create_song(self):
        """Test song creation"""
        try:
            song_data = {
                "title": "Test Jazz Standard",
                "artist": "Miles Davis",
                "genres": ["Jazz", "Bebop"],
                "moods": ["Smooth", "Sophisticated"],
                "year": 1959,
                "notes": "Classic jazz standard for testing"
            }
            
            response = self.make_request("POST", "/songs", song_data)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and data["title"] == song_data["title"]:
                    self.test_song_id = data["id"]
                    self.log_result("Create Song", True, f"Created song: {data['title']}")
                else:
                    self.log_result("Create Song", False, f"Unexpected response structure: {data}")
            else:
                self.log_result("Create Song", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Create Song", False, f"Exception: {str(e)}")

    def test_get_songs(self):
        """Test retrieving songs"""
        try:
            response = self.make_request("GET", "/songs")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_result("Get Songs", True, f"Retrieved {len(data)} songs")
                else:
                    self.log_result("Get Songs", False, f"Expected list, got: {type(data)}")
            else:
                self.log_result("Get Songs", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Get Songs", False, f"Exception: {str(e)}")

    def test_update_song(self):
        """Test song update"""
        try:
            if not self.test_song_id:
                self.log_result("Update Song", False, "No test song ID available")
                return
            
            update_data = {
                "title": "Updated Jazz Standard",
                "artist": "Miles Davis",
                "genres": ["Jazz", "Cool Jazz"],
                "moods": ["Mellow", "Contemplative"],
                "year": 1959,
                "notes": "Updated notes for testing"
            }
            
            response = self.make_request("PUT", f"/songs/{self.test_song_id}", update_data)
            
            if response.status_code == 200:
                data = response.json()
                if data["title"] == update_data["title"]:
                    self.log_result("Update Song", True, f"Updated song: {data['title']}")
                else:
                    self.log_result("Update Song", False, f"Title not updated correctly: {data}")
            else:
                self.log_result("Update Song", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Update Song", False, f"Exception: {str(e)}")

    def test_get_musician_by_slug(self):
        """Test getting musician by slug"""
        try:
            if not self.musician_slug:
                self.log_result("Get Musician by Slug", False, "No musician slug available")
                return
            
            response = self.make_request("GET", f"/musicians/{self.musician_slug}")
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "name" in data and "slug" in data:
                    self.log_result("Get Musician by Slug", True, f"Retrieved musician: {data['name']}")
                else:
                    self.log_result("Get Musician by Slug", False, f"Missing required fields: {data}")
            else:
                self.log_result("Get Musician by Slug", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Get Musician by Slug", False, f"Exception: {str(e)}")

    def test_advanced_filtering(self):
        """Test advanced song filtering"""
        try:
            if not self.musician_slug:
                self.log_result("Advanced Filtering", False, "No musician slug available")
                return
            
            # Test filtering by genre
            params = {"genre": "Jazz"}
            response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs", params)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    # Check if all returned songs have Jazz genre
                    jazz_songs = [song for song in data if "Jazz" in song.get("genres", [])]
                    if len(jazz_songs) == len(data):
                        self.log_result("Advanced Filtering - Genre", True, f"Found {len(data)} Jazz songs")
                    else:
                        self.log_result("Advanced Filtering - Genre", False, f"Filter not working correctly")
                else:
                    self.log_result("Advanced Filtering - Genre", False, f"Expected list, got: {type(data)}")
            else:
                self.log_result("Advanced Filtering - Genre", False, f"Status code: {response.status_code}")
            
            # Test filtering by artist
            params = {"artist": "Miles"}
            response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs", params)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_result("Advanced Filtering - Artist", True, f"Found {len(data)} songs by Miles")
                else:
                    self.log_result("Advanced Filtering - Artist", False, f"Expected list, got: {type(data)}")
            else:
                self.log_result("Advanced Filtering - Artist", False, f"Status code: {response.status_code}")
                
        except Exception as e:
            self.log_result("Advanced Filtering", False, f"Exception: {str(e)}")

    def test_create_request(self):
        """Test creating a song request"""
        try:
            if not self.test_song_id:
                self.log_result("Create Request", False, "No test song ID available")
                return
            
            request_data = {
                "song_id": self.test_song_id,
                "requester_name": "Jazz Fan",
                "requester_email": "fan@example.com",
                "dedication": "For my anniversary!",
                "tip_amount": 5.0
            }
            
            response = self.make_request("POST", "/requests", request_data)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and data["status"] == "pending":
                    self.test_request_id = data["id"]
                    self.log_result("Create Request", True, f"Created request: {data['id']}")
                else:
                    self.log_result("Create Request", False, f"Unexpected response structure: {data}")
            else:
                self.log_result("Create Request", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Create Request", False, f"Exception: {str(e)}")

    def test_get_musician_requests(self):
        """Test getting musician requests"""
        try:
            response = self.make_request("GET", f"/requests/musician/{self.musician_id}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_result("Get Musician Requests", True, f"Retrieved {len(data)} requests")
                else:
                    self.log_result("Get Musician Requests", False, f"Expected list, got: {type(data)}")
            else:
                self.log_result("Get Musician Requests", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Get Musician Requests", False, f"Exception: {str(e)}")

    def test_update_request_status(self):
        """Test updating request status"""
        try:
            if not self.test_request_id:
                self.log_result("Update Request Status", False, "No test request ID available")
                return
            
            # Test updating to accepted - fix the request format
            response = self.make_request("PUT", f"/requests/{self.test_request_id}/status?status=accepted")
            
            if response.status_code == 200:
                self.log_result("Update Request Status", True, "Successfully updated request status")
            else:
                self.log_result("Update Request Status", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Update Request Status", False, f"Exception: {str(e)}")

    def test_real_time_polling(self):
        """Test real-time polling endpoint"""
        try:
            if not self.musician_id:
                self.log_result("Real-time Polling", False, "No musician ID available")
                return
            
            response = self.make_request("GET", f"/requests/updates/{self.musician_id}")
            
            if response.status_code == 200:
                data = response.json()
                if "requests" in data and "timestamp" in data:
                    self.log_result("Real-time Polling", True, f"Polling endpoint working, timestamp: {data['timestamp']}")
                else:
                    self.log_result("Real-time Polling", False, f"Missing required fields: {data}")
            else:
                self.log_result("Real-time Polling", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Real-time Polling", False, f"Exception: {str(e)}")

    def test_csv_preview_valid(self):
        """Test CSV preview with valid file"""
        try:
            with open('/app/test_songs_valid.csv', 'rb') as f:
                files = {'file': ('test_songs_valid.csv', f, 'text/csv')}
                response = self.make_request("POST", "/songs/csv/preview", files=files)
            
            if response.status_code == 200:
                data = response.json()
                if "preview" in data and "total_rows" in data and "valid_rows" in data:
                    self.log_result("CSV Preview - Valid File", True, f"Preview shows {data['valid_rows']} valid rows out of {data['total_rows']}")
                else:
                    self.log_result("CSV Preview - Valid File", False, f"Missing required fields: {data}")
            else:
                self.log_result("CSV Preview - Valid File", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("CSV Preview - Valid File", False, f"Exception: {str(e)}")

    def test_csv_preview_invalid(self):
        """Test CSV preview with invalid file"""
        try:
            with open('/app/test_songs_invalid.csv', 'rb') as f:
                files = {'file': ('test_songs_invalid.csv', f, 'text/csv')}
                response = self.make_request("POST", "/songs/csv/preview", files=files)
            
            if response.status_code == 200:
                data = response.json()
                if "errors" in data and len(data["errors"]) > 0:
                    self.log_result("CSV Preview - Invalid File", True, f"Correctly detected {len(data['errors'])} errors")
                else:
                    self.log_result("CSV Preview - Invalid File", False, f"Should have detected errors: {data}")
            else:
                self.log_result("CSV Preview - Invalid File", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("CSV Preview - Invalid File", False, f"Exception: {str(e)}")

    def test_csv_preview_missing_columns(self):
        """Test CSV preview with missing required columns"""
        try:
            with open('/app/test_songs_missing_columns.csv', 'rb') as f:
                files = {'file': ('test_songs_missing_columns.csv', f, 'text/csv')}
                response = self.make_request("POST", "/songs/csv/preview", files=files)
            
            if response.status_code == 400:
                self.log_result("CSV Preview - Missing Columns", True, "Correctly rejected file with missing columns")
            else:
                self.log_result("CSV Preview - Missing Columns", False, f"Should have returned 400, got: {response.status_code}")
        except Exception as e:
            self.log_result("CSV Preview - Missing Columns", False, f"Exception: {str(e)}")

    def test_csv_upload_valid(self):
        """Test CSV upload with valid file"""
        try:
            with open('/app/test_songs_valid.csv', 'rb') as f:
                files = {'file': ('test_songs_valid.csv', f, 'text/csv')}
                response = self.make_request("POST", "/songs/csv/upload", files=files)
            
            if response.status_code == 200:
                data = response.json()
                if "success" in data and data["success"] and "songs_added" in data:
                    self.log_result("CSV Upload - Valid File", True, f"Successfully uploaded {data['songs_added']} songs")
                else:
                    self.log_result("CSV Upload - Valid File", False, f"Upload failed: {data}")
            else:
                self.log_result("CSV Upload - Valid File", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("CSV Upload - Valid File", False, f"Exception: {str(e)}")

    def test_csv_duplicate_detection(self):
        """Test CSV duplicate detection by uploading same file twice"""
        try:
            # Upload the same file again to test duplicate detection
            with open('/app/test_songs_valid.csv', 'rb') as f:
                files = {'file': ('test_songs_valid.csv', f, 'text/csv')}
                response = self.make_request("POST", "/songs/csv/upload", files=files)
            
            if response.status_code == 200:
                data = response.json()
                if "errors" in data and len(data["errors"]) > 0:
                    # Check if errors mention duplicates
                    duplicate_errors = [error for error in data["errors"] if "duplicate" in error.lower()]
                    if duplicate_errors:
                        self.log_result("CSV Duplicate Detection", True, f"Correctly detected {len(duplicate_errors)} duplicates")
                    else:
                        self.log_result("CSV Duplicate Detection", False, f"No duplicate errors found: {data['errors']}")
                else:
                    self.log_result("CSV Duplicate Detection", False, f"Should have detected duplicates: {data}")
            else:
                self.log_result("CSV Duplicate Detection", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("CSV Duplicate Detection", False, f"Exception: {str(e)}")

    def test_spotify_playlist_import(self):
        """Test Spotify playlist import functionality - CRITICAL FIX TEST"""
        try:
            if not self.auth_token:
                self.log_result("Spotify Playlist Import", False, "No auth token available")
                return
            
            # Test with the EXACT URL from the user report
            playlist_data = {
                "playlist_url": "https://open.spotify.com/playlist/37i9dQZEVXbLRQDuF5jeBp",
                "platform": "spotify"
            }
            
            print(f"🔍 Testing Spotify playlist import with URL: {playlist_data['playlist_url']}")
            response = self.make_request("POST", "/songs/playlist/import", playlist_data)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Import response: {json.dumps(data, indent=2)}")
                
                if "success" in data and data["success"] and "songs_added" in data:
                    if data["songs_added"] > 0:
                        self.log_result("Spotify Playlist Import", True, f"Successfully imported {data['songs_added']} songs from Spotify playlist")
                        
                        # CRITICAL: Verify songs were actually added to database with REAL song data
                        songs_response = self.make_request("GET", "/songs")
                        if songs_response.status_code == 200:
                            songs = songs_response.json()
                            
                            # Find the most recently imported songs
                            imported_songs = [song for song in songs if "spotify" in song.get("notes", "").lower() or "demo" in song.get("notes", "").lower()]
                            
                            if len(imported_songs) > 0:
                                print(f"🎵 Found {len(imported_songs)} imported songs:")
                                
                                # CRITICAL TEST: Check if songs have REAL titles (not generic/placeholder data)
                                real_song_count = 0
                                placeholder_songs = []
                                
                                for song in imported_songs[:5]:  # Check first 5 songs
                                    title = song.get("title", "")
                                    artist = song.get("artist", "")
                                    print(f"   • '{title}' by '{artist}' (genres: {song.get('genres', [])}, year: {song.get('year', 'N/A')})")
                                    
                                    # Check for placeholder/generic data patterns
                                    if any(placeholder in title.lower() for placeholder in ["sample", "demo", "test", "unknown", "playlist"]):
                                        placeholder_songs.append(f"'{title}' by '{artist}'")
                                    elif any(placeholder in artist.lower() for placeholder in ["demo", "test", "unknown"]):
                                        placeholder_songs.append(f"'{title}' by '{artist}'")
                                    else:
                                        real_song_count += 1
                                
                                if real_song_count > 0 and len(placeholder_songs) == 0:
                                    self.log_result("Spotify Playlist Import - Real Song Data", True, f"✅ CRITICAL FIX VERIFIED: All {real_song_count} songs have real titles/artists (no placeholder data)")
                                elif real_song_count > len(placeholder_songs):
                                    self.log_result("Spotify Playlist Import - Real Song Data", True, f"✅ MOSTLY REAL DATA: {real_song_count} real songs, {len(placeholder_songs)} placeholder songs")
                                else:
                                    self.log_result("Spotify Playlist Import - Real Song Data", False, f"❌ CRITICAL BUG: Found placeholder songs: {placeholder_songs}")
                                
                                self.log_result("Spotify Playlist Import - Database Verification", True, f"Found {len(imported_songs)} imported songs in database")
                            else:
                                self.log_result("Spotify Playlist Import - Database Verification", False, "❌ CRITICAL BUG: No imported songs found in database")
                    else:
                        self.log_result("Spotify Playlist Import", False, f"❌ CRITICAL BUG: No songs were imported: {data}")
                else:
                    self.log_result("Spotify Playlist Import", False, f"❌ CRITICAL BUG: Unexpected response structure: {data}")
            else:
                self.log_result("Spotify Playlist Import", False, f"❌ CRITICAL BUG: Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Spotify Playlist Import", False, f"❌ CRITICAL BUG: Exception: {str(e)}")

    def test_apple_music_playlist_import(self):
        """Test Apple Music playlist import functionality - CRITICAL FIX TEST"""
        try:
            if not self.auth_token:
                self.log_result("Apple Music Playlist Import", False, "No auth token available")
                return
            
            # Test with a valid Apple Music playlist URL
            playlist_data = {
                "playlist_url": "https://music.apple.com/us/playlist/todays-hits/pl.f4d106fed2bd41149aaacabb233eb5eb",
                "platform": "apple_music"
            }
            
            print(f"🔍 Testing Apple Music playlist import with URL: {playlist_data['playlist_url']}")
            response = self.make_request("POST", "/songs/playlist/import", playlist_data)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Import response: {json.dumps(data, indent=2)}")
                
                if "success" in data and data["success"] and "songs_added" in data:
                    if data["songs_added"] > 0:
                        self.log_result("Apple Music Playlist Import", True, f"Successfully imported {data['songs_added']} songs from Apple Music playlist")
                        
                        # CRITICAL: Verify songs were actually added to database with REAL song data
                        songs_response = self.make_request("GET", "/songs")
                        if songs_response.status_code == 200:
                            songs = songs_response.json()
                            
                            # Find the most recently imported songs
                            apple_songs = [song for song in songs if "apple" in song.get("notes", "").lower() or "demo" in song.get("notes", "").lower()]
                            
                            if len(apple_songs) > 0:
                                print(f"🎵 Found {len(apple_songs)} imported Apple Music songs:")
                                
                                # CRITICAL TEST: Check if songs have REAL titles (not generic/placeholder data)
                                real_song_count = 0
                                placeholder_songs = []
                                
                                for song in apple_songs[:5]:  # Check first 5 songs
                                    title = song.get("title", "")
                                    artist = song.get("artist", "")
                                    print(f"   • '{title}' by '{artist}' (genres: {song.get('genres', [])}, year: {song.get('year', 'N/A')})")
                                    
                                    # Check for placeholder/generic data patterns
                                    if any(placeholder in title.lower() for placeholder in ["sample", "demo", "test", "unknown", "playlist"]):
                                        placeholder_songs.append(f"'{title}' by '{artist}'")
                                    elif any(placeholder in artist.lower() for placeholder in ["demo", "test", "unknown"]):
                                        placeholder_songs.append(f"'{title}' by '{artist}'")
                                    else:
                                        real_song_count += 1
                                
                                if real_song_count > 0 and len(placeholder_songs) == 0:
                                    self.log_result("Apple Music Playlist Import - Real Song Data", True, f"✅ CRITICAL FIX VERIFIED: All {real_song_count} songs have real titles/artists (no placeholder data)")
                                elif real_song_count > len(placeholder_songs):
                                    self.log_result("Apple Music Playlist Import - Real Song Data", True, f"✅ MOSTLY REAL DATA: {real_song_count} real songs, {len(placeholder_songs)} placeholder songs")
                                else:
                                    self.log_result("Apple Music Playlist Import - Real Song Data", False, f"❌ CRITICAL BUG: Found placeholder songs: {placeholder_songs}")
                                
                                self.log_result("Apple Music Playlist Import - Database Verification", True, f"Found {len(apple_songs)} imported songs in database")
                            else:
                                self.log_result("Apple Music Playlist Import - Database Verification", False, "❌ CRITICAL BUG: No imported songs found in database")
                    else:
                        self.log_result("Apple Music Playlist Import", False, f"❌ CRITICAL BUG: No songs were imported: {data}")
                else:
                    self.log_result("Apple Music Playlist Import", False, f"❌ CRITICAL BUG: Unexpected response structure: {data}")
            else:
                self.log_result("Apple Music Playlist Import", False, f"❌ CRITICAL BUG: Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Apple Music Playlist Import", False, f"❌ CRITICAL BUG: Exception: {str(e)}")

    def test_playlist_import_authentication(self):
        """Test playlist import requires authentication"""
        try:
            # Save current token
            original_token = self.auth_token
            
            # Test without token
            self.auth_token = None
            playlist_data = {
                "playlist_url": "https://open.spotify.com/playlist/37i9dQZEVXbLRQDuF5jeBp",
                "platform": "spotify"
            }
            
            response = self.make_request("POST", "/songs/playlist/import", playlist_data)
            
            if response.status_code in [401, 403]:  # Accept both 401 and 403 as valid auth failures
                self.log_result("Playlist Import Authentication - No Token", True, f"Correctly rejected request without auth token (status: {response.status_code})")
            else:
                self.log_result("Playlist Import Authentication - No Token", False, f"Should have returned 401/403, got: {response.status_code}")
            
            # Test with invalid token
            self.auth_token = "invalid_token_12345"
            response = self.make_request("POST", "/songs/playlist/import", playlist_data)
            
            if response.status_code == 401:
                self.log_result("Playlist Import Authentication - Invalid Token", True, "Correctly rejected request with invalid token")
            else:
                self.log_result("Playlist Import Authentication - Invalid Token", False, f"Should have returned 401, got: {response.status_code}")
            
            # Restore original token
            self.auth_token = original_token
            
        except Exception as e:
            self.log_result("Playlist Import Authentication", False, f"Exception: {str(e)}")

    def test_playlist_import_invalid_urls(self):
        """Test playlist import with invalid URLs"""
        try:
            if not self.auth_token:
                self.log_result("Playlist Import Invalid URLs", False, "No auth token available")
                return
            
            # Test invalid Spotify URL
            invalid_spotify_data = {
                "playlist_url": "https://invalid-spotify-url.com/playlist/123",
                "platform": "spotify"
            }
            
            response = self.make_request("POST", "/songs/playlist/import", invalid_spotify_data)
            
            if response.status_code == 400:
                self.log_result("Playlist Import - Invalid Spotify URL", True, "Correctly rejected invalid Spotify URL")
            else:
                self.log_result("Playlist Import - Invalid Spotify URL", False, f"Should have returned 400, got: {response.status_code}")
            
            # Test invalid Apple Music URL
            invalid_apple_data = {
                "playlist_url": "https://invalid-apple-url.com/playlist/123",
                "platform": "apple_music"
            }
            
            response = self.make_request("POST", "/songs/playlist/import", invalid_apple_data)
            
            if response.status_code == 400:
                self.log_result("Playlist Import - Invalid Apple Music URL", True, "Correctly rejected invalid Apple Music URL")
            else:
                self.log_result("Playlist Import - Invalid Apple Music URL", False, f"Should have returned 400, got: {response.status_code}")
            
            # Test unsupported platform
            unsupported_platform_data = {
                "playlist_url": "https://open.spotify.com/playlist/37i9dQZEVXbLRQDuF5jeBp",
                "platform": "youtube"
            }
            
            response = self.make_request("POST", "/songs/playlist/import", unsupported_platform_data)
            
            if response.status_code == 400:
                self.log_result("Playlist Import - Unsupported Platform", True, "Correctly rejected unsupported platform")
            else:
                self.log_result("Playlist Import - Unsupported Platform", False, f"Should have returned 400, got: {response.status_code}")
                
        except Exception as e:
            self.log_result("Playlist Import Invalid URLs", False, f"Exception: {str(e)}")

    def test_playlist_import_song_data_quality(self):
        """Test that imported songs have proper data quality"""
        try:
            if not self.auth_token:
                self.log_result("Playlist Import Song Data Quality", False, "No auth token available")
                return
            
            # Import a playlist first
            playlist_data = {
                "playlist_url": "https://open.spotify.com/playlist/37i9dQZEVXbLRQDuF5jeBp",
                "platform": "spotify"
            }
            
            import_response = self.make_request("POST", "/songs/playlist/import", playlist_data)
            
            if import_response.status_code == 200:
                import_data = import_response.json()
                if import_data.get("songs_added", 0) > 0:
                    # Get all songs and check the imported ones
                    songs_response = self.make_request("GET", "/songs")
                    if songs_response.status_code == 200:
                        songs = songs_response.json()
                        
                        # Find recently imported songs (demo songs from playlist import)
                        imported_songs = [song for song in songs if "demo" in song.get("notes", "").lower() or "spotify" in song.get("notes", "").lower()]
                        
                        if imported_songs:
                            quality_issues = []
                            
                            for song in imported_songs:
                                # Check required fields
                                if not song.get("title") or song["title"].strip() == "":
                                    quality_issues.append(f"Song missing title: {song}")
                                if not song.get("artist") or song["artist"].strip() == "":
                                    quality_issues.append(f"Song missing artist: {song}")
                                
                                # Check optional but expected fields
                                if not song.get("genres") or len(song["genres"]) == 0:
                                    quality_issues.append(f"Song missing genres: {song['title']}")
                                if not song.get("moods") or len(song["moods"]) == 0:
                                    quality_issues.append(f"Song missing moods: {song['title']}")
                                if not song.get("year"):
                                    quality_issues.append(f"Song missing year: {song['title']}")
                            
                            if len(quality_issues) == 0:
                                self.log_result("Playlist Import Song Data Quality", True, f"All {len(imported_songs)} imported songs have proper data quality")
                            else:
                                self.log_result("Playlist Import Song Data Quality", False, f"Found {len(quality_issues)} data quality issues: {quality_issues[:3]}")
                        else:
                            self.log_result("Playlist Import Song Data Quality", False, "No imported songs found to check quality")
                    else:
                        self.log_result("Playlist Import Song Data Quality", False, "Could not retrieve songs to check quality")
                else:
                    self.log_result("Playlist Import Song Data Quality", False, "No songs were imported to check quality")
            else:
                self.log_result("Playlist Import Song Data Quality", False, f"Could not import playlist for quality check: {import_response.status_code}")
                
        except Exception as e:
            self.log_result("Playlist Import Song Data Quality", False, f"Exception: {str(e)}")

    def test_playlist_import_duplicate_detection(self):
        """Test that playlist import detects and handles duplicates"""
        try:
            if not self.auth_token:
                self.log_result("Playlist Import Duplicate Detection", False, "No auth token available")
                return
            
            # Import the same playlist twice
            playlist_data = {
                "playlist_url": "https://open.spotify.com/playlist/37i9dQZEVXbLRQDuF5jeBp",
                "platform": "spotify"
            }
            
            # First import
            first_response = self.make_request("POST", "/songs/playlist/import", playlist_data)
            
            if first_response.status_code == 200:
                first_data = first_response.json()
                first_songs_added = first_data.get("songs_added", 0)
                
                if first_songs_added > 0:
                    # Second import (should detect duplicates)
                    second_response = self.make_request("POST", "/songs/playlist/import", playlist_data)
                    
                    if second_response.status_code == 200:
                        second_data = second_response.json()
                        second_songs_added = second_data.get("songs_added", 0)
                        songs_skipped = second_data.get("songs_skipped", 0)
                        errors = second_data.get("errors", [])
                        
                        # Check if duplicates were detected
                        duplicate_errors = [error for error in errors if "duplicate" in error.lower() or "skipped" in error.lower()]
                        
                        if songs_skipped > 0 or duplicate_errors:
                            self.log_result("Playlist Import Duplicate Detection", True, f"Correctly detected duplicates: {songs_skipped} skipped, {len(duplicate_errors)} duplicate errors")
                        else:
                            self.log_result("Playlist Import Duplicate Detection", False, f"Should have detected duplicates but didn't: {second_data}")
                    else:
                        self.log_result("Playlist Import Duplicate Detection", False, f"Second import failed: {second_response.status_code}")
                else:
                    self.log_result("Playlist Import Duplicate Detection", False, "First import added no songs, cannot test duplicates")
            else:
                self.log_result("Playlist Import Duplicate Detection", False, f"First import failed: {first_response.status_code}")
                
        except Exception as e:
            self.log_result("Playlist Import Duplicate Detection", False, f"Exception: {str(e)}")

    def test_delete_song(self):
        """Test song deletion - CRITICAL FIX TEST"""
        try:
            if not self.test_song_id:
                self.log_result("Delete Song", False, "No test song ID available")
                return
            
            print(f"🔍 Testing song deletion for song ID: {self.test_song_id}")
            
            # First, verify the song exists
            songs_before_response = self.make_request("GET", "/songs")
            if songs_before_response.status_code == 200:
                songs_before = songs_before_response.json()
                song_exists_before = any(song["id"] == self.test_song_id for song in songs_before)
                print(f"📊 Song exists before deletion: {song_exists_before}")
                
                if not song_exists_before:
                    self.log_result("Delete Song - Pre-check", False, "Test song not found in database before deletion")
                    return
            else:
                self.log_result("Delete Song - Pre-check", False, f"Could not retrieve songs before deletion: {songs_before_response.status_code}")
                return
            
            # Test deletion
            response = self.make_request("DELETE", f"/songs/{self.test_song_id}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Delete response: {json.dumps(data, indent=2)}")
                
                if "message" in data:
                    self.log_result("Delete Song - API Response", True, f"✅ API returned success: {data['message']}")
                    
                    # CRITICAL TEST: Verify the song is actually deleted from the database
                    songs_after_response = self.make_request("GET", "/songs")
                    if songs_after_response.status_code == 200:
                        songs_after = songs_after_response.json()
                        song_exists_after = any(song["id"] == self.test_song_id for song in songs_after)
                        
                        print(f"📊 Song exists after deletion: {song_exists_after}")
                        print(f"📊 Songs count before: {len(songs_before)}, after: {len(songs_after)}")
                        
                        if not song_exists_after:
                            self.log_result("Delete Song - Database Verification", True, f"✅ CRITICAL FIX VERIFIED: Song successfully deleted from database")
                            self.log_result("Delete Song", True, "✅ CRITICAL FIX VERIFIED: Song deletion working correctly")
                        else:
                            self.log_result("Delete Song - Database Verification", False, f"❌ CRITICAL BUG: Song still exists in database after deletion")
                            self.log_result("Delete Song", False, f"❌ CRITICAL BUG: Song not actually deleted from database")
                    else:
                        self.log_result("Delete Song - Database Verification", False, f"Could not verify deletion: {songs_after_response.status_code}")
                        self.log_result("Delete Song", False, f"Could not verify deletion from database")
                else:
                    self.log_result("Delete Song", False, f"❌ CRITICAL BUG: Unexpected response format: {data}")
            else:
                self.log_result("Delete Song", False, f"❌ CRITICAL BUG: Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Delete Song", False, f"❌ CRITICAL BUG: Exception: {str(e)}")

    def test_delete_song_authentication(self):
        """Test that song deletion requires proper authentication - CRITICAL FIX TEST"""
        try:
            if not self.test_song_id:
                # Create a temporary song for this test
                temp_song_data = {
                    "title": "Temp Song for Auth Test",
                    "artist": "Test Artist",
                    "genres": ["Test"],
                    "moods": ["Test"],
                    "year": 2023,
                    "notes": "Temporary song for authentication test"
                }
                
                create_response = self.make_request("POST", "/songs", temp_song_data)
                if create_response.status_code == 200:
                    temp_song_id = create_response.json()["id"]
                else:
                    self.log_result("Delete Song Authentication", False, "Could not create temporary song for auth test")
                    return
            else:
                temp_song_id = self.test_song_id
            
            # Save current token
            original_token = self.auth_token
            
            # Test without token
            self.auth_token = None
            print(f"🔍 Testing song deletion without authentication for song ID: {temp_song_id}")
            
            response = self.make_request("DELETE", f"/songs/{temp_song_id}")
            
            if response.status_code in [401, 403]:  # Accept both 401 and 403 as valid auth failures
                self.log_result("Delete Song Authentication - No Token", True, f"✅ Correctly rejected deletion without auth token (status: {response.status_code})")
            else:
                self.log_result("Delete Song Authentication - No Token", False, f"❌ CRITICAL BUG: Should have returned 401/403, got: {response.status_code}")
            
            # Test with invalid token
            self.auth_token = "invalid_token_12345"
            response = self.make_request("DELETE", f"/songs/{temp_song_id}")
            
            if response.status_code == 401:
                self.log_result("Delete Song Authentication - Invalid Token", True, "✅ Correctly rejected deletion with invalid token")
            else:
                self.log_result("Delete Song Authentication - Invalid Token", False, f"❌ CRITICAL BUG: Should have returned 401, got: {response.status_code}")
            
            # Restore original token
            self.auth_token = original_token
            
        except Exception as e:
            self.log_result("Delete Song Authentication", False, f"❌ CRITICAL BUG: Exception: {str(e)}")
            # Restore token in case of exception
            if 'original_token' in locals():
                self.auth_token = original_token

    def run_critical_fixes_test(self):
        """Run ONLY the critical fixes tests requested in the review"""
        print("🚨 CRITICAL FIXES TESTING - RequestWave Backend API")
        print("=" * 60)
        print("Testing TWO CRITICAL FIXES:")
        print("1. Playlist Import Fix - Real Song Data Extraction")
        print("2. Delete Button Fix - Song Deletion")
        print("=" * 60)
        
        # Authentication setup
        self.test_musician_registration()
        self.test_jwt_token_validation()
        
        # Create a test song for deletion testing
        self.test_create_song()
        
        print("\n🔥 CRITICAL FIX #1: PLAYLIST IMPORT - REAL SONG DATA")
        print("-" * 50)
        
        # Test playlist import with the EXACT URLs from user report
        self.test_spotify_playlist_import()
        self.test_apple_music_playlist_import()
        self.test_playlist_import_authentication()
        
        print("\n🔥 CRITICAL FIX #2: DELETE BUTTON - SONG DELETION")
        print("-" * 50)
        
        # Test song deletion functionality
        self.test_delete_song_authentication()
        self.test_delete_song()  # This should be last as it deletes the test song
        
        # Print summary
        print("\n" + "=" * 60)
        print("🏁 CRITICAL FIXES TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n🔍 Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        # Specific summary for the two critical fixes
        playlist_tests = [error for error in self.results['errors'] if 'playlist' in error.lower() or 'import' in error.lower()]
        delete_tests = [error for error in self.results['errors'] if 'delete' in error.lower()]
        
        print(f"\n📊 CRITICAL FIX #1 (Playlist Import): {'✅ WORKING' if len(playlist_tests) == 0 else '❌ FAILING'}")
        if playlist_tests:
            for error in playlist_tests:
                print(f"   • {error}")
        
        print(f"📊 CRITICAL FIX #2 (Song Deletion): {'✅ WORKING' if len(delete_tests) == 0 else '❌ FAILING'}")
        if delete_tests:
            for error in delete_tests:
                print(f"   • {error}")
        
        return self.results['failed'] == 0
    def run_all_tests(self):
        """Run all tests in order"""
        print("=" * 50)
        
        # Health check
        self.test_health_check()
        
        # Authentication tests
        self.test_musician_registration()
        self.test_jwt_token_validation()
        
        # Song management tests
        self.test_create_song()
        self.test_get_songs()
        self.test_update_song()
        
        # Musician profile tests
        self.test_get_musician_by_slug()
        
        # Advanced filtering tests
        self.test_advanced_filtering()
        
        # Request management tests
        self.test_create_request()
        self.test_get_musician_requests()
        self.test_update_request_status()
        self.test_real_time_polling()
        
        # CSV upload tests
        self.test_csv_preview_valid()
        self.test_csv_preview_invalid()
        self.test_csv_preview_missing_columns()
        self.test_csv_upload_valid()
        self.test_csv_duplicate_detection()
        
        # Playlist import tests (NEW)
        self.test_playlist_import_authentication()
        self.test_playlist_import_invalid_urls()
        self.test_spotify_playlist_import()
        self.test_apple_music_playlist_import()
        self.test_playlist_import_song_data_quality()
        self.test_playlist_import_duplicate_detection()
        
        # Cleanup
        self.test_delete_song()
        
        # Print summary
        print("\n" + "=" * 50)
        print("🏁 Test Summary")
        print("=" * 50)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n🔍 Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        return self.results['failed'] == 0

if __name__ == "__main__":
    tester = RequestWaveAPITester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed!")
        exit(0)
    else:
        print(f"\n💥 {tester.results['failed']} tests failed!")
        exit(1)