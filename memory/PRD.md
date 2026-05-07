# RequestWave - Product Requirements Document

## Original Problem Statement
RequestWave is a live music request platform enabling musicians to manage song requests, shows, and audience tipping during performances.

## Architecture
- **Backend**: FastAPI (monolithic `server.py`) with MongoDB
- **Frontend**: React (monolithic `App.js`) with Tailwind CSS
- **Database**: MongoDB collections: musicians, songs, requests, shows, playlists, profiles, analytics_events

## Sprint 1: Multi-Profile System (Complete)

### Phase 1 (Initial Build)
- Profile CRUD (POST/GET/PUT/DELETE /api/profiles) with slug validation
- Public profile resolution (GET /api/musicians/{master_slug}/{profile_slug})
- Slug resolver for short URLs (GET /api/resolve/{slug})
- Profile-scoped songs via active_playlist_ids ("__all__" = full library)
- Tip visibility toggles per profile
- Request profile tracking (profile_id on requests)
- Short URL redirects (/:slug -> /musician/:slug)
- 404 page for unknown slugs
- Profiles tab with card list, editor modal, collapsible Account Settings

### Phase 2 (Fixes & Additions)
- Profile override fields: paypal_username, venmo_username, cashapp_username, zelle_info, instagram_username, tiktok_username, facebook_url, spotify_url, apple_music_url, website, bio, musician_name
- is_default: first profile auto-default, cannot delete default, Set Default button
- Default profile resolution: /musician/{slug} resolves to default profile
- Account Settings slimmed to: stage name, email, slug

### Phase 3 (Bug Fixes - Current)
- Removed Master Audience Link section (redundant with default profile card)
- Fixed profile card buttons: Delete + Set Default visible on non-default cards on their own row
- Fixed profile overrides: chained fetchDesignSettings then fetchProfileData to prevent race condition
- New profile form fields start empty (active_playlist_ids defaults to __all__)
- Added "Copy from Account Settings" button in profile editor

### Profile Override Logic
Profile fields override master account values when set (non-null, non-empty). Falls back to master when blank. Frontend chains design settings fetch before profile data fetch to prevent race conditions.

### Data Model: profiles collection
```
id, musician_id, name, slug, active_playlist_ids, 
show_tips_in_success_screen, show_tips_in_orientation, is_default,
paypal_username, venmo_username, cashapp_username, zelle_info,
instagram_username, tiktok_username, facebook_url, spotify_url, apple_music_url,
website, bio, musician_name, created_at
```

## Test Reports
- /app/test_reports/iteration_2.json (Phase 1)
- /app/test_reports/iteration_3.json (Phase 2)
- /app/test_reports/iteration_4.json (Phase 3 fixes)

## Upcoming Tasks
- Analytics: Tip conversion analytics
- Mailing list: Capture feature
- Post-Show Reflection features
