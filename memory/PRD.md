# RequestWave PRD

## Product Vision
RequestWave is a multi-profile platform for live musicians to accept song requests, tips, and email signups from audiences during shows.

## Core Domain Model
- **Musician** (account root): `{id, email, slug, ...}`
- **Profile** (multi-profile per musician): `{id, musician_id, slug, is_default, current_show_id, active_playlist_ids, ...}`
- **Event** → **Show** (per-show analytics scope): `{id, musician_id, profile_id, event_id, name, request_count, ...}`
- **Playlist**, **Song**, **Request** linked by `musician_id` / `profile_id` / `show_id`.

## Authoritative Rules
- Playlist selection lives on the **profile** as `active_playlist_ids` (list). `__all__` means full library; `[]` means empty. The legacy `musician.active_playlist_id` is **not** consulted.
- A show only restricts playlist when `playlist_filter_mode == "selected"`. Otherwise the profile's `active_playlist_ids` is the source of truth.
- Profile social links never inherit from master musician if intentionally blank.
- Default profile is auto-created on new musician registration.
- Audience public URLs are resolved at runtime via `window.location.origin`.
- Admin panel lives at `/rw-ops` (Cloudflare bypass). `package.json` post-build copies `index.html` → `rw-ops.html`. **Do not remove.**

## Implemented (Recent)
- **2026-06 — Playlist-from-file importer (frontend):** New "Build a playlist from a file" modal in the Songs tab (Manage Songs dropdown → `open-playlist-file-import-btn`). Uploads `.lst`/`.csv` → `POST /playlists/import/classify` → resolve UI with three live counts and buckets: "Needs your call" (likely/ambiguous, amber), "will be added" (blue, checkbox add/skip + Edit), "Already in your library" (collapsed, green). Client-side edit-and-rematch mirrors backend normalization against the loaded `songs` array; an edited add that matches an existing song moves to the linked group with an Undo. Commit → `POST /playlists/import/commit`, green toast, refreshes songs+playlists. Info popover provides a copy-able CSV-conversion prompt. Verified by testing agent (iteration_23.json, 8/8 flows, 100%). Note (deferred, no-refactor rule): could extract into its own component; edit-match note is inside the collapsed `<details>`.
- **2026-06 — Playlist-from-file importer (backend):** New `backend/playlist_match.py` (pure, no-DB matching logic: `parse_lst`, `parse_csv_rows`, `normalize`, `classify` → exact/likely/ambiguous/none buckets). Two new routes in server.py after `/songs/csv/preview`: `POST /api/playlists/import/classify` (auth; accepts `.lst`/`.csv`, 10MB cap, classifies rows against the musician's library, returns `playlist_exists`+results, saves nothing) and `POST /api/playlists/import/commit` (auth; creates missing songs de-duped by case-insensitive title+artist, `$addToSet` into an existing same-name non-deleted playlist or creates a new one, returns created/linked/added/total). Does NOT reuse `parse_lst_file`/`parse_csv_content`. Verified via curl (all buckets, validation 400s, create + idempotent re-commit, blank-name guard). No frontend wiring yet.
- **2026-06 — Fix (backend, file corruption):** server.py had a duplicated startup block (migrate/log_routes/CORS/logging) with a fused line `client.close()"One-time migration...` at the tail, breaking uvicorn reload. Removed the corrupted duplicate (lines 9940–10078); the single clean shutdown handler remains at EOF. Backend restarts clean.
- **2026-06 — Fix (backend, empty playlist = show all):** New accounts previously got a default profile with `active_playlist_ids=[]`, and the audience song-read code treated empty as "show no songs," so a new musician's audience page stayed empty until they manually picked a playlist. Now: (1) registration seeds the default profile with `["__all__"]` (server.py ~L2144); (2) `get_musician_songs` treats empty `active_ids` same as `"__all__"` (server.py ~L4494); (3) `_get_profile_songs` same (server.py ~L8784). This retroactively repairs existing profiles stored with `[]`. The `"selected"`-mode show branch (`enabled_playlist_ids`, ~L4452-4476) is unchanged — empty there still returns `[]`. Verified 7/7 backend tests (iteration_20.json).
- **2026-02 — ChordPro ZIP Import (PREVIEW ONLY, read-only):** New `POST /api/songs/chordpro-import/preview` (auth, musician-scoped). Accepts a `.zip` (multipart), unzips in memory, processes `.cho/.crd/.chopro/.chordpro/.pro/.txt` (ignores `__MACOSX`, `.DS_Store`, `._*`). Parses `{title}/{t}` + `{subtitle}/{st}` directives only (no filename guessing). Sorts each file into EXACT (title+artist normalized match → would attach chart_chordpro to existing song), FUZZY (same normalized title w/ different artist ranks 0.99, else difflib SequenceMatcher ≥0.82 — includes candidate existing song id/title/artist), or NEW. Files w/o `{title}` → could-not-parse w/ filename+reason. Returns counts + full lists + raw `chart_chordpro` per entry for the later commit step. **NO DB WRITES** (read-only catalog query). Verified via curl (all 4 buckets). Frontend: "Import ChordPro (zip)" item in Songs-tab management dropdown opens a section (`chordpro-import-section`) with a `.zip` input + "Preview Import" button, rendering 4 labeled sections w/ counts (attach-existing / needs-review side-by-side comparison / create-new / couldn't-parse). No commit button yet (separate later prompt).
- Per-show Analytics dashboard, Learn Later toggle, Unassigned Requests panel, standalone Admin panel.
- Requests tab mobile-first redesign (single + bulk action modals, 2-row show cards).
- Admin: per-show request count + `show_id` column in Data Actions.
- Null-safe `GET /api/requests/grouped` (skips missing `song_id`).
- **2026-02 — Fix:** `GET /api/musicians/{slug}/songs` now respects the default profile's `active_playlist_ids` in all cases except an active show with `playlist_filter_mode="selected"` (which still wins). `__all__` → full catalog; specific IDs → union; `[]` → empty. `?playlist=` query param override preserved. Verified against the live preview for 5 scenarios.
- **2026-02 — UX:** Audience page no longer flashes "Musician not found" before the initial fetch resolves. Loading spinner shows until the musician/profile/event fetch completes.
- **2026-02 — On Stage indicators:** RequestCard now shows small read-only ✉️ email and 💰 "tapped tip" indicators (from `requester_email` / `tip_clicked`) below the "From:" line; existing `tip_amount` display untouched.
- **2026-02 — ChordPro viewer wired into On Stage:** `chordsheetjs` (15.3.1) added. `ChordProViewer` modal (full-screen, stage-legible: bg-gray-900, purple bold chords above syllables, 18px wrapping lyrics, monospace, title/subtitle suppressed) parses `chart_chordpro` via ChordProParser→HtmlDivFormatter. Wired into all THREE "📄 Charts" button sites (two inline dashboard On Stage tab sites + the shared `RequestCard` used by standalone `/on-stage/:slug`). Button now shows when `((chart_type∈{link,pdf}) && chart_url) || (chart_type==='chordpro' && chart_chordpro)`. chordpro → opens modal in-app (no new tab); link/pdf → unchanged `window.open(chart_url)`. Separate `openChordpro` state in MusicianDashboard and OnStageInterface (each renders its own `ChordProViewer`). Temp test button removed. Verified by testing agent (4/4 frontend, 0 new tabs).
- **2026-02 — ChordPro editor support:** Added `chart_chordpro` (raw ChordPro text) to backend Song/SongCreate models + non-destructive guard in update_song (coexists with chart_url). Frontend: "ChordPro" is now a 4th chart type in BOTH Add and Edit song forms (`add-chart-type-chordpro` / `edit-chart-type-chordpro`), with a monospace paste textarea (`add-chart-chordpro-input` / `edit-chart-chordpro-input`) shown when type==='chordpro'. `chart_chordpro` round-trips in songForm state (init, edit-load, all resets). No viewer yet; On Stage Charts button unchanged (later prompt).
- **2026-02 — Sprint 10 Charts:** Songs support one chart (`chart_type`: null/"link"/"pdf", `chart_url`). Backend: added to Song/SongCreate models, persisted in create_song & update_song (non-destructive — update only writes chart fields explicitly present in payload, so type-only changes never erase the URL). Frontend: chart section (None/Link/PDF + conditional URL input) in Add form & Edit modal, non-destructive type switching in state; `OnStageInterface` RequestCard shows a "Charts" button (opens chart_url) only when the request's song has a chart. No ChordPro.

## Roadmap
### P2
- Tip conversion analytics (CTR, per-show conversion).
### P3
- Post-Show Reflection features.
- Spotify Web API enrichment.
### Refactor (P2 — DO NOT execute unless explicitly requested)
- Decompose `App.js` (14.7K lines) and `server.py` (9.4K lines).

## Project Health
- Broken: None. Mocked: None.
- Production lives at https://requestwave.app — preview is separate.

## Test Credentials
See `/app/memory/test_credentials.md`.
