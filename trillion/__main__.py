"""Entry point: python -m trillion [--voice]

The typed REPL is the permanent debug path; voice wraps the same brain.
"""

from __future__ import annotations

import argparse
import sys

from .brain import Brain
from .config import Config
from .provider import FakeProvider, ProviderError, get_provider


def build_brain(config: Config) -> Brain:
    provider = get_provider(config)
    return Brain(config, provider)


def repl(brain: Brain) -> None:
    name = brain.config.get("assistant.name", "Trillion")
    offline = isinstance(brain.provider, FakeProvider)
    print(f"{name} — text mode{' (offline fake: no ANTHROPIC_API_KEY)' if offline else ''}.")
    print("Type to talk; /quit to exit.\n")

    while True:
        try:
            user_text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_text:
            continue
        if user_text in ("/quit", "/exit"):
            break

        print(f"{name}> ", end="", flush=True)
        try:
            brain.run_turn(user_text, on_text=lambda t: print(t, end="", flush=True))
            print()
        except ProviderError as e:
            print(f"\n[{e}]")

    print(f"\nSession cost: {brain.provider.cost.summary()}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="trillion")
    parser.add_argument("--voice", action="store_true", help="push-to-talk voice mode")
    args = parser.parse_args(argv)

    config = Config()
    brain = build_brain(config)

    if args.voice:
        print("Voice mode arrives in Tier 3 — starting text mode.")
    repl(brain)
    return 0


if __name__ == "__main__":
    sys.exit(main())
