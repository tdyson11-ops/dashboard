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
    from .memory import Memory
    from .tools import build_default_registry

    provider = get_provider(config)
    memory = Memory()
    registry = build_default_registry(config, memory=memory)
    return Brain(config, provider, registry=registry, memory=memory)


def show_catch_up(board) -> None:
    """Everything noticed while Tom was away — held, never lost."""
    unseen = board.unseen()
    if not unseen:
        return
    print(f"While you were away ({len(unseen)} notice{'s' if len(unseen) != 1 else ''}):")
    for n in unseen:
        print(f"  #{n['id']} [{n['level']}] {n['message']}")
    print("(/notices lists pending, /dismiss <id> clears one)\n")
    board.mark_seen([n["id"] for n in unseen])


def handle_command(user_text: str, board, heartbeat) -> bool:
    """Slash commands. Returns True when the input was a command."""
    if user_text == "/notices":
        pending = board.pending()
        if not pending:
            print("(no pending notices)")
        for n in pending:
            print(f"  #{n['id']} [{n['level']}] {n['created']} — {n['message']}")
        board.mark_seen([n["id"] for n in pending])
        return True
    if user_text.startswith("/dismiss"):
        arg = user_text.removeprefix("/dismiss").strip()
        if not arg.isdigit():
            print("usage: /dismiss <id>")
        elif board.dismiss(int(arg)):
            print(f"(dismissed #{arg})")
        else:
            print(f"(no pending notice #{arg})")
        return True
    return False


def repl(brain: Brain, board=None, heartbeat=None) -> None:
    name = brain.config.get("assistant.name", "Trillion")
    offline = isinstance(brain.provider, FakeProvider)
    print(f"{name} — text mode{' (offline fake: no ANTHROPIC_API_KEY)' if offline else ''}.")
    print("Type to talk; /notices, /dismiss <id>, /quit.\n")
    if board:
        show_catch_up(board)

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
        if board and handle_command(user_text, board, heartbeat):
            continue

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
    parser.add_argument("--no-heartbeat", action="store_true", help="run without proactive checks")
    args = parser.parse_args(argv)

    config = Config()
    brain = build_brain(config)

    from .heartbeat import Heartbeat
    from .notices import NoticeBoard

    board = NoticeBoard()
    heartbeat = None
    if config.get("heartbeat.enabled", True) and not args.no_heartbeat:
        def push(notice):
            print(f"\n🔔 {notice['message']}   (/dismiss {notice['id']} to clear)")

        heartbeat = Heartbeat(config, board, on_interrupt=push)
        heartbeat.start()

    if args.voice:
        try:
            from .voice import build_voice_interface

            voice = build_voice_interface(config, brain)
        except (RuntimeError, ImportError, OSError) as e:
            print(f"Voice mode unavailable: {e}")
            print("Falling back to text mode.\n")
        else:
            show_catch_up(board)
            voice.run()
            print(f"\nSession cost: {brain.provider.cost.summary()}")
            return 0

    repl(brain, board=board, heartbeat=heartbeat)
    return 0


if __name__ == "__main__":
    sys.exit(main())
