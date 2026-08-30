"""Office schedule / calendar panel.

A light starting point: quick reminders/notes she can keep, plus a shortcut to the
Outlook calendar. We'll tailor this once we know how she actually keeps the office
schedule (an Outlook calendar, an Excel schedule sheet, or a wall calendar she'd
like to move into the app).
"""

from __future__ import annotations

import datetime
import json
import os
import webbrowser

import customtkinter as ctk

from .. import theme
from .base import BasePanel
from ..config import config_dir


class SchedulePanel(BasePanel):
    title = "Schedule"
    subtitle = "Office reminders and calendar — we'll shape this to how she works."

    def build(self) -> None:
        self._build_calendar()
        self._build_reminders()

    def _build_calendar(self) -> None:
        card = self.card("Calendar", "Open the office calendar to add or check appointments.")
        card.grid_columnconfigure(0, weight=1)
        self.primary_button(card, "📅  Open Outlook Calendar", self._open_calendar, width=240).grid(
            row=0, column=0, sticky="w")
        ctk.CTkLabel(card, text="(Tell me how the office schedule is kept and I'll build it in here — "
                                "e.g. read/write an Outlook calendar or a schedule spreadsheet.)",
                     font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w", justify="left",
                     wraplength=760).grid(row=1, column=0, sticky="w", pady=(8, 0))

    def _open_calendar(self) -> None:
        webbrowser.open("https://outlook.office.com/calendar/")
        self.app.set_status("Opened Outlook calendar in the browser.")

    def _build_reminders(self) -> None:
        card = self.card("Quick reminders", "Simple notes so nothing gets forgotten.")
        card.grid_columnconfigure(0, weight=1)
        addf = ctk.CTkFrame(card, fg_color="transparent")
        addf.grid(row=0, column=0, sticky="ew")
        addf.grid_columnconfigure(1, weight=1)
        self.date_entry = ctk.CTkEntry(addf, width=120, height=32)
        self.date_entry.insert(0, datetime.date.today().strftime("%m/%d/%Y"))
        self.date_entry.grid(row=0, column=0, padx=(0, 8))
        self.text_entry = ctk.CTkEntry(addf, height=32, placeholder_text="Reminder…")
        self.text_entry.grid(row=0, column=1, sticky="ew")
        self.text_entry.bind("<Return>", lambda _e: self.add())
        self.ghost_button(addf, "Add", self.add, width=70).grid(row=0, column=2, padx=(8, 0))

        self.list_holder = ctk.CTkFrame(card, fg_color="transparent")
        self.list_holder.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.list_holder.grid_columnconfigure(0, weight=1)
        self._render()

    # -- storage ---------------------------------------------------------
    def _path(self):
        return os.path.join(config_dir(), "schedule.json")

    def _load(self):
        try:
            with open(self._path(), "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return []

    def _save(self, items):
        with open(self._path(), "w", encoding="utf-8") as fh:
            json.dump(items, fh, indent=2)

    def _render(self):
        for child in self.list_holder.winfo_children():
            child.destroy()
        items = self._load()
        if not items:
            ctk.CTkLabel(self.list_holder, text="No reminders yet.", font=theme.FONT_SMALL,
                         text_color=theme.MUTED, anchor="w").grid(row=0, column=0, sticky="w")
        for i, it in enumerate(items):
            rowf = ctk.CTkFrame(self.list_holder, fg_color=theme.SIDEBAR, corner_radius=6)
            rowf.grid(row=i, column=0, sticky="ew", pady=1)
            rowf.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(rowf, text=f"{it.get('date','')}   {it.get('text','')}", font=theme.FONT_SMALL,
                         anchor="w").grid(row=0, column=0, sticky="w", padx=10, pady=6)
            ctk.CTkButton(rowf, text="✓ Done", width=64, height=24, fg_color="transparent",
                          text_color=theme.SUCCESS, hover_color="#E4E8EE",
                          command=lambda idx=i: self.remove(idx)).grid(row=0, column=1, padx=6)

    def add(self):
        text = self.text_entry.get().strip()
        if not text:
            return
        items = self._load()
        items.append({"date": self.date_entry.get().strip(), "text": text})
        self._save(items)
        self.text_entry.delete(0, "end")
        self._render()

    def remove(self, idx):
        items = self._load()
        if 0 <= idx < len(items):
            items.pop(idx)
            self._save(items)
            self._render()
