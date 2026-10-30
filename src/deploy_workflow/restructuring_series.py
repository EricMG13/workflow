"""Source-native chart coordinates from a settled CP-4C register (DR.2 to DR.5).

This projection selects settled facts and spells a series label; it never calculates a value.
Every point names the fact that carries its number, with the companion facts that explain it,
and the consumer (``deploy_vii.chart_producers``) reads amount, status, unit and the report's
``G#`` from those facts alone. A missing fact stays a gap point: nothing is replaced by 0.

DR.2 is the recovery by class (creditor classes by scenario). DR.3, DR.4 and DR.5 are the value
allocation waterfalls of the scenarios in row order. A waterfall builds up to the enterprise
value (rulings item 6.4): the classes by (rank, id), the equity residual, then the total.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from deploy_vii.contracts import Fact, ModuleView
from deploy_vii.display import format_value

# A multiple is illustrative unless the settled record states it as sourced. The oracle words
# this "source or cited"; a cited multiple is a ``source`` value_class. A missing multiple, or
# one with no declared basis, hatches by default (dr2-expected.json hatched_basis).
_SOURCED = frozenset({"source"})
_ALLOCATION_SERIES = "Value allocation"
_WATERFALL_IDS = ("DR.3", "DR.4", "DR.5")


@dataclass(frozen=True, slots=True)
class RestructuringPoint:
    series: str
    category: str
    fact_id: str
    companion_fact_ids: tuple[str, ...]
    role: Literal["value", "residual", "total"]
    hatched: bool


@dataclass(frozen=True, slots=True)
class RestructuringFigureSeries:
    fig_id: str
    title: str
    kind: Literal["grouped", "waterfall", "na"]
    unit_class: Literal["percent", "amount"]
    unit: str
    currency: str | None
    series: tuple[str, ...]
    points: tuple[RestructuringPoint, ...]
    reason: str | None
    dropped_fact_ids: tuple[str, ...]


@dataclass(frozen=True)
class _Scenario:
    row: str
    label: str
    hatched: bool


def _known_text(fact: Fact) -> str:
    if fact.status != "known" or fact.text is None or fact.amount is not None:
        raise ValueError(f"Unresolved chart identity: {fact.fact_id}")
    return fact.text


def _scenarios(facts: dict[str, Fact], module: ModuleView) -> tuple[_Scenario, ...]:
    """The T4E.3 valuation rows in order, each with its series label and hatching."""
    rows = list(dict.fromkeys(f.row_id for f in module.facts if f.table_id == "T4E.3"))
    scenarios = []
    for row in rows:
        name = _known_text(_need(facts, f"T4E.3.{row}.scenario"))
        multiple = _need(facts, f"T4E.3.{row}.multiple")
        label = name
        if multiple.status == "known" and multiple.amount is not None:
            label = f"{name} {format_value(multiple.amount, 'multiple', 'known', decimals=multiple.decimals)}"
        hatched = multiple.status != "known" or multiple.value_class not in _SOURCED
        scenarios.append(_Scenario(row, label, hatched))
    if len({s.label for s in scenarios}) != len(scenarios):
        raise ValueError("CP-4C scenario series labels must be distinct")
    return tuple(scenarios)


def _need(facts: dict[str, Fact], fact_id: str) -> Fact:
    if fact_id not in facts:
        raise ValueError(f"CP-4C chart references an unknown fact: {fact_id}")
    return facts[fact_id]


def _classes(facts: dict[str, Fact], module: ModuleView) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(creditor class ids by (rank, id), equity class ids) from the T4E.2 claims register."""
    ids = list(
        dict.fromkeys(f.row_id for f in module.facts if f.table_id == "T4E.2" and f.field == "name")
    )
    equity = tuple(c for c in ids if _known_text(_need(facts, f"T4E.2.{c}.kind")) == "equity")
    creditors = []
    for class_id in ids:
        if class_id in equity:
            continue
        rank = _known_text(_need(facts, f"T4E.2.{class_id}.rank"))
        if not rank.isascii() or not rank.isdigit():
            raise ValueError(f"Unresolved chart identity: T4E.2.{class_id}.rank")
        creditors.append((int(rank), class_id))
    return tuple(class_id for _, class_id in sorted(creditors)), equity


def _reason(facts: dict[str, Fact], ids: list[str]) -> str:
    """The module's own limitation for a chart with no plottable point (never invented)."""
    texts = [facts[i].limitation for i in ids if facts[i].limitation]
    reason = "; ".join(dict.fromkeys(text for text in texts if text))
    if not reason:
        raise ValueError("CP-4C chart without a plottable point states no limitation")
    return reason


def _currency(module: ModuleView) -> str | None:
    """The one currency of the known USD-scaled amounts of the CP-4C register, if any."""
    found = {
        f.currency
        for f in module.facts
        if f.table_id.startswith("T4E.") and f.status == "known" and f.unit == "MILLIONS"
    }
    found.discard(None)
    if len(found) > 1:
        raise ValueError("CP-4C amounts state more than one currency")
    return found.pop() if found else None


def _recovery(
    facts: dict[str, Fact], module: ModuleView, scenarios: tuple[_Scenario, ...]
) -> RestructuringFigureSeries:
    creditors, equity = _classes(facts, module)
    points = []
    for class_id in creditors:
        category = _known_text(_need(facts, f"T4E.2.{class_id}.name"))
        for s in scenarios:
            fact_id = f"T4E.5.{s.row}{class_id}.recovery"
            _need(facts, fact_id)
            points.append(
                RestructuringPoint(
                    series=s.label,
                    category=category,
                    fact_id=fact_id,
                    companion_fact_ids=(
                        f"T4E.3.{s.row}.scenario",
                        f"T4E.3.{s.row}.multiple",
                        f"T4E.2.{class_id}.name",
                    ),
                    role="value",
                    hatched=s.hatched,
                )
            )
    dropped = tuple(f"T4E.5.{s.row}{c}.recovery" for c in equity for s in scenarios)
    for fact_id in dropped:
        if _need(facts, fact_id).status != "not_applicable":
            raise ValueError(f"CP-4C equity recovery is not n.m.: {fact_id}")
    ids = [p.fact_id for p in points]
    plottable = any(facts[i].status == "known" for i in ids)
    return RestructuringFigureSeries(
        fig_id="DR.2",
        title="Recovery by class",
        kind="grouped" if plottable else "na",
        unit_class="percent",
        unit="PERCENT",
        currency=None,
        series=tuple(s.label for s in scenarios),
        points=tuple(points),
        reason=None if plottable else _reason(facts, ids),
        dropped_fact_ids=dropped,
    )


def _waterfall(
    facts: dict[str, Fact],
    module: ModuleView,
    fig_id: str,
    s: _Scenario,
    creditors: tuple[str, ...],
) -> RestructuringFigureSeries:
    head = (f"T4E.3.{s.row}.scenario", f"T4E.3.{s.row}.multiple")
    steps: list[tuple[str, str, tuple[str, ...], Literal["value", "residual", "total"]]] = []
    for class_id in creditors:
        fact_id = f"T4E.4.{s.row}{class_id}.distribution"
        steps.append(
            (
                fact_id,
                _known_text(_need(facts, f"T4E.2.{class_id}.name")),
                (*head, f"T4E.4.{s.row}{class_id}.claim", f"T4E.2.{class_id}.name"),
                "value",
            )
        )
    residual = f"T4E.9.{s.row}.equity_residual"
    total = f"T4E.3.{s.row}.ev"
    checks = tuple(
        f"T4E.9.{s.row}.{name}" for name in ("total_claims", "creditor_distributions", "balance")
    )
    steps.append((residual, _need(facts, residual).label, head, "residual"))
    steps.append((total, _need(facts, total).label, (*head, *checks), "total"))
    points = []
    for fact_id, category, companions, role in steps:
        for needed in (fact_id, *companions):
            _need(facts, needed)
        points.append(
            RestructuringPoint(
                series=_ALLOCATION_SERIES,
                category=category,
                fact_id=fact_id,
                companion_fact_ids=companions,
                role=role,
                hatched=s.hatched,
            )
        )
    ids = [p.fact_id for p in points]
    plottable = any(facts[i].status == "known" for i in ids)
    return RestructuringFigureSeries(
        fig_id=fig_id,
        title=f"Value allocation, {s.label}",
        kind="waterfall" if plottable else "na",
        unit_class="amount",
        unit="MILLIONS",
        currency=_currency(module),
        series=(_ALLOCATION_SERIES,),
        points=tuple(points),
        reason=None if plottable else _reason(facts, ids),
        dropped_fact_ids=(),
    )


def cp4c_chart_series(module: ModuleView) -> tuple[RestructuringFigureSeries, ...]:
    """DR.2, then DR.3 to DR.5 for the valuation rows in order; none without a valuation.

    A module with no T4E.3 valuation rows supplies no figure. Unknown or malformed settled
    coordinates raise ``ValueError``; a missing fact stays a gap point. More valuation rows than
    the three allocation figures is refused rather than silently dropped.
    """
    facts = {fact.fact_id: fact for fact in module.facts}
    scenarios = _scenarios(facts, module)
    if not scenarios:
        return ()
    if len(scenarios) > len(_WATERFALL_IDS):
        raise ValueError("CP-4C has more valuation scenarios than allocation figures")
    creditors, _ = _classes(facts, module)
    return (
        _recovery(facts, module, scenarios),
        *(
            _waterfall(facts, module, fig_id, s, creditors)
            for fig_id, s in zip(_WATERFALL_IDS, scenarios, strict=False)
        ),
    )
