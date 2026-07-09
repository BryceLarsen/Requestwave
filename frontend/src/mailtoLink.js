// mailtoLink.js
// Pure helpers for the Requests-tab "tap a requester's email to write to them" flow.
// No React, no network, no DOM. Input in, string out.

export const DEFAULT_TEMPLATE = {
  subject: "{show}",
  body: [
    "Hi {name},",
    "",
    "Thanks for putting in a request at {show}. Requests actually change what I play, so you had a hand in how it went.",
    "",
    "I'm Bryce. I run Adventure Sound Live, and I was the guy singing.",
    "",
    "If you feel like it, reply with a song or an artist you've been listening to lately. I'm always building the repertoire and I get most of my best ideas this way.",
    "",
    "Glad you were there,",
    "",
    "Bryce",
  ].join("\n"),
};

// Shown in the editor so you never have to remember what is available.
export const TEMPLATE_TOKENS = ["{name}", "{show}", "{song}", "{venue}"];

// Fallbacks keep a missing value from leaving a raw {token} in the message.
const FALLBACKS = {
  name: "there",
  song: "a song",
  show: "the party",
  venue: "the party",
};

export function cpFirstName(fullName) {
  if (typeof fullName !== "string") return "";
  return fullName.trim().split(/\s+/)[0] || "";
}

// Replaces {name} {song} {show} {venue}. Unknown tokens are left alone on
// purpose, so a typo shows up in the compose window instead of vanishing.
export function fillTemplate(text, vars) {
  if (typeof text !== "string") return "";
  const v = vars || {};
  return text.replace(/\{(name|song|show|venue)\}/g, (match, key) => {
    const raw = v[key];
    const val = typeof raw === "string" ? raw.trim() : "";
    return val || FALLBACKS[key];
  });
}

// encodeURIComponent leaves ! ' ( ) * unescaped. Some mail clients choke on
// those inside a mailto query, so escape them too. Newlines become %0A.
function enc(s) {
  return encodeURIComponent(String(s)).replace(
    /[!'()*]/g,
    (c) => "%" + c.charCodeAt(0).toString(16).toUpperCase()
  );
}

const MAX_URL = 1800; // conservative. Some clients truncate past ~2000.

// Returns { href, tooLong, subject, body } or null when there is no usable email.
export function buildMailto(opts) {
  const o = opts || {};
  const email = typeof o.email === "string" ? o.email.trim() : "";
  if (!email || !email.includes("@")) return null;

  const tpl = o.template || DEFAULT_TEMPLATE;
  const vars = {
    name: cpFirstName(o.requesterName),
    song: o.songTitle,
    show: o.showName,
    venue: o.venue,
  };

  const subject = fillTemplate(tpl.subject, vars);
  const body = fillTemplate(tpl.body, vars);
  const href =
    "mailto:" + enc(email) + "?subject=" + enc(subject) + "&body=" + enc(body);

  return { href, tooLong: href.length > MAX_URL, subject, body };
}
