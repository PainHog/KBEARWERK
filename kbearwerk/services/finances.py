"""Money totals from the invoice ledger.

Answers the questions she needs at a glance:
  * **Held job fund** - total income tied up in invoices currently on hold.
  * **This month's billing** - overall and per engineer.
  * **Running yearly total.**

All figures are derived from the same Excel ledger the Held Invoices panel reads,
so there's one source of truth. Column names/dates are read loosely and will be
tuned to her real ledger.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import excel, invoices


_DATE_KEYS = ["invoice date", "date", "date sent", "billed date", "sent date", "date billed"]
_DATE_FORMATS = ["%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%m-%d-%Y", "%m.%d.%Y", "%B %d, %Y", "%b %d, %Y"]


def parse_amount(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[^0-9.\-]", "", str(value))
    try:
        return float(cleaned) if cleaned not in ("", "-", ".") else 0.0
    except ValueError:
        return 0.0


def parse_date(value: Any) -> Optional[datetime.date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    text = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


@dataclass
class FinanceSummary:
    held_total: float = 0.0
    month_total: float = 0.0
    year_total: float = 0.0
    per_engineer_month: Dict[str, float] = field(default_factory=dict)
    per_engineer_year: Dict[str, float] = field(default_factory=dict)
    month_label: str = ""
    year: int = 0
    counted_rows: int = 0
    undated_rows: int = 0


def summarize(config: Dict[str, Any], today: Optional[datetime.date] = None) -> FinanceSummary:
    """Compute the financial dashboard figures from the invoice ledger."""
    today = today or datetime.date.today()
    summary = FinanceSummary(
        month_label=today.strftime("%B %Y"),
        year=today.year,
    )
    path = config.get("paths", {}).get("invoice_ledger", "")
    if not path:
        return summary
    inv_cfg = config.get("invoices", {})
    sheet = inv_cfg.get("sheet") or None
    try:
        rows = excel.read_rows(path, sheet_name=sheet)
    except Exception:
        return summary

    terms = [t.lower() for t in inv_cfg.get("held_terms", ["held"]) if t]

    def _bump(d: Dict[str, float], key: str, amt: float) -> None:
        d[key] = d.get(key, 0.0) + amt

    for row in rows:
        amount = parse_amount(invoices._get(row, invoices._AMOUNT_KEYS))
        status = invoices._get(row, invoices._STATUS_KEYS)
        notes = invoices._get(row, invoices._NOTES_KEYS)
        held = any(t in f"{status} {notes}".lower() for t in terms)
        engineer = invoices._guess_engineer(config, notes, invoices._get(row, invoices._ENGINEER_KEYS)) or "(unknown)"

        if held:
            summary.held_total += amount
            continue  # held money isn't billed yet

        d = parse_date(invoices._get(row, _DATE_KEYS))
        if d is None:
            summary.undated_rows += 1
            continue
        if d.year == today.year:
            summary.year_total += amount
            _bump(summary.per_engineer_year, engineer, amount)
            if d.month == today.month:
                summary.month_total += amount
                _bump(summary.per_engineer_month, engineer, amount)
                summary.counted_rows += 1
    return summary


def engineers_sorted(summary: FinanceSummary) -> List[str]:
    """Engineer names ordered by yearly total (desc)."""
    names = set(summary.per_engineer_year) | set(summary.per_engineer_month)
    return sorted(names, key=lambda n: summary.per_engineer_year.get(n, 0.0), reverse=True)
