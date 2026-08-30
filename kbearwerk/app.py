"""Main application window: navigation sidebar + swappable panels + status bar."""

from __future__ import annotations

import re
import threading

import customtkinter as ctk

from . import config as config_mod
from . import theme
from .version import APP_TITLE, __version__
from .services import outlook, outbox

from .panels.dashboard import DashboardPanel
from .panels.new_project import NewProjectPanel
from .panels.job import JobWorkspacePanel
from .panels.documents import DocumentsPanel
from .panels.jobs_list import ProjectListPanel
from .panels.redlines import RedlinesPanel
from .panels.email_monitor import EmailMonitorPanel
from .panels.observations import ObservationsPanel
from .panels.needed import NeededPanel
from .panels.meeting_checklist import MeetingChecklistPanel
from .panels.schedule import SchedulePanel
from .panels.billing import BillingPanel
from .panels.settings import SettingsPanel

# Optional real OS drag-and-drop (bundled with the .exe). Degrades gracefully.
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _DND_AVAILABLE = True
except Exception:
    _DND_AVAILABLE = False

# (key, sidebar label, emoji, panel class)
NAV = [
    ("dashboard", "Home", "\U0001F3E0", DashboardPanel),
    ("job", "Open a Job", "\U0001F4C2", JobWorkspacePanel),
    ("new_project", "New Project", "\U0001F195", NewProjectPanel),
    ("documents", "Documents", "\U0001F4C4", DocumentsPanel),
    ("project_list", "Project List", "\U0001F4CB", ProjectListPanel),
    ("redlines", "Redlines", "\U0001F58A", RedlinesPanel),
    ("email", "Boss's Inbox", "\U0001F4E5", EmailMonitorPanel),
    ("observations", "Observations", "\U0001F50D", ObservationsPanel),
    ("needed", "Needed", "\U0001F4CC", NeededPanel),
    ("billing", "Billing", "\U0001F4B5", BillingPanel),
    ("meeting", "Meeting Checklist", "✅", MeetingChecklistPanel),
    ("schedule", "Schedule", "\U0001F4C5", SchedulePanel),
    ("settings", "Settings", "⚙️", SettingsPanel),
]

_NAV_CLASS = {k: c for k, _l, _e, c in NAV}


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config_data = config_mod.load()
        theme.apply(self.config_data.get("appearance", "light"))

        # Enable OS drag-and-drop on the whole app if the library loaded.
        self._dnd_ok = False
        if _DND_AVAILABLE:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
                self._dnd_ok = True
            except Exception:
                self._dnd_ok = False

        self.current_job = None  # set by open_job(), read by the Job panel

        self.title(APP_TITLE)
        self.geometry("1180x760")
        self.minsize(980, 640)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._panels = {}
        self._nav_buttons = {}
        self._current = None

        self._build_sidebar()
        self._build_content()
        self._build_statusbar()

        self.show_panel("dashboard")
        self.after(300, self._refresh_env_label)
        self.after(800, self._startup_sync)

    # -- sidebar ---------------------------------------------------------
    def _build_sidebar(self) -> None:
        bar = ctk.CTkFrame(self, width=224, corner_radius=0, fg_color=theme.SIDEBAR)
        bar.grid(row=0, column=0, sticky="nsw")
        bar.grid_rowconfigure(len(NAV) + 1, weight=1)
        bar.grid_propagate(False)

        ctk.CTkLabel(bar, text="KBEARWERK", font=("Segoe UI Semibold", 19),
                     text_color=theme.PRIMARY).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 0))
        ctk.CTkLabel(bar, text="Office Assistant", font=theme.FONT_SMALL,
                     text_color=theme.MUTED).grid(row=0, column=0, sticky="w", padx=18, pady=(44, 0))

        for i, (key, label, emoji, _cls) in enumerate(NAV, start=1):
            btn = ctk.CTkButton(
                bar, text=f"  {emoji}   {label}", anchor="w",
                font=theme.FONT_NAV, height=36, corner_radius=8,
                fg_color="transparent", text_color=("#1F2937", "#E5E7EB"),
                hover_color=("#E4E8EE", "#2C2F33"),
                command=lambda k=key: self.show_panel(k),
            )
            btn.grid(row=i, column=0, sticky="ew", padx=10, pady=1)
            self._nav_buttons[key] = btn

        ctk.CTkLabel(bar, text=f"v{__version__}", font=theme.FONT_SMALL,
                     text_color=theme.MUTED).grid(row=len(NAV) + 2, column=0, sticky="w", padx=18, pady=(0, 12))

    def _build_content(self) -> None:
        self.content = ctk.CTkFrame(self, fg_color=theme.PAGE_BG, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

    def _build_statusbar(self) -> None:
        bar = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color=theme.SIDEBAR)
        bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)
        self._status = ctk.CTkLabel(bar, text="Ready.", font=theme.FONT_SMALL,
                                    text_color=theme.MUTED, anchor="w")
        self._status.grid(row=0, column=0, sticky="w", padx=14, pady=2)
        self._env = ctk.CTkLabel(bar, text="", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="e")
        self._env.grid(row=0, column=1, sticky="e", padx=14, pady=2)

    def _refresh_env_label(self) -> None:
        base = self.config_data.get("base_folder") or "no work folder set"
        mail = "Outlook: on" if outlook.available() else "Outlook: off (Windows only)"
        pend = outbox.pending_count()
        pend_txt = f"    |    Pending sync: {pend}" if pend else ""
        self._env.configure(text=f"{mail}    |    Work folder: {base}{pend_txt}")

    # -- panel switching -------------------------------------------------
    def show_panel(self, key: str) -> None:
        if key not in self._panels:
            self._panels[key] = _NAV_CLASS[key](self.content, self)
        if self._current is not None and self._current in self._panels:
            self._panels[self._current].grid_forget()
        panel = self._panels[key]
        panel.grid(row=0, column=0, sticky="nsew")
        self._current = key
        self._update_nav_highlight(key)
        if hasattr(panel, "on_show"):
            panel.on_show()

    def _update_nav_highlight(self, active: str) -> None:
        for key, btn in self._nav_buttons.items():
            if key == active:
                btn.configure(fg_color=theme.PRIMARY, text_color="#FFFFFF", hover_color=theme.PRIMARY_HOVER)
            else:
                btn.configure(fg_color="transparent", text_color=("#1F2937", "#E5E7EB"),
                              hover_color=("#E4E8EE", "#2C2F33"))

    def open_job(self, context: dict) -> None:
        """Open the Job workspace on a specific job (used by Home search)."""
        self.current_job = context
        self.show_panel("job")

    # -- drag and drop ---------------------------------------------------
    def register_drop(self, widget, callback) -> None:
        """Make ``widget`` accept a dropped file, calling ``callback(path)``.

        No-op when drag-and-drop isn't available, so panels can always call this.
        """
        if not self._dnd_ok:
            return
        try:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", lambda e: self._on_drop(e, callback))
        except Exception:
            pass

    def _on_drop(self, event, callback) -> None:
        paths = self._parse_dnd(getattr(event, "data", "") or "")
        if paths:
            callback(paths[0])

    @staticmethod
    def _parse_dnd(data: str):
        # Tk gives paths with spaces wrapped in {braces}.
        return [m[1:-1] if m.startswith("{") else m
                for m in re.findall(r"\{[^}]*\}|\S+", data)]

    # -- shared services for panels -------------------------------------
    def set_status(self, text: str) -> None:
        self._status.configure(text=text)

    def save_config(self) -> None:
        config_mod.save(self.config_data)
        self._refresh_env_label()

    def reload_config(self) -> None:
        theme.apply(self.config_data.get("appearance", "light"))
        self._refresh_env_label()
        if self._current and self._current in self._panels:
            self._panels[self._current].on_show()

    # -- background sync -------------------------------------------------
    def _bg(self, work, on_done=None) -> None:
        def runner():
            try:
                result = work()
            except Exception:
                return
            if on_done:
                self.after(0, lambda: on_done(result))
        threading.Thread(target=runner, daemon=True).start()

    def _startup_sync(self) -> None:
        if outbox.pending_count() == 0:
            return

        def done(res):
            self._refresh_env_label()
            if res.get("done"):
                self.set_status(f"Synced {res['done']} pending item(s) that were saved locally.")
        self._bg(outbox.flush, done)

    def flush_outbox(self):
        res = outbox.flush()
        self._refresh_env_label()
        self.set_status(f"Sync: {res['done']} sent, {res['pending']} still pending.")
        return res


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
