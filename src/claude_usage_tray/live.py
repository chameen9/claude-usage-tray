"""Optional live polling of Anthropic's OAuth usage endpoint.

Off by default. Reads the access token Claude Code already stored, and only
sends it to api.anthropic.com. It never refreshes the token: refresh tokens
rotate, and refreshing here could sign the user out of Claude Code. When the
token has expired we stop and wait for Claude Code to refresh it.

The endpoint is undocumented and may change without notice.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Optional, Tuple

from . import __version__, paths, store

USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
BETA_HEADER = "oauth-2025-04-20"


class LiveError(Exception):
    """Human-readable reason live polling could not run."""


def _read_oauth() -> dict:
    data = None
    if sys.platform == "darwin":
        try:
            out = subprocess.run(
                ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
                capture_output=True, text=True, timeout=10,
            )
            if out.returncode == 0 and out.stdout.strip():
                data = json.loads(out.stdout)
        except (OSError, ValueError, subprocess.SubprocessError):
            data = None
    if data is None:
        data = store.read_json(paths.credentials_file())
    oauth = data.get("claudeAiOauth") if isinstance(data, dict) else None
    if not isinstance(oauth, dict) or not oauth.get("accessToken"):
        raise LiveError("not signed in to Claude Code with a Claude account")
    return oauth


def _to_epoch(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        return int(v / 1000 if v > 1e11 else v)  # accept ms or s
    if isinstance(value, str):
        try:
            return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
        except ValueError:
            return None
    return None


def normalize_window(w: Any) -> Optional[dict]:
    """Endpoint shape {utilization, resets_at(ISO)} -> statusline shape."""
    if not isinstance(w, dict):
        return None
    pct = w.get("utilization", w.get("used_percentage"))
    if pct is None:
        return None
    return {"used_percentage": float(pct), "resets_at": _to_epoch(w.get("resets_at"))}


def fetch(timeout: float = 15.0) -> Tuple[Optional[dict], Optional[dict]]:
    oauth = _read_oauth()
    expires = _to_epoch(oauth.get("expiresAt"))
    if expires and expires <= time.time():
        raise LiveError("login token expired - open Claude Code to refresh it")
    req = urllib.request.Request(
        USAGE_URL,
        headers={
            "Authorization": "Bearer " + oauth["accessToken"],
            "anthropic-beta": BETA_HEADER,
            "Accept": "application/json",
            "User-Agent": "claude-usage-tray/" + __version__,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise LiveError("login rejected - open Claude Code to refresh it") from None
        raise LiveError("usage endpoint returned HTTP %d" % e.code) from None
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise LiveError("network error: %s" % getattr(e, "reason", e)) from None
    five, seven = normalize_window(body.get("five_hour")), normalize_window(body.get("seven_day"))
    if five is None and seven is None:
        raise LiveError("usage endpoint response had no limit data")
    return five, seven


def poll_once() -> None:
    """Fetch and write to the cache. Raises LiveError on failure."""
    five, seven = fetch()
    store.write_usage(five, seven, source="live")
