"""CR.1 (CP-4) producer: the points of ``cases/charts/cr1-expected.json`` from the settled view.

The CP-4 module is the Stage 1 composer's output for the oracle case
(``test_connect_cp4._expected_view``). The threshold is a settled text read by the strict parse;
the varied-fact tests at the end keep a constant equal to the oracle from passing.
"""

import json
import re
from decimal import Decimal
from pathlib import Path

import pytest
import test_connect_cp4 as cp4
from deploy_vii import report_view
from deploy_vii.report_view import Figure, build_index

ORACLE = json.loads(
    (Path(__file__).parents[1] / "cases" / "charts" / "cr1-expected.json").read_text()
)
MODULE = "CP-4"
BLOCK = "covenant-tests-headroom"


def _module_of(view):
    return next(m for m in view.modules if m.module_id == MODULE)


def _edit(view, **per_fact):
    """The view with the named facts updated (fact id to the field updates)."""
    module = _module_of(view)
    facts = tuple(
        f.model_copy(update=per_fact[f.fact_id]) if f.fact_id in per_fact else f
        for f in module.facts
    )
    changed = module.model_copy(update={"facts": facts})
    return view.model_copy(
        update={"modules": tuple(changed if m is module else m for m in view.modules)}
    )


def _produce(view):
    _, index = build_index(view)
    refs = report_view._refs_by_fact(index)
    producer, pathways_ = report_view._FIGURE_PRODUCERS[BLOCK]
    assert pathways_ == frozenset({"covenant_refinancing"})
    return producer(BLOCK, view, refs), refs


def _strip_refs(label):
    return re.sub(r" \[[A-Z]\d+\]", "", re.sub(r"G\d+", "G#", label))


def test_the_producer_is_registered_on_the_block():
    assert BLOCK in report_view._FIGURE_PRODUCERS


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_the_figure_is_the_oracle_record(case):
    figures, _ = _produce(cp4._expected_view(case))
    want = ORACLE["cases"][case]["chart_series"][0]
    assert len(figures) == 1
    figure = figures[0]
    assert isinstance(figure, Figure)
    assert (figure.fig_id, figure.title, figure.placement) == ("CR.1", want["title"], "beside")
    chart = figure.chart
    assert chart.kind == want["kind"] == "bullet"
    assert (chart.unit_class, chart.unit) == (want["unit_class"], want["unit"])
    assert chart.series == tuple(want["series"]) == ("Threshold", "Current", "Headroom")
    assert chart.reason is None


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_marks_equal_the_oracle_points(case):
    figures, refs = _produce(cp4._expected_view(case))
    want = ORACLE["cases"][case]["chart_series"][0]["points"]
    marks = figures[0].chart.marks
    assert len(marks) == len(want)
    for mark, point in zip(marks, want, strict=True):
        assert (mark.series, mark.label) == (point["series"], point["category"])
        assert mark.ref_id in refs[(MODULE, point["fact_id"])]
        assert mark.hatched is False
        if point["state"] == "gap":
            assert mark.value is None
            assert mark.text == f"∅ {mark.ref_id}" and mark.ref_id.startswith("G")
            assert point["gap_ref_pattern"] == "∅ G\\d+"
        else:
            assert mark.value == Decimal(point["amount_exact"])
            assert mark.text == point["shown"]


def test_the_threshold_mark_carries_the_settled_text_read_by_the_strict_parse():
    figures, _ = _produce(cp4._expected_view("positive"))
    threshold = figures[0].chart.marks[0]
    point = ORACLE["cases"]["positive"]["chart_series"][0]["points"][0]
    assert point["parse_rule"] == "\\d+(\\.\\d+)?x" and point["settled_text"] == "4.00x"
    assert (threshold.text, threshold.value, threshold.decimals) == ("4.00x", Decimal("4.00"), 2)


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_the_table_twin_rows_follow_the_oracle(case):
    figures, _ = _produce(cp4._expected_view(case))
    twin = ORACLE["cases"][case]["table_twin"]["CR.1"]
    rows = figures[0].chart.table_twin.rows
    assert len(rows) == len(twin["rows"])
    assert figures[0].chart.table_twin.columns == tuple(twin["columns"])
    for row, expected in zip(rows, twin["rows"], strict=True):
        assert _strip_refs(row.label) == " · ".join(expected["label_parts"])
        assert _strip_refs(row.cells[0].text) == _strip_refs(expected["cell"])


def test_the_gap_run_has_one_gap_mark_the_headroom_and_never_a_number():
    figures, refs = _produce(cp4._expected_view("gap"))
    marks = figures[0].chart.marks
    gaps = [m for m in marks if m.value is None]
    want = ORACLE["cases"]["gap"]["gap_marks"]
    assert [(m.series, m.label) for m in gaps] == [(w["series"], w["category"]) for w in want]
    assert gaps[0].ref_id in refs[(MODULE, "T4.9.r01.headroom")]
    assert not any(m.text in {"3.00x", "75.0%"} for m in marks)
    assert [m.text for m in marks[:2]] == ["4.00x", "1.00x"]


@pytest.mark.parametrize("text", ["4.00", ">4.00x", "4,00x", "", "n/a", "04.00x", "4.00 x"])
def test_a_threshold_text_the_parse_rejects_is_a_gap_with_its_reference(text):
    view = _edit(cp4._expected_view("positive"), **{"T4.9.r01.threshold": {"text": text}})
    figures, refs = _produce(view)
    marks = figures[0].chart.marks
    assert marks[0].value is None and marks[0].series == "Threshold"
    assert marks[0].ref_id.startswith("G") and marks[0].text == f"∅ {marks[0].ref_id}"
    assert marks[0].ref_id in refs[(MODULE, "T4.9.r01.threshold")]
    assert [m.text for m in marks[1:]] == ["1.00x", "3.00x"]


def test_marks_follow_the_facts_not_the_oracle_constant():
    view = _edit(
        cp4._expected_view("positive"),
        **{
            "T4.9.r01.threshold": {"text": "5.25x"},
            "T4.9.r01.current": {"amount": Decimal("2.5")},
            "T4.9.r01.headroom": {"amount": Decimal("2.75")},
        },
    )
    figures, _ = _produce(view)
    marks = figures[0].chart.marks
    assert [(m.text, m.value) for m in marks] == [
        ("5.25x", Decimal("5.25")),
        ("2.50x", Decimal("2.5")),
        ("2.75x", Decimal("2.75")),
    ]


def test_a_floor_comparison_is_drawn_as_well():
    view = _edit(
        cp4._expected_view("positive"), **{"T4.9.r01.comparison": {"text": "Not less than"}}
    )
    figures, _ = _produce(view)
    assert len(figures[0].chart.marks) == 3
    assert "Comparison: Not less than" in figures[0].chart.table_twin.rows[0].label


@pytest.mark.parametrize("text", ["Greater than", "Not stated", "", "not more than"])
def test_any_other_comparison_text_draws_no_row_and_the_reason_names_the_fact(text):
    view = _edit(cp4._expected_view("positive"), **{"T4.9.r01.comparison": {"text": text}})
    figures, _ = _produce(view)
    assert len(figures) == 1
    chart = figures[0].chart
    assert chart.kind == "na" and chart.marks == ()
    assert "T4.9.r01.comparison" in (chart.reason or "")


def test_no_legal_verdict_words_are_drawn():
    for case in ("positive", "gap"):
        figures, _ = _produce(cp4._expected_view(case))
        chart = figures[0].chart
        texts = [m.text for m in chart.marks] + [chart.reason or ""]
        assert not any(word in t for t in texts for word in ("Tight", "Breached", "breach"))


@pytest.mark.parametrize("status", ["blocked", "unrun", "stale"])
def test_a_cp4_that_is_not_shown_gives_no_figure(status):
    """The gap_false_same_definition first submission settles no head: no chart, no T4.9 row."""
    view = cp4._expected_view("positive")
    module = _module_of(view).model_copy(update={"status": status})
    view = view.model_copy(
        update={"modules": tuple(module if m.module_id == MODULE else m for m in view.modules)}
    )
    assert _produce(view)[0] == ()


def test_a_view_without_cp4_facts_gives_no_figure():
    view = cp4._expected_view("positive")
    module = _module_of(view).model_copy(update={"facts": (), "tables": ()})
    view = view.model_copy(
        update={"modules": tuple(module if m.module_id == MODULE else m for m in view.modules)}
    )
    assert _produce(view)[0] == ()
