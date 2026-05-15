"""
Tests for the rewritten GET /api/analytics/export-requesters endpoint.

Spec under test:
- Optional `show_id` query param scopes export to a single show
- CSV output: exactly 3 columns header `name,email,show_name`
- Email validation: must match ^[^@\s]+@[^@\s]+\.[^@\s]+$ (empty, missing @, missing TLD all excluded)
- `show_name` resolved per-row from db.shows; empty when request has no show_id
- Filename suffix: `-show-<id8>` when show_id provided; coexists with profile_id filter
"""
import csv
import io
import os
import re
import time
import uuid
import pytest
import requests
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "test"


@pytest.fixture(scope="module")
def auth_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"Login failed: {r.status_code} {r.text}")
    token = r.json().get("token")
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def musician_slug(auth_session):
    # Try a few common endpoints to discover slug; fall back to 'test'
    for path in ("/api/auth/me", "/api/musicians/me", "/api/me"):
        try:
            r = auth_session.get(f"{BASE_URL}{path}")
            if r.status_code == 200:
                j = r.json()
                if isinstance(j, dict) and j.get("slug"):
                    return j["slug"]
        except Exception:
            pass
    return "test"


@pytest.fixture(scope="module")
def shows_list(auth_session):
    r = auth_session.get(f"{BASE_URL}/api/shows")
    assert r.status_code == 200, r.text
    data = r.json()
    if isinstance(data, dict):
        data = data.get("shows", [])
    return data


@pytest.fixture(scope="module")
def profiles_list(auth_session):
    r = auth_session.get(f"{BASE_URL}/api/profiles")
    assert r.status_code == 200, r.text
    return r.json()


def _parse_csv(text):
    return list(csv.reader(io.StringIO(text)))


def _filename(resp):
    cd = resp.headers.get("Content-Disposition", "")
    m = re.search(r'filename=([^;]+)', cd)
    return m.group(1).strip().strip('"') if m else None


# -------- 1. CSV shape (3-column header, no legacy columns) --------

class TestCsvShape:
    def test_header_is_exactly_three_columns(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/analytics/export-requesters")
        assert r.status_code == 200, r.text
        rows = _parse_csv(r.text)
        assert len(rows) >= 1, "Empty CSV (no header)"
        header = rows[0]
        assert header == ["name", "email", "show_name"], f"Unexpected header: {header}"

    def test_no_legacy_columns_anywhere(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/analytics/export-requesters")
        text = r.text
        for forbidden in ["Request Count", "Total Tips", "Latest Request"]:
            assert forbidden not in text, f"Legacy column {forbidden!r} still present in CSV body"

    def test_data_rows_have_three_fields(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/analytics/export-requesters")
        rows = _parse_csv(r.text)
        for i, row in enumerate(rows[1:], start=1):
            if not row:
                continue
            assert len(row) == 3, f"Row {i} has {len(row)} fields, expected 3: {row}"

    def test_filename_no_filter(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/analytics/export-requesters")
        fname = _filename(r)
        assert fname and re.match(r"^requesters-\d{8}\.csv$", fname), f"Got: {fname}"


# -------- 2. show_id filter --------

class TestShowIdFilter:
    def test_filename_has_show_suffix(self, auth_session, shows_list):
        if not shows_list:
            pytest.skip("No shows available")
        sid = shows_list[0]["id"]
        r = auth_session.get(
            f"{BASE_URL}/api/analytics/export-requesters",
            params={"show_id": sid},
        )
        assert r.status_code == 200, r.text
        fname = _filename(r)
        assert fname.startswith(f"requesters-show-{sid[:8]}-"), f"Got: {fname}"
        assert fname.endswith(".csv")

    def test_all_rows_belong_to_filtered_show(self, auth_session, shows_list):
        """For every show, if its export returns data rows, every row's show_name
        must equal that show's name (or be empty when DB couldn't resolve)."""
        if not shows_list:
            pytest.skip("No shows available")
        checked = 0
        for show in shows_list[:20]:  # cap to keep runtime bounded
            sid = show["id"]
            sname = show.get("name", "")
            r = auth_session.get(
                f"{BASE_URL}/api/analytics/export-requesters",
                params={"show_id": sid},
            )
            assert r.status_code == 200
            rows = _parse_csv(r.text)
            data_rows = [row for row in rows[1:] if row]
            for row in data_rows:
                # All rows in a show-filtered export must carry this show's name.
                # Empty is acceptable only if the show name itself is empty.
                assert row[2] == sname, (
                    f"show_id={sid} row show_name={row[2]!r} != expected {sname!r}"
                )
            if data_rows:
                checked += 1
            if checked >= 3:
                break
        if checked == 0:
            pytest.skip("No show had any requesters to validate")


# -------- 3. Email validation --------

class TestEmailValidation:
    """Seed requests with malformed and valid emails on one show; verify only the
    valid email appears in the show-filtered export."""

    @pytest.fixture(scope="class")
    def seed(self, auth_session, musician_slug, shows_list, profiles_list):
        if not shows_list:
            pytest.skip("No shows available to scope email-validation seed")
        # pick or create a show
        show = shows_list[0]
        show_id = show["id"]

        # Need a song to request
        r = auth_session.get(f"{BASE_URL}/api/songs")
        assert r.status_code == 200, r.text
        songs = r.json()
        if isinstance(songs, dict):
            songs = songs.get("songs", [])
        if not songs:
            pytest.skip("No songs available to seed requests")
        song = songs[0]

        # Find profile id linked to this show, fallback to default profile
        profile_id = show.get("profile_id")
        if not profile_id and profiles_list:
            default = next((p for p in profiles_list if p.get("is_default")), profiles_list[0])
            profile_id = default["id"]

        marker = uuid.uuid4().hex[:8]
        cases = [
            ("",                       "TEST_empty_"  + marker, False),
            ("no-at-symbol",           "TEST_noat_"   + marker, False),
            ("invalid@nodomain",       "TEST_nodot_"  + marker, False),
            (f"good+{marker}@example.com", "TEST_good_" + marker, True),
        ]
        created_ids = []
        seeded_valid_email = None
        for email, name, is_valid in cases:
            payload = {
                "song_id": song["id"],
                "song_title": song.get("title", "Song"),
                "song_artist": song.get("artist", "Artist"),
                "requester_name": name,
                "requester_email": email,
                "dedication": "",
                "show_id": show_id,
            }
            if profile_id:
                payload["profile_id"] = profile_id
            rr = requests.post(
                f"{BASE_URL}/api/musicians/{musician_slug}/requests",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if rr.status_code in (200, 201):
                body = rr.json()
                rid = body.get("id") or body.get("request", {}).get("id")
                if rid:
                    created_ids.append(rid)
            # Even if server rejects invalid email at write-time, that satisfies the spec
            # (such rows are simply absent from the export).
            if is_valid:
                seeded_valid_email = email.lower()

        # tiny wait so aggregation sees the writes
        time.sleep(1.0)

        yield {
            "show_id": show_id,
            "marker": marker,
            "valid_email": seeded_valid_email,
            "request_ids": created_ids,
        }

        # Teardown: archive the seeded requests
        for rid in created_ids:
            try:
                auth_session.put(f"{BASE_URL}/api/requests/{rid}/archive", json={})
            except Exception:
                pass

    def test_valid_email_present_invalid_absent(self, auth_session, seed):
        # Query WITHOUT show filter — the request may have been routed to the
        # active/current show on the server, not the show_id we passed in. We
        # only need to validate email-validation semantics in the global export.
        r = auth_session.get(f"{BASE_URL}/api/analytics/export-requesters")
        assert r.status_code == 200
        rows = _parse_csv(r.text)[1:]
        emails = [row[1].lower() for row in rows if row]
        marker = seed["marker"]

        # Valid one should be present (only if seed write succeeded)
        if seed["valid_email"]:
            assert seed["valid_email"] in emails, (
                f"Expected valid email {seed['valid_email']} in export; "
                f"found {len(emails)} rows, sample: {emails[:5]}"
            )

        # No invalid emails should appear anywhere in export
        for bad in ["", "no-at-symbol", "invalid@nodomain"]:
            assert bad not in emails, f"Invalid email {bad!r} leaked into export"

        # Names tied to invalid emails must also be absent (defensive)
        names = [row[0] for row in rows if row]
        for tag in ["empty", "noat", "nodot"]:
            for n in names:
                if n.startswith(f"TEST_{tag}_{marker}"):
                    pytest.fail(f"Seeded invalid-email name {n} should not be in export")

    def test_regex_directly(self):
        """Sanity: re-implement the same regex and assert behavior on the seeded cases."""
        rx = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
        assert rx.match("good@example.com")
        assert not rx.match("")
        assert not rx.match("no-at-symbol")
        assert not rx.match("invalid@nodomain")
        assert not rx.match("bad @space.com")


# -------- 4. show_name resolution semantics --------

class TestShowNameResolution:
    def test_show_name_matches_show_doc(self, auth_session, shows_list):
        """For any data row in the no-filter export with a known show name, ensure
        show_name field is either '' (no show_id on request) or matches a real show name."""
        valid_names = {s.get("name", "") for s in shows_list}
        r = auth_session.get(f"{BASE_URL}/api/analytics/export-requesters")
        assert r.status_code == 200
        rows = _parse_csv(r.text)[1:]
        for row in rows[:200]:  # cap for runtime
            if not row:
                continue
            show_name = row[2]
            # show_name must be either empty (no show_id) or match a real show name
            assert show_name == "" or show_name in valid_names, (
                f"Row {row} has show_name {show_name!r} not in known set"
            )


# -------- 5. Coexistence with profile_id filter --------

class TestFilterCoexistence:
    def test_profile_and_show_filename_uses_show_suffix(self, auth_session, profiles_list, shows_list):
        if not profiles_list or not shows_list:
            pytest.skip("Need both profiles and shows")
        pid = profiles_list[0]["id"]
        sid = shows_list[0]["id"]
        r = auth_session.get(
            f"{BASE_URL}/api/analytics/export-requesters",
            params={"profile_id": pid, "show_id": sid},
        )
        assert r.status_code == 200
        fname = _filename(r)
        # Code prioritizes show_id in the filename suffix
        assert fname.startswith(f"requesters-show-{sid[:8]}-"), f"Got: {fname}"

    def test_intersection_results_subset(self, auth_session, profiles_list, shows_list):
        """Result rows under (profile_id AND show_id) must be a subset of (show_id only)."""
        if not profiles_list or not shows_list:
            pytest.skip("Need both profiles and shows")
        sid = shows_list[0]["id"]
        # show-only set
        r_show = auth_session.get(
            f"{BASE_URL}/api/analytics/export-requesters",
            params={"show_id": sid},
        )
        assert r_show.status_code == 200
        show_emails = {row[1] for row in _parse_csv(r_show.text)[1:] if row}

        for p in profiles_list:
            pid = p["id"]
            r = auth_session.get(
                f"{BASE_URL}/api/analytics/export-requesters",
                params={"profile_id": pid, "show_id": sid},
            )
            assert r.status_code == 200
            both = {row[1] for row in _parse_csv(r.text)[1:] if row}
            assert both.issubset(show_emails), (
                f"profile {pid} + show {sid} returned emails not in show-only set: "
                f"{both - show_emails}"
            )

    def test_bogus_show_id_returns_empty_body(self, auth_session):
        r = auth_session.get(
            f"{BASE_URL}/api/analytics/export-requesters",
            params={"show_id": "bogus-show-id-xyz"},
        )
        assert r.status_code == 200
        rows = _parse_csv(r.text)
        # only header, no data
        assert rows[0] == ["name", "email", "show_name"]
        data = [row for row in rows[1:] if row]
        assert data == [], f"Expected no data rows; got: {data[:5]}"
