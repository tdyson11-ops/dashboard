// Unit tests for the WHOOP refresh logic with a fake WHOOP API and fake
// storage. Run with: node test.js   (no Firebase or network needed)
'use strict';

const assert = require('assert');
const { refreshWhoop } = require('./whoop');

const silent = { info() {}, warn() {} };

function makeWhoopApi({ validTokens, scored = true }) {
  const calls = { token: [], data: [] };
  let issued = 0;
  const fetchImpl = async (url, opts) => {
    if (url.includes('/oauth/oauth2/token')) {
      const params = new URLSearchParams(opts.body);
      calls.token.push(Object.fromEntries(params));
      const rt = params.get('refresh_token');
      if (!validTokens.has(rt)) {
        return { ok: false, status: 400, text: async () => '{"error":"invalid_request"}' };
      }
      validTokens.delete(rt);                 // single use
      const next = `ROTATED_${++issued}`;
      validTokens.add(next);
      return {
        ok: true, status: 200,
        text: async () => JSON.stringify({ access_token: 'AT_' + issued, refresh_token: next })
      };
    }
    calls.data.push(url);
    const auth = opts.headers.Authorization;
    if (!/^Bearer AT_/.test(auth)) return { ok: false, status: 401, json: async () => ({}) };
    const score =
      url.includes('recovery') ? { recovery_score: 74.6, hrv_rmssd_milli: 118.2, resting_heart_rate: 43.4 } :
      url.includes('sleep')    ? { sleep_performance_percentage: 88.7 } :
                                 { strain: 9.271 };
    return { ok: true, status: 200, json: async () => ({ records: scored ? [{ score }] : [] }) };
  };
  return { fetchImpl, calls };
}

function makeStore(initial = {}) {
  const state = { token: initial.token || null, data: initial.data || null };
  return {
    state,
    readToken: async () => state.token,
    writeToken: async (t) => { state.token = t; },
    readPrevious: async () => state.data,
    writeData: async (d) => { state.data = d; }
  };
}

(async () => {
  // 1. First run: no stored token, uses the seed secret, stores the rotation
  {
    const api = makeWhoopApi({ validTokens: new Set(['SEED']) });
    const store = makeStore();
    const out = await refreshWhoop({
      fetchImpl: api.fetchImpl, clientId: 'cid', clientSecret: 'sec',
      seedToken: 'SEED', log: silent, ...store
    });
    assert.strictEqual(api.calls.token[0].scope, 'offline', 'scope=offline must be sent');
    assert.strictEqual(api.calls.token[0].grant_type, 'refresh_token');
    assert.strictEqual(store.state.token, 'ROTATED_1', 'rotated token must be stored');
    assert.deepStrictEqual(
      { r: out.recovery, h: out.hrv, rhr: out.rhr, s: out.sleep_score, st: out.strain },
      { r: 75, h: 118, rhr: 43, s: 89, st: 9.3 }, 'rounding'
    );
    assert.ok(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(out.fetched_at), 'fetched_at format');
    assert.strictEqual(api.calls.data.length, 3, 'recovery + sleep + cycle');
    console.log('1. first run seeds, sends scope=offline, rotates and stores token  ✓');
  }

  // 2. Second run uses the STORED token, not the (now dead) seed
  {
    const api = makeWhoopApi({ validTokens: new Set(['STORED']) });
    const store = makeStore({ token: 'STORED' });
    await refreshWhoop({
      fetchImpl: api.fetchImpl, clientId: 'cid', clientSecret: 'sec',
      seedToken: 'DEAD_SEED', log: silent, ...store
    });
    assert.strictEqual(api.calls.token[0].refresh_token, 'STORED', 'must try stored token first');
    assert.strictEqual(store.state.token, 'ROTATED_1');
    console.log('2. later runs use the stored token and keep rotating             ✓');
  }

  // 3. Stored token dead -> falls back to the seed secret
  {
    const api = makeWhoopApi({ validTokens: new Set(['SEED']) });
    const store = makeStore({ token: 'STALE' });
    await refreshWhoop({
      fetchImpl: api.fetchImpl, clientId: 'cid', clientSecret: 'sec',
      seedToken: 'SEED', log: silent, ...store
    });
    assert.deepStrictEqual(api.calls.token.map(c => c.refresh_token), ['STALE', 'SEED']);
    assert.strictEqual(store.state.token, 'ROTATED_1', 'recovers and stores a fresh token');
    console.log('3. dead stored token falls back to the seed secret               ✓');
  }

  // 4. Everything rejected -> clear error, nothing written
  {
    const api = makeWhoopApi({ validTokens: new Set() });
    const store = makeStore({ token: 'STALE' });
    await assert.rejects(
      refreshWhoop({
        fetchImpl: api.fetchImpl, clientId: 'cid', clientSecret: 'sec',
        seedToken: 'ALSO_DEAD', log: silent, ...store
      }),
      /re-authorise/i
    );
    assert.strictEqual(store.state.token, 'STALE', 'must not clobber the token on failure');
    assert.strictEqual(store.state.data, null, 'must not write data on failure');
    console.log('4. all tokens rejected -> actionable error, nothing clobbered     ✓');
  }

  // 5. Unscored records fall back to the previous values, not zeroes
  {
    const api = makeWhoopApi({ validTokens: new Set(['SEED']), scored: false });
    const prev = { recovery: 66, hrv: 110, rhr: 45, sleep_score: 80, strain: 12.1 };
    const store = makeStore({ token: null, data: prev });
    const out = await refreshWhoop({
      fetchImpl: api.fetchImpl, clientId: 'cid', clientSecret: 'sec',
      seedToken: 'SEED', log: silent, ...store
    });
    assert.strictEqual(out.recovery, 66);
    assert.strictEqual(out.strain, 12.1);
    assert.notStrictEqual(out.fetched_at, undefined);
    console.log('5. pending WHOOP scores keep the last known numbers              ✓');
  }

  // 6. The token is persisted even if fetching the data then fails
  {
    const api = makeWhoopApi({ validTokens: new Set(['SEED']) });
    const store = makeStore();
    const boom = async (url, opts) => {
      if (url.includes('/oauth/')) return api.fetchImpl(url, opts);
      throw new Error('network went away');
    };
    await assert.rejects(refreshWhoop({
      fetchImpl: boom, clientId: 'cid', clientSecret: 'sec',
      seedToken: 'SEED', log: silent, ...store
    }), /network went away/);
    assert.strictEqual(store.state.token, 'ROTATED_1',
      'rotated token must survive a later failure or the chain breaks');
    console.log('6. rotated token survives a failure after the refresh            ✓');
  }

  console.log('\nALL FUNCTION TESTS PASSED');
})().catch((e) => { console.error('\nFAILED:', e.message); process.exit(1); });
