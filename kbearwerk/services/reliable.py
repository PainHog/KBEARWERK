"""Resilient saves - the layer panels call so her work is never lost.

* :func:`excel_append` appends a row; if the cloud file is unreachable it stashes
  the row in the local outbox and returns ``"queued"`` instead of failing.
* :func:`place_file` copies a generated document into one or more folders; any
  unreachable folder is queued for later.

"File is open in Excel" is deliberately **not** swallowed - that should tell her
to close Excel and retry, not be queued (which could duplicate the row).
"""

from __future__ import annotations

import os
import shutil
from typing import Any, Dict, List, Tuple

from . import excel, excel_com, outbox, produced
from .files import unique_destination
from ..config import config_dir


def excel_append(path: str, values: Dict[str, Any], sheet=None, unique_key=None,
                 label: str = "", prefer_com: bool = False) -> str:
    """Append a row. Return 'added' | 'updated' | 'queued'.

    Raises ExcelBusyError if the file is open in Excel (so the caller can ask her
    to close it). If the cloud location is unreachable, the row is stashed in the
    local outbox and 'queued' is returned - never lost.

    ``prefer_com=True`` routes through the Excel application (preserving
    dropdowns/checkboxes/tabs/macros) when it's available - use it for the
    heavily-edited inspection workbooks.
    """
    if prefer_com and excel_com.available():
        try:
            excel_com.append_rows(path, [values], sheet)
            return "added"
        except excel_com.ExcelComError:
            outbox.queue_excel_append(path, values, sheet, unique_key, label=label)
            return "queued"
    try:
        return excel.append_row(path, values, sheet, unique_key)
    except excel.ExcelBusyError:
        raise  # let the caller ask her to close Excel
    except excel.ExcelUnavailableError:
        outbox.queue_excel_append(path, values, sheet, unique_key, label=label)
        return "queued"


def local_temp(filename: str) -> str:
    """A safe local path to generate a file into before copying it out."""
    d = os.path.join(config_dir(), "generated")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, filename)


def place_file(local_src: str, dest_dirs: List[str], filename: str, label: str = "") -> Tuple[List[str], List[str]]:
    """Copy ``local_src`` into each destination folder.

    Returns ``(written, queued)`` - folders that were reachable vs. queued for
    later. The local source copy is kept in the outbox for any queued folder, so
    her document is never lost.
    """
    written: List[str] = []
    queued: List[str] = []
    for d in dest_dirs:
        if not d:
            continue
        try:
            if not os.path.isdir(d):
                raise OSError("folder not available")
            dest = unique_destination(d, filename)
            shutil.copy2(local_src, dest)
            written.append(dest)
            produced.record(dest, label)  # so Home can show its sync status
        except OSError:
            outbox.queue_file_copy(local_src, d, filename, label=label)
            queued.append(d)
    return written, queued
