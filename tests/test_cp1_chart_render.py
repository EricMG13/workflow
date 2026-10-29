"""Shared chart-consumer component checks; genuine publication/native proof is separate."""

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import pytest

from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Citation, Fact, Module, ModuleView, PathwayId, Run, View
from deploy_vii.render import empty_view, render
from deploy_vii.report_view import Block, ReportView, build, pathways

EXPECTED = json.loads((Path(__file__).parents[1] / "cases/charts/expected.json").read_text())


@dataclass(frozen=True)
class ComponentPoint:
    series: str
    category: str
    fact_id: str
    companion_fact_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ComponentFigure:
    fig_id: str
    title: str
    kind: str
    unit_class: str
    unit: str
    series: tuple[str, ...]
    points: tuple[ComponentPoint, ...]
    reason: str | None = None


ChartCase = tuple[View, list[ComponentFigure], list[Any]]


@pytest.fixture
def chart_case(monkeypatch: pytest.MonkeyPatch) -> ChartCase:
    """Typed projection seam only: values are independent literals, not a fake analyst run."""
    facts: list[Fact] = []
    definitions = (
        ("S.1", "Leverage", "multiple", "x", ("total_leverage_reported", "net_leverage_reported")),
        ("S.2", "Interest cover", "multiple", "x", ("interest_coverage_reported",)),
        ("S.3", "Liquidity", "amount", "US$ m", ("cash_closing", "undrawn_rcf", "liquidity")),
    )
    cite = Citation(
        source_id="financial",
        source_sha256=EXPECTED["source_authority"]["financial_sha256"],
        locator="page:4",
        quote="RCF commitment  0  0  0  0  0  0",
    )
    figures: list[ComponentFigure] = []
    for number, quarter in enumerate(EXPECTED["quarters"], 1):
        facts.append(
            Fact(
                fact_id=f"period.q{number}",
                label="Period ID",
                table_id="T4.14",
                row_id=f"q{number}",
                field="period_id",
                text=quarter["period_id"],
                citations=(cite,),
            )
        )
    for fig_id, title, unit_class, unit, names in definitions:
        points = []
        for number, quarter in enumerate(EXPECTED["quarters"], 1):
            for name in names:
                raw = (
                    quarter[name]["amount"]
                    if unit_class == "multiple"
                    else quarter[
                        {
                            "cash_closing": "cash_millions",
                            "undrawn_rcf": "undrawn_rcf_millions",
                            "liquidity": "liquidity_millions",
                        }[name]
                    ]
                )
                fact_id = f"{name}.q{number}"
                facts.append(
                    Fact(
                        fact_id=fact_id,
                        label=name,
                        table_id="T4.10",
                        row_id=name,
                        field=f"q{number}",
                        amount=None if raw is None else Decimal(raw),
                        status="missing" if raw is None else "known",
                        unit="MULTIPLE" if unit_class == "multiple" else "MILLIONS",
                        currency=None if unit_class == "multiple" else "USD",
                        scale=Decimal(1 if unit_class == "multiple" else 1000000),
                        period=quarter["period_id"],
                        basis="IFRS · consolidated group",
                        calculation_id=f"component:{fact_id}",
                        value_class="calculated",
                        calculation_status="Not Calculable" if raw is None else "Calculated",
                        limitation=quarter["trailing_gap"] if raw is None else None,
                        citations=() if raw is None else (cite,),
                    )
                )
                points.append(
                    ComponentPoint(name, f"Q{number} 25", fact_id, (f"period.q{number}",))
                )
        figures.append(
            ComponentFigure(fig_id, title, "line", unit_class, unit, names, tuple(points))
        )
    facts.extend(
        (
            Fact(
                fact_id="facility.principal",
                label="Principal",
                table_id="T4.18",
                row_id="term-loan",
                field="principal",
                amount=Decimal("50"),
                unit="MILLIONS",
                currency="USD",
                scale=Decimal(1000000),
                period="2025-12-31",
                citations=(cite,),
            ),
            Fact(
                fact_id="facility.maturity",
                label="Contractual maturity",
                table_id="T4.18",
                row_id="term-loan",
                field="maturity_date",
                text="2029-12-31",
                citations=(cite,),
            ),
            Fact(
                fact_id="facility.snapshot",
                label="Snapshot",
                table_id="T4.18",
                row_id="term-loan",
                field="period_id",
                text="2025-12-31",
                citations=(cite,),
            ),
        )
    )
    figures.append(
        ComponentFigure(
            "S.4",
            "Maturity wall — current principal at 2025-12-31 (not a forecast)",
            "grouped",
            "amount",
            "US$ m",
            ("Northbridge Term Loan",),
            (
                ComponentPoint(
                    "Northbridge Term Loan",
                    "2029",
                    "facility.principal",
                    ("facility.maturity", "facility.snapshot"),
                ),
            ),
            None,
        )
    )
    run = Run(
        run_id="chart-component",
        issuer_id="northbridge-synthetic",
        issuer_name="Northbridge Synthetic Group",
        as_of=date(2026, 1, 10),
        case_kind="synthetic",
        pathway="credit_snapshot",
        requested_modules=("CP-1", "CP-MODEL"),
    )
    module = ModuleView(
        module_id="CP-1",
        title="Canonical data foundation",
        aliases=(),
        status="restricted",
        artifact_sha256="a" * 64,
        facts=tuple(facts),
        limitations=("Component fixture; unaudited synthetic data",),
    )
    base = empty_view(run, candidate=False)
    view = View.model_validate(
        base.model_copy(
            update={"modules": tuple(module if m.module_id == "CP-1" else m for m in base.modules)}
        ).model_dump()
    )
    producer: Any = ModuleType("deploy_workflow.financial_series")
    calls: list[Any] = []

    def project(selected: Any) -> tuple[ComponentFigure, ...]:
        calls.append(selected)
        return tuple(figures)

    producer.cp1_chart_series = project
    monkeypatch.setitem(sys.modules, producer.__name__, producer)
    return view, figures, calls


def _report(view: View) -> ReportView:
    pathway = next(item for item in pathways() if item.id == view.run.pathway)
    return build(view, pathway, SHIPPED_MAPS)


def _strip(report: ReportView) -> Block:
    return next(block for block in report.blocks if block.block_id == "model-chart-strip")


def test_shared_consumer_replaces_na_with_four_real_figures(chart_case: ChartCase) -> None:
    view, _, calls = chart_case
    report = _report(view)
    strip = _strip(report)
    assert [figure.chart.kind for figure in strip.figures] == ["line", "line", "line", "grouped"]
    assert [figure.fig_id for figure in strip.figures] == ["S.1", "S.2", "S.3", "S.4"]
    assert calls and calls[0].artifact_sha256 == "a" * 64
    assert sum(mark.value is None for fig in strip.figures for mark in fig.chart.marks) == 9
    for figure in strip.figures:
        assert [cell.text for row in figure.chart.table_twin.rows for cell in row.cells] == [
            mark.text for mark in figure.chart.marks
        ]
        assert all(report.passport(cast(str, mark.ref_id)) for mark in figure.chart.marks)
    assert [mark.value for mark in strip.figures[3].chart.marks] == [Decimal("50")]


def _changed_fact(view: View, fact_id: str, **updates: Any) -> View:
    modules = tuple(
        module.model_copy(
            update={
                "facts": tuple(
                    fact.model_copy(update=updates) if fact.fact_id == fact_id else fact
                    for fact in module.facts
                )
            }
        )
        if module.module_id == "CP-1"
        else module
        for module in view.modules
    )
    return View.model_validate(view.model_copy(update={"modules": modules}).model_dump())


def _payload(html: str) -> Any:
    return json.loads(
        html.split('<script id="report-data" type="application/json">', 1)[1].split("</script>", 1)[
            0
        ]
    )


def test_exact_values_zero_gaps_human_labels_and_companion_dates(chart_case: ChartCase) -> None:
    view, _, _ = chart_case
    report = _report(view)
    strip = _strip(report)
    leverage, cover, liquidity, maturity = (fig.chart for fig in strip.figures)
    assert leverage.series == ("Total leverage (reported)", "Net leverage (reported)")
    assert cover.series == ("Interest cover (reported)",)
    assert liquidity.series == ("Cash", "Undrawn RCF", "Total liquidity")
    assert [m.value for m in leverage.marks if m.label == "Q4 25"] == [
        Decimal(EXPECTED["quarters"][3]["total_leverage_reported"]["amount"]),
        Decimal("1"),
    ]
    assert [m.value for m in cover.marks if m.label == "Q4 25"] == [Decimal("6")]
    assert [m.value for m in liquidity.marks if m.series == "Cash"] == [
        Decimal(q["cash_millions"]) for q in EXPECTED["quarters"]
    ]
    assert [m.value for m in liquidity.marks if m.series == "Undrawn RCF"] == [Decimal(0)] * 4
    assert all(
        cast(str, m.ref_id).startswith("G")
        for chart in (leverage, cover)
        for m in chart.marks
        if m.value is None
    )
    assert all(
        cast(str, m.ref_id).startswith("K")
        for chart in (leverage, cover, liquidity)
        for m in chart.marks
        if m.value is not None
    )
    assert "2029-12-31" in maturity.table_twin.rows[0].label
    assert "2025-12-31" in maturity.table_twin.rows[0].label
    assert "not a forecast" in strip.figures[3].title
    assert strip.note is None


@pytest.mark.parametrize("target", ["primary", "companion"])
def test_missing_or_foreign_selected_fact_refuses(chart_case: ChartCase, target: str) -> None:
    view, figures, _ = chart_case
    point = figures[0].points[0]
    point = replace(
        point,
        **(
            {"fact_id": "foreign.fact"}
            if target == "primary"
            else {"companion_fact_ids": ("foreign.fact",)}
        ),
    )
    figures[0] = replace(figures[0], points=(point, *figures[0].points[1:]))
    with pytest.raises(ValueError, match="unknown selected fact"):
        _report(view)


@pytest.mark.parametrize(
    "updates",
    [
        {"scale": Decimal(1)},
        {"currency": "EUR"},
        {"unit": "THOUSANDS"},
        {"amount": None, "text": "not a numeric value"},
        {"citations": (), "calculation_id": None},
    ],
)
def test_numeric_dimension_or_passport_mismatch_refuses(
    chart_case: ChartCase, updates: dict[str, Any]
) -> None:
    view, _, _ = chart_case
    view = _changed_fact(view, "cash_closing.q4", **updates)
    with pytest.raises(ValueError):
        _report(view)


def test_duplicate_or_undeclared_point_series_refuses(chart_case: ChartCase) -> None:
    view, figures, _ = chart_case
    original = figures[0]
    figures[0] = replace(original, points=(*original.points, original.points[0]))
    with pytest.raises(ValueError, match="cannot repeat"):
        _report(view)
    figures[0] = replace(
        original, points=(replace(original.points[0], series="undeclared"), *original.points[1:])
    )
    with pytest.raises(ValueError, match="undeclared raw series"):
        _report(view)


@pytest.mark.parametrize(
    "variant",
    [
        "missing_figure",
        "wrong_order",
        "wrong_kind",
        "wrong_unit",
        "empty_without_reason",
        "points_with_reason",
        "duplicate_series",
    ],
)
def test_malformed_producer_metadata_refuses(chart_case: ChartCase, variant: str) -> None:
    view, figures, _ = chart_case
    if variant == "missing_figure":
        figures.pop()
    elif variant == "wrong_order":
        figures.reverse()
    else:
        changes: dict[str, dict[str, Any]] = {
            "wrong_kind": {"kind": "stacked"},
            "wrong_unit": {"unit": "USD"},
            "empty_without_reason": {"points": ()},
            "points_with_reason": {"reason": "Unavailable"},
            "duplicate_series": {"series": ("same", "same")},
        }
        figures[0] = replace(figures[0], **changes[variant])
    with pytest.raises(ValueError):
        _report(view)


def test_unavailable_figure_names_real_reason_without_invented_points(
    chart_case: ChartCase,
) -> None:
    view, figures, _ = chart_case
    reason = "Four reported QUARTER identities are unavailable"
    figures[0] = replace(figures[0], points=(), reason=reason)
    report = _report(view)
    first = _strip(report).figures[0]
    assert first.chart.marks == () and first.chart.table_twin.rows == ()
    assert first.chart.reason == reason
    assert reason in cast(str, _strip(report).note)
    assert reason in render(view, report)


@pytest.mark.parametrize("status", ["candidate", "blocked", "stale"])
def test_nonsettled_cp1_never_invokes_numeric_producer(chart_case: ChartCase, status: str) -> None:
    view, _, calls = chart_case
    modules = tuple(
        m.model_copy(update={"status": status}) if m.module_id == "CP-1" else m
        for m in view.modules
    )
    view = View.model_validate(
        view.model_copy(update={"modules": modules, "mode": "candidate"}).model_dump()
    )
    report = _report(view)
    assert not calls
    assert not any(
        mark.value is not None for figure in _strip(report).figures for mark in figure.chart.marks
    )


def test_metric_strip_has_only_its_three_pathway_figures(chart_case: ChartCase) -> None:
    view, _, _ = chart_case
    run = view.run.model_copy(update={"pathway": "earnings_update"})
    view = View.model_validate(view.model_copy(update={"run": run}).model_dump())
    strip = next(b for b in _report(view).blocks if b.block_id == "metric-strip")
    assert [fig.fig_id for fig in strip.figures] == ["S.1", "S.2", "S.3"]


def test_shared_core_html_serializes_svg_marks_and_exact_twins(chart_case: ChartCase) -> None:
    view, _, _ = chart_case
    payload = _payload(render(view))
    strip = next(b for b in payload["report"]["blocks"] if b["block_id"] == "model-chart-strip")
    assert "KPI register shown as a table" not in (strip["note"] or "")
    for figure in strip["figures"]:
        chart = figure["chart"]
        assert "<svg" in chart["svg"] and 'class="mark"' in chart["svg"]
        assert [cell["text"] for row in chart["table_twin"]["rows"] for cell in row["cells"]] == [
            mark["text"] for mark in chart["marks"]
        ]
        assert all(f'data-ref="{mark["ref_id"]}"' in chart["svg"] for mark in chart["marks"])


def test_canonical_model_caller_uses_identical_shared_chart_payload(
    chart_case: ChartCase, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Component envelope-read seam; this is not actual publication authentication."""
    from deploy_vii import cp1_render

    view, _, _ = chart_case
    cp1 = next(m for m in view.modules if m.module_id == "CP-1")
    identity: dict[str, Any] = dict(
        run_id=view.run.run_id, issuer_id=view.run.issuer_id, as_of=view.run.as_of
    )
    module = Module(
        **identity,
        module_id="CP-1",
        status="restricted",
        facts=cp1.facts,
        limitations=cp1.limitations,
    )
    envelope = SimpleNamespace(run=view.run, module=module)
    monkeypatch.setattr(cp1_render, "read_cp1_envelope", lambda *_: envelope)
    store: Any = SimpleNamespace(read=lambda: SimpleNamespace(run=view.run))
    model = Module(**identity, module_id="CP-MODEL", status="accepted")
    canonical = _payload(cp1_render.model_destination_html(store, tmp_path, model))
    delivered = _payload(render(view))
    select: Callable[[Any], Any] = lambda payload: next(
        b["figures"] for b in payload["report"]["blocks"] if b["block_id"] == "model-chart-strip"
    )
    assert select(canonical) == select(delivered)


def test_raw_series_cannot_masquerade_as_a_human_caption(chart_case: ChartCase) -> None:
    view, figures, _ = chart_case
    first = figures[0]
    aliased = replace(first.points[0], series="Total leverage (reported)")
    figures[0] = replace(first, points=(aliased, *first.points[1:]))
    with pytest.raises(ValueError, match="undeclared raw series"):
        _report(view)


@pytest.mark.parametrize("provided_reason", [None, "All trailing ratios are unavailable"])
def test_all_gap_figure_names_canonical_limitations(
    chart_case: ChartCase, provided_reason: str | None
) -> None:
    view, figures, _ = chart_case
    reason = "Trailing EBITDA denominator is unavailable"
    for key in ("total_leverage_reported.q4", "net_leverage_reported.q4"):
        view = _changed_fact(view, key, amount=None, status="missing", limitation=reason)
    figures[0] = replace(figures[0], reason=provided_reason)
    report = _report(view)
    first = _strip(report).figures[0].chart
    assert first.marks and all(mark.value is None for mark in first.marks)
    assert first.reason is not None and reason in first.reason
    assert reason in cast(str, _strip(report).note)
    payload = _payload(render(view, report))
    strip = next(b for b in payload["report"]["blocks"] if b["block_id"] == "model-chart-strip")
    assert reason in strip["figures"][0]["chart"]["svg"]


def test_override_excluded_preset_module_reads_not_requested_not_outside_pathway() -> None:
    """A preset module left out by ``requested_modules`` was not requested; it is not outside."""
    run = Run(
        run_id="override-slice",
        issuer_id="northbridge-synthetic",
        issuer_name="Northbridge Synthetic Group",
        as_of=date(2026, 1, 10),
        case_kind="synthetic",
        pathway="credit_snapshot",
        requested_modules=("CP-1",),
    )
    pathway = next(item for item in pathways() if item.id == "credit_snapshot")
    assert "CP-3" in pathway.requested_modules
    blocks = {b.block_id: b for b in build(empty_view(run), pathway, SHIPPED_MAPS).blocks}
    excluded = blocks["relative-value"]  # CP-3 is in the preset, omitted by the override
    assert excluded.state == "not_run"
    assert excluded.note == "Not run: CP-3 was not requested in this run."
    assert "Not in this Pathway" not in excluded.note
    assert excluded.full_analysis_route is None  # documents behaviour; it also holds on HEAD
    # A producer outside the preset keeps the Pathway wording.
    foreign = _spec_pathway_foreign()
    assert foreign.note == "Not in this Pathway: CP-9 is not part of Credit Snapshot."


def _spec_pathway_foreign() -> SimpleNamespace:
    from deploy_vii.report_view import _honest_state, _Spec

    pathway = next(item for item in pathways() if item.id == "credit_snapshot")
    assert "CP-9" not in pathway.requested_modules
    state, note = _honest_state(
        _Spec("X", "CP-9", "prose", ("CP-9",)), {"CP-9": "not_in_pathway"}, pathway
    )
    assert state == "not_in_pathway"
    # CP-1A is not in the relative_value preset list but is in its dependency closure: an
    # override that drops it left it unrequested, not outside the Pathway.
    closure = next(item for item in pathways() if item.id == "relative_value")
    assert "CP-1A" not in closure.requested_modules
    _, closure_note = _honest_state(
        _Spec("Y", "CP-1A", "prose", ("CP-1A",)), {"CP-1A": "not_in_pathway"}, closure
    )
    assert closure_note == "Not run: CP-1A was not requested in this run."
    return SimpleNamespace(note=note)


def test_skip_link_focuses_main_without_reaching_the_hash_router() -> None:
    """``href="#workbench"`` is not a route: the default jump set the hash and routed to
    "Unknown destination", so the skip link needs a handler that focuses and stops there."""
    run = Run(
        run_id="skip-link",
        issuer_id="northbridge-synthetic",
        issuer_name="Northbridge Synthetic Group",
        as_of=date(2026, 1, 10),
        case_kind="synthetic",
    )
    html = render(empty_view(run))
    assert '<a class="skip" href="#workbench">' in html
    assert '<main id="workbench" class="workbench" tabindex="-1">' in html
    marker = 'document.querySelector("a.skip")?.addEventListener("click"'
    assert marker in html
    handler = html.split(marker, 1)[1]
    handler = handler.split("});", 1)[0]
    assert "event.preventDefault()" in handler
    assert '$("workbench").focus()' in handler


def test_loading_the_shell_at_the_skip_link_hash_is_the_default_view() -> None:
    """A URL ending in ``#workbench`` (the skip link without JS) must not route to
    "Unknown destination": the router maps it to the Front Page like ``#overview``."""
    run = Run(
        run_id="skip-hash",
        issuer_id="northbridge-synthetic",
        issuer_name="Northbridge Synthetic Group",
        as_of=date(2026, 1, 10),
        case_kind="synthetic",
    )
    html = render(empty_view(run))
    assert 'return route === "overview" || route === "workbench" ? "front" : route;' in html


def test_call_band_script_says_cp6_was_not_requested_for_the_not_requested_state() -> None:
    """The shipped call band must not say the Pathway "does not make this call" when CP-6 was
    only left out by the run's ``requested_modules`` override."""
    html = render(empty_view(_override_run("credit_snapshot", ("CP-1",))))
    marker = 'front.call_state === "not-requested"'
    assert marker in html
    branch = html.split(marker, 1)[1].split("does not make this call", 1)[0]
    assert '" CP-6 was not requested in this run."' in branch


def test_navigator_footer_groups_outside_rows_by_word() -> None:
    """One summary per word: override-excluded ("Not run") and foreign ("Not in this Pathway")
    rows must not share the first row's word and the total count."""
    html = render(empty_view(_override_run("credit_snapshot", ("CP-1",))))
    marker = "[...new Set(outside.map(row => row.word))].forEach(word => {"
    assert marker in html
    group = html.split(marker, 1)[1].split("});", 1)[0]
    assert "outside.filter(row => row.word === word)" in group
    assert "`${word} · ${group.length}`" in group
    assert "outside[0].word" not in html


def test_module_payload_word_follows_the_not_requested_rule() -> None:
    """The module payload word (shown in the shell) matches the navigator: a preset module the
    override left out reads "Not run"; a module outside the preset keeps "Not in this Pathway"."""
    html = render(empty_view(_override_run("credit_snapshot", ("CP-1",))))
    modules = {m["module_id"]: m for m in _payload(html)["modules"]}
    assert (modules["CP-6"]["status_glyph"], modules["CP-6"]["status_word"]) == ("unrun", "Not run")
    assert modules["CP-8"]["status_word"] == "Not in this Pathway"


def _override_run(pathway_id: PathwayId, requested: tuple[str, ...]) -> Run:
    return Run(
        run_id="override-call",
        issuer_id="northbridge-synthetic",
        issuer_name="Northbridge Synthetic Group",
        as_of=date(2026, 1, 10),
        case_kind="synthetic",
        pathway=pathway_id,
        requested_modules=requested,
    )


def test_call_band_under_override_reads_not_requested_not_outside_pathway() -> None:
    """CP-6 is in the credit_snapshot preset; ``requested_modules=("CP-1",)`` only left it out."""
    from deploy_vii.report_view import call_state

    run = _override_run("credit_snapshot", ("CP-1",))
    pathway = next(item for item in pathways() if item.id == "credit_snapshot")
    assert "CP-6" in pathway.requested_modules
    report = build(empty_view(run), pathway, SHIPPED_MAPS)
    assert report.call_withheld == "not_requested"
    state, words = call_state(report)
    assert state != "outside"
    assert words == ("unrun", "Not run")


def test_call_band_outside_the_preset_keeps_not_in_this_pathway() -> None:
    from deploy_vii.report_view import call_state

    run = _override_run("earnings_update", ("CP-1",))
    pathway = next(item for item in pathways() if item.id == "earnings_update")
    assert "CP-6" not in pathway.requested_modules
    report = build(empty_view(run), pathway, SHIPPED_MAPS)
    assert report.call_withheld == "outside_pathway"
    assert call_state(report) == ("outside", ("na", "Not in this Pathway"))


def test_navigator_word_distinguishes_override_excluded_from_foreign_module() -> None:
    from deploy_vii.report_view import navigator

    rows = {
        row.module_id: row
        for row in navigator(empty_view(_override_run("credit_snapshot", ("CP-1",))))
    }
    assert (
        "CP-6"
        in next(item for item in pathways() if item.id == "credit_snapshot").requested_modules
    )
    assert str(rows["CP-6"].word) == "Not run"  # preset module the override left out
    assert str(rows["CP-8"].word) == "Not in this Pathway"  # CP-8 is outside the preset
