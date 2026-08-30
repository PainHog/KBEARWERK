"""Boss's Inbox monitor.

Reads her supervisor's mailbox through the classic Outlook desktop app (using the
access she already has) and flags anything that looks **urgent**, is from a
**client**, or is an **RFP / proposal request** - so those don't slip past while
he's busy. Nothing leaves the PC.

Off Windows (e.g. during development) it shows a friendly notice instead of
failing, so the rest of the app still runs.
"""

from __future__ import annotations

import customtkinter as ctk

from .. import theme
from .base import BasePanel
from ..services import outlook


REASON_COLORS = {
    "Urgent": theme.DANGER,
    "Client": theme.ACCENT,
    "RFP / Proposal": theme.SUCCESS,
}


class EmailMonitorPanel(BasePanel):
    title = "Boss's Inbox"
    subtitle = "Catch urgent, client and proposal emails before they slip."

    def build(self) -> None:
        self._build_controls()
        self._build_results()

    def _build_controls(self) -> None:
        card = self.card()
        card.grid_columnconfigure(0, weight=1)
        self.info_label = ctk.CTkLabel(card, text="", font=theme.FONT_BODY, anchor="w", justify="left")
        self.info_label.grid(row=0, column=0, sticky="w")
        self.primary_button(card, "🔄  Scan now", self.scan, width=140).grid(row=0, column=1, padx=(10, 0))

    def _build_results(self) -> None:
        card = self.card("Flagged emails")
        card.grid_columnconfigure(0, weight=1)
        self.results = ctk.CTkFrame(card, fg_color="transparent")
        self.results.grid(row=0, column=0, sticky="ew")
        self.results.grid_columnconfigure(0, weight=1)
        self._hint = ctk.CTkLabel(self.results, text="Click 'Scan now' to check the inbox.",
                                  font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w")
        self._hint.grid(row=0, column=0, sticky="w")

    def _mailbox(self):
        return self.config.get("email", {}).get("monitored_mailbox", "")

    def scan(self) -> None:
        for child in self.results.winfo_children():
            child.destroy()
        if not outlook.available():
            ctk.CTkLabel(
                self.results, justify="left", anchor="w", text_color=theme.MUTED, font=theme.FONT_BODY,
                text=("Email monitoring runs on her Windows PC with the classic Outlook "
                      "desktop app.\nIt's inactive on this machine, but will work there."),
            ).grid(row=0, column=0, sticky="w")
            return
        mailbox = self._mailbox()
        email_cfg = self.config.get("email", {})

        def work():
            return outlook.scan_inbox(
                mailbox=mailbox,
                urgent_keywords=email_cfg.get("urgent_keywords", []),
                rfp_keywords=email_cfg.get("rfp_keywords", []),
                client_domains=email_cfg.get("client_domains", []),
                lookback_days=email_cfg.get("lookback_days", 7),
            )

        self.run_async(work, self._render, busy=f"Scanning {mailbox or 'inbox'}…")

    def _render(self, items) -> None:
        for child in self.results.winfo_children():
            child.destroy()
        if not items:
            ctk.CTkLabel(self.results, text="Nothing flagged in the look-back window. 🎉",
                         font=theme.FONT_BODY, text_color=theme.SUCCESS, anchor="w").grid(
                row=0, column=0, sticky="w")
            self.app.set_status("Scan complete — nothing flagged.")
            return
        self.app.set_status(f"Scan complete — {len(items)} flagged.")
        for i, item in enumerate(items):
            self._email_row(i, item)

    def _email_row(self, i, item) -> None:
        row = ctk.CTkFrame(self.results, fg_color=theme.SIDEBAR, corner_radius=8)
        row.grid(row=i, column=0, sticky="ew", pady=3)
        row.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(row, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 2))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, text=item.subject or "(no subject)", font=theme.FONT_CARD_TITLE, anchor="w").grid(
            row=0, column=0, sticky="w")
        badges = ctk.CTkFrame(top, fg_color="transparent")
        badges.grid(row=0, column=1, sticky="e")
        for reason in item.reasons:
            ctk.CTkLabel(badges, text=f" {reason} ", font=theme.FONT_SMALL, text_color="#FFFFFF",
                         fg_color=REASON_COLORS.get(reason, theme.MUTED), corner_radius=6).pack(side="left", padx=2)

        when = item.received.strftime("%m/%d %I:%M %p") if item.received else ""
        ctk.CTkLabel(row, text=f"From: {item.sender}  ·  {when}", font=theme.FONT_SMALL,
                     text_color=theme.MUTED, anchor="w").grid(row=1, column=0, sticky="w", padx=12)
        if item.preview:
            ctk.CTkLabel(row, text=item.preview, font=theme.FONT_SMALL, text_color=theme.MUTED,
                         anchor="w", wraplength=760, justify="left").grid(row=2, column=0, sticky="w", padx=12, pady=(0, 8))

    def on_show(self) -> None:
        mailbox = self._mailbox() or "(not set — add the boss's mailbox in Settings)"
        look = self.config.get("email", {}).get("lookback_days", 7)
        self.info_label.configure(text=f"Watching: {mailbox}\nLooking back {look} day(s).")
