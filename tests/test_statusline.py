import io
import json
import sys

import pytest

from claude_usage_tray import statusline, store

PAYLOAD = {
    "model": {"display_name": "Opus"},
    "rate_limits": {
        "five_hour": {"used_percentage": 15, "resets_at": 1795012800},
        "seven_day": {"used_percentage": 64, "resets_at": 1795273200},
    },
}


class FakeStdio:
    def __init__(self, data: bytes):
        self.buffer = io.BytesIO(data)


def run_wrapper(monkeypatch, payload_bytes):
    out = FakeStdio(b"")
    monkeypatch.setattr(sys, "stdin", FakeStdio(payload_bytes))
    monkeypatch.setattr(sys, "stdout", out)
    assert statusline.main() == 0
    return out.buffer.getvalue()


def test_saves_rate_limits_to_cache(monkeypatch):
    run_wrapper(monkeypatch, json.dumps(PAYLOAD).encode())
    data = store.read_usage()
    assert data["five_hour"]["used_percentage"] == 15
    assert data["seven_day"]["resets_at"] == 1795273200
    assert data["source"] == "statusline"


def test_no_rate_limits_leaves_cache_alone(monkeypatch):
    run_wrapper(monkeypatch, json.dumps({"model": {}}).encode())
    assert store.read_usage() is None


def test_bad_json_does_not_crash(monkeypatch):
    assert run_wrapper(monkeypatch, b"not json") == b""


def test_utf8_bom_payload(monkeypatch):
    run_wrapper(monkeypatch, b"\xef\xbb\xbf" + json.dumps(PAYLOAD).encode())
    assert store.read_usage()["five_hour"]["used_percentage"] == 15


@pytest.mark.skipif(statusline.shell_argv("true") is None, reason="needs bash")
def test_original_command_gets_same_stdin_and_output_passes_through(monkeypatch):
    store.update_config(original_statusline={"type": "command", "command": "cat"})
    raw = json.dumps(PAYLOAD).encode()
    assert run_wrapper(monkeypatch, raw) == raw


def test_windows_never_picks_wsl_bash(monkeypatch):
    if sys.platform != "win32":
        pytest.skip("windows only")
    bash = statusline._git_bash()
    if bash:
        assert "system32" not in bash.lower()
