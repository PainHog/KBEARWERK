"""New Project panel - the flagship "enter once, it goes everywhere" workflow.

She fills the form **one time**. Then:
  * "Do all automatic steps" creates the folder, updates the Proposal List,
    Weekly Worksheet and Project List, and generates the Project Information
    Sheet - all from that single set of inputs.
  * The manual steps (physical folder, Monograph, OCE website) get a helping
    hand: one click opens the site and copies the project info to the clipboard
    so she just pastes.

Every column/header name and the exact sheet layout are first drafts - once we
have her real files we point the app at them in Settings and adjust the field
mapping here.
"""

from __future__ import annotations

import datetime
import os
import re
import webbrowser

import customtkinter as ctk

from .. import theme
from .base import BasePanel
from ..services import files, excel, docgen, billing, reliable, jobdata, extract, activity


# (key, label). Laid out two-per-row. "notes" is handled specially (full width).
FORM_FIELDS = [
    ("number", "Project Number"),
    ("name", "Project Name"),
    ("client", "Client"),
    ("contractor", "Contractor"),
    ("client_contact", "Client Contact"),
    ("client_phone", "Client Phone"),
    ("client_email", "Client Email"),
    ("address", "Project Address"),
    ("project_type", "Project Type"),
    ("engineer", "Engineer / PM"),
    ("proposal_date", "Proposal Date"),
    ("fee", "Fee / Contract $"),
]


class NewProjectPanel(BasePanel):
    title = "New Project"
    subtitle = "Enter the project once — the app files it everywhere it needs to go."

    def build(self) -> None:
        self.fields = {}
        self.status_labels = {}
        self._build_import()
        self._build_form()
        self._build_automatic()
        self._build_manual()
        self._build_footer()

    # -- import from a document -----------------------------------------
    def _build_import(self) -> None:
        card = self.card(
            "Start from a document (optional)",
            "Drag a proposal (PDF or Word) onto the box — or click it — and the app "
            "fills in what it can. Nothing is required; you can always type it yourself.",
        )
        card.grid_columnconfigure(0, weight=1)
        self.drop_zone = ctk.CTkFrame(card, fg_color=theme.SIDEBAR, corner_radius=10, height=66)
        self.drop_zone.grid(row=0, column=0, sticky="ew")
        self.drop_zone.grid_propagate(False)
        self.drop_label = ctk.CTkLabel(
            self.drop_zone, text="⬇   Drag a proposal here, or click to choose a file",
            font=theme.FONT_BODY, text_color=theme.MUTED,
        )
        self.drop_label.place(relx=0.5, rely=0.5, anchor="center")
        for w in (self.drop_zone, self.drop_label):
            w.bind("<Button-1>", lambda _e: self.import_dialog())
        # Real OS drag-and-drop when it's available (see app.register_drop).
        self.app.register_drop(self.drop_zone, self.import_document)
        self.app.register_drop(self.drop_label, self.import_document)

    def import_dialog(self) -> None:
        path = self.pick_file("Choose a proposal or document to import",
                              [("Documents", "*.pdf *.docx *.txt"), ("All files", "*.*")])
        if path:
            self.import_document(path)

    def import_document(self, path) -> None:
        def work():
            return extract.extract_from_file(path)

        def done(fields):
            self._apply_extracted(fields)

        self.run_async(work, done, busy=f"Reading {os.path.basename(path)}…")

    def _apply_extracted(self, fields) -> None:
        count = 0
        for key, val in fields.items():
            widget = self.fields.get(key)
            if widget is None or isinstance(widget, ctk.CTkTextbox):
                continue
            if not widget.get().strip():
                widget.insert(0, val)
                count += 1
        if count:
            self.app.set_status(f"Imported {count} field(s) from the document — please review them.")
            self.drop_label.configure(text=f"✓ Imported {count} field(s) — review below", text_color=theme.SUCCESS)
        else:
            self.show_info(
                "I couldn't confidently pull fields from that document. It may be a "
                "scanned image (which needs OCR) or an unusual layout — you can still "
                "type the details in. Once you share a real proposal I can tune this.",
                title="Nothing auto-filled",
            )

    # -- form ------------------------------------------------------------
    def _build_form(self) -> None:
        form = self.card("Project details", "Fill this in once. Everything below uses it.")
        for col in (1, 3):
            form.grid_columnconfigure(col, weight=1)

        for i, (key, label) in enumerate(FORM_FIELDS):
            r, c = divmod(i, 2)
            base_col = c * 2
            ctk.CTkLabel(form, text=label, font=theme.FONT_BODY, anchor="w").grid(
                row=r, column=base_col, sticky="w", padx=(0, 8), pady=6
            )
            entry = ctk.CTkEntry(form, height=32)
            entry.grid(row=r, column=base_col + 1, sticky="ew", padx=(0, 18), pady=6)
            self.fields[key] = entry

        # Drafter as a dropdown pulled from Settings.
        next_row = (len(FORM_FIELDS) + 1) // 2
        ctk.CTkLabel(form, text="Drafter", font=theme.FONT_BODY, anchor="w").grid(
            row=next_row, column=0, sticky="w", padx=(0, 8), pady=6
        )
        self.drafter_menu = ctk.CTkOptionMenu(form, values=self._drafter_values(), height=32)
        self.drafter_menu.grid(row=next_row, column=1, sticky="ew", padx=(0, 18), pady=6)

        ctk.CTkLabel(form, text="Date Opened", font=theme.FONT_BODY, anchor="w").grid(
            row=next_row, column=2, sticky="w", padx=(0, 8), pady=6
        )
        date_entry = ctk.CTkEntry(form, height=32)
        date_entry.insert(0, datetime.date.today().strftime("%m/%d/%Y"))
        date_entry.grid(row=next_row, column=3, sticky="ew", padx=(0, 18), pady=6)
        self.fields["date_opened"] = date_entry

        ctk.CTkLabel(form, text="Notes", font=theme.FONT_BODY, anchor="nw").grid(
            row=next_row + 1, column=0, sticky="nw", padx=(0, 8), pady=6
        )
        notes = ctk.CTkTextbox(form, height=60)
        notes.grid(row=next_row + 1, column=1, columnspan=3, sticky="ew", padx=(0, 18), pady=6)
        self.fields["notes"] = notes

    def _drafter_values(self):
        names = [d.get("name", "") for d in self.config.get("drafters", []) if d.get("name")]
        return names or ["(add drafters in Settings)"]

    # -- automatic steps -------------------------------------------------
    def _build_automatic(self) -> None:
        card = self.card(
            "Automatic — the app does these for you",
            "One click runs every step below from the details above.",
        )
        self.primary_button(card, "▶  Do all automatic steps", self.do_all).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )
        card.grid_columnconfigure(1, weight=1)

        self._step_row(card, 1, "folder", "1. Create digital project folder", "Create folder", self.do_create_folder)
        self._step_row(card, 2, "proposal", "2. Add to Proposal List (mark Accepted)", "Update", self.do_proposal_list)
        self._step_row(card, 3, "weekly", "3. Update Weekly Worksheet", "Update", self.do_weekly_worksheet)
        self._step_row(card, 4, "project", "4. Add to Project List", "Update", self.do_project_list)
        self._step_row(card, 5, "info", "5. Create Project Information Sheet", "Generate", self.do_info_sheet)

    def _step_row(self, parent, row, key, text, btn_text, command) -> None:
        ctk.CTkLabel(parent, text=text, font=theme.FONT_BODY, anchor="w").grid(
            row=row, column=0, sticky="w", pady=4
        )
        status = ctk.CTkLabel(parent, text="", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w")
        status.grid(row=row, column=1, sticky="w", padx=12, pady=4)
        self.status_labels[key] = status
        self.accent_button(parent, btn_text, command, width=110).grid(
            row=row, column=2, sticky="e", pady=4
        )

    # -- manual steps ----------------------------------------------------
    def _build_manual(self) -> None:
        card = self.card(
            "Manual — with a helping hand",
            "The app can't do these for you, but it opens the site and copies the "
            "project info so you just paste.",
        )
        card.grid_columnconfigure(1, weight=1)
        self._manual_row(card, 0, "Create the physical (paper) folder", "Copy info", self.copy_info)
        self._manual_row(card, 1, "Add to Monograph", "Open Monograph", self.open_monograph)
        self._manual_row(card, 2, "Add to OCE print-tracking website", "Open OCE", self.open_oce)

    def _manual_row(self, parent, row, text, btn_text, command) -> None:
        chk = ctk.CTkCheckBox(parent, text=text, font=theme.FONT_BODY)
        chk.grid(row=row, column=0, sticky="w", pady=6)
        self.ghost_button(parent, btn_text, command, width=150).grid(row=row, column=2, sticky="e", pady=6)

    def _build_footer(self) -> None:
        card = self.card()
        card.grid_columnconfigure(0, weight=1)
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew")
        self.ghost_button(row, "Copy all project info", self.copy_info, width=180).pack(side="left")
        self.ghost_button(row, "Start a new project (clear)", self.clear_form, width=200).pack(side="left", padx=10)

    # -- data ------------------------------------------------------------
    def get_info(self) -> dict:
        info = {}
        for key, widget in self.fields.items():
            if isinstance(widget, ctk.CTkTextbox):
                info[key] = widget.get("1.0", "end").strip()
            else:
                info[key] = widget.get().strip()
        drafter = self.drafter_menu.get()
        info["drafter"] = "" if drafter.startswith("(") else drafter
        return info

    def _require_min(self, info) -> bool:
        if not info.get("number") and not info.get("name"):
            self.show_error("Please enter at least a Project Number or Project Name first.")
            return False
        return True

    def _fee_amount(self, info) -> float:
        raw = re.sub(r"[^0-9.]", "", info.get("fee", "") or "")
        try:
            return float(raw) if raw else 0.0
        except ValueError:
            return 0.0

    def _excel_values(self, info, accepted=False) -> dict:
        vals = {
            "Project Number": info["number"], "Project No": info["number"], "Job Number": info["number"], "Job #": info["number"],
            "Project Name": info["name"], "Project": info["name"], "Job Name": info["name"], "Name": info["name"],
            "Client": info["client"], "Client Name": info["client"], "Owner": info["client"],
            "Contractor": info["contractor"], "General Contractor": info["contractor"],
            "Address": info["address"], "Project Address": info["address"], "Location": info["address"],
            "Engineer": info["engineer"], "PM": info["engineer"], "Engineer / PM": info["engineer"],
            "Drafter": info["drafter"],
            "Project Type": info["project_type"], "Type": info["project_type"],
            "Date": info["date_opened"], "Date Opened": info["date_opened"],
            "Proposal Date": info["proposal_date"],
            "Fee": info["fee"], "Contract Amount": info["fee"], "Contract": info["fee"],
            "Notes": info["notes"],
        }
        if accepted:
            vals["Status"] = "Accepted"
            vals["Accepted"] = "Yes"
        return vals

    def _project_folder_path(self) -> str:
        info = self.get_info()
        base = self.config.get("base_folder", "")
        name = files.format_folder_name(
            self.config.get("project_folder_pattern", "{number} - {name}"),
            number=info["number"], name=info["name"], client=info["client"],
        )
        return files.create_project_folder(base, name, self.config.get("folder_template", [])).path

    def _set_step(self, key, text, ok=True) -> None:
        lbl = self.status_labels.get(key)
        if lbl:
            lbl.configure(text=text, text_color=(theme.SUCCESS if ok else theme.DANGER))

    # -- automatic actions ----------------------------------------------
    def do_create_folder(self) -> None:
        info = self.get_info()
        if not self._require_min(info):
            return

        def work():
            base = self.config.get("base_folder", "")
            name = files.format_folder_name(
                self.config.get("project_folder_pattern", "{number} - {name}"),
                number=info["number"], name=info["name"], client=info["client"],
            )
            return files.create_project_folder(base, name, self.config.get("folder_template", []))

        def done(res):
            msg = "Created ✓" if res.created else "Already existed ✓"
            self._set_step("folder", f"{msg}  ({res.path})")
            self.app.set_status(f"Project folder ready: {res.path}")
            if res.created:
                activity.log(activity.JOB_CREATED, project=info.get("number") or info.get("name"),
                             details=info.get("name", ""))

        self.run_async(work, done, busy="Creating project folder…")

    def do_proposal_list(self) -> None:
        self._excel_step("proposal", "proposal_list", "Proposal List", accepted=True)

    def do_weekly_worksheet(self) -> None:
        self._excel_step("weekly", "weekly_worksheet", "Weekly Worksheet")

    def do_project_list(self) -> None:
        self._excel_step("project", "project_list", "Project List")

    def _excel_step(self, step_key, path_key, label, accepted=False) -> None:
        info = self.get_info()
        if not self._require_min(info):
            return
        path = self.config.get("paths", {}).get(path_key, "")
        if not path:
            self.show_error(f"Set the {label} file in Settings first (Settings → File locations).")
            return
        # Remember everything she entered so it carries over to future sheets.
        jobdata.update(info.get("number") or info.get("name"), info)

        def work():
            return reliable.excel_append(
                path, self._excel_values(info, accepted=accepted),
                unique_key="Project Number", label=label,
            )

        def done(result):
            if result == "queued":
                self._set_step(step_key, "Saved locally — will sync when cloud is back ⏳")
                self.app.set_status(f"{label}: cloud unreachable; saved locally, will sync.")
            else:
                verb = "Updated" if result == "updated" else "Added"
                self._set_step(step_key, f"{verb} ✓")
                self.app.set_status(f"{label}: {verb.lower()} {info.get('number') or info.get('name')}.")

        def on_error(exc):
            self._set_step(step_key, "Couldn't save (see message)", ok=False)
            self.show_error(str(exc))

        self.run_async(work, done, on_error=on_error, busy=f"Updating {label}…")

    def do_info_sheet(self) -> None:
        info = self.get_info()
        if not self._require_min(info):
            return

        jobdata.update(info.get("number") or info.get("name"), info)

        def work():
            import os
            folder = self._project_folder_path()
            info_sub = None
            for sub in self.config.get("folder_template", []):
                if "information" in sub.lower():
                    info_sub = sub
                    break
            dest_dir = os.path.join(folder, info_sub) if info_sub else folder
            company = self.config.get("company", {}).get("name", "")
            # Generate locally first, then place it (survives a cloud desync).
            tmp = reliable.local_temp("Project Information Sheet.docx")
            docgen.generate_project_info_sheet(tmp, info, company_name=company)
            return reliable.place_file(tmp, [dest_dir], "Project Information Sheet.docx",
                                       label="Project Information Sheet")

        def done(result):
            written, queued = result
            if queued and not written:
                self._set_step("info", "Saved locally — will sync ⏳")
            else:
                self._set_step("info", "Created ✓")
            self.app.set_status("Project Information Sheet ready.")

        self.run_async(work, done, busy="Generating Project Information Sheet…")

    def do_all(self) -> None:
        info = self.get_info()
        if not self._require_min(info):
            return
        # Record the contract amount for the Billing panel, if a fee was entered.
        fee = self._fee_amount(info)
        if fee:
            billing.set_contract(info["number"] or info["name"], fee, info["name"])
        # Run each automatic step. Steps that need a file report their own error.
        self.do_create_folder()
        if self.config.get("paths", {}).get("proposal_list"):
            self.do_proposal_list()
        if self.config.get("paths", {}).get("weekly_worksheet"):
            self.do_weekly_worksheet()
        if self.config.get("paths", {}).get("project_list"):
            self.do_project_list()
        self.do_info_sheet()
        self.app.set_status("Running all automatic steps…")

    # -- manual actions --------------------------------------------------
    def copy_info(self) -> None:
        info = self.get_info()
        lines = [
            f"Project Number: {info['number']}",
            f"Project Name:   {info['name']}",
            f"Client:         {info['client']}",
            f"Contractor:     {info['contractor']}",
            f"Address:        {info['address']}",
            f"Project Type:   {info['project_type']}",
            f"Engineer / PM:  {info['engineer']}",
            f"Drafter:        {info['drafter']}",
            f"Proposal Date:  {info['proposal_date']}",
            f"Fee:            {info['fee']}",
        ]
        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))
        self.app.set_status("Project info copied — paste it into Monograph / OCE.")

    def open_monograph(self) -> None:
        self.copy_info()
        webbrowser.open(self.config.get("monograph_url") or "https://app.monograph.com/")

    def open_oce(self) -> None:
        url = self.config.get("oce_url", "")
        if not url:
            self.show_error("Set the OCE website address in Settings first.")
            return
        self.copy_info()
        webbrowser.open(url)

    def clear_form(self) -> None:
        for key, widget in self.fields.items():
            if isinstance(widget, ctk.CTkTextbox):
                widget.delete("1.0", "end")
            else:
                widget.delete(0, "end")
        self.fields["date_opened"].insert(0, datetime.date.today().strftime("%m/%d/%Y"))
        for lbl in self.status_labels.values():
            lbl.configure(text="")
        self.app.set_status("Cleared — ready for a new project.")

    def on_show(self) -> None:
        # Keep the drafter dropdown in sync with Settings.
        current = self.drafter_menu.get()
        values = self._drafter_values()
        self.drafter_menu.configure(values=values)
        if current not in values:
            self.drafter_menu.set(values[0])
