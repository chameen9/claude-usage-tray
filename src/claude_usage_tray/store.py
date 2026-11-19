"""JSON read/write helpers for the cache and the tool's config."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

from . import paths


def read_json(path: Path) -> Optional[Any]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def write_json_atomic(path: Path, data: Any, indent: Optional[int] = None) -> None:
    """Write via temp file + rename so readers never see a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            if indent:
                f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---- config ---------------------------------------------------------------

DEFAULT_CONFIG = {
    "live_polling": False,
    "poll_interval_seconds": 300,
    "layout": None,  # "split" | "combined"; None = platform default
}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    data = read_json(paths.config_file())
    if isinstance(data, dict):
        cfg.update(data)
    return cfg


def save_config(cfg: dict) -> None:
    write_json_atomic(paths.config_file(), cfg, indent=2)


def update_config(**changes: Any) -> dict:
    cfg = load_config()
    cfg.update(changes)
    save_config(cfg)
    return cfg


# ---- usage cache ------------------------------------------------------------

def write_usage(five_hour: Any, seven_day: Any, source: str, now: Optional[int] = None) -> None:
    write_json_atomic(
        paths.cache_file(),
        {
            "updated_at": int(now if now is not None else time.time()),
            "source": source,
            "five_hour": five_hour,
            "seven_day": seven_day,
        },
    )


def read_usage() -> Optional[dict]:
    data = read_json(paths.cache_file())
    return data if isinstance(data, dict) else None
