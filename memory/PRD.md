# RequestWave - Product Requirements Document

## Original Problem Statement
RequestWave is a live music request platform enabling musicians to manage song requests, shows, and audience tipping during performances.

## Architecture
- **Backend**: FastAPI (monolithic `server.py`) with MongoDB
- **Frontend**: React (monolithic `App.js`) with Tailwind CSS
- **Database**: MongoDB with collections: musicians, songs, requests, shows, playlists, profiles, analytics_events
- **Deployment**: Kubernetes container environment

## Core Features (Implemented)
- Musician registration/login with JWT auth
- Song library management (CRUD, CSV import/export with pipe-delimited playlists)
- Playlist management (create, assign songs, filter)
- Show management (start/stop shows, request grouping)
- Audience interface (public URL, song browsing, request submission)
- Tipping system (Venmo, PayPal, Cash App, Zelle deep links)
- QR code generation for audience links
- Analytics events tracking
- Design customization (color schemes, layouts)
- Subscription/billing system (disabled in free mode)

## Sprint 1: Multi-Profile System (Completed 2026-05-06)
### What Was Built
- **Profiles collection**: Musicians can create multiple named performance profiles
- **Profile CRUD API**: POST/GET/PUT/DELETE /api/profiles with slug validation
- **Public profile resolution**: GET /api/musicians/{master_slug}/{profile_slug}
- **Profile-scoped songs**: Only songs from active playlists shown in profile audience page
- **Tip visibility toggles**: Per-profile control over tip prompts (success screen + orientation)
- **Request profile tracking**: profile_slug passed on request submission, stored as profile_id
- **Short URL redirects**: Catch-all routes resolve vanity URLs (/:slug -> /musician/:slug)
- **404 page**: Clean 404 for unknown slugs
- **Profiles tab UI**: Profile list with cards, editor modal, collapsible account settings
- **Profile filter in requests tab**: Filter requests by profile

### Constraints Maintained
- /musician/{slug} existing route: ZERO breaking changes
- OnStage, shows, billing, analytics, song library, CSV: UNTOUCHED

## Upcoming Tasks
- Documentation: current_build_inventory.yaml updated
- Analytics: Tip conversion analytics
- Mailing list: Capture feature
- Post-Show Reflection features

## Technical Debt
- App.js is ~12800 lines (monolithic)
- server.py is ~7800 lines (monolithic)
- Both should eventually be decomposed into modules

## Key Endpoints
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/profiles | Yes | Create profile |
| GET | /api/profiles | Yes | List musician profiles |
| PUT | /api/profiles/{id} | Yes | Update profile |
| DELETE | /api/profiles/{id} | Yes | Delete profile (not last) |
| GET | /api/musicians/{master}/{profile} | No | Public profile resolution |
| GET | /api/resolve/{slug} | No | Slug lookup for short URLs |
| POST | /api/requests | No | Submit request (accepts profile_slug) |

## Test Coverage
- Backend: 20 tests in /app/backend/tests/test_multi_profile_system.py (all passing)
- Test report: /app/test_reports/iteration_2.json
