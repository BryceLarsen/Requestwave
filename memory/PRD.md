# RequestWave - Product Requirements Document

## Original Problem Statement
RequestWave is a live music request platform enabling musicians to manage song requests, shows, and audience tipping during performances.

## Architecture
- **Backend**: FastAPI (monolithic `server.py`) with MongoDB
- **Frontend**: React (monolithic `App.js`) with Tailwind CSS
- **Database**: MongoDB collections: musicians, songs, requests, shows, playlists, profiles, analytics_events

## Sprint 1: Multi-Profile System (Complete)

### Core Feature
Musicians can create multiple performance profiles. Each profile has its own audience URL, active playlists, tip visibility, payment/social overrides, and design settings.

### Profile Data Model
```
id, musician_id, name, slug, active_playlist_ids ("__all__" = full library),
show_tips_in_success_screen, show_tips_in_orientation, is_default,
paypal_username, venmo_username, cashapp_username, zelle_info,
instagram_username, tiktok_username, facebook_url, spotify_url, apple_music_url,
website, bio, musician_name,
design_color_scheme, design_artist_photo, design_show_year, design_show_notes,
created_at
```

### Override Logic
Profile fields override master account values when set. Falls back to master when blank/null. Design settings override global design_settings document.

### Key Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST/GET/PUT/DELETE | /api/profiles | Profile CRUD |
| GET | /api/musicians/{master}/{profile} | Public profile resolution with merged data + design_settings |
| GET | /api/musicians/{slug}/design | Returns default profile design or global fallback |
| GET | /api/resolve/{slug} | Slug lookup for short URL redirects |

### Frontend Structure
- **Profiles tab**: Profile list cards (with Copy URL, QR, Edit, Set Default, Delete), profile editor modal
- **Profile editor**: Name, slug, display name, bio, website, playlists, tip toggles, tip platform overrides, social link overrides, Design Settings (color theme, photo, display options)
- **Account Settings**: Email, slug, password change only
- **Design tab**: Removed (merged into profile editor)
- **AudienceInterface**: Uses profile design_settings when available. Song display is always list layout (Grid/List toggle removed Feb 2026).
- **Short URL redirects**: /:slug -> /musician/:slug, /:seg1/:seg2 -> /musician/:seg1/:seg2

### is_default Profile
- First profile auto-set as default
- Cannot be deleted
- /musician/{slug} master URL resolves to default profile
- "Copy from Default Profile" button in editor copies from default profile

## Test Reports
- /app/test_reports/iteration_2.json through iteration_5.json

## Upcoming Tasks
- Tip conversion analytics
- Mailing list capture feature
- Post-Show Reflection features
