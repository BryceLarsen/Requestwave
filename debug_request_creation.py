#!/usr/bin/env python3
"""
Debug Request Creation Issue
Test request creation on internal API to get detailed error information
"""

import requests
import json

# Test on internal API first
INTERNAL_BASE_URL = "http://localhost:8001/api"
PRODUCTION_BASE_URL = "https://requestwave.app/api"

def test_internal_request_creation():
    print("=== Testing Internal Request Creation ===")
    
    # First get a song ID from Bryce's songs
    try:
        response = requests.get(f"{INTERNAL_BASE_URL}/musicians/bryce-larsen/songs", timeout=10)
        if response.status_code == 200:
            songs = response.json()
            if songs:
                test_song = songs[0]
                print(f"Using song: {test_song['title']} by {test_song['artist']}")
                
                # Try to create a request
                request_data = {
                    "song_id": test_song["id"],
                    "requester_name": "Debug Test User",
                    "requester_email": "debug@test.com",
                    "dedication": "Debug test request",
                    "tip_amount": 0.0
                }
                
                print(f"Request data: {json.dumps(request_data, indent=2)}")
                
                response = requests.post(f"{INTERNAL_BASE_URL}/requests", json=request_data, timeout=10)
                print(f"Response status: {response.status_code}")
                print(f"Response headers: {dict(response.headers)}")
                print(f"Response text: {response.text}")
                
                if response.status_code == 200:
                    print("✅ Internal request creation successful!")
                    return response.json()
                else:
                    print(f"❌ Internal request creation failed: {response.status_code}")
                    return None
            else:
                print("No songs found")
                return None
        else:
            print(f"Failed to get songs: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def test_production_request_creation():
    print("\n=== Testing Production Request Creation ===")
    
    # First get a song ID from Bryce's songs
    try:
        response = requests.get(f"{PRODUCTION_BASE_URL}/musicians/bryce-larsen/songs", timeout=30)
        if response.status_code == 200:
            songs = response.json()
            if songs:
                test_song = songs[0]
                print(f"Using song: {test_song['title']} by {test_song['artist']}")
                
                # Try to create a request
                request_data = {
                    "song_id": test_song["id"],
                    "requester_name": "Debug Test User",
                    "requester_email": "debug@test.com",
                    "dedication": "Debug test request",
                    "tip_amount": 0.0
                }
                
                print(f"Request data: {json.dumps(request_data, indent=2)}")
                
                response = requests.post(f"{PRODUCTION_BASE_URL}/requests", json=request_data, timeout=30)
                print(f"Response status: {response.status_code}")
                print(f"Response headers: {dict(response.headers)}")
                print(f"Response text: {response.text}")
                
                if response.status_code == 200:
                    print("✅ Production request creation successful!")
                    return response.json()
                else:
                    print(f"❌ Production request creation failed: {response.status_code}")
                    return None
            else:
                print("No songs found")
                return None
        else:
            print(f"Failed to get songs: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    print("🔍 DEBUG REQUEST CREATION ISSUE")
    print("=" * 50)
    
    # Test internal first
    internal_result = test_internal_request_creation()
    
    # Test production
    production_result = test_production_request_creation()
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"Internal API: {'✅ SUCCESS' if internal_result else '❌ FAILED'}")
    print(f"Production API: {'✅ SUCCESS' if production_result else '❌ FAILED'}")