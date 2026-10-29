"""CR.1 (CP-4) through ``report_view.build`` and ``render``: the block of ``cr1-expected.json``."""

import json
import re
from pathlib import Path

import pytest
import test_connect_cp4 as cp4
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.render import render
from deploy_vii.report_view import build, pathways

ORACLE = json.loads((Path(__file__).parents[1] / "cases" / "charts" / "cr1-expected.json").read_text())
BLOCK = "covenant-tests-headroom"


def _report(case):
    pathway = next(p for p in pathways() if p.id == ORACLE["render"]["pathway"])
    view = cp4._expected_view(case)
    return view, build(view, pathway, SHIPPED_MAPS)


def _block(case):
    _, report = _report(case)
    return next(b for b in report.blocks if b.block_id == BLOCK)


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_block_shape_and_figure_equal_the_render_oracle(case):
    want = ORACLE["render"]
    block = _block(case)
    assert (block.owner, block.kind, block.state) == (want["owner"], want["kind"], want["state"])
    assert [(f.fig_id, f.placement) for f in block.figures] == [
        (f["fig_id"], f["placement"]) for f in want["figures"]
    ]
    assert block.tab_label is None and block.tabs == ()
    assert want["tabs"] == []


def test_positive_mark_texts_and_twin_cells():
    chart = _block("positive").figures[0].chart
    assert [m.text for m in chart.marks] == ["4.00x", "1.00x", "3.00x"]
    assert [c.text for r in chart.table_twin.rows for c in r.cells] == [m.text for m in chart.marks]


def test_gap_headroom_is_a_g_reference_and_the_others_are_unchanged():
    chart = _block("gap").figures[0].chart
    threshold, current, headroom = chart.marks
    assert (threshold.text, current.text) == ("4.00x", "1.00x")
    assert headroom.value is None and re.fullmatch(r"G\d+", headroom.ref_id)
    assert headroom.text == f"∅ {headroom.ref_id}"
    assert [c.text for r in chart.table_twin.rows for c in r.cells] == [m.text for m in chart.marks]


def test_the_full_html_carries_the_figure_and_the_threshold_text():
    view, report = _report("positive")
    html = render(view, report)
    assert "CR.1" in html and "Covenant tests and headroom" in html
    assert "Maximum net leverage ratio" in html


def test_a_report_with_cp4_not_shown_keeps_the_block_without_a_figure():
    view = cp4._expected_view("positive")
    view = view.model_copy(
        update={
            "modules": tuple(
                m.model_copy(update={"status": "blocked", "facts": (), "tables": ()})
                if m.module_id == "CP-4"
                else m
                for m in view.modules
            )
        }
    )
    pathway = next(p for p in pathways() if p.id == "covenant_refinancing")
    report = build(view, pathway, SHIPPED_MAPS)
    block = next(b for b in report.blocks if b.block_id == BLOCK)
    assert block.figures == ()
    assert block.state != "populated" or block.rows == ()


def test_figure_ids_are_unique_in_the_report():
    _, report = _report("positive")
    ids = [f.fig_id for b in report.blocks for f in b.figures]
    assert len(ids) == len(set(ids))
