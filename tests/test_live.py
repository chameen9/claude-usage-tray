import io
import json
import sys
import time
import urllib.error

import pytest

from claude_usage_tray import live, paths, store


def fake_creds(expires_ms):
    paths.credentials_file().write_text(json.dumps(
        {"claudeAiOauth": {"accessToken": "test-token", "expiresAt": expires_ms}}), encoding="utf-8")


@pytest.fixture(autouse=True)
def no_keychain(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")  # use the file, never the real keychain


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_normalize_iso_and_epoch():
    w = live.normalize_window({"utilization": 37.0, "resets_at": "2026-11-18T20:00:00+00:00"})
    assert w["used_percentage"] == 37.0
    assert w["resets_at"] == 1795032000
    assert live.normalize_window({"utilization": 5, "resets_at": 1795032000000})["resets_at"] == 1795032000
    assert live.normalize_window(None) is None
    assert live.normalize_window({"resets_at": None}) is None


def test_poll_writes_cache_and_sends_token_only_to_anthropic(monkeypatch):
    fake_creds(int((time.time() + 3600) * 1000))
    seen = {}

    def fake_urlopen(req, timeout):
        seen["url"] = req.full_url
        seen["auth"] = req.get_header("Authorization")
        return FakeResp(json.dumps({
            "five_hour": {"utilization": 12.0, "resets_at": "2026-11-18T20:00:00Z"},
            "seven_day": {"utilization": 64.0, "resets_at": "2026-11-21T20:00:00Z"},
        }).encode())

    monkeypatch.setattr(live.urllib.request, "urlopen", fake_urlopen)
    live.poll_once()
    assert seen["url"].startswith("https://api.anthropic.com/")
    assert seen["auth"] == "Bearer test-token"
    data = store.read_usage()
    assert data["source"] == "live"
    assert data["five_hour"]["used_percentage"] == 12.0


def test_expired_token_is_not_used(monkeypatch):
    fake_creds(int((time.time() - 60) * 1000))
    monkeypatch.setattr(live.urllib.request, "urlopen", lambda *a, **k: pytest.fail("must not call"))
    with pytest.raises(live.LiveError, match="expired"):
        live.poll_once()


def test_no_credentials():
    with pytest.raises(live.LiveError, match="not signed in"):
        live.poll_once()


def test_401_is_friendly(monkeypatch):
    fake_creds(int((time.time() + 3600) * 1000))

    def boom(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 401, "no", {}, None)

    monkeypatch.setattr(live.urllib.request, "urlopen", boom)
    with pytest.raises(live.LiveError, match="rejected"):
        live.poll_once()
