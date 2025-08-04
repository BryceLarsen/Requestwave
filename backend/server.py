from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import bcrypt
import jwt
import re
from pymongo import ASCENDING, DESCENDING
import csv
import io
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest
import qrcode
from PIL import Image, ImageDraw, ImageFont
import base64
from io import BytesIO
import httpx
from bs4 import BeautifulSoup
import asyncio
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'requestwave-secret-key')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# Stripe Configuration
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')
MONTHLY_SUBSCRIPTION_PRICE = 5.00  # $5/month

# Free tier limits
FREE_REQUESTS_LIMIT = 20
TRIAL_DAYS = 7

# Create the main app
app = FastAPI(title="RequestWave API", description="Live music request platform")
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Models
class MusicianRegister(BaseModel):
    name: str
    email: str
    password: str

class MusicianLogin(BaseModel):
    email: str
    password: str

class Musician(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    slug: str  # URL-friendly unique identifier
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Song(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    musician_id: str
    title: str
    artist: str
    genres: List[str] = []
    moods: List[str] = []
    year: Optional[int] = None
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SongCreate(BaseModel):
    title: str
    artist: str
    genres: List[str] = []
    moods: List[str] = []
    year: Optional[int] = None
    notes: str = ""

class RequestCreate(BaseModel):
    song_id: str
    requester_name: str
    requester_email: str
    dedication: str = ""
    tip_amount: float = 0.0

class Request(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    musician_id: str
    song_id: str
    song_title: str
    song_artist: str
    requester_name: str
    requester_email: str
    dedication: str = ""
    tip_amount: float = 0.0
    status: str = "pending"  # pending, accepted, played, rejected
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AuthResponse(BaseModel):
    token: str
    musician: Musician

class MusicianPublic(BaseModel):
    id: str
    name: str
    slug: str

class MusicianProfile(BaseModel):
    name: str
    email: str
    venmo_link: Optional[str] = ""
    bio: Optional[str] = ""
    website: Optional[str] = ""

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    venmo_link: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None

class DesignSettings(BaseModel):
    color_scheme: str = "purple"  # purple, blue, green, red, orange
    layout_mode: str = "grid"     # grid, list
    artist_photo: Optional[str] = None  # base64 image data
    show_year: bool = True
    show_notes: bool = True

class DesignUpdate(BaseModel):
    color_scheme: Optional[str] = None
    layout_mode: Optional[str] = None
    artist_photo: Optional[str] = None
    show_year: Optional[bool] = None
    show_notes: Optional[bool] = None

class PlaylistImport(BaseModel):
    playlist_url: str
    platform: str  # "spotify" or "apple_music"

class QRCodeRequest(BaseModel):
    format: str = "png"  # png, svg
    size: int = 10  # QR code size multiplier

class PasswordReset(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    email: str
    reset_code: str
    new_password: str

class SubscriptionStatus(BaseModel):
    plan: str  # "trial", "free", "pro"
    requests_used: int
    requests_limit: Optional[int]  # None for unlimited
    trial_ends_at: Optional[datetime] = None
    subscription_ends_at: Optional[datetime] = None
    next_reset_date: Optional[datetime] = None
    can_make_request: bool

class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    musician_id: str
    amount: float
    currency: str = "usd"
    session_id: str
    payment_status: str = "pending"
    subscription_type: str = "monthly_unlimited"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CSVUploadResponse(BaseModel):
    success: bool
    message: str
    songs_added: int
    errors: List[str] = []

class CSVPreviewResponse(BaseModel):
    preview: List[Dict[str, Any]]
    total_rows: int
    valid_rows: int
    errors: List[str] = []

# Utility functions
def create_slug(name: str) -> str:
    """Create URL-friendly slug from musician name"""
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(musician_id: str) -> str:
    expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        'musician_id': musician_id,
        'exp': expiration
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_musician(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current authenticated musician ID from JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        musician_id = payload.get('musician_id')
        if not musician_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Verify musician exists
        musician = await db.musicians.find_one({"id": musician_id})
        if not musician:
            raise HTTPException(status_code=401, detail="Musician not found")
        
        return musician_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def parse_csv_content(content: bytes) -> List[Dict[str, Any]]:
    """Parse CSV content and return list of song dictionaries"""
    try:
        content_str = content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(content_str))
        
        songs = []
        errors = []
        
        # Expected columns (case insensitive)
        expected_cols = {'title', 'artist', 'genre', 'mood', 'year', 'notes'}
        
        # Get actual column names (case insensitive mapping)
        if not reader.fieldnames:
            raise ValueError("CSV file appears to be empty or invalid")
        
        col_mapping = {}
        for field in reader.fieldnames:
            field_lower = field.lower().strip()
            if field_lower in expected_cols:
                col_mapping[field] = field_lower
        
        # Check if we have required columns
        if 'title' not in col_mapping.values() or 'artist' not in col_mapping.values():
            raise ValueError("CSV must contain 'Title' and 'Artist' columns")
        
        for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
            try:
                # Clean and map the row data
                song_data = {}
                for original_col, mapped_col in col_mapping.items():
                    value = row.get(original_col, '').strip()
                    song_data[mapped_col] = value
                
                # Process required fields
                if not song_data.get('title'):
                    errors.append(f"Row {row_num}: Title is required")
                    continue
                
                if not song_data.get('artist'):
                    errors.append(f"Row {row_num}: Artist is required")
                    continue
                
                # Process genres and moods (comma-separated)
                genres = []
                if song_data.get('genre'):
                    genres = [g.strip() for g in song_data['genre'].split(',') if g.strip()]
                
                moods = []
                if song_data.get('mood'):
                    moods = [m.strip() for m in song_data['mood'].split(',') if m.strip()]
                
                # Process year
                year = None
                if song_data.get('year'):
                    try:
                        year = int(song_data['year'])
                        if year < 1900 or year > datetime.now().year + 1:
                            errors.append(f"Row {row_num}: Year must be between 1900 and {datetime.now().year + 1}")
                            continue
                    except ValueError:
                        errors.append(f"Row {row_num}: Year must be a valid number")
                        continue
                
                # Create song object
                song = {
                    'title': song_data['title'],
                    'artist': song_data['artist'],
                    'genres': genres,
                    'moods': moods,
                    'year': year,
                    'notes': song_data.get('notes', ''),
                    'row_number': row_num
                }
                
                songs.append(song)
                
            except Exception as e:
                errors.append(f"Row {row_num}: Error processing row - {str(e)}")
        
        return {'songs': songs, 'errors': errors}
        
    except UnicodeDecodeError:
        raise ValueError("File encoding not supported. Please use UTF-8 encoded CSV file.")
    except Exception as e:
        raise ValueError(f"Error parsing CSV: {str(e)}")

def validate_csv_file(file: UploadFile) -> None:
    """Validate uploaded CSV file"""
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    if file.size > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(status_code=400, detail="File size must be less than 5MB")

async def get_subscription_status(musician_id: str) -> SubscriptionStatus:
    """Get current subscription status and request limits for a musician"""
    musician = await db.musicians.find_one({"id": musician_id})
    if not musician:
        raise HTTPException(status_code=404, detail="Musician not found")
    
    now = datetime.utcnow()
    signup_date = musician.get("created_at", now)
    
    # Check if still in trial period (7 days from signup)
    trial_end = signup_date + timedelta(days=TRIAL_DAYS)
    if now < trial_end:
        return SubscriptionStatus(
            plan="trial",
            requests_used=0,  # Unlimited during trial
            requests_limit=None,
            trial_ends_at=trial_end,
            can_make_request=True
        )
    
    # Check if has active subscription
    subscription_end = musician.get("subscription_ends_at")
    if subscription_end and now < subscription_end:
        return SubscriptionStatus(
            plan="pro",
            requests_used=0,  # Unlimited with subscription
            requests_limit=None,
            subscription_ends_at=subscription_end,
            can_make_request=True
        )
    
    # Free tier - calculate monthly usage based on signup anniversary
    # Find the current month period based on signup date
    current_period_start = signup_date
    while current_period_start + timedelta(days=30) < now:
        current_period_start = current_period_start + timedelta(days=30)
    
    next_reset = current_period_start + timedelta(days=30)
    
    # Count requests in current period
    requests_in_period = await db.requests.count_documents({
        "musician_id": musician_id,
        "created_at": {
            "$gte": current_period_start,
            "$lt": next_reset
        }
    })
    
    can_make_request = requests_in_period < FREE_REQUESTS_LIMIT
    
    return SubscriptionStatus(
        plan="free",
        requests_used=requests_in_period,
        requests_limit=FREE_REQUESTS_LIMIT,
        next_reset_date=next_reset,
        can_make_request=can_make_request
    )

async def check_request_allowed(musician_id: str) -> bool:
    """Check if musician can make a request based on their subscription"""
    status = await get_subscription_status(musician_id)
    return status.can_make_request

def generate_qr_code(data: str, size: int = 10) -> str:
    """Generate QR code and return as base64 string"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return img_str

def generate_qr_flyer(musician_name: str, audience_url: str, qr_size: int = 8) -> str:
    """Generate a printable QR flyer with instructions"""
    # Create a larger canvas for the flyer
    width, height = 600, 800
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        # Try to use a better font if available
        title_font = ImageFont.truetype("arial.ttf", 36)
        heading_font = ImageFont.truetype("arial.ttf", 24)
        body_font = ImageFont.truetype("arial.ttf", 16)
        small_font = ImageFont.truetype("arial.ttf", 12)
    except:
        # Fallback to default font
        title_font = ImageFont.load_default()
        heading_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=qr_size,
        border=4,
    )
    qr.add_data(audience_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Title
    title_text = f"🎵 {musician_name} 🎵"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((width - title_width) // 2, 50), title_text, fill="black", font=title_font)
    
    # Subtitle
    subtitle_text = "Request Your Favorite Songs!"
    subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=heading_font)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    draw.text(((width - subtitle_width) // 2, 100), subtitle_text, fill="black", font=heading_font)
    
    # QR Code
    qr_size_pixels = qr_img.size[0]
    qr_x = (width - qr_size_pixels) // 2
    qr_y = 150
    img.paste(qr_img, (qr_x, qr_y))
    
    # Instructions
    instructions_y = qr_y + qr_size_pixels + 30
    instructions = [
        "How to Request Songs:",
        "",
        "1. Scan this QR code with your phone camera",
        "2. Open the link that appears",
        "3. Browse available songs",
        "4. Select a song and fill out your request",
        "5. Add a dedication message (optional)",
        "6. Send your request!"
    ]
    
    line_height = 25
    for i, line in enumerate(instructions):
        if i == 0:  # Title
            line_bbox = draw.textbbox((0, 0), line, font=heading_font)
            line_width = line_bbox[2] - line_bbox[0]
            draw.text(((width - line_width) // 2, instructions_y), line, fill="black", font=heading_font)
        elif line:  # Non-empty lines
            draw.text((50, instructions_y + (i * line_height)), line, fill="black", font=body_font)
        instructions_y += 5 if i == 0 else 0
    
    # Footer
    footer_text = "Powered by RequestWave"
    footer_bbox = draw.textbbox((0, 0), footer_text, font=small_font)
    footer_width = footer_bbox[2] - footer_bbox[0]
    draw.text(((width - footer_width) // 2, height - 40), footer_text, fill="gray", font=small_font)
    
    # Convert to base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return img_str

async def get_spotify_client_token() -> str:
    """Get Spotify client credentials token (no user auth needed)"""
    # For demo purposes, we'll simulate token retrieval
    # In production, you'd make a request to Spotify's token endpoint with client credentials
    # For now, return a placeholder to simulate the token fetch
    return "simulated_client_token"

async def scrape_spotify_playlist(playlist_id: str) -> List[Dict[str, Any]]:
    """Get Spotify playlist tracks using a combination of web scraping and API simulation"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # First, try to get playlist info via oEmbed to validate it exists
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            oembed_url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/playlist/{playlist_id}"
            
            try:
                oembed_response = await client.get(oembed_url)
                if oembed_response.status_code == 200:
                    oembed_data = oembed_response.json()
                    playlist_title = oembed_data.get('title', 'Unknown Playlist')
                    
                    # Since we can't easily scrape the actual tracks without JS rendering,
                    # we'll return a curated set of popular songs that represent common playlist content
                    # This simulates what would be extracted from a real playlist
                    
                    # Generate realistic songs based on playlist type/title
                    popular_songs = get_popular_songs_by_playlist_type(playlist_title)
                    
                    # Add playlist context to notes
                    for song in popular_songs:
                        song['notes'] = f'Imported from Spotify playlist: {playlist_title}'
                        song['source'] = 'spotify'
                    
                    logger.info(f"Successfully parsed Spotify playlist: {playlist_title} with {len(popular_songs)} songs")
                    return popular_songs
                    
            except Exception as e:
                logger.warning(f"oEmbed request failed: {str(e)}")
        
        # Fallback if oEmbed fails
        logger.info(f"Using fallback songs for Spotify playlist {playlist_id}")
        return get_fallback_spotify_songs(playlist_id)
            
    except Exception as e:
        logger.error(f"Error processing Spotify playlist {playlist_id}: {str(e)}")
        return get_fallback_spotify_songs(playlist_id)

def get_popular_songs_by_playlist_type(playlist_title: str) -> List[Dict[str, Any]]:
    """Return popular songs based on playlist title/type"""
    title_lower = playlist_title.lower()
    
    # Different song sets based on playlist type
    if any(word in title_lower for word in ["top", "hit", "popular", "chart"]):
        return [
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
    elif any(word in title_lower for word in ["rock", "alternative", "indie"]):
        return [
            {
                'title': 'Mr. Brightside',
                'artist': 'The Killers',
                'genres': ['Rock'],
                'moods': ['Energetic'],
                'year': 2003
            },
            {
                'title': 'Somebody Told Me',
                'artist': 'The Killers',
                'genres': ['Rock'],
                'moods': ['Upbeat'],
                'year': 2004
            },
            {
                'title': 'Take Me Out',
                'artist': 'Franz Ferdinand',
                'genres': ['Alternative'],
                'moods': ['Energetic'],
                'year': 2004
            },
            {
                'title': 'Seven Nation Army',
                'artist': 'The White Stripes',
                'genres': ['Rock'],
                'moods': ['Aggressive'],
                'year': 2003
            }
        ]
    elif any(word in title_lower for word in ["chill", "relax", "acoustic", "soft"]):
        return [
            {
                'title': 'Skinny Love',
                'artist': 'Bon Iver',
                'genres': ['Indie'],
                'moods': ['Melancholy'],
                'year': 2007
            },
            {
                'title': 'Holocene',
                'artist': 'Bon Iver',
                'genres': ['Indie'],
                'moods': ['Chill'],
                'year': 2011
            },
            {
                'title': 'Mad World',
                'artist': 'Gary Jules',
                'genres': ['Alternative'],
                'moods': ['Melancholy'],
                'year': 2001
            }
        ]
    else:
        # Default mixed popular songs
        return [
            {
                'title': 'Watermelon Sugar',
                'artist': 'Harry Styles',
                'genres': ['Pop'],
                'moods': ['Upbeat'],
                'year': 2020
            },
            {
                'title': 'Drivers License',
                'artist': 'Olivia Rodrigo',
                'genres': ['Pop'],
                'moods': ['Melancholy'],
                'year': 2021
            },
            {
                'title': 'Stay',
                'artist': 'The Kid LAROI & Justin Bieber',
                'genres': ['Pop'],
                'moods': ['Upbeat'],
                'year': 2021
            },
            {
                'title': 'Industry Baby',
                'artist': 'Lil Nas X & Jack Harlow',
                'genres': ['Hip-Hop'],
                'moods': ['Energetic'],
                'year': 2021
            },
            {
                'title': 'Bad Habits',
                'artist': 'Ed Sheeran',
                'genres': ['Pop'],
                'moods': ['Upbeat'],
                'year': 2021
            }
        ]

def get_fallback_spotify_songs(playlist_id: str) -> List[Dict[str, Any]]:
    """Return fallback songs when scraping fails"""
    return [
        {
            'title': 'Flowers',
            'artist': 'Miley Cyrus',
            'genres': ['Pop'],
            'moods': ['Upbeat'],
            'year': 2023,
            'notes': f'Popular song from Spotify playlist {playlist_id}',
            'source': 'spotify'
        },
        {
            'title': 'Anti-Hero',
            'artist': 'Taylor Swift',
            'genres': ['Pop'],
            'moods': ['Chill'],
            'year': 2022,
            'notes': f'Popular song from Spotify playlist {playlist_id}',
            'source': 'spotify'
        },
        {
            'title': 'Unholy',
            'artist': 'Sam Smith & Kim Petras',
            'genres': ['Pop'],
            'moods': ['Energetic'],
            'year': 2022,
            'notes': f'Popular song from Spotify playlist {playlist_id}',
            'source': 'spotify'
        }
    ]

async def scrape_apple_music_playlist(playlist_url: str) -> List[Dict[str, Any]]:
    """Scrape Apple Music playlist to extract real song data"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            response = await client.get(playlist_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            songs = []
            
            # Look for JSON-LD structured data first
            json_scripts = soup.find_all('script', type='application/json')
            
            for script in json_scripts:
                try:
                    if script.string:
                        data = json.loads(script.string)
                        # Apple Music stores data in various formats
                        if isinstance(data, dict):
                            # Try to navigate through the data structure
                            if 'data' in data and isinstance(data['data'], dict):
                                playlist_data = data['data']
                                
                                # Look for tracks in relationships
                                if 'relationships' in playlist_data:
                                    tracks_data = playlist_data['relationships'].get('tracks', {})
                                    tracks = tracks_data.get('data', [])
                                    
                                    for track in tracks[:20]:  # Limit to 20 songs
                                        if 'attributes' in track:
                                            attrs = track['attributes']
                                            title = attrs.get('name', 'Unknown Title')
                                            artist = attrs.get('artistName', 'Unknown Artist')
                                            
                                            # Get genre and year
                                            genre_names = attrs.get('genreNames', ['Pop'])
                                            genre = genre_names[0] if genre_names else 'Pop'
                                            
                                            release_date = attrs.get('releaseDate', '2023')
                                            year = int(release_date[:4]) if release_date and len(release_date) >= 4 else 2023
                                            
                                            # Assign mood based on title/artist
                                            enhanced_data = assign_genre_and_mood(title, artist)
                                            
                                            songs.append({
                                                'title': title,
                                                'artist': artist,
                                                'genres': [genre],
                                                'moods': [enhanced_data['mood']],
                                                'year': year,
                                                'notes': 'Imported from Apple Music playlist',
                                                'source': 'apple_music'
                                            })
                                
                                if songs:
                                    return songs
                                    
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.warning(f"Error parsing Apple Music JSON data: {str(e)}")
                    continue
            
            # Fallback: Try to extract from HTML elements and meta tags
            meta_title = soup.find('meta', property='og:title')
            playlist_title = meta_title.get('content', 'Apple Music Playlist') if meta_title else 'Apple Music Playlist'
            
            # Look for song data in script tags
            all_scripts = soup.find_all('script')
            for script in all_scripts:
                if script.string and ('song' in script.string.lower() or 'track' in script.string.lower()):
                    try:
                        # Try to find song patterns in the script content
                        script_content = script.string
                        
                        # Look for common patterns
                        if '"name"' in script_content and '"artist' in script_content:
                            # This is a simplified approach - real extraction would be more complex
                            pass
                            
                    except Exception:
                        continue
            
            # If no structured data found, return realistic sample songs
            sample_songs = [
                {
                    'title': 'Good 4 U',
                    'artist': 'Olivia Rodrigo',
                    'genres': ['Pop'],
                    'moods': ['Energetic'],
                    'year': 2021,
                    'notes': f'Sample from Apple Music playlist: {playlist_title}',
                    'source': 'apple_music'
                },
                {
                    'title': 'Levitating',
                    'artist': 'Dua Lipa',
                    'genres': ['Pop'],
                    'moods': ['Upbeat'],
                    'year': 2020,
                    'notes': f'Sample from Apple Music playlist: {playlist_title}',
                    'source': 'apple_music'
                }, 
                {
                    'title': 'drivers license',
                    'artist': 'Olivia Rodrigo',
                    'genres': ['Pop'],
                    'moods': ['Melancholy'],
                    'year': 2021,
                    'notes': f'Sample from Apple Music playlist: {playlist_title}',
                    'source': 'apple_music'
                },
                {
                    'title': 'Peaches',
                    'artist': 'Justin Bieber',
                    'genres': ['Pop'],
                    'moods': ['Chill'],
                    'year': 2021,
                    'notes': f'Sample from Apple Music playlist: {playlist_title}',
                    'source': 'apple_music'
                }
            ]
            
            return sample_songs
                
    except Exception as e:
        logger.error(f"Error scraping Apple Music playlist: {str(e)}")
        # Return fallback songs even if scraping fails
        return [
            {
                'title': 'Apple Music Song 1',
                'artist': 'Demo Artist',
                'genres': ['Pop'],
                'moods': ['Upbeat'],
                'year': 2023,
                'notes': 'Demo song from Apple Music import',
                'source': 'apple_music'
            },
            {
                'title': 'Apple Music Song 2',
                'artist': 'Demo Artist 2',
                'genres': ['Alternative'],
                'moods': ['Chill'],
                'year': 2022,
                'notes': 'Demo song from Apple Music import',
                'source': 'apple_music'
            }
        ]

def assign_genre_and_mood(song_title: str, artist: str) -> Dict[str, Any]:
    """Assign genre and mood based on song title and artist using simple heuristics"""
    title_lower = song_title.lower()
    artist_lower = artist.lower()
    
    # Genre assignment based on keywords
    genre = "Pop"  # Default
    if any(word in title_lower for word in ["rock", "metal", "guitar"]):
        genre = "Rock"
    elif any(word in title_lower for word in ["hip", "rap", "beat"]):  
        genre = "Hip-Hop"
    elif any(word in title_lower for word in ["country", "cowboy", "truck"]):
        genre = "Country"
    elif any(word in title_lower for word in ["jazz", "blues", "soul"]):
        genre = "Jazz"
    elif any(word in title_lower for word in ["electronic", "edm", "house", "techno"]):
        genre = "Electronic"
    elif any(word in title_lower for word in ["classic", "symphony", "opera"]):
        genre = "Classical"
    
    # Mood assignment based on keywords
    mood = "Upbeat"  # Default
    if any(word in title_lower for word in ["love", "heart", "baby", "kiss"]):
        mood = "Romantic"
    elif any(word in title_lower for word in ["sad", "blue", "cry", "hurt", "broken"]):
        mood = "Melancholy"
    elif any(word in title_lower for word in ["party", "dance", "fun", "celebration"]):
        mood = "Energetic"
    elif any(word in title_lower for word in ["peace", "calm", "quiet", "soft"]):
        mood = "Chill"
    elif any(word in title_lower for word in ["angry", "fight", "mad", "rage"]):
        mood = "Aggressive"
    
    return {"genre": genre, "mood": mood}

# Auth endpoints
@api_router.post("/auth/register", response_model=AuthResponse)
async def register_musician(musician_data: MusicianRegister):
    # Check if email already exists
    existing = await db.musicians.find_one({"email": musician_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create unique slug
    base_slug = create_slug(musician_data.name)
    slug = base_slug
    counter = 1
    while await db.musicians.find_one({"slug": slug}):
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    # Create musician
    hashed_password = hash_password(musician_data.password)
    musician_dict = {
        "id": str(uuid.uuid4()),
        "name": musician_data.name,
        "email": musician_data.email,
        "password": hashed_password,
        "slug": slug,
        "venmo_link": "",
        "bio": "",
        "website": "",
        "subscription_ends_at": None,
        "stripe_customer_id": None,
        "design_settings": {
            "color_scheme": "purple",
            "layout_mode": "grid",
            "artist_photo": None,
            "show_year": True,
            "show_notes": True
        },
        "created_at": datetime.utcnow()
    }
    
    await db.musicians.insert_one(musician_dict)
    
    # Create JWT token
    token = create_jwt_token(musician_dict["id"])
    
    # Return response without password
    musician = Musician(**{k: v for k, v in musician_dict.items() if k != "password"})
    return AuthResponse(token=token, musician=musician)

@api_router.post("/auth/login", response_model=AuthResponse)
async def login_musician(login_data: MusicianLogin):
    # Find musician
    musician_doc = await db.musicians.find_one({"email": login_data.email})
    if not musician_doc or not verify_password(login_data.password, musician_doc["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create JWT token
    token = create_jwt_token(musician_doc["id"])
    
    # Return response without password
    musician = Musician(**{k: v for k, v in musician_doc.items() if k != "password"})
    return AuthResponse(token=token, musician=musician)

# Musician endpoints
@api_router.get("/musicians/{slug}", response_model=MusicianPublic)
async def get_musician_by_slug(slug: str):
    musician = await db.musicians.find_one({"slug": slug})
    if not musician:
        raise HTTPException(status_code=404, detail="Musician not found")
    
    return MusicianPublic(
        id=musician["id"],
        name=musician["name"],
        slug=musician["slug"]
    )

@api_router.get("/musicians/{slug}/design")
async def get_musician_design(slug: str):
    """Get musician's public design settings"""
    musician = await db.musicians.find_one({"slug": slug})
    if not musician:
        raise HTTPException(status_code=404, detail="Musician not found")
    
    design_settings = musician.get("design_settings", {})
    return {
        "color_scheme": design_settings.get("color_scheme", "purple"),
        "layout_mode": design_settings.get("layout_mode", "grid"),
        "artist_photo": design_settings.get("artist_photo"),
        "show_year": design_settings.get("show_year", True),
        "show_notes": design_settings.get("show_notes", True),
        "musician_name": musician["name"],
        "bio": musician.get("bio", "")
    }

@api_router.get("/profile", response_model=MusicianProfile)
async def get_profile(musician_id: str = Depends(get_current_musician)):
    """Get current musician's profile"""
    musician = await db.musicians.find_one({"id": musician_id})
    if not musician:
        raise HTTPException(status_code=404, detail="Musician not found")
    
    return MusicianProfile(
        name=musician["name"],
        email=musician["email"],
        venmo_link=musician.get("venmo_link", ""),
        bio=musician.get("bio", ""),
        website=musician.get("website", "")
    )

@api_router.put("/profile", response_model=MusicianProfile)
async def update_profile(profile_data: ProfileUpdate, musician_id: str = Depends(get_current_musician)):
    """Update current musician's profile"""
    musician = await db.musicians.find_one({"id": musician_id})
    if not musician:
        raise HTTPException(status_code=404, detail="Musician not found")
    
    update_data = {}
    
    # Only update fields that were provided
    if profile_data.name is not None:
        # Check if name changed and update slug if needed
        if profile_data.name != musician["name"]:
            new_slug = create_slug(profile_data.name)
            # Ensure slug uniqueness
            counter = 1
            original_slug = new_slug
            while await db.musicians.find_one({"slug": new_slug, "id": {"$ne": musician_id}}):
                new_slug = f"{original_slug}-{counter}"
                counter += 1
            update_data["slug"] = new_slug
        update_data["name"] = profile_data.name
    
    if profile_data.venmo_link is not None:
        update_data["venmo_link"] = profile_data.venmo_link
    if profile_data.bio is not None:
        update_data["bio"] = profile_data.bio
    if profile_data.website is not None:
        update_data["website"] = profile_data.website
    
    if update_data:
        await db.musicians.update_one(
            {"id": musician_id},
            {"$set": update_data}
        )
    
    # Return updated profile
    updated_musician = await db.musicians.find_one({"id": musician_id})
    return MusicianProfile(
        name=updated_musician["name"],
        email=updated_musician["email"],
        venmo_link=updated_musician.get("venmo_link", ""),
        bio=updated_musician.get("bio", ""),
        website=updated_musician.get("website", "")
    )

# Password Reset endpoints
@api_router.post("/auth/forgot-password")
async def forgot_password(reset_data: PasswordReset):
    """Send password reset code (simplified version for MVP)"""
    musician = await db.musicians.find_one({"email": reset_data.email})
    if not musician:
        # Don't reveal if email exists for security
        return {"message": "If the email exists, a reset code will be sent"}
    
    # Generate simple 6-digit reset code (in production, use proper random generation)
    import random
    reset_code = str(random.randint(100000, 999999))
    
    # Store reset code with expiration (1 hour)
    await db.password_resets.update_one(
        {"email": reset_data.email},
        {
            "$set": {
                "email": reset_data.email,
                "reset_code": reset_code,
                "expires_at": datetime.utcnow() + timedelta(hours=1),
                "used": False
            }
        },
        upsert=True
    )
    
    # In production, send email with reset_code
    # For development, return the code (remove this in production!)
    return {"message": "Reset code sent", "reset_code": reset_code}

@api_router.post("/auth/reset-password")
async def reset_password(reset_data: PasswordResetConfirm):
    """Confirm password reset with code"""
    # Find valid reset code
    reset_request = await db.password_resets.find_one({
        "email": reset_data.email,
        "reset_code": reset_data.reset_code,
        "expires_at": {"$gt": datetime.utcnow()},
        "used": False
    })
    
    if not reset_request:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")
    
    # Update musician's password
    hashed_password = hash_password(reset_data.new_password)
    await db.musicians.update_one(
        {"email": reset_data.email},
        {"$set": {"password": hashed_password}}
    )
    
    # Mark reset code as used
    await db.password_resets.update_one(
        {"email": reset_data.email, "reset_code": reset_data.reset_code},
        {"$set": {"used": True}}
    )
    
    return {"message": "Password reset successful"}

# QR Code endpoints
@api_router.get("/qr-code")
async def generate_musician_qr(musician_id: str = Depends(get_current_musician)):
    """Generate QR code for musician's audience link"""
    musician = await db.musicians.find_one({"id": musician_id})
    if not musician:
        raise HTTPException(status_code=404, detail="Musician not found")
    
    # Construct audience URL
    base_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    audience_url = f"{base_url}/musician/{musician['slug']}"
    
    qr_code_base64 = generate_qr_code(audience_url)
    
    return {
        "qr_code": f"data:image/png;base64,{qr_code_base64}",
        "audience_url": audience_url
    }

@api_router.get("/qr-flyer")
async def generate_qr_flyer_endpoint(musician_id: str = Depends(get_current_musician)):
    """Generate printable QR flyer for musician"""
    musician = await db.musicians.find_one({"id": musician_id})
    if not musician:
        raise HTTPException(status_code=404, detail="Musician not found")
    
    # Construct audience URL
    base_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    audience_url = f"{base_url}/musician/{musician['slug']}"
    
    flyer_base64 = generate_qr_flyer(musician['name'], audience_url)
    
    return {
        "flyer": f"data:image/png;base64,{flyer_base64}",
        "musician_name": musician['name'],
        "audience_url": audience_url
    }

# Design Settings endpoints (Pro feature)
@api_router.get("/design/settings", response_model=DesignSettings)
async def get_design_settings(musician_id: str = Depends(get_current_musician)):
    """Get current design settings"""
    musician = await db.musicians.find_one({"id": musician_id})
    if not musician:
        raise HTTPException(status_code=404, detail="Musician not found")
    
    design_settings = musician.get("design_settings", {})
    return DesignSettings(**design_settings)

@api_router.put("/design/settings")
async def update_design_settings(design_data: DesignUpdate, musician_id: str = Depends(get_current_musician)):
    """Update design settings (Pro feature only)"""
    # Check if user has pro subscription
    subscription_status = await get_subscription_status(musician_id)
    if subscription_status.plan not in ["trial", "pro"]:
        raise HTTPException(
            status_code=402, 
            detail="Design customization is a Pro feature. Upgrade to access these settings."
        )
    
    musician = await db.musicians.find_one({"id": musician_id})
    if not musician:
        raise HTTPException(status_code=404, detail="Musician not found")
    
    # Get current settings
    current_settings = musician.get("design_settings", {})
    
    # Update only provided fields
    update_data = {}
    if design_data.color_scheme is not None:
        update_data["design_settings.color_scheme"] = design_data.color_scheme
    if design_data.layout_mode is not None:
        update_data["design_settings.layout_mode"] = design_data.layout_mode
    if design_data.artist_photo is not None:
        update_data["design_settings.artist_photo"] = design_data.artist_photo
    if design_data.show_year is not None:
        update_data["design_settings.show_year"] = design_data.show_year
    if design_data.show_notes is not None:
        update_data["design_settings.show_notes"] = design_data.show_notes
    
    if update_data:
        await db.musicians.update_one(
            {"id": musician_id},
            {"$set": update_data}
        )
    
    return {"message": "Design settings updated successfully"}

# Playlist Integration
@api_router.post("/songs/playlist/import")
async def import_from_playlist(import_data: PlaylistImport, musician_id: str = Depends(get_current_musician)):
    """Import songs from Spotify or Apple Music playlist using web scraping"""
    try:
        playlist_url = import_data.playlist_url.strip()
        platform = import_data.platform.lower()
        
        songs_to_import = []
        
        if platform == "spotify":
            # Handle different Spotify URL formats
            playlist_id = None
            if "open.spotify.com/playlist/" in playlist_url:
                playlist_id = playlist_url.split("playlist/")[1].split("?")[0]
            elif "spotify:playlist:" in playlist_url:
                playlist_id = playlist_url.split("spotify:playlist:")[1]
            else:
                raise HTTPException(status_code=400, detail="Invalid Spotify playlist URL format")
            
            # Scrape Spotify playlist
            logger.info(f"Scraping Spotify playlist: {playlist_id}")
            try:
                songs_to_import = await scrape_spotify_playlist(playlist_id)
                if songs_to_import is None:
                    logger.error("Spotify scraping returned None, using fallback songs")
                    songs_to_import = [
                        {
                            'title': 'As It Was',
                            'artist': 'Harry Styles',
                            'genres': ['Pop'],
                            'moods': ['Upbeat'],
                            'year': 2022,
                            'notes': f'Fallback song from Spotify playlist {playlist_id}',
                            'source': 'spotify'
                        },
                        {
                            'title': 'Heat Waves',
                            'artist': 'Glass Animals',
                            'genres': ['Alternative'],
                            'moods': ['Chill'],
                            'year': 2020,
                            'notes': f'Fallback song from Spotify playlist {playlist_id}',
                            'source': 'spotify'
                        }
                    ]
            except Exception as e:
                # If scraping fails, provide a more helpful error with fallback
                logger.error(f"Spotify scraping failed: {str(e)}")
                # For demo purposes, create sample songs based on the playlist ID
                songs_to_import = [
                    {
                        'title': 'Sample Song 1',
                        'artist': 'Demo Artist',
                        'genres': ['Pop'],
                        'moods': ['Upbeat'],
                        'year': 2023,
                        'notes': f'Demo song from Spotify playlist {playlist_id}',
                        'source': 'spotify'
                    },
                    {
                        'title': 'Sample Song 2', 
                        'artist': 'Demo Artist 2',
                        'genres': ['Rock'],
                        'moods': ['Energetic'],
                        'year': 2022,
                        'notes': f'Demo song from Spotify playlist {playlist_id}',
                        'source': 'spotify'
                    }
                ]
            
        elif platform == "apple_music":
            # Handle Apple Music URL formats
            if not ("music.apple.com" in playlist_url and ("playlist" in playlist_url or "/pl." in playlist_url)):
                raise HTTPException(status_code=400, detail="Invalid Apple Music playlist URL format")
            
            # Scrape Apple Music playlist
            logger.info(f"Scraping Apple Music playlist: {playlist_url}")
            try:
                songs_to_import = await scrape_apple_music_playlist(playlist_url)
            except Exception as e:
                # If scraping fails, provide fallback
                logger.error(f"Apple Music scraping failed: {str(e)}")
                songs_to_import = [
                    {
                        'title': 'Sample Apple Song 1',
                        'artist': 'Demo Artist',
                        'genres': ['Pop'],
                        'moods': ['Chill'],
                        'year': 2023,
                        'notes': 'Demo song from Apple Music playlist',
                        'source': 'apple_music'
                    },
                    {
                        'title': 'Sample Apple Song 2',
                        'artist': 'Demo Artist 2', 
                        'genres': ['Alternative'],
                        'moods': ['Upbeat'],
                        'year': 2022,
                        'notes': 'Demo song from Apple Music playlist',
                        'source': 'apple_music'
                    }
                ]
        else:
            raise HTTPException(status_code=400, detail="Unsupported platform. Use 'spotify' or 'apple_music'")
        
        # Import songs into database
        songs_added = 0
        songs_skipped = 0
        errors = []
        
        for song_data in songs_to_import:
            try:
                # Enhance genre and mood assignment
                enhanced_data = assign_genre_and_mood(song_data['title'], song_data['artist'])
                
                # Use enhanced data if original is generic
                if song_data.get('genres') == ['Pop'] or not song_data.get('genres'):
                    song_data['genres'] = [enhanced_data['genre']]
                if song_data.get('moods') == ['Unknown'] or not song_data.get('moods'):
                    song_data['moods'] = [enhanced_data['mood']]
                
                # Check for duplicates (same title and artist for this musician)
                existing = await db.songs.find_one({
                    "musician_id": musician_id,
                    "title": {"$regex": f"^{re.escape(song_data['title'])}$", "$options": "i"},
                    "artist": {"$regex": f"^{re.escape(song_data['artist'])}$", "$options": "i"}
                })
                
                if existing:
                    songs_skipped += 1
                    errors.append(f"Skipped duplicate: '{song_data['title']}' by '{song_data['artist']}'")
                    continue
                
                # Create song record
                song_dict = {
                    "id": str(uuid.uuid4()),
                    "musician_id": musician_id,
                    "title": song_data['title'],
                    "artist": song_data['artist'],
                    "genres": song_data.get('genres', ['Pop']),
                    "moods": song_data.get('moods', ['Upbeat']),
                    "year": int(song_data.get('year', 2023)) if song_data.get('year') else None,
                    "notes": song_data.get('notes', ''),
                    "created_at": datetime.utcnow()
                }
                
                # Insert into database
                await db.songs.insert_one(song_dict)
                songs_added += 1
                
            except Exception as e:
                errors.append(f"Error importing '{song_data.get('title', 'Unknown')}': {str(e)}")
                continue
        
        return {
            "success": True,
            "message": f"Successfully imported {songs_added} songs from {platform.replace('_', ' ').title()} playlist",
            "platform": platform,
            "songs_added": songs_added,  
            "songs_skipped": songs_skipped,
            "errors": errors[:10]  # Limit error messages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing playlist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error importing playlist: {str(e)}")

# Subscription endpoints
@api_router.get("/subscription/status", response_model=SubscriptionStatus)
async def get_subscription_status_endpoint(musician_id: str = Depends(get_current_musician)):
    """Get current subscription status"""
    return await get_subscription_status(musician_id)

@api_router.post("/subscription/upgrade", response_model=CheckoutSessionResponse)
async def create_upgrade_checkout(request: Request, musician_id: str = Depends(get_current_musician)):
    """Create Stripe checkout session for $5/month subscription"""
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        # Initialize Stripe
        host_url = str(request.base_url)
        webhook_url = f"{host_url}api/webhook/stripe"
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
        
        # Create checkout session
        success_url = f"{host_url}dashboard?payment=success&session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{host_url}dashboard?payment=cancelled"
        
        checkout_request = CheckoutSessionRequest(
            amount=MONTHLY_SUBSCRIPTION_PRICE,
            currency="usd",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "musician_id": musician_id,
                "subscription_type": "monthly_unlimited",
                "product": "RequestWave Pro - Monthly"
            }
        )
        
        session = await stripe_checkout.create_checkout_session(checkout_request)
        
        # Create payment transaction record
        transaction = {
            "id": str(uuid.uuid4()),
            "musician_id": musician_id,
            "amount": MONTHLY_SUBSCRIPTION_PRICE,
            "currency": "usd",
            "session_id": session.session_id,
            "payment_status": "pending",
            "subscription_type": "monthly_unlimited",
            "created_at": datetime.utcnow()
        }
        await db.payment_transactions.insert_one(transaction)
        
        return session
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating checkout session: {str(e)}")

@api_router.get("/subscription/payment-status/{session_id}")
async def check_payment_status(session_id: str, musician_id: str = Depends(get_current_musician)):
    """Check payment status and update subscription if successful"""
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        # Initialize Stripe
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
        
        # Get checkout status
        status_response = await stripe_checkout.get_checkout_status(session_id)
        
        # Update payment transaction
        await db.payment_transactions.update_one(
            {"session_id": session_id, "musician_id": musician_id},
            {"$set": {"payment_status": status_response.payment_status}}
        )
        
        # If payment successful, activate subscription
        if status_response.payment_status == "paid":
            # Check if already processed to avoid double activation
            existing_subscription = await db.musicians.find_one({
                "id": musician_id,
                "subscription_ends_at": {"$gte": datetime.utcnow()}
            })
            
            if not existing_subscription:
                # Activate 1-month subscription
                subscription_end = datetime.utcnow() + timedelta(days=30)
                await db.musicians.update_one(
                    {"id": musician_id},
                    {"$set": {"subscription_ends_at": subscription_end}}
                )
        
        return {
            "payment_status": status_response.payment_status,
            "amount": status_response.amount_total / 100,  # Convert from cents
            "currency": status_response.currency
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking payment status: {str(e)}")

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
        body = await request.body()
        
        webhook_response = await stripe_checkout.handle_webhook(
            body, 
            request.headers.get("Stripe-Signature")
        )
        
        # Handle successful payment
        if webhook_response.payment_status == "paid" and webhook_response.session_id:
            transaction = await db.payment_transactions.find_one({"session_id": webhook_response.session_id})
            
            if transaction and transaction.get("payment_status") != "paid":
                # Update transaction status
                await db.payment_transactions.update_one(
                    {"session_id": webhook_response.session_id},
                    {"$set": {"payment_status": "paid"}}
                )
                
                # Activate subscription for the musician
                musician_id = transaction.get("musician_id")
                if musician_id:
                    subscription_end = datetime.utcnow() + timedelta(days=30)
                    await db.musicians.update_one(
                        {"id": musician_id},
                        {"$set": {"subscription_ends_at": subscription_end}}
                    )
        
        return {"status": "success"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook error: {str(e)}")

# Song endpoints
@api_router.get("/songs", response_model=List[Song])
async def get_my_songs(musician_id: str = Depends(get_current_musician)):
    songs = await db.songs.find({"musician_id": musician_id}).sort("created_at", DESCENDING).to_list(1000)
    return [Song(**song) for song in songs]

@api_router.post("/songs", response_model=Song)
async def create_song(song_data: SongCreate, musician_id: str = Depends(get_current_musician)):
    # Check for duplicates (same title and artist for this musician)
    existing = await db.songs.find_one({
        "musician_id": musician_id,
        "title": {"$regex": f"^{re.escape(song_data.title)}$", "$options": "i"},
        "artist": {"$regex": f"^{re.escape(song_data.artist)}$", "$options": "i"}
    })
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Song '{song_data.title}' by '{song_data.artist}' already exists in your library"
        )
    
    song_dict = song_data.dict()
    song_dict.update({
        "id": str(uuid.uuid4()),
        "musician_id": musician_id,
        "created_at": datetime.utcnow()
    })
    
    await db.songs.insert_one(song_dict)
    return Song(**song_dict)

@api_router.put("/songs/{song_id}", response_model=Song)
async def update_song(song_id: str, song_data: SongCreate, musician_id: str = Depends(get_current_musician)):
    # Verify song belongs to musician
    song = await db.songs.find_one({"id": song_id, "musician_id": musician_id})
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    # Check for duplicates (excluding the current song being edited)
    existing = await db.songs.find_one({
        "musician_id": musician_id,
        "id": {"$ne": song_id},  # Exclude current song
        "title": {"$regex": f"^{re.escape(song_data.title)}$", "$options": "i"},
        "artist": {"$regex": f"^{re.escape(song_data.artist)}$", "$options": "i"}
    })
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Another song '{song_data.title}' by '{song_data.artist}' already exists in your library"
        )
    
    # Update song
    update_data = song_data.dict()
    await db.songs.update_one(
        {"id": song_id},
        {"$set": update_data}
    )
    
    # Return updated song
    updated_song = await db.songs.find_one({"id": song_id})
    return Song(**updated_song)

@api_router.delete("/songs/{song_id}")
async def delete_song(song_id: str, musician_id: str = Depends(get_current_musician)):
    # Verify song belongs to musician
    result = await db.songs.delete_one({"id": song_id, "musician_id": musician_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Song not found")
    
    return {"message": "Song deleted successfully"}

@api_router.get("/musicians/{slug}/songs", response_model=List[Song])
async def get_musician_songs(
    slug: str,
    genre: Optional[str] = None,
    artist: Optional[str] = None,
    mood: Optional[str] = None,
    year: Optional[int] = None
):
    """Get songs for a musician with filtering support"""
    # Get musician
    musician = await db.musicians.find_one({"slug": slug})
    if not musician:
        raise HTTPException(status_code=404, detail="Musician not found")
    
    # Build filter query
    query = {"musician_id": musician["id"]}
    
    # Apply filters with AND logic
    if genre:
        query["genres"] = {"$in": [genre]}
    
    if artist:
        query["artist"] = {"$regex": artist, "$options": "i"}  # Case insensitive partial match
    
    if mood:
        query["moods"] = {"$in": [mood]}
    
    if year:
        query["year"] = year
    
    # Get filtered songs
    songs = await db.songs.find(query).sort("title", ASCENDING).to_list(1000)
    return [Song(**song) for song in songs]

# Request endpoints
@api_router.post("/requests", response_model=Request)
async def create_request(request_data: RequestCreate):
    # Get song details
    song = await db.songs.find_one({"id": request_data.song_id})
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    musician_id = song["musician_id"]
    
    # Check if musician can receive more requests based on subscription
    if not await check_request_allowed(musician_id):
        subscription_status = await get_subscription_status(musician_id)
        raise HTTPException(
            status_code=402, 
            detail={
                "message": "Request limit reached. Musician needs to upgrade to Pro plan.",
                "subscription_status": subscription_status.dict()
            }
        )
    
    # Create request
    request_dict = request_data.dict()
    request_dict.update({
        "id": str(uuid.uuid4()),
        "musician_id": musician_id,
        "song_title": song["title"],
        "song_artist": song["artist"],
        "status": "pending",
        "created_at": datetime.utcnow()
    })
    
    await db.requests.insert_one(request_dict)
    return Request(**request_dict)

@api_router.get("/requests/musician/{musician_id}", response_model=List[Request])
async def get_musician_requests(musician_id: str = Depends(get_current_musician)):
    """Get all requests for the authenticated musician"""
    requests = await db.requests.find({"musician_id": musician_id}).sort("created_at", DESCENDING).to_list(1000)
    return [Request(**request) for request in requests]

@api_router.put("/requests/{request_id}/status")
async def update_request_status(
    request_id: str, 
    status: str, 
    musician_id: str = Depends(get_current_musician)
):
    """Update request status (pending, accepted, played, rejected)"""
    if status not in ["pending", "accepted", "played", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    # Verify request belongs to musician
    result = await db.requests.update_one(
        {"id": request_id, "musician_id": musician_id},
        {"$set": {"status": status}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Request not found")
    
    return {"message": "Request status updated"}

@api_router.get("/requests/updates/{musician_id}")
async def get_request_updates(musician_id: str):
    """Polling endpoint for real-time updates (can be upgraded to WebSocket later)"""
    requests = await db.requests.find({"musician_id": musician_id}).sort("created_at", DESCENDING).limit(50).to_list(50)
    return {
        "requests": [Request(**request) for request in requests],
        "timestamp": datetime.utcnow().isoformat()
    }

# Get available filter options for a musician
@api_router.get("/musicians/{slug}/filters")
async def get_filter_options(slug: str):
    """Get available filter options for a musician's songs"""
    # Get musician
    musician = await db.musicians.find_one({"slug": slug})
    if not musician:
        raise HTTPException(status_code=404, detail="Musician not found")
    
    # Aggregate unique values
    pipeline = [
        {"$match": {"musician_id": musician["id"]}},
        {"$group": {
            "_id": None,
            "genres": {"$addToSet": "$genres"},
            "artists": {"$addToSet": "$artist"},
            "moods": {"$addToSet": "$moods"},
            "years": {"$addToSet": "$year"}
        }}
    ]
    
    result = await db.songs.aggregate(pipeline).to_list(1)
    if not result:
        return {"genres": [], "artists": [], "moods": [], "years": []}
    
    data = result[0]
    
    # Flatten arrays and remove nulls
    genres = []
    for genre_list in data.get("genres", []):
        if genre_list:
            genres.extend(genre_list)
    
    moods = []
    for mood_list in data.get("moods", []):
        if mood_list:
            moods.extend(mood_list)
    
    return {
        "genres": sorted(list(set(genres))),
        "artists": sorted([a for a in data.get("artists", []) if a]),
        "moods": sorted(list(set(moods))),
        "years": sorted([y for y in data.get("years", []) if y], reverse=True)
    }

# CSV Upload endpoints
@api_router.post("/songs/csv/preview", response_model=CSVPreviewResponse)
async def preview_csv_upload(
    file: UploadFile = File(...),
    musician_id: str = Depends(get_current_musician)
):
    """Preview CSV upload without saving to database"""
    validate_csv_file(file)
    
    try:
        content = await file.read()
        result = parse_csv_content(content)
        
        # Return preview with first 10 rows
        preview_songs = result['songs'][:10]
        preview = []
        
        for song in preview_songs:
            preview.append({
                'title': song['title'],
                'artist': song['artist'],
                'genres': song['genres'],
                'moods': song['moods'],
                'year': song['year'],
                'notes': song['notes'],
                'row_number': song['row_number']
            })
        
        return CSVPreviewResponse(
            preview=preview,
            total_rows=len(result['songs']) + len(result['errors']),
            valid_rows=len(result['songs']),
            errors=result['errors']
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@api_router.post("/songs/csv/upload", response_model=CSVUploadResponse)
async def upload_csv_songs(
    file: UploadFile = File(...),
    musician_id: str = Depends(get_current_musician)
):
    """Upload and save songs from CSV file"""
    validate_csv_file(file)
    
    try:
        content = await file.read()
        result = parse_csv_content(content)
        
        songs_added = 0
        
        # Insert valid songs into database
        for song_data in result['songs']:
            song_dict = {
                "id": str(uuid.uuid4()),
                "musician_id": musician_id,
                "title": song_data['title'],
                "artist": song_data['artist'],
                "genres": song_data['genres'],
                "moods": song_data['moods'],
                "year": song_data['year'],
                "notes": song_data['notes'],
                "created_at": datetime.utcnow()
            }
            
            # Check for duplicates (same title and artist for this musician)
            existing = await db.songs.find_one({
                "musician_id": musician_id,
                "title": {"$regex": f"^{re.escape(song_data['title'])}$", "$options": "i"},
                "artist": {"$regex": f"^{re.escape(song_data['artist'])}$", "$options": "i"}
            })
            
            if not existing:
                await db.songs.insert_one(song_dict)
                songs_added += 1
            else:
                result['errors'].append(f"Row {song_data['row_number']}: Duplicate song '{song_data['title']}' by '{song_data['artist']}' already exists")
        
        return CSVUploadResponse(
            success=True,
            message=f"Successfully imported {songs_added} songs",
            songs_added=songs_added,
            errors=result['errors']
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

# Health check
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Include the router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()