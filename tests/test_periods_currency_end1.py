"""Phase 8 end batch 1: Low findings of the closed Task 1, 3, 4 and 7 reviews."""

from __future__ import annotations

import pytest
from test_period_basis import _calendar, _context

from deploy_vii.contracts import Fact
from deploy_workflow.owners.period_basis import PeriodRefused, currency_basis, period_basis


def _without_unit(facts: list[Fact]) -> list[Fact]:
    return [fact for fact in facts if fact.field != "unit"]


@pytest.mark.parametrize("period", ["fy-2026", "q4-2026", "q3-2026"])
def test_currency_basis_refuses_a_row_with_no_unit_fact(period: str) -> None:
    """A: a T4.14 row with no `unit` fact is not skipped (the probe's `r4a` edge)."""
    with pytest.raises(PeriodRefused, match="unit is not MILLIONS"):
        currency_basis(_context(period), _without_unit(_calendar()))


def test_period_basis_refuses_a_row_with_no_unit_fact() -> None:
    with pytest.raises(PeriodRefused, match="unit is not MILLIONS"):
        period_basis(_context("fy-2026"), _without_unit(_calendar()))
