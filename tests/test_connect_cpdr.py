"""CP-DR Stage 2: the owner core's G1-X parts, store adapter, registrations and bindings.

Expected values come from `cases/cpdr-owner` and `docs/CPDR-OWNER-LEASE.md`, never from the code
under test. Store runs (a real `Execution` with CP-0 settled) are `tests/test_owner_cpdr.py`
(Stage 5); here the store is a read-only test double that serves the bound CP-0 module.
"""

import copy
import hashlib
import json
import shutil
from dataclasses import fields
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from defect_classes import BLANK_CASES, EMPTY_TEXT, blank_failure
from test_method_cpdr import (
    AS_OF,
    EXPECTED,
    GAP_ID,
    MANIFEST,
    SUBMISSIONS,
    TRANSACTIONS,
    agenda,
    check,
    cp0_facts,
    oracle_fact,
    sources,
    submission,
)

from deploy_vii import report_view
from deploy_vii.bindings import RAIL_DESTINATIONS, validate_bindings
from deploy_vii.bindings.cpdr import CPDR
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Fact, Input, Module, ModuleView, Run, Source, View
from deploy_vii.cp0_workflow import submit_cp0_review
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    Head,
    Qualification,
    StepSubmission,
    head_of,
)
from deploy_vii.live.tools import Seen
from deploy_vii.preparation import PreparedPack
from deploy_workflow import host
from deploy_workflow import owner_workflow as owner
from deploy_workflow.owners import cpdr
from deploy_workflow.workflow import WorkflowError

# --- backlog: blank citation quote (round 13 addendum 3) --------------------------------------

QUOTE_PATH = "gaps[0].questions[0].citations[0].quote"


def _quote_adapter(page: str, quote: str, value: str) -> tuple[str, ...]:
    raw = copy.deepcopy(SUBMISSIONS["cpdr"]["partial"])
    raw["gaps"][0]["questions"][0]["citations"][0]["quote"] = value
    return check(submission(raw))


@pytest.mark.parametrize("blank", BLANK_CASES, ids=lambda c: c.case_id)
def test_blank_citation_quote_is_refused_with_the_empty_text_frame(blank: Any) -> None:
    failure = blank_failure(blank, _quote_adapter, EMPTY_TEXT.format(path=QUOTE_PATH))
    assert failure is None, failure


@pytest.mark.parametrize(
    "blank", [c for c in BLANK_CASES if c.whitespace_only], ids=lambda c: c.case_id
)
def test_blank_citation_quote_is_refused_before_the_occurrence_check(blank: Any) -> None:
    """The frame replaces the page-occurrence mismatch for that citation (one defect, one issue)."""
    assert _quote_adapter("", "", blank.value) == (EMPTY_TEXT.format(path=QUOTE_PATH),)


def test_genuine_citation_quote_is_accepted() -> None:
    assert _quote_adapter("", "", TRANSACTIONS["citations"][0]["quote"]) == ()


# --- backlog: caller-quoting issue lines go through clipped / listed_issues --------------------

HUGE = "x" * 5000


def test_validator_gap_issue_is_clipped() -> None:
    """cpdr.py:231: a gap id past the schema bound (model_construct) cannot grow the issue line."""
    gap = cpdr.GapResearch.model_construct(gap_id=HUGE, questions=())
    sub = cpdr.ResearchSubmission.model_construct(gaps=(gap,))
    issues = cpdr.validate_research(submission=sub, upstream=agenda(empty=False), pack=sources())
    assert issues[0].startswith("gap_id is not in the CP-0 agenda: xxx")
    assert all(len(line) <= 600 for line in issues)


@pytest.mark.parametrize("field", ["fact_id", "row_id"])
def test_agenda_parse_errors_are_clipped(field: str) -> None:
    """cpdr.py:126/:137/:155/:161: the ValueError text quotes a gap or fact id."""
    bad = Fact.model_construct(
        fact_id=HUGE if field == "fact_id" else "T5.g.gap",
        table_id="T5",
        row_id=HUGE if field == "row_id" else "g",
        field="gap" if field == "row_id" else "other",
        status="known",
        text="not the readiness form" if field == "row_id" else "x",
    )
    with pytest.raises(ValueError) as error:
        cpdr.parse_agenda((bad,))
    assert 0 < len(str(error.value)) <= 600


def _rules_payload(count: int, source: str) -> str:
    questions = [
        {
            "question_id": f"q{i}",
            "outcome": "not_found",
            "searched_sources": [source],
            "citations": [],
        }
        for i in range(count)
    ]
    return json.dumps({"gaps": [{"gap_id": "g", "questions": questions}]})


def test_rules_absence_lines_are_listed_and_clipped() -> None:
    lines = cpdr.RULES(_rules_payload(60, HUGE), Seen())
    assert len(lines) == 20
    assert all(len(line) <= 600 for line in lines)
    assert lines[-1] == (
        "Absence claim without a recorded search: 41 further absence claims not listed"
    )


TOTALS = (
    "gaps_total",
    "gaps_resolved",
    "gaps_partial",
    "gaps_unresolved",
    "questions_total",
    "answered_total",
    "unresolved_total",
)

# --- the plug-in parts (protocol section 2) ------------------------------------------------------

RULES_PREFIXES = (
    "Absence claim without a recorded search:",
    "Cited page not read through read_pages:",
)


def test_core_constants_match_the_lease() -> None:
    assert cpdr.MODULE_ID == "CP-DR"
    assert cpdr.STEP_ID == "research"
    assert cpdr.STEP_IDS == ("research",)
    assert cpdr.SCHEMAS == {"research": cpdr.ResearchSubmission}
    assert cpdr.QUALIFICATION == Qualification(implementation="implemented")


LITERALS = {
    "partial": SUBMISSIONS["cpdr"]["partial"],
    "unresolved": SUBMISSIONS["cpdr"]["unresolved"],
    "empty_agenda": SUBMISSIONS["cpdr"]["empty_agenda"],
    "blocked-0": SUBMISSIONS["cpdr"]["blocked"]["attempt_0"],
    "blocked-1": SUBMISSIONS["cpdr"]["blocked"]["attempt_1"],
}


@pytest.mark.parametrize("name", list(LITERALS))
def test_schema_round_trips_and_gives_the_tail_digest(name: str) -> None:
    text = json.dumps(LITERALS[name])
    parsed = cpdr.SCHEMAS[cpdr.STEP_ID].model_validate_json(text)
    again = cpdr.SCHEMAS[cpdr.STEP_ID].model_validate_json(parsed.model_dump_json())
    assert again == parsed
    assert parsed.content_hash() == hashlib.sha256(parsed.model_dump_json().encode()).hexdigest()
    assert json.loads(parsed.model_dump_json()) == LITERALS[name]


def seen_of(calls: list[dict[str, Any]]) -> Seen:
    """Seen rebuilt from the oracle's literal call list (an unscoped search covers every source)."""
    read: set[tuple[str, str]] = set()
    searched: list[str | None] = []
    for call in calls:
        arguments = call["arguments"]
        if call["tool"] == "search_pack":
            searched.append(arguments["source_id"])
        elif call["tool"] == "read_pages":
            read |= {
                (arguments["source_id"], f"page:{n}")
                for n in range(arguments["first_page"], arguments["last_page"] + 1)
            }
    return Seen(read=frozenset(read), searched=tuple(searched))


@pytest.mark.parametrize("name", list(EXPECTED["refusals"]))
def test_rules_reproduce_the_oracle_refusals(name: str) -> None:
    item = SUBMISSIONS["refusal_inputs"][name]
    pinned = tuple(EXPECTED["refusals"][name]["step_issues"])
    calls = item["calls"]
    if isinstance(calls, str):  # a named recorded sequence of `submissions.tool_calls`
        calls = SUBMISSIONS["tool_calls"][calls]
    rules = cpdr.RULES(json.dumps(item["payload"]), seen_of(calls))
    assert rules == tuple(i for i in pinned if i.startswith(RULES_PREFIXES))
    gaps = agenda(empty=item["cp0"] == "cp0_readiness_review_empty_agenda")
    content = cpdr.validate_research(
        submission=submission(item["payload"]), upstream=gaps, pack=sources()
    )
    assert tuple(dict.fromkeys((*content, *rules))) == pinned


def test_rules_reproduce_the_blocked_attempts() -> None:
    for attempt in ("attempt_0", "attempt_1"):
        payload = SUBMISSIONS["cpdr"]["blocked"][attempt]
        calls = SUBMISSIONS["tool_calls"]["blocked"]
        got = cpdr.RULES(json.dumps(payload), seen_of(calls))
        want = tuple(
            i for i in EXPECTED["blocked"][attempt]["issues"] if i.startswith(RULES_PREFIXES)
        )
        assert got == want, attempt


@pytest.mark.parametrize("case", ["partial", "unresolved", "empty_agenda"])
def test_rules_accept_the_recorded_tool_use_of_each_positive_case(case: str) -> None:
    calls = [c for c in SUBMISSIONS["tool_calls"][case] if c["tool"] != "read_inputs"]
    assert cpdr.RULES(json.dumps(SUBMISSIONS["cpdr"][case]), seen_of(calls)) == ()


def _not_found(qid: str, *searched: str) -> dict[str, Any]:
    return {
        "question_id": qid,
        "outcome": "not_found",
        "searched_sources": list(searched),
        "citations": [],
    }


def _payload(*questions: dict[str, Any]) -> str:
    return json.dumps({"gaps": [{"gap_id": "g", "questions": list(questions)}]})


ABSENCE = "Absence claim without a recorded search: {} not_found for {}; search_pack that source before claiming it is not found"


def test_rules_absence_is_sorted_by_line_and_deduplicated() -> None:
    text = _payload(
        _not_found("b", "financial-2", "financial"),
        _not_found("a", "x"),
        _not_found("b", "financial"),
    )
    assert cpdr.RULES(text, Seen()) == (
        ABSENCE.format("a", "x"),
        ABSENCE.format("b", "financial-2"),
        ABSENCE.format("b", "financial"),
    )


def test_rules_absence_honours_a_scoped_or_unscoped_search() -> None:
    text = _payload(_not_found("a", "x", "y"))
    assert cpdr.RULES(text, Seen(searched=("x",))) == (ABSENCE.format("a", "y"),)
    assert cpdr.RULES(text, Seen(searched=(None,))) == ()


def test_rules_ignore_answered_questions_and_malformed_payloads() -> None:
    answered = {**_not_found("a", "x"), "outcome": "answered"}
    assert cpdr.RULES(_payload(answered), Seen()) == ()
    for text in ("not json", "[1]", '{"gaps": 3}', '{"gaps": [3, {"questions": 4}]}', "{}"):
        assert cpdr.RULES(text, Seen()) == (), text
    odd = _payload({**_not_found("a", "x"), "searched_sources": [3, "y"]})
    assert cpdr.RULES(odd, Seen()) == (ABSENCE.format("a", "y"),)


def test_rules_put_absence_before_unread_pages() -> None:
    citation = {
        "source_id": "financial",
        "source_sha256": "0" * 64,
        "locator": "page:2",
        "quote": "q",
    }
    question = {**_not_found("a", "x"), "citations": [citation]}
    assert cpdr.RULES(_payload(question), Seen()) == (
        ABSENCE.format("a", "x"),
        "Cited page not read through read_pages: financial page:2",
    )


# --- the store double: serves the bound CP-0 module, the pack and retained payloads ---------------


class Store(Execution):
    """A read-only `Execution` double (tests only): no directory is touched."""

    def __init__(
        self,
        pack: PreparedPack,
        modules: dict[str, Module],
        payloads: dict[str, str],
        *,
        head_only: bool = False,
    ):
        super().__init__(Path("/nonexistent-cpdr-store"))
        self._head_only = head_only
        self._pack = pack
        self._modules = modules
        self._payloads = payloads
        self._snapshot = ExecutionSnapshot(run=pack.run, pack_sha256=pack.content_hash())

    def read(self) -> ExecutionSnapshot:
        return self._snapshot

    def pack(self, snapshot: ExecutionSnapshot | None = None) -> PreparedPack:
        return self._pack

    def result(self, sha256: str) -> Module:
        if self._head_only:  # a head is read through `head_module` (its live status), not the blob
            raise AssertionError("result() read where head_module() is the contract")
        return self._modules[sha256]

    def head_module(self, head: Head) -> Module:
        return self._modules[head.result_sha256].model_copy(update={"status": head.status})

    def payload(self, sha256: str) -> str:
        return self._payloads[sha256]


def prepared_pack() -> PreparedPack:
    return PreparedPack(run=Run.model_validate_json(json.dumps(MANIFEST["run"])), sources=sources())


def cp0_module(*, empty: bool, status: str = "restricted") -> Module:
    run = prepared_pack().run
    return Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id="CP-0",
        status=status,  # type: ignore[arg-type]
        facts=cp0_facts(empty=empty),
        limitations=("Synthetic case; not real issuer qualification",),
    )


def attempt_of(
    cp0: Module | None,
    payload: str | None = None,
    *,
    cp0_status: str = "restricted",
    pack: PreparedPack | None = None,
) -> tuple[Attempt, Store]:
    """A CP-DR attempt binding the pack and `cp0` (`prepared-pack`, `CP-0` at `cp0_status`)."""
    pack = prepared_pack() if pack is None else pack
    modules = {} if cp0 is None else {cp0.content_hash(): cp0}
    payloads = {} if payload is None else {hashlib.sha256(payload.encode()).hexdigest(): payload}
    bound = [Input(input_id="prepared-pack", sha256=pack.content_hash())]
    if cp0 is not None:
        bound.append(Input(input_id="CP-0", sha256=cp0.content_hash(), status=cp0_status))  # type: ignore[arg-type]
    steps = (
        ()
        if payload is None
        else (
            StepSubmission(
                step_id="research",
                inputs=tuple(bound),
                payload_sha256=hashlib.sha256(payload.encode()).hexdigest(),
            ),
        )
    )
    attempt = Attempt(
        ticket_id="ticket-1", module_id="CP-DR", inputs=tuple(bound), number=0, steps=steps
    )
    return attempt, Store(pack, modules, payloads)


# --- the store adapter ---------------------------------------------------------------------------


@pytest.mark.parametrize("empty", [False, True])
def test_adapter_returns_the_stage_1_input_object(empty: bool) -> None:
    case = "empty_agenda" if empty else "partial"
    sub = submission(SUBMISSIONS["cpdr"][case])
    attempt, store = attempt_of(cp0_module(empty=empty))
    want = cpdr.CpdrInputs(agenda=agenda(empty=empty), submission=sub, as_of=AS_OF)
    assert cpdr._inputs(store, attempt, sub) == want


def test_adapter_reads_the_as_of_of_the_run_and_the_agenda_of_the_bound_cp0() -> None:
    sub = submission(SUBMISSIONS["cpdr"]["partial"])
    attempt, store = attempt_of(cp0_module(empty=False))
    got = cpdr._inputs(store, attempt, sub)
    assert got.as_of == date.fromisoformat(MANIFEST["run"]["as_of"])
    assert got.submission is sub
    assert [g.gap_id for g in got.agenda] == [GAP_ID]


def test_adapter_without_a_bound_cp0_fails_closed() -> None:
    attempt, store = attempt_of(None)
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        cpdr.cpdr_upstream(store=store, attempt=attempt)


def test_adapter_with_a_cp0_outside_the_readiness_form_fails_closed() -> None:
    bad = cp0_module(empty=False).model_copy(update={"facts": (cp0_facts(empty=False)[1],)})
    attempt, store = attempt_of(bad)
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        cpdr.cpdr_upstream(store=store, attempt=attempt)


def test_upstream_carries_the_bound_cp0_status() -> None:
    attempt, store = attempt_of(cp0_module(empty=False))
    got = cpdr.cpdr_upstream(store=store, attempt=attempt)
    assert got.cp0_status == "restricted"
    assert got.agenda == agenda(empty=False)
    assert got.sources == tuple((s.source_id, s.status) for s in sources())


# --- view ----------------------------------------------------------------------------------------

DRAFT_KEYS = MANIFEST["view_tree_draft"]["keys"]


def _walk_keys(node: Any) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in _walk_keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in _walk_keys(v)}
    return set()


@pytest.mark.parametrize("empty", [False, True])
def test_view_matches_the_draft_tree(empty: bool) -> None:
    attempt, store = attempt_of(cp0_module(empty=empty))
    digest, body = cpdr.view(store, attempt)
    tree = json.loads(body)
    assert tree == {**DRAFT_KEYS, "gaps": [] if empty else DRAFT_KEYS["gaps"]}
    assert list(tree) == list(DRAFT_KEYS)
    assert body == json.dumps(tree, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    assert digest == hashlib.sha256(body.encode()).hexdigest()


def test_view_holds_no_quote_citation_or_record_at_any_depth() -> None:
    attempt, store = attempt_of(cp0_module(empty=False))
    keys = _walk_keys(json.loads(cpdr.view(store, attempt)[1]))
    assert not keys & {"quote", "quotes", "citations", "citation", "record_json"}


def test_view_of_a_gap_whose_text_splits_two_ways_shows_the_full_text() -> None:
    text = "scope/material: A; affects CP-DR; B; affects CP-DR; C"
    fact = Fact(fact_id="T5.g.gap", label="gap", table_id="T5", row_id="g", field="gap", text=text)
    cp0 = cp0_module(empty=False).model_copy(update={"facts": (fact,)})
    attempt, store = attempt_of(cp0)
    (gap,) = json.loads(cpdr.view(store, attempt)[1])["gaps"]
    assert gap == {
        "gap_id": "g",
        "kind": "scope",
        "severity": "material",
        "description": text,
        "named_consumers": None,
        "remediation": None,
    }


# --- the validator the entry hands Execution.submit_step -------------------------------------------


def test_entry_validator_retains_the_validated_submission() -> None:
    text = json.dumps(SUBMISSIONS["cpdr"]["partial"])
    attempt, store = attempt_of(cp0_module(empty=False), text)
    outcome = cpdr.ENTRY_VALIDATOR(store, store.pack(), attempt)
    assert outcome.issues == ()
    assert outcome.output == submission(SUBMISSIONS["cpdr"]["partial"]).model_dump_json()


@pytest.mark.parametrize("name", list(EXPECTED["refusals"]))
def test_entry_validator_refuses_with_the_content_issues(name: str) -> None:
    item = SUBMISSIONS["refusal_inputs"][name]
    empty = item["cp0"] == "cp0_readiness_review_empty_agenda"
    text = json.dumps(item["payload"])
    attempt, store = attempt_of(cp0_module(empty=empty), text)
    outcome = cpdr.ENTRY_VALIDATOR(store, store.pack(), attempt)
    pinned = tuple(EXPECTED["refusals"][name]["step_issues"])
    content = tuple(i for i in pinned if not i.startswith(RULES_PREFIXES))
    assert outcome.issues == content
    # a class whose only issues are RULES (tool use) passes the content validator
    assert (outcome.output is None) == bool(content)


@pytest.mark.parametrize("text", ["not json", "[1]", '{"gaps": 3}', '{"gaps": [], "extra": 1}'])
def test_entry_validator_reports_a_shape_issue_not_an_exception(text: str) -> None:
    attempt, store = attempt_of(cp0_module(empty=False), text)
    outcome = cpdr.ENTRY_VALIDATOR(store, store.pack(), attempt)
    assert outcome.output is None
    assert outcome.issues
    assert all(len(line) <= 600 for line in outcome.issues)


# --- the candidate module and the tail input -------------------------------------------------------


@pytest.mark.parametrize("case", ["partial", "unresolved", "empty_agenda"])
def test_research_module_is_the_oracle_result_bound_to_its_inputs(case: str) -> None:
    empty = case == "empty_agenda"
    want = EXPECTED["cases"][case]
    sub = submission(SUBMISSIONS["cpdr"][case])
    attempt, store = attempt_of(cp0_module(empty=empty))
    inputs = cpdr._inputs(store, attempt, sub)
    report = cpdr.compose(inputs)
    module = cpdr.research_module(
        report=report, inputs=inputs, attempt=attempt, run=store.read().run
    )
    assert module.module_id == "CP-DR"
    assert module.status == "candidate"
    assert module.inputs == (
        *attempt.inputs,
        Input(input_id="research-submission", sha256=sub.content_hash()),
    )
    assert [i.input_id for i in module.inputs] == [
        *EXPECTED["attempt_inputs"],
        EXPECTED["settled_module_adds_input"],
    ]
    assert [f.fact_id for f in module.facts] == [f["fact_id"] for f in want["facts"]]
    assert module.limitations == tuple(want["own_limitations"])
    assert [t.table_id for t in module.tables] == list(want["tables"])
    assert [c.claim_id for c in module.claims] == [c["claim_id"] for c in want["claims"]]
    assert (module.run_id, module.issuer_id, module.as_of, module.attempt) == (
        MANIFEST["run"]["run_id"],
        MANIFEST["run"]["issuer_id"],
        AS_OF,
        0,
    )
    assert module.facts == report.facts
    assert module.tables == report.tables
    assert module.claims == report.claims


def test_research_module_carries_the_attempt_number() -> None:
    sub = submission(SUBMISSIONS["cpdr"]["partial"])
    attempt, store = attempt_of(cp0_module(empty=False))
    inputs = cpdr._inputs(store, attempt, sub)
    second = attempt.model_copy(update={"number": 1})
    module = cpdr.research_module(
        report=cpdr.compose(inputs), inputs=inputs, attempt=second, run=store.read().run
    )
    assert module.attempt == 1


# --- the consumer reader (D3 is OPEN: the reader and what it exposes, no completion claim) ---------


def settled(module: Module, status: str = "restricted") -> tuple[Store, Head]:
    final = module.model_copy(update={"status": status})
    if status == "stale":  # staleness is the head's, never the blob's
        head = head_of(final.model_copy(update={"status": "restricted"})).model_copy(
            update={"status": "stale", "notes": ("CP-0 changed",)}
        )
    else:
        head = head_of(final)
    return Store(prepared_pack(), {head.result_sha256: final}, {}, head_only=True), head


@pytest.mark.parametrize("case", ["partial", "unresolved", "empty_agenda"])
def test_reader_exposes_what_the_lease_pins(case: str) -> None:
    empty = case == "empty_agenda"
    want = EXPECTED["cases"][case]
    sub = submission(SUBMISSIONS["cpdr"][case])
    attempt, store = attempt_of(cp0_module(empty=empty))
    inputs = cpdr._inputs(store, attempt, sub)
    module = cpdr.research_module(
        report=cpdr.compose(inputs), inputs=inputs, attempt=attempt, run=store.read().run
    )
    served, head = settled(module)
    got = cpdr.cpdr_reader(served, head)
    book = want["bookkeeping"]
    assert got.result_sha256 == head.result_sha256
    assert got.status == "restricted" == want["module_status"]
    assert [(g.gap_id, g.status, g.questions, g.answered) for g in got.gaps] == [
        (g["gap_id"], g["status"], g["questions"], g["answered"]) for g in book["gaps"]
    ]
    assert got.totals is not None
    assert (
        got.totals.gaps_total,
        got.totals.gaps_resolved,
        got.totals.gaps_partial,
        got.totals.gaps_unresolved,
        got.totals.questions_total,
        got.totals.answered_total,
        got.totals.unresolved_total,
    ) == tuple(book[k] for k in TOTALS)
    share = book["answered_share"]
    assert got.totals.answered_share == (None if share is None else Decimal(share))
    assert got.unresolved == tuple(
        f.removeprefix("TDR.2.").removesuffix(".answer")
        for f in want["consumption_facts"]["missing_for_unresolved"]
    )


def test_reader_exposes_no_more_than_the_lease_lists() -> None:
    assert [f.name for f in fields(cpdr.CpdrHead)] == [
        "result_sha256",
        "status",
        "gaps",
        "totals",
        "unresolved",
    ]
    assert [f.name for f in fields(cpdr.CpdrGapHead)] == [
        "gap_id",
        "status",
        "questions",
        "answered",
    ]
    assert [f.name for f in fields(cpdr.CpdrTotals)] == [*TOTALS, "answered_share"]


def test_reader_of_a_blocked_head_exposes_the_status_only() -> None:
    blocked = cp0_module(empty=False, status="blocked").model_copy(
        update={"module_id": "CP-DR", "facts": (), "limitations": ("Quote mismatch",)}
    )
    served, head = settled(blocked, "blocked")
    got = cpdr.cpdr_reader(served, head)
    assert (got.status, got.gaps, got.totals, got.unresolved) == ("blocked", (), None, ())


def test_reader_refuses_another_modules_head() -> None:
    served, head = settled(cp0_module(empty=False))
    with pytest.raises(ValueError, match="Not a CP-DR head"):
        cpdr.cpdr_reader(served, head)


def test_reader_fails_closed_on_a_result_without_the_total_facts() -> None:
    sub = submission(SUBMISSIONS["cpdr"]["partial"])
    attempt, store = attempt_of(cp0_module(empty=False))
    inputs = cpdr._inputs(store, attempt, sub)
    module = cpdr.research_module(
        report=cpdr.compose(inputs), inputs=inputs, attempt=attempt, run=store.read().run
    )
    trimmed = module.model_copy(update={"facts": (), "tables": (), "claims": ()})
    served, head = settled(trimmed)
    with pytest.raises(ValueError, match="TDR"):
        cpdr.cpdr_reader(served, head)


# --- registrations (lease: Files, Public API; protocol section 2) ----------------------------------


def test_owner_spec_row_equals_the_lease() -> None:
    assert owner.OWNER_SPECS["CP-DR"] == owner.OwnerSpec(
        module_id="CP-DR",
        steps=(
            owner.StepSpec(
                step_id="research",
                schema=cpdr.ResearchSubmission,
                sources=True,
                extract=False,
                upstream_grant=None,
                inputs="module_context",
                rules="journaled",
            ),
        ),
        entry="owner_core",
        kind="analytical",
        publish=None,
    )


def test_registration_rows_equal_the_lease() -> None:
    assert owner._CORES["CP-DR"] is cpdr
    assert "CP-DR" in owner.SUPPORTED_ANALYTICAL
    assert owner._QUALIFICATION["CP-DR"] == cpdr.QUALIFICATION
    assert owner._PROBES["CP-DR"] is cpdr.probe
    assert owner._VIEWS["research"] is cpdr.view
    assert owner._ENTRY_VALIDATORS["CP-DR"] is cpdr.ENTRY_VALIDATOR
    assert "CP-DR" not in owner._PRECHECKS  # lease: no precheck (ruling Q5)


def test_registrations_are_appended_after_the_existing_rows() -> None:
    for table in (owner._QUALIFICATION, owner._PROBES, owner._ENTRY_VALIDATORS, owner.OWNER_SPECS):
        keys = list(table)
        assert keys.index("CP-DR") > keys.index("CP-2")
    assert list(owner._PROBES)[:4] == ["CP-0", "CP-1", "CP-1A", "CP-2"]
    assert list(owner._VIEWS)[:1] == ["credit_synthesis"]
    assert list(owner._VIEWS).index("research") == 1


def test_the_spec_passes_the_create_time_step_check() -> None:
    owner._check_steps("CP-DR", owner.OWNER_SPECS["CP-DR"])


def test_the_h1_host_rows_for_cpdr_exist() -> None:
    assert host._SOURCE_STEPS["CP-DR"] == ("research",)
    assert ("CP-DR", "research") in host._OWNER_SCOPES


# --- bindings (lease D-C, Rendered sections D7/D8) -------------------------------------------------


def test_bindings_are_rails_only_and_prefixed() -> None:
    assert CPDR.module_id == "CP-DR"
    assert {(e.fact_coord.table_id, e.block_id) for e in CPDR.entries} == {
        ("TDR.1", "evidence"),
        ("TDR.2", "evidence"),
        ("TDR.3", "limitations"),
    }
    assert all(e.cell_slot.startswith("cpdr-") for e in CPDR.entries)
    assert all(e.block_id in RAIL_DESTINATIONS for e in CPDR.entries)
    assert [e.cell_slot for e in CPDR.entries] == ["cpdr-tdr-1", "cpdr-tdr-2", "cpdr-tdr-3"]


def test_shipped_maps_list_cpdr_after_the_existing_maps() -> None:
    ids = [m.module_id for m in SHIPPED_MAPS]
    assert ids.index("CP-DR") > ids.index("CP-6")
    assert ids.count("CP-DR") == 1
    assert SHIPPED_MAPS[ids.index("CP-DR")] is CPDR


@pytest.mark.parametrize("case", ["partial", "unresolved", "empty_agenda"])
def test_expected_tables_bind_without_a_gap_or_double_binding(case: str) -> None:
    empty = case == "empty_agenda"
    sub = submission(SUBMISSIONS["cpdr"][case])
    attempt, store = attempt_of(cp0_module(empty=empty))
    inputs = cpdr._inputs(store, attempt, sub)
    module = cpdr.research_module(
        report=cpdr.compose(inputs), inputs=inputs, attempt=attempt, run=store.read().run
    )
    shown = ModuleView(
        module_id="CP-DR",
        title="Deep research",
        aliases=(),
        status="restricted",
        artifact_sha256=module.content_hash(),
        facts=module.facts,
        tables=module.tables,
        claims=module.claims,
        limitations=module.limitations,
    )
    view = View(run=store.read().run, mode="accepted", modules=(shown,))
    assert validate_bindings(view, SHIPPED_MAPS) == ()


def test_rail_blocks_need_no_spec_row() -> None:
    """`_spec_of` has no composition row for a rail: nothing produces it as a Front Page block."""
    for block in ("evidence", "limitations"):
        assert report_view._spec_of(block).producers == ()


# --- a real store: CP-0 settled, then CP-DR through submit / probe / the reader ---------------------
# The store is a real `Execution` and CP-0 settles through `submit_cp0_review` (pure Python, no
# tool session). The session-bound run (`OwnerWorkflow`, tool receipts, tamper) is Stage 5.

PACK_MARK = "<<PACK_SHA256: PreparedPack.content_hash() of the run's pack, bound at run time>>"


def settled_cp0(root: Path, *, empty: bool = False) -> Execution:
    pack = prepared_pack()
    store = Execution.create(root / "store", pack)
    key = "cp0_readiness_review_empty_agenda" if empty else "cp0_readiness_review"
    text = json.dumps(SUBMISSIONS[key]).replace(PACK_MARK, pack.content_hash())
    cp0 = submit_cp0_review(store, store.begin("CP-0").ticket_id, text)
    assert cp0.status == "finished"
    assert not cp0.issues
    return store


def clone(store: Execution, root: Path) -> Execution:
    shutil.copytree(store.directory, root / "clone")
    return Execution(root / "clone")


def run_cpdr(store: Execution, payload: Any, calls: list[dict[str, Any]] | None = None) -> Attempt:
    """Submit `payload` as attempt 0 or 1 of CP-DR with the oracle's tool use as `Seen`."""
    seen = seen_of([] if calls is None else calls)
    ticket = store.begin("CP-DR").ticket_id
    outcome = cpdr.submit(
        store, ticket, "research", json.dumps(payload), lambda text: cpdr.RULES(text, seen)
    )
    return outcome.journal


def cpdr_head(store: Execution) -> Head:
    return next(h for h in store.read().heads if h.module_id == "CP-DR")


@pytest.mark.parametrize("case", ["partial", "unresolved", "empty_agenda"])
def test_a_valid_submission_settles_the_oracle_result(case: str, tmp_path: Path) -> None:
    want = EXPECTED["cases"][case]
    store = settled_cp0(tmp_path, empty=case == "empty_agenda")
    calls = [c for c in SUBMISSIONS["tool_calls"][case] if c["tool"] != "read_inputs"]
    attempt = run_cpdr(store, SUBMISSIONS["cpdr"][case], calls)
    assert attempt.status == "finished"
    assert attempt.issues == ()
    assert attempt.steps[0].status == "valid"
    module = store.head_module(cpdr_head(store))
    assert module.status == want["module_status"]
    assert list(module.limitations) == want["settled_limitations"]
    assert list(module.inherited_limitations) == want["inherited_limitations"]
    assert [i.input_id for i in module.inputs] == [
        *EXPECTED["attempt_inputs"],
        EXPECTED["settled_module_adds_input"],
    ]
    assert module.inputs[-1].sha256 == submission(SUBMISSIONS["cpdr"][case]).content_hash()
    assert module.facts == tuple(oracle_fact(f) for f in want["facts"])
    assert [c.text for c in module.claims] == [c["text"] for c in want["claims"]]
    assert cpdr_head(store).qualification == cpdr.QUALIFICATION


@pytest.mark.parametrize("case", ["partial", "unresolved", "empty_agenda"])
def test_probe_accepts_the_settled_attempt(case: str, tmp_path: Path) -> None:
    store = settled_cp0(tmp_path, empty=case == "empty_agenda")
    calls = [c for c in SUBMISSIONS["tool_calls"][case] if c["tool"] != "read_inputs"]
    attempt = run_cpdr(store, SUBMISSIONS["cpdr"][case], calls)
    cpdr.probe(store, store.read(), attempt)


def test_probe_refuses_a_result_that_is_not_the_rebuilt_candidate(tmp_path: Path) -> None:
    """The tamper of the lease (a settled fact edited, hashes rewritten) is refused by the probe."""
    store = settled_cp0(tmp_path)
    attempt = run_cpdr(store, SUBMISSIONS["cpdr"]["partial"], seen_calls("partial"))
    snapshot = store.read()
    head = cpdr_head(store)
    module = store.head_module(head)
    target = "TDR.1.missing-ownership-transaction.status"
    forged = module.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"text": "Resolved"}) if f.fact_id == target else f
                for f in module.facts
            )
        }
    )
    digest = hashlib.sha256(forged.model_dump_json().encode()).hexdigest()
    assert store._store(forged.model_dump_json()) == digest
    new_head = head_of(forged, cpdr.QUALIFICATION)
    forged_attempt = attempt.model_copy(update={"result_sha256": new_head.result_sha256})
    forged_snapshot = snapshot.model_copy(
        update={
            "heads": tuple(new_head if h.module_id == "CP-DR" else h for h in snapshot.heads),
            "attempts": tuple(
                forged_attempt if a.ticket_id == attempt.ticket_id else a for a in snapshot.attempts
            ),
        }
    )
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        cpdr.probe(store, forged_snapshot, forged_attempt)


def seen_calls(case: str) -> list[dict[str, Any]]:
    return [c for c in SUBMISSIONS["tool_calls"][case] if c["tool"] != "read_inputs"]


@pytest.mark.parametrize("name", list(EXPECTED["refusals"]))
def test_each_refusal_is_a_journaled_invalid_step_with_the_pinned_issues(
    name: str, tmp_path: Path
) -> None:
    item = SUBMISSIONS["refusal_inputs"][name]
    base = settled_cp0(tmp_path, empty=item["cp0"] == "cp0_readiness_review_empty_agenda")
    calls = item["calls"]
    if isinstance(calls, str):
        calls = SUBMISSIONS["tool_calls"][calls]
    attempt = run_cpdr(clone(base, tmp_path), item["payload"], calls)
    pinned = tuple(EXPECTED["refusals"][name]["step_issues"])
    assert attempt.status == "finished"
    assert attempt.steps[0].status == "invalid"
    assert attempt.steps[0].issues == pinned
    assert attempt.issues == pinned


def test_the_blocked_case_consumes_two_attempts_and_exposes_the_status_only(
    tmp_path: Path,
) -> None:
    store = settled_cp0(tmp_path)
    calls = SUBMISSIONS["tool_calls"]["blocked"]
    zero = run_cpdr(store, SUBMISSIONS["cpdr"]["blocked"]["attempt_0"], calls)
    one = run_cpdr(store, SUBMISSIONS["cpdr"]["blocked"]["attempt_1"], calls)
    assert zero.steps[0].issues == tuple(EXPECTED["blocked"]["attempt_0"]["issues"])
    assert one.steps[0].issues == tuple(EXPECTED["blocked"]["attempt_1"]["issues"])
    head = cpdr_head(store)
    assert head.status == "blocked"
    reader = cpdr.cpdr_reader(store, head)
    assert (reader.status, reader.gaps, reader.totals, reader.unresolved) == (
        "blocked",
        (),
        None,
        (),
    )


def test_submit_refuses_another_step_and_another_modules_ticket(tmp_path: Path) -> None:
    store = settled_cp0(tmp_path)
    ticket = store.begin("CP-DR").ticket_id
    with pytest.raises(ValueError, match="one step"):
        cpdr.submit(store, ticket, "other", "{}", None)
    with pytest.raises(ValueError, match="absent"):
        cpdr.submit(store, "no-such-ticket", "research", "{}", None)


def test_submit_without_rules_journals_the_content_issues_only(tmp_path: Path) -> None:
    store = settled_cp0(tmp_path)
    attempt = run_cpdr(store, {"gaps": []})
    assert attempt.steps[0].issues == (
        "a gap takes 1 to 4 research questions: missing-ownership-transaction",
    )


def test_the_view_a_real_attempt_reads_is_the_draft_tree(tmp_path: Path) -> None:
    store = settled_cp0(tmp_path)
    attempt = store.begin("CP-DR")
    assert json.loads(cpdr.view(store, attempt)[1]) == DRAFT_KEYS


def test_the_method_note_is_installed_with_its_guard_limits() -> None:
    note = (Path(__file__).parents[1] / "src/deploy_vii/methods/cpdr.md").read_text()
    assert "DRAFT" not in note
    assert "## Guard limits" in note
    assert not (Path(__file__).parents[1] / "docs/methods-drafts/cpdr.md").exists()


def _partial_module() -> Module:
    sub = submission(SUBMISSIONS["cpdr"]["partial"])
    attempt, store = attempt_of(cp0_module(empty=False))
    inputs = cpdr._inputs(store, attempt, sub)
    return cpdr.research_module(
        report=cpdr.compose(inputs), inputs=inputs, attempt=attempt, run=store.read().run
    )


def test_reader_refuses_tdr1_rows_that_differ_from_the_gap_total() -> None:
    module = _partial_module()
    rows_gone = module.model_copy(
        update={"tables": tuple(t for t in module.tables if t.table_id != "TDR.1")}
    )
    served, head = settled(rows_gone)
    with pytest.raises(ValueError, match="differ from the TDR.3 gap total"):
        cpdr.cpdr_reader(served, head)


def test_reader_refuses_a_share_that_is_neither_known_nor_not_applicable() -> None:
    module = _partial_module()
    broken = module.model_copy(
        update={
            "facts": tuple(
                Fact(
                    fact_id=f.fact_id,
                    label=f.label,
                    table_id=f.table_id,
                    row_id=f.row_id,
                    field=f.field,
                    status="missing",
                    limitation="share not stated",
                )
                if f.fact_id == "TDR.3.total.answered_share"
                else f
                for f in module.facts
            )
        }
    )
    served, head = settled(broken)
    with pytest.raises(ValueError, match="neither known nor not applicable"):
        cpdr.cpdr_reader(served, head)


def test_upstream_refuses_a_bound_input_that_is_not_the_cp0_module() -> None:
    attempt, store = attempt_of(cp0_module(empty=False))
    other = cp0_module(empty=False).model_copy(update={"module_id": "CP-1"})
    store._modules[attempt.inputs[1].sha256] = other
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        cpdr.cpdr_upstream(store=store, attempt=attempt)


@pytest.mark.parametrize("text", ["not json", "[1]", '{"gaps": [{"a": 1}'])
def test_entry_validator_names_text_the_journal_cannot_store(text: str) -> None:
    attempt, store = attempt_of(cp0_module(empty=False), text)
    outcome = cpdr.ENTRY_VALIDATOR(store, store.pack(), attempt)
    assert outcome.issues == ("(root): payload is not a JSON object the journal can store",)


# --- fixtures that vary what the oracle holds constant (review L1) -----------------------------


def test_upstream_and_view_carry_the_status_the_attempt_bound_cp0_at() -> None:
    attempt, store = attempt_of(cp0_module(empty=False, status="accepted"), cp0_status="accepted")
    assert cpdr.cpdr_upstream(store=store, attempt=attempt).cp0_status == "accepted"
    assert json.loads(cpdr.view(store, attempt)[1])["upstream"] == {"CP-0": "accepted"}


def test_adapter_reads_the_as_of_of_whatever_run_the_store_holds() -> None:
    base = prepared_pack()
    other = Run.model_validate_json(json.dumps({**MANIFEST["run"], "as_of": "2026-02-02"}))
    pack = PreparedPack(run=other, sources=base.sources)
    attempt, store = attempt_of(cp0_module(empty=False), pack=pack)
    got = cpdr._inputs(store, attempt, submission(SUBMISSIONS["cpdr"]["partial"]))
    assert got.as_of == date(2026, 2, 2)


def test_upstream_and_view_carry_the_status_of_every_pack_source() -> None:
    missing = Source(
        source_id="registry", name="Register", status="missing", limitation="Not supplied."
    )
    base = prepared_pack()
    pack = PreparedPack(run=base.run, sources=(*base.sources, missing))
    attempt, store = attempt_of(cp0_module(empty=False), pack=pack)
    got = cpdr.cpdr_upstream(store=store, attempt=attempt)
    assert got.sources[-1] == ("registry", "missing")
    assert json.loads(cpdr.view(store, attempt)[1])["sources"][-1] == {
        "source_id": "registry",
        "status": "missing",
    }


def test_reader_status_is_the_heads_not_a_constant_and_reads_through_head_module() -> None:
    module = _partial_module()
    for status in ("accepted", "stale"):
        served, head = settled(module, status)
        assert cpdr.cpdr_reader(served, head).status == status


# --- cpdr_reader fails closed on a forged result (review L2) -----------------------------------


def _forged(module: Module, fact_id: str, **update: Any) -> Module:
    return module.model_copy(
        update={
            "facts": tuple(
                Fact.model_validate({**f.model_dump(), **update}) if f.fact_id == fact_id else f
                for f in module.facts
            )
        }
    )


def test_reader_refuses_a_known_share_carried_as_text() -> None:
    module = _forged(
        _partial_module(),
        "TDR.3.total.answered_share",
        amount=None,
        text="0.6667",
        unit=None,
        period=None,
    )
    served, head = settled(module)
    with pytest.raises(ValueError, match="share"):
        cpdr.cpdr_reader(served, head)


def test_reader_refuses_a_non_integral_count() -> None:
    module = _forged(_partial_module(), "TDR.3.total.questions_total", amount=Decimal("3.9"))
    served, head = settled(module)
    with pytest.raises(ValueError, match="not a known count"):
        cpdr.cpdr_reader(served, head)


@pytest.mark.parametrize("field", ["unresolved", "answered_share"])
def test_reader_refuses_a_result_without_the_per_gap_consumption_facts(field: str) -> None:
    module = _partial_module()
    gone = f"TDR.1.{GAP_ID}.{field}"
    trimmed = module.model_copy(
        update={"facts": tuple(f for f in module.facts if f.fact_id != gone)}
    )
    trimmed = trimmed.model_copy(
        update={
            "tables": tuple(
                t.model_copy(
                    update={
                        "rows": tuple(
                            r.model_copy(
                                update={"fact_ids": tuple(i for i in r.fact_ids if i != gone)}
                            )
                            for r in t.rows
                        )
                    }
                )
                for t in module.tables
            )
        }
    )
    served, head = settled(trimmed)
    with pytest.raises(ValueError, match="TDR"):
        cpdr.cpdr_reader(served, head)


def test_reader_refuses_per_gap_counts_that_do_not_add_up() -> None:
    module = _forged(_partial_module(), f"TDR.1.{GAP_ID}.unresolved", amount=Decimal(2))
    served, head = settled(module)
    with pytest.raises(ValueError, match="unresolved"):
        cpdr.cpdr_reader(served, head)


def test_reader_refuses_a_negative_count() -> None:
    """L2b: a forged count below zero is not a count (the `found.amount < 0` check)."""
    module = _forged(_partial_module(), "TDR.3.total.questions_total", amount=Decimal(-1))
    served, head = settled(module)
    with pytest.raises(ValueError, match="not a known count"):
        cpdr.cpdr_reader(served, head)


def test_reader_refuses_a_per_gap_share_that_is_not_known() -> None:
    """L2f: the per-gap share must be a known amount (the lease lists it for consumption)."""
    module = _forged(
        _partial_module(),
        f"TDR.1.{GAP_ID}.answered_share",
        status="missing",
        amount=None,
        unit=None,
        period=None,
        limitation="Not stated.",
    )
    served, head = settled(module)
    with pytest.raises(ValueError, match="answered share is not known"):
        cpdr.cpdr_reader(served, head)


# --- question_id length and the unconditional RunText check (Stage 2 close release) -------------


def _with_question_id(question_id: str) -> dict[str, Any]:
    payload = copy.deepcopy(SUBMISSIONS["cpdr"]["partial"])
    payload["gaps"][0]["questions"][0]["question_id"] = question_id
    return payload


def test_the_longest_accepted_question_id_composes() -> None:
    """Every id Python derives from a question id (`TDR.2.<id>.<field>`, `cpdr-<id>-<field>`,
    `CPDR-ANS-<id>`) is an `Identifier`: the longest id the validator accepts composes."""
    longest = "q" * cpdr.QUESTION_ID_MAX
    sub = submission(_with_question_id(longest))
    assert check(sub) == ()
    attempt, store = attempt_of(cp0_module(empty=False))
    inputs = cpdr._inputs(store, attempt, sub)
    assert cpdr.compose(inputs).facts


@pytest.mark.parametrize("extra", [1, 15])
def test_a_question_id_too_long_to_compose_is_refused_at_validation(extra: int) -> None:
    qid = "q" * (cpdr.QUESTION_ID_MAX + extra)
    sub = submission(_with_question_id(qid))
    expected = (
        f"question_id is too long to compose its fact ids (at most {cpdr.QUESTION_ID_MAX} "
        f"characters): {qid}"
    )
    assert check(sub) == (expected,)
    attempt, store = attempt_of(cp0_module(empty=False), json.dumps(_with_question_id(qid)))
    outcome = cpdr.ENTRY_VALIDATOR(store, store.pack(), attempt)
    assert outcome.output is None
    assert any(line.startswith("question_id is too long") for line in outcome.issues)


def test_question_id_max_is_the_longest_id_the_composer_accepts() -> None:
    """The constant is tight: one more character makes `Fact` raise."""
    attempt, store = attempt_of(cp0_module(empty=False))
    sub = submission(_with_question_id("q" * (cpdr.QUESTION_ID_MAX + 1)))
    inputs = cpdr._inputs(store, attempt, sub)
    with pytest.raises(ValueError, match="Fact"):
        cpdr.compose(inputs)


# --- gap_id length (Stage 5) ---------------------------------------------------------------------

# The CP-0 fact `T5.<gap>.gap` is itself an `Identifier`, so the longest agenda gap id a CP-0
# module can carry is 160 less `T5.` and `.gap`.
CP0_GAP_ID_LONGEST = cpdr.IDENTIFIER_MAX - len("T5.") - len(".gap")


def _with_gap_id(gap_id: str) -> tuple[dict[str, Any], Module]:
    """A submission payload and a CP-0 module whose single agenda gap carries `gap_id`."""
    (fact, other) = cp0_facts(empty=False)
    renamed = fact.model_copy(update={"fact_id": f"T5.{gap_id}.gap", "row_id": gap_id})
    module = cp0_module(empty=False).model_copy(update={"facts": (renamed, other)})
    payload = copy.deepcopy(SUBMISSIONS["cpdr"]["partial"])
    payload["gaps"][0]["gap_id"] = gap_id
    return payload, module


def test_the_longest_accepted_gap_id_composes() -> None:
    """Every id Python derives from a gap id (`TDR.1.<id>.<field>`, `cpdr-<id>-<field>`) is an
    `Identifier`: the longest id the validator accepts composes."""
    payload, module = _with_gap_id("g" * cpdr.GAP_ID_MAX)
    sub = submission(payload)
    attempt, store = attempt_of(module)
    inputs = cpdr._inputs(store, attempt, sub)
    assert cpdr.validate_research(submission=sub, upstream=inputs.agenda, pack=sources()) == ()
    assert cpdr.compose(inputs).facts


@pytest.mark.parametrize("length_of", ["one-past", "longest-cp0-gap"])
def test_a_gap_id_too_long_to_compose_is_refused_at_validation(length_of: str) -> None:
    gap_id = "g" * (cpdr.GAP_ID_MAX + 1 if length_of == "one-past" else CP0_GAP_ID_LONGEST)
    payload, module = _with_gap_id(gap_id)
    expected = (
        f"gap_id is too long to compose its fact ids (at most {cpdr.GAP_ID_MAX} "
        f"characters): {gap_id}"
    )
    attempt, store = attempt_of(module, json.dumps(payload))
    inputs = cpdr._inputs(store, attempt, submission(payload))
    assert cpdr.validate_research(
        submission=inputs.submission, upstream=inputs.agenda, pack=sources()
    ) == (expected,)
    outcome = cpdr.ENTRY_VALIDATOR(store, store.pack(), attempt)
    assert outcome.output is None
    assert expected in outcome.issues


def test_gap_id_max_is_the_longest_id_the_composer_accepts() -> None:
    """The constant is tight: one more character makes `Fact` raise."""
    payload, module = _with_gap_id("g" * (cpdr.GAP_ID_MAX + 1))
    attempt, store = attempt_of(module)
    inputs = cpdr._inputs(store, attempt, submission(payload))
    with pytest.raises(ValueError, match="Fact"):
        cpdr.compose(inputs)


def test_a_malformed_answer_is_reported_beside_a_content_issue() -> None:
    """The RunText check is unconditional (as CP-2E's): a content issue no longer masks it."""
    payload = copy.deepcopy(SUBMISSIONS["cpdr"]["partial"])
    question = payload["gaps"][0]["questions"][0]
    question["answer"] = "Rates matter [a lot"
    question["limitation"] = "Some limitation text"
    issues = check(submission(payload))
    malformed = "gaps[0].questions[0].answer: Value error, Malformed run text: unbalanced or empty reference"
    assert issues == ("an answered question carries no limitation: transactions", malformed)
    question["limitation"] = None
    assert check(submission(payload)) == issues[1:]


# --- free text is not run text (rulings item 56) ----------------------------------------------------


def test_a_question_with_a_bracketed_citation_renders_as_written() -> None:
    from deploy_vii.contracts import ModuleView as _MV
    from deploy_vii.render import empty_view, render

    payload = copy.deepcopy(SUBMISSIONS["cpdr"]["partial"])
    question = payload["gaps"][0]["questions"][0]
    question["text"] = question["text"].rstrip("?") + " [sic]?"
    attempt, store = attempt_of(cp0_module(empty=False), json.dumps(payload))
    assert cpdr.ENTRY_VALIDATOR(store, store.pack(), attempt).issues == ()
    inputs = cpdr._inputs(store, attempt, submission(payload))
    run = store.read().run
    module = cpdr.research_module(
        report=cpdr.compose(inputs), inputs=inputs, attempt=attempt, run=run
    )
    base = empty_view(run, candidate=False)
    mods = tuple(
        _MV(
            module_id=m.module_id,
            title=m.title,
            aliases=m.aliases,
            status="restricted",
            artifact_sha256=module.content_hash(),
            facts=module.facts,
            tables=module.tables,
            claims=module.claims,
            limitations=module.limitations,
        )
        if m.module_id == "CP-DR"
        else m
        for m in base.modules
    )
    page = render(base.model_copy(update={"modules": mods}))
    assert "[sic]?" in page
