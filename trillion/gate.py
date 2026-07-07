"""The confirmation gate — between the model choosing a tool and the tool
running, on every path (typed, spoken, heartbeat-initiated).

A tool is gated when its code flags requires_confirmation, or when its name
is listed in trillion.toml under [tools] confirm — so Tom can tighten the
list with a one-line config edit.

Two hard rules:
- approval is per action and never remembered — one yes covers one run;
- the gate never blocks forever waiting on a human: with nobody there to
  ask (heartbeat context), the safe default is do nothing and leave a note.
"""

from __future__ import annotations


class Gate:
    def __init__(self, config, audit=None, board=None, ask=None):
        self.confirm_names = set(config.get("tools.confirm", []))
        self.audit = audit
        self.board = board
        # ask(description) -> bool. Set by an interactive interface; None
        # means nobody is present to answer.
        self.ask = ask

    def is_gated(self, tool) -> bool:
        return bool(tool) and (tool.requires_confirmation or tool.name in self.confirm_names)

    def check(self, tool, args: dict) -> tuple[bool, str | None]:
        """Returns (allowed, message). When blocked, message is the plain
        explanation that goes back to the model as the tool result."""
        if not self.is_gated(tool):
            return True, None

        description = tool.describe(args) if tool.describe else f"run {tool.name} with {args}"

        if self.ask is None:
            # Nobody to ask — safe default: don't act, leave a note, move on.
            if self.board:
                self.board.add(
                    f"Held: I wanted to {description}, but you weren't around to approve it. "
                    "Nothing was done — ask me again when you're back.",
                    level="notice",
                )
            if self.audit:
                self.audit.log("gate", tool=tool.name, description=description, decision="held_no_human")
            return False, (
                f"This action ({description}) needs Tom's explicit confirmation and he isn't "
                "available right now. It was NOT performed; a note was left for him."
            )

        approved = bool(self.ask(description))
        if self.audit:
            self.audit.log("gate", tool=tool.name, description=description,
                           decision="approved" if approved else "declined")
        if approved:
            return True, None
        return False, f"Tom declined this action ({description}). Do not retry it unless he asks."
