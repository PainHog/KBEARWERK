"""Read and send email through the classic Outlook desktop app (Windows only).

This talks to Outlook via COM automation (``win32com``). The big advantages:

* It uses the mailboxes she is **already signed into** in Outlook - including her
  boss's mailbox if he has shared/delegated it to her - so there are no
  passwords to enter and nothing is sent to any outside service.
* It works with both Microsoft 365 and on-premises Exchange.

Everything here degrades safely off Windows (or when Outlook isn't installed):
:func:`available` returns ``False`` and the panels show a friendly notice instead
of crashing, so the rest of the app still runs during development on Linux.
"""

from __future__ import annotations

import datetime as _dt
import sys
from dataclasses import dataclass, field
from typing import List, Optional

# Outlook MailItem body-format / item constants (avoid importing the type lib).
OL_FOLDER_INBOX = 6


def available() -> bool:
    """True only on Windows with pywin32 importable."""
    if sys.platform != "win32":
        return False
    try:
        import win32com.client  # noqa: F401
        return True
    except Exception:
        return False


class OutlookError(Exception):
    """A user-friendly Outlook problem."""


def _dispatch():
    if sys.platform != "win32":
        raise OutlookError(
            "Email features run on the office Windows PC with the classic "
            "Outlook desktop app. They're inactive here."
        )
    try:
        import win32com.client
        return win32com.client.Dispatch("Outlook.Application")
    except Exception as exc:  # pragma: no cover - Windows only
        raise OutlookError(
            "Couldn't connect to Outlook. Make sure the classic Outlook desktop "
            f"app is installed and open, then try again.\n\n({exc})"
        )


def _namespace():
    app = _dispatch()
    return app.GetNamespace("MAPI")


@dataclass
class Mailbox:
    name: str


@dataclass
class FlaggedEmail:
    subject: str
    sender: str
    sender_email: str
    received: Optional[_dt.datetime]
    reasons: List[str] = field(default_factory=list)
    preview: str = ""
    entry_id: str = ""


def list_mailboxes() -> List[str]:
    """Names of every mailbox/store currently loaded in Outlook."""
    ns = _namespace()
    names: List[str] = []
    try:
        for folder in ns.Folders:
            names.append(str(folder.Name))
    except Exception as exc:  # pragma: no cover - Windows only
        raise OutlookError(f"Couldn't list Outlook mailboxes.\n\n({exc})")
    return names


def _resolve_inbox(ns, mailbox: str):
    """Return the Inbox folder for the named mailbox, or the default inbox."""
    if mailbox:
        for folder in ns.Folders:
            if str(folder.Name).strip().lower() == mailbox.strip().lower():
                for sub in folder.Folders:
                    if str(sub.Name).strip().lower() == "inbox":
                        return sub
                return folder  # fall back to the store root
    return ns.GetDefaultFolder(OL_FOLDER_INBOX)


def scan_inbox(
    mailbox: str,
    urgent_keywords: List[str],
    rfp_keywords: List[str],
    client_domains: List[str],
    lookback_days: int = 7,
    max_items: int = 300,
) -> List[FlaggedEmail]:
    """Scan a mailbox's inbox and return messages that match any rule.

    A message is flagged if its subject/body contains an urgent or RFP keyword,
    or if the sender's domain is in ``client_domains``.
    """
    ns = _namespace()
    inbox = _resolve_inbox(ns, mailbox)
    try:
        items = inbox.Items
        items.Sort("[ReceivedTime]", True)  # newest first
    except Exception as exc:  # pragma: no cover - Windows only
        raise OutlookError(f"Couldn't read that inbox.\n\n({exc})")

    cutoff = _dt.datetime.now() - _dt.timedelta(days=max(lookback_days, 1))
    urgent = [k.lower() for k in urgent_keywords if k]
    rfp = [k.lower() for k in rfp_keywords if k]
    domains = [d.lower().lstrip("@") for d in client_domains if d]

    flagged: List[FlaggedEmail] = []
    count = 0
    for item in items:
        count += 1
        if count > max_items:
            break
        try:
            if getattr(item, "Class", 43) != 43:  # 43 == MailItem
                continue
            received = item.ReceivedTime
            recv_dt = _dt.datetime(received.year, received.month, received.day,
                                   received.hour, received.minute, received.second)
            if recv_dt < cutoff:
                break  # sorted newest-first, so we can stop
            subject = str(item.Subject or "")
            body = str(getattr(item, "Body", "") or "")[:2000]
            sender = str(getattr(item, "SenderName", "") or "")
            sender_email = str(getattr(item, "SenderEmailAddress", "") or "")
            haystack = f"{subject}\n{body}".lower()

            reasons: List[str] = []
            if any(k in haystack for k in urgent):
                reasons.append("Urgent")
            if any(k in haystack for k in rfp):
                reasons.append("RFP / Proposal")
            if domains and any(d in sender_email.lower() for d in domains):
                reasons.append("Client")

            if reasons:
                flagged.append(FlaggedEmail(
                    subject=subject,
                    sender=sender,
                    sender_email=sender_email,
                    received=recv_dt,
                    reasons=reasons,
                    preview=body.strip().replace("\r", " ").replace("\n", " ")[:180],
                    entry_id=str(getattr(item, "EntryID", "")),
                ))
        except Exception:
            continue  # one bad item shouldn't stop the scan
    return flagged


def create_email(
    to: str,
    subject: str,
    body: str,
    attachments: Optional[List[str]] = None,
    send: bool = False,
) -> None:
    """Create an Outlook email (as a draft she can review, or sent directly).

    Default is to *display* a draft so she always gets to review before sending.
    """
    app = _dispatch()
    try:
        mail = app.CreateItem(0)  # 0 == olMailItem
        mail.To = to or ""
        mail.Subject = subject or ""
        mail.Body = body or ""
        for path in attachments or []:
            mail.Attachments.Add(path)
        if send:
            mail.Send()
        else:
            mail.Display(False)  # open the draft window for review
    except Exception as exc:  # pragma: no cover - Windows only
        raise OutlookError(f"Couldn't create the email.\n\n({exc})")
