#!/usr/bin/env python3
"""
Test playlist import with blank notes using unique song titles
"""

import requests
import json
import uuid

# Configuration
BASE_URL = "https://requestwave-revamp.preview.emergentagent.com/api"

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
    print("🔍 TESTING PLAYLIST IMPORT WITH BLANK NOTES - NEW SONGS")
    print("=" * 80)
    
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
    
    # First, let's delete a few existing songs to make room for testing
    print("\n📊 Step 1: Delete some existing songs to test fresh imports")
    
    songs_response = make_request("GET", "/songs", auth_token=auth_token)
    if songs_response.status_code == 200:
        songs = songs_response.json()
        
        # Find songs with old playlist notes to delete
        songs_to_delete = []
        for song in songs:
            notes = song.get("notes", "")
            if "Imported from Spotify playlist" in notes or "Sample from Apple Music playlist" in notes:
                songs_to_delete.append(song)
                if len(songs_to_delete) >= 3:  # Delete up to 3 songs
                    break
        
        print(f"   🗑️  Found {len(songs_to_delete)} songs with old playlist notes to delete")
        
        for song in songs_to_delete:
            delete_response = requests.delete(
                f"{BASE_URL}/songs/{song['id']}", 
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            if delete_response.status_code == 200:
                print(f"   ✅ Deleted: '{song['title']}' by '{song['artist']}'")
            else:
                print(f"   ❌ Failed to delete: '{song['title']}' by '{song['artist']}'")
    
    # Now test playlist import
    print("\n📊 Step 2: Test Spotify playlist import with fresh songs")
    
    # Get song count before import
    songs_before_response = make_request("GET", "/songs", auth_token=auth_token)
    songs_before_count = len(songs_before_response.json()) if songs_before_response.status_code == 200 else 0
    print(f"   📊 Songs before import: {songs_before_count}")
    
    # Test Spotify playlist import
    spotify_playlist_data = {
        "playlist_url": "https://open.spotify.com/playlist/37i9dQZEVXbLRQDuF5jeBp",
        "platform": "spotify"
    }
    
    spotify_response = make_request("POST", "/songs/playlist/import", spotify_playlist_data, auth_token=auth_token)
    
    if spotify_response.status_code == 200:
        spotify_data = spotify_response.json()
        print(f"   📊 Spotify import response: {json.dumps(spotify_data, indent=2)}")
        
        if spotify_data.get("songs_added", 0) > 0:
            print(f"   ✅ Successfully imported {spotify_data['songs_added']} new songs")
            
            # Check the notes field of newly imported songs
            songs_after_response = make_request("GET", "/songs", auth_token=auth_token)
            if songs_after_response.status_code == 200:
                songs_after = songs_after_response.json()
                newly_imported = songs_after[songs_before_count:] if len(songs_after) > songs_before_count else []
                
                print(f"\n🎵 Checking {len(newly_imported)} newly imported songs for blank notes:")
                
                blank_notes_count = 0
                non_blank_notes = []
                
                for i, song in enumerate(newly_imported):
                    title = song.get("title", "Unknown")
                    artist = song.get("artist", "Unknown")
                    notes = song.get("notes", None)
                    
                    print(f"     • Song {i+1}: '{title}' by '{artist}'")
                    print(f"       Notes field: {repr(notes)}")
                    
                    if notes == "":
                        blank_notes_count += 1
                        print(f"       ✅ Notes field is blank (empty string)")
                    else:
                        non_blank_notes.append(f"'{title}' by '{artist}' has notes: {repr(notes)}")
                        print(f"       ❌ Notes field is NOT blank: {repr(notes)}")
                
                # Final assessment
                if blank_notes_count == len(newly_imported) and len(non_blank_notes) == 0:
                    print(f"\n🎉 SUCCESS: All {blank_notes_count} newly imported songs have blank notes field!")
                    print("✅ CRITICAL CHECK PASSED: Playlist import blank notes functionality is working correctly")
                else:
                    print(f"\n❌ FAILURE: {len(non_blank_notes)} songs have non-blank notes:")
                    for error in non_blank_notes:
                        print(f"   • {error}")
            else:
                print(f"   ❌ Failed to retrieve songs after import: {songs_after_response.status_code}")
        else:
            print(f"   ⚠️  No new songs imported (all were duplicates): {spotify_data}")
    else:
        print(f"   ❌ Spotify import failed: {spotify_response.status_code}, Response: {spotify_response.text}")
    
    # Test Apple Music import
    print("\n📊 Step 3: Test Apple Music playlist import")
    
    songs_before_apple_response = make_request("GET", "/songs", auth_token=auth_token)
    songs_before_apple_count = len(songs_before_apple_response.json()) if songs_before_apple_response.status_code == 200 else 0
    
    apple_playlist_data = {
        "playlist_url": "https://music.apple.com/us/playlist/todays-hits/pl.f4d106fed2bd41149aaacabb233eb5eb",
        "platform": "apple_music"
    }
    
    apple_response = make_request("POST", "/songs/playlist/import", apple_playlist_data, auth_token=auth_token)
    
    if apple_response.status_code == 200:
        apple_data = apple_response.json()
        print(f"   📊 Apple Music import response: {json.dumps(apple_data, indent=2)}")
        
        if apple_data.get("songs_added", 0) > 0:
            print(f"   ✅ Successfully imported {apple_data['songs_added']} new Apple Music songs")
            
            # Check the notes field of newly imported Apple Music songs
            songs_after_apple_response = make_request("GET", "/songs", auth_token=auth_token)
            if songs_after_apple_response.status_code == 200:
                songs_after_apple = songs_after_apple_response.json()
                newly_imported_apple = songs_after_apple[songs_before_apple_count:] if len(songs_after_apple) > songs_before_apple_count else []
                
                print(f"\n🎵 Checking {len(newly_imported_apple)} newly imported Apple Music songs for blank notes:")
                
                apple_blank_notes_count = 0
                apple_non_blank_notes = []
                
                for i, song in enumerate(newly_imported_apple):
                    title = song.get("title", "Unknown")
                    artist = song.get("artist", "Unknown")
                    notes = song.get("notes", None)
                    
                    print(f"     • Apple Song {i+1}: '{title}' by '{artist}'")
                    print(f"       Notes field: {repr(notes)}")
                    
                    if notes == "":
                        apple_blank_notes_count += 1
                        print(f"       ✅ Notes field is blank (empty string)")
                    else:
                        apple_non_blank_notes.append(f"'{title}' by '{artist}' has notes: {repr(notes)}")
                        print(f"       ❌ Notes field is NOT blank: {repr(notes)}")
                
                # Final assessment for Apple Music
                if apple_blank_notes_count == len(newly_imported_apple) and len(apple_non_blank_notes) == 0:
                    print(f"\n🎉 SUCCESS: All {apple_blank_notes_count} newly imported Apple Music songs have blank notes field!")
                else:
                    print(f"\n❌ FAILURE: {len(apple_non_blank_notes)} Apple Music songs have non-blank notes:")
                    for error in apple_non_blank_notes:
                        print(f"   • {error}")
        else:
            print(f"   ⚠️  No new Apple Music songs imported (all were duplicates): {apple_data}")
    else:
        print(f"   ❌ Apple Music import failed: {apple_response.status_code}")
    
    print("\n" + "=" * 80)
    print("🎯 BLANK NOTES TESTING COMPLETE")

if __name__ == "__main__":
    main()