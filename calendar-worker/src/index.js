// ─────────────────────────────────────────────────────────────
// Cloudflare Worker: today's calendar for the dashboard.
//
// GET /  with  Authorization: Bearer <CALENDAR_KEY>
//   → { date, today: [...], tomorrow: [...], fetchedAt }
//
// Secrets (set with `npx wrangler secret put …`, never in the repo):
//   CALENDAR_ICS_URL — your calendar's private iCal address
//   CALENDAR_KEY     — a long random string; the dashboard sends it to prove
//                      it's you. Without it the Worker answers 401.
//
// Nothing is stored. Only the dashboard's own sites may call it from a
// browser (CORS), and the key is required either way.
// ─────────────────────────────────────────────────────────────
import { calendarToday } from './calendar.js';

const ALLOWED_ORIGINS = [
  'https://tdyson11-ops.github.io',
  'http://localhost:8000',
  'http://localhost:8765'
];

function cors(origin) {
  const h = {
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Authorization',
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

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors(origin) });
    if (request.method !== 'GET') return json({ error: 'Method not allowed' }, 405, origin);

    const key = String(env.CALENDAR_KEY || '');
    const sent = (request.headers.get('Authorization') || '').replace(/^Bearer\s+/i, '');
    if (key.length < 16 || !sameKey(sent, key)) return json({ error: 'Not authorised' }, 401, origin);

    try {
      const data = await calendarToday({ fetchImpl: fetch, icsUrl: String(env.CALENDAR_ICS_URL || '').trim() });
      return json(data, 200, origin);
    } catch (err) {
      console.error('[calendar]', err);
      return json({ error: err.message || 'Calendar fetch failed' }, 502, origin);
    }
  }
};
