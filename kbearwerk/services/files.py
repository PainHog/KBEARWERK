"""File-system helpers: create project folders, open folders, file documents.

These work on any OS so they can be tested on Linux. Windows-specific niceties
(opening a folder in Explorer) degrade gracefully elsewhere.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import List, Optional

# Characters Windows forbids in file/folder names.
_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def clean_name(name: str) -> str:
    """Make a string safe to use as a folder/file name.

    Replaces characters Windows forbids, collapses whitespace and trims
    trailing dots/spaces (also illegal on Windows).
    """
    cleaned = _INVALID_CHARS.sub(" ", name or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.rstrip(". ")
    return cleaned


def format_folder_name(pattern: str, *, number: str = "", name: str = "", client: str = "") -> str:
    """Build a project folder name from a pattern like ``"{number} - {name}"``."""
    try:
        raw = pattern.format(number=number, name=name, client=client)
    except (KeyError, IndexError):
        # Bad pattern: fall back to something sensible rather than crashing.
        raw = " - ".join(p for p in (number, name) if p)
    raw = clean_name(raw)
    # If the pattern left dangling separators (e.g. missing number), tidy them.
    raw = re.sub(r"^\W+|\W+$", "", raw).strip()
    return raw or clean_name(name) or clean_name(number) or "New Project"


@dataclass
class FolderResult:
    path: str
    created: bool          # True if we made it, False if it already existed
    subfolders_created: List[str] = field(default_factory=list)


def create_project_folder(
    base_folder: str,
    folder_name: str,
    subfolders: Optional[List[str]] = None,
) -> FolderResult:
    """Create ``base_folder/folder_name`` plus the given sub-folders.

    Safe to call twice: existing folders are left alone (never overwritten),
    and we report whether the top folder already existed so the UI can warn.

    Raises ``ValueError`` if ``base_folder`` is blank or does not exist.
    """
    if not base_folder:
        raise ValueError("No base folder is set. Set it in Settings first.")
    if not os.path.isdir(base_folder):
        raise ValueError(f"Base folder does not exist:\n{base_folder}")

    folder_name = clean_name(folder_name)
    if not folder_name:
        raise ValueError("Project folder name is empty.")

    project_path = os.path.join(base_folder, folder_name)
    already_existed = os.path.isdir(project_path)
    os.makedirs(project_path, exist_ok=True)

    made: List[str] = []
    for sub in subfolders or []:
        sub = clean_name(sub)
        if not sub:
            continue
        sub_path = os.path.join(project_path, sub)
        if not os.path.isdir(sub_path):
            os.makedirs(sub_path, exist_ok=True)
            made.append(sub)

    return FolderResult(path=project_path, created=not already_existed, subfolders_created=made)


def open_in_file_manager(path: str) -> None:
    """Open ``path`` in the OS file manager (Explorer on Windows)."""
    if not path or not os.path.exists(path):
        raise ValueError(f"Path does not exist:\n{path}")
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]  # noqa: S606 (Windows only)
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


def unique_destination(dest_dir: str, filename: str) -> str:
    """Return a path in ``dest_dir`` for ``filename`` that does not clobber an
    existing file (appends " (2)", " (3)", ... before the extension)."""
    os.makedirs(dest_dir, exist_ok=True)
    stem, ext = os.path.splitext(filename)
    candidate = os.path.join(dest_dir, filename)
    counter = 2
    while os.path.exists(candidate):
        candidate = os.path.join(dest_dir, f"{stem} ({counter}){ext}")
        counter += 1
    return candidate


def file_into_folder(src: str, dest_dir: str, new_name: Optional[str] = None, move: bool = False) -> str:
    """Copy (or move) a file into ``dest_dir``, optionally renaming it.

    Never overwrites an existing file. Returns the final path.
    """
    if not os.path.isfile(src):
        raise ValueError(f"File not found:\n{src}")
    filename = new_name or os.path.basename(src)
    filename = clean_name(os.path.splitext(filename)[0]) + os.path.splitext(filename)[1]
    dest = unique_destination(dest_dir, filename)
    if move:
        shutil.move(src, dest)
    else:
        shutil.copy2(src, dest)
    return dest


def find_project_folder(base_folder: str, number: str = "", name: str = "") -> Optional[str]:
    """Best-effort: find an existing project folder by number or name.

    Returns the first sub-folder of ``base_folder`` whose name contains the
    project number (preferred) or the project name. Used to route redlines and
    observations to the right place.
    """
    if not base_folder or not os.path.isdir(base_folder):
        return None
    number = (number or "").strip().lower()
    name = (name or "").strip().lower()
    best = None
    for entry in sorted(os.listdir(base_folder)):
        full = os.path.join(base_folder, entry)
        if not os.path.isdir(full):
            continue
        low = entry.lower()
        if number and number in low:
            return full
        if name and name in low and best is None:
            best = full
    return best
