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
- **Unique-show popularity ranking**: Replaced raw `request_count` as the popularity signal with a "distinct non-archived shows requested in" count. New shared backend helper `get_unique_show_counts(musician_id, song_ids)` uses a single `$match` (`status != archived`, `song_id ∈ list`) + `$group` `$addToSet` of `show_id` + `$size`. `unique_show_count` is now attached to each song on `GET /api/songs` (and used as the in-memory sort key when `sort_by=popularity`) and on the public `GET /api/musicians/{slug}/songs`. `GET /api/analytics/daily` top_songs is ranked by this metric (limit raised 10→50 to support Top 50 dropdown). Frontend Songs tab and Audience sorts use `unique_show_count`. Analytics Most Requested Songs renders titles only (no badge), data-testid `most-requested-songs-list`. `request_count` and `requests_this_show` semantics are unchanged.
- **Requests tab: per-profile live banners + On-Stage-aware Start a Show**: The Requests tab live banner now renders one banner per profile that has an active show (format: "🎤 Live: &lt;profile&gt; (&lt;show&gt;)") with its own "Stop Show" button scoped to that profile (`POST /api/shows/stop {profile_id}`). Zero banners when no profile is live (Start a Show button shown instead). New helper `handleStopShowForProfile(profileId, showName)` added. The existing `handleStartShow` already inherits the On-Stage selector's profile/event context for `POST /api/shows/start`; backend falls back to default profile when neither is sent. `data-testid`s: `start-a-show-btn`, `live-shows-banners`, `live-show-banner-<profile_id>`, `stop-show-btn-<profile_id>`.
- **Show-scoped per-song request badge**: Added transient `requests_this_show: int` to the `Song` Pydantic model (not persisted). `GET /api/songs` and `GET /api/musicians/{slug}/songs` now resolve the active show via the default profile's `current_show_id` and aggregate `db.requests` by `{musician_id, show_id, song_id ∈ catalog}` to attach a per-song count. When there is no active show, all songs return `requests_this_show=0`. `request_count` (all-time) is unchanged. Frontend Songs tab badge replaced from "🔥 N requests" to "🔥 N tonight" rendered only when N>0. Same conditional badge added to the Audience song list. `data-testid`s: `song-tonight-badge-<id>` and `audience-song-tonight-badge-<id>`.
- **Analytics → Most Active Requesters filter**: `GET /api/analytics/requesters` and `GET /api/analytics/export-requesters` accept optional `profile_id` and `event_id` query params (added to `$match`). Both endpoints now consistently exclude archived requests.
- Frontend Analytics tab: Most Active Requesters section has a filter dropdown ("All Profiles" / per-profile / per-event) that re-fetches and re-renders the list. Export CSV button label switches to "Export filtered list" when a filter is active and includes the filter in the export URL. Filename suffix on the server (`requesters-profile-<id8>-YYYYMMDD.csv` or `requesters-event-<id8>-YYYYMMDD.csv`) reflects the filter.

- **Email List Export by Show**: `GET /api/analytics/export-requesters` accepts `show_id` query param; CSV restricted to 3 columns (`name`, `email`, `show_name`) with basic regex email validation. Frontend Analytics tab Export panel adds a Show selector dropdown (`export-show-select`) that scopes the email-list CSV to a single show. Filename suffix `-show-<id8>` when the show filter is active.
- **Show Analytics Dashboard (Feb 16, 2026)**: Two new endpoints + UI section in the Analytics tab, both profile-scoped.
  - `GET /api/analytics/show-detail?show_id=<id>` returns `{show, metrics:{total_requests, requests_with_email, email_capture_rate, total_tip_revenue, tip_count, click_through_rate, requests_with_click}, top_songs[<=5], top_tippers[<=5], repeat_requesters[]}`. Tip revenue aggregated from `db.tips` (not `request.tip_amount`) to avoid double counting. CTR counts requests where `tip_clicked=true OR social_clicks` non-empty. Repeat requesters compares emails in the selected show against other shows in the same profile (`shows_count >= 2`).
  - `GET /api/analytics/show-trends?profile_id=<id>&limit=5|10|20` returns last N shows for the profile in chronological order with per-show `total_requests, email_capture_count, tip_revenue, click_through_rate`. Invalid `limit` coerces to 5. Unknown profile returns `{shows:[]}` with 200.
  - Frontend: new `Show Analytics` section under existing Analytics charts with view toggle (Show Detail / Show Trends), profile selector (defaults to is_default profile), show selector scoped to profile, and 5/10/20 N selector for trends. Trends view renders two `recharts` charts: `ComposedChart` dual-axis (bar = email captures, line = tip revenue) + `LineChart` for CTR % (0-100 domain). `data-testid`s: `show-analytics-dashboard`, `show-analytics-view-detail`, `show-analytics-view-trends`, `show-analytics-profile-select`, `show-analytics-show-select`, `show-analytics-trends-limit`, `metric-email-capture`, `metric-tip-revenue`, `metric-click-through`, `metric-total-requests`, `show-top-songs`, `show-top-tippers`, `show-repeat-requesters`, `trend-graph-email-tips`, `trend-graph-ctr`. Dependency added: `recharts` (yarn).

## Upcoming Tasks
- Tip conversion analytics
- Post-Show Reflection features
- Spotify Web API enrichment
- Analytics UI for `analytics_events` collection

## Backlog (Deferred per user)
- Refactor monolithic `App.js` (13.9k lines) and `server.py` (8.9k lines)
