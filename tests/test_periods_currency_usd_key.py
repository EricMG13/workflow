"""CP-2D and CP-3C under an fy-2026 USD run (R1) equal the frozen `module_oracles/CP-2D@USD` and
`CP-3C@USD` (Phase 8 Task 4, fix 1). The EUR comparisons live in
`test_periods_currency_e2e_cp2d.py` and `_cp3c.py`; this file points the same composers at the
USD run's key (context, T4.14 rows, oracle, tokens), loaded from `cases/periods-currency-owner/`
at run time."""

from __future__ import annotations

import functools
import json
from pathlib import Path

import pytest
import test_period_basis as tpb
import test_periods_currency_e2e_cp2d as a
import test_periods_currency_e2e_cp3c as a2

from deploy_workflow.owners.period_basis import period_basis


def _use_usd_run(monkeypatch: pytest.MonkeyPatch, module: str) -> None:
    rows = json.loads((a.CASE / "t414.json").read_text(encoding="utf-8"))["contexts"]["R1"]["rows"]
    context = tpb._context("fy-2026", "USD")
    monkeypatch.setattr(a, "ROWS", rows)
    monkeypatch.setattr(a, "CURRENCY", "USD")
    monkeypatch.setattr(a, "CONTEXT", context)
    monkeypatch.setattr(a, "BASIS", period_basis(context, tpb._oracle_facts(rows)))
    monkeypatch.setattr(a, "cp1_2026", functools.partial(a.cp1_2026, "USD"))
    monkeypatch.setattr(a, "ORACLE", a.KEY["module_oracles"]["CP-2D@USD"]["expected"])
    monkeypatch.setattr(a, "R6", a.KEY["runs"]["R1"]["modules"]["CP-2D"])
    if module == "CP-3C":
        monkeypatch.setattr(a2, "ORACLE", a.KEY["module_oracles"]["CP-3C@USD"]["expected"])
        monkeypatch.setattr(a2, "R6", a.KEY["runs"]["R1"]["modules"]["CP-3C"])
        monkeypatch.setattr(a2, "_compose", functools.partial(a2._compose, currency="USD"))


def test_cp2d_usd_2026_equals_the_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_usd_run(monkeypatch, "CP-2D")
    a.test_cp2d_eur_2026_equals_the_key(tmp_path, monkeypatch)


def test_cp3c_usd_2026_equals_the_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_usd_run(monkeypatch, "CP-3C")
    a2.test_cp3c_eur_2026_equals_the_key(tmp_path, monkeypatch)
