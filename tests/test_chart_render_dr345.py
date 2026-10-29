"""DR.3-5 (CP-4C value allocation waterfalls) through ``report_view.build``.

Marks, twin rows and render facts come from ``cases/charts/dr345-expected.json``. The block is
``value-allocation-claims`` (owner CP-4C, kind dense); DR.3, DR.4 and DR.5 sit above the tabs in
scenario row order.
"""

import re
from decimal import Decimal
from pathlib import Path

import chart_dr_support as support
import pytest

from deploy_vii import charts
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.report_view import Block, Figure, ReportView

ORACLE = support.oracle("dr345")
RECORDS = ORACLE["chart_series"]["DR.3-5"]
TWINS = ORACLE["table_twins"]
RENDER = ORACLE["render"]["distressed_restructuring"]
BLOCK_ID = RENDER["block_id"]
FIG_IDS = ["DR.3", "DR.4", "DR.5"]


def _label(table_id: str) -> str:
    return next(
        e.label
        for m in SHIPPED_MAPS
        for e in m.entries
        if m.module_id == "CP-4C" and e.fact_coord.table_id == table_id
    )


def _block(report: ReportView) -> Block:
    return {b.block_id: b for b in report.blocks}[BLOCK_ID]


def _dr345(case: str) -> Block:
    return _block(support.report_of(support.view_with(support.composer_module(case), case)))


def _by_id(block: Block) -> dict[str, Figure]:
    return {f.fig_id or "": f for f in block.figures}


@pytest.mark.parametrize("case", support.CASES)
def test_block_holds_the_three_figures_in_order_each_above(case: str) -> None:
    block = _dr345(case)
    assert (block.owner, block.kind, block.state) == (RENDER["owner"], "dense", "populated")
    assert [f.fig_id for f in block.figures] == FIG_IDS == [f["fig_id"] for f in RENDER["figures"]]
    for figure in block.figures:
        want = RECORDS[case][figure.fig_id or ""]
        assert (figure.placement, figure.title) == ("above", want["title"])
        assert figure.chart.kind == want["kind"]
        assert (figure.chart.unit, figure.chart.unit_class) == ("US$ m", "amount")
        assert list(figure.chart.series) == want["series"]
        assert figure.chart.reason == want["reason"]


@pytest.mark.parametrize("case", support.CASES)
def test_marks_are_the_settled_two_decimal_texts_with_the_oracle_roles(case: str) -> None:
    for fig_id, figure in _by_id(_dr345(case)).items():
        want = RECORDS[case][fig_id]["points"]
        marks = figure.chart.marks
        assert [
            (m.series, m.label, support.unbound(m.text), m.role, m.value is None, m.hatched)
            for m in marks
        ] == [
            (w["series"], w["category"], w["shown"], w["role"], w["state"] == "gap", True)
            for w in want
        ]
        for mark, w in zip(marks, want, strict=True):
            if w["state"] == "known":
                assert mark.value == Decimal(w["value"]) and mark.decimals == 2
            else:
                assert mark.ref_id is not None and re.fullmatch(r"G\d+", mark.ref_id)
                assert mark.text == f"∅ {mark.ref_id}"


def test_the_two_decimal_text_is_accepted_for_the_exact_repeating_value() -> None:
    marks = _by_id(_dr345("positive"))["DR.4"].chart.marks
    trade = next(m for m in marks if m.label == "Trade payables")
    assert trade.text == "3.75" and trade.value == Decimal(
        RECORDS["positive"]["DR.4"]["points"][1]["value"]
    )
    assert trade.value != Decimal("3.75") and trade.decimals == 2


@pytest.mark.parametrize("case", support.CASES)
def test_table_twin_rows_equal_the_oracle(case: str) -> None:
    for fig_id, figure in _by_id(_dr345(case)).items():
        twin = figure.chart.table_twin
        want = TWINS[case][fig_id]
        assert [twin.row_header, *twin.columns] == want["columns"]
        assert [row.label for row in twin.rows] == [r["label"] for r in want["rows"]]
        assert [[support.unbound(c.text) for c in row.cells] for row in twin.rows] == [
            r["cells"] for r in want["rows"]
        ]


def test_zero_and_gap_steps_are_told_apart() -> None:
    zero = _by_id(_dr345("fixture_ev_zero"))["DR.4"].chart.marks
    assert all(m.value == 0 and m.text == "0.00" for m in zero)
    gap = _by_id(_dr345("gap"))["DR.3"].chart.marks
    assert [m.value is None for m in gap] == [False, True, True, True, True, False]


def test_the_na_frame_keeps_its_gap_marks_and_the_module_reason() -> None:
    stress = _by_id(_dr345("gap"))["DR.5"].chart
    assert (
        stress.kind == "na" and stress.reason == "Not calculable: the EV multiple was not assessed"
    )
    assert len(stress.marks) == 6 and all(m.value is None for m in stress.marks)


def test_tabs_are_unchanged_behind_the_figures() -> None:
    block = _dr345("positive")
    assert block.tab_label == _label(RENDER["primary_tab"])
    assert [t.label for t in block.tabs] == [_label(t) for t in RENDER["tabs"]]


@pytest.mark.parametrize("case", support.CASES)
def test_every_figure_draws_as_svg(case: str) -> None:
    for fig_id, figure in _by_id(_dr345(case)).items():
        svg = charts.render_svg(figure.chart, chart_id=fig_id.replace(".", ""), title=figure.title)
        assert svg.startswith("<svg")
    positive = _by_id(_dr345("positive"))["DR.4"]
    svg = charts.render_svg(positive.chart, chart_id="dr4", title=positive.title)
    assert "running total 53.75" in svg


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_the_settled_owner_head_renders_the_same_marks(case: str, tmp_path: Path) -> None:
    module = support.settled_module(tmp_path, case)
    block = _block(support.report_of(support.view_with(module, case)))
    for fig_id, figure in _by_id(block).items():
        assert [(m.label, support.unbound(m.text)) for m in figure.chart.marks] == [
            (w["category"], w["shown"]) for w in RECORDS[case][fig_id]["points"]
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
