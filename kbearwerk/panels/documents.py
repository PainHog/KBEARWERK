"""Documents panel - fill in a blank template once and save it everywhere.

Replaces the "find blank form → duplicate → fill → save to several folders"
chore. Pick a registered template, the app auto-builds a form from its fill-in
tags, she fills it, and Generate saves filled copies to all chosen locations.
"""

from __future__ import annotations

import datetime
import os

import customtkinter as ctk

from .. import theme
from .base import BasePanel
from ..services import templates, files, reliable, jobdata, activity, convert


class DocumentsPanel(BasePanel):
    title = "Documents"
    subtitle = "Fill in a blank form once — the app makes the copies and files them."

    def build(self) -> None:
        self.field_widgets = {}
        self._selected = None
        self._build_picker()
        self.form_card_holder = ctk.CTkFrame(self.body, fg_color="transparent")
        self.form_card_holder.pack(fill="x")
        self.form_card_holder.grid_columnconfigure(0, weight=1)

    # -- template picker -------------------------------------------------
    def _build_picker(self) -> None:
        card = self.card("1. Choose a template")
        card.grid_columnconfigure(0, weight=1)
        self.template_menu = ctk.CTkOptionMenu(
            card, values=self._template_names(), command=self._on_template_change, height=34
        )
        self.template_menu.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        btnrow = ctk.CTkFrame(card, fg_color="transparent")
        btnrow.grid(row=1, column=0, sticky="w")
        self.ghost_button(btnrow, "＋ Add a template…", self.add_template, width=170).pack(side="left")
        self.ghost_button(btnrow, "Remove", self.remove_template, width=90).pack(side="left", padx=8)
        self.ghost_button(btnrow, "Convert a document to PDF…", self.convert_dialog, width=230).pack(side="left", padx=8)

    def convert_dialog(self) -> None:
        src = self.pick_file("Choose a Word document to convert to PDF",
                             [("Word documents", "*.docx"), ("All files", "*.*")])
        if not src:
            return

        def work():
            return convert.to_pdf(src)

        def done(pdf):
            self.show_info(f"PDF created:\n{pdf}", title="PDF ready")
            try:
                files.open_in_file_manager(os.path.dirname(pdf))
            except Exception:
                pass

        self.run_async(work, done, busy="Converting to PDF…")

    def _template_names(self):
        names = [t.get("name", "") for t in self.config.get("templates", []) if t.get("name")]
        return names or ["(no templates yet — click Add a template)"]

    def _templates(self):
        return self.config.get("templates", [])

    def _find_template(self, name):
        for t in self._templates():
            if t.get("name") == name:
                return t
        return None

    # -- add / remove ----------------------------------------------------
    def add_template(self) -> None:
        path = self.pick_file("Choose the blank template (Word .docx)", [("Word documents", "*.docx"), ("All files", "*.*")])
        if not path:
            return
        try:
            keys = templates.get_placeholders(path)
        except templates.TemplateError as exc:
            self.show_error(str(exc))
            return
        name = os.path.splitext(os.path.basename(path))[0]
        entry = {"name": name, "path": path, "save_to": []}
        self.config.setdefault("templates", []).append(entry)
        self.app.save_config()
        self.template_menu.configure(values=self._template_names())
        self.template_menu.set(name)
        self._on_template_change(name)
        if keys:
            self.show_info(
                f"Added '{name}'. The app found {len(keys)} fill-in field(s):\n\n"
                + ", ".join(keys)
                + "\n\nTip: set the folders to save into with 'Save locations' below.",
                title="Template added",
            )
        else:
            self.show_info(
                f"Added '{name}', but it has no {{{{ fill-in }}}} tags yet.\n\n"
                "Open the blank document and put tags where text should go, e.g. "
                "{{ client }} or {{ project_address }}, then re-add it.",
                title="Template added",
            )

    def remove_template(self) -> None:
        name = self.template_menu.get()
        entry = self._find_template(name)
        if not entry:
            return
        if not self.ask_yes_no(f"Remove the template '{name}' from the app?\n\n(The blank file on disk is not deleted.)"):
            return
        self.config["templates"] = [t for t in self._templates() if t is not entry]
        self.app.save_config()
        self.template_menu.configure(values=self._template_names())
        self.template_menu.set(self._template_names()[0])
        self._on_template_change(self.template_menu.get())

    # -- build the fill-in form -----------------------------------------
    def _on_template_change(self, name) -> None:
        for child in self.form_card_holder.winfo_children():
            child.destroy()
        self.field_widgets = {}
        entry = self._find_template(name)
        if not entry:
            return
        try:
            keys = templates.get_placeholders(entry["path"])
        except templates.TemplateError as exc:
            ctk.CTkLabel(self.form_card_holder, text=str(exc), text_color=theme.DANGER,
                         justify="left").pack(anchor="w")
            return
        self._selected = entry
        self._build_form(entry, keys)
        self._build_output(entry)

    def _build_form(self, entry, keys) -> None:
        holder = ctk.CTkFrame(self.form_card_holder, fg_color=theme.CARD, corner_radius=12,
                              border_width=1, border_color=theme.CARD_BORDER)
        holder.pack(fill="x", pady=(0, 14))
        holder.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(holder, text="2. Fill in the fields", font=theme.FONT_CARD_TITLE, anchor="w").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 4)
        )
        if not keys:
            ctk.CTkLabel(holder, text="This template has no {{ fill-in }} tags.",
                         text_color=theme.MUTED).grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 16))
            return

        prefill = ctk.CTkFrame(holder, fg_color="transparent")
        prefill.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 6))
        ctk.CTkLabel(prefill, text="Pre-fill from project #:", font=theme.FONT_SMALL,
                     text_color=theme.MUTED).pack(side="left")
        self.prefill_entry = ctk.CTkEntry(prefill, width=140, height=28)
        self.prefill_entry.pack(side="left", padx=8)
        self.ghost_button(prefill, "Fill", self.prefill_from_project, width=70, height=28).pack(side="left")

        for i, key in enumerate(keys, start=2):
            ctk.CTkLabel(holder, text=templates.humanize(key), font=theme.FONT_BODY, anchor="w").grid(
                row=i, column=0, sticky="w", padx=(18, 8), pady=5
            )
            w = ctk.CTkEntry(holder, height=30)
            w.grid(row=i, column=1, sticky="ew", padx=(0, 18), pady=5)
            # Friendly defaults for common tags.
            if key.lower() in ("date", "today", "date_today"):
                w.insert(0, datetime.date.today().strftime("%m/%d/%Y"))
            self.field_widgets[key] = w

    def _build_output(self, entry) -> None:
        holder = ctk.CTkFrame(self.form_card_holder, fg_color=theme.CARD, corner_radius=12,
                              border_width=1, border_color=theme.CARD_BORDER)
        holder.pack(fill="x", pady=(0, 14))
        holder.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(holder, text="3. Generate & save", font=theme.FONT_CARD_TITLE, anchor="w").grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 4)
        )

        ctk.CTkLabel(holder, text="File name", font=theme.FONT_SMALL, text_color=theme.MUTED).grid(
            row=1, column=0, sticky="w", padx=18)
        self.filename_entry = ctk.CTkEntry(holder, height=30)
        self.filename_entry.insert(0, f"{entry['name']}.docx")
        self.filename_entry.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 8))

        # Save locations list.
        ctk.CTkLabel(holder, text="Save copies to:", font=theme.FONT_SMALL, text_color=theme.MUTED).grid(
            row=3, column=0, sticky="w", padx=18)
        self.loc_frame = ctk.CTkFrame(holder, fg_color="transparent")
        self.loc_frame.grid(row=4, column=0, sticky="ew", padx=18, pady=(2, 6))
        self._render_locations(entry)

        self.ghost_button(holder, "＋ Add save location…", lambda: self.add_location(entry), width=200).grid(
            row=5, column=0, sticky="w", padx=18, pady=(0, 8))

        self.pdf_var = ctk.StringVar(value="off")
        ctk.CTkCheckBox(holder, text="Also save a PDF copy", variable=self.pdf_var,
                        onvalue="on", offvalue="off").grid(row=6, column=0, sticky="w", padx=18, pady=(0, 6))

        self.primary_button(holder, "📄  Generate document", self.generate).grid(
            row=7, column=0, sticky="w", padx=18, pady=(4, 16))

    def _render_locations(self, entry) -> None:
        for child in self.loc_frame.winfo_children():
            child.destroy()
        locs = entry.get("save_to", [])
        if not locs:
            ctk.CTkLabel(self.loc_frame, text="No fixed locations yet — you'll be asked where to save.",
                         font=theme.FONT_SMALL, text_color=theme.MUTED).pack(anchor="w")
        for loc in locs:
            row = ctk.CTkFrame(self.loc_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text="• " + loc, font=theme.FONT_SMALL, anchor="w").pack(side="left")
            ctk.CTkButton(row, text="✕", width=24, height=22, fg_color="transparent",
                          text_color=theme.DANGER, hover_color=theme.SIDEBAR,
                          command=lambda l=loc: self.remove_location(entry, l)).pack(side="right")

    def add_location(self, entry) -> None:
        folder = self.pick_folder("Choose a folder to always save this document into")
        if not folder:
            return
        entry.setdefault("save_to", []).append(folder)
        self.app.save_config()
        self._render_locations(entry)

    def remove_location(self, entry, loc) -> None:
        entry["save_to"] = [l for l in entry.get("save_to", []) if l != loc]
        self.app.save_config()
        self._render_locations(entry)

    # -- actions ---------------------------------------------------------
    def prefill_from_project(self) -> None:
        from ..services import search
        number = self.prefill_entry.get().strip()
        if not number:
            return
        hits = search.search(self.config, number, limit=1)
        row = {str(k).strip().lower(): v for k, v in (hits[0].row.items() if hits else [])}
        # Merge in everything remembered for this job (the pull-list wins).
        for k, v in jobdata.get(number).items():
            if v not in (None, ""):
                row[str(k).strip().lower()] = v
        if not row:
            self.app.set_status(f"No project or saved data found for '{number}'.")
            return
        # Map common template keys to project columns.
        aliases = {
            "client": ["client", "client name", "owner"],
            "client_name": ["client", "client name", "owner"],
            "project_name": ["project name", "job name", "project", "name"],
            "project_number": ["project number", "project no", "job number", "job #"],
            "project": ["project name", "job name", "project"],
            "address": ["address", "project address", "location"],
            "project_address": ["address", "project address", "location"],
            "contractor": ["contractor", "general contractor", "gc"],
            "engineer": ["engineer", "pm", "engineer / pm"],
        }
        filled = 0
        for key, widget in self.field_widgets.items():
            for col in aliases.get(key.lower(), []):
                if col in row and row[col] not in (None, ""):
                    widget.delete(0, "end")
                    widget.insert(0, str(row[col]))
                    filled += 1
                    break
        self.app.set_status(f"Pre-filled {filled} field(s) from {hits[0].title}.")

    def generate(self) -> None:
        entry = self._selected
        if not entry:
            return
        context = {k: w.get().strip() for k, w in self.field_widgets.items()}
        filename = self.filename_entry.get().strip() or f"{entry['name']}.docx"
        if not filename.lower().endswith(".docx"):
            filename += ".docx"

        locations = list(entry.get("save_to", []))
        if not locations:
            folder = self.pick_folder("Where should this document be saved?")
            if not folder:
                return
            locations = [folder]

        want_pdf = self.pdf_var.get() == "on"

        def work():
            # Fill locally first, then place into each folder (survives a desync).
            tmp = reliable.local_temp(filename)
            templates.fill_template(entry["path"], context, tmp)
            written, queued = reliable.place_file(tmp, locations, filename, label=entry["name"])
            if want_pdf:
                try:
                    pdf_tmp = convert.to_pdf(tmp)
                    pdf_name = os.path.splitext(filename)[0] + ".pdf"
                    pw, pq = reliable.place_file(pdf_tmp, locations, pdf_name, label=entry["name"] + " (PDF)")
                    written += pw
                    queued += pq
                except convert.ConvertError:
                    pass  # PDF is a bonus; don't fail the whole save
            return written, queued

        def done(result):
            written, queued = result
            activity.log(activity.DOCUMENT_GENERATED, details=entry["name"])
            lines = []
            if written:
                lines.append("Saved to:\n" + "\n".join(written))
            if queued:
                lines.append("Cloud unreachable — saved locally, will sync to:\n" + "\n".join(queued))
            self.show_info("\n\n".join(lines) or "Saved.", title="Saved")
            self.app.set_status(f"Generated {filename}.")

        self.run_async(work, done, busy="Filling and saving document…")

    def on_show(self) -> None:
        names = self._template_names()
        self.template_menu.configure(values=names)
        # If search sent us here to generate a specific template, select it.
        pending = getattr(self.app, "pending_template", None)
        if pending and pending in names:
            self.app.pending_template = None
            self.template_menu.set(pending)
            self._on_template_change(pending)
            return
        current = self.template_menu.get()
        if current not in names:
            self.template_menu.set(names[0])
