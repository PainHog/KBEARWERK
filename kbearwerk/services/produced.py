"""A small log of documents the app produced, so Home can show their sync status.

Records the final path of each generated/filed document. The Home screen reads
this and shows a ✓ / ☁ / ⏳ next to recent ones (see syncstatus).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List

from ..config import config_dir


def _path() -> str:
    return os.path.join(config_dir(), "produced.json")


def _load() -> List[Dict[str, Any]]:
    p = _path()
    if not os.path.exists(p):
        return []
    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save(items: List[Dict[str, Any]]) -> None:
    p = _path()
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(items, fh, indent=2)
    os.replace(tmp, p)


def record(path: str, label: str = "") -> None:
    if not path:
        return
    items = _load()
    items.append({"path": path, "label": label or os.path.basename(path), "when": time.time()})
    if len(items) > 500:
        items = items[-500:]
    _save(items)


def recent(n: int = 10) -> List[Dict[str, Any]]:
    return list(reversed(_load()))[:n]
