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
from cp2e_runs import make_pack
from test_method_cp2e import (
    CASES,
    EXPECTED,
    SUBMISSIONS,
    _cited,
    _inputs,
    _issues_with,
    _names,
    _pages,
    _reference_rate_adapter,
)

from deploy_vii import prose
from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.cp2e import CP2E
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Module, ModuleView, View
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
    assert SHIPPED_MAPS[-1] is CP2E


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
def test_a_page_citation_carries_the_first_quote_the_submission_gives_for_it() -> None:
    store, pack = _store("positive"), _pack("positive")
    outcome = cp2e.ENTRY_VALIDATOR(cast(Execution, store), pack, _attempt(store))
    assert outcome.output is not None
    report = cp2e.MacroFxReport.model_validate_json(outcome.output)
    first = SUBMISSIONS["positive"]["rate_exposure"]["facility_balance"]["quote"]
    fact = next(f for f in report.facts if f.fact_id == "T2F.1.r03.value")
    assert [(c.locator, c.quote) for c in fact.citations] == [("page:5", first)]


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
