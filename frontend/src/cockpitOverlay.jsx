import React, { useState, useEffect, useCallback } from 'react';

/*
 * cockpitOverlay.jsx
 * -----------------------------------------------------------------------------
 * Pure presentational cockpit chrome added to ChordProViewer when a chart is
 * opened from On Stage. No app-internal dependencies: all data and actions come
 * in through props, so the Songs-tab and standalone viewer call sites are
 * unaffected (they simply do not render these pieces).
 *
 * Pieces (placed by the integration prompt):
 *   useCockpit(scrollRef)  -> shared UI state (faded box, open panel)
 *   <UpNextTrigger/>       -> header, left (the freed top-bar space, in line with the gear)
 *   <UpNextPanel/>         -> dropdown anchored top-left, mirrors the gear dropdown
 *   <DedicationBox/>       -> overlay near the top of the chart body
 *   <PlayedButton/>        -> floating bottom-right
 *
 * Data shapes:
 *   requestsForThisSong : [{ id, requester_name, dedication, tip_clicked }]   oldest first
 *   openQueue           : [{ song_id, title, subtitle, count, hasChart, isCurrent }] oldest first
 *
 * Decisions encoded here:
 *   - Dedication box fades on scroll and is recoverable by tapping a chip (or the count).
 *   - The Up next list shows chartless requested songs too, tappable, flagged "no chart".
 * Decision NOT encoded here (lives in the parent's onPlayed wiring):
 *   - "Played" marks every open request for the song. This module only calls onPlayed().
 */

// ---- pure data shaping (verified here; the wire-in only feeds raw state) ------
//
// "Open" for the cockpit is pending, up_next, accepted. This is intentionally
// broader than the existing On Stage active filter (pending, accepted) so that
// Played never strands an up_next copy of the same song. Do not change the
// existing app filters to match; the cockpit owns its own open-set.

const COCKPIT_OPEN = ['pending', 'up_next', 'accepted'];

// Dedication stack for the song currently shown, oldest request first.
export function buildSongRequests(requests, songId, showId) {
  return (requests || [])
    .filter(r => r.song_id === songId && r.show_id === showId && COCKPIT_OPEN.includes(r.status))
    .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
    .map(r => ({
      id: r.id,
      requester_name: r.requester_name,
      dedication: r.dedication,
      tip_clicked: r.tip_clicked,
    }));
}

// Song-grouped Up next list for the current show, oldest first, current song on top.
// hasChart means a chordpro chart exists to open IN this viewer (link/pdf charts
// open externally elsewhere and are treated as not-openable here).
export function buildOpenQueue(requests, songs, currentSongId, showId) {
  const open = (requests || []).filter(r => r.show_id === showId && COCKPIT_OPEN.includes(r.status));
  const byId = {};
  (songs || []).forEach(s => { byId[s.id] = s; });

  const groups = new Map();
  open.forEach(r => {
    const key = r.song_id || `t:${r.song_title || ''}|${r.song_artist || ''}`;
    if (!groups.has(key)) {
      groups.set(key, { song_id: r.song_id, title: r.song_title || 'Untitled', count: 0, earliest: r.created_at, firstRequester: r.requester_name });
    }
    const g = groups.get(key);
    g.count += 1;
    if (new Date(r.created_at) < new Date(g.earliest)) g.earliest = r.created_at;
  });

  const list = Array.from(groups.values()).map(g => {
    const song = byId[g.song_id] || {};
    return {
      song_id: g.song_id,
      title: g.title,
      count: g.count,
      hasChart: song.chart_type === 'chordpro' && !!song.chart_chordpro,
      isCurrent: g.song_id === currentSongId,
      subtitle: g.count > 1 ? `${g.count} people` : (g.firstRequester || 'Anonymous'),
      earliest: g.earliest,
    };
  });

  list.sort((a, b) => {
    if (a.isCurrent && !b.isCurrent) return -1;
    if (b.isCurrent && !a.isCurrent) return 1;
    return new Date(a.earliest) - new Date(b.earliest);
  });
  return list;
}

// ---- shared state -----------------------------------------------------------

export function useCockpit(scrollRef) {
  const [faded, setFaded] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);

  useEffect(() => {
    const el = scrollRef && scrollRef.current;
    if (!el) return;
    const onScroll = () => setFaded(el.scrollTop > 40);
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, [scrollRef]);

  const recover = useCallback(() => {
    const el = scrollRef && scrollRef.current;
    if (el) el.scrollTo({ top: 0, behavior: 'smooth' });
    setFaded(false);
  }, [scrollRef]);

  const hide = useCallback(() => setFaded(true), []);

  return { faded, recover, hide, panelOpen, setPanelOpen };
}

// ---- header trigger (left, in line with the gear) ---------------------------

export function UpNextTrigger({ count = 0, onToggle, isLight = false, isOnStage = false }) {
  if (!isOnStage) return null;
  const base = isLight
    ? 'text-gray-600 hover:text-gray-900 hover:bg-gray-200'
    : 'text-gray-300 hover:text-white hover:bg-gray-700';
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label="Up next"
      className={`flex items-center gap-2 h-11 px-3 rounded-lg transition duration-200 ${base}`}
    >
      <span className="flex flex-col gap-[2.5px]">
        <span className="block w-[15px] h-[2px] rounded bg-current" />
        <span className="block w-[10px] h-[2px] rounded bg-current" />
        <span className="block w-[15px] h-[2px] rounded bg-current" />
      </span>
      <span className="text-sm font-semibold">Up next</span>
      {count > 0 && (
        <span className="min-w-[19px] h-[19px] px-[5px] rounded-full bg-purple-600 text-white text-[11px] font-extrabold flex items-center justify-center">
          {count}
        </span>
      )}
      <span className="text-[11px] text-gray-400">▾</span>
    </button>
  );
}

// ---- up next dropdown -------------------------------------------------------

export function UpNextPanel({ queue = [], open, onClose, onOpenSong }) {
  if (!open) return null;
  return (
    <>
      <div className="fixed inset-0 z-10" onClick={onClose} />
      <div className="absolute top-full left-2 mt-1 z-20 bg-gray-800 border border-gray-700 rounded-xl shadow-xl p-2 w-[264px] max-h-[70vh] overflow-y-auto">
        <div className="px-2 pt-1 pb-2 text-[10.5px] uppercase tracking-wide text-gray-400 font-semibold">
          Open requests · oldest first
        </div>
        {queue.map((q, i) => {
          const tappable = q.hasChart && !q.isCurrent;
          return (
            <button
              type="button"
              key={q.song_id}
              disabled={q.isCurrent}
              onClick={() => {
                if (tappable && onOpenSong) onOpenSong(q.song_id);
                onClose();
              }}
              className={`w-full flex items-center gap-2.5 px-2 py-2.5 rounded-lg text-left transition ${
                q.isCurrent
                  ? 'bg-purple-900/30 border border-purple-700/60'
                  : 'hover:bg-gray-700'
              }`}
            >
              <span className="w-[18px] text-center text-xs font-bold text-gray-500 shrink-0">
                {q.isCurrent ? '♪' : i}
              </span>
              <span className="flex-1 min-w-0">
                <span className="block text-sm font-semibold text-gray-100 truncate">{q.title}</span>
                <span className="block text-[11.5px] text-gray-400 mt-px">
                  {q.isCurrent ? 'on stage now' : q.subtitle}
                </span>
              </span>
              {q.count > 1 && (
                <span className="text-[11px] text-purple-200 bg-purple-900/40 border border-purple-700/60 rounded-full px-2 font-bold shrink-0">
                  ×{q.count}
                </span>
              )}
              {!q.hasChart && (
                <span className="text-[11px] text-gray-500 shrink-0">no chart</span>
              )}
            </button>
          );
        })}
      </div>
    </>
  );
}

// ---- dedication box (overlay near top of chart body) ------------------------

function Requester({ r, divider }) {
  const anon = !r.requester_name || !r.requester_name.trim();
  return (
    <div className={`flex gap-2 items-start ${divider ? 'mt-2 pt-2 border-t border-slate-700/60' : ''}`}>
      <div>
        <div className={`text-[15px] font-bold ${anon ? 'text-gray-400 italic font-semibold' : 'text-white'}`}>
          {anon ? 'Anonymous' : r.requester_name}
          {r.tip_clicked && (
            <span className="text-emerald-400 font-semibold text-[12.5px] ml-1.5">💰 tipped</span>
          )}
        </div>
        {r.dedication && r.dedication.trim() && (
          <div className="text-[13.5px] text-slate-200 italic mt-px">{r.dedication}</div>
        )}
      </div>
    </div>
  );
}

export function DedicationBox({ requests = [], songTitle = '', faded, onRecover, onHide }) {
  if (!requests.length) return null;

  if (faded) {
    return (
      <button
        type="button"
        onClick={onRecover}
        className="absolute top-2 right-3 z-[35] inline-flex items-center gap-1.5 bg-slate-900/95 border border-slate-600 text-slate-200 rounded-full px-3 py-1.5 text-xs font-semibold shadow-lg"
      >
        ♪ {requests.length} dedication{requests.length > 1 ? 's' : ''} ▾
      </button>
    );
  }

  return (
    <div className="absolute top-0 left-0 right-0 z-30 px-3.5 pt-3 pointer-events-none">
      <div className="pointer-events-auto bg-slate-900/95 border border-slate-600 border-l-[3px] border-l-purple-500 rounded-xl px-3.5 py-3 shadow-2xl">
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <span className="text-[10.5px] uppercase tracking-wide text-slate-400 font-bold truncate">
            On stage now{songTitle ? ` · ${songTitle}` : ''}
          </span>
          <div className="flex items-center gap-2 shrink-0">
            {requests.length > 1 && (
              <span className="text-[11px] text-slate-300 bg-slate-800 border border-slate-600 rounded-full px-2 py-0.5 font-semibold">
                {requests.length} requests
              </span>
            )}
            <button type="button" onClick={onHide} aria-label="Hide" className="text-gray-500 text-lg leading-none px-1.5">
              −
            </button>
          </div>
        </div>
        {requests.map((r, i) => (
          <Requester key={r.id || i} r={r} divider={i > 0} />
        ))}
      </div>
    </div>
  );
}

// ---- played button ----------------------------------------------------------

export function PlayedButton({ onPlayed, isOnStage = false }) {
  if (!isOnStage || !onPlayed) return null;
  return (
    <button
      type="button"
      onClick={onPlayed}
      className="absolute right-4 bottom-[18px] z-[45] flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white font-bold text-[15.5px] rounded-full pl-[18px] pr-[22px] py-3.5 shadow-2xl active:translate-y-px transition"
    >
      ✓ Played
    </button>
  );
}
