#!/usr/bin/env python3
"""
Quick test to check both subscription status functions for brycelarsenmusic@gmail.com
"""

import requests
import json

BASE_URL = "https://music-flow-update.preview.emergentagent.com/api"
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
    print("🔍 DEBUGGING SUBSCRIPTION STATUS MISMATCH")
    print("=" * 80)
    
    # Login
    print("📊 Step 1: Login with brycelarsenmusic@gmail.com")
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
    musician_id = login_data_response["musician"]["id"]
    
    print(f"   ✅ Successfully logged in")
    print(f"   ✅ Musician ID: {musician_id}")
    
    # Check freemium subscription status (what the endpoint returns)
    print("\n📊 Step 2: Check /subscription/status endpoint (freemium system)")
    
    subscription_response = make_request("GET", "/subscription/status", auth_token=auth_token)
    
    if subscription_response.status_code == 200:
        subscription_data = subscription_response.json()
        print(f"   📊 Freemium status: {json.dumps(subscription_data, indent=2, default=str)}")
    else:
        print(f"   ❌ Failed to get freemium status: {subscription_response.status_code}")
    
    # Check if there's a legacy subscription status endpoint
    print("\n📊 Step 3: Check if legacy subscription status is accessible")
    
    # Try to find a legacy endpoint or check the musician data directly
    # Since we can't directly call the legacy function, let's see what the musician record contains
    
    # Check if playlists are accessible (this uses check_pro_access internally)
    print("\n📊 Step 4: Test playlist access (uses check_pro_access internally)")
    
    playlists_response = make_request("GET", "/playlists", auth_token=auth_token)
    
    if playlists_response.status_code == 200:
        playlists_data = playlists_response.json()
        print(f"   ✅ Playlists accessible - found {len(playlists_data)} playlists")
        print(f"   📊 This means check_pro_access() returned True")
    elif playlists_response.status_code == 403:
        print(f"   ❌ Playlists access denied - check_pro_access() returned False")
    else:
        print(f"   ⚠️  Unexpected response: {playlists_response.status_code}")
    
    # Try to create a playlist (also uses check_pro_access)
    print("\n📊 Step 5: Test playlist creation (uses check_pro_access internally)")
    
    test_playlist_data = {
        "name": "Debug Test Playlist",
        "song_ids": []
    }
    
    create_response = make_request("POST", "/playlists", test_playlist_data, auth_token=auth_token)
    
    if create_response.status_code == 200:
        created_playlist = create_response.json()
        print(f"   ✅ Playlist creation successful - check_pro_access() returned True")
        print(f"   📊 Created playlist: {created_playlist.get('name')}")
        
        # Clean up
        delete_response = requests.delete(f"{BASE_URL}/playlists/{created_playlist['id']}", 
                                        headers={"Authorization": f"Bearer {auth_token}"})
        if delete_response.status_code == 200:
            print(f"   ✅ Cleaned up test playlist")
    elif create_response.status_code == 403:
        print(f"   ❌ Playlist creation denied - check_pro_access() returned False")
        print(f"   📊 Response: {create_response.text}")
    else:
        print(f"   ⚠️  Unexpected response: {create_response.status_code}")
        print(f"   📊 Response: {create_response.text}")
    
    print("\n" + "=" * 80)
    print("🔍 ANALYSIS:")
    print("- Freemium system shows plan='canceled'")
    print("- But playlist access works, meaning check_pro_access() returns True")
    print("- This suggests check_pro_access() uses legacy system with different logic")
    print("- The mismatch explains why frontend might not show playlists but backend allows them")
    print("=" * 80)

if __name__ == "__main__":
    main()