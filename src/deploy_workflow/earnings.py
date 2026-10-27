"""Pure paired-period deltas over a selected, settled CP1 fact register.

This core checks structural coordinates, not producer run authentication. It
preserves CP1's reported values and existing ratio results without recalculation.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Context, Decimal, DecimalException, localcontext
from typing import Literal

from deploy_vii.contracts import Fact, ModuleView

FactStatus = Literal["known", "missing", "conflicting", "not_applicable"]


@dataclass(frozen=True, slots=True)
class EarningsDeltaPoint:
    measure_id: str
    prior_fact_id: str | None
    current_fact_id: str
    companion_fact_ids: tuple[str, ...]
    prior_value: Decimal | None
    current_value: Decimal | None
    prior_status: FactStatus
    current_status: FactStatus
    delta: Decimal | None
    delta_status: FactStatus
    delta_unit: str
    growth: Decimal | None
    growth_status: FactStatus
    reason: str | None
    unit: str
    currency: str | None
    scale: Decimal


@dataclass(frozen=True, slots=True)
class EarningsDeltaReport:
    producer_sha256: str
    prior_period_id: str
    current_period_id: str
    prior_basis_id: str | None
    current_basis_id: str
    points: tuple[EarningsDeltaPoint, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _Period:
    identity: str
    kind: str
    start: date
    end: date
    row: dict[str, Fact]


_PERIOD_FIELDS = (
    "period_id", "period_type", "fiscal_year", "fiscal_quarter", "start_date", "end_date",
    "currency", "unit", "accounting_basis", "entity_perimeter",
)
_MEASURES = (
    "revenue", "ebitda", "adjusted_ebitda", "ebitda_margin", "cfo_reported", "capex",
    "fcf", "cash_closing", "total_debt", "net_debt", "total_leverage_reported",
    "net_leverage_reported",
)
_GROWTH = frozenset(_MEASURES[:3])
_SCOPE = "IFRS · consolidated group"
_LIMITATIONS = (
    "Core-only paired-period component; no actual owner, permission, journal, CP5 or render acceptance.",
    "No causal-driver or guidance inference is supported by these deltas.",
    "Comparative income is not supplied for absent prior periods; no source period is fabricated.",
    "No broader nonzero earnings, provider or production qualification is established.",
)


def _validate_fact(fact: Fact) -> None:
    if fact.status not in {"known", "missing", "conflicting", "not_applicable"}:
        raise ValueError("invalid_fact")
    if fact.status == "known":
        if (fact.amount is None) == (fact.text is None):
            raise ValueError("invalid_fact")
    elif fact.amount is not None or fact.text is not None or not fact.limitation:
        raise ValueError("invalid_fact")
    if fact.amount is not None and (
        not isinstance(fact.amount, Decimal) or not fact.amount.is_finite()
    ):
        raise ValueError("invalid_fact")
    if fact.text is not None and not isinstance(fact.text, str):
        raise ValueError("invalid_fact")
    if fact.limitation is not None and not isinstance(fact.limitation, str):
        raise ValueError("invalid_fact")
    if not isinstance(fact.scale, Decimal) or not fact.scale.is_finite():
        raise ValueError("invalid_fact")


def _rows(module: ModuleView, table: str) -> tuple[dict[str, Fact], ...]:
    rows: dict[str, dict[str, Fact]] = {}
    for fact in module.facts:
        if fact.table_id != table:
            continue
        _validate_fact(fact)
        row = rows.setdefault(fact.row_id, {})
        if fact.field in row:
            raise ValueError("ambiguous_coordinate")
        row[fact.field] = fact
    return tuple(rows.values())


def _text(fact: Fact) -> str:
    if fact.status != "known" or not fact.text or fact.amount is not None:
        raise ValueError("invalid_fact")
    return fact.text


def _periods(module: ModuleView) -> dict[str, dict[str, Fact]]:
    periods = {}
    for row in _rows(module, "T4.14"):
        if not set(_PERIOD_FIELDS) <= row.keys():
            raise ValueError("incomplete_register")
        identity = _text(row["period_id"])
        if identity in periods:
            raise ValueError("ambiguous_coordinate")
        periods[identity] = row
    return periods


def _duration_period(row: dict[str, Fact]) -> _Period:
    kind = _text(row["period_type"])
    if kind not in {"QUARTER", "FY"}:
        raise ValueError("incompatible_periods")
    try:
        start = date.fromisoformat(_text(row["start_date"]))
        end = date.fromisoformat(_text(row["end_date"]))
    except ValueError as exc:
        raise ValueError("invalid_fact") from exc
    return _Period(_text(row["period_id"]), kind, start, end, row)


def _check_period(period: _Period) -> None:
    row = period.row
    if any(f.period != period.identity or f.basis != _SCOPE for f in row.values()):
        raise ValueError("incompatible_dimensions")
    if tuple(_text(row[k]) for k in (
        "currency", "unit", "accounting_basis", "entity_perimeter"
    )) != ("USD", "MILLIONS", "IFRS", "consolidated group"):
        raise ValueError("incompatible_dimensions")
    if period.kind not in {"QUARTER", "FY"} or period.start > period.end:
        raise ValueError("incompatible_periods")
    _text(row["fiscal_year"])
    if period.kind == "QUARTER":
        _text(row["fiscal_quarter"])
    elif row["fiscal_quarter"].status != "not_applicable":
        raise ValueError("invalid_fact")


def _basis(period: _Period) -> str:
    # Adopt financial_model._basis_id / financial_periods._id exactly. Labels,
    # equal-date FY aliases and rolling bases never determine this join.
    column = f"{'Q' if period.kind == 'QUARTER' else 'FY'}:{period.identity}"
    payload = "".join(f"{len(part)}:{part}" for part in ("historical", column))
    return "model-basis:" + hashlib.sha256(payload.encode()).hexdigest()


def _metrics(module: ModuleView) -> dict[str, dict[str, Fact]]:
    metrics = {}
    for row in _rows(module, "T4.10"):
        if "field_1" not in row:
            raise ValueError("incomplete_register")
        identity = _text(row["field_1"])
        if identity in metrics:
            raise ValueError("ambiguous_coordinate")
        metrics[identity] = row
    if not set(_MEASURES) <= metrics.keys():
        raise ValueError("incomplete_register")
    return metrics


def _dimensions(measure: str) -> tuple[str, str | None, Decimal]:
    if measure == "ebitda_margin":
        return "PERCENT", None, Decimal(1)
    if measure in {"total_leverage_reported", "net_leverage_reported"}:
        return "MULTIPLE", None, Decimal(1)
    return "MILLIONS", "USD", Decimal(1000000)


def _selected(row: dict[str, Fact], period: _Period, measure: str) -> Fact:
    fact = row.get(_basis(period))
    if fact is None:
        raise ValueError("incomplete_register")
    # A known textual value cannot be a selected numeric coordinate.
    if fact.text is not None:
        raise ValueError("invalid_fact")
    expected = (*_dimensions(measure), _SCOPE)
    dates = f"{period.start.isoformat()} to {period.end.isoformat()}"
    if (fact.unit, fact.currency, fact.scale, fact.basis) != expected or (
        not isinstance(fact.period, str) or fact.period.rsplit(": ", 1)[-1] != dates
    ):
        raise ValueError("incompatible_dimensions")
    return fact


def _point(
    measure: str, row: dict[str, Fact], prior: _Period | None, current: _Period
) -> EarningsDeltaPoint:
    current_fact = _selected(row, current, measure)
    prior_fact = _selected(row, prior, measure) if prior is not None else None
    unit, currency, scale = _dimensions(measure)
    delta_unit = "PERCENTAGE_POINTS" if unit == "PERCENT" else unit
    delta = growth = None
    growth_status: FactStatus = "not_applicable"
    reasons = [
        fact.limitation
        for fact in (prior_fact, current_fact)
        if fact is not None and fact.limitation
    ]

    if prior_fact is None:
        delta_status: FactStatus = "missing"
        if measure in _GROWTH:
            growth_status = "missing"
        reasons.insert(0, "COMPARATIVE_NOT_SUPPLIED")
    elif prior_fact.status != "known" or current_fact.status != "known":
        delta_status = next(
            status
            for status in ("conflicting", "missing", "not_applicable")
            if status in (prior_fact.status, current_fact.status)
        )
        if measure in _GROWTH:
            growth_status = delta_status
    else:
        prior_amount, current_amount = prior_fact.amount, current_fact.amount
        if prior_amount is None or current_amount is None:
            raise ValueError("invalid_fact")
        delta = current_amount - prior_amount
        delta_status = "known"
        if unit == "PERCENT":
            delta = Decimal(100) * delta
        if measure in _GROWTH:
            if prior_amount == 0:
                growth_status = "missing"
                reasons.append("ZERO_DENOMINATOR")
            else:
                growth = delta / prior_amount
                growth_status = "known"

    companions = (
        row["field_1"].fact_id,
        *(
            period.row[field].fact_id
            for period in (prior, current)
            if period is not None
            for field in _PERIOD_FIELDS
        ),
    )
    return EarningsDeltaPoint(
        measure_id=measure,
        prior_fact_id=prior_fact.fact_id if prior_fact else None,
        current_fact_id=current_fact.fact_id,
        companion_fact_ids=companions,
        prior_value=prior_fact.amount if prior_fact else None,
        current_value=current_fact.amount,
        prior_status=prior_fact.status if prior_fact else "missing",
        current_status=current_fact.status,
        delta=delta,
        delta_status=delta_status,
        delta_unit=delta_unit,
        growth=growth,
        growth_status=growth_status,
        reason="; ".join(dict.fromkeys(reasons)) or None,
        unit=unit,
        currency=currency,
        scale=scale,
    )


def build_earnings_delta(
    module: ModuleView, prior_period_id: str, current_period_id: str
) -> EarningsDeltaReport:
    """Compare exact reported periods using pinned Decimal arithmetic.

    ModuleView checks are structural only. Authentication, settlement and actual
    downstream consumption belong to the separately leased owner workflow.
    """
    try:
        with localcontext(Context(prec=38, rounding=ROUND_HALF_EVEN)):
            if (
                not isinstance(module, ModuleView)
                or module.module_id != "CP-1"
                or module.status not in {"accepted", "restricted"}
                or not module.artifact_sha256
            ):
                raise ValueError("invalid_source_view")

            facts_by_id = {fact.fact_id: fact for fact in module.facts}
            if len(facts_by_id) != len(module.facts):
                raise ValueError("ambiguous_coordinate")

            periods = _periods(module)
            current_row = periods.get(current_period_id)
            if current_row is None:
                raise ValueError("incomplete_register")
            current = _duration_period(current_row)
            prior_row = periods.get(prior_period_id)
            prior = _duration_period(prior_row) if prior_row is not None else None

            _check_period(current)
            if prior is not None:
                _check_period(prior)
                if (
                    prior.kind != current.kind
                    or prior.end - prior.start != current.end - current.start
                    or current.start <= prior.end
                ):
                    raise ValueError("incompatible_periods")

            metrics = _metrics(module)
            points = tuple(
                _point(measure, metrics[measure], prior, current)
                for measure in _MEASURES
            )
            source_limitations = tuple(
                limitation
                for point in points
                for fact_id in (point.prior_fact_id, point.current_fact_id)
                if fact_id is not None
                for limitation in (facts_by_id[fact_id].limitation,)
                if limitation
            )
            limitations = tuple(
                dict.fromkeys(
                    (*module.limitations, *source_limitations, *_LIMITATIONS)
                )
            )
            return EarningsDeltaReport(
                producer_sha256=module.artifact_sha256,
                prior_period_id=prior_period_id,
                current_period_id=current_period_id,
                prior_basis_id=_basis(prior) if prior is not None else None,
                current_basis_id=_basis(current),
                points=points,
                limitations=limitations,
            )
    except DecimalException as exc:
        raise ValueError("invalid_fact") from exc
