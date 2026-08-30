"""Job workspace - open one job and do everything for it in one place.

She searches a job, opens it here, and then acts on it:
  * open its folder / Correspondence sub-folder,
  * scan it for missing documents & info (and print the outstanding list),
  * generate a letter from a template - the app pre-fills it from the job and
    saves the finished letter straight into the job's Correspondence folder.

Templates come from the shared library (the same one the Documents panel manages),
so any template she adds is available here too.
"""

from __future__ import annotations

import datetime
import os

import customtkinter as ctk

from .. import theme
from .base import BasePanel
from ..services import files, search, checklist, templates, jobdata, activity, reliable, fieldscan


def _first(row, keys):
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for key in keys:
        v = lowered.get(key.lower())
        if v not in (None, ""):
            return str(v)
    return ""


class JobWorkspacePanel(BasePanel):
    title = "Open a Job"
    subtitle = "Open one job and work on it — scan for missing data, generate letters."

    def build(self) -> None:
        self.job = None
        self._letter_fields = {}
        self._build_open()
        self.detail = ctk.CTkFrame(self.body, fg_color="transparent")
        self.detail.pack(fill="x")
        self.detail.grid_columnconfigure(0, weight=1)

    def _build_open(self) -> None:
        card = self.card("Open a job")
        card.grid_columnconfigure(0, weight=1)
        self.open_entry = ctk.CTkEntry(card, height=36, placeholder_text="Project number, client, address…")
        self.open_entry.grid(row=0, column=0, sticky="ew")
        self.open_entry.bind("<Return>", lambda _e: self.load(self.open_entry.get().strip()))
        self.primary_button(card, "Open", lambda: self.load(self.open_entry.get().strip()), width=100).grid(
            row=0, column=1, padx=(10, 0))

    # -- load ------------------------------------------------------------
    def load(self, query) -> None:
        if not query:
            return

        def work():
            hits = search.search(self.config, query, limit=1)
            return hits[0] if hits else None

        self.run_async(work, self._loaded, busy=f"Opening '{query}'…")

    def load_context(self, ctx) -> None:
        """Open directly from a dict {number,name,row,folder} (used by Home search)."""
        self.job = ctx
        self._render()

    def _loaded(self, hit) -> None:
        if not hit:
            for child in self.detail.winfo_children():
                child.destroy()
            ctk.CTkLabel(self.detail, text="No matching job found.", text_color=theme.DANGER,
                         anchor="w").pack(anchor="w")
            return
        row = hit.row
        number = _first(row, ["project number", "project no", "job number", "job #", "number"])
        name = _first(row, ["project name", "job name", "project", "name"])
        folder = hit.folder or files.find_project_folder(self.config.get("base_folder", ""), number, name)
        self.job = {
            "number": number, "name": name,
            "client": _first(row, ["client", "client name", "owner"]),
            "address": _first(row, ["address", "project address", "location"]),
            "contractor": _first(row, ["contractor", "general contractor", "gc"]),
            "row": row, "folder": folder or "",
        }
        self._render()

    # -- render ----------------------------------------------------------
    def _render(self) -> None:
        for child in self.detail.winfo_children():
            child.destroy()
        if not self.job:
            return
        self._render_summary()
        self._render_missing()
        self._render_letters()

    def _render_summary(self) -> None:
        job = self.job
        card = self.card(f"{job['number']}  {('- ' + job['name']) if job['name'] else ''}".strip())
        card.grid_columnconfigure(0, weight=1)
        bits = []
        if job["client"]:
            bits.append(f"Client: {job['client']}")
        if job["contractor"]:
            bits.append(f"Contractor: {job['contractor']}")
        if job["address"]:
            bits.append(f"Address: {job['address']}")
        ctk.CTkLabel(card, text="   ·   ".join(bits) or "(no details on the list)",
                     font=theme.FONT_BODY, text_color=theme.MUTED, anchor="w", justify="left",
                     wraplength=800).grid(row=0, column=0, sticky="w")
        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=1, column=0, sticky="w", pady=(10, 0))
        if job["folder"]:
            self.accent_button(btns, "Open Folder", lambda: self._open(job["folder"]), width=130).pack(side="left", padx=(0, 8))
            corr = self._correspondence_dir()
            if corr:
                self.ghost_button(btns, "Open Correspondence", lambda c=corr: self._open(c), width=180).pack(side="left", padx=(0, 8))
        else:
            ctk.CTkLabel(card, text="No folder found under the work folder for this job.",
                         text_color=theme.WARNING, font=theme.FONT_SMALL).grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.ghost_button(btns, "🖨 Missing-fields report", self.print_missing_fields, width=210).pack(side="left")

    def print_missing_fields(self) -> None:
        number = self.job["number"]
        job_values = {str(k): v for k, v in self.job.get("row", {}).items()}
        for k in ("number", "name", "client", "address", "contractor"):
            if self.job.get(k):
                job_values[k] = self.job[k]
        job_values.update(jobdata.get(number))

        def work():
            groups = fieldscan.scan(self.config, job_values)
            base_dir = self.job.get("folder") or self.config.get("base_folder", "") or "."
            dest = os.path.join(base_dir, f"Missing Fields - {number}.docx")
            company = self.config.get("company", {}).get("name", "")
            return fieldscan.generate_report(dest, number, self.job.get("name", ""), groups, company)

        def done(path):
            self.show_info(f"Saved:\n{path}\n\nOpen it and print — red MISSING marks each unfilled field.",
                           title="Missing-fields report")
            try:
                files.open_in_file_manager(os.path.dirname(path))
            except Exception:
                pass

        self.run_async(work, done, busy="Building missing-fields report…")

    def _render_missing(self) -> None:
        card = self.card("Missing data", "Scan this job's folder for required documents and info.")
        card.grid_columnconfigure(0, weight=1)
        self.primary_button(card, "🔍  Scan for missing items", self.scan_missing, width=220).grid(
            row=0, column=0, sticky="w")
        self.missing_area = ctk.CTkFrame(card, fg_color="transparent")
        self.missing_area.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.missing_area.grid_columnconfigure(0, weight=1)

    def _render_letters(self) -> None:
        card = self.card("Generate a letter / document",
                         "Pick a template — it fills from this job and saves into Correspondence.")
        card.grid_columnconfigure(0, weight=1)
        rowf = ctk.CTkFrame(card, fg_color="transparent")
        rowf.grid(row=0, column=0, sticky="ew")
        rowf.grid_columnconfigure(0, weight=1)
        self.template_menu = ctk.CTkOptionMenu(rowf, values=self._template_names(), height=34)
        self.template_menu.grid(row=0, column=0, sticky="ew")
        self.ghost_button(rowf, "＋ Add template…", self.add_template, width=150).grid(row=0, column=1, padx=(8, 0))
        self.primary_button(rowf, "Prepare", self.prepare_letter, width=110).grid(row=0, column=2, padx=(8, 0))
        self.letter_area = ctk.CTkFrame(card, fg_color="transparent")
        self.letter_area.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.letter_area.grid_columnconfigure(1, weight=1)

    # -- helpers ---------------------------------------------------------
    def _correspondence_dir(self) -> str:
        folder = self.job.get("folder", "") if self.job else ""
        if not folder:
            return ""
        for sub in self.config.get("folder_template", []):
            if "correspond" in sub.lower():
                p = os.path.join(folder, sub)
                if os.path.isdir(p):
                    return p
        return folder

    def _open(self, path) -> None:
        try:
            files.open_in_file_manager(path)
        except Exception as exc:  # noqa: BLE001
            self.show_error(str(exc))

    def _template_names(self):
        names = [t.get("name", "") for t in self.config.get("templates", []) if t.get("name")]
        return names or ["(no templates — click Add template)"]

    def _find_template(self, name):
        for t in self.config.get("templates", []):
            if t.get("name") == name:
                return t
        return None

    # -- missing scan ----------------------------------------------------
    def scan_missing(self) -> None:
        job = self.job

        def work():
            return checklist.scan_job(job["number"], job.get("folder", ""),
                                      self.config.get("required_documents", []),
                                      self.config.get("required_info", []))

        self.run_async(work, self._render_missing_results, busy="Scanning job folder…")

    def _render_missing_results(self, needs) -> None:
        self._needs = needs
        for child in self.missing_area.winfo_children():
            child.destroy()
        for i, d in enumerate(needs.documents):
            mark = "✓" if d.present else "✗"
            color = theme.SUCCESS if d.present else theme.DANGER
            ctk.CTkLabel(self.missing_area, text=f"{mark}  {d.label}", text_color=color,
                         font=theme.FONT_BODY, anchor="w").grid(row=i, column=0, sticky="w", pady=1)
        base = len(needs.documents)
        for j, item in enumerate(needs.info):
            mark = "✓" if item["confirmed"] else "○"
            color = theme.SUCCESS if item["confirmed"] else theme.MUTED
            ctk.CTkLabel(self.missing_area, text=f"{mark}  {item['label']}", text_color=color,
                         font=theme.FONT_BODY, anchor="w").grid(row=base + j, column=0, sticky="w", pady=1)
        self.ghost_button(self.missing_area, "🖨  Print outstanding-items sheet", self.print_missing, width=260).grid(
            row=base + len(needs.info), column=0, sticky="w", pady=(8, 0))

    def print_missing(self) -> None:
        needs = getattr(self, "_needs", None)
        if not needs:
            return

        def work():
            base_dir = self.job.get("folder") or self.config.get("base_folder", "") or "."
            dest = os.path.join(base_dir, f"Outstanding Items - {self.job['number']}.docx")
            company = self.config.get("company", {}).get("name", "")
            return checklist.generate_missing_sheet(dest, needs, self.job.get("name", ""), company)

        def done(path):
            self.show_info(f"Saved:\n{path}\n\nOpen it and print.", title="Sheet ready")

        self.run_async(work, done, busy="Building outstanding-items sheet…")

    # -- letters ---------------------------------------------------------
    def add_template(self) -> None:
        path = self.pick_file("Choose the blank letter template (Word .docx)",
                              [("Word documents", "*.docx"), ("All files", "*.*")])
        if not path:
            return
        try:
            keys = templates.get_placeholders(path)
        except templates.TemplateError as exc:
            self.show_error(str(exc))
            return
        name = os.path.splitext(os.path.basename(path))[0]
        self.config.setdefault("templates", []).append({"name": name, "path": path, "save_to": []})
        self.app.save_config()
        self.template_menu.configure(values=self._template_names())
        self.template_menu.set(name)
        self.show_info(f"Added '{name}'. Found {len(keys)} fill-in field(s).", title="Template added")

    def prepare_letter(self) -> None:
        for child in self.letter_area.winfo_children():
            child.destroy()
        self._letter_fields = {}
        entry = self._find_template(self.template_menu.get())
        if not entry:
            self.show_error("Add a template first.")
            return
        try:
            keys = templates.get_placeholders(entry["path"])
        except templates.TemplateError as exc:
            self.show_error(str(exc))
            return

        job = self.job
        prefill = {
            "client": job["client"], "client_name": job["client"],
            "project": job["name"], "project_name": job["name"],
            "project_number": job["number"], "job_number": job["number"],
            "address": job["address"], "project_address": job["address"],
            "contractor": job["contractor"],
            "date": datetime.date.today().strftime("%m/%d/%Y"),
            "today": datetime.date.today().strftime("%m/%d/%Y"),
        }
        # Everything ever entered for this job feeds the letter (enter once).
        for k, v in jobdata.get(job["number"]).items():
            if v not in (None, ""):
                prefill.setdefault(k.lower(), v)
        for i, key in enumerate(keys):
            ctk.CTkLabel(self.letter_area, text=templates.humanize(key), font=theme.FONT_BODY, anchor="w").grid(
                row=i, column=0, sticky="w", padx=(0, 10), pady=4)
            w = ctk.CTkEntry(self.letter_area, height=30)
            if key.lower() in prefill and prefill[key.lower()]:
                w.insert(0, prefill[key.lower()])
            w.grid(row=i, column=1, sticky="ew", pady=4)
            self._letter_fields[key] = w

        namerow = len(keys)
        ctk.CTkLabel(self.letter_area, text="Save as", font=theme.FONT_BODY, anchor="w").grid(
            row=namerow, column=0, sticky="w", padx=(0, 10), pady=4)
        self.letter_filename = ctk.CTkEntry(self.letter_area, height=30)
        self.letter_filename.insert(0, f"{entry['name']} - {job['number']}.docx")
        self.letter_filename.grid(row=namerow, column=1, sticky="ew", pady=4)

        self.primary_button(self.letter_area, "📄  Generate & save to Correspondence",
                            lambda e=entry: self.generate_letter(e), width=300).grid(
            row=namerow + 1, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def generate_letter(self, entry) -> None:
        context = {k: w.get().strip() for k, w in self._letter_fields.items()}
        # Remember what she typed so future documents pre-fill from it.
        jobdata.update(self.job["number"], context)
        filename = self.letter_filename.get().strip() or f"{entry['name']}.docx"
        if not filename.lower().endswith(".docx"):
            filename += ".docx"
        corr = self._correspondence_dir()
        if not corr:
            corr = self.pick_folder("No Correspondence folder found — choose where to save")
            if not corr:
                return
        locations = [corr] + list(entry.get("save_to", []))

        def work():
            tmp = reliable.local_temp(filename)
            templates.fill_template(entry["path"], context, tmp)
            return reliable.place_file(tmp, locations, filename, label=entry["name"])

        def done(result):
            written, queued = result
            activity.log(activity.LETTER_GENERATED, project=self.job["number"], details=entry["name"])
            lines = []
            if written:
                lines.append("Saved to:\n" + "\n".join(written))
            if queued:
                lines.append("Cloud unreachable — saved locally, will sync to:\n" + "\n".join(queued))
            self.show_info("\n\n".join(lines) or "Saved.", title="Saved")
            self.app.set_status(f"Letter saved for job {self.job['number']}.")

        self.run_async(work, done, busy="Generating letter…")

    # -- lifecycle -------------------------------------------------------
    def on_show(self) -> None:
        ctx = getattr(self.app, "current_job", None)
        if ctx:
            self.app.current_job = None
            self.load_context(ctx)
