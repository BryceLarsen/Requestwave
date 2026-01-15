# RequestWave PRD

## Original Problem Statement
Live music request platform enabling musicians to receive song requests from audiences during performances, with features for managing requests, suggestions, tips, and analytics.

## Current State (as of January 15, 2026)

### Completed Features
- ✅ CSV export with genre, mood, playlists, and year metadata
- ✅ Unified On Stage timeline (requests + suggestions)
- ✅ Suggestion actions (Match to Song, Learn it later, Skip)
- ✅ Restore functionality for all handled items
- ✅ `show_id` as primary identifier everywhere
- ✅ Auto-show creation when no active show exists
- ✅ UX cleanup for destructive actions
- ✅ **Analytics Event System** - Phase 1 complete
  - `analytics_events` collection created
  - `AnalyticsEvent` model defined
  - `emit_analytics_event()` helper (non-blocking, 200ms timeout)
  - `ANALYTICS_EVENTS_ENABLED` feature flag (default: true)
  - `audience.request_submitted` event emitting from both endpoints

### Analytics Event System Details
**Collection**: `analytics_events`
**Model Fields**:
- id (uuid)
- event_type (string)
- musician_id (string)
- show_id (optional string)
- entity_id (optional string)
- entity_type (optional string)
- metadata (dict)
- requester_email (normalized - lower().strip())
- timestamp (UTC datetime)

**Current Events**:
- `audience.request_submitted` - Emitted when audience submits a song request

**Guardrails**:
- Append-only (never update/delete)
- Non-blocking (200ms timeout)
- Silent failures (logs only, never throws)

## Upcoming Tasks (P0)

### Analytics Event System - Remaining Events
After user approval, add these events:
- `audience.suggestion_submitted`
- `musician.request_played`
- `musician.request_skipped`
- `musician.suggestion_matched`
- `musician.suggestion_learn_later`
- `musician.show_started`
- `musician.show_stopped`

## Future Tasks (Backlog)
- Build analytics UI powered by `analytics_events`
- Spotify Web API integration for playlist enrichment
- Show rename functionality
- Frontend refactoring (App.js is ~11,000+ lines)

## Technical Debt
- `/app/frontend/src/App.js` is monolithic (~11,000+ lines)
- Refactoring into modular components required before scaling

## Key API Endpoints
- `/api/requests` - Create request
- `/api/musicians/{slug}/requests` - Audience request submission
- `/api/requests/{id}/status` - Update request status
- `/api/song-suggestions` - Suggestions CRUD
- `/api/song-suggestions/{id}/match` - Match suggestion to song
- `/api/shows/start` - Start show
- `/api/shows/stop` - Stop show
- `/api/shows/{id}/archive` - Archive show

## Environment
- Preview URL: https://songsync-10.preview.emergentagent.com
- Backend: FastAPI (Python)
- Frontend: React
- Database: MongoDB
