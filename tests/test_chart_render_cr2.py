"""CR.2 through ``report_view.build``: block liquidity-runway on FP 04 and FP 05.

Every expected value is read from ``cases/charts/cr2-expected.json`` (render, table_twins and
chart_series). FP 05 draws the same figure when the run requests CP-2D (rulings item 6.2).
"""

import chart_wiring_c as w
import pytest

from deploy_vii.report_view import Figure


def _mark_rows(figure: Figure) -> list[tuple[str, str, str, str | None, str]]:
    return [
        (m.series, m.label, m.text, None if m.value is None else str(m.value), m.role)
        for m in figure.chart.marks
    ]


def _oracle_marks(case: str) -> list[tuple[str, str, str, str | None, str]]:
    return [
        (p["series"], p["category"], p["shown"], p["value"], p["role"])
        for p in w.CR2_FIG[case]["points"]
    ]


@pytest.mark.parametrize("case", w.CR2_CASES)
def test_fp04_runway_block_draws_cr2(case: str) -> None:
    block = w.block_of(w.report_of(w.cp2d_view(case)), "liquidity-runway")
    spec = w.CR2["render"]["covenant_refinancing"]
    assert (block.owner, block.kind, block.state) == (spec["owner"], "dense", "populated")
    (figure,) = block.figures
    assert (figure.fig_id, figure.placement) == ("CR.2", spec["figure"]["placement"])
    assert figure.chart.kind == spec["figure"]["chart_kind"] == "waterfall"
    assert figure.summary == w.CR2_FIG[case]["note"]
    assert _mark_rows(figure) == _oracle_marks(case)


@pytest.mark.parametrize("case", w.CR2_CASES)
def test_the_table_twin_equals_the_oracle_and_the_marks(case: str) -> None:
    (figure,) = w.block_of(w.report_of(w.cp2d_view(case)), "liquidity-runway").figures
    twin = w.CR2["table_twins"][case]
    assert w.twin_rows(figure) == w.oracle_twin(twin)
    flat = [text for _, cells in w.twin_rows(figure) for text in cells]
    assert flat == [m.text for m in figure.chart.marks]
    block = figure.chart.table_twin
    assert [block.row_header, *block.columns] == twin["columns"]


def test_the_long_horizon_closing_total_plots_below_zero() -> None:
    (figure,) = w.block_of(w.report_of(w.cp2d_view("long_horizon")), "liquidity-runway").figures
    closing = figure.chart.marks[-1]
    assert closing.value is not None and closing.value < 0
    assert closing.text == "(30)" and closing.role == "total"


def test_the_tabs_are_unchanged() -> None:
    block = w.block_of(w.report_of(w.cp2d_view("positive")), "liquidity-runway")
    spec = w.CR2["render"]["covenant_refinancing"]
    assert w.tab_labels(block) == w.labels_of(spec["primary_tab"], *spec["tabs"])


def test_fp05_draws_the_same_figure_when_cp2d_is_in_the_run() -> None:
    view = w.cp2d_view("positive")
    fp04 = w.figure_of(w.block_of(w.report_of(view), "liquidity-runway"), "CR.2")
    block = w.block_of(w.report_of(view, "distressed_restructuring"), "liquidity-runway")
    (fp05,) = block.figures
    for field in ("fig_id", "title", "placement", "summary"):
        assert getattr(fp05, field) == getattr(fp04, field), field
    assert fp05.chart.kind == fp04.chart.kind
    assert fp05.chart.series == fp04.chart.series
    assert _mark_rows(fp05) == _mark_rows(fp04)
    assert [m.ref_id for m in fp05.chart.marks] == [m.ref_id for m in fp04.chart.marks]
    assert w.twin_rows(fp05) == w.twin_rows(fp04)


def test_a_run_without_cp2d_has_no_figure() -> None:
    view = w.cp2d_view("positive")
    cp2d = w.module_of(view, "CP-2D")
    bare = cp2d.model_copy(
        update={"status": "unrun", "facts": (), "tables": (), "claims": (), "artifact_sha256": None}
    )
    modules = tuple(bare if m.module_id == "CP-2D" else m for m in view.modules)
    block = w.block_of(
        w.report_of(view.model_copy(update={"modules": modules})), "liquidity-runway"
    )
    assert block.figures == ()
    assert block.state != "populated"
