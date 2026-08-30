"""Site Inspection Sheet panel.

When she sends an inspector to a site she fills out a site inspection sheet. This
panel is that sheet:

* Job side (auto-filled from the job's saved data): client name, phone, job
  number, address, scheduled date.
* Inspector side: mileage, hours, actual date (for reschedules / return visits),
  and **approved for city letter**.
* When "approved for city letter" is ticked, the city-letter template library
  comes into play - one click generates the right city letter, pre-filled, into
  the job's Correspondence folder.

Saving writes to the inspection workbook through Excel itself (preserving its
dropdowns / checkboxes / tabs), and remembers the client info on the job so it
carries over.
"""

from __future__ import annotations

import datetime
import os

import customtkinter as ctk

from .. import theme
from .base import BasePanel
from ..services import (reliable, people, activity, jobdata, search, files,
                        templates, outlook, seal)


class ObservationsPanel(BasePanel):
    title = "Observations / Inspections"
    subtitle = "Fill the site inspection sheet — client info auto-fills from the job."

    def build(self) -> None:
        self.fields = {}
        self._build_job_section()
        self._build_inspector_section()
        self._build_actions()

    # -- job section -----------------------------------------------------
    def _build_job_section(self) -> None:
        card = self.card("Job & client", "Enter the project number and click Load — the rest fills in.")
        card.grid_columnconfigure((1, 3), weight=1)
        ctk.CTkLabel(card, text="Project #", font=theme.FONT_BODY).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=5)
        self.fields["number"] = ctk.CTkEntry(card, height=32)
        self.fields["number"].grid(row=0, column=1, sticky="ew", pady=5)
        self.ghost_button(card, "Load job", self.load_job, width=100).grid(row=0, column=2, padx=(8, 8))

        self._field(card, 1, 0, "client", "Client Name")
        self._field(card, 1, 2, "client_phone", "Client Phone")
        self._field(card, 2, 0, "address", "Address")
        self._field(card, 2, 2, "sched_date", "Scheduled Date", datetime.date.today().strftime("%m/%d/%Y"))

    # -- inspector section ----------------------------------------------
    def _build_inspector_section(self) -> None:
        card = self.card("Inspector & visit", "The inspector supplies these.")
        card.grid_columnconfigure((1, 3), weight=1)
        ctk.CTkLabel(card, text="Inspector", font=theme.FONT_BODY).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=5)
        self.inspector_menu = ctk.CTkOptionMenu(card, values=self._inspector_values(), height=32)
        self.inspector_menu.grid(row=0, column=1, sticky="ew", pady=5)
        self._field(card, 0, 2, "actual_date", "Actual Date (if changed)")
        self._field(card, 1, 0, "mileage", "Mileage")
        self._field(card, 1, 2, "hours", "Hours")

        self.approved_var = ctk.StringVar(value="off")
        ctk.CTkCheckBox(card, text="Approved for city letter", variable=self.approved_var,
                        onvalue="on", offvalue="off", command=self._toggle_city).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(8, 5))
        self.city_label = ctk.CTkLabel(card, text="City letter template", font=theme.FONT_BODY)
        self.city_menu = ctk.CTkOptionMenu(card, values=self._template_values(), height=32)
        self.eng_label = ctk.CTkLabel(card, text="Engineer (seal)", font=theme.FONT_BODY)
        self.eng_menu = ctk.CTkOptionMenu(card, values=self._engineer_values(), height=32)
        self._city_row = 3
        ctk.CTkLabel(card, text="Notes", font=theme.FONT_BODY, anchor="nw").grid(
            row=4, column=0, sticky="nw", padx=(0, 8), pady=5)
        self.notes = ctk.CTkTextbox(card, height=54)
        self.notes.grid(row=4, column=1, columnspan=3, sticky="ew", pady=5)
        self._city_card = card

    def _toggle_city(self) -> None:
        if self.approved_var.get() == "on":
            self.city_label.grid(row=self._city_row, column=0, sticky="w", padx=(0, 8), pady=5)
            self.city_menu.configure(values=self._template_values())
            self.city_menu.grid(row=self._city_row, column=1, sticky="ew", pady=5)
            self.eng_label.grid(row=self._city_row, column=2, sticky="w", padx=(0, 8), pady=5)
            self.eng_menu.configure(values=self._engineer_values())
            self.eng_menu.grid(row=self._city_row, column=3, sticky="ew", pady=5)
        else:
            for w in (self.city_label, self.city_menu, self.eng_label, self.eng_menu):
                w.grid_forget()

    def _engineer_values(self):
        names = [s.get("name", "") for s in self.config.get("seals", []) if s.get("name")]
        return names or ["(add engineer seals in Settings)"]

    def _build_actions(self) -> None:
        card = self.card()
        card.grid_columnconfigure(0, weight=1)
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=0, column=0, sticky="w")
        self.primary_button(row, "Save inspection sheet", self.save).pack(side="left")
        self.ghost_button(row, "Email inspector assignment", self.email, width=210).pack(side="left", padx=10)
        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.accent_button(row2, "1) Draft city letter (review)", self.draft_city_letter, width=230).pack(side="left")
        self.seal_button = self.ghost_button(row2, "2) Seal & Save final", self.seal_and_save, width=180)
        self.seal_button.pack(side="left", padx=10)
        self.status = ctk.CTkLabel(card, text="", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w")
        self.status.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self._seal_pending = None

    # -- helpers ---------------------------------------------------------
    def _field(self, parent, r, c, key, label, default=""):
        ctk.CTkLabel(parent, text=label, font=theme.FONT_BODY).grid(row=r, column=c, sticky="w", padx=(0, 8), pady=5)
        e = ctk.CTkEntry(parent, height=32)
        if default:
            e.insert(0, default)
        e.grid(row=r, column=c + 1, sticky="ew", pady=5)
        self.fields[key] = e
        return e

    def _inspector_values(self):
        return people.nicknames(self.config, role="inspector") or ["(add people in Settings)"]

    def _template_values(self):
        names = [t.get("name", "") for t in self.config.get("templates", []) if t.get("name")]
        return names or ["(add city-letter templates in Documents)"]

    def _values(self):
        v = {k: w.get().strip() for k, w in self.fields.items()}
        v["inspector"] = self.inspector_menu.get()
        v["approved"] = self.approved_var.get() == "on"
        v["notes"] = self.notes.get("1.0", "end").strip()
        return v

    def load_job(self) -> None:
        number = self.fields["number"].get().strip()
        if not number:
            return
        merged = {}
        hits = search.search(self.config, number, limit=1)
        if hits:
            merged.update({str(k).strip().lower(): val for k, val in hits[0].row.items()})
        merged.update({k.lower(): val for k, val in jobdata.get(number).items()})

        def pick(*keys):
            for k in keys:
                if merged.get(k) not in (None, ""):
                    return str(merged[k])
            return ""
        self._set("client", pick("client", "client_name", "owner"))
        self._set("client_phone", pick("client_phone", "phone"))
        self._set("address", pick("address", "project_address", "location"))
        self.app.set_status(f"Loaded job {number}.")

    def _set(self, key, value):
        if value and key in self.fields:
            self.fields[key].delete(0, "end")
            self.fields[key].insert(0, value)

    # -- actions ---------------------------------------------------------
    def save(self) -> None:
        v = self._values()
        # Carry client info back onto the job so it's remembered.
        jobdata.update(v["number"], {"client": v["client"], "client_phone": v["client_phone"],
                                     "address": v["address"]})
        path = self.config.get("paths", {}).get("observations_log", "")
        if not path:
            self.show_error("Set the Observations/Inspection workbook in Settings first.")
            return
        row = {
            "Project Number": v["number"], "Job Number": v["number"],
            "Client": v["client"], "Client Name": v["client"],
            "Phone": v["client_phone"], "Client Phone": v["client_phone"],
            "Address": v["address"], "Site Address": v["address"],
            "Date": v["sched_date"], "Scheduled Date": v["sched_date"],
            "Actual Date": v["actual_date"], "Inspector": v["inspector"],
            "Mileage": v["mileage"], "Hours": v["hours"],
            "Approved for City Letter": "Yes" if v["approved"] else "No",
            "City Letter": "Yes" if v["approved"] else "",
            "Notes": v["notes"], "Status": "Inspected",
        }

        def work():
            return reliable.excel_append(path, row, label="Inspection Log", prefer_com=True)

        def done(result):
            if result == "queued":
                self.status.configure(text="Cloud unreachable — saved locally, will sync. ⏳",
                                      text_color=theme.WARNING)
            else:
                self.status.configure(text="Inspection sheet saved. ✓", text_color=theme.SUCCESS)
                activity.log(activity.OBSERVATION_SET, project=v["number"], details=v["inspector"])
            if v["approved"]:
                self.status.configure(text=self.status.cget("text") + "  — approved: you can Generate the city letter.")

        def on_error(exc):
            self.status.configure(text=str(exc).splitlines()[0], text_color=theme.DANGER)
            self.show_error(str(exc))

        self.run_async(work, done, on_error=on_error, busy="Saving inspection sheet…")

    def email(self) -> None:
        to = people.resolve_email(self.config, self.inspector_menu.get())
        if not to:
            self.show_error(f"'{self.inspector_menu.get()}' has no email set. Add it in Settings → People.")
            return
        if not outlook.available():
            self.show_info("Email runs on her Windows PC with Outlook; it's inactive here.")
            return
        v = self._values()

        def work():
            subject = f"Site inspection - {v['number']} {v['client']}".strip()
            body = (f"Hi {v['inspector']},\n\nPlease perform a site inspection:\n\n"
                    f"Job: {v['number']}\nClient: {v['client']}  ({v['client_phone']})\n"
                    f"Address: {v['address']}\nDate: {v['sched_date']}\n\n"
                    f"Please record mileage, hours, actual date, and whether it's approved "
                    f"for a city letter.\n\nThanks!")
            outlook.create_email(to=to, subject=subject, body=body, send=False)
            return True

        def done(_r):
            self.status.configure(text="Inspector assignment drafted in Outlook. ✓", text_color=theme.SUCCESS)

        self.run_async(work, done, busy="Drafting inspector email…")

    def _city_setup(self):
        """Validate + gather (entry, context, corr, number, tpl_name) for a city letter."""
        v = self._values()
        if not v["approved"]:
            self.show_info("Tick 'Approved for city letter' first.")
            return None
        tpl_name = self.city_menu.get()
        entry = next((t for t in self.config.get("templates", []) if t.get("name") == tpl_name), None)
        if not entry:
            self.show_error("Choose a city-letter template (add them in the Documents panel).")
            return None
        number = v["number"]
        context = dict(jobdata.get(number))
        context.update({
            "client": v["client"], "client_name": v["client"],
            "client_phone": v["client_phone"], "phone": v["client_phone"],
            "address": v["address"], "project_address": v["address"],
            "project_number": number, "job_number": number,
            "date": datetime.date.today().strftime("%m/%d/%Y"),
        })
        folder = files.find_project_folder(self.config.get("base_folder", ""), number, "")
        corr = folder
        if folder:
            for sub in self.config.get("folder_template", []):
                if "correspond" in sub.lower() and os.path.isdir(os.path.join(folder, sub)):
                    corr = os.path.join(folder, sub)
                    break
        if not corr:
            corr = self.pick_folder("Where should the city letter be saved?")
            if not corr:
                return None
        return entry, context, corr, number, tpl_name

    def draft_city_letter(self) -> None:
        setup = self._city_setup()
        if not setup:
            return
        entry, context, corr, number, tpl_name = setup

        def work():
            draft_name = f"{tpl_name} - {number} - DRAFT.docx"
            tmp = reliable.local_temp(draft_name)
            seal.render_draft(entry["path"], context, tmp)
            written, queued = reliable.place_file(tmp, [corr], draft_name, label=tpl_name + " (draft)")
            path = (written or [tmp])[0]
            try:
                files.open_in_file_manager(os.path.dirname(path))
            except Exception:
                pass
            return path

        def done(path):
            self._seal_pending = (entry, context, corr, number, tpl_name)
            self.status.configure(text="Draft created (watermarked). Review it, then click 'Seal & Save final'.",
                                  text_color=theme.WARNING)

        self.run_async(work, done, busy="Creating draft city letter…")

    def seal_and_save(self) -> None:
        if not self._seal_pending:
            self.show_info("Make the draft first, review it, then Seal & Save.")
            return
        entry, context, corr, number, tpl_name = self._seal_pending
        engineer = seal.find_engineer(self.config, self.eng_menu.get())
        if not engineer:
            self.show_error("No engineer seal is set up. Add one in Settings → Engineer seals.")
            return
        if not self.ask_yes_no(
            f"Apply {engineer.get('name','the engineer')}'s signature and seal and save the FINAL letter?"
        ):
            return
        filename = f"{tpl_name} - {number}.docx"

        def work():
            tmp = reliable.local_temp(filename)
            seal.render_sealed(entry["path"], context, tmp,
                               signature_image=engineer.get("signature_image", ""),
                               seal_image=engineer.get("seal_image", ""))
            return reliable.place_file(tmp, [corr], filename, label=tpl_name)

        def done(result):
            written, queued = result
            activity.log(activity.LETTER_GENERATED, project=number, details=f"Sealed city letter: {tpl_name}")
            where = "\n".join(written or queued)
            self.status.configure(text=f"Sealed & saved → {where}", text_color=theme.SUCCESS)
            self.show_info(f"Sealed city letter saved:\n{where}", title="Sealed & saved")
            self._seal_pending = None

        self.run_async(work, done, busy="Sealing and saving…")

    def on_show(self) -> None:
        values = self._inspector_values()
        self.inspector_menu.configure(values=values)
        if self.inspector_menu.get() not in values:
            self.inspector_menu.set(values[0])
