"""Billing panel.

Tracks, per project, the agreed **contract amount** against everything billed so
far (in hours/portions) and shows what's **remaining**. For now this uses a local
ledger so it works immediately; we'll wire it to her real billing spreadsheets
next.
"""

from __future__ import annotations

import datetime

import customtkinter as ctk

from .. import theme
from .base import BasePanel
from ..services import billing


class BillingPanel(BasePanel):
    title = "Billing"
    subtitle = "See how much of each contract is billed and what's left."

    def build(self) -> None:
        self._project = ""
        self._build_pick()
        self.detail_holder = ctk.CTkFrame(self.body, fg_color="transparent")
        self.detail_holder.pack(fill="x")
        self.detail_holder.grid_columnconfigure(0, weight=1)

    def _build_pick(self) -> None:
        card = self.card("Choose a project")
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Project #", font=theme.FONT_BODY).grid(row=0, column=0, padx=(0, 8))
        self.project_menu = ctk.CTkComboBox(card, values=self._project_values(), height=32)
        self.project_menu.grid(row=0, column=1, sticky="ew")
        self.primary_button(card, "Open", self.load, width=100).grid(row=0, column=2, padx=(10, 0))

    def _project_values(self):
        return billing.list_projects() or [""]

    def load(self) -> None:
        self._project = self.project_menu.get().strip()
        if not self._project:
            self.show_error("Enter or pick a project number.")
            return
        self._render()

    def _render(self) -> None:
        for child in self.detail_holder.winfo_children():
            child.destroy()
        rec = billing.get_project(self._project)
        summ = billing.summarize(self._project)

        # Contract + summary.
        card = self.card(f"Project {self._project}")
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Contract $", font=theme.FONT_BODY).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.contract_entry = ctk.CTkEntry(card, width=160, height=32)
        self.contract_entry.insert(0, f"{summ.contract_amount:.2f}")
        self.contract_entry.grid(row=0, column=1, sticky="w")
        self.ghost_button(card, "Set contract", self.set_contract, width=130).grid(row=0, column=2, sticky="w")

        stats = ctk.CTkFrame(card, fg_color="transparent")
        stats.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        self._stat(stats, 0, "Contract", f"${summ.contract_amount:,.2f}", theme.PRIMARY)
        self._stat(stats, 1, "Billed", f"${summ.billed:,.2f}", theme.ACCENT)
        rem_color = theme.SUCCESS if summ.remaining >= 0 else theme.DANGER
        self._stat(stats, 2, "Remaining", f"${summ.remaining:,.2f}", rem_color)
        self._stat(stats, 3, "% Billed", f"{summ.percent_billed:.0f}%", theme.MUTED)

        bar = ctk.CTkProgressBar(card, height=14)
        bar.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        bar.set(min(max(summ.percent_billed / 100.0, 0.0), 1.0))

        # Existing entries.
        entries = self.card("Billing entries")
        entries.grid_columnconfigure(0, weight=1)
        rows = rec.get("entries", [])
        if not rows:
            ctk.CTkLabel(entries, text="No billing entries yet.", text_color=theme.MUTED,
                         font=theme.FONT_SMALL, anchor="w").grid(row=0, column=0, sticky="w")
        for i, e in enumerate(rows):
            line = ctk.CTkFrame(entries, fg_color=theme.SIDEBAR, corner_radius=6)
            line.grid(row=i, column=0, sticky="ew", pady=2)
            line.grid_columnconfigure(0, weight=1)
            txt = f"{e.get('date','')}  ·  {e.get('description','')}  ·  {e.get('hours','')} hrs"
            ctk.CTkLabel(line, text=txt, font=theme.FONT_SMALL, anchor="w").grid(row=0, column=0, sticky="w", padx=10, pady=6)
            ctk.CTkLabel(line, text=f"${float(e.get('amount',0)):,.2f}", font=theme.FONT_BODY, anchor="e").grid(
                row=0, column=1, sticky="e", padx=8)
            ctk.CTkButton(line, text="✕", width=26, height=24, fg_color="transparent",
                          text_color=theme.DANGER, hover_color="#E4E8EE",
                          command=lambda idx=i: self._remove(idx)).grid(row=0, column=2, padx=6)

        # Add entry.
        add = self.card("Add a billing entry")
        add.grid_columnconfigure((1, 3), weight=1)
        self.e_date = self._add_field(add, 0, 0, "Date", datetime.date.today().strftime("%m/%d/%Y"))
        self.e_amount = self._add_field(add, 0, 2, "Amount $", "")
        self.e_hours = self._add_field(add, 1, 0, "Hours", "")
        self.e_invoice = self._add_field(add, 1, 2, "Invoice #", "")
        ctk.CTkLabel(add, text="Description", font=theme.FONT_BODY).grid(row=2, column=0, sticky="w", padx=(0, 8), pady=6)
        self.e_desc = ctk.CTkEntry(add, height=32)
        self.e_desc.grid(row=2, column=1, columnspan=3, sticky="ew", pady=6)
        self.primary_button(add, "Add entry", self.add_entry, width=130).grid(row=3, column=0, sticky="w", pady=(8, 0))

    def _stat(self, parent, col, label, value, color) -> None:
        box = ctk.CTkFrame(parent, fg_color=theme.SIDEBAR, corner_radius=8)
        box.grid(row=0, column=col, sticky="ew", padx=4)
        parent.grid_columnconfigure(col, weight=1)
        ctk.CTkLabel(box, text=label, font=theme.FONT_SMALL, text_color=theme.MUTED).pack(pady=(8, 0))
        ctk.CTkLabel(box, text=value, font=("Segoe UI Semibold", 18), text_color=color).pack(pady=(0, 8))

    def _add_field(self, parent, r, c, label, default):
        ctk.CTkLabel(parent, text=label, font=theme.FONT_BODY).grid(row=r, column=c, sticky="w", padx=(0, 8), pady=6)
        e = ctk.CTkEntry(parent, height=32)
        if default:
            e.insert(0, default)
        e.grid(row=r, column=c + 1, sticky="ew", pady=6)
        return e

    # -- actions ---------------------------------------------------------
    def set_contract(self) -> None:
        try:
            amount = float(self.contract_entry.get().replace(",", "").replace("$", "") or 0)
        except ValueError:
            self.show_error("Contract must be a number.")
            return
        billing.set_contract(self._project, amount)
        self.app.set_status("Contract amount saved.")
        self._render()

    def add_entry(self) -> None:
        try:
            amount = float(self.e_amount.get().replace(",", "").replace("$", "") or 0)
            hours = float(self.e_hours.get() or 0)
        except ValueError:
            self.show_error("Amount and Hours must be numbers.")
            return
        billing.add_entry(self._project, {
            "date": self.e_date.get().strip(),
            "description": self.e_desc.get().strip(),
            "hours": hours,
            "amount": amount,
            "invoice": self.e_invoice.get().strip(),
        })
        self.app.set_status("Billing entry added.")
        self._render()

    def _remove(self, idx) -> None:
        billing.remove_entry(self._project, idx)
        self._render()

    def on_show(self) -> None:
        self.project_menu.configure(values=self._project_values())
