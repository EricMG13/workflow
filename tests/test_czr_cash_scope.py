"""CZR with the filing's printed cash scope declared: both NCF_CASH_MOVEMENT checks agree.

The recorded partial submission is loaded and extended in memory (the "restricted and escrow cash
included in other long-term assets" balance, one scope declaration per flow period, and the two
pages that print the balance); nothing under `cases/**` is edited. The run still stops at the
calculation gate for the other open checks, so the reconciliation is captured as the audit builds it.
"""

import copy
import json
from typing import Any

import pytest
from czr_runs import CASE, czr_closed

from deploy_vii import canonical_audit
from deploy_vii.financial_reconciliation import Reconciliation, ReconciliationReport

NONCURRENT = "bs-restricted-and-escrow-cash-included-in-other-long-term-assets-net"
BOTH = ["restricted_cash", "restricted_cash_noncurrent"]
K_QUOTE = "Restricted and escrow cash included in other long-term assets, net | 12 | 55 | 16"
Q_QUOTE = "Restricted and escrow cash included in other long-term assets, net | 16 | 19"
# period -> (amount, source id, locator, quote)
BALANCES = {
    "bs-2025-12-31": ("12", "czr-fy2025-10k", "page:61", K_QUOTE),
    "bs-2024-12-31": ("55", "czr-fy2025-10k", "page:61", K_QUOTE),
    "bs-2026-06-30": ("16", "czr-q2-2026-10q", "page:10", Q_QUOTE),
}


def _declared(data: dict[str, Any]) -> dict[str, Any]:
    stage = next(s for s in data["stages"] if s["step"] == "financials")
    book = stage["submission"]["financial"]["books"][0]
    shas = {
        c["source_id"]: c["source_sha256"]
        for row in book["statement_lines"]
        for c in row["value"]["citations"]
    }
    top = max(row["display_priority"] for row in book["statement_lines"])
    for period, (amount, source, locator, quote) in BALANCES.items():
        citation = {
            "source_id": source,
            "source_sha256": shas[source],
            "locator": locator,
            "quote": quote,
        }
        book["statement_lines"].append(
            {
                "line_id": NONCURRENT,
                "statement": "BS",
                "item_id": "restricted_cash_noncurrent",
                "label": "Restricted and escrow cash included in other long-term assets, net",
                "period_id": period,
                "display_priority": top + 1,
                "line_kind": "detail",
                "value": {
                    "observation_id": f"{NONCURRENT}--{period}",
                    "status": "known",
                    "amount": amount,
                    "citations": [citation],
                },
            }
        )
    for period in ("fy-2025", "h1-2026"):
        line = next(
            r
            for r in book["statement_lines"]
            if r["item_id"] == "net_cash_change" and r["period_id"] == period
        )
        citation = line["value"]["citations"][0]
        book["cash_movement_bridges"].append(
            {
                "bridge_id": f"bridge-{period}",
                "period_id": period,
                "components": [],
                "explanation": "No FX or perimeter adjustment is printed in the cash flow statement.",
                "citations": [citation],
                "cash_scope": {"items": BOTH, "citations": [citation]},
            }
        )
    stage["calls"] += [
        {
            "tool": "read_pages",
            "arguments": {"source_id": "czr-fy2025-10k", "first_page": 61, "last_page": 61},
        },
        {
            "tool": "read_pages",
            "arguments": {"source_id": "czr-q2-2026-10q", "first_page": 10, "last_page": 10},
        },
    ]
    return data


def test_czr_cash_movement_agrees_with_the_declared_scope(tmp_path, monkeypatch):
    data = _declared(copy.deepcopy(json.loads((CASE / "submissions-partial.json").read_text())))
    path = tmp_path / "submissions.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    captured: list[ReconciliationReport] = []
    original = canonical_audit.reconcile_financials

    def spy(*args: Any, **kwargs: Any) -> ReconciliationReport:
        report = original(*args, **kwargs)
        captured.append(report)
        return report

    monkeypatch.setattr(canonical_audit, "reconcile_financials", spy)
    with pytest.raises(RuntimeError):
        czr_closed(tmp_path / "run", path)
    assert captured, "the audit never reconciled the financials"
    checks: dict[str, Reconciliation] = {
        c.period_id: c for c in captured[-1].checks if c.check_type == "NCF_CASH_MOVEMENT"
    }
    for period, calculated in (("fy-2025", -32), ("h1-2026", 93)):
        check = checks[period]
        assert (check.status, check.calculated_value, check.difference) == (
            "PASS",
            calculated,
            0,
        )
