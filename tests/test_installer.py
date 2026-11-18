import json
import sys

import pytest

from claude_usage_tray import installer, paths, store


def write_settings(data):
    paths.settings_file().write_text(json.dumps(data), encoding="utf-8")


def read_settings():
    return json.loads(paths.settings_file().read_text(encoding="utf-8"))


ORIGINAL = {"type": "command", "command": "bash ~/.claude/my-status.sh", "padding": 2}


def test_wrap_saves_original_and_keeps_other_settings():
    write_settings({"model": "opus", "statusLine": ORIGINAL})
    backup = installer.wrap_statusline()
    s = read_settings()
    assert s["model"] == "opus"
    assert installer.MARKER in s["statusLine"]["command"]
    assert s["statusLine"]["padding"] == 2
    assert store.load_config()["original_statusline"] == ORIGINAL
    assert backup is not None and backup.exists()


def test_reinstall_does_not_overwrite_saved_original():
    write_settings({"statusLine": ORIGINAL})
    installer.wrap_statusline()
    installer.wrap_statusline()
    assert store.load_config()["original_statusline"] == ORIGINAL


def test_uninstall_restores_original():
    write_settings({"statusLine": ORIGINAL})
    installer.wrap_statusline()
    assert installer.unwrap_statusline() is True
    assert read_settings()["statusLine"] == ORIGINAL


def test_no_prior_statusline_roundtrip():
    write_settings({"model": "opus"})
    installer.wrap_statusline()
    assert store.load_config()["original_statusline"] is None
    installer.unwrap_statusline()
    assert read_settings() == {"model": "opus"}


def test_missing_settings_file_is_created():
    installer.wrap_statusline()
    assert installer.MARKER in read_settings()["statusLine"]["command"]


def test_invalid_settings_json_is_refused():
    paths.settings_file().write_text("{oops", encoding="utf-8")
    with pytest.raises(installer.InstallError):
        installer.wrap_statusline()
    assert paths.settings_file().read_text(encoding="utf-8") == "{oops"


def test_uninstall_when_not_wrapped_is_noop():
    write_settings({"statusLine": ORIGINAL})
    assert installer.unwrap_statusline() is False
    assert read_settings()["statusLine"] == ORIGINAL


def test_statusline_command_uses_console_python():
    cmd = installer.statusline_command()
    assert "pythonw" not in cmd.lower()
    assert "\\" not in cmd


def test_linux_autostart_desktop_file(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    where = installer.enable_autostart()
    text = (tmp_path / "xdg" / "autostart" / "claude-usage-tray.desktop").read_text()
    assert where.endswith("claude-usage-tray.desktop")
    assert "-m claude_usage_tray run" in text
    installer.disable_autostart()
    assert not (tmp_path / "xdg" / "autostart" / "claude-usage-tray.desktop").exists()


def test_macos_launch_agent(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(installer.Path, "home", classmethod(lambda cls: tmp_path))
    installer.enable_autostart()
    plist = tmp_path / "Library" / "LaunchAgents" / "com.claude-usage-tray.plist"
    assert "<string>claude_usage_tray</string>" in plist.read_text()
    installer.disable_autostart()
    assert not plist.exists()
