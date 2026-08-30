"""Edit Excel workbooks through Excel itself (Windows COM).

Her inspection workbooks are heavily edited - data-validation **dropdowns**,
**checkboxes**, **multiple tabs**, formulas, maybe macros. The lightweight
library (openpyxl) can drop those on save. To keep every one of them intact, this
engine asks the installed **Excel application** to open the file, make the edit,
and save - so the file is written exactly the way Excel would write it.

Only used on Windows with Excel installed; :func:`available` gates it. Simple flat
lists keep using the fast openpyxl path.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional

# Excel constant: Range.End direction "up".
_XL_UP = -4162


def available() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import win32com.client  # noqa: F401
        return True
    except Exception:
        return False


class ExcelComError(Exception):
    """A user-friendly problem from the Excel COM engine."""


def _norm(v: Any) -> str:
    return str(v).strip().lower() if v is not None else ""


class _ExcelSession:
    """Context manager that opens Excel, yields the workbook, saves & cleans up."""

    def __init__(self, path: str, save: bool):
        self.path = path
        self.save = save
        self.app = None
        self.wb = None

    def __enter__(self):
        import win32com.client
        try:
            self.app = win32com.client.DispatchEx("Excel.Application")
        except Exception as exc:
            raise ExcelComError(f"Couldn't start Excel: {exc}")
        self.app.Visible = False
        self.app.DisplayAlerts = False
        try:
            self.wb = self.app.Workbooks.Open(self.path)
        except Exception as exc:
            self._quit()
            raise ExcelComError(
                f"Couldn't open the workbook (it may be on a disconnected cloud "
                f"drive, or open elsewhere):\n{self.path}\n\n({exc})"
            )
        return self.wb

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.wb is not None:
                if self.save and exc_type is None:
                    self.wb.Save()
                self.wb.Close(SaveChanges=False)
        finally:
            self._quit()
        return False

    def _quit(self):
        try:
            if self.app is not None:
                self.app.Quit()
        except Exception:
            pass
        self.app = None
        self.wb = None


def _sheet(wb, sheet_name: Optional[str]):
    if sheet_name:
        for ws in wb.Worksheets:
            if _norm(ws.Name) == _norm(sheet_name):
                return ws
        raise ExcelComError(f"Tab '{sheet_name}' not found. Tabs: "
                            + ", ".join(ws.Name for ws in wb.Worksheets))
    return wb.Worksheets(1)


def list_sheets(path: str) -> List[str]:
    with _ExcelSession(path, save=False) as wb:
        return [ws.Name for ws in wb.Worksheets]


def _headers(ws) -> Dict[str, int]:
    """Map normalised header -> column index, reading row 1 until a blank gap."""
    mapping: Dict[str, int] = {}
    col = 1
    blanks = 0
    while blanks < 5 and col < 200:
        val = ws.Cells(1, col).Value
        key = _norm(val)
        if key:
            mapping.setdefault(key, col)
            blanks = 0
        else:
            blanks += 1
        col += 1
    return mapping


def append_rows(path: str, rows: List[Dict[str, Any]], sheet_name: Optional[str] = None) -> int:
    """Append rows to a sheet, matching dict keys to headers, preserving the file.

    Writes each row at the next empty row (never overwrites). Returns how many
    rows were written.
    """
    if not rows:
        return 0
    with _ExcelSession(path, save=True) as wb:
        ws = _sheet(wb, sheet_name)
        headers = _headers(ws)
        if not headers:
            raise ExcelComError("That tab has no header row to match columns to.")
        next_row = int(ws.Cells(ws.Rows.Count, 1).End(_XL_UP).Row) + 1
        written = 0
        for values in rows:
            for key, val in values.items():
                col = headers.get(_norm(key))
                if col:
                    ws.Cells(next_row, col).Value = val
            next_row += 1
            written += 1
        return written


def read_rows(path: str, sheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read a sheet's rows as dicts keyed by header text (values only)."""
    with _ExcelSession(path, save=False) as wb:
        ws = _sheet(wb, sheet_name)
        used = ws.UsedRange
        data = used.Value  # tuple of tuples
        if not data:
            return []
        headers = [str(h).strip() if h is not None else f"Column {i+1}"
                   for i, h in enumerate(data[0])]
        rows: List[Dict[str, Any]] = []
        for r in data[1:]:
            if all(c is None or str(c).strip() == "" for c in r):
                continue
            rows.append({headers[i]: r[i] for i in range(len(headers))})
        return rows
