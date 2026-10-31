// ─────────────────────────────────────────────────────────────
// Today's calendar for the dashboard.
//
// Reads a calendar's private iCal (.ics) address — Google Calendar's
// "Secret address in iCal format" or Outlook's published ICS link — and
// returns the events for today and tomorrow in Europe/London. Recurring
// meetings, cancelled instances (EXDATE), moved instances (RECURRENCE-ID)
// and the clocks changing are all handled by node-ical.
//
// Pure logic, no Firebase: index.js wires it up, test.js exercises it.
// ─────────────────────────────────────────────────────────────
'use strict';

const ical = require('node-ical');

const TZ = 'Europe/London';
const DAY_MS = 86400000;

// 'YYYY-MM-DD' for an instant, as seen in London.
function londonDay(date) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit'
  }).format(date);
}

// 'HH:MM' for an instant, as seen in London.
function londonTime(date) {
  return new Intl.DateTimeFormat('en-GB', {
    timeZone: TZ, hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
  }).format(date);
}

// The calendar day an all-day value falls on. node-ical keeps the original
// instant and, when given, its timezone; floating dates are read in UTC.
function allDayKey(date) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: date.tz || 'UTC', year: 'numeric', month: '2-digit', day: '2-digit'
  }).format(date);
}

function addDays(dayKey, n) {
  const d = new Date(dayKey + 'T12:00:00Z');
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function text(v) {
  if (v == null) return '';
  if (typeof v === 'string') return v;
  if (typeof v === 'object' && 'val' in v) return String(v.val);
  return String(v);
}

// Events on `days` London calendar days starting at `fromDay`, grouped by day.
// Returns { 'YYYY-MM-DD': [{ title, start, end, allDay, location }] }.
function eventsByDay(icsText, fromDay, days) {
  const wanted = [];
  for (let i = 0; i < days; i++) wanted.push(addDays(fromDay, i));
  const out = {};
  wanted.forEach((k) => { out[k] = []; });

  // Generous window (a day either side) so nothing is lost to time zones;
  // each instance is then placed on its London day below.
  const from = new Date(new Date(fromDay + 'T00:00:00Z').getTime() - DAY_MS);
  const to = new Date(new Date(addDays(fromDay, days) + 'T00:00:00Z').getTime() + DAY_MS);

  const parsed = ical.sync.parseICS(icsText);
  for (const ev of Object.values(parsed)) {
    if (!ev || ev.type !== 'VEVENT' || !ev.start) continue;
    if (String(ev.status || '').toUpperCase() === 'CANCELLED') continue;

    let instances;
    try {
      instances = ical.expandRecurringEvent(ev, { from, to, expandOngoing: true });
    } catch (e) {
      instances = [];
    }

    for (const inst of instances) {
      const title = text(inst.summary || ev.summary) || '(no title)';
      const location = text((inst.event && inst.event.location) || ev.location);
      const start = inst.start;
      const end = inst.end || start;

      if (inst.isFullDay) {
        // All-day: list it on every day it covers (end is exclusive).
        const first = allDayKey(start);
        let last = allDayKey(end);
        if (last > first) last = addDays(last, -1);
        wanted.forEach((k) => {
          if (k >= first && k <= last) out[k].push({ title, start: null, end: null, allDay: true, location });
        });
        continue;
      }

      // Timed: show on each London day it overlaps.
      const sDay = londonDay(start);
      const eDay = londonDay(new Date(end.getTime() - 1));
      wanted.forEach((k) => {
        if (k < sDay || k > eDay) return;
        out[k].push({
          title,
          start: k === sDay ? londonTime(start) : '00:00',
          end: k === eDay ? londonTime(end) : '24:00',
          allDay: false,
          location
        });
      });
    }
  }

  wanted.forEach((k) => {
    // De-duplicate (an override can appear alongside its parent) and sort:
    // all-day first, then by start time.
    const seen = new Set();
    out[k] = out[k].filter((e) => {
      const id = [e.title, e.start, e.end, e.allDay].join('|');
      if (seen.has(id)) return false;
      seen.add(id);
      return true;
    }).sort((a, b) => {
      if (a.allDay !== b.allDay) return a.allDay ? -1 : 1;
      return String(a.start).localeCompare(String(b.start)) || a.title.localeCompare(b.title);
    });
  });
  return out;
}

// Fetch the .ics and return today + tomorrow (London).
async function calendarToday({ fetchImpl, icsUrl, now = new Date() }) {
  if (!icsUrl) throw new Error('No calendar address set (CALENDAR_ICS_URL).');
  const url = icsUrl.replace(/^webcal:\/\//i, 'https://');
  const res = await fetchImpl(url, { headers: { Accept: 'text/calendar' } });
  if (!res.ok) throw new Error('Calendar fetch failed: HTTP ' + res.status);
  const body = await res.text();
  if (!/BEGIN:VCALENDAR/.test(body)) throw new Error('That address did not return a calendar.');

  const today = londonDay(now);
  const tomorrow = addDays(today, 1);
  const byDay = eventsByDay(body, today, 2);
  return {
    date: today,
    today: byDay[today],
    tomorrow: byDay[tomorrow],
    fetchedAt: now.toISOString()
  };
}

module.exports = { calendarToday, eventsByDay, londonDay };
