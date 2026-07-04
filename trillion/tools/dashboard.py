"""Read-only view over the dashboard's data.json: WHOOP health numbers,
the Cyden building project, and university deadlines."""

from __future__ import annotations

import json

from ..config import ROOT
from .registry import Tool

DATA_PATH = ROOT / "data.json"

SECTIONS = ("whoop", "cyden", "university", "all")


def _whoop(d: dict) -> str:
    w = d.get("whoop", {})
    return (
        f"WHOOP (as of {d.get('updated', 'unknown')}): recovery {w.get('recovery')}%, "
        f"HRV {w.get('hrv')}ms, resting HR {w.get('rhr')}bpm, "
        f"sleep score {w.get('sleep_score')}%, day strain {w.get('strain')}."
    )


def _cyden(d: dict) -> str:
    c = d.get("cyden", {})
    kpis = ", ".join(
        f"{k.get('label')}: {k.get('value')} ({k.get('status')})" for k in c.get("kpis", [])
    )
    return (
        f"Cyden project: {c.get('plots_complete')}/{c.get('plots_total')} plots complete. "
        f"Current stage: {c.get('current_stage')}. Next milestone: {c.get('next_milestone')}. "
        f"KPIs — {kpis}."
    )


def _university(d: dict) -> str:
    u = d.get("university", {})
    return (
        f"University: module {u.get('module')}; next deadline {u.get('next_deadline')} "
        f"({u.get('deadline_label')}); target grade {u.get('grade_target')}, "
        f"current average {u.get('current_avg')}."
    )


def get_dashboard(section: str = "all") -> str:
    with open(DATA_PATH) as f:
        data = json.load(f)
    parts = {
        "whoop": _whoop,
        "cyden": _cyden,
        "university": _university,
    }
    if section == "all":
        return "\n".join(fn(data) for fn in parts.values())
    if section not in parts:
        return f"Unknown section '{section}'. Pick one of: {', '.join(SECTIONS)}."
    return parts[section](data)


TOOLS = [
    Tool(
        name="get_dashboard",
        description=(
            "Read Tom's dashboard data — use for questions about his WHOOP health/recovery/sleep "
            "('whoop'), the Cyden building project and its KPIs ('cyden'), or his university module "
            "and deadlines ('university'). Use 'all' for an overview."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "enum": list(SECTIONS),
                    "description": "Which part of the dashboard to read",
                }
            },
            "required": [],
        },
        fn=get_dashboard,
    ),
]
