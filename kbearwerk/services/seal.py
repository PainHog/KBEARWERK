"""Sealed-document flow: draft for review, then apply the engineer's seal.

Engineering letters can't go out unsealed or unreviewed. So generating a city
letter is two steps:

1. **Draft** - fill the template, but leave the seal/signature empty and stamp a
   "DRAFT - FOR REVIEW (NOT SEALED)" notice. She opens and checks it.
2. **Seal and Save** - re-fill the same template, this time dropping in the
   engineer's saved **signature** and **seal** images, and save the final.

Templates mark the spots with ``{{ signature }}``, ``{{ seal }}`` and
``{{ draft_notice }}`` tags. Image insertion needs ``docxtpl``; without it we can
still produce the draft (text only) and warn that sealing needs the Word engine.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

try:
    from docxtpl import DocxTemplate, InlineImage
    from docx.shared import Inches
    _DOCXTPL_OK = True
except Exception:  # pragma: no cover
    _DOCXTPL_OK = False


class SealError(Exception):
    """A user-friendly sealing problem."""


DRAFT_NOTICE = "DRAFT — FOR REVIEW (NOT SEALED)"


def find_engineer(config: Dict[str, Any], name: str = "") -> Optional[Dict[str, str]]:
    seals = config.get("seals", [])
    name = name or config.get("default_engineer", "")
    if name:
        for s in seals:
            if s.get("name") == name:
                return s
    return seals[0] if seals else None


def render_draft(template_path: str, context: Dict[str, str], out_path: str) -> str:
    """Fill the template unsealed, with a DRAFT notice. Returns the path."""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    ctx = dict(context)
    ctx.setdefault("draft_notice", DRAFT_NOTICE)
    ctx["signature"] = ""
    ctx["seal"] = ""
    # Reuse the general template filler (docxtpl or fallback) for the draft.
    from . import templates
    return templates.fill_template(template_path, ctx, out_path)


def render_sealed(template_path: str, context: Dict[str, str], out_path: str,
                  signature_image: str = "", seal_image: str = "") -> str:
    """Fill the template with the engineer's signature + seal images. Returns path."""
    if not _DOCXTPL_OK:
        raise SealError("Applying a seal needs the Word engine (docxtpl). Please reinstall the app.")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    try:
        doc = DocxTemplate(template_path)
        ctx = dict(context)
        ctx["draft_notice"] = ""
        ctx["signature"] = (InlineImage(doc, signature_image, width=Inches(2.0))
                            if signature_image and os.path.exists(signature_image) else "")
        ctx["seal"] = (InlineImage(doc, seal_image, width=Inches(1.5))
                       if seal_image and os.path.exists(seal_image) else "")
        doc.render(ctx)
        doc.save(out_path)
        return out_path
    except Exception as exc:
        raise SealError(f"Couldn't seal the document:\n{exc}")
