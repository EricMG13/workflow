"""Period resolution for a run context (Phase 2): context period strings against CP-1 T4.14 rows.

A context names periods as ``q3-2025`` / ``fy-2024`` (``context.PERIOD``). The CP-1 head holds
them as T4.14 rows (``earnings._periods``). ``resolve`` returns the one matching ``period_id``
and never guesses: zero or several matches is ``None``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from deploy_vii.contracts import Fact

_QUARTER = re.compile(r"q([1-4])-(\d{4})")
_ANNUAL = re.compile(r"fy-(\d{4})")


def _text(row: Mapping[str, Fact], field: str) -> str | None:
    fact = row.get(field)
    if fact is None or fact.status != "known" or fact.amount is not None:
        return None
    return fact.text


def _matches(row: Mapping[str, Fact], kind: str, year: str, quarter: str | None) -> bool:
    fiscal_year = _text(row, "fiscal_year")
    if _text(row, "period_type") != kind or fiscal_year is None:
        return False
    if re.findall(r"\d{4}", fiscal_year) != [year]:
        return False
    if quarter is None:
        return True
    fiscal_quarter = _text(row, "fiscal_quarter")
    return fiscal_quarter is not None and fiscal_quarter.removeprefix("Q") == quarter


def resolve(period: str, rows: Mapping[str, Mapping[str, Fact]]) -> str | None:
    """The one T4.14 ``period_id`` matching ``period``; ``None`` on zero or several matches."""
    quarter = _QUARTER.fullmatch(period)
    annual = _ANNUAL.fullmatch(period)
    if quarter:
        kind, year, number = "QUARTER", quarter[2], quarter[1]
    elif annual:
        kind, year, number = "FY", annual[1], None
    else:
        return None
    found = [pid for pid, row in rows.items() if _matches(row, kind, year, number)]
    return found[0] if len(found) == 1 else None


def quarters_ending_at(period: str) -> tuple[str, ...]:
    """The four quarter strings ending at the quarter ``period`` (oldest first)."""
    match = _QUARTER.fullmatch(period)
    if match is None:
        raise ValueError("context_period_not_quarter")
    index = int(match[2]) * 4 + int(match[1]) - 1
    return tuple(f"q{i % 4 + 1}-{i // 4}" for i in range(index - 3, index + 1))
