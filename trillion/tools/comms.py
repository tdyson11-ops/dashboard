"""Outbound communication — the canonical gated capability.

send_message is on Tom's "never without asking" list, so it carries
requires_confirmation=True from day one. There's no delivery channel wired
up yet: an approved send lands in state/outbox.json, honestly labelled.
When a real channel (email, SMS) arrives, only this file changes — the gate
already covers it.
"""

from __future__ import annotations

import json
from datetime import datetime

from ..config import STATE_DIR
from .registry import Tool

OUTBOX_PATH = STATE_DIR / "outbox.json"


def send_message(to: str, message: str) -> str:
    outbox = json.loads(OUTBOX_PATH.read_text()) if OUTBOX_PATH.exists() else []
    outbox.append({
        "to": to,
        "message": message,
        "at": datetime.now().isoformat(sep=" ", timespec="seconds"),
    })
    OUTBOX_PATH.write_text(json.dumps(outbox, indent=2) + "\n")
    return (
        f"Message for {to} placed in the outbox (state/outbox.json). "
        "No delivery channel is connected yet, so nothing has actually left this machine."
    )


TOOLS = [
    Tool(
        name="send_message",
        description=(
            "Send a message to a person on Tom's behalf — email, text, or similar. "
            "Use only when Tom explicitly asks you to send something. This always "
            "requires his confirmation before it runs."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Who the message is for"},
                "message": {"type": "string", "description": "The full message text"},
            },
            "required": ["to", "message"],
        },
        fn=send_message,
        requires_confirmation=True,   # "never without asking" — sends
        describe=lambda a: f"send a message to {a.get('to')}: \"{str(a.get('message'))[:80]}\"",
    ),
]
