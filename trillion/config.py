"""Configuration for Trillion.

Loads trillion.toml (tunables) and .env (secrets) from the repo root.
Everything else in the harness asks this module for settings and paths;
nothing else reads files or environment variables for configuration.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "trillion.toml"
ENV_PATH = ROOT / ".env"
STATE_DIR = ROOT / "state"


def _load_env(path: Path = ENV_PATH) -> None:
    """Load KEY=value lines from .env into os.environ (existing vars win)."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key and value and key not in os.environ:
            os.environ[key] = value


class Config:
    def __init__(self, path: Path = CONFIG_PATH):
        self.path = path
        with open(path, "rb") as f:
            self.data = tomllib.load(f)
        _load_env()
        STATE_DIR.mkdir(exist_ok=True)

    def get(self, dotted_key: str, default=None):
        """cfg.get("model.max_tokens", 8192) — dotted lookup with default."""
        node = self.data
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def secret(self, name: str) -> str | None:
        return os.environ.get(name) or None
