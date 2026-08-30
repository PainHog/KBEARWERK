"""Colors, fonts and appearance helpers for a clean, professional look.

Colors are given as ``(light, dark)`` tuples where it matters, which is the
format CustomTkinter understands, so the app looks right in either mode.
"""

from __future__ import annotations

import customtkinter as ctk

# Brand palette (professional blue). Tweak freely to match her office colors.
PRIMARY = "#1F4E79"
PRIMARY_HOVER = "#163A5A"
ACCENT = "#2D6CDF"
ACCENT_HOVER = "#2457B8"

SUCCESS = "#1F7A44"
WARNING = "#B26A00"
DANGER = "#B02A2A"
MUTED = "#6B7280"

# Card / surface colors as (light, dark).
CARD = ("#FFFFFF", "#2B2B2B")
CARD_BORDER = ("#E2E6EB", "#3A3A3A")
SIDEBAR = ("#F2F4F7", "#202124")
PAGE_BG = ("#FAFBFC", "#1A1A1A")

# Fonts (tuples so we don't need a live root to construct them).
FONT_TITLE = ("Segoe UI Semibold", 22)
FONT_SUBTITLE = ("Segoe UI", 13)
FONT_CARD_TITLE = ("Segoe UI Semibold", 15)
FONT_BODY = ("Segoe UI", 13)
FONT_SMALL = ("Segoe UI", 11)
FONT_NAV = ("Segoe UI", 14)
FONT_BUTTON = ("Segoe UI Semibold", 13)


def apply(appearance: str = "light") -> None:
    """Set global appearance mode and color theme."""
    mode = appearance if appearance in ("light", "dark", "system") else "light"
    ctk.set_appearance_mode(mode)
    ctk.set_default_color_theme("blue")
