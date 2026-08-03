#!/usr/bin/env python3
"""
Side-hustle engine — the part of the business that runs without you.

Two modes:

  python3 hustle_engine.py outreach
      Reads the lead list, and for every lead marked `new` writes a genuine
      sample article for that specific business plus a short personalised
      email. Drops both in outbox/ for you to read and send. Never sends
      anything itself — cold email goes out from your hands, not a robot's.

  python3 hustle_engine.py deliver
      For every active client, writes the month's content pack (blog posts,
      social captions, Google Business posts, newsletter) into clients/, and
      optionally pushes the posts to their WordPress site as drafts.

Both modes update hustle.json so the dashboard shows what happened.

Requires ANTHROPIC_API_KEY. Lead list lives outside the repo — see README.
"""

import argparse
import base64
import csv
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "hustle.json"
LEADS_PATH = Path(os.environ.get("LEADS_CSV_PATH", ROOT / "leads.csv"))
OUTBOX = ROOT / "outbox"
CLIENTS_DIR = ROOT / "clients"

LEAD_FIELDS = [
    "business", "contact", "email", "town",
    "website", "focus", "status", "notes",
]


# ── plumbing ──────────────────────────────────────────────────────────

def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(cfg):
    cfg["updated"] = dt.date.today().isoformat()
    CONFIG_PATH.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug or "untitled"


def today():
    return dt.date.today()


def ask(client, cfg, system, prompt, max_tokens=16000, schema=None):
    """One Claude call. Streams so long packs don't hit the request timeout."""
    output_config = {"effort": cfg["settings"].get("effort", "medium")}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}

    with client.messages.stream(
        model=cfg["settings"].get("model", "claude-opus-5"),
        max_tokens=max_tokens,
        system=system,
        output_config=output_config,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        message = stream.get_final_message()

    if message.stop_reason == "refusal":
        raise RuntimeError("request was declined by the model's safety classifiers")

    text = next((b.text for b in message.content if b.type == "text"), "")
    return json.loads(text) if schema else text.strip()


# ── the voice ─────────────────────────────────────────────────────────

BRAND = """You write marketing content for independent UK gyms, personal-training
studios and sports-therapy clinics. You are ghostwriting AS the business owner.

Rules that matter more than anything else:
- Write like a coach talking to a member, not like a marketing agency. Short
  sentences. Second person. No "unlock your potential", no "in today's fast-paced
  world", no "elevate", no emoji walls, no exclamation marks in body copy.
- Be specific and locally grounded: name the town, the streets, the local
  parkrun, the weather, the commute. Generic content is worthless for local search.
- Every claim must be defensible. Never invent statistics, studies, prices,
  opening hours, staff names, or client results. If a specific fact would help
  but you do not have it, write around it or leave an obvious [BRACKETED NOTE]
  for the owner to fill in.
- No medical claims. Training and nutrition guidance stays general and sensible,
  and points anyone with pain or a condition towards a qualified professional.
- British English throughout. Metric. £."""


def biz_brief(name, town, focus, website=""):
    lines = [f"Business: {name}", f"Town: {town}", f"What they do: {focus}"]
    if website:
        lines.append(f"Website: {website}")
    return "\n".join(lines)


# ── outreach ──────────────────────────────────────────────────────────

SAMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "email_body": {"type": "string"},
        "article_title": {"type": "string"},
        "article_markdown": {"type": "string"},
    },
    "required": ["subject", "email_body", "article_title", "article_markdown"],
    "additionalProperties": False,
}


def read_leads():
    if not LEADS_PATH.exists():
        return []
    with LEADS_PATH.open(newline="", encoding="utf-8-sig") as f:
        return [dict(row) for row in csv.DictReader(f)]


def write_leads(rows):
    LEADS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEADS_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LEAD_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in LEAD_FIELDS})


def cmd_outreach(cfg, client):
    leads = read_leads()
    if not leads:
        print(f"No leads found at {LEADS_PATH} — nothing to do.")
        return 0

    pending = [r for r in leads if (r.get("status") or "new").strip().lower() == "new"]
    limit = int(cfg["settings"].get("outreach_per_run", 4))
    batch = pending[:limit]

    if not batch:
        print(f"No leads with status 'new' ({len(leads)} in the list).")
        return 0

    sender = cfg["settings"].get("sender", {})
    offer = cfg["offer"]
    done = 0

    for lead in batch:
        name = (lead.get("business") or "").strip()
        town = (lead.get("town") or "").strip()
        focus = (lead.get("focus") or "gym and personal training").strip()
        contact = (lead.get("contact") or "there").strip()
        if not name:
            continue

        prompt = f"""{biz_brief(name, town, focus, lead.get('website', ''))}

Write two things.

1. A complete, genuinely useful 900-word article this business could publish
   on their own site tomorrow. Pick a topic their actual local customers would
   search for — something tied to {town} and to {focus}. This is a free sample
   given away with no strings, so it has to be good enough that they would have
   paid for it. Markdown, with a clear H1 and sensible H2s.

2. A cold email from {sender.get('name', 'me')} to {contact} at {name}, offering
   the article for free with no conditions.

   The email must:
   - be under 120 words, plain text, no formatting, no links
   - open with something specific and true about {name} or about running a gym
     in {town} — never "I hope this email finds you well"
   - say plainly that a free article is attached below, theirs to use whether or
     not they ever reply
   - mention in one sentence that the sender does this monthly for gyms —
     {offer['price']} pounds a month for {offer['deliverables'][0]} plus social
     and Google Business posts — and ask a single easy question
   - end with one line offering to be removed from the list, since this is a
     cold approach to a business
   - sound like a 20-year-old who lifts, not like an agency

   Do not invent anything about their business you were not told."""

        try:
            out = ask(client, cfg, BRAND, prompt, schema=SAMPLE_SCHEMA)
        except Exception as e:                                  # noqa: BLE001
            print(f"  ! {name}: {e}", file=sys.stderr)
            lead["notes"] = f"generation failed: {e}"
            continue

        folder = OUTBOX / f"{today():%Y-%m-%d}-{slugify(name)}"
        folder.mkdir(parents=True, exist_ok=True)

        (folder / "email.txt").write_text(
            f"To: {lead.get('email', '')}\n"
            f"Subject: {out['subject']}\n\n"
            f"{out['email_body']}\n",
            encoding="utf-8",
        )
        (folder / "sample-article.md").write_text(
            f"# {out['article_title']}\n\n{out['article_markdown']}\n", encoding="utf-8"
        )

        lead["status"] = "ready"
        lead["notes"] = f"pack written {today():%Y-%m-%d}"
        done += 1
        print(f"  ✓ {name} → {folder.relative_to(ROOT)}")

    write_leads(leads)

    cfg.setdefault("runs", {})["outreach"] = {
        "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "packs": done,
        "remaining": max(0, len(pending) - done),
    }
    save_config(cfg)
    print(f"\n{done} pack(s) ready in outbox/. {max(0, len(pending) - done)} lead(s) left.")
    return done


# ── delivery ──────────────────────────────────────────────────────────

def wordpress_draft(site, user, app_password, title, body_markdown, status):
    """Push a post to WordPress. Returns the post's edit URL, or raises."""
    url = site.rstrip("/") + "/wp-json/wp/v2/posts"
    payload = json.dumps({
        "title": title,
        "content": body_markdown,
        "status": status,
    }).encode("utf-8")

    token = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {token}",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        created = json.loads(resp.read().decode("utf-8"))
    return created.get("link") or created.get("guid", {}).get("rendered", "")


def cmd_deliver(cfg, client):
    active = [c for c in cfg.get("clients", []) if c.get("status", "active") == "active"]
    if not active:
        print("No active clients yet — nothing to deliver.")
        return 0

    settings = cfg["settings"]
    month = f"{today():%Y-%m}"
    month_name = f"{today():%B %Y}"
    delivered = 0

    for c in active:
        name = c["name"]
        town = c.get("town", "")
        focus = c.get("focus", "gym and personal training")
        slug = c.get("slug") or slugify(name)
        folder = CLIENTS_DIR / slug / month
        folder.mkdir(parents=True, exist_ok=True)
        brief = biz_brief(name, town, focus, c.get("website", ""))
        print(f"\n{name} — {month_name}")

        # Plan the month first, so the four posts don't overlap.
        try:
            plan = ask(client, cfg, BRAND, f"""{brief}

Plan {settings['posts_per_month']} blog posts for {month_name}. Each one must
target a different thing a local customer would actually type into Google, and
the four together should cover different stages: someone who has never trained,
someone comparing gyms, someone stuck, someone injured or returning.

Reply with a numbered list. One line each: the post title, then a dash, then the
search phrase it targets. Nothing else.""", max_tokens=2000)
        except Exception as e:                                  # noqa: BLE001
            print(f"  ! planning failed: {e}", file=sys.stderr)
            continue

        (folder / "00-plan.md").write_text(
            f"# {name} — {month_name}\n\n{plan}\n", encoding="utf-8"
        )
        titles = [
            re.sub(r"^\s*\d+[.)]\s*", "", line).strip()
            for line in plan.splitlines()
            if re.match(r"^\s*\d+[.)]", line)
        ][: settings["posts_per_month"]]

        posts = []
        for i, line in enumerate(titles, start=1):
            title = line.split(" - ")[0].split(" — ")[0].strip().strip("*")
            try:
                body = ask(client, cfg, BRAND, f"""{brief}

Write this month's post {i} of {len(titles)} in full: {line}

900 words, markdown, no H1 (the title is set separately). Open with the reader's
actual problem in the first two sentences — no throat-clearing. Give away real,
usable specifics: sets, reps, timings, what to eat, what to expect week by week.
Close with one soft, human line inviting them to come in. No hard sell.""")
            except Exception as e:                              # noqa: BLE001
                print(f"  ! post {i} failed: {e}", file=sys.stderr)
                continue
            path = folder / f"{i:02d}-{slugify(title)}.md"
            path.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
            posts.append({"title": title, "body": body, "file": path.name})
            print(f"  ✓ post {i}: {title}")

        extras = [
            ("social.md", f"""{brief}

Write {settings['social_per_month']} social captions for {month_name} — a mix of
Instagram and Facebook. Each under 60 words, each able to stand alone, each in a
different register: a tip, a member win (leave the name as [MEMBER]), a myth
corrected, a behind-the-scenes, a question that invites replies. Number them and
put 3-5 relevant hashtags at the end of each. No emoji spam — one at most."""),
            ("google-business.md", f"""{brief}

Write {settings['gbp_per_month']} Google Business Profile posts for {month_name}.
Each 100-150 words, written for someone who has just found the business on Maps
and is deciding whether to walk in. One clear call to action each. Number them."""),
            ("newsletter.md", f"""{brief}

Write one email to this gym's existing members for {month_name}. Subject line,
then the body. Under 350 words. It should feel like it came from the owner, not
a mailing list — one useful thing, one thing happening at the gym this month,
one line at the end. No graphics, no buttons, no "Dear valued member"."""),
        ]
        for filename, prompt in extras:
            try:
                (folder / filename).write_text(
                    ask(client, cfg, BRAND, prompt), encoding="utf-8"
                )
                print(f"  ✓ {filename}")
            except Exception as e:                              # noqa: BLE001
                print(f"  ! {filename} failed: {e}", file=sys.stderr)

        # Optional: push straight into their site as drafts.
        published = []
        site = c.get("wordpress_url")
        key = f"WP_{slug.upper().replace('-', '_')}"
        wp_user = os.environ.get(f"{key}_USER")
        wp_pass = os.environ.get(f"{key}_APP_PASSWORD")
        if site and wp_user and wp_pass:
            status = c.get("publish_status", settings.get("publish_status", "draft"))
            for p in posts:
                try:
                    link = wordpress_draft(
                        site, wp_user, wp_pass, p["title"], p["body"], status
                    )
                    published.append(link)
                    print(f"  ↑ {status}: {p['title']}")
                except (urllib.error.URLError, OSError, ValueError) as e:
                    print(f"  ! upload failed for {p['title']}: {e}", file=sys.stderr)
        elif site:
            print(f"  · WordPress configured but {key}_USER/{key}_APP_PASSWORD not set")

        c["last_delivered"] = month
        cfg.setdefault("deliveries", []).insert(0, {
            "client": name,
            "month": month,
            "posts": len(posts),
            "published": len(published),
            "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        })
        delivered += 1

    cfg["deliveries"] = cfg.get("deliveries", [])[:24]
    cfg.setdefault("runs", {})["deliver"] = {
        "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "clients": delivered,
        "month": month,
    }
    save_config(cfg)
    print(f"\nDelivered {delivered} client pack(s) for {month_name}.")
    return delivered


# ── entry ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["outreach", "deliver"])
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        return 1

    cfg = load_config()
    client = anthropic.Anthropic()

    if args.mode == "outreach":
        cmd_outreach(cfg, client)
    else:
        cmd_deliver(cfg, client)
    return 0


if __name__ == "__main__":
    sys.exit(main())
