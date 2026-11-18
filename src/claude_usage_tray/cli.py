"""Command line entry point."""

from __future__ import annotations

import argparse
import sys
import time

from . import __version__, installer, live, paths, store
from .usage import describe, window_state


def _cmd_install(args) -> int:
    try:
        backup = installer.wrap_statusline()
    except installer.InstallError as e:
        print("error:", e, file=sys.stderr)
        return 1
    print("statusLine wrapped in %s" % paths.settings_file())
    if backup:
        print("  backup: %s" % backup)
    original = store.load_config().get("original_statusline")
    if original:
        print("  your original statusline still runs: %s" % original.get("command"))
    if not args.no_autostart:
        print("autostart enabled (%s)" % installer.enable_autostart())
    if not args.no_start:
        installer.start_detached()
        print("tray started.")
    print("\nUsage numbers appear after Claude Code next renders its status line.")
    print("Optional: `claude-usage-tray config --live on` to also poll while Claude Code is closed.")
    return 0


def _cmd_uninstall(args) -> int:
    try:
        restored = installer.unwrap_statusline()
    except installer.InstallError as e:
        print("error:", e, file=sys.stderr)
        return 1
    print("statusLine restored." if restored else "statusLine was not wrapped; left as is.")
    installer.disable_autostart()
    print("autostart removed.")
    print("If the tray is running, choose Quit from its menu.")
    return 0


def _cmd_status(args) -> int:
    data = store.read_usage()
    if not data:
        print("No usage data yet. Use Claude Code once after installing.")
        return 1
    now = time.time()
    print(describe("Session (5h)", window_state(data.get("five_hour"), now), now))
    print(describe("Weekly (7d)", window_state(data.get("seven_day"), now), now))
    print("Source: %s, %ds ago" % (data.get("source", "?"), int(now - data.get("updated_at", now))))
    return 0


def _cmd_config(args) -> int:
    changes = {}
    if args.live is not None:
        changes["live_polling"] = args.live == "on"
    if args.layout is not None:
        changes["layout"] = None if args.layout == "auto" else args.layout
    if args.interval is not None:
        changes["poll_interval_seconds"] = max(60, args.interval)
    cfg = store.update_config(**changes) if changes else store.load_config()
    for k in ("live_polling", "poll_interval_seconds", "layout"):
        print("%s = %s" % (k, cfg.get(k)))
    if "layout" in changes:
        print("Restart the tray for the layout change to apply.")
    return 0


def _cmd_poll(args) -> int:
    try:
        live.poll_once()
    except live.LiveError as e:
        print("live poll failed:", e, file=sys.stderr)
        return 1
    return _cmd_status(args)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="claude-usage-tray",
                                description="Tray rings for Claude Code usage limits.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("run", help="start the tray (default)")
    i = sub.add_parser("install", help="wrap your statusLine, enable autostart, start the tray")
    i.add_argument("--no-autostart", action="store_true")
    i.add_argument("--no-start", action="store_true")
    sub.add_parser("uninstall", help="restore your statusLine and remove autostart")
    sub.add_parser("status", help="print the latest usage")
    c = sub.add_parser("config", help="show or change settings")
    c.add_argument("--live", choices=["on", "off"], help="poll Anthropic's usage endpoint (beta)")
    c.add_argument("--layout", choices=["split", "combined", "auto"])
    c.add_argument("--interval", type=int, help="live poll interval in seconds (min 60)")
    sub.add_parser("poll", help="one live poll now, then print usage")
    sub.add_parser("statusline", help=argparse.SUPPRESS)

    args = p.parse_args(argv)
    if args.cmd == "statusline":
        from . import statusline
        return statusline.main()
    if args.cmd in (None, "run"):
        from . import tray
        return tray.run()
    return {
        "install": _cmd_install,
        "uninstall": _cmd_uninstall,
        "status": _cmd_status,
        "config": _cmd_config,
        "poll": _cmd_poll,
    }[args.cmd](args)


def run_gui() -> int:
    return main(["run"])
