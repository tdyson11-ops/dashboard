// ─────────────────────────────────────────────────────────────
// WHOOP refresh logic, kept free of Firebase imports so it can be
// unit-tested with plain fakes (see test.js).
//
// Mirrors update_whoop.py: WHOOP refresh tokens are SINGLE USE, so every
// refresh returns a new one and invalidates the old. The rotated token is
// persisted before anything else can fail, otherwise the chain breaks and
// you have to re-authorise by hand.
// ─────────────────────────────────────────────────────────────
'use strict';

const TOKEN_URL = 'https://api.prod.whoop.com/oauth/oauth2/token';
const API = 'https://api.prod.whoop.com/developer/v2';

async function exchangeToken(fetchImpl, refreshToken, clientId, clientSecret) {
  const res = await fetchImpl(TOKEN_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    // scope=offline is required by WHOOP on refresh; without it the request
    // is rejected as malformed.
    body: new URLSearchParams({
      grant_type: 'refresh_token',
      refresh_token: refreshToken,
      client_id: clientId,
      client_secret: clientSecret,
      scope: 'offline'
    }).toString()
  });
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch (e) { /* non-JSON error body */ }
  return { ok: res.ok, status: res.status, body: text, json: json };
}

// Most recent record's `score`, or null while WHOOP still has it pending.
async function latestScore(fetchImpl, path, accessToken) {
  const res = await fetchImpl(`${API}/${path}?limit=1`, {
    headers: { Authorization: `Bearer ${accessToken}` }
  });
  if (!res.ok) throw new Error(`${path} returned ${res.status}`);
  const body = await res.json();
  const records = (body && body.records) || [];
  return records.length ? (records[0].score || null) : null;
}

function round1(n) { return Math.round(n * 10) / 10; }
function nowIso() { return new Date().toISOString().replace(/\.\d+Z$/, 'Z'); }

/**
 * Refresh WHOOP data.
 *
 * @param {object} deps
 *   fetchImpl    - fetch-compatible function
 *   clientId     - WHOOP client id
 *   clientSecret - WHOOP client secret
 *   seedToken    - refresh token from config, used only until one is stored
 *   readToken    - async () => stored refresh token or null
 *   writeToken   - async (token) => persist the rotated token
 *   readPrevious - async () => last stored whoop object (for fallbacks)
 *   writeData    - async (whoop) => persist the new numbers
 *   log          - { info, warn }
 */
async function refreshWhoop(deps) {
  const log = deps.log || { info() {}, warn() {} };

  const candidates = [];
  const stored = await deps.readToken();
  if (stored) candidates.push(['stored', stored]);
  if (deps.seedToken && deps.seedToken !== stored) candidates.push(['seed secret', deps.seedToken]);
  if (!candidates.length) throw new Error('No WHOOP refresh token available — set the WHOOP_REFRESH_TOKEN secret.');

  let tokens = null;
  for (const [source, token] of candidates) {
    const res = await exchangeToken(deps.fetchImpl, token, deps.clientId, deps.clientSecret);
    if (res.ok && res.json && res.json.access_token) {
      log.info(`[whoop] refreshed using the ${source} token`);
      tokens = res.json;
      break;
    }
    log.warn(`[whoop] ${source} token rejected (${res.status}): ${res.body}`);
  }
  if (!tokens) {
    throw new Error('All WHOOP refresh tokens were rejected — re-authorise and update WHOOP_REFRESH_TOKEN.');
  }

  // Persist the rotated token immediately. If a later step throws, the chain
  // still survives; losing this is what breaks the integration for good.
  if (tokens.refresh_token) await deps.writeToken(tokens.refresh_token);

  const prev = (await deps.readPrevious()) || {};
  const [rec, slp, cyc] = await Promise.all([
    latestScore(deps.fetchImpl, 'recovery', tokens.access_token),
    latestScore(deps.fetchImpl, 'activity/sleep', tokens.access_token),
    latestScore(deps.fetchImpl, 'cycle', tokens.access_token)
  ]);

  // Keep the last known value when a record is briefly unscored, so a WHOOP
  // blip never blanks the dashboard.
  const whoop = {
    recovery:    rec ? Math.round(rec.recovery_score)                : (prev.recovery || 0),
    hrv:         rec ? Math.round(rec.hrv_rmssd_milli)               : (prev.hrv || 0),
    rhr:         rec ? Math.round(rec.resting_heart_rate)            : (prev.rhr || 0),
    sleep_score: slp ? Math.round(slp.sleep_performance_percentage)  : (prev.sleep_score || 0),
    strain:      cyc ? round1(cyc.strain)                            : (prev.strain || 0),
    fetched_at:  nowIso()
  };

  await deps.writeData(whoop);
  log.info(`[whoop] recovery=${whoop.recovery}% hrv=${whoop.hrv}ms rhr=${whoop.rhr}bpm ` +
           `sleep=${whoop.sleep_score}% strain=${whoop.strain}`);
  return whoop;
}

module.exports = { refreshWhoop, exchangeToken, latestScore };
