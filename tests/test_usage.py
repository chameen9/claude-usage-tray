from claude_usage_tray.usage import describe, format_left, window_state

NOW = 1_000_000


def test_missing_window_is_no_data():
    w = window_state(None, NOW)
    assert (w.pct, w.stale) == (None, True)
    assert describe("S", w, NOW) == "S: no data"


def test_active_window_rounds_and_counts_down():
    w = window_state({"used_percentage": 42.6, "resets_at": NOW + 7800}, NOW)
    assert (w.pct, w.reset_at, w.stale) == (43, NOW + 7800, False)
    assert describe("S", w, NOW) == "S: 43% - resets in 2h 10m"


def test_window_past_reset_shows_zero_and_stale():
    w = window_state({"used_percentage": 80, "resets_at": NOW - 1}, NOW)
    assert (w.pct, w.stale) == (0, True)
    assert describe("S", w, NOW) == "S: 0% (reset)"


def test_clamped_to_0_100():
    assert window_state({"used_percentage": 140}, NOW).pct == 100
    assert window_state({"used_percentage": -3}, NOW).pct == 0


def test_garbage_percentage():
    assert window_state({"used_percentage": "x"}, NOW).pct is None


def test_format_left():
    assert format_left(0) == "now"
    assert format_left(59) == "0m"
    assert format_left(3 * 86400 + 5 * 3600) == "3d 5h"
    assert format_left(125) == "2m"
