# RequestWave PRD

## Original Problem Statement
Live music request platform enabling musicians to receive song requests from audiences during performances, with features for managing requests, suggestions, tips, and analytics.

## Current State (as of January 22, 2026)

### Phase Status
- **Phase 1: Foundation and Correctness** - COMPLETE (Signed off 2026-01-16)
- **Phase 2: Audience Interaction Capture** - COMPLETE (Signed off 2026-01-16)
- **Audience Moment Model Refactor** - COMPLETE (Signed off 2026-01-21)
- **Moment 0/1A UI Polish** - COMPLETE (2026-01-22)
- **Send Tip → Orientation Support Mode** - COMPLETE (2026-01-22)
- **Phase 3: Post-Show Reflection** - NOT STARTED (Deferred)

### Completed Features

#### Orientation Tip CTA Button (January 22, 2026)
Replaced subtle collapsible tip card with prominent full-width CTA button:

- ✅ **Full-width CTA button**: Light teal background (`bg-teal-500/90`), distinct from Spotify green
- ✅ **Big text**: "Leave a tip" (text-lg, font-bold)
- ✅ **Small text**: "(totally optional)" in lighter teal below
- ✅ **Toggle behavior**: Tap expands/collapses inline tip form in place
- ✅ **Works in both modes**: default (via "About") and post_request (after song request)
- ✅ **Empty payment guard**: CTA hidden when no payment methods configured (P2)
- ✅ **Expanded state**: Amount input, $3/$5/$10, payment selector, dynamic CTA button
- ✅ **Dynamic CTA labels**: "Open Venmo", "Open PayPal", "Show Zelle info"
- ✅ **PayPal fallback link**: "Having trouble? Open in browser" when PayPal selected
- ✅ **PayPal URL sanitization**: Removes leading @ from username, uses window.location.assign
- ✅ **Bio expandable**: Read more/Show less toggle with smooth transition

#### Runtime Error Fix (January 22, 2026)
- ✅ Fixed JSX syntax error caused by orphaned duplicate code block
- ✅ Removed orphaned lines 11073-11125 (duplicate select/button elements)

#### Moment 0/1A UI Polish (January 22, 2026)
The audience landing page has been polished for improved clarity and information density:

- ✅ **Header Helper Line (Split Layout)**: "About · Tip · Follow" on left, glowing "Live Now: {show_name}" on right
- ✅ **Live Now Glow Effect**: Subtle animated text-shadow pulse on green Live Now indicator (2.5s cycle)
- ✅ **Song Card Single-Line Format**: "Song Title · Artist Name" on one line for better density
- ✅ **Reduced Card Padding**: py-3 px-4 (down from p-4 md:p-5) for more songs per viewport
- ✅ **CSS Animations**: Added `animate-live-glow` keyframes to App.css
- ✅ **Documentation**: `current_build_inventory.yaml` updated with as-built behavior

#### Audience Moment Model Refactor (January 21, 2026)
The frontend has been refactored to align with the "Audience Moment Model" - an intent-based framework governing the audience user experience:

- ✅ **Moment 1A (Browse)**: Landing view shows "Tap a song to request it" with tappable song cards
- ✅ **Moment 1B (Commit)**: Song confirmation step with Continue/Back buttons
- ✅ **Moment 2 (Identity)**: Name (required) + Dedication (optional) - NO email in this step
- ✅ **Moment 3 (Follow-up)**: Optional email capture shown AFTER request submission, fully skippable
- ✅ **New Endpoint**: `POST /api/requests/{request_id}/email` - Attaches email to existing request
- ✅ **New Analytics Event**: `audience.email_submitted` - Logged when email provided (email_provided: true)
- ✅ **Security**: audience_id validation on email endpoint prevents unauthorized updates
- ✅ **Backend Tests**: `/app/backend/tests/test_moment3_email_endpoint.py` (5 tests passing)
- ✅ **Documentation**: `current_build_inventory.yaml` updated with endpoint and gap resolution

#### Phase 2: Audience Interaction Capture (Latest - January 16, 2026)
- ✅ **Anonymous audience_id**: Client-side UUID generation, persisted in localStorage
- ✅ **audience_id stored**: Included in request and tip documents
- ✅ **4 new analytics events** with correct context (musician_id, show_id, audience_id):
  - `audience.dedication_submitted` (conditional on non-empty dedication)
  - `audience.tip_clicked` (when tip payment link clicked)
  - `audience.follow_clicked` (when social follow link clicked)
  - `audience.tip_completed` (when tip record submitted)
- ✅ **Backend models updated**: RequestCreate, TipCreate accept audience_id
- ✅ **Documentation updated**: current_build_inventory.yaml, requestwave_combined_planning.yaml

#### Phase 1: Foundation and Correctness (Completed January 16, 2026)
- ✅ **Analytics Period Filters Fixed**: All 5 periods validated with multi-day test data
- ✅ **Learn Later Actions Fixed**: Match button errors resolved, UX cleaned up
- ✅ **On Stage Tab Scope Fixed**: API-level show_id filtering implemented

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
- `audience.request_submitted` - when audience submits request (includes audience_id)
- `audience.suggestion_submitted` - when audience submits suggestion
- `audience.dedication_submitted` - when request includes dedication (Phase 2)
- `audience.tip_clicked` - when audience clicks tip link (Phase 2)
- `audience.follow_clicked` - when audience clicks social link (Phase 2)
- `audience.tip_completed` - when audience submits tip (Phase 2)
- `audience.email_submitted` - when audience provides email in Moment 3 (new)
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

#### Show-Scoped Architecture
- ✅ Suggestions now have `show_id` and `show_name` fields
- ✅ Suggestions auto-create shows when no active show exists
- ✅ Requests tab displays shows with both Requests and Suggestions sections
- ✅ Batch selection and actions for suggestions within shows
- ✅ Legacy suggestions (without show_id) shown in "Unassigned Suggestions" section
- ✅ Learn Later toggle on Songs tab showing learn_later suggestions
- ✅ Restore archived shows without success popup

### Bug Fixes (January 15-16, 2026)

#### P0: Analytics Period Filters - FIXED
- **Issue**: `days=0` (All Time) returned 0 results instead of all requests
- **Root Cause**: Condition `if days is not None` treated `days=0` as a date filter
- **Fix**: Changed to `if days is not None and days > 0` to correctly identify All Time
- **File**: `/app/backend/server.py` line ~4315

#### P1: Learn Later List Actions - FIXED
- **Issue**: Match button caused runtime errors, Restore button was redundant
- **Root Cause**: Calls to non-existent `setShowMatchModal(true)` function
- **Fix**: Removed `setShowMatchModal(true)` calls, removed Restore button
- **File**: `/app/frontend/src/App.js` lines ~4850-4888

#### P2: On Stage Tab Scope - FIXED
- **Issue**: On Stage tab showed all requests/suggestions, not just active show
- **Root Cause**: Missing `currentShow` conditional and show_id filtering
- **Fix**: 
  - Added empty state when no active show exists
  - Filtered all requests/suggestions by `show_id === currentShow.id`
  - Updated useEffect to run on 'onstage' tab too
- **File**: `/app/frontend/src/App.js` lines ~5822-6143

### Architecture

#### Backend: `/app/backend/server.py`
- SongSuggestion model includes `show_id` and `show_name`
- Auto-show creation in suggestion submission endpoint
- Analytics events for all suggestion and show lifecycle actions
- Timezone-aware analytics with musician timezone stored in profile

#### Frontend: `/app/frontend/src/App.js`
- Show tiles display "(X requests, Y suggestions)" counts
- Collapsible Requests and Suggestions sections within each show
- Batch actions: Learn Later, Skip, Trash for suggestions
- Learn Later view on Songs tab with Match, Add, Trash actions
- On Stage tab shows empty state when no active show, filters by currentShow when active

## Key API Endpoints
- `/api/requests` - Create request (accepts audience_id)
- `/api/requests/{request_id}/email` - Attach email post-submission (Moment 3)
- `/api/musicians/{slug}/requests` - Audience request submission (accepts audience_id)
- `/api/requests/{id}/status` - Update request status
- `/api/requests/{id}/track-click` - Track tip/social clicks (accepts audience_id)
- `/api/musicians/{slug}/tips` - Submit tip (accepts audience_id, show_id)
- `/api/song-suggestions` - Create suggestion (with auto-show)
- `/api/song-suggestions/{id}/status` - Update suggestion status
- `/api/song-suggestions/{id}/match` - Match suggestion to song
- `/api/song-suggestions/{id}/learn-later` - Mark as learn later
- `/api/shows/start` - Start show (captures musician timezone)
- `/api/shows/stop` - Stop show
- `/api/shows/{id}/archive` - Archive show
- `/api/shows/{id}/restore` - Restore show
- `/api/analytics/daily` - Get daily analytics (timezone-aware)

## Known Edge Cases
1. Legacy suggestions without show_id appear in "Unassigned Suggestions"
2. Archived shows don't show suggestions count in summary
3. "Song Suggestions" button at top still exists for backwards compatibility
4. `created_at` field in requests/suggestions has mixed types (string/datetime)

## Upcoming Tasks (Backlog)
- **Phase 3: Post-Show Reflection** - Summary analytics, exports, historical views (DEFERRED)
- Build analytics UI powered by `analytics_events`
- Spotify Web API integration for playlist enrichment
- Show rename functionality
- Frontend refactoring (App.js is ~12,000+ lines)
- Increment 4: Update UI to format timestamps in musician's local timezone

## Technical Debt
- `/app/frontend/src/App.js` is monolithic (~12,000+ lines)
- Refactoring into modular components required before scaling

## Environment
- Preview URL: https://songrequest-ui.preview.emergentagent.com
- Backend: FastAPI (Python)
- Frontend: React
- Database: MongoDB

## Test Credentials
- Email: test@test.com
- Password: test
