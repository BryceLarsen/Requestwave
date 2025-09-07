#!/usr/bin/env python3
"""
FINAL PLAYLIST CREATION TEST
Test playlist creation with existing songs to confirm the fix is complete
"""

import requests
import json

# Configuration
BASE_URL = "https://music-flow-update.preview.emergentagent.com/api"

# Pro account credentials
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

def test_playlist_creation_with_existing_songs():
    print("🔍 FINAL PLAYLIST CREATION TEST")
    print("=" * 50)
    
    # Step 1: Login
    print("1. Logging in...")
    login_response = make_request("POST", "/auth/login", PRO_MUSICIAN)
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return
    
    auth_token = login_response.json()["token"]
    print("✅ Login successful")
    
    # Step 2: Get existing songs
    print("2. Getting existing songs...")
    songs_response = make_request("GET", "/songs", auth_token=auth_token)
    
    if songs_response.status_code != 200:
        print(f"❌ Failed to get songs: {songs_response.status_code}")
        return
    
    songs = songs_response.json()
    print(f"✅ Found {len(songs)} existing songs")
    
    if len(songs) == 0:
        print("⚠️ No songs available for playlist test")
        return
    
    # Step 3: Create playlist with first 3 songs
    song_ids = [song["id"] for song in songs[:3]]
    print(f"3. Creating playlist with {len(song_ids)} songs...")
    
    playlist_data = {
        "name": "Final Test Playlist",
        "song_ids": song_ids
    }
    
    playlist_response = make_request("POST", "/playlists", playlist_data, auth_token=auth_token)
    
    print(f"Status Code: {playlist_response.status_code}")
    
    if playlist_response.status_code == 200:
        data = playlist_response.json()
        print("✅ PLAYLIST CREATION SUCCESSFUL!")
        print(f"   Playlist ID: {data['id']}")
        print(f"   Playlist Name: {data['name']}")
        print(f"   Song Count: {data['song_count']}")
        print(f"   Is Active: {data['is_active']}")
        
        # Step 4: Verify playlist was created by listing all playlists
        print("4. Verifying playlist in list...")
        playlists_response = make_request("GET", "/playlists", auth_token=auth_token)
        
        if playlists_response.status_code == 200:
            playlists = playlists_response.json()
            created_playlist = next((p for p in playlists if p["id"] == data["id"]), None)
            
            if created_playlist:
                print("✅ Playlist verified in list")
                print(f"   Found playlist: {created_playlist['name']} with {created_playlist['song_count']} songs")
            else:
                print("❌ Playlist not found in list")
        else:
            print(f"❌ Failed to get playlists: {playlists_response.status_code}")
        
        print("\n🎉 PLAYLIST CREATION BUG FIXED!")
        print("   The user can now successfully create playlists")
        
    else:
        print("❌ PLAYLIST CREATION FAILED")
        print(f"   Status: {playlist_response.status_code}")
        print(f"   Response: {playlist_response.text}")

if __name__ == "__main__":
    test_playlist_creation_with_existing_songs()