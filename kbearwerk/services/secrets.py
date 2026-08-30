"""Secure secret storage backed by the OS keychain.

On Windows this uses the built-in **Credential Manager** (encrypted per-user),
so any password we ever need to store (e.g. a website login) is never written to
a plain-text file. Reading Outlook does *not* need a stored password - it uses
the session she is already signed into - but this is here for the OCE site etc.
"""

from __future__ import annotations

from typing import Optional

from ..version import APP_NAME

try:
    import keyring
    _KEYRING_OK = True
except Exception:  # pragma: no cover
    _KEYRING_OK = False

SERVICE = APP_NAME


def available() -> bool:
    return _KEYRING_OK


def set_secret(key: str, value: str) -> None:
    if not _KEYRING_OK:
        raise RuntimeError("Secure storage (keyring) is not available on this machine.")
    keyring.set_password(SERVICE, key, value)


def get_secret(key: str) -> Optional[str]:
    if not _KEYRING_OK:
        return None
    try:
        return keyring.get_password(SERVICE, key)
    except Exception:
        return None


def delete_secret(key: str) -> None:
    if not _KEYRING_OK:
        return
    try:
        keyring.delete_password(SERVICE, key)
    except Exception:
        pass
