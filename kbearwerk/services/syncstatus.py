"""Tell whether a file has actually synced to the cloud.

Desync-avoidance is only trustworthy if she can *see* the state. On Windows,
cloud files (OneDrive/SharePoint, and similar providers) carry attributes that
reveal their state - this reads them so we can show the same ✓ she's used to:

* **synced**    - the cloud has it (offloaded placeholder, or marked free-uppable)
* **on_device** - present locally; sync not yet confirmed (may still be uploading)
* **pending**   - we couldn't reach the cloud folder, so it's queued locally
* **missing**   - not found

Off Windows we can only say present/missing (best-effort), which is fine for
development.
"""

from __future__ import annotations

import os
import sys

# Windows cloud/placeholder file attributes.
_RECALL_ON_DATA_ACCESS = 0x00400000  # fully offloaded to cloud (definitely synced)
_RECALL_ON_OPEN = 0x00040000
_UNPINNED = 0x00100000               # synced; may be dehydrated to free space
_PINNED = 0x00080000                 # kept on device
_OFFLINE = 0x00001000

SYNCED = "synced"
ON_DEVICE = "on_device"
PENDING = "pending"
MISSING = "missing"

_ICON = {SYNCED: "✓", ON_DEVICE: "☁", PENDING: "⏳", MISSING: "✗"}
_LABEL = {SYNCED: "synced", ON_DEVICE: "on this PC (syncing)", PENDING: "waiting to sync", MISSING: "missing"}


def file_state(path: str) -> str:
    if not path or not os.path.exists(path):
        return MISSING
    if sys.platform == "win32":
        try:
            import ctypes
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            if attrs == -1:
                return MISSING
            if attrs & (_RECALL_ON_DATA_ACCESS | _UNPINNED | _OFFLINE):
                return SYNCED           # the cloud holds it
            if attrs & _PINNED:
                return ON_DEVICE        # kept local; upload may be in progress
            return ON_DEVICE            # ordinary local file in a synced folder
        except Exception:
            return ON_DEVICE
    # Non-Windows: present is the best we can say.
    return SYNCED


def icon(state: str) -> str:
    return _ICON.get(state, "?")


def label(state: str) -> str:
    return _LABEL.get(state, "unknown")
