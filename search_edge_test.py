#!/usr/bin/env python3
"""
Edge case testing for search functionality
"""

import requests
import json

BASE_URL = "https://c9aa150a-6f2f-42af-9179-ded9ed77f946.preview.emergentagent.com/api"

def test_search_edge_cases():
    """Test search functionality edge cases"""
    
    # Use the existing test musician
    login_data = {
        "email": "search.test@requestwave.com",
        "password": "SearchTest123!"
    }
    
    # Login
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code != 200:
        print("❌ Failed to login")
        return
    
    auth_data = response.json()
    token = auth_data["token"]
    slug = auth_data["musician"]["slug"]
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔍 Testing search edge cases")
    
    edge_cases = [
        ("", "Empty search should return all songs"),
        ("   ", "Whitespace search should return all songs"),
        ("nonexistent", "Non-existent search should return empty results"),
        ("love's", "Search with apostrophe"),
        ("rock&roll", "Search with ampersand"),
        ("jazz-fusion", "Search with hyphen"),
        ("20", "Partial year search"),
        ("a" * 50, "Very long search term")
    ]
    
    for search_term, description in edge_cases:
        params = {"search": search_term}
        response = requests.get(f"{BASE_URL}/musicians/{slug}/songs", headers=headers, params=params)
        
        if response.status_code == 200:
            songs = response.json()
            print(f"✅ {description}: Found {len(songs)} songs")
        else:
            print(f"❌ {description}: API error {response.status_code}")

if __name__ == "__main__":
    test_search_edge_cases()