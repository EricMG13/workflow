"""RV.3 (CP-1C) through ``report_view.build`` and ``render``: the block of ``rv3-expected.json``."""

import json
import re
from pathlib import Path

import pytest
import test_connect_cp1c as cp1c
import test_method_cp1c as stage1
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import ModuleView
from deploy_vii.render import render
from deploy_vii.report_view import build, pathways

ORACLE = json.loads(
    (Path(__file__).parents[1] / "cases" / "charts" / "rv3-expected.json").read_text()
)
BLOCK = "peer-positioning"


def _view(case):
    only = cp1c._view(case, cp1c._module(case), mode="accepted")
    others = tuple(
        ModuleView(module_id=m.module_id, title=m.module_id, aliases=(), status="unrun")
        for m in SHIPPED_MAPS
        if m.module_id != "CP-1C"
    )
    return only.model_copy(update={"modules": (*only.modules, *others)})


def _report(case):
    pathway = next(p for p in pathways() if p.id == ORACLE["render"]["pathway"])
    view = _view(case)
    return view, build(view, pathway, SHIPPED_MAPS)


def _block(case):
    _, report = _report(case)
    return next(b for b in report.blocks if b.block_id == BLOCK)


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_block_shape_and_figures_equal_the_render_oracle(case):
    want = ORACLE["render"]
    block = _block(case)
    assert (block.owner, block.kind, block.state) == (want["owner"], want["kind"], want["state"])
    assert [f.fig_id for f in block.figures] == [f["fig_id"] for f in want["figures"]]
    assert [f.placement for f in block.figures] == [f["placement"] for f in want["figures"]]
    assert [f.chart.unit_class for f in block.figures] == [f["panel"] for f in want["figures"]]
    assert {f.title for f in block.figures} == {"Peer positioning"}


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_tabs_are_unchanged_by_the_figures(case):
    block = _block(case)
    labels = [t["label"] for t in stage1.expected()["cases"][case]["FP03"]["blocks"][BLOCK]["tabs"]]
    assert [block.tab_label, *(t.label for t in block.tabs)] == labels


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_mark_texts_and_twin_cells_equal_the_oracle(case):
    block = _block(case)
    for figure, panel in zip(block.figures, ORACLE["cases"][case]["chart_series"], strict=True):
        chart = figure.chart
        shown = [p["shown"] for p in panel["points"]]
        got = [m.text for m in chart.marks]
        for text, want in zip(got, shown, strict=True):
            assert re.sub(r"G\d+", "G#", text) == want
        assert [c.text for r in chart.table_twin.rows for c in r.cells] == got
        gaps = [m for m in chart.marks if m.value is None]
        assert all(re.fullmatch(r"G\d+", m.ref_id) for m in gaps)


def test_the_gap_case_draws_two_gap_marks_and_the_others_plotted():
    block = _block("gap")
    gaps = [m for f in block.figures for m in f.chart.marks if m.value is None]
    assert sorted((m.series, m.label) for m in gaps) == sorted(
        (g["series"], g["category"]) for g in ORACLE["cases"]["gap"]["gap_marks"]
    )
    assert len(gaps) == 2


def test_the_full_html_carries_both_panels_with_their_marks():
    view, report = _report("positive")
    html = render(view, report)
    assert "RV.3a" in html and "RV.3b" in html and "Peer positioning" in html
    for figure in _block("positive").figures:
        assert figure.title in html


def test_no_peers_keeps_the_populated_block_without_figures():
    block = _block("no_peers")
    assert block.state == "populated"
    assert block.figures == ()


def test_figure_ids_are_unique_in_the_report():
    _, report = _report("positive")
    ids = [f.fig_id for b in report.blocks for f in b.figures]
    assert len(ids) == len(set(ids))
