"""DR.2 (CP-4C recovery by class) through ``report_view.build`` on a distressed-restructuring run.

Marks, twin rows and the render facts come from ``cases/charts/dr2-expected.json``. The block is
``recovery-by-class``, owner CP-4C, kind dense; the figure sits above the tabs.
"""

import re
from decimal import Decimal
from pathlib import Path

import chart_dr_support as support
import pytest

from deploy_vii import charts
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.report_view import Block, ReportView

ORACLE = support.oracle("dr2")
RECORDS = ORACLE["chart_series"]["DR.2"]
TWINS = ORACLE["table_twins"]
RENDER = ORACLE["render"]["distressed_restructuring"]
BLOCK_ID = RENDER["block_id"]


def _label(table_id: str) -> str:
    entry = next(
        e
        for m in SHIPPED_MAPS
        for e in m.entries
        if m.module_id == "CP-4C" and e.fact_coord.table_id == table_id
    )
    return entry.label


def _block(report: ReportView) -> Block:
    return {b.block_id: b for b in report.blocks}[BLOCK_ID]


def _dr2(case: str) -> Block:
    return _block(support.report_of(support.view_with(support.composer_module(case), case)))


@pytest.mark.parametrize("case", support.CASES)
def test_block_holds_the_figure_above_with_the_oracle_marks(case: str) -> None:
    block = _dr2(case)
    assert (block.owner, block.kind, block.state) == (RENDER["owner"], "dense", "populated")
    assert [f.fig_id for f in block.figures] == ["DR.2"]
    figure = block.figures[0]
    assert (figure.placement, figure.title) == (RENDER["figure"]["placement"], "Recovery by class")
    want = RECORDS[case]
    chart = figure.chart
    assert chart.kind == want["kind"]
    assert list(chart.series) == want["series"]
    assert (chart.unit, chart.unit_class) == ("%", "percent")
    assert [
        (m.series, m.label, support.unbound(m.text), m.value is None, m.hatched)
        for m in chart.marks
    ] == [
        (w["series"], w["category"], w["shown"], w["state"] == "gap", w["hatched"])
        for w in want["points"]
    ]
    assert chart.reason == want["reason"]


@pytest.mark.parametrize("case", support.CASES)
def test_values_are_the_settled_amounts_and_gap_marks_carry_a_report_gap_reference(
    case: str,
) -> None:
    chart = _dr2(case).figures[0].chart
    for mark, want in zip(chart.marks, RECORDS[case]["points"], strict=True):
        if want["state"] == "known":
            assert mark.value == Decimal(want["value"])
            assert mark.ref_id and mark.ref_id[0] in "CKS"
        else:
            assert mark.value is None
            assert mark.ref_id is not None and re.fullmatch(r"G\d+", mark.ref_id)
            assert mark.text == f"∅ {mark.ref_id}"


@pytest.mark.parametrize("case", support.CASES)
def test_table_twin_rows_equal_the_oracle(case: str) -> None:
    twin = _dr2(case).figures[0].chart.table_twin
    want = TWINS[case]
    assert [twin.row_header, *twin.columns] == want["columns"]
    assert [row.label for row in twin.rows] == [r["label"] for r in want["rows"]]
    assert [[support.unbound(c.text) for c in row.cells] for row in twin.rows] == [
        r["cells"] for r in want["rows"]
    ]


def test_zero_recoveries_are_known_zero_marks_and_gaps_are_not_zero() -> None:
    zero = _dr2("fixture_ev_zero").figures[0].chart.marks
    assert [m.text for m in zero if m.value == 0] == ["0.0%"] * 6
    gap = _dr2("fixture_ebitda_missing").figures[0].chart.marks
    assert sum(1 for m in gap if m.value is None) == 6 and all(
        m.text.startswith("∅ G") for m in gap if m.value is None
    )


def test_equity_has_no_mark_and_no_twin_cell() -> None:
    chart = _dr2("positive").figures[0].chart
    assert {m.label for m in chart.marks} == {
        "Senior secured term loan",
        "Trade payables",
        "Other current liabilities",
    }
    assert [r.label for r in chart.table_twin.rows] == [
        "Senior secured term loan",
        "Trade payables",
        "Other current liabilities",
    ]


def test_tabs_are_unchanged_behind_the_figure() -> None:
    block = _dr2("positive")
    assert block.tab_label == _label(RENDER["primary_tab"])
    assert [t.label for t in block.tabs] == [_label(t) for t in RENDER["tabs"]]


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_the_hatched_marks_draw_the_hatch_pattern_in_the_svg(case: str) -> None:
    figure = _dr2(case).figures[0]
    svg = charts.render_svg(figure.chart, chart_id="dr2", title=figure.title)
    assert "hatch-dr2-s1" in svg


def test_a_mark_whose_multiple_is_sourced_is_not_hatched() -> None:
    module = support.composer_module("positive")
    sourced = module.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"value_class": "source"}) if f.field == "multiple" else f
                for f in module.facts
            )
        }
    )
    chart = _block(support.report_of(support.view_with(sourced))).figures[0].chart
    assert not any(m.hatched for m in chart.marks)


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_the_settled_owner_head_renders_the_same_marks(case: str, tmp_path: Path) -> None:
    module = support.settled_module(tmp_path, case)
    chart = _block(support.report_of(support.view_with(module, case))).figures[0].chart
    assert [(m.series, m.label, support.unbound(m.text), m.hatched) for m in chart.marks] == [
        (w["series"], w["category"], w["shown"], w["hatched"]) for w in RECORDS[case]["points"]
    ]


def test_no_cp4c_head_means_no_figure_and_the_honest_state() -> None:
    run = support.view_with(support.composer_module("positive")).run
    block = _block(support.report_of(support.empty_view(run, candidate=False)))
    assert block.figures == () and block.state != "populated" and block.note


def test_a_blocked_producer_shows_its_first_limitation_and_no_figure(tmp_path: Path) -> None:
    store, _pack, first = support.connect.seed(tmp_path)
    support.connect._submit(store, first, support.stage1._refusal_text("r01"))
    second = store.begin("CP-4C")
    support.connect._submit(store, second, support.stage1._refusal_text("v13"))
    module = support.store_module(store, "CP-4C")
    view = support.view_with(module)
    assert module.status == "blocked"
    block = _block(support.report_of(view))
    assert block.figures == () and block.state == "blocked"
    assert block.note is not None and module.limitations[0] in block.note


def test_a_blocked_cp2g_leaves_cp4c_unrun_and_the_block_without_a_figure(tmp_path: Path) -> None:
    store, _pack, _attempt = support.connect.seed(tmp_path, cp2g_blocked=True)
    view = support.view_with(
        support.store_module(store, "CP-4C"), extra=(support.store_module(store, "CP-2G"),)
    )
    assert support.store_module(store, "CP-2G").status == "blocked"
    block = _block(support.report_of(view))
    assert block.figures == () and block.state != "populated" and block.note
