#!/usr/bin/env python3
"""
Comprehensive test to understand the playlist creation flow and Pro access
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "https://music-flow-update.preview.emergentagent.com/api"

# Pro account for testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

def comprehensive_playlist_test():
    """Run comprehensive test to understand the issue"""
    
    print("🔍 COMPREHENSIVE PLAYLIST CREATION ANALYSIS")
    print("=" * 80)
    
    # Step 1: Login
    print("📊 STEP 1: Login and get user data")
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
    musician_data = login_data_response["musician"]
    
    print(f"✅ Logged in as: {musician_data['name']}")
    print(f"📊 Signup date: {musician_data['created_at']}")
    print(f"📊 Subscription status: {musician_data.get('subscription_status')}")
    print(f"📊 Audience link active: {musician_data.get('audience_link_active')}")
    print(f"📊 Trial end: {musician_data.get('trial_end')}")
    print(f"📊 Subscription ends at: {musician_data.get('subscription_current_period_end')}")
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Step 2: Check subscription status endpoint
    print("\n📊 STEP 2: Check subscription status endpoint")
    status_response = requests.get(f"{BASE_URL}/subscription/status", headers=headers)
    
    if status_response.status_code == 200:
        status_data = status_response.json()
        print(f"✅ Subscription status: {json.dumps(status_data, indent=2, default=str)}")
    else:
        print(f"❌ Failed to get subscription status: {status_response.status_code}")
    
    # Step 3: Get existing playlists
    print("\n📊 STEP 3: Get existing playlists")
    playlists_response = requests.get(f"{BASE_URL}/playlists", headers=headers)
    
    if playlists_response.status_code == 200:
        playlists = playlists_response.json()
        print(f"✅ Found {len(playlists)} existing playlists:")
        for i, playlist in enumerate(playlists):
            print(f"   {i+1}. '{playlist.get('name')}' (ID: {playlist.get('id')}, Songs: {playlist.get('song_count', 0)})")
    else:
        print(f"❌ Failed to get playlists: {playlists_response.status_code}")
        print(f"📊 Response: {playlists_response.text}")
    
    # Step 4: Get songs for playlist creation
    print("\n📊 STEP 4: Get songs for playlist creation")
    songs_response = requests.get(f"{BASE_URL}/songs", headers=headers)
    
    if songs_response.status_code != 200:
        print(f"❌ Failed to get songs: {songs_response.status_code}")
        return
    
    songs = songs_response.json()
    print(f"✅ Found {len(songs)} songs")
    
    if len(songs) < 5:
        print(f"❌ Not enough songs for testing: {len(songs)}")
        return
    
    # Step 5: Create a test playlist
    print("\n📊 STEP 5: Create test playlist with 5 songs")
    selected_songs = songs[:5]
    song_ids = [song["id"] for song in selected_songs]
    
    print(f"📊 Selected songs:")
    for i, song in enumerate(selected_songs):
        print(f"   {i+1}. '{song.get('title')}' by {song.get('artist')}")
    
    playlist_name = f"Debug Test Playlist - {int(datetime.now().timestamp())}"
    playlist_data = {
        "name": playlist_name,
        "song_ids": song_ids
    }
    
    print(f"📊 Creating playlist: {playlist_name}")
    
    create_response = requests.post(f"{BASE_URL}/playlists", json=playlist_data, headers=headers)
    
    print(f"📊 Create playlist response: {create_response.status_code}")
    print(f"📊 Response body: {create_response.text}")
    
    if create_response.status_code == 200:
        created_playlist = create_response.json()
        print(f"✅ Playlist created successfully!")
        print(f"📊 Created playlist: {json.dumps(created_playlist, indent=2, default=str)}")
        
        # Step 6: Verify playlist appears in list
        print("\n📊 STEP 6: Verify playlist appears in list")
        verify_response = requests.get(f"{BASE_URL}/playlists", headers=headers)
        
        if verify_response.status_code == 200:
            updated_playlists = verify_response.json()
            
            found_playlist = None
            for playlist in updated_playlists:
                if playlist.get("id") == created_playlist.get("id"):
                    found_playlist = playlist
                    break
            
            if found_playlist:
                print(f"✅ Created playlist found in list!")
                print(f"📊 Found playlist: {json.dumps(found_playlist, indent=2, default=str)}")
                
                # Check if it has the correct number of songs
                expected_song_count = len(song_ids)
                actual_song_count = found_playlist.get("song_count", 0)
                
                if actual_song_count == expected_song_count:
                    print(f"✅ Song count correct: {actual_song_count}")
                else:
                    print(f"❌ Song count mismatch: expected {expected_song_count}, got {actual_song_count}")
                
                # Check if song_ids are included (for client-side filtering)
                playlist_song_ids = found_playlist.get("song_ids", [])
                if len(playlist_song_ids) == expected_song_count:
                    print(f"✅ Song IDs included: {len(playlist_song_ids)}")
                else:
                    print(f"❌ Song IDs missing or incorrect: expected {expected_song_count}, got {len(playlist_song_ids)}")
                
            else:
                print(f"❌ Created playlist NOT found in list!")
                print(f"📊 Available playlists:")
                for playlist in updated_playlists:
                    print(f"   - '{playlist.get('name')}' (ID: {playlist.get('id')})")
        else:
            print(f"❌ Failed to verify playlist: {verify_response.status_code}")
        
        # Step 7: Test public playlist access
        print("\n📊 STEP 7: Test public playlist access")
        musician_slug = musician_data.get("slug")
        
        # Clear auth for public access
        public_playlists_response = requests.get(f"{BASE_URL}/musicians/{musician_slug}/playlists")
        
        print(f"📊 Public playlists response: {public_playlists_response.status_code}")
        
        if public_playlists_response.status_code == 200:
            public_playlists = public_playlists_response.json()
            
            public_found = any(p.get("id") == created_playlist.get("id") for p in public_playlists)
            
            if public_found:
                print(f"✅ Playlist appears in public endpoint")
            else:
                print(f"❌ Playlist missing from public endpoint")
                print(f"📊 Public playlists: {len(public_playlists)}")
        else:
            print(f"❌ Public playlists endpoint failed: {public_playlists_response.status_code}")
        
        # Step 8: Cleanup
        print("\n📊 STEP 8: Cleanup test playlist")
        delete_response = requests.delete(f"{BASE_URL}/playlists/{created_playlist['id']}", headers=headers)
        
        if delete_response.status_code == 200:
            print(f"✅ Test playlist deleted")
        else:
            print(f"⚠️  Failed to delete test playlist: {delete_response.status_code}")
        
    elif create_response.status_code == 403:
        print(f"❌ Playlist creation DENIED - Pro access required")
        try:
            error_data = create_response.json()
            print(f"📊 Error details: {error_data}")
        except:
            pass
    else:
        print(f"❌ Unexpected playlist creation response: {create_response.status_code}")
    
    print("\n" + "=" * 80)
    print("🎯 ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    comprehensive_playlist_test()