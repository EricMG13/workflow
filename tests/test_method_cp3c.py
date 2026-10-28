"""CP-3C Stage 1: the pure calculation equals the frozen oracle (cases/cp3c-owner).

Inputs come from the oracle's own records only: the CP-1 head values observed for the bindings
(manifest.json#fact_bindings), the frozen CP-2D oracle cells this oracle pins as its upstream
(cases/cp2d-owner/expected.json, sha256 in manifest.json#frozen_inputs), the literal analyst
submissions (submissions.json) and the composer fixtures' own input vectors. Every expected
value is read from expected.json. The run-time binding of ``{{FACT:name}}`` to an offered ref is
stood in for by the CP-2D stable id (the manifest's ref) or ``cp1:<name>`` (CP-1 fact ids are
bound in Stage 2); an unknown name binds to a ref the view never offers.
"""

import hashlib
import json
import re
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

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

# docs/CP3C-OWNER-LEASE.md header (rev 3) and manifest.json#frozen_inputs.
PINS = {
    "cases/cp3c-owner/manifest.json": "aa2c8f57cc6077109db684c0b5aa1c620d1e19453f8640089db7176a82e67d0e",
    "cases/cp3c-owner/submissions.json": "8c2b08fa3a7022097aca03798b81a23fd678ba2654ff9ef970a4c02166c34e3c",
    "cases/cp3c-owner/expected.json": "50ef4a7f9199e1da4a73fc75eaaf6bc8215bef12cec26067d2d44aead0952e5f",
    "cases/cp3c-owner/builder/build.py": "66a3ba8696a81d58d527c1fbf0f0841738537b666225c8479988bd619e16412d",
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
        "nearest_maturity": r.nearest_maturity.isoformat(),
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


def _same(expected: Any, actual: Any, at: str = "") -> None:
    """Oracle equality: numeric Decimal equality, ``nm`` is not applicable, None is missing."""
    if expected is None:
        assert actual is None, f"{at}: expected missing, got {actual!r}"
    elif expected == "nm":
        assert actual == cp3c.NOT_APPLICABLE, f"{at}: expected n.m., got {actual!r}"
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
        assert derived[key] is None, (case, key)


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
        assert derived[key] is None, (name, key)


def test_unassessed_step_up_is_missing_and_zero_step_up_is_known_zero() -> None:
    operands, _ = _fixture_operands("fixture_zero_step_up")
    zero = cp3c.compose_refinancing(operands=operands, step_up_bps=0)
    unassessed = cp3c.compose_refinancing(operands=operands, step_up_bps=None)
    assert zero.added_interest == 0 and zero.added_interest is not None
    assert unassessed.added_interest is None and unassessed.pro_forma_interest_cover is None


# --- lease boundaries the oracle states as rules (not oracle cases) ----------------------------


def _single(**changes: Any) -> cp3c.Operands:
    operands, _ = _fixture_operands("fixture_zero_step_up")
    return replace(operands, **changes)


def test_a_covered_maturity_is_a_known_zero_need_not_missing() -> None:
    """method_rules.refinancing_need: a computed 0 is 'no need', distinct from missing."""
    r = cp3c.compose_refinancing(operands=_single(cash=Decimal(1000)), step_up_bps=0)
    assert r.total_need == 0 and r.total_need is not None
    assert r.maturities[0].cover == 1


def test_zero_interest_gives_not_applicable_cover() -> None:
    """method_rules.interest_cover: a zero interest is not_applicable."""
    r = cp3c.compose_refinancing(operands=_single(cash_interest_paid=Decimal(0)), step_up_bps=None)
    assert r.interest_cover == cp3c.NOT_APPLICABLE


def test_fully_amortised_principal_gives_not_applicable_cover() -> None:
    """method_rules.cover: not_applicable when the principal payable at maturity is 0."""
    operands = _single()
    (f,) = operands.facilities
    r = cp3c.compose_refinancing(
        operands=replace(operands, facilities=(replace(f, annual_amortisation=Decimal(50)),)),
        step_up_bps=0,
    )
    assert r.maturities[0].principal_payable == 0 and r.maturities[0].cover == cp3c.NOT_APPLICABLE


def _two_facilities() -> tuple[cp3c.Operands, cp3c.FacilityOperand, cp3c.FacilityOperand]:
    operands, _ = _fixture_operands("fixture_two_facilities")
    later, earlier = sorted(operands.facilities, key=lambda f: -f.months)
    return operands, earlier, later


def test_equal_months_order_by_facility_id() -> None:
    """method_rules.facility_order: ties by facility_id, whatever order the facilities arrive in."""
    operands, earlier, later = _two_facilities()
    tied = replace(later, facility_id="a-loan", months=earlier.months)
    r = cp3c.compose_refinancing(
        operands=replace(operands, facilities=(earlier, tied)), step_up_bps=0
    )
    assert [m.facility.facility_id for m in r.maturities] == ["a-loan", earlier.facility_id]


def test_amortisation_of_a_matured_facility_stops_at_its_maturity() -> None:
    """method_rules.resources_at_maturity: each facility amortises to min(date, own maturity),
    so moving a later, non-amortising maturity leaves its resources unchanged at a zero flow."""
    operands, earlier, later = _two_facilities()
    amortising = replace(earlier, annual_amortisation=Decimal(6))
    flat = replace(later, annual_amortisation=Decimal(0))
    resources = []
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


# --- fail closed where the lease and oracle pin no wording -------------------------------------


def _positive_with(terms: cp3c.FacilityTerms) -> cp3c.Cp3cInputs:
    inputs = _inputs("positive")
    return replace(inputs, cp1=replace(inputs.cp1, facilities=(terms,)))


def _positive_terms() -> cp3c.FacilityTerms:
    (terms,) = _inputs("positive").cp1.facilities
    return terms


def test_missing_amortisation_fails_closed_in_the_tables() -> None:
    missing = cp3c.Cp1Fact(
        table_id="T4.18",
        period="q4-2025",
        status="missing",
        reason="Not stated",
        value_class="source",
    )
    inputs = _positive_with(replace(_positive_terms(), annual_amortisation=missing))
    with pytest.raises(ValueError, match="not pinned"):
        cp3c.compute(inputs)


def test_unstated_ranking_fails_closed_in_the_tables() -> None:
    unstated = cp3c.Cp1Fact(
        table_id="T4.18", period="q4-2025", status="known", text="NOT_STATED", value_class="source"
    )
    inputs = _positive_with(replace(_positive_terms(), secured_status=unstated))
    with pytest.raises(ValueError, match="not pinned"):
        cp3c.compute(inputs)


def test_a_facility_in_another_currency_fails_closed() -> None:
    inputs = _positive_with(replace(_positive_terms(), currency="EUR"))
    with pytest.raises(ValueError, match="currency"):
        cp3c.compute(inputs)


def test_a_zero_step_up_claim_fails_closed() -> None:
    """The pinned COST-01 template says the step-up lowers interest cover; at 0 bp it does not."""
    payload = json.loads(json.dumps(SUBMISSIONS["cp3c"]["positive"]))
    payload["repricing"]["bps"] = 0
    inputs = replace(_inputs("positive"), submission=_submission(payload))
    with pytest.raises(ValueError, match="CP-3C-COST-01"):
        cp3c.compute(inputs)
