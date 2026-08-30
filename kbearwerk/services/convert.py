"""Convert Word documents to PDF.

On her PC (Windows + Word) this uses Word itself, so the PDF looks exactly like
the document — seals, letterhead and all. If Word isn't available it falls back to
LibreOffice (``soffice``) when present. Either way it degrades to a clear message
rather than crashing.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


class ConvertError(Exception):
    """A user-friendly conversion problem."""


def available() -> bool:
    """True if some engine can produce a PDF here."""
    if sys.platform == "win32":
        try:
            import docx2pdf  # noqa: F401
            return True
        except Exception:
            pass
    return _soffice_path() is not None


def _soffice_path():
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    return None


def to_pdf(docx_path: str, pdf_path: str = "") -> str:
    """Convert ``docx_path`` to PDF. Returns the PDF path.

    ``pdf_path`` defaults to the same name with a .pdf extension.
    """
    if not os.path.exists(docx_path):
        raise ConvertError(f"Document not found:\n{docx_path}")
    if not pdf_path:
        pdf_path = os.path.splitext(docx_path)[0] + ".pdf"

    # Preferred on Windows: Word via docx2pdf (pixel-perfect).
    if sys.platform == "win32":
        try:
            from docx2pdf import convert
            convert(docx_path, pdf_path)
            if os.path.exists(pdf_path):
                return pdf_path
        except Exception as exc:
            # Fall through to LibreOffice if that's around; else report Word error.
            if _soffice_path() is None:
                raise ConvertError(
                    "Couldn't convert to PDF with Word. Make sure Microsoft Word "
                    f"is installed.\n\n({exc})"
                )

    soffice = _soffice_path()
    if soffice:
        out_dir = os.path.dirname(os.path.abspath(pdf_path)) or "."
        try:
            subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf", "--outdir", out_dir, docx_path],
                check=True, capture_output=True, timeout=120,
            )
            produced = os.path.join(out_dir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")
            if produced != pdf_path and os.path.exists(produced):
                os.replace(produced, pdf_path)
            if os.path.exists(pdf_path):
                return pdf_path
        except Exception as exc:
            raise ConvertError(f"Couldn't convert to PDF with LibreOffice.\n\n({exc})")

    raise ConvertError(
        "No PDF converter is available here. On her Windows PC with Microsoft "
        "Word installed this will work automatically."
    )
