"""Install / uninstall: statusLine wrapping and login autostart."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from . import paths, store

MARKER = "claude_usage_tray statusline"
APP_NAME = "ClaudeUsageTray"


# ---- interpreters -----------------------------------------------------------

def console_python() -> str:
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":
        cand = exe.with_name("python.exe")
        if cand.exists():
            return str(cand)
    return str(exe)


def gui_python() -> str:
    exe = Path(sys.executable)
    if sys.platform == "win32":
        cand = exe.with_name("pythonw.exe")
        if cand.exists():
            return str(cand)
    return str(exe)


def statusline_command() -> str:
    # Forward slashes work in Git Bash, cmd and PowerShell alike.
    py = console_python().replace("\\", "/")
    return '"%s" -m %s' % (py, MARKER)


# ---- settings.json ------------------------------------------------------------

class InstallError(Exception):
    pass


def _load_settings() -> dict:
    path = paths.settings_file()
    if not path.exists():
        return {}
    data = store.read_json(path)
    if not isinstance(data, dict):
        raise InstallError("%s is not valid JSON; fix it and retry." % path)
    return data


def _backup_settings() -> Optional[Path]:
    path = paths.settings_file()
    if not path.exists():
        return None
    dest = path.with_name("settings.json.usage-tray-backup-%d" % int(time.time()))
    shutil.copy2(path, dest)
    return dest


def is_wrapped(statusline) -> bool:
    return isinstance(statusline, dict) and MARKER in str(statusline.get("command", ""))


def wrap_statusline() -> Optional[Path]:
    settings = _load_settings()
    current = settings.get("statusLine")
    backup = _backup_settings()

    cfg = store.load_config()
    if not is_wrapped(current):
        cfg["original_statusline"] = current if isinstance(current, dict) else None
        store.save_config(cfg)
        base = dict(current) if isinstance(current, dict) else {}
    else:
        base = dict(current)  # re-install: keep saved original, refresh interpreter path

    base["type"] = "command"
    base["command"] = statusline_command()
    settings["statusLine"] = base
    store.write_json_atomic(paths.settings_file(), settings, indent=2)
    return backup


def unwrap_statusline() -> bool:
    settings = _load_settings()
    if not is_wrapped(settings.get("statusLine")):
        return False
    _backup_settings()
    original = store.load_config().get("original_statusline")
    if isinstance(original, dict):
        settings["statusLine"] = original
    else:
        settings.pop("statusLine", None)
    store.write_json_atomic(paths.settings_file(), settings, indent=2)
    return True


# ---- autostart ----------------------------------------------------------------

def _run_argv() -> list:
    return [gui_python(), "-m", "claude_usage_tray", "run"]


def _mac_plist() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / "com.claude-usage-tray.plist"


def _linux_desktop() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "autostart" / "claude-usage-tray.desktop"


def enable_autostart() -> str:
    argv = _run_argv()
    if sys.platform == "win32":
        import winreg
        cmd = subprocess.list2cmdline(argv)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                            winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, cmd)
        return "registry Run key"
    if sys.platform == "darwin":
        from xml.sax.saxutils import escape
        args = "".join("<string>%s</string>" % escape(a) for a in argv)
        plist = _mac_plist()
        plist.parent.mkdir(parents=True, exist_ok=True)
        plist.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0"><dict>'
            "<key>Label</key><string>com.claude-usage-tray</string>"
            "<key>ProgramArguments</key><array>%s</array>"
            "<key>RunAtLoad</key><true/>"
            "</dict></plist>\n" % args,
            encoding="utf-8",
        )
        return str(plist)
    import shlex
    desktop = _linux_desktop()
    desktop.parent.mkdir(parents=True, exist_ok=True)
    desktop.write_text(
        "[Desktop Entry]\nType=Application\nName=Claude Usage Tray\n"
        "Exec=%s\nX-GNOME-Autostart-enabled=true\nNoDisplay=true\n"
        % " ".join(shlex.quote(a) for a in argv),
        encoding="utf-8",
    )
    return str(desktop)


def disable_autostart() -> None:
    if sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                                winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, APP_NAME)
        except FileNotFoundError:
            pass
        return
    target = _mac_plist() if sys.platform == "darwin" else _linux_desktop()
    try:
        target.unlink()
    except FileNotFoundError:
        pass


def start_detached() -> None:
    argv = _run_argv()
    kwargs = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(argv, **kwargs)
