"""Period resolution against the frozen oracle ``cases/context-identity-periods``."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from deploy_vii.contracts import Fact
from deploy_workflow.context_periods import quarters_ending_at, resolve

ORACLE = json.loads(
    (
        Path(__file__).resolve().parents[2] / "cases" / "context-identity-periods" / "expected.json"
    ).read_text(encoding="utf-8")
)
PACK_IDS = ORACLE["periods_resolution"]["pack_t414_periods"]


def _row(pid: str, kind: str, year: str, quarter: str | None) -> dict[str, Fact]:
    def text(field: str, value: str | None) -> Fact:
        return Fact(
            fact_id=f"{pid}:{field}",
            label=field,
            table_id="T4.14",
            row_id=pid,
            field=field,
            text=value,
            status="known" if value else "not_applicable",
            limitation=None if value else "not a quarter",
            scale=Decimal(1),
        )

    return {
        "period_id": text("period_id", pid),
        "period_type": text("period_type", kind),
        "fiscal_year": text("fiscal_year", year),
        "fiscal_quarter": text("fiscal_quarter", quarter),
    }


def _rows(*ids: str) -> dict[str, dict[str, Fact]]:
    out: dict[str, dict[str, Fact]] = {}
    for pid in ids:
        if pid.startswith("q"):
            out[pid] = _row(pid, "QUARTER", f"FY{pid[3:]}", pid[:2].upper())
        elif pid.startswith("fy"):
            out[pid] = _row(pid, "FY", f"FY{pid[3:]}", None)
        else:
            out[pid] = _row(pid, "PERIOD_END", "FY2024", None)
    return out


def test_oracle_pack_periods_resolve_to_their_own_ids() -> None:
    rows = _rows(*PACK_IDS)
    for pid in PACK_IDS:
        if pid.startswith(("q", "fy")):
            assert resolve(pid, rows) == pid


def test_year_absent_from_the_pack_resolves_to_none() -> None:
    rows = _rows(*PACK_IDS)
    # the oracle's q2031 case: no 2031 period exists
    assert ORACLE["periods_resolution"]["q2031"]
    assert resolve("q4-2031", rows) is None
    assert resolve("q3-2031", rows) is None


def test_two_matching_rows_resolve_to_none() -> None:
    rows = _rows("q4-2025")
    rows["q4-2025-restated"] = _row("q4-2025-restated", "QUARTER", "FY2025", "Q4")
    assert resolve("q4-2025", rows) is None


def test_fy_not_found_among_quarters_only() -> None:
    assert resolve("fy-2025", _rows("q1-2025", "q4-2025")) is None


@pytest.mark.parametrize("bad", ["h1-2025", "", "q5-2025", "2025"])
def test_non_quarter_non_fy_text_resolves_to_none(bad: str) -> None:
    assert resolve(bad, _rows(*PACK_IDS)) is None


def test_quarters_ending_at_matches_oracle_ctx_l10_and_ctx_q3() -> None:
    l10 = [q["context_period"] for q in ORACLE["cpl10"]["ctx-l10"]["quarters"]]
    assert quarters_ending_at("q4-2025") == tuple(l10)
    assert list(quarters_ending_at("q3-2025")) == ORACLE["cpl10"]["ctx-q3"]["quarters_ending_at"]


def test_quarters_ending_at_spans_the_year_boundary() -> None:
    assert quarters_ending_at("q2-2026") == ("q3-2025", "q4-2025", "q1-2026", "q2-2026")


@pytest.mark.parametrize("bad", ["fy-2025", "h1-2025", ""])
def test_quarters_ending_at_refuses_non_quarters(bad: str) -> None:
    with pytest.raises(ValueError, match="context_period_not_quarter"):
        quarters_ending_at(bad)
