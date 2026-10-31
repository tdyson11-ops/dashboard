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

  // ── Calendar ──
  const { eventsByDay, calendarToday } = require('./calendar');
  const ICS = `BEGIN:VCALENDAR
VERSION:2.0
PRODID:test
BEGIN:VTIMEZONE
TZID:Europe/London
BEGIN:DAYLIGHT
TZOFFSETFROM:+0000
TZOFFSETTO:+0100
DTSTART:19700329T010000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
TZNAME:BST
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0100
TZOFFSETTO:+0000
DTSTART:19701025T020000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
TZNAME:GMT
END:STANDARD
END:VTIMEZONE
BEGIN:VEVENT
UID:weekly
DTSTART;TZID=Europe/London:20260902T090000
DTEND;TZID=Europe/London:20260902T093000
RRULE:FREQ=WEEKLY;BYDAY=WE
EXDATE;TZID=Europe/London:20261111T090000
SUMMARY:Site meeting
LOCATION:Plot 7
END:VEVENT
BEGIN:VEVENT
UID:weekly
RECURRENCE-ID;TZID=Europe/London:20261118T090000
DTSTART;TZID=Europe/London:20261118T140000
DTEND;TZID=Europe/London:20261118T150000
SUMMARY:Site meeting (moved)
END:VEVENT
BEGIN:VEVENT
UID:allday
DTSTART;VALUE=DATE:20261104
DTEND;VALUE=DATE:20261106
SUMMARY:Leave
END:VEVENT
BEGIN:VEVENT
UID:utc
DTSTART:20261104T170000Z
DTEND:20261104T180000Z
SUMMARY:Call with Gav
END:VEVENT
BEGIN:VEVENT
UID:cancel
STATUS:CANCELLED
DTSTART:20261104T120000Z
DTEND:20261104T130000Z
SUMMARY:Cancelled thing
END:VEVENT
END:VCALENDAR`;

  // 7. Recurring meetings keep their local time across the clocks changing,
  //    cancelled instances vanish, moved ones move, all-day spans every day
  {
    const day = (d) => eventsByDay(ICS, d, 1)[d];
    const sep = day('2026-09-09'), nov = day('2026-11-04');
    assert.deepStrictEqual(sep.map((e) => e.start), ['09:00'], 'BST weekly at 09:00');
    assert.deepStrictEqual(nov.map((e) => e.title), ['Leave', 'Site meeting', 'Call with Gav']);
    assert.strictEqual(nov[1].start, '09:00', 'still 09:00 after clocks go back');
    assert.strictEqual(nov[2].start, '17:00', 'UTC event shown in London time');
    assert.deepStrictEqual(day('2026-11-05').map((e) => e.title), ['Leave'], 'all-day covers both days');
    assert.deepStrictEqual(day('2026-11-11'), [], 'EXDATE removes the instance');
    assert.deepStrictEqual(day('2026-11-18').map((e) => e.start + ' ' + e.title), ['14:00 Site meeting (moved)']);
    console.log('7. calendar: DST, EXDATE, moved instances, all-day, cancelled     ✓');
  }

  // 8. calendarToday fetches the feed and returns today + tomorrow
  {
    let asked = null;
    const fetchImpl = async (url) => { asked = url; return { ok: true, status: 200, text: async () => ICS }; };
    const out = await calendarToday({ fetchImpl, icsUrl: 'webcal://example.com/x.ics', now: new Date('2026-11-04T08:00:00Z') });
    assert.strictEqual(asked, 'https://example.com/x.ics', 'webcal:// becomes https://');
    assert.strictEqual(out.date, '2026-11-04');
    assert.strictEqual(out.today.length, 3);
    assert.deepStrictEqual(out.tomorrow.map((e) => e.title), ['Leave']);
    await assert.rejects(calendarToday({ fetchImpl: async () => ({ ok: true, status: 200, text: async () => '<html>' }), icsUrl: 'https://x' }),
      /did not return a calendar/);
    console.log('8. calendar: fetch, webcal:// links, bad responses                ✓');
  }

  console.log('\nALL FUNCTION TESTS PASSED');
})().catch((e) => { console.error('\nFAILED:', e.message); process.exit(1); });
