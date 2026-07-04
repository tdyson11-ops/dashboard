"""Tools that let Trillion manage its own long-term memory as it learns."""

from __future__ import annotations

from .registry import Tool


def build_memory_tools(memory) -> list[Tool]:
    def remember_fact(fact: str) -> str:
        fact_id = memory.remember(fact)
        return f"Remembered as fact #{fact_id}: {fact}"

    def update_fact(fact_id: int, fact: str) -> str:
        if memory.update(fact_id, fact):
            return f"Fact #{fact_id} is now: {fact}"
        return f"There is no fact #{fact_id} to update."

    def forget_fact(fact_id: int) -> str:
        if memory.forget(fact_id):
            return f"Forgot fact #{fact_id}."
        return f"There is no fact #{fact_id} to forget."

    return [
        Tool(
            name="remember_fact",
            description=(
                "Store one durable fact about Tom or his world for future sessions — "
                "preferences, identities, decisions. One plain statement per fact. "
                "Don't store passing chatter the conversation already covers."
            ),
            input_schema={
                "type": "object",
                "properties": {"fact": {"type": "string", "description": "A single plain statement, e.g. 'Tom prefers morning meetings'"}},
                "required": ["fact"],
            },
            fn=remember_fact,
            describe=lambda a: f"remember '{a.get('fact')}'",
        ),
        Tool(
            name="update_fact",
            description="Rewrite a stored fact (by its # id, visible in your long-term memory) when it has become stale or was wrong.",
            input_schema={
                "type": "object",
                "properties": {
                    "fact_id": {"type": "integer", "description": "The # id of the fact"},
                    "fact": {"type": "string", "description": "The corrected statement"},
                },
                "required": ["fact_id", "fact"],
            },
            fn=update_fact,
        ),
        Tool(
            name="forget_fact",
            description="Delete a stored fact (by its # id) when Tom asks or it no longer applies.",
            input_schema={
                "type": "object",
                "properties": {"fact_id": {"type": "integer", "description": "The # id of the fact"}},
                "required": ["fact_id"],
            },
            fn=forget_fact,
        ),
    ]
