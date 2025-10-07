#!/usr/bin/env python3
"""
Check existing songs to understand duplicate detection
"""

import requests
import json

# Configuration
BASE_URL = "https://request-error-fix.preview.emergentagent.com/api"

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
    # Login
    login_data = {
        "email": PRO_MUSICIAN["email"],
        "password": PRO_MUSICIAN["password"]
    }
    
    login_response = make_request("POST", "/auth/login", login_data)
    
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.status_code}")
        return
    
    login_data_response = login_response.json()
    auth_token = login_data_response["token"]
    
    print(f"✅ Logged in as: {login_data_response['musician']['name']}")
    
    # Get existing songs
    songs_response = make_request("GET", "/songs", auth_token=auth_token)
    
    if songs_response.status_code != 200:
        print(f"Failed to get songs: {songs_response.status_code}")
        return
    
    songs = songs_response.json()
    print(f"📊 Total songs: {len(songs)}")
    
    # Check for songs with playlist-related notes
    playlist_songs = []
    blank_notes_songs = []
    
    for song in songs:
        notes = song.get("notes", "")
        if "playlist" in notes.lower() or "imported from" in notes.lower():
            playlist_songs.append({
                "title": song.get("title"),
                "artist": song.get("artist"),
                "notes": notes
            })
        elif notes == "":
            blank_notes_songs.append({
                "title": song.get("title"),
                "artist": song.get("artist")
            })
    
    print(f"\n🎵 Songs with playlist-related notes: {len(playlist_songs)}")
    for i, song in enumerate(playlist_songs[:10]):  # Show first 10
        print(f"   {i+1}. '{song['title']}' by '{song['artist']}' - Notes: {repr(song['notes'])}")
    
    print(f"\n✅ Songs with blank notes: {len(blank_notes_songs)}")
    for i, song in enumerate(blank_notes_songs[:10]):  # Show first 10
        print(f"   {i+1}. '{song['title']}' by '{song['artist']}'")
    
    # Check specific songs that were being skipped
    test_songs = [
        ("As It Was", "Harry Styles"),
        ("Heat Waves", "Glass Animals"),
        ("Blinding Lights", "The Weeknd"),
        ("Good 4 U", "Olivia Rodrigo"),
        ("Levitating", "Dua Lipa")
    ]
    
    print(f"\n🔍 Checking specific test songs:")
    for title, artist in test_songs:
        found_song = None
        for song in songs:
            if song.get("title", "").lower() == title.lower() and song.get("artist", "").lower() == artist.lower():
                found_song = song
                break
        
        if found_song:
            notes = found_song.get("notes", "")
            print(f"   • '{title}' by '{artist}' - Notes: {repr(notes)}")
        else:
            print(f"   • '{title}' by '{artist}' - NOT FOUND")

if __name__ == "__main__":
    main()