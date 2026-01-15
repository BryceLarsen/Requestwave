# RequestWave PRD

## Original Problem Statement
Live music request platform enabling musicians to receive song requests from audiences during performances, with features for managing requests, suggestions, tips, and analytics.

## Current State (as of January 15, 2026)

### Completed Features

#### Core Features
- ✅ CSV export with genre, mood, playlists, and year metadata
- ✅ Unified On Stage timeline (requests + suggestions)
- ✅ Suggestion actions (Match to Song, Learn it later, Skip)
- ✅ Restore functionality for all handled items
- ✅ `show_id` as primary identifier everywhere
- ✅ Auto-show creation for requests AND suggestions
- ✅ UX cleanup for destructive actions (no redundant popups)

#### Analytics Event System (Complete)
- ✅ `analytics_events` collection (append-only ledger)
- ✅ `AnalyticsEvent` model with schema_version
- ✅ `emit_analytics_event()` helper (non-blocking, 200ms timeout)
- ✅ `ANALYTICS_EVENTS_ENABLED` feature flag

**Implemented Events:**
- `audience.request_submitted` - when audience submits request
- `audience.suggestion_submitted` - when audience submits suggestion
- `musician.request_played` - when musician marks request as played
- `musician.request_skipped` - when musician rejects request
- `musician.request_restored` - when musician restores request
- `musician.suggestion_matched` - when suggestion matched to song
- `musician.suggestion_learn_later` - when suggestion marked learn later
- `musician.suggestion_skipped` - when suggestion rejected
- `musician.suggestion_restored` - when suggestion restored
- `musician.show_started` - when musician starts a show
- `musician.show_stopped` - when musician stops a show
- `musician.show_archived` - when musician archives a show
- `system.auto_show_created` - when system auto-creates show

#### Show-Scoped Architecture (Latest - January 15, 2026)
- ✅ Suggestions now have `show_id` and `show_name` fields
- ✅ Suggestions auto-create shows when no active show exists
- ✅ Requests tab displays shows with both Requests and Suggestions sections
- ✅ Batch selection and actions for suggestions within shows
- ✅ Legacy suggestions (without show_id) shown in "Unassigned Suggestions" section
- ✅ Learn Later toggle on Songs tab showing learn_later suggestions
- ✅ Restore archived shows without success popup

### Architecture

#### Backend: `/app/backend/server.py`
- SongSuggestion model includes `show_id` and `show_name`
- Auto-show creation in suggestion submission endpoint
- Analytics events for all suggestion and show lifecycle actions

#### Frontend: `/app/frontend/src/App.js`
- Show tiles display "(X requests, Y suggestions)" counts
- Collapsible Requests and Suggestions sections within each show
- Batch actions: Learn Later, Skip, Trash for suggestions
- Learn Later view on Songs tab with Match, Add, Restore, Delete actions

## Key API Endpoints
- `/api/requests` - Create request
- `/api/musicians/{slug}/requests` - Audience request submission
- `/api/requests/{id}/status` - Update request status
- `/api/song-suggestions` - Create suggestion (with auto-show)
- `/api/song-suggestions/{id}/status` - Update suggestion status
- `/api/song-suggestions/{id}/match` - Match suggestion to song
- `/api/song-suggestions/{id}/learn-later` - Mark as learn later
- `/api/shows/start` - Start show
- `/api/shows/stop` - Stop show
- `/api/shows/{id}/archive` - Archive show
- `/api/shows/{id}/restore` - Restore show

## Known Edge Cases
1. Legacy suggestions without show_id appear in "Unassigned Suggestions"
2. Archived shows don't show suggestions count in summary
3. "Song Suggestions" button at top still exists for backwards compatibility

## Upcoming Tasks (Backlog)
- Build analytics UI powered by `analytics_events`
- Spotify Web API integration for playlist enrichment
- Show rename functionality
- Frontend refactoring (App.js is ~12,000+ lines)

## Technical Debt
- `/app/frontend/src/App.js` is monolithic (~12,000+ lines)
- Refactoring into modular components required before scaling

## Environment
- Preview URL: https://songsync-10.preview.emergentagent.com
- Backend: FastAPI (Python)
- Frontend: React
- Database: MongoDB
