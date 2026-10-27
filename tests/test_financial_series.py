"""Small fact projections; these fixtures do not qualify analyst execution."""

import json
from dataclasses import FrozenInstanceError
from decimal import Decimal
from pathlib import Path

import pytest

from deploy_vii.contracts import Citation, Fact, ModuleView
from deploy_workflow.financial_series import cp1_chart_series

ORACLE = json.loads((Path(__file__).parents[1] / "cases/charts/expected.json").read_text())
# Adopted financial_model._basis_id('historical', 'Q:<source period id>') identities.
BASES = (
    "166bb94eecfa6fdbd7bbc5a81ef57c48d46696fdc9032c1abe11abc6ad613dbb",
    "89e8b30cb7c8ce8b334dc7fba59bccc2c1dfd5ebc7d7f8b8caa5fff3c766f5cb",
    "36604f9b09d609dfe1b66ec07a153d836a007251b6564d183773b8be2b3c959a",
    "1a39b61b63ee7f787ffcf5706f5dbbea2def3aa196fc2c23e4d88b6d19b834e6",
)
METRICS = (
    "total_leverage_reported", "net_leverage_reported", "interest_coverage_reported",
    "cash_closing", "undrawn_rcf", "liquidity",
)


def fixture():
    facts = []
    citation = Citation(source_id="financial", source_sha256=ORACLE["source_authority"]["financial_sha256"],
                        locator="page:5", quote="final maturity is December 31, 2029")

    def row(table, identity, values, period):
        for field, value in values.items():
            numeric = isinstance(value, Decimal)
            money = field in {"principal", "carrying_value", "drawn_amount", "annual_amortisation"} or (table == "T4.10" and identity in METRICS[3:])
            facts.append(Fact(
                fact_id=f"{table}.{identity}.{field}", label=field, table_id=table,
                row_id=f"{table}.{identity}", field=field,
                amount=value if numeric else None, text=None if numeric or value is None else value,
                status="missing" if value is None else "known",
                limitation="Not supplied" if value is None else None,
                period=period, basis="IFRS · consolidated group", citations=(citation,),
                unit="MILLIONS" if money else "MULTIPLE" if numeric else None, currency="USD" if money else None,
                scale=Decimal(1000000) if money else Decimal(1),
            ))

    dates = ("2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01")
    for i, quarter in enumerate(ORACLE["quarters"]):
        pid = quarter["period_id"]
        row("T4.14", pid, dict(period_id=pid, period_type="QUARTER", fiscal_year="2025",
            fiscal_quarter=str(i + 1), start_date=dates[i], end_date=quarter["quarter_end"],
            currency="USD", unit="MILLIONS", accounting_basis="IFRS",
            entity_perimeter="consolidated group"), pid)
        for metric in METRICS:
            value = (quarter[metric]["amount"] if metric in METRICS[:3] else
                     quarter["cash_millions"] if metric == "cash_closing" else
                     quarter["undrawn_rcf_millions"] if metric == "undrawn_rcf" else
                     quarter["liquidity_millions"])
            field = "model-basis:" + BASES[i]
            row("T4.10", metric, {"field_1": metric} if i == 0 else {}, "dashboard")
            row("T4.10", metric, {field: None if value is None else Decimal(value)},
                f"Q{i+1} 25: {dates[i]} to {quarter['quarter_end']}")
            facts[-1] = facts[-1].model_copy(update=dict(
                unit="MULTIPLE" if metric in METRICS[:3] else "MILLIONS",
                currency=None if metric in METRICS[:3] else "USD",
                scale=Decimal(1) if metric in METRICS[:3] else Decimal(1000000),
                calculation_id=f"calculation.{metric}.{pid}", value_class="calculated"))
        row("T4.18", pid, dict(facility_id="term-loan", facility_name="Northbridge Term Loan",
            period_id=pid, facility_type="TERM_LOAN", principal=Decimal(quarter["total_debt_millions"]),
            carrying_value=Decimal(quarter["total_debt_millions"]),
            drawn_amount=Decimal(quarter["total_debt_millions"]), maturity_date="2029-12-31",
            annual_amortisation=Decimal(0), currency="USD", lease_classification="NOT_LEASE"), pid)
    return ModuleView(module_id="CP-1", title="Financials", aliases=(), status="restricted",
                      artifact_sha256="a" * 64, facts=tuple(facts))


def change(module, *, table=None, field=None, row=None, **updates):
    return module.model_copy(update={"facts": tuple(
        fact.model_copy(update=updates) if (table is None or fact.table_id == table)
        and (field is None or fact.field == field) and (row is None or fact.row_id == row)
        else fact for fact in module.facts)})


def amounts(module, figure):
    facts = {f.fact_id: f for f in module.facts}
    return [facts[p.fact_id].amount for p in figure.points]


def test_source_first_series_values_identity_and_immutability():
    module = fixture()
    figures = cp1_chart_series(module)
    assert [f.fig_id for f in figures] == ["S.1", "S.2", "S.3", "S.4"]
    assert [f.kind for f in figures] == ["line", "line", "line", "grouped"]
    assert amounts(module, figures[0]) == [None, None, None, Decimal(ORACLE["quarters"][3]["total_leverage_reported"]["amount"]), None, None, None, Decimal(1)]
    assert amounts(module, figures[1]) == [None, None, None, Decimal(6)]
    assert amounts(module, figures[2]) == [Decimal(v) for v in ("16.25", "17.5", "18.75", "20", "0", "0", "0", "0", "16.25", "17.5", "18.75", "20")]
    assert amounts(module, figures[3]) == [Decimal(50)]
    assert figures[3].points[0].category == "2029-12-31"
    assert "2025-12-31" in figures[3].title and "principal" in figures[3].title.lower()
    assert figures[2].unit == "US$m"
    for figure in figures:
        assert len({(p.series, p.category) for p in figure.points}) == len(figure.points)
        for point in figure.points:
            assert point.companion_fact_ids
            assert set(point.companion_fact_ids) <= {f.fact_id for f in module.facts}
    with pytest.raises(FrozenInstanceError):
        figures[0].title = "forged"


@pytest.mark.parametrize("status", ["unrun", "blocked", "stale", "candidate", "not_in_pathway"])
def test_only_settled_cp1_is_projected(status):
    assert cp1_chart_series(fixture().model_copy(update={"status": status})) == ()
    assert cp1_chart_series(fixture().model_copy(update={"module_id": "CP-2"})) == ()


@pytest.mark.parametrize("updates", [dict(unit="UNITS"), dict(scale=Decimal(1)),
    dict(currency="EUR"), dict(basis="IFRS · borrower"), dict(period="FY25: 2025-01-01 to 2025-12-31")])
def test_wrong_dimensions_or_period_fail_closed(updates):
    module = change(fixture(), table="T4.10", field="model-basis:" + BASES[0],
                    row="T4.10.cash_closing", **updates)
    with pytest.raises(ValueError):
        cp1_chart_series(module)


def test_missing_rcf_is_gap_and_term_headroom_never_substituted():
    module = change(fixture(), table="T4.10", row="T4.10.undrawn_rcf",
                    field="model-basis:" + BASES[0], amount=None, status="missing", limitation="RCF unavailable")
    assert amounts(module, cp1_chart_series(module)[2])[4] is None


def test_missing_quarter_is_disclosed_without_synthetic_points():
    module = fixture()
    module = module.model_copy(update={"facts": tuple(f for f in module.facts if f.row_id not in {"T4.14.q2-2025", "T4.18.q2-2025"})})
    figures = cp1_chart_series(module)
    assert all(not f.points and f.reason for f in figures[:3])


def test_missing_maturity_discloses_no_invented_date_or_zero():
    module = change(fixture(), table="T4.18", row="T4.18.q4-2025", field="maturity_date",
                    text=None, status="missing", limitation="Maturity not supplied")
    figure = cp1_chart_series(module)[3]
    assert not figure.points and "maturity" in figure.reason.lower()


def test_absent_current_facility_population_cannot_use_prior_balance():
    module = fixture()
    module = module.model_copy(update={"facts": tuple(f for f in module.facts if f.row_id != "T4.18.q4-2025")})
    figure = cp1_chart_series(module)[3]
    assert not figure.points and figure.reason


def test_duplicate_fact_coordinates_and_missing_metric_fail_closed():
    module = fixture()
    duplicate = module.facts[0].model_copy(update={"fact_id": "duplicate"})
    with pytest.raises(ValueError):
        cp1_chart_series(module.model_copy(update={"facts": (*module.facts, duplicate)}))
    module = module.model_copy(update={"facts": tuple(f for f in module.facts if f.row_id != "T4.10.cash_closing")})
    with pytest.raises(ValueError):
        cp1_chart_series(module)


def test_missing_quarters_do_not_hide_a_missing_metric_implementation():
    module = fixture()
    module = module.model_copy(update={"facts": tuple(f for f in module.facts if f.row_id not in {
        "T4.14.q2-2025", "T4.18.q2-2025", "T4.10.cash_closing"})})
    with pytest.raises(ValueError):
        cp1_chart_series(module)


def test_malformed_nonknown_maturity_fails_closed_instead_of_claiming_source_gap():
    module = change(fixture(), table="T4.18", row="T4.18.q4-2025", field="maturity_date",
                    status="missing", limitation="Not supplied")
    with pytest.raises(ValueError):
        cp1_chart_series(module)


def test_nonhistorical_period_cannot_become_current_facility_snapshot():
    module = change(fixture(), table="T4.14", row="T4.14.q4-2025", field="period_type",
                    text="FORECAST")
    with pytest.raises(ValueError):
        cp1_chart_series(module)


def test_empty_period_register_cannot_hide_malformed_facility_payload():
    module = change(fixture(), table="T4.18", row="T4.18.q4-2025", field="maturity_date",
                    status="missing", limitation="Not supplied")
    module = module.model_copy(update={"facts": tuple(f for f in module.facts if f.table_id != "T4.14")})
    with pytest.raises(ValueError):
        cp1_chart_series(module)


def test_fy_q4_snapshot_alias_is_not_double_counted_and_conflict_refuses():
    module = fixture()
    added = []
    for f in module.facts:
        if f.row_id in {"T4.14.q4-2025", "T4.18.q4-2025"}:
            updates = dict(fact_id=f.fact_id.replace("q4-2025", "fy-2025"),
                row_id=f.row_id.replace("q4-2025", "fy-2025"), period="fy-2025")
            if f.field == "period_id": updates["text"] = "fy-2025"
            if f.field == "period_type": updates["text"] = "FY"
            if f.field == "start_date": updates["text"] = "2025-01-01"
            if f.field == "fiscal_quarter": updates.update(text=None, status="not_applicable", limitation="FY")
            added.append(f.model_copy(update=updates))
    module = module.model_copy(update={"facts": (*module.facts, *added)})
    assert amounts(module, cp1_chart_series(module)[3]) == [Decimal(50)]
    module = change(module, table="T4.18", row="T4.18.fy-2025", field="principal", amount=Decimal(51))
    with pytest.raises(ValueError):
        cp1_chart_series(module)
