#!/usr/bin/env python3
"""
Mirror the hustle into Notion, so the Command Center shows it alongside
everything else.

    python3 hustle_notion.py

Creates (once) and then keeps up to date:
  - a "Hustle — Clients" database, one row per client
  - a "Hustle — Snapshot" page with MRR, the delivery log and the last run

Self-configuring: give it NOTION_TOKEN and NOTION_PARENT_PAGE_ID the first
time and it builds both, writing the IDs back into hustle.json. After that
it just updates them.

Connectors live inside a chat, so a scheduled job needs an integration token:
  1. https://www.notion.so/my-integrations → New integration → copy the secret
  2. Open the Notion page you want this to live under → ••• → Connections →
     add your integration. Without this the API cannot see the page.
  3. Copy that page's URL — the 32-character id on the end is the parent id.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "hustle.json"

API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

DB_TITLE = "Hustle — Clients"
SNAPSHOT_TITLE = "Hustle — Snapshot"


# ── api ───────────────────────────────────────────────────────────────

def call(method, path, token, body=None):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail).get("message", detail)
        except ValueError:
            pass
        raise RuntimeError(f"Notion {method} {path} → {e.code}: {detail}") from None


def page_id(raw):
    """Accept a bare id, a dashed id, or a full Notion URL."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    tail = raw.rstrip("/").split("/")[-1].split("?")[0]
    digits = "".join(c for c in tail if c in "0123456789abcdefABCDEF")
    if len(digits) >= 32:
        d = digits[-32:].lower()
        return f"{d[:8]}-{d[8:12]}-{d[12:16]}-{d[16:20]}-{d[20:]}"
    return raw


def text(content):
    return [{"type": "text", "text": {"content": str(content)[:2000]}}]


# ── clients database ──────────────────────────────────────────────────

SCHEMA = {
    "Name": {"title": {}},
    "Status": {"select": {"options": [
        {"name": "active", "color": "green"},
        {"name": "paused", "color": "yellow"},
        {"name": "churned", "color": "red"},
    ]}},
    "Price": {"number": {"format": "pound"}},
    "Town": {"rich_text": {}},
    "Focus": {"rich_text": {}},
    "Last pack": {"rich_text": {}},
    "Website": {"url": {}},
}


def ensure_database(token, parent, cfg):
    existing = cfg.get("notion", {}).get("database_id")
    if existing:
        try:
            call("GET", f"/databases/{existing}", token)
            return existing
        except RuntimeError as e:
            print(f"  stored database unreachable ({e}) — making a new one")

    db = call("POST", "/databases", token, {
        "parent": {"type": "page_id", "page_id": parent},
        "title": text(DB_TITLE),
        "description": text("Synced from hustle.json by the Side Hustle workflow. "
                            "Edits here are overwritten."),
        "properties": SCHEMA,
    })
    cfg.setdefault("notion", {})["database_id"] = db["id"]
    print(f"  created database {db['id']}")
    return db["id"]


def client_props(c, default_price):
    return {
        "Name": {"title": text(c.get("name", "Untitled"))},
        "Status": {"select": {"name": c.get("status", "active")}},
        "Price": {"number": float(c.get("price", default_price))},
        "Town": {"rich_text": text(c.get("town", ""))},
        "Focus": {"rich_text": text(c.get("focus", ""))},
        "Last pack": {"rich_text": text(c.get("last_delivered", "—"))},
        "Website": {"url": c.get("website") or None},
    }


def sync_clients(token, db_id, cfg):
    clients = cfg.get("clients", [])
    default_price = cfg["offer"]["price"]

    rows = call("POST", f"/databases/{db_id}/query", token, {"page_size": 100})
    by_name = {}
    for row in rows.get("results", []):
        title = row.get("properties", {}).get("Name", {}).get("title", [])
        if title:
            by_name[title[0].get("plain_text", "").strip()] = row["id"]

    seen = set()
    for c in clients:
        name = c.get("name", "").strip()
        if not name:
            continue
        seen.add(name)
        props = client_props(c, default_price)
        if name in by_name:
            call("PATCH", f"/pages/{by_name[name]}", token, {"properties": props})
            print(f"  updated {name}")
        else:
            call("POST", "/pages", token,
                 {"parent": {"database_id": db_id}, "properties": props})
            print(f"  added {name}")

    # A client removed from hustle.json is archived rather than deleted, so the
    # history stays readable in Notion.
    for name, pid in by_name.items():
        if name not in seen:
            call("PATCH", f"/pages/{pid}", token, {"archived": True})
            print(f"  archived {name}")

    return len(clients)


# ── snapshot page ─────────────────────────────────────────────────────

def para(content):
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": text(content)}}


def heading(content):
    return {"object": "block", "type": "heading_2",
            "heading_2": {"rich_text": text(content)}}


def bullet(content):
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": text(content)}}


def snapshot_blocks(cfg):
    active = [c for c in cfg.get("clients", []) if c.get("status", "active") == "active"]
    price = cfg["offer"]["price"]
    mrr = sum(float(c.get("price", price)) for c in active)
    target = cfg["target_mrr"]
    gap = max(0, -(-int(target - mrr) // int(price)))  # ceil

    blocks = [
        heading(f"£{mrr:,.0f} / £{target:,.0f} a month"),
        para(f"{len(active)} active client(s). "
             + ("Target hit." if mrr >= target
                else f"{gap} more at £{price:,.0f} gets you there.")),
        heading("Clients"),
    ]
    if active:
        for c in active:
            blocks.append(bullet(
                f"{c.get('name')} — {c.get('town', '')} · "
                f"£{float(c.get('price', price)):,.0f} · "
                f"last pack {c.get('last_delivered', 'none yet')}"))
    else:
        blocks.append(para("None yet."))

    deliveries = cfg.get("deliveries", [])[:8]
    if deliveries:
        blocks.append(heading("Recent packs"))
        for d in deliveries:
            line = f"{d.get('month')} — {d.get('client')}: {d.get('posts')} posts"
            if d.get("published"):
                line += f", {d['published']} pushed to their site"
            blocks.append(bullet(line))

    runs = cfg.get("runs", {})
    blocks.append(heading("Automation"))
    o, d = runs.get("outreach", {}), runs.get("deliver", {})
    blocks.append(bullet(
        f"Outreach — last run {o.get('at', 'never')}"
        + (f", {o['packs']} pack(s) written" if o.get("packs") is not None else "")
        + (f", {o['remaining']} lead(s) left" if o.get("remaining") is not None else "")))
    blocks.append(bullet(f"Delivery — last run {d.get('at', 'never')}"
                         + (f", {d['clients']} client pack(s)" if d.get("clients") is not None else "")))
    blocks.append(para("Synced from hustle.json. Edits here are overwritten."))
    return blocks


def ensure_snapshot(token, parent, cfg):
    existing = cfg.get("notion", {}).get("snapshot_page_id")
    if existing:
        try:
            call("GET", f"/pages/{existing}", token)
            return existing
        except RuntimeError as e:
            print(f"  stored snapshot unreachable ({e}) — making a new one")

    page = call("POST", "/pages", token, {
        "parent": {"type": "page_id", "page_id": parent},
        "properties": {"title": {"title": text(SNAPSHOT_TITLE)}},
    })
    cfg.setdefault("notion", {})["snapshot_page_id"] = page["id"]
    print(f"  created snapshot page {page['id']}")
    return page["id"]


def sync_snapshot(token, page, cfg):
    # Notion has no "replace page body", so clear the old blocks then append.
    children = call("GET", f"/blocks/{page}/children?page_size=100", token)
    for block in children.get("results", []):
        try:
            call("DELETE", f"/blocks/{block['id']}", token)
        except RuntimeError as e:
            print(f"  could not clear a block: {e}", file=sys.stderr)

    blocks = snapshot_blocks(cfg)
    for i in range(0, len(blocks), 100):
        call("PATCH", f"/blocks/{page}/children", token, {"children": blocks[i:i + 100]})
    print(f"  snapshot rewritten ({len(blocks)} blocks)")


# ── entry ─────────────────────────────────────────────────────────────

def sync(cfg):
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print("NOTION_TOKEN not set — skipping Notion sync.")
        return False

    parent = page_id(os.environ.get("NOTION_PARENT_PAGE_ID", ""))
    stored = cfg.get("notion", {})
    if not parent and not (stored.get("database_id") and stored.get("snapshot_page_id")):
        print("NOTION_PARENT_PAGE_ID not set and nothing built yet — skipping.")
        return False

    print("Notion:")
    db_id = ensure_database(token, parent, cfg)
    n = sync_clients(token, db_id, cfg)
    page = ensure_snapshot(token, parent, cfg)
    sync_snapshot(token, page, cfg)
    print(f"  done — {n} client(s) mirrored")
    return True


def main():
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    try:
        changed = sync(cfg)
    except RuntimeError as e:
        print(f"Notion sync failed: {e}", file=sys.stderr)
        return 1
    if changed:
        CONFIG_PATH.write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
