"""Settings panel - point the app at her real folders, files, people and rules.

Everything here is saved locally. This is the one place we'll spend time together
once she shares her real files, so the rest of the app lines up with how her
office actually works.
"""

from __future__ import annotations

import customtkinter as ctk

from .. import theme
from .base import BasePanel


PATH_FIELDS = [
    ("proposal_list", "Proposal List"),
    ("project_list", "Project List"),
    ("weekly_worksheet", "Weekly Worksheet"),
    ("redline_log", "Redline Log"),
    ("drafting_list", "Drafting List"),
    ("observations_log", "Observations / Inspection workbook"),
    ("invoice_ledger", "Invoice Ledger"),
]


class SettingsPanel(BasePanel):
    title = "Settings"
    subtitle = "Tell the app where her files are and who her people are."

    def build(self) -> None:
        self._build_folders()
        self._build_files()
        self._build_folder_template()
        self._build_people()
        self._build_seals()
        self._build_email()
        self._build_urls_company()
        self._build_appearance()
        self._build_save()

    # -- work folder -----------------------------------------------------
    def _build_folders(self) -> None:
        card = self.card("Work folder", "The folder that all job folders live under (e.g. D:\\Work or a synced cloud folder).")
        card.grid_columnconfigure(0, weight=1)
        self.base_entry = ctk.CTkEntry(card, height=32)
        self.base_entry.insert(0, self.config.get("base_folder", ""))
        self.base_entry.grid(row=0, column=0, sticky="ew")
        self.ghost_button(card, "Browse…", self._pick_base, width=100).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkLabel(card, text="New project folder name pattern (fields: {number} {name} {client})",
                     font=theme.FONT_SMALL, text_color=theme.MUTED).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.pattern_entry = ctk.CTkEntry(card, height=30)
        self.pattern_entry.insert(0, self.config.get("project_folder_pattern", "{number} - {name}"))
        self.pattern_entry.grid(row=2, column=0, sticky="ew", pady=(2, 0))

    def _pick_base(self) -> None:
        folder = self.pick_folder("Choose the work folder")
        if folder:
            self.base_entry.delete(0, "end")
            self.base_entry.insert(0, folder)

    # -- file locations --------------------------------------------------
    def _build_files(self) -> None:
        card = self.card("File locations", "Point at each spreadsheet. The app writes to the next empty row and never overwrites old data.")
        card.grid_columnconfigure(1, weight=1)
        self.path_entries = {}
        for i, (key, label) in enumerate(PATH_FIELDS):
            ctk.CTkLabel(card, text=label, font=theme.FONT_BODY, anchor="w").grid(row=i, column=0, sticky="w", padx=(0, 8), pady=4)
            e = ctk.CTkEntry(card, height=30)
            e.insert(0, self.config.get("paths", {}).get(key, ""))
            e.grid(row=i, column=1, sticky="ew", pady=4)
            self.ghost_button(card, "Browse…", lambda k=key: self._pick_path(k), width=90).grid(row=i, column=2, padx=(8, 0))
            self.path_entries[key] = e

    def _pick_path(self, key) -> None:
        path = self.pick_file("Choose the spreadsheet", [("Excel", "*.xlsx *.xlsm *.xls"), ("All files", "*.*")])
        if path:
            self.path_entries[key].delete(0, "end")
            self.path_entries[key].insert(0, path)

    # -- folder template -------------------------------------------------
    def _build_folder_template(self) -> None:
        card = self.card("Job folder sub-folders", "One per line — created inside every new job folder.")
        card.grid_columnconfigure(0, weight=1)
        self.template_box = ctk.CTkTextbox(card, height=140)
        self.template_box.insert("1.0", "\n".join(self.config.get("folder_template", [])))
        self.template_box.grid(row=0, column=0, sticky="ew")

    # -- people ----------------------------------------------------------
    def _build_people(self) -> None:
        card = self.card("People (contacts)", "She picks people by nickname — the email is used quietly when sending.")
        card.grid_columnconfigure(0, weight=1)
        self.people_holder = ctk.CTkFrame(card, fg_color="transparent")
        self.people_holder.grid(row=0, column=0, sticky="ew")
        self.people_holder.grid_columnconfigure(0, weight=1)
        self._render_people()

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        form.grid_columnconfigure((0, 1, 2), weight=1)
        self.new_nick = ctk.CTkEntry(form, height=30, placeholder_text="Nickname (e.g. Carl)")
        self.new_nick.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.new_email = ctk.CTkEntry(form, height=30, placeholder_text="Email")
        self.new_email.grid(row=0, column=1, sticky="ew", padx=6)
        self.new_role = ctk.CTkOptionMenu(form, values=["drafter", "inspector", "staff"], height=30)
        self.new_role.grid(row=0, column=2, sticky="ew", padx=6)
        self.ghost_button(form, "Add", self._add_person, width=70).grid(row=0, column=3, padx=(6, 0))

    def _render_people(self) -> None:
        for child in self.people_holder.winfo_children():
            child.destroy()
        contacts = self.config.get("contacts", [])
        if not contacts:
            ctk.CTkLabel(self.people_holder, text="No contacts yet.", font=theme.FONT_SMALL,
                         text_color=theme.MUTED, anchor="w").grid(row=0, column=0, sticky="w")
        for i, c in enumerate(contacts):
            rowf = ctk.CTkFrame(self.people_holder, fg_color=theme.SIDEBAR, corner_radius=6)
            rowf.grid(row=i, column=0, sticky="ew", pady=1)
            rowf.grid_columnconfigure(0, weight=1)
            txt = f"{c.get('nickname','')}  <{c.get('email','')}>   ({c.get('role','')})"
            ctk.CTkLabel(rowf, text=txt, font=theme.FONT_SMALL, anchor="w").grid(row=0, column=0, sticky="w", padx=10, pady=6)
            ctk.CTkButton(rowf, text="✕", width=26, height=24, fg_color="transparent",
                          text_color=theme.DANGER, hover_color="#E4E8EE",
                          command=lambda idx=i: self._remove_person(idx)).grid(row=0, column=1, padx=6)

    def _add_person(self) -> None:
        nick = self.new_nick.get().strip()
        if not nick:
            return
        self.config.setdefault("contacts", []).append({
            "nickname": nick, "email": self.new_email.get().strip(), "role": self.new_role.get(),
        })
        self.app.save_config()
        for e in (self.new_nick, self.new_email):
            e.delete(0, "end")
        self._render_people()

    def _remove_person(self, idx) -> None:
        contacts = self.config.get("contacts", [])
        if 0 <= idx < len(contacts):
            contacts.pop(idx)
            self.app.save_config()
            self._render_people()

    # -- engineer seals --------------------------------------------------
    def _build_seals(self) -> None:
        card = self.card("Engineer seals", "Signature + seal images, applied only on 'Seal & Save'. Kept on this PC.")
        card.grid_columnconfigure(0, weight=1)
        self.seals_holder = ctk.CTkFrame(card, fg_color="transparent")
        self.seals_holder.grid(row=0, column=0, sticky="ew")
        self.seals_holder.grid_columnconfigure(0, weight=1)
        self._render_seals()
        form = ctk.CTkFrame(card, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        form.grid_columnconfigure(0, weight=1)
        self.seal_name = ctk.CTkEntry(form, height=30, placeholder_text="Engineer name (e.g. Jane Smith, PE)")
        self.seal_name.grid(row=0, column=0, sticky="ew")
        self._seal_sig = ctk.CTkEntry(form, height=30, placeholder_text="Signature image…")
        self._seal_sig.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.ghost_button(form, "Browse", lambda: self._pick_img(self._seal_sig), width=90).grid(row=1, column=1, padx=(6, 0))
        self._seal_img = ctk.CTkEntry(form, height=30, placeholder_text="Seal image…")
        self._seal_img.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        self.ghost_button(form, "Browse", lambda: self._pick_img(self._seal_img), width=90).grid(row=2, column=1, padx=(6, 0))
        self.ghost_button(form, "Add engineer", self._add_seal, width=140).grid(row=3, column=0, sticky="w", pady=(6, 0))

    def _pick_img(self, entry) -> None:
        path = self.pick_file("Choose an image", [("Images", "*.png *.jpg *.jpeg"), ("All files", "*.*")])
        if path:
            entry.delete(0, "end")
            entry.insert(0, path)

    def _render_seals(self) -> None:
        for child in self.seals_holder.winfo_children():
            child.destroy()
        seals = self.config.get("seals", [])
        if not seals:
            ctk.CTkLabel(self.seals_holder, text="No engineer seals yet.", font=theme.FONT_SMALL,
                         text_color=theme.MUTED, anchor="w").grid(row=0, column=0, sticky="w")
        for i, s in enumerate(seals):
            rowf = ctk.CTkFrame(self.seals_holder, fg_color=theme.SIDEBAR, corner_radius=6)
            rowf.grid(row=i, column=0, sticky="ew", pady=1)
            rowf.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(rowf, text=f"{s.get('name','')}  (sig + seal set)", font=theme.FONT_SMALL,
                         anchor="w").grid(row=0, column=0, sticky="w", padx=10, pady=6)
            ctk.CTkButton(rowf, text="✕", width=26, height=24, fg_color="transparent",
                          text_color=theme.DANGER, hover_color="#E4E8EE",
                          command=lambda idx=i: self._remove_seal(idx)).grid(row=0, column=1, padx=6)

    def _add_seal(self) -> None:
        name = self.seal_name.get().strip()
        if not name:
            return
        self.config.setdefault("seals", []).append({
            "name": name,
            "signature_image": self._seal_sig.get().strip(),
            "seal_image": self._seal_img.get().strip(),
        })
        if not self.config.get("default_engineer"):
            self.config["default_engineer"] = name
        self.app.save_config()
        for e in (self.seal_name, self._seal_sig, self._seal_img):
            e.delete(0, "end")
        self._render_seals()

    def _remove_seal(self, idx) -> None:
        seals = self.config.get("seals", [])
        if 0 <= idx < len(seals):
            seals.pop(idx)
            self.app.save_config()
            self._render_seals()

    # -- email -----------------------------------------------------------
    def _build_email(self) -> None:
        card = self.card("Boss's inbox monitoring", "Reads the classic Outlook desktop app locally — nothing leaves the PC.")
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Mailbox name", font=theme.FONT_BODY).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.mailbox_entry = ctk.CTkEntry(card, height=30)
        self.mailbox_entry.insert(0, self.config.get("email", {}).get("monitored_mailbox", ""))
        self.mailbox_entry.grid(row=0, column=1, sticky="ew", pady=4)

        self.urgent_box = self._kw_row(card, 1, "Urgent keywords", self.config.get("email", {}).get("urgent_keywords", []))
        self.rfp_box = self._kw_row(card, 2, "RFP / proposal keywords", self.config.get("email", {}).get("rfp_keywords", []))
        self.domains_box = self._kw_row(card, 3, "Client email domains", self.config.get("email", {}).get("client_domains", []))

        ctk.CTkLabel(card, text="Look back (days)", font=theme.FONT_BODY).grid(row=4, column=0, sticky="w", padx=(0, 8), pady=4)
        self.lookback_entry = ctk.CTkEntry(card, height=30, width=80)
        self.lookback_entry.insert(0, str(self.config.get("email", {}).get("lookback_days", 7)))
        self.lookback_entry.grid(row=4, column=1, sticky="w", pady=4)

    def _kw_row(self, parent, row, label, values):
        ctk.CTkLabel(parent, text=label, font=theme.FONT_BODY).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        e = ctk.CTkEntry(parent, height=30)
        e.insert(0, ", ".join(values))
        e.grid(row=row, column=1, sticky="ew", pady=4)
        return e

    # -- urls / company --------------------------------------------------
    def _build_urls_company(self) -> None:
        card = self.card("Websites & company")
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Monograph URL", font=theme.FONT_BODY).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.monograph_entry = ctk.CTkEntry(card, height=30)
        self.monograph_entry.insert(0, self.config.get("monograph_url", ""))
        self.monograph_entry.grid(row=0, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(card, text="OCE URL (localhost)", font=theme.FONT_BODY).grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.oce_entry = ctk.CTkEntry(card, height=30, placeholder_text="e.g. http://localhost:8080/")
        self.oce_entry.insert(0, self.config.get("oce_url", ""))
        self.oce_entry.grid(row=1, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(card, text="Company name", font=theme.FONT_BODY).grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        self.company_entry = ctk.CTkEntry(card, height=30)
        self.company_entry.insert(0, self.config.get("company", {}).get("name", ""))
        self.company_entry.grid(row=2, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(card, text="Invoice template (.docx)", font=theme.FONT_BODY).grid(row=3, column=0, sticky="w", padx=(0, 8), pady=4)
        self.invoice_tpl_entry = ctk.CTkEntry(card, height=30)
        self.invoice_tpl_entry.insert(0, self.config.get("invoice_template", ""))
        self.invoice_tpl_entry.grid(row=3, column=1, sticky="ew", pady=4)
        self.ghost_button(card, "Browse…", self._pick_invoice_tpl, width=90).grid(row=3, column=2, padx=(8, 0))

    def _pick_invoice_tpl(self) -> None:
        path = self.pick_file("Choose the invoice template", [("Word documents", "*.docx"), ("All files", "*.*")])
        if path:
            self.invoice_tpl_entry.delete(0, "end")
            self.invoice_tpl_entry.insert(0, path)

    # -- appearance ------------------------------------------------------
    def _build_appearance(self) -> None:
        card = self.card("Appearance")
        card.grid_columnconfigure(0, weight=1)
        self.appearance_menu = ctk.CTkOptionMenu(card, values=["light", "dark", "system"], width=160)
        self.appearance_menu.set(self.config.get("appearance", "light"))
        self.appearance_menu.grid(row=0, column=0, sticky="w")

    # -- save ------------------------------------------------------------
    def _build_save(self) -> None:
        card = self.card()
        card.grid_columnconfigure(0, weight=1)
        self.primary_button(card, "💾  Save settings", self.save, width=200).grid(row=0, column=0, sticky="w")
        self.saved_label = ctk.CTkLabel(card, text="", font=theme.FONT_SMALL, text_color=theme.SUCCESS)
        self.saved_label.grid(row=1, column=0, sticky="w", pady=(6, 0))

    def _split(self, text):
        return [t.strip() for t in text.replace("\n", ",").split(",") if t.strip()]

    def save(self) -> None:
        cfg = self.config
        cfg["base_folder"] = self.base_entry.get().strip()
        cfg["project_folder_pattern"] = self.pattern_entry.get().strip() or "{number} - {name}"
        cfg.setdefault("paths", {})
        for key, e in self.path_entries.items():
            cfg["paths"][key] = e.get().strip()
        cfg["folder_template"] = [ln.strip() for ln in self.template_box.get("1.0", "end").splitlines() if ln.strip()]
        cfg.setdefault("email", {})
        cfg["email"]["monitored_mailbox"] = self.mailbox_entry.get().strip()
        cfg["email"]["urgent_keywords"] = self._split(self.urgent_box.get())
        cfg["email"]["rfp_keywords"] = self._split(self.rfp_box.get())
        cfg["email"]["client_domains"] = self._split(self.domains_box.get())
        try:
            cfg["email"]["lookback_days"] = int(self.lookback_entry.get().strip() or 7)
        except ValueError:
            cfg["email"]["lookback_days"] = 7
        cfg["monograph_url"] = self.monograph_entry.get().strip()
        cfg["oce_url"] = self.oce_entry.get().strip()
        cfg.setdefault("company", {})["name"] = self.company_entry.get().strip()
        cfg["appearance"] = self.appearance_menu.get()

        self.app.save_config()
        self.app.reload_config()
        self.saved_label.configure(text="Saved. ✓")
        self.app.set_status("Settings saved.")

    def on_show(self) -> None:
        self._render_people()
