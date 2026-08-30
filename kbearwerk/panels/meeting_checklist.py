"""Weekly Meeting Checklist panel.

A reusable checklist for her weekly meeting. Items come from a template she can
edit; tick them off during the meeting; "New week" resets the ticks. She can also
print the checklist. (Next step: auto-pull each job's outstanding items from the
Needed panel into this checklist.)
"""

from __future__ import annotations

import json
import os

import customtkinter as ctk

from .. import theme
from .base import BasePanel
from ..config import config_dir


DEFAULT_ITEMS = [
    "Review new proposals / accepted jobs",
    "Review outstanding redlines with drafters",
    "Confirm this week's observations / inspections",
    "Review billing status on active jobs",
    "Collect any missing documents / info per job",
    "Update the office schedule / calendar",
]


class MeetingChecklistPanel(BasePanel):
    title = "Meeting Checklist"
    subtitle = "Your weekly meeting run-through — tick items off, reset each week."

    def build(self) -> None:
        self._ensure_items()
        self._build_toolbar()
        self.list_holder = ctk.CTkFrame(self.body, fg_color="transparent")
        self.list_holder.pack(fill="x")
        self.list_holder.grid_columnconfigure(0, weight=1)
        self._render()

    # -- storage ---------------------------------------------------------
    def _state_path(self):
        return os.path.join(config_dir(), "meeting_state.json")

    def _load_state(self):
        try:
            with open(self._state_path(), "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}

    def _save_state(self, state):
        with open(self._state_path(), "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)

    def _ensure_items(self):
        if not self.config.get("meeting_checklist_items"):
            self.config["meeting_checklist_items"] = list(DEFAULT_ITEMS)
            self.app.save_config()

    # -- ui --------------------------------------------------------------
    def _build_toolbar(self):
        card = self.card()
        card.grid_columnconfigure(0, weight=1)
        add = ctk.CTkFrame(card, fg_color="transparent")
        add.grid(row=0, column=0, sticky="ew")
        add.grid_columnconfigure(0, weight=1)
        self.new_item = ctk.CTkEntry(add, height=32, placeholder_text="Add a checklist item…")
        self.new_item.grid(row=0, column=0, sticky="ew")
        self.ghost_button(add, "Add", self.add_item, width=80).grid(row=0, column=1, padx=(8, 0))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.primary_button(row, "New week (reset ticks)", self.reset, width=200).pack(side="left")

    def _render(self):
        for child in self.list_holder.winfo_children():
            child.destroy()
        card = self.card("This week")
        card.grid_columnconfigure(0, weight=1)
        state = self._load_state()
        self._vars = {}
        items = self.config.get("meeting_checklist_items", [])
        for i, item in enumerate(items):
            var = ctk.StringVar(value="on" if state.get(item) else "off")
            rowf = ctk.CTkFrame(card, fg_color="transparent")
            rowf.grid(row=i, column=0, sticky="ew", pady=2)
            rowf.grid_columnconfigure(0, weight=1)
            ctk.CTkCheckBox(rowf, text=item, variable=var, onvalue="on", offvalue="off",
                            command=lambda it=item, v=var: self._toggle(it, v)).grid(row=0, column=0, sticky="w")
            ctk.CTkButton(rowf, text="✕", width=26, height=24, fg_color="transparent",
                          text_color=theme.DANGER, hover_color="#E4E8EE",
                          command=lambda it=item: self.remove_item(it)).grid(row=0, column=1, sticky="e")
            self._vars[item] = var

    # -- actions ---------------------------------------------------------
    def _toggle(self, item, var):
        state = self._load_state()
        state[item] = var.get() == "on"
        self._save_state(state)

    def add_item(self):
        text = self.new_item.get().strip()
        if not text:
            return
        items = self.config.setdefault("meeting_checklist_items", [])
        if text not in items:
            items.append(text)
            self.app.save_config()
        self.new_item.delete(0, "end")
        self._render()

    def remove_item(self, item):
        items = self.config.get("meeting_checklist_items", [])
        if item in items:
            items.remove(item)
            self.app.save_config()
        self._render()

    def reset(self):
        self._save_state({})
        self._render()
        self.app.set_status("Checklist reset for a new week.")
