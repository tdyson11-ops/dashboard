// ─────────────────────────────────────────────────────────────
// Cloudflare Worker: today's calendar for the dashboard.
//
// GET /  with  Authorization: Bearer <CALENDAR_KEY>
//   → { date, today: [...], tomorrow: [...], fetchedAt }
// POST /prep  (same key)  body { now, events: [...], context: {...} }
//   → { meetings: [{ id, why, actions: [...] }], model }  — prep written by Claude
//
// Secrets (set with `npx wrangler secret put …`, never in the repo):
//   CALENDAR_ICS_URL — your calendar's private iCal address
//   CALENDAR_KEY     — a long random string; the dashboard sends it to prove
//                      it's you. Without it the Worker answers 401.
//   ANTHROPIC_API_KEY — optional; turns on Claude-written prep. Without it
//                      POST /prep answers 503 and the dashboard keeps its
//                      built-in rules.
//
// Nothing is stored. Only the dashboard's own sites may call it from a
// browser (CORS), and the key is required either way.
// ─────────────────────────────────────────────────────────────
import Anthropic from '@anthropic-ai/sdk';
import { calendarToday } from './calendar.js';
import { prepWithClaude } from './prep.js';

const ALLOWED_ORIGINS = [
  'https://tdyson11-ops.github.io',
  'http://localhost:8000',
  'http://localhost:8765'
];

function cors(origin) {
  const h = {
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin'
  };
  if (ALLOWED_ORIGINS.includes(origin)) h['Access-Control-Allow-Origin'] = origin;
  return h;
}

function json(body, status, origin) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', ...cors(origin) }
  });
}

// Constant-time comparison so the key can't be guessed by timing.
function sameKey(a, b) {
  const x = new TextEncoder().encode(a), y = new TextEncoder().encode(b);
  if (x.length !== y.length) return false;
  let diff = 0;
  for (let i = 0; i < x.length; i++) diff |= x[i] ^ y[i];
  return diff === 0;
}

async function prep(request, env, origin, clean) {
  const apiKey = clean(env.ANTHROPIC_API_KEY);
  if (!apiKey) return json({ error: 'Claude is not set up on the Worker' }, 503, origin);
  const raw = await request.text();
  if (raw.length > 64 * 1024) return json({ error: 'Too much to send' }, 413, origin);
  let body;
  try { body = JSON.parse(raw); } catch (e) { return json({ error: 'Bad request' }, 400, origin); }
  try {
    const client = env.ANTHROPIC_CLIENT || new Anthropic({ apiKey });   // ANTHROPIC_CLIENT: tests only
    return json(await prepWithClaude({ client, body }), 200, origin);
  } catch (err) {
    console.error('[prep]', err);
    return json({ error: err.message || 'Claude didn’t answer' }, 502, origin);
  }
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors(origin) });
    const path = new URL(request.url).pathname.replace(/\/+$/, '');
    const isPrep = path === '/prep';
    if (request.method !== (isPrep ? 'POST' : 'GET')) return json({ error: 'Method not allowed' }, 405, origin);

    // Trim both sides: a secret piped in from PowerShell can arrive with a
    // byte-order mark or a trailing CR/LF, which would never match.
    const clean = (v) => String(v || '').replace(/^\uFEFF/, '').trim();
    const key = clean(env.CALENDAR_KEY);
    const sent = clean((request.headers.get('Authorization') || '').replace(/^\s*Bearer\s+/i, ''));
    if (key.length < 16 || !sameKey(sent, key)) return json({ error: 'Not authorised' }, 401, origin);

    if (isPrep) return prep(request, env, origin, clean);

    try {
      const data = await calendarToday({ fetchImpl: fetch, icsUrl: clean(env.CALENDAR_ICS_URL) });
      return json(data, 200, origin);
    } catch (err) {
      console.error('[calendar]', err);
      return json({ error: err.message || 'Calendar fetch failed' }, 502, origin);
    }
  }
};
