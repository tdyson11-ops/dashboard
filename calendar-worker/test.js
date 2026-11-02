// Tests for the calendar Worker. Run with: npm test   (no network needed)
import assert from 'node:assert';
import { eventsByDay, calendarToday } from './src/calendar.js';
import worker from './src/index.js';

(async () => {
  // ── Calendar ──
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
    console.log('1. calendar: DST, EXDATE, moved instances, all-day, cancelled     ✓');
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
    console.log('2. calendar: fetch, webcal:// links, bad responses                ✓');
  }

  // 3. The Worker refuses requests without the right key, allows the dashboard's origin
  {
    const env = { CALENDAR_KEY: 'k'.repeat(32), CALENDAR_ICS_URL: 'https://example.com/x.ics' };
    const realFetch = globalThis.fetch;
    globalThis.fetch = async () => ({ ok: true, status: 200, text: async () => ICS });
    try {
      const req = (auth, origin = 'https://tdyson11-ops.github.io') =>
        new Request('https://w.example/', { headers: { ...(auth ? { Authorization: auth } : {}), Origin: origin } });
      assert.strictEqual((await worker.fetch(req(null), env)).status, 401, 'no key');
      assert.strictEqual((await worker.fetch(req('Bearer wrong'), env)).status, 401, 'wrong key');
      const ok = await worker.fetch(req('Bearer ' + env.CALENDAR_KEY), env);
      assert.strictEqual(ok.status, 200);
      assert.strictEqual(ok.headers.get('Access-Control-Allow-Origin'), 'https://tdyson11-ops.github.io');
      assert.ok(Array.isArray((await ok.json()).today));
      const other = await worker.fetch(req('Bearer ' + env.CALENDAR_KEY, 'https://evil.example'), env);
      assert.strictEqual(other.headers.get('Access-Control-Allow-Origin'), null, 'other sites get no CORS');
      assert.strictEqual((await worker.fetch(req('Bearer ' + 'k'.repeat(32)), { ...env, CALENDAR_KEY: '' })).status, 401, 'unset key locks it');
      const piped = { ...env, CALENDAR_KEY: '\uFEFF' + env.CALENDAR_KEY + '\r\n', CALENDAR_ICS_URL: '\uFEFF' + env.CALENDAR_ICS_URL + '\r\n' };
      assert.strictEqual((await worker.fetch(req('Bearer ' + env.CALENDAR_KEY), piped)).status, 200, 'secret piped from PowerShell (BOM + CRLF) still matches');
      assert.strictEqual((await worker.fetch(req('Bearer ' + env.CALENDAR_KEY + ' '), env)).status, 200, 'stray space from the phone still matches');
    } finally { globalThis.fetch = realFetch; }
    console.log('3. worker: key required (whitespace-tolerant), CORS only for site ✓');
  }

  console.log('\nALL CALENDAR TESTS PASSED');
})().catch((e) => { console.error('\nFAILED:', e.message); process.exit(1); });
