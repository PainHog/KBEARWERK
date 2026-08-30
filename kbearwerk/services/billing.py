"""Per-project billing ledger.

Her firm agrees a fixed **contract amount** per project but bills it out in
pieces (hours / phases / percentages). She needs to see, at a glance, how much
of the contract has been billed and how much is **remaining**.

For now this is stored in a simple local JSON file so the panel works out of the
box. Once we have her real billing spreadsheets we can switch the storage to
read/write those directly - the panel code won't have to change, only this file.

Data shape::

    {
      "2025-104": {
        "project_name": "Smith Residence",
        "contract_amount": 12000.0,
        "entries": [
          {"date": "2026-08-30", "description": "Schematic design",
           "hours": 12.0, "amount": 1800.0, "invoice": "INV-001"}
        ]
      }
    }
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List

from ..config import config_dir


def _store_path() -> str:
    return os.path.join(config_dir(), "billing.json")


def load_all() -> Dict[str, Any]:
    path = _store_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_all(data: Dict[str, Any]) -> None:
    path = _store_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, path)


def _key(project_number: str) -> str:
    return (project_number or "").strip()


def get_project(project_number: str) -> Dict[str, Any]:
    data = load_all()
    return data.get(_key(project_number), {
        "project_name": "",
        "contract_amount": 0.0,
        "entries": [],
    })


def set_contract(project_number: str, amount: float, project_name: str = "") -> None:
    data = load_all()
    key = _key(project_number)
    rec = data.get(key, {"project_name": "", "contract_amount": 0.0, "entries": []})
    rec["contract_amount"] = float(amount or 0.0)
    if project_name:
        rec["project_name"] = project_name
    data[key] = rec
    _save_all(data)


def add_entry(project_number: str, entry: Dict[str, Any]) -> None:
    data = load_all()
    key = _key(project_number)
    rec = data.get(key, {"project_name": "", "contract_amount": 0.0, "entries": []})
    rec.setdefault("entries", []).append({
        "date": str(entry.get("date", "")),
        "description": str(entry.get("description", "")),
        "hours": float(entry.get("hours") or 0.0),
        "amount": float(entry.get("amount") or 0.0),
        "invoice": str(entry.get("invoice", "")),
    })
    data[key] = rec
    _save_all(data)


def remove_entry(project_number: str, index: int) -> None:
    data = load_all()
    key = _key(project_number)
    rec = data.get(key)
    if rec and 0 <= index < len(rec.get("entries", [])):
        rec["entries"].pop(index)
        _save_all(data)


def list_projects() -> List[str]:
    return sorted(load_all().keys())


@dataclass
class BillingSummary:
    contract_amount: float
    billed: float
    remaining: float
    percent_billed: float
    entry_count: int


def summarize(project_number: str) -> BillingSummary:
    rec = get_project(project_number)
    contract = float(rec.get("contract_amount") or 0.0)
    billed = sum(float(e.get("amount") or 0.0) for e in rec.get("entries", []))
    remaining = contract - billed
    pct = (billed / contract * 100.0) if contract else 0.0
    return BillingSummary(
        contract_amount=contract,
        billed=billed,
        remaining=remaining,
        percent_billed=pct,
        entry_count=len(rec.get("entries", [])),
    )
