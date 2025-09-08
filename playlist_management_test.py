#!/usr/bin/env python3
"""
FOCUSED PLAYLIST MANAGEMENT TESTING

Quick focused test of the core playlist management features:
1. Playlist creation with is_public=false default
2. Rename functionality  
3. Visibility toggle
4. Soft delete
5. Audience filtering

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://requestwave-revamp.preview.emergentagent.com/api"
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

def make_request(method, endpoint, data=None, auth_token=None):
    """Make HTTP request with proper headers"""
    url = f"{BASE_URL}{endpoint}"
    
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=data)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return response
    except Exception as e:
        print(f"Request failed: {e}")
        raise

def main():
    print("🎵 FOCUSED PLAYLIST MANAGEMENT TESTING")
    print("=" * 60)
    
    # Step 1: Login
    print("📊 Step 1: Login with Pro account")
    login_response = make_request("POST", "/auth/login", PRO_MUSICIAN)
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return
    
    login_data = login_response.json()
    auth_token = login_data["token"]
    musician_slug = login_data["musician"]["slug"]
    
    print(f"✅ Logged in as: {login_data['musician']['name']}")
    
    # Step 2: Get songs for testing
    print("📊 Step 2: Get songs for testing")
    songs_response = make_request("GET", "/songs", auth_token=auth_token)
    
    if songs_response.status_code != 200:
        print(f"❌ Failed to get songs: {songs_response.status_code}")
        return
    
    songs = songs_response.json()
    if len(songs) < 2:
        print(f"❌ Need at least 2 songs, found {len(songs)}")
        return
    
    test_song_ids = [songs[0]["id"], songs[1]["id"]]
    print(f"✅ Using {len(test_song_ids)} songs for testing")
    
    # Step 3: Test playlist creation with defaults
    print("📊 Step 3: Test playlist creation with defaults")
    
    playlist_data = {
        "name": "Test Playlist Defaults",
        "song_ids": test_song_ids
    }
    
    create_response = make_request("POST", "/playlists", playlist_data, auth_token)
    
    if create_response.status_code != 200:
        print(f"❌ Playlist creation failed: {create_response.status_code}")
        return
    
    created_playlist = create_response.json()
    playlist_id = created_playlist["id"]
    
    print(f"✅ Created playlist: {created_playlist['name']}")
    print(f"📊 is_public: {created_playlist.get('is_public', 'missing')}")
    
    # Verify is_public defaults to false
    if created_playlist.get("is_public") == False:
        print("✅ is_public correctly defaults to false")
    else:
        print("❌ is_public not defaulting to false")
    
    # Step 4: Test rename functionality
    print("📊 Step 4: Test rename functionality")
    
    time.sleep(1)  # Ensure updated_at changes
    
    rename_data = {"name": "Renamed Test Playlist"}
    rename_response = make_request("PUT", f"/playlists/{playlist_id}/name", rename_data, auth_token)
    
    if rename_response.status_code == 200:
        rename_result = rename_response.json()
        print(f"✅ Rename successful: {rename_result.get('name')}")
        print(f"📊 updated_at changed: {rename_result.get('updated_at')}")
    else:
        print(f"❌ Rename failed: {rename_response.status_code}")
    
    # Step 5: Test visibility toggle
    print("📊 Step 5: Test visibility toggle")
    
    time.sleep(1)  # Ensure updated_at changes
    
    # Make public
    public_data = {"is_public": True}
    public_response = make_request("PUT", f"/playlists/{playlist_id}/visibility", public_data, auth_token)
    
    if public_response.status_code == 200:
        public_result = public_response.json()
        print(f"✅ Made public: is_public={public_result.get('is_public')}")
        
        # Verify appears in audience list
        audience_response = make_request("GET", f"/musicians/{musician_slug}/playlists")
        if audience_response.status_code == 200:
            audience_playlists = audience_response.json()
            playlist_in_audience = any(p["id"] == playlist_id for p in audience_playlists)
            if playlist_in_audience:
                print("✅ Playlist appears in audience list when public")
            else:
                print("❌ Playlist not in audience list when public")
        
        # Make private again
        time.sleep(1)
        private_data = {"is_public": False}
        private_response = make_request("PUT", f"/playlists/{playlist_id}/visibility", private_data, auth_token)
        
        if private_response.status_code == 200:
            print("✅ Made private successfully")
            
            # Verify removed from audience list
            audience_response2 = make_request("GET", f"/musicians/{musician_slug}/playlists")
            if audience_response2.status_code == 200:
                audience_playlists2 = audience_response2.json()
                playlist_in_audience2 = any(p["id"] == playlist_id for p in audience_playlists2)
                if not playlist_in_audience2:
                    print("✅ Playlist removed from audience list when private")
                else:
                    print("❌ Playlist still in audience list when private")
        else:
            print(f"❌ Make private failed: {private_response.status_code}")
    else:
        print(f"❌ Make public failed: {public_response.status_code}")
    
    # Step 6: Test soft delete
    print("📊 Step 6: Test soft delete")
    
    # Get playlist count before deletion
    playlists_before_response = make_request("GET", "/playlists", auth_token=auth_token)
    if playlists_before_response.status_code == 200:
        playlists_before = playlists_before_response.json()
        count_before = len(playlists_before)
        print(f"📊 Playlists before deletion: {count_before}")
    
    # Delete playlist
    delete_response = make_request("DELETE", f"/playlists/{playlist_id}", auth_token=auth_token)
    
    if delete_response.status_code == 200:
        delete_result = delete_response.json()
        print(f"✅ Soft delete successful: {delete_result.get('message')}")
        
        # Verify removed from authenticated list
        playlists_after_response = make_request("GET", "/playlists", auth_token=auth_token)
        if playlists_after_response.status_code == 200:
            playlists_after = playlists_after_response.json()
            count_after = len(playlists_after)
            print(f"📊 Playlists after deletion: {count_after}")
            
            if count_after == count_before - 1:
                print("✅ Playlist count decreased correctly")
            else:
                print("❌ Playlist count not decreased correctly")
            
            # Verify not in list
            playlist_still_in_list = any(p["id"] == playlist_id for p in playlists_after)
            if not playlist_still_in_list:
                print("✅ Playlist removed from authenticated list")
            else:
                print("❌ Playlist still in authenticated list")
        
        # Verify not in audience list
        audience_final_response = make_request("GET", f"/musicians/{musician_slug}/playlists")
        if audience_final_response.status_code == 200:
            audience_final_playlists = audience_final_response.json()
            playlist_in_audience_final = any(p["id"] == playlist_id for p in audience_final_playlists)
            if not playlist_in_audience_final:
                print("✅ Playlist removed from audience list")
            else:
                print("❌ Playlist still in audience list")
    else:
        print(f"❌ Soft delete failed: {delete_response.status_code}")
    
    print("=" * 60)
    print("🎵 FOCUSED TESTING COMPLETE")

if __name__ == "__main__":
    main()