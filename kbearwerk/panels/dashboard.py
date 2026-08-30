"""Home dashboard.

Three jobs:
1. **Find a job fast** - the big search box (her boss-just-asked lifesaver).
2. **See what she got done** - today/this-week counts, because the admin grind is
   invisible and she deserves to see the wins.
3. Quick actions, recent activity, and setup/sync status.
"""

from __future__ import annotations

import datetime
import os

import customtkinter as ctk

from .. import theme
from .base import BasePanel
from ..services import search, files, activity, outbox, produced, syncstatus


def _first(row, keys):
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for key in keys:
        v = lowered.get(key.lower())
        if v not in (None, ""):
            return str(v)
    return ""


class DashboardPanel(BasePanel):
    title = "Home"
    subtitle = "Find any job fast — and see everything you've gotten done."

    def build(self) -> None:
        self._build_search()
        self._build_accomplishments()
        self._build_quick_actions()
        self._build_recent()
        self._build_setup_status()

    # -- search ----------------------------------------------------------
    def _build_search(self) -> None:
        card = self.card(
            "Find a job",
            "Type anything — client, address, contractor, job number. You get matching jobs "
            "from your lists AND every folder/file on the drive, ready to open.",
        )
        card.grid_columnconfigure(0, weight=1)
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew")
        row.grid_columnconfigure(0, weight=1)
        self.search_entry = ctk.CTkEntry(row, height=44, font=("Segoe UI", 16),
                                         placeholder_text="Type an address, client, contractor…")
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<Return>", lambda _e: self.do_search())
        self.primary_button(row, "Search", self.do_search, width=110, height=44).grid(row=0, column=1, padx=(10, 0))

        self.results = ctk.CTkFrame(card, fg_color="transparent")
        self.results.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.results.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.results, text="Results will appear here.", font=theme.FONT_SMALL,
                     text_color=theme.MUTED, anchor="w").grid(row=0, column=0, sticky="w")

    def do_search(self) -> None:
        query = self.search_entry.get().strip()
        for child in self.results.winfo_children():
            child.destroy()
        if not query:
            return

        def work():
            return (search.search(self.config, query),
                    search.search_files(self.config, query),
                    search.search_templates(self.config, query))
        self.run_async(work, self._render_results, busy=f"Searching for '{query}'…")

    def _render_results(self, result) -> None:
        hits, file_hits, tpl_hits = result
        for child in self.results.winfo_children():
            child.destroy()
        if not hits and not file_hits and not tpl_hits:
            ctk.CTkLabel(self.results,
                         text="No matches. Set your work folder and lists in Settings so search can find things.",
                         font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w").grid(row=0, column=0, sticky="w")
            self.app.set_status("No matches found.")
            return
        self.app.set_status(f"Found {len(tpl_hits)} document(s), {len(hits)} job(s), {len(file_hits)} file(s)/folder(s).")

        r = 0
        if tpl_hits:
            ctk.CTkLabel(self.results, text="Documents to generate", font=theme.FONT_CARD_TITLE,
                         anchor="w").grid(row=r, column=0, sticky="w", pady=(2, 4)); r += 1
            for tpl in tpl_hits:
                self._template_row(r, tpl); r += 1
        if hits:
            ctk.CTkLabel(self.results, text="Jobs (from your lists)", font=theme.FONT_CARD_TITLE,
                         anchor="w").grid(row=r, column=0, sticky="w", pady=(2, 4)); r += 1
            for hit in hits:
                self._result_row(r, hit); r += 1
        if file_hits:
            ctk.CTkLabel(self.results, text="Files & folders on the drive", font=theme.FONT_CARD_TITLE,
                         anchor="w").grid(row=r, column=0, sticky="w", pady=(12, 4)); r += 1
            shown = file_hits[:60]
            for fh in shown:
                self._file_row(r, fh); r += 1
            if len(file_hits) > len(shown):
                ctk.CTkLabel(self.results, text=f"…and {len(file_hits) - len(shown)} more. Narrow the search to see them.",
                             font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w").grid(row=r, column=0, sticky="w"); r += 1

    def _file_row(self, i, fh) -> None:
        row = ctk.CTkFrame(self.results, fg_color=theme.SIDEBAR, corner_radius=8)
        row.grid(row=i, column=0, sticky="ew", pady=2)
        row.grid_columnconfigure(0, weight=1)
        icon = "📁" if fh.is_dir else "📄"
        text = ctk.CTkFrame(row, fg_color="transparent")
        text.grid(row=0, column=0, sticky="w", padx=12, pady=6)
        ctk.CTkLabel(text, text=f"{icon}  {fh.name}", font=theme.FONT_BODY, anchor="w").pack(anchor="w")
        sub = fh.job if fh.job else fh.path
        ctk.CTkLabel(text, text=sub, font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w").pack(anchor="w")

        btns = ctk.CTkFrame(row, fg_color="transparent")
        btns.grid(row=0, column=1, sticky="e", padx=10)
        if fh.is_dir:
            self.accent_button(btns, "Open Folder", lambda p=fh.path: self._open_folder(p), width=110).pack(side="right", padx=4)
        else:
            self.accent_button(btns, "Open File", lambda p=fh.path: self._open_folder(p), width=100).pack(side="right", padx=4)
            self.ghost_button(btns, "Folder", lambda p=fh.path: self._open_folder(os.path.dirname(p)), width=80).pack(side="right", padx=4)

    def _result_row(self, i, hit) -> None:
        row = ctk.CTkFrame(self.results, fg_color=theme.SIDEBAR, corner_radius=8)
        row.grid(row=i, column=0, sticky="ew", pady=3)
        row.grid_columnconfigure(0, weight=1)
        text = ctk.CTkFrame(row, fg_color="transparent")
        text.grid(row=0, column=0, sticky="w", padx=12, pady=8)
        ctk.CTkLabel(text, text=hit.title, font=theme.FONT_CARD_TITLE, anchor="w").pack(anchor="w")
        if hit.subtitle:
            ctk.CTkLabel(text, text=hit.subtitle, font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w").pack(anchor="w")
        ctk.CTkLabel(text, text=f"in {hit.source}", font=theme.FONT_SMALL, text_color=theme.ACCENT, anchor="w").pack(anchor="w")

        btns = ctk.CTkFrame(row, fg_color="transparent")
        btns.grid(row=0, column=1, sticky="e", padx=10)
        self.accent_button(btns, "Open Job", lambda h=hit: self._open_job(h), width=100).pack(side="right", padx=4)
        if hit.folder:
            self.ghost_button(btns, "Folder", lambda f=hit.folder: self._open_folder(f), width=80).pack(side="right", padx=4)

    def _open_job(self, hit) -> None:
        row = hit.row
        ctx = {
            "number": _first(row, ["project number", "project no", "job number", "job #", "number"]),
            "name": _first(row, ["project name", "job name", "project", "name"]),
            "client": _first(row, ["client", "client name", "owner"]),
            "address": _first(row, ["address", "project address", "location"]),
            "contractor": _first(row, ["contractor", "general contractor", "gc"]),
            "row": row, "folder": hit.folder or "",
        }
        self.app.open_job(ctx)

    def _open_folder(self, folder) -> None:
        try:
            files.open_in_file_manager(folder)
        except Exception as exc:  # noqa: BLE001
            self.show_error(str(exc))

    def _template_row(self, i, tpl) -> None:
        row = ctk.CTkFrame(self.results, fg_color=theme.SIDEBAR, corner_radius=8)
        row.grid(row=i, column=0, sticky="ew", pady=2)
        row.grid_columnconfigure(0, weight=1)
        text = ctk.CTkFrame(row, fg_color="transparent")
        text.grid(row=0, column=0, sticky="w", padx=12, pady=6)
        ctk.CTkLabel(text, text=f"📝  {tpl.name}", font=theme.FONT_BODY, anchor="w").pack(anchor="w")
        ctk.CTkLabel(text, text="blank template — fill & generate", font=theme.FONT_SMALL,
                     text_color=theme.MUTED, anchor="w").pack(anchor="w")
        btns = ctk.CTkFrame(row, fg_color="transparent")
        btns.grid(row=0, column=1, sticky="e", padx=10)
        self.accent_button(btns, "Generate", lambda n=tpl.name: self.app.open_template(n), width=100).pack(side="right", padx=4)
        if tpl.path:
            self.ghost_button(btns, "Open blank", lambda p=tpl.path: self._open_folder(p), width=100).pack(side="right", padx=4)

    # -- accomplishments -------------------------------------------------
    def _build_accomplishments(self) -> None:
        today = datetime.date.today().strftime("%A, %B %d")
        self.acc_card = self.card("Your work", f"What you've gotten done — {today}.")
        self.acc_card.grid_columnconfigure(0, weight=1)
        self.acc_holder = ctk.CTkFrame(self.acc_card, fg_color="transparent")
        self.acc_holder.grid(row=0, column=0, sticky="ew")
        self._render_accomplishments()

    def _render_accomplishments(self) -> None:
        for child in self.acc_holder.winfo_children():
            child.destroy()
        today = activity.counts_today()
        week = activity.counts_week()
        tiles = ctk.CTkFrame(self.acc_holder, fg_color="transparent")
        tiles.pack(fill="x")
        for i, action in enumerate(activity.TILE_ACTIONS):
            tiles.grid_columnconfigure(i, weight=1)
            box = ctk.CTkFrame(tiles, fg_color=theme.SIDEBAR, corner_radius=10)
            box.grid(row=0, column=i, sticky="ew", padx=4, pady=2)
            ctk.CTkLabel(box, text=str(today.get(action, 0)), font=("Segoe UI Semibold", 26),
                         text_color=theme.PRIMARY).pack(pady=(10, 0))
            ctk.CTkLabel(box, text=action, font=theme.FONT_SMALL, text_color=theme.MUTED,
                         wraplength=120).pack()
            ctk.CTkLabel(box, text=f"{week.get(action, 0)} this week", font=("Segoe UI", 10),
                         text_color=theme.ACCENT).pack(pady=(0, 10))
        total_today = sum(today.values())
        if total_today:
            ctk.CTkLabel(self.acc_holder,
                         text=f"That's {total_today} thing(s) handled today. Nice work. 💪",
                         font=theme.FONT_BODY, text_color=theme.SUCCESS, anchor="w").pack(anchor="w", pady=(8, 0))
        else:
            ctk.CTkLabel(self.acc_holder,
                         text="Nothing logged yet today — as you work, your wins show up here.",
                         font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w").pack(anchor="w", pady=(8, 0))

    # -- quick actions ---------------------------------------------------
    def _build_quick_actions(self) -> None:
        card = self.card("Quick actions")
        card.grid_columnconfigure((0, 1, 2, 3), weight=1)
        actions = [
            ("🆕  New Project", "new_project"),
            ("📄  Make a Document", "documents"),
            ("🖊  Process a Redline", "redlines"),
            ("📥  Check Boss's Inbox", "email"),
        ]
        for i, (label, key) in enumerate(actions):
            self.accent_button(card, label, lambda k=key: self.app.show_panel(k)).grid(
                row=0, column=i, sticky="ew", padx=4, pady=4)

    # -- recent activity -------------------------------------------------
    def _build_recent(self) -> None:
        self.recent_card = self.collapsible_card("Recent activity", collapsed=True)
        self.recent_card.grid_columnconfigure(0, weight=1)
        self.recent_holder = ctk.CTkFrame(self.recent_card, fg_color="transparent")
        self.recent_holder.grid(row=0, column=0, sticky="ew")
        self._render_recent()

    def _render_recent(self) -> None:
        for child in self.recent_holder.winfo_children():
            child.destroy()
        items = activity.recent(8)
        if not items:
            ctk.CTkLabel(self.recent_holder, text="No activity yet.", font=theme.FONT_SMALL,
                         text_color=theme.MUTED, anchor="w").grid(row=0, column=0, sticky="w")
            return
        for i, it in enumerate(items):
            when = datetime.datetime.fromtimestamp(it.get("when", 0)).strftime("%m/%d %I:%M %p")
            label = it.get("action", "")
            if it.get("project"):
                label += f" · {it['project']}"
            if it.get("details"):
                label += f" · {it['details']}"
            ctk.CTkLabel(self.recent_holder, text=f"{when}   {label}", font=theme.FONT_SMALL,
                         anchor="w").grid(row=i, column=0, sticky="w", pady=1)

    # -- setup / sync ----------------------------------------------------
    def _build_setup_status(self) -> None:
        self.status_card = self.collapsible_card("Setup & sync", "Point the app at her real folders and lists.", collapsed=True)
        self.status_card.grid_columnconfigure(0, weight=1)
        self._status_rows = ctk.CTkFrame(self.status_card, fg_color="transparent")
        self._status_rows.grid(row=0, column=0, sticky="ew")
        self._status_rows.grid_columnconfigure(0, weight=1)
        btns = ctk.CTkFrame(self.status_card, fg_color="transparent")
        btns.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.ghost_button(btns, "Open Settings", lambda: self.app.show_panel("settings"), width=140).pack(side="left")
        self.sync_button = self.ghost_button(btns, "Sync now", self._sync_now, width=110)
        self.sync_button.pack(side="left", padx=8)
        self._refresh_status()

    def _sync_now(self) -> None:
        res = self.app.flush_outbox()
        self._refresh_status()
        self.show_info(f"Synced {res['done']} item(s). {res['pending']} still waiting for the cloud.",
                       title="Sync")

    def _refresh_status(self) -> None:
        for child in self._status_rows.winfo_children():
            child.destroy()
        cfg = self.config
        paths = cfg.get("paths", {})
        checks = [
            ("Work folder set", bool(cfg.get("base_folder"))),
            ("Project List file set", bool(paths.get("project_list"))),
            ("Proposal List file set", bool(paths.get("proposal_list"))),
            ("Weekly Worksheet file set", bool(paths.get("weekly_worksheet"))),
            ("People / contacts added", bool(cfg.get("contacts") or cfg.get("drafters") or cfg.get("inspectors"))),
            ("Boss's mailbox set", bool(cfg.get("email", {}).get("monitored_mailbox"))),
        ]
        for i, (label, ok) in enumerate(checks):
            mark = "✓" if ok else "○"
            color = theme.SUCCESS if ok else theme.MUTED
            ctk.CTkLabel(self._status_rows, text=f"{mark}  {label}", font=theme.FONT_BODY,
                         text_color=color, anchor="w").grid(row=i, column=0, sticky="w", pady=2)
        pend = outbox.pending_count()
        pend_txt = (f"⏳  {pend} item(s) saved locally, waiting to sync to the cloud"
                    if pend else "✓  Nothing waiting to sync")
        ctk.CTkLabel(self._status_rows, text=pend_txt, font=theme.FONT_BODY,
                     text_color=(theme.WARNING if pend else theme.SUCCESS), anchor="w").grid(
            row=len(checks), column=0, sticky="w", pady=(6, 2))

        # Recent documents with their live sync marker (✓ synced / ☁ on PC / ✗).
        docs = produced.recent(6)
        if docs:
            ctk.CTkLabel(self._status_rows, text="Recent documents", font=theme.FONT_CARD_TITLE,
                         anchor="w").grid(row=len(checks) + 1, column=0, sticky="w", pady=(8, 2))
            for j, d in enumerate(docs):
                state = syncstatus.file_state(d.get("path", ""))
                color = {syncstatus.SYNCED: theme.SUCCESS, syncstatus.ON_DEVICE: theme.ACCENT,
                         syncstatus.PENDING: theme.WARNING, syncstatus.MISSING: theme.DANGER}.get(state, theme.MUTED)
                name = os.path.basename(d.get("path", "")) or d.get("label", "")
                ctk.CTkLabel(self._status_rows,
                             text=f"{syncstatus.icon(state)}  {name}   ({syncstatus.label(state)})",
                             font=theme.FONT_SMALL, text_color=color, anchor="w").grid(
                    row=len(checks) + 2 + j, column=0, sticky="w", pady=1)

    def on_show(self) -> None:
        self._refresh_status()
        self._render_accomplishments()
        self._render_recent()
