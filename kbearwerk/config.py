"""Application configuration: load, save and defaults.

Settings are stored as JSON in a per-user config directory so they survive
app restarts and are never committed to source control. On Windows this is
``%APPDATA%\\KBEARWERK\\config.json``.

The config is intentionally a plain ``dict`` (not a rigid schema) so we can add
new settings later without breaking older config files - :func:`load` deep-merges
whatever is on disk on top of :data:`DEFAULTS`, so missing keys fill in and
unknown keys are preserved.
"""

from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict

from .version import APP_NAME

# ---------------------------------------------------------------------------
# Default settings
# ---------------------------------------------------------------------------
# Everything here is a placeholder we will make precise once we see her real
# files, folder names and lists. The app works with these defaults but the
# Settings panel lets her point the app at the real locations.

DEFAULT_FOLDER_TEMPLATE = [
    "01 - Correspondence",
    "02 - Proposal & Contract",
    "03 - Calculations",
    "04 - Drawings",
    "05 - Redlines",
    "06 - Submittals & RFIs",
    "07 - Field & Observations",
    "08 - Photos",
    "09 - Reference & Client Docs",
    "10 - Project Information",
]

DEFAULTS: Dict[str, Any] = {
    # Root folder that all project folders live under, e.g. "D:\\Work".
    "base_folder": "",
    # How a new project folder is named. Available fields: {number} {name} {client}.
    "project_folder_pattern": "{number} - {name}",
    # Sub-folders created inside every new project folder.
    "folder_template": list(DEFAULT_FOLDER_TEMPLATE),
    # Paths to the various Excel workbooks she maintains.
    "paths": {
        "proposal_list": "",
        "project_list": "",
        "weekly_worksheet": "",
        "redline_log": "",
        "drafting_list": "",
        "observations_log": "",
        "invoice_ledger": "",
    },
    # Held-invoice reminders. The ledger marks held invoices with one of these
    # terms (in a Status or Notes column); the engineer's nickname sits in the
    # notes next to it. Emails are DRAFTED (never auto-sent) until send_emails is
    # turned on after testing.
    "invoices": {
        "held_terms": ["held", "hold", "on hold"],
        "send_emails": False,
        "sheet": "",
    },
    # Documents every job folder should contain. The app scans the folder and
    # marks each item found/missing by looking for these keywords in file names.
    "required_documents": [
        {"label": "Signed Proposal", "keywords": ["proposal", "signed proposal"]},
        {"label": "Executed Contract / Agreement", "keywords": ["contract", "agreement", "executed"]},
        {"label": "Project Information Sheet", "keywords": ["project information", "project info", "info sheet"]},
        {"label": "Structural Calculations", "keywords": ["calc", "calculation"]},
        {"label": "Geotechnical / Soils Report", "keywords": ["geotech", "soils", "soil report"]},
        {"label": "Architectural Drawings", "keywords": ["architectural", "arch", "floor plan", "a-1"]},
    ],
    # Non-file items she must confirm per job (tracked as check-offs, remembered
    # per project). These are the "they left me without info" gaps.
    "required_info": [
        "Client contact confirmed",
        "Contractor confirmed",
        "Billing rate / fee confirmed",
        "Scope of work confirmed",
    ],
    # In-house drafters that redlines get sent to.
    "drafters": [
        # {"name": "Example Drafter", "email": "drafter@example.com"}
    ],
    # Field inspectors that observations get assigned to.
    "inspectors": [
        # {"name": "Example Inspector", "email": "inspector@example.com"}
    ],
    # Friendly contacts directory: she picks people by NICKNAME, never by email
    # address. The real address is looked up silently when sending.
    "contacts": [
        # {"nickname": "Carl", "email": "carl@firm.com", "role": "drafter"}
        # {"nickname": "Ian",  "email": "ian@firm.com",  "role": "staff"}
    ],
    # Email monitoring (reads the classic Outlook desktop app locally).
    "email": {
        # Display name or address of the mailbox to watch (her boss's inbox).
        "monitored_mailbox": "",
        "urgent_keywords": ["urgent", "asap", "emergency", "immediately", "critical"],
        "rfp_keywords": ["rfp", "request for proposal", "proposal", "quote", "bid"],
        # Client email domains worth flagging (without the @).
        "client_domains": [],
        "lookback_days": 7,
    },
    # Fill-in document templates for the Documents panel. Each entry:
    #   {"name": "Transmittal", "path": "C:/.../Transmittal (blank).docx",
    #    "save_to": ["C:/folderA", "C:/folderB"]}
    # Fields are detected automatically from {{ tags }} inside the template.
    "templates": [],
    # Engineer signature + seal images, applied only on "Seal and Save".
    # Each: {"name": "Jane Smith, PE", "signature_image": "C:/.../sig.png",
    #        "seal_image": "C:/.../seal.png"}. Templates use {{ signature }} and
    #  {{ seal }} tags where the images should appear, and {{ draft_notice }} for
    #  the DRAFT watermark line.
    "seals": [],
    "default_engineer": "",
    # External sites opened during the new-project workflow.
    "monograph_url": "https://app.monograph.com/",
    "oce_url": "",
    # Company details used when generating documents.
    "company": {
        "name": "",
        "address": "",
        "phone": "",
    },
    # UI preferences.
    "appearance": "light",  # "light", "dark" or "system"
}


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------

def config_dir() -> str:
    """Return the directory where config + logs live (created if missing)."""
    override = os.environ.get("KBEARWERK_CONFIG_DIR")
    if override:
        path = override
    elif os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(base, APP_NAME)
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
            os.path.expanduser("~"), ".config"
        )
        path = os.path.join(base, APP_NAME.lower())
    os.makedirs(path, exist_ok=True)
    return path


def config_path() -> str:
    return os.path.join(config_dir(), "config.json")


# ---------------------------------------------------------------------------
# Deep merge helper
# ---------------------------------------------------------------------------

def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Return ``base`` with ``override`` merged in (override wins on leaves)."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def default_config() -> Dict[str, Any]:
    return copy.deepcopy(DEFAULTS)


def load() -> Dict[str, Any]:
    """Load config from disk, filling in any missing defaults."""
    path = config_path()
    if not os.path.exists(path):
        return default_config()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        # Corrupt or unreadable config: fall back to defaults rather than crash.
        return default_config()
    if not isinstance(data, dict):
        return default_config()
    return _deep_merge(DEFAULTS, data)


def save(config: Dict[str, Any]) -> str:
    """Write config to disk atomically. Returns the path written."""
    path = config_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2, sort_keys=False)
    os.replace(tmp, path)
    return path
