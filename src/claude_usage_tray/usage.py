"""Turn a cached snapshot into display state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Window:
    pct: Optional[int]       # None = no data
    reset_at: Optional[int]  # epoch seconds, None = unknown / already reset
    stale: bool              # True = no data or the window has rolled over


def window_state(w: Any, now: float) -> Window:
    if not isinstance(w, dict) or w.get("used_percentage") is None:
        return Window(None, None, True)
    try:
        pct = int(round(float(w["used_percentage"])))
    except (TypeError, ValueError):
        return Window(None, None, True)
    reset = w.get("resets_at")
    reset = int(reset) if isinstance(reset, (int, float)) else None
    if reset is not None and now >= reset:
        return Window(0, None, True)  # window rolled over since last data
    return Window(max(0, min(100, pct)), reset, False)


def format_left(secs: float) -> str:
    secs = int(secs)
    if secs <= 0:
        return "now"
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    if d:
        return "%dd %dh" % (d, h)
    if h:
        return "%dh %dm" % (h, m)
    return "%dm" % m


def describe(name: str, w: Window, now: float) -> str:
    if w.pct is None:
        return "%s: no data" % name
    if w.reset_at is None:
        return "%s: %d%% (reset)" % (name, w.pct) if w.stale else "%s: %d%%" % (name, w.pct)
    return "%s: %d%% - resets in %s" % (name, w.pct, format_left(w.reset_at - now))
