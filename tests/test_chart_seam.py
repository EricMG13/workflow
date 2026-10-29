"""Stage 3 chart seam (W1): each rule the frozen chart oracles name as a seam change.

Marks, units and texts come from ``cases/charts/*-expected.json``. The per-figure producers
and block wiring are W2's; these tests hold the shared seam only.
"""

import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
import test_cp1_chart_render as base
from pydantic import ValidationError

from deploy_vii import charts, report_view
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Citation, Fact, ModuleView, Run, View
from deploy_vii.render import empty_view
from deploy_vii.report_view import (
    Block,
    Cell,
    ChartMark,
    ChartSpec,
    Figure,
    Row,
    build,
    build_index,
    pathways,
)

CHARTS = Path(__file__).parents[1] / "cases" / "charts"
chart_case = base.chart_case  # the CP-1 component fixture, reused for the S.5 and dispatch tests


def _oracle(name):
    return json.loads((CHARTS / f"{name}-expected.json").read_text())


CITE = Citation(
    source_id="legal-covenants",
    source_sha256="b" * 64,
    locator="page:2",
    quote="Net leverage shall not exceed 4.00:1.00",
)


def _twin(marks, unit_class):
    rows = []
    for index, mark in enumerate(marks):
        if mark.value is None:
            cell = Cell(
                text=mark.text,
                prov="gap",
                gap_ref=mark.ref_id,
                unit_class=unit_class,
                state="gap",
            )
        else:
            ref = mark.ref_id or "C1"
            cell = Cell(
                text=mark.text,
                prov={"C": "cited", "K": "calculated", "S": "synthetic"}[ref[0]],
                ref_id=ref,
                unit_class=unit_class,
                state="known",
            )
        rows.append(Row(row_id=f"p{index}", label=f"{mark.series} · {mark.label}", cells=(cell,)))
    return Block(
        block_id="twin",
        title="Twin",
        owner="MODEL",
        state="populated",
        kind="dense",
        columns=("Value",),
        rows=tuple(rows),
    )


def _spec(kind, series, marks, unit_class, unit):
    return ChartSpec(
        kind=kind,
        series=tuple(series),
        table_twin=_twin(marks, unit_class),
        marks=tuple(marks),
        unit=unit,
        unit_class=unit_class,
    )


def _oracle_marks(points, *, decimals=None):
    """Marks from a frozen oracle's points; ``∅ G#`` gets a distinct G number per gap."""
    marks, gaps = [], 0
    for point in points:
        if point["state"] == "gap":
            gaps += 1
            marks.append(
                ChartMark(
                    series=point["series"],
                    label=point["category"],
                    text=f"∅ G{gaps}",
                    ref_id=f"G{gaps}",
                )
            )
        else:
            marks.append(
                ChartMark(
                    series=point["series"],
                    label=point["category"],
                    text=point["shown"],
                    ref_id="C1",
                    value=Decimal(point["amount_exact"]),
                    decimals=decimals,
                )
            )
    return marks


# --- 1. ChartKind gains range and bullet, with geometry and table twins -----------------------


def _rv3(panel_fig, case="positive"):
    figure = next(
        item
        for item in _oracle("rv3")["cases"][case]["chart_series"]
        if item["fig_id"] == panel_fig
    )
    marks = _oracle_marks(figure["points"])
    series = list(dict.fromkeys(mark.series for mark in marks))
    return _spec("range", series, marks, figure["unit_class"], figure["unit"])


@pytest.mark.parametrize(("fig", "case"), [("RV.3a", "positive"), ("RV.3b", "positive")])
def test_range_kind_draws_one_strip_per_metric_and_every_mark_is_reachable(fig, case):
    spec = _rv3(fig, case)
    svg = charts.render_svg(spec, chart_id="rv3", title="Peer positioning")
    rows = {mark.label.split(" · ")[0] for mark in spec.marks}
    for row in rows:
        assert row in svg
    assert svg.count('class="mark"') == len(spec.marks)
    for mark in spec.marks:
        assert mark.text in svg
    assert [c.text for r in spec.table_twin.rows for c in r.cells] == [m.text for m in spec.marks]


def test_range_kind_keeps_a_gap_mark_as_a_labelled_slot_and_never_a_position():
    spec = _rv3("RV.3b", "positive")
    peers = [m for m in spec.marks if m.series == "Peers"]
    gap = peers[0].model_copy(update={"value": None, "text": "∅ G9", "ref_id": "G9"})
    marks = [gap if m is peers[0] else m for m in spec.marks]
    gapped = _spec("range", spec.series, marks, "multiple", "x")
    svg = charts.render_svg(gapped, chart_id="rv3g", title="Peer positioning")
    assert "∅ G9" in svg
    assert svg.count('class="mark"') == len(marks)


def _cr1(case):
    figure = _oracle("cr1")["cases"][case]["chart_series"][0]
    marks = _oracle_marks(figure["points"], decimals=2)
    return _spec("bullet", figure["series"], marks, "multiple", "x"), marks


def test_bullet_kind_draws_threshold_current_and_headroom_from_the_marks():
    spec, marks = _cr1("positive")
    assert [m.text for m in marks] == ["4.00x", "1.00x", "3.00x"]
    svg = charts.render_svg(spec, chart_id="cr1", title="Covenant tests and headroom")
    assert "Maximum net leverage ratio" in svg
    assert svg.count('class="mark"') == 3
    for mark in marks:
        assert mark.text in svg


def test_bullet_kind_with_a_headroom_gap_keeps_threshold_and_current_plotted():
    spec, marks = _cr1("gap")
    assert [m.value is None for m in marks] == [False, False, True]
    svg = charts.render_svg(spec, chart_id="cr1g", title="Covenant tests and headroom")
    assert svg.count('class="mark"') == 3
    assert marks[2].text in svg


def test_bullet_needs_a_threshold_and_a_current_series():
    one = [ChartMark(series="Threshold", label="Row", text="4.00x", ref_id="C1", value=Decimal(4))]
    spec = _spec("bullet", ["Threshold"], one, "multiple", "x")
    with pytest.raises(ValueError, match="bullet"):
        charts.render_svg(spec, chart_id="b", title="T")


# --- 2. ChartMark carries declared decimals; the text check passes them -----------------------


def _amount_spec(marks):
    return _spec("waterfall", ["Value allocation"], marks, "amount", "US$m")


def test_declared_decimals_let_a_two_decimal_text_pass_the_text_check():
    # DR.3-5 oracle: DR.4 "Trade payables" 3.7466... is settled as "3.75".
    value = Decimal("3.7466666666666666666666666666666666667")
    mark = ChartMark(
        series="Value allocation", label="Trade payables", text="3.75", ref_id="C1", value=value
    )
    with pytest.raises(ValidationError, match="formatted display"):
        _amount_spec([mark])  # no declared decimals: checked as today ("4")
    declared = mark.model_copy(update={"decimals": 2})
    assert _amount_spec([declared]).marks[0].text == "3.75"


def test_declared_decimals_do_not_loosen_the_check():
    value = Decimal("3.7466666666666666666666666666666666667")
    wrong = ChartMark(
        series="Value allocation",
        label="Trade payables",
        text="4",
        ref_id="C1",
        value=value,
        decimals=2,
    )
    with pytest.raises(ValidationError, match="formatted display"):
        _amount_spec([wrong])


def test_a_mark_without_decimals_is_checked_as_before():
    mark = ChartMark(series="Cash", label="Q1 25", text="8", ref_id="C1", value=Decimal("7.5"))
    assert mark.decimals is None
    assert mark.hatched is False
    assert _spec("grouped", ["Cash"], [mark], "amount", "US$m").marks[0].text == "8"


@pytest.mark.parametrize("decimals", [-1, 7])
def test_decimals_are_bounded_like_the_fact_field(decimals):
    with pytest.raises(ValidationError):
        ChartMark(series="s", label="l", text="1", ref_id="C1", value=Decimal(1), decimals=decimals)


def test_waterfall_running_total_label_uses_the_declared_decimals():
    value = Decimal("3.7466666666666666666666666666666666667")
    marks = [
        ChartMark(
            series="Value allocation",
            label="Trade payables",
            text="3.75",
            ref_id="C1",
            value=value,
            decimals=2,
        ),
        ChartMark(
            series="Value allocation",
            label="Enterprise value",
            text="3.75",
            ref_id="C2",
            value=value,
            decimals=2,
            role="total",
        ),
    ]
    svg = charts.render_svg(_amount_spec(marks), chart_id="wf", title="Value allocation")
    assert "running total 3.75" in svg


# --- 3. percent unit class and the strict-parse text path in _chart_fact_cell -----------------


def _percent_fact(**updates):
    fields = {
        "fact_id": "T1C.3.issuer.adjusted_ebitda_margin",
        "label": "Adjusted EBITDA margin",
        "table_id": "T1C.3",
        "row_id": "issuer",
        "field": "adjusted_ebitda_margin",
        "amount": Decimal("0.25"),
        "unit": "PERCENT",
        "scale": Decimal(1),
        "period": "LTM Q4 25",
        "citations": (CITE,),
    }
    return Fact(**{**fields, **updates})


def test_percent_unit_class_is_accepted_for_a_fraction_fact():
    cell = report_view._chart_fact_cell(_percent_fact(), "percent", ("C1",))
    assert (cell.text, cell.unit_class, cell.ref_id) == ("25.0%", "percent", "C1")


@pytest.mark.parametrize(
    "updates",
    [
        {"unit": "MILLIONS", "currency": "USD", "scale": Decimal(1000000)},
        {"unit": "MULTIPLE"},
        {"scale": Decimal(100)},
    ],
)
def test_percent_unit_class_refuses_other_dimensions(updates):
    with pytest.raises(ValueError, match="unsupported numeric dimensions"):
        report_view._chart_fact_cell(_percent_fact(**updates), "percent", ("C1",))


def test_percent_fact_is_refused_for_the_multiple_class():
    with pytest.raises(ValueError, match="unsupported numeric dimensions"):
        report_view._chart_fact_cell(_percent_fact(), "multiple", ("C1",))


def _threshold(text, **updates):
    fields = {
        "fact_id": "T4.9.r01.threshold",
        "label": "Threshold",
        "table_id": "T4.9",
        "row_id": "r01",
        "field": "threshold",
        "text": text,
        "citations": (CITE,),
    }
    return Fact(**{**fields, **updates})


def test_strict_text_reads_the_settled_threshold_without_arithmetic():
    fact = _threshold("4.00x")
    cell = report_view._chart_fact_cell(fact, "multiple", ("C1",), strict_text=True)
    assert (cell.text, cell.state, cell.ref_id) == ("4.00x", "known", "C1")
    mark = report_view._chart_mark(fact, cell, series="Threshold", label="Row")
    assert (mark.value, mark.decimals, mark.text) == (Decimal("4.00"), 2, "4.00x")
    spec = _spec("bullet", ["Threshold"], [mark], "multiple", "x")  # passes the text check
    assert spec.marks[0].value == Decimal("4.00")


def test_strict_text_decimals_follow_the_text_so_the_display_reproduces_it():
    fact = _threshold("4x")
    cell = report_view._chart_fact_cell(fact, "multiple", ("C1",), strict_text=True)
    mark = report_view._chart_mark(fact, cell, series="Threshold", label="Row")
    assert (mark.value, mark.decimals, mark.text) == (Decimal(4), 0, "4x")


@pytest.mark.parametrize(
    "text",
    ["4.00", ">4.00x", "4,00x", "n/a", "4.00X", " 4.00x", "4.00x ", "4.x", ".5x", "04.00x"]
    + ["1000.00x", "4.0000000x", "-4.00x", "4.00 x"],
)
def test_a_text_the_strict_parse_rejects_becomes_a_gap_never_zero(text):
    fact = _threshold(text)
    cell = report_view._chart_fact_cell(fact, "multiple", ("C1", "G7"), strict_text=True)
    assert (cell.text, cell.state, cell.gap_ref, cell.prov) == ("∅ G7", "gap", "G7", "gap")
    mark = report_view._chart_mark(fact, cell, series="Threshold", label="Row")
    assert (mark.value, mark.ref_id, mark.text) == (None, "G7", "∅ G7")


def test_a_rejected_text_without_a_gap_reference_fails_closed():
    with pytest.raises(ValueError, match="G#"):
        report_view._chart_fact_cell(_threshold(">4.00x"), "multiple", ("C1",), strict_text=True)


def test_strict_text_applies_to_known_text_facts_in_the_multiple_class_only():
    with pytest.raises(ValueError, match="strict"):
        report_view._chart_fact_cell(_threshold("4.00x"), "percent", ("C1",), strict_text=True)
    with pytest.raises(ValueError, match="strict"):
        report_view._chart_fact_cell(_percent_fact(), "multiple", ("C1",), strict_text=True)
    # Without the flag a known text fact is still refused, as before.
    with pytest.raises(ValueError, match="unsupported numeric dimensions"):
        report_view._chart_fact_cell(_threshold("4.00x"), "multiple", ("C1",))


def _cp4_view(text):
    run = Run(
        run_id="seam-cp4",
        issuer_id="northbridge-synthetic",
        issuer_name="Northbridge Synthetic Group",
        as_of=date(2026, 1, 10),
        case_kind="synthetic",
        pathway="covenant_refinancing",
        requested_modules=("CP-4",),
    )
    module = ModuleView(
        module_id="CP-4",
        title="Legal",
        aliases=(),
        status="restricted",
        artifact_sha256="c" * 64,
        facts=(_threshold(text),),
        limitations=("Component fixture",),
    )
    seed = empty_view(run, candidate=False)
    return View.model_validate(
        seed.model_copy(
            update={"modules": tuple(module if m.module_id == "CP-4" else m for m in seed.modules)}
        ).model_dump()
    )


def test_build_index_allocates_a_gap_reference_for_a_rejected_strict_text():
    _, accepted = build_index(_cp4_view("4.00x"))
    _, rejected = build_index(_cp4_view(">4.00x"))
    accepted_refs = next(
        f.ref_ids for f in accepted.facts if f.coord.fact_id == "T4.9.r01.threshold"
    )
    rejected_refs = next(
        f.ref_ids for f in rejected.facts if f.coord.fact_id == "T4.9.r01.threshold"
    )
    assert not any(ref.startswith("G") for ref in accepted_refs)
    assert [ref for ref in rejected_refs if ref.startswith("G")] == ["G1"]
    passports, _ = build_index(_cp4_view(">4.00x"))
    gap = next(p for p in passports if p.ref_id == "G1")
    assert gap.kind == "gap"


def test_build_index_leaves_other_known_text_facts_alone():
    other = _cp4_view("4.00x")
    module = other.modules[[m.module_id for m in other.modules].index("CP-4")]
    comparison = _threshold(">4.00x", fact_id="T4.9.r01.comparison", field="comparison")
    changed = module.model_copy(update={"facts": (*module.facts, comparison)})
    view = View.model_validate(
        other.model_copy(
            update={
                "modules": tuple(changed if m.module_id == "CP-4" else m for m in other.modules)
            }
        ).model_dump()
    )
    _, index = build_index(view)
    refs = next(f.ref_ids for f in index.facts if f.coord.fact_id == "T4.9.r01.comparison")
    assert not any(ref.startswith("G") for ref in refs)


# --- 4. hatching follows the fact basis -------------------------------------------------------


def test_chart_mark_is_hatched_for_an_analyst_judgment_basis_only():
    fact = _percent_fact(value_class="analyst_judgment")
    cell = report_view._chart_fact_cell(fact, "percent", ("C1",))
    assert report_view._chart_mark(fact, cell, series="s", label="l").hatched is True
    for basis in (None, "source", "normalized", "calculated"):
        plain = _percent_fact(value_class=basis)
        cell = report_view._chart_fact_cell(plain, "percent", ("C1",))
        assert report_view._chart_mark(plain, cell, series="s", label="l").hatched is False


def test_chart_mark_carries_the_facts_declared_decimals():
    fact = _percent_fact(decimals=2)
    cell = report_view._chart_fact_cell(fact, "percent", ("C1",))
    mark = report_view._chart_mark(fact, cell, series="s", label="l")
    assert (mark.decimals, mark.text) == (2, "25.00%")
    _spec("range", ["s"], [mark], "percent", "%")


def _grouped(hatched):
    marks = [
        ChartMark(
            series="Recovery",
            label="Senior",
            text="2.50x",
            ref_id="C1",
            value=Decimal("2.5"),
            decimals=2,
            hatched=hatched,
        )
    ]
    return charts.render_svg(
        _spec("grouped", ["Recovery"], marks, "multiple", "x"), chart_id="dr2", title="Recovery"
    )


def test_a_hatched_mark_draws_the_hatch_pattern_and_a_plain_one_does_not():
    assert "hatch-dr2-s1" in _grouped(True)
    assert "pattern" not in _grouped(False)


def test_hatched_waterfall_steps_use_the_stripe_pattern():
    marks = [
        ChartMark(
            series="Value allocation",
            label="Senior",
            text="50.00",
            ref_id="C1",
            value=Decimal(50),
            decimals=2,
            hatched=True,
        ),
        ChartMark(
            series="Value allocation",
            label="Enterprise value",
            text="50.00",
            ref_id="C2",
            value=Decimal(50),
            decimals=2,
            role="total",
        ),
    ]
    svg = charts.render_svg(_amount_spec(marks), chart_id="wf", title="Value allocation")
    assert "hatch-wf-wf-up" in svg
    assert "hatch-wf-wf-total" not in svg


def test_the_synthetic_reference_still_hatches_as_before():
    marks = [ChartMark(series="Cash", label="Q1 25", text="8", ref_id="S1", value=Decimal("7.5"))]
    svg = charts.render_svg(
        _spec("grouped", ["Cash"], marks, "amount", "US$m"), chart_id="syn", title="Cash"
    )
    assert "hatch-syn-s1" in svg


# --- 5. _na_strip takes a reason; a view without CP-1 degrades, never KeyError ----------------


def test_na_strip_default_reason_is_unchanged():
    (figure,) = report_view._na_strip("model-chart-strip", "MODEL", None)[3:]
    assert figure.chart.reason == "The KPI register carries no series for this chart"


def test_na_strip_names_the_reason_it_is_given():
    reason = "CP-1 is not settled in this run"
    figures = report_view._na_strip("maturity-wall", "MODEL", None, reason)
    assert [fig.fig_id for fig in figures] == ["S.4"]
    assert figures[0].chart.kind == "na"
    assert figures[0].chart.reason == reason
    assert reason in (figures[0].chart.table_twin.note or "")


def test_maturity_wall_has_one_strip_figure_and_a_cp1_not_settled_reason():
    assert report_view._STRIP_FIGURES["maturity-wall"] == (("S.4", "Maturity wall", None),)
    assert "CP-1" in report_view._strip_reason("maturity-wall")
    assert "not settled" in report_view._strip_reason("maturity-wall")
    assert report_view._strip_reason("model-chart-strip") is None


def test_maturity_wall_is_a_chart_strip_since_the_s4_wiring():
    assert report_view._spec_of("maturity-wall").kind == "chart"


def test_a_chart_block_without_a_cp1_entry_takes_the_degraded_path(tmp_path):
    import test_connect_cp2d as c2d

    store, attempt = c2d.make_upstream(tmp_path)
    c2d._submit(store, attempt, c2d._literal("positive"))
    full = store.view()
    modules = {m.module_id: m for m in full.modules}
    assert modules["CP-2D"].status in {"accepted", "restricted"}
    view = View.model_validate(
        full.model_copy(
            update={"modules": tuple(m for m in full.modules if m.module_id != "CP-1")}
        ).model_dump()
    )
    assert "CP-1" not in {m.module_id for m in view.modules}
    pathway = next(p for p in pathways() if p.id == view.run.pathway)
    block = {b.block_id: b for b in build(view, pathway, SHIPPED_MAPS).blocks}["maturity-wall"]
    assert block.figures[0].fig_id == "S.4"
    assert block.figures[0].chart.kind == "na"
    assert "CP-1" in (block.figures[0].chart.reason or "")
    assert block.tab_label is None
    assert block.tabs == ()
    assert block.rows


# --- 6. per-producer figure dispatch ----------------------------------------------------------


def _figure():
    mark = ChartMark(series="s", label="l", text="1", ref_id="C1", value=Decimal(1))
    chart = _spec("grouped", ["s"], [mark], "amount", "US$m")
    return Figure(fig_id="X.1", title="X", chart=chart, placement="beside")


def test_the_registry_holds_exactly_the_producers_of_the_four_w2_groups():
    # Every block id and pathway each group registered, in group order a, b, c, d.
    distressed = frozenset({"distressed_restructuring"})
    expected = {
        # group a: S.5 beside the financials period grid
        "financials-credit-metrics": ("_cp1_period_figures", frozenset({"credit_snapshot"})),
        # group b: RV.3 and CR.1
        "peer-positioning": ("_rv3_figures", frozenset({"relative_value"})),
        "covenant-tests-headroom": ("_cr1_figures", frozenset({"covenant_refinancing"})),
        # group c: CR.2 and CR.3 (every pathway that holds the block)
        "liquidity-runway": ("_cr2_figures", None),
        "funding-gap": ("_cr3_figures", None),
        # group d: DR.2 to DR.6
        "recovery-by-class": ("recovery_by_class_figures", distressed),
        "value-allocation-claims": ("value_allocation_figures", distressed),
        "rating-triggers": ("rating_trigger_figures", distressed),
    }
    registered = {
        block_id: (producer.__name__, pathways)
        for block_id, (producer, pathways) in report_view._FIGURE_PRODUCERS.items()
    }
    assert registered == expected
    assert list(report_view._FIGURE_PRODUCERS) == list(expected)


def test_an_empty_registry_leaves_the_dispatch_with_no_figure_of_its_own(monkeypatch, chart_case):
    """The seam holds no producer; the W2 groups register theirs at the end of ``report_view``."""
    view, _, _ = chart_case
    monkeypatch.setattr(report_view, "_FIGURE_PRODUCERS", {})
    assert report_view._registered_figures("capital-structure", "credit_snapshot", view, {}) == ()


def test_register_figure_producer_refuses_a_duplicate_and_an_unknown_pathway(monkeypatch):
    monkeypatch.setattr(report_view, "_FIGURE_PRODUCERS", {})

    def producer(block_id, view, refs):
        return ()

    report_view.register_figure_producer("capital-structure", producer)
    with pytest.raises(ValueError, match="already"):
        report_view.register_figure_producer("capital-structure", producer)
    with pytest.raises(ValueError, match="pathway"):
        report_view.register_figure_producer("red-flags", producer, pathways=frozenset({"nope"}))


def test_registered_figures_are_gated_by_pathway(monkeypatch, chart_case):
    view, _, _ = chart_case
    calls = []

    def producer(block_id, view_, refs):
        calls.append(block_id)
        return (_figure(),)

    monkeypatch.setattr(report_view, "_FIGURE_PRODUCERS", {})
    report_view.register_figure_producer(
        "financials-credit-metrics", producer, pathways=frozenset({"credit_snapshot"})
    )
    assert report_view._registered_figures("financials-credit-metrics", "credit_snapshot", view, {})
    assert (
        report_view._registered_figures("financials-credit-metrics", "earnings_update", view, {})
        == ()
    )
    assert report_view._registered_figures("capital-structure", "credit_snapshot", view, {}) == ()
    assert calls == ["financials-credit-metrics"]


def _s5_case(chart_case):
    """The CP-1 component fixture plus the S.5 facts and series of the frozen S.5 oracle."""
    view, figures, _ = chart_case
    oracle = _oracle("s5")
    cite = next(m for m in view.modules if m.module_id == "CP-1").facts[0].citations
    points, facts = [], []
    quarters = base.EXPECTED["quarters"]
    for series, caption in (("revenue", "Net revenues"), ("adjusted_ebitda", "Adjusted EBITDA")):
        for number, quarter in enumerate(quarters, 1):
            expected = next(
                p
                for p in oracle["chart_series"][0]["points"]
                if p["series"] == series and p["category"] == f"Q{number} 2025"
            )
            fact_id = f"{series}.q{number}"
            facts.append(
                Fact(
                    fact_id=fact_id,
                    label=caption,
                    table_id="T4.10",
                    row_id=series,
                    field=f"q{number}",
                    amount=Decimal(expected["amount_exact"]),
                    unit="MILLIONS",
                    currency="USD",
                    scale=Decimal(1000000),
                    period=quarter["period_id"],
                    basis="IFRS · consolidated group",
                    calculation_id=f"component:{fact_id}",
                    value_class="calculated",
                    calculation_status="Calculated",
                    citations=cite,
                )
            )
            points.append(
                base.ComponentPoint(series, f"Q{number} 25", fact_id, (f"period.q{number}",))
            )
    figures.append(
        base.ComponentFigure(
            "S.5",
            "Revenue and Adjusted EBITDA",
            "grouped",
            "amount",
            "US$m",
            ("revenue", "adjusted_ebitda"),
            tuple(points),
        )
    )
    # One income-statement fact fills the financials period grid the S.5 figure sits beside.
    statement = facts[0].model_copy(
        update={"fact_id": "income.revenue.q1", "table_id": "T4.4", "row_id": "revenue"}
    )
    modules = tuple(
        m.model_copy(update={"facts": (*m.facts, *facts, statement)})
        if m.module_id == "CP-1"
        else m
        for m in view.modules
    )
    return View.model_validate(view.model_copy(update={"modules": modules}).model_dump())


def test_s5_entry_point_builds_the_figure_from_the_oracle_series(chart_case):
    view = _s5_case(chart_case)
    _, index = build_index(view)
    refs = report_view._refs_by_fact(index)
    (figure,) = report_view._cp1_period_figures("financials-credit-metrics", view, refs)
    assert (figure.fig_id, figure.placement, figure.chart.kind) == ("S.5", "beside", "grouped")
    assert (figure.chart.unit, figure.chart.unit_class) == ("US$m", "amount")
    assert figure.chart.series == ("Net revenues", "Adjusted EBITDA")
    by_series = {}
    for mark in figure.chart.marks:
        by_series.setdefault(mark.series, []).append(mark)
    assert [m.value for m in by_series["Net revenues"]] == [Decimal(30)] * 4
    assert [m.value for m in by_series["Adjusted EBITDA"]] == [Decimal("7.5")] * 4
    assert {m.text for m in by_series["Net revenues"]} == {"30"}
    assert {m.text for m in by_series["Adjusted EBITDA"]} == {"8"}
    twin = [c.text for r in figure.chart.table_twin.rows for c in r.cells]
    assert twin == [m.text for m in figure.chart.marks]


def test_s5_entry_point_is_empty_when_the_producer_supplies_no_s5(chart_case):
    view, _, _ = chart_case
    _, index = build_index(view)
    refs = report_view._refs_by_fact(index)
    assert report_view._cp1_period_figures("financials-credit-metrics", view, refs) == ()


def test_s5_gap_fact_is_a_gap_mark_never_zero(chart_case):
    view = _s5_case(chart_case)
    modules = tuple(
        m.model_copy(
            update={
                "facts": tuple(
                    f.model_copy(
                        update={
                            "amount": None,
                            "status": "missing",
                            "citations": (),
                            "limitation": "Not supplied",
                        }
                    )
                    if f.fact_id == "adjusted_ebitda.q2"
                    else f
                    for f in m.facts
                )
            }
        )
        if m.module_id == "CP-1"
        else m
        for m in view.modules
    )
    view = View.model_validate(view.model_copy(update={"modules": modules}).model_dump())
    _, index = build_index(view)
    refs = report_view._refs_by_fact(index)
    (figure,) = report_view._cp1_period_figures("financials-credit-metrics", view, refs)
    gap = next(m for m in figure.chart.marks if m.value is None)
    assert re.fullmatch(r"∅ G\d+", gap.text) and gap.ref_id == gap.text[2:]
    assert sum(m.value is not None for m in figure.chart.marks) == 7


def test_s5_period_grid_block_holds_the_registered_figure_beside(monkeypatch, chart_case):
    view = _s5_case(chart_case)
    monkeypatch.setattr(report_view, "_FIGURE_PRODUCERS", {})
    report_view.register_figure_producer(
        "financials-credit-metrics",
        report_view._cp1_period_figures,
        pathways=frozenset({"credit_snapshot"}),
    )
    pathway = next(p for p in pathways() if p.id == view.run.pathway)
    blocks = {b.block_id: b for b in build(view, pathway, SHIPPED_MAPS).blocks}
    block = blocks["financials-credit-metrics"]
    assert block.kind == "period_grid"
    assert [f.fig_id for f in block.figures] == ["S.5"]
    assert block.figures[0].placement == "beside"
    # S.1 to S.4 in the strip are unchanged by the S.5 data (regression).
    assert [f.fig_id for f in blocks["model-chart-strip"].figures] == ["S.1", "S.2", "S.3", "S.4"]


def test_s5_is_not_drawn_on_earnings_update(monkeypatch, chart_case):
    view = _s5_case(chart_case)
    monkeypatch.setattr(report_view, "_FIGURE_PRODUCERS", {})
    report_view.register_figure_producer(
        "financials-credit-metrics",
        report_view._cp1_period_figures,
        pathways=frozenset({"credit_snapshot"}),
    )
    update = view.model_copy(
        update={"run": view.run.model_copy(update={"pathway": "earnings_update"})}
    )
    update = View.model_validate(update.model_dump())
    pathway = next(p for p in pathways() if p.id == "earnings_update")
    blocks = {b.block_id: b for b in build(update, pathway, SHIPPED_MAPS).blocks}
    block = blocks["financials-credit-metrics"]
    assert block.state == "populated"
    assert block.rows
    assert block.figures == ()
    # Control: the same producer registered for every Pathway does draw S.5 here.
    monkeypatch.setattr(report_view, "_FIGURE_PRODUCERS", {})
    report_view.register_figure_producer(
        "financials-credit-metrics", report_view._cp1_period_figures
    )
    ungated = {b.block_id: b for b in build(update, pathway, SHIPPED_MAPS).blocks}
    assert [f.fig_id for f in ungated["financials-credit-metrics"].figures] == ["S.5"]
