import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { DEFAULT_TEMPLATE } from './mailtoLink';

/*
 * emailTemplateEditor.jsx
 * -----------------------------------------------------------------------------
 * Account Settings section that lets a musician edit the email template used by
 * the Requests-tab "tap a requester's email" mailto flow. Self-contained: it owns
 * its own draft state, its own save call, and its own status message, so App.js
 * only has to import it and render it.
 *
 * Props:
 *   profile  : the musician profile object from GET /profile. Reads
 *              profile.email_template_subject and profile.email_template_body.
 *   onSaved  : (updatedProfile) => void. Called with the PUT /profile response so
 *              the parent can keep its own profile state in sync. Optional.
 *
 * Storage contract (matches the backend):
 *   empty string  = this musician has not set a template; the app falls back to
 *                   DEFAULT_TEMPLATE at the point of use.
 *   non-empty     = custom.
 *
 * The textarea PRE-FILLS with DEFAULT_TEMPLATE when nothing custom is stored, so
 * the musician edits real text instead of retyping a message from scratch. This
 * is deliberate: it is how a new musician discovers and replaces the default
 * signature rather than silently sending it.
 */

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Tokens offered in the UI. {venue} is intentionally NOT offered: no surface in
// the app sets Show.venue, so it would always resolve to its fallback.
const TOKENS = ['{name}', '{song}', '{show}', '{artist}'];

export default function EmailTemplateEditor({ profile, onSaved }) {
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState({ type: '', text: '' });
  const bodyRef = useRef(null);

  // Load the stored template, falling back to the default text so the box is
  // never blank. Re-syncs if the profile arrives or changes underneath us.
  useEffect(() => {
    setSubject(profile?.email_template_subject || DEFAULT_TEMPLATE.subject);
    setBody(profile?.email_template_body || DEFAULT_TEMPLATE.body);
    setMsg({ type: '', text: '' });
  }, [profile?.email_template_subject, profile?.email_template_body]);

  const insertToken = (tok) => {
    const el = bodyRef.current;
    if (!el) {
      setBody((prev) => (prev || '') + tok);
      return;
    }
    const start = el.selectionStart ?? (body || '').length;
    const end = el.selectionEnd ?? start;
    const next = (body || '').slice(0, start) + tok + (body || '').slice(end);
    setBody(next);
    // Restore the caret after the inserted token so you can keep typing.
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(start + tok.length, start + tok.length);
    });
  };

  const handleSave = async () => {
    setSaving(true);
    setMsg({ type: '', text: '' });
    try {
      const res = await axios.put(`${API}/profile`, {
        ...profile,
        email_template_subject: subject,
        email_template_body: body,
      });
      if (onSaved) onSaved(res.data);
      setMsg({ type: 'success', text: 'Template saved.' });
    } catch (err) {
      setMsg({ type: 'error', text: 'Could not save the template. Please try again.' });
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setSubject(DEFAULT_TEMPLATE.subject);
    setBody(DEFAULT_TEMPLATE.body);
    setMsg({ type: '', text: 'Default message restored. Tap Save to keep it.' });
  };

  return (
    <div className="border-t border-gray-700 pt-6" data-testid="email-template-editor">
      <label className="block text-gray-300 text-sm font-bold mb-2">Request Email Template</label>
      <p className="text-gray-400 text-xs mb-4 leading-relaxed">
        On the Requests tab, tapping a requester's email opens your mail app with this message ready to send. Write it in your own voice.
      </p>

      <p className="text-gray-400 text-xs mb-2">Tap to insert. These fill in automatically for each requester.</p>
      <div className="flex flex-wrap gap-2 mb-4">
        {TOKENS.map((tok) => (
          <button
            key={tok}
            type="button"
            data-testid={`email-template-token-${tok.replace(/[{}]/g, '')}`}
            onClick={() => insertToken(tok)}
            className="bg-gray-700 hover:bg-gray-600 border border-gray-600 rounded-md px-2.5 py-1 text-xs font-mono text-purple-300 transition"
          >
            {tok}
          </button>
        ))}
      </div>

      <label className="block text-gray-300 text-sm font-bold mb-2">Subject</label>
      <input
        type="text"
        data-testid="email-template-subject-input"
        value={subject}
        onChange={(e) => setSubject(e.target.value)}
        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400 mb-4"
        placeholder={DEFAULT_TEMPLATE.subject}
      />

      <label className="block text-gray-300 text-sm font-bold mb-2">Message</label>
      <textarea
        ref={bodyRef}
        rows={11}
        data-testid="email-template-body-input"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400 text-sm leading-relaxed mb-4"
        placeholder={DEFAULT_TEMPLATE.body}
      />

      <div className="flex items-center gap-2">
        <button
          type="button"
          data-testid="email-template-save-btn"
          onClick={handleSave}
          disabled={saving}
          className="bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 px-4 py-2 rounded-lg font-bold text-sm transition duration-300"
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
        <button
          type="button"
          data-testid="email-template-reset-btn"
          onClick={handleReset}
          className="border border-gray-600 hover:bg-gray-700 text-gray-300 px-4 py-2 rounded-lg font-bold text-sm transition duration-300"
        >
          Reset to default
        </button>
      </div>

      {msg.text && (
        <p
          data-testid="email-template-msg"
          className={`mt-2 text-xs ${msg.type === 'error' ? 'text-red-400' : msg.type === 'success' ? 'text-green-400' : 'text-gray-400'}`}
        >
          {msg.text}
        </p>
      )}
    </div>
  );
}
