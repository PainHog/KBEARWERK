"""Financials panel.

The money-at-a-glance dashboard she asked for:
  * Held job fund (income tied up in held invoices)
  * This month's billing — overall and per engineer
  * Running yearly total

Plus the monthly billing step: add an entry to the ledger and generate + draft the
invoice (draft-gated until she confirms it's right).
"""

from __future__ import annotations

import datetime
import os
from tkinter import ttk

import customtkinter as ctk

from .. import theme
from .base import BasePanel
from ..services import finances, reliable, templates, files, jobdata, people, outlook, activity, search


class FinancialsPanel(BasePanel):
    title = "Financials"
    subtitle = "Held fund, monthly billing (with per-engineer), and the yearly total."

    def build(self) -> None:
        self._build_kpis()
        self._build_per_engineer()
        self._build_invoice()
        self._refresh()

    # -- KPIs ------------------------------------------------------------
    def _build_kpis(self) -> None:
        card = self.card("Overview")
        card.grid_columnconfigure(0, weight=1)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure((0, 1, 2), weight=1)
        self._kpi = {}
        self._kpi["held"] = self._tile(top, 0, "Held job fund", theme.WARNING)
        self._kpi["month"] = self._tile(top, 1, "Billed this month", theme.ACCENT)
        self._kpi["year"] = self._tile(top, 2, "Billed this year", theme.PRIMARY)
        self.kpi_note = ctk.CTkLabel(card, text="", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w")
        self.kpi_note.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.ghost_button(card, "🔄 Refresh", self._refresh, width=110).grid(row=2, column=0, sticky="w", pady=(6, 0))

    def _tile(self, parent, col, label, color):
        box = ctk.CTkFrame(parent, fg_color=theme.SIDEBAR, corner_radius=10)
        box.grid(row=0, column=col, sticky="ew", padx=4)
        ctk.CTkLabel(box, text=label, font=theme.FONT_SMALL, text_color=theme.MUTED).pack(pady=(10, 0))
        val = ctk.CTkLabel(box, text="$0", font=("Segoe UI Semibold", 24), text_color=color)
        val.pack(pady=(0, 10))
        return val

    # -- per engineer ----------------------------------------------------
    def _build_per_engineer(self) -> None:
        card = self.card("By engineer")
        card.grid_columnconfigure(0, weight=1)
        holder = ctk.CTkFrame(card, fg_color="transparent", height=220)
        holder.grid(row=0, column=0, sticky="nsew")
        holder.grid_columnconfigure(0, weight=1)
        holder.grid_rowconfigure(0, weight=1)
        theme.style_treeview(ttk.Style(), "KBFin.Treeview")
        self.tree = ttk.Treeview(holder, show="headings", style="KBFin.Treeview",
                                 columns=["Engineer", "This month", "This year"], height=8)
        for col, w in [("Engineer", 220), ("This month", 140), ("This year", 140)]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="w")
        vsb = ttk.Scrollbar(holder, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

    # -- invoice a job ---------------------------------------------------
    def _build_invoice(self) -> None:
        card = self.collapsible_card("Bill a job → ledger + invoice",
                                     "Add an entry to the ledger and generate the invoice. Email is drafted for review.",
                                     collapsed=True)
        card.grid_columnconfigure((1, 3), weight=1)
        self.inv_fields = {}
        self._inv_field(card, 0, 0, "number", "Project #")
        self._inv_field(card, 0, 2, "invoice", "Invoice #")
        self._inv_field(card, 1, 0, "client", "Client")
        self._inv_field(card, 1, 2, "amount", "Amount $")
        ctk.CTkLabel(card, text="Engineer", font=theme.FONT_BODY).grid(row=2, column=0, sticky="w", padx=(0, 8), pady=5)
        self.eng_menu = ctk.CTkOptionMenu(card, values=self._engineer_values(), height=32)
        self.eng_menu.grid(row=2, column=1, sticky="ew", pady=5)
        self._inv_field(card, 2, 2, "date", "Date", datetime.date.today().strftime("%m/%d/%Y"))

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=3, column=0, columnspan=4, sticky="w", pady=(8, 0))
        self.primary_button(btns, "Add to ledger", self.add_to_ledger, width=150).pack(side="left")
        self.accent_button(btns, "Generate invoice", self.generate_invoice, width=170).pack(side="left", padx=8)
        self.ghost_button(btns, "Draft invoice email", self.draft_invoice_email, width=190).pack(side="left")
        self.inv_status = ctk.CTkLabel(card, text="", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w")
        self.inv_status.grid(row=4, column=0, columnspan=4, sticky="w", pady=(8, 0))

    def _inv_field(self, parent, r, c, key, label, default=""):
        ctk.CTkLabel(parent, text=label, font=theme.FONT_BODY).grid(row=r, column=c, sticky="w", padx=(0, 8), pady=5)
        e = ctk.CTkEntry(parent, height=32)
        if default:
            e.insert(0, default)
        e.grid(row=r, column=c + 1, sticky="ew", pady=5)
        self.inv_fields[key] = e
        return e

    def _engineer_values(self):
        return people.nicknames(self.config) or ["(add people in Settings)"]

    # -- data ------------------------------------------------------------
    def _refresh(self) -> None:
        def work():
            return finances.summarize(self.config)

        def done(s):
            self._kpi["held"].configure(text=f"${s.held_total:,.0f}")
            self._kpi["month"].configure(text=f"${s.month_total:,.0f}")
            self._kpi["year"].configure(text=f"${s.year_total:,.0f}")
            note = f"{s.month_label}. "
            if not self.config.get("paths", {}).get("invoice_ledger"):
                note = "Set the Invoice Ledger in Settings to see real figures. "
            elif s.undated_rows:
                note += f"({s.undated_rows} ledger row(s) had no readable date and weren't counted.)"
            self.kpi_note.configure(text=note)
            self.tree.delete(*self.tree.get_children())
            for eng in finances.engineers_sorted(s):
                self.tree.insert("", "end", values=[
                    eng,
                    f"${s.per_engineer_month.get(eng, 0):,.0f}",
                    f"${s.per_engineer_year.get(eng, 0):,.0f}",
                ])

        self.run_async(work, done, busy="Adding up the ledger…")

    # -- invoice actions -------------------------------------------------
    def _inv_values(self):
        v = {k: e.get().strip() for k, e in self.inv_fields.items()}
        v["engineer"] = self.eng_menu.get()
        return v

    def add_to_ledger(self):
        v = self._inv_values()
        path = self.config.get("paths", {}).get("invoice_ledger", "")
        if not path:
            self.show_error("Set the Invoice Ledger file in Settings first.")
            return
        row = {
            "Invoice": v["invoice"], "Invoice #": v["invoice"],
            "Project Number": v["number"], "Job Number": v["number"],
            "Client": v["client"], "Amount": v["amount"],
            "Engineer": v["engineer"], "Date": v["date"], "Invoice Date": v["date"],
            "Status": "Billed", "Notes": "",
        }

        def work():
            return reliable.excel_append(path, row, label="Invoice Ledger")

        def done(result):
            msg = "Added to ledger ✓" if result != "queued" else "Saved locally — will sync ⏳"
            self.inv_status.configure(text=msg, text_color=theme.SUCCESS)
            self._refresh()

        def on_error(exc):
            self.inv_status.configure(text=str(exc).splitlines()[0], text_color=theme.DANGER)
            self.show_error(str(exc))

        self.run_async(work, done, on_error=on_error, busy="Adding to ledger…")

    def _invoice_context(self, v):
        ctx = dict(jobdata.get(v["number"]))
        ctx.update({
            "invoice": v["invoice"], "invoice_number": v["invoice"],
            "project_number": v["number"], "job_number": v["number"],
            "client": v["client"], "client_name": v["client"],
            "amount": v["amount"], "engineer": v["engineer"],
            "date": v["date"],
        })
        return ctx

    def _invoice_dir(self, number):
        folder = files.find_project_folder(self.config.get("base_folder", ""), number, "")
        if not folder:
            return ""
        for sub in self.config.get("folder_template", []):
            low = sub.lower()
            if "billing" in low or "invoice" in low or "correspond" in low:
                p = os.path.join(folder, sub)
                if os.path.isdir(p):
                    return p
        return folder

    def generate_invoice(self):
        v = self._inv_values()
        tpl = self.config.get("invoice_template", "")
        if not tpl or not os.path.exists(tpl):
            self.show_error("Set the invoice template (.docx) in Settings → Websites & company.")
            return
        dest = self._invoice_dir(v["number"]) or self.pick_folder("Where should the invoice be saved?")
        if not dest:
            return
        filename = f"Invoice {v['invoice'] or v['number']}.docx"
        ctx = self._invoice_context(v)

        def work():
            tmp = reliable.local_temp(filename)
            templates.fill_template(tpl, ctx, tmp)
            return reliable.place_file(tmp, [dest], filename, label="Invoice")

        def done(result):
            written, queued = result
            where = "\n".join(written or queued)
            self.inv_status.configure(text=f"Invoice generated → {where}", text_color=theme.SUCCESS)
            activity.log(activity.DOCUMENT_GENERATED, project=v["number"], details=f"Invoice {v['invoice']}")

        self.run_async(work, done, busy="Generating invoice…")

    def draft_invoice_email(self):
        v = self._inv_values()
        to = jobdata.get(v["number"]).get("client_email", "")
        if not to:
            self.show_error("No client email saved for this job. Add it on the job (New Project) first, "
                            "or send the generated invoice manually.")
            return
        if not outlook.available():
            self.show_info("Email runs on her Windows PC with Outlook; it's inactive here.")
            return
        send = bool(self.config.get("invoices", {}).get("send_emails", False))

        def work():
            subject = f"Invoice {v['invoice']} — {v['client']}".strip()
            body = (f"Hello,\n\nPlease find attached invoice {v['invoice']} for project "
                    f"{v['number']} in the amount of {v['amount']}.\n\nThank you.")
            outlook.create_email(to=to, subject=subject, body=body, send=send)
            return send

        def done(was_sent):
            self.inv_status.configure(
                text=("Invoice email sent ✓" if was_sent else "Invoice email drafted in Outlook — review & send."),
                text_color=theme.SUCCESS)
            if was_sent:
                activity.log(activity.EMAIL_SENT, project=v["number"], details=f"Invoice {v['invoice']}")

        self.run_async(work, done, busy="Preparing invoice email…")

    def on_show(self):
        self.eng_menu.configure(values=self._engineer_values())
        self._refresh()
