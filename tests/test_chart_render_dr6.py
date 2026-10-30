"""DR.6 (CP-2H rating trigger headroom): the n/a frame through ``report_view.build``.

Expectations come from ``cases/charts/dr6-expected.json``. The frame draws no T2R.4 or T2R.5
mark: the reason is true for the case (item 8 M1) and, where settled facts are missing, carries
their report ``G<n>`` bound at run time. The two owner runs are real CP-2H stores.
"""

import re
from pathlib import Path
from typing import Any

import chart_dr_support as support
import pytest
import test_connect_cp2h as connect
import test_method_cp2h as stage1

from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Fact
from deploy_vii.render import empty_view
from deploy_vii.report_view import Block, ReportView, build, pathways

ORACLE = support.oracle("dr6")
CASES = ORACLE["cases"]
RENDER = ORACLE["render"]["distressed_restructuring"]
FRAMES = RENDER["frame_texts"]["per_case"]
BLOCK_ID = RENDER["block_id"]
FRAME = ORACLE["chart_series"]["DR.6"]


def _report(view: Any) -> ReportView:
    return build(view, next(p for p in pathways() if p.id == view.run.pathway), SHIPPED_MAPS)


def _block(report: ReportView) -> Block:
    return {b.block_id: b for b in report.blocks}[BLOCK_ID]


def _settled(case: str, tmp_path: Path) -> tuple[ReportView, Any]:
    store, _pack, _attempt, _done = connect.settled(tmp_path, case)
    view = store.view()
    return _report(view), next(m for m in view.modules if m.module_id == "CP-2H")


def _g_of(report: ReportView, fact_id: str) -> str:
    entry = next(e for e in report.index.facts if e.coord.fact_id == fact_id)
    return next(r for r in entry.ref_ids if r.startswith("G"))


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_the_block_holds_the_one_na_frame_with_no_mark_and_an_empty_twin(
    case: str, tmp_path: Path
) -> None:
    report, _module = _settled(case, tmp_path)
    block = _block(report)
    assert (block.owner, block.kind, block.state) == (RENDER["owner"], "dense", "populated")
    assert len(block.figures) == 1
    figure = block.figures[0]
    assert (figure.fig_id, figure.title, figure.placement) == ("DR.6", FRAME["title"], "above")
    assert RENDER["figure"]["chart_kind"] == figure.chart.kind == "na"
    assert figure.chart.marks == () and figure.chart.series == ()
    assert figure.chart.unit_class == FRAME["unit_class"]
    assert figure.chart.table_twin.rows == () and figure.chart.table_twin.state == "absent"


def test_positive_reason_is_the_oracle_text_without_a_gap_reference(tmp_path: Path) -> None:
    report, _module = _settled("positive", tmp_path)
    reason = _block(report).figures[0].chart.reason
    assert reason == FRAMES["positive"]["reason"] == CASES["positive"]["frame_reason"]
    assert not re.search(r"G\d+", reason or "")
    assert FRAMES["positive"]["reference"] is None


def test_gap_reason_starts_with_the_oracle_text_and_cites_the_settled_gaps(
    tmp_path: Path,
) -> None:
    report, module = _settled("gap", tmp_path)
    reason = _block(report).figures[0].chart.reason or ""
    assert reason.startswith(FRAMES["gap"]["reason"])
    cited = CASES["gap"]["cited_gap_fact_ids"]
    missing = sorted(
        f.fact_id
        for f in module.facts
        if f.table_id in ("T2R.4", "T2R.5") and f.status == "missing"
    )
    assert missing == sorted(cited) == sorted(CASES["gap"]["gap_fact_ids_in_module"])
    wanted = {_g_of(report, fact_id) for fact_id in cited}
    assert set(re.findall(r"∅ (G\d+)", reason)) == wanted
    assert len(re.findall(r"∅ G\d+", reason)) == len(wanted)


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_no_t2r_4_or_t2r_5_fact_is_a_point_or_companion_of_the_frame(
    case: str, tmp_path: Path
) -> None:
    report, _module = _settled(case, tmp_path)
    figure = _block(report).figures[0]
    payload = figure.model_dump_json()
    assert not [f for f in CASES[case]["forbidden_mark_fact_ids"] if f in payload]
    assert len(CASES[case]["forbidden_mark_fact_ids"]) == CASES[case]["forbidden_count"]


def test_the_reason_follows_the_settled_gaps_not_the_case_name(tmp_path: Path) -> None:
    store, _pack, _attempt, _done = connect.settled(tmp_path, "positive")
    view = store.view()
    module = next(m for m in view.modules if m.module_id == "CP-2H")
    hole = next(f for f in module.facts if f.fact_id == "T2R.4.t01.headroom")
    gap = Fact(
        **{
            **hole.model_dump(),
            "status": "missing",
            "amount": None,
            "text": None,
            "limitation": "Not stated in the agency source",
        }
    )
    changed = module.model_copy(
        update={"facts": tuple(gap if f.fact_id == hole.fact_id else f for f in module.facts)}
    )
    view = view.model_copy(
        update={"modules": tuple(changed if m.module_id == "CP-2H" else m for m in view.modules)}
    )
    report = _report(view)
    reason = _block(report).figures[0].chart.reason or ""
    assert reason.startswith(FRAMES["gap"]["reason"])
    assert f"∅ {_g_of(report, hole.fact_id)}" in reason
    assert len(re.findall(r"∅ G\d+", reason)) == 1


def test_tabs_are_unchanged_behind_the_frame(tmp_path: Path) -> None:
    report, _module = _settled("positive", tmp_path)
    block = _block(report)
    labels = {
        e.fact_coord.table_id: e.label
        for m in SHIPPED_MAPS
        if m.module_id == "CP-2H"
        for e in m.entries
    }
    assert block.tab_label == labels[RENDER["primary_tab"]]
    assert [t.label for t in block.tabs] == [labels[t] for t in RENDER["tabs"]]


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_the_block_shows_the_not_computable_chip(case: str, tmp_path: Path) -> None:
    """The oracle target 'the block shows the chip text Not computable' (OI-13): the producer
    sets ``Figure.status_chip`` beside ``reason`` on the n/a frame, in both oracle cases."""
    report, _module = _settled(case, tmp_path)
    assert FRAME["status_chip"] == "Not computable"
    block = _block(report)
    assert [f.status_chip for f in block.figures] == [FRAME["status_chip"]]
    assert FRAME["status_chip"] in block.model_dump_json()


def test_only_the_na_frame_carries_a_chip(tmp_path: Path) -> None:
    report, _module = _settled("positive", tmp_path)
    chipped = [(b.block_id, f.fig_id) for b in report.blocks for f in b.figures if f.status_chip]
    assert chipped == [(BLOCK_ID, "DR.6")]


def test_no_cp2h_head_means_no_frame_and_the_honest_state() -> None:
    run = support.view_with(support.composer_module("positive")).run
    block = _block(_report(empty_view(run, candidate=False)))
    assert block.figures == () and block.state != "populated" and block.note
    assert FRAME["status_chip"] not in block.model_dump_json()


def test_a_blocked_producer_shows_its_first_limitation_and_no_frame(tmp_path: Path) -> None:
    store, _pack, first = connect.seed(tmp_path)
    connect._submit(store, first, connect._refusal_text("r01", connect._cp1(store)))
    second = store.begin("CP-2H")
    connect._submit(store, second, connect._refusal_text("v08", connect._cp1(store)))
    view = store.view()
    module = next(m for m in view.modules if m.module_id == "CP-2H")
    assert module.status == "blocked"
    block = _block(_report(view))
    assert block.figures == () and block.state == "blocked"
    assert FRAME["status_chip"] not in block.model_dump_json()
    assert block.note is not None and module.limitations[0] in block.note


def test_a_blocked_cp2g_leaves_cp2h_unrun_and_the_block_without_a_frame(tmp_path: Path) -> None:
    pack = connect._pack("gap")
    store = connect.Execution.create(tmp_path / "store", pack)
    connect._finish(
        store, "CP-0", tuple(connect._command(m) for m in ("CP-1", "CP-2A", "CP-2G", "CP-2H")), None
    )
    connect._finish(store, "CP-1", (*stage1.cp1_facts("gap"), connect._decoy()), None)
    connect._finish(store, "CP-2A", (), None)
    for _ in range(2):
        ticket = store.begin("CP-2G")
        store.finish(ticket.ticket_id, "{}", lambda _m: ("refused",))
    block = _block(_report(store.view()))
    assert block.figures == () and block.state != "populated" and block.note
