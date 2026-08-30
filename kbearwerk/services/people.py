"""Friendly people directory - pick contacts by nickname, not email address.

She should email "Carl" or "Ian", never "ianhurley@blah.blah". This unifies the
contacts directory with the drafters and inspectors lists so any of them can be
chosen by nickname anywhere, and the real address is resolved silently at send
time. Logs and the UI always show the nickname.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _all(config: Dict[str, Any]) -> List[Dict[str, str]]:
    people: List[Dict[str, str]] = []
    for c in config.get("contacts", []):
        people.append({"nickname": c.get("nickname", ""), "email": c.get("email", ""),
                       "role": c.get("role", "")})
    for d in config.get("drafters", []):
        people.append({"nickname": d.get("name", ""), "email": d.get("email", ""), "role": "drafter"})
    for i in config.get("inspectors", []):
        people.append({"nickname": i.get("name", ""), "email": i.get("email", ""), "role": "inspector"})
    # De-dupe by nickname (first wins).
    seen = set()
    out: List[Dict[str, str]] = []
    for p in people:
        nk = (p["nickname"] or "").strip()
        if not nk or nk.lower() in seen:
            continue
        seen.add(nk.lower())
        out.append(p)
    return out


def nicknames(config: Dict[str, Any], role: Optional[str] = None) -> List[str]:
    """Nicknames to show in a dropdown. If ``role`` is given, that role plus any
    role-less contacts; otherwise everyone."""
    people = _all(config)
    if role:
        names = [p["nickname"] for p in people if p["role"] == role]
        names += [p["nickname"] for p in people if not p["role"] and p["nickname"] not in names]
        return names or [p["nickname"] for p in people]
    return [p["nickname"] for p in people]


def resolve_email(config: Dict[str, Any], nickname: str) -> str:
    """Nickname -> real email. If she typed an address directly, accept it."""
    nk = (nickname or "").strip().lower()
    if not nk:
        return ""
    for p in _all(config):
        if (p["nickname"] or "").strip().lower() == nk:
            return p["email"]
    return nickname if "@" in nickname else ""


def has_any(config: Dict[str, Any]) -> bool:
    return bool(_all(config))
