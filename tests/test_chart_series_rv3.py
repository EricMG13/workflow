"""RV.3 (CP-1C) producer: the points of ``cases/charts/rv3-expected.json`` from the settled view.

Every expected value is read from the frozen oracle. The CP-1C module is the Stage 1 composer's
output for the oracle case (``test_connect_cp1c._module``), so a producer that returned a constant
equal to the oracle would still fail the varied-fact tests at the end.
"""

import json
import re
from decimal import Decimal
from pathlib import Path

import pytest
import test_connect_cp1c as cp1c

from deploy_vii import report_view
from deploy_vii.report_view import Figure, build_index

ORACLE = json.loads(
    (Path(__file__).parents[1] / "cases" / "charts" / "rv3-expected.json").read_text()
)
MODULE = "CP-1C"
BLOCK = "peer-positioning"


def _produce(case, module=None):
    module = module or cp1c._module(case)
    view = cp1c._view(case, module, mode="accepted")
    _, index = build_index(view)
    refs = report_view._refs_by_fact(index)
    producer, pathways_ = report_view._FIGURE_PRODUCERS[BLOCK]
    assert pathways_ == frozenset({"relative_value"})
    return producer(BLOCK, view, refs), refs


def _strip_refs(label):
    return re.sub(r" \[[A-Z]\d+\]", "", re.sub(r"G\d+", "G#", label))


def test_the_producer_is_registered_once_on_the_block_for_relative_value_only():
    assert BLOCK in report_view._FIGURE_PRODUCERS


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_figures_are_the_two_panels_in_order(case):
    figures, _ = _produce(case)
    want = ORACLE["cases"][case]["chart_series"]
    assert [f.fig_id for f in figures] == [w["fig_id"] for w in want] == ["RV.3a", "RV.3b"]
    for figure, panel in zip(figures, want, strict=True):
        assert isinstance(figure, Figure)
        assert figure.title == panel["title"] == "Peer positioning"
        assert figure.placement == "above"
        chart = figure.chart
        assert chart.kind == panel["kind"] == "range"
        assert (chart.unit_class, chart.unit) == (panel["unit_class"], panel["unit"])
        assert chart.series == tuple(panel["series"])
        assert chart.reason is None


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_marks_equal_the_oracle_points_in_order(case):
    figures, refs = _produce(case)
    for figure, panel in zip(figures, ORACLE["cases"][case]["chart_series"], strict=True):
        marks = figure.chart.marks
        assert len(marks) == len(panel["points"])
        for mark, point in zip(marks, panel["points"], strict=True):
            assert (mark.series, mark.label) == (point["series"], point["category"])
            assert mark.text == point["shown"] or point["state"] == "gap"
            assert mark.hatched is False
            known_refs = refs[(MODULE, point["fact_id"])]
            assert mark.ref_id in known_refs
            if point["state"] == "gap":
                assert mark.value is None
                assert re.fullmatch(r"∅ G\d+", mark.text)
                assert mark.ref_id.startswith("G") and mark.text == f"∅ {mark.ref_id}"
                assert point["gap_ref_pattern"] == "∅ G\\d+"
            else:
                assert mark.value == Decimal(point["amount_exact"])
                assert mark.ref_id[0] in "CKS"


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_the_table_twin_rows_follow_the_oracle_label_parts_and_cells(case):
    figures, _ = _produce(case)
    twin = ORACLE["cases"][case]["table_twin"]
    for figure, key in zip(figures, ("percent", "multiple"), strict=True):
        rows = figure.chart.table_twin.rows
        want = twin[key]["rows"]
        assert len(rows) == len(want)
        assert figure.chart.table_twin.columns == tuple(twin[key]["columns"])
        for row, expected in zip(rows, want, strict=True):
            assert _strip_refs(row.label) == " · ".join(expected["label_parts"])
            assert _strip_refs(row.cells[0].text) == _strip_refs(expected["cell"])


def test_gap_marks_are_exactly_the_oracle_gap_facts_and_never_zero():
    figures, refs = _produce("gap")
    marks = [m for f in figures for m in f.chart.marks]
    gaps = [m for m in marks if m.value is None]
    want = ORACLE["cases"]["gap"]["gap_marks"]
    assert [(m.series, m.label) for m in gaps] == [(w["series"], w["category"]) for w in want]
    for mark, expected in zip(gaps, want, strict=True):
        assert mark.ref_id in refs[(MODULE, expected["fact_id"])]
    assert all(m.value != 0 for m in marks)


def test_an_excluded_peer_is_never_plotted_or_read():
    """The oracle's p05 is Excluded in the positive case: no mark carries its name or facts."""
    figures, _ = _produce("positive")
    labels = [m.label for f in figures for m in f.chart.marks]
    assert not any("Ellsworth" in label for label in labels)
    assert ORACLE["cases"]["positive"]["excluded_facts_never_plotted"]
    assert {
        p["state"] for f in ORACLE["cases"]["positive"]["chart_series"] for p in f["points"]
    } == {"plotted"}


def _with(module, fact_id, **updates):
    facts = tuple(f.model_copy(update=updates) if f.fact_id == fact_id else f for f in module.facts)
    return module.model_copy(update={"facts": facts})


def test_flipping_a_plotted_peer_to_excluded_removes_its_marks():
    module = _with(cp1c._module("positive"), "T1C.1.p04.included", text="Excluded")
    figures, _ = _produce("positive", module)
    labels = [m.label for f in figures for m in f.chart.marks]
    assert not any("Dunmore" in label for label in labels)
    assert sum("Calder Vale" in label for label in labels) == 4


def test_marks_follow_the_facts_not_the_oracle_constant():
    module = _with(
        cp1c._module("positive"),
        "T1C.3.issuer.ffo_to_debt",
        amount=Decimal("0.5"),
    )
    figures, _ = _produce("positive", module)
    issuer = next(m for m in figures[0].chart.marks if m.series == "Issuer" and "FFO" in m.label)
    assert (issuer.value, issuer.text) == (Decimal("0.5"), "50.0%")


def test_a_missing_peer_fact_is_a_gap_with_its_reference_not_a_zero():
    module = _with(
        cp1c._module("positive"),
        "T1C.3.p02.total_leverage_adjusted",
        status="missing",
        amount=None,
        limitation="Not calculable: removed by the test",
    )
    figures, refs = _produce("positive", module)
    mark = next(
        m
        for m in figures[1].chart.marks
        if m.label == "Total leverage (adjusted) · Brookmere Industries"
    )
    assert mark.value is None and mark.ref_id in refs[(MODULE, "T1C.3.p02.total_leverage_adjusted")]
    assert mark.text == f"∅ {mark.ref_id}"


def test_no_peers_gives_no_figure():
    module = cp1c._module("no_peers")
    figures, _ = _produce("no_peers", module)
    assert figures == ()


@pytest.mark.parametrize("status", ["blocked", "unrun", "stale"])
def test_a_module_that_is_not_shown_gives_no_figure(status):
    module = cp1c._module("positive")
    view = cp1c._view("positive", module, mode="accepted")
    view = view.model_copy(
        update={"modules": tuple(m.model_copy(update={"status": status}) for m in view.modules)}
    )
    _, index = build_index(view)
    refs = report_view._refs_by_fact(index)
    producer, _ = report_view._FIGURE_PRODUCERS[BLOCK]
    assert producer(BLOCK, view, refs) == ()


def test_a_view_without_cp1c_gives_no_figure():
    view = cp1c._view("positive", cp1c._module("positive"), mode="accepted")
    view = view.model_copy(update={"modules": ()})
    producer, _ = report_view._FIGURE_PRODUCERS[BLOCK]
    assert producer(BLOCK, view, {}) == ()
