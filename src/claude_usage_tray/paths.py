"""Filesystem locations shared by every component."""

from __future__ import annotations

import os
from pathlib import Path


def claude_dir() -> Path:
    """Claude Code's config directory (honours CLAUDE_CONFIG_DIR)."""
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(env).expanduser() if env else Path.home() / ".claude"


def settings_file() -> Path:
    return claude_dir() / "settings.json"


def cache_file() -> Path:
    """Latest rate-limit snapshot, written by the statusline wrapper or live poller."""
    return claude_dir() / "usage-limits.json"


def config_file() -> Path:
    """This tool's own settings (saved original statusLine, live polling flag...)."""
    return claude_dir() / "usage-tray.json"


def credentials_file() -> Path:
    return claude_dir() / ".credentials.json"


def lock_file() -> Path:
    return claude_dir() / "usage-tray.lock"
