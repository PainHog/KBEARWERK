"""Her coloring-page database - a calming outlet built into the app.

Coloring pages are image files kept in a local folder. She can add her own
(upload), list them, and remove them. The colored results can be saved back here
too.
"""

from __future__ import annotations

import os
import shutil
from typing import List

from ..config import config_dir
from .files import unique_destination

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def pages_dir() -> str:
    d = os.path.join(config_dir(), "coloring")
    os.makedirs(d, exist_ok=True)
    return d


def add_page(src_path: str) -> str:
    """Copy an image into the coloring database. Returns the stored path."""
    if not os.path.isfile(src_path):
        raise ValueError("That image can't be found.")
    ext = os.path.splitext(src_path)[1].lower()
    if ext not in IMAGE_EXTS:
        raise ValueError("Please choose an image file (PNG, JPG, GIF, BMP).")
    dest = unique_destination(pages_dir(), os.path.basename(src_path))
    shutil.copy2(src_path, dest)
    return dest


def list_pages() -> List[str]:
    d = pages_dir()
    return [os.path.join(d, f) for f in sorted(os.listdir(d))
            if os.path.splitext(f)[1].lower() in IMAGE_EXTS]


def remove_page(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def colored_output_path(source_path: str) -> str:
    """A destination path for a colored version of a page."""
    base = os.path.splitext(os.path.basename(source_path))[0]
    return unique_destination(pages_dir(), f"{base} - colored.png")
