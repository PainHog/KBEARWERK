"""Cross-list project search.

This powers the "boss just asked about a job - find it NOW" feature. It reads her
project/proposal lists and matches the query against **every** column, so a
search for an address, client, contractor, project number or project name all
work without her having to know which column holds what.

It also (optionally) matches folder names under the base folder, so even a job
that isn't in a list yet can be found.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

from . import excel


@dataclass
class SearchHit:
    title: str                       # best label (project number / name)
    subtitle: str                    # secondary info (client / address)
    source: str                      # which list/folder it came from
    matched_on: List[str] = field(default_factory=list)  # columns that matched
    row: Dict[str, Any] = field(default_factory=dict)    # full row data
    folder: str = ""                 # project folder path if we can find one


@dataclass
class FileHit:
    name: str          # file or folder name
    path: str          # full path on disk
    is_dir: bool       # True = folder, False = file
    job: str = ""      # the top-level job folder it lives under (context)


@dataclass
class TemplateHit:
    name: str          # template name (e.g. "CD Sheet")
    path: str          # blank template file on disk


def search_templates(config: Dict[str, Any], query: str) -> List[TemplateHit]:
    """Match registered document templates by name, so she can search 'CD Sheet'
    and generate it directly without opening a panel."""
    q = (query or "").strip().lower()
    if not q:
        return []
    hits: List[TemplateHit] = []
    for t in config.get("templates", []):
        name = t.get("name", "")
        if name and q in name.lower():
            hits.append(TemplateHit(name=name, path=t.get("path", "")))
    return hits


# Header names we prefer when building a title/subtitle. Matched loosely.
_TITLE_KEYS = ["project number", "project no", "job number", "job #", "job no", "number", "project", "project name", "job name", "name"]
_CLIENT_KEYS = ["client", "client name", "owner", "customer"]
_ADDRESS_KEYS = ["address", "project address", "site address", "location"]
_CONTRACTOR_KEYS = ["contractor", "general contractor", "gc"]


def _first(row: Dict[str, Any], keys: List[str]) -> str:
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for key in keys:
        if key in lowered and lowered[key] not in (None, ""):
            return str(lowered[key]).strip()
    return ""


def _hit_from_row(row: Dict[str, Any], source: str, query: str) -> SearchHit:
    q = query.lower()
    matched = [str(k) for k, v in row.items() if v is not None and q in str(v).lower()]

    number = _first(row, ["project number", "project no", "job number", "job #", "job no", "number"])
    name = _first(row, ["project name", "job name", "project", "name"])
    client = _first(row, _CLIENT_KEYS)
    address = _first(row, _ADDRESS_KEYS)
    contractor = _first(row, _CONTRACTOR_KEYS)

    title = " - ".join(p for p in (number, name) if p) or name or number or "(project)"
    sub_bits = [b for b in (client, address, contractor) if b]
    subtitle = "  •  ".join(sub_bits)

    return SearchHit(
        title=title,
        subtitle=subtitle,
        source=source,
        matched_on=matched,
        row=row,
        folder="",
    )


def search(config: Dict[str, Any], query: str, limit: int = 100) -> List[SearchHit]:
    """Search the configured project/proposal lists for ``query``.

    Returns hits sorted so exact/earlier matches come first. Never raises for a
    missing or open file - those lists are simply skipped (their trouble is
    surfaced elsewhere), so search stays fast and reliable under stress.
    """
    query = (query or "").strip()
    if not query:
        return []

    paths = config.get("paths", {})
    sources = [
        (paths.get("project_list", ""), "Project List"),
        (paths.get("proposal_list", ""), "Proposal List"),
    ]

    hits: List[SearchHit] = []
    seen = set()
    for path, label in sources:
        if not path or not os.path.exists(path):
            continue
        try:
            rows = excel.read_rows(path)
        except Exception:
            continue  # locked/corrupt: skip rather than fail the whole search
        q = query.lower()
        for row in rows:
            if any(v is not None and q in str(v).lower() for v in row.values()):
                hit = _hit_from_row(row, label, query)
                key = (hit.title, hit.subtitle)
                if key in seen:
                    continue
                seen.add(key)
                # Try to locate the folder for a quick "Open Folder".
                base = config.get("base_folder", "")
                if base and os.path.isdir(base):
                    number = _first(row, ["project number", "project no", "job number", "job #", "job no", "number"])
                    name = _first(row, ["project name", "job name", "project", "name"])
                    from .files import find_project_folder
                    hit.folder = find_project_folder(base, number, name) or ""
                hits.append(hit)
                if len(hits) >= limit:
                    return hits
    return hits


# Folders we never want to descend into or return.
_SKIP_DIRS = {".git", "$recycle.bin", "system volume information", "__pycache__"}


def _top_job(base: str, path: str) -> str:
    """The first folder under ``base`` that ``path`` lives in (its job folder)."""
    try:
        rel = os.path.relpath(path, base)
    except ValueError:
        return ""
    parts = rel.split(os.sep)
    return parts[0] if parts and parts[0] not in (".", "..") else ""


def search_files(config: Dict[str, Any], query: str, limit: int = 250) -> List[FileHit]:
    """Find every folder and file under the work folder whose name matches.

    This is the "type Callahan, see every folder and file" finder. Folders come
    first (so the job folder is easy to spot), then files. It never raises - an
    unreachable drive just yields no results.
    """
    query = (query or "").strip().lower()
    base = config.get("base_folder", "")
    if not query or not base or not os.path.isdir(base):
        return []

    folder_hits: List[FileHit] = []
    file_hits: List[FileHit] = []
    try:
        for root, dirs, filenames in os.walk(base):
            # Prune noise folders in place so we don't descend into them.
            dirs[:] = [d for d in dirs if d.lower() not in _SKIP_DIRS]
            for d in dirs:
                if query in d.lower():
                    p = os.path.join(root, d)
                    folder_hits.append(FileHit(d, p, True, _top_job(base, p)))
            for f in filenames:
                if query in f.lower():
                    p = os.path.join(root, f)
                    file_hits.append(FileHit(f, p, False, _top_job(base, p)))
            if len(folder_hits) + len(file_hits) >= limit * 2:
                break
    except OSError:
        pass
    return (folder_hits + file_hits)[:limit]
