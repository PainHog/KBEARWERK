"""A simple activity log - a record that a task was actually done.

When she sends a redline, files a document, or finishes a step, we drop a line
here so there's proof it happened and when. The Home screen shows the most recent
entries so she (and her boss) can see what's been handled.
"""

from __future__ import annotations

import datetime
import json
import os
import time
from typing import Any, Dict, List

from ..config import config_dir

# Standard action labels so counts line up across panels.
JOB_CREATED = "Jobs created"
EMAIL_SENT = "Emails sent"
REDLINE_PROCESSED = "Redlines processed"
DOCUMENT_GENERATED = "Documents generated"
LETTER_GENERATED = "Letters generated"
OBSERVATION_SET = "Observations scheduled"
BILLING_ADDED = "Billing entries"

# Order shown as tiles on the Home screen.
TILE_ACTIONS = [
    JOB_CREATED, EMAIL_SENT, REDLINE_PROCESSED,
    DOCUMENT_GENERATED, LETTER_GENERATED, OBSERVATION_SET,
]


def _path() -> str:
    return os.path.join(config_dir(), "activity.json")


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


def log(action: str, project: str = "", details: str = "") -> None:
    items = _load()
    items.append({
        "when": time.time(),
        "action": action,
        "project": project,
        "details": details,
    })
    # Keep the file from growing without bound.
    if len(items) > 2000:
        items = items[-2000:]
    _save(items)


def recent(n: int = 15) -> List[Dict[str, Any]]:
    return list(reversed(_load()))[:n]


def _start_of_today() -> float:
    now = datetime.datetime.now()
    return datetime.datetime(now.year, now.month, now.day).timestamp()


def _start_of_week() -> float:
    now = datetime.datetime.now()
    monday = now - datetime.timedelta(days=now.weekday())
    return datetime.datetime(monday.year, monday.month, monday.day).timestamp()


def summary_since(since_ts: float) -> Dict[str, int]:
    """Count activity by action label since a timestamp."""
    counts: Dict[str, int] = {}
    for item in _load():
        if item.get("when", 0) >= since_ts:
            action = item.get("action", "")
            counts[action] = counts.get(action, 0) + 1
    return counts


def counts_today() -> Dict[str, int]:
    return summary_since(_start_of_today())


def counts_week() -> Dict[str, int]:
    return summary_since(_start_of_week())


def total_since(since_ts: float) -> int:
    return sum(1 for item in _load() if item.get("when", 0) >= since_ts)
