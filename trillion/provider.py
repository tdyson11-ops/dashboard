"""The provider seam — the only file that talks to a model API.

Everything else calls Provider.complete(system, messages, tools, on_text) and
gets back a Reply. Swapping models, adding retries, and counting cost all
happen here and nowhere else.

With no ANTHROPIC_API_KEY set, get_provider() returns FakeProvider — a
scripted stand-in that keeps the whole harness runnable and testable offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class ProviderError(Exception):
    """A model call failed in a way the interface should explain, not crash on."""


# --- content blocks arrive either as SDK objects or plain dicts; treat alike ---

def block_field(block, name, default=None):
    if isinstance(block, dict):
        return block.get(name, default)
    return getattr(block, name, default)


def text_of(content: list) -> str:
    """Concatenated text of all text blocks in an assistant content list."""
    return "".join(
        block_field(b, "text", "") for b in content if block_field(b, "type") == "text"
    )


def tool_calls_of(content: list) -> list:
    return [b for b in content if block_field(b, "type") == "tool_use"]


@dataclass
class Reply:
    content: list                 # blocks to append back into history verbatim
    stop_reason: str = "end_turn"

    @property
    def text(self) -> str:
        return text_of(self.content)

    @property
    def tool_calls(self) -> list:
        return tool_calls_of(self.content)


# $/MTok — used only for the running cost tally, not billing.
PRICES = {
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-fable-5": (10.00, 50.00),
}


@dataclass
class CostTally:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    usd: float = 0.0

    def add(self, model: str, usage) -> None:
        inp = getattr(usage, "input_tokens", 0) or 0
        out = getattr(usage, "output_tokens", 0) or 0
        cread = getattr(usage, "cache_read_input_tokens", 0) or 0
        cwrite = getattr(usage, "cache_creation_input_tokens", 0) or 0
        self.input_tokens += inp
        self.output_tokens += out
        self.cache_read_tokens += cread
        self.cache_write_tokens += cwrite
        in_price, out_price = PRICES.get(model, (5.00, 25.00))
        self.usd += (
            inp * in_price
            + out * out_price
            + cread * in_price * 0.1
            + cwrite * in_price * 1.25
        ) / 1_000_000

    def summary(self) -> str:
        return (
            f"{self.input_tokens + self.cache_read_tokens + self.cache_write_tokens} in / "
            f"{self.output_tokens} out tokens, ~${self.usd:.4f}"
        )


class ClaudeProvider:
    """Claude via the official Anthropic SDK, streaming."""

    def __init__(self, config):
        import anthropic  # deferred so offline mode never needs the package

        self._anthropic = anthropic
        self.client = anthropic.Anthropic(max_retries=2)
        self.model = config.get("model.model", "claude-opus-4-8")
        self.max_tokens = config.get("model.max_tokens", 8192)
        self.thinking = config.get("model.thinking", "adaptive")
        self.effort = config.get("model.effort", "high")
        self.cost = CostTally()

    def complete(self, system: str, messages: list, tools: list | None = None,
                 on_text=None) -> Reply:
        kwargs = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=messages,
            output_config={"effort": self.effort},
        )
        if self.thinking == "adaptive":
            kwargs["thinking"] = {"type": "adaptive"}
        if tools:
            kwargs["tools"] = tools
        try:
            with self.client.messages.stream(**kwargs) as stream:
                for chunk in stream.text_stream:
                    if on_text:
                        on_text(chunk)
                final = stream.get_final_message()
        except self._anthropic.AuthenticationError as e:
            raise ProviderError("The API key was rejected — check ANTHROPIC_API_KEY in .env.") from e
        except self._anthropic.RateLimitError as e:
            raise ProviderError("The model is rate-limiting us right now. Give it a minute and try again.") from e
        except self._anthropic.APIConnectionError as e:
            raise ProviderError("Couldn't reach the model (network problem). Your message wasn't lost — try again.") from e
        except self._anthropic.APIStatusError as e:
            raise ProviderError(f"The model API returned an error ({e.status_code}). Try again shortly.") from e

        self.cost.add(self.model, final.usage)
        return Reply(content=list(final.content), stop_reason=final.stop_reason)


class FakeProvider:
    """Offline stand-in. Two modes:

    - scripted: tests enqueue Reply objects; complete() pops them in order.
    - interactive: with an empty queue it answers with a reply that provably
      depends on earlier turns, so in-session memory is checkable by eye.
    """

    def __init__(self, script: list[Reply] | None = None):
        self.queue = list(script or [])
        self.calls: list[dict] = []  # what complete() was asked, for tests
        self.cost = CostTally()

    def complete(self, system: str, messages: list, tools: list | None = None,
                 on_text=None) -> Reply:
        self.calls.append({"system": system, "messages": list(messages), "tools": tools})
        if self.queue:
            reply = self.queue.pop(0)
        else:
            reply = self._echo(messages)
        if on_text and reply.text:
            on_text(reply.text)
        return reply

    def _echo(self, messages: list) -> Reply:
        user_texts = []
        for m in messages:
            if block_field(m, "role") == "user":
                content = block_field(m, "content")
                if isinstance(content, str):
                    user_texts.append(content)
        current = user_texts[-1] if user_texts else ""
        text = f'(offline fake) You said: "{current}".'
        if len(user_texts) > 1:
            text += f' That\'s your message #{len(user_texts)} — the first was "{user_texts[0]}".'
        text += " Set ANTHROPIC_API_KEY in .env to talk to the real model."
        return Reply(content=[{"type": "text", "text": text}])


def get_provider(config):
    if config.secret("ANTHROPIC_API_KEY"):
        return ClaudeProvider(config)
    return FakeProvider()
