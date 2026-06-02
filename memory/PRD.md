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
