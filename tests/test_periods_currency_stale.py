"""Probe E: Done-when 1 on the R6 (EUR fy-2026) CP-2D and CP-3C modules composed end to end by
probes A and A2: no stale literal of `expected.json#runs/R6/stale_period_literals_forbidden_in_
emitted_period_strings` in the module (tables, facts, claims, limitations). The CP-2D fixture
pack runs as of 2026-01-10 (the frozen run), so the as-of literals are excluded for CP-2D only.
Exit 0 = none found."""

from __future__ import annotations

from pathlib import Path

import pytest
import test_periods_currency_e2e_cp2d as a
import test_periods_currency_e2e_cp3c as a2

from deploy_workflow.owners import cp3c

STALE = a.KEY["runs"]["R6"]["stale_period_literals_forbidden_in_emitted_period_strings"]
AS_OF = {"As of 2026-01-10", "as of 2026-01-10", "Terms published 2026-01-10"}


def test_cp2d_r6_module_has_no_stale_literal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, module = a._compose(tmp_path, monkeypatch, a.cp1_2026())
    text = module.model_dump_json()
    assert [s for s in STALE if s in text and s not in AS_OF] == []


def test_cp3c_r6_module_has_no_stale_literal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _store, pack, attempt, upstream = a2._compose(tmp_path, monkeypatch)
    report = cp3c.refinancing_risk(
        pack=pack, submission=a2._submission(upstream), upstream=upstream
    )
    text = cp3c.cp3c_module(
        report=report, inputs=attempt.inputs, attempt=attempt.number
    ).model_dump_json()
    assert [s for s in STALE if s in text] == []
