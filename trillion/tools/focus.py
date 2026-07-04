"""Daily focus list (lives in the dashboard's data.json) and reminders
(lives in state/reminders.json; the Tier 5 heartbeat surfaces due ones)."""

from __future__ import annotations

import json
from datetime import datetime

from ..config import ROOT, STATE_DIR
from .registry import Tool

DATA_PATH = ROOT / "data.json"
REMINDERS_PATH = STATE_DIR / "reminders.json"


# -- focus list ---------------------------------------------------------------

def _load_data() -> dict:
    with open(DATA_PATH) as f:
        return json.load(f)


def _save_data(data: dict) -> None:
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _format_focus(items: list[str]) -> str:
    if not items:
        return "The focus list is empty."
    return "Focus list:\n" + "\n".join(f"{i}. {item}" for i, item in enumerate(items, 1))


def get_focus_list() -> str:
    return _format_focus(_load_data().get("focus", []))


def add_focus_item(item: str) -> str:
    data = _load_data()
    data.setdefault("focus", []).append(item)
    _save_data(data)
    return f"Added. {_format_focus(data['focus'])}"


def remove_focus_item(number: int) -> str:
    data = _load_data()
    focus = data.get("focus", [])
    if not 1 <= number <= len(focus):
        return f"There's no item {number}; the list has {len(focus)} item(s)."
    removed = focus.pop(number - 1)
    _save_data(data)
    return f"Removed '{removed}'. {_format_focus(focus)}"


# -- reminders ----------------------------------------------------------------

def _load_reminders() -> list[dict]:
    if not REMINDERS_PATH.exists():
        return []
    return json.loads(REMINDERS_PATH.read_text())


def _save_reminders(reminders: list[dict]) -> None:
    REMINDERS_PATH.write_text(json.dumps(reminders, indent=2))


def add_reminder(text: str, due: str) -> str:
    try:
        due_dt = datetime.fromisoformat(due)
    except ValueError:
        return f"'{due}' isn't a date I can parse — use YYYY-MM-DD or YYYY-MM-DD HH:MM."
    reminders = _load_reminders()
    next_id = max((r["id"] for r in reminders), default=0) + 1
    reminders.append({
        "id": next_id,
        "text": text,
        "due": due_dt.isoformat(sep=" "),
        "done": False,
    })
    _save_reminders(reminders)
    return f"Reminder #{next_id} set for {due_dt:%A %d %B %Y %H:%M}: {text}"


def list_reminders() -> str:
    pending = [r for r in _load_reminders() if not r["done"]]
    if not pending:
        return "No pending reminders."
    return "Pending reminders:\n" + "\n".join(
        f"#{r['id']} — {r['text']} (due {r['due']})" for r in pending
    )


TOOLS = [
    Tool(
        name="get_focus_list",
        description="Read Tom's daily focus list — use this when he asks what's on his list or plate today.",
        input_schema={"type": "object", "properties": {}, "required": []},
        fn=get_focus_list,
    ),
    Tool(
        name="add_focus_item",
        description="Add one task to Tom's daily focus list when he asks to put something on it.",
        input_schema={
            "type": "object",
            "properties": {"item": {"type": "string", "description": "The task, phrased as a short action"}},
            "required": ["item"],
        },
        fn=add_focus_item,
        describe=lambda a: f"add '{a.get('item')}' to the focus list",
    ),
    Tool(
        name="remove_focus_item",
        description="Remove a task from the focus list by its number (as shown by get_focus_list) when Tom says it's done or no longer needed.",
        input_schema={
            "type": "object",
            "properties": {"number": {"type": "integer", "description": "1-based position in the list"}},
            "required": ["number"],
        },
        fn=remove_focus_item,
        describe=lambda a: f"remove item {a.get('number')} from the focus list",
    ),
    Tool(
        name="add_reminder",
        description="Set a reminder for a specific date/time — use when Tom asks to be reminded of something. Trillion surfaces it when due.",
        input_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "What to remind Tom about"},
                "due": {"type": "string", "description": "When, as YYYY-MM-DD or YYYY-MM-DD HH:MM (24h)"},
            },
            "required": ["text", "due"],
        },
        fn=add_reminder,
        describe=lambda a: f"set a reminder '{a.get('text')}' for {a.get('due')}",
    ),
    Tool(
        name="list_reminders",
        description="List Tom's pending reminders when he asks what reminders he has.",
        input_schema={"type": "object", "properties": {}, "required": []},
        fn=list_reminders,
    ),
]
