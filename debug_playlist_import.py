#!/usr/bin/env python3
"""
Debug playlist import to see what's happening with notes field
"""

import requests
import json
import httpx
import asyncio

async def debug_spotify_playlist():
    """Debug the Spotify playlist scraping process"""
    playlist_id = "37i9dQZEVXbLRQDuF5jeBp"
    
    print(f"🔍 Debugging Spotify playlist: {playlist_id}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # Test oEmbed request
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        oembed_url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/playlist/{playlist_id}"
        
        try:
            oembed_response = await client.get(oembed_url)
            if oembed_response.status_code == 200:
                oembed_data = oembed_response.json()
                playlist_title = oembed_data.get('title', 'Unknown Playlist')
                
                print(f"📊 oEmbed response successful")
                print(f"   Playlist title: {repr(playlist_title)}")
                print(f"   Full oEmbed data: {json.dumps(oembed_data, indent=2)}")
                
                # Check what get_popular_songs_by_playlist_type would return
                title_lower = playlist_title.lower()
                print(f"   Title lowercase: {repr(title_lower)}")
                
                # Check conditions
                top_hit_condition = any(word in title_lower for word in ["top", "hit", "popular", "chart"])
                print(f"   Matches 'top/hit/popular/chart' condition: {top_hit_condition}")
                
                if top_hit_condition:
                    print("   Would return top hits songs:")
                    songs = [
                        {
                            'title': 'As It Was',
                            'artist': 'Harry Styles',
                            'genres': ['Pop'],
                            'moods': ['Upbeat'],
                            'year': 2022
                        },
                        {
                            'title': 'Heat Waves',
                            'artist': 'Glass Animals',
                            'genres': ['Alternative'],
                            'moods': ['Chill'],
                            'year': 2020
                        },
                        {
                            'title': 'Blinding Lights',
                            'artist': 'The Weeknd',
                            'genres': ['Pop'],
                            'moods': ['Energetic'],
                            'year': 2019
                        },
                        {
                            'title': 'Good 4 U',
                            'artist': 'Olivia Rodrigo',
                            'genres': ['Pop'],
                            'moods': ['Energetic'],
                            'year': 2021
                        },
                        {
                            'title': 'Levitating',
                            'artist': 'Dua Lipa',
                            'genres': ['Pop'],
                            'moods': ['Upbeat'],
                            'year': 2020
                        }
                    ]
                    
                    # Simulate the notes setting process
                    for song in songs:
                        song['notes'] = ''
                        song['source'] = 'spotify'
                    
                    print("   After setting notes to blank:")
                    for i, song in enumerate(songs):
                        print(f"     {i+1}. '{song['title']}' by '{song['artist']}' - Notes: {repr(song['notes'])}")
                
            else:
                print(f"❌ oEmbed request failed: {oembed_response.status_code}")
                
        except Exception as e:
            print(f"❌ oEmbed request exception: {str(e)}")

def main():
    print("🔍 DEBUGGING PLAYLIST IMPORT PROCESS")
    print("=" * 60)
    
    asyncio.run(debug_spotify_playlist())

if __name__ == "__main__":
    main()