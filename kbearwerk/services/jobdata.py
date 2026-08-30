"""Per-job data record - the "pull list" that makes 'enter once' real.

Everything she types for a job anywhere in the app (client, address, contractor,
dates, contacts, and later any field from any form) is remembered here, keyed by
project number. Every future sheet/letter pre-fills from this record, so the same
information never has to be typed twice.

Stored locally as JSON. Values are always merged (never wiped), and blank values
don't overwrite existing ones - so partial entry is safe and nothing is lost.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from ..config import config_dir


def _path() -> str:
    return os.path.join(config_dir(), "jobdata.json")


def _load() -> Dict[str, Any]:
    p = _path()
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: Dict[str, Any]) -> None:
    p = _path()
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, p)


def _key(project_number: str) -> str:
    return (project_number or "").strip()


def get(project_number: str) -> Dict[str, Any]:
    """Return the stored field record for a job (empty dict if none)."""
    return dict(_load().get(_key(project_number), {}))


def update(project_number: str, fields: Dict[str, Any]) -> None:
    """Merge ``fields`` into the job's record.

    Blank values are ignored so we never erase a value she entered earlier.
    """
    key = _key(project_number)
    if not key:
        return
    data = _load()
    rec = data.get(key, {})
    for k, v in fields.items():
        if v is None:
            continue
        if isinstance(v, str) and v.strip() == "":
            continue  # don't overwrite existing data with a blank
        rec[k] = v
    data[key] = rec
    _save(data)


def set_field(project_number: str, field: str, value: Any) -> None:
    key = _key(project_number)
    if not key:
        return
    data = _load()
    rec = data.get(key, {})
    rec[field] = value
    data[key] = rec
    _save(data)


def all_numbers() -> list:
    return sorted(_load().keys())
