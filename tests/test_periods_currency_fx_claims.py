"""Probe F: the FX claim and limitation texts of a EUR run with a USD facility, each compared
whole (the task test's substring "every facility in EUR, and one is not" is matched by either
the CP-2D-MAT claim or the funding-gap claim, so each alone can regress). Expected texts are the
frozen USD texts pinned in tests/test_method_cp2d.py (:1002, :1149) with the run currency in
place of USD. Exit 0 = both claims and the sources-and-uses difference unit name EUR.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import test_method_cp2d as tm2
import test_periods_currency_e2e_cp2d as a

from deploy_workflow.owners import cp2d

MAT = (
    "The cash outflow from debt maturing inside the horizon is not calculated: [T2E.3.r07] needs "
    "every facility in EUR, and one is not; no FX conversion is applied."
)
GAP = "The funding gap is not calculated: [T2E.5.r07] needs every facility in EUR, and one is not."


def _eur_run_usd_facility() -> cp2d.Cp2dResult:
    inputs = tm2._inputs("positive")
    facs = tuple(replace(f, currency="USD") for f in inputs.operands.facilities or ())
    return cp2d.compute(
        replace(inputs, operands=replace(inputs.operands, facilities=facs), basis=a.BASIS)
    )


def test_both_fx_claims_name_the_run_currency() -> None:
    texts = [c.text for c in _eur_run_usd_facility().claims]
    assert MAT in texts, texts
    assert GAP in texts, texts


def test_a_sources_and_uses_difference_is_spelled_in_the_run_unit() -> None:
    inputs = tm2._inputs("positive")
    closing = inputs.operands.closing_cash
    assert closing is not None and closing.amount is not None
    ops = replace(
        inputs.operands, closing_cash=replace(closing, amount=closing.amount + Decimal("1.5"))
    )
    r = cp2d.compute(replace(inputs, operands=ops, basis=a.BASIS))
    lims = [t for t in r.own_limitations if t.startswith("Sources and uses differ")]
    assert lims and lims[0].endswith("EUR m."), lims
