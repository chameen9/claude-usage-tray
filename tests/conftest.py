import pytest


@pytest.fixture(autouse=True)
def claude_home(tmp_path, monkeypatch):
    """Point every component at a throwaway Claude config dir."""
    d = tmp_path / "claude"
    d.mkdir()
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(d))
    return d
