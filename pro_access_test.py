#!/usr/bin/env python3
"""
Test the check_pro_access function directly to debug the playlist creation issue
"""

import requests
import json

# Configuration
BASE_URL = "https://requestwave-app.preview.emergentagent.com/api"

# Pro account for testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

def test_pro_access_directly():
    """Test Pro access by trying to create a playlist directly"""
    
    # Login first
    login_data = {
        "email": PRO_MUSICIAN["email"],
        "password": PRO_MUSICIAN["password"]
    }
    
    login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return
    
    login_data_response = login_response.json()
    auth_token = login_data_response["token"]
    musician_id = login_data_response["musician"]["id"]
    
    print(f"✅ Logged in as: {login_data_response['musician']['name']}")
    print(f"📊 Musician ID: {musician_id}")
    
    # Get subscription status using both endpoints
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Test freemium subscription status
    freemium_status_response = requests.get(f"{BASE_URL}/subscription/status", headers=headers)
    print(f"\n📊 Freemium subscription status: {freemium_status_response.status_code}")
    if freemium_status_response.status_code == 200:
        freemium_status = freemium_status_response.json()
        print(f"📊 Freemium status: {json.dumps(freemium_status, indent=2)}")
    
    # Get some songs for playlist creation
    songs_response = requests.get(f"{BASE_URL}/songs", headers=headers)
    if songs_response.status_code != 200:
        print(f"❌ Failed to get songs: {songs_response.status_code}")
        return
    
    songs = songs_response.json()
    if len(songs) < 2:
        print(f"❌ Not enough songs: {len(songs)}")
        return
    
    print(f"✅ Found {len(songs)} songs")
    
    # Try to create a playlist
    playlist_data = {
        "name": f"Pro Access Test Playlist",
        "song_ids": [songs[0]["id"], songs[1]["id"]]
    }
    
    print(f"\n📊 Attempting to create playlist...")
    playlist_response = requests.post(f"{BASE_URL}/playlists", json=playlist_data, headers=headers)
    
    print(f"📊 Playlist creation response: {playlist_response.status_code}")
    print(f"📊 Response body: {playlist_response.text}")
    
    if playlist_response.status_code == 200:
        print("✅ Playlist creation SUCCEEDED - User has Pro access")
        created_playlist = playlist_response.json()
        
        # Clean up
        delete_response = requests.delete(f"{BASE_URL}/playlists/{created_playlist['id']}", headers=headers)
        print(f"📊 Cleanup: {delete_response.status_code}")
        
    elif playlist_response.status_code == 403:
        print("❌ Playlist creation FAILED - User does NOT have Pro access")
        try:
            error_data = playlist_response.json()
            print(f"📊 Error details: {error_data}")
        except:
            pass
    else:
        print(f"❌ Unexpected response: {playlist_response.status_code}")

if __name__ == "__main__":
    test_pro_access_directly()