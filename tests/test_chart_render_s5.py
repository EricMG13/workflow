"""S.5 on the Credit Snapshot financials block, through the real producer and the registered
figure seam. Expected values are read from ``cases/charts/s5-expected.json``."""

import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from test_financial_series import BASES, change, fixture

from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Run, View
from deploy_vii.render import empty_view
from deploy_vii.report_view import build, pathways

ORACLE = json.loads((Path(__file__).parents[1] / "cases/charts/s5-expected.json").read_text())
SERIES = ORACLE["chart_series"][0]
BLOCK = ORACLE["render"]["block_id"]


def _view(module, pathway="credit_snapshot"):
    run = Run(
        run_id="s5-render",
        issuer_id="northbridge-synthetic",
        issuer_name="Northbridge Synthetic Group",
        as_of=date(2026, 1, 10),
        case_kind="synthetic",
        pathway=pathway,
        requested_modules=("CP-1", "CP-MODEL"),
    )
    base = empty_view(run, candidate=False)
    # One income-statement fact fills the financials period grid S.5 sits beside.
    statement = module.facts[0].model_copy(
        update={
            "fact_id": "income.revenue.q1",
            "table_id": "T4.4",
            "row_id": "revenue",
            "field": "q1",
            "text": None,
            "amount": Decimal(30),
            "unit": "MILLIONS",
            "currency": "USD",
            "scale": Decimal(1000000),
        }
    )
    module = module.model_copy(update={"facts": (*module.facts, statement)})
    modules = tuple(module if m.module_id == "CP-1" else m for m in base.modules)
    return View.model_validate(base.model_copy(update={"modules": modules}).model_dump())


def _blocks(view):
    pathway = next(p for p in pathways() if p.id == view.run.pathway)
    return {b.block_id: b for b in build(view, pathway, SHIPPED_MAPS).blocks}


def test_credit_snapshot_draws_s5_beside_the_period_grid():
    block = _blocks(_view(fixture()))[BLOCK]
    expected = ORACLE["render"]
    assert (block.owner, block.kind, block.state) == (
        expected["owner"],
        expected["kind"],
        expected["state"],
    )
    assert [(f.fig_id, f.placement) for f in block.figures] == [
        (f["fig_id"], f["placement"]) for f in expected["figures"]
    ]
    chart = block.figures[0].chart
    assert (chart.kind, chart.unit, chart.unit_class) == ("grouped", "US$m", "amount")
    assert chart.series == ("Net revenues", "Adjusted EBITDA")
    points = SERIES["points"]
    assert [m.value for m in chart.marks] == [Decimal(p["amount_exact"]) for p in points]
    assert [m.text for m in chart.marks] == [p["shown"] for p in points]
    assert [m.label for m in chart.marks] == [p["category"] for p in points]
    twin = ORACLE["table_twin"]["S.5"]["rows"]
    assert [c.text for r in chart.table_twin.rows for c in r.cells] == [r["cell"] for r in twin]
    assert [c.text for r in chart.table_twin.rows for c in r.cells] == [m.text for m in chart.marks]
    for row, expected_row in zip(chart.table_twin.rows, twin, strict=True):
        assert row.label.startswith(expected_row["label_parts"][0])


def test_marks_keep_the_exact_value_and_the_display_rounding():
    chart = _blocks(_view(fixture()))[BLOCK].figures[0].chart
    ebitda = [m for m in chart.marks if m.series == "Adjusted EBITDA"]
    assert [m.value for m in ebitda] == [Decimal("7.5")] * 4
    assert {m.text for m in ebitda} == {"8"}


def test_strip_s1_to_s4_is_unchanged_by_s5():
    blocks = _blocks(_view(fixture()))
    assert [f.fig_id for f in blocks["model-chart-strip"].figures] == ["S.1", "S.2", "S.3", "S.4"]
    assert "S.5" not in {f.fig_id for b in blocks.values() if b.block_id != BLOCK for f in b.figures}


def test_a_gap_quarter_is_a_gap_mark_with_its_reference_and_the_others_survive():
    module = change(
        fixture(),
        table="T4.10",
        row="T4.10.adjusted_ebitda",
        field="model-basis:" + BASES[1],
        amount=None,
        status="missing",
        limitation="Adjusted EBITDA not supplied",
        citations=(),
    )
    chart = _blocks(_view(module))[BLOCK].figures[0].chart
    gaps = [m for m in chart.marks if m.value is None]
    assert len(gaps) == 1
    assert re.fullmatch(r"∅ G\d+", gaps[0].text) and gaps[0].ref_id == gaps[0].text[2:]
    assert gaps[0].series == "Adjusted EBITDA" and gaps[0].label == "Q2 2025"
    assert sum(m.value is not None for m in chart.marks) == 7


def test_earnings_update_draws_no_s5():
    expected = ORACLE["render"]["earnings_update"]
    block = _blocks(_view(fixture(), pathway=expected["pathway"]))[BLOCK]
    assert block.state == "populated" and block.rows
    assert [f.fig_id for f in block.figures] == expected["figures"] == []


@pytest.mark.parametrize("status", ["blocked", "stale"])
def test_an_unsettled_cp1_draws_no_s5(status):
    view = _view(fixture().model_copy(update={"status": status}))
    block = _blocks(view)[BLOCK]
    assert block.figures == ()
