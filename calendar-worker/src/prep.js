// ─────────────────────────────────────────────────────────────
// "Prep for what's coming up", written by Claude.
//
// The dashboard posts the upcoming meetings plus what it already knows
// (People, Waiting on, Focus, Business pulse, deadlines, notes) and gets
// back, per meeting, a short reason and 2–4 concrete things to do first.
// ─────────────────────────────────────────────────────────────

export const PREP_MODEL = 'claude-opus-5-5';

const SYSTEM = `You are the chief-of-staff behind Tom Dyson's personal dashboard. Tom works in UK housebuilding \
(sites, plots, NHBC/building control, H&S, trades and suppliers, customers, cash and the build programme), \
is aiming to be an MD by 2030, and is studying part-time at university.

You get the meetings in his diary for the next 7 days (each with its date and weekday), plus what his \
dashboard knows: people he tracks and the next thing to raise with each, what people owe him (Waiting on), \
his Focus list, Business pulse numbers, uni deadlines and his notes.

Look across the whole week and pick the meetings worth preparing for — usually no more than 8, the ones \
where prep changes the outcome. For each, suggest 2–4 specific things Tom can do BEFORE it starts so he \
walks in ready. Good suggestions:
- are concrete actions he can do himself, starting with a verb ("Ask Gav for the revised plot 7 programme", \
not "Think about the programme");
- use the context: chase what someone in the meeting owes him, raise his noted point with them, tie in a \
Focus item, pulse number, deadline or note that is relevant, flag a clash or tight gap between meetings;
- think about lead time across the week: if something has to be requested, booked, drafted or chased days \
ahead for a later meeting to go well, say when ("By Mon: ask the QS for the updated valuation"); a meeting \
in 30 minutes gets quick wins only;
- link meetings that belong together (a site walk before a board meeting, a supplier call before a customer \
handover) rather than repeating the same action;
- are short (under 110 characters each), British English, no filler.

Never invent facts, names or numbers that aren't in the input. Ignore meetings that have already finished. \
Leave out meetings that need no prep (personal blocks, lunch, travel time, routine stand-ups with nothing \
relevant in the context), and all-day events unless they change what he should do. "why" is a few words \
saying what the meeting is or why it matters (e.g. "NHBC inspection · Gav owes you the snag list").`;

const SCHEMA = {
  type: 'object',
  properties: {
    meetings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'The id of the meeting, exactly as given' },
          why: { type: 'string' },
          actions: { type: 'array', items: { type: 'string' } }
        },
        required: ['id', 'why', 'actions'],
        additionalProperties: false
      }
    }
  },
  required: ['meetings'],
  additionalProperties: false
};

// Keep what the phone sends small and well-formed before it goes anywhere.
const str = (v, n) => String(v == null ? '' : v).slice(0, n);
const list = (v, n) => (Array.isArray(v) ? v.slice(0, n) : []);

export function cleanInput(body) {
  const b = body && typeof body === 'object' ? body : {};
  const c = b.context && typeof b.context === 'object' ? b.context : {};
  const events = list(b.events, 80).map((e) => ({
    id: str(e && e.id, 20), date: str(e && e.date, 10), day: str(e && e.day, 20), start: str(e && e.start, 5), end: str(e && e.end, 5),
    allDay: !!(e && e.allDay), title: str(e && e.title, 160), location: str(e && e.location, 160)
  })).filter((e) => e.id && e.title);
  const ctx = {
    now: str(b.now, 40),
    people: list(c.people, 30).map((p) => ({ name: str(p.name, 60), next: str(p.next, 200), lastSpoke: str(p.lastSpoke, 30) })),
    waitingOn: list(c.waiting, 30).map((w) => ({ who: str(w.who, 60), what: str(w.what, 200), asked: str(w.asked, 30) })),
    focus: list(c.focus, 20).map((f) => str(f, 200)),
    pulse: list(c.pulse, 10).map((p) => ({ label: str(p.label, 40), value: str(p.value, 40), note: str(p.note, 120), status: str(p.status, 10) })),
    deadlines: list(c.deadlines, 8).map((d) => ({ name: str(d.name, 100), module: str(d.module, 60), date: str(d.date, 10) })),
    notes: list(c.notes, 6).map((n) => ({ name: str(n.name, 40), text: str(n.text, 1200) }))
  };
  return { events, ctx };
}

export async function prepWithClaude({ client, body }) {
  const { events, ctx } = cleanInput(body);
  if (!events.length) return { meetings: [], model: PREP_MODEL };

  const response = await client.beta.messages.create({
    model: PREP_MODEL,
    max_tokens: 16000,
    betas: ['server-side-fallback-2026-07-01'],
    fallbacks: 'default',
    output_config: { effort: 'medium', format: { type: 'json_schema', schema: SCHEMA } },
    system: SYSTEM,
    messages: [{
      role: 'user',
      content: 'It is now ' + (ctx.now || 'unknown') + ' (Europe/London).\n\n' +
        '<meetings>\n' + JSON.stringify(events, null, 1) + '\n</meetings>\n\n' +
        '<dashboard>\n' + JSON.stringify({ ...ctx, now: undefined }, null, 1) + '\n</dashboard>'
    }]
  });

  if (response.stop_reason === 'refusal') throw new Error('Claude declined this one');
  if (response.stop_reason === 'max_tokens') throw new Error('Claude’s answer was cut short');
  const text = (response.content || []).filter((b) => b.type === 'text').map((b) => b.text).join('');
  let parsed;
  try { parsed = JSON.parse(text); } catch (e) { throw new Error('Claude’s answer wasn’t readable'); }

  const ids = new Set(events.map((e) => e.id));
  const meetings = list(parsed && parsed.meetings, 10)
    .filter((m) => m && ids.has(m.id))
    .map((m) => ({ id: m.id, why: str(m.why, 120), actions: list(m.actions, 4).map((a) => str(a, 200)).filter(Boolean) }))
    .filter((m) => m.actions.length);
  return { meetings, model: response.model || PREP_MODEL };
}
