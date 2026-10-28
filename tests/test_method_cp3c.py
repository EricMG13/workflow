"""CP-3C Stage 1: the pure calculation equals the frozen oracle (cases/cp3c-owner).

Inputs come from the oracle's own records only: the CP-1 head values observed for the bindings
(manifest.json#fact_bindings), the frozen CP-2D oracle cells this oracle pins as its upstream
(cases/cp2d-owner/expected.json, sha256 in manifest.json#frozen_inputs), the literal analyst
submissions (submissions.json) and the composer fixtures' own input vectors. Every expected
value is read from expected.json. The run-time binding of ``{{FACT:name}}`` to an offered ref is
stood in for by the CP-2D stable id (the manifest's ref) or ``cp1:<name>`` (CP-1 fact ids are
bound in Stage 2); an unknown name binds to a ref the view never offers.
"""

import calendar
import hashlib
import json
import re
from dataclasses import replace
from datetime import date, timedelta
from decimal import Context, Decimal, localcontext
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.display import format_date
from deploy_workflow.owners import cp3c

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cp3c-owner"
EXPECTED: dict[str, Any] = json.loads((CASE / "expected.json").read_text(encoding="utf-8"))
SUBMISSIONS: dict[str, Any] = json.loads((CASE / "submissions.json").read_text(encoding="utf-8"))
MANIFEST: dict[str, Any] = json.loads((CASE / "manifest.json").read_text(encoding="utf-8"))
CP2D_EXPECTED: dict[str, Any] = json.loads(
    (ROOT / "cases" / "cp2d-owner" / "expected.json").read_text(encoding="utf-8")
)
BINDINGS: dict[str, Any] = MANIFEST["fact_bindings"]

# docs/CP3C-OWNER-LEASE.md header (rev 3; LEAD re-pins 2026-10-28 for methodology.json and the
# round 6 oracle batch, builder and manifest only) and manifest.json#frozen_inputs.
PINS = {
    "cases/cp3c-owner/manifest.json": "7a0056a1145f9a92efd11f18fd6512e8c86e508b25176d457f0fe07394ad8a5a",
    "cases/cp3c-owner/submissions.json": "8c2b08fa3a7022097aca03798b81a23fd678ba2654ff9ef970a4c02166c34e3c",
    "cases/cp3c-owner/expected.json": "50ef4a7f9199e1da4a73fc75eaaf6bc8215bef12cec26067d2d44aead0952e5f",
    "cases/cp3c-owner/builder/build.py": "b2cdb63c560abdfdd4387f5d337fb7462c93218b4c24f48c6c4142deaf00bf56",
}
PACK_CASES = ("positive", "gap_minimum_cash", "gap_no_repricing")
FIXTURES = tuple(k for k in EXPECTED["cases"] if k.startswith("fixture_"))
BALANCE_DATE = date.fromisoformat(EXPECTED["method_rules"]["balance_date"])
AS_OF = date.fromisoformat(MANIFEST["run"]["as_of"])
CURRENCY = "USD"  # expected.json#derivation_note and method_rules.currency
TOKEN = re.compile(r"\{\{FACT:([^}]+)\}\}")
STATE = {"known": "known", "missing": "gap", "not_applicable": "not_applicable"}


def test_oracle_files_match_the_lease_pins() -> None:
    for path, sha in PINS.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha, path
    for frozen in MANIFEST["frozen_inputs"]:
        digest = hashlib.sha256((ROOT / frozen["path"]).read_bytes()).hexdigest()
        assert digest == frozen["sha256"], frozen["path"]


# --- run-time binding stand-ins ----------------------------------------------------------------


def _ref(name: str) -> str:
    binding = BINDINGS.get(name)
    if binding is None:
        return f"unbound:{name}"
    return str(binding["fact_id"]) if binding["source"] == "CP-2D" else f"cp1:{name}"


OFFERED = {_ref(name): name for name in BINDINGS}


def _bind(value: Any) -> Any:
    if isinstance(value, str):
        return TOKEN.sub(lambda m: _ref(m.group(1)), value)
    if isinstance(value, list):
        return [_bind(v) for v in value]
    if isinstance(value, dict):
        return {k: _bind(v) for k, v in value.items()}
    return value


def _submission(payload: dict[str, Any]) -> cp3c.RefinancingRiskSubmission:
    return cp3c.RefinancingRiskSubmission.model_validate_json(json.dumps(_bind(payload)))


# --- inputs from the oracle's own records ------------------------------------------------------

_T410 = ("cash_closing", "undrawn_rcf", "adjusted_ebitda", "cash_interest")
# The head fact's own value_class, bound from the head in Stage 2: the T4.18 terms are source
# facts (lease, Composer); the T4.10 metrics are CP-1 calculations (the class the oracle's
# copies T3D.2.r07 and T3D.3.r02 keep under manifest.json#fact_copy_rule).
_CP1_CLASS: dict[str, cp3c.ValueClass] = {"T4.10": "calculated", "T4.18": "source"}


def _cp1_fact(name: str) -> cp3c.Cp1Fact:
    b = BINDINGS[name]
    observed = b["observed_on_promoted_head"]
    numeric = name in _T410 or b.get("field") == "annual_amortisation"
    return cp3c.Cp1Fact(
        table_id=b["table_id"],
        period=b["period"],
        status="known",
        amount=Decimal(observed) if numeric else None,
        text=None if numeric else observed,
        unit="MILLIONS" if numeric else None,
        value_class=_CP1_CLASS[b["table_id"]],
    )


def _facility_ids() -> list[str]:
    return [n[len("cp2d.") : -len(".principal")] for n in BINDINGS if n.endswith(".principal")]


def _cp1() -> cp3c.Cp1Operands:
    terms = tuple(
        cp3c.FacilityTerms(
            facility_id=fid,
            currency=CURRENCY,
            facility_name=_cp1_fact(f"{fid}.facility_name"),
            secured_status=_cp1_fact(f"{fid}.secured_status"),
            seniority=_cp1_fact(f"{fid}.seniority"),
            annual_amortisation=_cp1_fact(f"{fid}.annual_amortisation"),
        )
        for fid in _facility_ids()
    )
    return cp3c.Cp1Operands(
        cash_closing=_cp1_fact("cash_closing"),
        undrawn_rcf=_cp1_fact("undrawn_rcf"),
        adjusted_ebitda=_cp1_fact("adjusted_ebitda"),
        cash_interest=_cp1_fact("cash_interest"),
        facilities=terms,
    )


def _cells(tables: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for table in tables.values():
        for _, cells in table["rows"]:
            for cell in cells if isinstance(cells, list) else [cells]:
                out[cell["fact_id"]] = cell
    return out


CP2D_POSITIVE = _cells(CP2D_EXPECTED["cases"]["positive"]["tables"])


def _cp2d_fact(cp2d_case: str, name: str) -> cp3c.Cp2dFact:
    fact_id = BINDINGS[name]["fact_id"]
    cell = _cells(CP2D_EXPECTED["cases"][cp2d_case]["tables"])[fact_id]
    if cell["state"] != "known":
        # The CP-2D oracle records no value_class on a gap; a fact's class does not change with
        # its state, so the known twin's class stands in for the head's (Stage 2 binds it).
        return cp3c.Cp2dFact(
            fact_id=fact_id,
            status="missing",
            unit=cell["unit"],
            value_class=CP2D_POSITIVE[fact_id]["value_class"],
            reason=cell["reason"],
        )
    numeric = "amount" in cell
    return cp3c.Cp2dFact(
        fact_id=fact_id,
        status="known",
        amount=Decimal(cell["amount"]) if numeric else None,
        text=None if numeric else cell["shown"],
        unit=cell.get("unit"),
        # manifest.json#fact_copy_rule: the CP-2D head fact's period at the balance date.
        period=BALANCE_DATE.isoformat() if numeric else None,
        value_class=cell["value_class"],
    )


def _cp2d(cp2d_case: str) -> cp3c.Cp2dOperands:
    wall = tuple(
        cp3c.WallRow(
            facility_id=fid,
            principal=_cp2d_fact(cp2d_case, f"cp2d.{fid}.principal"),
            maturity_date=_cp2d_fact(cp2d_case, f"cp2d.{fid}.maturity_date"),
            months=_cp2d_fact(cp2d_case, f"cp2d.{fid}.months"),
            inside_horizon=_cp2d_fact(cp2d_case, f"cp2d.{fid}.inside_horizon"),
        )
        for fid in _facility_ids()
    )
    return cp3c.Cp2dOperands(
        horizon=_cp2d_fact(cp2d_case, "cp2d.horizon"),
        run_rate=_cp2d_fact(cp2d_case, "cp2d.run_rate"),
        minimum_cash=_cp2d_fact(cp2d_case, "cp2d.min_cash"),
        funding_gap=_cp2d_fact(cp2d_case, "cp2d.funding_gap"),
        wall=wall,
    )


def _inputs(case: str) -> cp3c.Cp3cInputs:
    return cp3c.Cp3cInputs(
        balance_date=BALANCE_DATE,
        as_of=AS_OF,
        currency=CURRENCY,
        cp1=_cp1(),
        cp2d=_cp2d(EXPECTED["cases"][case]["consumes_cp2d_case"]),
        submission=_submission(SUBMISSIONS["cp3c"][case]),
        offered=OFFERED,
    )


def _fixture_operands(name: str) -> tuple[cp3c.Operands, int]:
    given = EXPECTED["cases"][name]["inputs"]

    def dec(v: str | None) -> Decimal | None:
        return None if v is None else Decimal(v)

    facilities = []
    for f in given["facilities"]:
        maturity = date.fromisoformat(f["maturity"])
        months, inside = cp3c.wall_position(
            balance_date=BALANCE_DATE,
            maturity=maturity,
            horizon_months=given["cp2d_horizon_months"],
        )
        facilities.append(
            cp3c.FacilityOperand(
                facility_id=f["id"],
                principal=Decimal(f["principal"]),
                maturity_date=maturity,
                months=months,
                inside_horizon=inside,
                annual_amortisation=dec(f["annual_amortisation"]),
                secured_status=f["secured_status"],
                seniority=f["seniority"],
            )
        )
    operands = cp3c.Operands(
        cash=dec(given["cash"]),
        undrawn_revolver=dec(given["undrawn_revolver"]),
        run_rate_annual=dec(given["run_rate_annual"]),
        minimum_cash=dec(given["minimum_cash"]),
        adjusted_ebitda=dec(given["adjusted_ebitda"]),
        cash_interest_paid=dec(given["cash_interest"]),
        facilities=tuple(facilities),
    )
    return operands, int(given["margin_step_up_bps"])


# --- comparison helpers ------------------------------------------------------------------------


def _derived(r: cp3c.Refinancing) -> dict[str, Any]:
    """The composer's values in the oracle's ``derived`` shape (no arithmetic here)."""
    return {
        "base_resources_before_flows": r.base_resources,
        "run_rate_annual": r.operands.run_rate_annual,
        "facilities": [
            {
                "id": m.facility.facility_id,
                "months": m.facility.months,
                "inside_horizon": m.facility.inside_horizon,
                "principal": m.facility.principal,
                "amortisation_before_maturity": m.amortisation_before_maturity,
                "principal_payable_at_maturity": m.principal_payable,
                "resources_at_maturity": m.resources,
                "resources_applied": m.applied,
                "refinancing_need": m.need,
                "cover": m.cover,
            }
            for m in r.maturities
        ],
        "total_principal": r.total_principal,
        "total_principal_payable_at_maturity": r.total_principal_payable,
        "total_resources_applied": r.total_applied,
        "total_refinancing_need": r.total_need,
        "principal_after_cp2d_horizon": r.principal_after_horizon,
        "nearest_maturity": (
            r.nearest_maturity.isoformat()
            if isinstance(r.nearest_maturity, date)
            else r.nearest_maturity
        ),
        "months_to_nearest_maturity": r.months_to_nearest,
        "principal_payable_over_ebitda": r.payable_over_ebitda,
        "need_over_ebitda": r.need_over_ebitda,
        "added_annual_cash_interest": r.added_interest,
        "pro_forma_cash_interest": r.pro_forma_interest,
        "interest_cover": r.interest_cover,
        "pro_forma_interest_cover": r.pro_forma_interest_cover,
        "creditor_position": [
            {
                "id": c.facility.facility_id,
                "secured": c.facility.secured_status,
                "seniority": c.facility.seniority,
                "principal": c.facility.principal,
                "share": c.share,
                "claims_at_or_ahead": c.claims_at_or_ahead,
                "claims_over_ebitda": c.claims_over_ebitda,
            }
            for c in r.creditors
        ],
        "claims_at_or_ahead_of_most_junior": r.junior_claims,
        "junior_over_ebitda": r.junior_over_ebitda,
    }


def _missing(value: Any) -> bool:
    return isinstance(value, cp3c.Gap) and value.applicable


def _same(expected: Any, actual: Any, at: str = "") -> None:
    """Oracle equality: numeric Decimal equality, ``nm`` is not applicable, None is missing."""
    if expected is None:
        assert _missing(actual), f"{at}: expected missing, got {actual!r}"
    elif expected == "nm":
        assert isinstance(actual, cp3c.Gap) and not actual.applicable, f"{at}: {actual!r}"
    elif isinstance(actual, Decimal):
        assert isinstance(expected, str) and Decimal(expected) == actual, (
            f"{at}: {expected!r} != {actual!r}"
        )
    elif isinstance(expected, dict):
        assert isinstance(actual, dict) and expected.keys() == actual.keys(), at
        for key in expected:
            _same(expected[key], actual[key], f"{at}.{key}")
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(expected) == len(actual), at
        for i, (e, a) in enumerate(zip(expected, actual, strict=True)):
            _same(e, a, f"{at}[{i}]")
    else:
        assert expected == actual, f"{at}: {expected!r} != {actual!r}"


_OPTIONAL = ("unit", "currency", "period", "formula", "reason", "cp1_operand", "cp2d_operand")


def _cell_view(c: cp3c.Cell) -> dict[str, Any]:
    out: dict[str, Any] = {
        "fact_id": c.fact_id,
        "state": STATE[c.status],
        "shown": c.shown,
        "value_class": c.value_class,
    }
    if c.amount is not None:
        out["amount"] = c.amount
    for key in _OPTIONAL:
        if getattr(c, key) is not None:
            out[key] = getattr(c, key)
    return out


def _expected_cell(e: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in e.items() if k != "shown_pattern"}
    if "amount" in out:
        out["amount"] = Decimal(out["amount"])
    return out


# --- pack-run cases: derived values, tables, ledgers, claims -----------------------------------


@pytest.mark.parametrize("case", PACK_CASES)
def test_pack_case_derived_values(case: str) -> None:
    result = cp3c.compute(_inputs(case))
    _same(EXPECTED["cases"][case]["derived"], _derived(result.refinancing), case)


@pytest.mark.parametrize("case", PACK_CASES)
def test_pack_case_missing_is_not_zero(case: str) -> None:
    derived = _derived(cp3c.compute(_inputs(case)).refinancing)
    for key in EXPECTED["cases"][case]["missing_not_zero"]:
        assert _missing(derived[key]), (case, key)


@pytest.mark.parametrize("case", PACK_CASES)
def test_pack_case_tables(case: str) -> None:
    want = EXPECTED["cases"][case]["tables"]
    got = {t.table_id: t for t in cp3c.compute(_inputs(case)).tables}
    assert list(got) == list(want)
    for table_id, table in want.items():
        t = got[table_id]
        assert (t.title, t.row_header, list(t.columns)) == (
            table["title"],
            table["row_header"],
            table["columns"],
        ), table_id
        assert [r.label for r in t.rows] == [r[0] for r in table["rows"]], table_id
        for row, (_, cells) in zip(t.rows, table["rows"], strict=True):
            expected_cells = cells if isinstance(cells, list) else [cells]
            assert [_cell_view(c) for c in row.cells] == [_expected_cell(e) for e in expected_cells]


def test_table_titles_and_ids_are_the_registered_ones() -> None:
    module = EXPECTED["cp3c_module"]
    result = cp3c.compute(_inputs("positive"))
    tables: list[cp3c.Table | cp3c.TextTable] = [
        *result.tables,
        result.judgments,
        result.gaps_ledger,
        result.trace,
    ]
    assert [t.table_id for t in tables] == module["table_ids"]
    assert {t.table_id: t.title for t in tables} == module["table_titles"]


@pytest.mark.parametrize("case", PACK_CASES)
def test_pack_case_ledgers_limitations_and_status(case: str) -> None:
    want = EXPECTED["cases"][case]
    result = cp3c.compute(_inputs(case))
    assert [list(r) for r in result.judgments.rows] == want["T3D.7_rows"]
    assert [list(r) for r in result.gaps_ledger.rows] == want["T3D.8_rows"]
    assert [list(r) for r in result.trace.rows] == want["T3D.9_rows"]
    assert list(result.own_limitations) == want["own_limitations"]
    assert result.status == want["status"]


@pytest.mark.parametrize("case", PACK_CASES)
def test_pack_case_claims(case: str) -> None:
    got = [
        {
            "claim_id": c.claim_id,
            "template": c.template,
            "text": c.text,
            "references": list(c.references),
            "cites_from": list(c.cites_from),
        }
        for c in cp3c.compute(_inputs(case)).claims
    ]
    want = [
        {k: v for k, v in claim.items() if k != "text_is_pattern"}
        for claim in EXPECTED["cases"][case]["claims"]
    ]
    assert got == want


def test_cp2d_copies_carry_the_cp2d_cell_values() -> None:
    """Consumption proof (lease D3): the copied cells are the CP-2D cells, gaps never 0."""
    for case in ("positive", "gap_minimum_cash"):
        cp2d_cells = _cells(
            CP2D_EXPECTED["cases"][EXPECTED["cases"][case]["consumes_cp2d_case"]]["tables"]
        )
        result = cp3c.compute(_inputs(case))
        copies = [c for t in result.tables for r in t.rows for c in r.cells if c.cp2d_operand]
        assert copies
        for c in copies:
            source = cp2d_cells[c.cp2d_operand or ""]
            assert STATE[c.status] == source["state"] and c.shown == source["shown"], c.fact_id
            if c.status == "known":
                assert c.value_class == source["value_class"], c.fact_id
            else:
                assert c.amount is None and c.reason == source["reason"], c.fact_id


# --- composer fixtures -------------------------------------------------------------------------


@pytest.mark.parametrize("name", FIXTURES)
def test_fixture_wall_position_is_cp2ds_whole_month_rule(name: str) -> None:
    operands, _ = _fixture_operands(name)
    derived = EXPECTED["cases"][name]["derived"]["facilities"]
    by_id = {f.facility_id: f for f in operands.facilities}
    for row in derived:
        f = by_id[row["id"]]
        assert (f.months, f.inside_horizon) == (row["months"], row["inside_horizon"]), name


@pytest.mark.parametrize("name", FIXTURES)
def test_fixture_derived_values(name: str) -> None:
    operands, bps = _fixture_operands(name)
    result = cp3c.compose_refinancing(operands=operands, step_up_bps=bps)
    _same(EXPECTED["cases"][name]["derived"], _derived(result), name)
    derived = _derived(result)
    for key in EXPECTED["cases"][name]["missing_not_zero"]:
        assert _missing(derived[key]), (name, key)


def test_unassessed_step_up_is_missing_and_zero_step_up_is_known_zero() -> None:
    operands, _ = _fixture_operands("fixture_zero_step_up")
    zero = cp3c.compose_refinancing(operands=operands, step_up_bps=0)
    unassessed = cp3c.compose_refinancing(operands=operands, step_up_bps=None)
    assert zero.added_interest == 0 and zero.added_interest is not None
    assert _missing(unassessed.added_interest) and _missing(unassessed.pro_forma_interest_cover)


# --- lease boundaries the oracle states as rules (not oracle cases) ----------------------------


def _single(**changes: Any) -> cp3c.Operands:
    operands, _ = _fixture_operands("fixture_zero_step_up")
    return replace(operands, **changes)


def test_a_covered_maturity_is_a_known_zero_need_not_missing() -> None:
    """method_rules.refinancing_need: a computed 0 is 'no need', distinct from missing."""
    r = cp3c.compose_refinancing(operands=_single(cash=Decimal(1000)), step_up_bps=0)
    assert r.total_need == 0 and r.total_need is not None
    assert r.maturities[0].cover == 1


NM = "(ZERO_OR_NEGATIVE_DENOMINATOR)"


def _nm(reason: str) -> cp3c.Gap:
    return cp3c.Gap(f"Not meaningful: {reason} {NM}", applicable=False)


def test_zero_interest_gives_not_applicable_cover() -> None:
    """method_rules.interest_cover: a zero interest is not_applicable (C-2 reason)."""
    r = cp3c.compose_refinancing(operands=_single(cash_interest_paid=Decimal(0)), step_up_bps=0)
    assert r.interest_cover == _nm("cash interest paid is zero or negative")
    assert r.pro_forma_interest_cover == _nm("cash interest paid is zero or negative")


def test_fully_amortised_principal_gives_not_applicable_cover() -> None:
    """method_rules.cover: not_applicable when the principal payable at maturity is 0."""
    operands = _single()
    (f,) = operands.facilities
    r = cp3c.compose_refinancing(
        operands=replace(operands, facilities=(replace(f, annual_amortisation=Decimal(50)),)),
        step_up_bps=0,
    )
    assert r.maturities[0].principal_payable == 0
    assert r.maturities[0].cover == _nm("principal payable at maturity is zero")


def _two_facilities() -> tuple[cp3c.Operands, cp3c.FacilityOperand, cp3c.FacilityOperand]:
    operands, _ = _fixture_operands("fixture_two_facilities")
    earlier, later = sorted(operands.facilities, key=lambda f: str(f.maturity_date))
    return operands, earlier, later


def test_equal_maturity_dates_order_by_facility_id() -> None:
    """Ruling C-4 (2D6): ties by facility_id, whatever order the facilities arrive in."""
    operands, earlier, later = _two_facilities()
    tied = replace(
        later, facility_id="a-loan", maturity_date=earlier.maturity_date, months=earlier.months
    )
    r = cp3c.compose_refinancing(
        operands=replace(operands, facilities=(earlier, tied)), step_up_bps=0
    )
    assert [m.facility.facility_id for m in r.maturities] == ["a-loan", earlier.facility_id]


def test_c4_facilities_order_by_maturity_date_not_months() -> None:
    """Ruling C-4: (maturity_date, facility_id). 2028-08-30 is 31 whole months from 2025-12-31,
    as is 2028-07-31, so a months order would put a-loan first."""
    operands, earlier, later = _two_facilities()
    maturity = date(2028, 8, 30)
    months, inside = cp3c.wall_position(
        balance_date=BALANCE_DATE, maturity=maturity, horizon_months=24
    )
    assert months == earlier.months
    same_month = replace(
        later, facility_id="a-loan", maturity_date=maturity, months=months, inside_horizon=inside
    )
    r = cp3c.compose_refinancing(
        operands=replace(operands, facilities=(same_month, earlier)), step_up_bps=0
    )
    assert [m.facility.facility_id for m in r.maturities] == [earlier.facility_id, "a-loan"]
    assert r.nearest_maturity == earlier.maturity_date


def test_amortisation_of_a_matured_facility_stops_at_its_maturity() -> None:
    """method_rules.resources_at_maturity: each facility amortises to min(date, own maturity),
    so moving a later, non-amortising maturity leaves its resources unchanged at a zero flow."""
    operands, earlier, later = _two_facilities()
    amortising = replace(earlier, annual_amortisation=Decimal(6))
    flat = replace(later, annual_amortisation=Decimal(0))
    resources = []
    assert isinstance(later.months, int)
    for months in (later.months, later.months + 12):
        moved = replace(flat, months=months)
        r = cp3c.compose_refinancing(
            operands=replace(operands, facilities=(amortising, moved)), step_up_bps=0
        )
        resources.append(r.maturities[1].resources)
    assert resources[0] is not None and resources[0] == resources[1]


def test_ratios_are_stored_to_four_places_half_up() -> None:
    """ratio_storage_rule: 4 dp half-up (1/32 = 0.03125 stores 0.0313, not half-even 0.0312)."""
    r = cp3c.compose_refinancing(
        operands=_single(adjusted_ebitda=Decimal(1), cash_interest_paid=Decimal(32)),
        step_up_bps=None,
    )
    assert r.interest_cover == Decimal("0.0313")


# --- validator refusals (calculation-level) ----------------------------------------------------

REFUSALS = [k for k in SUBMISSIONS["refusal_inputs"] if k != "note"]


@pytest.mark.parametrize("name", REFUSALS)
def test_each_refusal_payload_yields_exactly_its_issue(name: str) -> None:
    entry = SUBMISSIONS["refusal_inputs"][name]
    issues = cp3c.submission_issues(submission=_submission(entry["payload"]), offered=OFFERED)
    assert list(issues) == [EXPECTED["refusals"][name]]


@pytest.mark.parametrize("case", PACK_CASES)
def test_the_case_literals_are_valid(case: str) -> None:
    assert (
        cp3c.submission_issues(submission=_submission(SUBMISSIONS["cp3c"][case]), offered=OFFERED)
        == ()
    )


@pytest.mark.parametrize("attempt", ["attempt_0", "attempt_1"])
def test_blocked_cp3c_attempts_are_invalid(attempt: str) -> None:
    payload = SUBMISSIONS["cp3c_blocked"][attempt]
    issues = cp3c.submission_issues(submission=_submission(payload), offered=OFFERED)
    assert list(issues) == EXPECTED["negative_cases"]["blocked_cp3c"][attempt]["issues"]


@pytest.mark.parametrize("bps", [0, 1000])
def test_step_up_bounds_are_inclusive(bps: int) -> None:
    payload = json.loads(json.dumps(SUBMISSIONS["cp3c"]["positive"]))
    payload["repricing"]["bps"] = bps
    assert cp3c.submission_issues(submission=_submission(payload), offered=OFFERED) == ()


@pytest.mark.parametrize("probe", EXPECTED["prohibited_probe"], ids=lambda p: p["text"])
def test_prohibited_probe(probe: dict[str, Any]) -> None:
    assert list(cp3c.prohibited_conclusions("probe", probe["text"])) == probe["issues"]


def test_compute_refuses_an_invalid_submission() -> None:
    entry = SUBMISSIONS["refusal_inputs"]["step_up_over_limit"]
    inputs = replace(_inputs("positive"), submission=_submission(entry["payload"]))
    with pytest.raises(ValueError, match="must be between 0 and 1000"):
        cp3c.compute(inputs)


# --- LEAD rulings round 5 (docs/rulings/2026-10-28-stage1.md "# Round 5", CP-3C) -------------


def _positive_with(
    *terms: cp3c.FacilityTerms, wall: tuple[cp3c.WallRow, ...] | None = None
) -> cp3c.Cp3cInputs:
    inputs = _inputs("positive")
    cp2d = inputs.cp2d if wall is None else replace(inputs.cp2d, wall=wall)
    return replace(inputs, cp1=replace(inputs.cp1, facilities=terms), cp2d=cp2d)


def _positive_terms() -> cp3c.FacilityTerms:
    (terms,) = _inputs("positive").cp1.facilities
    return terms


def _positive_row() -> cp3c.WallRow:
    (row,) = _inputs("positive").cp2d.wall
    return row


def _missing_cp1(name: str) -> cp3c.Cp1Fact:
    """A CP-1 head fact the head states as missing (its own limitation as the reason)."""
    b = BINDINGS[name]
    numeric = name in _T410 or b.get("field") == "annual_amortisation"
    return cp3c.Cp1Fact(
        table_id=b["table_id"],
        period=b["period"],
        status="missing",
        unit="MILLIONS" if numeric else None,
        value_class=_CP1_CLASS[b["table_id"]],
        reason="Not stated in the source",
    )


def _cp1_amount(name: str, amount: str) -> cp3c.Cp1Fact:
    return replace(_cp1_fact(name), amount=Decimal(amount))


def _with_cp1(**facts: Any) -> cp3c.Cp3cInputs:
    """The positive case with some CP-1 T4.10 facts replaced (Any: replace() checks the names)."""
    inputs = _inputs("positive")
    return replace(inputs, cp1=replace(inputs.cp1, **facts))


def _with_step_up(inputs: cp3c.Cp3cInputs, bps: int) -> cp3c.Cp3cInputs:
    payload = json.loads(json.dumps(SUBMISSIONS["cp3c"]["positive"]))
    payload["repricing"]["bps"] = bps
    return replace(inputs, submission=_submission(payload))


def _gone(fact: cp3c.Cp2dFact, reason: str) -> cp3c.Cp2dFact:
    return replace(fact, status="missing", amount=None, text=None, period=None, reason=reason)


def _no_amortisation() -> cp3c.FacilityTerms:
    missing = _missing_cp1("term-loan.annual_amortisation")
    return replace(_positive_terms(), annual_amortisation=missing)


# Cells that are gaps in every case (lease: no LME evidence and no stress case is bound).
_ALWAYS_GAPS = {f"T3D.5.r0{r}.c{c}" for r in (1, 2) for c in (2, 3)}


def _own_gaps(result: cp3c.Cp3cResult) -> dict[str, tuple[str, str | None]]:
    """fact_id -> (status, reason) of each own cell that is not known; copies keep their
    upstream reason and are left out (T3D.3.r01 is an own negation of the CP-1 outflow)."""
    return {
        c.fact_id: (c.status, c.reason)
        for t in result.tables
        for r in t.rows
        for c in r.cells
        if c.status != "known"
        and c.cp2d_operand is None
        and c.cp1_operand in (None, "cash_interest")
        and c.fact_id not in _ALWAYS_GAPS
    }


def _cells_of(result: cp3c.Cp3cResult) -> dict[str, cp3c.Cell]:
    return {c.fact_id: c for t in result.tables for r in t.rows for c in r.cells}


def _claim(result: cp3c.Cp3cResult, claim_id: str) -> str:
    (claim,) = (c for c in result.claims if c.claim_id == claim_id)
    return claim.template


def _all(ids: list[str], status: str, reason: str) -> dict[str, tuple[str, str | None]]:
    return dict.fromkeys(ids, (status, reason))


_ROW_PAYABLE = ["T3D.1.r01.c5", "T3D.1.r01.c6"]
_ROW_RESOURCES = [f"T3D.1.r01.c{n}" for n in (7, 8, 9, 10)]
_RESOURCES = [*_ROW_RESOURCES, "T3D.2.r02", "T3D.2.r03", "T3D.2.r09"]
_PAYABLE = [*_ROW_PAYABLE, "T3D.2.r01", "T3D.2.r04", "T3D.2.r08"]
_REPRICED = ["T3D.3.r05", "T3D.3.r06", "T3D.3.r07", "T3D.3.r08"]
_CLAIMS = ["T3D.4.r01.c5", "T3D.4.r01.c6", "T3D.5.r01.c1", "T3D.5.r02.c1"]
_OVER_EBITDA = ["T3D.2.r08", "T3D.2.r09", "T3D.4.r01.c6", "T3D.5.r02.c1"]
AMORT = "Not calculable: facility term-loan annual amortisation is not stated"
COST = "An assumed margin step-up on the principal payable at maturity adds "
LME_TAIL = (
    "; the position after such an exercise is [T3D.5.r01.c2] because the legal capacity "
    "evidence is not bound."
)
LME_GAP = (
    "Claims at or ahead of the most junior facility are [T3D.5.r01.c1] before any "
    "liability-management exercise, because {cause}" + LME_TAIL
)
NEED_GAP = (
    "Principal payable at maturity totals {r01}; the refinancing need after resources is "
    "[T3D.2.r03], because {cause}."
)
DATE = format_date(BALANCE_DATE)


# C-1 COST-01


def test_c1_cost_claim_at_a_zero_step_up_leaves_interest_cover() -> None:
    result = cp3c.compute(_with_step_up(_inputs("positive"), 0))
    assert _claim(result, "CP-3C-COST-01") == (
        f"{COST}{{T3D.3.r06|US$ m}} to annual cash interest and leaves interest cover at "
        "{T3D.3.r03|x}."
    )


def test_c1_cost_claim_with_cover_raised_changes_interest_cover() -> None:
    """Negative EBITDA: the cover rises towards zero as interest grows."""
    result = cp3c.compute(_with_cp1(adjusted_ebitda=_cp1_amount("adjusted_ebitda", "-30")))
    assert _claim(result, "CP-3C-COST-01") == (
        f"{COST}{{T3D.3.r06|US$ m}} to annual cash interest and changes interest cover from "
        "{T3D.3.r03|x} to {T3D.3.r08|x}."
    )


def test_c1_cost_claim_with_one_cover_not_known_keeps_the_known_side() -> None:
    result = cp3c.compute(_with_cp1(cash_interest=_cp1_amount("cash_interest", "0")))
    assert _claim(result, "CP-3C-COST-01") == (
        f"{COST}{{T3D.3.r06|US$ m}} to annual cash interest; interest cover is [T3D.3.r03] "
        "before and {T3D.3.r08|x} after it."
    )


def test_c1_cost_claim_with_neither_cover_known() -> None:
    result = cp3c.compute(_with_cp1(cash_interest=_missing_cp1("cash_interest")))
    assert _claim(result, "CP-3C-COST-01") == (
        f"{COST}{{T3D.3.r06|US$ m}} to annual cash interest; interest cover is [T3D.3.r03] "
        "before and [T3D.3.r08] after it."
    )


# C-2 reasons


def test_c2_missing_amortisation_names_the_facility() -> None:
    result = cp3c.compute(_positive_with(_no_amortisation()))
    assert _own_gaps(result) == _all([*_PAYABLE, *_RESOURCES, *_REPRICED], "missing", AMORT)


def test_c2_resources_reason_takes_minimum_cash_before_amortisation() -> None:
    inputs = _inputs("gap_minimum_cash")
    result = cp3c.compute(
        replace(inputs, cp1=replace(inputs.cp1, facilities=(_no_amortisation(),)))
    )
    assert _own_gaps(result) == {
        **_all([*_PAYABLE, *_REPRICED], "missing", AMORT),
        **_all(_RESOURCES, "missing", cp3c.REASON_MINIMUM_CASH),
    }


@pytest.mark.parametrize(
    ("names", "label"),
    [
        (("cash_closing",), "cash and cash equivalents"),
        (("undrawn_rcf",), "undrawn revolver"),
        (("undrawn_rcf", "cash_closing"), "cash and cash equivalents"),
    ],
)
def test_c2_missing_resources_operand_names_the_first_in_formula_order(
    names: tuple[str, ...], label: str
) -> None:
    result = cp3c.compute(_with_cp1(**{n: _missing_cp1(n) for n in names}))
    reason = f"Not calculable: {label} is missing"
    assert _own_gaps(result) == _all(_RESOURCES, "missing", reason)


def test_c2_missing_run_rate_names_the_cp2d_flow() -> None:
    inputs = _inputs("positive")
    run_rate = _gone(inputs.cp2d.run_rate, "Not calculable: Operating cash flow is missing")
    result = cp3c.compute(replace(inputs, cp2d=replace(inputs.cp2d, run_rate=run_rate)))
    reason = "Not calculable: CP-2D run-rate annual flow is missing"
    assert _own_gaps(result) == _all(_RESOURCES, "missing", reason)


def test_c2_missing_ebitda_and_cash_interest() -> None:
    ebitda = cp3c.compute(_with_cp1(adjusted_ebitda=_missing_cp1("adjusted_ebitda")))
    assert _own_gaps(ebitda) == _all(
        ["T3D.2.r08", "T3D.2.r09", "T3D.3.r03", "T3D.3.r08", "T3D.4.r01.c6", "T3D.5.r02.c1"],
        "missing",
        "Not calculable: adjusted EBITDA is missing",
    )
    interest = cp3c.compute(_with_cp1(cash_interest=_missing_cp1("cash_interest")))
    assert _own_gaps(interest) == _all(
        ["T3D.3.r01", "T3D.3.r03", "T3D.3.r07", "T3D.3.r08"],
        "missing",
        "Not calculable: cash interest paid is missing",
    )


@pytest.mark.parametrize("ebitda", ["0", "-30"])
def test_c2_non_positive_ebitda_is_not_meaningful(ebitda: str) -> None:
    result = cp3c.compute(_with_cp1(adjusted_ebitda=_cp1_amount("adjusted_ebitda", ebitda)))
    reason = f"Not meaningful: adjusted EBITDA is zero or negative {NM}"
    assert _own_gaps(result) == _all(_OVER_EBITDA, "not_applicable", reason)


def test_c2_zero_cash_interest_and_zero_balloon_are_not_meaningful() -> None:
    result = cp3c.compute(_with_cp1(cash_interest=_cp1_amount("cash_interest", "0")))
    reason = f"Not meaningful: cash interest paid is zero or negative {NM}"
    assert _own_gaps(result) == {"T3D.3.r03": ("not_applicable", reason)}
    amortised = _cp1_amount("term-loan.annual_amortisation", "50")
    result = cp3c.compute(_positive_with(replace(_positive_terms(), annual_amortisation=amortised)))
    reason = f"Not meaningful: principal payable at maturity is zero {NM}"
    assert _own_gaps(result) == {"T3D.1.r01.c10": ("not_applicable", reason)}


@pytest.mark.parametrize(
    ("field", "term"), [("secured_status", "secured status"), ("seniority", "seniority")]
)
def test_c2_unstated_ranking_names_the_facility_and_term(field: str, term: str) -> None:
    name = f"term-loan.{field}"
    for fact in (replace(_cp1_fact(name), text="NOT_STATED"), _missing_cp1(name)):
        change: dict[str, Any] = {field: fact}
        result = cp3c.compute(_positive_with(replace(_positive_terms(), **change)))
        reason = f"Not calculable: facility term-loan {term} is not stated"
        assert _own_gaps(result) == _all(_CLAIMS, "missing", reason)


# C-3 claim gap forms


def test_c3_need_claim_names_the_unstated_amortisation() -> None:
    result = cp3c.compute(_positive_with(_no_amortisation()))
    cause = "facility term-loan annual amortisation is not stated"
    assert _claim(result, "CP-3C-NEED-01") == NEED_GAP.format(r01="[T3D.2.r01]", cause=cause)


def test_c3_need_claim_names_the_missing_operand() -> None:
    result = cp3c.compute(_with_cp1(cash_closing=_missing_cp1("cash_closing")))
    assert _claim(result, "CP-3C-NEED-01") == NEED_GAP.format(
        r01="{T3D.2.r01|US$ m}", cause="cash and cash equivalents is missing"
    )


def test_c3_lme_claim_names_the_unstated_ranking() -> None:
    unstated = replace(_cp1_fact("term-loan.secured_status"), text="NOT_STATED")
    result = cp3c.compute(_positive_with(replace(_positive_terms(), secured_status=unstated)))
    assert _claim(result, "CP-3C-LME-01") == (
        "Claims at or ahead of the most junior facility are [T3D.5.r01.c1] before any "
        "liability-management exercise, because facility term-loan secured status is not stated"
        f"{LME_TAIL}"
    )


def test_c3_burden_claim_with_non_positive_ebitda() -> None:
    result = cp3c.compute(_with_cp1(adjusted_ebitda=_cp1_amount("adjusted_ebitda", "0")))
    assert _claim(result, "CP-3C-BURDEN-01") == (
        "Principal payable at maturity is [T3D.2.r08] of adjusted EBITDA for the twelve months "
        f"to {DATE}, because adjusted EBITDA is zero or negative; the refinancing need is "
        "[T3D.2.r09] of the same earnings."
    )


def test_unruled_claim_slots_take_the_chip_form() -> None:
    """Not ruled (listed for LEAD): with the amortisation not stated, HORIZON-01, BURDEN-01 and
    COST-01 keep their pinned or C-1 words and show each cell that is not known as its chip."""
    result = cp3c.compute(_positive_with(_no_amortisation()))
    assert _claim(result, "CP-3C-HORIZON-01") == (
        "The liquidity analysis reports a funding gap of {T3D.2.r10|US$ m} at its horizon end, "
        "while [T3D.2.r04] falls due after that horizon."
    )
    assert _claim(result, "CP-3C-BURDEN-01") == (
        "Principal payable at maturity is [T3D.2.r08] of adjusted EBITDA for the twelve months "
        f"to {DATE}; the refinancing need is [T3D.2.r09] of the same earnings."
    )
    assert _claim(result, "CP-3C-COST-01") == (
        f"{COST}[T3D.3.r06] to annual cash interest; interest cover is {{T3D.3.r03|x}} before "
        "and [T3D.3.r08] after it."
    )


# C-6 other states


def test_c6_a_facility_in_another_currency_uses_the_2d5_wording() -> None:
    """Ruling A5: the currency is the T4.18 row's own text fact, so 2D5 is reached while the
    CP-2D wall principal is missing (a read through _maturity_figure would raise first)."""
    fx = "Not calculable: facility term-loan is in EUR, not USD; no FX conversion is applied"
    row = _positive_row()
    wall = (replace(row, principal=_gone(row.principal, fx)),)
    result = cp3c.compute(_positive_with(replace(_positive_terms(), currency="EUR"), wall=wall))
    assert _own_gaps(result) == _all(
        [*_PAYABLE, *_RESOURCES, *_REPRICED, "T3D.4.r01.c4", *_CLAIMS], "missing", fx
    )
    cells = _cells_of(result)
    statuses = [cells[f"T3D.1.r01.c{n}"].status for n in (1, 2, 3, 4)]
    assert statuses == ["missing", "known", "known", "known"]
    assert result.own_limitations[-3] == (
        "Facility term-loan is denominated in EUR; maturity-wall totals and shares are not "
        "calculated because no FX conversion is applied."
    )
    assert list(result.gaps_ledger.rows[-3]) == ["Facility currency (term-loan)", "Limitation"]
    cause = "the total needs every facility in USD, and one is not"  # round 8 B2 (L5 frame)
    assert _claim(result, "CP-3C-NEED-01") == NEED_GAP.format(r01="[T3D.2.r01]", cause=cause)
    assert _claim(result, "CP-3C-LME-01") == LME_GAP.format(cause=cause)


def test_c6_an_empty_register_settles_with_its_own_line() -> None:
    none = "Not calculable: no facility is in the CP-1 debt register"
    result = cp3c.compute(_positive_with(wall=()))
    t3d2 = [f"T3D.2.r0{n}" for n in (1, 2, 3, 4, 5, 6, 8, 9)]
    assert _own_gaps(result) == _all(
        [*t3d2, *_REPRICED, "T3D.5.r01.c1", "T3D.5.r02.c1"], "missing", none
    )
    by_id = {t.table_id: t for t in result.tables}
    assert by_id["T3D.1"].rows == () and by_id["T3D.4"].rows == ()
    assert result.refinancing.total_principal == cp3c.Gap(none)  # never a summed 0
    assert result.own_limitations[-3] == (
        "No facility is in the CP-1 debt register; refinancing figures are not calculated."
    )
    assert list(result.gaps_ledger.rows[-3]) == ["Facility schedule", "Gap"]


def test_c6_zero_total_principal_gives_known_zero_totals_and_no_shares() -> None:
    row = _positive_row()
    zero = replace(row, principal=replace(row.principal, amount=Decimal(0)))
    result = cp3c.compute(_positive_with(_positive_terms(), wall=(zero,)))
    assert _own_gaps(result) == {
        "T3D.1.r01.c10": (
            "not_applicable",
            f"Not meaningful: principal payable at maturity is zero {NM}",
        ),
        "T3D.4.r01.c4": (
            "not_applicable",
            f"Not meaningful: total facility principal is zero {NM}",
        ),
    }
    assert result.refinancing.total_principal == 0 and result.refinancing.total_need == 0


def test_c6_an_unknown_ranking_flag_is_an_invariant() -> None:
    flag = replace(_cp1_fact("term-loan.secured_status"), text="PARI_PASSU")
    with pytest.raises(ValueError, match="unknown ranking flag") as raised:
        cp3c.compute(_positive_with(replace(_positive_terms(), secured_status=flag)))
    assert "not pinned" not in str(raised.value)


@pytest.mark.parametrize(("field", "value"), [("months", Decimal(47)), ("inside_horizon", "Yes")])
def test_c6_a_wall_row_off_cp2ds_rule_uses_the_recomputed_position(field: str, value: Any) -> None:
    row = _positive_row()
    fact = getattr(row, field)
    changed = replace(fact, amount=value) if field == "months" else replace(fact, text=value)
    result = cp3c.compute(
        _positive_with(_positive_terms(), wall=(replace(row, **{field: changed}),))
    )
    (m,) = result.refinancing.maturities
    assert (m.facility.months, m.facility.inside_horizon) == (48, False)
    column = 3 if field == "months" else 4
    copy = _cells_of(result)[f"T3D.1.r01.c{column}"]
    assert (copy.amount, copy.text) == (changed.amount, changed.text)  # CP-2D's own value
    assert _own_gaps(result) == {}
    assert result.own_limitations[-3] == (
        "CP-2D's maturity wall for facility term-loan differs from the position recomputed from "
        "its horizon and maturity date; CP-3C uses the recomputed position and shows both."
    )
    assert list(result.gaps_ledger.rows[-3]) == [
        "CP-2D maturity wall cross-check (term-loan)",
        "Limitation",
    ]


def test_c6_a_facility_missing_from_the_wall_leaves_its_cells_and_totals_missing() -> None:
    notes = "Not calculable: facility notes is not in the CP-2D maturity wall"
    other = replace(_positive_terms(), facility_id="notes")
    result = cp3c.compute(_positive_with(_positive_terms(), other))
    own_row = [f"T3D.1.r02.c{n}" for n in range(1, 11)] + [f"T3D.4.r02.c{n}" for n in range(1, 7)]
    totals = ["T3D.2.r01", "T3D.2.r04", "T3D.2.r05", "T3D.2.r06", "T3D.2.r08"]
    resources = [*_ROW_RESOURCES, "T3D.2.r02", "T3D.2.r03", "T3D.2.r09"]
    assert _own_gaps(result) == _all(
        [*own_row, *resources, *totals, *_REPRICED, "T3D.4.r01.c4", *_CLAIMS], "missing", notes
    )
    assert result.own_limitations[-3] == notes
    assert [r.label for r in result.tables[0].rows] == [
        "Northbridge Term Loan (term-loan)",
        "Northbridge Term Loan (notes)",
    ]


def test_c6_a_facility_missing_from_the_register_is_labelled_by_its_id() -> None:
    reason = "Not calculable: facility term-loan is not in the CP-1 debt register"
    result = cp3c.compute(_positive_with())
    assert [r.label for r in result.tables[0].rows] == ["term-loan"]
    assert {c.reason for r in result.tables[0].rows for c in r.cells} == {reason}
    assert result.own_limitations[-3] == reason


# C-8 no de-duplication (confirmed; no code change)


def test_c8_a_repeated_issue_is_reported_each_time() -> None:
    payload = json.loads(json.dumps(SUBMISSIONS["cp3c"]["positive"]))
    path = next(p for p in payload["paths"] if p["basis_refs"])
    path["basis_refs"] = ["not-offered", "also-not-offered"]
    issues = cp3c.submission_issues(submission=_submission(payload), offered=OFFERED)
    at = f"paths[{path['kind']}].basis_refs: names a fact the view does not offer"
    assert list(issues).count(at) == 2


# C-7 Stage 2 bindings


def test_c7_a_gap_copy_keeps_the_upstream_class_period_and_reason() -> None:
    inputs = _inputs("gap_minimum_cash")
    minimum = replace(inputs.cp2d.minimum_cash, period=BALANCE_DATE.isoformat())
    result = cp3c.compute(replace(inputs, cp2d=replace(inputs.cp2d, minimum_cash=minimum)))
    copy = _cells_of(result)["T3D.2.r11"]
    assert (copy.status, copy.value_class, copy.period, copy.reason) == (
        "missing",
        minimum.value_class,
        minimum.period,
        minimum.reason,
    )
    ebitda = _missing_cp1("adjusted_ebitda")
    copy = _cells_of(cp3c.compute(_with_cp1(adjusted_ebitda=ebitda)))["T3D.2.r07"]
    assert (copy.value_class, copy.period, copy.reason) == (
        ebitda.value_class,
        ebitda.period,
        ebitda.reason,
    )


def test_b6_a_negative_total_principal_keeps_totals_and_has_no_shares() -> None:
    """Round 8 B6 (D-4/L2): totals stay known; shares are not meaningful."""
    row = _positive_row()
    negative = replace(row, principal=replace(row.principal, amount=Decimal(-1)))
    result = cp3c.compute(_positive_with(_positive_terms(), wall=(negative,)))
    assert result.refinancing.total_principal == -1
    assert _own_gaps(result)["T3D.4.r01.c4"] == (
        "not_applicable",
        f"Not meaningful: total facility principal is negative {NM}",
    )


# Precedence checks for the round 5 composer (formula order, own facility first, wall order)


def test_without_a_matched_facility_the_resources_operands_still_come_first() -> None:
    inputs = _inputs("gap_minimum_cash")
    result = cp3c.compute(replace(inputs, cp1=replace(inputs.cp1, facilities=())))
    gaps = _own_gaps(result)
    assert gaps["T3D.2.r02"] == gaps["T3D.2.r03"] == ("missing", cp3c.REASON_MINIMUM_CASH)
    assert gaps["T3D.2.r01"] == (
        "missing",
        "Not calculable: facility term-loan is not in the CP-1 debt register",
    )


def test_an_unranked_row_names_its_own_facility_and_the_junior_total_the_first() -> None:
    operands, earlier, later = _two_facilities()
    both = (replace(earlier, seniority=None), replace(later, seniority="NOT_STATED"))
    r = cp3c.compose_refinancing(operands=replace(operands, facilities=both), step_up_bps=0)
    named = {c.facility.facility_id: c.claims_at_or_ahead for c in r.creditors}
    reason = "Not calculable: facility {} seniority is not stated"
    assert named == {f.facility_id: cp3c.Gap(reason.format(f.facility_id)) for f in both}
    assert r.junior_claims == cp3c.Gap(reason.format(earlier.facility_id))


def test_equal_ranks_order_creditors_by_maturity_date() -> None:
    operands, earlier, later = _two_facilities()
    maturity = date(2028, 8, 30)  # 31 whole months, as earlier's 2028-07-31
    peer = replace(
        later,
        facility_id="a-loan",
        maturity_date=maturity,
        months=earlier.months,
        secured_status=earlier.secured_status,
        seniority=earlier.seniority,
    )
    r = cp3c.compose_refinancing(
        operands=replace(operands, facilities=(peer, earlier)), step_up_bps=0
    )
    assert [c.facility.facility_id for c in r.creditors] == [earlier.facility_id, "a-loan"]


def test_amortisation_comes_before_the_principal_in_formula_order() -> None:
    fx = "Not calculable: facility term-loan is in EUR, not USD; no FX conversion is applied"
    row = _positive_row()
    terms = replace(_no_amortisation(), currency="EUR")
    result = cp3c.compute(
        _positive_with(terms, wall=(replace(row, principal=_gone(row.principal, fx)),))
    )
    gaps = _own_gaps(result)
    assert (gaps["T3D.1.r01.c5"], gaps["T3D.1.r01.c6"]) == (("missing", AMORT), ("missing", fx))


# --- LEAD rulings round 6 (docs/rulings/2026-10-28-stage1.md "# Round 6", A1 and A5) ---------


def _plus_months(start: date, n: int) -> date:
    """The test's own calendar month step, the day clamped to the end of the month."""
    years, index = divmod(start.month - 1 + n, 12)
    year, month = start.year + years, index + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def test_a1_months_are_the_largest_n_with_d0_plus_n_on_or_before_the_maturity() -> None:
    """Dec 31 to Jun 30 is 30 months; this supersedes CP-3C lease note :218 (29)."""
    position = cp3c.wall_position(
        balance_date=date(2025, 12, 31), maturity=date(2028, 6, 30), horizon_months=30
    )
    assert position == (30, True)


def test_a1_wall_position_over_every_day_of_four_years() -> None:
    """A1 property scope: D0 + months <= maturity < D0 + months + 1; months < H is inside and
    months > H is outside; inside is maturity <= D0 + H (lease :34)."""
    for d0 in (date(2025, 12, 31), date(2025, 1, 31), date(2024, 2, 29), date(2025, 6, 15)):
        for offset in range(4 * 366):
            maturity = d0 + timedelta(days=offset)
            for horizon in (1, 12, 24, 59):
                months, inside = cp3c.wall_position(
                    balance_date=d0, maturity=maturity, horizon_months=horizon
                )
                assert _plus_months(d0, months) <= maturity < _plus_months(d0, months + 1)
                assert inside == (maturity <= _plus_months(d0, horizon))
                assert not (months < horizon and not inside) and not (months > horizon and inside)


def test_a1_amortisation_runs_for_the_largest_n_months() -> None:
    """A maturity on 2028-06-30 amortises 12 a year for 30 months (not 29), and CP-2D's 30
    months agree with the recomputed position."""
    row = _positive_row()
    wall = replace(
        row,
        maturity_date=replace(row.maturity_date, text="2028-06-30"),
        months=replace(row.months, amount=Decimal(30)),
    )
    terms = replace(
        _positive_terms(), annual_amortisation=_cp1_amount("term-loan.annual_amortisation", "12")
    )
    result = cp3c.compute(_positive_with(terms, wall=(wall,)))
    (m,) = result.refinancing.maturities
    assert m.facility.months == 30
    assert not [line for line in result.own_limitations if "maturity wall for facility" in line]
    assert m.amortisation_before_maturity == 30 and m.principal_payable == 20


# --- LEAD rulings round 8 Part B (docs/rulings/2026-10-28-stage1.md "# Round 8") -------------

_FACILITY_CELLS = [*_PAYABLE, *_RESOURCES, *_REPRICED, "T3D.4.r01.c4", *_CLAIMS]
_UNSTATED_LINE = (
    "Facility term-loan {term} is not stated; maturity-wall figures that need it are not "
    "calculated."
)


def test_b6_a_usd_facility_without_a_wall_principal() -> None:
    reason = "Not calculable: facility term-loan principal is not stated"
    row = _positive_row()
    copied = "Not calculable: facility term-loan principal is not stated (CP-2D)"
    result = cp3c.compute(
        _positive_with(
            _positive_terms(), wall=(replace(row, principal=_gone(row.principal, copied)),)
        )
    )
    assert _own_gaps(result) == _all(_FACILITY_CELLS, "missing", reason)
    assert _cells_of(result)["T3D.1.r01.c1"].reason == copied  # C-7: CP-2D's own limitation
    assert result.own_limitations[-3] == _UNSTATED_LINE.format(term="principal")
    assert list(result.gaps_ledger.rows[-3]) == ["Facility principal (term-loan)", "Gap"]
    cause = "facility term-loan principal is not stated"
    assert _claim(result, "CP-3C-NEED-01") == NEED_GAP.format(r01="[T3D.2.r01]", cause=cause)


def _undated(row: cp3c.WallRow) -> cp3c.WallRow:
    """A wall row as CP-2D gives it (2D-c) when the maturity date is not stated."""
    why = "Not calculable: facility term-loan maturity date is not stated"
    return replace(
        row,
        maturity_date=_gone(row.maturity_date, why),
        months=_gone(row.months, why),
        inside_horizon=_gone(row.inside_horizon, why),
    )


def test_b6_a_facility_without_a_maturity_date() -> None:
    reason = "Not calculable: facility term-loan maturity date is not stated"
    result = cp3c.compute(_positive_with(_positive_terms(), wall=(_undated(_positive_row()),)))
    positions = [*_PAYABLE, *_RESOURCES, *_REPRICED, "T3D.2.r05", "T3D.2.r06"]
    assert _own_gaps(result) == _all(positions, "missing", reason)  # shares and claims known
    assert result.own_limitations[-3] == _UNSTATED_LINE.format(term="maturity date")
    assert list(result.gaps_ledger.rows[-3]) == ["Facility maturity date (term-loan)", "Gap"]


def test_b6_an_undated_facility_sorts_after_every_dated_one() -> None:
    operands, earlier, later = _two_facilities()
    why = cp3c.Gap("Not calculable: facility a-loan maturity date is not stated")
    undated = replace(
        later, facility_id="a-loan", maturity_date=why, months=why, inside_horizon=why
    )
    r = cp3c.compose_refinancing(
        operands=replace(operands, facilities=(undated, earlier)), step_up_bps=0
    )
    assert [m.facility.facility_id for m in r.maturities] == [earlier.facility_id, "a-loan"]
    assert (r.nearest_maturity, r.months_to_nearest) == (why, why)
    assert r.total_principal == 80 and all(
        isinstance(c.claims_at_or_ahead, Decimal) for c in r.creditors
    )


@pytest.mark.parametrize(
    ("field", "what"), [("months", "months to maturity"), ("inside_horizon", "inside-horizon flag")]
)
def test_b6_a_wall_row_without_months_or_flag_uses_the_recomputed_position(
    field: str, what: str
) -> None:
    row = _positive_row()
    stated = "Not calculable: CP-2D states nothing (test)"
    change: dict[str, Any] = {field: _gone(getattr(row, field), stated)}
    changed = replace(row, **change)
    result = cp3c.compute(_positive_with(_positive_terms(), wall=(changed,)))
    assert _own_gaps(result) == {}
    (m,) = result.refinancing.maturities
    assert (m.facility.months, m.facility.inside_horizon) == (48, False)
    copy = _cells_of(result)["T3D.1.r01.c3" if field == "months" else "T3D.1.r01.c4"]
    assert (copy.status, copy.reason) == ("missing", stated)  # CP-2D's cell verbatim
    assert result.own_limitations[-3] == (
        f"CP-2D's maturity wall for facility term-loan states no {what}; CP-3C uses the "
        "position recomputed from its horizon and maturity date."
    )
    assert list(result.gaps_ledger.rows[-3]) == [
        "CP-2D maturity wall cross-check (term-loan)",
        "Limitation",
    ]


def test_b6_a_missing_horizon_leaves_the_position_dependent_cells_missing() -> None:
    inputs = _inputs("positive")
    horizon = _gone(inputs.cp2d.horizon, "Horizon not given (test)")
    result = cp3c.compute(replace(inputs, cp2d=replace(inputs.cp2d, horizon=horizon)))
    reason = "Not calculable: CP-2D horizon is missing"
    assert _own_gaps(result) == {"T3D.2.r04": ("missing", reason)}
    assert result.own_limitations == cp3c.compute(inputs).own_limitations  # no own line


def test_b6_a_missing_name_labels_the_facility_by_its_id() -> None:
    terms = replace(_positive_terms(), facility_name=_missing_cp1("term-loan.facility_name"))
    result = cp3c.compute(_positive_with(terms))
    assert [r.label for t in result.tables if t.table_id in ("T3D.1", "T3D.4") for r in t.rows] == [
        "term-loan",
        "term-loan",
    ]
    assert _own_gaps(result) == {}
    assert result.own_limitations == cp3c.compute(_inputs("positive")).own_limitations
    (name_row,) = (r for r in result.trace.rows if r[0] == "term-loan.facility_name")
    assert name_row[3] == "∅ G#"


def test_b6_a_t418_row_without_a_currency() -> None:
    reason = (
        "Not calculable: facility term-loan currency is not stated; no FX conversion is applied"
    )
    row = _positive_row()
    wall = (replace(row, principal=_gone(row.principal, reason)),)
    result = cp3c.compute(_positive_with(replace(_positive_terms(), currency=None), wall=wall))
    assert _own_gaps(result) == _all(_FACILITY_CELLS, "missing", reason)
    assert result.own_limitations[-3] == _UNSTATED_LINE.format(term="currency")
    assert list(result.gaps_ledger.rows[-3]) == ["Facility currency (term-loan)", "Gap"]
    cause = "the total needs every facility with its currency stated, and one is not"
    assert _claim(result, "CP-3C-NEED-01") == NEED_GAP.format(r01="[T3D.2.r01]", cause=cause)
    assert _claim(result, "CP-3C-LME-01") == LME_GAP.format(cause=cause)


def test_b6_an_undated_row_names_its_own_date_before_any_amortisation() -> None:
    """Formula order: the row's months (flow x months / 12) come before amortisation to date."""
    operands, earlier, later = _two_facilities()
    why = cp3c.Gap("Not calculable: facility term-loan maturity date is not stated")
    undated = replace(later, maturity_date=why, months=why, inside_horizon=why)
    unstated = replace(earlier, annual_amortisation=None)
    r = cp3c.compose_refinancing(
        operands=replace(operands, facilities=(unstated, undated)), step_up_bps=0
    )
    assert [m.resources for m in r.maturities] == [
        cp3c.Gap("Not calculable: facility notes annual amortisation is not stated"),
        why,
    ]


# --- Fix round 1 (work/build/stage1/cp3c/review-adversary.md) ----------------------------------


def _dated(row: cp3c.WallRow, maturity: str, months: int, inside: str) -> cp3c.WallRow:
    return replace(
        row,
        maturity_date=replace(row.maturity_date, text=maturity),
        months=replace(row.months, amount=Decimal(months)),
        inside_horizon=replace(row.inside_horizon, text=inside),
    )


def test_m1_a_maturity_before_the_balance_date_is_an_invariant() -> None:
    """Not ruled (listed for LEAD): negative months would sign-flip amortisation, flow and
    balloon, so the Method fails closed; a maturity on D0 itself is 0 months and computes."""
    past = _dated(_positive_row(), "2025-06-30", -6, "Yes")
    with pytest.raises(ValueError, match=r"term-loan.*2025-06-30.*2025-12-31"):
        cp3c.compute(_positive_with(_positive_terms(), wall=(past,)))
    on_d0 = _dated(_positive_row(), "2025-12-31", 0, "Yes")
    (m,) = cp3c.compute(_positive_with(_positive_terms(), wall=(on_d0,))).refinancing.maturities
    assert m.facility.months == 0


def test_m2_facility_ids_with_digits_are_names_not_figures() -> None:
    row = _positive_row()
    copied = "Not calculable: facility tl2 principal is not stated (CP-2D)"
    tl2 = replace(row, facility_id="tl2", principal=_gone(row.principal, copied))
    unranked = replace(_cp1_fact("term-loan.seniority"), text="NOT_STATED")
    result = cp3c.compute(
        _positive_with(
            replace(_positive_terms(), facility_id="tl2"),
            replace(_positive_terms(), facility_id="tla1", seniority=unranked),
            wall=(tl2, replace(row, facility_id="tla1")),
        )
    )
    cause = "facility tl2 principal is not stated"
    assert _claim(result, "CP-3C-NEED-01") == NEED_GAP.format(r01="[T3D.2.r01]", cause=cause)


def test_a13_a_positive_cp1_cash_interest_is_a_negative_interest_paid() -> None:
    """CP-1 states cash interest as a signed flow; paid is its exact negation, not abs()."""
    inputs = _with_cp1(cash_interest=_cp1_amount("cash_interest", "5"))
    operands = cp3c.compose_operands(
        cp1=inputs.cp1, cp2d=inputs.cp2d, balance_date=BALANCE_DATE, currency=CURRENCY
    )
    assert operands.cash_interest_paid == Decimal(-5)


def test_a18_a_maturity_exactly_on_the_horizon_end_is_inside() -> None:
    """2027-12-31 is D0 + 24 months (H = 24): inside, as CP-2D's wall states it."""
    on_end = _dated(_positive_row(), "2027-12-31", 24, "Yes")
    result = cp3c.compute(_positive_with(_positive_terms(), wall=(on_end,)))
    (m,) = result.refinancing.maturities
    assert m.facility.inside_horizon is True
    assert not [line for line in result.own_limitations if "maturity wall for facility" in line]


def test_a25_own_lines_name_currency_then_maturity_date_then_principal() -> None:
    def own(result: cp3c.Cp3cResult) -> list[str]:
        return [x for x in result.own_limitations if x.startswith("Facility term-loan ")]

    row = _undated(_positive_row())
    no_ccy = cp3c.compute(_positive_with(replace(_positive_terms(), currency=None), wall=(row,)))
    assert own(no_ccy) == [
        _UNSTATED_LINE.format(term="currency"),
        _UNSTATED_LINE.format(term="maturity date"),
    ]
    gone = replace(row, principal=_gone(row.principal, "Not stated (test)"))
    usd = cp3c.compute(_positive_with(_positive_terms(), wall=(gone,)))
    assert own(usd) == [
        _UNSTATED_LINE.format(term="maturity date"),
        _UNSTATED_LINE.format(term="principal"),
    ]


def test_a39_a_usd_principal_gap_keeps_its_own_cause_beside_a_eur_facility() -> None:
    """Round 8 B2: only the currency gap takes the FX frame; a-usd is first in wall order."""
    row = _positive_row()
    usd = replace(row, facility_id="a-usd", principal=_gone(row.principal, "Not stated (test)"))
    result = cp3c.compute(
        _positive_with(
            replace(_positive_terms(), facility_id="a-usd"),
            replace(_positive_terms(), facility_id="b-eur", currency="EUR"),
            wall=(usd, replace(row, facility_id="b-eur")),
        )
    )
    cause = "facility a-usd principal is not stated"
    assert _claim(result, "CP-3C-NEED-01") == NEED_GAP.format(r01="[T3D.2.r01]", cause=cause)


def test_l1_junior_claims_are_the_largest_claims_at_or_ahead() -> None:
    """Lease Method 7 and method_rules.lme_capacity: the largest claims at or ahead, so a
    negative junior principal does not lower the base below the senior claims."""
    operands, earlier, later = _two_facilities()
    senior = replace(earlier, secured_status="SECURED", seniority="SENIOR")
    junior = replace(later, secured_status="UNSECURED", seniority="SENIOR", principal=Decimal(-10))
    r = cp3c.compose_refinancing(
        operands=replace(operands, facilities=(senior, junior)), step_up_bps=0
    )
    assert isinstance(senior.principal, Decimal)
    claims = [c.claims_at_or_ahead for c in r.creditors]
    assert claims == [senior.principal, senior.principal - 10]
    assert r.junior_claims == senior.principal


def test_l2_amounts_are_computed_at_the_builders_precision() -> None:
    """cases/cp3c-owner/builder/build.py sets prec 60; 5 x 7 / 12 does not terminate."""
    terms = replace(
        _positive_terms(), annual_amortisation=_cp1_amount("term-loan.annual_amortisation", "5")
    )
    wall = (_dated(_positive_row(), "2026-07-31", 7, "Yes"),)
    (m,) = cp3c.compute(_positive_with(terms, wall=wall)).refinancing.maturities
    with localcontext(Context(prec=60)):
        assert m.amortisation_before_maturity == Decimal(5) * 7 / 12


# Fix round 1, Low survivors (review-adversary.md mutants A33-A45)


@pytest.mark.parametrize(
    ("at", "where"),
    [
        ("repricing_absence.reason", ("repricing_absence", "reason")),
        ("paths[repay_from_resources].limitation", ("paths", 0, "limitation")),
    ],
)
def test_absence_reason_and_path_limitation_are_guarded(at: str, where: tuple[Any, ...]) -> None:
    payload = json.loads(json.dumps(SUBMISSIONS["cp3c"]["gap_no_repricing"]))
    holder = payload
    for key in where[:-1]:
        holder = holder[key]
    holder[where[-1]] = "The company will default."
    issues = cp3c.submission_issues(submission=_submission(payload), offered=OFFERED)
    assert f'{at}: prohibited conclusion (refinancing outcome): "will default"' in issues


def test_the_covenant_guard_window_is_four_words() -> None:
    near = "the covenants were in all respects met"
    far = "the covenants were in all relevant respects met"
    assert cp3c.prohibited_conclusions("x", near) and not cp3c.prohibited_conclusions("x", far)


@pytest.mark.parametrize(
    ("field", "change", "match"),
    [
        ("principal", {"unit": "THOUSANDS"}, "expected a MILLIONS amount"),
        ("months", {"amount": Decimal("47.5")}, "whole number of months"),
        ("inside_horizon", {"text": "Maybe"}, "inside-horizon flag"),
    ],
)
def test_a_malformed_wall_fact_is_an_invariant(field: str, change: Any, match: str) -> None:
    row = _positive_row()
    bad: dict[str, Any] = {field: replace(getattr(row, field), **change)}
    with pytest.raises(ValueError, match=match):
        cp3c.compute(_positive_with(_positive_terms(), wall=(replace(row, **bad),)))


def test_interest_and_ebitda_over_different_periods_is_an_invariant() -> None:
    other = replace(_cp1_fact("cash_interest"), period="FY 2025: 2025-01-01 to 2025-12-31")
    with pytest.raises(ValueError, match="different periods"):
        cp3c.compute(_with_cp1(cash_interest=other))


def test_a_repeated_operand_facility_is_an_invariant() -> None:
    operands, earlier, _ = _two_facilities()
    with pytest.raises(ValueError, match="facility_id repeats"):
        cp3c.compose_refinancing(
            operands=replace(operands, facilities=(earlier, earlier)), step_up_bps=0
        )


def test_a_claim_template_with_a_bare_figure_is_refused() -> None:
    with pytest.raises(ValueError, match="Bare figure"):
        cp3c._Claims({}, ()).claim("CP-3C-TEST", "The need is 40 million.", ())
