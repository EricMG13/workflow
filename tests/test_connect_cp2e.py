"""CP-2E Stage 2: the backlog rows, then the connection (G1-X protocol parts) over the oracle.

Oracle: cases/cp2e-owner. Every expected value is read from its files; the Stage 1 helpers of
`test_method_cp2e` supply the frozen literals and pages.
"""

import copy
import hashlib
import json
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

import pytest
from cp2e_runs import drive_cp0, make_pack, start
from test_method_cp2e import (
    CASES,
    EXPECTED,
    SUBMISSIONS,
    _cited,
    _inputs,
    _issues_with,
    _mutated,
    _names,
    _pages,
    _reference_rate_adapter,
)

from deploy_vii import prose
from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.cp2e import CP2E
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Claim, Fact, Module, ModuleView, View
from deploy_vii.execution import Execution, StepValidation, head_of
from deploy_vii.live.tools import Seen
from deploy_vii.preparation import PreparedPack
from deploy_vii.readiness import citation_issues
from deploy_workflow import owner_workflow as owner
from deploy_workflow.owners import cp2e

# U+2800 and Cc/default-ignorable blanks wait on LEAD's `is_blank` batch (backlog "All" row).
BLANKS = ["", "   ", "\u200b", " \n "]


def _positive() -> dict[str, Any]:
    return copy.deepcopy(SUBMISSIONS["positive"])


def _set(raw: dict[str, Any], path: tuple[str | int, ...], value: Any) -> dict[str, Any]:
    node: Any = raw
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return raw


# --- backlog: a blank support or citation quote is refused as empty text, before the page check ---
_QUOTE_PATHS = [
    (("reporting_currency", "quote"), "reporting_currency.quote"),
    (("rate_exposure", "facility_balance", "quote"), "rate_exposure.facility_balance.quote"),
    (("rate_exposure", "rate_basis", "quote"), "rate_exposure.rate_basis.quote"),
    (("rate_exposure", "spread", "quote"), "rate_exposure.spread.quote"),
    (("rate_exposure", "floor", "quote"), "rate_exposure.floor.quote"),
    (("earnings", "ebitda", "quote"), "earnings.ebitda.quote"),
    (("earnings", "total_debt", "quote"), "earnings.total_debt.quote"),
    (("fx", "fx_cash_effect", "quote"), "fx.fx_cash_effect.quote"),
    (("fx", "debt_currency", "quote"), "fx.debt_currency.quote"),
    (("assessments", 0, "basis", 0, "quote"), "assessments[0].basis[0].quote"),
    (("assessments", 1, "basis", 2, "quote"), "assessments[1].basis[2].quote"),
]


@pytest.mark.parametrize("blank", BLANKS, ids=["empty", "spaces", "zwsp", "newline"])
@pytest.mark.parametrize(("path", "named"), _QUOTE_PATHS, ids=[n for _, n in _QUOTE_PATHS])
def test_a_blank_quote_is_refused_as_empty_text(
    path: tuple[str | int, ...], named: str, blank: str
) -> None:
    raw = _set(_positive(), path, blank)
    assert _issues_with(raw) == (f"{named}: empty text",)


def test_a_blank_share_quote_is_refused_as_empty_text() -> None:
    raw = _positive()
    raw["fx"]["operating_fx_absence"] = None
    raw["fx"]["foreign_ebitda_share"] = {**_cited("  "), "percent_text": "25"}
    assert _issues_with(raw) == ("fx.foreign_ebitda_share.quote: empty text",)


def test_a_blank_quote_outside_the_scope_keeps_the_scope_issue() -> None:
    raw = _set(_positive(), ("reporting_currency", "source_id"), "identity")
    raw["reporting_currency"]["quote"] = " "
    assert _issues_with(raw) == (
        "reporting_currency: source identity is outside the CP-2E scope (financial)",
    )


# --- backlog (r13 Info 1): the occurrence check compares the normalised value with the quote ---
def test_a_minus_sign_reference_rate_occurs_in_a_hyphen_quote() -> None:
    """`rb["reference_rate"] not in quote` compared the raw value with the normalised quote, so a
    U+2212 name never occurred; both sides are now normalised."""
    page = "The loan pays Term-SOFR plus the spread."
    assert _reference_rate_adapter(page, "Term-SOFR", "Term−SOFR") == ()


def test_a_reference_rate_not_in_the_quote_is_still_refused() -> None:
    page = "The loan pays Term-SOFR plus the spread."
    assert _reference_rate_adapter(page, "Term-SOFR", "Term−EURIBOR") == (
        "rate_exposure.rate_basis: reference_rate does not occur in the quote",
    )


def test_the_positive_literal_is_still_valid() -> None:
    assert (
        cp2e.validate_macro_fx(submission=SUBMISSIONS["positive"], pages=_pages("positive")) == ()
    )


# =================================================================================================
# The connection (G1-X protocol section 2) over the oracle
# =================================================================================================
def _pack(case: str) -> PreparedPack:
    return make_pack(case)


def _store(case: str) -> Any:
    """The duck-typed store the validator reads: the retained step payload by its hash."""
    payload = json.dumps(SUBMISSIONS[case])
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return SimpleNamespace(payload=lambda sha: payload if sha == digest else "", digest=digest)


def _attempt(store: Any) -> Any:
    return SimpleNamespace(steps=(SimpleNamespace(payload_sha256=store.digest),), number=0)


def test_the_registered_step_and_schema() -> None:
    assert cp2e.STEP_ID == "macro_fx"
    assert cp2e.STEP_IDS == ("macro_fx",)
    assert type(cp2e.STEP_IDS) is tuple
    assert cp2e.SCHEMAS == {"macro_fx": cp2e.MacroFxSubmission}
    assert cp2e.QUALIFICATION.implementation == "implemented"


@pytest.mark.parametrize("case", CASES)
def test_schema_round_trips_the_oracle_literal(case: str) -> None:
    schema = cp2e.SCHEMAS[cp2e.STEP_ID]
    parsed = schema.model_validate_json(json.dumps(SUBMISSIONS[case]))
    assert parsed.model_dump(mode="json") == SUBMISSIONS[case]
    assert parsed.content_hash() == hashlib.sha256(parsed.model_dump_json().encode()).hexdigest()


@pytest.mark.parametrize("case", CASES)
def test_the_tail_digest_is_the_schema_hash_of_the_payload(case: str) -> None:
    store = _store(case)
    outcome = cp2e.ENTRY_VALIDATOR(cast(Execution, store), _pack(case), _attempt(store))
    assert outcome.output is not None
    report = cp2e.MacroFxReport.model_validate_json(outcome.output)
    expected = cp2e.SCHEMAS[cp2e.STEP_ID].model_validate_json(json.dumps(SUBMISSIONS[case]))
    assert report.submission_sha256 == expected.content_hash()
    module = cp2e.cp2e_module(report=report, inputs=(), attempt=0)
    assert [i.input_id for i in module.inputs] == ["macro-fx-submission"]
    assert module.inputs[0].sha256 == expected.content_hash()


# --- RULES: the tool-use rules over the session's Seen -------------------------------------------
def _seen(reads: list[list[str]], searches: int) -> Seen:
    return Seen(
        read=frozenset((r[0], r[1]) for r in reads), searched=tuple(None for _ in range(searches))
    )


@pytest.mark.parametrize("row", SUBMISSIONS["tool_use_refusals"], ids=lambda r: r["id"])
def test_rules_reproduce_the_tool_use_refusals(row: dict[str, Any]) -> None:
    text = json.dumps(SUBMISSIONS["positive"])
    expected = {r["id"]: r["issue"] for r in EXPECTED["tool_use_refusals"]}
    assert cp2e.RULES(text, _seen(row["reads"], row["searches"])) == (expected[row["id"]],)


@pytest.mark.parametrize("case", CASES)
def test_rules_pass_when_every_cited_page_is_read_and_a_search_ran(case: str) -> None:
    required = EXPECTED["cases"][case]["tool_use_required"]
    seen = _seen(required["read_pages_cover"], required["search_pack_min"])
    assert cp2e.RULES(json.dumps(SUBMISSIONS[case]), seen) == ()


def test_rules_ask_a_search_only_for_an_absence() -> None:
    raw = _positive()
    for path in (("fx", "operating_fx_absence"), ("hedge_absence",)):
        _set(raw, path, None)
    raw["fx"]["foreign_ebitda_share"] = {**_cited("x"), "locator": "page:1", "percent_text": "25"}
    raw["hedge_ratio"] = {"percent_text": "40", "rationale": "assumed"}
    seen = _seen(EXPECTED["cases"]["positive"]["tool_use_required"]["read_pages_cover"], 0)
    assert cp2e.RULES(json.dumps(raw), seen) == ()


def _no_absence() -> dict[str, Any]:
    """The positive literal with every alternative set to its sourced side, no absence object."""
    raw = _positive()
    raw["fx"]["operating_fx_absence"] = None
    raw["fx"]["foreign_ebitda_share"] = {**_cited("x"), "locator": "page:1", "percent_text": "25"}
    raw["hedge_absence"] = None
    raw["hedge_ratio"] = {"percent_text": "40", "rationale": "assumed"}
    return raw


@pytest.mark.parametrize(
    "path",
    [("rate_absence",), ("fx", "debt_currency_absence"), ("fx", "operating_fx_absence")]
    + [("hedge_absence",)],
    ids=["rate", "debt-currency", "operating-fx", "hedge"],
)
def test_each_absence_object_needs_a_search_alone(path: tuple[str, ...]) -> None:
    raw = _no_absence()
    seen = _seen(EXPECTED["cases"]["positive"]["tool_use_required"]["read_pages_cover"], 0)
    assert cp2e.RULES(json.dumps(raw), seen) == ()
    if path == ("rate_absence",):
        raw["rate_exposure"] = None
    node: Any = raw
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = {"reason": "none", "follow_up": "ask"}
    assert cp2e.RULES(json.dumps(raw), seen) == ("Absence claim without a recorded search",)


def test_the_absence_issue_comes_before_the_unread_pages() -> None:
    out = cp2e.RULES(json.dumps(_positive()), _seen([], 0))
    assert out[0] == "Absence claim without a recorded search"
    assert out[1].startswith("Cited page not read through read_pages: ")


def test_rules_read_text_that_is_not_an_object_as_no_claim() -> None:
    assert cp2e.RULES("[1]", Seen()) == ()
    assert cp2e.RULES("not json", Seen()) == ()


def test_rules_bound_a_payload_that_cites_many_pages() -> None:
    raw = _positive()
    raw["assessments"][0]["basis"] = [
        {"source_id": "financial", "locator": f"page:{n}", "quote": "q"} for n in range(50)
    ]
    out = cp2e.RULES(json.dumps(raw), _seen([], 1))
    assert len(out) <= 20
    assert all(len(line) <= 600 for line in out)


def test_the_core_has_no_precheck_and_no_view() -> None:
    assert not hasattr(cp2e, "precheck")
    assert not hasattr(cp2e, "view")
    assert "CP-2E" not in owner._PRECHECKS
    assert "macro_fx" not in owner._VIEWS


# --- the adapter: the retained payload and the pack -> the Stage 1 input object -------------------
@pytest.mark.parametrize("case", CASES)
def test_the_adapter_returns_the_stage1_input_object(case: str) -> None:
    store = _store(case)
    submission = cp2e.MacroFxSubmission.model_validate_json(store.payload(store.digest))
    assert cp2e._inputs(_pack(case), submission) == _inputs(case)
    assert dict(_inputs(case).source_names) == _names(case)


@pytest.mark.parametrize("case", CASES)
def test_the_pack_names_the_sources_the_oracle_lists(case: str) -> None:
    assert {s.source_id: s.name for s in _pack(case).sources} == _names(case)


# --- the validator and the report -----------------------------------------------------------------
@pytest.mark.parametrize("case", CASES)
def test_the_step_validator_composes_the_oracle_report(case: str) -> None:
    store, pack = _store(case), _pack(case)
    outcome = cp2e.ENTRY_VALIDATOR(cast(Execution, store), pack, _attempt(store))
    assert outcome.issues == ()
    assert outcome.output is not None
    report = cp2e.MacroFxReport.model_validate_json(outcome.output)
    expected = EXPECTED["cases"][case]
    assert report.run == pack.run
    assert report.pack_sha256 == pack.content_hash()
    assert [
        t.model_dump(mode="json", exclude={"rows": {"__all__": {"row_kind"}}}, exclude_none=True)
        for t in report.tables
    ] == expected["module_tables"]
    assert [c.claim_id for c in report.claims] == [c["claim_id"] for c in expected["claims"]]
    assert [c.text for c in report.claims] == [c["text"] for c in expected["claims"]]
    assert list(report.limitations) == expected["own_limitations"]
    cells = [f for t in expected["tables"] for r in t["rows"] for f in r["facts"]]
    assert [f.fact_id for f in report.facts] == [c["fact_id"] for c in cells]
    for fact, cell in zip(report.facts, cells, strict=True):
        assert [(c.source_id, c.locator) for c in fact.citations] == [
            tuple(x) for x in cell["cites"]
        ]
        assert citation_issues(fact.citations, pack.sources) == ()
    for claim, row in zip(report.claims, expected["claims"], strict=True):
        assert [(c.source_id, c.locator) for c in claim.citations] == [
            tuple(x) for x in row["cites"]
        ]
        assert citation_issues(claim.citations, pack.sources) == ()


@pytest.mark.parametrize("case", CASES)
def test_the_report_module_holds_no_prose_issue(case: str) -> None:
    store, pack = _store(case), _pack(case)
    outcome = cp2e.ENTRY_VALIDATOR(cast(Execution, store), pack, _attempt(store))
    assert outcome.output is not None
    report = cp2e.MacroFxReport.model_validate_json(outcome.output)
    module = cp2e.cp2e_module(report=report, inputs=(), attempt=0)
    assert prose.prose_issues(module, names=(pack.run.issuer_name,)) == ()
    assert [i.input_id for i in module.inputs] == ["macro-fx-submission"]
    assert module.module_id == "CP-2E"


def _validate(raw: dict[str, Any] | str) -> StepValidation:
    text = raw if isinstance(raw, str) else json.dumps(raw)
    digest = hashlib.sha256(text.encode()).hexdigest()
    store = SimpleNamespace(payload=lambda sha: text, digest=digest)
    return cp2e.ENTRY_VALIDATOR(cast(Execution, store), _pack("positive"), _attempt(store))


def test_the_step_validator_returns_a_journaled_validator_issue() -> None:
    raw = _set(_positive(), ("rate_exposure", "floor", "bps_text"), "25")
    out = _validate(raw)
    assert out.output is None
    assert out.issues == ("rate_exposure.floor: bps_text 25 does not occur in the quote",)


def test_the_step_validator_returns_shape_issues_for_a_wrong_shape() -> None:
    raw = _positive()
    del raw["summary"]
    out = _validate(raw)
    assert out.output is None
    assert out.issues
    assert any("summary" in line for line in out.issues)


@pytest.mark.parametrize("text", ["[1]", "not json", "null", '{"a": NaN}'])
def test_the_step_validator_refuses_text_that_is_not_a_json_object(text: str) -> None:
    out = _validate(text)
    assert out.output is None
    assert out.issues == ("payload: not a JSON object",)


def test_a_numeric_field_is_a_shape_issue_not_a_crash() -> None:
    raw = _set(_positive(), ("rate_shocks_bp",), [100.5])
    out = _validate(raw)
    assert out.output is None
    assert out.issues


# --- the registrations equal the lease ------------------------------------------------------------
def test_the_owner_spec_is_the_lease_line() -> None:
    expected = owner.OwnerSpec(
        module_id="CP-2E",
        steps=(
            owner.StepSpec(
                "macro_fx",
                cp2e.MacroFxSubmission,
                sources=True,
                extract=False,
                upstream_grant=None,
                inputs="none",
                rules="journaled",
            ),
        ),
        entry="owner_core",
        kind="analytical",
        publish=None,
    )
    assert owner.OWNER_SPECS["CP-2E"] == expected
    owner._check_steps("CP-2E", owner.OWNER_SPECS["CP-2E"])


def test_the_module_is_registered_in_every_table_the_lease_names() -> None:
    assert "CP-2E" in owner.SUPPORTED_ANALYTICAL
    assert owner._CORES["CP-2E"] is cp2e
    assert owner._QUALIFICATION["CP-2E"] == cp2e.QUALIFICATION
    assert owner._PROBES["CP-2E"] is cp2e.probe
    assert owner._ENTRY_VALIDATORS["CP-2E"] is cp2e.ENTRY_VALIDATOR


def test_earlier_registrations_keep_their_rows_and_order() -> None:
    assert list(owner._PROBES)[:4] == ["CP-0", "CP-1", "CP-1A", "CP-2"]
    assert list(owner._ENTRY_VALIDATORS)[:2] == ["CP-1A", "CP-2"]
    assert list(owner._QUALIFICATION)[:4] == ["CP-1", "CP-1A", "CP-2", "CP-MODEL"]


def test_the_host_scope_is_the_financial_source_only() -> None:
    from deploy_workflow import host

    assert host._SOURCE_STEPS["CP-2E"] == ("macro_fx",)
    for case in CASES:
        pack = _pack(case)
        assert host._OWNER_SCOPES[("CP-2E", "macro_fx")](pack) == ("financial",)


# --- bindings (D12) -------------------------------------------------------------------------------
def _view(case: str) -> View:
    store, pack = _store(case), _pack(case)
    outcome = cp2e.ENTRY_VALIDATOR(cast(Execution, store), pack, _attempt(store))
    assert outcome.output is not None
    report = cp2e.MacroFxReport.model_validate_json(outcome.output)
    module = cp2e.cp2e_module(report=report, inputs=(), attempt=0).model_copy(
        update={"status": "restricted", "limitations": report.limitations}
    )
    return View(
        run=pack.run,
        mode="candidate",
        modules=(
            ModuleView(
                module_id="CP-2E",
                title="Macro, FX and hedging sensitivity",
                aliases=("CP-2F",),
                status="restricted",
                artifact_sha256=module.content_hash(),
                facts=module.facts,
                tables=module.tables,
                claims=module.claims,
                limitations=module.limitations,
            ),
        ),
    )


@pytest.mark.parametrize("case", CASES)
def test_the_shipped_maps_bind_every_cp2e_fact_exactly_once(case: str) -> None:
    assert validate_bindings(_view(case), SHIPPED_MAPS) == ()
    ids = [m.module_id for m in SHIPPED_MAPS]
    assert CP2E in SHIPPED_MAPS
    assert ids.index("CP-2E") > ids.index("CP-6")


def test_the_binding_rows_equal_the_oracle() -> None:
    rows = EXPECTED["render"]["bindings"]
    assert [
        {
            "table_id": b.fact_coord.table_id,
            "block_id": b.block_id,
            "cell_slot": b.cell_slot,
            "unit_class": b.unit_class,
            "label": b.label,
        }
        for b in CP2E.entries
    ] == rows
    assert CP2E.module_id == "CP-2E"


def test_the_bound_blocks_are_the_two_rails_so_no_spec_row_is_needed() -> None:
    from deploy_vii.bindings import RAIL_DESTINATIONS

    assert {b.block_id for b in CP2E.entries} == {"evidence", "limitations"} <= RAIL_DESTINATIONS


# --- the reader (D3 is OPEN: the test pins what is exposed, it claims no completion) ---------------
def _head_and_store(case: str) -> tuple[Any, Any]:
    view = _view(case)
    (mv,) = view.modules
    module = Module(
        run_id=view.run.run_id,
        issuer_id=view.run.issuer_id,
        as_of=view.run.as_of,
        module_id="CP-2E",
        status="restricted",
        facts=mv.facts,
        tables=mv.tables,
        claims=mv.claims,
        limitations=mv.limitations,
    )
    head = head_of(module)
    store = SimpleNamespace(head_module=lambda h: module if h == head else None)
    return head, store


def test_the_reader_exposes_what_the_lease_pins() -> None:
    head, store = _head_and_store("positive")
    read = cp2e.cp2e_reader(cast(Execution, store), head)
    pinned = EXPECTED["consumption"]["reader_pinned"]["positive_values"]
    assert read.head_sha256 == head.result_sha256
    assert read.status == "restricted"
    assert (read.floating_debt.state, read.floating_debt.amount) == (
        pinned["floating"]["state"],
        Decimal(pinned["floating"]["amount"]),
    )
    first = read.shocks[0]
    assert first.shock_bp.amount == Decimal(100)
    assert (first.added_interest.state, first.added_interest.amount) == (
        "known",
        Decimal(pinned["first_shock_gross"]["amount"]),
    )
    assert first.cov_after.amount == Decimal(pinned["first_shock_cov_after"]["amount"])
    assert first.after_hedge.state == "missing"
    assert first.after_hedge.amount is None and first.after_hedge.reason
    assert len(read.shocks) == 2
    assert (read.foreign_debt.state, read.foreign_debt.amount) == ("known", Decimal(0))
    assert read.hedge_ratio.state == "missing" and read.hedge_ratio.reason
    assert list(read.limitations) == EXPECTED["cases"]["positive"]["own_limitations"]


def test_the_reader_shows_a_gap_with_its_reason_never_zero() -> None:
    head, store = _head_and_store("gap_no_facility_schedule")
    read = cp2e.cp2e_reader(cast(Execution, store), head)
    assert read.floating_debt.state == "missing"
    assert read.floating_debt.amount is None
    assert read.floating_debt.reason
    assert read.foreign_debt.state == "missing" and read.foreign_debt.amount is None
    assert all(s.added_interest.state == "missing" for s in read.shocks)


def test_the_reader_refuses_another_modules_head() -> None:
    head, store = _head_and_store("positive")
    other = SimpleNamespace(
        head_module=lambda h: store.head_module(h).model_copy(update={"module_id": "CP-8"})
    )
    with pytest.raises(ValueError, match="CP-2E"):
        cp2e.cp2e_reader(cast(Execution, other), head)


def test_the_reader_refuses_a_head_without_the_pinned_facts() -> None:
    head, store = _head_and_store("positive")
    bare = SimpleNamespace(
        head_module=lambda h: store.head_module(h).model_copy(update={"facts": (), "tables": ()})
    )
    with pytest.raises(ValueError, match="T2F"):
        cp2e.cp2e_reader(cast(Execution, bare), head)


# --- ruling Q5: hostile text raises only ValueError subclasses from every schema class -----------
_HOSTILE = [
    "",
    "null",
    "[]",
    '{"summary": {"text": "\\ud800"}}',
    "{" * 5000,
    '{"rate_shocks_bp": [1e999], "summary": 7}',
    '{"reporting_currency": {"source_id": "\u0000", "locator": 1}}',
    json.dumps({"assessments": [{"basis": [None]}]}),
]


@pytest.mark.parametrize("text", _HOSTILE)
def test_hostile_text_raises_only_value_errors_from_the_schema(text: str) -> None:
    try:
        cp2e.MacroFxSubmission.model_validate_json(text)
    except ValueError:
        pass
    assert cp2e._parsed(text)[0] is None


def test_no_schema_class_carries_a_custom_validator() -> None:
    for cls in (cp2e.MacroFxSubmission, cp2e.MacroFxReport):
        assert not cls.__pydantic_decorators__.model_validators
        assert not cls.__pydantic_decorators__.field_validators


# --- mutation pins: citation quote choice, attempt, reader fact coordinates ------------------------
_OWN_FIELD = {  # T2F.1 row -> the submission field the row was read from
    "r01": ("reporting_currency",),
    "r02": ("earnings", "total_debt"),
    "r03": ("rate_exposure", "facility_balance"),
    "r04": ("rate_exposure", "rate_basis"),
    "r05": ("rate_exposure", "spread"),
    "r06": ("rate_exposure", "floor"),
    "r07": ("earnings", "ebitda"),
    "r08": ("earnings", "interest"),
    "r09": ("earnings", "fcf"),
    "r10": ("fx", "fx_cash_effect"),
    "r11": ("fx", "debt_currency"),
}


def _positive_report() -> cp2e.MacroFxReport:
    store, pack = _store("positive"), _pack("positive")
    outcome = cp2e.ENTRY_VALIDATOR(cast(Execution, store), pack, _attempt(store))
    assert outcome.output is not None
    return cp2e.MacroFxReport.model_validate_json(outcome.output)


@pytest.mark.parametrize("row", sorted(_OWN_FIELD))
@pytest.mark.parametrize("column", ["value", "basis"])
def test_a_sourced_fact_cites_the_quote_of_the_field_it_was_read_from(
    row: str, column: str
) -> None:
    """Fix round 1, M1: a T2F.1 fact carries its own field's quote, not the first quote given
    for its page."""
    node: Any = SUBMISSIONS["positive"]
    for key in _OWN_FIELD[row]:
        node = node[key]
    fact = next(f for f in _positive_report().facts if f.fact_id == f"T2F.1.{row}.{column}")
    assert [c.quote for c in fact.citations] == [node["quote"]]
    assert [(c.source_id, c.locator) for c in fact.citations] == [
        (node["source_id"], node["locator"])
    ]


def test_a_derived_fact_cites_the_first_of_its_own_input_quotes_on_each_page() -> None:
    sub = SUBMISSIONS["positive"]
    facts = {f.fact_id: f for f in _positive_report().facts}
    balance = sub["rate_exposure"]["facility_balance"]["quote"]
    ebitda, interest = sub["earnings"]["ebitda"]["quote"], sub["earnings"]["interest"]["quote"]
    # added interest reads the balance, the rate basis and the floor (all page:5): the balance is
    # the first of them in formula order
    assert [(c.locator, c.quote) for c in facts["T2F.3.r01.gross"].citations] == [
        ("page:5", balance)
    ]
    # interest cover reads EBITDA (page:2) and cash interest (page:3), not the page:5 quotes
    assert [(c.locator, c.quote) for c in facts["T2F.2.r03.value"].citations] == [
        ("page:2", ebitda),
        ("page:3", interest),
    ]


def test_every_citation_quote_is_a_quote_the_submission_gave_for_that_page() -> None:
    sub = json.dumps(SUBMISSIONS["positive"])
    report = _positive_report()
    given: dict[tuple[str, str], set[str]] = {}
    for found in cp2e_quote_refs(json.loads(sub)):
        given.setdefault((found["source_id"], found["locator"]), set()).add(found["quote"])
    records: tuple[Fact | Claim, ...] = (*report.facts, *report.claims)
    for record in records:
        for c in record.citations:
            assert c.quote in given[(c.source_id, c.locator)]


def cp2e_quote_refs(node: Any) -> list[dict[str, str]]:
    if isinstance(node, dict):
        here = [node] if {"source_id", "locator", "quote"} <= node.keys() else []
        return here + [x for v in node.values() for x in cp2e_quote_refs(v)]
    if isinstance(node, list):
        return [x for v in node for x in cp2e_quote_refs(v)]
    return []


def test_the_module_carries_the_attempt_number() -> None:
    store, pack = _store("positive"), _pack("positive")
    outcome = cp2e.ENTRY_VALIDATOR(cast(Execution, store), pack, _attempt(store))
    assert outcome.output is not None
    report = cp2e.MacroFxReport.model_validate_json(outcome.output)
    assert cp2e.cp2e_module(report=report, inputs=(), attempt=1).attempt == 1


def test_the_reader_takes_each_value_from_its_own_fact() -> None:
    head, store = _head_and_store("positive")
    module = store.head_module(head)
    changed = {"T2F.2.r05.value": Decimal(7), "T2F.5.r01.value": Decimal("0.4")}
    facts = tuple(
        f.model_copy(update={"amount": changed[f.fact_id], "status": "known", "limitation": None})
        if f.fact_id in changed
        else f
        for f in module.facts
    )
    other = SimpleNamespace(head_module=lambda h: module.model_copy(update={"facts": facts}))
    read = cp2e.cp2e_reader(cast(Execution, other), head)
    assert read.foreign_debt.amount == Decimal(7)
    assert (read.hedge_ratio.state, read.hedge_ratio.amount) == ("known", Decimal("0.4"))


# --- fix round 1, H1: a summary that is not valid run text is a journaled issue --------------------
_MALFORMED = "summary.text: Value error, Malformed run text: unbalanced or empty reference"


@pytest.mark.parametrize("summary", ["Rates matter [a lot", "Exposure is {low", "Outlook [", "{}"])
def test_a_malformed_summary_is_a_journaled_issue_not_a_raise(summary: str) -> None:
    raw = _set(_positive(), ("summary", "text"), summary)
    assert cp2e.validate_macro_fx(submission=raw, pages=_pages("positive")) == (_MALFORMED,)
    out = _validate(raw)
    assert out.output is None
    assert out.issues == (_MALFORMED,)


@pytest.mark.parametrize("summary", ["Watch [abc] closely", "Watch {abc|x} closely", "See [a]"])
def test_a_summary_reference_is_a_journaled_issue(summary: str) -> None:
    """A reference in the summary names no fact of the module, so settle would reject the
    module after a valid step; it is refused with the step instead."""
    raw = _set(_positive(), ("summary", "text"), summary)
    assert _validate(raw).issues == ("summary.text: text carries a reference",)


_EMPTY = "summary.text: empty text"


@pytest.mark.parametrize("summary", ["", " ", "\u200b"], ids=["empty", "space", "zwsp"])
def test_an_empty_or_blank_summary_gets_exactly_one_issue(summary: str) -> None:
    """`chk.prose` already refuses it as empty text; RunText's own length message would only
    repeat the same fault, so `run_text` does not run on text refused as empty/blank."""
    raw = _set(_positive(), ("summary", "text"), summary)
    assert cp2e.validate_macro_fx(submission=raw, pages=_pages("positive")) == (_EMPTY,)
    out = _validate(raw)
    assert out.output is None
    assert out.issues == (_EMPTY,)


def test_the_empty_summary_fix_changes_no_frozen_cp2e_outcome() -> None:
    """Parity over cases/cp2e-owner: the valid cases stay valid, and every refusal and blocked
    mutation keeps its frozen issues."""
    for case in CASES:
        raw = copy.deepcopy(SUBMISSIONS[case])
        assert cp2e.validate_macro_fx(submission=raw, pages=_pages(case)) == ()
    for entry in SUBMISSIONS["refusal_mutations"]["entries"]:
        raw = _mutated(entry["edits"])
        issues = cp2e.validate_macro_fx(submission=raw, pages=_pages("positive"))
        assert list(issues) == entry["all_issues"]


def test_a_plain_summary_still_passes() -> None:
    assert _validate(_positive()).issues == ()


# --- fix round 1, M2: acceptance 1 compares every Fact field of every cell -------------------------
def _amount(text: str | None) -> Decimal | None:
    return None if text is None else Decimal(text)


@pytest.mark.parametrize("case", CASES)
def test_every_fact_equals_its_expected_cell_field_for_field(case: str) -> None:
    store, pack = _store(case), _pack(case)
    outcome = cp2e.ENTRY_VALIDATOR(cast(Execution, store), pack, _attempt(store))
    assert outcome.output is not None
    report = cp2e.MacroFxReport.model_validate_json(outcome.output)
    cells = [f for t in EXPECTED["cases"][case]["tables"] for r in t["rows"] for f in r["facts"]]
    assert len(report.facts) == len(cells)
    for fact, cell in zip(report.facts, cells, strict=True):
        table_id, row_id, field = cell["fact_id"].rsplit(".", 2)
        assert (fact.fact_id, fact.table_id, fact.row_id, fact.field) == (
            cell["fact_id"],
            table_id,
            row_id,
            field,
        )
        assert fact.label == cell["column"]
        assert (fact.amount, fact.scale) == (_amount(cell["amount"]), Decimal(cell["scale"]))
        assert (fact.text, fact.status, fact.unit, fact.currency) == (
            cell["text"],
            cell["status"],
            cell["unit"],
            cell["currency"],
        )
        assert (fact.decimals, fact.period) == (cell["decimals"], cell["period"])
        assert (fact.calculation_id, fact.value_class, fact.formula) == (
            cell["calculation_id"],
            cell["value_class"],
            cell["formula"],
        )
        assert fact.limitation == cell["limitation"]
        # nothing the oracle does not list is set
        assert (fact.basis, fact.denominator, fact.source_amount, fact.stated_amount) == (
            None,
            None,
            None,
            None,
        )
        assert fact.calculation_status is None


# --- fix round 1, L2: the stored reference rate is the normalised name the page prints -----------
def test_the_stored_reference_rate_is_normalised() -> None:
    raw = _positive()
    raw["rate_exposure"]["rate_basis"]["reference_rate"] = "Term− SOFR"
    inputs = cp2e.inputs_from_submission(raw, source_names=_names("positive"))
    assert inputs.facility is not None
    assert inputs.facility.basis.reference_rate == "Term- SOFR"
    cell = next(
        c
        for t in cp2e.compute(inputs).tables
        for r in t.rows
        for c in r.cells
        if c.fact_id == "T2F.1.r04.value"
    )
    assert cell.text == "Floating rate, Term- SOFR reference rate"


def test_the_frozen_reference_rate_is_unchanged() -> None:
    assert _inputs("positive").facility is not None
    assert _inputs("positive").facility.basis.reference_rate == "SOFR"  # type: ignore[union-attr]


@pytest.mark.parametrize("bad", ["Rates [a lot", "{low", "{}", "[]"])
@pytest.mark.parametrize(
    "path",
    [
        ("shock_rationale",),
        ("assessments", 0, "text"),
        ("assessments", 2, "limitation"),
        ("hedge_absence", "reason"),
        ("hedge_absence", "follow_up"),
        ("fx", "operating_fx_absence", "reason"),
        ("fx", "operating_fx_absence", "follow_up"),
    ],
    ids=lambda p: ".".join(map(str, p)) if isinstance(p, tuple) else p,
)
def test_no_other_free_text_field_can_raise_the_report_builder(
    path: tuple[str | int, ...], bad: str
) -> None:
    """Fix round 1, H1 class: every model text field is tried with hostile bracket text. Those
    that become ``Fact.text`` or ``limitation`` are plain strings, so the validator returns a
    result (never raises); only the summary is ``RunText``."""
    out = _validate(_set(_positive(), path, bad))
    assert out.output is not None or out.issues


def test_the_summary_is_the_only_run_text() -> None:
    claims = [c for c in _positive_report().claims]
    texts = {c.claim_id: c.text for c in claims}
    assert texts["CP-2E-VIEW-01"] == SUBMISSIONS["positive"]["summary"]["text"]
    assert not any(SUBMISSIONS["positive"]["shock_rationale"] in t for t in texts.values())


# --- fix round 1, L3: submit over a real store, the parse path, the RULES guard, reader status ---
def _ready_store(tmp_path: Any) -> tuple[Execution, str]:
    """CP-0 settled through the public workflow; the CP-2E ticket is open and untouched."""
    workflow, pack = start("positive", tmp_path)
    drive_cp0(workflow, pack, "positive")
    return Execution(tmp_path / "store"), workflow._binding.ticket_id


def test_submit_journals_the_step_and_settles_the_module(tmp_path: Any) -> None:
    store, ticket = _ready_store(tmp_path)
    payload = json.dumps(SUBMISSIONS["positive"])
    out = cp2e.submit(store, ticket, "macro_fx", payload, None)
    assert out.journal.status == "finished" and not out.journal.issues
    assert (out.nulls_resolved, out.prefilled, out.prefilled_kinds) == ((), (), ())
    assert json.loads(out.payload) == SUBMISSIONS["positive"]
    head = next(h for h in store.read().heads if h.module_id == "CP-2E")
    assert head.status == "restricted"
    assert head.qualification == cp2e.QUALIFICATION
    assert head.result_sha256 == out.journal.result_sha256
    module = store.head_module(head)
    assert [i.input_id for i in module.inputs] == ["prepared-pack", "CP-0", "macro-fx-submission"]
    step = out.journal.steps[0]
    assert (step.step_id, step.status) == ("macro_fx", "valid")


def test_submit_serves_only_its_one_step(tmp_path: Any) -> None:
    store, ticket = _ready_store(tmp_path)
    with pytest.raises(ValueError, match="one step"):
        cp2e.submit(store, ticket, "other_step", json.dumps(SUBMISSIONS["positive"]), None)
    assert not [a for a in store.read().attempts if a.module_id == "CP-2E" and a.steps]


def test_submit_adds_the_journaled_rule_issues_to_the_step(tmp_path: Any) -> None:
    store, ticket = _ready_store(tmp_path)
    out = cp2e.submit(
        store, ticket, "macro_fx", json.dumps(SUBMISSIONS["positive"]), lambda _t: ("Rule says no",)
    )
    assert out.journal.status == "finished"
    assert out.journal.steps[0].status == "invalid"
    assert "Rule says no" in out.journal.issues
    assert not [h for h in store.read().heads if h.module_id == "CP-2E" and h.status != "blocked"]


def test_submit_journals_a_validator_issue_without_raising(tmp_path: Any) -> None:
    store, ticket = _ready_store(tmp_path)
    raw = _set(_positive(), ("summary", "text"), "Rates matter [a lot")
    out = cp2e.submit(store, ticket, "macro_fx", json.dumps(raw), None)
    assert out.journal.steps[0].status == "invalid"
    assert out.journal.issues == (_MALFORMED,)


@pytest.mark.parametrize(
    "text", ["{" * 400, '{"summary": {"text": "\\ud800"}}', '{"a": NaN}', "not json"]
)
def test_the_parse_path_is_the_bounded_storable_one(text: str) -> None:
    """Protocol section 6: model text is parsed by `json_object`, which refuses what a record
    cannot store; a plain `model_validate_json` would report these as shape errors instead."""
    assert cp2e._parsed(text) == (None, ("payload: not a JSON object",))


@pytest.mark.parametrize("text", ['{"fx": 5}', '{"fx": null}', '{"fx": []}'])
def test_rules_read_a_non_object_branch_as_no_absence(text: str) -> None:
    seen = _seen(EXPECTED["cases"]["positive"]["tool_use_required"]["read_pages_cover"], 0)
    assert cp2e.RULES(text, seen) == ()


def test_the_no_search_case_can_hold_one_more_line_than_the_listed_bound() -> None:
    """RULES = the fixed absence line + at most 20 listed unread-page lines, each <= 600."""
    raw = _positive()
    raw["assessments"][0]["basis"] = [
        {"source_id": "financial", "locator": f"page:{n}", "quote": "q"} for n in range(50)
    ]
    out = cp2e.RULES(json.dumps(raw), _seen([], 0))
    assert out[0] == "Absence claim without a recorded search"
    assert len(out) <= 21
    assert all(len(line) <= 600 for line in out)


@pytest.mark.parametrize("status", ["accepted", "restricted"])
def test_the_reader_reports_the_head_status(status: str) -> None:
    head, store = _head_and_store("positive")
    module = store.head_module(head).model_copy(update={"status": status, "limitations": ()})
    if status == "restricted":
        module = module.model_copy(update={"limitations": ("a limit",)})
    head = head_of(module)
    other = SimpleNamespace(head_module=lambda h: module)
    assert cp2e.cp2e_reader(cast(Execution, other), head).status == status


# --- fix round 1, rulings round 5: label decimal (item 2) and absence paths (item 3) -------------
def test_a_decimal_label_run_does_not_label_a_whole_figure() -> None:
    """`spread 25.5` must not label the token 25 when another whole 25 is the quote's one
    occurrence (probe p_label_decimal): the label match needs the whole-run trailing guard."""
    sentence = "The margin is spread 25.5 basis points and the fee is 25 basis points."
    pages = dict(_pages("positive"))
    pages["page:5"] += "\n" + sentence
    raw = _positive()
    raw["rate_exposure"]["spread"] = {
        "source_id": "financial",
        "locator": "page:5",
        "quote": sentence,
        "bps_text": "25",
    }
    assert cp2e.validate_macro_fx(submission=raw, pages=pages) == (
        "rate_exposure.spread: bps_text 25 is not labelled spread in the quote",
    )


@pytest.mark.parametrize("tail", [" basis points", ".", " and more"])
def test_a_whole_labelled_figure_is_still_accepted(tail: str) -> None:
    sentence = f"The margin is spread 25{tail}"
    pages = dict(_pages("positive"))
    pages["page:5"] += "\n" + sentence
    raw = _positive()
    raw["rate_exposure"]["spread"] = {
        "source_id": "financial",
        "locator": "page:5",
        "quote": sentence,
        "bps_text": "25",
    }
    assert cp2e.validate_macro_fx(submission=raw, pages=pages) == ()


@pytest.mark.parametrize(
    ("path", "key"),
    [
        (("rate_absence",), "rate_absence"),
        (("fx", "debt_currency_absence"), "fx.debt_currency_absence"),
        (("fx", "operating_fx_absence"), "fx.operating_fx_absence"),
        (("hedge_absence",), "hedge_absence"),
    ],
    ids=["rate", "debt-currency", "operating-fx", "hedge"],
)
@pytest.mark.parametrize("part", ["reason", "follow_up"])
def test_an_absence_digit_issue_names_the_submission_path(
    path: tuple[str, ...], key: str, part: str
) -> None:
    raw = _no_absence()
    if path == ("rate_absence",):
        raw["rate_exposure"] = None
    node: Any = raw
    for step in path[:-1]:
        node = node[step]
    node[path[-1]] = {"reason": "none", "follow_up": "ask"}
    node[path[-1]][part] = "see 5 items"
    issues = cp2e.validate_macro_fx(submission=raw, pages=_pages("positive"))
    assert f"{key}.{part}: digits are not allowed" in issues
    assert not any(i.startswith(f"{path[-1]}.") for i in issues if path[0] == "fx")
