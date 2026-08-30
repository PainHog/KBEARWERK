"""Shared base class for every panel.

Provides a consistent header, a scrollable body, a ``card()`` helper for the
boxed sections, simple dialog helpers, and - importantly - ``run_async`` so slow
work (reading Outlook, saving Excel on a network drive) runs off the UI thread
and never freezes the window.
"""

from __future__ import annotations

import threading
from tkinter import filedialog, messagebox
from typing import Callable, Optional

import customtkinter as ctk

from .. import theme


class BasePanel(ctk.CTkFrame):
    # Overridden by subclasses.
    title: str = "Panel"
    subtitle: str = ""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()

        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=(28, 20), pady=(4, 16))
        self.body.grid_columnconfigure(0, weight=1)

        self.build()

    # -- lifecycle -------------------------------------------------------
    def build(self) -> None:
        """Build the panel contents. Override in subclasses."""

    def on_show(self) -> None:
        """Called each time the panel becomes visible. Override to refresh."""

    # -- header ----------------------------------------------------------
    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 6))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=self.title, font=theme.FONT_TITLE, anchor="w").grid(
            row=0, column=0, sticky="w"
        )
        if self.subtitle:
            ctk.CTkLabel(
                header, text=self.subtitle, font=theme.FONT_SUBTITLE,
                text_color=theme.MUTED, anchor="w",
            ).grid(row=1, column=0, sticky="w", pady=(2, 0))

    # -- layout helpers --------------------------------------------------
    def card(self, title: Optional[str] = None, description: Optional[str] = None) -> ctk.CTkFrame:
        """Create and pack a boxed 'card' section in the body; return its inner frame."""
        outer = ctk.CTkFrame(
            self.body, fg_color=theme.CARD, corner_radius=12,
            border_width=1, border_color=theme.CARD_BORDER,
        )
        outer.pack(fill="x", pady=(0, 14))
        outer.grid_columnconfigure(0, weight=1)
        row = 0
        if title:
            ctk.CTkLabel(outer, text=title, font=theme.FONT_CARD_TITLE, anchor="w").grid(
                row=row, column=0, sticky="w", padx=18, pady=(16, 2)
            )
            row += 1
        if description:
            ctk.CTkLabel(
                outer, text=description, font=theme.FONT_SMALL,
                text_color=theme.MUTED, anchor="w", justify="left",
            ).grid(row=row, column=0, sticky="w", padx=18, pady=(0, 6))
            row += 1
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.grid(row=row, column=0, sticky="ew", padx=18, pady=(4, 16))
        inner.grid_columnconfigure(0, weight=1)
        return inner

    def primary_button(self, parent, text, command, **kw) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent, text=text, command=command, font=theme.FONT_BUTTON,
            fg_color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER,
            height=36, corner_radius=8, **kw,
        )

    def accent_button(self, parent, text, command, **kw) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent, text=text, command=command, font=theme.FONT_BUTTON,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            height=34, corner_radius=8, **kw,
        )

    def ghost_button(self, parent, text, command, **kw) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent, text=text, command=command, font=theme.FONT_BUTTON,
            fg_color="transparent", hover_color=theme.SIDEBAR,
            text_color=theme.PRIMARY, border_width=1, border_color=theme.PRIMARY,
            height=34, corner_radius=8, **kw,
        )

    # -- threading -------------------------------------------------------
    def run_async(
        self,
        work: Callable,
        on_done: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        busy: str = "",
    ) -> None:
        """Run ``work()`` in a background thread; deliver results on the UI thread."""
        if busy:
            self.app.set_status(busy)

        def runner():
            try:
                result = work()
            except Exception as exc:  # noqa: BLE001 - surfaced to the user
                self.after(0, lambda e=exc: (on_error or self._default_error)(e))
                return
            if on_done:
                self.after(0, lambda r=result: on_done(r))
            else:
                self.after(0, lambda: self.app.set_status("Done."))

        threading.Thread(target=runner, daemon=True).start()

    def _default_error(self, exc: Exception) -> None:
        self.app.set_status("Something went wrong.")
        self.show_error(str(exc))

    # -- dialogs ---------------------------------------------------------
    def show_error(self, message: str, title: str = "Problem") -> None:
        messagebox.showerror(title, message, parent=self)

    def show_info(self, message: str, title: str = "Done") -> None:
        messagebox.showinfo(title, message, parent=self)

    def ask_yes_no(self, message: str, title: str = "Please confirm") -> bool:
        return bool(messagebox.askyesno(title, message, parent=self))

    def pick_file(self, title: str = "Choose a file", filetypes=None) -> str:
        return filedialog.askopenfilename(
            title=title, filetypes=filetypes or [("All files", "*.*")], parent=self
        ) or ""

    def pick_folder(self, title: str = "Choose a folder") -> str:
        return filedialog.askdirectory(title=title, parent=self) or ""

    # -- convenience -----------------------------------------------------
    @property
    def config(self) -> dict:
        return self.app.config_data
