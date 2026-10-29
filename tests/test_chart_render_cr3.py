"""CR.3 through ``report_view.build``: block funding-gap on FP 04, and the T3D.1 binding move.

Every expected value is read from ``cases/charts/cr3-expected.json`` (render, table_twins and
chart_series). CP-3C is a producer of funding-gap (rulings item 6.1), so the T3D.1 register is
bound there and no longer in refinancing-paths.
"""

import re
from decimal import Decimal

import chart_wiring_c as w
import pytest

from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.report_view import _spec_of

RENDER = w.CR3["render"]["covenant_refinancing"]


def _figure(case: str):
    block = w.block_of(w.report_of(w.cp3c_view(case)), "funding-gap")
    return block, w.figure_of(block, "CR.3")


@pytest.mark.parametrize("case", w.CR3_PACK_CASES)
def test_funding_gap_draws_cr3_beside_the_tables(case: str) -> None:
    block, figure = _figure(case)
    assert (block.owner, block.kind, block.state) == (RENDER["owner"], "dense", "populated")
    assert [f.fig_id for f in block.figures] == ["CR.3"]
    assert figure.placement == RENDER["figure"]["placement"] == "beside"
    assert figure.chart.kind == RENDER["figure"]["chart_kind"] == "grouped"
    assert figure.title == w.CR3_FIG[case]["title"]
    assert w.tab_labels(block) == w.labels_of(RENDER["primary_tab"], *RENDER["tabs_with_cp3c"])


@pytest.mark.parametrize("case", w.CR3_PACK_CASES)
def test_marks_and_twin_equal_the_oracle(case: str) -> None:
    _, figure = _figure(case)
    expected = w.CR3_FIG[case]
    marks = [(m.series, m.label, m.text, m.value) for m in figure.chart.marks]
    want = [
        (p["series"], p["category"], p["shown"], w.decimal_or_none(p["value"]))
        for p in expected["points"]
    ]
    gap_refs = [m.ref_id for m in figure.chart.marks if m.value is None]
    # a gap mark spells ∅ G<n> with n from the report's ledger; the oracle spells it ∅ G#
    for (series, label, text, value), (w_series, w_label, w_text, w_value) in zip(
        marks, want, strict=True
    ):
        assert (series, label, value) == (w_series, w_label, w_value)
        assert text == w_text or (value is None and text.startswith("∅ G"))
    assert len(gap_refs) == expected["gap_count"]
    twin = figure.chart.table_twin
    assert [twin.row_header, *twin.columns] == w.CR3["table_twins"][case]["columns"]
    flat = [text for _, cells in w.twin_rows(figure) for text in cells]
    assert flat == [m.text for m in figure.chart.marks]
    assert [label for label, _ in w.twin_rows(figure)] == [
        r["label"] for r in w.CR3["table_twins"][case]["rows"]
    ]


def test_the_gap_mark_is_spelled_from_the_reports_gap_ledger() -> None:
    figure = w.figure_of(
        w.block_of(w.report_of(w.cp3c_view("gap_minimum_cash")), "funding-gap"), "CR.3"
    )
    principal, resources = figure.chart.marks
    assert (principal.text, principal.value) == ("50", w.decimal_or_none("50"))
    assert resources.value is None
    assert resources.ref_id is not None and re.fullmatch(r"G\d+", resources.ref_id)
    assert resources.text == f"\u2205 {resources.ref_id}"


def test_a_negative_settled_resource_is_drawn_below_zero_with_the_bracket_spelling() -> None:
    view = w.cp3c_view("positive")
    module = w.module_of(view, "CP-3C")
    facts = tuple(
        f.model_copy(update={"amount": Decimal("-8.5")}) if f.fact_id == "T3D.1.r01.c7" else f
        for f in module.facts
    )
    forged = module.model_copy(update={"facts": facts})
    modules = tuple(forged if m.module_id == "CP-3C" else m for m in view.modules)
    report = w.report_of(view.model_copy(update={"modules": modules}))
    figure = w.figure_of(w.block_of(report, "funding-gap"), "CR.3")
    resources = figure.chart.marks[1]
    assert resources.value == Decimal("-8.5") and resources.text == "(9)"


def test_without_cp3c_there_is_no_figure_and_the_cp2d_tabs_stay() -> None:
    view = w.cp3c_view("positive")
    bare = w.module_of(view, "CP-3C").model_copy(
        update={"status": "unrun", "facts": (), "tables": (), "claims": (), "artifact_sha256": None}
    )
    modules = tuple(bare if m.module_id == "CP-3C" else m for m in view.modules)
    block = w.block_of(w.report_of(view.model_copy(update={"modules": modules})), "funding-gap")
    assert block.figures == ()
    assert w.tab_labels(block) == w.labels_of(RENDER["primary_tab"], *RENDER["tabs_without_cp3c"])


def test_t3d1_is_bound_to_funding_gap_only() -> None:
    cp3c_map = next(m for m in SHIPPED_MAPS if m.module_id == "CP-3C")
    blocks = {e.block_id for e in cp3c_map.entries if e.fact_coord.table_id == "T3D.1"}
    assert blocks == {"funding-gap"}
    assert _spec_of("funding-gap").producers == tuple(RENDER["producers"])
    for case in w.CR3_PACK_CASES:
        view = w.cp3c_view(case)
        assert validate_bindings(view, SHIPPED_MAPS) == ()
        report = w.report_of(view)
        paths = w.block_of(report, "refinancing-paths")
        assert w.tab_labels(paths) == w.labels_of("T3D.6", *RENDER["refinancing_paths_tabs_after"])
