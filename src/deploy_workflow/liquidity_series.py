"""Chart coordinates of CR.2 (CP-2D cash bridge) and CR.3 (CP-3C refinancing need by maturity).

Like ``financial_series`` this projection selects settled facts, it never calculates one: each
point names its fact, and carries that fact's own amount and its display spelling. A fact that
is not known is a gap point (no value, spelled ``∅ G#``; the report binds the ``G#`` when the
figure is rendered). A fact the module does not carry fails closed. Nothing here is zero-filled.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from deploy_vii.contracts import Fact, ModuleView
from deploy_vii.display import format_value

PointRole = Literal["value", "total"]

# A gap point's spelling before the report binds it: the series is produced from one module
# and has no gap ledger, so the ``G#`` is bound at render time (``report_view`` replaces it).
GAP_UNBOUND = "∅ G#"

_CP2D = "CP-2D"
_CP3C = "CP-3C"
_AXIS = "US$ m"
_CR2_SERIES = "Cash bridge"
_CR2_NOTE = (
    "Steps are CP-2D's settled cash bridge: cash at the balance date, run-rate net cash flow "
    "over the horizon, scheduled amortisation, maturities, and cash at horizon end before "
    "refinancing. The design bridge (accessible liquidity plus inflow less mandatory uses less "
    "discretionary capex, rbot-fp-04 :39) is not drawn: CP-2D settles no lease or capex split."
)
_HORIZON = ("T2E.3.r03", "T2E.3.r04")
# (fact id, role, companion fact ids) of the five steps, in drawing order.
_CR2_STEPS: tuple[tuple[str, PointRole, tuple[str, ...]], ...] = (
    ("T2E.2.r01", "total", _HORIZON),
    ("T2E.3.r05", "value", _HORIZON),
    ("T2E.3.r06", "value", _HORIZON),
    ("T2E.3.r07", "value", _HORIZON),
    (
        "T2E.3.r08",
        "total",
        (*_HORIZON, "T2E.2.r01", "T2E.3.r05", "T2E.3.r06", "T2E.3.r07"),
    ),
)
_CR3_SERIES = ("Principal payable at maturity", "Resources at maturity")
_CR3_FIELDS = ("c6", "c7")
_CR3_COMPANIONS = ("c2", "c3")


@dataclass(frozen=True, slots=True)
class LiquidityPoint:
    series: str
    category: str
    fact_id: str
    companion_fact_ids: tuple[str, ...]
    shown: str
    value: Decimal | None
    role: PointRole = "value"
    sublabel: str | None = None


@dataclass(frozen=True, slots=True)
class LiquidityFigureSeries:
    fig_id: str
    title: str
    kind: Literal["waterfall", "grouped", "na"]
    unit_class: Literal["amount"]
    unit: str
    axis_label: str
    series: tuple[str, ...]
    points: tuple[LiquidityPoint, ...]
    reason: str | None
    note: str | None = None


def _facts(module: ModuleView, module_id: str) -> Mapping[str, Fact]:
    if module.module_id != module_id:
        raise ValueError(f"The {module_id} chart producer was given module {module.module_id}")
    return {fact.fact_id: fact for fact in module.facts}


def _fact(facts: Mapping[str, Fact], fact_id: str, module_id: str) -> Fact:
    if fact_id not in facts:
        raise ValueError(f"{module_id} chart references {fact_id}, which the module does not carry")
    return facts[fact_id]


def _amount(fact: Fact) -> Decimal | None:
    """The fact's own settled amount; None for an unsettled fact (a gap, never 0)."""
    if fact.status != "known":
        return None
    if fact.amount is None or not fact.amount.is_finite():
        raise ValueError(f"Malformed chart fact: {fact.fact_id}")
    return fact.amount


def _shown(fact: Fact, value: Decimal | None) -> str:
    if value is None:
        return GAP_UNBOUND
    return format_value(value, "amount", "known", decimals=fact.decimals)


def _kind_and_reason(
    points: tuple[LiquidityPoint, ...],
    facts: Mapping[str, Fact],
    kind: Literal["waterfall", "grouped"],
) -> tuple[Literal["waterfall", "grouped", "na"], str | None]:
    """The drawn kind, or the n/a frame with the facts' own reasons when nothing is plottable."""
    if any(point.value is not None for point in points):
        return kind, None
    reasons = [facts[point.fact_id].limitation for point in points]
    return "na", "; ".join(dict.fromkeys(text for text in reasons if text)) or None


def cp2d_chart_series(module: ModuleView) -> tuple[LiquidityFigureSeries, ...]:
    """CR.2: the settled cash bridge, five steps from the CP-2D head (Q-C3)."""
    facts = _facts(module, _CP2D)
    points = []
    for fact_id, role, companions in _CR2_STEPS:
        fact = _fact(facts, fact_id, _CP2D)
        for companion in companions:
            _fact(facts, companion, _CP2D)
        value = _amount(fact)
        points.append(
            LiquidityPoint(
                series=_CR2_SERIES,
                category=fact.label,
                fact_id=fact_id,
                companion_fact_ids=companions,
                shown=_shown(fact, value),
                value=value,
                role=role,
            )
        )
    drawn = tuple(points)
    kind, reason = _kind_and_reason(drawn, facts, "waterfall")
    return (
        LiquidityFigureSeries(
            fig_id="CR.2",
            title="Liquidity runway",
            kind=kind,
            unit_class="amount",
            unit="MILLIONS",
            axis_label=_AXIS,
            series=(_CR2_SERIES,),
            points=drawn,
            reason=reason,
            note=_CR2_NOTE,
        ),
    )


def cp3c_chart_series(module: ModuleView) -> tuple[LiquidityFigureSeries, ...]:
    """CR.3: principal payable and resources at maturity, one category per T3D.1 facility row."""
    facts = _facts(module, _CP3C)
    table = next((item for item in module.tables if item.table_id == "T3D.1"), None)
    if table is None or not table.rows:
        raise ValueError("CP-3C chart needs the T3D.1 register, which the module does not carry")
    points = []
    for row in table.rows:
        companions = tuple(f"T3D.1.{row.row_id}.{field}" for field in _CR3_COMPANIONS)
        date_fact = _fact(facts, companions[0], _CP3C)
        _fact(facts, companions[1], _CP3C)
        sublabel = date_fact.text if date_fact.status == "known" else None
        for series, field in zip(_CR3_SERIES, _CR3_FIELDS, strict=True):
            fact_id = f"T3D.1.{row.row_id}.{field}"
            fact = _fact(facts, fact_id, _CP3C)
            value = _amount(fact)
            points.append(
                LiquidityPoint(
                    series=series,
                    category=row.label,
                    fact_id=fact_id,
                    companion_fact_ids=companions,
                    shown=_shown(fact, value),
                    value=value,
                    sublabel=sublabel,
                )
            )
    drawn = tuple(points)
    kind, reason = _kind_and_reason(drawn, facts, "grouped")
    return (
        LiquidityFigureSeries(
            fig_id="CR.3",
            title="Funding gap",
            kind=kind,
            unit_class="amount",
            unit="MILLIONS",
            axis_label=_AXIS,
            series=_CR3_SERIES,
            points=drawn,
            reason=reason,
        ),
    )
