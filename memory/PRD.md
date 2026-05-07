# RequestWave - Product Requirements Document

## Original Problem Statement
RequestWave is a live music request platform enabling musicians to manage song requests, shows, and audience tipping during performances.

## Architecture
- **Backend**: FastAPI (monolithic `server.py`) with MongoDB
- **Frontend**: React (monolithic `App.js`) with Tailwind CSS
- **Database**: MongoDB with collections: musicians, songs, requests, shows, playlists, profiles, analytics_events

## Sprint 1: Multi-Profile System (Complete)

### Phase 1 (Initial Build)
- Profile CRUD (POST/GET/PUT/DELETE /api/profiles) with slug validation
- Public profile resolution (GET /api/musicians/{master_slug}/{profile_slug})
- Slug resolver for short URLs (GET /api/resolve/{slug})
- Profile-scoped songs (active_playlist_ids)
- Tip visibility toggles per profile
- Request profile tracking (profile_id on requests)
- Short URL redirects (/:slug -> /musician/:slug)
- 404 page for unknown slugs
- Profiles tab with card list, editor modal, collapsible Account Settings

### Phase 2 (Fixes & Additions)
- **Bug fixes**: Copy URL button (e.currentTarget), clickable profile URLs, "__all__" sentinel for All Songs
- **Profile override fields**: paypal_username, venmo_username, cashapp_username, zelle_info, instagram_username, tiktok_username, facebook_url, spotify_url, apple_music_url, website, bio, musician_name
- **is_default**: First profile auto-default, cannot delete default, Set Default button
- **Default profile resolution**: /musician/{slug} resolves to default profile (merged data + songs)
- **Account Settings slimmed**: Only stage name, email, slug (social/tip/bio moved to profiles)

### Data Model: profiles collection
```
id: str (uuid)
musician_id: str
name: str
slug: str (lowercase letters, numbers, hyphens)
active_playlist_ids: List[str] ("__all__" = full library)
show_tips_in_success_screen: bool
show_tips_in_orientation: bool
is_default: bool
paypal_username, venmo_username, cashapp_username, zelle_info: Optional[str]
instagram_username, tiktok_username, facebook_url, spotify_url, apple_music_url: Optional[str]
website, bio, musician_name: Optional[str]
created_at: datetime
```

### Override Logic
Profile fields override master account values when set (non-null/non-empty). Falls back to master when blank.

### Constraints Maintained
- /musician/{slug}: ZERO breaking changes (resolves default profile when exists)
- OnStage, shows, billing, analytics, song library, CSV: UNTOUCHED

## Test Coverage
- /app/backend/tests/test_multi_profile_system.py (20 tests)
- /app/backend/tests/test_sprint1_profile_features.py (16 tests)
- /app/test_reports/iteration_2.json, iteration_3.json

## Upcoming Tasks
- Analytics: Tip conversion analytics
- Mailing list: Capture feature
- Post-Show Reflection features

## Technical Debt
- App.js ~12800 lines, server.py ~7800 lines (monolithic)
