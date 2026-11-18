"""Statusline wrapper.

Claude Code pipes a JSON blob to the configured statusLine command on every
render. That blob carries `rate_limits.five_hour` / `rate_limits.seven_day`.
We save those to the cache, then run the user's original statusLine command
with the same stdin and pass its output through untouched.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from . import store


def _git_bash() -> Optional[str]:
    """Git Bash on Windows — the shell Claude Code itself uses for commands.

    Deliberately avoids C:\\Windows\\System32\\bash.exe (WSL), which would run
    the command inside Linux with the wrong paths.
    """
    env = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH")
    if env and Path(env).is_file():
        return env
    git = shutil.which("git")
    if git:
        root = Path(git).resolve().parent.parent  # ...\Git\cmd\git.exe -> ...\Git
        for cand in (root / "bin" / "bash.exe", root / "usr" / "bin" / "bash.exe"):
            if cand.is_file():
                return str(cand)
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if base:
            cand = Path(base) / "Git" / "bin" / "bash.exe"
            if cand.is_file():
                return str(cand)
    return None


def shell_argv(command: str) -> Optional[list]:
    """argv that runs `command` the way Claude Code would. None = use shell=True."""
    if sys.platform == "win32":
        bash = _git_bash()
        return [bash, "-c", command] if bash else None
    bash = shutil.which("bash")
    return [bash, "-c", command] if bash else None


def save_rate_limits(payload: dict) -> bool:
    rl = payload.get("rate_limits") if isinstance(payload, dict) else None
    if not isinstance(rl, dict):
        return False
    five, seven = rl.get("five_hour"), rl.get("seven_day")
    if five is None and seven is None:
        return False
    store.write_usage(five, seven, source="statusline")
    return True


def run_original(command: str, raw_stdin: bytes) -> bytes:
    argv = shell_argv(command)
    try:
        if argv:
            proc = subprocess.run(argv, input=raw_stdin, capture_output=True, timeout=30)
        else:
            proc = subprocess.run(command, shell=True, input=raw_stdin, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return b""
    return proc.stdout


def main() -> int:
    raw = sys.stdin.buffer.read()
    try:
        save_rate_limits(json.loads(raw.decode("utf-8-sig")))
    except Exception:
        pass  # never break the user's statusline over our cache

    original = store.load_config().get("original_statusline")
    command = original.get("command") if isinstance(original, dict) else None
    if command:
        out = sys.stdout.buffer
        out.write(run_original(command, raw))
        out.flush()
    return 0
