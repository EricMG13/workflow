"""FP 04 maturity-wall block on the covenant_refinancing run, through the real S.4 producer.

Cases are the ``adversarial_cases`` of ``cases/charts/s4fp04-expected.json``; every label, text
and tab is read from that oracle.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from test_connect_cp2d import _literal, _submit, make_upstream

from deploy_vii import report_view
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import View

ORACLE = json.loads((Path(__file__).parents[1] / "cases/charts/s4fp04-expected.json").read_text())
RENDER = ORACLE["render"]
CASES = {c["case"]: c["expected"] for c in ORACLE["adversarial_cases"]}
T2E4 = ORACLE["t2e4_tab"]
POINT = ORACLE["chart_series"][0]["points"][0]


def _block(view: View):
    pathway = next(p for p in report_view.pathways() if p.id == view.run.pathway)
    blocks = {b.block_id: b for b in report_view.build(view, pathway, SHIPPED_MAPS).blocks}
    return blocks["maturity-wall"]


@pytest.fixture
def settled(tmp_path: Path) -> View:
    store, attempt = make_upstream(tmp_path, charts=True)
    _submit(store, attempt, _literal("positive"))
    return store.view()


@pytest.fixture
def cp1_only(tmp_path: Path) -> View:
    store, _ = make_upstream(tmp_path, charts=True)
    return store.view()


def _without_cp1(view: View) -> View:
    modules = tuple(m for m in view.modules if m.module_id != "CP-1")
    return View.model_construct(**{**dict(view), "modules": modules})


def _with_cp1_status(view: View, status: str) -> View:
    modules = tuple(
        m.model_copy(update={"status": status, "facts": (), "limitations": ("not settled",)})
        if m.module_id == "CP-1"
        else m
        for m in view.modules
    )
    return View.model_construct(**{**dict(view), "modules": modules})


def test_populated_block_matches_the_frozen_render(settled: View) -> None:
    block = _block(settled)
    assert block.owner == RENDER["owner"]
    assert block.kind == RENDER["block_kind"]
    assert block.state == RENDER["state"]
    assert [(f.fig_id, f.placement) for f in block.figures] == [
        (f["fig_id"], f["placement"]) for f in RENDER["figures"]
    ]
    assert block.tab_label == RENDER["primary_tab"]["label"]
    assert [t.label for t in block.tabs] == [t["label"] for t in RENDER["tabs"]]


def test_single_count_one_mark_never_doubled_by_the_fy_alias_or_t2e4(settled: View) -> None:
    assert "50" in CASES["single_count"]
    chart = _block(settled).figures[0].chart
    (mark,) = chart.marks
    assert (mark.label, mark.value, mark.text) == (
        POINT["category"],
        Decimal(POINT["amount_exact"]),
        POINT["shown"],
    )
    assert [c.text for r in chart.table_twin.rows for c in r.cells] == [POINT["shown"]]
    # The twin row label opens with the oracle's label prefix.
    prefix = ORACLE["table_twin"]["S.4"]["rows"][0]["label_parts"][0]
    assert chart.table_twin.rows[0].label.startswith(prefix)


def test_model_first_t2e4_is_a_tab_with_its_frozen_cells(settled: View) -> None:
    block = _block(settled)
    assert block.figures[0].fig_id == "S.4"
    assert block.tab_label != T2E4["table_id"] and block.tab_label != T2E4["label"]
    (tab,) = block.tabs
    assert tab.label == T2E4["label"]
    assert tab.columns == tuple(T2E4["columns"])
    assert [[c.text for c in row.cells] for row in tab.rows] == [r["cells"] for r in T2E4["rows"]]


def test_no_cp2d_figure_the_t2e4_rows_are_table_only(settled: View) -> None:
    assert CASES["no_cp2d_figure"]
    assert [f.fig_id for f in _block(settled).figures] == ["S.4"]


def test_cp2d_absent_cp1_present_shows_the_figure_and_the_register_without_tabs(
    cp1_only: View,
) -> None:
    assert CASES["cp2d_absent_cp1_present"]
    block = _block(cp1_only)
    assert [f.fig_id for f in block.figures] == ["S.4"]
    assert block.tabs == () and block.tab_label is None
    assert block.rows


@pytest.mark.parametrize("how", ["no_entry", "blocked", "stale"])
def test_cp2d_settled_cp1_not_settled_draws_the_na_frame_first(settled: View, how: str) -> None:
    assert "n/a frame" in CASES["cp2d_settled_cp1_not_settled"]
    view = _without_cp1(settled) if how == "no_entry" else _with_cp1_status(settled, how)
    block = _block(view)
    (figure,) = block.figures
    assert figure.fig_id == "S.4" and figure.chart.kind == "na"
    assert figure.chart.marks == ()
    assert "CP-1" in figure.chart.reason and "not settled" in figure.chart.reason
    # T2E.4 is the block's own register: no primary tab label, no tabs, the T2E.4 rows.
    assert block.tab_label is None and block.tabs == ()
    assert [[c.text for c in row.cells] for row in block.rows] == [r["cells"] for r in T2E4["rows"]]
