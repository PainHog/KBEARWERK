"""Redlines panel.

She scans the redline herself (the app doesn't touch the scanner). Then this
panel does the tedious part:
  * files the scanned PDF into the right project's Redlines folder,
  * emails it to the correct drafter (as a draft she can review before sending),
  * logs it to the two lists she keeps.
Printing stays with her.
"""

from __future__ import annotations

import datetime
import os

import customtkinter as ctk

from .. import theme
from .base import BasePanel
from ..services import files, outlook, reliable, people, activity


class RedlinesPanel(BasePanel):
    title = "Redlines"
    subtitle = "File a scanned redline, send it to the drafter, and update the lists."

    def build(self) -> None:
        self._filed_path = ""
        self._project_folder = ""
        self._build_pick()
        self._build_project()
        self._build_drafter()
        self._build_actions()

    def _build_pick(self) -> None:
        card = self.card("1. The scanned redline", "Choose the PDF you just scanned.")
        card.grid_columnconfigure(0, weight=1)
        self.file_entry = ctk.CTkEntry(card, height=32, placeholder_text="No file chosen")
        self.file_entry.grid(row=0, column=0, sticky="ew")
        self.ghost_button(card, "Browse…", self.browse, width=100).grid(row=0, column=1, padx=(10, 0))

    def _build_project(self) -> None:
        card = self.card("2. Which project?")
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Project #", font=theme.FONT_BODY).grid(row=0, column=0, padx=(0, 8))
        self.number_entry = ctk.CTkEntry(card, height=32, placeholder_text="e.g. 2025-104")
        self.number_entry.grid(row=0, column=1, sticky="ew")
        self.ghost_button(card, "Find folder", self.find_folder, width=110).grid(row=0, column=2, padx=(10, 0))
        self.folder_label = ctk.CTkLabel(card, text="", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w")
        self.folder_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))

    def _build_drafter(self) -> None:
        card = self.card("3. Which drafter?")
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Drafter", font=theme.FONT_BODY).grid(row=0, column=0, padx=(0, 8))
        self.drafter_menu = ctk.CTkOptionMenu(card, values=self._drafter_values(), height=32)
        self.drafter_menu.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(card, text="Note", font=theme.FONT_BODY).grid(row=1, column=0, padx=(0, 8), pady=(8, 0), sticky="w")
        self.note_entry = ctk.CTkEntry(card, height=32, placeholder_text="Optional note for the drafter")
        self.note_entry.grid(row=1, column=1, columnspan=2, sticky="ew", pady=(8, 0))
        self.send_now = ctk.CTkCheckBox(card, text="Send immediately (otherwise it opens a draft to review)")
        self.send_now.grid(row=2, column=1, columnspan=2, sticky="w", pady=(8, 0))

    def _build_actions(self) -> None:
        card = self.card("4. Do it")
        card.grid_columnconfigure(0, weight=1)
        self.primary_button(card, "▶  File + Email drafter + Update lists", self.do_all).grid(
            row=0, column=0, sticky="w", pady=(0, 10))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=1, column=0, sticky="w")
        self.ghost_button(row, "File into folder", self.do_file, width=150).pack(side="left", padx=(0, 8))
        self.ghost_button(row, "Email drafter", self.do_email, width=140).pack(side="left", padx=8)
        self.ghost_button(row, "Update the 2 lists", self.do_lists, width=160).pack(side="left", padx=8)
        self.status = ctk.CTkLabel(card, text="", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w")
        self.status.grid(row=2, column=0, sticky="w", pady=(8, 0))

    # -- helpers ---------------------------------------------------------
    def _drafter_values(self):
        names = people.nicknames(self.config, role="drafter")
        return names or ["(add people in Settings)"]

    def _drafter_email(self):
        return people.resolve_email(self.config, self.drafter_menu.get())

    def browse(self) -> None:
        path = self.pick_file("Choose the scanned redline", [("PDF files", "*.pdf"), ("All files", "*.*")])
        if path:
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, path)

    def find_folder(self) -> None:
        base = self.config.get("base_folder", "")
        number = self.number_entry.get().strip()
        folder = files.find_project_folder(base, number, "")
        if folder:
            self._project_folder = folder
            self.folder_label.configure(text=f"Folder: {folder}", text_color=theme.SUCCESS)
        else:
            self._project_folder = ""
            self.folder_label.configure(text="No matching folder found under the work folder.", text_color=theme.DANGER)

    def _redline_dir(self) -> str:
        if not self._project_folder:
            self.find_folder()
        if not self._project_folder:
            raise ValueError("Find the project folder first (enter the project number and click Find folder).")
        for sub in self.config.get("folder_template", []):
            if "redline" in sub.lower():
                candidate = os.path.join(self._project_folder, sub)
                if os.path.isdir(candidate):
                    return candidate
        return self._project_folder

    def _set_status(self, text, ok=True) -> None:
        self.status.configure(text=text, text_color=(theme.SUCCESS if ok else theme.DANGER))

    # -- actions ---------------------------------------------------------
    def do_file(self) -> None:
        src = self.file_entry.get().strip()
        number = self.number_entry.get().strip()
        if not src:
            self.show_error("Choose the scanned PDF first.")
            return

        def work():
            dest_dir = self._redline_dir()
            today = datetime.date.today().strftime("%m-%d-%Y")
            newname = f"{number} - Redline - {today}.pdf" if number else None
            return files.file_into_folder(src, dest_dir, new_name=newname)

        def done(path):
            self._filed_path = path
            self._set_status(f"Filed to: {path}")
            self.app.set_status("Redline filed.")

        self.run_async(work, done, busy="Filing redline…")

    def do_email(self) -> None:
        drafter = self.drafter_menu.get()
        to = self._drafter_email()
        if not to:
            self.show_error(f"'{drafter}' has no email set. Add their email in Settings → People.")
            return
        number = self.number_entry.get().strip()
        note = self.note_entry.get().strip()
        attach = self._filed_path or self.file_entry.get().strip()
        send = self.send_now.get() == "on"

        def work():
            subject = f"Redline - {number}".strip(" -")
            body = (f"Hi {drafter},\n\nPlease find the attached redline for project {number}.\n"
                    f"{note}\n\nThanks!")
            outlook.create_email(to=to, subject=subject, body=body,
                                 attachments=[attach] if attach and os.path.exists(attach) else [],
                                 send=send)
            return send

        def done(was_sent):
            if was_sent:
                self._set_status(f"Redline sent to {drafter} ✓")
                activity.log(activity.EMAIL_SENT, project=number, details=f"Redline to {drafter}")
                activity.log(activity.REDLINE_PROCESSED, project=number, details=f"Sent to {drafter}")
            else:
                self._set_status(f"Draft to {drafter} opened in Outlook — review and Send.")
            self.app.set_status("Redline email handled.")

        if not outlook.available():
            self.show_info("Email runs on her Windows PC with Outlook. It's inactive here, "
                           "but the button will send/draft the email there.")
            return
        self.run_async(work, done, busy="Creating email…")

    def do_lists(self) -> None:
        number = self.number_entry.get().strip()
        drafter = self.drafter_menu.get()
        note = self.note_entry.get().strip()
        today = datetime.date.today().strftime("%m/%d/%Y")
        values = {
            "Project Number": number, "Job Number": number, "Job #": number,
            "Drafter": drafter, "Date": today, "Date Sent": today,
            "Description": note, "Notes": note,
            "File": os.path.basename(self._filed_path) if self._filed_path else "",
            "Status": "Sent to drafter",
        }
        paths = self.config.get("paths", {})
        targets = [("redline_log", "Redline Log"), ("drafting_list", "Drafting List")]

        def work():
            done_to, queued = [], []
            for key, label in targets:
                p = paths.get(key, "")
                if not p:
                    continue
                result = reliable.excel_append(p, values, label=label)
                (queued if result == "queued" else done_to).append(label)
            return done_to, queued

        def done(result):
            done_to, queued = result
            if not done_to and not queued:
                self._set_status("No list files set. Add Redline Log / Drafting List in Settings.", ok=False)
                return
            msg = ""
            if done_to:
                msg += "Updated: " + ", ".join(done_to)
            if queued:
                msg += ("   " if msg else "") + "Saved locally (will sync): " + ", ".join(queued)
            self._set_status(msg + "  ✓")

        def on_error(exc):
            self._set_status(str(exc).splitlines()[0], ok=False)
            self.show_error(str(exc))

        self.run_async(work, done, on_error=on_error, busy="Updating lists…")

    def do_all(self) -> None:
        self.do_file()
        self.after(400, self.do_email)
        self.after(800, self.do_lists)

    def on_show(self) -> None:
        values = self._drafter_values()
        self.drafter_menu.configure(values=values)
        if self.drafter_menu.get() not in values:
            self.drafter_menu.set(values[0])
