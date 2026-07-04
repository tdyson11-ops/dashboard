"""The tool registry — the one extension point.

Each tool is a name, a when-to-use-it description the model reads, a typed
input schema, and a function. Tools marked requires_confirmation=True are
stopped by the gate (Tier 6) until Tom says yes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Tool:
    name: str
    description: str            # written for a reader: when to use it, not just what it is
    input_schema: dict          # JSON schema; typed, named inputs — no freeform blobs
    fn: Callable[..., str]
    requires_confirmation: bool = False
    describe: Callable[[dict], str] | None = None   # "about to …" line for the gate


class Registry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return list(self._tools)

    def schemas(self) -> list[dict]:
        return [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in self._tools.values()
        ]

    def run(self, name: str, args: dict) -> tuple[str, bool]:
        """Run a tool; never raise. Returns (output, is_error) — errors go back
        to the model in plain language so it can recover or explain."""
        tool = self._tools.get(name)
        if tool is None:
            return f"There is no tool called '{name}'. Available: {', '.join(self._tools)}.", True

        missing = [
            key for key in tool.input_schema.get("required", [])
            if key not in (args or {})
        ]
        if missing:
            return f"'{name}' needs the missing input(s): {', '.join(missing)}.", True

        try:
            return str(tool.fn(**(args or {}))), False
        except Exception as e:  # a tool will fail; the model reasoning over it is a feature
            return f"The tool '{name}' failed: {e}", True
