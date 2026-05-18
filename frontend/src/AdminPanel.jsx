import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const ADMIN_TOKEN_KEY = 'rw_admin_token';

const fmtDate = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
};

function AdminLogin({ onAuthed }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const { data } = await axios.post(`${API}/admin/login`, { password });
      sessionStorage.setItem(ADMIN_TOKEN_KEY, data.token);
      onAuthed(data.token);
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4" data-testid="admin-login-screen">
      <form
        onSubmit={submit}
        className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-sm"
      >
        <h1 className="text-xl font-bold text-white mb-1">Admin Panel</h1>
        <p className="text-xs text-gray-400 mb-4">Restricted access</p>
        <label className="block text-xs font-medium text-gray-300 mb-1">Password</label>
        <input
          type="password"
          autoFocus
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white mb-3 focus:outline-none focus:border-purple-500"
          data-testid="admin-password-input"
        />
        {error && (
          <p className="text-sm text-red-400 mb-3" data-testid="admin-login-error">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={submitting || !password}
          className="w-full bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white py-2 rounded font-medium transition"
          data-testid="admin-login-submit"
        >
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  );
}

function DataActionsPanel({ token, musician, onActionDone }) {
  // musician is the currently-expanded user-detail object (with profiles + shows)
  const [shows, setShows] = useState([]); // flat list
  const [filterShowId, setFilterShowId] = useState('unassigned');
  const [requests, setRequests] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [reassignTo, setReassignTo] = useState('');
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    const flat = [];
    (musician.profiles || []).forEach((p) => {
      (p.shows || []).forEach((s) => flat.push({ ...s, profile_name: p.name }));
    });
    (musician.orphan_shows || []).forEach((s) => flat.push({ ...s, profile_name: '—' }));
    setShows(flat);
  }, [musician]);

  const fetchRequests = async () => {
    setLoading(true);
    setMsg('');
    setSelected(new Set());
    try {
      const { data } = await axios.get(`${API}/admin/users/${musician.musician.id}/requests`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { show_id: filterShowId },
      });
      setRequests(data.requests || []);
    } catch (err) {
      setMsg(err.response?.data?.detail || 'Failed to load requests');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterShowId, musician.musician.id]);

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selected.size === requests.length) setSelected(new Set());
    else setSelected(new Set(requests.map((r) => r.id)));
  };

  const doReassign = async () => {
    if (!reassignTo || selected.size === 0) return;
    setBusy(true);
    setMsg('');
    try {
      const { data } = await axios.post(
        `${API}/admin/requests/reassign`,
        { request_ids: Array.from(selected), show_id: reassignTo },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setMsg(`Reassigned ${data.modified} request${data.modified === 1 ? '' : 's'}`);
      setSelected(new Set());
      await fetchRequests();
      onActionDone && onActionDone();
    } catch (err) {
      setMsg(err.response?.data?.detail || 'Reassign failed');
    } finally {
      setBusy(false);
    }
  };

  const doDelete = async () => {
    if (selected.size === 0) return;
    const confirmed = window.confirm(
      `Permanently delete ${selected.size} request${selected.size === 1 ? '' : 's'}? This cannot be undone.`
    );
    if (!confirmed) return;
    setBusy(true);
    setMsg('');
    try {
      const { data } = await axios.post(
        `${API}/admin/requests/delete`,
        { request_ids: Array.from(selected) },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setMsg(`Deleted ${data.deleted} request${data.deleted === 1 ? '' : 's'}`);
      setSelected(new Set());
      await fetchRequests();
      onActionDone && onActionDone();
    } catch (err) {
      setMsg(err.response?.data?.detail || 'Delete failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-4 bg-gray-900/60 border border-gray-700 rounded-lg p-4" data-testid="admin-data-actions">
      <h4 className="text-sm font-bold text-white mb-3">Data Actions</h4>

      <div className="flex flex-wrap items-center gap-3 mb-3">
        <div>
          <label className="block text-[10px] uppercase tracking-wide text-gray-400 mb-1">Filter</label>
          <select
            value={filterShowId}
            onChange={(e) => setFilterShowId(e.target.value)}
            className="bg-gray-700 border border-gray-600 text-sm text-white rounded px-2 py-1"
            data-testid="admin-filter-show-select"
          >
            <option value="unassigned">Unassigned</option>
            {shows.map((s) => (
              <option key={s.id} value={s.id}>
                {s.profile_name} — {s.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex-1 min-w-[180px]">
          <label className="block text-[10px] uppercase tracking-wide text-gray-400 mb-1">Reassign to</label>
          <select
            value={reassignTo}
            onChange={(e) => setReassignTo(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 text-sm text-white rounded px-2 py-1"
            data-testid="admin-reassign-target-select"
          >
            <option value="">Select target show…</option>
            {shows.map((s) => (
              <option key={s.id} value={s.id}>
                {s.profile_name} — {s.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={doReassign}
            disabled={busy || !reassignTo || selected.size === 0}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm px-3 py-1 rounded transition"
            data-testid="admin-reassign-btn"
          >
            Reassign ({selected.size})
          </button>
          <button
            type="button"
            onClick={doDelete}
            disabled={busy || selected.size === 0}
            className="bg-red-600 hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm px-3 py-1 rounded transition"
            data-testid="admin-delete-btn"
          >
            Delete ({selected.size})
          </button>
        </div>
      </div>

      {msg && (
        <p className="text-xs text-gray-300 mb-2" data-testid="admin-action-msg">
          {msg}
        </p>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="text-xs uppercase tracking-wide text-gray-400 border-b border-gray-700">
            <tr>
              <th className="px-2 py-2 w-8">
                <input
                  type="checkbox"
                  checked={requests.length > 0 && selected.size === requests.length}
                  onChange={selectAll}
                  data-testid="admin-select-all"
                  aria-label="Select all"
                />
              </th>
              <th className="px-2 py-2 text-left">Song</th>
              <th className="px-2 py-2 text-left">Requester</th>
              <th className="px-2 py-2 text-left">Submitted</th>
              <th className="px-2 py-2 text-left">Show</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={5} className="px-2 py-4 text-center text-gray-400">
                  Loading…
                </td>
              </tr>
            )}
            {!loading && requests.length === 0 && (
              <tr>
                <td colSpan={5} className="px-2 py-4 text-center text-gray-500">
                  No requests for this filter
                </td>
              </tr>
            )}
            {!loading &&
              requests.map((r) => (
                <tr
                  key={r.id}
                  className="border-b border-gray-800 hover:bg-gray-800/40"
                  data-testid={`admin-request-row-${r.id}`}
                >
                  <td className="px-2 py-2">
                    <input
                      type="checkbox"
                      checked={selected.has(r.id)}
                      onChange={() => toggleSelect(r.id)}
                      data-testid={`admin-request-checkbox-${r.id}`}
                      aria-label="Select request"
                    />
                  </td>
                  <td className="px-2 py-2 text-gray-200">
                    <div className="font-medium">{r.song_title}</div>
                    <div className="text-xs text-gray-400">{r.song_artist}</div>
                  </td>
                  <td className="px-2 py-2 text-gray-300">
                    <div>{r.requester_name || 'Anonymous'}</div>
                    {r.requester_email && <div className="text-xs text-gray-500">{r.requester_email}</div>}
                  </td>
                  <td className="px-2 py-2 text-xs text-gray-400">{fmtDate(r.created_at)}</td>
                  <td className="px-2 py-2 text-xs text-gray-400">
                    {r.show_name || (r.show_id ? r.show_id.slice(0, 8) : '—')}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function UserRow({ user, token, expanded, onToggle }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadDetail = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/admin/users/${user.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setDetail(data);
    } catch {
      setDetail(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (expanded && !detail && !loading) loadDetail();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expanded]);

  return (
    <>
      <tr
        onClick={onToggle}
        className="cursor-pointer border-b border-gray-800 hover:bg-gray-800/60 transition"
        data-testid={`admin-user-row-${user.id}`}
      >
        <td className="px-3 py-2 text-gray-500">{expanded ? '▾' : '▸'}</td>
        <td className="px-3 py-2 text-white">{user.name}</td>
        <td className="px-3 py-2 text-gray-300">{user.email}</td>
        <td className="px-3 py-2 text-gray-400 text-xs">{fmtDate(user.created_at)}</td>
        <td className="px-3 py-2 text-gray-200 text-center">{user.profile_count}</td>
        <td className="px-3 py-2 text-gray-200 text-center">{user.show_count}</td>
        <td className="px-3 py-2 text-gray-200 text-center">{user.request_count}</td>
      </tr>
      {expanded && (
        <tr className="bg-gray-900/40">
          <td colSpan={7} className="px-3 py-4">
            {loading && <p className="text-gray-400">Loading detail…</p>}
            {!loading && detail && (
              <div data-testid={`admin-user-detail-${user.id}`}>
                <div className="flex flex-wrap gap-4 text-xs text-gray-400 mb-3">
                  <span>
                    Profiles: <span className="text-white">{detail.profiles.length}</span>
                  </span>
                  <span>
                    Unassigned requests:{' '}
                    <span className="text-yellow-400">{detail.unassigned_request_count}</span>
                  </span>
                </div>

                <div className="space-y-3">
                  {detail.profiles.length === 0 && (
                    <p className="text-gray-500 text-sm italic">No profiles</p>
                  )}
                  {detail.profiles.map((p) => (
                    <div key={p.id} className="bg-gray-800 border border-gray-700 rounded p-3">
                      <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
                        <div>
                          <span className="text-white font-medium">{p.name}</span>
                          {p.is_default && (
                            <span className="ml-2 text-[10px] uppercase bg-purple-600/40 text-purple-200 px-1.5 py-0.5 rounded">
                              default
                            </span>
                          )}
                          <span className="ml-2 text-xs text-gray-500">/{p.slug}</span>
                        </div>
                        <span className="text-xs text-gray-400">
                          {p.shows.length} show{p.shows.length === 1 ? '' : 's'}
                        </span>
                      </div>
                      {p.shows.length === 0 ? (
                        <p className="text-xs text-gray-500 italic">No shows</p>
                      ) : (
                        <ul className="text-xs text-gray-300 space-y-1">
                          {p.shows.map((s) => (
                            <li key={s.id} className="flex items-center justify-between gap-2">
                              <span className="truncate">
                                {s.name}
                                {s.date ? ` · ${s.date}` : ''}
                              </span>
                              <span className="text-gray-500 whitespace-nowrap">
                                {s.request_count} req · {s.status}
                              </span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>

                <DataActionsPanel
                  token={token}
                  musician={detail}
                  onActionDone={loadDetail}
                />
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function AdminDashboard({ token, onLogout }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('');
  const [expandedId, setExpandedId] = useState(null);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await axios.get(`${API}/admin/users`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setUsers(data.users || []);
    } catch (err) {
      if (err.response?.status === 401) {
        sessionStorage.removeItem(ADMIN_TOKEN_KEY);
        onLogout();
        return;
      }
      setError(err.response?.data?.detail || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = useMemo(() => {
    if (!filter.trim()) return users;
    const q = filter.toLowerCase();
    return users.filter(
      (u) =>
        (u.name || '').toLowerCase().includes(q) || (u.email || '').toLowerCase().includes(q)
    );
  }, [users, filter]);

  return (
    <div className="min-h-screen bg-gray-900 text-white" data-testid="admin-dashboard">
      <header className="bg-gray-950 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold">Admin Panel</h1>
          <p className="text-xs text-gray-400">RequestWave</p>
        </div>
        <button
          type="button"
          onClick={onLogout}
          className="text-sm text-gray-300 hover:text-white px-3 py-1 border border-gray-700 rounded transition"
          data-testid="admin-logout-btn"
        >
          Sign out
        </button>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between gap-3 mb-4">
          <h2 className="text-base font-semibold">Users ({users.length})</h2>
          <input
            type="text"
            placeholder="Filter by name or email…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm w-72 focus:outline-none focus:border-purple-500"
            data-testid="admin-user-filter"
          />
        </div>

        {error && <p className="text-red-400 text-sm mb-3">{error}</p>}

        <div className="bg-gray-800/40 border border-gray-700 rounded-lg overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-800/80 text-xs uppercase tracking-wide text-gray-400">
              <tr>
                <th className="px-3 py-2 w-8"></th>
                <th className="px-3 py-2 text-left">Name</th>
                <th className="px-3 py-2 text-left">Email</th>
                <th className="px-3 py-2 text-left">Registered</th>
                <th className="px-3 py-2 text-center">Profiles</th>
                <th className="px-3 py-2 text-center">Shows</th>
                <th className="px-3 py-2 text-center">Requests</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={7} className="px-3 py-4 text-center text-gray-400">
                    Loading users…
                  </td>
                </tr>
              )}
              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-3 py-4 text-center text-gray-500">
                    No users
                  </td>
                </tr>
              )}
              {!loading &&
                filtered.map((u) => (
                  <UserRow
                    key={u.id}
                    user={u}
                    token={token}
                    expanded={expandedId === u.id}
                    onToggle={() => setExpandedId(expandedId === u.id ? null : u.id)}
                  />
                ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}

export default function AdminPanel() {
  const [token, setToken] = useState(() => sessionStorage.getItem(ADMIN_TOKEN_KEY));

  const handleLogout = () => {
    sessionStorage.removeItem(ADMIN_TOKEN_KEY);
    setToken(null);
  };

  if (!token) return <AdminLogin onAuthed={setToken} />;
  return <AdminDashboard token={token} onLogout={handleLogout} />;
}
