#!/usr/bin/env python3
"""
Check specific song details to understand the notes issue
"""

import requests
import json

# Configuration
BASE_URL = "https://stagepro-app.preview.emergentagent.com/api"

# Pro account for testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

def make_request(method: str, endpoint: str, data=None, auth_token=None):
    """Make HTTP request with proper headers"""
    url = f"{BASE_URL}{endpoint}"
    
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    if method.upper() == "GET":
        response = requests.get(url, headers=headers, params=data)
    elif method.upper() == "POST":
        response = requests.post(url, headers=headers, json=data)
    else:
        raise ValueError(f"Unsupported method: {method}")
    
    return response

def main():
    print("🔍 CHECKING SONG DETAILS FOR NOTES ISSUE")
    print("=" * 60)
    
    # Login
    login_data = {
        "email": PRO_MUSICIAN["email"],
        "password": PRO_MUSICIAN["password"]
    }
    
    login_response = make_request("POST", "/auth/login", login_data)
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return
    
    login_data_response = login_response.json()
    auth_token = login_data_response["token"]
    
    print(f"✅ Logged in as: {login_data_response['musician']['name']}")
    
    # Get all songs
    songs_response = make_request("GET", "/songs", auth_token=auth_token)
    
    if songs_response.status_code != 200:
        print(f"❌ Failed to get songs: {songs_response.status_code}")
        return
    
    songs = songs_response.json()
    print(f"📊 Total songs: {len(songs)}")
    
    # Find all instances of "As It Was" by Harry Styles
    as_it_was_songs = []
    for song in songs:
        if song.get("title", "").lower() == "as it was" and "harry styles" in song.get("artist", "").lower():
            as_it_was_songs.append(song)
    
    print(f"\n🎵 Found {len(as_it_was_songs)} instances of 'As It Was' by Harry Styles:")
    
    for i, song in enumerate(as_it_was_songs):
        print(f"\n   Instance {i+1}:")
        print(f"     ID: {song.get('id')}")
        print(f"     Title: {repr(song.get('title'))}")
        print(f"     Artist: {repr(song.get('artist'))}")
        print(f"     Notes: {repr(song.get('notes'))}")
        print(f"     Created: {song.get('created_at')}")
        print(f"     Genres: {song.get('genres')}")
        print(f"     Moods: {song.get('moods')}")
        print(f"     Year: {song.get('year')}")
    
    # Also check for "Blinding Lights" to compare
    blinding_lights_songs = []
    for song in songs:
        if song.get("title", "").lower() == "blinding lights" and "weeknd" in song.get("artist", "").lower():
            blinding_lights_songs.append(song)
    
    print(f"\n🎵 Found {len(blinding_lights_songs)} instances of 'Blinding Lights' by The Weeknd:")
    
    for i, song in enumerate(blinding_lights_songs):
        print(f"\n   Instance {i+1}:")
        print(f"     ID: {song.get('id')}")
        print(f"     Title: {repr(song.get('title'))}")
        print(f"     Artist: {repr(song.get('artist'))}")
        print(f"     Notes: {repr(song.get('notes'))}")
        print(f"     Created: {song.get('created_at')}")
        print(f"     Genres: {song.get('genres')}")
        print(f"     Moods: {song.get('moods')}")
        print(f"     Year: {song.get('year')}")

if __name__ == "__main__":
    main()