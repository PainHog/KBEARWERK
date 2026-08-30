"""Needed panel - what's still missing for a job.

Enter a project number; the app finds its folder, scans for the required
documents, shows what's present vs. missing, lets her tick off the manual info
items (remembered per job), and prints a clean "outstanding items" sheet for the
weekly meeting or to hand to an employee.
"""

from __future__ import annotations

import os

import customtkinter as ctk

from .. import theme
from .base import BasePanel
from ..services import files, checklist


class NeededPanel(BasePanel):
    title = "Needed"
    subtitle = "Track and print the documents & info still missing for a job."

    def build(self) -> None:
        self._needs = None
        self._project_folder = ""
        self._project_name = ""
        self._build_pick()
        self.results_holder = ctk.CTkFrame(self.body, fg_color="transparent")
        self.results_holder.pack(fill="x")
        self.results_holder.grid_columnconfigure(0, weight=1)

    def _build_pick(self) -> None:
        card = self.card("Which job?")
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Project #", font=theme.FONT_BODY).grid(row=0, column=0, padx=(0, 8))
        self.number_entry = ctk.CTkEntry(card, height=32, placeholder_text="e.g. 2025-104")
        self.number_entry.grid(row=0, column=1, sticky="ew")
        self.number_entry.bind("<Return>", lambda _e: self.scan())
        self.primary_button(card, "Scan job", self.scan, width=120).grid(row=0, column=2, padx=(10, 0))
        self.folder_label = ctk.CTkLabel(card, text="", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w")
        self.folder_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))

    def scan(self) -> None:
        number = self.number_entry.get().strip()
        if not number:
            self.show_error("Enter a project number first.")
            return
        base = self.config.get("base_folder", "")
        folder = files.find_project_folder(base, number, "")
        self._project_folder = folder or ""
        if folder:
            self.folder_label.configure(text=f"Folder: {folder}", text_color=theme.SUCCESS)
        else:
            self.folder_label.configure(text="No folder found — checking info items only.", text_color=theme.WARNING)

        def work():
            return checklist.scan_job(
                number, folder or "",
                self.config.get("required_documents", []),
                self.config.get("required_info", []),
            )

        self.run_async(work, self._render, busy=f"Scanning job {number}…")

    def _render(self, needs) -> None:
        self._needs = needs
        for child in self.results_holder.winfo_children():
            child.destroy()

        # Summary line.
        summary = self.card()
        summary.grid_columnconfigure(0, weight=1)
        n_missing = len(needs.missing_documents) + len(needs.missing_info)
        if needs.all_complete:
            text, color = "Everything is present and confirmed. ✓", theme.SUCCESS
        else:
            text, color = f"{n_missing} item(s) still needed.", theme.DANGER
        ctk.CTkLabel(summary, text=text, font=theme.FONT_CARD_TITLE, text_color=color, anchor="w").grid(
            row=0, column=0, sticky="w")
        self.primary_button(summary, "🖨  Print missing-items sheet", self.print_sheet, width=240).grid(
            row=0, column=1, sticky="e")

        # Documents.
        docs = self.card("Required documents (from folder scan)")
        docs.grid_columnconfigure(0, weight=1)
        for i, d in enumerate(needs.documents):
            mark = "✓" if d.present else "✗"
            color = theme.SUCCESS if d.present else theme.DANGER
            text = f"{mark}  {d.label}"
            if d.present and d.found:
                text += f"   ({d.found})"
            ctk.CTkLabel(docs, text=text, font=theme.FONT_BODY, text_color=color, anchor="w").grid(
                row=i, column=0, sticky="w", pady=2)

        # Info check-offs.
        info = self.card("Required information (tick when confirmed — remembered per job)")
        info.grid_columnconfigure(0, weight=1)
        self._info_vars = {}
        for i, item in enumerate(needs.info):
            var = ctk.StringVar(value="on" if item["confirmed"] else "off")
            chk = ctk.CTkCheckBox(
                info, text=item["label"], variable=var, onvalue="on", offvalue="off",
                command=lambda lbl=item["label"], v=var: self._toggle_info(lbl, v),
            )
            chk.grid(row=i, column=0, sticky="w", pady=3)
            self._info_vars[item["label"]] = var

    def _toggle_info(self, label, var) -> None:
        number = self.number_entry.get().strip()
        checklist.set_info_state(number, label, var.get() == "on")
        # Update the cached needs so the printed sheet reflects the toggle.
        if self._needs:
            for item in self._needs.info:
                if item["label"] == label:
                    item["confirmed"] = var.get() == "on"

    def print_sheet(self) -> None:
        if not self._needs:
            return
        number = self._needs.project_number

        def work():
            base_dir = self._project_folder or self.config.get("base_folder", "") or "."
            dest = os.path.join(base_dir, f"Outstanding Items - {number}.docx")
            company = self.config.get("company", {}).get("name", "")
            path = checklist.generate_missing_sheet(dest, self._needs, self._project_name, company)
            return path

        def done(path):
            self.app.set_status(f"Saved outstanding-items sheet: {path}")
            try:
                files.open_in_file_manager(os.path.dirname(path))
            except Exception:
                pass
            self.show_info(f"Saved:\n{path}\n\nOpen it and print for the meeting.", title="Sheet ready")

        self.run_async(work, done, busy="Building the sheet…")
