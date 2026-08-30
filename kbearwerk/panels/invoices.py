"""Held Invoices panel.

Load the invoice ledger, show everything currently HELD so nothing slips, print a
report on demand, and draft one reminder email per engineer (nickname read from
the ledger notes → address via contacts).

Emails are DRAFTED for review, never auto-sent, until she confirms it's correct
and turns on sending in Settings.
"""

from __future__ import annotations

import os
from tkinter import ttk

import customtkinter as ctk

from .. import theme
from .base import BasePanel
from ..services import invoices, outlook, people, reliable, files, activity


class InvoicesPanel(BasePanel):
    title = "Held Invoices"
    subtitle = "See every invoice on hold, print the list, and draft reminders."

    COLUMNS = ["Invoice", "Client", "Amount", "Engineer", "Notes"]

    def build(self) -> None:
        self._held = []
        self._build_controls()
        self._build_table()

    def _build_controls(self) -> None:
        card = self.card()
        card.grid_columnconfigure(0, weight=1)
        self.primary_button(card, "🔄  Load held invoices", self.load, width=200).grid(row=0, column=0, sticky="w")
        self.count_label = ctk.CTkLabel(card, text="", font=theme.FONT_BODY, text_color=theme.MUTED, anchor="w")
        self.count_label.grid(row=1, column=0, sticky="w", pady=(8, 0))
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.ghost_button(actions, "🖨  Print held list", self.print_report, width=170).pack(side="left", padx=(0, 8))
        self.accent_button(actions, "✉  Draft reminder emails", self.draft_emails, width=220).pack(side="left")
        self.note_label = ctk.CTkLabel(card, text="", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w")
        self.note_label.grid(row=3, column=0, sticky="w", pady=(6, 0))

    def _build_table(self) -> None:
        card = self.card()
        card.grid_columnconfigure(0, weight=1)
        holder = ctk.CTkFrame(card, fg_color="transparent", height=360)
        holder.grid(row=0, column=0, sticky="nsew")
        holder.grid_columnconfigure(0, weight=1)
        holder.grid_rowconfigure(0, weight=1)
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("KBInv.Treeview", rowheight=26, font=("Segoe UI", 11))
        style.configure("KBInv.Treeview.Heading", font=("Segoe UI Semibold", 11))
        self.tree = ttk.Treeview(holder, show="headings", style="KBInv.Treeview",
                                 columns=self.COLUMNS, height=14)
        for col in self.COLUMNS:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=200 if col == "Notes" else 130, anchor="w")
        vsb = ttk.Scrollbar(holder, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

    # -- actions ---------------------------------------------------------
    def load(self) -> None:
        if not self.config.get("paths", {}).get("invoice_ledger"):
            self.show_error("Set the Invoice Ledger file in Settings → File locations first.")
            return

        def work():
            return invoices.load_held(self.config)

        def done(held):
            self._held = held
            self.tree.delete(*self.tree.get_children())
            for h in held:
                self.tree.insert("", "end", values=[h.invoice, h.client, h.amount, h.engineer, h.notes])
            self.count_label.configure(
                text=(f"{len(held)} invoice(s) on hold." if held else "No held invoices found. ✓"))

        self.run_async(work, done, busy="Loading held invoices…")

    def print_report(self) -> None:
        if not self._held:
            self.show_info("Load the held invoices first.")
            return

        def work():
            fname = "Held Invoices.docx"
            tmp = reliable.local_temp(fname)
            invoices.generate_report(tmp, self._held, self.config.get("company", {}).get("name", ""))
            dest_dir = self.config.get("base_folder") or os.path.dirname(tmp)
            written, queued = reliable.place_file(tmp, [dest_dir], fname, label="Held Invoices")
            return (written or [tmp])[0]

        def done(path):
            try:
                files.open_in_file_manager(os.path.dirname(path))
            except Exception:
                pass
            self.show_info(f"Saved:\n{path}\n\nOpen it and print.", title="Held-invoices report")

        self.run_async(work, done, busy="Building held-invoices report…")

    def draft_emails(self) -> None:
        if not self._held:
            self.show_info("Load the held invoices first.")
            return
        if not outlook.available():
            self.show_info("Email runs on her Windows PC with Outlook; it's inactive here, "
                           "but the button will draft the emails there.")
            return
        send = bool(self.config.get("invoices", {}).get("send_emails", False))
        if send and not self.ask_yes_no("Sending is ON — really SEND these reminder emails now?"):
            return

        groups = invoices.group_by_engineer(self._held)

        def work():
            drafted, skipped = [], []
            for engineer, items in groups.items():
                to = people.resolve_email(self.config, engineer)
                if not to:
                    skipped.append(engineer)
                    continue
                lines = [f"- Invoice {h.invoice}  {h.client}  {h.amount}  ({h.notes})" for h in items]
                body = (f"Hi {engineer},\n\nThe following invoice(s) are currently on hold. "
                        f"Please let me know if we can release them:\n\n" + "\n".join(lines) +
                        "\n\nThanks!")
                subject = f"Held invoices — {len(items)} on hold"
                outlook.create_email(to=to, subject=subject, body=body, send=send)
                drafted.append(engineer)
            return drafted, skipped, send

        def done(result):
            drafted, skipped, was_sent = result
            verb = "Sent" if was_sent else "Drafted"
            if was_sent:
                for e in drafted:
                    activity.log(activity.EMAIL_SENT, details=f"Held-invoice reminder to {e}")
            msg = f"{verb} {len(drafted)} reminder email(s)."
            if skipped:
                msg += f"  No email on file for: {', '.join(skipped)} (add them in Settings → People)."
            self.note_label.configure(text=msg, text_color=theme.SUCCESS)
            self.app.set_status(msg)

        self.run_async(work, done, busy="Preparing reminder emails…")

    def on_show(self) -> None:
        send = bool(self.config.get("invoices", {}).get("send_emails", False))
        self.note_label.configure(
            text=("Sending is ON — emails will send when you click Draft reminders."
                  if send else "Emails are drafted for review (sending is off during testing)."),
            text_color=(theme.DANGER if send else theme.MUTED))
