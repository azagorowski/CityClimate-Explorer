"""JSON cache and processed dataset storage helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path, default: Any = None) -> Any:
    """Read JSON from *path*, returning *default* when it does not exist."""
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data: Any) -> None:
    """Atomically-ish write JSON data to *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
    tmp.replace(path)


def cache_key(value: str) -> str:
    """Return a filesystem-safe cache key."""
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value)[:180]
