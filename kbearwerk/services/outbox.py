"""The safety net: a local "outbox" so her work is never lost to a cloud desync.

When a save to a cloud file/folder fails because the location is temporarily
unreachable, we don't throw her work away - we stash it here on her PC and mark it
pending. When the location comes back, :func:`flush` replays everything.

Two kinds of pending work:
  * ``excel_append`` - a row that should be appended to a spreadsheet.
  * ``file_copy``   - a generated document that should be copied into a folder
    (the file itself is copied into the outbox so it survives even if the
    original temp file goes away).
"""

from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from typing import Any, Dict, List

from ..config import config_dir


def _dir() -> str:
    d = os.path.join(config_dir(), "outbox")
    os.makedirs(os.path.join(d, "files"), exist_ok=True)
    return d


def _manifest_path() -> str:
    return os.path.join(_dir(), "manifest.json")


def _load() -> List[Dict[str, Any]]:
    path = _manifest_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _store(items: List[Dict[str, Any]]) -> None:
    path = _manifest_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(items, fh, indent=2)
    os.replace(tmp, path)


def pending_count() -> int:
    return len(_load())


def list_pending() -> List[Dict[str, Any]]:
    return _load()


def queue_excel_append(path: str, values: Dict[str, Any], sheet=None, unique_key=None, label: str = "") -> None:
    items = _load()
    items.append({
        "id": uuid.uuid4().hex,
        "kind": "excel_append",
        "created": time.time(),
        "label": label or os.path.basename(path),
        "path": path,
        "values": values,
        "sheet": sheet,
        "unique_key": unique_key,
    })
    _store(items)


def queue_file_copy(local_src: str, dest_dir: str, filename: str, label: str = "") -> None:
    items = _load()
    item_id = uuid.uuid4().hex
    ext = os.path.splitext(local_src)[1]
    stored = os.path.join(_dir(), "files", item_id + ext)
    shutil.copy2(local_src, stored)
    items.append({
        "id": item_id,
        "kind": "file_copy",
        "created": time.time(),
        "label": label or filename,
        "stored": stored,
        "dest_dir": dest_dir,
        "filename": filename,
    })
    _store(items)


def flush() -> Dict[str, int]:
    """Try to replay every pending item. Successful ones are removed.

    Returns {"done": N, "pending": M}. Never raises - a still-unreachable target
    just stays pending for next time.
    """
    from . import excel
    from .files import unique_destination

    items = _load()
    remaining: List[Dict[str, Any]] = []
    done = 0
    for item in items:
        try:
            if item["kind"] == "excel_append":
                excel.append_row(item["path"], item["values"], item.get("sheet"), item.get("unique_key"))
                done += 1
            elif item["kind"] == "file_copy":
                if not os.path.isdir(item["dest_dir"]):
                    raise OSError("destination folder not available")
                dest = unique_destination(item["dest_dir"], item["filename"])
                shutil.copy2(item["stored"], dest)
                try:
                    os.remove(item["stored"])
                except OSError:
                    pass
                done += 1
            else:
                remaining.append(item)
        except Exception:
            remaining.append(item)  # still can't reach it; keep for later
    _store(remaining)
    return {"done": done, "pending": len(remaining)}
