# RequestWave - Product Requirements Document

## Original Problem Statement
RequestWave is a live music request platform enabling musicians to manage song requests, shows, and audience tipping during performances.

## Architecture
- **Backend**: FastAPI (monolithic `server.py`) with MongoDB
- **Frontend**: React (monolithic `App.js`) with Tailwind CSS
- **Database**: MongoDB collections: musicians, songs, requests, shows, playlists, profiles, analytics_events

## Sprint 2: Per-Profile Shows (In Progress)

### Architecture
- `current_show_id` / `current_show_name` moved from `musicians` doc to **`profiles`** doc — each profile can have its own active show simultaneously.
- `shows` documents gain `profile_id` so they're owned by a specific profile.
- Auto-show creation (no active show → create one) now operates per-profile with an **optimistic null-guard lock** (`update_one({"id": profile_id, "current_show_id": None}, {...})`) to prevent races.
- One-time startup migration copies `musician.current_show_id/name` → default profile, nulls musician fields. Idempotent.
- Backward-compat: top-level `current_show_id`/`current_show_name` on `/api/profile` and `/api/shows/start|stop` responses still populated, sourced from default profile. Frontend untouched.
- `POST /api/shows/start` and `POST /api/shows/stop` accept optional `profile_id` body field; default to musician's default profile.
- `GET /api/shows/current?profile_id=` query param for per-profile lookup.
- `DELETE`/`archive` of a show now clears `current_show_id` on **all** profiles whose value matches.
- Verified: starting a show on profile A leaves profile B with no active show; starting a show on profile B then yields two independent active shows simultaneously.

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
current_show_id, current_show_name,  # Sprint 2: per-profile active show
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
- **Account Settings**: Email and master slug are editable with inline Save buttons (PUT `/api/account/email`, PUT `/api/account/slug`); password change inline
- **Design tab**: Removed (merged into profile editor)
- **AudienceInterface**: Uses profile design_settings when available. Song display is always list layout (Grid/List toggle removed Feb 2026).
- **Short URL redirects**: /:slug -> /musician/:slug, /:seg1/:seg2 -> /musician/:seg1/:seg2

### is_default Profile
- First profile auto-set as default
- Cannot be deleted
- /musician/{slug} master URL resolves to default profile
- "Copy from Default Profile" button in editor copies from default profile

## Test Reports
- /app/test_reports/iteration_2.json through iteration_6.json

## Recent Changes (Feb 2026)
- **Requests tab: per-profile live banners + On-Stage-aware Start a Show**: The Requests tab live banner now renders one banner per profile that has an active show (format: "🎤 Live: &lt;profile&gt; (&lt;show&gt;)") with its own "Stop Show" button scoped to that profile (`POST /api/shows/stop {profile_id}`). Zero banners when no profile is live (Start a Show button shown instead). New helper `handleStopShowForProfile(profileId, showName)` added. The existing `handleStartShow` already inherits the On-Stage selector's profile/event context for `POST /api/shows/start`; backend falls back to default profile when neither is sent. `data-testid`s: `start-a-show-btn`, `live-shows-banners`, `live-show-banner-<profile_id>`, `stop-show-btn-<profile_id>`.
- **Show-scoped per-song request badge**: Added transient `requests_this_show: int` to the `Song` Pydantic model (not persisted). `GET /api/songs` and `GET /api/musicians/{slug}/songs` now resolve the active show via the default profile's `current_show_id` and aggregate `db.requests` by `{musician_id, show_id, song_id ∈ catalog}` to attach a per-song count. When there is no active show, all songs return `requests_this_show=0`. `request_count` (all-time) is unchanged. Frontend Songs tab badge replaced from "🔥 N requests" to "🔥 N tonight" rendered only when N>0. Same conditional badge added to the Audience song list. `data-testid`s: `song-tonight-badge-<id>` and `audience-song-tonight-badge-<id>`.
- **Analytics → Most Active Requesters filter**: `GET /api/analytics/requesters` and `GET /api/analytics/export-requesters` accept optional `profile_id` and `event_id` query params (added to `$match`). Both endpoints now consistently exclude archived requests.
- Frontend Analytics tab: Most Active Requesters section has a filter dropdown ("All Profiles" / per-profile / per-event) that re-fetches and re-renders the list. Export CSV button label switches to "Export filtered list" when a filter is active and includes the filter in the export URL. Filename suffix on the server (`requesters-profile-<id8>-YYYYMMDD.csv` or `requesters-event-<id8>-YYYYMMDD.csv`) reflects the filter.

## Upcoming Tasks
- Tip conversion analytics
- Post-Show Reflection features
- Spotify Web API enrichment
- Analytics UI for `analytics_events` collection

## Backlog (Deferred per user)
- Refactor monolithic `App.js` (13.7k lines) and `server.py` (8.5k lines)
