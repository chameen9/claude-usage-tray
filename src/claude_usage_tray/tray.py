"""The tray application."""

from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from typing import Optional

from . import icons, live, paths, store
from .usage import Window, describe, format_left, window_state

USAGE_PAGE = "https://claude.ai/settings/usage"
REFRESH_SECONDS = 15


def default_layout() -> str:
    # Several icons from one process is only dependable with pystray's win32 backend.
    return "split" if sys.platform == "win32" else "combined"


class _SingleInstance:
    """OS file lock held for the process lifetime."""

    def __init__(self) -> None:
        self._fh = None

    def acquire(self) -> bool:
        path = paths.lock_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(path, "a+")
        try:
            if sys.platform == "win32":
                import msvcrt
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fh.close()
            return False
        self._fh = fh
        return True


class TrayApp:
    def __init__(self) -> None:
        import pystray  # imported lazily so CLI commands work without a display

        self.pystray = pystray
        cfg = store.load_config()
        self.layout = cfg.get("layout") or default_layout()
        self.lines = ["Session (5h): ...", "Weekly (7d): ...", "Updated: ..."]
        self.live_status = ""
        self._last_poll = 0.0
        self._stop = threading.Event()
        self._wake = threading.Event()

        menu = pystray.Menu(
            pystray.MenuItem(lambda _: self.lines[0], None, enabled=False),
            pystray.MenuItem(lambda _: self.lines[1], None, enabled=False),
            pystray.MenuItem(lambda _: self.lines[2], None, enabled=False),
            pystray.MenuItem(lambda _: self.live_status, None, enabled=False,
                             visible=lambda _: bool(self.live_status)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Refresh", self._on_refresh, default=True),
            pystray.MenuItem("Live updates (beta)", self._on_toggle_live,
                             checked=lambda _: bool(store.load_config().get("live_polling"))),
            pystray.MenuItem("Open usage page", lambda *_: webbrowser.open(USAGE_PAGE)),
            pystray.MenuItem("Quit", self._on_quit),
        )
        blank = icons.ring_icon(None, True)
        if self.layout == "split":
            self.icons = [
                pystray.Icon("claude-usage-session", blank, "Session (5h)", menu),
                pystray.Icon("claude-usage-weekly", blank, "Weekly (7d)", menu),
            ]
        else:
            self.icons = [pystray.Icon("claude-usage", blank, "Claude usage", menu)]

    # ---- menu handlers ---------------------------------------------------

    def _on_refresh(self, *_):
        self._last_poll = 0.0
        self._wake.set()

    def _on_toggle_live(self, *_):
        cfg = store.load_config()
        store.update_config(live_polling=not cfg.get("live_polling"))
        self._on_refresh()

    def _on_quit(self, *_):
        self._stop.set()
        self._wake.set()
        for ic in self.icons:
            ic.stop()

    # ---- refresh loop ----------------------------------------------------

    def _maybe_poll(self, now: float) -> None:
        cfg = store.load_config()
        if not cfg.get("live_polling"):
            self.live_status = ""
            return
        interval = max(60, int(cfg.get("poll_interval_seconds") or 300))
        if now - self._last_poll < interval:
            return
        self._last_poll = now
        try:
            live.poll_once()
            self.live_status = "Live: ok"
        except live.LiveError as e:
            self.live_status = "Live: %s" % e
        except Exception as e:  # never let polling kill the tray
            self.live_status = "Live: error (%s)" % type(e).__name__

    def refresh(self) -> None:
        now = time.time()
        self._maybe_poll(now)
        data = store.read_usage() or {}
        s = window_state(data.get("five_hour"), now)
        w = window_state(data.get("seven_day"), now)
        updated = data.get("updated_at")
        age = "%s ago" % format_left(now - updated) if isinstance(updated, (int, float)) else "never"
        if age == "now ago":
            age = "just now"
        self.lines = [
            describe("Session (5h)", s, now),
            describe("Weekly (7d)", w, now),
            "Updated: %s" % age,
        ]
        if self.layout == "split":
            self._set(self.icons[0], icons.ring_icon(s.pct, s.stale), self.lines[0])
            self._set(self.icons[1], icons.ring_icon(w.pct, w.stale), self.lines[1])
        else:
            img = icons.combined_icon(s.pct, s.stale, w.pct, w.stale)
            self._set(self.icons[0], img, "%s\n%s" % (self.lines[0], self.lines[1]))
        for ic in self.icons:
            try:
                ic.update_menu()
            except Exception:
                pass

    @staticmethod
    def _set(icon, image, title: str) -> None:
        icon.icon = image
        icon.title = title[:127]

    def _loop(self, icon) -> None:
        for ic in self.icons:
            ic.visible = True
        while not self._stop.is_set():
            try:
                self.refresh()
            except Exception:
                pass
            self._wake.wait(REFRESH_SECONDS)
            self._wake.clear()

    def run(self) -> None:
        primary = self.icons[-1]
        for extra in self.icons[:-1]:
            extra.run_detached()
        primary.run(setup=self._loop)


def run() -> int:
    lock = _SingleInstance()
    if not lock.acquire():
        print("claude-usage-tray is already running.", file=sys.stderr)
        return 1
    TrayApp().run()
    return 0
