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


def apply(appearance: str = "dark", text_color: str = "") -> None:
    """Set global appearance mode, color theme, and optional text-color override."""
    mode = appearance if appearance in ("light", "dark", "system") else "dark"
    ctk.set_appearance_mode(mode)
    ctk.set_default_color_theme("blue")  # reloads theme dict (resets any override)
    if text_color:
        try:
            ctk.ThemeManager.theme["CTkLabel"]["text_color"] = text_color
        except Exception:
            pass


def style_treeview(style, name: str) -> None:
    """Style a ttk.Treeview to match the current light/dark appearance.

    Without this a table renders bright white in dark mode (overstimulating).
    """
    try:
        style.theme_use("clam")
    except Exception:
        pass
    dark = ctk.get_appearance_mode() == "Dark"
    if dark:
        bg, fg, head_bg, sel = "#2B2B2B", "#E5E7EB", "#202124", PRIMARY
    else:
        bg, fg, head_bg, sel = "#FFFFFF", "#1F2937", "#F2F4F7", ACCENT
    style.configure(name, background=bg, fieldbackground=bg, foreground=fg,
                    rowheight=26, font=("Segoe UI", 11), borderwidth=0)
    style.map(name, background=[("selected", sel)], foreground=[("selected", "#FFFFFF")])
    style.configure(name + ".Heading", background=head_bg, foreground=fg,
                    font=("Segoe UI Semibold", 11))
