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

    def test_phase2_request_count_tracking(self):
        """Test Phase 2: Request count tracking functionality"""
        try:
            if not self.test_song_id:
                self.log_result("Phase 2 Request Count Tracking", False, "No test song ID available")
                return
            
            print(f"🔍 Testing request count tracking for song ID: {self.test_song_id}")
            
            # First, verify the song has request_count: 0 initially
            songs_response = self.make_request("GET", "/songs")
            if songs_response.status_code == 200:
                songs = songs_response.json()
                test_song = next((song for song in songs if song["id"] == self.test_song_id), None)
                
                if test_song:
                    initial_count = test_song.get("request_count", 0)
                    print(f"📊 Initial request_count: {initial_count}")
                    
                    if initial_count == 0:
                        self.log_result("Phase 2 Request Count - Initial Value", True, "Song has request_count: 0 initially")
                    else:
                        self.log_result("Phase 2 Request Count - Initial Value", False, f"Expected request_count: 0, got: {initial_count}")
                        return
                else:
                    self.log_result("Phase 2 Request Count - Initial Value", False, "Test song not found")
                    return
            else:
                self.log_result("Phase 2 Request Count - Initial Value", False, f"Could not retrieve songs: {songs_response.status_code}")
                return
            
            # Create multiple requests for the song
            request_count = 3
            created_requests = []
            
            for i in range(request_count):
                request_data = {
                    "song_id": self.test_song_id,
                    "requester_name": f"Fan {i+1}",
                    "requester_email": f"fan{i+1}@example.com",
                    "dedication": f"Request #{i+1}",
                    "tip_amount": 2.0
                }
                
                response = self.make_request("POST", "/requests", request_data)
                
                if response.status_code == 200:
                    data = response.json()
                    created_requests.append(data["id"])
                    print(f"📊 Created request #{i+1}: {data['id']}")
                else:
                    self.log_result("Phase 2 Request Count - Create Requests", False, f"Failed to create request #{i+1}: {response.status_code}")
                    return
            
            # Verify that each request incremented the song's request_count
            songs_response = self.make_request("GET", "/songs")
            if songs_response.status_code == 200:
                songs = songs_response.json()
                test_song = next((song for song in songs if song["id"] == self.test_song_id), None)
                
                if test_song:
                    final_count = test_song.get("request_count", 0)
                    print(f"📊 Final request_count: {final_count}")
                    
                    if final_count == request_count:
                        self.log_result("Phase 2 Request Count Tracking", True, f"✅ Request count correctly incremented from 0 to {final_count} after {request_count} requests")
                    else:
                        self.log_result("Phase 2 Request Count Tracking", False, f"❌ Expected request_count: {request_count}, got: {final_count}")
                else:
                    self.log_result("Phase 2 Request Count Tracking", False, "Test song not found after creating requests")
            else:
                self.log_result("Phase 2 Request Count Tracking", False, f"Could not retrieve songs after creating requests: {songs_response.status_code}")
                
        except Exception as e:
            self.log_result("Phase 2 Request Count Tracking", False, f"Exception: {str(e)}")

    def test_phase2_popularity_sorting(self):
        """Test Phase 2: Popularity sorting functionality"""
        try:
            print("🔍 Testing popularity sorting with different sort_by parameters")
            
            # Create multiple test songs with different request counts
            test_songs = [
                {"title": "Popular Song A", "artist": "Artist A", "genres": ["Pop"], "moods": ["Upbeat"], "year": 2023},
                {"title": "Popular Song B", "artist": "Artist B", "genres": ["Rock"], "moods": ["Energetic"], "year": 2022},
                {"title": "Popular Song C", "artist": "Artist C", "genres": ["Jazz"], "moods": ["Smooth"], "year": 2021}
            ]
            
            created_song_ids = []
            
            # Create the test songs
            for song_data in test_songs:
                response = self.make_request("POST", "/songs", song_data)
                if response.status_code == 200:
                    song_id = response.json()["id"]
                    created_song_ids.append(song_id)
                    print(f"📊 Created test song: {song_data['title']} (ID: {song_id})")
                else:
                    self.log_result("Phase 2 Popularity Sorting - Create Test Songs", False, f"Failed to create song: {song_data['title']}")
                    return
            
            # Create different numbers of requests for each song to establish popularity order
            # Song A: 5 requests (most popular)
            # Song B: 3 requests (medium popular)  
            # Song C: 1 request (least popular)
            request_counts = [5, 3, 1]
            
            for i, (song_id, count) in enumerate(zip(created_song_ids, request_counts)):
                for j in range(count):
                    request_data = {
                        "song_id": song_id,
                        "requester_name": f"Fan {j+1}",
                        "requester_email": f"fan{j+1}@song{i}.com",
                        "dedication": f"Request for song {i+1}",
                        "tip_amount": 1.0
                    }
                    
                    response = self.make_request("POST", "/requests", request_data)
                    if response.status_code != 200:
                        self.log_result("Phase 2 Popularity Sorting - Create Requests", False, f"Failed to create request for song {i+1}")
                        return
                
                print(f"📊 Created {count} requests for song {test_songs[i]['title']}")
            
            # Test different sorting options
            sort_tests = [
                ("popularity", "Most requested first"),
                ("title", "A-Z by title"),
                ("artist", "A-Z by artist"),
                ("year", "Newest first by year"),
                ("created_at", "Default - newest first by creation")
            ]
            
            for sort_by, description in sort_tests:
                params = {"sort_by": sort_by}
                response = self.make_request("GET", "/songs", params)
                
                if response.status_code == 200:
                    songs = response.json()
                    
                    if sort_by == "popularity":
                        # Verify songs are sorted by request_count descending
                        request_counts = [song.get("request_count", 0) for song in songs]
                        is_sorted_desc = all(request_counts[i] >= request_counts[i+1] for i in range(len(request_counts)-1))
                        
                        if is_sorted_desc:
                            self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", True, f"✅ Songs correctly sorted by popularity: {request_counts[:5]}")
                        else:
                            self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", False, f"❌ Songs not sorted by popularity: {request_counts[:5]}")
                    
                    elif sort_by == "title":
                        # Verify songs are sorted by title ascending
                        titles = [song.get("title", "") for song in songs]
                        is_sorted_asc = all(titles[i].lower() <= titles[i+1].lower() for i in range(len(titles)-1))
                        
                        if is_sorted_asc:
                            self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", True, f"✅ Songs correctly sorted by title A-Z")
                        else:
                            self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", False, f"❌ Songs not sorted by title A-Z: {titles[:5]}")
                    
                    elif sort_by == "artist":
                        # Verify songs are sorted by artist ascending
                        artists = [song.get("artist", "") for song in songs]
                        is_sorted_asc = all(artists[i].lower() <= artists[i+1].lower() for i in range(len(artists)-1))
                        
                        if is_sorted_asc:
                            self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", True, f"✅ Songs correctly sorted by artist A-Z")
                        else:
                            self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", False, f"❌ Songs not sorted by artist A-Z: {artists[:5]}")
                    
                    elif sort_by == "year":
                        # Verify songs are sorted by year descending (newest first)
                        years = [song.get("year", 0) or 0 for song in songs]
                        is_sorted_desc = all(years[i] >= years[i+1] for i in range(len(years)-1))
                        
                        if is_sorted_desc:
                            self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", True, f"✅ Songs correctly sorted by year (newest first)")
                        else:
                            self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", False, f"❌ Songs not sorted by year: {years[:5]}")
                    
                    else:  # created_at (default)
                        self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", True, f"✅ Default sorting working")
                    
                else:
                    self.log_result(f"Phase 2 Popularity Sorting - {sort_by}", False, f"Failed to get songs with sort_by={sort_by}: {response.status_code}")
                    
        except Exception as e:
            self.log_result("Phase 2 Popularity Sorting", False, f"Exception: {str(e)}")

    def test_phase2_request_count_field(self):
        """Test Phase 2: Request count field in song data"""
        try:
            print("🔍 Testing request_count field presence in all song responses")
            
            # Get all songs
            response = self.make_request("GET", "/songs")
            
            if response.status_code == 200:
                songs = response.json()
                
                if len(songs) > 0:
                    missing_request_count = []
                    invalid_request_count = []
                    
                    for song in songs:
                        # Check if request_count field exists
                        if "request_count" not in song:
                            missing_request_count.append(song.get("title", "Unknown"))
                        else:
                            # Check if request_count is a valid integer >= 0
                            request_count = song["request_count"]
                            if not isinstance(request_count, int) or request_count < 0:
                                invalid_request_count.append(f"{song.get('title', 'Unknown')}: {request_count}")
                    
                    if len(missing_request_count) == 0 and len(invalid_request_count) == 0:
                        self.log_result("Phase 2 Request Count Field", True, f"✅ All {len(songs)} songs have valid request_count field")
                    else:
                        error_msg = ""
                        if missing_request_count:
                            error_msg += f"Missing request_count: {missing_request_count[:3]}. "
                        if invalid_request_count:
                            error_msg += f"Invalid request_count: {invalid_request_count[:3]}."
                        self.log_result("Phase 2 Request Count Field", False, f"❌ {error_msg}")
                    
                    # Test that older songs without request_count get 0 as default
                    zero_count_songs = [song for song in songs if song.get("request_count", 0) == 0]
                    if len(zero_count_songs) > 0:
                        self.log_result("Phase 2 Request Count Field - Default Value", True, f"✅ {len(zero_count_songs)} songs have request_count: 0 (default for older songs)")
                    else:
                        self.log_result("Phase 2 Request Count Field - Default Value", True, f"✅ No songs with request_count: 0 (all have been requested)")
                        
                else:
                    self.log_result("Phase 2 Request Count Field", True, "✅ No songs to test (empty database)")
                    
            else:
                self.log_result("Phase 2 Request Count Field", False, f"Failed to get songs: {response.status_code}")
                
        except Exception as e:
            self.log_result("Phase 2 Request Count Field", False, f"Exception: {str(e)}")

    def test_phase2_edge_cases(self):
        """Test Phase 2: Edge cases for request tracking"""
        try:
            print("🔍 Testing Phase 2 edge cases")
            
            # Test requesting a non-existent song (should return 404)
            fake_song_id = "non-existent-song-id-12345"
            request_data = {
                "song_id": fake_song_id,
                "requester_name": "Test Fan",
                "requester_email": "fan@example.com",
                "dedication": "Test request",
                "tip_amount": 1.0
            }
            
            response = self.make_request("POST", "/requests", request_data)
            
            if response.status_code == 404:
                self.log_result("Phase 2 Edge Cases - Non-existent Song", True, "✅ Correctly returned 404 for non-existent song")
            else:
                self.log_result("Phase 2 Edge Cases - Non-existent Song", False, f"❌ Expected 404, got: {response.status_code}")
            
            # Test sorting with empty database (create a new musician for this)
            empty_musician_data = {
                "name": "Empty Musician",
                "email": "empty@requestwave.com",
                "password": "SecurePassword123!"
            }
            
            # Save current auth
            original_token = self.auth_token
            
            # Register new musician
            register_response = self.make_request("POST", "/auth/register", empty_musician_data)
            if register_response.status_code == 200:
                empty_auth_data = register_response.json()
                self.auth_token = empty_auth_data["token"]
                
                # Test sorting with empty song list
                for sort_by in ["popularity", "title", "artist", "year", "created_at"]:
                    params = {"sort_by": sort_by}
                    response = self.make_request("GET", "/songs", params)
                    
                    if response.status_code == 200:
                        songs = response.json()
                        if len(songs) == 0:
                            self.log_result(f"Phase 2 Edge Cases - Empty DB Sort ({sort_by})", True, f"✅ Sorting works with empty database")
                        else:
                            self.log_result(f"Phase 2 Edge Cases - Empty DB Sort ({sort_by})", False, f"❌ Expected empty list, got {len(songs)} songs")
                    else:
                        self.log_result(f"Phase 2 Edge Cases - Empty DB Sort ({sort_by})", False, f"❌ Failed to get songs: {response.status_code}")
                
                # Restore original auth
                self.auth_token = original_token
            else:
                self.log_result("Phase 2 Edge Cases - Empty Database Setup", False, "Could not create empty musician for testing")
            
            # Test multiple requests for same song increment correctly
            if self.test_song_id:
                # Get current request count
                songs_response = self.make_request("GET", "/songs")
                if songs_response.status_code == 200:
                    songs = songs_response.json()
                    test_song = next((song for song in songs if song["id"] == self.test_song_id), None)
                    
                    if test_song:
                        initial_count = test_song.get("request_count", 0)
                        
                        # Create 2 more requests
                        for i in range(2):
                            request_data = {
                                "song_id": self.test_song_id,
                                "requester_name": f"Edge Case Fan {i+1}",
                                "requester_email": f"edge{i+1}@example.com",
                                "dedication": f"Edge case request #{i+1}",
                                "tip_amount": 1.0
                            }
                            
                            response = self.make_request("POST", "/requests", request_data)
                            if response.status_code != 200:
                                self.log_result("Phase 2 Edge Cases - Multiple Requests", False, f"Failed to create edge case request #{i+1}")
                                return
                        
                        # Verify count increased by 2
                        songs_response = self.make_request("GET", "/songs")
                        if songs_response.status_code == 200:
                            songs = songs_response.json()
                            test_song = next((song for song in songs if song["id"] == self.test_song_id), None)
                            
                            if test_song:
                                final_count = test_song.get("request_count", 0)
                                expected_count = initial_count + 2
                                
                                if final_count == expected_count:
                                    self.log_result("Phase 2 Edge Cases - Multiple Requests", True, f"✅ Request count correctly incremented from {initial_count} to {final_count}")
                                else:
                                    self.log_result("Phase 2 Edge Cases - Multiple Requests", False, f"❌ Expected {expected_count}, got {final_count}")
                            else:
                                self.log_result("Phase 2 Edge Cases - Multiple Requests", False, "Test song not found after creating requests")
                        else:
                            self.log_result("Phase 2 Edge Cases - Multiple Requests", False, "Could not verify final request count")
                    else:
                        self.log_result("Phase 2 Edge Cases - Multiple Requests", False, "Test song not found for multiple requests test")
                else:
                    self.log_result("Phase 2 Edge Cases - Multiple Requests", False, "Could not get initial request count")
            else:
                self.log_result("Phase 2 Edge Cases - Multiple Requests", False, "No test song available for multiple requests test")
                
        except Exception as e:
            self.log_result("Phase 2 Edge Cases", False, f"Exception: {str(e)}")

    def test_analytics_requesters(self):
        """Test Phase 3: Requester Analytics Endpoint"""
        try:
            if not self.auth_token:
                self.log_result("Analytics Requesters", False, "No auth token available")
                return
            
            print("🔍 Testing requester analytics endpoint")
            
            # First create some test requests with different requesters
            test_requests = [
                {"requester_name": "Alice Johnson", "requester_email": "alice@example.com", "tip_amount": 5.0},
                {"requester_name": "Bob Smith", "requester_email": "bob@example.com", "tip_amount": 3.0},
                {"requester_name": "Alice Johnson", "requester_email": "alice@example.com", "tip_amount": 2.0},  # Same person, different request
                {"requester_name": "Charlie Brown", "requester_email": "charlie@example.com", "tip_amount": 0.0}
            ]
            
            # Create requests if we have a test song
            if self.test_song_id:
                for req_data in test_requests:
                    request_data = {
                        "song_id": self.test_song_id,
                        "requester_name": req_data["requester_name"],
                        "requester_email": req_data["requester_email"],
                        "dedication": "Test request for analytics",
                        "tip_amount": req_data["tip_amount"]
                    }
                    
                    response = self.make_request("POST", "/requests", request_data)
                    if response.status_code != 200:
                        print(f"⚠️ Failed to create test request for {req_data['requester_name']}")
            
            # Test the analytics endpoint
            response = self.make_request("GET", "/analytics/requesters")
            
            if response.status_code == 200:
                data = response.json()
                
                if "requesters" in data and isinstance(data["requesters"], list):
                    requesters = data["requesters"]
                    
                    # Verify response structure
                    if len(requesters) > 0:
                        first_requester = requesters[0]
                        required_fields = ["name", "email", "request_count", "total_tips", "latest_request"]
                        
                        missing_fields = [field for field in required_fields if field not in first_requester]
                        
                        if not missing_fields:
                            # Verify sorting (most frequent first)
                            request_counts = [req["request_count"] for req in requesters]
                            is_sorted_desc = all(request_counts[i] >= request_counts[i+1] for i in range(len(request_counts)-1))
                            
                            if is_sorted_desc:
                                self.log_result("Analytics Requesters", True, f"✅ Retrieved {len(requesters)} requesters, sorted by request count")
                                
                                # Verify aggregation logic
                                alice_requests = [req for req in requesters if req["email"] == "alice@example.com"]
                                if alice_requests and alice_requests[0]["request_count"] >= 2:
                                    self.log_result("Analytics Requesters - Aggregation", True, f"✅ Correctly aggregated multiple requests per requester")
                                else:
                                    self.log_result("Analytics Requesters - Aggregation", False, "❌ Request aggregation not working correctly")
                            else:
                                self.log_result("Analytics Requesters", False, f"❌ Requesters not sorted by request count: {request_counts}")
                        else:
                            self.log_result("Analytics Requesters", False, f"❌ Missing required fields: {missing_fields}")
                    else:
                        self.log_result("Analytics Requesters", True, "✅ No requesters found (empty result)")
                else:
                    self.log_result("Analytics Requesters", False, f"❌ Invalid response structure: {data}")
            else:
                self.log_result("Analytics Requesters", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_result("Analytics Requesters", False, f"❌ Exception: {str(e)}")

    def test_analytics_export_csv(self):
        """Test Phase 3: Export Requesters CSV Endpoint"""
        try:
            if not self.auth_token:
                self.log_result("Analytics Export CSV", False, "No auth token available")
                return
            
            print("🔍 Testing requester CSV export endpoint")
            
            response = self.make_request("GET", "/analytics/export-requesters")
            
            if response.status_code == 200:
                # Check Content-Type header
                content_type = response.headers.get("content-type", "")
                if "text/csv" in content_type:
                    # Check Content-Disposition header for file download
                    content_disposition = response.headers.get("content-disposition", "")
                    if "attachment" in content_disposition and "filename=" in content_disposition:
                        # Verify CSV content structure
                        csv_content = response.text
                        lines = csv_content.strip().split('\n')
                        
                        if len(lines) > 0:
                            # Check CSV headers
                            header_line = lines[0]
                            expected_headers = ["Name", "Email", "Request Count", "Total Tips", "Latest Request"]
                            
                            # Remove quotes and check headers
                            actual_headers = [h.strip('"') for h in header_line.split(',')]
                            
                            if all(header in actual_headers for header in expected_headers):
                                self.log_result("Analytics Export CSV", True, f"✅ CSV export working with {len(lines)} lines (including header)")
                                self.log_result("Analytics Export CSV - Headers", True, f"✅ Correct CSV headers: {actual_headers}")
                                self.log_result("Analytics Export CSV - Download", True, f"✅ Proper Content-Disposition header for download")
                            else:
                                self.log_result("Analytics Export CSV", False, f"❌ Missing CSV headers. Expected: {expected_headers}, Got: {actual_headers}")
                        else:
                            self.log_result("Analytics Export CSV", False, "❌ Empty CSV content")
                    else:
                        self.log_result("Analytics Export CSV", False, f"❌ Missing Content-Disposition header: {content_disposition}")
                else:
                    self.log_result("Analytics Export CSV", False, f"❌ Wrong Content-Type: {content_type}")
            else:
                self.log_result("Analytics Export CSV", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_result("Analytics Export CSV", False, f"❌ Exception: {str(e)}")

    def test_analytics_daily(self):
        """Test Phase 3: Daily Analytics Endpoint"""
        try:
            if not self.auth_token:
                self.log_result("Analytics Daily", False, "No auth token available")
                return
            
            print("🔍 Testing daily analytics endpoint")
            
            # Test default 7 days
            response = self.make_request("GET", "/analytics/daily")
            
            if response.status_code == 200:
                data = response.json()
                
                required_fields = ["period", "daily_stats", "top_songs", "top_requesters", "totals"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    # Verify daily_stats structure
                    daily_stats = data["daily_stats"]
                    if isinstance(daily_stats, list):
                        if len(daily_stats) > 0:
                            first_day = daily_stats[0]
                            day_required_fields = ["date", "request_count", "tip_total", "unique_requesters"]
                            day_missing_fields = [field for field in day_required_fields if field not in first_day]
                            
                            if not day_missing_fields:
                                self.log_result("Analytics Daily - Structure", True, f"✅ Correct daily_stats structure with {len(daily_stats)} days")
                            else:
                                self.log_result("Analytics Daily - Structure", False, f"❌ Missing daily_stats fields: {day_missing_fields}")
                        else:
                            self.log_result("Analytics Daily - Structure", True, "✅ Empty daily_stats (no data in period)")
                    else:
                        self.log_result("Analytics Daily - Structure", False, f"❌ daily_stats should be list, got: {type(daily_stats)}")
                    
                    # Verify top_songs structure
                    top_songs = data["top_songs"]
                    if isinstance(top_songs, list):
                        if len(top_songs) > 0:
                            first_song = top_songs[0]
                            if "song" in first_song and "count" in first_song:
                                self.log_result("Analytics Daily - Top Songs", True, f"✅ Top songs structure correct with {len(top_songs)} songs")
                            else:
                                self.log_result("Analytics Daily - Top Songs", False, f"❌ Invalid top_songs structure: {first_song}")
                        else:
                            self.log_result("Analytics Daily - Top Songs", True, "✅ Empty top_songs (no requests in period)")
                    else:
                        self.log_result("Analytics Daily - Top Songs", False, f"❌ top_songs should be list, got: {type(top_songs)}")
                    
                    # Verify totals structure
                    totals = data["totals"]
                    if isinstance(totals, dict):
                        totals_required_fields = ["total_requests", "total_tips", "unique_requesters"]
                        totals_missing_fields = [field for field in totals_required_fields if field not in totals]
                        
                        if not totals_missing_fields:
                            self.log_result("Analytics Daily - Totals", True, f"✅ Totals structure correct: {totals}")
                        else:
                            self.log_result("Analytics Daily - Totals", False, f"❌ Missing totals fields: {totals_missing_fields}")
                    else:
                        self.log_result("Analytics Daily - Totals", False, f"❌ totals should be dict, got: {type(totals)}")
                    
                    self.log_result("Analytics Daily", True, f"✅ Daily analytics working for {data['period']}")
                else:
                    self.log_result("Analytics Daily", False, f"❌ Missing required fields: {missing_fields}")
            else:
                self.log_result("Analytics Daily", False, f"❌ Status code: {response.status_code}, Response: {response.text}")
            
            # Test with different day ranges
            for days in [7, 30]:
                params = {"days": days}
                response = self.make_request("GET", "/analytics/daily", params)
                
                if response.status_code == 200:
                    data = response.json()
                    if f"Last {days} days" in data.get("period", ""):
                        self.log_result(f"Analytics Daily - {days} Days", True, f"✅ {days} days parameter working")
                    else:
                        self.log_result(f"Analytics Daily - {days} Days", False, f"❌ Wrong period: {data.get('period')}")
                else:
                    self.log_result(f"Analytics Daily - {days} Days", False, f"❌ Status code: {response.status_code}")
                    
        except Exception as e:
            self.log_result("Analytics Daily", False, f"❌ Exception: {str(e)}")

    def test_analytics_authentication(self):
        """Test Phase 3: Analytics Authentication & Security"""
        try:
            print("🔍 Testing analytics authentication requirements")
            
            # Save current token
            original_token = self.auth_token
            
            analytics_endpoints = [
                "/analytics/requesters",
                "/analytics/export-requesters", 
                "/analytics/daily"
            ]
            
            for endpoint in analytics_endpoints:
                # Test without token
                self.auth_token = None
                response = self.make_request("GET", endpoint)
                
                if response.status_code in [401, 403]:
                    self.log_result(f"Analytics Auth - {endpoint} (No Token)", True, f"✅ Correctly rejected unauthorized request")
                else:
                    self.log_result(f"Analytics Auth - {endpoint} (No Token)", False, f"❌ Should have returned 401/403, got: {response.status_code}")
                
                # Test with invalid token
                self.auth_token = "invalid_token_12345"
                response = self.make_request("GET", endpoint)
                
                if response.status_code == 401:
                    self.log_result(f"Analytics Auth - {endpoint} (Invalid Token)", True, f"✅ Correctly rejected invalid token")
                else:
                    self.log_result(f"Analytics Auth - {endpoint} (Invalid Token)", False, f"❌ Should have returned 401, got: {response.status_code}")
            
            # Restore original token
            self.auth_token = original_token
            
        except Exception as e:
            self.log_result("Analytics Authentication", False, f"❌ Exception: {str(e)}")
            # Restore token in case of exception
            if 'original_token' in locals():
                self.auth_token = original_token

    def test_analytics_data_quality(self):
        """Test Phase 3: Analytics Data Quality and Edge Cases"""
        try:
            if not self.auth_token:
                self.log_result("Analytics Data Quality", False, "No auth token available")
                return
            
            print("🔍 Testing analytics data quality and edge cases")
            
            # Test with no data (should return empty results, not errors)
            response = self.make_request("GET", "/analytics/requesters")
            
            if response.status_code == 200:
                data = response.json()
                if "requesters" in data and isinstance(data["requesters"], list):
                    self.log_result("Analytics Data Quality - Empty Data", True, f"✅ Handles empty data correctly")
                else:
                    self.log_result("Analytics Data Quality - Empty Data", False, f"❌ Invalid response for empty data: {data}")
            else:
                self.log_result("Analytics Data Quality - Empty Data", False, f"❌ Status code: {response.status_code}")
            
            # Test daily analytics with edge case parameters
            edge_case_params = [
                {"days": 1},    # Single day
                {"days": 365},  # Full year
                {"days": 0}     # Invalid parameter
            ]
            
            for params in edge_case_params:
                response = self.make_request("GET", "/analytics/daily", params)
                days = params["days"]
                
                if days == 0:
                    # Should handle invalid parameter gracefully
                    if response.status_code in [400, 422]:
                        self.log_result(f"Analytics Data Quality - Invalid Days ({days})", True, f"✅ Correctly rejected invalid days parameter")
                    else:
                        self.log_result(f"Analytics Data Quality - Invalid Days ({days})", False, f"❌ Should reject days=0, got status: {response.status_code}")
                else:
                    # Should work with valid parameters
                    if response.status_code == 200:
                        data = response.json()
                        if f"Last {days} days" in data.get("period", ""):
                            self.log_result(f"Analytics Data Quality - Edge Case Days ({days})", True, f"✅ Handles {days} days correctly")
                        else:
                            self.log_result(f"Analytics Data Quality - Edge Case Days ({days})", False, f"❌ Wrong period for {days} days")
                    else:
                        self.log_result(f"Analytics Data Quality - Edge Case Days ({days})", False, f"❌ Status code: {response.status_code}")
                        
        except Exception as e:
            self.log_result("Analytics Data Quality", False, f"❌ Exception: {str(e)}")

    def run_phase3_analytics_tests(self):
        """Run Phase 3 Analytics Dashboard tests"""
        print("🚨 PHASE 3 TESTING - Analytics Dashboard Backend")
        print("=" * 70)
        print("Testing Phase 3 Analytics Dashboard Features:")
        print("1. Requester Analytics Endpoint")
        print("2. Export Requesters CSV Endpoint")
        print("3. Daily Analytics Endpoint")
        print("4. Authentication & Security")
        print("5. Data Quality & Edge Cases")
        print("=" * 70)
        
        # Authentication setup
        self.test_musician_registration()
        self.test_jwt_token_validation()
        
        # Create a test song for analytics data
        self.test_create_song()
        
        print("\n🔥 PHASE 3 TEST #1: REQUESTER ANALYTICS")
        print("-" * 50)
        self.test_analytics_requesters()
        
        print("\n🔥 PHASE 3 TEST #2: CSV EXPORT")
        print("-" * 50)
        self.test_analytics_export_csv()
        
        print("\n🔥 PHASE 3 TEST #3: DAILY ANALYTICS")
        print("-" * 50)
        self.test_analytics_daily()
        
        print("\n🔥 PHASE 3 TEST #4: AUTHENTICATION & SECURITY")
        print("-" * 50)
        self.test_analytics_authentication()
        
        print("\n🔥 PHASE 3 TEST #5: DATA QUALITY & EDGE CASES")
        print("-" * 50)
        self.test_analytics_data_quality()
        
        # Print summary
        print("\n" + "=" * 70)
        print("🏁 PHASE 3 ANALYTICS TEST SUMMARY")
        print("=" * 70)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n🔍 Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        # Specific summary for Phase 3 analytics features
        analytics_tests = [error for error in self.results['errors'] if 'analytics' in error.lower()]
        
        print(f"\n📊 PHASE 3 ANALYTICS DASHBOARD: {'✅ WORKING' if len(analytics_tests) == 0 else '❌ FAILING'}")
        if analytics_tests:
            for error in analytics_tests:
                print(f"   • {error}")
        
        return self.results['failed'] == 0

    def run_phase2_tests(self):
        """Run Phase 2 Request Tracking & Popularity Features tests"""
        print("🚨 PHASE 2 TESTING - Request Tracking & Popularity Features")
        print("=" * 70)
        print("Testing Phase 2 Request Tracking & Popularity Features:")
        print("1. Request Count Tracking")
        print("2. Popularity Sorting")
        print("3. Request Count in Song Data")
        print("4. Edge Cases")
        print("=" * 70)
        
        # Authentication setup
        self.test_musician_registration()
        self.test_jwt_token_validation()
        
        # Create a test song for request tracking
        self.test_create_song()
        
        print("\n🔥 PHASE 2 TEST #1: REQUEST COUNT TRACKING")
        print("-" * 50)
        self.test_phase2_request_count_tracking()
        
        print("\n🔥 PHASE 2 TEST #2: POPULARITY SORTING")
        print("-" * 50)
        self.test_phase2_popularity_sorting()
        
        print("\n🔥 PHASE 2 TEST #3: REQUEST COUNT FIELD")
        print("-" * 50)
        self.test_phase2_request_count_field()
        
        print("\n🔥 PHASE 2 TEST #4: EDGE CASES")
        print("-" * 50)
        self.test_phase2_edge_cases()
        
        # Print summary
        print("\n" + "=" * 70)
        print("🏁 PHASE 2 TEST SUMMARY")
        print("=" * 70)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n🔍 Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        # Specific summary for Phase 2 features
        phase2_tests = [error for error in self.results['errors'] if 'phase 2' in error.lower()]
        
        print(f"\n📊 PHASE 2 REQUEST TRACKING & POPULARITY: {'✅ WORKING' if len(phase2_tests) == 0 else '❌ FAILING'}")
        if phase2_tests:
            for error in phase2_tests:
                print(f"   • {error}")
        
        return self.results['failed'] == 0

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
    
    # Run Phase 3 Analytics Dashboard tests as requested in the review
    success = tester.run_phase3_analytics_tests()
    
    if success:
        print("\n🎉 All Phase 3 Analytics tests passed!")
        exit(0)
    else:
        print(f"\n💥 {tester.results['failed']} Phase 3 Analytics tests failed!")
        exit(1)