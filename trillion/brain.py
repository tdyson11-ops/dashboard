"""The one agent core.

A typed turn, a spoken turn, and a heartbeat-initiated turn all flow through
Brain.run_turn(). Interfaces (REPL, voice, heartbeat) are adapters on its
edges — if you're tempted to duplicate this logic elsewhere, stop and unify.
"""

from __future__ import annotations

from .provider import ProviderError, Reply  # noqa: F401  (Reply re-exported for tests)


class Brain:
    def __init__(self, config, provider, registry=None, memory=None, gate=None, audit=None):
        self.config = config
        self.provider = provider
        self.registry = registry   # Tier 2: tools
        self.memory = memory       # Tier 4: long-term facts
        self.gate = gate           # Tier 6: confirmation gate
        self.audit = audit         # Tier 6: audit log
        self.history: list[dict] = []   # short-term memory; in-process only

    # -- system prompt -------------------------------------------------------

    def system_prompt(self) -> str:
        from datetime import datetime

        name = self.config.get("assistant.name", "Trillion")
        purpose = self.config.get("assistant.purpose", "")
        tone = self.config.get("assistant.tone", "warm, plain-spoken, and brief")
        now = datetime.now()
        parts = [
            f"You are {name}, {purpose}",
            f"Your tone is {tone}. Answer in a few sentences unless more is truly needed; "
            "your replies are often spoken aloud, so long answers drag.",
            f"Right now it is {now:%A} {now.day} {now:%B %Y}, {now:%H:%M}.",
        ]
        if self.registry:
            parts.append(
                "Use your tools when they help, and weave results into a natural reply. "
                "If a tool fails, say what went wrong in plain words."
            )
        if self.memory:
            rendered = self.memory.render_for_prompt()
            if rendered:
                parts.append(rendered)
        return "\n\n".join(parts)

    # -- the turn loop -------------------------------------------------------

    def run_turn(self, user_text: str, on_text=None) -> str:
        """One full turn: user input in, final assistant text out.

        The model may call several tools before answering; the loop continues
        until it stops asking. On provider failure the turn is rolled back so
        history never holds a half-finished exchange.
        """
        checkpoint = len(self.history)
        self.history.append({"role": "user", "content": user_text})
        tools = self.registry.schemas() if self.registry else None
        try:
            while True:
                reply = self.provider.complete(
                    self.system_prompt(), self.history, tools=tools, on_text=on_text
                )
                self.history.append({"role": "assistant", "content": reply.content})
                if reply.stop_reason == "pause_turn":
                    continue
                if reply.stop_reason != "tool_use" or not reply.tool_calls:
                    return reply.text
                results = self._run_tools(reply.tool_calls)
                self.history.append({"role": "user", "content": results})
        except ProviderError:
            del self.history[checkpoint:]
            raise

    # -- tools (Tier 2 fills the registry; Tier 6 adds the gate) -------------

    def _run_tools(self, tool_calls: list) -> list[dict]:
        from .provider import block_field

        results = []
        for call in tool_calls:
            name = block_field(call, "name")
            args = block_field(call, "input") or {}
            call_id = block_field(call, "id")
            output, is_error = self._run_one_tool(name, args)
            result = {"type": "tool_result", "tool_use_id": call_id, "content": output}
            if is_error:
                result["is_error"] = True
            results.append(result)
        return results

    def _run_one_tool(self, name: str, args: dict) -> tuple[str, bool]:
        if not self.registry:
            return f"No tools are available, so '{name}' cannot run.", True
        return self.registry.run(name, args)
