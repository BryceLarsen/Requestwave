"""
playlist_match.py
Pure logic for the playlist-from-file importer.
No database, no framework, no I/O. Every function here is deterministic and
testable in isolation, which is why it lives in its own module.
Public API:
    parse_lst(text)      -> (playlist_name, [(title, artist), ...])
    parse_csv_rows(rows) -> [(title, artist), ...]
    normalize(s)         -> str
    classify(csv_rows, library) -> list of dicts, one per row
`library` is a list of dicts, each with at least: id, title, artist.
classify() never mutates its inputs and never touches the network or db.
"""
import re
import unicodedata
from difflib import SequenceMatcher
# Score at or above this against the single best candidate: treat as a match
# needing confirmation ("likely"). Below it: no match, offer to add.
LIKELY_THRESHOLD = 0.86
# If the two best candidates are within this of each other, the match is
# ambiguous and the user must pick, even if the top score is very high.
AMBIGUITY_MARGIN = 0.02
_LEADING_ARTICLES = ("the ", "a ", "an ")
def normalize(s):
    """Collapse cosmetic differences that should never block a match."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.lower().strip()
    s = re.sub(r"\s*\b(19|20)\d{2}\b\s*$", "", s)   # trailing year token
    s = s.replace("&", " and ")
    s = re.sub(r"\bfeat\.?\b.*$", "", s)            # drop trailing feat...
    s = re.sub(r"\bfeaturing\b.*$", "", s)
    s = s.replace("(", " ").replace(")", " ")
    s = s.replace("[", " ").replace("]", " ")
    s = s.replace("'", "")                          # gettin' -> gettin
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for art in _LEADING_ARTICLES:
        if s.startswith(art):
            s = s[len(art):]
            break
    return re.sub(r"\s+", " ", s).strip()
def parse_lst(text):
    """Songbook Pro .lst: line 1 is the playlist name, the rest are 'Title - Artist'."""
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    if not lines:
        return "", []
    name = lines[0]
    rows = []
    for line in lines[1:]:
        if " - " in line:
            title, artist = line.rsplit(" - ", 1)   # rightmost, so dashes in titles survive
        else:
            title, artist = line, ""
        rows.append((title.strip(), artist.strip()))
    return name, rows
def parse_csv_rows(rows):
    """rows: list of dicts from csv.DictReader. Requires a title column; artist optional."""
    out = []
    for row in rows or []:
        lowered = {(k or "").lower().strip(): (v or "").strip() for k, v in row.items()}
        title = lowered.get("title", "")
        artist = lowered.get("artist", "")
        if title:
            out.append((title, artist))
    return out
def _sim(a, b):
    return SequenceMatcher(None, a, b).ratio()
def _score(csv_title, csv_artist, lib_title, lib_artist):
    """Title dominates. An absent artist on either side must not fake a perfect artist score."""
    t = _sim(normalize(csv_title), normalize(lib_title))
    na, nb = normalize(csv_artist), normalize(lib_artist)
    if not na or not nb:
        return 0.7 * t          # title-only evidence, capped below the likely threshold
    return 0.7 * t + 0.3 * _sim(na, nb)
def classify(csv_rows, library):
    """
    Sort each incoming row into exactly one bucket:
      'exact'     - normalized title AND artist both match a library song
      'likely'    - one clear best candidate at or above LIKELY_THRESHOLD
      'ambiguous' - top candidates too close to call, user picks
      'none'      - nothing close, offer to add as a new song
    Returns a list of dicts; ordering matches csv_rows.
    """
    results = []
    for title, artist in csv_rows:
        nt, na = normalize(title), normalize(artist)
        # An artist is required for an auto-link. Without one, a title hit is
        # only evidence, never proof, so it always goes to the user.
        if na:
            exact = [s for s in library
                     if normalize(s.get("title")) == nt and normalize(s.get("artist")) == na]
            if len(exact) == 1:
                results.append({
                    "csv_title": title, "csv_artist": artist,
                    "bucket": "exact", "song_id": exact[0]["id"],
                    "matched": exact[0], "score": 1.0, "candidates": [],
                })
                continue
            if len(exact) > 1:
                # Two library songs are indistinguishable on title+artist. Never guess.
                results.append({
                    "csv_title": title, "csv_artist": artist,
                    "bucket": "ambiguous", "song_id": None, "matched": None, "score": 1.0,
                    "candidates": [{"song": s, "score": 1.0} for s in exact],
                })
                continue
        else:
            # No artist in the file. If the title alone lands on library songs,
            # surface them for confirmation rather than adding a duplicate.
            title_hits = [s for s in library if normalize(s.get("title")) == nt]
            if title_hits:
                results.append({
                    "csv_title": title, "csv_artist": artist,
                    "bucket": "ambiguous" if len(title_hits) > 1 else "likely",
                    "song_id": None,
                    "matched": title_hits[0] if len(title_hits) == 1 else None,
                    "score": 0.7,
                    "candidates": ([{"song": s, "score": 0.7} for s in title_hits]
                                   if len(title_hits) > 1 else []),
                })
                continue
        scored = sorted(
            ({"song": s, "score": _score(title, artist, s.get("title"), s.get("artist"))}
             for s in library),
            key=lambda x: x["score"], reverse=True,
        )
        top = scored[0] if scored else None
        runner = scored[1] if len(scored) > 1 else None
        if top and top["score"] >= LIKELY_THRESHOLD:
            tied = runner and (top["score"] - runner["score"]) <= AMBIGUITY_MARGIN
            results.append({
                "csv_title": title, "csv_artist": artist,
                "bucket": "ambiguous" if tied else "likely",
                "song_id": None,
                "matched": None if tied else top["song"],
                "score": round(top["score"], 3),
                "candidates": [
                    {"song": c["song"], "score": round(c["score"], 3)}
                    for c in scored[:3] if c["score"] >= LIKELY_THRESHOLD
                ] if tied else [],
            })
        else:
            results.append({
                "csv_title": title, "csv_artist": artist,
                "bucket": "none", "song_id": None, "matched": None,
                "score": round(top["score"], 3) if top else 0.0,
                "candidates": [],
            })
    return results
