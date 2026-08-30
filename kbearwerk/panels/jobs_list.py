"""Project List panel - a searchable table of every project.

Loads her Project List (and optionally Proposal List) spreadsheet and shows it as
a filterable table. Type in the filter box to narrow across every column; select a
row and open its folder.
"""

from __future__ import annotations

from tkinter import ttk

import customtkinter as ctk

from .. import theme
from .base import BasePanel
from ..services import excel, files


class ProjectListPanel(BasePanel):
    title = "Project List"
    subtitle = "Search and browse every project."

    def build(self) -> None:
        self._all_rows = []
        self._headers = []
        self._which = "project_list"
        self._build_controls()
        self._build_table()

    def _build_controls(self) -> None:
        card = self.card()
        card.grid_columnconfigure(1, weight=1)
        self.source_menu = ctk.CTkOptionMenu(
            card, values=["Project List", "Proposal List"], width=150,
            command=self._on_source_change,
        )
        self.source_menu.grid(row=0, column=0, padx=(0, 10))
        self.filter_entry = ctk.CTkEntry(card, height=34, placeholder_text="Filter (address, client, contractor…)")
        self.filter_entry.grid(row=0, column=1, sticky="ew")
        self.filter_entry.bind("<KeyRelease>", lambda _e: self._apply_filter())
        self.ghost_button(card, "Refresh", self.reload, width=90).grid(row=0, column=2, padx=(10, 0))
        self.accent_button(card, "Open Folder", self.open_selected, width=120).grid(row=0, column=3, padx=(8, 0))
        self.count_label = ctk.CTkLabel(card, text="", font=theme.FONT_SMALL, text_color=theme.MUTED)
        self.count_label.grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 0))

    def _build_table(self) -> None:
        card = self.card()
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)
        holder = ctk.CTkFrame(card, fg_color="transparent", height=420)
        holder.grid(row=0, column=0, sticky="nsew")
        holder.grid_columnconfigure(0, weight=1)
        holder.grid_rowconfigure(0, weight=1)

        theme.style_treeview(ttk.Style(), "KB.Treeview")
        self.tree = ttk.Treeview(holder, show="headings", style="KB.Treeview", height=16)
        vsb = ttk.Scrollbar(holder, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(holder, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

    # -- data ------------------------------------------------------------
    def _path(self) -> str:
        return self.config.get("paths", {}).get(self._which, "")

    def _on_source_change(self, label) -> None:
        self._which = "proposal_list" if label == "Proposal List" else "project_list"
        self.reload()

    def reload(self) -> None:
        path = self._path()
        if not path:
            self._all_rows = []
            self._headers = []
            self._render([])
            self.count_label.configure(text="No file set for this list. Add it in Settings → File locations.")
            return

        def work():
            return excel.read_rows(path)

        def done(rows):
            self._all_rows = rows
            self._headers = list(rows[0].keys()) if rows else []
            self._configure_columns()
            self._apply_filter()

        self.run_async(work, done, on_error=self._load_error, busy="Loading list…")

    def _load_error(self, exc) -> None:
        self._all_rows = []
        self._render([])
        self.count_label.configure(text=str(exc).splitlines()[0])

    def _configure_columns(self) -> None:
        self.tree["columns"] = self._headers
        for h in self._headers:
            self.tree.heading(h, text=h)
            self.tree.column(h, width=max(90, min(240, len(h) * 12)), anchor="w")

    def _apply_filter(self) -> None:
        q = self.filter_entry.get().strip().lower()
        if not q:
            rows = self._all_rows
        else:
            rows = [r for r in self._all_rows
                    if any(v is not None and q in str(v).lower() for v in r.values())]
        self._render(rows)
        self.count_label.configure(text=f"{len(rows)} of {len(self._all_rows)} shown")

    def _render(self, rows) -> None:
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=[r.get(h, "") for h in self._headers])

    def open_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            self.app.set_status("Select a row first.")
            return
        values = self.tree.item(sel[0], "values")
        row = dict(zip(self._headers, values))
        base = self.config.get("base_folder", "")
        number = _first(row, ["Project Number", "Project No", "Job Number", "Job #", "Number"])
        name = _first(row, ["Project Name", "Job Name", "Project", "Name"])
        folder = files.find_project_folder(base, number, name)
        if not folder:
            self.show_error("Couldn't find a matching folder for this project under the work folder.")
            return
        try:
            files.open_in_file_manager(folder)
        except Exception as exc:  # noqa: BLE001
            self.show_error(str(exc))

    def on_show(self) -> None:
        self.reload()


def _first(row, keys):
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for key in keys:
        v = lowered.get(key.lower())
        if v not in (None, ""):
            return str(v)
    return ""
