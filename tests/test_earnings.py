"""Independent A1 component cases; these do not qualify owner execution.

The handwritten coordinates follow the adopted CP1 register shape. Numeric
fixtures are literal source/oracle values, never financial-engine output.
"""

import importlib
import importlib.util
import inspect
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
from decimal import ROUND_DOWN, Decimal, Inexact, getcontext, localcontext
from pathlib import Path

import pytest

from deploy_vii.contracts import Citation, Fact, ModuleView

ORACLE = json.loads((Path(__file__).parents[1] / "cases/earnings/expected.json").read_text())
MEASURES = (
    "revenue",
    "ebitda",
    "adjusted_ebitda",
    "ebitda_margin",
    "cfo_reported",
    "capex",
    "fcf",
    "cash_closing",
    "total_debt",
    "net_debt",
    "total_leverage_reported",
    "net_leverage_reported",
)
GROWTH = frozenset(MEASURES[:3])
PERIOD_FIELDS = (
    "period_id",
    "period_type",
    "fiscal_year",
    "fiscal_quarter",
    "start_date",
    "end_date",
    "currency",
    "unit",
    "accounting_basis",
    "entity_perimeter",
)
# Literal adopted length-prefixed historical Q:<id> / FY:<id> identities.
BASES = {
    "q3-2025": "model-basis:36604f9b09d609dfe1b66ec07a153d836a007251b6564d183773b8be2b3c959a",
    "q4-2025": "model-basis:1a39b61b63ee7f787ffcf5706f5dbbea2def3aa196fc2c23e4d88b6d19b834e6",
    "fy-2025": "model-basis:3a1cc226cb809c75fa088ce0e414c452c69707fa935237a2f18c4576adc4bed5",
}
DATES = {
    "q3-2025": ("QUARTER", "3", "2025-07-01", "2025-09-30", "Q3 25"),
    "q4-2025": ("QUARTER", "4", "2025-10-01", "2025-12-31", "Q4 25"),
    "fy-2025": ("FY", None, "2025-01-01", "2025-12-31", "FY25"),
}
VALUES = {
    "q3-2025": (
        "30",
        "7.5",
        "7.5",
        ".25",
        "4.75",
        "-2.5",
        "2.25",
        "18.75",
        "48.75",
        "30",
        None,
        None,
    ),
    "q4-2025": (
        "30",
        "7.5",
        "7.5",
        ".25",
        "4.75",
        "-2.5",
        "2.25",
        "20",
        "50",
        "30",
        "1.6666666666666666666666666666666666667",
        "1",
    ),
    "fy-2025": (
        "120",
        "30",
        "30",
        ".25",
        "19",
        "-10",
        "9",
        "20",
        "50",
        "30",
        "1.6666666666666666666666666666666666667",
        "1",
    ),
}
SOURCE_LIMIT = "Source perimeter is consolidated group; supplied statements are unaudited."


def api():
    # Collection succeeds before implementation; RED names the missing feature.
    assert importlib.util.find_spec("deploy_workflow.earnings") is not None, (
        "A1 earnings core is not implemented"
    )
    return importlib.import_module("deploy_workflow.earnings")


def fixture():
    facts = []
    citation = Citation(
        source_id="financial",
        source_sha256=ORACLE["financial_source_sha256"],
        locator="page:2",
        quote="Revenue",
    )
    for pid, (kind, quarter, start, end, label) in DATES.items():
        values = dict(
            zip(
                PERIOD_FIELDS,
                (
                    pid,
                    kind,
                    "2025",
                    quarter,
                    start,
                    end,
                    "USD",
                    "MILLIONS",
                    "IFRS",
                    "consolidated group",
                ),
                strict=True,
            )
        )
        for field, value in values.items():
            facts.append(
                Fact(
                    fact_id=f"period.{pid}.{field}",
                    label=field,
                    table_id="T4.14",
                    row_id=f"period.{pid}",
                    field=field,
                    text=value,
                    status="not_applicable" if value is None else "known",
                    limitation="FY has no fiscal quarter" if value is None else None,
                    period=pid,
                    basis="IFRS · consolidated group",
                    citations=(citation,),
                )
            )
    for index, measure in enumerate(MEASURES):
        facts.append(
            Fact(
                fact_id=f"metric.{measure}",
                label="Display label is not identity",
                table_id="T4.10",
                row_id=f"metric.{measure}",
                field="field_1",
                text=measure,
                period="dashboard",
                basis="IFRS · consolidated group",
                citations=(citation,),
            )
        )
        for pid, (_, _, start, end, label) in DATES.items():
            value = VALUES[pid][index]
            unit = (
                "PERCENT"
                if measure == "ebitda_margin"
                else "MULTIPLE"
                if index >= 10
                else "MILLIONS"
            )
            facts.append(
                Fact(
                    fact_id=f"value.{measure}.{pid}",
                    label=measure,
                    table_id="T4.10",
                    row_id=f"metric.{measure}",
                    field=BASES[pid],
                    amount=None if value is None else Decimal(value),
                    status="missing" if value is None else "known",
                    limitation="Four complete contiguous quarters are required"
                    if value is None
                    else None,
                    unit=unit,
                    currency="USD" if unit == "MILLIONS" else None,
                    scale=Decimal(1000000) if unit == "MILLIONS" else Decimal(1),
                    period=f"{label}: {start} to {end}",
                    basis="IFRS · consolidated group",
                    citations=(citation,),
                    value_class="calculated",
                )
            )
    return ModuleView(
        module_id="CP-1",
        title="Financials",
        aliases=(),
        status="restricted",
        artifact_sha256="a" * 64,
        facts=tuple(facts),
        limitations=(SOURCE_LIMIT,),
    )


def change(module, fact_id, **updates):
    assert sum(f.fact_id == fact_id for f in module.facts) == 1
    return module.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update=updates) if f.fact_id == fact_id else f for f in module.facts
            )
        }
    )


def without(module, *ids):
    return module.model_copy(
        update={"facts": tuple(f for f in module.facts if f.fact_id not in ids)}
    )


def build(module=None, prior="q3-2025", current="q4-2025"):
    return api().build_earnings_delta(fixture() if module is None else module, prior, current)


def point(report, measure):
    return next(p for p in report.points if p.measure_id == measure)


def refusal(module, error, prior="q3-2025", current="q4-2025"):
    with pytest.raises(ValueError, match=f"^{error}$"):
        build(module, prior, current)


def test_public_frozen_api_and_input_immutability():
    core = api()
    assert tuple(inspect.signature(core.build_earnings_delta).parameters) == (
        "module",
        "prior_period_id",
        "current_period_id",
    )
    module = fixture()
    original = module.model_dump_json()
    report = build(module)
    assert isinstance(report, core.EarningsDeltaReport) and isinstance(
        report.points[0], core.EarningsDeltaPoint
    )
    assert [f.name for f in fields(report)] == [
        "producer_sha256",
        "prior_period_id",
        "current_period_id",
        "prior_basis_id",
        "current_basis_id",
        "points",
        "limitations",
    ]
    assert [f.name for f in fields(report.points[0])] == [
        "measure_id",
        "prior_fact_id",
        "current_fact_id",
        "companion_fact_ids",
        "prior_value",
        "current_value",
        "prior_status",
        "current_status",
        "delta",
        "delta_status",
        "delta_unit",
        "growth",
        "growth_status",
        "reason",
        "unit",
        "currency",
        "scale",
    ]
    for record in (report, *report.points):
        assert is_dataclass(record) and not hasattr(record, "__dict__")
        with pytest.raises(FrozenInstanceError):
            setattr(record, fields(record)[0].name, "forged")
    assert isinstance(report.points, tuple) and isinstance(report.limitations, tuple)
    assert module.model_dump_json() == original


@pytest.mark.parametrize("status", ["accepted", "restricted"])
def test_all_twelve_independent_qoq_oracle_points_and_fact_lineage(status):
    module = fixture().model_copy(update={"status": status})
    report = build(module)
    assert report.producer_sha256 == module.artifact_sha256
    assert (report.prior_period_id, report.current_period_id) == ("q3-2025", "q4-2025")
    assert (report.prior_basis_id, report.current_basis_id) == (BASES["q3-2025"], BASES["q4-2025"])
    assert tuple(p.measure_id for p in report.points) == MEASURES
    for actual, expected in zip(report.points, ORACLE["positive"]["points"], strict=True):
        for field in ("prior_value", "current_value", "delta", "growth", "scale"):
            value = expected[field]
            assert getattr(actual, field) == (None if value is None else Decimal(value))
        for field in (
            "measure_id",
            "prior_status",
            "current_status",
            "delta_status",
            "growth_status",
            "unit",
            "currency",
            "delta_unit",
        ):
            assert getattr(actual, field) == expected[field]
        assert actual.prior_fact_id == f"value.{actual.measure_id}.q3-2025"
        assert actual.current_fact_id == f"value.{actual.measure_id}.q4-2025"
        required = {
            f"metric.{actual.measure_id}",
            *(f"period.{pid}.{f}" for pid in ("q3-2025", "q4-2025") for f in PERIOD_FIELDS),
        }
        assert required <= set(actual.companion_fact_ids)
        assert set(actual.companion_fact_ids) <= {f.fact_id for f in module.facts}
        assert isinstance(actual.companion_fact_ids, tuple)
        if expected["reason_contains"]:
            assert expected["reason_contains"] in actual.reason
        else:
            assert actual.reason is None
    assert SOURCE_LIMIT in report.limitations
    limits = " ".join(report.limitations).lower()
    for word in ("core", "causal", "guidance", "comparative", "nonzero"):
        assert word in limits


def test_absent_prior_fy_retains_current_and_never_invents_income_comparator():
    report = build(prior="fy-2024", current="fy-2025")
    assert report.prior_period_id == "fy-2024" and report.prior_basis_id is None
    assert report.current_basis_id == BASES["fy-2025"]
    assert tuple(p.measure_id for p in report.points) == MEASURES
    assert point(report, "revenue").current_value == Decimal(120)
    assert point(report, "ebitda").current_value == Decimal(30)
    for p in report.points:
        assert p.prior_fact_id is None and p.prior_value is None and p.delta is None
        assert p.prior_status == p.delta_status == "missing"
        assert p.current_fact_id == f"value.{p.measure_id}.fy-2025" and p.current_status == "known"
        assert p.growth is None and p.growth_status == (
            "missing" if p.measure_id in GROWTH else "not_applicable"
        )
        assert "COMPARATIVE_NOT_SUPPLIED" in p.reason
        assert {f"metric.{p.measure_id}", *(f"period.fy-2025.{f}" for f in PERIOD_FIELDS)} <= set(
            p.companion_fact_ids
        )
        assert not any("fy-2024" in fid for fid in p.companion_fact_ids)


def test_zero_prior_and_percentage_point_artificial_guards():
    module = change(fixture(), "value.revenue.q3-2025", amount=Decimal(0))
    module = change(module, "value.ebitda_margin.q3-2025", amount=Decimal(".20"))
    report = build(module)
    p = point(report, "revenue")
    assert p.delta == Decimal(30) and p.delta_status == "known"
    assert p.growth is None and p.growth_status == "missing" and "ZERO_DENOMINATOR" in p.reason
    p = point(report, "ebitda_margin")
    assert p.delta == Decimal(5) and p.delta_unit == "PERCENTAGE_POINTS"
    assert p.growth is None and p.growth_status == "not_applicable"


@pytest.mark.parametrize("prior_status", ["missing", "conflicting", "not_applicable"])
@pytest.mark.parametrize("current_status", ["missing", "conflicting", "not_applicable"])
def test_existing_nonknown_precedence_preserves_limits(prior_status, current_status):
    module = fixture()
    for pid, status in (("q3-2025", prior_status), ("q4-2025", current_status)):
        module = change(
            module,
            f"value.revenue.{pid}",
            amount=None,
            status=status,
            limitation=f"Explicit {pid} {status} limitation",
        )
    p = point(build(module), "revenue")
    expected = next(
        s
        for s in ("conflicting", "missing", "not_applicable")
        if s in (prior_status, current_status)
    )
    assert (p.prior_status, p.current_status) == (prior_status, current_status)
    assert p.delta is p.growth is None and p.delta_status == p.growth_status == expected
    assert f"Explicit q3-2025 {prior_status} limitation" in p.reason
    assert f"Explicit q4-2025 {current_status} limitation" in p.reason


def test_nongrowth_missing_input_does_not_make_growth_applicable():
    module = change(
        fixture(), "value.fcf.q4-2025", amount=None, status="conflicting", limitation="FCF conflict"
    )
    p = point(build(module), "fcf")
    assert p.delta_status == "conflicting" and p.delta is None
    assert p.growth_status == "not_applicable" and p.growth is None and "FCF conflict" in p.reason


def test_arithmetic_uses_fresh_precision38_half_even_and_restores_caller():
    module = change(fixture(), "value.revenue.q3-2025", amount=Decimal(6))
    module = change(module, "value.revenue.q4-2025", amount=Decimal(7))
    with localcontext() as caller:
        caller.prec = 9
        caller.rounding = ROUND_DOWN
        caller.traps[Inexact] = True
        caller.clear_flags()
        before = caller.copy()
        p = point(build(module), "revenue")
        assert p.delta == Decimal(1)
        assert p.growth == Decimal("0.16666666666666666666666666666666666667")
        assert p.growth_status == "known"
        assert getcontext() is caller
        assert (caller.prec, caller.rounding, caller.traps, caller.flags) == (
            before.prec,
            before.rounding,
            before.traps,
            before.flags,
        )
        refusal(change(module, "value.revenue.q4-2025", amount=Decimal("NaN")), "invalid_fact")
        assert (caller.prec, caller.rounding, caller.traps, caller.flags) == (
            before.prec,
            before.rounding,
            before.traps,
            before.flags,
        )


def test_operands_are_not_prerounded_to_caller_precision():
    module = change(
        fixture(), "value.revenue.q3-2025", amount=Decimal("100000000000000000000000000000000000.1")
    )
    module = change(
        module, "value.revenue.q4-2025", amount=Decimal("100000000000000000000000000000000000.2")
    )
    with localcontext() as caller:
        caller.prec = 3
        assert point(build(module), "revenue").delta == Decimal(".1")


@pytest.mark.parametrize(
    "prior,current", [("fy-2025", "q4-2025"), ("q4-2025", "q4-2025"), ("q4-2025", "q3-2025")]
)
def test_incompatible_periods(prior, current):
    refusal(fixture(), "incompatible_periods", prior, current)


@pytest.mark.parametrize(
    "field,value",
    [("start_date", "2025-10-02"), ("start_date", "2025-09-30"), ("end_date", "2025-07-01")],
)
def test_duration_overlap_and_reversed_date_ranges_refuse(field, value):
    refusal(change(fixture(), f"period.q4-2025.{field}", text=value), "incompatible_periods")


@pytest.mark.parametrize(
    "updates",
    [
        {"module_id": "CP-2"},
        {"status": "candidate"},
        {"status": "blocked"},
        {"status": "stale"},
        {"status": "rejected"},
        {"status": "unrun"},
        {"status": "not_in_pathway"},
        {"artifact_sha256": None},
    ],
)
def test_invalid_source_view(updates):
    refusal(fixture().model_copy(update=updates), "invalid_source_view")


@pytest.mark.parametrize(
    "updates",
    [
        {"unit": "UNITS"},
        {"currency": "EUR"},
        {"scale": Decimal(1)},
        {"basis": "IFRS · borrower"},
        {"period": "FY25: 2025-01-01 to 2025-12-31"},
    ],
)
def test_selected_amount_dimensions_and_date_relation_refuse(updates):
    refusal(change(fixture(), "value.revenue.q4-2025", **updates), "incompatible_dimensions")


@pytest.mark.parametrize(
    "field,value",
    [
        ("currency", "EUR"),
        ("unit", "UNITS"),
        ("accounting_basis", "US_GAAP"),
        ("entity_perimeter", "borrower"),
    ],
)
def test_selected_period_perimeter_and_dimensions_refuse(field, value):
    refusal(change(fixture(), f"period.q4-2025.{field}", text=value), "incompatible_dimensions")


@pytest.mark.parametrize(
    "measure,updates",
    [
        ("ebitda_margin", {"unit": "MULTIPLE"}),
        ("ebitda_margin", {"scale": Decimal(100)}),
        ("total_leverage_reported", {"currency": "USD"}),
        ("total_leverage_reported", {"unit": "MILLIONS"}),
    ],
)
def test_ratio_dimensions_refuse(measure, updates):
    refusal(change(fixture(), f"value.{measure}.q4-2025", **updates), "incompatible_dimensions")


@pytest.mark.parametrize(
    "updates",
    [
        {"amount": Decimal("NaN")},
        {"amount": Decimal("sNaN")},
        {"amount": Decimal("Infinity")},
        {"amount": Decimal("-Infinity")},
        {"amount": None},
        {"text": "30"},
        {"amount": None, "text": "30"},
        {"amount": "30"},
        {"status": "missing", "limitation": "Missing but still numeric"},
        {"amount": None, "status": "missing", "limitation": None},
        {"amount": None, "status": "conflicting", "text": "conflict", "limitation": "Conflict"},
        {"amount": None, "status": "not_applicable", "limitation": ""},
    ],
)
def test_malformed_selected_known_nonknown_and_nonfinite_facts_refuse(updates):
    refusal(change(fixture(), "value.revenue.q4-2025", **updates), "invalid_fact")


def test_malformed_period_identity_refuses():
    refusal(change(fixture(), "period.q4-2025.period_id", text=None), "invalid_fact")


@pytest.mark.parametrize(
    "fact_id",
    [
        "value.revenue.q3-2025",
        "value.revenue.q4-2025",
        "metric.revenue",
        "period.q4-2025.start_date",
    ],
)
def test_missing_selected_coordinates_are_incomplete_not_source_gaps(fact_id):
    refusal(without(fixture(), fact_id), "incomplete_register")


def test_unknown_current_period_and_absent_current_register_refuse():
    refusal(fixture(), "incomplete_register", current="q1-2026")
    module = fixture()
    refusal(
        module.model_copy(
            update={"facts": tuple(f for f in module.facts if f.table_id != "T4.14")}
        ),
        "incomplete_register",
    )


@pytest.mark.parametrize(
    "fact_id", ["value.revenue.q4-2025", "metric.revenue", "period.q4-2025.period_id"]
)
def test_duplicate_selected_coordinates_refuse(fact_id):
    module = fixture()
    duplicate = next(f for f in module.facts if f.fact_id == fact_id).model_copy(
        update={"fact_id": "duplicate"}
    )
    refusal(module.model_copy(update={"facts": (*module.facts, duplicate)}), "ambiguous_coordinate")


def test_duplicate_metric_identity_in_other_row_and_duplicate_fact_id_refuse():
    module = fixture()
    original = next(f for f in module.facts if f.fact_id == "metric.revenue")
    duplicate = original.model_copy(update={"fact_id": "duplicate", "row_id": "other.row"})
    refusal(module.model_copy(update={"facts": (*module.facts, duplicate)}), "ambiguous_coordinate")
    refusal(module.model_copy(update={"facts": (*module.facts, original)}), "ambiguous_coordinate")


def test_exact_own_basis_ignores_rolling_fy_aliases_and_labels():
    module = fixture()
    q4 = next(f for f in module.facts if f.fact_id == "value.revenue.q4-2025")
    rolling = q4.model_copy(
        update={
            "fact_id": "rolling.revenue",
            "field": "model-basis:" + "b" * 64,
            "amount": Decimal(999),
        }
    )
    module = module.model_copy(update={"facts": (*module.facts, rolling)})
    module = change(module, "value.revenue.fy-2025", amount=Decimal(777))
    module = change(module, "value.revenue.q4-2025", label="FY2025 rolling display alias")
    assert point(build(module), "revenue").current_value == Decimal(30)
    refusal(without(module, "value.revenue.q4-2025"), "incomplete_register")


def test_canonical_identity_not_row_name_or_fact_order_controls_join():
    module = fixture()
    facts = tuple(
        f.model_copy(update={"row_id": "opaque.revenue.row"}) if f.row_id == "metric.revenue" else f
        for f in reversed(module.facts)
    )
    report = build(module.model_copy(update={"facts": facts}))
    assert tuple(p.measure_id for p in report.points) == MEASURES
    assert point(report, "revenue").prior_fact_id == "value.revenue.q3-2025"


@pytest.mark.parametrize(
    "prior,current,error",
    [
        ("q3-2025", "q4-2025", None),
        ("opening-2024", "q4-2025", "incompatible_periods"),
        ("q3-2025", "opening-2024", "incompatible_periods"),
    ],
)
def test_canonical_opening_period_end_is_indexed_but_not_a_duration_comparator(
    prior, current, error
):
    # Handwritten from the unchanged financial manifest and model_interface
    # _period_accounts/_Tables.row shape. Only fiscal_quarter/component references
    # are not_applicable; an absent opening start_date/day_count remains missing.
    module = fixture()
    citation = Citation(
        source_id="financial",
        source_sha256=ORACLE["financial_source_sha256"],
        locator="page:1",
        quote="The opening balance is December 31, 2024.",
    )
    values = {
        "period_id": "opening-2024",
        "fiscal_year": "2024",
        "fiscal_quarter": None,
        "period_type": "PERIOD_END",
        "start_date": None,
        "end_date": "2024-12-31",
        "day_count": None,
        "audit_status": "unaudited",
        "currency": "USD",
        "unit": "MILLIONS",
        "accounting_basis": "IFRS",
        "entity_perimeter": "consolidated group",
        "source_id": "financial",
        "source_locator": "page:1",
        "component_period_ids": None,
    }
    opening = tuple(
        Fact(
            fact_id=f"opening-2024.{field}",
            label=field,
            table_id="T4.14",
            row_id="opening-2024",
            field=field,
            text=value,
            status="known"
            if value is not None
            else "not_applicable"
            if field in {"fiscal_quarter", "component_period_ids"}
            else "missing",
            limitation=None
            if value is not None
            else "No reference or applicable value"
            if field in {"fiscal_quarter", "component_period_ids"}
            else "Source does not supply this field",
            period="opening-2024",
            basis="IFRS · consolidated group",
            citations=(citation,),
        )
        for field, value in values.items()
    )
    with_opening = module.model_copy(update={"facts": (*module.facts, *opening)})
    if error is not None:
        refusal(with_opening, error, prior, current)
    else:
        assert build(with_opening, prior, current) == build(module, prior, current)
